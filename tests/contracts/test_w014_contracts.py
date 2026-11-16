"""Public W014 reconstruction, source closure and original exception history."""
from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import ast
import hashlib
from pathlib import Path

import pytest

from layauto_v2.domain.codec import FrozenMap, canonical_bytes, decode
from layauto_v2.domain.terminal_relations import TerminalRef, TerminalTarget
from layauto_v2.normalization import terminal_relations as component
from layauto_v2.normalization import terminal_relations_codec as codec
from w013_cases import unchecked_replace
from w014_cases import normal_capture, readback_capture


@pytest.fixture(scope='module')
def accepted():
    return normal_capture()


def test_each_terminal_leaf_has_closed_canonical_roundtrip_and_distinct_device_target(accepted):
    draft = accepted.value
    records = [draft.binding_ref, draft.ref]
    for relation in draft.relations:
        records.extend((relation.target, relation.target.ref, relation, relation.ref))
    for record in records:
        wire = codec.encode_record(record)
        restored = codec.decode_record(wire)
        assert type(restored) is type(record) and restored == record
        assert codec.encode_record(restored) == wire
        assert codec.record_digest(record) == hashlib.sha256(wire).hexdigest()
        with pytest.raises(FrozenInstanceError):
            record.schema_version = 'mutable'
    gates = [row for row in draft.relations if row.target.role == 'G']
    assert gates[0].node_refs == gates[1].node_refs
    assert gates[0].target.ref != gates[1].target.ref


def test_neutral_wire_roundtrip_rebuilds_all_inputs_outputs_and_refs(accepted):
    draft = accepted.value
    wire = codec.encode_record(draft)
    restored = codec.decode_record(wire)
    assert type(restored) is type(draft) and restored == draft
    assert restored.ref == draft.ref and restored.to_value() == draft.to_value()
    assert codec.encode_record(restored) == wire


def test_result_wire_contains_one_complete_unchanged_w010_value_and_all_target_intent(accepted):
    from layauto_v2.normalization.local_connectivity_codec import encode_record
    wire = codec.encode_record(accepted)
    envelope = decode(wire)
    assert canonical_bytes(envelope['captured_input_wire']) == encode_record(accepted.input)
    assert 'input' not in envelope['result'] and 'local' not in envelope['result']
    restored = codec.decode_record(wire)
    assert restored == accepted
    assert restored.semantic_facts.target == accepted.semantic_facts.target
    assert restored.semantic_facts.differences == accepted.semantic_facts.differences
    assert codec.encode_record(restored) == wire
    changed = dict(envelope.items())
    outputs = dict(envelope['result'].items())
    outputs['status'] = 'error'
    changed['result'] = outputs
    with pytest.raises(ValueError):
        codec.decode_record(canonical_bytes(changed))
    changed = dict(envelope.items())
    changed['captured_input_wire'] = FrozenMap({'ref': accepted.input.value.ref.to_value()})
    with pytest.raises(ValueError):
        codec.decode_record(canonical_bytes(changed))


@pytest.mark.parametrize('field', ['relations', 'issues', 'channel_observations', 'body'])
def test_neutral_encoding_rejects_omitted_or_changed_correlated_outputs(accepted, field):
    draft = accepted.value
    if field in ('relations', 'issues'):
        poisoned = () if field == 'relations' else (accepted.input.completed[0],)
    else:
        poisoned = FrozenMap({})
    forged = unchecked_replace(draft, **{field: poisoned})
    with pytest.raises(ValueError):
        codec.encode_record(forged)


def test_result_encoding_rejects_changed_status_instead_of_trusting_frozen_shell(accepted):
    forged = unchecked_replace(accepted, status='error')
    with pytest.raises(ValueError):
        codec.encode_record(forged)


def test_output_from_direct_capture_cannot_be_attached_to_another_valid_run_receipt(accepted):
    readback = readback_capture()[0]
    assert readback.input != accepted.input
    forged = unchecked_replace(accepted, input=readback.input)
    with pytest.raises(ValueError):
        codec.encode_record(forged)


@pytest.mark.parametrize('which', ['result', 'draft', 'leaf'])
def test_new_records_reject_undeclared_retained_fields_instead_of_silently_dropping_them(accepted, which):
    record = (accepted if which == 'result' else accepted.value if which == 'draft'
              else accepted.value.relations[0])
    forged = unchecked_replace(record)
    object.__setattr__(forged, 'unowned_extra', FrozenMap({'unexpected': True}))
    with pytest.raises(ValueError):
        codec.encode_record(forged)


def test_neutral_malformed_selected_source_cell_has_explicit_value_error(accepted):
    from layauto_v2.domain.identifiers import CellId
    draft = accepted.value
    source = unchecked_replace(draft.source, selected_cell=CellId('ABSENT_CELL'))
    with pytest.raises(ValueError):
        replace(draft, source=source)


@pytest.mark.parametrize('field', ['source', 'channel_seeds', 'capture_binding'])
def test_result_codec_cannot_silently_discard_changed_retained_neutral_inputs(accepted, field):
    draft = accepted.value
    changed = (unchecked_replace(draft.source, dialect='forged') if field == 'source'
               else () if field == 'channel_seeds' else FrozenMap({}))
    forged_draft = unchecked_replace(draft, **{field: changed})
    forged = unchecked_replace(accepted, value=forged_draft)
    with pytest.raises(ValueError):
        codec.encode_record(forged)


def test_untyped_map_cannot_impersonate_the_retained_typed_draft(accepted):
    forged = unchecked_replace(accepted, value=codec._stored_value(accepted.value))
    with pytest.raises(ValueError):
        codec.encode_record(forged)


@pytest.mark.parametrize('where', ['source', 'channel', 'net', 'body', 'derived'])
def test_neutral_capture_source_set_must_close_every_consumed_owner_and_seed(accepted, where):
    draft = accepted.value
    if where == 'source':
        reference = draft.source.preservation.sources[0]
    elif where == 'body':
        reference = draft.body_evidence.sources[0]
    elif where == 'derived':
        reference = draft.derived.sources[0]
    else:
        seed = draft.channel_seeds[0] if where == 'channel' else draft.net_evidence[0]
        from layauto_v2.domain.source_location import ref_from_location
        # A coordinate operand identifies the actual per-device/per-net raw
        # response. ChannelSeed does not expose NetEvidence's source property.
        reference = ref_from_location(seed.record['field_sources']['vertices_nm']['sources'][1])
    binding = dict(draft.capture_binding.items())
    binding['sources'] = tuple(row for row in binding['sources']
                              if (row['uri'], row['sha256']) != (reference.uri, reference.sha256))
    with pytest.raises(ValueError):
        replace(draft, capture_binding=FrozenMap(binding))


def test_new_public_boundary_rejects_mutable_map_backing_before_old_authentication(accepted, monkeypatch):
    broken_map = object.__new__(FrozenMap)
    object.__setattr__(broken_map, '_entries', list(accepted.input.body_evidence.payload.items()))
    broken_body = unchecked_replace(accepted.input.body_evidence, payload=broken_map)
    # body_evidence is a property on W010; poison the retained completed body.
    local = unchecked_replace(accepted.input, completed=tuple(
        broken_body if item.kind == 'body' else item for item in accepted.input.completed))
    def forbidden(*args, **kwargs):
        pytest.fail('old decoder copied an unsafe exact FrozenMap shell')
    monkeypatch.setattr(component.local_connectivity_codec, 'decode_record', forbidden)
    with pytest.raises(ValueError):
        component.build_terminal_relations(local)


@pytest.mark.parametrize('change', [
    {'schema_version': 'unknown/99'}, {'kind': 'unknown'}, {'extra': None},
])
def test_new_wire_rejects_unknown_envelope_fields_and_versions(accepted, change):
    leaf = accepted.value.relations[0].target
    value = dict(decode(codec.encode_record(leaf)).items())
    if 'schema_version' in change:
        value['wire_schema'] = change['schema_version']
    else:
        value.update(change)
    with pytest.raises(ValueError):
        codec.decode_record(canonical_bytes(value))


def test_leaf_wire_rejects_missing_field_and_root_of_another_record_kind(accepted):
    target = accepted.value.relations[0].target
    value = decode(codec.encode_record(target))
    record = dict(value['record'].items())
    fields = dict(record['fields'].items())
    fields.pop('device_id')
    record['fields'] = fields
    envelope = dict(value.items())
    envelope['record'] = record
    with pytest.raises(ValueError):
        codec.decode_record(canonical_bytes(envelope))
    envelope['record'] = codec._pack(target.device_id)
    with pytest.raises(ValueError):
        codec.decode_record(canonical_bytes(envelope))
    # A foreign old record with init=False fields must be rejected before its
    # constructor can receive a keyword it does not accept.
    envelope['record'] = FrozenMap({'record': 'RunRequest', 'fields': FrozenMap({})})
    with pytest.raises(ValueError):
        codec.decode_record(canonical_bytes(envelope))
    nested = dict(value['record'].items())
    nested_fields = dict(nested['fields'].items())
    nested_fields['device_id'] = envelope['record']
    nested['fields'] = nested_fields
    envelope['record'] = nested
    with pytest.raises(ValueError):
        codec.decode_record(canonical_bytes(envelope))


class MutableText(str):
    pass


@pytest.mark.parametrize('field', ['role', 'binding'])
def test_native_leaf_ids_and_roles_cannot_retain_foreign_mutable_scalars(accepted, field):
    target = accepted.value.relations[0].target
    with pytest.raises(ValueError):
        if field == 'role':
            replace(target, role=MutableText(target.role))
        else:
            TerminalRef('binding', MutableText(target.binding_ref.sha256))


def test_new_relation_modules_preserve_read_only_dependency_and_no_io_boundaries():
    root = Path(__file__).resolve().parents[2] / 'layauto_v2'
    files = ('domain/terminal_relations.py', 'derive/terminal_relations.py',
             'derive/body_relations.py', 'normalization/terminal_relations.py',
             'normalization/terminal_relations_codec.py')
    for name in files:
        path = root / name
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ''
                assert not module.startswith(('tests', 'legacy_mvp', 'layauto_v2.transactions',
                    'layauto_v2.export', 'layauto_v2.repository', 'layauto_v2.pipeline')), (name, module)
                if name.startswith('domain/'):
                    assert not module.startswith(('layauto_v2.normalization', 'layauto_v2.state',
                                                   'layauto_v2.annotation', 'layauto_v2.derive'))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in ('open', 'hash', 'eval', 'exec'), (name, node.lineno)


@pytest.mark.parametrize('failure_type', [RuntimeError, KeyboardInterrupt, SystemExit])
@pytest.mark.parametrize('entry', ['builder', 'constructor', 'encode', 'decode'])
def test_original_nested_public_authentication_exception_history_is_unchanged(
        accepted, monkeypatch, failure_type, entry):
    cause, context = LookupError('original cause'), IndexError('original context')
    failure = failure_type('retained failure')
    failure.__cause__, failure.__context__, failure.__suppress_context__ = cause, context, False
    wire = None
    if entry == 'decode':
        # A compact leaf cannot exercise captured authentication. Prepare this
        # packet once before injecting the nested decoder failure.
        wire = canonical_bytes({'wire_schema': codec.WIRE_VERSION, 'kind': 'result',
            'captured_input_wire': FrozenMap({}), 'result': FrozenMap({})})
    def broken(*args, **kwargs):
        raise failure
    monkeypatch.setattr(component.local_connectivity_codec, 'decode_record', broken)
    with pytest.raises(failure_type) as raised:
        if entry == 'builder':
            component.build_terminal_relations(accepted.input)
        elif entry == 'constructor':
            component.TerminalRelationsResult(accepted.input)
        elif entry == 'encode':
            codec.encode_record(accepted)
        else:
            codec.decode_record(wire)
    assert raised.value is failure
    assert failure.__cause__ is cause and failure.__context__ is context
    assert failure.__suppress_context__ is False


def test_expected_component_issue_unwinds_before_later_output_failure(accepted, monkeypatch):
    from layauto_v2.derive.body_relations import BodyProblem
    from layauto_v2.domain.results import EvidenceIssue
    issue = EvidenceIssue('unsupported', 'ExpectedBodyOwnerFailure', 'controlled owner failure',
                          accepted.body_evidence.sources[0])
    expected = BodyProblem(issue)
    def expected_failure(*args, **kwargs):
        raise expected
    monkeypatch.setattr(component, 'build_terminal_relations_draft', expected_failure)
    result = component.build_terminal_relations(accepted.input)
    assert result.status == 'error' and result.value is None and result.issues == (issue,)
    cause, context = LookupError('original cause'), IndexError('original context')
    failure = RuntimeError('later compact encoding failure')
    failure.__cause__, failure.__context__, failure.__suppress_context__ = cause, context, True
    def later_failure(*args, **kwargs):
        raise failure
    monkeypatch.setattr(codec, '_compact', later_failure)
    with pytest.raises(RuntimeError) as raised:
        codec.encode_record(result)
    assert raised.value is failure
    assert failure.__cause__ is cause and failure.__context__ is context
    assert failure.__suppress_context__ is True
