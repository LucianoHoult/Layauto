"""Full-run layer checks, independent source geometry and policy failure witnesses."""
from collections import Counter
from dataclasses import FrozenInstanceError, replace
from unittest.mock import PropertyMock, patch

import pytest
import yaml

from layauto_v2.domain.publication import InputsReady, PipelineResult, RunRequest
from layauto_v2.normalization.projection_model import ProjectionConfigError
from layauto_v2.pipeline import assemble_stage2, prepare_inputs
from layauto_v2.repository import PublicationRepository
from layauto_v2.state.layer_checks import LayerInitializationChecks
from w005_cases import rebind, sha, write_json
from w008_geometry_cases import EXPECTED_RECTS, edit_geometry
from w009_cases import change_owner, independent_difference
from w018_cases import COORDINATE_URI
from w022_cases import assemble, sample


def check(root, budget=312):
    state, repo, before = assemble(root, budget)
    result = LayerInitializationChecks(state)
    assert result.candidate is state and repo.snapshot() == before
    assert repo.load_attempt('w022').phase == 'unsealed' and repo.read_terminal('w022') is None
    return result


@pytest.fixture(scope='module')
def full(tmp_path_factory):
    return check(sample(tmp_path_factory.mktemp('complete'), complete=True))


@pytest.fixture(scope='module')
def partial(tmp_path_factory):
    return check(sample(tmp_path_factory.mktemp('w018'), complete=False), 68)


def test_complete_checks_bind_capture_frame_and_both_owners(full):
    assert full.passed
    state = full.candidate
    assert len(full.layers) == 15 and all(row.passed for row in full.layers.values())
    assert Counter(row.initialization.policy.declaration['lifecycle'] for row in full.layers.values()) == {
        'frame_static': 5, 'preserve_drawn': 10}
    assert Counter(row.initialization.availability for row in full.layers.values()) == {
        'reconstructed': 10, 'projection_none': 2, 'no_local_records': 3}
    hashes = {s['uri']: s['sha256'] for s in state.capture_binding['sources']}
    for ref, field in ((full.comparator, '/geometry_capability/comparator'),
                       (full.lifecycle_operator, '/operators/lifecycle~11'), (full.frame_rule, '/rules/0')):
        assert ref.sha256 == hashes[ref.uri] and ref.field == field
    assert state.occupancy.model.coordinate_source.sha256 == 'cd25a045187c22d23040ea45363043b33b497d6318890a73a15782b293346009'
    for name, row in full.layers.items():
        assert row.initialization is state.layers[name]
        assert row.initialization.projection.declaration.sha256 == hashes[COORDINATE_URI]
        assert row.initialization.policy.source.sha256 == hashes['tech/drawn.json']
        assert row.frame is full.layers['BOUNDARY'].frame
        assert row.frame.rect.bounds == (0, 0, 160, 200) and row.frame.source.byte_offset == 112
        records = [r for r in state.layout.records if r.layer == name]
        assert Counter(r.rect.bounds for r in records) == Counter(EXPECTED_RECTS.get(name, ()))
        assert set(row.sources) == {r.source for r in records}
        assert all(s.sha256 == hashes['source.gds'] for s in row.sources)
    marker, = full.layers['MARKER'].sources
    assert marker.byte_offset == 2608 and full.layers['MARKER'].initialization.availability == 'projection_none'


def test_all_projected_sources_reconstruct_and_keep_record_region_piece_backlinks(full):
    index = full.candidate.occupancy
    assert Counter(f.view for f in index.fragments) == {'drawn': 220, 'effective': 92}
    assert sum(r.initialization.drawn_reconstructed for r in full.layers.values()) == 38
    for record in index.layout.records:
        if not full.layers[record.layer].initialization.policy.projected:
            assert not index.for_record(record.id)
            continue
        rows = index.for_record(record.id, view='drawn')
        independent_difference(record.rect.bounds, (), [f.rect.bounds for f in rows])
        for f in rows:
            assert f.source.record is record and f in index.in_cell(record.layer, *f.indices, view='drawn')
    for result in index.effective.records:
        for region in result.regions:
            for piece in region.pieces:
                rows = [f for f in index.for_record(result.record_id, view='effective') if f.piece_ref == piece.ref]
                independent_difference(piece.rect.bounds, (), [f.rect.bounds for f in rows])
                assert all(f.region_ref == region.ref and f.contributors == region.contributors
                           and f in index.in_cell(f.layer, *f.indices, view='effective') for f in rows)
    poly, = index.in_cell('POLY', -3)
    assert full.layers['POLY'].gate_track_numbers_available is True
    assert full.layers['FIN'].gate_track_numbers_available is None
    assert poly.rect.bounds == (58, 10, 62, 190) and poly.source.record_source.byte_offset == 432
    assert index.model.layers['POLY'].centre(-3) == 60 and index.model.layers['POLY'].centre(-2) == 69
    m1, = index.in_cell('M1', 2, 2)
    assert (m1.rect.bounds, m1.rect.area, m1.source.record_source.byte_offset) == ((32, 48, 45, 58), 130, 2352)


def test_partial_retains_supported_checks_and_single_capture(partial, full):
    assert not partial.passed and sum(not row.passed for row in partial.layers.values()) == 10
    poly = partial.layers['POLY']
    assert not poly.projection_passed and poly.lifecycle_passed and not poly.drawn_issues
    assert poly.gate_track_numbers_available is False
    assert poly.sources == full.layers['POLY'].sources and poly.sources[0].byte_offset == 432
    assert poly.initialization.gap.operation == 'initialize_gate_tracks'
    assert 'pitch_nm or pitch_nm_ref' in poly.initialization.gap.required_fields
    issue, = poly.projection_issues
    assert issue.code == 'RequiredProjectionUnavailable'
    assert issue.source == poly.initialization.projection.declaration
    assert issue.source.field == '/coordinate_projection/layers/POLY'
    assert partial.candidate.capture_binding != full.candidate.capture_binding
    with pytest.raises(ValueError):
        replace(partial, layers=full.layers)
    with pytest.raises(TypeError):
        full.layers['POLY'] = poly
    with pytest.raises(FrozenInstanceError):
        full.layers['POLY'].frame = None
    for checks in (partial, full):
        state = checks.candidate
        assert state.body['local_graph_union'] is False and state.body['lvs_status'] == 'not_run'
        assert state.body_evidence.sources[0].uri == 'body/context.json'
        assert any(f.status == 'unknown' for f in state.annotation.fragments)
        assert state.uncovered_conductor_policy == 'suspect_conductor'
        delta, = state.target_context.differences
        assert (delta.operand_ref.name, delta.axis, delta.semantic_before.lexeme, delta.semantic_after.lexeme
                ) == ('MN0', 'channel_length', '4n', '5n')


@pytest.mark.parametrize('x_cells', [8, 3], ids=['full_grid', 'ends_inside_gate'])
def test_poly_2d_occupancy_uses_its_declared_grid(tmp_path, full, x_cells):
    root = sample(tmp_path, complete=True)
    owner = root / COORDINATE_URI
    doc = yaml.safe_load(owner.read_bytes())
    layers = doc['coordinate_projection']['layers']
    grid = layers['OD']
    layers['POLY'] = {**grid, 'x_edges': {**grid['x_edges'], 'cells': x_cells}}
    write_json(owner, doc)
    rebind(root)

    checks = check(root, 400)
    gate = checks.layers['POLY']
    row = gate.initialization
    record, = (r for r in checks.candidate.layout.records if r.layer == 'POLY')
    assert checks.candidate.layout == full.candidate.layout
    assert all(layer.passed for name, layer in checks.layers.items() if name != 'POLY')
    assert record.rect.bounds == (58, 10, 62, 190) and record.source.byte_offset == 432
    assert gate.sources == (record.source,) and gate.lifecycle_passed and not gate.frame_issues
    assert row.projection.projection == '2d_cells' and not gate.projection_issues
    assert gate.gate_track_numbers_available is False
    declaration = row.projection.declaration
    assert (declaration.uri, declaration.sha256, declaration.field) == (
        COORDINATE_URI, sha(owner), '/coordinate_projection/layers/POLY')

    pieces = checks.candidate.occupancy.for_record(record.id, view='drawn')
    if x_cells == 8:
        # The x=60 edge bisects the strip. Each half occupies rows 1 through 18.
        assert {(f.indices, f.rect.bounds) for f in pieces} == {
            ((x, y), (left, 10 * y, right, 10 * (y + 1)))
            for x, left, right in ((2, 58, 60), (3, 60, 62)) for y in range(1, 19)}
        assert len(pieces) == 36 and sum(f.rect.area for f in pieces) == 720
        assert row.availability == 'reconstructed' and row.drawn_reconstructed == 1 and not row.diagnostics
        assert gate.projection_passed and gate.passed and checks.passed
    else:
        # The grid stops at x=60, two DBU short of the original right edge.
        diagnostic, = row.diagnostics
        assert diagnostic.status == 'outside_range' and diagnostic.source.record_source == record.source
        assert row.availability == 'incomplete' and row.drawn_reconstructed == 0 and pieces == ()
        assert not gate.projection_passed and not gate.passed and not checks.passed


def test_gate_between_declared_1d_tracks_has_no_track_number(tmp_path):
    root = sample(tmp_path, complete=True)
    owner = root / COORDINATE_URI
    doc = yaml.safe_load(owner.read_bytes())
    # The first two centres become 59 and 68 nm. The captured strip stays at 60 nm.
    doc['coordinate_projection']['layers']['POLY']['first_centre']['lower_edge_nm'] = 57
    write_json(owner, doc)
    rebind(root)
    checks = check(root)
    gate = checks.layers['POLY']
    diagnostic, = gate.initialization.diagnostics
    assert diagnostic.status == 'off_track' and diagnostic.source.record_source.byte_offset == 432
    assert gate.lifecycle_passed and not gate.projection_passed and not checks.passed
    assert gate.gate_track_numbers_available is False


@pytest.fixture(scope='module')
def altered(tmp_path_factory):
    root = sample(tmp_path_factory.mktemp('altered'), complete=True)
    config = root / COORDINATE_URI
    doc = yaml.safe_load(config.read_bytes())
    layers = doc['coordinate_projection']['layers']
    layers['M1']['x_edges']['cells'] = 3  # End at x=48.
    layers['POLY'] = layers['OD']  # 2D coverage gives no gate track number.
    layers['BTAP_N'] = {'projection': 'none'}
    del layers['BTAP_P'], layers['MARKER']
    layers['LI']['x_edges'].update(pitch_dbu=32, cells=5)
    layers['LI']['y_edges'].update(pitch_dbu=16, cells=13)
    write_json(config, doc)
    edit_geometry(root, append=[('MARKER', EXPECTED_RECTS['MARKER'][0]), ('MARKER', (159, 10, 161, 12)),
                                ('LI', (130, 20, 150, 24)), ('CUT', (139, 18, 141, 26))])
    return check(root, 500)


def test_outside_empty_required_layers_gate_and_marker_have_independent_verdicts(altered):
    assert not altered.passed
    m1, gate, empty, missing, marker = (altered.layers[n] for n in ('M1', 'POLY', 'BTAP_N', 'BTAP_P', 'MARKER'))
    assert m1.lifecycle_passed and not m1.projection_passed and m1.initialization.drawn_reconstructed == 2
    assert [(d.status, d.source.record_source.byte_offset) for d in m1.initialization.diagnostics] == [
        ('outside_range', 2480), ('outside_range', 2544)]
    assert gate.initialization.availability == 'reconstructed' and gate.projection_passed and gate.passed
    assert gate.gate_track_numbers_available is False
    for row, kind in ((empty, 'projection_none'), (missing, 'missing_declaration')):
        assert not row.sources and row.initialization.availability == kind
        assert not row.passed and row.projection_issues[0].code == 'RequiredProjectionUnavailable'
    assert marker.projection_passed and marker.initialization.availability == 'missing_declaration'
    outside, = marker.frame_issues
    assert not marker.passed and marker.lifecycle_passed and outside.code == 'OutsideFrame'
    assert outside.source == marker.sources[-1] and outside.source.uri == 'source.gds'


def test_same_cell_cut_islands_in_complete_run(altered):
    assert altered.layers['LI'].passed
    index = altered.candidate.occupancy
    raw, = index.in_cell('LI', 4, 1, view='drawn')
    cut, = (r for r in index.layout.records if r.layer == 'CUT')
    pieces = sorted(index.in_cell('LI', 4, 1, view='effective'), key=lambda f: f.rect.x0)
    assert [f.rect.bounds for f in pieces] == [(130, 20, 139, 24), (141, 20, 150, 24)]
    assert [f.rect.area for f in pieces] == [36, 36] and pieces[1].rect.x0 - pieces[0].rect.x1 == 2
    assert independent_difference(raw.rect.bounds, [cut.rect.bounds], [f.rect.bounds for f in pieces]) == 72
    assert len({f.piece_ref for f in pieces}) == 2
    regions = index.effective.for_record(raw.record_id).regions
    assert {f.region_ref for f in pieces} == {region.ref for region in regions}
    assert all(f.record_id == raw.record_id and f.contributors == (cut.id,) for f in pieces)


def test_dropped_duplicate_and_substituted_frame_are_detected(altered):
    # Inject a read fault on the actual side only. The frozen captured GDS stays intact.
    state = altered.candidate
    records = state.layout.records
    original, duplicate = [r for r in records if r.layer == 'MARKER' and r.rect.bounds == EXPECTED_RECTS['MARKER'][0]]
    assert duplicate.source != original.source
    frame, = [r for r in records if r.layer == 'BOUNDARY']
    wrong = replace(frame, rect=original.rect)
    observed = tuple(wrong if r is frame else r for r in records if r is not duplicate)
    with patch.object(type(state.layout), 'records', new=PropertyMock(return_value=observed), create=True):
        damaged = LayerInitializationChecks(state)
    missing, = damaged.layers['MARKER'].drawn_issues
    assert missing.code == 'MissingDrawnRecord' and missing.source == duplicate.source
    for name in ('BOUNDARY', 'BODY_N', 'BODY_P', 'POLY', 'FIN'):
        row = damaged.layers[name]
        assert not row.lifecycle_passed and row.frame is None
        assert row.frame_issues[0].code == 'FrameBindingMismatch' and row.frame_issues[0].source == frame.source
    assert state.layout.records is records and altered.layers['MARKER'].drawn_issues == ()


def test_unsupported_lifecycle_and_frame_rule_do_not_certify_layers(tmp_path):
    root = sample(tmp_path, complete=True)
    change_owner(root, 'physical', lambda doc: doc['operators'].update({'lifecycle/1': 'unavailable'}))
    change_owner(root, 'rules', lambda doc: doc['rules'][0]['parameters'].update(margin_nm=1))
    result = check(root)
    assert not result.passed
    for row in result.layers.values():
        assert row.projection_passed and not row.drawn_issues and not row.lifecycle_passed
        issue, = row.lifecycle_issues
        assert issue.code == 'UnsupportedLifecycleOperator' and issue.source == result.lifecycle_operator
        issue, = row.frame_issues
        assert issue.code == 'UnsupportedFrameRule' and issue.source.field == '/rules/0/parameters'
        assert issue.source.sha256 == sha(root / 'tech/rules.json')


@pytest.mark.parametrize('owner,remove', [
    ('physical', lambda d: d['operators'].pop('lifecycle/1')),
    ('formats', lambda d: d['geometry_capability'].pop('comparator')),
])
def test_missing_required_tech_is_located_before_candidate(tmp_path, owner, remove):
    root = sample(tmp_path, complete=True)
    change_owner(root, owner, remove)
    repo = PublicationRepository()
    result = prepare_inputs(repo, RunRequest('invalid', 'lineage', 'create', str(root / 'site_config.yaml')))
    assert isinstance(result, PipelineResult) and result.deployment_disposition == 'reject'
    failure = repo.read(repo.read(result.closure_ref).failure_ref)
    assert failure.stage == 'stage1' and failure.source.sha256 == sha(root / failure.source.uri)
    if owner == 'physical':
        assert (failure.code, failure.source.uri, failure.source.field) == (
            'RequiredOperatorUnavailable', 'tech/physical.json', '/physical/required_operator_refs')
    else:
        assert (failure.code, failure.source.uri, failure.source.field) == (
            'MissingField', 'tech/formats.json', '/geometry_capability/comparator')


def test_invalid_grid_field_keeps_projection_binder_error_and_geometry(tmp_path):
    root = sample(tmp_path, complete=True)
    path = root / COORDINATE_URI
    doc = yaml.safe_load(path.read_bytes())
    doc['coordinate_projection']['layers']['M1']['x_edges']['pitch_dbu'] = 0
    write_json(path, doc)
    rebind(root)
    repo = PublicationRepository()
    ready = prepare_inputs(repo, RunRequest('bad-grid', 'lineage', 'create', str(root / 'site_config.yaml')))
    assert isinstance(ready, InputsReady)
    before = repo.snapshot()
    with pytest.raises(ProjectionConfigError) as caught:
        assemble_stage2(repo, ready, fragment_budget=312)
    issue = caught.value.issue
    assert issue.code == 'InvalidProjectionDeclaration'
    assert (issue.source.uri, issue.source.sha256, issue.source.field) == (
        COORDINATE_URI, sha(path), '/coordinate_projection/layers/M1/x_edges/pitch_dbu')
    assert len(caught.value.geometry.layout.records) == 40 and repo.snapshot() == before
