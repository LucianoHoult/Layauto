"""Exercise occupancy solely via the actual-file analysis facade."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'support'))
from analysis_inputs import FIXTURE, load, materialize, rebind, write
from analysis_projection_inputs import COORDINATE, SAMPLE, projected_manifest
from layauto_v2.analysis import AnalysisRequest, OccupancyRequest, analyze_cell


def run(manifest, budget, *, effective=False):
    return analyze_cell(AnalysisRequest(manifest), occupancy=OccupancyRequest(budget, effective))


def index_of(result):
    query = result.occupancy
    assert query.status == 'success' and query.value is not None, query
    assert query.layout is result.local.facets.drawn.value.layout
    if query.effective is not None:
        assert query.effective is result.local.facets.effective.value
    return query.value


def test_public_cell_to_gds_and_track_queries(tmp_path):
    result = run(projected_manifest(tmp_path), 48)
    assert result.request_status == 'completed'
    index = index_of(result)
    assert index.effective is None
    reports = {r.layer: (r.record_count, r.projection) for r in index.layers}
    assert len(reports) == 15 and sum(n for n, _ in reports.values()) == 40
    assert reports['POLY'] == (1, 'missing_declaration')
    assert reports['BOUNDARY'] == (1, 'projection_none')
    assert reports['CUT'] == (0, 'missing_declaration')
    assert Counter(f.layer for f in index.fragments) == {'FIN': 18, 'LI': 20, 'M1': 10}
    assert index.in_cell('M1', 9, 9) == ()
    fin, = index.in_cell('FIN', 0)
    assert fin.rect.bounds == (10, 24, 110, 26)
    assert fin in index.for_layer('FIN', view='drawn')
    assert index.model.layers['M1'].cell_bounds(2, 2).bounds == (32, 40, 48, 60)
    fragment, = index.in_cell('M1', 2, 2, view='drawn')
    assert fragment.rect.bounds == (32, 48, 45, 58) and fragment.rect.area == 130
    record = fragment.source.record
    source = next(s for s in result.captures if s.uri == record.source.uri)
    assert record.source.sha256 == source.sha256 and record.source.byte_offset == 2352
    assert source.data[2352:2356] == bytes.fromhex('00040800')  # GDS BOUNDARY
    assert record.raw_xy == ((0, 48), (45, 48), (45, 58), (0, 58), (0, 48))
    pieces = index.for_record(record.id, view='drawn')
    assert [f.indices for f in pieces] == [(0, 2), (1, 2), (2, 2)]
    assert [f.rect.x1 - f.rect.x0 for f in pieces] == [16, 16, 13]
    assert pieces[-1] is fragment
    summary = json.loads(result.report_json)
    assert 'occupancy' in summary['facets'] and 'DiscreteFragment' not in result.report_json


def test_local_queries_equal_across_absent_valid_and_invalid_external_body(tmp_path):
    manifest = projected_manifest(tmp_path / 'absent')
    assert not (manifest.parent / 'body/context.json').exists()
    absent = run(manifest, 100, effective=True)
    selected_manifest = projected_manifest(tmp_path / 'selected', body=True)
    valid = run(selected_manifest, 100, effective=True)
    assert absent.request_status == valid.request_status == 'completed'
    assert absent.external_body.status == 'not_selected' and valid.external_body.status == 'evaluated'
    assert absent.parent_global == 'unknown' and 'body_path_proof' in absent.missing_context
    body_rows = [t for t in absent.local.facets.terminals.value if t.expected.role == 'B']
    assert len(body_rows) == 2 and all(t.comparison == 'indeterminate' for t in body_rows)
    assert absent.local.receipt_ref != valid.local.receipt_ref
    path = selected_manifest.parent / 'body/context.json'
    body = load(path)
    body['source_gds']['sha256'] = '0' * 64
    write(path, body)
    invalid = run(selected_manifest, 100, effective=True)
    assert invalid.request_status == 'rejected' and invalid.external_body.status == 'error'
    assert any(f.source.uri == 'body/context.json' for f in invalid.findings)
    expected = index_of(absent)
    for other in (index_of(valid), index_of(invalid)):
        assert other.model == expected.model and other.layers == expected.layers
        assert other.fragments == expected.fragments and other.diagnostics == expected.diagnostics
        for f in expected.fragments:
            assert other.in_cell(f.layer, *f.indices, view=f.view) == expected.in_cell(
                f.layer, *f.indices, view=f.view)
            assert other.for_record(f.record_id, view=f.view) == expected.for_record(f.record_id, view=f.view)


def test_effective_cut_islands_preserve_piece_and_contributor_ids(tmp_path):
    manifest = projected_manifest(tmp_path)
    # Bind the W018 special stream to a local header; raw electrical facts still
    # refer to the synthetic circuit. Only drawn/effective geometry is exercised.
    (tmp_path / 'source.gds').write_bytes((FIXTURE / 'special/cut_islands/source.gds').read_bytes())
    header = load(tmp_path / 'query/local-header.json')
    header['top_identities']['layout'] = 'CUT_ISLANDS_SYNTH'
    write(tmp_path / 'query/local-header.json', header)
    for name in ('iXref.temp', 'nXref.temp'):
        path = tmp_path / 'query/raw' / name
        lines = path.read_text().splitlines()
        lines[1] = '# SVDB: Layout Primary CUT_ISLANDS_SYNTH'
        lines[7] = lines[7].replace('INV_M1_SYNTH', 'CUT_ISLANDS_SYNTH', 1)
        path.write_text('\n'.join(lines) + '\n')
    doc = yaml.safe_load(SAMPLE.read_bytes())
    li = doc['coordinate_projection']['layers']['LI']
    li['x_edges'].update(pitch_dbu=32, cells=5)
    li['y_edges'].update(pitch_dbu=16, cells=13)
    write(tmp_path / COORDINATE, doc)
    rebind(tmp_path)
    result = run(manifest, 5, effective=True)
    index = index_of(result)
    raw, = index.in_cell('LI', 4, 1, view='drawn')
    assert raw.rect.bounds == (130, 20, 150, 24) and raw.source.record_source.byte_offset == 182
    pieces = sorted(index.in_cell('LI', 4, 1, view='effective'), key=lambda f: f.rect.x0)
    assert [f.rect.bounds for f in pieces] == [(130, 20, 139, 24), (141, 20, 150, 24)]
    scale = index.layout.units.canonical_tick_nm
    assert [f.rect.area * scale**2 for f in pieces] == [36, 36]
    assert (pieces[1].rect.x0 - pieces[0].rect.x1) * scale == 2
    regions = result.local.facets.effective.value.for_record(raw.record_id).regions
    assert {(f.region_ref, f.piece_ref, f.rect) for f in pieces} == {
        (r.ref, p.ref, p.rect) for r in regions for p in r.pieces}
    assert set(index.for_record(raw.record_id, view='effective')) == set(pieces)
    for f in pieces:
        cut_id, = f.contributors
        cut = index.layout.record(cut_id)
        assert cut.layer == 'CUT' and cut.source.byte_offset == 246


def test_old_coordinate_owner_absent_by_layer(tmp_path):
    result = run(materialize(tmp_path), 0)
    index = index_of(result)
    assert len(index.layers) == 15 and len(index.layout.records) == 40
    assert {r.projection for r in index.layers} == {'missing_declaration'}
    assert len(index.diagnostics) == 40 and not index.fragments


def test_invalid_declaration_and_capture_drift(tmp_path):
    manifest = projected_manifest(tmp_path)
    doc = yaml.safe_load(SAMPLE.read_bytes())
    doc['coordinate_projection']['layers']['M1']['x/edge~'] = 17
    path = tmp_path / COORDINATE
    write(path, doc)
    stale = run(manifest, 48)
    assert stale.local is None and stale.request_status == 'rejected'
    assert stale.occupancy.status == 'not_evaluated' and stale.occupancy.value is None
    assert stale.occupancy.issues[0].code == 'ClosureHashMismatch'
    rebind(tmp_path)
    invalid = run(manifest, 48)
    assert invalid.request_status == 'completed' and len(invalid.local.facets.drawn.value.layout.records) == 40
    query = invalid.occupancy
    assert query.status == 'invalid_declaration' and query.value is None
    issue, = query.issues
    assert issue.code == 'InvalidProjectionDeclaration'
    assert issue.source.uri == COORDINATE and issue.source.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    assert issue.source.field == '/coordinate_projection/layers/M1/x~1edge~0'


def test_combined_budget_and_effective_dependency(tmp_path):
    manifest = projected_manifest(tmp_path)
    drawn = run(manifest, 47).occupancy
    assert drawn.status == 'resource_limit' and drawn.value is None
    assert drawn.required_fragments == 48 and drawn.budget == 47
    assert drawn.exceeded_at.record_source == drawn.layout.record(drawn.exceeded_at.record_id).source
    combined = run(manifest, 48, effective=True).occupancy
    assert combined.status == 'resource_limit' and combined.required_fragments == 68
    assert combined.value is None and combined.exceeded_at.view == 'effective'
    owner = tmp_path / 'tech/physical.json'
    doc = load(owner)
    doc['operators']['rectangle_set_difference/1'] = 'unsupported test operator'
    write(owner, doc)
    rebind(tmp_path)
    result = run(manifest, 100, effective=True)
    assert result.local.facets.drawn.status == 'available'
    query = result.occupancy
    assert query.status == 'not_evaluated' and query.dependencies == ('effective',)
    assert query.value is None and query.issues == result.local.facets.effective.issues
    assert len(index_of(run(manifest, 48)).fragments) == 48


@pytest.mark.parametrize(('budget', 'effective'), [(-1, False), (True, False), (1.5, False), (0, 1)])
def test_invalid_query_options(budget, effective):
    with pytest.raises(ValueError):
        OccupancyRequest(budget, effective)


def test_drawn_dependency_and_large_caller_budget(tmp_path):
    manifest = projected_manifest(tmp_path)
    budget = 1 << 20000
    result = run(manifest, budget)
    assert index_of(result).budget == budget
    assert hex(budget) in result.report_json
    path = tmp_path / 'tech/formats.json'
    doc = load(path)
    doc['geometry_capability']['comparator'] = 'unsupported comparator'
    write(path, doc)
    rebind(tmp_path)
    blocked = run(manifest, 48)
    assert blocked.occupancy.status == 'not_evaluated' and blocked.occupancy.value is None
    assert blocked.occupancy.dependencies == ('drawn',)
    issue, = blocked.occupancy.issues
    assert issue.code == 'UnsupportedGeometryComparator' and issue.source.uri == 'tech/formats.json'


def reported_occupancy_issues(result):
    report = json.loads(result.report_json)
    objects = report['objects']
    summary = objects[report['facets']['occupancy']['ref']]
    assert summary['status'] == result.occupancy.status
    assert tuple(objects[summary['dependencies']['ref']]) == result.occupancy.dependencies
    locations = {}
    for ref in objects[summary['issues']['ref']]:
        issue = objects[ref['ref']]['fields']
        source = issue['source']
        capture = report['captures'][source['capture']]
        locations[issue['code']] = (capture['uri'], source['field'], capture['sha256'])
    return locations


def test_independent_coordinate_and_effective_errors_keep_both_locations(tmp_path):
    outcomes = {}
    for case in ('axis', 'operator', 'combined'):
        root = tmp_path / case
        manifest = projected_manifest(root)
        if case in ('axis', 'combined'):
            coordinate = yaml.safe_load(SAMPLE.read_bytes())
            del coordinate['coordinate_projection']['layers']['M1']['y_edges']
            write(root / COORDINATE, coordinate)
        if case in ('operator', 'combined'):
            physical = root / 'tech/physical.json'
            document = load(physical)
            document['operators']['rectangle_set_difference/1'] = 'unsupported test operator'
            write(physical, document)
        rebind(root)

        result = run(manifest, 100, effective=True)
        query = result.occupancy
        assert result.request_status == ('completed' if case == 'axis' else 'unsupported')
        assert query.status == ('invalid_declaration' if case == 'axis' else 'not_evaluated')
        assert query.value is None and len(result.local.facets.drawn.value.layout.records) == 40
        issues = {}
        for issue in query.issues:
            source = issue.source
            assert source.sha256 == hashlib.sha256((root / source.uri).read_bytes()).hexdigest()
            issues[issue.code] = (source.uri, source.field, source.sha256)
        assert reported_occupancy_issues(result) == issues
        outcomes[case] = result, issues

    _, axis = outcomes['axis']
    _, operator = outcomes['operator']
    combined, both = outcomes['combined']
    assert set(axis) == {'InvalidProjectionDeclaration'}
    assert axis['InvalidProjectionDeclaration'][:2] == (COORDINATE, '/coordinate_projection/layers/M1/y_edges')
    assert set(operator) == {'UnsupportedRegionOperator'}
    assert operator['UnsupportedRegionOperator'][:2] == ('tech/physical.json', '/operators/rectangle_set_difference~11')
    assert both == axis | operator
    assert set(combined.occupancy.dependencies) == {'effective', 'coordinate'}

    manifest = tmp_path / 'combined/analysis.json'
    drawn = run(manifest, 100)
    plain = analyze_cell(AnalysisRequest(manifest))
    assert plain.occupancy is None and 'occupancy' not in json.loads(plain.report_json)['facets']
    assert plain.local == drawn.local == combined.local
    assert plain.request_status == drawn.request_status == combined.request_status
    assert plain.findings == drawn.findings == combined.findings
    assert drawn.occupancy.status == 'invalid_declaration' and drawn.occupancy.value is None
    assert reported_occupancy_issues(drawn) == axis
