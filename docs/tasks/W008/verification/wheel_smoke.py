"""W008 installed-package smoke, run outside the source checkout.

Usage: /clean/venv/bin/python -I -B /path/to/wheel_smoke.py /absolute/fixture/path
Only input captures are read; no source/test helper or expected answer is imported.
"""
from __future__ import annotations

import builtins
from contextlib import ExitStack
from dataclasses import replace
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys
import sysconfig
from tempfile import TemporaryDirectory
from unittest.mock import patch

import layauto_v2
from layauto_v2.domain.codec import freeze_map
from layauto_v2.domain.evidence import SourceFile
from layauto_v2.domain.publication import InputsReady, RunRequest
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import (
    build_geometry, from_inputs_ready, from_parse_result,
    GeometryInputError, geometry_from_normalization_input, geometry_from_parse_result, normalize,
)
from layauto_v2.normalization.geometry_codec import decode_record, encode_record, record_digest
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository


def sha(data):
    return hashlib.sha256(data).hexdigest()


def forbidden(*args, **kwargs):
    raise AssertionError('component construction attempted file IO or repository access')


def check_coverage(result):
    assert result.status == 'success' and not result.issues
    occupancy, layout = result.value, result.layout
    assert occupancy is not None and layout is not None
    assert len(layout.records) == 40
    assert len(occupancy.fragments) == 41
    assert len({record.id for record in layout.records}) == 40
    assert len(result.body_evidence.payload['shapes']) == 6
    assert result.body_evidence.payload['read_only'] is True
    assert result.body_evidence.payload['exported'] is False
    assert len(result.body_evidence.sources) == 2
    assert result.body_evidence.sources[1] == layout.gds.sources[0]
    units = layout.units
    assert units.nominal_tick_m == Fraction(1, 1_000_000_000)
    assert units.canonical_tick_nm == 1
    for name, nominal in (('metres_per_tick', Fraction(1, 1_000_000_000)),
                          ('user_units_per_tick', Fraction(1, 1000))):
        encoding = units.encoded[name]
        assert type(encoding['raw']) is bytes and len(encoding['raw']) == 8
        assert type(encoding['exact']) is Fraction
        assert encoding['nominal'] == nominal
        assert encoding['encoding_delta'] == encoding['exact'] - nominal
        assert abs(encoding['encoding_delta']) <= encoding['ulp'] / 2
    records = {record.id: record for record in layout.records}
    for fragment in occupancy.fragments:
        assert fragment.record_id in records
        assert fragment.cell.layer == records[fragment.record_id].layer
        assert fragment.unit_ref == units.ref
        assert fragment.cell.partition_ref == result.partition.ref
    projected, unprojected = 0, 0
    for record in layout.records:
        assert record.source.uri == layout.gds.sources[0].uri
        assert record.source.sha256 == layout.gds.sources[0].sha256
        assert all(type(coordinate) is int for point in record.raw_xy for coordinate in point)
        xs, ys = [p[0] for p in record.raw_xy], [p[1] for p in record.raw_xy]
        assert record.rect.bounds == (min(xs), min(ys), max(xs), max(ys))
        for tick in record.rect.bounds:
            assert units.source_to_nm(tick) == Fraction(tick)
            assert units.source_to_canonical(tick) == tick
            assert units.canonical_to_source(tick) == tick
        fragments = [f for f in occupancy.fragments if f.record_id == record.id]
        if record.layer in ('BOUNDARY', 'MARKER'):
            assert not fragments
            assert not layout.policy(record.layer).projected
            unprojected += 1
            continue
        projected += 1
        assert fragments and layout.policy(record.layer).projected
        x0, y0, x1, y1 = record.rect.bounds
        area = 0
        for i, fragment in enumerate(fragments):
            a, b, c, d = fragment.rect.bounds
            assert x0 <= a < c <= x1 and y0 <= b < d <= y1
            area += (c - a) * (d - b)
            # Independent interval arithmetic, without the product intersection
            # or projection routines. Interior-disjoint subsets with equal area
            # exactly cover this half-open rectangle.
            for other in fragments[:i]:
                e, f, g, h = other.rect.bounds
                assert max(a, e) >= min(c, g) or max(b, f) >= min(d, h)
        assert area == (x1 - x0) * (y1 - y0)
    assert (projected, unprojected) == (38, 2)
    for value in (result, layout, occupancy, result.partition):
        for name in ('coordinate_ref', 'baseline', 'no_change', 'terminal', 'physical_edges',
                     'body_complete', 'final_snapshot_id', 'deployment_disposition'):
            assert not hasattr(value, name)


def assert_wire(result):
    data = encode_record(result)
    restored = decode_record(data)
    assert restored == result
    assert encode_record(restored) == data
    assert record_digest(result) == sha(data)
    return sha(data)


def unsupported_comparator(parsed):
    """Reauthor a temporary input, with exact source/header closure rebinding."""
    with TemporaryDirectory(prefix='layauto-w008-installed-smoke-') as directory:
        root = Path(directory)
        for source in parsed.sources:
            relative = Path(source.uri)
            # Optional normalized caches use absolute acquisition URIs. They
            # are omitted so the copied input is built from raw captures alone.
            if relative.is_absolute():
                continue
            assert '..' not in relative.parts
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(source.data)
        site_record = next(record for record in parsed.completed if record.kind == 'config')
        site_path = root / site_record.sources[0].uri
        site = json.loads(site_path.read_text(encoding='utf-8'))
        bundle = json.loads((root / site['tech_ref']).read_text(encoding='utf-8'))
        formats_path = root / bundle['owners']['formats']['path']
        formats = json.loads(formats_path.read_text(encoding='utf-8'))
        formats['geometry_capability']['comparator'] = 'unsupported-installed-smoke/1'
        formats_path.write_text(json.dumps(formats, indent=2) + '\n', encoding='utf-8')
        header_path = root / site['inputs']['query_header']
        header = json.loads(header_path.read_text(encoding='utf-8'))
        for entry in header['closure']['entries']:
            entry['sha256'] = sha((root / entry['uri']).read_bytes())
        header['closure']['entries'].sort(key=lambda entry: entry['uri'])
        header['closure']['sha256'] = sha(json.dumps(header['closure']['entries'], sort_keys=True,
                                                    separators=(',', ':'), ensure_ascii=False).encode())
        header_path.write_text(json.dumps(header, indent=2) + '\n', encoding='utf-8')
        changed = read_inputs(site_path)
        assert changed.status == 'success', changed.issues
        result = build_geometry(geometry_from_parse_result(changed))
        assert result.status == 'error' and result.value is None
        assert [issue.code for issue in result.issues] == ['UnsupportedGeometryComparator']
        assert result.issues[0].source.uri == bundle['owners']['formats']['path']
        assert result.issues[0].source.field == '/geometry_capability/comparator'
        assert result.completed == changed.completed
        return {'issue': result.issues[0].code, 'wire_sha256': assert_wire(result)}


def false_first_acquisition_alias(parsed):
    """CR-01: equal bytes cannot hide an impossible first GDS acquisition URI."""
    original = next(r for r in parsed.completed if r.kind == 'gds').sources[0]
    capture = next(s for s in parsed.sources if s.uri == original.uri)
    sibling = SourceFile('forged-first-acquisition.gds', capture.data)
    gds = freeze_map({**parsed.value['gds'], 'source': {'uri': sibling.uri, 'sha256': sibling.sha256}})
    completed = tuple(replace(r, payload=gds, sources=(sibling.ref(),)) if r.kind == 'gds'
                      else replace(r, sources=(r.sources[0], sibling.ref())) if r.kind == 'body'
                      else r for r in parsed.completed)
    forged = replace(parsed, value=freeze_map({**parsed.value, 'gds': gds}), completed=completed,
                     sources=tuple(s for s in parsed.sources if s.uri != original.uri) + (sibling,))
    try:
        geometry_from_parse_result(forged)
    except GeometryInputError as error:
        assert error.issue.source.field == '/inputs/gds'
        assert error.completed == forged.completed
        return error.issue.code
    raise AssertionError('an impossible first-acquisition alias was accepted')


def main():
    assert len(sys.argv) == 2, 'supply the absolute W003/W004 fixture directory'
    assert sys.flags.isolated == 1 and sys.dont_write_bytecode, 'invoke with -I -B'
    fixture = Path(sys.argv[1])
    assert fixture.is_absolute() and fixture.is_dir()
    package_file = Path(layauto_v2.__file__).resolve()
    install_roots = {Path(sysconfig.get_path(key)).resolve() for key in ('purelib', 'platlib')}
    assert any(package_file.is_relative_to(root) for root in install_roots), package_file
    assert 'site-packages' in package_file.parts, package_file
    package_root = package_file.parent
    package_manifest = {str(path.relative_to(package_root)): sha(path.read_bytes())
                        for path in sorted(package_root.rglob('*'))
                        if path.is_file() and (path.suffix == '.py' or path.name == 'py.typed')}
    startup = {'python': sys.version, 'executable': sys.executable, 'prefix': sys.prefix,
               'isolated': sys.flags.isolated, 'dont_write_bytecode': sys.dont_write_bytecode,
               'installed_package': str(package_file), 'installed_package_sha256': sha(package_file.read_bytes()),
               'fixture': str(fixture), 'package_manifest': package_manifest}
    print(json.dumps({'environment': startup}, indent=2), flush=True)
    parsed = read_inputs(fixture / 'site_config.yaml')
    assert parsed.status == 'success', parsed.issues
    repository = PublicationRepository()
    request = RunRequest(proposed_run_id='installed-w008-smoke', lineage_id='installed-smoke-lineage',
                         idempotency_key='installed-smoke-create', site_path=str(fixture / 'site_config.yaml'))
    ready = prepare_inputs(repository, request)
    assert isinstance(ready, InputsReady), ready
    checkpoint = repository.load_checkpoint(ready.run_id)
    parse_audit = repository.read(ready.parse_ref)
    tool_run = repository.read(ready.tool_ref)
    evidence = tuple(repository.read(ref) for ref in ready.evidence_refs)
    attempt = repository.load_attempt(ready.run_id)
    with ExitStack() as stack:
        for name in ('open', 'read_bytes', 'read_text', 'resolve'):
            stack.enter_context(patch.object(Path, name, forbidden))
        stack.enter_context(patch.object(builtins, 'open', forbidden))
        stack.enter_context(patch.object(repository, 'read', forbidden))
        semantic_input = from_parse_result(parsed)
        semantic = normalize(semantic_input)
        geometry = build_geometry(geometry_from_normalization_input(semantic_input))
        run_input = from_inputs_ready(ready, checkpoint, parse_audit, tool_run, evidence)
        run_semantic = normalize(run_input)
        run_geometry = build_geometry(geometry_from_normalization_input(run_input))
        assert semantic.status == run_semantic.status == 'success'
        assert semantic.value == run_semantic.value
        assert normalize(semantic_input) == semantic
        assert geometry.layout == run_geometry.layout
        assert geometry.partition == run_geometry.partition
        assert geometry.value == run_geometry.value
        check_coverage(geometry)
        check_coverage(run_geometry)
        direct_wire = assert_wire(geometry)
        run_wire = assert_wire(run_geometry)
    assert repository.load_attempt(ready.run_id) == attempt
    assert repository.load_checkpoint(ready.run_id) == checkpoint
    assert repository.read_terminal(ready.run_id) is None
    assert attempt.phase == 'unsealed'
    negative = unsupported_comparator(parsed)
    alias_rejection = false_first_acquisition_alias(parsed)
    print(json.dumps({'checks': {'status': 'passed', 'local_records': 40, 'base_fragments': 41,
                                'independent_body_shapes': 6, 'projected_records': 38,
                                'exact_units_and_per_record_coverage': True,
                                'w005_w006_w007_w008_no_io_equivalence': True,
                                'attempt_phase': attempt.phase, 'terminal': None,
                                'direct_wire_sha256': direct_wire, 'readback_wire_sha256': run_wire,
                                'unsupported_comparator': negative,
                                'false_first_acquisition_alias': alias_rejection}}, indent=2))


if __name__ == '__main__':
    main()
