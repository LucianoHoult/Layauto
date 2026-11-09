"""Closed W011 public reconstruction checks; same-capture and immutable boundary."""
from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, replace
from fractions import Fraction
from pathlib import Path

import pytest

from layauto_v2.domain.channel_identity import ChannelRef, RationalRect
from layauto_v2.domain.codec import canonical_bytes, decode
from layauto_v2.domain.evidence import SourceRef
from layauto_v2.derive.channel_identity import build_channel_identity_draft
from layauto_v2.normalization.channel_identity import build_channel_identity
from layauto_v2.normalization.channel_identity_codec import decode_record, encode_record, record_digest
from w005_cases import FIXTURE
from w007_cases import mutable, ready_copy
from w011_cases import build, change_cdl, unchecked_replace


@pytest.fixture(scope='module')
def accepted():
    result = build()
    assert result.status == 'success'
    return result


def public_records(result):
    draft = result.value
    return (draft.ref, draft.seeds[0], draft.seeds[0].rectangle, draft.locations[0],
            draft.locations[0].intersections[0], draft.associations[0], draft.topology[0],
            draft.measurements[0], draft.measurements[0].evaluations[0], draft.comparisons[0],
            draft, result)


def test_all_public_records_roundtrip_are_frozen_and_rebuild_stably(accepted):
    for record in public_records(accepted):
        wire = encode_record(record)
        rebuilt = decode_record(wire)
        assert rebuilt == record and encode_record(rebuilt) == wire
        assert record_digest(rebuilt) == record_digest(record)
        with pytest.raises(FrozenInstanceError): record.foreign = []
    draft = accepted.value
    assert build_channel_identity_draft(draft.local, draft.source, draft.seeds, draft.derived) == draft
    assert replace(accepted) == accepted


@pytest.mark.parametrize('change', (
    'missing_seed', 'extra_seed', 'missing_location', 'missing_intersection', 'missing_association',
    'wrong_coverage', 'missing_measurement', 'missing_evaluation', 'extra_evaluation',
    'false_count', 'false_length', 'false_width', 'foreign_channel', 'foreign_fin',
    'missing_comparison', 'false_comparison', 'missing_topology', 'wrong_source_node',
    'false_issue',
))
def test_public_draft_reconstructs_complete_correlated_tables(accepted, change):
    draft = accepted.value
    with pytest.raises(ValueError):
        if change == 'missing_seed': replace(draft, seeds=draft.seeds[1:])
        elif change == 'extra_seed': replace(draft, seeds=draft.seeds + draft.seeds[:1])
        elif change == 'missing_location': replace(draft, locations=draft.locations[1:])
        elif change == 'missing_intersection':
            replace(draft, locations=(replace(draft.locations[0], intersections=()),) + draft.locations[1:])
        elif change == 'missing_association': replace(draft, associations=draft.associations[1:])
        elif change == 'wrong_coverage':
            replace(draft, associations=(replace(draft.associations[0], coverage_fraction=Fraction(1, 2)),) + draft.associations[1:])
        elif change == 'missing_measurement': replace(draft, measurements=draft.measurements[1:])
        elif change == 'missing_evaluation':
            row = draft.measurements[0]
            replace(draft, measurements=(replace(row, evaluations=row.evaluations[1:]),) + draft.measurements[1:])
        elif change == 'extra_evaluation':
            row = draft.measurements[0]
            replace(draft, measurements=(replace(row, evaluations=row.evaluations + row.evaluations[:1]),) + draft.measurements[1:])
        elif change == 'false_count':
            replace(draft, measurements=(replace(draft.measurements[0], count=999),) + draft.measurements[1:])
        elif change == 'false_length':
            replace(draft, measurements=(replace(draft.measurements[0], length_nm=Fraction(5)),) + draft.measurements[1:])
        elif change == 'false_width':
            row = draft.measurements[0]
            evaluation = replace(row.evaluations[0], width_nm=Fraction(3))
            replace(draft, measurements=(replace(row, evaluations=(evaluation,) + row.evaluations[1:]),) + draft.measurements[1:])
        elif change == 'foreign_channel':
            row = draft.measurements[0]
            replace(draft, measurements=(replace(row, channel_ref=replace(row.channel_ref, sha256='e' * 64)),) + draft.measurements[1:])
        elif change == 'foreign_fin':
            row = draft.measurements[0]
            evaluation = replace(row.evaluations[0], fin_id=replace(row.evaluations[0].fin_id, sha256='f' * 64))
            replace(draft, measurements=(replace(row, evaluations=(evaluation,) + row.evaluations[1:]),) + draft.measurements[1:])
        elif change == 'missing_comparison': replace(draft, comparisons=draft.comparisons[1:])
        elif change == 'false_comparison':
            replace(draft, comparisons=(replace(draft.comparisons[0], measured=Fraction(123)),) + draft.comparisons[1:])
        elif change == 'missing_topology': replace(draft, topology=draft.topology[1:])
        elif change == 'wrong_source_node':
            row = draft.topology[0]
            replace(draft, topology=(replace(row, source_node=row.drain_node),) + draft.topology[1:])
        else:
            from layauto_v2.domain.results import EvidenceIssue
            replace(draft, issues=(EvidenceIssue('unsupported', 'Invented', 'invented failure',
                                               draft.local.binding.physical.sources[0]),))


def test_all_topology_refs_reach_actual_ordered_regions_and_shared_gate(accepted):
    draft = accepted.value
    graph = draft.local
    nodes = {node.ref: node for node in graph.nodes}
    components = {component.ref: set(component.members) for component in graph.components}
    assert len(draft.topology) == 2
    assert draft.topology[0].gate_nodes == draft.topology[1].gate_nodes
    assert len(draft.topology[0].gate_nodes) == 1
    for row in draft.topology:
        assert nodes[row.source_node].region.role == 'S'
        assert nodes[row.drain_node].region.role == 'D'
        assert nodes[row.source_node].region.owner_id == nodes[row.drain_node].region.owner_id
        assert row.source_node in components[row.source_component]
        assert row.drain_node in components[row.drain_component]
        assert row.source_component != row.drain_component
        assert all(nodes[ref].layer == 'POLY' for ref in row.gate_nodes)
        assert set(row.gate_nodes) <= set().union(*(components[ref] for ref in row.gate_components))
    assert len({row.source_node for row in draft.topology} | {row.drain_node for row in draft.topology}) == 4


def test_public_results_reject_cross_capture_semantic_or_graph_substitution(accepted, tmp_path):
    root = ready_copy(tmp_path)
    change_cdl(root, 'source', 'NFIN=5', 'NFIN=4')
    other = build(root)
    for changes in ({'semantic': other.semantic}, {'input': other.input}, {'value': other.value}):
        with pytest.raises(ValueError): replace(accepted, **changes)
    for changes in ({'status': 'error'}, {'value': None}, {'completed': ()}, {'input': None}):
        with pytest.raises(ValueError): replace(accepted, **changes)
    with pytest.raises(ValueError): build_channel_identity(accepted.input.input)


def test_derived_source_role_is_bound_to_actual_capture(accepted):
    draft = accepted.value
    for source in (SourceRef('foreign-derived.json', draft.derived.sources[0].sha256),
                   draft.local.binding.physical.sources[0]):
        with pytest.raises(ValueError):
            alternate = build_channel_identity_draft(draft.local, draft.source, draft.seeds,
                                                      replace(draft.derived, sources=(source,)))
            replace(accepted, value=alternate)


def test_native_collection_snapshots_detach_all_caller_aliases(accepted):
    draft = accepted.value
    names = ('seeds', 'locations', 'associations', 'topology', 'measurements', 'fin_relations', 'comparisons', 'issues')
    values = {name: list(getattr(draft, name)) for name in names}
    rebuilt = replace(draft, **values)
    for value in values.values(): value.clear()
    assert rebuilt == draft and all(type(getattr(rebuilt, name)) is tuple for name in names)
    location = draft.locations[0]
    intersections = list(location.intersections)
    copied = replace(location, intersections=intersections)
    intersections.clear()
    assert copied == location
    class AdversarialList(list):
        def __iter__(self):
            raise AssertionError('foreign collection iterated before type rejection')
    with pytest.raises(ValueError): replace(draft, seeds=AdversarialList(draft.seeds))


class MutableText(str):
    pass


class EqualObject:
    def __eq__(self, other): return True
    def __ne__(self, other): return False


@pytest.mark.parametrize('where', ('new_literal', 'seed_identity', 'old_local_literal', 'retained_source', 'foreign_scalar'))
def test_foreign_mutable_aliases_rejected_before_codec_can_copy_them(accepted, where):
    draft = accepted.value
    if where == 'new_literal': value = unchecked_replace(draft.measurements[0].evaluations[0], status=MutableText('outside'))
    elif where == 'seed_identity':
        seed = draft.seeds[0]
        value = unchecked_replace(seed, device_id=unchecked_replace(seed.device_id, name=MutableText(seed.device_id.name)))
    elif where == 'old_local_literal':
        value = unchecked_replace(accepted, input=unchecked_replace(accepted.input, status=MutableText('success')))
    elif where == 'retained_source':
        value = unchecked_replace(draft.derived, kind=MutableText('derived'))
        value = unchecked_replace(draft, derived=value)
    else: value = unchecked_replace(draft, schema_version=EqualObject())
    with pytest.raises(ValueError): encode_record(value)


def test_wire_is_closed_versioned_and_requires_every_field(accepted):
    record = accepted.value.measurements[0]
    original = encode_record(record)
    for key in [field.name for field in fields(record)]:
        tree = mutable(decode(original))
        del tree['record']['fields'][key]
        with pytest.raises(ValueError): decode_record(canonical_bytes(tree))
    tree = mutable(decode(original))
    tree['record']['fields']['foreign'] = {'scalar': True}
    with pytest.raises(ValueError): decode_record(canonical_bytes(tree))
    for wire in (original + b'\n', b'{}', canonical_bytes({'wire_schema': 'foreign/1', 'record': {}})):
        with pytest.raises(ValueError): decode_record(wire)


def test_new_modules_have_named_dependency_and_io_guards():
    import layauto_v2
    root = Path(layauto_v2.__file__).resolve().parent
    pure = ('domain/channel_identity.py', 'annotation/channel_identity.py',
            'derive/fin_count.py', 'derive/channel_identity.py')
    for relative in pure + ('normalization/channel_identity.py', 'normalization/channel_identity_codec.py'):
        source = ast.parse((root / relative).read_text())
        forbidden = ('legacy_mvp', 'tests', 'subprocess', 'pathlib', 'os', 'io',
                     'layauto_v2.pipeline', 'layauto_v2.repository', 'layauto_v2.transactions')
        if relative in pure:
            forbidden += ('layauto_v2.normalization', 'layauto_v2.importers')
        if relative.startswith('domain/'):
            forbidden += ('layauto_v2.state', 'layauto_v2.annotation', 'layauto_v2.derive')
        for node in ast.walk(source):
            imports = [alias.name for alias in node.names] if isinstance(node, ast.Import) else (
                [node.module or ''] if isinstance(node, ast.ImportFrom) else [])
            assert not any(name.startswith(forbidden) for name in imports), (relative, imports)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in ('open', 'hash', 'eval', 'exec'), (relative, node.lineno)


@pytest.mark.parametrize('owner', ('physical', 'derived', 'drawn', 'formats', 'rules'))
def test_complete_input_chain_rejects_grouped_payload_forgery(accepted, owner):
    from test_w008_capture_binding import forged_payload
    local = accepted.input
    effective, geometry = local.input, local.input.input
    source = geometry.input
    def mutate(tech):
        if owner == 'physical': tech[owner]['fin_count_profile']['effective_fin_operator'] = 'forged'
        elif owner == 'derived': tech[owner]['derived_registry'][0]['trim_operator'] = 'identity'
        elif owner == 'drawn': tech[owner]['layers'][0]['purpose'] = 'forged'
        elif owner == 'formats': tech[owner]['unit_scale_contract']['canonical_tick_nm'] = 2
        else: tech[owner]['rules'][4]['parameters']['enclosure_nm'] = 2
    parsed = forged_payload(source.parse, 'tech', mutate)
    semantic = unchecked_replace(source.semantic_input, parse=parsed)
    input = unchecked_replace(source, semantic_input=semantic)
    borrowed_geometry = unchecked_replace(geometry, input=input, completed=parsed.completed)
    borrowed_effective = unchecked_replace(effective, input=borrowed_geometry, completed=parsed.completed)
    borrowed_local = unchecked_replace(local, input=borrowed_effective, completed=parsed.completed)
    with pytest.raises(ValueError): build_channel_identity(borrowed_local)
