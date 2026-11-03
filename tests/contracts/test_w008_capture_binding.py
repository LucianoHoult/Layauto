"""Captured-byte and source-role checks independent of base projection math."""
from __future__ import annotations

import builtins
import hashlib
import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from layauto_v2.domain.evidence import SourceFile
from layauto_v2.domain.publication import InputsReady
from layauto_v2.domain.results import InputError
from layauto_v2.normalization import from_parse_result, normalize
from layauto_v2.normalization.geometry_input import (
    GeometryInput, GeometryInputError, geometry_from_inputs_ready,
    geometry_from_normalization_input, geometry_from_parse_result,
)
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository
from w005_cases import FIXTURE, apply_case, copy_input, inventory, read_json, rebind, write_json
from w006_cases import caller_request
from w007_cases import mutable, read, ready_copy


@pytest.fixture(scope='module')
def captured():
    return read(FIXTURE)


def forged_payload(parsed, kind, mutate):
    """Change both downstream copies, retaining the exact original captures."""
    value = mutable(parsed.value)
    mutate(value[kind])
    payload = {'bundle': value['tech_bundle'], 'owners': value['tech']} if kind == 'tech' else value[kind]
    completed = tuple(replace(item, payload=payload) if item.kind == kind else item for item in parsed.completed)
    return replace(parsed, value=value, completed=completed)


def captured_document(parsed, kind, mutate):
    """Author changed document bytes and rebinding; no product decoder/golden.

    W007 accepts these schema-valid, cross-document-inconsistent receipts. W008
    must reject their specific relation, beyond comparing raw and derived maps.
    """
    value = mutable(parsed.value)
    mutate(value[kind])
    source = next(s for s in parsed.sources if s.uri == next(r for r in parsed.completed if r.kind == kind).sources[0].uri)
    changed = SourceFile(source.uri, (json.dumps(value[kind], indent=2) + '\n').encode())
    if kind != 'header':
        for entry in value['header']['closure']['entries']:
            if entry['uri'] == source.uri:
                entry['sha256'] = changed.sha256
        closure_bytes = json.dumps(value['header']['closure']['entries'], sort_keys=True,
                                   separators=(',', ':'), ensure_ascii=False).encode()
        value['header']['closure']['sha256'] = hashlib.sha256(closure_bytes).hexdigest()
    header_source = next(s for s in parsed.sources if s.uri == next(r for r in parsed.completed if r.kind == 'header').sources[0].uri)
    new_header = SourceFile(header_source.uri, (json.dumps(value['header'], indent=2) + '\n').encode())
    replacements = {source.uri: changed, header_source.uri: new_header}
    sources = tuple(replacements.get(s.uri, s) for s in parsed.sources)
    completed = tuple(replace(r, payload=value[r.kind] if r.kind in (kind, 'header') else r.payload,
                              sources=tuple(replacements[ref.uri].ref() if ref.uri in replacements else ref for ref in r.sources))
                      for r in parsed.completed)
    return replace(parsed, value=value, completed=completed, sources=sources)


def forbidden(*args, **kwargs):
    pytest.fail('captured geometry adapter must not acquire/resolve/publish')


def test_actual_capture_complete_geometry_and_semantics_remain_separate_without_io(captured, monkeypatch):
    before = inventory(FIXTURE)
    semantic = from_parse_result(captured)
    normalized_before = normalize(semantic)
    with monkeypatch.context() as patch:
        for name in ('open', 'read_bytes', 'read_text', 'resolve'):
            patch.setattr(Path, name, forbidden)
        patch.setattr(builtins, 'open', forbidden)
        adapted = geometry_from_normalization_input(semantic)
        assert adapted.semantic_input is semantic
        assert adapted.parse is captured
        assert adapted.value is captured.value
        assert normalize(adapted.semantic_input) == normalized_before
    assert len(adapted.value['gds']['elements']) == 40
    assert len(adapted.value['body']['shapes']) == 6
    assert adapted.readback is None
    assert inventory(FIXTURE) == before
    with pytest.raises(FrozenInstanceError):
        adapted.semantic_input = None
    for change in ({'schema_version': 'bad'}, {'semantic_input': captured}):
        with pytest.raises(ValueError):
            replace(adapted, **change)


@pytest.mark.parametrize('field,change', [
    ('xy', lambda e: e['xy'][0].__setitem__(0, -999)),
    ('bbox', lambda e: e.__setitem__('bbox', [-999, -999, 999, 999])),
    ('layer', lambda e: e.__setitem__('layer', 1)),
    ('datatype', lambda e: e.__setitem__('datatype', 99)),
    ('canonical_layer', lambda e: e.__setitem__('canonical_layer', 'FIN')),
    ('element', lambda e: e.__setitem__('element', 'BOX')),
    ('byte_offset', lambda e: e.__setitem__('byte_offset', 1)),
    ('record_index', lambda e: e.__setitem__('record_index', 999)),
    ('xy_byte_offset', lambda e: e.__setitem__('xy_byte_offset', 1)),
    ('xy_record_index', lambda e: e.__setitem__('xy_record_index', 999)),
    ('byte_length', lambda e: e.__setitem__('byte_length', 999)),
])
def test_coherent_gds_element_forgery_rejects_original_capture(captured, field, change):
    forged = forged_payload(captured, 'gds', lambda doc: change(doc['elements'][0]))
    # The W007 receipt alone is intentionally insufficient for geometry.
    semantic = from_parse_result(forged)
    with pytest.raises(GeometryInputError) as caught:
        GeometryInput(semantic)
    assert caught.value.issue.source.uri == 'source.gds'
    assert caught.value.issue.source.field == '/gds'
    assert caught.value.completed == forged.completed


@pytest.mark.parametrize('mutation', ['top', 'library', 'metadata', 'omit', 'duplicate', 'units', 'raw', 'count', 'unknown'])
def test_coherent_full_gds_forgery_is_bound_to_raw_bytes(captured, mutation):
    def change(doc):
        if mutation == 'top': doc['top'] = 'FORGED'
        elif mutation == 'library': doc['library'] = 'FORGED'
        elif mutation == 'metadata': doc['cell_timestamps'] = bytes(24)
        elif mutation == 'omit': doc['elements'].pop()
        elif mutation == 'duplicate': doc['elements'].append(doc['elements'][0])
        elif mutation == 'units': doc['units']['metres_per_tick']['nominal'] *= 2
        elif mutation == 'raw': doc['raw_document'] += b'forged'
        elif mutation == 'count': doc['stream_record_count'] += 1
        else: doc['invented'] = 'field'
    forged = forged_payload(captured, 'gds', change)
    with pytest.raises(GeometryInputError):
        geometry_from_parse_result(forged)


@pytest.mark.parametrize('owner,field,value', [
    ('drawn', 'layers', []),
    ('derived', 'derived_registry', []),
    ('physical', 'operators', {}),
    ('formats', 'geometry_capability', {}),
    ('coordinate', 'coordinate_projection', {}),
    ('rules', 'rules', []),
])
def test_each_coherently_forged_owner_is_redecoded(captured, owner, field, value):
    # Some malformed owners fail in W007 first; both boundaries must reject.
    forged = forged_payload(captured, 'tech', lambda tech: tech[owner].__setitem__(field, value))
    with pytest.raises(ValueError):
        geometry_from_parse_result(forged)


@pytest.mark.parametrize('field,new_value', [('tier', 'A'), ('role', 'marker'),
                                           ('projection_kind', 'exact_fragment_rectangles'),
                                           ('purpose', 'annotation'), ('lifecycle', 'preserve_drawn')])
def test_valid_but_uncaptured_layer_policy_is_not_trusted(captured, field, new_value):
    forged = forged_payload(captured, 'tech', lambda tech: tech['drawn']['layers'][0].__setitem__(field, new_value))
    semantic = from_parse_result(forged)
    with pytest.raises(GeometryInputError) as caught:
        GeometryInput(semantic)
    assert caught.value.issue.source.field == '/tech'


def test_bundle_owner_declaration_and_policies_are_bound_to_raw(captured):
    value = mutable(captured.value)
    value['tech_bundle']['profile_id'] = 'forged-profile'
    completed = tuple(replace(r, payload={'bundle': value['tech_bundle'], 'owners': value['tech']})
                      if r.kind == 'tech' else r for r in captured.completed)
    with pytest.raises(GeometryInputError):
        geometry_from_parse_result(replace(captured, value=value, completed=completed))
    forged = forged_payload(captured, 'policies', lambda policies: policies['limitations'].__setitem__('parser_status', 'forged'))
    with pytest.raises(GeometryInputError):
        geometry_from_parse_result(forged)


@pytest.mark.parametrize('kind,field,new_value', [('config', 'mode', 'calibre'), ('body', 'author', 'forged'),
                                                 ('header', 'geometry_unit_contract', 'forged')])
def test_coherent_metadata_requires_captured_document_bytes(captured, kind, field, new_value):
    forged = forged_payload(captured, kind, lambda doc: doc.__setitem__(field, new_value))
    with pytest.raises(GeometryInputError):
        geometry_from_parse_result(forged)


@pytest.mark.parametrize('kind,field,new_value,expected_field', [
    ('header', 'top_identities', {'layout': 'FOREIGN', 'source': 'INV_M1_SYNTH'}, '/top_identities/layout'),
    ('header', 'geometry_unit_contract', 'foreign/1', '/geometry_unit_contract'),
    ('body', 'top', 'FOREIGN', '/top'),
    ('body', 'profile_ref', 'foreign/1', '/profile_ref'),
    ('body', 'operator_ref', 'foreign/1', '/operator_ref'),
    ('body', 'unit', {'name': 'nm', 'metres_per_tick': {'numerator': '1', 'denominator': '500000000'}}, '/unit'),
])
def test_ir01_cross_document_binding_requires_more_than_independent_redecode(captured, kind, field, new_value, expected_field):
    forged = captured_document(captured, kind, lambda doc: doc.__setitem__(field, new_value))
    semantic = from_parse_result(forged)
    with pytest.raises(GeometryInputError) as caught:
        GeometryInput(semantic)
    assert caught.value.issue.source.field == expected_field
    assert caught.value.completed == forged.completed


@pytest.mark.parametrize('mutation', ['missing', 'extra', 'wrong_second'])
def test_body_source_roles_require_exact_selected_gds_reference(captured, mutation):
    body = next(r for r in captured.completed if r.kind == 'body')
    refs = body.sources
    if mutation == 'missing': refs = refs[:1]
    elif mutation == 'extra': refs = refs + refs[:1]
    else: refs = (refs[0], next(r for r in captured.completed if r.kind == 'source_cdl').sources[0])
    completed = tuple(replace(r, sources=refs) if r.kind == 'body' else r for r in captured.completed)
    with pytest.raises(GeometryInputError):
        geometry_from_parse_result(replace(captured, completed=completed))


def test_same_hash_wrong_gds_role_does_not_hide_behind_content_equality(captured):
    original = next(r for r in captured.completed if r.kind == 'gds')
    source = next(s for s in captured.sources if s.uri == original.sources[0].uri)
    sibling = SourceFile('another-captured-role.gds', source.data)
    value = mutable(captured.value)
    value['gds']['source']['uri'] = sibling.uri
    completed = []
    for record in captured.completed:
        if record.kind == 'gds': record = replace(record, payload=value['gds'], sources=(sibling.ref(),))
        if record.kind == 'body': record = replace(record, sources=(record.sources[0], sibling.ref()))
        completed.append(record)
    forged = replace(captured, value=value, completed=tuple(completed), sources=captured.sources + (sibling,))
    with pytest.raises(GeometryInputError) as caught:
        geometry_from_parse_result(forged)
    assert caught.value.issue.source.field == '/inputs/gds'


@pytest.mark.parametrize('kind,index,field', [
    ('tech', 0, '/tech_ref'),
    ('tech', 1, '/owners/drawn/path'), ('tech', 2, '/owners/derived/path'),
    ('tech', 3, '/owners/physical/path'), ('tech', 4, '/owners/formats/path'),
    ('tech', 5, '/owners/coordinate/path'), ('tech', 6, '/owners/rules/path'),
    ('policies', 0, '/export_policy_ref'), ('policies', 1, '/validation_policy_ref'),
    ('policies', 2, '/limitation_ref'),
    ('gds', 0, '/inputs/gds'), ('source_cdl', 0, '/inputs/source_cdl'),
    ('target_cdl', 0, '/inputs/target_cdl'), ('header', 0, '/inputs/query_header'),
    ('body', 0, '/inputs/body_context'),
])
def test_cr01_absent_first_uri_cannot_be_forged_into_a_historical_alias(captured, kind, index, field):
    record = next(r for r in captured.completed if r.kind == kind)
    original = next(s for s in captured.sources if s.uri == record.sources[index].uri)
    sibling = SourceFile('forged-first-role/' + original.uri, original.data)
    value = mutable(captured.value)

    def relocate_locations(item):
        if isinstance(item, dict):
            if item.get('sha256') == original.sha256:
                for key in ('uri', 'path'):
                    if item.get(key) == original.uri:
                        item[key] = sibling.uri
            for child in item.values():
                relocate_locations(child)
        elif isinstance(item, list):
            for child in item:
                relocate_locations(child)

    # Keep declaration documents and all capture bytes unchanged. Only the
    # role receipt and its derived preservation/source locations are forged.
    if kind in ('gds', 'source_cdl', 'target_cdl'):
        relocate_locations(value[kind])
    if kind == 'tech':
        relocate_locations(value['query'])
    completed = tuple(replace(r,
                              payload={'bundle': value['tech_bundle'], 'owners': value['tech']}
                              if r.kind == 'tech' else value[r.kind],
                              sources=tuple(sibling.ref() if ref.uri == original.uri else ref for ref in r.sources))
                      for r in captured.completed)
    sources = tuple(sibling if source.uri == original.uri else source for source in captured.sources)
    forged = replace(captured, value=value, completed=completed, sources=sources)
    assert original.uri not in {source.uri for source in forged.sources}
    assert original.sha256 == sibling.sha256
    semantic = from_parse_result(forged)
    with pytest.raises(GeometryInputError) as caught:
        GeometryInput(semantic)
    assert caught.value.issue.source.field == field
    assert 'first acquisition URI' in caught.value.issue.message


def test_actual_gds_aliases_preserve_w005_acquisition_identity(tmp_path, monkeypatch):
    root = ready_copy(tmp_path)
    (root / 'layout-alias.gds').symlink_to('source.gds')
    header = read_json(root / 'query/header.json')
    header['layout']['uri'] = 'layout-alias.gds'
    write_json(root / 'query/header.json', header)
    parsed = read(root)
    assert 'layout-alias.gds' not in {s.uri for s in parsed.sources}
    with monkeypatch.context() as patch:
        patch.setattr(Path, 'resolve', forbidden)
        patch.setattr(Path, 'read_bytes', forbidden)
        adapted = geometry_from_parse_result(parsed)
    assert adapted.value['gds']['source']['uri'] == 'source.gds'
    assert adapted.value['header']['layout']['uri'] == 'layout-alias.gds'


def test_actual_owner_alias_and_gds_site_alias_are_not_resolved_again(tmp_path, monkeypatch):
    root = ready_copy(tmp_path)
    (root / 'drawn-alias.json').symlink_to('tech/drawn.json')
    bundle = read_json(root / 'tech.json')
    bundle['owners']['drawn']['path'] = 'drawn-alias.json'
    write_json(root / 'tech.json', bundle)
    (root / 'layout-alias.gds').symlink_to('source.gds')
    site = read_json(root / 'site_config.yaml')
    site['inputs']['gds'] = 'layout-alias.gds'
    write_json(root / 'site_config.yaml', site)
    rebind(root)
    parsed = read(root)
    with monkeypatch.context() as patch:
        patch.setattr(Path, 'resolve', forbidden)
        patch.setattr(Path, 'read_bytes', forbidden)
        adapted = geometry_from_parse_result(parsed)
    assert adapted.value['gds']['source']['uri'] == 'layout-alias.gds'
    assert next(r for r in adapted.parse.completed if r.kind == 'tech').sources[1].uri == 'drawn-alias.json'


def test_actual_target_can_reuse_earlier_source_under_a_later_alias(tmp_path, monkeypatch):
    root = ready_copy(tmp_path)
    (root / 'target.cdl').unlink()
    (root / 'target.cdl').symlink_to('source.cdl')
    header = read_json(root / 'query/header.json')
    # W005's closure contains each resolved file once, although the later target
    # selector legitimately uses another spelling for the earlier CDL capture.
    header['closure']['entries'] = [entry for entry in header['closure']['entries'] if entry['uri'] != 'target.cdl']
    write_json(root / 'query/header.json', header)
    rebind(root)
    parsed = read(root)
    assert 'target.cdl' not in {source.uri for source in parsed.sources}
    records = {record.kind: record for record in parsed.completed}
    assert records['target_cdl'].sources == records['source_cdl'].sources
    with monkeypatch.context() as patch:
        patch.setattr(Path, 'resolve', forbidden)
        patch.setattr(Path, 'read_bytes', forbidden)
        adapted = geometry_from_parse_result(parsed)
    assert adapted.value['config']['inputs']['target_cdl'] == 'target.cdl'
    assert adapted.value['target_cdl']['source']['uri'] == 'source.cdl'


def readback(root, run):
    repository = PublicationRepository()
    ready = prepare_inputs(repository, caller_request(root, run_id=run))
    assert isinstance(ready, InputsReady)
    args = (ready, repository.load_checkpoint(run), repository.read(ready.parse_ref),
            repository.read(ready.tool_ref), tuple(repository.read(ref) for ref in ready.evidence_refs))
    return repository, args


def test_actual_w006_readback_is_equivalent_without_io_or_attempt_changes(tmp_path, monkeypatch):
    root = ready_copy(tmp_path)
    repository, args = readback(root, 'w008-geometry-input')
    direct = geometry_from_parse_result(read(root))
    before = repository.load_attempt(args[0].run_id)
    with monkeypatch.context() as patch:
        patch.setattr(Path, 'read_bytes', forbidden)
        patch.setattr(Path, 'resolve', forbidden)
        patch.setattr(builtins, 'open', forbidden)
        patch.setattr(repository, 'read', forbidden)
        adapted = geometry_from_inputs_ready(*args)
    assert adapted.value == direct.value
    assert adapted.readback is not None
    assert repository.load_attempt(args[0].run_id) == before
    assert repository.read_terminal(args[0].run_id) is None
    assert before.phase == 'unsealed'


@pytest.mark.parametrize('index', range(5))
def test_wrong_run_readback_keeps_w007_receipt_rejection(tmp_path, index):
    root = ready_copy(tmp_path)
    _, first = readback(root, 'w008-first')
    _, second = readback(root, 'w008-second')
    changed = list(first)
    changed[index] = second[index]
    with pytest.raises(ValueError) as caught:
        geometry_from_inputs_ready(*changed)
    assert not isinstance(caught.value, GeometryInputError)


@pytest.mark.parametrize('decoder', ['load_document', 'validate_document', 'validate_tech', 'parse_gds'])
@pytest.mark.parametrize('failure', [TypeError('unexpected'), KeyError('unexpected'), RuntimeError('unexpected'),
                                     KeyboardInterrupt(), SystemExit(21)])
def test_unexpected_decoder_failures_keep_exception_identity(captured, monkeypatch, decoder, failure):
    from layauto_v2.normalization import geometry_input
    semantic = from_parse_result(captured)
    def broken(*args, **kwargs):
        raise failure
    monkeypatch.setattr(geometry_input, decoder, broken)
    with pytest.raises(type(failure)) as caught:
        GeometryInput(semantic)
    assert caught.value is failure


def test_expected_decoder_failure_retains_issue_and_prior_facts(captured, monkeypatch):
    from layauto_v2.normalization import geometry_input
    semantic = from_parse_result(captured)
    source = next(s for s in captured.sources if s.uri == 'source.gds')
    failure = InputError('unsupported', 'UnsupportedNonrectangle', 'test decoder rejection', source.ref(record_index=7))
    def broken(*args):
        raise failure
    monkeypatch.setattr(geometry_input, 'parse_gds', broken)
    with pytest.raises(GeometryInputError) as caught:
        GeometryInput(semantic)
    assert caught.value.issue is failure.issue
    assert caught.value.completed is captured.completed


@pytest.mark.parametrize('case', ['unit_mismatch', 'missing_terminator'])
def test_prior_reader_failures_are_not_relabelled_as_geometry_success(tmp_path, case):
    from layauto_v2.importers import read_inputs
    root = copy_input(tmp_path)
    apply_case(root, case)
    parsed = read_inputs(root / 'site_config.yaml')
    assert parsed.status == 'error'
    with pytest.raises(ValueError) as caught:
        geometry_from_parse_result(parsed)
    assert not isinstance(caught.value, GeometryInputError)
