"""A1/A3–A6: actual-file component contracts, independent of fixture helpers."""
from __future__ import annotations

import hashlib
import io
from collections import Counter
from fractions import Fraction
from pathlib import Path

import pytest

from w005_cases import (FIXTURE, apply_case, copy_input, inventory, read_json,
                        rebind, renamed_input, without_cache, write_json)


def load(root: Path, **kwargs):
    from layauto_v2.importers import read_inputs
    return read_inputs(root / 'site_config.yaml', **kwargs)


def success(result):
    assert result.status == 'success', [(x.code, x.message, x.source) for x in result.issues]
    assert result.value is not None
    assert not result.issues
    return result.value


def exact(value):
    if isinstance(value, (int, Fraction)):
        return Fraction(value)
    return Fraction(int(value['numerator']), int(value['denominator']))


def test_accepted_actual_files_match_independent_answers_without_runtime_oracles(monkeypatch):
    answer = read_json(FIXTURE / 'independent-design-answer.json')['local_scope']
    semantic = read_json(FIXTURE / 'oracle.json')['semantic']
    before = inventory(FIXTURE)
    original_open = io.open
    opened = []

    def guarded_open(file, *args, **kwargs):
        if isinstance(file, (str, Path)):
            path = Path(file)
            opened.append(path)
            assert path.name not in {'spec.json', 'oracle.json', 'independent-design-answer.json', 'context-template.json'}
            assert 'expected' not in path.parts and 'examples' not in path.parts
        return original_open(file, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(io, 'open', guarded_open)
        result = load(FIXTURE, tool_run_id='external-read-17')
    value = success(result)
    assert result.tool_run_id == 'external-read-17'
    assert inventory(FIXTURE) == before
    assert opened
    assert value['gds']['top'] == answer['top']
    expected = Counter((shape['layer'], tuple(shape['bbox'])) for shape in answer['coordinates'].values())
    actual = Counter((element['canonical_layer'], tuple(element['bbox'])) for element in value['gds']['elements'])
    assert actual == expected
    assert len(value['gds']['elements']) == 40
    assert Counter(x['canonical_layer'] for x in value['gds']['elements']) == Counter(answer['shape_counts_by_layer'])
    for key in ('source_cdl', 'target_cdl'):
        tops = value[key]['tops']
        assert len(tops) == 1
        top = tops[0]
        assert top['name'] == semantic['cell']
        assert tuple(top['pins']) == tuple(semantic['pins'])
        assert tuple(top['globals']) == ()
        devices = {d['name']: d for d in top['devices']}
        assert set(devices) == {d['id'] for d in semantic['devices']}
        for expected_device in semantic['devices']:
            device = devices[expected_device['id']]
            assert device['model'] == expected_device['model']
            assert tuple(device['terminal_order']) == ('D', 'G', 'S', 'B')
            assert tuple(device['terminals']) == tuple(expected_device['terminals'][k] for k in ('D', 'G', 'S', 'B'))
            params = device['parameters']
            expected_params = expected_device['parameters']
            assert exact(params['NFIN']['exact']) == expected_params['fins_per_finger']
            assert exact(params['NF']['exact']) == expected_params['finger_count']
            assert exact(params['M']['exact']) == expected_params['multiplicity']
            assert exact(params['L']['exact']) == Fraction(expected_params['L_nm'], 10**9)
            assert exact(params['W']['exact']) == Fraction(expected_params['W_nm'], 10**9)
            assert params['VT']['exact'] == expected_params['VT']
            assert {p['lexeme'] for p in params.values()} >= {'1', '4n', '2n', 'toy'}
    assert {cap: len(value['query'][cap]['records']) for cap in ('instance_xref', 'net_xref', 'device_regions', 'net_regions')} == {
        'instance_xref': 2, 'net_xref': 4, 'device_regions': 2, 'net_regions': 8}
    region = value['query']['device_regions']['records'][0]
    assert region['quality'] == 'exact'
    assert [(exact(p['x']), exact(p['y'])) for p in region['vertices_nm']] == [(58, 20), (58, 70), (62, 70), (62, 20)]
    assert len(value['body']['shapes']) == 6
    assert value['body']['production_matched_body_evidence'] is False
    assert 'body_complete' not in value['body']
    assert result.completed and result.sources
    for source in result.sources:
        assert source.sha256 == hashlib.sha256(source.data).hexdigest()
        assert not any(part in Path(source.uri).parts for part in ('expected', 'examples'))
    read_hashes = {source.sha256 for source in result.sources}
    assert all(ref.sha256 in read_hashes for record in result.completed for ref in record.sources)


NEGATIVES = [
    ('unit_mismatch', 'UnitScaleMismatch'),
    ('missing_terminator', 'MissingTerminator'),
    ('wrong_count', 'CountMismatch'),
    ('dialect_drift', 'UnsupportedGeometryToken'),
    ('unknown_unit', 'UnitBindingMismatch'),
    ('raw_byte_drift', 'RawHashMismatch'),
    ('header_top_mismatch', 'TopBindingMismatch'),
    ('cdl_expression', 'UnsupportedCdlExpression'),
    ('cdl_include', 'UnsupportedDependencyDirective'),
    ('gds_text', 'UnsupportedGdsElement'),
    ('gds_nonrectangle', 'UnsupportedNonrectangle'),
    ('normalized_cache_drift', 'NormalizedCacheMismatch'),
    ('missing_body_operator', 'RequiredBodyOperatorUnavailable'),
    ('body_wrong_binding', 'BodySourceBindingMismatch'),
]


@pytest.mark.parametrize('case_name,expected_code', NEGATIVES)
def test_actual_negative_overlays_report_intended_defect(tmp_path, case_name, expected_code):
    root = copy_input(tmp_path)
    apply_case(root, case_name)
    result = load(root)
    assert result.status == 'error'
    assert result.value is None and result.issues
    issue = result.issues[0]
    assert issue.code == expected_code or issue.code.startswith(expected_code + ':'), (issue.code, issue.message)
    assert issue.source.uri and issue.message
    # Readable malformed files retain their actual bytes and a field/record/line location.
    assert issue.source.sha256 in {s.sha256 for s in result.sources}
    assert any(x is not None for x in (issue.source.field, issue.source.line, issue.source.byte_offset, issue.source.record_index))


def test_missing_required_body_has_no_fabricated_bytes_hash(tmp_path):
    root = copy_input(tmp_path)
    apply_case(root, 'missing_body_context')
    result = load(root)
    assert result.status == 'error'
    issue = result.issues[0]
    assert issue.category == 'read'
    assert issue.source.uri.endswith('body/context.json')
    assert issue.source.sha256 is None


@pytest.mark.parametrize('case_name', [
    'mapping_many_to_one', 'multifinger', 'device_reduction', 'unsupported_target',
    'count_correct_rule_wrong', 'via_enclosure', 'extraction_mismatch',
    'output_nonrepresentable', 'output_overflow', 'body_wrong_type',
    'body_disconnected', 'body_ambiguous', 'body_enclosure', 'body_wrong_rail',
])
def test_later_stage_failures_remain_input_facts(tmp_path, case_name):
    root = copy_input(tmp_path)
    apply_case(root, case_name)
    value = success(load(root))
    assert value['gds']['elements']
    assert 'no_change' not in value and 'body_complete' not in value
    if case_name == 'multifinger':
        params = value['source_cdl']['tops'][0]['devices'][0]['parameters']
        assert params['NF']['lexeme'] == '2' and exact(params['NF']['exact']) == 2


def test_all_normalized_caches_are_optional(tmp_path):
    root = copy_input(tmp_path)
    without_cache(root)
    value = success(load(root))
    assert len(value['query']['device_regions']['records']) == 2


def test_bad_raw_cannot_hide_behind_absent_caches(tmp_path):
    root = copy_input(tmp_path)
    apply_case(root, 'missing_terminator')
    without_cache(root)
    result = load(root)
    assert result.status == 'error' and result.issues[0].code == 'MissingTerminator'


@pytest.mark.parametrize('mutation', ['executed', 'matched', 'completed', 'database', 'assurance', 'classification', 'mode'])
def test_rebound_synthetic_header_cannot_claim_real_execution(tmp_path, mutation):
    root = copy_input(tmp_path)
    path = root / 'query/header.json'
    header = read_json(path)
    if mutation == 'executed':
        header['tool'] = {'name': 'Calibre', 'version': '2026.1', 'executed': True}
    elif mutation == 'matched':
        header['lvs_match_status'] = 'matched'
    elif mutation == 'completed':
        header['lvs_completion_status'] = 'completed'
    elif mutation == 'database':
        header['query_database_id'] = 'pretend-db'
    elif mutation == 'assurance':
        header['assurance'] = 'matched'
    elif mutation == 'classification':
        header['classification'] = 'tool_captured'
    else:
        header['mode'] = 'calibre'
    write_json(path, header)
    rebind(root)
    result = load(root)
    assert result.status == 'error'
    issue = result.issues[0]
    assert issue.category in ('binding', 'config', 'unsupported')
    assert 'HashMismatch' not in issue.code
    assert issue.source.uri.endswith('query/header.json')
    assert issue.source.field is not None


@pytest.mark.parametrize('missing', ['tech/physical.json', 'query/requests.json', 'source.cdl', 'body/context.json'])
def test_missing_closure_member_rejected_after_digest_rebinding(tmp_path, missing):
    root = copy_input(tmp_path)
    path = root / 'query/header.json'
    header = read_json(path)
    header['closure']['entries'] = [x for x in header['closure']['entries'] if x['uri'] != missing]
    write_json(path, header)
    rebind(root)
    result = load(root)
    assert result.status == 'error'
    assert result.issues[0].category == 'binding'
    assert 'HashMismatch' not in result.issues[0].code
    assert result.issues[0].source.field is not None


def test_second_legal_input_reads_changed_bytes_names_order_and_coordinates(tmp_path):
    root = copy_input(tmp_path)
    changed = renamed_input(root)
    value = success(load(root))
    assert value['gds']['top'] == changed['top']
    expected_coordinates = read_json(FIXTURE / 'independent-design-answer.json')['local_scope']['coordinates']
    expected = Counter((s['layer'], tuple(v + (changed['dx'] if i % 2 == 0 else changed['dy']) for i, v in enumerate(s['bbox']))) for s in expected_coordinates.values())
    actual = Counter((s['canonical_layer'], tuple(s['bbox'])) for s in value['gds']['elements'])
    assert actual == expected
    first = value['source_cdl']['tops'][0]
    assert first['name'] == changed['top']
    device = next(d for d in first['devices'] if d['name'] == changed['device'])
    assert exact(device['parameters']['NFIN']['exact']) == 6
    region = value['query']['device_regions']['records'][0]
    assert [(exact(p['x']), exact(p['y'])) for p in region['vertices_nm']] == [(68, 17), (68, 67), (72, 67), (72, 17)]
    assert value['header']['header_id'] == 'second.synthetic.query'
    assert all('capture_' in ref['uri'] for ref in value['header']['raw'])
    # A targeted later defect still reports its actual new source path.
    raw_path = root / changed['paths']['query/raw/device_info_Q17.txt']
    raw_path.write_text(raw_path.read_text().replace('END OF RESPONSE\n', ''))
    rebind(root)
    failed = load(root)
    assert failed.status == 'error' and failed.issues[0].code == 'MissingTerminator'
    assert failed.issues[0].source.uri.endswith(str(raw_path.relative_to(root)))


@pytest.mark.parametrize('failure', [KeyboardInterrupt, SystemExit, RuntimeError])
def test_interrupts_and_unexpected_errors_preserve_root_cause(monkeypatch, failure):
    original_open = io.open

    def broken(file, *args, **kwargs):
        if isinstance(file, (str, Path)) and Path(file).name == 'site_config.yaml':
            raise failure('injected-root-cause')
        return original_open(file, *args, **kwargs)

    monkeypatch.setattr(io, 'open', broken)
    with pytest.raises(failure, match='injected-root-cause'):
        load(FIXTURE)


@pytest.mark.parametrize('missing', ['source.gds', 'source.cdl', 'target.cdl', 'query/header.json', 'query/raw/nXref.temp', 'tech/physical.json'])
def test_missing_selected_input_is_localized_without_invented_hash(tmp_path, missing):
    root = copy_input(tmp_path)
    (root / missing).unlink()
    result = load(root)
    assert result.status == 'error'
    issue = result.issues[0]
    assert issue.category == 'read'
    assert issue.source.uri.endswith(missing)
    assert issue.source.sha256 is None


def test_query_fractional_raw_tick_is_preserved_exactly(tmp_path):
    root = copy_input(tmp_path)
    path = root / 'query/raw/device_info_Q17.txt'
    # Move both left vertices one raw tick right, retaining a legal rectangle.
    path.write_text(path.read_text().replace('1160', '1161'))
    without_cache(root)
    rebind(root)
    value = success(load(root))
    region = value['query']['device_regions']['records'][0]
    assert [exact(p['x']) for p in region['vertices_nm']] == [Fraction(1161, 20), Fraction(1161, 20), 62, 62]
