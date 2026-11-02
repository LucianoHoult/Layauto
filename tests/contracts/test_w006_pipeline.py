"""W006 actual-file contracts: identity, caller binding, ready/failure and recovery."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from layauto_v2.domain.publication import (
    InputsReady, PipelineResult, PublicationUnavailable, RunRequest,
    RunRecordFreezeFailureClosure, Selection, WithRunRecordClosure,
)
from layauto_v2.domain.publication_codec import content_ref, decode_record, encode_record
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository, RepositoryConflict

from w005_cases import FIXTURE, apply_case, copy_input, rebind, renamed_input
from w006_cases import byte_sha, caller_request, rename_site


def failure_chain(repository, result):
    assert isinstance(result, PipelineResult), result
    assert result.lifecycle_status == 'terminal'
    assert result.deployment_disposition == 'reject'
    attempt = repository.load_attempt(result.run_id)
    assert attempt.phase == 'terminal' and attempt.terminal_ref == result.ref
    assert repository.read_terminal(result.run_id) == result
    checkpoint = repository.load_checkpoint(result.run_id)
    assert checkpoint.outcome == 'failure'
    closure = repository.read(result.closure_ref)
    failure = repository.read(closure.failure_ref)
    assert failure.completed == checkpoint.completed == closure.completed
    assert failure.run_id == result.run_id
    assert closure.failure_ref == checkpoint.failure_ref
    if isinstance(closure, WithRunRecordClosure):
        record = repository.read(closure.run_record_ref)
        assert record.status == 'precontext_failure'
        assert record.run_id == result.run_id
        assert record.completed == checkpoint.completed
        assert record.failure_ref == closure.failure_ref
        for absent in ('canonical_context', 'final_snapshot_id', 'manifest_ref',
                       'validation_ref', 'ordered_commit_ids'):
            assert not hasattr(record, absent)
    for ref in checkpoint.completed:
        record = repository.read(ref)
        assert record.run_id == result.run_id
        assert content_ref(record) == ref
        assert decode_record(encode_record(record)) == record
    return checkpoint, closure, failure


@pytest.mark.parametrize('case', ['normal', 'missing_site', 'bad_site'])
def test_attempt_is_created_before_any_actual_read_or_parse(tmp_path, monkeypatch, case):
    from layauto_v2.importers import reader

    root = copy_input(tmp_path)
    if case == 'missing_site':
        (root / 'site_config.yaml').unlink()
    elif case == 'bad_site':
        (root / 'site_config.yaml').write_bytes(b'{broken')
    request = RunRequest('ordered-run', 'ordered-lineage', 'create', str(root / 'site_config.yaml'))
    repository = PublicationRepository()
    events = []
    create = repository.create_attempt
    read_bytes = Path.read_bytes
    load_document = reader.load_document

    def create_spy(value):
        events.append('create')
        attempt = create(value)
        assert attempt.revision == 0 and attempt.phase == 'unsealed'
        assert attempt.terminal_ref is None and attempt.checkpoint_ref is None
        return attempt

    def read_spy(path):
        assert repository.load_attempt(request.run_id).run_id == request.run_id
        events.append('read')
        return read_bytes(path)

    def parse_spy(*args, **kwargs):
        assert repository.load_attempt(request.run_id).run_id == request.run_id
        events.append('parse')
        return load_document(*args, **kwargs)

    monkeypatch.setattr(repository, 'create_attempt', create_spy)
    monkeypatch.setattr(Path, 'read_bytes', read_spy)
    monkeypatch.setattr(reader, 'load_document', parse_spy)
    result = prepare_inputs(repository, request)
    assert events[0] == 'create' and 'read' in events
    if case == 'normal':
        assert isinstance(result, InputsReady)
        assert 'parse' in events
    else:
        checkpoint, _, failure = failure_chain(repository, result)
        tool = repository.read(checkpoint.tool_ref)
        if case == 'missing_site':
            assert failure.category == 'read' and failure.source.sha256 is None
            assert tool.execution_status == 'error' and not tool.sources
        else:
            assert failure.category in ('config', 'parse')
            assert tool.execution_status == 'completed'
            assert tool.sources[0].data == b'{broken'


def test_create_failure_does_not_read_or_parse(tmp_path, monkeypatch):
    from layauto_v2.importers import reader

    def fault(point):
        if point == 'create.before_switch':
            raise OSError('create storage unavailable')

    request = RunRequest('not-created', 'lineage', 'key', str(tmp_path / 'site'))
    repository = PublicationRepository(fault_injector=fault)

    def forbidden(*args, **kwargs):
        pytest.fail('acquisition or parser ran without a created attempt')

    monkeypatch.setattr(Path, 'read_bytes', forbidden)
    monkeypatch.setattr(reader, 'load_document', forbidden)
    result = prepare_inputs(repository, request)
    assert isinstance(result, PublicationUnavailable)
    assert result.attempt is None
    assert not result.completed
    with pytest.raises(RepositoryConflict) as missing:
        repository.load_attempt(request.run_id)
    assert missing.value.code == 'MissingAttempt'


def test_f1_full_caller_request_ready_is_unsealed_and_all_refs_resolve(tmp_path, monkeypatch):
    root = copy_input(tmp_path)
    request = caller_request(root)
    assert tuple(map(len, (request.raw_input_selections, request.raw_capture_selections,
                          request.config_policy_selections))) == (5, 9, 13)
    before = request.digest
    read_bytes = Path.read_bytes
    reads = []

    def actual_inputs_only(path):
        assert not {'examples', 'expected'} & set(path.parts)
        assert path.name not in ('records.json', 'oracle.json', 'spec.json', 'independent-design-answer.json')
        reads.append(path)
        return read_bytes(path)

    repository = PublicationRepository()
    with monkeypatch.context() as patch:
        patch.setattr(Path, 'read_bytes', actual_inputs_only)
        result = prepare_inputs(repository, request)
    assert isinstance(result, InputsReady)
    assert result.status == 'inputs_ready' and result.run_id == request.run_id
    assert result.attempt.request == request and request.digest == before
    assert result.attempt.phase == 'unsealed' and result.attempt.terminal_ref is None
    assert repository.read_terminal(request.run_id) is None
    assert not hasattr(result, 'deployment_disposition')
    assert not hasattr(result, 'lifecycle_status')
    assert not hasattr(result.attempt, 'canonical_context')
    checkpoint = repository.load_checkpoint(request.run_id)
    assert checkpoint.outcome == 'inputs_ready'
    assert checkpoint.failure_ref is None and checkpoint.finalize_request is None
    tool = repository.read(result.tool_ref)
    parse = repository.read(result.parse_ref)
    assert tool.mode == 'dummy_fixture' and tool.tool_name == 'fixture-reader'
    assert tool.execution_status == 'completed'
    assert not hasattr(tool, 'parse_ref') and not hasattr(tool, 'findings')
    assert parse.tool_ref == result.tool_ref
    assert parse.result.tool_run_id == tool.tool_run_id
    assert parse.result.status == 'success' and parse.result.value == result.value
    assert len(tool.sources) == len(reads) == 31
    assert all(count == 1 for count in Counter(reads).values())
    assert parse.result.sources == tool.sources
    by_uri = {source.uri: source for source in tool.sources}
    for selection in request.selections:
        assert by_uri[selection.uri].sha256 == selection.declared_sha256
    for ref in checkpoint.completed:
        value = repository.read(ref)
        assert content_ref(value) == ref
        assert decode_record(encode_record(value)) == value
    assert len(result.evidence_refs) == len(parse.result.completed)
    assert decode_record(encode_record(request)) == request
    assert decode_record(encode_record(result)) == result
    with pytest.raises((TypeError, FrozenInstanceError, AttributeError)):
        result.value['gds']['elements'][0]['bbox'] = (0, 0, 0, 0)
    with pytest.raises((TypeError, FrozenInstanceError, AttributeError)):
        result.attempt.request.raw_descriptor['caller'] = 'changed'
    assert request.digest == before


def test_f1_request_independently_matches_accepted_sample(tmp_path):
    root = copy_input(tmp_path)
    request = caller_request(root)
    path = Path(__file__).resolve().parents[2] / 'docs/tasks/W003/examples/records.json'
    samples = json.loads(path.read_text(encoding='utf-8'))['records']
    attempt = next(record for record in samples if record.get('kind') == 'RunAttempt'
                   and record.get('variant') == 'unsealed')
    raw = attempt['raw_request_descriptor']
    for name in ('raw_input_selections', 'raw_capture_selections', 'config_policy_selections'):
        declared = {selection.uri: selection.declared_sha256 for selection in getattr(request, name)}
        expected = {selection['path']: selection['actual_byte_sha256'] for selection in raw[name]}
        assert declared == expected


def test_f2_real_missing_terminator_has_same_run_bytes_and_failure_chain(tmp_path):
    root = copy_input(tmp_path)
    apply_case(root, 'missing_terminator')
    raw_path = root / 'query/raw/device_info_Q17.txt'
    raw = raw_path.read_bytes()
    assert b'END OF RESPONSE' not in raw
    assert byte_sha(raw_path) == '5e1ef71218be96a097fa261772bd6cede4ec244d65af9dc1a44e50034e7e7073'
    header = json.loads((root / 'query/header.json').read_text())
    assert next(item for item in header['raw'] if item['uri'] == 'query/raw/device_info_Q17.txt')['sha256'] == byte_sha(raw_path)
    request = caller_request(root)
    repository = PublicationRepository()
    result = prepare_inputs(repository, request)
    checkpoint, closure, failure = failure_chain(repository, result)
    assert isinstance(closure, WithRunRecordClosure)
    assert failure.category == 'parse' and failure.code == 'MissingTerminator'
    assert failure.source.uri == 'query/raw/device_info_Q17.txt'
    assert failure.source.sha256 == hashlib.sha256(raw).hexdigest()
    assert failure.source.line is not None or failure.source.byte_offset is not None
    tool = repository.read(checkpoint.tool_ref)
    parse = repository.read(checkpoint.parse_ref)
    assert tool.execution_status == 'completed' and tool.mode == 'dummy_fixture'
    assert parse.result.status == 'error'
    assert parse.result.issues[0].code == 'MissingTerminator'
    assert parse.result.tool_run_id == tool.tool_run_id
    assert parse.tool_ref == checkpoint.tool_ref
    source = next(source for source in tool.sources if source.uri == failure.source.uri)
    assert source.data == raw
    assert source in parse.result.sources
    assert {repository.read(ref).evidence.kind for ref in checkpoint.evidence_refs} >= {
        'config', 'tech', 'policies', 'header', 'gds', 'source_cdl', 'target_cdl', 'body'}
    assert not any(repository.read(ref).evidence.kind == 'query' for ref in checkpoint.evidence_refs)


def test_second_legal_names_paths_and_changed_site_filename(tmp_path):
    root = copy_input(tmp_path)
    renamed = renamed_input(root)
    site_name = rename_site(root)
    request = caller_request(root, run_id='renamed-run', site_name=site_name)
    repository = PublicationRepository()
    result = prepare_inputs(repository, request)
    assert isinstance(result, InputsReady)
    assert result.value['gds']['top'] == renamed['top']
    assert len(request.selections) == 27
    assert all('capture_' in selection.uri for selection in request.raw_capture_selections)
    tool = repository.read(result.tool_ref)
    assert len(tool.sources) == 27
    assert any(source.uri == site_name for source in tool.sources)
    assert repository.read_terminal(request.run_id) is None


def test_caller_declared_hash_drift_does_not_rewrite_frozen_request(tmp_path):
    root = copy_input(tmp_path)
    request = caller_request(root)
    before = request.digest
    with (root / 'source.cdl').open('ab') as stream:
        stream.write(b'\n* modified after caller selection\n')
    rebind(root)
    repository = PublicationRepository()
    result = prepare_inputs(repository, request)
    checkpoint, _, failure = failure_chain(repository, result)
    assert failure.category == 'binding' and 'Drift' in failure.code
    assert failure.source.sha256 is not None
    assert request.digest == before
    assert repository.load_attempt(request.run_id).request == request
    assert any(selection.declared_sha256 != byte_sha(root / selection.uri)
               for selection in request.selections)
    parse = repository.read(checkpoint.parse_ref)
    assert parse.result.status == 'success', 'drift must be independently checked against a valid actual input'


def test_same_captured_bytes_feed_tool_and_parser_despite_disk_replacement(tmp_path, monkeypatch):
    root = copy_input(tmp_path)
    request = caller_request(root)
    read_bytes = Path.read_bytes
    captured = {}

    def replacing_read(path):
        data = read_bytes(path)
        if path == root / 'source.gds':
            captured['data'] = data
            path.write_bytes(b'disk changed immediately after acquisition')
        return data

    repository = PublicationRepository()
    monkeypatch.setattr(Path, 'read_bytes', replacing_read)
    result = prepare_inputs(repository, request)
    assert isinstance(result, InputsReady)
    tool = repository.read(result.tool_ref)
    parse = repository.read(result.parse_ref)
    source = next(source for source in tool.sources if source.uri == 'source.gds')
    assert source.data == captured['data']
    assert source.sha256 == hashlib.sha256(captured['data']).hexdigest()
    assert source in parse.result.sources
    assert len(result.value['gds']['elements']) == 40


@pytest.mark.parametrize('boundary', ['read', 'parse'])
def test_unexpected_exception_preserves_cause_and_completed_evidence(tmp_path, monkeypatch, boundary):
    from layauto_v2.importers import reader

    root = copy_input(tmp_path)
    request = caller_request(root)
    repository = PublicationRepository()

    def explode(*args, **kwargs):
        try:
            raise OSError('original infrastructure cause')
        except OSError as cause:
            raise RuntimeError('unexpected boundary failure') from cause

    if boundary == 'parse':
        monkeypatch.setattr(reader, 'parse_query', explode)
    else:
        original = Path.read_bytes

        def read(path):
            if path == root / 'source.gds':
                explode()
            return original(path)

        monkeypatch.setattr(Path, 'read_bytes', read)
    result = prepare_inputs(repository, request)
    checkpoint, _, failure = failure_chain(repository, result)
    assert failure.category == 'internal' and failure.code == 'InternalStageFailure'
    assert [(cause.exception_type, cause.message) for cause in failure.causes] == [
        ('RuntimeError', 'unexpected boundary failure'), ('OSError', 'original infrastructure cause')]
    assert checkpoint.evidence_refs
    tool = repository.read(checkpoint.tool_ref)
    assert tool.execution_status == ('error' if boundary == 'read' else 'completed')


@pytest.mark.parametrize('exception', [KeyboardInterrupt, SystemExit])
@pytest.mark.parametrize('boundary', ['read', 'parse'])
def test_interrupt_is_not_swallowed_and_best_effort_keeps_completed_refs(tmp_path, monkeypatch, exception, boundary):
    from layauto_v2.importers import reader

    root = copy_input(tmp_path)
    request = caller_request(root)
    repository = PublicationRepository()
    original_exception = exception('stop this run')

    def interrupt(*args, **kwargs):
        raise original_exception

    if boundary == 'parse':
        monkeypatch.setattr(reader, 'parse_query', interrupt)
    else:
        original = Path.read_bytes

        def read(path):
            if path == root / 'source.gds':
                interrupt()
            return original(path)

        monkeypatch.setattr(Path, 'read_bytes', read)
    with pytest.raises(exception) as caught:
        prepare_inputs(repository, request)
    assert caught.value is original_exception
    result = repository.read_terminal(request.run_id)
    checkpoint, _, failure = failure_chain(repository, result)
    assert failure.category == 'interrupted'
    assert failure.causes[0].exception_type == exception.__name__
    assert checkpoint.evidence_refs


def test_failed_terminal_publication_resumes_checkpoint_without_reading_changed_files(tmp_path, monkeypatch):
    root = copy_input(tmp_path)
    apply_case(root, 'missing_terminator')
    request = caller_request(root)
    blocked = True

    def fault(point):
        if blocked and point == 'finalize.before_switch':
            raise OSError('terminal storage unavailable')

    repository = PublicationRepository(fault_injector=fault)
    result = prepare_inputs(repository, request)
    assert isinstance(result, PublicationUnavailable)
    assert repository.read_terminal(request.run_id) is None
    checkpoint = repository.load_checkpoint(request.run_id)
    assert checkpoint.outcome == 'failure'
    first_finalize = checkpoint.finalize_request
    first_tool = repository.read(checkpoint.tool_ref)
    (root / 'query/raw/device_info_Q17.txt').write_bytes(b'new bytes must never replace captured bytes')
    blocked = False

    def no_reread(*args, **kwargs):
        pytest.fail('retry must reuse the original checkpoint without IO')

    monkeypatch.setattr(Path, 'read_bytes', no_reread)
    retried = prepare_inputs(repository, request)
    recovered, _, failure = failure_chain(repository, retried)
    assert recovered == checkpoint and recovered.finalize_request == first_finalize
    assert repository.read(checkpoint.tool_ref) == first_tool
    assert failure.code == 'MissingTerminator'


def test_audit_storage_failure_keeps_pending_facts_without_published_refs(tmp_path):
    root = copy_input(tmp_path)
    apply_case(root, 'missing_terminator')
    request = caller_request(root)

    def fault(point):
        if point == 'audits.before_switch':
            raise OSError('audit storage unavailable')

    repository = PublicationRepository(fault_injector=fault)
    result = prepare_inputs(repository, request)
    assert isinstance(result, PublicationUnavailable)
    assert result.attempt.phase == 'unsealed' and result.attempt.revision == 0
    assert repository.load_checkpoint(request.run_id) is None
    assert repository.read_terminal(request.run_id) is None
    assert not result.completed
    assert result.pending_tool.sources and result.pending_evidence
    assert result.pending_parse.issues[0].code == 'MissingTerminator'
    assert result.pending_failure.code == 'MissingTerminator'
    assert not result.pending_failure.completed


@pytest.mark.parametrize('exception', [KeyboardInterrupt, SystemExit])
def test_failed_diagnostics_and_readback_cannot_replace_original_interrupt(tmp_path, monkeypatch, exception):
    from layauto_v2.importers import reader

    root = copy_input(tmp_path)
    request = caller_request(root)
    repository = PublicationRepository()
    original_exception = exception('original caller interruption')
    unavailable = False
    load_checkpoint = repository.load_checkpoint

    def interrupt(*args, **kwargs):
        raise original_exception

    def fail_audit(*args, **kwargs):
        nonlocal unavailable
        unavailable = True
        raise OSError('diagnostic storage failed')

    def fail_readback(run_id):
        if unavailable:
            raise OSError('diagnostic readback failed')
        return load_checkpoint(run_id)

    monkeypatch.setattr(reader, 'parse_query', interrupt)
    monkeypatch.setattr(repository, 'record_audits', fail_audit)
    monkeypatch.setattr(repository, 'load_checkpoint', fail_readback)
    with pytest.raises(exception) as caught:
        prepare_inputs(repository, request)
    assert caught.value is original_exception
    assert unavailable
    assert repository.load_attempt(request.run_id).revision == 0
    assert repository.read_terminal(request.run_id) is None


def test_response_loss_and_unavailable_readback_do_not_claim_terminal_reject(tmp_path, monkeypatch):
    root = copy_input(tmp_path)
    apply_case(root, 'missing_terminator')
    request = caller_request(root)
    offline = False

    def fault(point):
        nonlocal offline
        if point == 'finalize.after_switch':
            offline = True
            raise OSError('response lost and storage is unavailable')

    repository = PublicationRepository(fault_injector=fault)
    read_terminal = repository.read_terminal
    load_attempt = repository.load_attempt
    load_checkpoint = repository.load_checkpoint

    def read_when_online(method):
        def read(run_id):
            if offline:
                raise OSError('readback unavailable')
            return method(run_id)
        return read

    monkeypatch.setattr(repository, 'read_terminal', read_when_online(read_terminal))
    monkeypatch.setattr(repository, 'load_attempt', read_when_online(load_attempt))
    monkeypatch.setattr(repository, 'load_checkpoint', read_when_online(load_checkpoint))
    first = prepare_inputs(repository, request)
    assert isinstance(first, PublicationUnavailable)
    assert not hasattr(first, 'deployment_disposition')
    assert first.attempt is None and not first.completed
    offline = False

    def no_reread(*args, **kwargs):
        pytest.fail('published retry must recover references without reading files')

    monkeypatch.setattr(Path, 'read_bytes', no_reread)
    recovered = prepare_inputs(repository, request)
    _, _, failure = failure_chain(repository, recovered)
    assert failure.code == 'MissingTerminator'


@pytest.mark.parametrize('point', ['create.after_switch', 'audits.after_switch', 'finalize.after_switch'])
def test_response_loss_retains_one_run_and_replays_original_result(tmp_path, monkeypatch, point):
    root = copy_input(tmp_path)
    apply_case(root, 'missing_terminator')
    request = caller_request(root)
    triggered = []

    def fault(actual):
        if actual == point and not triggered:
            triggered.append(actual)
            raise OSError('response lost after publication')

    repository = PublicationRepository(fault_injector=fault)
    first = prepare_inputs(repository, request)
    assert triggered == [point]
    if isinstance(first, PublicationUnavailable):
        first = prepare_inputs(repository, request)
    checkpoint, _, _ = failure_chain(repository, first)

    def no_reread(*args, **kwargs):
        pytest.fail('completed request was re-executed after response loss')

    monkeypatch.setattr(Path, 'read_bytes', no_reread)
    repeated = prepare_inputs(repository, request)
    assert repeated == first
    assert repository.load_checkpoint(request.run_id) == checkpoint
    # Idempotent finalize must be checked before terminal/revision guards.
    assert repository.finalize_precontext_failure(checkpoint.finalize_request) == first


def test_run_record_freeze_failure_uses_only_special_closure(tmp_path):
    root = copy_input(tmp_path)
    apply_case(root, 'missing_terminator')
    request = caller_request(root)

    def fault(point):
        if point == 'finalize.freeze':
            raise RuntimeError('record construction failed')

    repository = PublicationRepository(fault_injector=fault)
    result = prepare_inputs(repository, request)
    checkpoint, closure, failure = failure_chain(repository, result)
    assert isinstance(closure, RunRecordFreezeFailureClosure)
    assert closure.closure_kind == 'run_record_freeze_failure'
    assert not hasattr(closure, 'run_record_ref')
    assert failure.code == 'MissingTerminator'
    freeze_failure = repository.read(closure.freeze_failure_ref)
    assert freeze_failure.category == 'run_record_freeze'
    assert freeze_failure.completed == checkpoint.completed
    assert freeze_failure.causes[0].message == 'record construction failed'


def test_request_is_frozen_without_mutable_alias_and_explicit_path_is_required(tmp_path):
    descriptor = {'nested': [{'value': 1}]}
    selections = [Selection('site', None)]
    request = RunRequest('run', 'lineage', 'key', str(tmp_path / 'site'),
                         config_policy_selections=selections, raw_descriptor=descriptor)
    before = request.digest
    descriptor['nested'][0]['value'] = 99
    selections.clear()
    assert request.raw_descriptor['nested'][0]['value'] == 1
    assert len(request.config_policy_selections) == 1
    assert request.digest == before
    with pytest.raises(ValueError, match='absolute'):
        replace(request, site_path='relative-site.yaml')


def test_absolute_request_survives_changed_working_directory(tmp_path, monkeypatch):
    root = copy_input(tmp_path)
    request = caller_request(root)
    unrelated = tmp_path / 'unrelated'
    unrelated.mkdir()
    monkeypatch.chdir(unrelated)
    result = prepare_inputs(PublicationRepository(), request)
    assert isinstance(result, InputsReady)
    assert result.attempt.request.site_path == str(root / 'site_config.yaml')


def test_binding_uses_capture_time_path_when_symlink_changes_after_parsing(tmp_path, monkeypatch):
    from layauto_v2.importers import reader

    root = copy_input(tmp_path)
    selected = root / 'source.cdl'
    captured_path = root / 'captured-source.cdl'
    selected.rename(captured_path)
    selected.symlink_to(captured_path.name)
    replacement = root / 'later-source.cdl'
    replacement.write_bytes(b'these later bytes were never acquired')
    request = caller_request(root)
    parse_query = reader.parse_query

    def change_link_after_prior_bindings(*args, **kwargs):
        result = parse_query(*args, **kwargs)
        selected.unlink()
        selected.symlink_to(replacement.name)
        return result

    monkeypatch.setattr(reader, 'parse_query', change_link_after_prior_bindings)
    repository = PublicationRepository()
    result = prepare_inputs(repository, request)
    assert isinstance(result, InputsReady)
    tool = repository.read(result.tool_ref)
    event = next(event for event in tool.events if event.uri == 'source.cdl')
    source = next(source for source in tool.sources if source.uri == 'source.cdl')
    assert event.path == str(captured_path)
    assert selected.resolve() == replacement
    assert source.data == captured_path.read_bytes()
    assert source.sha256 == next(s.declared_sha256 for s in request.selections if s.uri == 'source.cdl')


def test_concurrent_same_request_uses_one_acquisition_and_one_checkpoint(tmp_path, monkeypatch):
    root = copy_input(tmp_path)
    request = caller_request(root)
    repository = PublicationRepository()
    read_bytes = Path.read_bytes
    reads = []

    def read_once(path):
        reads.append(path)
        return read_bytes(path)

    monkeypatch.setattr(Path, 'read_bytes', read_once)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = tuple(pool.map(lambda _: prepare_inputs(repository, request), range(4)))
    assert all(isinstance(result, InputsReady) for result in results)
    assert all(result == results[0] for result in results)
    assert len(reads) == 31 and len(set(reads)) == 31
    assert repository.load_attempt(request.run_id).revision == results[0].attempt.revision


def test_successful_parse_rejects_declared_selection_that_was_never_read(tmp_path):
    root = copy_input(tmp_path)
    request = caller_request(root)
    extra = Selection('unselected.txt', None)
    request = replace(request, config_policy_selections=request.config_policy_selections + (extra,))
    repository = PublicationRepository()
    result = prepare_inputs(repository, request)
    checkpoint, _, failure = failure_chain(repository, result)
    assert failure.category == 'binding' and failure.code == 'UnreadSelection'
    assert failure.source.uri == extra.uri and failure.source.sha256 is None
    assert repository.read(checkpoint.parse_ref).result.status == 'success'
