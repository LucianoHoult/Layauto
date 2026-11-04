"""Installed W005-W009 composition; run with -I -B outside the checkout.

Reads only declared W005 captures. No tests, answers or legacy modules imported.
"""
from __future__ import annotations

import builtins
from contextlib import ExitStack
from dataclasses import replace
from fractions import Fraction
import hashlib
import importlib.metadata
import io
import json
from pathlib import Path
import sys
import sysconfig
from tempfile import TemporaryDirectory
from unittest.mock import patch

import layauto_v2
from layauto_v2.domain.publication import InputsReady, RunRequest
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import (
    build_geometry, build_effective_geometry, from_inputs_ready, from_parse_result,
    geometry_from_normalization_input, normalize,
)
from layauto_v2.normalization.effective_codec import decode_record, encode_record, record_digest
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository
from layauto_v2.state import occupancy


def sha(data):
    return hashlib.sha256(data).hexdigest()


def forbidden(*args, **kwargs):
    raise AssertionError('pure composition attempted file IO or repository access')


def inside(rect, x, y):
    a, b, c, d = rect.bounds
    return a <= x < c and b <= y < d


def check_geometry(result):
    assert result.status == 'success' and not result.issues
    draft = result.value
    assert draft is not None
    base = result.input.value
    assert draft.base is base or draft.base == base
    assert len(base.layout.records) == 40
    assert len(base.fragments) == 41
    assert len(result.body_evidence.payload['shapes']) == 6
    assert result.body_evidence == result.input.body_evidence
    assert len(draft.records) == sum(r.layer in ('LI', 'OD') for r in base.layout.records)
    assert {r.record_id for r in draft.records} == {r.id for r in base.layout.records if r.layer in ('LI', 'OD')}
    records = {r.id: r for r in base.layout.records}
    cuts = [r for r in base.layout.records if r.layer == 'CUT']
    checked_points = 0
    counts = {'effective': 0, 'channel': 0, 'S': 0, 'D': 0}
    for transformed in draft.records:
        drawn = records[transformed.record_id]
        regions = transformed.regions
        for region in regions:
            counts[region.role] += 1
            assert region.owner_id == drawn.id
            assert region.unit_ref == base.layout.units.ref
            assert region.operator_ref == draft.operators.ref
            assert all(piece.region_ref == region.ref for piece in region.pieces)
        pieces = [rect for region in regions for rect in region.rectangles]
        # Independent all-boundary partition: exact midpoint membership checks
        # establish subset, multiplicity and no omitted positive-area atom.
        relevant = [drawn.rect, *pieces]
        if drawn.layer == 'LI':
            relevant += [cut.rect for cut in cuts]
        xs = sorted({v for r in relevant for v in (r.x0, r.x1)})
        ys = sorted({v for r in relevant for v in (r.y0, r.y1)})
        for left, right in zip(xs, xs[1:]):
            for low, high in zip(ys, ys[1:]):
                x, y = Fraction(left + right, 2), Fraction(low + high, 2)
                expected = inside(drawn.rect, x, y)
                if drawn.layer == 'LI':
                    expected = expected and not any(inside(cut.rect, x, y) for cut in cuts)
                assert sum(inside(r, x, y) for r in pieces) == int(expected)
                checked_points += 1
        if drawn.layer == 'OD':
            assert [r.role for r in regions] == ['channel', 'S', 'D']
            channel, source, drain = [r.rectangles[0] for r in regions]
            assert len(regions) == 3 and all(len(r.rectangles) == 1 for r in regions)
            assert source.x0 == drawn.rect.x0 and source.x1 == channel.x0
            assert channel.x1 == drain.x0 and drain.x1 == drawn.rect.x1
            assert all((r.y0, r.y1) == (drawn.rect.y0, drawn.rect.y1) for r in (source, channel, drain))
    assert (counts['channel'], counts['S'], counts['D']) == (2, 2, 2)
    for value in (result, draft):
        assert all(not hasattr(value, name) for name in (
            'physical_edges', 'components', 'net_id', 'device_id', 'baseline',
            'no_change', 'terminal', 'body_complete', 'final_snapshot_id'))
    return {'counts': counts, 'independent_exact_atoms': checked_points}


def check_wire(result):
    wire = encode_record(result)
    restored = decode_record(wire)
    assert restored == result
    assert encode_record(restored) == wire
    assert record_digest(result) == sha(wire)
    try:
        replace(result, value=None) if result.status == 'success' else replace(result, status='success')
    except ValueError:
        pass
    else:
        raise AssertionError('forged effective success accepted')
    return sha(wire)


def check_nested_exception_identity(direct, readback):
    """Installed packages must retain an internal base error and its history."""
    rows = []
    wires = [(entry, name, encode_record(value))
             for entry, result in (('direct', direct), ('readback', readback))
             for name, value in (('draft', result.value), ('result', result))]
    for entry, name, wire in wires:
        cause = RuntimeError('prior installed-smoke cause')
        context = LookupError('prior installed-smoke context')
        failure = TypeError('installed internal base reconstruction failure')
        failure.__cause__ = cause
        failure.__context__ = context
        failure.__suppress_context__ = True

        def broken(*args, **kwargs):
            raise failure

        with patch.object(occupancy, '_fragments', broken):
            try:
                decode_record(wire)
            except BaseException as observed:
                assert observed is failure
                assert observed.__cause__ is cause
                assert observed.__context__ is context
                assert observed.__suppress_context__ is True
            else:
                raise AssertionError('internal installed reconstruction failure disappeared')
        rows.append({'entry': entry, 'enclosing': name, 'same_object': True,
                     'cause_preserved': True, 'context_preserved': True,
                     'suppress_context_preserved': True, 'wire_sha256': sha(wire)})
    return rows


def unsupported_operator(parsed):
    """Reauthor only temporary captured input and rebind declared closure hashes."""
    with TemporaryDirectory(prefix='w009-installed-error-', dir=str(Path.cwd())) as directory:
        root = Path(directory)
        for source in parsed.sources:
            relative = Path(source.uri)
            if relative.is_absolute():
                continue
            assert '..' not in relative.parts
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.data)
        site_record = next(record for record in parsed.completed if record.kind == 'config')
        site_path = root / site_record.sources[0].uri
        site = json.loads(site_path.read_text())
        bundle = json.loads((root / site['tech_ref']).read_text())
        physical_path = root / bundle['owners']['physical']['path']
        physical = json.loads(physical_path.read_text())
        physical['device_extraction_contract']['sd_policy'] = 'unsupported installed smoke orientation'
        physical_path.write_text(json.dumps(physical, indent=2) + '\n')
        header_path = root / site['inputs']['query_header']
        header = json.loads(header_path.read_text())
        for entry in header['closure']['entries']:
            entry['sha256'] = sha((root / entry['uri']).read_bytes())
        header['closure']['entries'].sort(key=lambda row: row['uri'])
        header['closure']['sha256'] = sha(json.dumps(header['closure']['entries'], sort_keys=True,
                                                   separators=(',', ':'), ensure_ascii=False).encode())
        header_path.write_text(json.dumps(header, indent=2) + '\n')
        changed = read_inputs(site_path)
        assert changed.status == 'success', changed.issues
        with ExitStack() as stack:
            for name in ('open', 'read_bytes', 'read_text', 'resolve'):
                stack.enter_context(patch.object(Path, name, forbidden))
            stack.enter_context(patch.object(builtins, 'open', forbidden))
            stack.enter_context(patch.object(io, 'open', forbidden))
            geometry = build_geometry(geometry_from_normalization_input(from_parse_result(changed)))
            assert geometry.status == 'success', geometry.issues
            result = build_effective_geometry(geometry)
            assert result.status == 'error' and result.value is None
            assert len(result.issues) == 1 and result.issues[0].code == 'UnsupportedRegionOperator'
            assert result.issues[0].source.uri == bundle['owners']['physical']['path']
            assert result.issues[0].source.field == '/device_extraction_contract/sd_policy'
            assert result.completed == changed.completed
            wire = check_wire(result)
        return {'issue': result.issues[0].code, 'field': result.issues[0].source.field, 'wire_sha256': wire}


def main():
    assert len(sys.argv) == 3
    assert sys.flags.isolated == 1 and sys.dont_write_bytecode
    fixture = Path(sys.argv[1])
    assert fixture.is_absolute() and fixture.is_dir()
    package = Path(layauto_v2.__file__).resolve()
    roots = {Path(sysconfig.get_path(name)).resolve() for name in ('purelib', 'platlib')}
    assert any(package.is_relative_to(root) for root in roots), package
    assert 'site-packages' in package.parts
    manifest = {str(p.relative_to(package.parent)): sha(p.read_bytes())
                for p in sorted(package.parent.rglob('*'))
                if p.is_file() and (p.suffix == '.py' or p.name == 'py.typed')}
    source_manifest_path = Path(sys.argv[2]).resolve()
    source_manifest_bytes = source_manifest_path.read_bytes()
    expected = json.loads(source_manifest_bytes)
    source_root = Path(expected['checkout_root']).resolve()
    assert not Path.cwd().resolve().is_relative_to(source_root)
    assert not package.is_relative_to(source_root)
    assert str(source_root) not in sys.path
    assert manifest == expected['runtime_files']
    print(json.dumps({'environment': {'python': sys.version, 'executable': sys.executable,
          'installed_package': str(package), 'fixture': str(fixture),
          'cwd': str(Path.cwd()), 'sys_path': sys.path,
          'prefix': sys.prefix, 'base_prefix': sys.base_prefix,
          'source_manifest_sha256': sha(source_manifest_bytes),
          'source_git_head': expected['git_head'], 'source_base_sha': expected['base_sha'],
          'source_runtime_count': len(expected['runtime_files']),
          'distributions': {d.metadata['Name']: d.version for d in importlib.metadata.distributions()},
          'isolated': sys.flags.isolated, 'dont_write_bytecode': sys.dont_write_bytecode,
          'package_manifest': manifest}}, indent=2), flush=True)
    parsed = read_inputs(fixture / 'site_config.yaml')
    assert parsed.status == 'success', parsed.issues
    repository = PublicationRepository()
    ready = prepare_inputs(repository, RunRequest(
        proposed_run_id='installed-w009-smoke', lineage_id='installed-w009-lineage',
        idempotency_key='installed-w009-create', site_path=str(fixture / 'site_config.yaml')))
    assert isinstance(ready, InputsReady), ready
    checkpoint = repository.load_checkpoint(ready.run_id)
    parse_audit = repository.read(ready.parse_ref)
    tool_run = repository.read(ready.tool_ref)
    evidence = tuple(repository.read(ref) for ref in ready.evidence_refs)
    attempt = repository.load_attempt(ready.run_id)
    with ExitStack() as stack:
        for method in ('open', 'read_bytes', 'read_text', 'resolve'):
            stack.enter_context(patch.object(Path, method, forbidden))
        stack.enter_context(patch.object(builtins, 'open', forbidden))
        stack.enter_context(patch.object(io, 'open', forbidden))
        stack.enter_context(patch.object(repository, 'read', forbidden))
        direct_input = from_parse_result(parsed)
        semantic = normalize(direct_input)
        geometry = build_geometry(geometry_from_normalization_input(direct_input))
        effective = build_effective_geometry(geometry)
        run_input = from_inputs_ready(ready, checkpoint, parse_audit, tool_run, evidence)
        run_semantic = normalize(run_input)
        run_geometry = build_geometry(geometry_from_normalization_input(run_input))
        run_effective = build_effective_geometry(run_geometry)
        assert semantic.status == run_semantic.status == 'success'
        assert semantic.value == run_semantic.value
        assert geometry.value == run_geometry.value
        assert effective.value == run_effective.value
        assert effective.input is geometry and run_effective.input is run_geometry
        assert normalize(direct_input) == semantic
        geometry_checks = check_geometry(effective)
        assert check_geometry(run_effective) == geometry_checks
        direct_wire, readback_wire = check_wire(effective), check_wire(run_effective)
        nested_exceptions = check_nested_exception_identity(effective, run_effective)
    assert repository.load_attempt(ready.run_id) == attempt
    assert repository.load_checkpoint(ready.run_id) == checkpoint
    assert repository.read_terminal(ready.run_id) is None
    assert attempt.phase == 'unsealed'
    negative = unsupported_operator(parsed)
    print(json.dumps({'checks': {'status': 'passed', **geometry_checks,
          'captured_w005_w006_w007_w008_w009_without_io': True,
          'base_records': 40, 'base_fragments': 41, 'body_shapes': 6,
          'attempt_phase': attempt.phase, 'terminal': None,
          'direct_wire_sha256': direct_wire, 'readback_wire_sha256': readback_wire,
          'nested_base_exception_identity': nested_exceptions,
          'captured_sources': [{'uri': source.uri, 'sha256': sha(source.data)} for source in parsed.sources],
          'unsupported_operator_error': negative}}, indent=2), flush=True)


if __name__ == '__main__':
    main()
