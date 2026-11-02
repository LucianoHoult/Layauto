"""Byte-level parser regressions independent of fixture support helpers."""
from __future__ import annotations

import json
import struct
from fractions import Fraction
from pathlib import Path

import pytest

from layauto_v2.domain.codec import FrozenMap, freeze_map
from layauto_v2.domain.evidence import SourceFile
from layauto_v2.domain.results import InputError
from layauto_v2.importers._access import mapping, sequence
from layauto_v2.importers.cdl import parse_cdl
from layauto_v2.importers.gds import decode_real8, parse_gds

ROOT = Path(__file__).resolve().parents[1] / 'fixtures' / 'w003_m1'


def tech() -> FrozenMap:
    return freeze_map({owner: json.loads((ROOT / 'tech' / f'{owner}.json').read_bytes())
                       for owner in ('drawn', 'derived', 'physical', 'formats', 'coordinate', 'rules')})


def source(path: str = 'source.gds') -> SourceFile:
    return SourceFile(path, (ROOT / path).read_bytes())


def records(data: bytes) -> list[bytes]:
    result = []
    offset = 0
    while offset < len(data):
        length = int.from_bytes(data[offset:offset + 2], 'big')
        result.append(data[offset:offset + length])
        offset += length
    return result


def test_all_gds_geometry_against_independent_answer() -> None:
    parsed = parse_gds(source(), tech())
    independent = json.loads((ROOT / 'independent-design-answer.json').read_bytes())
    actual = sorted((mapping(x)['canonical_layer'], mapping(x)['bbox']) for x in sequence(parsed['elements']))
    expected = sorted((x['layer'], tuple(x['bbox'])) for x in independent['local_scope']['coordinates'].values())
    assert actual == expected
    assert len(actual) == 40
    marker = independent['local_scope']['coordinates']['MARK']
    assert (marker['layer'], tuple(marker['bbox'])) in actual
    raw = source().data
    assert parsed['raw_document'] == raw
    units = mapping(parsed['units'])
    tick = mapping(units['metres_per_tick'])
    assert tick['raw'] == raw[60:68]
    assert tick['nominal'] == Fraction(1, 1_000_000_000)
    assert tick['exact'] == Fraction(int.from_bytes(raw[61:68], 'big'), 2**56 * 16**7)
    assert tick['encoding_delta'] != 0


@pytest.mark.parametrize(('path', 'code'), [
    ('failures/unit_mismatch/source.gds', 'UnitScaleMismatch'),
    ('failures/gds_text/source.gds', 'UnsupportedGdsElement:TEXT'),
    ('failures/gds_nonrectangle/source.gds', 'UnsupportedNonrectangle'),
])
def test_gds_delivered_failure_bytes(path: str, code: str) -> None:
    with pytest.raises(InputError) as info:
        parse_gds(source(path), tech())
    issue = info.value.issue
    assert issue.code == code
    assert issue.source.sha256 == source(path).sha256
    assert issue.source.byte_offset is not None
    assert issue.source.record_index is not None


@pytest.mark.parametrize('transform', ['reverse', 'rotate'])
def test_gds_rectangle_vertex_order_is_not_semantic(transform: str) -> None:
    raw_records = records(source().data)
    for index, rec in enumerate(raw_records):
        if rec[2] == 16:
            values = struct.unpack('>10i', rec[4:])
            vertices = list(zip(values[::2], values[1::2]))[:-1]
            vertices = vertices[::-1] if transform == 'reverse' else vertices[1:] + vertices[:1]
            vertices.append(vertices[0])
            raw_records[index] = rec[:4] + struct.pack('>10i', *(v for pair in vertices for v in pair))
    original, changed = parse_gds(source(), tech()), parse_gds(SourceFile('rotated.gds', b''.join(raw_records)), tech())
    assert [mapping(x)['bbox'] for x in sequence(original['elements'])] == [mapping(x)['bbox'] for x in sequence(changed['elements'])]
    assert mapping(sequence(original['elements'])[0])['xy'] != mapping(sequence(changed['elements'])[0])['xy']


@pytest.mark.parametrize(('mutate', 'code'), [
    (lambda b: b[:-1], 'TruncatedGdsRecord'),
    (lambda b: b + b'\x00', 'TruncatedGdsRecord'),
    (lambda b: b[:2] + b'\x00\x03' + b[4:], 'InvalidGdsRecordType'),
    (lambda b: b'\x00\x03' + b[2:], 'InvalidGdsRecordLength'),
    (lambda b: b[:-4], 'TruncatedGdsStructure'),
    (lambda b: b[:116] + b'\x00\x06\x0d\x02\x7f\xff' + b[122:], 'UnknownStreamKey'),
    (lambda b: b[:-4] + b'\x00\x04\x2b\x00' + b[-4:], 'UnsupportedGdsElement:PROPATTR'),
])
def test_gds_structural_failures(mutate: object, code: str) -> None:
    # pytest inputs deliberately operate on raw bytes, outside runtime parser.
    assert callable(mutate)
    with pytest.raises(InputError) as info:
        parse_gds(SourceFile('bad.gds', mutate(source().data)), tech())
    assert info.value.issue.code == code


def test_real8_rejects_noncanonical_and_wrong_rounding() -> None:
    assert decode_real8(bytes(8)) == 0
    assert decode_real8(bytes.fromhex('4110000000000000')) == 1
    assert decode_real8(bytes.fromhex('c110000000000000')) == -1
    for raw in (b'', bytes.fromhex('4100000000000000'), bytes.fromhex('4101000000000000')):
        with pytest.raises(ValueError):
            decode_real8(raw)
    data = bytearray(source().data)
    data[67] += 1
    with pytest.raises(InputError, match='nominal scale') as info:
        parse_gds(SourceFile('one-ulp.gds', bytes(data)), tech())
    assert info.value.issue.code == 'UnitScaleMismatch'


def test_gds_record_limit_counts_all_stream_records() -> None:
    original = parse_gds(source(), tech())
    config = {owner: json.loads((ROOT / 'tech' / f'{owner}.json').read_bytes())
              for owner in ('drawn', 'derived', 'physical', 'formats', 'coordinate', 'rules')}
    config['formats']['limits']['max_records'] = original['stream_record_count']
    assert parse_gds(source(), freeze_map(config))['top'] == original['top']
    config['formats']['limits']['max_records'] -= 1
    with pytest.raises(InputError) as info:
        parse_gds(source(), freeze_map(config))
    assert info.value.issue.code == 'RecordLimitExceeded'


def test_cdl_full_document_exact_and_nf_is_not_admitted_here() -> None:
    parsed = parse_cdl(source('source.cdl'), tech())
    top = mapping(sequence(parsed['tops'])[0])
    assert top['pins'] == ('A', 'Y', 'VSS', 'VDD')
    assert top['globals'] == ()
    device = mapping(sequence(top['devices'])[0])
    assert device['terminals'] == ('Y', 'A', 'VSS', 'VSS')
    parameters = mapping(device['parameters'])
    assert mapping(parameters['L'])['exact'] == Fraction(4, 1_000_000_000)
    assert mapping(parameters['L'])['lexeme'] == '4n'
    assert parsed['raw_document'] == source('source.cdl').data
    assert parsed['dependency_closure'] == ()
    nf2 = parse_cdl(source('failures/multifinger/source.cdl'), tech())
    first = mapping(sequence(mapping(sequence(nf2['tops'])[0])['devices'])[0])
    assert mapping(mapping(first['parameters'])['NF'])['exact'] == 2


@pytest.mark.parametrize(('text', 'code'), [
    ('failures/cdl_expression/source.cdl', 'UnsupportedCdlExpression'),
    ('failures/cdl_include/source.cdl', 'UnsupportedDependencyDirective'),
])
def test_cdl_delivered_failure_bytes(text: str, code: str) -> None:
    with pytest.raises(InputError) as info:
        parse_cdl(source(text), tech())
    assert info.value.issue.code == code
    assert info.value.issue.source.line is not None
    assert info.value.issue.source.sha256 == source(text).sha256


@pytest.mark.parametrize(('old', 'new', 'code'), [
    (b'NFIN=5', b'NFIN=0', 'InvalidCdlValue'),
    (b'NFIN=5', b'NFIN=-5', 'InvalidCdlValue'),
    (b' L=4n', b' L=4.5n', 'InvalidCdlValue'),
    (b' L=4n', b' L=4n L=5n', 'DuplicateCdlParameter'),
    (b' L=4n', b'', 'MissingCdlParameter'),
    (b' L=4n', b' EXTRA=4n', 'UnsupportedCdlParameter'),
    (b'TOY_N ', b'UNKNOWN ', 'UnsupportedCdlModel'),
    (b'.ENDS INV_M1_SYNTH', b'.ENDS OTHER', 'InvalidCdlStructure'),
    (b'.ENDS INV_M1_SYNTH', b'', 'MissingCdlTerminator'),
    (b'.ENDS INV_M1_SYNTH', b'.GLOBAL VSS\n.ENDS INV_M1_SYNTH', 'UnsupportedCdlDirective'),
])
def test_cdl_literal_and_structural_rejection(old: bytes, new: bytes, code: str) -> None:
    data = source('source.cdl').data.replace(old, new, 1)
    with pytest.raises(InputError) as info:
        parse_cdl(SourceFile('changed.cdl', data), tech())
    assert info.value.issue.code == code


def test_second_cdl_multiple_tops_order_whitespace_and_coordinates_independent() -> None:
    data = b'* second legal document\n.SUBCKT SECOND IN OUT\nMchanged OUT IN OUT IN TOY_N VT=toy W=3n L=9n M=2 NF=3 NFIN=11\n.ENDS SECOND\n.SUBCKT EMPTY\n.ENDS EMPTY\n'
    parsed = parse_cdl(SourceFile('arbitrary.cdl', data), tech())
    assert len(sequence(parsed['tops'])) == 2
    top = mapping(sequence(parsed['tops'])[0])
    assert top['name'] == 'SECOND'
    parameters = mapping(mapping(sequence(top['devices'])[0])['parameters'])
    assert mapping(parameters['NFIN'])['exact'] == 11
    assert mapping(parameters['W'])['exact'] == Fraction(3, 1_000_000_000)
    assert mapping(sequence(parsed['tops'])[1])['devices'] == ()


def test_cdl_text_byte_limit_and_record_limit_boundaries() -> None:
    config = {owner: json.loads((ROOT / 'tech' / f'{owner}.json').read_bytes())
              for owner in ('drawn', 'derived', 'physical', 'formats', 'coordinate', 'rules')}
    data = source('source.cdl').data
    config['formats']['limits']['max_bytes_per_text_file'] = len(data)
    config['formats']['limits']['max_records'] = 4
    assert parse_cdl(SourceFile('limit.cdl', data), freeze_map(config))['logical_record_count'] == 4
    with pytest.raises(InputError) as info:
        parse_cdl(SourceFile('limit.cdl', data + b'\n'), freeze_map(config))
    assert info.value.issue.code == 'TextSizeExceeded'
    config['formats']['limits']['max_records'] = 3
    with pytest.raises(InputError) as info:
        parse_cdl(SourceFile('limit.cdl', data), freeze_map(config))
    assert info.value.issue.code == 'RecordLimitExceeded'
