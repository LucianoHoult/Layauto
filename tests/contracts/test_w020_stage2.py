"""Full-run Stage 2 assembly, capture isolation and exact cross-component witnesses."""
from collections import Counter
from dataclasses import replace
from fractions import Fraction

import pytest

from layauto_v2.domain.publication import InputsReady
from layauto_v2.normalization.stage2 import Stage2AssemblyError
from layauto_v2.pipeline import assemble_stage2, prepare_inputs
from layauto_v2.repository import PublicationRepository, RepositoryConflict
from w005_cases import apply_case, sha
from w006_cases import caller_request
from w007_cases import ready_copy
from w009_cases import change_owner
from w013_cases import rewrite_net_response
from w018_cases import COORDINATE_URI, select_projection


def capture(repository, root, run_id):
    ready = prepare_inputs(repository, caller_request(root, run_id=run_id))
    assert isinstance(ready, InputsReady)
    return ready


@pytest.fixture(scope='module')
def interleaved(tmp_path_factory):
    repository = PublicationRepository()
    original = ready_copy(tmp_path_factory.mktemp('original'))
    rewrite_net_response(original, 'n_a', ())
    first = capture(repository, original, 'old-grid-missing-gate-label')
    selected = ready_copy(tmp_path_factory.mktemp('selected'))
    apply_case(selected, 'unsupported_target')
    select_projection(selected)
    second = capture(repository, selected, 'layer-grid-c13')
    snapshots = repository.snapshot()
    # Hide both site trees after W006 has captured their real bytes.
    original.rename(original.with_name('captured-files'))
    selected.rename(selected.with_name('captured-files'))
    second_result = []
    read = repository.read

    def interleave(ref):
        record = read(ref)
        if ref == first.parse_ref:
            # Complete B while A is partway through reading its checkpoint's refs.
            second_result.append(assemble_stage2(repository, second, fragment_budget=100))
        return record

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(repository, 'read', interleave)
        first_result = assemble_stage2(repository, first, fragment_budget=100)
    other, = second_result
    assert repository.snapshot() == snapshots
    return (repository, first, first_result), (repository, second, other)


def test_each_interleaved_assembly_resolves_only_its_captured_inputs(interleaved):
    for (repository, ready, facts), coordinate in zip(interleaved, ('tech/coordinate.json', COORDINATE_URI), strict=True):
        index = facts.occupancy
        terminal = facts.terminals
        binding = terminal.value.capture_binding['readback']
        assert binding['run_id'] == ready.run_id
        for name, ref in [('checkpoint_ref', ready.checkpoint_ref), ('parse_ref', ready.parse_ref), ('tool_ref', ready.tool_ref)]:
            assert (binding[name]['run_id'], binding[name]['digest']) == (ready.run_id, ref.digest)
        captured = {s.uri: s.sha256 for s in repository.read(ready.parse_ref).result.sources}
        assert index.model.coordinate_source.uri == coordinate
        assert index.model.coordinate_source.sha256 == captured[coordinate]
        assert terminal.input.value.effective is index.effective
        assert index.effective.base.layout is index.layout
        assert index.layout.gds.sources[0].sha256 == captured['source.gds']
        assert all(ref.sha256 == captured[ref.uri] for ref in index.model.tech_sources)
        assert terminal.semantic_facts.source.selected_cell.name == 'INV_M1_SYNTH'
        assert [cell.id for cell in terminal.semantic_facts.target.cells] == [terminal.semantic_facts.source.selected_cell]
        for circuit, uri in [(terminal.semantic_facts.source, 'source.cdl'), (terminal.semantic_facts.target, 'target.cdl')]:
            assert circuit.preservation.sources[0].uri == uri
            assert circuit.preservation.sources[0].sha256 == captured[uri]
        assert len(index.layout.records) == 40
        assert repository.load_attempt(ready.run_id) == ready.attempt
        assert (ready.attempt.phase, ready.attempt.revision) == ('unsealed', 1)
        assert repository.read_terminal(ready.run_id) is None
    (_, first, old), (_, second, new) = interleaved
    assert first.checkpoint_ref.digest != second.checkpoint_ref.digest
    assert old.occupancy.model.model_id != new.occupancy.model.model_id
    assert old.occupancy.fragments == ()
    assert {r.projection for r in old.occupancy.layers} == {'missing_declaration'}
    assert Counter(f.layer for f in new.occupancy.fragments if f.view == 'drawn') == {'FIN': 18, 'LI': 20, 'M1': 10}
    old_draft, new_draft = old.terminals.value, new.terminals.value
    assert old_draft.local.semantic_digest == new_draft.local.semantic_digest
    for draft, expected in [(old_draft, ()), (new_draft, ('A',))]:
        gates = [row for row in draft.relations if row.target.role == 'G']
        assert len(gates) == 2
        assert all(tuple(net.name for net in row.local_observed_net_ids) == expected for row in gates)
        assert len(draft.local.edges) == 8 and len(draft.local.components) == 6


def test_equal_fin_counts_preserve_the_channel_length_obligation(interleaved):
    (_, _, original), (repository, ready, selected) = interleaved
    assert original.terminals.semantic_facts.differences == ()
    facts = selected.terminals.semantic_facts
    for circuit in (facts.source, facts.target):
        assert {dev.id.name: param.exact for dev in circuit.cells[0].devices for param in dev.parameters
                if param.axis == 'fins_per_finger'} == {'MN0': 5, 'MP0': 7}
    rows = selected.terminals.value.channel_observations['comparisons']
    assert {r['fields']['device_id']['name']: r['fields']['measured'] for r in rows
            if r['fields']['axis'] == 'fins_per_finger'} == {'MN0': 5, 'MP0': 7}
    delta, = facts.differences
    assert (delta.operand_ref.name, delta.axis, delta.required_capability) == ('MN0', 'channel_length', 'resize:channel_length')
    assert 'planner_admission_required' in delta.obligations
    captured = {s.uri: s for s in repository.read(ready.parse_ref).result.sources}
    for p, uri, n in [(delta.semantic_before, 'source.cdl', 4), (delta.semantic_after, 'target.cdl', 5)]:
        assert p.exact == Fraction(n, 10**9) and p.unit == 'metres'
        assert p.source.uri == uri and p.source.sha256 == captured[uri].sha256 and p.source.line == 3
        assert f'L={n}n' in captured[uri].data.decode().splitlines()[p.source.line - 1].split()
        assert p.source in delta.provenance


def test_annotation_trace_checks_exact_piece_membership_and_raw_source(interleaved):
    from docs.tasks.W020.trace import conductor_trace
    repository, ready, facts = interleaved[1]
    trace = conductor_trace(facts)
    assert trace['record']['source']['byte_offset'] == 1648
    assert list(trace['drawn']['bounds_dbu']) == list(trace['effective']['bounds_dbu']) == [28, 30, 34, 40]
    assert trace['drawn']['area_dbu2'] == 60
    physical, annotation = trace['physical'], trace['annotation']
    assert len(physical['members']) == 3 and physical['node_ref'] in physical['members']
    assert physical['component_ref'] == annotation['component_ref']
    assert {edge['source']['byte_offset'] for edge in physical['edges']} == {1840, 2096}
    for edge in physical['edges']:
        assert {endpoint['node_ref'] for endpoint in edge['endpoints']} <= set(physical['members'])
        assert all(endpoint['overlaps'] for endpoint in edge['endpoints'])
    assert (annotation['net_name'], annotation['query_record']) == ('VSS', 'R04')
    assert Fraction(annotation['covered_area_nm2']) == 60
    capture_data = {s.uri: s.data for s in repository.read(ready.parse_ref).result.sources}
    sources = annotation['source_operands']
    assert {ref['uri'] for ref in sources['vertices_nm']} >= {'query/raw/net_shapes_n_lo.txt', 'query/dialect.json'}
    assert any(ref['uri'] == 'query/raw/nXref.temp' and ref['line'] == 11 and ref['token_0based'] == 3
               for ref in sources['schematic_name'])
    assert capture_data['source.gds'][1648:1652] == bytes.fromhex('00040800')
    assert capture_data['query/raw/nXref.temp'].splitlines()[10].split() == [b'0', b'n_lo', b'0', b'VSS']
    line_end = trace['m1_line_end']
    assert line_end['source']['byte_offset'] == 2352 and line_end['area_dbu2'] == 130
    assert list(line_end['bounds_dbu']) == [32, 48, 45, 58]


def test_scope_distinguishes_empty_missing_skipped_covered_and_body_context(interleaved):
    from docs.tasks.W020.scope_report import scope_summary
    original, selected = (scope_summary(facts) for _, _, facts in interleaved)
    assert set(selected) == {'current_semantic', 'immutable_target', 'geometry', 'occupancy', 'annotation', 'connectivity'}
    assert selected['current_semantic']['source']['uri'] == 'source.cdl'
    assert selected['immutable_target']['source']['uri'] == 'target.cdl'
    assert len(selected['immutable_target']['delta_ids']) == 1
    old = original['occupancy']['layers']
    assert len(old) == 15 and all(row['declaration'] == 'missing_declaration' for row in old.values())
    assert sum(row['drawn_fragments'] for row in old.values()) == 0
    layers = selected['occupancy']['layers']
    assert (layers['CUT']['drawn_records'], layers['CUT']['declaration']) == (0, 'missing_declaration')
    assert (layers['POLY']['drawn_records'], layers['POLY']['drawn_diagnostics']) == (1, {'missing_declaration': 1})
    assert (layers['BOUNDARY']['drawn_records'], layers['BOUNDARY']['declaration']) == (1, 'projection_none')
    for name, records, fragments in [('FIN', 18, 18), ('LI', 3, 20), ('M1', 4, 10)]:
        row = layers[name]
        assert row['drawn_records'] == row['drawn_reconstructed'] == records
        assert row['drawn_fragments'] == fragments
    assert layers['LI']['effective_reconstructed'] == layers['LI']['effective_source_pieces'] == 3
    marker, = selected['geometry']['markers']
    assert not marker['has_net_target'] and marker['source']['uri'] == 'source.gds'
    connectivity = selected['connectivity']
    assert connectivity['local_graph_union'] is False
    assert connectivity['body_context_source']['uri'] == 'body/context.json'
    assert {r['device']: r['context_observed_nets'] for r in connectivity['body_terminals']} == {
        'MN0': ['VSS'], 'MP0': ['VDD']}
    assert all(not r['local_observed_nets'] for r in connectivity['body_terminals'])


def test_readback_rejects_foreign_attempt_for_same_run_id(tmp_path):
    original = ready_copy(tmp_path / 'first')
    selected = ready_copy(tmp_path / 'second')
    select_projection(selected)
    repository, other = PublicationRepository(), PublicationRepository()
    first, second = capture(repository, original, 'shared-id'), capture(other, selected, 'shared-id')
    assert first.run_id == second.run_id and first.checkpoint_ref != second.checkpoint_ref
    for mixed, locator in [(second, first.run_id), (replace(first, tool_ref=second.tool_ref), first.checkpoint_ref.id)]:
        with pytest.raises(RepositoryConflict) as caught:
            assemble_stage2(repository, mixed, fragment_budget=100)
        assert caught.value.code == 'ReadbackConflict' and locator in str(caught.value)
    assert repository.load_attempt(first.run_id) == first.attempt


def test_combined_fragment_budget_error_keeps_input_and_unchanged_attempt(interleaved):
    repository, ready, facts = interleaved[1]
    with pytest.raises(Stage2AssemblyError) as caught:
        assemble_stage2(repository, ready, fragment_budget=48)
    error = caught.value
    assert error.stage == 'occupancy' and error.result.status == 'resource_limit'
    assert error.result.budget == 48 and error.result.required_fragments == len(facts.occupancy.fragments) > 48
    assert error.result.value is None and error.result.exceeded_at.record_source.uri == 'source.gds'
    assert repository.load_attempt(ready.run_id) == ready.attempt and repository.read_terminal(ready.run_id) is None


@pytest.mark.parametrize(('owner', 'section', 'key', 'stage', 'code'), [
    ('formats', 'geometry_capability', 'comparator', 'geometry', 'UnsupportedGeometryComparator'),
    ('physical', 'operators', 'terminal_split/1', 'effective', 'UnsupportedRegionOperator'),
    ('physical', 'operators', 'cross_layer_contact/1', 'local_connectivity', 'UnsupportedLocalContactOperator'),
])
def test_unsupported_operators_preserve_located_issues(tmp_path, owner, section, key, stage, code):
    repository = PublicationRepository()
    root = ready_copy(tmp_path)
    change_owner(root, owner, lambda document: document[section].update({key: 'unavailable/1'}))
    ready = capture(repository, root, 'unknown-operator')
    with pytest.raises(Stage2AssemblyError) as caught:
        assemble_stage2(repository, ready, fragment_budget=100)
    error = caught.value
    issue, = error.result.issues
    assert error.stage == stage and issue.code == code
    assert issue.source.uri == f'tech/{owner}.json' and issue.source.sha256 == sha(root / issue.source.uri)
    assert issue.source.field == '/' + section + '/' + key.replace('/', '~1')
    assert repository.load_attempt(ready.run_id) == ready.attempt and repository.read_terminal(ready.run_id) is None


def test_conflicting_query_keeps_graph_and_diagnostic_without_admitting_the_draft(tmp_path):
    repository = PublicationRepository()
    root = ready_copy(tmp_path)
    rewrite_net_response(root, 'n_lo', [
        ('toy_li', (28, 30, 34, 55)), ('toy_m1', (0, 48, 45, 58)), ('toy_poly', (58, 10, 62, 190)),
    ])
    ready = capture(repository, root, 'conflicting-gate')
    with pytest.raises(Stage2AssemblyError) as caught:
        assemble_stage2(repository, ready, fragment_budget=100)
    error = caught.value
    assert error.stage == 'terminal_relations'
    assert error.result.value is not None and error.result.status == 'error'
    assert len(error.result.value.local.edges) == 8 and len(error.result.value.local.components) == 6
    issue = next(i for i in error.result.issues if i.code == 'ConflictingComponentNets')
    assert issue.source.sha256 == sha(root / issue.source.uri)
    assert repository.load_attempt(ready.run_id) == ready.attempt and repository.read_terminal(ready.run_id) is None
