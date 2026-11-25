"""Transaction-facing reads from two same-name cells after their files disappear."""
from dataclasses import FrozenInstanceError, replace
from fractions import Fraction

import pytest

from layauto_v2.domain.channel_identity import RationalRect
from layauto_v2.domain.net_annotation import intersections
from layauto_v2.domain.publication import InputsReady, RunRequest
from layauto_v2.normalization.initial_state import build_proposed_initial_state
from layauto_v2.pipeline import assemble_stage2, prepare_inputs
from layauto_v2.repository import PublicationRepository, RepositoryConflict
from layauto_v2.state.mutation import ProposedInitialState
from w005_cases import apply_case, rebind
from w007_cases import ready_copy
from w018_cases import COORDINATE_URI, select_projection


@pytest.fixture(scope='module')
def candidates(tmp_path_factory):
    parent = tmp_path_factory.mktemp('w021')
    root = ready_copy(parent)
    select_projection(root)
    request = RunRequest('w021', 'lineage', 'create', str(root / 'site_config.yaml'))
    a, b = PublicationRepository(), PublicationRepository()
    full = prepare_inputs(a, request)
    root.rename(parent / 'first-capture')
    root = ready_copy(parent)
    apply_case(root, 'unsupported_target')
    select_projection(root)
    raw = root / 'query/raw/net_shapes_n_lo.txt'
    raw.write_bytes(raw.read_bytes().replace(b'600 560\n', b'1000 560\n').replace(b'600 680\n', b'1000 680\n'))
    rebind(root)
    short = prepare_inputs(b, request)
    assert isinstance(full, InputsReady) and isinstance(short, InputsReady)
    assert full.checkpoint_ref != short.checkpoint_ref
    root.rename(parent / 'captured')
    result = []
    for repo, ready, foreign in ((a, full, short), (b, short, full)):
        before = repo.snapshot()
        with pytest.raises(RepositoryConflict) as caught:
            assemble_stage2(repo, foreign, fragment_budget=68)
        assert caught.value.code == 'ReadbackConflict'
        facts = assemble_stage2(repo, ready, fragment_budget=68)
        candidate = build_proposed_initial_state(facts)
        assert candidate == build_proposed_initial_state(facts)
        assert candidate.occupancy is facts.occupancy
        assert candidate.connectivity.effective is candidate.occupancy.effective
        assert candidate.connectivity.effective.base.layout is candidate.layout
        assert candidate.annotation is facts.terminals.value.annotation
        assert candidate.target_context.target is facts.terminals.semantic_facts.target
        binding = candidate.capture_binding['readback']
        assert binding['checkpoint_ref']['digest'] == ready.checkpoint_ref.digest
        assert binding['attempt_digest'] == ready.attempt.ref.digest
        assert repo.load_attempt(ready.run_id) == ready.attempt and repo.read_terminal(ready.run_id) is None
        assert repo.snapshot() == before
        result.append(candidate)
    return result


def test_direct_fragment_evidence_is_independent_of_component(candidates):
    full, short = candidates
    assert full.connectivity.edges == short.connectivity.edges
    assert full.connectivity.components == short.connectivity.components
    for state, expected in ((full, 'annotated'), (short, 'unknown')):
        li, = state.occupancy.in_cell('LI', 1, 3, view='effective')
        assert li.rect.area == 60 and li.source.record.source.byte_offset == 1648
        node, = (n for n in state.connectivity.nodes if n.region.ref == li.region_ref)
        component, = (c for c in state.connectivity.components if node.ref in c.members)
        assert len(component.members) == 3
        target, = (t for t in state.annotation.targets if t.target_id.region_ref == li.region_ref)
        assert (target.node_ref, target.component_ref) == (node.ref, component.ref)
        tick = state.layout.units.canonical_tick_nm
        window = RationalRect(*(Fraction(v * tick) for v in li.rect.bounds))
        fragment, = (f for f in state.annotation.fragments if f.target_ref == target.ref
                     and intersections((window,), f.rectangles))
        assert intersections((window,), fragment.rectangles) == (window,)
        assert fragment.status == expected
        seed, = (e for e in state.annotation.evidence if e.record['record_id'] == 'R04')
        assert seed.query_key.identity == 'n_lo' and seed.net_id.name == 'VSS'
        if expected == 'annotated':
            assert fragment.evidence_refs == (seed.ref,) and fragment.net_ids == (seed.net_id,)
        else:
            assert fragment.evidence_refs == fragment.net_ids == ()
            assert state.uncovered_conductor_policy == 'suspect_conductor'
        m1, = state.occupancy.in_cell('M1', 2, 2, view='drawn')
        assert m1.rect.area == 130 and m1.source.record.source.byte_offset == 2352


def test_local_body_and_nonconducting_marker(candidates):
    state, _ = candidates
    marker, = (r for r in state.layout.records if r.layer == 'MARKER')
    assert all(t.target_id.record_id != marker.id for t in state.annotation.targets)
    cls, = (r for r in state.annotation.classifications if r.record_id == marker.id)
    assert cls.classification == 'marker' and cls.source == marker.source
    coverage, = (r for r in state.rules.payload['rules'] if r['id'] == 'T10.coverage')
    assert coverage['parameters']['unknown_nonconductor_policy'] == 'preserve_disclose'
    assert state.body['local_graph_union'] is False and state.body['lvs_status'] == 'not_run'
    assert state.body_evidence.sources[0].uri == 'body/context.json'
    body = [r for r in state.terminals if r.target.role == 'B']
    assert {r.target.device_id.name: tuple(n.name for n in r.observed_net_ids) for r in body} == {
        'MN0': ('VSS',), 'MP0': ('VDD',)}
    assert all(r.component_refs and r.context_path and not r.local_observed_net_ids for r in body)


def test_per_layer_owners_reconstruction_and_scope(candidates):
    state, _ = candidates
    layers = state.layers
    assert len(layers) == 15
    for name, records, fragments in [('FIN', 18, 18), ('LI', 3, 20), ('M1', 4, 10)]:
        row = layers[name]
        assert row.availability == 'reconstructed' and row.gap is None
        assert row.drawn_reconstructed == row.projection.record_count == records
        assert len(state.occupancy.for_layer(name, view='drawn')) == fragments
    assert layers['LI'].effective_pieces == layers['LI'].effective_reconstructed == 3
    for name, lifecycle in [('BOUNDARY', 'frame_static'), ('MARKER', 'preserve_drawn')]:
        row = layers[name]
        assert row.availability == 'projection_none' and row.projection.record_count == 1
        assert row.gap is None and row.policy.declaration['lifecycle'] == lifecycle
    poly = layers['POLY']
    assert poly.policy.declaration['lifecycle'] == 'frame_static'
    assert poly.availability == 'missing_declaration' and poly.projection.record_count == 1
    diag, = poly.diagnostics
    assert diag.source.record.source.byte_offset == 432
    assert poly.projection.declaration.uri == COORDINATE_URI
    assert poly.projection.declaration.field == '/coordinate_projection/layers/POLY'
    assert poly.gap.operation == 'initialize_gate_tracks'
    assert 'pitch_nm or pitch_nm_ref' in poly.gap.required_fields and 'index_range_inclusive' in poly.gap.required_fields
    assert layers['CUT'].projection.record_count == 0 and layers['CUT'].availability == 'missing_declaration'


def test_target_is_bound_separately_and_cannot_be_spliced(candidates):
    full, short = candidates
    assert full.target_context.differences == ()
    diff, = short.target_context.differences
    assert (diff.operand_ref.name, diff.axis) == ('MN0', 'channel_length')
    for circuit, value, uri, n in ((short.current, diff.semantic_before, 'source.cdl', 4),
                                   (short.target_context.target, diff.semantic_after, 'target.cdl', 5)):
        device, = (d for d in circuit.cells[0].devices if d.id.name == 'MN0')
        length, = (p for p in device.parameters if p.axis == 'channel_length')
        assert length == value and length.exact == Fraction(n, 10**9)
        assert length.source in diff.provenance and (length.source.uri, length.source.line) == (uri, 3)
        hashes = {s['uri']: s['sha256'] for s in short.capture_binding['sources']}
        assert length.source.sha256 == hashes[uri]
    with pytest.raises(TypeError):
        ProposedInitialState()
    with pytest.raises(TypeError):
        replace(full, target_context=short.target_context)
    with pytest.raises(FrozenInstanceError):
        full.current = short.current
    with pytest.raises(TypeError):
        full.layers['POLY'] = None
    with pytest.raises(TypeError):
        full.capture_binding['readback']['run_id'] = 'foreign'
    assert full.target_context.differences == () and full.layers['POLY'].projection.record_count == 1
