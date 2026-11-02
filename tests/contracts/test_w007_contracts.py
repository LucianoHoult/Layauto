"""A6: public DTO, evidence binding, exact wire and ownership regressions."""
from __future__ import annotations

import ast
import hashlib
import os
import subprocess
import sys
from dataclasses import FrozenInstanceError, replace
from fractions import Fraction
from pathlib import Path

import pytest

from layauto_v2.domain.circuit import semantic_digest
from layauto_v2.domain.codec import canonical_bytes, decode
from layauto_v2.domain.evidence import EvidenceRecord
from layauto_v2.domain.identifiers import CellId, DeviceId, NetId
from layauto_v2.normalization.codec import decode_record, encode_record, record_digest
from layauto_v2.domain.publication import InputsReady
from layauto_v2.normalization import from_inputs_ready, from_parse_result, normalize
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository

from w005_cases import FIXTURE, rebind
from w006_cases import caller_request
from w007_cases import edit, mutable, normal, read, ready_copy


@pytest.fixture(scope='module')
def accepted():
    return normal(FIXTURE)


def test_public_records_and_full_result_have_closed_canonical_wire_roundtrip(accepted):
    facts = accepted.value
    records = [accepted.input, accepted, facts, facts.source, facts.target,
               facts.source.cells[0], *facts.source.cells[0].devices,
               *facts.source.cells[0].nets, *facts.device_identities,
               *facts.net_identities, *facts.device_seeds, *facts.net_seeds,
               facts.source.cells[0].id, facts.device_identities[0].query_key]
    for record in records:
        data = encode_record(record)
        restored = decode_record(data)
        assert type(restored) is type(record)
        assert restored == record
        assert encode_record(restored) == data
        assert record_digest(record) == hashlib.sha256(data).hexdigest()


def test_success_and_error_discriminators_reject_invalid_combinations(accepted, tmp_path):
    root = ready_copy(tmp_path)
    edit(root, 'source.cdl', 'NF=1', 'NF=2')
    rebind(root)
    failure = normalize(from_parse_result(read(root)))
    assert failure.status == 'error'
    assert failure.value is None and failure.issues
    assert decode_record(encode_record(failure)) == failure
    for original, kwargs in ((accepted, {'status': 'error'}),
                             (accepted, {'issues': failure.issues}),
                             (accepted, {'value': None}),
                             (failure, {'status': 'success'}),
                             (failure, {'value': accepted.value}),
                             (failure, {'issues': ()}),
                             (accepted, {'status': 'no_change'}),
                             (accepted, {'schema_version': 'unknown/99'})):
        with pytest.raises(ValueError):
            replace(original, **kwargs)


def test_recursive_immutability_rejects_mutation_and_retains_no_caller_alias(accepted):
    before = record_digest(accepted)
    source = accepted.value.source
    cell = source.cells[0]
    device = cell.devices[0]
    parameter = device.parameters[0]
    evidence_alias = mutable(parameter.field_evidence)
    copied_parameter = replace(parameter, field_evidence=evidence_alias)
    evidence_alias['lexeme'] = 'poisoned'
    assert copied_parameter.field_evidence == parameter.field_evidence
    mutable_devices = list(cell.devices)
    copied_cell = replace(cell, devices=mutable_devices)
    mutable_devices.clear()
    assert copied_cell.devices == cell.devices
    mutable_seeds = list(accepted.value.device_seeds)
    copied_facts = replace(accepted.value, device_seeds=mutable_seeds)
    mutable_seeds.clear()
    assert copied_facts.device_seeds == accepted.value.device_seeds
    for action in (lambda: setattr(source, 'cells', ()),
                   lambda: setattr(parameter, 'exact', Fraction(99)),
                   lambda: parameter.field_evidence.__setitem__('lexeme', '99'),
                   lambda: accepted.value.device_seeds[0].record.__setitem__('quality', 'unknown')):
        with pytest.raises((TypeError, AttributeError, FrozenInstanceError)):
            action()
    assert record_digest(accepted) == before
    assert accepted.value.source is not accepted.value.target


@pytest.mark.parametrize('mutation', ['foreign_device', 'foreign_port', 'missing_net',
                                      'missing_member', 'duplicate_member', 'wrong_terminal'])
def test_cell_aggregate_rejects_foreign_missing_or_conflicting_membership(accepted, mutation):
    cell = accepted.value.source.cells[0]
    device = cell.devices[0]
    net = next(item for item in cell.nets if item.memberships)
    foreign = CellId('UNRELATED_CELL')
    with pytest.raises(ValueError):
        if mutation == 'foreign_device':
            altered = replace(device, id=DeviceId(foreign, device.id.name))
            replace(cell, devices=(altered,) + cell.devices[1:])
        elif mutation == 'foreign_port':
            replace(cell, ports=(NetId(foreign, cell.ports[0].name),) + cell.ports[1:])
        elif mutation == 'missing_net':
            replace(cell, nets=tuple(item for item in cell.nets if item.id != net.id))
        elif mutation == 'missing_member':
            altered = replace(net, memberships=net.memberships[1:])
            replace(cell, nets=tuple(altered if item.id == net.id else item for item in cell.nets))
        elif mutation == 'duplicate_member':
            altered = replace(net, memberships=net.memberships + net.memberships[:1])
            replace(cell, nets=tuple(altered if item.id == net.id else item for item in cell.nets))
        else:
            term = replace(device.terminals[0], net_id=NetId(cell.id, 'NO_SUCH_NET'))
            altered = replace(device, terminals=(term,) + device.terminals[1:])
            replace(cell, devices=(altered,) + cell.devices[1:])


@pytest.mark.parametrize('mutation', ['missing_identity', 'duplicate_identity', 'foreign_identity',
                                      'foreign_seed', 'wrong_seed_key', 'duplicate_seed',
                                      'missing_seed'])
def test_facts_aggregate_rejects_wrong_identity_or_seed_relationships(accepted, mutation):
    facts = accepted.value
    with pytest.raises(ValueError):
        if mutation == 'missing_identity':
            changed = replace(facts, device_identities=facts.device_identities[1:])
        elif mutation == 'duplicate_identity':
            changed = replace(facts, device_identities=facts.device_identities + facts.device_identities[:1])
        elif mutation == 'foreign_identity':
            identity = replace(facts.device_identities[0], device_id=DeviceId(CellId('OTHER'), 'MN0'))
            changed = replace(facts, device_identities=(identity,) + facts.device_identities[1:])
        elif mutation == 'foreign_seed':
            seed = replace(facts.device_seeds[0], semantic_id=DeviceId(CellId('OTHER'), 'MN0'))
            changed = replace(facts, device_seeds=(seed,) + facts.device_seeds[1:])
        elif mutation == 'wrong_seed_key':
            seed = replace(facts.device_seeds[0], query_key=facts.device_seeds[1].query_key)
            changed = replace(facts, device_seeds=(seed,) + facts.device_seeds[1:])
        elif mutation == 'duplicate_seed':
            changed = replace(facts, device_seeds=facts.device_seeds + facts.device_seeds[:1])
        else:
            changed = replace(facts, net_seeds=facts.net_seeds[1:])
        # An error may legitimately carry incomplete facts. A successful public
        # result must prove complete identity and seed coverage of its input.
        replace(accepted, value=changed, completed=changed)


@pytest.mark.parametrize('mutation', ['operand', 'before', 'after', 'provenance'])
def test_target_delta_aggregate_rejects_semantically_wrong_associations(tmp_path, mutation):
    root = ready_copy(tmp_path)
    edit(root, 'target.cdl', 'L=4n', 'L=5n')
    rebind(root)
    result = normal(root)
    facts = result.value
    delta = facts.differences[0]
    with pytest.raises(ValueError):
        if mutation == 'operand':
            changed = replace(delta, operand_ref=DeviceId(CellId('WRONG'), delta.operand_ref.name))
        elif mutation == 'before':
            changed = replace(delta, semantic_before=delta.semantic_after)
        elif mutation == 'after':
            changed = replace(delta, semantic_after=delta.semantic_before)
        else:
            changed = replace(delta, provenance=())
        changed_facts = replace(facts, differences=(changed,) + facts.differences[1:])
        replace(result, value=changed_facts, completed=changed_facts)


def test_input_rejects_value_completed_mismatch_and_unknown_evidence(accepted):
    parsed = accepted.input.parse
    changed_value = mutable(parsed.value)
    changed_value['source_cdl']['tops'][0]['devices'][0]['name'] = 'FORGED'
    with pytest.raises(ValueError):
        from_parse_result(replace(parsed, value=changed_value))
    source_record = next(record for record in parsed.completed if record.kind == 'source_cdl')
    changed_payload = mutable(source_record.payload)
    changed_payload['tops'][0]['name'] = 'FORGED'
    bad_record = replace(source_record, payload=changed_payload)
    with pytest.raises(ValueError):
        from_parse_result(replace(parsed, completed=tuple(bad_record if item.kind == 'source_cdl' else item for item in parsed.completed)))
    with pytest.raises(ValueError):
        from_parse_result(replace(parsed, completed=parsed.completed + (source_record,)))
    with pytest.raises(ValueError):
        from_parse_result(replace(parsed, completed=tuple(item for item in parsed.completed if item.kind != 'query')))
    extra = EvidenceRecord('invented-kind', {}, (parsed.sources[0].ref(),))
    with pytest.raises(ValueError):
        from_parse_result(replace(parsed, completed=parsed.completed + (extra,)))


@pytest.mark.parametrize('role', ['source_cdl', 'target_cdl', 'query'])
def test_coherent_role_from_other_capture_cannot_hide_behind_old_header(tmp_path, role):
    root = ready_copy(tmp_path)
    first = read(root)
    if role == 'source_cdl':
        edit(root, 'source.cdl', 'NFIN=5', 'NFIN=6')
    elif role == 'target_cdl':
        edit(root, 'target.cdl', 'L=4n', 'L=5n')
    else:
        edit(root, 'query/raw/device_info_Q17.txt', '\n400 ', '\n420 ')
    rebind(root)
    second = read(root)
    value = mutable(first.value)
    value[role] = second.value[role]
    selected = next(item for item in second.completed if item.kind == role)
    completed = tuple(selected if item.kind == role else item for item in first.completed)
    selected_uris = {source.uri for source in selected.sources}
    sources = tuple(next(other for other in second.sources if other.uri == item.uri)
                    if item.uri in selected_uris else item for item in first.sources)
    with pytest.raises(ValueError):
        mixed = replace(first, value=value, completed=completed, sources=sources)
        from_parse_result(mixed)


def test_header_role_swap_does_not_pick_a_source_merely_by_matching_hash(accepted):
    parsed = accepted.input.parse
    value = mutable(parsed.value)
    header = value['header']
    header['source_netlist'], header['target'] = header['target'], header['source_netlist']
    completed = tuple(replace(item, payload=header) if item.kind == 'header' else item for item in parsed.completed)
    with pytest.raises(ValueError):
        from_parse_result(replace(parsed, value=value, completed=completed))


def ready_bundle(root, run_id):
    repository = PublicationRepository()
    ready = prepare_inputs(repository, caller_request(root, run_id=run_id))
    assert isinstance(ready, InputsReady)
    return (ready, repository.load_checkpoint(run_id), repository.read(ready.parse_ref),
            repository.read(ready.tool_ref), tuple(repository.read(ref) for ref in ready.evidence_refs))


@pytest.mark.parametrize('member', [0, 1, 2, 3, 4])
def test_readback_rejects_sibling_from_another_real_run(tmp_path, member):
    root = ready_copy(tmp_path)
    first = ready_bundle(root, 'w007-run-A')
    second = ready_bundle(root, 'w007-run-B')
    mixed = list(first)
    mixed[member] = second[member]
    with pytest.raises(ValueError):
        from_inputs_ready(*mixed)


def test_readback_rejects_missing_duplicated_evidence_or_changed_ready_payload(tmp_path):
    root = ready_copy(tmp_path)
    ready, checkpoint, parsed, tool, evidence = ready_bundle(root, 'w007-valid')
    assert from_inputs_ready(ready, checkpoint, parsed, tool, evidence)
    for altered in (evidence[:-1], evidence + evidence[:1]):
        with pytest.raises(ValueError):
            from_inputs_ready(ready, checkpoint, parsed, tool, altered)
    value = mutable(ready.value)
    value['source_cdl']['tops'][0]['name'] = 'FORGED'
    with pytest.raises(ValueError):
        from_inputs_ready(replace(ready, value=value), checkpoint, parsed, tool, evidence)


@pytest.mark.parametrize('mutation', ['schema', 'extra', 'missing', 'status', 'trailing', 'float'])
def test_wire_rejects_unknown_version_fields_and_invalid_value_combinations(accepted, mutation):
    encoded = encode_record(accepted)
    value = mutable(decode(encoded))
    if mutation == 'schema':
        value['wire_schema'] = 'unknown/99'
    elif mutation == 'extra':
        value['record']['fields']['surprise'] = {'scalar': 1}
    elif mutation == 'missing':
        del value['record']['fields']['status']
    elif mutation == 'status':
        value['record']['fields']['status'] = {'scalar': 'error'}
    elif mutation == 'trailing':
        encoded += b'\n'
    else:
        encoded = b'1.25'
    if mutation not in ('trailing', 'float'):
        encoded = canonical_bytes(value)
    with pytest.raises(ValueError):
        decode_record(encoded)


def test_hashseed_stability_in_fresh_processes_for_full_normalized_result(accepted):
    code = '''
from pathlib import Path
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import from_parse_result, normalize
from layauto_v2.normalization.codec import record_digest
from layauto_v2.domain.circuit import semantic_digest
result = normalize(from_parse_result(read_inputs(Path(%r))))
print(record_digest(result))
print(semantic_digest(result.value.source))
print(semantic_digest(result.value.target))
''' % str(FIXTURE / 'site_config.yaml')
    outputs = []
    for seed in ('1', '987654321'):
        env = dict(os.environ, PYTHONHASHSEED=seed, PYTHONDONTWRITEBYTECODE='1')
        outputs.append(subprocess.check_output([sys.executable, '-B', '-c', code], env=env, text=True))
    assert outputs[0] == outputs[1]
    assert outputs[0].splitlines() == [record_digest(accepted), semantic_digest(accepted.value.source), semantic_digest(accepted.value.target)]


def test_normalization_and_new_domain_keep_pure_dependency_boundaries():
    import layauto_v2
    root = Path(layauto_v2.__file__).resolve().parent
    files_to_check = list((root / 'normalization').glob('*.py')) + [root / 'domain' / name for name in (
        'circuit.py', 'identifiers.py', 'intent.py', 'source_location.py')]
    assert files_to_check
    forbidden = ('pathlib', 'os', 'io', 'subprocess', 'layauto_v2.importers',
                 'layauto_v2.tooling', 'layauto_v2.repository', 'layauto_v2.pipeline',
                 'layauto_v2.transactions', 'layauto_v2.state', 'legacy_mvp', 'tests')
    violations = []
    for path in files_to_check:
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [item.name for item in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module or '']
            else:
                continue
            allowed_decoder = (path.parent.name == 'normalization' and path.name == '_validation.py'
                               and isinstance(node, ast.ImportFrom)
                               and node.module == 'layauto_v2.importers.config'
                               and {alias.name for alias in node.names} <= {'load_document', 'validate_document'})
            if not allowed_decoder:
                violations.extend((str(path), module) for module in modules if module.startswith(forbidden))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in ('open', 'hash', 'eval', 'exec'), (path, node.lineno)
    assert violations == []


@pytest.mark.parametrize('where', ['build_source', 'build_target', 'admit_source', 'join_identities'])
@pytest.mark.parametrize('failure', [RuntimeError('unexpected bug'), KeyboardInterrupt(), SystemExit(17)])
def test_unexpected_errors_and_process_interrupts_propagate_unchanged(accepted, monkeypatch, where, failure):
    from layauto_v2.normalization import component

    def broken(*args, **kwargs):
        raise failure

    monkeypatch.setattr(component, where, broken)
    with pytest.raises(type(failure)) as raised:
        normalize(accepted.input)
    assert raised.value is failure


@pytest.mark.parametrize('value', [None, {}, 'source.cdl', 1])
def test_normalize_requires_validated_input_dto(value):
    with pytest.raises(ValueError):
        normalize(value)


@pytest.mark.parametrize('value', [None, {}, 'success', 1])
def test_parse_adapter_requires_actual_success_record(value):
    with pytest.raises(ValueError):
        from_parse_result(value)


@pytest.mark.parametrize('field,value', [
    ('exact', 1.5), ('exact', 1), ('exact', True),
    ('exact', Fraction(-1)), ('exact', Fraction(1, 2)),
    ('unit', 'guessed'), ('source', None), ('token', ''),
])
def test_parameter_rejects_inexact_or_illegal_values(accepted, field, value):
    parameter = next(p for p in accepted.value.source.cells[0].devices[0].parameters
                     if p.axis == 'fins_per_finger')
    with pytest.raises(ValueError):
        replace(parameter, **{field: value})


@pytest.mark.parametrize('kind', ['device', 'net'])
def test_query_key_constructor_rejects_invalid_index_or_run_scope(accepted, kind):
    key = (accepted.value.device_identities if kind == 'device' else accepted.value.net_identities)[0].query_key
    for change in ({'query_run_id': ''}, {'header_id': ''}, {'kind': 'unknown'},
                   {'index': '1' if kind == 'device' else None}):
        with pytest.raises(ValueError):
            replace(key, **change)


def test_typed_semantic_identity_digests_distinguish_kind_and_cell():
    cell = CellId('CELL_A')
    other = CellId('CELL_B')
    device = DeviceId(cell, 'IDENTITY')
    net = NetId(cell, 'IDENTITY')
    assert device.digest != net.digest
    assert device.digest != DeviceId(other, 'IDENTITY').digest
    assert net.digest != NetId(other, 'IDENTITY').digest
    for bad in ('', 'with space', 7, None):
        with pytest.raises(ValueError):
            CellId(bad)
    with pytest.raises(ValueError):
        DeviceId('CELL_A', 'IDENTITY')


def test_coherent_but_foreign_query_run_keys_are_rejected_against_input(accepted):
    facts = accepted.value
    new_devices = tuple(replace(item, query_key=replace(item.query_key, query_run_id='forged-query-run')) for item in facts.device_identities)
    new_nets = tuple(replace(item, query_key=replace(item.query_key, query_run_id='forged-query-run')) for item in facts.net_identities)
    new_device_seeds = tuple(replace(item, query_key=replace(item.query_key, query_run_id='forged-query-run')) for item in facts.device_seeds)
    new_net_seeds = tuple(replace(item, query_key=replace(item.query_key, query_run_id='forged-query-run')) for item in facts.net_seeds)
    with pytest.raises(ValueError):
        forged = replace(facts, device_identities=new_devices, net_identities=new_nets,
                         device_seeds=new_device_seeds, net_seeds=new_net_seeds)
        replace(accepted, value=forged, completed=forged)


def test_delta_set_cannot_omit_one_of_several_target_obligations(tmp_path):
    root = ready_copy(tmp_path)
    edit(root, 'target.cdl', 'L=4n', 'L=5n')
    edit(root, 'target.cdl', 'W=2n', 'W=3n')
    rebind(root)
    result = normal(root)
    assert len(result.value.differences) == 4
    with pytest.raises(ValueError):
        partial = replace(result.value, differences=result.value.differences[:-1])
        replace(result, value=partial, completed=partial)


@pytest.mark.parametrize('destination,donor', [(0, 1), (1, 0)])
def test_cr01_same_capture_parameter_provenance_cannot_move_between_devices(accepted, destination, donor):
    """Independent review CR-01: a valid SHA alone does not bind a parameter owner."""
    parsed = accepted.input.parse
    value = mutable(parsed.value)
    devices = value['source_cdl']['tops'][0]['devices']
    devices[destination]['parameters']['NFIN'] = devices[donor]['parameters']['NFIN']
    completed = tuple(replace(record, payload=value['source_cdl']) if record.kind == 'source_cdl'
                      else record for record in parsed.completed)
    with pytest.raises(ValueError):
        from_parse_result(replace(parsed, value=value, completed=completed))


def test_cr01_consistent_query_value_swap_cannot_override_unchanged_field_provenance(accepted):
    parsed = accepted.input.parse
    value = mutable(parsed.value)
    for capability in ('instance_xref', 'device_regions'):
        for row in value['query'][capability]['records']:
            row['schematic_instance'] = {'MN0': 'MP0', 'MP0': 'MN0'}[row['schematic_instance']]
    completed = tuple(replace(record, payload=value['query']) if record.kind == 'query'
                      else record for record in parsed.completed)
    with pytest.raises(ValueError):
        from_parse_result(replace(parsed, value=value, completed=completed))


def test_cr01_query_polygon_cannot_borrow_other_objects_exact_values(accepted):
    parsed = accepted.input.parse
    value = mutable(parsed.value)
    first, second = value['query']['device_regions']['records']
    first['vertices_nm'] = second['vertices_nm']
    first['bbox_nm'] = second['bbox_nm']
    completed = tuple(replace(record, payload=value['query']) if record.kind == 'query'
                      else record for record in parsed.completed)
    with pytest.raises(ValueError):
        from_parse_result(replace(parsed, value=value, completed=completed))


def test_cr02_net_provenance_must_belong_to_its_own_port_and_terminal_members(accepted):
    cell = accepted.value.source.cells[0]
    signal = next(net for net in cell.nets if net.id.name == 'A')
    rail = next(net for net in cell.nets if net.id.name == 'VDD')
    with pytest.raises(ValueError):
        forged = replace(signal, sources=rail.sources)
        replace(cell, nets=tuple(forged if net.id == signal.id else net for net in cell.nets))


def test_unordered_identity_seed_permutations_have_canonical_record_digest(accepted):
    facts = accepted.value
    reordered = replace(facts, device_identities=tuple(reversed(facts.device_identities)),
                        net_identities=tuple(reversed(facts.net_identities)),
                        device_seeds=tuple(reversed(facts.device_seeds)),
                        net_seeds=tuple(reversed(facts.net_seeds)))
    rebuilt = replace(accepted, value=reordered, completed=reordered)
    assert record_digest(rebuilt) == record_digest(accepted)


@pytest.mark.parametrize('case,expected_code', [
    ('multifinger', 'UnsupportedFingerCount'),
    ('device_reduction', 'UnsupportedDeviceReduction'),
    ('swap', 'UnsupportedTerminalSwap'),
    ('multiplicity', 'UnsupportedMultiplicity'),
    ('comparator', 'UnsupportedSemanticComparator'),
    ('pin_count', 'SourceTopIdentityMismatch'),
])
def test_cr05_real_unadmitted_source_cannot_be_relabelled_as_success(tmp_path, case, expected_code):
    """A complete-looking DTO must not bypass actual source profile admission.

    The raw C10 extra row is deliberately omitted from the forged identity table;
    the other cases retain their real forbidden NF/M/swap evidence unchanged.
    """
    from layauto_v2.domain.identifiers import QueryKey
    from layauto_v2.normalization.contracts import (DeviceIdentity, NetIdentity,
        DeviceAnnotationSeed, NetAnnotationSeed, NormalizationResult)
    from w005_cases import apply_case, copy_input, without_cache

    root = copy_input(tmp_path)
    if case in ('multifinger', 'device_reduction'):
        apply_case(root, case)
    elif case == 'swap':
        edit(root, 'query/raw/iXref.temp', '0 Q17 0 MN0', '0 Q17 0 MN0 X')
    elif case == 'comparator':
        from w005_cases import read_json, write_json
        profile = read_json(root / 'tech/formats.json')
        profile['cdl_dialect']['semantic_comparator'] = 'unsupported-comparison-policy'
        write_json(root / 'tech/formats.json', profile)
    elif case == 'pin_count':
        edit(root, 'source.cdl', '.SUBCKT INV_M1_SYNTH A Y VSS VDD', '.SUBCKT INV_M1_SYNTH A Y VSS')
    else:
        edit(root, 'source.cdl', 'NFIN=5 NF=1 M=1', 'NFIN=5 NF=1 M=2')
    without_cache(root)
    rebind(root)
    parsed = read(root)
    outcome = normalize(from_parse_result(parsed))
    assert outcome.status == 'error' and outcome.issues[0].code == expected_code
    facts = outcome.completed
    cell = next(cell for cell in facts.source.cells if cell.id == facts.source.selected_cell)
    devices = {device.id.name: device.id for device in cell.devices}
    nets = {net.id.name: net.id for net in cell.nets}
    header, query = parsed.value['header'], parsed.value['query']

    def query_key(kind, row):
        return QueryKey(header['header_id'], header['query_run_id'], header['query_database_id'],
                        kind, row['layout_instance'] if kind == 'device' else row['lvs_name'],
                        None if kind == 'device' else row['lvs_index'])

    with pytest.raises(ValueError):
        device_identities = []
        seen = set()
        for row in query['instance_xref']['records']:
            if row['schematic_instance'] in seen:
                continue
            seen.add(row['schematic_instance'])
            device_identities.append(DeviceIdentity(devices[row['schematic_instance']],
                query_key('device', row), row['sd_swap'], row))
        net_identities = [NetIdentity(nets[row['schematic_name']], query_key('net', row), row)
                          for row in query['net_xref']['records']]
        device_seeds = [DeviceAnnotationSeed(devices[row['schematic_instance']], query_key('device', row), row)
                        for row in query['device_regions']['records']]
        net_seeds = [NetAnnotationSeed(nets[row['schematic_name']], query_key('net', row), row)
                     for row in query['net_regions']['records']]
        forged = replace(facts, device_identities=device_identities, net_identities=net_identities,
                         device_seeds=device_seeds, net_seeds=net_seeds)
        NormalizationResult('success', forged, (), forged, outcome.input)



@pytest.mark.parametrize('capability', ['instance_xref', 'net_xref', 'device_regions', 'net_regions'])
def test_cr01_completed_query_cannot_omit_one_captured_record(accepted, capability):
    parsed = accepted.input.parse
    value = mutable(parsed.value)
    value['query'][capability]['records'].pop(0)
    completed = tuple(replace(record, payload=value['query']) if record.kind == 'query'
                      else record for record in parsed.completed)
    with pytest.raises(ValueError):
        from_parse_result(replace(parsed, value=value, completed=completed))


@pytest.mark.parametrize('role', ['source_cdl', 'target_cdl'])
def test_cdl_preservation_cannot_omit_a_captured_device_record(accepted, role):
    parsed = accepted.input.parse
    value = mutable(parsed.value)
    value[role]['tops'][0]['devices'].pop(0)
    completed = tuple(replace(record, payload=value[role]) if record.kind == role
                      else record for record in parsed.completed)
    with pytest.raises(ValueError):
        from_parse_result(replace(parsed, value=value, completed=completed))


@pytest.mark.parametrize('capability', ['device_regions', 'net_regions'])
def test_cr01_fr2_region_geometry_and_all_provenance_stay_bound_to_request_ordinal(accepted, capability):
    """Moving whole valid operands must not change which queried object owns them.

    Device rows come from two response captures. The first two net rows are two
    ordinals of one response, so both cross-capture and within-capture swaps are
    covered while every original raw block remains represented exactly once.
    """
    parsed = accepted.input.parse
    value = mutable(parsed.value)
    first, second = value['query'][capability]['records'][:2]
    identity_fields = ({'record_id', 'layout_instance', 'schematic_instance', 'field_sources'}
                       if capability == 'device_regions' else
                       {'record_id', 'lvs_name', 'lvs_index', 'schematic_name', 'field_sources'})
    for field in set(first) - identity_fields:
        first[field], second[field] = second[field], first[field]
        first['field_sources'][field], second['field_sources'][field] = (
            second['field_sources'][field], first['field_sources'][field])
    completed = tuple(replace(record, payload=value['query']) if record.kind == 'query'
                      else record for record in parsed.completed)
    with pytest.raises(ValueError):
        from_parse_result(replace(parsed, value=value, completed=completed))


def test_cr01_fr2_record_id_and_object_must_use_the_same_request_entry(accepted):
    parsed = accepted.input.parse
    value = mutable(parsed.value)
    first = value['query']['device_regions']['records'][0]
    declaration = first['field_sources']['record_id']['sources'][0]
    assert declaration['json_pointer'] == '/requests/0/record_ids/0'
    declaration['json_pointer'] = '/requests/1/record_ids/0'
    completed = tuple(replace(record, payload=value['query']) if record.kind == 'query'
                      else record for record in parsed.completed)
    with pytest.raises(ValueError):
        from_parse_result(replace(parsed, value=value, completed=completed))


def test_cr01_fr3_geometry_plus_metadata_permutation_cannot_rebind_captured_requests(accepted):
    """Metadata is derived evidence; captured request object/path remains binding."""
    parsed = accepted.input.parse
    value = mutable(parsed.value)
    first, second = value['query']['device_regions']['records']
    identity_fields = {'record_id', 'layout_instance', 'schematic_instance', 'field_sources'}
    for field in set(first) - identity_fields:
        first[field], second[field] = second[field], first[field]
        first['field_sources'][field], second['field_sources'][field] = (
            second['field_sources'][field], first['field_sources'][field])
    responses = value['query']['_format_metadata']['responses']
    responses[0], responses[1] = responses[1], responses[0]
    completed = tuple(replace(record, payload=value['query']) if record.kind == 'query'
                      else record for record in parsed.completed)
    forged = replace(parsed, value=value, completed=completed)
    assert forged.sources == parsed.sources
    with pytest.raises(ValueError):
        from_parse_result(forged)


@pytest.mark.parametrize('via', ['adapter', 'wire', 'wire_result'])
def test_captured_requests_decoder_input_error_becomes_invalid_dto(accepted, monkeypatch, via):
    from layauto_v2.normalization import _validation
    from layauto_v2.domain.results import InputError
    encoded = encode_record(accepted if via == 'wire_result' else accepted.input)

    def bad_captured_document(source, **kwargs):
        raise InputError('parse', 'InvalidDocumentSyntax', 'injected invalid captured request', source.ref(line=1, column=1))

    monkeypatch.setattr(_validation, 'load_document', bad_captured_document)
    with pytest.raises(ValueError):
        if via == 'adapter':
            from_parse_result(accepted.input.parse)
        else:
            decode_record(encoded)


@pytest.mark.parametrize('via', ['adapter', 'wire', 'wire_result'])
@pytest.mark.parametrize('failure', [RuntimeError('decoder implementation bug'), TypeError('decoder bug'),
                                     KeyError('decoder bug'), KeyboardInterrupt(), SystemExit(29)])
def test_captured_requests_decoder_unexpected_errors_propagate_unchanged(accepted, monkeypatch, via, failure):
    from layauto_v2.normalization import _validation
    encoded = encode_record(accepted if via == 'wire_result' else accepted.input)

    def broken_decoder(*args, **kwargs):
        raise failure

    monkeypatch.setattr(_validation, 'load_document', broken_decoder)
    with pytest.raises(type(failure)) as raised:
        if via == 'adapter':
            from_parse_result(accepted.input.parse)
        else:
            decode_record(encoded)
    assert raised.value is failure
