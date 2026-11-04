"""W009's nested W008 reconstruction keeps faults distinct from bad wire."""
from dataclasses import replace

import pytest

from layauto_v2.domain.codec import canonical_bytes, decode
from layauto_v2.domain import publication_codec
from layauto_v2.normalization import build_effective_geometry, build_geometry, geometry_from_parse_result
from layauto_v2.normalization import effective_codec, geometry_codec
from w005_cases import FIXTURE
from w007_cases import mutable, read


@pytest.fixture(scope='module')
def accepted():
    return build_effective_geometry(build_geometry(geometry_from_parse_result(read(FIXTURE))))


TARGETS = ('layauto_v2.state.layout_store._materialize',
           'layauto_v2.state.coordinate._layers',
           'layauto_v2.state.occupancy._fragments')
FAILURES = (RuntimeError, ValueError, TypeError, KeyError, AttributeError,
            IndexError, UnicodeError, KeyboardInterrupt, SystemExit)


@pytest.mark.parametrize('target', TARGETS)
@pytest.mark.parametrize('failure_type', FAILURES)
@pytest.mark.parametrize('enclosing', ('draft', 'result', 'w008'))
def test_nested_base_fault_keeps_object_cause_and_context(accepted, monkeypatch, target, failure_type, enclosing):
    if enclosing == 'w008':
        wire, decoder = geometry_codec.encode_record(accepted.input), geometry_codec.decode_record
    else:
        wire = effective_codec.encode_record(accepted.value if enclosing == 'draft' else accepted)
        decoder = effective_codec.decode_record
    failure = failure_type('internal reconstruction fault')
    cause, context = RuntimeError('existing cause'), LookupError('existing context')
    failure.__cause__, failure.__context__ = cause, context
    failure.__suppress_context__ = False

    def broken(*args, **kwargs):
        raise failure

    monkeypatch.setattr(target, broken)
    with pytest.raises(failure_type) as caught:
        decoder(wire)
    assert caught.value is failure
    assert caught.value.__cause__ is cause
    assert caught.value.__context__ is context
    assert caught.value.__suppress_context__ is False


def bad_gds(accepted, change):
    gds = accepted.value.base.layout.gds
    payload = mutable(gds.payload)
    row = payload['elements'][0]
    if change == 'missing':
        del row['bbox']
    elif change == 'extra':
        row['unknown'] = True
    elif change == 'layer':
        row['canonical_layer'] = 'unknown layer'
    elif change == 'short_xy':
        row['xy'][0] = [1]
    elif change == 'scalar_xy':
        row['xy'] = 1
    elif change == 'nested_xy':
        row['xy'][0] = {'x': 1, 'y': 2}
    elif change == 'scalar_bbox':
        row['bbox'] = False
    elif change == 'short_bbox':
        row['bbox'] = [1, 2]
    elif change == 'scalar_row':
        payload['elements'][0] = 1
    elif change == 'collection_position':
        row['byte_offset'] = []
    else:
        raise AssertionError(change)
    return replace(gds, payload=payload)


def with_gds(tree, record):
    if isinstance(tree, dict):
        if tree.get('record') == 'LayoutDraft':
            tree['fields']['gds'] = {'captured_record': publication_codec.encode_record(record)}
            return True
        return any(with_gds(value, record) for value in tree.values())
    if isinstance(tree, list):
        return any(with_gds(value, record) for value in tree)
    return False


@pytest.mark.parametrize('change', ('missing', 'extra', 'layer', 'short_xy', 'scalar_xy',
                                    'nested_xy', 'scalar_bbox', 'short_bbox', 'scalar_row',
                                    'collection_position'))
@pytest.mark.parametrize('entry', ('constructor', 'w008', 'w009'))
def test_preserved_boundary_malformed_fields_are_explicitly_rejected(accepted, change, entry):
    bad = bad_gds(accepted, change)
    layout = accepted.value.base.layout
    if entry == 'constructor':
        with pytest.raises(ValueError):
            replace(layout, gds=bad)
        return
    if entry == 'w008':
        tree = mutable(decode(geometry_codec.encode_record(layout)))
        assert with_gds(tree, bad)
        wire, decoder = canonical_bytes(tree), geometry_codec.decode_record
    else:
        tree = mutable(decode(effective_codec.encode_record(accepted.value)))
        base = mutable(decode(tree['record']['fields']['base']['geometry_record']))
        assert with_gds(base, bad)
        tree['record']['fields']['base']['geometry_record'] = canonical_bytes(base)
        wire, decoder = canonical_bytes(tree), effective_codec.decode_record
    with pytest.raises(ValueError):
        decoder(wire)


@pytest.mark.parametrize('codec', (geometry_codec, effective_codec))
def test_wire_changes_do_not_change_valid_roundtrip_or_digest(accepted, codec):
    record = accepted.input if codec is geometry_codec else accepted
    wire = codec.encode_record(record)
    rebuilt = codec.decode_record(wire)
    assert rebuilt == record
    assert codec.encode_record(rebuilt) == wire
    assert codec.record_digest(rebuilt) == codec.record_digest(record)
    with pytest.raises(ValueError):
        codec.decode_record(wire + b'\n')


@pytest.mark.parametrize('kind', tuple(geometry_codec._SPEC))
def test_all_w008_wire_record_fields_reject_missing_extra_and_null(accepted, kind):
    base = accepted.value.base
    layout = base.layout
    fragment = base.fragments[0]
    values = (layout.units.ref, layout.records[0].id, fragment.id, layout.records[0].rect,
              layout.records[0].stream_key, layout.units, layout.policies[0], layout.records[0],
              layout, base.partition.layers[0], base.partition, fragment.cell, fragment,
              base, accepted.input.input, accepted.input)
    record = next(value for value in values if type(value).__name__ == kind)
    original = geometry_codec.encode_record(record)
    tree = mutable(decode(original))
    keys = tuple(tree['record']['fields'])
    for key in keys:
        missing = mutable(decode(original))
        del missing['record']['fields'][key]
        with pytest.raises(ValueError):
            geometry_codec.decode_record(canonical_bytes(missing))
        null = mutable(decode(original))
        null['record']['fields'][key] = {'scalar': None}
        with pytest.raises(ValueError):
            geometry_codec.decode_record(canonical_bytes(null))
    tree['record']['fields']['unknown'] = {'scalar': 1}
    with pytest.raises(ValueError):
        geometry_codec.decode_record(canonical_bytes(tree))
