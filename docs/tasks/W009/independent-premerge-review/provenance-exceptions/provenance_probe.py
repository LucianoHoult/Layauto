"""Independent W009 capture, owner, pure-composition and malformed-wire probes.

No formal test helper or expected/spec/oracle is imported. Modified captures are
temporary copies; actual fixture and product files are never written.
"""
from __future__ import annotations

import builtins
from collections.abc import Mapping
from contextlib import ExitStack
from dataclasses import replace
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from unittest.mock import patch

from layauto_v2.domain.codec import canonical_bytes, decode
from layauto_v2.domain.evidence import SourceRef
from layauto_v2.domain.publication import InputsReady, RunRequest
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import (
    build_effective_geometry, build_geometry, from_parse_result,
    geometry_from_inputs_ready, geometry_from_parse_result, normalize,
)
from layauto_v2.normalization import codec as semantic_codec
from layauto_v2.normalization.effective_codec import decode_record, encode_record
from layauto_v2.normalization.geometry_codec import encode_record as encode_geometry
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository
from layauto_v2.state.regions import build_effective_draft


def thaw(value):
    if isinstance(value, Mapping):
        return {key: thaw(item) for key, item in value.items()}
    if type(value) is tuple:
        return [thaw(item) for item in value]
    return value


def main():
    checkout = Path.cwd()
    fixture = checkout / 'tests/fixtures/w003_m1'
    observations = []

    def passed(case, **detail):
        observations.append({'case': case, 'passed': True, **detail})

    def reject(case, action):
        try:
            action()
        except ValueError as error:
            passed(case, observed=type(error).__name__, message=str(error))
        else:
            raise AssertionError(case + ' was accepted')

    # Guard the actual reader too: product acquisition must not consult answers.
    original_open, original_io_open = builtins.open, io.open

    def guard(original):
        def checked(path, *args, **kwargs):
            if isinstance(path, (str, Path)):
                parts = Path(path).parts
                assert not any(p == 'expected' or p in ('oracle.json', 'spec.json') for p in parts), path
            return original(path, *args, **kwargs)
        return checked

    with patch('builtins.open', guard(original_open)), patch('io.open', guard(original_io_open)):
        parsed = read_inputs(fixture / 'site_config.yaml')
    assert parsed.status == 'success', parsed.issues
    semantic = normalize(from_parse_result(parsed))
    geometry = build_geometry(geometry_from_parse_result(parsed))
    semantic_before, geometry_before = semantic_codec.encode_record(semantic), encode_geometry(geometry)

    def no_io(*args, **kwargs):
        raise AssertionError('unexpected IO during captured-data composition')

    with ExitStack() as patches:
        patches.enter_context(patch('builtins.open', no_io))
        patches.enter_context(patch('io.open', no_io))
        for name in ('open', 'read_bytes', 'read_text', 'resolve'):
            patches.enter_context(patch.object(Path, name, no_io))
        result = build_effective_geometry(geometry)
    assert result.status == 'success', result.issues
    assert result.input is geometry and result.value.base is geometry.value
    assert result.completed == parsed.completed
    assert result.body_evidence is geometry.body_evidence
    assert semantic_codec.encode_record(semantic) == semantic_before
    assert encode_geometry(geometry) == geometry_before
    tech = next(row for row in parsed.completed if row.kind == 'tech')
    assert result.value.physical.sources == (tech.sources[3],)
    assert result.value.operators.drawn.sources == (tech.sources[1],)
    assert geometry.value.layout.formats.sources == (tech.sources[4],)
    assert result.value.operators.unit_ref == geometry.value.layout.units.ref
    passed('direct-W005-W008-W009-no-IO-prior-facts-and-owner-roles')

    repo = PublicationRepository()
    request = RunRequest('independent-premerge-capture', 'independent-premerge-lineage',
                         'create-only', str(fixture / 'site_config.yaml'))
    ready = prepare_inputs(repo, request)
    assert isinstance(ready, InputsReady), ready
    checkpoint = repo.load_checkpoint(ready.run_id)
    parse_audit = repo.read(ready.parse_ref)
    tool = repo.read(ready.tool_ref)
    audits = tuple(repo.read(ref) for ref in ready.evidence_refs)
    attempt_before = repo.load_attempt(ready.run_id)
    with ExitStack() as patches:
        patches.enter_context(patch('builtins.open', no_io))
        patches.enter_context(patch('io.open', no_io))
        patches.enter_context(patch.object(repo, 'read', no_io))
        for name in ('open', 'read_bytes', 'read_text', 'resolve'):
            patches.enter_context(patch.object(Path, name, no_io))
        bound_geometry = build_geometry(geometry_from_inputs_ready(ready, checkpoint, parse_audit, tool, audits))
        bound_result = build_effective_geometry(bound_geometry)
    assert bound_result.status == 'success' and bound_result.value == result.value
    assert repo.load_attempt(ready.run_id) == attempt_before
    assert attempt_before.phase == 'unsealed' and repo.read_terminal(ready.run_id) is None
    assert bound_result.input.input.readback.ready is ready
    passed('real-W006-readback-W008-W009-no-IO-unchanged-attempt')
    # A valid run's complete records may not be mixed with another run's ready.
    second = prepare_inputs(repo, replace(request, proposed_run_id='independent-second-run',
                                         lineage_id='independent-second-lineage', idempotency_key='second'))
    assert isinstance(second, InputsReady)
    reject('wrong-run-readback', lambda: geometry_from_inputs_ready(second, checkpoint, parse_audit, tool, audits))

    # Neutral state evidence may be internally consistent but is not capture
    # authentication. A foreign owner must fail at the outer successful result.
    physical = result.value.physical
    foreign = replace(physical, sources=(SourceRef('foreign/physical.json', physical.sources[0].sha256),))
    neutral = build_effective_draft(result.value.base, foreign)
    reject('foreign-physical-owner-on-success', lambda: replace(result, value=neutral))

    # Alter grouped downstream value+completed evidence, leaving captures intact.
    forged_value = thaw(parsed.value)
    forged_value['tech']['physical']['operators']['terminal_split/1'] = 'union forbidden by real captured owner'
    forged_tech = {'bundle': forged_value['tech_bundle'], 'owners': forged_value['tech']}
    completed = tuple(replace(row, payload=forged_tech) if row.kind == 'tech' else row
                      for row in parsed.completed)
    forged = replace(parsed, value=forged_value, completed=completed)
    reject('grouped-payload-forgery-direct', lambda: geometry_from_parse_result(forged))
    semantic_forged = from_parse_result(forged)
    tree = thaw(decode(encode_record(result)))
    nested = thaw(decode(tree['record']['fields']['input']['geometry_record']))
    nested['record']['fields']['input']['fields']['semantic_input'] = {
        'semantic_input': semantic_codec.encode_record(semantic_forged)}
    tree['record']['fields']['input']['geometry_record'] = canonical_bytes(nested)
    reject('grouped-payload-forgery-nested-result', lambda: decode_record(canonical_bytes(tree)))

    # Every declared consumed semantic is checked against real modified bytes.
    # Rebind only actual-byte header hashes in temporary reader inputs.
    with tempfile.TemporaryDirectory(prefix='w009-provenance-', dir='/workspace/work') as temporary:
        for kind, name, key, wrong in (
            ('physical', 'fin_count_profile', 'effective_active_operator', 'wrong_active/1'),
            ('physical', 'fin_count_profile', 'recognized_channel_operator', 'wrong_channel/1'),
            ('physical', 'device_extraction_contract', 'sd_policy', 'top is source'),
            ('physical', 'device_extraction_contract', 'gate_operator', 'OD source drain are a conductor'),
            ('physical', 'operators', 'rectangle_set_difference/1', 'bbox-only'),
            ('physical', 'operators', 'terminal_split/1', 'discard one residual'),
            ('drawn', 'OD', 'role', 'gate'), ('drawn', 'POLY', 'role', 'marker'),
            ('drawn', 'LI', 'role', 'marker'), ('drawn', 'CUT', 'role', 'marker'),
            ('drawn', 'CUT', 'cut_target', 'OD'),
            ('drawn', 'CUT', 'effective_geometry_operator', 'terminal_split/1'),
        ):
            case = f'captured-{kind}-{name}-{key}'
            root = Path(temporary) / str(len(observations))
            shutil.copytree(fixture, root)
            shutil.rmtree(root / 'query/normalized')
            path = root / 'tech' / (kind + '.json')
            document = json.loads(path.read_text())
            if kind == 'physical':
                document[name][key] = wrong
            else:
                row = next(row for row in document['layers'] if row['name'] == name)
                row[key] = wrong
                if name == 'CUT' and key == 'role':
                    del row['cut_target'], row['effective_geometry_operator']
            path.write_text(json.dumps(document, indent=2) + '\n')
            header_path = root / 'query/header.json'
            header = json.loads(header_path.read_text())
            for row in header['closure']['entries']:
                row['sha256'] = hashlib.sha256((root / row['uri']).read_bytes()).hexdigest()
            header['closure']['sha256'] = hashlib.sha256(json.dumps(
                header['closure']['entries'], sort_keys=True,
                separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
            header_path.write_text(json.dumps(header, indent=2) + '\n')
            changed_parse = read_inputs(root / 'site_config.yaml')
            if changed_parse.status == 'error':
                # Some consumed fields are already enum-locked by W005. Keep
                # that earlier located boundary; do not mislabel it W009.
                issue, = changed_parse.issues
                assert issue.source.uri == 'tech/' + kind + '.json', (case, issue)
                assert issue.source.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
                passed(case, boundary='W005', code=issue.code, field=issue.source.field)
                continue
            changed_geometry = build_geometry(geometry_from_parse_result(changed_parse))
            rejected = build_effective_geometry(changed_geometry)
            assert rejected.status == 'error' and rejected.value is None, case
            issue, = rejected.issues
            assert issue.code == 'UnsupportedRegionOperator', (case, issue)
            assert issue.source.uri == 'tech/' + kind + '.json', (case, issue)
            assert issue.source.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
            assert rejected.completed == changed_parse.completed
            passed(case, boundary='W009', code=issue.code, field=issue.source.field)

    for enclosing, value in (('draft', result.value), ('result', result)):
        for change in ('unknown-field', 'missing-field', 'scalar-collection', 'bad-nested-geometry'):
            tree = thaw(decode(encode_record(value)))
            fields = tree['record']['fields']
            if change == 'unknown-field':
                fields['invented'] = {'scalar': 3}
            elif change == 'missing-field':
                del fields['schema_version']
            elif change == 'scalar-collection':
                fields['schema_version'] = {'scalar': ['foreign']}
            elif enclosing == 'draft':
                fields['base']['geometry_record'] = b'invalid canonical wire'
            else:
                fields['input']['geometry_record'] = b'invalid canonical wire'
            reject(f'malformed-{enclosing}-{change}', lambda tree=tree: decode_record(canonical_bytes(tree)))

    paths = ('layauto_v2/domain/regions.py', 'layauto_v2/state/regions.py',
             'layauto_v2/normalization/effective.py', 'layauto_v2/normalization/effective_codec.py',
             'layauto_v2/normalization/geometry_input.py', 'layauto_v2/normalization/geometry_codec.py')
    print(json.dumps({
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'python': sys.version, 'cwd': str(checkout), 'case_count': len(observations),
        'sources': {p: hashlib.sha256((checkout / p).read_bytes()).hexdigest() for p in paths},
        'observations': observations,
    }, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
