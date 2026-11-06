"""Independent premerge exception/immutability probes; no test-helper imports.

Run from the reviewed repository with PYTHONDONTWRITEBYTECODE=1 and PYTHONPATH=.
All captures are real; temporary policy input is copied outside the checkout.
"""
from __future__ import annotations

from contextlib import ExitStack
from dataclasses import fields, replace
import hashlib
import importlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
from unittest.mock import patch

from layauto_v2.domain.codec import FrozenMap, canonical_bytes, decode
from layauto_v2.domain.evidence import EvidenceRecord
from layauto_v2.domain.publication import InputsReady, RunRequest
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import build_effective_geometry, build_geometry, geometry_from_parse_result
from layauto_v2.normalization.geometry_input import geometry_from_inputs_ready
from layauto_v2.normalization import local_connectivity as local
from layauto_v2.normalization import local_connectivity_codec as codec
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository

ROOT = Path(__file__).resolve().parents[4]
OUTPUT = Path(__file__).with_name('exception-results.json')
checks = []


def check(name, passed, **detail):
    row = dict(name=name, passed=bool(passed), **detail)
    checks.append(row)
    print(json.dumps(row), flush=True)


def mutable(value):
    if type(value) is FrozenMap:
        return {key: mutable(item) for key, item in value.items()}
    if type(value) is tuple:
        return [mutable(item) for item in value]
    return value


def tamper(value, **changes):
    obj = object.__new__(type(value))
    for field in fields(value):
        object.__setattr__(obj, field.name, changes.get(field.name, getattr(value, field.name)))
    return obj


def fault_case(name, operation, target, failure_type, *, suppression=False, gate=None):
    failure = failure_type('independent-premerge injected fault')
    cause, context = RuntimeError('retained cause'), LookupError('retained context')
    failure.__cause__, failure.__context__, failure.__suppress_context__ = cause, context, suppression
    calls = 0
    module_name, attribute = target.rsplit('.', 1)
    module = importlib.import_module(module_name)
    original = getattr(module, attribute)

    def broken(*args, **kwargs):
        nonlocal calls
        calls += 1
        if gate is None or gate():
            raise failure
        return original(*args, **kwargs)

    replacement = SimpleNamespace(sha256=broken) if attribute == 'hashlib' else broken
    # hashlib's real function is needed on the first authentication.
    if attribute == 'hashlib':
        original = original.sha256
    with patch.object(module, attribute, replacement):
        try:
            operation()
        except BaseException as observed:
            check(name, observed is failure and observed.__cause__ is cause
                  and observed.__context__ is context and observed.__suppress_context__ is suppression,
                  target=target, fault=failure_type.__name__, calls=calls,
                  received=type(observed).__name__, same_object=observed is failure,
                  context=type(observed.__context__).__name__ if observed.__context__ else None,
                  suppression=suppression)
        else:
            check(name, False, target=target, reason='injection not reached')


def explicitly_rejected(name, action):
    try:
        action()
    except ValueError as exc:
        check(name, bool(str(exc)), exception=type(exc).__name__, message=str(exc))
    except BaseException as exc:
        check(name, False, exception=type(exc).__name__, message=str(exc))
    else:
        check(name, False, reason='unexpected accepted value')


def make_effective(site, readback=False, suffix='normal'):
    if not readback:
        parsed = read_inputs(site)
        assert parsed.status == 'success', parsed.issues
        geometry_input = geometry_from_parse_result(parsed)
    else:
        repository = PublicationRepository()
        ready = prepare_inputs(repository, RunRequest(
            proposed_run_id='independent-exception-' + suffix,
            lineage_id='independent-exception-lineage', idempotency_key='create-' + suffix,
            site_path=str(site)))
        assert isinstance(ready, InputsReady), ready
        geometry_input = geometry_from_inputs_ready(
            ready, repository.load_checkpoint(ready.run_id), repository.read(ready.parse_ref),
            repository.read(ready.tool_ref), tuple(repository.read(ref) for ref in ready.evidence_refs))
    result = build_effective_geometry(build_geometry(geometry_input))
    assert result.status == 'success'
    return result


def main():
    started = time.time()
    site = ROOT / 'tests/fixtures/w003_m1/site_config.yaml'
    effective = make_effective(site)
    direct = local.build_local_connectivity(effective)
    readback = local.build_local_connectivity(make_effective(site, True))
    assert direct.status == readback.status == 'success' and direct.value == readback.value
    records = {'direct': direct, 'readback': readback}
    wires = {name: codec.encode_record(value) for name, value in records.items()}
    for name, value in records.items():
        rebuilt = codec.decode_record(wires[name])
        check('roundtrip-' + name, rebuilt == value and codec.record_digest(rebuilt) == codec.record_digest(value))

    targets = (
        'layauto_v2.state.local_connectivity.same_layer_contact',
        'layauto_v2.state.local_connectivity.encloses_connector',
        'layauto_v2.state.local_connectivity._components',
        'layauto_v2.state.regions.slab_difference',
        'layauto_v2.state.layout_store._materialize',
        'layauto_v2.state.coordinate._layers',
        'layauto_v2.state.occupancy._fragments',
        'layauto_v2.normalization.contracts.request_decoder_input',
        'layauto_v2.normalization._validation._validate_cdl',
        'layauto_v2.normalization._validation._validate_query',
        'layauto_v2.domain.evidence.hashlib',
    )
    for name, wire in wires.items():
        for index, target in enumerate(targets + (('layauto_v2.normalization.contracts.content_ref',) if name == 'readback' else ())):
            for failure_type in (ValueError, TypeError, KeyboardInterrupt, SystemExit):
                fault_case('nested-' + name, lambda: codec.decode_record(wire), target, failure_type,
                           suppression=bool(index % 2))
    for target in targets:
        fault_case('builder-direct', lambda: local.build_local_connectivity(effective), target, RuntimeError)

    # A real unsupported captured contact operator, not an injected policy error.
    with tempfile.TemporaryDirectory(prefix='w010-premerge-exception-') as temporary:
        root = Path(temporary) / 'input'
        shutil.copytree(site.parent, root)
        owner_path = root / 'tech/physical.json'
        owner = json.loads(owner_path.read_text())
        owner['operators']['same_layer_contact/1'] = 'unsupported independent review policy'
        owner_path.write_text(json.dumps(owner, indent=2) + '\n')
        header_path = root / 'query/header.json'
        header = json.loads(header_path.read_text())
        for entry in header['closure']['entries']:
            entry['sha256'] = hashlib.sha256((root / entry['uri']).read_bytes()).hexdigest()
        header['closure']['entries'].sort(key=lambda entry: entry['uri'])
        header['closure']['sha256'] = hashlib.sha256(json.dumps(
            header['closure']['entries'], sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
        header_path.write_text(json.dumps(header, indent=2) + '\n')
        shutil.rmtree(root / 'query/normalized')
        for scope in ('direct', 'readback'):
            bad = make_effective(root / 'site_config.yaml', scope == 'readback', 'policy')
            error = local.build_local_connectivity(bad)
            check('real-policy-error-' + scope, error.status == 'error' and error.input is bad
                  and error.completed == bad.completed and error.issues[0].code == 'UnsupportedLocalContactOperator',
                  issue=error.issues[0].code, source=error.issues[0].source.uri, field=error.issues[0].source.field)
            check('error-wire-roundtrip-' + scope, codec.decode_record(codec.encode_record(error)) == error)
            for target in ('layauto_v2.state.layout_store._materialize',
                           'layauto_v2.normalization.contracts.request_decoder_input',
                           'layauto_v2.domain.evidence.hashlib') + (('layauto_v2.normalization.contracts.content_ref',) if scope == 'readback' else ()):
                for failure_type in (ValueError, TypeError, KeyboardInterrupt, SystemExit):
                    for suppression in (False, True):
                        original_require = local._require_input
                        passes = [0]
                        def mark(value):
                            passes[0] += 1
                            return original_require(value)
                        with patch.object(local, '_require_input', mark):
                            fault_case('real-policy-second-auth-' + scope,
                                       lambda: local.build_local_connectivity(bad), target, failure_type,
                                       suppression=suppression, gate=lambda: passes[0] == 2)
                        check('second-auth-reached-' + scope, passes[0] == 2)

    draft = direct.value
    # The new API accepts native lists by one immutable snapshot and rejects
    # subclasses; inherited APIs retain their list-subclass compatibility.
    for record, name in [(draft, f) for f in ('nodes', 'edges', 'audits', 'components')] + [
            (draft.edges[0], 'endpoints'), (draft.components[0], 'members'),
            (direct, 'issues'), (direct, 'completed')]:
        alias = list(getattr(record, name))
        copied = replace(record, **{name: alias})
        alias[:] = [None]
        check('native-snapshot-' + name, copied == record and type(getattr(copied, name)) is tuple)

    class Alternating(list):
        def __init__(self, first, second):
            super().__init__(first)
            self.first, self.second, self.calls = first, second, 0
        def __iter__(self):
            self.calls += 1
            return iter(self.first if self.calls == 1 else self.second)

    source = direct.completed[0]
    for valid_first in (True, False):
        aliases = Alternating(source.sources if valid_first else [None], [None] if valid_first else source.sources)
        try:
            copied = replace(source, sources=aliases)
        except ValueError:
            check('inherited-single-snapshot-invalid', not valid_first and aliases.calls == 1)
        else:
            check('inherited-single-snapshot-valid', valid_first and aliases.calls == 1 and copied == source)
    aliases = Alternating(draft.nodes, [None])
    explicitly_rejected('new-subclass-rejected-before-iteration', lambda: replace(draft, nodes=aliases))
    check('new-subclass-no-iteration', aliases.calls == 0)
    polluted = tamper(draft, nodes=list(draft.nodes))
    explicitly_rejected('recursive-alias-encode', lambda: codec.encode_record(polluted))
    explicitly_rejected('recursive-alias-captured-success', lambda: replace(direct, value=polluted))

    # Wrong shape controls require ValueError with an actual diagnostic; other
    # exceptions and accepted malformed records are failures, never successes.
    for record in (draft.ref, draft.binding, draft.nodes[0], draft.edges[0], draft.audits[0], draft.components[0], draft, direct):
        tree = mutable(decode(codec.encode_record(record)))
        for mutation in ('missing', 'extra'):
            changed = mutable(decode(codec.encode_record(record)))
            data = changed['record']['fields']
            if mutation == 'missing':
                del data[next(iter(data))]
            else:
                data['not_a_field'] = {'scalar': None}
            explicitly_rejected('wire-' + type(record).__name__ + '-' + mutation,
                                lambda changed=changed: codec.decode_record(canonical_bytes(changed)))
    for field in ('nodes', 'edges', 'audits', 'components'):
        changed = mutable(decode(codec.encode_record(draft)))
        changed['record']['fields'][field]['tuple'].pop()
        explicitly_rejected('nested-omission-' + field, lambda changed=changed: codec.decode_record(canonical_bytes(changed)))
        explicitly_rejected('constructor-omission-' + field, lambda field=field: replace(draft, **{field: getattr(draft, field)[:-1]}))
    changed = mutable(decode(wires['direct']))
    changed['record']['fields']['input']['effective_record'] = b'{}'
    explicitly_rejected('malformed-nested-effective-wire', lambda: codec.decode_record(canonical_bytes(changed)))
    report = dict(head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  python=sys.version, executable=sys.executable, cwd=str(ROOT), checks=checks,
                  elapsed_seconds=time.time() - started, failures=[row for row in checks if not row['passed']])
    report['status'] = 'failed' if report['failures'] else 'passed'
    OUTPUT.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(status=report['status'], checks=len(checks), failures=report['failures'])), flush=True)
    return bool(report['failures'])


if __name__ == '__main__':
    raise SystemExit(main())
