"""Independent W010 boundary review probes; no production/test helper imports."""
from __future__ import annotations

import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

from layauto_v2.domain.codec import canonical_bytes, decode, FrozenMap
from layauto_v2.domain.publication import RunRequest, InputsReady
from layauto_v2.domain import publication_codec
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import (
    build_effective_geometry, build_geometry, geometry_from_parse_result,
    build_local_connectivity,
)
from layauto_v2.normalization.geometry_input import geometry_from_inputs_ready
from layauto_v2.normalization import codec as semantic_codec
from layauto_v2.normalization import effective_codec, geometry_codec, local_connectivity_codec
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).with_name('boundary-probe-result.json')


def mutable(value):
    if type(value) is FrozenMap:
        return {k: mutable(v) for k, v in value.items()}
    if type(value) is tuple:
        return [mutable(v) for v in value]
    return value


def compose(geometry):
    return build_local_connectivity(build_effective_geometry(build_geometry(geometry)))


def main():
    started = time.time()
    result = {'head': '0f5029df935bc0acd106aad1bc2be81304d4f442',
              'python': sys.version, 'executable': sys.executable,
              'failures': [], 'checks': [], 'source_sha256': {}}
    for name in ('domain/local_connectivity.py', 'normalization/local_connectivity.py',
                 'normalization/local_connectivity_codec.py', 'state/local_connectivity.py'):
        result['source_sha256'][name] = hashlib.sha256((ROOT / 'layauto_v2' / name).read_bytes()).hexdigest()
    site = ROOT / 'tests/fixtures/w003_m1/site_config.yaml'
    parsed = read_inputs(site)
    direct_geometry = geometry_from_parse_result(parsed)
    direct = compose(direct_geometry)
    repository = PublicationRepository()
    ready = prepare_inputs(repository, RunRequest(
        proposed_run_id='w010-independent-boundary', lineage_id='w010-independent-boundary',
        idempotency_key='create-boundary', site_path=str(site)))
    assert isinstance(ready, InputsReady)
    before_attempt = ready.attempt
    readback_geometry = geometry_from_inputs_ready(
        ready, repository.load_checkpoint(ready.run_id), repository.read(ready.parse_ref),
        repository.read(ready.tool_ref), tuple(repository.read(ref) for ref in ready.evidence_refs))
    readback = compose(readback_geometry)
    assert direct.status == readback.status == 'success' and direct.value == readback.value
    assert ready.attempt == before_attempt
    # All inputs are captured before the no-I/O section. These entrypoints are
    # independent of the application's tests and are the public supported APIs.
    def forbidden(*args, **kwargs):
        raise AssertionError('unexpected file I/O during captured composition')
    with patch('builtins.open', forbidden), patch.object(Path, 'read_bytes', forbidden), patch.object(Path, 'read_text', forbidden):
        assert compose(direct_geometry) == direct
        assert compose(readback_geometry) == readback
    result['checks'].append('real direct/readback equality; captured composition no file I/O; attempt unchanged')
    draft = direct.value
    records = (draft.ref, draft.binding, draft.nodes[0], draft.edges[0], draft.audits[0],
               draft.components[0], draft, direct)
    codec = local_connectivity_codec
    wires = {'direct': codec.encode_record(direct), 'readback': codec.encode_record(readback)}
    malformed = 0
    for record in records:
        wire = codec.encode_record(record)
        assert codec.decode_record(wire) == record
        tree = mutable(decode(wire))
        fields = tree['record']['fields']
        for field, original in fields.items():
            for replacement in ({'scalar': None}, {'scalar': True}, {'tuple': []}, {'map': {}}):
                if replacement == original:
                    continue
                changed = copy.deepcopy(tree)
                changed['record']['fields'][field] = replacement
                try:
                    rebuilt = codec.decode_record(canonical_bytes(changed))
                except ValueError:
                    malformed += 1
                except BaseException as exc:
                    result['failures'].append({'kind': 'malformed-error', 'record': type(record).__name__,
                                               'field': field, 'replacement': str(replacement),
                                               'exception': type(exc).__name__, 'message': str(exc)})
                else:
                    # An empty tuple is legitimate for success issues and None
                    # can be legitimate on discriminated optional fields.
                    if getattr(record, field) != getattr(rebuilt, field):
                        result['failures'].append({'kind': 'malformed-accepted', 'record': type(record).__name__,
                                                   'field': field, 'replacement': str(replacement)})
    result['malformed_fields_rejected'] = malformed
    targets = (
        (codec, name, scope) for scope in wires for name in codec._SPEC
    )
    targets = list(targets) + [
        (registry, name, scope)
        for scope in wires
        for registry, names in (
            (effective_codec, ('EffectiveGeometryResult', 'EffectiveDraft', 'ExactRegion', 'OperatorBinding')),
            (geometry_codec, ('GeometryResult', 'GeometryInput', 'BaseOccupancy', 'BasePartition', 'LayoutDraft', 'DrawnRecord', 'UnitBinding')),
            (semantic_codec, ('NormalizationInput',)),
            (publication_codec, ('SourceRef', 'SourceFile', 'EvidenceRecord', 'ParseResult')),
        )
        for name in names
    ] + [(semantic_codec, 'ReadbackBinding', 'readback'),
         (publication_codec, 'InputCheckpoint', 'readback'),
         (publication_codec, 'InputsReady', 'readback'),
         (publication_codec, 'ParseAudit', 'readback'),
         (publication_codec, 'ToolRunResult', 'readback'),
         (publication_codec, 'EvidenceAudit', 'readback'),
         (publication_codec, 'RunAttempt', 'readback')]
    exceptions = []
    for index, (registry, name, scope) in enumerate(targets):
        for failure_class in (TypeError, KeyError, KeyboardInterrupt, SystemExit):
            failure = failure_class('independent injected reconstruction fault')
            cause, context = RuntimeError('existing cause'), LookupError('existing context')
            failure.__cause__, failure.__context__ = cause, context
            suppressed = bool(index % 2)
            failure.__suppress_context__ = suppressed
            def broken(**kwargs):
                raise failure
            entry = registry._SPEC[name]
            registry._SPEC[name] = (broken, entry[1])
            try:
                try:
                    codec.decode_record(wires[scope])
                except BaseException as exc:
                    passed = (exc is failure and exc.__cause__ is cause and exc.__context__ is context
                              and exc.__suppress_context__ is suppressed)
                    outcome = {'scope': scope, 'registry': registry.__name__, 'record': name,
                               'fault': failure_class.__name__, 'same_object_and_history': passed}
                    exceptions.append(outcome)
                    if not passed:
                        result['failures'].append(dict(outcome, received=type(exc).__name__, message=str(exc)))
                else:
                    result['failures'].append({'kind': 'fault-target-unreached', 'record': name, 'scope': scope})
            finally:
                registry._SPEC[name] = entry
    result['constructor_faults'] = exceptions
    result['constructor_faults_count'] = len(exceptions)
    # Native collection inputs must be copied once; retained records are exact
    # DTOs and all new textual fields reject mutable subclasses before encoding.
    for field in ('nodes', 'edges', 'audits', 'components'):
        alias = list(getattr(draft, field))
        copied = replace(draft, **{field: alias})
        alias.clear()
        assert copied == draft
    class MutableText(str):
        pass
    aliases = 0
    for record, field in ((draft.ref, 'kind'), (draft.binding, 'scope'), (draft.nodes[0], 'layer'),
                          (draft.edges[0], 'kind'), (draft.audits[0], 'status'),
                          (draft.components[0], 'schema_version'), (draft, 'schema_version'), (direct, 'status')):
        alias = MutableText(getattr(record, field))
        alias.items = []
        try:
            replace(record, **{field: alias})
        except ValueError:
            aliases += 1
        else:
            result['failures'].append({'kind': 'mutable-text-retained', 'record': type(record).__name__, 'field': field})
    result['alias_cases'] = {'copied_collections': 4, 'mutable_text_rejected': aliases}
    result['elapsed_seconds'] = time.time() - started
    result['status'] = 'passed' if not result['failures'] else 'failed'
    OUT.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('constructor_faults', 'source_sha256')}, indent=2))
    return bool(result['failures'])


if __name__ == '__main__':
    raise SystemExit(main())
