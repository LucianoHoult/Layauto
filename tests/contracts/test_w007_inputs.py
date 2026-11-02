"""Independent A1–A5 checks from actual CDL/profile/query input bytes."""
from __future__ import annotations

import builtins
from dataclasses import fields
from fractions import Fraction
from pathlib import Path

import pytest

from layauto_v2.domain.circuit import semantic_digest
from layauto_v2.domain.normalization_codec import record_digest
from layauto_v2.domain.publication import InputsReady
from layauto_v2.normalization import from_inputs_ready, from_parse_result, normalize
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository

from w005_cases import FIXTURE, apply_case, copy_input, inventory, read_json, rebind, renamed_input, write_json
from w006_cases import caller_request
from w007_cases import (EXPECTED_MEMBERS, EXPECTED_PARAMETERS, EXPECTED_REGIONS,
                        edit, exact, normal, query_only_rename, read, ready_copy)


def by_name(values):
    return {value.id.name: value for value in values}


def assert_no_state_claims(value):
    for name in ('no_change', 'baseline', 'body_complete', 'extraction_equal',
                 'terminal', 'lifecycle_status', 'deployment_disposition',
                 'canonical_context', 'final_snapshot_id', 'ordered_commit_ids'):
        assert not hasattr(value, name)


def test_actual_w005_full_manual_semantics_and_source_backlinks_without_io(monkeypatch):
    fixture_before = inventory(FIXTURE)
    parsed = read(FIXTURE)
    captured = {source.uri: source for source in parsed.sources}

    def forbidden(*args, **kwargs):
        pytest.fail('normalization must consume captured evidence without file IO')

    with monkeypatch.context() as patch:
        patch.setattr(Path, 'open', forbidden)
        patch.setattr(Path, 'read_bytes', forbidden)
        patch.setattr(Path, 'read_text', forbidden)
        patch.setattr(Path, 'resolve', forbidden)
        patch.setattr(builtins, 'open', forbidden)
        result = normalize(from_parse_result(parsed))
    assert result.status == 'success' and not result.issues
    facts = result.value
    assert facts is not None
    assert facts.source is not facts.target
    assert semantic_digest(facts.source) == semantic_digest(facts.target)
    assert record_digest(facts.source) != record_digest(facts.target)
    assert facts.differences == ()
    for circuit, source_uri in ((facts.source, 'source.cdl'), (facts.target, 'target.cdl')):
        assert len(circuit.cells) == 1
        cell = circuit.cells[0]
        assert cell.id.name == 'INV_M1_SYNTH'
        assert tuple(net.name for net in cell.ports) == ('A', 'Y', 'VSS', 'VDD')
        assert cell.globals == ()
        devices = by_name(cell.devices)
        assert set(devices) == {'MN0', 'MP0'}
        for name, model, rail, nfin in (('MN0', 'TOY_N', 'VSS', 5), ('MP0', 'TOY_P', 'VDD', 7)):
            device = devices[name]
            assert device.model == model and device.id.cell == cell.id
            assert [(terminal.role, terminal.net_id.name) for terminal in device.terminals] == [
                ('D', 'Y'), ('G', 'A'), ('S', rail), ('B', rail)]
            params = {param.axis: param for param in device.parameters}
            assert set(params) == set(EXPECTED_PARAMETERS)
            for axis, (token, value, unit, lexeme) in EXPECTED_PARAMETERS.items():
                parameter = params[axis]
                if axis == 'fins_per_finger':
                    value, lexeme = Fraction(nfin), str(nfin)
                assert (parameter.token, parameter.exact, parameter.unit, parameter.lexeme) == (token, value, unit, lexeme)
                assert isinstance(parameter.exact, (Fraction, str))
                assert parameter.source.uri == source_uri
                assert parameter.source.sha256 == captured[source_uri].sha256
                assert parameter.source.line in (3, 4)
                assert parameter.field_evidence['lexeme'] == f'{token}={lexeme}'
            for terminal in device.terminals:
                assert terminal.source.uri == source_uri
                assert terminal.source.sha256 == captured[source_uri].sha256
            assert not {'bbox', 'fin_track_indices', 'segments', 'vias', 'query_key'} & {field.name for field in fields(device)}
        nets = by_name(cell.nets)
        assert set(nets) == set(EXPECTED_MEMBERS)
        for name, members in EXPECTED_MEMBERS.items():
            assert {(member.device_id.name, member.terminal) for member in nets[name].memberships} == members
            assert nets[name].port_indices == (('A', 'Y', 'VSS', 'VDD').index(name),)
            assert nets[name].global_net is False
            assert not {'segments', 'vias', 'bbox', 'query_key'} & {field.name for field in fields(nets[name])}
    assert_no_state_claims(result)
    assert_no_state_claims(facts)
    assert inventory(FIXTURE) == fixture_before


def test_actual_query_identity_and_every_seed_match_handwritten_regions():
    result = normal(FIXTURE)
    facts = result.value
    assert {(item.query_key.identity, item.device_id.name) for item in facts.device_identities} == {('Q17', 'MN0'), ('Q93', 'MP0')}
    assert {(item.query_key.identity, item.query_key.index, item.net_id.name) for item in facts.net_identities} == {
        ('n_a', '1', 'A'), ('n_y', '2', 'Y'), ('n_lo', '3', 'VSS'), ('n_hi', '4', 'VDD')}
    all_seeds = facts.device_seeds + facts.net_seeds
    assert len(facts.device_seeds) == 2 and len(facts.net_seeds) == 8
    assert {seed.record['record_id'] for seed in all_seeds} == set(EXPECTED_REGIONS)
    records = {row['record_id']: row for cap in ('device_regions', 'net_regions')
               for row in result.input.parse.value['query'][cap]['records']}
    for seed in all_seeds:
        row = seed.record
        name, layer, (x0, y0, x1, y1) = EXPECTED_REGIONS[row['record_id']]
        assert seed.semantic_id.name == name
        assert (row['derived_layer'], row['geometry_kind'], row['quality'], row['unit'], row['precision']) == (layer, 'rectangle', 'exact', 'nm', 20000)
        assert tuple((exact(p['x']), exact(p['y'])) for p in row['vertices_nm']) == ((x0, y0), (x0, y1), (x1, y1), (x1, y0))
        assert row == records[row['record_id']]
        assert row['field_sources']
        coordinate_lexemes = {entry['lexeme'] for entry in row['field_sources']['vertices_nm']['sources'] if isinstance(entry['lexeme'], str)}
        assert {str(coordinate * 20) for coordinate in (x0, y0, x1, y1)} <= coordinate_lexemes
        assert seed.query_key.header_id == 'w004.synthetic.query.2'
        assert_no_state_claims(seed)


def test_actual_w006_readback_has_equivalent_semantics_and_cannot_advance_run(tmp_path, monkeypatch):
    root = ready_copy(tmp_path)
    request = caller_request(root, run_id='w007-real-readback')
    repository = PublicationRepository()
    ready = prepare_inputs(repository, request)
    assert isinstance(ready, InputsReady)
    checkpoint = repository.load_checkpoint(ready.run_id)
    parse = repository.read(ready.parse_ref)
    tool = repository.read(ready.tool_ref)
    audits = tuple(repository.read(ref) for ref in ready.evidence_refs)
    attempt_before = repository.load_attempt(ready.run_id)
    direct = normalize(from_parse_result(read(root)))

    def forbidden(*args, **kwargs):
        pytest.fail('normalization must not fetch, parse, or publish anything')

    with monkeypatch.context() as patch:
        patch.setattr(Path, 'read_bytes', forbidden)
        patch.setattr(Path, 'open', forbidden)
        patch.setattr(builtins, 'open', forbidden)
        patch.setattr(repository, 'read', forbidden)
        result = normalize(from_inputs_ready(ready, checkpoint, parse, tool, audits))
    assert result.status == 'success'
    assert result.value.source == direct.value.source
    assert result.value.target == direct.value.target
    assert result.value.differences == direct.value.differences
    assert result.value.device_seeds == direct.value.device_seeds
    assert result.input.readback is not None
    assert repository.load_attempt(ready.run_id) == attempt_before
    assert repository.load_checkpoint(ready.run_id) == checkpoint
    assert repository.read_terminal(ready.run_id) is None
    assert attempt_before.phase == 'unsealed'
    assert_no_state_claims(result)


def test_w005_legal_source_symlink_alias_keeps_role_binding_without_resolving(tmp_path, monkeypatch):
    root = ready_copy(tmp_path)
    (root / 'source-alias.cdl').symlink_to('source.cdl')
    header = read_json(root / 'query/header.json')
    header['source_netlist']['uri'] = 'source-alias.cdl'
    write_json(root / 'query/header.json', header)
    parsed = read(root)
    assert 'source-alias.cdl' not in {item.uri for item in parsed.sources}

    def forbidden(*args, **kwargs):
        pytest.fail('W005 alias receipt must not be re-resolved')

    with monkeypatch.context() as patch:
        patch.setattr(Path, 'resolve', forbidden)
        patch.setattr(Path, 'read_bytes', forbidden)
        result = normalize(from_parse_result(parsed))
    assert result.status == 'success'
    assert result.input.parse.value['header']['source_netlist']['uri'] == 'source-alias.cdl'
    assert result.value.source.cells[0].devices[0].parameters[0].source.uri == 'source.cdl'


def test_format_only_order_changes_equal_semantics_but_keep_distinct_records(tmp_path):
    root = ready_copy(tmp_path)
    before = normal(root)
    path = root / 'target.cdl'
    path.write_text('* wholly different formatting\n\n.SUBCKT INV_M1_SYNTH A Y VSS VDD\n'
                    'MP0 Y A VDD VDD TOY_P NF=1 NFIN=7 VT=toy M=1 W=2n L=4n\n'
                    '\tMN0 Y A VSS VSS TOY_N W=2n M=1 L=4n VT=toy NFIN=5 NF=1\n'
                    '.ENDS INV_M1_SYNTH\n')
    rebind(root)
    after = normal(root)
    assert after.value.differences == ()
    assert semantic_digest(before.value.target) == semantic_digest(after.value.target)
    assert record_digest(before.value.target) != record_digest(after.value.target)
    assert after.value.source == before.value.source


def test_query_renaming_and_net_names_reordering_preserve_semantic_ids(tmp_path):
    root = ready_copy(tmp_path)
    before = normal(root)
    names = query_only_rename(root)
    after = normal(root)
    assert after.value.source == before.value.source
    assert after.value.target == before.value.target
    assert after.value.differences == ()
    assert {(identity.query_key.identity, identity.device_id) for identity in after.value.device_identities} == {
        (names[item.query_key.identity], item.device_id) for item in before.value.device_identities}
    assert {(item.query_key.identity, item.query_key.index, item.net_id.name) for item in after.value.net_identities} == {
        ('wire_z', '4', 'A'), ('wire_x', '3', 'Y'), ('wire_k', '2', 'VSS'), ('wire_t', '1', 'VDD')}
    assert {item.query_key.query_run_id for item in after.value.net_identities} == {'alternate.query.run'}
    assert {item.query_key.header_id for item in after.value.device_identities} == {'alternate.header'}


def test_second_legal_cell_and_device_names_are_not_fixture_constants(tmp_path):
    root = ready_copy(tmp_path)
    renamed_input(root)
    result = normal(root)
    cell = result.value.source.cells[0]
    assert cell.id.name == 'SECOND_CELL'
    devices = by_name(cell.devices)
    assert set(devices) == {'MN_NEW', 'MP_NEW'}
    assert {item.query_key.identity: item.device_id.name for item in result.value.device_identities} == {'Q101': 'MN_NEW', 'Q202': 'MP_NEW'}
    params = {item.axis: item.exact for item in devices['MN_NEW'].parameters}
    assert params['fins_per_finger'] == Fraction(6)
    assert result.value.differences == ()
    seed = next(s for s in result.value.device_seeds if s.semantic_id.name == 'MN_NEW')
    assert tuple((exact(p['x']), exact(p['y'])) for p in seed.record['vertices_nm']) == ((68, 17), (68, 67), (72, 67), (72, 17))


@pytest.mark.parametrize('case,code', [
    ('mapping_many_to_one', 'UnsupportedDeviceCardinality'),
    ('multifinger', 'UnsupportedFingerCount'),
    ('device_reduction', 'UnsupportedDeviceReduction'),
])
def test_original_source_admission_variants_reach_located_component_errors(tmp_path, case, code):
    root = copy_input(tmp_path)
    apply_case(root, case)
    # Applying an original case may install its historical cache: remove only
    # the disposable copy so the intended defect is isolated.
    from w005_cases import without_cache
    without_cache(root)
    rebind(root)
    parsed = read(root)
    result = normalize(from_parse_result(parsed))
    assert result.status == 'error' and result.value is None
    assert result.issues[0].code == code
    issue = result.issues[0]
    assert issue.source.sha256 == next(s.sha256 for s in parsed.sources if s.uri == issue.source.uri)
    assert issue.source.line is not None or issue.source.field is not None
    assert result.completed.source.cells and result.completed.target.cells
    assert_no_state_claims(result)


@pytest.mark.parametrize('condition', ['multiplicity', 'unknown_device', 'missing_device', 'missing_net', 'unknown_net', 'conflicting_net', 'swap'])
def test_additional_source_identity_errors_do_not_guess_or_rewrite(tmp_path, condition):
    root = ready_copy(tmp_path)
    if condition == 'multiplicity':
        edit(root, 'source.cdl', 'NFIN=5 NF=1 M=1', 'NFIN=5 NF=1 M=2')
    elif condition == 'unknown_device':
        edit(root, 'query/raw/iXref.temp', '0 Q17 0 MN0', '0 Q17 0 MUNKNOWN')
    elif condition == 'missing_device':
        edit(root, 'source.cdl', '.ENDS INV_M1_SYNTH', 'MEXTRA Y A VSS VSS TOY_N NFIN=5 NF=1 M=1 L=4n W=2n VT=toy\n.ENDS INV_M1_SYNTH')
    elif condition == 'missing_net':
        edit(root, 'source.cdl', 'MN0 Y A VSS VSS', 'MN0 Y A INTERNAL VSS')
    elif condition == 'unknown_net':
        edit(root, 'query/raw/nXref.temp', '0 n_a 0 A', '0 n_a 0 UNKNOWN')
    elif condition == 'conflicting_net':
        edit(root, 'query/raw/nXref.temp', '0 n_a 0 A', '0 n_a 0 Y')
    else:
        edit(root, 'query/raw/iXref.temp', '0 Q17 0 MN0', '0 Q17 0 MN0 X')
    rebind(root)
    parsed = read(root)
    result = normalize(from_parse_result(parsed))
    assert result.status == 'error' and result.value is None and result.issues
    if condition == 'multiplicity':
        assert result.issues[0].code == 'UnsupportedMultiplicity'
    elif condition == 'swap':
        assert result.issues[0].code == 'UnsupportedTerminalSwap'
        device = by_name(result.completed.source.cells[0].devices)['MN0']
        assert tuple((term.role, term.net_id.name) for term in device.terminals) == (('D', 'Y'), ('G', 'A'), ('S', 'VSS'), ('B', 'VSS'))
        assert any(item.sd_swap for item in result.completed.device_identities)
    assert result.completed.source.cells
    assert result.issues[0].source.sha256 in {source.sha256 for source in parsed.sources}
    assert result.issues[0].source.line is not None or result.issues[0].source.field is not None


def test_c13_retains_exact_channel_length_target_obligation_and_no_run_terminal(tmp_path):
    root = ready_copy(tmp_path)
    apply_case(root, 'unsupported_target')
    rebind(root)
    repository = PublicationRepository()
    ready = prepare_inputs(repository, caller_request(root, run_id='w007-c13'))
    assert isinstance(ready, InputsReady)
    result = normalize(from_inputs_ready(ready, repository.load_checkpoint(ready.run_id),
                       repository.read(ready.parse_ref), repository.read(ready.tool_ref),
                       tuple(repository.read(ref) for ref in ready.evidence_refs)))
    assert result.status == 'success'
    differences = result.value.differences
    assert len(differences) == 1
    difference = differences[0]
    assert difference.op_type == 'parameter_change'
    assert difference.operand_ref.name == 'MN0' and difference.axis == 'channel_length'
    assert difference.semantic_before.exact == Fraction(4, 10**9)
    assert difference.semantic_after.exact == Fraction(5, 10**9)
    assert difference.semantic_before.lexeme == '4n' and difference.semantic_after.lexeme == '5n'
    assert difference.required_capability == 'resize:channel_length'
    assert difference.source == 'cdl_diff' and difference.scope == 'device'
    assert 'planner_admission_required' in difference.obligations
    assert not difference.hard_constraints and not difference.preferences
    assert {difference.semantic_before.source, difference.semantic_after.source} <= set(difference.provenance)
    assert repository.load_attempt(ready.run_id).phase == 'unsealed'
    assert repository.read_terminal(ready.run_id) is None
    assert_no_state_claims(result)


def test_all_axes_models_and_terminals_remain_multiple_target_obligations(tmp_path):
    root = ready_copy(tmp_path)
    before = normal(root)
    edit(root, 'target.cdl', 'MN0   Y A VSS VSS TOY_N VT=toy W=2n L=4n M=1 NF=1 NFIN=5',
         'MN0   VSS A Y VSS TOY_P VT=toy W=3n L=5n M=2 NF=2 NFIN=6')
    rebind(root)
    result = normal(root)
    changes = result.value.differences
    params = {d.axis: d for d in changes if d.op_type == 'parameter_change'}
    assert set(params) == {'fins_per_finger', 'finger_count', 'multiplicity', 'channel_length', 'fin_width'}
    expected = {'fins_per_finger': (5, 6), 'finger_count': (1, 2), 'multiplicity': (1, 2),
                'channel_length': (Fraction(4, 10**9), Fraction(5, 10**9)),
                'fin_width': (Fraction(2, 10**9), Fraction(3, 10**9))}
    for axis, (old, new) in expected.items():
        assert (params[axis].semantic_before.exact, params[axis].semantic_after.exact) == (old, new)
    model = next(d for d in changes if d.op_type == 'model_change')
    assert (model.semantic_before, model.semantic_after) == ('TOY_N', 'TOY_P')
    terminals = next(d for d in changes if d.op_type == 'terminals_change')
    assert tuple(t.net_id.name for t in terminals.semantic_before) == ('Y', 'A', 'VSS', 'VSS')
    assert tuple(t.net_id.name for t in terminals.semantic_after) == ('VSS', 'A', 'Y', 'VSS')
    assert {d.operand_ref.name for d in changes if d.op_type == 'net_membership_change'} == {'Y', 'VSS'}
    assert len({d.delta_id for d in changes}) == len(changes)
    assert all(d.required_capability and d.provenance and 'planner_admission_required' in d.obligations for d in changes)
    assert result.value.source == before.value.source
    assert semantic_digest(result.value.source) != semantic_digest(result.value.target)


def test_structural_target_changes_preserve_added_removed_devices_nets_and_port_order(tmp_path):
    root = ready_copy(tmp_path)
    original = normal(root)
    (root / 'target.cdl').write_text('.SUBCKT INV_M1_SYNTH Y A VSS VDD EXTRA\n'
        'MN0 Y A INTERNAL VSS TOY_N NFIN=5 NF=1 M=1 L=4n W=2n VT=toy\n'
        'MNEW EXTRA A VDD VDD TOY_P NFIN=9 NF=1 M=1 L=4n W=2n VT=toy\n'
        '.ENDS INV_M1_SYNTH\n')
    rebind(root)
    result = normal(root)
    changes = result.value.differences
    assert {'ports_change', 'device_add', 'device_remove', 'terminals_change', 'net_add', 'net_membership_change'} <= {d.op_type for d in changes}
    assert {d.operand_ref.name for d in changes if d.op_type == 'device_add'} == {'MNEW'}
    assert {d.operand_ref.name for d in changes if d.op_type == 'device_remove'} == {'MP0'}
    assert {d.operand_ref.name for d in changes if d.op_type == 'net_add'} == {'EXTRA', 'INTERNAL'}
    port_delta = next(d for d in changes if d.op_type == 'ports_change')
    assert tuple(n.name for n in port_delta.semantic_before) == ('A', 'Y', 'VSS', 'VDD')
    assert tuple(n.name for n in port_delta.semantic_after) == ('Y', 'A', 'VSS', 'VDD', 'EXTRA')
    assert result.value.source == original.value.source


@pytest.mark.parametrize('operation', ['rename', 'add_top', 'remove_net'])
def test_every_supported_target_cell_or_net_structure_is_preserved(tmp_path, operation):
    root = ready_copy(tmp_path)
    if operation == 'rename':
        edit(root, 'target.cdl', 'INV_M1_SYNTH', 'ANOTHER_CELL')
    elif operation == 'add_top':
        with (root / 'target.cdl').open('a') as stream:
            stream.write('.SUBCKT EXTRA_CELL P Q\n.ENDS EXTRA_CELL\n')
    else:
        edit(root, 'target.cdl', ' A ', ' Y ')
        edit(root, 'target.cdl', '.SUBCKT INV_M1_SYNTH Y Y VSS VDD', '.SUBCKT INV_M1_SYNTH Y VSS VDD')
    rebind(root)
    result = normal(root)
    kinds = {delta.op_type for delta in result.value.differences}
    if operation == 'rename':
        assert {'cell_remove', 'cell_add'} <= kinds
        assert {c.id.name for c in result.value.target.cells} == {'ANOTHER_CELL'}
    elif operation == 'add_top':
        assert 'cell_add' in kinds
        assert {c.id.name for c in result.value.target.cells} == {'INV_M1_SYNTH', 'EXTRA_CELL'}
    else:
        assert 'net_remove' in kinds
        assert {d.operand_ref.name for d in result.value.differences if d.op_type == 'net_remove'} == {'A'}


def test_duplicate_layout_identity_stays_a_w005_reader_failure(tmp_path):
    from layauto_v2.importers import read_inputs
    root = ready_copy(tmp_path)
    edit(root, 'query/raw/iXref.temp', '0 Q93 0 MP0', '0 Q17 0 MP0')
    rebind(root)
    parsed = read_inputs(root / 'site_config.yaml')
    assert parsed.status == 'error'
    assert parsed.issues[0].code == 'DuplicateQueryIdentity'
    with pytest.raises(ValueError):
        from_parse_result(parsed)



def test_large_exact_target_values_are_neither_floats_nor_truncated(tmp_path):
    root = ready_copy(tmp_path)
    edit(root, 'target.cdl', 'NFIN=5', 'NFIN=9007199254740993')
    edit(root, 'target.cdl', 'L=4n', 'L=123456789012345678901n')
    rebind(root)
    result = normal(root)
    changes = result.value.differences
    counts = [d for d in changes if d.axis == 'fins_per_finger']
    lengths = [d for d in changes if d.axis == 'channel_length']
    assert len(counts) == 1 and len(lengths) == 2
    assert counts[0].semantic_after.exact == Fraction(9007199254740993)
    assert counts[0].semantic_after.lexeme == '9007199254740993'
    assert all(d.semantic_after.exact == Fraction(123456789012345678901, 10**9) for d in lengths)
    assert all(type(d.semantic_after.exact) is Fraction for d in counts + lengths)


def test_subnanometre_annotation_seed_retains_exact_raw_lexemes_without_snap(tmp_path):
    root = ready_copy(tmp_path)
    edit(root, 'query/raw/device_info_Q17.txt', ' 1160', ' 1161')
    edit(root, 'query/raw/device_info_Q17.txt', ' 1240', ' 1241')
    rebind(root)
    result = normal(root)
    seed = next(s for s in result.value.device_seeds if s.semantic_id.name == 'MN0')
    assert tuple((exact(p['x']), exact(p['y'])) for p in seed.record['vertices_nm']) == (
        (Fraction(1161, 20), 20), (Fraction(1161, 20), 70),
        (Fraction(1241, 20), 70), (Fraction(1241, 20), 20))
    refs = seed.record['field_sources']['vertices_nm']['sources']
    assert {'1161', '1241'} <= {ref['lexeme'] for ref in refs if isinstance(ref['lexeme'], str)}
    assert result.value.differences == ()
    assert_no_state_claims(result)


def test_equal_declared_semantics_do_not_claim_extraction_or_mandatory_success(tmp_path):
    from w005_cases import without_cache
    root = copy_input(tmp_path)
    apply_case(root, 'extraction_mismatch')
    without_cache(root)
    rebind(root)
    result = normal(root)
    assert result.value.differences == ()
    assert semantic_digest(result.value.source) == semantic_digest(result.value.target)
    assert {p.exact for p in by_name(result.value.source.cells[0].devices)['MN0'].parameters
            if p.axis == 'fins_per_finger'} == {Fraction(5)}
    for obj in (result, result.value, result.value.source, result.value.target):
        assert_no_state_claims(obj)


def test_delta_identity_is_stable_when_target_text_order_and_comment_change(tmp_path):
    root = ready_copy(tmp_path)
    edit(root, 'target.cdl', 'L=4n', 'L=5n')
    rebind(root)
    before = normal(root)
    text = (root / 'target.cdl').read_text()
    lines = text.splitlines()
    lines[2:4] = reversed(lines[2:4])
    (root / 'target.cdl').write_text('* another irrelevant comment\n' + '\n'.join(lines) + '\n')
    rebind(root)
    after = normal(root)
    assert {delta.delta_id for delta in before.value.differences} == {delta.delta_id for delta in after.value.differences}
    assert record_digest(before.value.target) != record_digest(after.value.target)
    assert semantic_digest(before.value.target) == semantic_digest(after.value.target)


def test_unknown_selected_semantic_comparator_is_a_located_component_issue(tmp_path):
    root = ready_copy(tmp_path)
    formats = read_json(root / 'tech/formats.json')
    formats['cdl_dialect']['semantic_comparator'] = 'an-unimplemented-comparator'
    write_json(root / 'tech/formats.json', formats)
    rebind(root)
    result = normalize(from_parse_result(read(root)))
    assert result.status == 'error' and result.value is None
    issue = result.issues[0]
    assert issue.code == 'UnsupportedSemanticComparator'
    assert issue.source.uri == 'tech/formats.json'
    assert issue.source.field == '/cdl_dialect/semantic_comparator'


def test_source_and_target_preserve_unselected_subcircuits_without_query_aliases(tmp_path):
    root = ready_copy(tmp_path)
    extra = ('.SUBCKT AUXILIARY P Q\n'
             'MAUX Q P Q Q TOY_N NFIN=3 NF=1 M=1 L=4n W=2n VT=toy\n'
             '.ENDS AUXILIARY\n')
    for name in ('source.cdl', 'target.cdl'):
        with (root / name).open('a') as stream:
            stream.write(extra)
    rebind(root)
    result = normal(root)
    assert result.value.source.selected_cell.name == 'INV_M1_SYNTH'
    for circuit in (result.value.source, result.value.target):
        assert {cell.id.name for cell in circuit.cells} == {'INV_M1_SYNTH', 'AUXILIARY'}
        auxiliary = next(cell for cell in circuit.cells if cell.id.name == 'AUXILIARY')
        assert tuple(net.name for net in auxiliary.ports) == ('P', 'Q')
        assert {device.id.name for device in auxiliary.devices} == {'MAUX'}
        assert {(member.device_id.name, member.terminal) for member in by_name(auxiliary.nets)['Q'].memberships} == {('MAUX', 'D'), ('MAUX', 'S'), ('MAUX', 'B')}
    assert result.value.differences == ()
    assert {item.device_id.name for item in result.value.device_identities} == {'MN0', 'MP0'}


def test_tab_separated_swap_token_keeps_w005_whitespace_semantics(tmp_path):
    root = ready_copy(tmp_path)
    edit(root, 'query/raw/iXref.temp', '0 Q17 0 MN0', '0 Q17 0 MN0\tX')
    rebind(root)
    parsed = read(root)
    result = normalize(from_parse_result(parsed))
    assert result.status == 'error' and result.issues[0].code == 'UnsupportedTerminalSwap'
    assert result.issues[0].source.uri == 'query/raw/iXref.temp'
    assert result.issues[0].source.line == 9
    assert any(identity.sd_swap for identity in result.completed.device_identities)
