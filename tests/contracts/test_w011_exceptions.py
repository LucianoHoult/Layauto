"""W011 original unexpected exceptions through actual complete receipt chains.

Each boundary is reached through a real captured direct/readback result. Test
faults are installed only after the original canonical wire has been built.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from layauto_v2.domain.channel_identity import ChannelProblem
from layauto_v2.domain.codec import canonical_bytes, decode
from layauto_v2.domain.publication import InputsReady
from layauto_v2.domain.results import EvidenceIssue
from layauto_v2.normalization import build_effective_geometry, build_geometry, build_local_connectivity
from layauto_v2.normalization import channel_identity as component
from layauto_v2.normalization.channel_identity import build_channel_identity
from layauto_v2.normalization.channel_identity_codec import decode_record, encode_record
from layauto_v2.normalization.geometry_input import geometry_from_inputs_ready
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository
from test_w009_nested_base_decode import bad_gds, with_gds
from test_w010_exceptions import assert_same_history, install_fault
from w005_cases import FIXTURE
from w006_cases import caller_request
from w007_cases import mutable
from w011_cases import build


@pytest.fixture(scope='module')
def captures():
    direct = build()
    repository = PublicationRepository()
    ready = prepare_inputs(repository, caller_request(FIXTURE, run_id='w011-exception-readback'))
    assert isinstance(ready, InputsReady)
    geometry = build_geometry(geometry_from_inputs_ready(
        ready, repository.load_checkpoint(ready.run_id), repository.read(ready.parse_ref),
        repository.read(ready.tool_ref), tuple(repository.read(ref) for ref in ready.evidence_refs)))
    readback = build_channel_identity(build_local_connectivity(build_effective_geometry(geometry)))
    assert direct.status == readback.status == 'success'
    assert direct.value == readback.value
    return direct, readback, {'direct': encode_record(direct), 'readback': encode_record(readback),
                             'draft': encode_record(direct.value)}


@pytest.mark.parametrize('entry,target,failure_type', [
    ('builder', 'layauto_v2.normalization.channel_identity.build_channel_identity_draft', RuntimeError),
    ('constructor', 'layauto_v2.normalization.channel_identity.build_channel_identity_draft', ValueError),
    ('decoder', 'layauto_v2.derive.channel_identity._analyze', TypeError),
    ('builder', 'layauto_v2.normalization.channel_identity.normalize', KeyError),
    ('constructor', 'layauto_v2.derive.channel_identity._topology', AttributeError),
    ('decoder', 'layauto_v2.derive.channel_identity._comparisons', IndexError),
    ('builder', 'layauto_v2.derive.channel_identity._comparisons', UnicodeError),
    ('constructor', 'layauto_v2.normalization.channel_identity.build_channel_identity_draft', KeyboardInterrupt),
    ('decoder', 'layauto_v2.derive.channel_identity._analyze', SystemExit),
])
def test_new_boundaries_keep_exception_identity_cause_context_and_suppression(captures, monkeypatch, entry, target, failure_type):
    direct, _, wires = captures
    failure, cause, context = install_fault(monkeypatch, target, failure_type)
    with pytest.raises(failure_type) as raised:
        if entry == 'builder': build_channel_identity(direct.input)
        elif entry == 'constructor': replace(direct)
        else: decode_record(wires['direct'])
    assert_same_history(raised, failure, cause, context)


@pytest.mark.parametrize('scope,target,failure_type', [
    ('direct', 'layauto_v2.state.local_connectivity._components', RuntimeError),
    ('direct', 'layauto_v2.state.regions.slab_difference', ValueError),
    ('direct', 'layauto_v2.state.layout_store._materialize', TypeError),
    ('direct', 'layauto_v2.state.coordinate._layers', KeyError),
    ('direct', 'layauto_v2.state.occupancy._fragments', AttributeError),
    ('direct', 'layauto_v2.normalization.contracts.request_decoder_input', IndexError),
    ('direct', 'layauto_v2.normalization._validation._validate_cdl', UnicodeError),
    ('direct', 'layauto_v2.normalization._validation._validate_query', KeyboardInterrupt),
    ('readback', 'layauto_v2.normalization.contracts.content_ref', SystemExit),
    ('readback', 'source_hash', TypeError),
    ('readback', 'layauto_v2.normalization._validation._validate_query', ValueError),
    ('draft', 'layauto_v2.state.local_connectivity._components', TypeError),
    ('draft', 'layauto_v2.state.regions.slab_difference', KeyboardInterrupt),
])
def test_actual_nested_w010_w009_w008_w007_wire_preserves_history(captures, monkeypatch, scope, target, failure_type):
    _, _, wires = captures
    failure, cause, context = install_fault(monkeypatch, target, failure_type)
    with pytest.raises(failure_type) as raised:
        decode_record(wires[scope])
    assert_same_history(raised, failure, cause, context)


@pytest.mark.parametrize('entry,target', [
    ('builder', 'layauto_v2.normalization.geometry_input.load_document'),
    ('constructor', 'layauto_v2.normalization.contracts.request_decoder_input'),
    ('readback', 'layauto_v2.normalization.contracts.content_ref'),
])
def test_public_builder_and_constructor_reauthenticate_actual_capture_chain(captures, monkeypatch, entry, target):
    direct, readback, _ = captures
    failure, cause, context = install_fault(monkeypatch, target, TypeError)
    with pytest.raises(TypeError) as raised:
        if entry == 'constructor': replace(direct)
        else: build_channel_identity(readback.input if entry == 'readback' else direct.input)
    assert_same_history(raised, failure, cause, context)


@pytest.mark.parametrize('failure_type,suppression', [(ValueError, False), (TypeError, True),
                                                      (KeyboardInterrupt, False), (SystemExit, True)])
def test_expected_error_then_second_authentication_fault_keeps_preexisting_history(captures, monkeypatch, failure_type, suppression):
    direct, _, _ = captures
    source = replace(direct.value.derived.sources[0], field='/derived_registry/0/trim_operator')
    expected = ChannelProblem(EvidenceIssue('unsupported', 'UnsupportedChannelOperator', 'unsupported trim', source))
    failure = failure_type('unexpected second authentication failure')
    cause, context = RuntimeError('existing cause'), LookupError('existing context')
    failure.__cause__, failure.__context__, failure.__suppress_context__ = cause, context, suppression
    original, calls = component._require_input, []
    def authenticate(value):
        calls.append(value)
        if len(calls) == 2: raise failure
        return original(value)
    def unsupported(*args, **kwargs): raise expected
    monkeypatch.setattr(component, '_require_input', authenticate)
    monkeypatch.setattr(component, 'build_channel_identity_draft', unsupported)
    with pytest.raises(failure_type) as raised:
        build_channel_identity(direct.input)
    assert len(calls) == 2 and raised.value is failure
    assert failure.__cause__ is cause and failure.__context__ is context
    assert failure.__suppress_context__ is suppression


@pytest.mark.parametrize('change', ('missing', 'scalar_bbox'))
def test_outer_wire_rejects_malformed_nested_geometry_instead_of_masking_it(captures, change):
    direct, _, wires = captures
    bad = bad_gds(direct.input.input, change)
    tree = mutable(decode(wires['draft']))
    local = mutable(decode(tree['record']['fields']['local']['local_record']))
    effective = mutable(decode(local['record']['fields']['effective']['effective_record']))
    base = mutable(decode(effective['record']['fields']['base']['geometry_record']))
    assert with_gds(base, bad)
    effective['record']['fields']['base']['geometry_record'] = canonical_bytes(base)
    local['record']['fields']['effective']['effective_record'] = canonical_bytes(effective)
    tree['record']['fields']['local']['local_record'] = canonical_bytes(local)
    with pytest.raises(ValueError): decode_record(canonical_bytes(tree))


@pytest.mark.parametrize('field', ('input', 'semantic', 'value', 'issues', 'completed'))
def test_outer_result_malformed_fields_have_explicit_value_error(captures, field):
    _, _, wires = captures
    tree = mutable(decode(wires['direct']))
    tree['record']['fields'][field] = {'scalar': None}
    with pytest.raises(ValueError): decode_record(canonical_bytes(tree))


@pytest.mark.parametrize('failure_type', (TypeError, KeyboardInterrupt, SystemExit))
def test_expected_owner_schema_error_then_diagnostic_fault_preserves_history(captures, monkeypatch, failure_type):
    from layauto_v2.derive import channel_identity as derive
    from layauto_v2.tech.schema import SchemaError
    direct, _, _ = captures
    draft = direct.value
    failure = failure_type('unexpected diagnostic construction fault')
    cause, context = RuntimeError('existing cause'), LookupError('existing context')
    failure.__cause__, failure.__context__, failure.__suppress_context__ = cause, context, False
    def malformed(*args, **kwargs):
        raise SchemaError('/fin_count_profile', 'injected expected owner schema failure')
    def broken(*args, **kwargs): raise failure
    monkeypatch.setattr(derive, 'validate_payload', malformed)
    monkeypatch.setattr(derive, 'problem', broken)
    with pytest.raises(failure_type) as raised:
        derive.build_channel_identity_draft(draft.local, draft.source, draft.seeds, draft.derived)
    assert_same_history(raised, failure, cause, context)


@pytest.mark.parametrize('scope', ('leaf', 'result'))
@pytest.mark.parametrize('failure_type', (TypeError, KeyError, AttributeError, UnicodeError))
def test_cr02_nested_parameter_constructor_keeps_original_exception_history(captures, monkeypatch, scope, failure_type):
    from layauto_v2.domain.circuit import Parameter
    direct, _, wires = captures
    wire = encode_record(direct.value.comparisons[0]) if scope == 'leaf' else wires['direct']
    failure = failure_type('unexpected nested Parameter constructor failure')
    cause, context = RuntimeError('existing cause'), LookupError('existing context')
    failure.__cause__, failure.__context__, failure.__suppress_context__ = cause, context, False
    def broken(*args, **kwargs): raise failure
    monkeypatch.setattr(Parameter, '__post_init__', broken)
    with pytest.raises(failure_type) as raised:
        decode_record(wire)
    assert_same_history(raised, failure, cause, context)


@pytest.mark.parametrize('change', ('missing_unit', 'extra_field', 'wrong_exact', 'missing_source'))
def test_nested_parameter_malformed_controls_still_raise_value_error(captures, change):
    direct, _, _ = captures
    tree = mutable(decode(encode_record(direct.value.comparisons[0])))
    parameter = mutable(decode(tree['record']['fields']['declared']['semantic_record']))
    fields = parameter['record']['fields']
    if change == 'missing_unit': del fields['unit']
    elif change == 'extra_field': fields['foreign'] = {'scalar': True}
    elif change == 'wrong_exact': fields['exact'] = {'scalar': None}
    else: fields['source'] = {'scalar': None}
    tree['record']['fields']['declared']['semantic_record'] = canonical_bytes(parameter)
    with pytest.raises(ValueError): decode_record(canonical_bytes(tree))


@pytest.mark.parametrize('case,hook', (('admission', 'NormalizationResult'), ('identity', 'replace')))
def test_cr03_actual_w007_expected_failure_then_completion_fault_keeps_history(tmp_path, monkeypatch, case, hook):
    from layauto_v2.normalization import component as semantic_component
    from w005_cases import rebind
    from w007_cases import ready_copy
    from w010_cases import build_local
    from w011_cases import change_cdl
    root = ready_copy(tmp_path)
    if case == 'admission':
        change_cdl(root, 'source', 'NF=1', 'NF=2')
    else:
        path = root / 'query/raw/iXref.temp'
        path.write_text(path.read_text().replace('MN0', 'UNDECLARED'))
        rebind(root)
    local = build_local(root)
    control = semantic_component.normalize(local.input.input.input.semantic_input)
    assert control.status == 'error' and control.issues
    failure = TypeError('unexpected W007 ' + hook + ' after actual expected failure')
    cause, context = RuntimeError('existing cause'), LookupError('existing context')
    failure.__cause__, failure.__context__, failure.__suppress_context__ = cause, context, False
    def broken(*args, **kwargs): raise failure
    monkeypatch.setattr(semantic_component, hook, broken)
    with pytest.raises(TypeError) as raised:
        build_channel_identity(local)
    assert_same_history(raised, failure, cause, context)
