"""W008 independent drawn-base geometry, coverage and public-contract checks."""
from __future__ import annotations

import ast
import builtins
import io
import os
import subprocess
import sys
from collections import Counter
from dataclasses import FrozenInstanceError, fields, replace
from fractions import Fraction
from pathlib import Path

import pytest

from layauto_v2.domain.codec import canonical_bytes, decode, freeze_map
from layauto_v2.domain.evidence import SourceRef
from layauto_v2.domain.geometry import (
    GeometryRecordId, GeometryRef, OccupantFragmentId, Rect, StreamLayerKey,
)
from layauto_v2.domain.publication import InputsReady
from layauto_v2.normalization import from_parse_result, normalize
from layauto_v2.normalization.codec import record_digest as semantic_record_digest
from layauto_v2.normalization.geometry import build_geometry
from layauto_v2.normalization.geometry_codec import decode_record, encode_record, record_digest
from layauto_v2.normalization.geometry_input import geometry_from_parse_result, geometry_from_inputs_ready
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository
from layauto_v2.state.coordinate import BasePartition, LayerPartition, build_partition
from layauto_v2.state.occupancy import BaseCellId, BaseOccupancy, OccupantFragment, build_occupancy, fragment_identity

from w005_cases import FIXTURE, inventory, renamed_input
from w006_cases import caller_request
from w007_cases import mutable, read, ready_copy
from w008_geometry_cases import EXPECTED_RECTS, STREAM_LAYER, area, edit_geometry, hand_multiset, independent_coverage, overlap_area


def build(root=FIXTURE):
    result = build_geometry(geometry_from_parse_result(read(root)))
    assert result.status == 'success', result.issues
    assert result.value is not None
    return result


@pytest.fixture(scope='module')
def accepted():
    return build()


def no_stage_claims(value):
    forbidden = {'no_change', 'baseline', 'body_complete', 'physical_edges', 'components', 'net_id',
                 'device_id', 'terminal', 'coordinate_ref', 'canonical_context', 'final_snapshot_id',
                 'deployment_disposition', 'ordered_commit_ids', 'extraction_equal'}
    assert not forbidden & {field.name for field in fields(value)}
    for name in forbidden:
        assert not hasattr(value, name)


def test_actual_input_all_hand_geometry_and_precise_backlinks_without_io(monkeypatch):
    before = inventory(FIXTURE)
    parsed = read(FIXTURE)
    semantic = normalize(from_parse_result(parsed))
    semantic_before = semantic_record_digest(semantic)
    captured = {source.uri: source for source in parsed.sources}

    def forbidden(*args, **kwargs):
        pytest.fail('geometry must use already captured bytes, never file IO')

    with monkeypatch.context() as patch:
        for method in ('open', 'read_bytes', 'read_text', 'resolve'):
            patch.setattr(Path, method, forbidden)
        patch.setattr(builtins, 'open', forbidden)
        patch.setattr(io, 'open', forbidden)
        result = build_geometry(geometry_from_parse_result(parsed))
    occupancy = result.value
    assert result.status == 'success' and not result.issues and occupancy is not None
    layout = occupancy.layout
    assert layout.top == 'INV_M1_SYNTH'
    assert len(layout.records) == 40
    assert Counter((r.layer, r.rect.bounds) for r in layout.records) == hand_multiset()
    assert len({r.id for r in layout.records}) == 40
    for record in layout.records:
        assert record.source.uri == 'source.gds'
        assert record.source.sha256 == captured['source.gds'].sha256
        assert record.stream_key == StreamLayerKey('BOUNDARY', STREAM_LAYER[record.layer], 0)
        assert record.purpose == 'drawing'
        assert record.unit_ref == layout.units.ref
        assert record.policy_ref == layout.policy(record.layer).ref
        assert record.raw_xy == record.preservation['xy']
        assert record.source.byte_offset == record.preservation['byte_offset']
        assert record.source.record_index == record.preservation['record_index']
        byte_start = record.source.byte_offset
        assert captured['source.gds'].data[byte_start:byte_start + 4] == bytes.fromhex('00040800')
        assert record.rect.bounds == record.preservation['bbox']  # selected 1 nm source/canonical DBU
    assert layout.gds.payload['raw_document'] == captured['source.gds'].data
    assert layout.formats.sources[0].uri == 'tech/formats.json'
    assert layout.drawn.sources[0].uri == 'tech/drawn.json'
    assert len(parsed.value['body']['shapes']) == 6
    assert not {'BTAP_N', 'BTAP_P'} & {record.layer for record in layout.records}
    assert semantic_record_digest(semantic) == semantic_before
    assert semantic.value.device_seeds and semantic.value.net_seeds
    for value in (result, occupancy, occupancy.partition, layout, *layout.records, *occupancy.fragments):
        no_stage_claims(value)
    assert inventory(FIXTURE) == before


def test_normal_layer_edges_and_complete_independent_coverage(accepted):
    occupancy = accepted.value
    # 40 source records minus nonprojected boundary+marker = 38. LI long branch
    # crosses three internal y edges (55,130,155), adding three fragments.
    assert len(occupancy.fragments) == 41
    assert Counter(f.cell.layer for f in occupancy.fragments) == {
        'BODY_N': 1, 'BODY_P': 1, 'OD': 2, 'POLY': 1, 'FIN': 18, 'LI': 6,
        'CONTACT': 4, 'VIA0': 3, 'GCONTACT': 1, 'M1': 4,
    }
    assert occupancy.partition.layer('LI').xs == (28, 34, 84, 90)
    assert occupancy.partition.layer('LI').ys == (30, 55, 130, 155, 165)
    assert occupancy.partition.layer('CUT').xs == ()
    with pytest.raises(KeyError):
        occupancy.partition.layer('MARKER')
    long_li = next(r for r in occupancy.layout.records if r.layer == 'LI' and r.rect.bounds == (84, 30, 90, 165))
    assert {f.rect.bounds for f in occupancy.for_record(long_li.id)} == {
        (84, 30, 90, 55), (84, 55, 90, 130), (84, 130, 90, 155), (84, 155, 90, 165),
    }
    # OD stays drawn-wide: terminal S/D partition is a later physical task.
    assert {f.rect.bounds for f in occupancy.fragments if f.cell.layer == 'OD'} == set(EXPECTED_RECTS['OD'])
    independent_coverage(occupancy)


def test_real_w006_readback_and_w007_combine_without_publishing(tmp_path, monkeypatch):
    root = ready_copy(tmp_path)
    repository = PublicationRepository()
    ready = prepare_inputs(repository, caller_request(root, run_id='w008-geometry-combination'))
    assert isinstance(ready, InputsReady)
    checkpoint = repository.load_checkpoint(ready.run_id)
    parse = repository.read(ready.parse_ref)
    tool = repository.read(ready.tool_ref)
    audits = tuple(repository.read(ref) for ref in ready.evidence_refs)
    before = repository.load_attempt(ready.run_id)
    semantic = normalize(from_parse_result(parse.result))
    semantic_before = semantic_record_digest(semantic)
    direct = build(root)

    def forbidden(*args, **kwargs):
        pytest.fail('pure geometry construction cannot acquire, read back or publish')

    with monkeypatch.context() as patch:
        patch.setattr(Path, 'open', forbidden)
        patch.setattr(Path, 'resolve', forbidden)
        patch.setattr(builtins, 'open', forbidden)
        patch.setattr(io, 'open', forbidden)
        patch.setattr(repository, 'read', forbidden)
        result = build_geometry(geometry_from_inputs_ready(ready, checkpoint, parse, tool, audits))
    assert result.status == 'success'
    assert result.value == direct.value
    assert semantic_record_digest(semantic) == semantic_before
    assert repository.load_attempt(ready.run_id) == before
    assert before.phase == 'unsealed'
    assert repository.load_checkpoint(ready.run_id) == checkpoint
    assert repository.read_terminal(ready.run_id) is None


def test_original_ticks_exact_real8_binding_and_inverse(accepted):
    unit = accepted.value.layout.units
    assert unit.nominal_tick_m == Fraction(1, 10**9)
    assert unit.canonical_tick_nm == 1
    for tick in (-2147483648, -200, -1, 0, 1, 75, 2147483647):
        physical = Fraction(tick, 10**9) * 10**9
        assert unit.source_to_nm(tick) == physical
        assert unit.source_to_canonical(tick) == tick
        assert unit.canonical_to_source(tick) == tick
        assert unit.canonical_to_nm(tick) == physical
    for name, nominal in (('user_units_per_tick', Fraction(1, 1000)), ('metres_per_tick', Fraction(1, 10**9))):
        encoded = unit.encoded[name]
        raw = encoded['raw']
        exponent = (raw[0] & 127) - 64
        power = Fraction(16**exponent) if exponent >= 0 else Fraction(1, 16**-exponent)
        independently_decoded = Fraction(int.from_bytes(raw[1:], 'big'), 2**56) * power
        assert encoded['exact'] == independently_decoded
        assert encoded['nominal'] == nominal
        assert encoded['encoding_delta'] == independently_decoded - nominal
        assert abs(encoded['encoding_delta']) <= encoded['ulp'] / 2
    # An explicit arithmetic-only modified scale tests nonrepresentability. It is
    # not a new admitted tech profile or input default (LayoutDraft rejects it).
    contract = mutable(unit.contract)
    contract['canonical_tick_nm'] = 2
    coarse_unit = replace(unit, contract=contract)
    assert coarse_unit.source_to_canonical(4) == 2
    with pytest.raises(ValueError):
        coarse_unit.source_to_canonical(75)
    with pytest.raises(ValueError):
        replace(accepted.value.layout, units=coarse_unit)
    for invalid in (True, 1.5):
        with pytest.raises(ValueError):
            unit.source_to_canonical(invalid)


def test_record_and_vertex_reordering_preserves_semantic_multiset_not_provenance(tmp_path):
    root = ready_copy(tmp_path)
    before = build(root)
    edit_geometry(root, reorder=True, vertices=True)
    after = build(root)
    assert after.value.layout.semantic_digest == before.value.layout.semantic_digest
    assert after.value.layout.ref != before.value.layout.ref
    assert after.value.partition.ref != before.value.partition.ref
    assert after.value.ref != before.value.ref
    assert Counter((r.layer, r.rect.bounds) for r in after.value.layout.records) == hand_multiset()
    # All input ordering changed, but axes are a deterministic mathematical set.
    assert after.value.partition.layers == before.value.partition.layers
    assert set(r.id for r in before.value.layout.records).isdisjoint(r.id for r in after.value.layout.records)
    independent_coverage(after.value)


def test_legal_rename_translation_and_negative_coordinates_are_exact(tmp_path):
    root = ready_copy(tmp_path)
    before = build(root)
    change = renamed_input(root)
    after = build(root)
    assert after.value.layout.top == change['top']
    assert Counter((r.layer, r.rect.bounds) for r in after.value.layout.records) == hand_multiset(change['dx'], change['dy'])
    assert min(r.rect.y0 for r in after.value.layout.records) == -3
    assert after.value.layout.semantic_digest != before.value.layout.semantic_digest
    independent_coverage(after.value)


def test_duplicate_overlap_and_cut_preserve_distinct_records_not_wire_facts(tmp_path):
    root = ready_copy(tmp_path)
    before = build(root)
    # Three new LI records: two equal A and one partly overlapping B. This gives
    # multiple occupants of one exact index cell with independent source IDs.
    a, b = (-2, 0, 4, 4), (1, 1, 5, 3)
    cut = (0, 1, 2, 2)
    edit_geometry(root, append=(('LI', a), ('LI', a), ('LI', b), ('CUT', cut)))
    after = build(root)
    occupancy = after.value
    assert len(occupancy.layout.records) == 44
    new = [r for r in occupancy.layout.records if r.layer == 'LI' and r.rect.x0 < 10]
    assert Counter(r.rect.bounds for r in new) == {a: 2, b: 1}
    assert len({r.id for r in new}) == 3
    assert occupancy.layout.semantic_digest != before.value.layout.semantic_digest
    shared = next(f.cell for f in occupancy.fragments if f.cell.layer == 'LI' and f.rect.bounds == (1, 1, 4, 3))
    occupants = occupancy.in_cell(shared)
    assert len(occupants) == 3
    assert {f.record_id for f in occupants} == {r.id for r in new}
    assert sorted(sum(f.rect.area for f in occupancy.for_record(r.id)) for r in new) == [8, 24, 24]
    assert {r.rect.bounds for r in occupancy.layout.records if r.layer == 'CUT'} == {cut}
    # Raw CUT does not subtract from LI or create effective topology.
    assert sum(f.rect.area for f in occupancy.for_record(new[0].id)) == 24
    for record in occupancy.layout.records:
        if record.layer in ('VIA0', 'CONTACT', 'GCONTACT'):
            assert all(f.cell.layer == record.layer for f in occupancy.for_record(record.id))
    independent_coverage(occupancy)


def test_manual_partition_and_named_coarse_witness_preserve_boundaries():
    layer = LayerPartition('manual-LI', (-2, 1, 4, 5), (0, 1, 3, 4))
    a, b = Rect(-2, 0, 4, 4), Rect(1, 1, 5, 3)
    assert {(x, y, r.bounds) for x, y, r in layer.project(a)} == {
        (0, 0, (-2, 0, 1, 1)), (0, 1, (-2, 1, 1, 3)), (0, 2, (-2, 3, 1, 4)),
        (1, 0, (1, 0, 4, 1)), (1, 1, (1, 1, 4, 3)), (1, 2, (1, 3, 4, 4)),
    }
    assert {(x, y, r.bounds) for x, y, r in layer.project(b)} == {
        (1, 1, (1, 1, 4, 3)), (2, 1, (4, 1, 5, 3)),
    }
    assert layer.point_to_index(-2, 0) == (0, 0)
    assert layer.point_to_index(1, 1) == (1, 1)
    assert layer.point_to_index(Fraction(9, 2), Fraction(7, 2)) == (2, 2)
    for point in ((5, 0), (0, 4), (-3, 0), (0, -1)):
        with pytest.raises(ValueError):
            layer.point_to_index(*point)
    coarse = LayerPartition('test-only-coarse-32x16', (0, 32), (0, 16))
    left, right = Rect(1, 1, 3, 3), Rect(7, 1, 9, 3)
    assert coarse.project(left) == ((0, 0, left),)
    assert coarse.project(right) == ((0, 0, right),)
    assert overlap_area(left.bounds, right.bounds) == 0
    # Sharing an index cell contains no assertion about physical connectivity.
    no_stage_claims(coarse)


def test_partition_rebuild_uses_only_bound_geometry_and_policy(accepted):
    occupancy = accepted.value
    rebuilt = build_occupancy(build_partition(occupancy.layout))
    assert rebuilt == occupancy
    assert rebuilt.ref == occupancy.ref
    assert rebuilt.partition.ref == occupancy.partition.ref
    assert occupancy.partition.physical_to_index('LI', 84, 55) == (2, 1)
    assert occupancy.partition.index_to_physical('LI', 2, 1) == tuple(map(Fraction, (84, 55, 90, 130)))
    with pytest.raises(ValueError):
        occupancy.partition.physical_to_index('LI', 90, 55)
    with pytest.raises(ValueError):
        replace(occupancy.partition, layers=(LayerPartition('LI', (0, 32), (0, 16)),))
    with pytest.raises(ValueError):
        replace(occupancy.partition, algorithm='unbound-algorithm/2')
    with pytest.raises(ValueError):
        replace(occupancy.partition, boundary='closed_both_sides')


@pytest.mark.parametrize('change', ['omit', 'duplicate', 'wrong_rect', 'foreign_record', 'wrong_unit', 'wrong_cell'])
def test_occupancy_constructor_rejects_incomplete_or_foreign_fragments(accepted, change):
    occupancy = accepted.value
    fragments = list(occupancy.fragments)
    old = fragments[0]
    if change == 'omit':
        fragments.pop()
    elif change == 'duplicate':
        fragments.append(fragments[-1])
    else:
        record_id, cell, rect, unit_ref = old.record_id, old.cell, old.rect, old.unit_ref
        if change == 'wrong_rect':
            rect = Rect(rect.x0, rect.y0, rect.x1 + 1, rect.y1)
        elif change == 'foreign_record':
            record_id = GeometryRecordId('e' * 64)
        elif change == 'wrong_unit':
            unit_ref = GeometryRef('unit', 'f' * 64)
        elif change == 'wrong_cell':
            cell = replace(cell, x=cell.x + 1)
        fragments[0] = OccupantFragment(fragment_identity(record_id, cell, rect, unit_ref), record_id, cell, rect, unit_ref)
    with pytest.raises(ValueError):
        BaseOccupancy(occupancy.partition, fragments)


@pytest.mark.parametrize('change', ['omit', 'duplicate', 'foreign_source', 'wrong_unit', 'wrong_policy', 'wrong_rect'])
def test_layout_constructor_rejects_missing_or_rebound_drawn_records(accepted, change):
    layout = accepted.value.layout
    records = list(layout.records)
    if change == 'omit':
        records.pop()
    elif change == 'duplicate':
        records.append(records[-1])
    else:
        record = records[0]
        with pytest.raises(ValueError):
            if change == 'foreign_source':
                replace(record, source=SourceRef('foreign.gds', record.source.sha256,
                                                byte_offset=record.source.byte_offset, record_index=record.source.record_index))
            else:
                changes = {
                    'wrong_unit': {'unit_ref': GeometryRef('unit', 'e' * 64)},
                    'wrong_policy': {'policy_ref': GeometryRef('layer_policy', 'e' * 64)},
                    'wrong_rect': {'rect': Rect(0, 0, 161, 200)},
                }
                records[0] = replace(record, **changes[change])
                replace(layout, records=records)
        return
    with pytest.raises(ValueError):
        replace(layout, records=records)


def test_recursive_immutability_copies_sequences_and_never_aliases_nested_maps(accepted):
    occupancy = accepted.value
    before = record_digest(occupancy)
    fragments = list(occupancy.fragments)
    copied = replace(occupancy, fragments=fragments)
    fragments.clear()
    assert copied.fragments == occupancy.fragments
    records = list(occupancy.layout.records)
    policies = list(occupancy.layout.policies)
    layout = replace(occupancy.layout, records=records, policies=policies)
    records.clear()
    policies.clear()
    assert layout == occupancy.layout
    original = occupancy.layout.records[0]
    xy = [list(point) for point in original.raw_xy]
    preservation = mutable(original.preservation)
    copied_record = replace(original, raw_xy=xy, preservation=preservation)
    xy[0][0] = 999
    preservation['bbox'][0] = 999
    assert copied_record == original
    with pytest.raises(FrozenInstanceError):
        copied_record.layer = 'foreign'
    with pytest.raises(TypeError):
        copied_record.preservation['bbox'] = (0, 0, 1, 1)
    assert record_digest(occupancy) == before


def test_closed_codec_roundtrip_for_all_geometry_records(accepted):
    occupancy = accepted.value
    layout = occupancy.layout
    objects = [accepted, accepted.input, occupancy, occupancy.partition, layout, layout.units,
               layout.policies[0], layout.records[0], layout.records[0].id, layout.records[0].stream_key,
               layout.records[0].rect, layout.ref, occupancy.fragments[0], occupancy.fragments[0].cell,
               occupancy.fragments[0].id, occupancy.partition.layers[0]]
    for obj in objects:
        wire = encode_record(obj)
        clone = decode_record(wire)
        assert clone == obj
        assert encode_record(clone) == wire
        assert record_digest(clone) == record_digest(obj)
    # Canonical scalar decoder rejects numeric shortcuts before DTO dispatch.
    with pytest.raises(ValueError):
        decode_record(b'{"$map":{"wire_schema":"foreign","record":1.0}}')
    with pytest.raises(ValueError):
        decode_record(encode_record(occupancy) + b'\n')


def mutate_first_record(tree, record_name, mutate):
    if isinstance(tree, dict):
        if tree.get('record') == record_name and isinstance(tree.get('fields'), dict):
            mutate(tree['fields'])
            return True
        return any(mutate_first_record(value, record_name, mutate) for value in tree.values())
    if isinstance(tree, list):
        return any(mutate_first_record(value, record_name, mutate) for value in tree)
    return False


@pytest.mark.parametrize('record_name,change', [
    ('LayoutDraft', 'unknown'), ('LayoutDraft', 'schema'),
    ('BasePartition', 'unknown'), ('BaseOccupancy', 'schema'),
    ('DrawnRecord', 'unknown'), ('OccupantFragment', 'unknown'),
])
def test_wire_unknown_fields_and_versions_are_rejected(accepted, record_name, change):
    tree = mutable(decode(encode_record(accepted.value)))
    def mutate(record_fields):
        if change == 'unknown':
            record_fields['invented'] = {'scalar': True}
        else:
            record_fields['schema_version'] = {'scalar': 'foreign/99'}
    assert mutate_first_record(tree, record_name, mutate)
    with pytest.raises(ValueError):
        decode_record(canonical_bytes(tree))


def test_public_success_rejects_other_input_geometry(tmp_path, accepted):
    root = ready_copy(tmp_path)
    edit_geometry(root, append=(('LI', (-2, 0, 4, 4)),))
    different = build(root)
    with pytest.raises(ValueError):
        replace(accepted, value=different.value)


def test_hash_seed_does_not_change_content_or_semantic_ids(accepted):
    code = '''
from pathlib import Path
from layauto_v2.importers import read_inputs
from layauto_v2.normalization.geometry_input import geometry_from_parse_result
from layauto_v2.normalization.geometry import build_geometry
from layauto_v2.normalization.geometry_codec import record_digest
r=build_geometry(geometry_from_parse_result(read_inputs(Path(%r))))
print(record_digest(r))
print(r.value.layout.semantic_digest)
print(r.value.partition.ref.sha256)
print(r.value.ref.sha256)
''' % str(FIXTURE / 'site_config.yaml')
    output = []
    for seed in ('1', '987654321'):
        output.append(subprocess.check_output([sys.executable, '-B', '-c', code], text=True,
                                             env=dict(os.environ, PYTHONHASHSEED=seed, PYTHONDONTWRITEBYTECODE='1')))
    assert output[0] == output[1]
    assert output[0].splitlines() == [record_digest(accepted), accepted.value.layout.semantic_digest,
                                     accepted.value.partition.ref.sha256, accepted.value.ref.sha256]


def test_domain_state_dependency_direction_and_no_hidden_occupancy_owner():
    import layauto_v2
    root = Path(layauto_v2.__file__).resolve().parent
    paths = [root / 'domain/geometry.py', *(root / 'state' / name for name in ('coordinate.py', 'layout_store.py', 'occupancy.py'))]
    forbidden = ('layauto_v2.normalization', 'layauto_v2.importers', 'layauto_v2.pipeline',
                 'layauto_v2.repository', 'layauto_v2.transactions', 'legacy_mvp', 'tests',
                 'pathlib', 'subprocess', 'os', 'io')
    for path in paths:
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                imports = [node.module or '']
            else:
                imports = []
            assert not any(module.startswith(forbidden) for module in imports), (path, imports)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in ('open', 'hash', 'eval', 'exec'), (path, node.lineno)
    assert {field.name for field in fields(BasePartition)} == {'layout', 'layers', 'algorithm', 'boundary', 'schema_version'}
    assert not hasattr(BasePartition, 'occupancy')


@pytest.mark.parametrize('where', ['build_layout', 'build_partition', 'build_occupancy'])
@pytest.mark.parametrize('failure', [RuntimeError('unexpected geometry bug'), KeyboardInterrupt(), SystemExit(19)])
def test_builder_unexpected_errors_and_interrupts_propagate_same_object(accepted, monkeypatch, where, failure):
    from layauto_v2.normalization import geometry

    def broken(*args, **kwargs):
        raise failure

    monkeypatch.setattr(geometry, where, broken)
    with pytest.raises(type(failure)) as caught:
        geometry.build_geometry(accepted.input)
    assert caught.value is failure


def test_unsupported_comparator_is_located_error_with_completed_capture_facts(tmp_path, accepted):
    from w005_cases import read_json, rebind, write_json

    root = ready_copy(tmp_path)
    path = root / 'tech/formats.json'
    document = read_json(path)
    document['geometry_capability']['comparator'] = 'hypothetical_topology_comparator/9'
    write_json(path, document)
    rebind(root)
    parsed = read(root)
    input = geometry_from_parse_result(parsed)
    result = build_geometry(input)
    assert result.status == 'error' and result.value is None
    assert result.layout is None and result.partition is None
    assert len(result.issues) == 1
    issue = result.issues[0]
    assert (issue.category, issue.code) == ('unsupported', 'UnsupportedGeometryComparator')
    assert issue.source.uri == 'tech/formats.json'
    assert issue.source.field == '/geometry_capability/comparator'
    assert issue.source.sha256 == next(s.sha256 for s in parsed.sources if s.uri == issue.source.uri)
    assert result.completed == parsed.completed
    assert result.body_evidence == next(e for e in parsed.completed if e.kind == 'body')
    assert decode_record(encode_record(result)) == result
    with pytest.raises(ValueError):
        replace(result, status='success', value=accepted.value, issues=())
    with pytest.raises(ValueError):
        replace(result, issues=())
    with pytest.raises(ValueError):
        replace(result, completed=result.completed[:-1])
    with pytest.raises(ValueError):
        replace(accepted, status='error', value=None, issues=result.issues)


@pytest.mark.parametrize('change', ['missing_value', 'missing_completed', 'illegal_status', 'error_with_value'])
def test_illegal_success_and_error_combinations_rejected(accepted, change):
    changes = {
        'missing_value': {'value': None},
        'missing_completed': {'completed': ()},
        'illegal_status': {'status': 'no_change'},
        'error_with_value': {'status': 'error'},
    }
    with pytest.raises(ValueError):
        replace(accepted, **changes[change])


def test_evidence_consistent_forgery_cannot_become_capture_authenticated_success(accepted):
    from layauto_v2.domain.evidence import EvidenceRecord
    from layauto_v2.state.layout_store import build_layout

    original = accepted.value.layout
    document = mutable(original.gds.payload)
    document['elements'][0]['bbox'][2] = 161
    for point in document['elements'][0]['xy']:
        if point[0] == 160:
            point[0] = 161
    forged_evidence = EvidenceRecord('gds', document, original.gds.sources)
    assert forged_evidence.payload['raw_document'] == original.gds.payload['raw_document']
    # Neutral drafts enforce evidence consistency, and intentionally have no raw
    # parser dependency. The public success boundary authenticates the capture.
    forged_layout = build_layout(forged_evidence, original.drawn, original.formats)
    assert forged_layout.records[0].rect == Rect(0, 0, 161, 200)
    forged_occupancy = build_occupancy(build_partition(forged_layout))
    with pytest.raises(ValueError):
        replace(accepted, value=forged_occupancy)


@pytest.mark.parametrize('record_name,field', [('LayoutDraft', 'records'), ('BaseOccupancy', 'fragments')])
def test_wire_omitted_geometry_or_fragments_rejected(accepted, record_name, field):
    tree = mutable(decode(encode_record(accepted.value)))
    def remove_one(record_fields):
        record_fields[field]['tuple'].pop()
    assert mutate_first_record(tree, record_name, remove_one)
    with pytest.raises(ValueError):
        decode_record(canonical_bytes(tree))


def test_special_cut_islands_stream_remains_drawn_base_not_effective_topology(tmp_path):
    from w005_cases import read_json, rebind, write_json

    root = ready_copy(tmp_path)
    # This temporary derived input isolates the existing special stream's drawn
    # geometry. Header/body top/hash are explicitly rebound; no assertion is
    # made that its retained semantic/query/body associations describe physics.
    special = FIXTURE / 'special/cut_islands/source.gds'
    (root / 'source.gds').write_bytes(special.read_bytes())
    header = read_json(root / 'query/header.json')
    header['top_identities']['layout'] = 'CUT_ISLANDS_SYNTH'
    write_json(root / 'query/header.json', header)
    body = read_json(root / 'body/context.json')
    body['top'] = 'CUT_ISLANDS_SYNTH'
    write_json(root / 'body/context.json', body)
    for name in ('iXref.temp', 'nXref.temp'):
        path = root / 'query/raw' / name
        lines = path.read_text().splitlines()
        lines[1] = '# SVDB: Layout Primary CUT_ISLANDS_SYNTH'
        lines[7] = lines[7].replace('INV_M1_SYNTH', 'CUT_ISLANDS_SYNTH', 1)
        path.write_text('\n'.join(lines) + '\n')
    rebind(root)
    result = build(root)
    occupancy = result.value
    assert occupancy.layout.top == 'CUT_ISLANDS_SYNTH'
    assert Counter((r.layer, r.rect.bounds) for r in occupancy.layout.records) == {
        ('BOUNDARY', (0, 0, 160, 200)): 1,
        ('LI', (130, 20, 150, 24)): 1,
        ('CUT', (139, 18, 141, 26)): 1,
        ('LI', (50, 20, 60, 24)): 1,
    }
    assert len(occupancy.fragments) == 3
    assert occupancy.partition.layer('LI').xs == (50, 60, 130, 150)
    assert occupancy.partition.layer('LI').ys == (20, 24)
    branch = next(r for r in occupancy.layout.records if r.layer == 'LI' and r.rect.x0 == 130)
    fragments = occupancy.for_record(branch.id)
    assert len(fragments) == 1 and fragments[0].rect.bounds == (130, 20, 150, 24)
    assert sum(area(f.rect.bounds) for f in fragments) == 80
    assert not any(r.rect.bounds in ((130, 20, 139, 24), (141, 20, 150, 24)) for r in occupancy.layout.records)
    independent_coverage(occupancy)
    no_stage_claims(result)
    no_stage_claims(occupancy)
