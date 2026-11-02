"""Query tests read accepted bytes; expected caches are test-only comparisons."""
from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path

import pytest

from layauto_v2.domain.codec import FrozenMap, canonical_bytes, freeze_map, rational
from layauto_v2.domain.evidence import SourceFile
from layauto_v2.domain.results import InputError
from layauto_v2.importers.calibre import CAPABILITIES, parse_query
from layauto_v2.importers._access import mapping, sequence, string
from layauto_v2.importers.config import load_document

FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures' / 'w003_m1'


def source(uri: str) -> SourceFile:
    return SourceFile(uri, (FIXTURE / uri).read_bytes())


def inputs() -> tuple[tuple[SourceFile, ...], FrozenMap, SourceFile, SourceFile, FrozenMap, SourceFile]:
    header = load_document(source('query/header.json'))
    raw = tuple(source(string(mapping(value)['uri'])) for value in sequence(header['raw']))
    tech = freeze_map({key: load_document(source(f'tech/{key}.json')) for key in ('drawn', 'derived', 'physical', 'formats', 'coordinate', 'rules')})
    return raw, header, source('query/requests.json'), source('query/dialect.json'), tech, source('tech/derived.json')


def run(raw: tuple[SourceFile, ...] | None = None, *, requests: SourceFile | None = None,
        dialect: SourceFile | None = None, header: FrozenMap | None = None) -> FrozenMap:
    original, default_header, default_requests, default_dialect, tech, derived = inputs()
    captures = raw if raw is not None else original
    selected_header = header if header is not None else default_header
    # Deliberate rebinding isolates syntax/format tests from hash tests.
    mutable = dict(selected_header)
    hashes = {item.uri: item.sha256 for item in captures}
    mutable['raw'] = tuple({**mapping(item), 'sha256': hashes[string(mapping(item)['uri'])]} for item in sequence(selected_header['raw']))
    return parse_query(captures, freeze_map(mutable), requests or default_requests,
                       dialect or default_dialect, tech, derived_source=derived)


def replace_raw(uri: str, old: bytes, new: bytes) -> tuple[SourceFile, ...]:
    raw, *_ = inputs()
    return tuple(SourceFile(item.uri, item.data.replace(old, new)) if item.uri == uri else item for item in raw)


def test_four_capabilities_match_independent_accepted_caches() -> None:
    parsed = run()
    for capability, count in zip(CAPABILITIES, (2, 4, 2, 8)):
        expected = load_document(source(f'query/normalized/{capability}.yaml'))
        actual = mapping(parsed[capability])
        assert canonical_bytes(actual) == canonical_bytes(expected)
        assert len(sequence(actual['records'])) == count
    metadata = mapping(parsed['_format_metadata'])
    assert mapping(metadata['instance_xref'])['layout_top'] == 'INV_M1_SYNTH'
    assert mapping(metadata['net_names'])['opener_opaque'] == '20000'


@pytest.mark.parametrize(('uri', 'old', 'new', 'code'), [
    ('query/raw/device_info_Q17.txt', b'END OF RESPONSE\n', b'', 'MissingTerminator'),
    ('query/raw/net_names.txt', b'0 0 4 ', b'0 0 5 ', 'CountMismatch'),
    ('query/raw/device_info_Q17.txt', b'p 1 4', b'b 1 4', 'UnsupportedGeometryToken'),
    ('query/raw/net_shapes_n_a.txt', b'Net_Shapes 20000', b'Net_Shapes 1000', 'UnitBindingMismatch'),
    ('query/raw/net_shapes_n_a.txt', b'200 1160', b'201 1160', 'UnsupportedNonrectangle'),
    ('query/raw/iXref.temp', b'0 Q17 0 MN0', b'0 Q17 0 MN0 Z', 'UnsupportedSwapToken'),
    ('query/raw/nXref.temp', b'0 n_y 0 Y', b'0 n_a 0 Y', 'DuplicateQueryIdentity'),
    ('query/raw/net_names.txt', b'n_y\n', b'n_a\n', 'DuplicateNetName'),
    ('query/raw/device_info_Q17.txt', b'toy_ngate', b'unknown_layer', 'UnknownDerivedLayer'),
    ('query/raw/device_info_Q17.txt', b'1 1 0 May', b'1 2 0 May', 'OpaqueSectionHeaderDrift'),
    ('query/raw/device_info_Q17.txt', b'0 0 2 May', b'0 0 3 May', 'MetadataCountMismatch'),
    ('query/raw/device_info_Q17.txt', b'400 1160', b'0.4 1160', 'InvalidCoordinate'),
    ('query/raw/iXref.temp', b'INV_M1_SYNTH 4 INV_M1_SYNTH 4', b'INV_OTHER 4 INV_M1_SYNTH 4', 'TopBindingMismatch'),
])
def test_rebound_bad_raw_keeps_targeted_reason(uri: str, old: bytes, new: bytes, code: str) -> None:
    with pytest.raises(InputError) as caught:
        run(replace_raw(uri, old, new))
    issue = caught.value.issue
    assert issue.code == code
    assert issue.source.uri == uri and issue.source.sha256 is not None
    assert issue.source.line is not None


def test_names_need_full_format_association() -> None:
    raw = replace_raw('query/raw/net_names.txt', b'n_a\n', b'other_net\n')
    with pytest.raises(InputError, match='nXref') as caught:
        run(raw)
    assert caught.value.issue.code == 'NetJoinMismatch'


def test_mapping_cardinality_and_swap_are_preserved_for_stage_two() -> None:
    raw = replace_raw('query/raw/iXref.temp', b'0 Q93 0 MP0', b'0 Q93 0 MN0 X')
    result = run(raw)
    records = sequence(mapping(result['instance_xref'])['records'])
    assert mapping(records[0])['schematic_instance'] == mapping(records[1])['schematic_instance']
    assert mapping(records[1])['sd_swap'] is True


def test_fractional_query_ticks_do_not_round() -> None:
    raw = replace_raw('query/raw/device_info_Q17.txt', b'1160', b'1161')
    parsed = run(raw)
    first = mapping(sequence(mapping(parsed['device_regions'])['records'])[0])
    vertex = mapping(sequence(first['vertices_nm'])[0])
    assert rational(vertex['x']) == Fraction(1161, 20)
    sources = mapping(first['field_sources'])
    assert '1161' in [mapping(item)['lexeme'] for item in sequence(mapping(sources['vertices_nm'])['sources'])]


def test_renamed_paths_top_and_objects_come_from_input() -> None:
    raw, header, requests, dialect, tech, derived = inputs()
    changes = {'INV_M1_SYNTH': 'CELL_TWO', 'Q17': 'LAYOUT_A', 'MN0': 'DEVICE_A', 'n_a': 'node_input'}
    def transform(data: bytes) -> bytes:
        for old, new in changes.items():
            data = data.replace(old.encode(), new.encode())
        return data
    captures = tuple(SourceFile('captures/' + str(i) + '.txt', transform(item.data)) for i, item in enumerate(reversed(raw)))
    by_old = {item.uri: updated for item, updated in zip(reversed(raw), captures)}
    h = json.loads(transform(source('query/header.json').data))
    for entry in h['raw']:
        old_uri = entry['uri']
        # Header URI strings were renamed too; match transformed URI to original.
        original_uri = next(uri for uri in by_old if transform(uri.encode()).decode() == old_uri)
        entry['uri'] = by_old[original_uri].uri
        entry['sha256'] = by_old[original_uri].sha256
    request_data = json.loads(transform(requests.data))
    for entry in request_data['requests']:
        original_uri = next(uri for uri in by_old if transform(uri.encode()).decode() == entry['path'])
        entry['path'] = by_old[original_uri].uri
    request_source = SourceFile('selection/requests.json', json.dumps(request_data).encode())
    parsed = parse_query(captures, freeze_map(h), request_source, dialect, tech, derived_source=derived)
    records = sequence(mapping(parsed['instance_xref'])['records'])
    assert mapping(records[0])['layout_instance'] == 'LAYOUT_A'
    assert mapping(records[0])['schematic_instance'] == 'DEVICE_A'
    assert mapping(mapping(parsed['_format_metadata'])['instance_xref'])['layout_top'] == 'CELL_TWO'
    refs = sequence(mapping(parsed['device_regions'])['raw_refs'])
    assert all(string(mapping(ref)['path']).startswith('captures/') for ref in refs)


def test_request_missing_duplicate_and_wrong_object() -> None:
    for mutate, expected in [
        (lambda d: d['requests'].pop(), 'RequestBindingMismatch'),
        (lambda d: d['requests'].append(d['requests'][0]), 'RequestBindingMismatch'),
        (lambda d: d['requests'][0].__setitem__('object', 'absent'), 'QueryObjectMismatch'),
        (lambda d: d['requests'][0]['record_ids'].append('extra'), 'ResponseShapeCountMismatch'),
    ]:
        data = json.loads(source('query/requests.json').data)
        mutate(data)
        with pytest.raises(InputError) as caught:
            run(requests=SourceFile('query/requests.json', json.dumps(data).encode()))
        assert caught.value.issue.code == expected


def test_bounded_raw_and_immutable_nested_results() -> None:
    raw, header, requests, dialect, tech, derived = inputs()
    constrained = {**tech, 'formats': {**mapping(tech['formats']), 'limits': {**mapping(mapping(tech['formats'])['limits']), 'max_bytes_per_text_file': 50}}}
    with pytest.raises(InputError) as caught:
        parse_query(raw, header, requests, dialect, freeze_map(constrained), derived_source=derived)
    assert caught.value.issue.code == 'SizeLimitExceeded'
    result = run()
    with pytest.raises(TypeError):
        result['device_regions'] = None  # type: ignore[index]


def test_profile_record_limits_are_exact_inclusive_boundaries() -> None:
    raw, header, requests, dialect, tech, derived = inputs()
    def limited(count: int) -> FrozenMap:
        return freeze_map({**tech, 'formats': {**mapping(tech['formats']), 'limits': {**mapping(mapping(tech['formats'])['limits']), 'max_records': count}}})
    assert len(sequence(mapping(parse_query(raw, header, requests, dialect, limited(8), derived_source=derived)['net_regions'])['records'])) == 8
    with pytest.raises(InputError) as caught:
        parse_query(raw, header, requests, dialect, limited(7), derived_source=derived)
    assert caught.value.issue.code == 'RecordLimit'


def test_raw_byte_limit_includes_final_lf() -> None:
    from layauto_v2.importers._query_raw import Text
    capture = SourceFile('capture', b'X\n')
    assert Text.read(capture, 2).lines == ('X',)
    with pytest.raises(InputError) as caught:
        Text.read(capture, 1)
    assert caught.value.issue.code == 'InputSizeLimit'


@pytest.mark.parametrize('bad', [b'X', b'X\r\n', b'X\n\n', b'X \n', b'X\x00\n', b'X\xff\n'])
def test_raw_encoding_rejected_without_skipping_bytes(bad: bytes) -> None:
    from layauto_v2.importers._query_raw import Text
    with pytest.raises(InputError) as caught:
        Text.read(SourceFile('capture', bad), 1000)
    assert caught.value.issue.code == 'RawEncoding'


def test_unlisted_or_duplicate_raw_inputs_are_binding_errors() -> None:
    raw, header, requests, dialect, tech, derived = inputs()
    for captures, expected in ((raw + (raw[0],), 'DuplicateRawBinding'),
                               (raw + (SourceFile('unlisted', b'X\n'),), 'RawListMismatch')):
        with pytest.raises(InputError) as caught:
            parse_query(captures, header, requests, dialect, tech, derived_source=derived)
        assert caught.value.issue.code == expected


def test_nondefault_timestamp_is_opaque_and_preserved() -> None:
    raw = replace_raw('query/raw/device_info_Q17.txt', b'May 07 03:00:00 2026', b'Nov 02 11:40:17 2026')
    parsed = run(raw)
    record = mapping(sequence(mapping(parsed['device_regions'])['records'])[0])
    assert record['section_header_opaque'] == '1 1 0 Nov 02 11:40:17 2026'
