"""Public constructor/wire and captured-owner adversarial checks for W009."""
from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import os
from pathlib import Path
import subprocess
import sys
from collections.abc import Mapping
from fractions import Fraction

import pytest

from layauto_v2.domain.codec import canonical_bytes, decode
from layauto_v2.domain.evidence import SourceFile, SourceRef
from layauto_v2.domain.geometry import GeometryRecordId, GeometryRef, Rect
from layauto_v2.domain.regions import RegionRef
from layauto_v2.normalization import geometry_input
from layauto_v2.normalization import from_parse_result
from layauto_v2.normalization.effective import EffectiveGeometryResult, build_effective_geometry
from layauto_v2.normalization.effective_codec import decode_record, encode_record, record_digest
from layauto_v2.normalization.geometry import build_geometry
from layauto_v2.normalization.geometry_input import GeometryInputError, geometry_from_parse_result
from layauto_v2.state import regions
from layauto_v2.state.regions import build_effective_draft
from test_w008_capture_binding import forged_payload
from w005_cases import FIXTURE
from w007_cases import mutable, read
from w007_cases import ready_copy
from w009_cases import change_owner
from test_w008_geometry_wire import replace_input


@pytest.fixture(scope='module')
def accepted():
    return build_effective_geometry(build_geometry(geometry_from_parse_result(read(FIXTURE))))


def test_closed_records_roundtrip_and_no_aliases(accepted):
    draft = accepted.value
    row = draft.records[0]
    region = row.regions[0]
    values = [accepted, draft, draft.operators, row, region, region.pieces[0], region.ref]
    for value in values:
        wire = encode_record(value)
        rebuilt = decode_record(wire)
        assert rebuilt == value
        assert encode_record(rebuilt) == wire
        assert record_digest(rebuilt) == record_digest(value)
        with pytest.raises(FrozenInstanceError):
            value.unexpected = 'mutation'
    rows = list(draft.records)
    rebuilt = replace(draft, records=rows)
    rows.clear()
    assert rebuilt == draft
    rectangles = list(region.rectangles)
    sources = list(region.contributors)
    rebuilt_region = replace(region, rectangles=rectangles, contributors=sources)
    rectangles.clear()
    sources.clear()
    assert rebuilt_region == region
    payload = mutable(draft.physical.payload)
    copied = replace(draft.physical, payload=payload)
    payload['operators']['rectangle_set_difference/1'] = 'caller mutation'
    assert copied == draft.physical


@pytest.mark.parametrize('change', ['missing', 'duplicate', 'foreign_record', 'unit', 'operator',
                                    'foreign_source', 'omit_region', 'duplicate_region', 'extra_region',
                                    'geometry', 'schema', 'physical_owner', 'drawn_owner'])
def test_aggregate_rejects_incomplete_or_foreign_regions(accepted, change):
    draft = accepted.value
    row = draft.records[0]
    region = row.regions[0]
    with pytest.raises(ValueError):
        if change == 'missing':
            replace(draft, records=draft.records[1:])
        elif change == 'duplicate':
            replace(draft, records=draft.records + draft.records[:1])
        elif change == 'foreign_record':
            replace(draft, records=(replace(row, record_id=GeometryRecordId('1' * 64)),) + draft.records[1:])
        elif change == 'unit':
            replace(draft, records=(replace(row, unit_ref=GeometryRef('unit', '1' * 64)),) + draft.records[1:])
        elif change == 'operator':
            replace(draft, records=(replace(row, operator_ref=RegionRef('operators', '1' * 64)),) + draft.records[1:])
        elif change == 'foreign_source':
            replace(draft, records=(replace(row, contributors=(GeometryRecordId('2' * 64),)),) + draft.records[1:])
        elif change == 'omit_region':
            replace(draft, records=(replace(row, regions=()),) + draft.records[1:])
        elif change == 'duplicate_region':
            replace(draft, records=(replace(row, regions=row.regions + row.regions[:1]),) + draft.records[1:])
        elif change == 'extra_region':
            extra = replace(region, rectangles=(Rect(-7, -7, -2, -2),))
            replace(draft, records=(replace(row, regions=row.regions + (extra,)),) + draft.records[1:])
        elif change == 'geometry':
            wrong = replace(region, rectangles=(Rect(-1, -1, 150, 199),))
            replace(draft, records=(replace(row, regions=(wrong,) + row.regions[1:]),) + draft.records[1:])
        elif change == 'schema':
            replace(draft, schema_version='foreign/1')
        elif change == 'physical_owner':
            ref = draft.physical.sources[0]
            evidence = replace(draft.physical, sources=(SourceRef('foreign.json', ref.sha256),))
            wrong = replace(draft, operators=replace(draft.operators, physical=evidence))
            replace(accepted, value=wrong)
        else:
            ref = draft.operators.drawn.sources[0]
            evidence = replace(draft.operators.drawn, sources=(SourceRef('foreign.json', ref.sha256),))
            replace(draft, operators=replace(draft.operators, drawn=evidence))


@pytest.mark.parametrize('change', ['no_value', 'bad_status', 'error_on_valid', 'issues', 'facts', 'schema'])
def test_result_discriminators_and_facts_are_enforced(accepted, change):
    with pytest.raises(ValueError):
        if change == 'no_value': replace(accepted, value=None)
        elif change == 'bad_status': replace(accepted, status='complete')
        elif change == 'error_on_valid': replace(accepted, status='error', value=None)
        elif change == 'issues': replace(accepted, issues=('invented',))
        elif change == 'facts': replace(accepted, completed=accepted.completed[1:])
        else: replace(accepted, schema_version='foreign/1')


def test_grouped_physical_payload_forgery_cannot_enter_success(accepted):
    def mutate(doc):
        doc['physical']['operators']['rectangle_set_difference/1'] = 'bbox only'
    forged = forged_payload(accepted.input.input.parse, 'tech', mutate)
    with pytest.raises(GeometryInputError):
        geometry_from_parse_result(forged)
    tree = mutable(decode(encode_record(accepted)))
    captured = mutable(decode(tree['record']['fields']['input']['geometry_record']))
    assert replace_input(captured, from_parse_result(forged))
    tree['record']['fields']['input']['geometry_record'] = canonical_bytes(captured)
    with pytest.raises(GeometryInputError):
        decode_record(canonical_bytes(tree))


@pytest.mark.parametrize('target', ['state', 'adapter'])
@pytest.mark.parametrize('failure', [RuntimeError('unexpected'), ValueError('unexpected value'),
                                    TypeError('unexpected type'), KeyError('unexpected key'),
                                    KeyboardInterrupt(), SystemExit(17)])
def test_builder_unexpected_exception_identity(accepted, monkeypatch, target, failure):
    def broken(*args, **kwargs):
        raise failure
    if target == 'state':
        monkeypatch.setattr(regions, 'slab_difference', broken)
    else:
        monkeypatch.setattr('layauto_v2.normalization.effective.build_effective_draft', broken)
    with pytest.raises(type(failure)) as caught:
        build_effective_geometry(accepted.input)
    assert caught.value is failure


@pytest.mark.parametrize('failure', [RuntimeError('decoder bug'), ValueError('decoder bug value'),
                                    TypeError('decoder bug type'), KeyError('decoder bug key'),
                                    KeyboardInterrupt(), SystemExit(23)])
def test_nested_capture_decoder_unexpected_exception_identity(accepted, monkeypatch, failure):
    wire = encode_record(accepted)
    def broken(*args, **kwargs):
        raise failure
    monkeypatch.setattr(geometry_input, 'load_document', broken)
    with pytest.raises(type(failure)) as caught:
        decode_record(wire)
    assert caught.value is failure


@pytest.mark.parametrize('enclosing', ['draft', 'result'])
@pytest.mark.parametrize('failure', [RuntimeError('algorithm bug'), ValueError('algorithm bug value'),
                                    TypeError('algorithm bug type'), KeyError('algorithm bug key'),
                                    AttributeError('algorithm bug attribute'), IndexError('algorithm bug index'),
                                    KeyboardInterrupt(), SystemExit(29)])
def test_neutral_aggregate_decode_preserves_algorithm_exception_identity(accepted, monkeypatch, enclosing, failure):
    wire = encode_record(accepted.value if enclosing == 'draft' else accepted)
    def broken(*args, **kwargs):
        raise failure
    monkeypatch.setattr(regions, 'slab_difference', broken)
    with pytest.raises(type(failure)) as caught:
        decode_record(wire)
    assert caught.value is failure


@pytest.mark.parametrize('change', ['outer', 'fields', 'nested', 'scalar_collection', 'wrong_type'])
def test_closed_wire_rejects_nested_malformations(accepted, change):
    tree = mutable(decode(encode_record(accepted.value.records[0].regions[0])))
    if change == 'outer': tree['extra'] = True
    elif change == 'fields': tree['record']['fields']['extra'] = {'scalar': 1}
    elif change == 'nested': tree['record']['fields']['unit_ref']['extra'] = True
    elif change == 'scalar_collection': tree['record']['fields']['role'] = {'scalar': []}
    else: tree['record']['fields']['unit_ref'] = {'scalar': 'foreign'}
    with pytest.raises(ValueError):
        decode_record(canonical_bytes(tree))


def test_nested_result_wire_rejects_missing_region(accepted):
    tree = mutable(decode(encode_record(accepted)))
    rows = tree['record']['fields']['value']['fields']['records']['tuple']
    rows.pop()
    with pytest.raises(ValueError):
        decode_record(canonical_bytes(tree))


def test_public_builder_requires_w008_success(accepted):
    with pytest.raises(ValueError):
        build_effective_geometry(accepted.input.input)
    with pytest.raises(ValueError):
        EffectiveGeometryResult('success', accepted.value, (), accepted.completed, None)


def test_reconstruction_is_stable_across_process_hash_seeds(accepted):
    script = '''
from pathlib import Path
from layauto_v2.importers import read_inputs
from layauto_v2.normalization.geometry_input import geometry_from_parse_result
from layauto_v2.normalization.geometry import build_geometry
from layauto_v2.normalization.effective import build_effective_geometry
from layauto_v2.normalization.effective_codec import record_digest
r = build_effective_geometry(build_geometry(geometry_from_parse_result(read_inputs(Path(%r)))))
print(record_digest(r), r.value.semantic_digest, r.value.ref.sha256)
''' % str(FIXTURE / 'site_config.yaml')
    expected = ' '.join((record_digest(accepted), accepted.value.semantic_digest, accepted.value.ref.sha256))
    for seed in ('1', '73', 'random'):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        result = subprocess.run([sys.executable, '-B', '-c', script], cwd=Path.cwd(),
                                env=env, text=True, capture_output=True, check=True)
        assert result.stdout.strip() == expected


class MutableLiteral:
    """An incompatible caller object must never enter a frozen DTO via equality."""
    def __init__(self):
        self.items = []

    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False


class MutableText(str):
    pass


@pytest.mark.parametrize('where', ['ref_kind', 'region_role', 'record_operation', 'result_status',
                                    'binding_version', 'piece_version', 'region_version',
                                    'record_version', 'draft_version', 'result_version', 'region_unit_kind',
                                    'record_unit_kind', 'binding_unit_kind'])
@pytest.mark.parametrize('literal', ['equal_object', 'text_subclass'])
def test_closed_literals_reject_mutable_equal_objects_and_text_subclasses(accepted, where, literal):
    draft = accepted.value
    record = draft.records[0]
    region = record.regions[0]
    expected = {'ref_kind': region.ref.kind, 'region_role': region.role,
                'record_operation': record.operation, 'result_status': accepted.status,
                'result_version': accepted.schema_version,
                'region_unit_kind': 'unit', 'record_unit_kind': 'unit',
                'binding_unit_kind': 'unit'}.get(where, draft.schema_version)
    foreign = MutableLiteral() if literal == 'equal_object' else MutableText(expected)
    foreign.items = []
    with pytest.raises(ValueError):
        if where == 'ref_kind': replace(region.ref, kind=foreign)
        elif where == 'region_role': replace(region, role=foreign)
        elif where == 'record_operation': replace(record, operation=foreign)
        elif where == 'result_status': replace(accepted, status=foreign)
        elif where == 'binding_version': replace(draft.operators, schema_version=foreign)
        elif where == 'piece_version': replace(region.pieces[0], schema_version=foreign)
        elif where == 'region_version': replace(region, schema_version=foreign)
        elif where == 'record_version': replace(record, schema_version=foreign)
        elif where == 'draft_version': replace(draft, schema_version=foreign)
        elif where == 'region_unit_kind': replace(region, unit_ref=replace(region.unit_ref, kind=foreign))
        elif where == 'record_unit_kind': replace(record, unit_ref=replace(record.unit_ref, kind=foreign))
        elif where == 'binding_unit_kind': replace(draft.operators, unit_ref=replace(draft.operators.unit_ref, kind=foreign))
        else: replace(accepted, schema_version=foreign)


@pytest.mark.parametrize('where', ['geometry_schema', 'geometry_status', 'geometry_input_schema',
                                    'semantic_input_schema', 'base_schema', 'fragment_schema'])
def test_new_boundary_rejects_mutable_literals_retained_by_legacy_receipts(accepted, where):
    geometry = accepted.input
    base = geometry.value
    if where == 'geometry_schema':
        foreign = MutableText(geometry.schema_version)
        borrowed = replace(geometry, schema_version=foreign)
    elif where == 'geometry_status':
        foreign = MutableText(geometry.status)
        borrowed = replace(geometry, status=foreign)
    elif where == 'geometry_input_schema':
        foreign = MutableText(geometry.input.schema_version)
        borrowed = replace(geometry, input=replace(geometry.input, schema_version=foreign))
    elif where == 'semantic_input_schema':
        semantic = geometry.input.semantic_input
        foreign = MutableText(semantic.schema_version)
        changed = replace(semantic, schema_version=foreign)
        borrowed = replace(geometry, input=replace(geometry.input, semantic_input=changed))
    elif where == 'base_schema':
        foreign = MutableText(base.schema_version)
        base = replace(base, schema_version=foreign)
        borrowed = replace(geometry, value=base)
    else:
        fragment = base.fragments[0]
        foreign = MutableText(fragment.schema_version)
        changed = replace(fragment, schema_version=foreign)
        base = replace(base, fragments=(changed,) + base.fragments[1:])
        borrowed = replace(geometry, value=base)
    foreign.items = []
    # These are valid legacy constructor calls above. The new component must
    # reject them at its own boundary without changing the historical DTOs.
    with pytest.raises(ValueError):
        build_effective_geometry(borrowed)
    with pytest.raises(ValueError):
        replace(accepted, input=borrowed)
    if where in ('base_schema', 'fragment_schema'):
        with pytest.raises(ValueError):
            build_effective_draft(base, accepted.value.physical)
        with pytest.raises(ValueError):
            replace(accepted.value, base=base)


@pytest.mark.parametrize('field', ['kind', 'parser_version', 'schema_version', 'source_uri'])
def test_completed_facts_cannot_add_mutable_aliases(accepted, field):
    original = accepted.completed[0]
    if field == 'source_uri':
        source = replace(original.sources[0], uri=MutableText(original.sources[0].uri))
        changed = replace(original, sources=(source,) + original.sources[1:])
    else:
        changed = replace(original, **{field: MutableText(getattr(original, field))})
    with pytest.raises(ValueError):
        replace(accepted, completed=(changed,) + accepted.completed[1:])


@pytest.mark.parametrize('field', ['kind', 'parser_version', 'schema_version'])
def test_standalone_binding_closes_legacy_evidence_literals(accepted, field):
    binding = accepted.value.operators
    original = binding.physical
    changed = replace(original, **{field: MutableText(getattr(original, field))})
    with pytest.raises(ValueError):
        replace(binding, physical=changed)


@pytest.fixture(scope='module')
def rejected(tmp_path_factory):
    root = ready_copy(tmp_path_factory.mktemp('w009-closed-error'))
    change_owner(root, 'physical', lambda doc: doc['operators'].__setitem__('terminal_split/1', 'unsupported'))
    value = build_effective_geometry(build_geometry(geometry_from_parse_result(read(root))))
    assert value.status == 'error'
    return value


@pytest.mark.parametrize('field', ['category', 'code', 'message', 'source_uri'])
def test_error_issues_cannot_retain_mutable_text_aliases(rejected, field):
    original = rejected.issues[0]
    if field == 'source_uri':
        source = replace(original.source, uri=MutableText(original.source.uri))
        changed = replace(original, source=source)
    else:
        changed = replace(original, **{field: MutableText(getattr(original, field))})
    with pytest.raises(ValueError):
        replace(rejected, issues=(changed,))


class ForeignRow:
    def __init__(self, actual):
        self.actual = actual
        self.items = []

    def __getattr__(self, name):
        return getattr(self.actual, name)

    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False


class SwitchingList(list):
    def __init__(self, good):
        super().__init__(good)
        self.good = tuple(good)
        self.bad = (ForeignRow(self.good[0]),) + self.good[1:] if self.good else ()
        self.calls = 0

    def __iter__(self):
        self.calls += 1
        return iter(self.good if self.calls == 1 else self.bad)


class SwitchingTuple(tuple):
    def __new__(cls, good):
        result = super().__new__(cls, good)
        result.good = tuple(good)
        result.bad = (ForeignRow(result.good[0]),) + result.good[1:] if result.good else ()
        result.calls = 0
        return result

    def __iter__(self):
        self.calls += 1
        return iter(self.good if self.calls == 1 else self.bad)


@pytest.mark.parametrize('container', [SwitchingList, SwitchingTuple])
@pytest.mark.parametrize('where', ['region_contributors', 'region_rectangles', 'record_contributors',
                                    'record_regions', 'draft_records', 'completed', 'issues'])
def test_new_collections_never_validate_and_copy_different_iterations(accepted, rejected, container, where):
    draft = accepted.value
    row = next(r for r in draft.records if r.operation == 'terminal')
    region = row.regions[0]
    owner, field = {
        'region_contributors': (region, 'contributors'), 'region_rectangles': (region, 'rectangles'),
        'record_contributors': (row, 'contributors'), 'record_regions': (row, 'regions'),
        'draft_records': (draft, 'records'), 'completed': (accepted, 'completed'),
        'issues': (rejected, 'issues'),
    }[where]
    changing = container(getattr(owner, field))
    with pytest.raises(ValueError):
        replace(owner, **{field: changing})
    assert changing.calls == 0


@pytest.mark.parametrize('where', ['records', 'policies', 'layers', 'fragments'])
def test_new_state_rejects_foreign_rows_hidden_in_legacy_base(accepted, where):
    base = accepted.value.base
    if where in ('records', 'policies'):
        layout = replace(base.layout, **{where: SwitchingList(getattr(base.layout, where))})
        partition = replace(base.partition, layout=layout)
        borrowed = replace(base, partition=partition)
        assert type(getattr(layout, where)[0]) is ForeignRow
    elif where == 'layers':
        partition = replace(base.partition, layers=SwitchingList(base.partition.layers))
        borrowed = replace(base, partition=partition)
        assert type(partition.layers[0]) is ForeignRow
    else:
        borrowed = replace(base, fragments=SwitchingList(base.fragments))
        assert type(borrowed.fragments[0]) is ForeignRow
    # Legacy constructors above remain untouched. Their folding to_value and
    # equality methods cannot make foreign objects admissible at the new seam.
    with pytest.raises(ValueError):
        build_effective_draft(borrowed, accepted.value.physical)
    with pytest.raises(ValueError):
        replace(accepted.value, base=borrowed)
    geometry = replace(accepted.input, value=borrowed)
    with pytest.raises(ValueError):
        build_effective_geometry(geometry)


class EqualType(type):
    def __eq__(cls, other): return True
    def __ne__(cls, other): return False
    __hash__ = type.__hash__


class EqualTypeText(str, metaclass=EqualType):
    pass


def test_closed_graph_checks_original_payload_before_canonical_folding(accepted):
    original = accepted.value.physical
    payload = mutable(original.payload)
    text = EqualTypeText(payload['device_extraction_contract']['body_operator'])
    text.items = []
    payload['device_extraction_contract']['body_operator'] = text
    changed = replace(original, payload=payload)
    assert changed.payload['device_extraction_contract']['body_operator'] is text
    assert canonical_bytes(changed.payload) == canonical_bytes(original.payload)
    with pytest.raises(ValueError):
        replace(accepted.value.operators, physical=changed)
    with pytest.raises(ValueError):
        build_effective_draft(accepted.value.base, changed)


class MutableInteger(int):
    def __new__(cls, value):
        result = super().__new__(cls, value)
        result.items = []
        return result

    @property
    def numerator(self): return self

    @property
    def denominator(self): return 1

    def __mul__(self, other):
        return self if other == 1 else MutableInteger(int(self) * int(other))

    def __rmul__(self, other): return self.__mul__(other)

    def __floordiv__(self, other):
        return self if other == 1 else MutableInteger(int(self) // int(other))


@pytest.mark.parametrize('entry', ['state_builder', 'draft_constructor', 'public_builder', 'result_constructor'])
def test_exact_fraction_must_also_have_native_integer_components(accepted, entry):
    base = accepted.value.base
    encoded = mutable(base.layout.units.encoded)
    actual = encoded['user_units_per_tick']['exact']
    numerator, denominator = MutableInteger(actual.numerator), MutableInteger(actual.denominator)
    foreign = Fraction(numerator, denominator)
    assert type(foreign) is Fraction and foreign.numerator is numerator
    assert canonical_bytes(foreign) == canonical_bytes(actual)
    encoded['user_units_per_tick']['exact'] = foreign
    unit = replace(base.layout.units, encoded=encoded)
    layout = replace(base.layout, units=unit)
    partition = replace(base.partition, layout=layout)
    borrowed = replace(base, partition=partition)
    geometry = replace(accepted.input, value=borrowed)
    with pytest.raises(ValueError):
        if entry == 'state_builder': build_effective_draft(borrowed, accepted.value.physical)
        elif entry == 'draft_constructor': replace(accepted.value, base=borrowed)
        elif entry == 'public_builder': build_effective_geometry(geometry)
        else: replace(accepted, input=geometry)


class MappingSourceFile(SourceFile, Mapping):
    def __getitem__(self, key): return 'ordinary exact value'
    def __iter__(self): return iter(('extra',))
    def __len__(self): return 1


def test_original_receipt_graph_requires_known_record_types_before_encoding(accepted):
    original = accepted.input.input.parse
    first = original.sources[0]
    source = MappingSourceFile(first.uri, first.data)
    source.mutable_items = []
    parsed = replace(original, sources=(source,) + original.sources[1:])
    semantic = replace(accepted.input.input.semantic_input, parse=parsed)
    receipt = replace(accepted.input.input, semantic_input=semantic)
    geometry = replace(accepted.input, input=receipt)
    # Canonical encoding can fold an unknown Mapping into a plain value. The
    # original graph must be checked before allowing the encoded receipt.
    from layauto_v2.normalization.geometry_codec import encode_record as encode_geometry
    assert encode_geometry(geometry)
    with pytest.raises(ValueError):
        build_effective_geometry(geometry)
