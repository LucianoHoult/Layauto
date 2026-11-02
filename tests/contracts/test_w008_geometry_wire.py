"""Capture authentication is rerun at the public geometry wire boundary."""
from dataclasses import replace

import pytest

from layauto_v2.domain.codec import canonical_bytes, decode
from layauto_v2.domain.evidence import SourceFile
from layauto_v2.normalization import from_parse_result
from layauto_v2.normalization import codec as semantic_codec
from layauto_v2.normalization import geometry_input
from layauto_v2.normalization.geometry import build_geometry
from layauto_v2.normalization.geometry_codec import encode_record, decode_record
from layauto_v2.normalization.geometry_input import GeometryInputError, geometry_from_parse_result
from test_w008_capture_binding import captured_document, forged_payload
from w005_cases import FIXTURE
from w007_cases import mutable, read


@pytest.fixture(scope='module')
def accepted():
    return build_geometry(geometry_from_parse_result(read(FIXTURE)))


@pytest.mark.parametrize('enclosing', ['input', 'result'])
@pytest.mark.parametrize('decoder', ['load_document', 'parse_gds'])
@pytest.mark.parametrize('failure', [RuntimeError('bug'), ValueError('unexpected value'),
                                     TypeError('unexpected type'), KeyError('bug key'),
                                     KeyboardInterrupt(), SystemExit(41)])
def test_geometry_codec_preserves_decoder_exception_identity(accepted, monkeypatch, enclosing, decoder, failure):
    wire = encode_record(accepted.input if enclosing == 'input' else accepted)
    def broken(*args, **kwargs):
        raise failure
    monkeypatch.setattr(geometry_input, decoder, broken)
    with pytest.raises(type(failure)) as caught:
        decode_record(wire)
    assert caught.value is failure


def replace_input(tree, semantic):
    if isinstance(tree, dict):
        if tree.get('record') == 'GeometryInput':
            tree['fields']['semantic_input'] = {'semantic_input': semantic_codec.encode_record(semantic)}
            return True
        return any(replace_input(value, semantic) for value in tree.values())
    if isinstance(tree, list):
        return any(replace_input(value, semantic) for value in tree)
    return False


@pytest.mark.parametrize('change', ['gds', 'missing_original_gds_role', 'body_ref', 'body_arity', 'body_top', 'body_unit',
                                    'body_profile', 'body_scope', 'header_top', 'header_unit'])
def test_geometry_input_and_result_wire_recheck_capture_and_cross_document_bindings(accepted, change):
    parsed = accepted.input.parse
    if change == 'gds':
        parsed = forged_payload(parsed, 'gds', lambda doc: doc['elements'][0].__setitem__('bbox', [-1, 0, 160, 200]))
    elif change == 'missing_original_gds_role':
        original = next(r for r in parsed.completed if r.kind == 'gds').sources[0]
        capture = next(s for s in parsed.sources if s.uri == original.uri)
        sibling = SourceFile('impossible-first-acquisition.gds', capture.data)
        value = mutable(parsed.value)
        value['gds']['source']['uri'] = sibling.uri
        completed = tuple(replace(r, payload=value['gds'], sources=(sibling.ref(),)) if r.kind == 'gds'
                          else replace(r, sources=(r.sources[0], sibling.ref())) if r.kind == 'body'
                          else r for r in parsed.completed)
        parsed = replace(parsed, value=value, completed=completed,
                         sources=tuple(s for s in parsed.sources if s.uri != original.uri) + (sibling,))
    elif change in ('body_ref', 'body_arity'):
        records = {record.kind: record for record in parsed.completed}
        refs = (records['body'].sources[0],) if change == 'body_arity' else (records['body'].sources[0], records['source_cdl'].sources[0])
        parsed = replace(parsed, completed=tuple(replace(r, sources=refs) if r.kind == 'body' else r for r in parsed.completed))
    else:
        kind = 'header' if change.startswith('header_') else 'body'
        def mutation(doc):
            if change == 'body_top': doc['top'] = 'FOREIGN'
            elif change == 'body_unit': doc['unit']['metres_per_tick'] = {'numerator': '1', 'denominator': '2000000000'}
            elif change == 'body_profile': doc['profile_ref'] = 'foreign-profile/1'
            elif change == 'body_scope': doc['exported'] = True
            elif change == 'header_top': doc['top_identities']['layout'] = 'FOREIGN'
            else: doc['geometry_unit_contract'] = 'foreign-unit/1'
        parsed = captured_document(parsed, kind, mutation)
    # Authenticity must be enforced beyond the preceding semantic-only receipt.
    semantic = from_parse_result(parsed)
    for original in (accepted.input, accepted):
        tree = mutable(decode(encode_record(original)))
        assert replace_input(tree, semantic)
        with pytest.raises(GeometryInputError):
            decode_record(canonical_bytes(tree))
