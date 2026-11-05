"""W010 public graph completeness, provenance, immutable and closed-wire checks."""
from dataclasses import FrozenInstanceError, fields, replace
from fractions import Fraction
import os
from pathlib import Path
import subprocess
import sys

import pytest

from layauto_v2.domain.codec import canonical_bytes, decode
from layauto_v2.domain.evidence import SourceRef
from layauto_v2.domain.geometry import GeometryRef
from layauto_v2.domain.local_connectivity import ContactComponent, ContactEdge, LocalRef
from layauto_v2.normalization import build_effective_geometry, build_geometry, geometry_from_parse_result
from layauto_v2.normalization.local_connectivity import LocalConnectivityResult, build_local_connectivity
from layauto_v2.normalization.local_connectivity_codec import decode_record, encode_record, record_digest
from layauto_v2.state.local_connectivity import build_local_connectivity_draft
from test_w008_capture_binding import forged_payload
from w005_cases import FIXTURE
from w007_cases import mutable, read


@pytest.fixture(scope='module')
def accepted():
    return build_local_connectivity(build_effective_geometry(
        build_geometry(geometry_from_parse_result(read(FIXTURE)))))


def public_records(result):
    draft = result.value
    return (draft.ref, draft.binding, draft.nodes[0], draft.edges[0],
            draft.audits[0], draft.components[0], draft, result)


def test_all_new_public_records_roundtrip_with_stable_digests_and_frozen_fields(accepted):
    assert accepted.status == 'success'
    for record in public_records(accepted):
        wire = encode_record(record)
        rebuilt = decode_record(wire)
        assert rebuilt == record
        assert encode_record(rebuilt) == wire
        assert record_digest(rebuilt) == record_digest(record)
        with pytest.raises(FrozenInstanceError):
            record.foreign = []
    draft = accepted.value
    assert build_local_connectivity_draft(draft.effective, draft.binding.rules) == draft


@pytest.mark.parametrize('change', (
    'missing_node', 'duplicate_node', 'missing_edge', 'duplicate_edge', 'extra_edge',
    'missing_audit', 'duplicate_audit', 'false_audit', 'wrong_margin', 'foreign_endpoint',
    'missing_component', 'duplicate_component', 'false_union', 'drop_isolated',
    'foreign_unit', 'foreign_effective', 'foreign_binding', 'foreign_node_geometry',
))
def test_public_draft_rejects_incomplete_or_forged_topology_and_audit(accepted, change):
    draft = accepted.value
    with pytest.raises(ValueError):
        if change == 'missing_node': replace(draft, nodes=draft.nodes[1:])
        elif change == 'duplicate_node': replace(draft, nodes=draft.nodes + draft.nodes[:1])
        elif change == 'missing_edge': replace(draft, edges=draft.edges[1:])
        elif change == 'duplicate_edge': replace(draft, edges=draft.edges + draft.edges[:1])
        elif change == 'extra_edge':
            endpoints = tuple(sorted((n.ref for n in draft.nodes if n.layer in ('BODY_N', 'BODY_P')),
                                     key=lambda ref: ref.sha256))
            edge = ContactEdge('same_layer', endpoints, draft.binding.ref, None)
            replace(draft, edges=tuple(sorted(draft.edges + (edge,), key=lambda item: item.ref.sha256)))
        elif change == 'missing_audit': replace(draft, audits=draft.audits[1:])
        elif change == 'duplicate_audit': replace(draft, audits=draft.audits + draft.audits[:1])
        elif change == 'false_audit':
            replace(draft, audits=(replace(draft.audits[0], status='violation'),) + draft.audits[1:])
        elif change == 'wrong_margin':
            replace(draft, audits=(replace(draft.audits[0], margin_ticks=Fraction(1, 2)),) + draft.audits[1:])
        elif change == 'foreign_endpoint':
            edge = draft.edges[0]
            ends = tuple(sorted((edge.endpoints[0], LocalRef('node', 'f' * 64)), key=lambda ref: ref.sha256))
            replace(draft, edges=(replace(edge, endpoints=ends),) + draft.edges[1:])
        elif change == 'missing_component': replace(draft, components=draft.components[1:])
        elif change == 'duplicate_component': replace(draft, components=draft.components + draft.components[:1])
        elif change == 'false_union':
            all_members = tuple(sorted((n.ref for n in draft.nodes), key=lambda ref: ref.sha256))
            replace(draft, components=(ContactComponent(all_members, draft.binding.ref),))
        elif change == 'drop_isolated':
            replace(draft, components=tuple(c for c in draft.components if len(c.members) > 1))
        elif change == 'foreign_unit':
            replace(draft, binding=replace(draft.binding, unit_ref=GeometryRef('unit', 'e' * 64)))
        elif change == 'foreign_effective':
            replace(draft, binding=replace(draft.binding, effective_ref=replace(draft.effective.ref, sha256='e' * 64)))
        elif change == 'foreign_binding':
            node = replace(draft.nodes[0], binding_ref=LocalRef('operators', 'd' * 64))
            replace(draft, nodes=(node,) + draft.nodes[1:])
        else:
            node = draft.nodes[0]
            region = replace(node.region, unit_ref=GeometryRef('unit', 'd' * 64))
            replace(draft, nodes=(replace(node, region=region),) + draft.nodes[1:])


def test_rules_payload_and_actual_source_role_must_match_this_capture(accepted):
    draft = accepted.value
    rules = draft.binding.rules
    wrong_source = draft.binding.drawn.sources[0]
    for source in (SourceRef('foreign-rules.json', rules.sources[0].sha256), wrong_source):
        # A neutral draft may describe a different evidence origin, but a
        # capture-bound public success must never certify that as this input.
        with pytest.raises(ValueError):
            alternate = build_local_connectivity_draft(draft.effective, replace(rules, sources=(source,)))
            replace(accepted, value=alternate)
    assert rules.payload == accepted.input.input.input.value['tech']['rules']
    tech = next(record for record in accepted.completed if record.kind == 'tech')
    assert rules.sources == (tech.sources[6],)


def unchecked_replace(record, **changes):
    """Model an externally tampered prior DTO; W010 must authenticate it again."""
    result = object.__new__(type(record))
    for field in fields(record):
        object.__setattr__(result, field.name, changes.get(field.name, getattr(record, field.name)))
    return result


@pytest.mark.parametrize('owner', ('rules', 'physical', 'drawn', 'formats'))
def test_w010_reauthenticates_grouped_payload_forgery_against_retained_bytes(accepted, owner):
    effective = accepted.input
    geometry = effective.input
    source_input = geometry.input
    parsed = source_input.parse
    def mutate(tech):
        if owner == 'rules': tech[owner]['rules'][4]['parameters']['enclosure_nm'] = 2
        elif owner == 'physical': tech[owner]['operators']['same_layer_contact/1'] = 'forged meaning'
        elif owner == 'drawn': tech[owner]['layers'][0]['purpose'] = 'forged-purpose'
        else: tech[owner]['unit_scale_contract']['canonical_tick_nm'] = 2
    forged = forged_payload(parsed, 'tech', mutate)
    semantic = unchecked_replace(source_input.semantic_input, parse=forged)
    borrowed = unchecked_replace(source_input, semantic_input=semantic)
    borrowed_geometry = unchecked_replace(geometry, input=borrowed, completed=forged.completed)
    borrowed_effective = unchecked_replace(effective, input=borrowed_geometry, completed=forged.completed)
    with pytest.raises(ValueError):
        build_local_connectivity(borrowed_effective)
    with pytest.raises(ValueError):
        LocalConnectivityResult('success', accepted.value, (), forged.completed, borrowed_effective)


def test_public_collections_take_one_snapshot_and_do_not_keep_caller_aliases(accepted):
    draft = accepted.value
    collections = {name: list(getattr(draft, name)) for name in ('nodes', 'edges', 'audits', 'components')}
    copied = replace(draft, **collections)
    for value in collections.values(): value.clear()
    assert copied == draft
    edge = draft.edges[0]
    ends = list(edge.endpoints)
    copied_edge = replace(edge, endpoints=ends)
    ends.clear()
    assert copied_edge == edge and type(copied_edge.endpoints) is tuple
    component = draft.components[0]
    members = list(component.members)
    copied_component = replace(component, members=members)
    members.clear()
    assert copied_component == component and type(copied_component.members) is tuple


class MutableText(str):
    pass


class EqualMutable:
    def __eq__(self, other): return True
    def __ne__(self, other): return False


@pytest.mark.parametrize('index,field', ((0, 'kind'), (1, 'scope'), (1, 'top'), (2, 'layer'),
                                       (3, 'kind'), (4, 'status'), (4, 'layer'),
                                       (5, 'schema_version'), (6, 'schema_version'),
                                       (7, 'status'), (7, 'schema_version')))
@pytest.mark.parametrize('kind', ('text_subclass', 'equal_object'))
def test_new_literal_fields_reject_mutable_equal_objects(accepted, index, field, kind):
    record = public_records(accepted)[index]
    original = getattr(record, field)
    value = MutableText(original) if kind == 'text_subclass' else EqualMutable()
    value.mutable = []
    with pytest.raises(ValueError): replace(record, **{field: value})


@pytest.mark.parametrize('where', ('node_region', 'binding_owner', 'effective_input', 'old_literal'))
def test_nested_foreign_and_mutable_aliases_are_rejected_before_encoding_copies_them(accepted, where):
    draft = accepted.value
    if where == 'node_region':
        borrowed = unchecked_replace(draft.nodes[0].region, role=MutableText(draft.nodes[0].region.role))
        value = unchecked_replace(draft.nodes[0], region=borrowed)
    elif where == 'binding_owner':
        borrowed = unchecked_replace(draft.binding.rules, kind=MutableText('rules'))
        value = unchecked_replace(draft.binding, rules=borrowed)
    elif where == 'effective_input':
        value = unchecked_replace(accepted, input=unchecked_replace(accepted.input, status=MutableText('success')))
    else:
        base = draft.effective.base
        borrowed = unchecked_replace(base, schema_version=MutableText(base.schema_version))
        value = unchecked_replace(draft, effective=unchecked_replace(draft.effective, base=borrowed))
    with pytest.raises(ValueError): encode_record(value)


@pytest.mark.parametrize('margin', (True, 1, 1.0, MutableText('1')))
def test_audit_margin_is_an_exact_native_fraction(accepted, margin):
    with pytest.raises(ValueError): replace(accepted.value.audits[0], margin_ticks=margin)


def test_fraction_subclass_and_mutable_fraction_components_do_not_enter_audit(accepted):
    class MutableInt(int): pass
    value = Fraction(1)
    value._numerator = MutableInt(1)
    value._numerator.mutable = []
    with pytest.raises(ValueError): replace(accepted.value.audits[0], margin_ticks=value)


def test_foreign_metaclass_equality_cannot_impersonate_a_registered_record(accepted):
    comparisons = []
    class EqualType(type):
        def __eq__(cls, other):
            comparisons.append(other)
            return True
        __hash__ = type.__hash__
    ForeignNode = EqualType('ContactNode', (), {})
    foreign = ForeignNode()
    foreign.layer = 'LI'
    foreign.mutable = []
    with pytest.raises(ValueError):
        replace(accepted.value, nodes=(foreign,) + accepted.value.nodes[1:])
    with pytest.raises(ValueError):
        encode_record(unchecked_replace(accepted.value, nodes=(foreign,) + accepted.value.nodes[1:]))
    assert comparisons == []


@pytest.mark.parametrize('entry', ('draft', 'result'))
@pytest.mark.parametrize('collection', ('nodes', 'edges', 'audits', 'components'))
def test_nested_public_wire_rejects_omitted_topology_or_audit(accepted, entry, collection):
    record = accepted.value if entry == 'draft' else accepted
    tree = mutable(decode(encode_record(record)))
    graph = tree['record'] if entry == 'draft' else tree['record']['fields']['value']
    graph['fields'][collection]['tuple'].pop()
    with pytest.raises(ValueError): decode_record(canonical_bytes(tree))


@pytest.mark.parametrize('record_index', range(8))
def test_each_new_record_rejects_unknown_missing_and_null_wire_fields(accepted, record_index):
    record = public_records(accepted)[record_index]
    original = encode_record(record)
    tree = mutable(decode(original))
    field_names = tuple(tree['record']['fields'])
    for name in field_names:
        missing = mutable(decode(original))
        del missing['record']['fields'][name]
        with pytest.raises(ValueError): decode_record(canonical_bytes(missing))
        bad = mutable(decode(original))
        bad['record']['fields'][name] = {'scalar': None}
        # None is the valid absent connector for same-layer edges only; the
        # selected fixture edge is a connector and all other fields required.
        if getattr(record, name) is not None:
            with pytest.raises(ValueError): decode_record(canonical_bytes(bad))
    extra = mutable(decode(original))
    extra['record']['fields']['foreign'] = {'scalar': 1}
    with pytest.raises(ValueError): decode_record(canonical_bytes(extra))
    for malformed in (original + b'\n', b'{}', canonical_bytes({'wire_schema': 'foreign/1', 'record': {}})):
        with pytest.raises(ValueError): decode_record(malformed)


@pytest.mark.parametrize('change', ('outer', 'scalar_collection', 'foreign_nested', 'wrong_tuple'))
def test_wire_tag_shapes_are_explicitly_validated(accepted, change):
    tree = mutable(decode(encode_record(accepted.value.nodes[0])))
    if change == 'outer': tree['extra'] = True
    elif change == 'scalar_collection': tree['record']['fields']['layer'] = {'scalar': []}
    elif change == 'foreign_nested': tree['record']['fields']['region'] = {'effective_record': b'not a wire'}
    else: tree['record']['fields']['binding_ref'] = {'tuple': 7}
    with pytest.raises(ValueError): decode_record(canonical_bytes(tree))


def test_false_success_errors_and_wrong_input_types_are_rejected(accepted):
    for changes in ({'value': None}, {'status': 'error'}, {'completed': ()}, {'input': None}):
        with pytest.raises(ValueError): replace(accepted, **changes)
    with pytest.raises(ValueError): build_local_connectivity(accepted.input.input)


def test_reconstruction_identity_is_stable_across_python_hash_seeds(accepted):
    script = '''
from pathlib import Path
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import build_geometry, geometry_from_parse_result, build_effective_geometry, build_local_connectivity
from layauto_v2.normalization.local_connectivity_codec import record_digest
r = build_local_connectivity(build_effective_geometry(build_geometry(geometry_from_parse_result(read_inputs(Path(%r))))))
print(record_digest(r), r.value.ref.sha256, r.value.semantic_digest)
''' % str(FIXTURE / 'site_config.yaml')
    expected = ' '.join((record_digest(accepted), accepted.value.ref.sha256, accepted.value.semantic_digest))
    for seed in ('1', '97'):
        result = subprocess.run([sys.executable, '-B', '-c', script], cwd=Path.cwd(),
                                env=dict(os.environ, PYTHONHASHSEED=seed), capture_output=True, text=True, check=True)
        assert result.stdout.strip() == expected
