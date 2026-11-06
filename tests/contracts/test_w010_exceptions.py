"""W010 preserves algorithm faults through the complete nested receipt chain.

Faults are injected only after valid real direct/readback wires exist. Malformed
wire controls are separate and require explicit ValueError rejection.
"""
from dataclasses import replace
from types import SimpleNamespace

import pytest

from layauto_v2.domain.codec import canonical_bytes, decode
from layauto_v2.domain.publication import InputsReady
from layauto_v2.domain.local_connectivity import ContactProblem
from layauto_v2.domain.results import EvidenceIssue
from layauto_v2.normalization import build_effective_geometry, build_geometry
from layauto_v2.normalization.geometry_input import geometry_from_inputs_ready, geometry_from_parse_result
from layauto_v2.normalization.local_connectivity import build_local_connectivity
from layauto_v2.normalization import local_connectivity as local_component
from layauto_v2.normalization.local_connectivity_codec import decode_record, encode_record
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository
from test_w009_nested_base_decode import bad_gds, with_gds
from w005_cases import FIXTURE
from w006_cases import caller_request
from w007_cases import mutable, read


@pytest.fixture(scope='module')
def captures():
    parsed = read(FIXTURE)
    direct = build_local_connectivity(build_effective_geometry(
        build_geometry(geometry_from_parse_result(parsed))))
    repository = PublicationRepository()
    ready = prepare_inputs(repository, caller_request(FIXTURE, run_id='w010-exception-wire'))
    assert isinstance(ready, InputsReady)
    readback = build_local_connectivity(build_effective_geometry(build_geometry(geometry_from_inputs_ready(
        ready, repository.load_checkpoint(ready.run_id), repository.read(ready.parse_ref),
        repository.read(ready.tool_ref), tuple(repository.read(ref) for ref in ready.evidence_refs)))))
    assert direct.status == readback.status == 'success'
    assert direct.value == readback.value
    wires = {name: encode_record(value) for name, value in
             (('direct', direct), ('readback', readback), ('draft', direct.value))}
    return direct, readback, wires


FAILURES = (RuntimeError, ValueError, TypeError, KeyError, AttributeError,
            IndexError, UnicodeError, KeyboardInterrupt, SystemExit)
NEW_TARGETS = (
    'layauto_v2.state.local_connectivity.same_layer_contact',
    'layauto_v2.state.local_connectivity.encloses_connector',
    'layauto_v2.state.local_connectivity._components',
    'layauto_v2.normalization.local_connectivity.build_local_connectivity_draft',
)
NESTED_TARGETS = (
    ('direct', 'layauto_v2.state.regions.slab_difference'),
    ('direct', 'layauto_v2.state.layout_store._materialize'),
    ('direct', 'layauto_v2.state.coordinate._layers'),
    ('direct', 'layauto_v2.state.occupancy._fragments'),
    ('direct', 'layauto_v2.normalization.contracts.request_decoder_input'),
    ('direct', 'layauto_v2.normalization._validation._validate_cdl'),
    ('direct', 'layauto_v2.normalization._validation._validate_query'),
    ('readback', 'layauto_v2.normalization.contracts.content_ref'),
    ('direct', 'source_hash'),
)


def install_fault(monkeypatch, target, cls):
    failure = cls('unexpected reconstruction failure')
    cause, context = RuntimeError('existing explicit cause'), LookupError('existing implicit context')
    failure.__cause__, failure.__context__ = cause, context
    failure.__suppress_context__ = False
    def broken(*args, **kwargs):
        raise failure
    if target == 'source_hash':
        # Replace evidence.py's module binding only. Replacing the shared
        # hashlib function would fault earlier and miss captured SourceFile.
        monkeypatch.setattr('layauto_v2.domain.evidence.hashlib', SimpleNamespace(sha256=broken))
    else:
        monkeypatch.setattr(target, broken)
    return failure, cause, context


def assert_same_history(raised, failure, cause, context):
    assert raised.value is failure
    assert failure.__cause__ is cause
    assert failure.__context__ is context
    assert failure.__suppress_context__ is False


@pytest.mark.parametrize('target', NEW_TARGETS)
@pytest.mark.parametrize('failure_type', FAILURES)
@pytest.mark.parametrize('entry', ('builder', 'decoder'))
def test_new_algorithms_preserve_original_exception_and_existing_history(captures, monkeypatch, target, failure_type, entry):
    direct, _, wires = captures
    failure, cause, context = install_fault(monkeypatch, target, failure_type)
    with pytest.raises(failure_type) as raised:
        build_local_connectivity(direct.input) if entry == 'builder' else decode_record(wires['direct'])
    assert_same_history(raised, failure, cause, context)


@pytest.mark.parametrize('scope,target', NESTED_TARGETS)
@pytest.mark.parametrize('failure_type', FAILURES)
def test_complete_nested_decode_keeps_original_exception_and_existing_history(captures, monkeypatch, scope, target, failure_type):
    _, _, wires = captures
    failure, cause, context = install_fault(monkeypatch, target, failure_type)
    with pytest.raises(failure_type) as raised:
        decode_record(wires[scope])
    assert_same_history(raised, failure, cause, context)


@pytest.mark.parametrize('scope,target', (
    ('draft', 'layauto_v2.state.local_connectivity._components'),
    ('draft', 'layauto_v2.state.regions.slab_difference'),
    ('draft', 'layauto_v2.state.layout_store._materialize'),
    ('draft', 'layauto_v2.state.coordinate._layers'),
    ('draft', 'layauto_v2.state.occupancy._fragments'),
    ('readback', 'layauto_v2.normalization.contracts.request_decoder_input'),
    ('readback', 'layauto_v2.normalization._validation._validate_cdl'),
    ('readback', 'layauto_v2.normalization._validation._validate_query'),
    ('readback', 'source_hash'),
))
def test_neutral_and_readback_outer_paths_reach_the_same_protected_boundaries(captures, monkeypatch, scope, target):
    _, _, wires = captures
    failure, cause, context = install_fault(monkeypatch, target, TypeError)
    with pytest.raises(TypeError) as raised:
        decode_record(wires[scope])
    assert_same_history(raised, failure, cause, context)


@pytest.mark.parametrize('target', (
    'layauto_v2.normalization.geometry_input.load_document',
    'layauto_v2.normalization.contracts.request_decoder_input',
    'layauto_v2.normalization.contracts.content_ref',
))
def test_public_builder_reauthenticates_full_direct_or_readback_capture_chain(captures, monkeypatch, target):
    direct, readback, _ = captures
    failure, cause, context = install_fault(monkeypatch, target, TypeError)
    source = readback.input if target.endswith('content_ref') else direct.input
    with pytest.raises(TypeError) as raised:
        build_local_connectivity(source)
    assert_same_history(raised, failure, cause, context)


@pytest.mark.parametrize('failure_type', (ValueError, TypeError, KeyboardInterrupt))
def test_expected_policy_failure_does_not_become_context_of_later_authentication_fault(captures, monkeypatch, failure_type):
    direct, _, _ = captures
    source = replace(direct.value.binding.physical.sources[0], field='/operators/same_layer_contact~11')
    policy_problem = ContactProblem(EvidenceIssue('unsupported', 'UnsupportedLocalContactOperator',
                                                 'unsupported captured contact policy', source))
    failure = failure_type('unexpected reauthentication fault while constructing error result')
    cause, context = RuntimeError('existing explicit cause'), LookupError('existing implicit context')
    failure.__cause__, failure.__context__ = cause, context
    failure.__suppress_context__ = False
    original = local_component._require_input
    calls = []
    def authenticate(value):
        calls.append(value)
        if len(calls) == 2:
            raise failure
        return original(value)
    def unsupported(*args, **kwargs):
        raise policy_problem
    monkeypatch.setattr(local_component, '_require_input', authenticate)
    monkeypatch.setattr(local_component, 'build_local_connectivity_draft', unsupported)
    with pytest.raises(failure_type) as raised:
        build_local_connectivity(direct.input)
    assert len(calls) == 2
    assert_same_history(raised, failure, cause, context)


@pytest.mark.parametrize('change', ('missing', 'extra', 'short_xy', 'scalar_bbox', 'scalar_row'))
def test_w010_nested_base_wire_malformed_controls_still_explicitly_reject(captures, change):
    direct, _, wires = captures
    bad = bad_gds(direct.input, change)
    tree = mutable(decode(wires['draft']))
    nested = mutable(decode(tree['record']['fields']['effective']['effective_record']))
    base = mutable(decode(nested['record']['fields']['base']['geometry_record']))
    assert with_gds(base, bad)
    nested['record']['fields']['base']['geometry_record'] = canonical_bytes(base)
    tree['record']['fields']['effective']['effective_record'] = canonical_bytes(nested)
    with pytest.raises(ValueError):
        decode_record(canonical_bytes(tree))


@pytest.mark.parametrize('field', ('input', 'value', 'issues', 'completed'))
def test_w010_malformed_receipt_fields_are_not_confused_with_algorithm_faults(captures, field):
    _, _, wires = captures
    tree = mutable(decode(wires['direct']))
    tree['record']['fields'][field] = {'scalar': None}
    with pytest.raises(ValueError):
        decode_record(canonical_bytes(tree))
