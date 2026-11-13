"""Independent small terminal-value probes without a captured geometry rebuild."""
from dataclasses import replace
from fractions import Fraction

import pytest

from layauto_v2.domain.circuit import Terminal
from layauto_v2.domain.codec import FrozenMap, canonical_bytes
from layauto_v2.domain.evidence import SourceRef
from layauto_v2.domain.geometry import source_value
from layauto_v2.domain.identifiers import CellId, DeviceId, NetId, identity_value
from layauto_v2.domain.local_connectivity import LocalRef
from layauto_v2.domain.net_annotation import AnnotationRef
from layauto_v2.domain.regions import RegionRef
from layauto_v2.domain.terminal_relations import BODY_PATH_FIELDS, TerminalRef, TerminalRelation, TerminalTarget


def relation(role='D', expected='Y', observed=('Y',), support='established'):
    cell = CellId('LEAF')
    nets = tuple(sorted((NetId(cell, name) for name in observed), key=lambda item: item.id))
    path = None
    if role == 'B':
        values = dict.fromkeys(BODY_PATH_FIELDS)
        values.update(device_id=identity_value(DeviceId(cell, 'MN0')),
                      channel_ref=RegionRef('region', 'c' * 64).to_value(),
                      local_body_node_ref=LocalRef('node', 'd' * 64).to_value(),
                      local_body_component_ref=LocalRef('component', 'e' * 64).to_value(),
                      observed_net_ids=tuple(identity_value(net) for net in nets),
                      evidence_refs=(AnnotationRef('evidence', '0' * 64).to_value(),),
                      chain_status=support, rule_status='satisfied', claim_status='equal',
                      body_candidates=(), rail_candidates=())
        path = FrozenMap(values)
    return TerminalRelation(
        TerminalTarget(TerminalRef('binding', 'a' * 64), DeviceId(cell, 'MN0'), role),
        Terminal(role, NetId(cell, expected), SourceRef('source.cdl', 'b' * 64, line=3)),
        RegionRef('region', 'c' * 64), (LocalRef('node', 'd' * 64),),
        (LocalRef('component', 'e' * 64),), (AnnotationRef('target', 'f' * 64),),
        () if role == 'B' else nets, (AnnotationRef('evidence', '0' * 64),),
        path, nets, support,
    )


@pytest.mark.parametrize(('expected', 'observed', 'support', 'status'), [
    ('Y', ('Y',), 'established', 'equal'),
    ('Y', ('A',), 'established', 'mismatch'),
    ('Y', (), 'established', 'unknown'),
    ('Y', ('A', 'Y'), 'established', 'conflict'),
    ('Y', ('Y',), 'indeterminate', 'indeterminate'),
])
def test_terminal_source_and_observation_have_distinct_statuses(expected, observed, support, status):
    row = relation(expected=expected, observed=observed, support=support)
    assert row.status == status
    assert row.expected.net_id.name == expected
    assert tuple(net.name for net in row.observed_net_ids) == tuple(
        net.name for net in sorted(row.observed_net_ids, key=lambda item: item.id))


def test_shared_gate_retains_two_device_targets_without_owning_the_conductor():
    first = relation(role='G', expected='A', observed=('A',))
    second = replace(first, target=replace(first.target, device_id=DeviceId(first.target.device_id.cell, 'MP0')))
    assert first.node_refs == second.node_refs
    assert first.component_refs == second.component_refs
    assert first.target.ref != second.target.ref
    assert first.status == second.status == 'equal'


def test_body_observation_is_independent_of_unknown_local_component():
    row = relation(role='B', expected='VSS', observed=('VSS',))
    assert not row.local_observed_net_ids
    assert row.context_path is not None
    assert row.status == 'equal'
    with pytest.raises(ValueError):
        replace(row, context_path=None)
    with pytest.raises(ValueError):
        replace(relation(), observed_net_ids=(NetId(CellId('LEAF'), 'A'),))


def test_terminal_constructor_snapshots_caller_sequences_and_nested_context():
    row = relation(role='B', expected='VSS', observed=('VSS',))
    nodes = list(row.node_refs)
    nets = list(row.observed_net_ids)
    raw = dict(row.context_path)
    raw['body_candidates'] = ['first']
    copied = replace(row, node_refs=nodes, observed_net_ids=nets, context_path=FrozenMap(raw))
    before = canonical_bytes(copied.to_value())
    nodes.clear()
    nets.clear()
    raw['body_candidates'].append('changed')
    assert canonical_bytes(copied.to_value()) == before


@pytest.mark.parametrize('mutation', ['map_backing', 'source_number', 'unknown_field', 'retained_list', 'role'])
def test_terminal_serialization_rejects_forged_native_alias_and_field_storage(mutation):
    row = relation(role='B', expected='VSS', observed=('VSS',))
    if mutation == 'map_backing':
        object.__setattr__(row.context_path, '_entries', list(row.context_path._entries))
    elif mutation == 'source_number':
        object.__setattr__(row.expected.source, 'line', True)
    elif mutation == 'unknown_field':
        object.__setattr__(row.target, 'extra', 'ignored')
    elif mutation == 'retained_list':
        object.__setattr__(row, 'node_refs', list(row.node_refs))
    else:
        object.__setattr__(row.target, 'role', 'X')
    with pytest.raises(ValueError):
        row.to_value()


def test_terminal_reference_rejects_unknown_retained_field():
    reference = TerminalRef('binding', 'a' * 64)
    object.__setattr__(reference, 'extra', 'ignored')
    with pytest.raises(ValueError):
        reference.to_value()


@pytest.mark.parametrize('location', ['source', 'terminal', 'device', 'cell', 'net', 'local_ref', 'map'])
def test_cr01_all_retained_leaf_storage_rejects_hidden_mutable_fields(location):
    row = relation(role='B', expected='VSS', observed=('VSS',))
    leaf = {
        'source': row.expected.source, 'terminal': row.expected,
        'device': row.target.device_id, 'cell': row.target.device_id.cell,
        'net': row.expected.net_id, 'local_ref': row.node_refs[0], 'map': row.context_path,
    }[location]
    alias = []
    object.__setattr__(leaf, 'undeclared_extra', alias)
    with pytest.raises(ValueError, match='undeclared retained fields'):
        replace(row)
    with pytest.raises(ValueError, match='undeclared retained fields'):
        row.to_value()


@pytest.mark.parametrize('status_field', ['chain_status', 'rule_status', 'claim_status'])
def test_body_path_status_fields_reject_undeclared_values(status_field):
    row = relation(role='B', expected='VSS', observed=('VSS',))
    path = dict(row.context_path)
    path[status_field] = 'successful_without_support'
    with pytest.raises(ValueError, match='unsupported .* status'):
        replace(row, context_path=FrozenMap(path))


@pytest.mark.parametrize('field_name', ['device_id', 'channel_ref', 'local_body_node_ref',
                                        'local_body_component_ref', 'observed_net_ids', 'evidence_refs'])
def test_body_path_cannot_contradict_the_terminal_identity_or_retained_sources(field_name):
    row = relation(role='B', expected='VSS', observed=('VSS',))
    path = dict(row.context_path)
    path[field_name] = () if field_name.endswith('ids') or field_name == 'evidence_refs' else None
    if field_name == 'evidence_refs':
        path[field_name] = (AnnotationRef('evidence', '9' * 64).to_value(),)
    with pytest.raises(ValueError):
        replace(row, context_path=FrozenMap(path))


@pytest.mark.parametrize(('field_name', 'value'), [
    ('active_enclosure_nm', True), ('tap_body_enclosure_nm', 8),
    ('rail_edge_length_nm', Fraction(-1)), ('active_id', True),
    ('local_body_record_id', 'not_a_sha256'), ('context_claim', ''),
    ('tap_id', 3), ('body_candidates', ('duplicate', 'duplicate')),
    ('rail_candidates', ('non_digest',)),
    ('rail_node_ref', LocalRef('component', 'a' * 64).to_value()),
    ('rail_component_ref', LocalRef('node', 'a' * 64).to_value()),
])
def test_body_path_retains_native_exact_measures_ids_and_typed_rail_refs(field_name, value):
    row = relation(role='B', expected='VSS', observed=('VSS',))
    path = dict(row.context_path)
    path[field_name] = value
    with pytest.raises(ValueError):
        replace(row, context_path=FrozenMap(path))


@pytest.mark.parametrize('mutation', ['missing', 'extra', 'native_number'])
def test_body_association_source_has_closed_native_located_fields(mutation):
    row = relation(role='B', expected='VSS', observed=('VSS',))
    source = dict(source_value(row.expected.source))
    if mutation == 'missing':
        del source['record_index']
    elif mutation == 'extra':
        source['guessed_owner'] = 'context'
    else:
        source['line'] = True
    path = dict(row.context_path)
    path['association_source'] = FrozenMap(source)
    with pytest.raises(ValueError):
        replace(row, context_path=FrozenMap(path))


def test_body_path_enclosure_keeps_signed_exact_fractions():
    row = relation(role='B', expected='VSS', observed=('VSS',))
    path = dict(row.context_path)
    path.update(active_enclosure_nm=Fraction(-1, 20), body_edge_length_nm=Fraction(1, 20),
                rail_node_ref=LocalRef('node', 'a' * 64).to_value(),
                association_source=source_value(row.expected.source))
    copied = replace(row, context_path=FrozenMap(path))
    assert copied.context_path['active_enclosure_nm'] == Fraction(-1, 20)


def test_initialized_default_fields_cannot_be_deleted_to_use_class_fallback():
    row = relation()
    target = row.target
    assert next(member for member in target.__dataclass_fields__.values()
                if member.name == 'schema_version').init is True
    object.__delattr__(target, 'schema_version')
    assert target.schema_version == type(target).schema_version
    with pytest.raises(ValueError, match='missing or undeclared retained fields'):
        target.to_value()
    with pytest.raises(ValueError, match='missing or undeclared retained fields'):
        row.to_value()
