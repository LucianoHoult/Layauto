"""W013 immutable and capture-bound public contracts.

Neutral cases exercise compact validation. Complete captured reconstruction is
reserved for a small shared receipt, so tests do not repeatedly build W011.
"""
from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import FrozenInstanceError, fields, replace
from fractions import Fraction
from pathlib import Path
import os
import subprocess
import sys

import pytest

from layauto_v2.domain.codec import canonical_bytes, decode, freeze_map
from layauto_v2.domain.identifiers import QueryKey
from layauto_v2.normalization import from_parse_result
from w005_cases import FIXTURE
from w007_cases import mutable, normal, read
from w013_cases import (neutral, neutral_inputs, normal_capture, normal_local,
                        normal_wire, readback_capture, unchecked_replace)


@pytest.fixture(scope='module')
def compact():
    return neutral(FIXTURE, normal_local().value)


def test_current_capture_scope_retains_text_ordinals_and_explicitly_rejects_007():
    """P01 choice A: refusal is a limitation, never a fabricated exact identity."""
    parsed = read(FIXTURE)
    facts = normal(FIXTURE).value
    assert {row.query_key.identity: (row.net_id.name, row.query_key.index)
            for row in facts.net_identities} == {
                'n_a': ('A', '1'), 'n_y': ('Y', '2'),
                'n_lo': ('VSS', '3'), 'n_hi': ('VDD', '4')}
    assert all(type(seed.query_key.index) is str for seed in facts.net_seeds)
    with pytest.raises(ValueError, match='positive opaque decimal index'):
        QueryKey('header', 'run', None, 'net', 'n_a', '007')

    def forged(value):
        if isinstance(value, Mapping):
            return {key: ('007' if key == 'lvs_index' and value.get('lvs_name') == 'n_a'
                          else forged(child)) for key, child in value.items()}
        if isinstance(value, tuple):
            return tuple(forged(child) for child in value)
        return value
    altered = replace(parsed, value=freeze_map(forged(parsed.value)),
                      completed=tuple(replace(row, payload=freeze_map(forged(row.payload)))
                                      for row in parsed.completed))
    with pytest.raises(ValueError, match='captured NET NAMES ordinal'):
        from_parse_result(altered)


@pytest.mark.parametrize('quality', ('approximate_bbox', 'untrimmed'))
def test_nonexact_quality_is_an_upstream_refusal_not_a_successful_w013_seed(quality):
    seed = normal(FIXTURE).value.net_seeds[0]
    row = mutable(seed.record)
    row['quality'] = quality
    with pytest.raises(ValueError, match='unsupported annotation seed geometry/quality/unit'):
        replace(seed, record=row)


def test_new_modules_keep_declared_dependency_and_no_io_boundaries():
    import layauto_v2
    root = Path(layauto_v2.__file__).resolve().parent
    pure = ('domain/net_annotation.py', 'state/annotation.py',
            'annotation/net_regions.py', 'derive/net_annotation.py')
    for relative in pure + ('normalization/net_annotation.py', 'normalization/net_annotation_codec.py'):
        tree = ast.parse((root / relative).read_text())
        forbidden = ('legacy_mvp', 'tests', 'subprocess', 'pathlib', 'os', 'io',
                     'layauto_v2.pipeline', 'layauto_v2.repository', 'layauto_v2.transactions')
        if relative in pure:
            forbidden += ('layauto_v2.normalization', 'layauto_v2.importers')
        if relative.startswith('domain/'):
            forbidden += ('layauto_v2.state', 'layauto_v2.annotation', 'layauto_v2.derive')
        for node in ast.walk(tree):
            modules = [alias.name for alias in node.names] if isinstance(node, ast.Import) else (
                [node.module or ''] if isinstance(node, ast.ImportFrom) else [])
            assert not any(module.startswith(forbidden) for module in modules), (relative, modules)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in ('open', 'hash', 'eval', 'exec'), (relative, node.lineno)


@pytest.mark.parametrize('table', ('evidence', 'targets', 'matches', 'fragments',
                                   'coverage', 'components', 'classifications'))
def test_compact_public_draft_rejects_incomplete_correlated_tables(compact, table):
    with pytest.raises(ValueError):
        replace(compact, **{table: getattr(compact, table)[1:]})


def test_compact_table_rejects_forged_coverage_component_inference_and_sources(compact):
    from layauto_v2.domain.net_annotation import AnnotationRef
    # Keep the coverage arithmetic internally consistent while lying about its
    # meaning; the aggregate must independently reconstruct the actual fragments.
    row = next(row for row in compact.coverage if row.layer == 'BODY_N')
    forged = replace(row, covered_area=row.total_area, uncovered_area=Fraction(0))
    with pytest.raises(ValueError):
        replace(compact, coverage=tuple(forged if item is row else item for item in compact.coverage))
    inferred = next(row for row in compact.components if len(row.members) == 3)
    forged = replace(inferred, directly_covered_targets=inferred.target_refs)
    with pytest.raises(ValueError):
        replace(compact, components=tuple(forged if item is inferred else item for item in compact.components))
    fragment = next(row for row in compact.fragments if row.status == 'annotated')
    foreign = AnnotationRef('evidence', 'f' * 64)
    forged = replace(fragment, evidence_refs=(foreign,))
    with pytest.raises(ValueError):
        replace(compact, fragments=tuple(forged if item is fragment else item for item in compact.fragments))
    target = compact.targets[0]
    with pytest.raises(ValueError):
        replace(compact, targets=(replace(target, source=replace(target.source, uri='foreign.gds')),)
                + compact.targets[1:])


@pytest.mark.parametrize('needed', ('query/raw/net_shapes_n_a.txt', 'source.cdl', 'tech/derived.json'))
def test_capture_source_set_must_close_all_retained_seed_and_owner_backlinks(compact, needed):
    from layauto_v2.annotation.net_regions import build_net_annotation_draft
    local = normal_local().value
    args = list(neutral_inputs(FIXTURE, local))
    binding = mutable(args[-1])
    assert any(row['uri'] == needed for row in binding['sources'])
    binding['sources'] = [row for row in binding['sources'] if row['uri'] != needed]
    args[-1] = freeze_map(binding)
    with pytest.raises(ValueError):
        build_net_annotation_draft(*args)
    # A well-formed hash alone cannot stand in for the actual derived owner role.
    args = list(neutral_inputs(FIXTURE, local))
    args[3] = replace(args[3], sources=local.binding.physical.sources)
    with pytest.raises(ValueError):
        build_net_annotation_draft(*args)


def test_compact_binding_keeps_the_source_cdl_backlink_and_rejects_substitution(compact):
    assert compact.binding.source_ref.uri == 'source.cdl'
    assert compact.binding.source_ref.sha256 is not None
    forged = replace(compact.binding, source_ref=compact.binding.derived.sources[0])
    # The original target ids bind the complete original binding as well as
    # geometry; a different source owner cannot silently retain them.
    with pytest.raises(ValueError):
        replace(compact, binding=forged)


@pytest.mark.parametrize('key_field,new_value', (('query_run_id', 'foreign.query.run'),
                                                ('database_id', 'foreign.database')))
def test_neutral_inputs_reject_mixed_query_run_or_database(compact, key_field, new_value):
    from layauto_v2.annotation.net_regions import build_net_annotation_draft
    args = list(neutral_inputs(FIXTURE, normal_local().value))
    evidence = args[2]
    mixed = replace(evidence[0], query_key=replace(evidence[0].query_key, **{key_field: new_value}))
    args[2] = (mixed,) + evidence[1:]
    with pytest.raises(ValueError):
        build_net_annotation_draft(*args)


def test_native_sequences_are_defensive_snapshots_and_record_objects_remain_frozen(compact):
    tables = ('evidence', 'targets', 'matches', 'fragments', 'coverage',
              'components', 'classifications', 'issues')
    aliases = {name: list(getattr(compact, name)) for name in tables}
    copied = replace(compact, **aliases)
    before = copied.ref
    for value in aliases.values():
        value.clear()
    assert copied == compact and copied.ref == before
    assert all(type(getattr(copied, name)) is tuple for name in tables)
    for value in (compact, compact.binding, compact.evidence[0], compact.targets[0],
                  compact.fragments[0], compact.coverage[0], compact.components[0]):
        with pytest.raises(FrozenInstanceError):
            value.foreign = []
    class ForeignList(list):
        def __iter__(self):
            raise AssertionError('foreign iterator was entered before type rejection')
    with pytest.raises(ValueError):
        replace(compact, targets=ForeignList(compact.targets))


def test_foreign_nested_scalar_aliases_are_rejected_before_reconstruction_can_copy_them(compact):
    class MutableText(str):
        pass
    class EqualObject:
        def __eq__(self, other): return True
        def __ne__(self, other): return False
    target = compact.targets[0]
    seed = compact.evidence[0]
    controls = (
        unchecked_replace(target, tick_nm=True),
        unchecked_replace(target, source=unchecked_replace(target.source, uri=MutableText(target.source.uri))),
        unchecked_replace(seed, query_key=unchecked_replace(seed.query_key,
                                                          identity=MutableText(seed.query_key.identity))),
    )
    for item in controls:
        table = 'targets' if type(item) is type(target) else 'evidence'
        values = getattr(compact, table)
        with pytest.raises(ValueError):
            replace(compact, **{table: (item,) + values[1:]})
    with pytest.raises(ValueError):
        replace(compact, schema_version=EqualObject())


@pytest.mark.parametrize('failure_type,suppress', ((RuntimeError, False), (ValueError, True),
                                                  (KeyboardInterrupt, False), (SystemExit, True)))
def test_compact_public_validation_preserves_original_exception_history(compact, monkeypatch, failure_type, suppress):
    failure = failure_type('unexpected compact reconstruction failure')
    cause, context = RuntimeError('existing cause'), LookupError('existing context')
    failure.__cause__, failure.__context__, failure.__suppress_context__ = cause, context, suppress
    def broken(*args, **kwargs):
        raise failure
    monkeypatch.setattr('layauto_v2.state.annotation.area', broken)
    with pytest.raises(failure_type) as raised:
        replace(compact)
    assert raised.value is failure
    assert failure.__cause__ is cause and failure.__context__ is context
    assert failure.__suppress_context__ is suppress


def test_each_neutral_public_record_has_canonical_roundtrip_and_stable_ref(compact):
    from layauto_v2.domain.net_annotation import AnnotationIssue
    from layauto_v2.domain.results import EvidenceIssue
    from layauto_v2.normalization.net_annotation_codec import decode_record, encode_record, record_digest
    seed, target, match = compact.evidence[0], compact.targets[0], compact.matches[0]
    located = AnnotationIssue(EvidenceIssue('unsupported', 'ProbeUnsupported', 'standalone neutral issue',
                                           target.source), (), (), (), (), 'warning')
    records = (compact.ref, compact.binding, seed, seed.net_id, seed.net_id.cell, seed.query_key,
               seed.rectangle, target, target.target_id, target.node, match,
               match.intersections[0], compact.fragments[0], compact.coverage[0],
               compact.components[0], compact.classifications[0], located, compact)
    for record in records:
        wire = encode_record(record)
        rebuilt = decode_record(wire)
        assert rebuilt == record and encode_record(rebuilt) == wire
        assert record_digest(rebuilt) == record_digest(record)


def test_neutral_wire_is_closed_versioned_and_requires_all_fields(compact):
    from layauto_v2.normalization.net_annotation_codec import decode_record, encode_record
    original = encode_record(compact.fragments[0])
    tree = mutable(decode(original))
    for key in tuple(tree['record']['fields']):
        changed = mutable(decode(original))
        del changed['record']['fields'][key]
        with pytest.raises(ValueError):
            decode_record(canonical_bytes(changed))
    changed = mutable(decode(original))
    changed['record']['fields']['foreign'] = {'scalar': True}
    with pytest.raises(ValueError):
        decode_record(canonical_bytes(changed))
    changed = mutable(decode(original))
    changed['foreign'] = 'ignored field is forbidden'
    with pytest.raises(ValueError):
        decode_record(canonical_bytes(changed))
    for wire in (original + b'\n', b'{}', canonical_bytes({'wire_schema': 'foreign/1', 'record': {}})):
        with pytest.raises(ValueError):
            decode_record(wire)


def test_neutral_digest_is_independent_of_process_hash_seed(compact):
    import layauto_v2
    from layauto_v2.normalization.net_annotation_codec import encode_record, record_digest
    wire = encode_record(compact)
    source = str(Path(layauto_v2.__file__).resolve().parent.parent)
    command = [sys.executable, '-B', '-c',
               'import sys; from layauto_v2.normalization.net_annotation_codec import decode_record, record_digest; '
               'print(record_digest(decode_record(sys.stdin.buffer.read())))']
    for seed in ('1', '731'):
        completed = subprocess.run(command, input=wire, capture_output=True,
                                   env=dict(os.environ, PYTHONPATH=source, PYTHONHASHSEED=seed,
                                            PYTHONDONTWRITEBYTECODE='1'), check=True)
        assert completed.stdout.decode().strip() == record_digest(compact)


def test_captured_result_roundtrip_carries_one_complete_unchanged_old_wire_value():
    from layauto_v2.domain.codec import FrozenMap
    from layauto_v2.normalization.local_connectivity_codec import encode_record as old_encode
    from layauto_v2.normalization.net_annotation_codec import decode_record, encode_record
    result, wire = normal_capture(), normal_wire()
    tree = decode(wire)
    assert set(tree) == {'wire_schema', 'captured_input_wire', 'record'}
    assert type(tree['captured_input_wire']) is FrozenMap
    assert canonical_bytes(tree['captured_input_wire']) == old_encode(result.input)
    rebuilt = decode_record(wire)
    assert rebuilt == result and rebuilt.completed == result.completed
    assert rebuilt.body_evidence == result.body_evidence
    assert encode_record(rebuilt) == wire


def test_captured_result_encode_reauthenticates_computed_outputs_and_native_input_graph():
    from layauto_v2.normalization.net_annotation import NetAnnotationResult
    from layauto_v2.normalization.net_annotation_codec import encode_record
    result = normal_capture()
    class MutableText(str):
        pass
    for changed in (unchecked_replace(result, status='error'),
                    unchecked_replace(result, value=None),
                    unchecked_replace(result, input=unchecked_replace(result.input,
                                                                      status=MutableText('success')))):
        with pytest.raises(ValueError):
            encode_record(changed)
    with pytest.raises(ValueError):
        NetAnnotationResult(result.input.input)


def test_captured_output_cannot_be_reused_with_another_valid_run_receipt():
    from layauto_v2.normalization.net_annotation_codec import encode_record
    direct = normal_capture()
    readback, _, ready, _, _ = readback_capture()
    assert readback.status == 'success' and readback.value.binding.capture_binding['readback']['run_id'] == ready.run_id
    assert direct.value.binding.capture_binding['readback'] is None
    with pytest.raises(ValueError):
        encode_record(unchecked_replace(direct, input=readback.input))


def test_captured_wire_rejects_ref_only_input_and_changed_complete_output():
    from layauto_v2.normalization.net_annotation_codec import decode_record
    original = normal_wire()
    tree = mutable(decode(original))
    tree['captured_input_wire'] = {'only_ref': normal_capture().value.binding.local_ref.sha256}
    with pytest.raises(ValueError):
        decode_record(canonical_bytes(tree))
    changed = mutable(decode(original))
    changed['record']['fields']['status'] = {'scalar': 'error'}
    with pytest.raises(ValueError):
        decode_record(canonical_bytes(changed))


@pytest.mark.parametrize('entry,failure_type,suppress', (
    ('builder', RuntimeError, False), ('constructor', ValueError, True),
    ('encoder', KeyboardInterrupt, False), ('decoder', SystemExit, True),
))
def test_captured_public_boundaries_preserve_original_exception_cause_context_and_suppression(
        monkeypatch, entry, failure_type, suppress):
    from layauto_v2.normalization import net_annotation as component
    from layauto_v2.normalization.net_annotation import NetAnnotationResult
    from layauto_v2.normalization.net_annotation_codec import decode_record, encode_record
    result, wire = normal_capture(), normal_wire()
    failure = failure_type('unexpected W013 semantic reconstruction failure')
    cause, context = RuntimeError('existing cause'), LookupError('existing context')
    failure.__cause__, failure.__context__, failure.__suppress_context__ = cause, context, suppress
    def broken(*args, **kwargs):
        raise failure
    monkeypatch.setattr(component, 'normalize', broken)
    with pytest.raises(failure_type) as raised:
        if entry == 'builder':
            component.build_net_annotation(result.input)
        elif entry == 'constructor':
            NetAnnotationResult(result.input)
        elif entry == 'encoder':
            encode_record(result)
        else:
            decode_record(wire)
    assert raised.value is failure
    assert failure.__cause__ is cause and failure.__context__ is context
    assert failure.__suppress_context__ is suppress


def _neutral_operator_control_and_forgery(change):
    """CR-01's tiny representation witness, with no captured result built.

    Symbolic content refs isolate contradictory retained operator owners. They
    claim neutral internal consistency only, never authenticity of a GDS record.
    """
    import hashlib
    from layauto_v2.domain.channel_identity import RationalRect
    from layauto_v2.domain.evidence import EvidenceRecord, SourceRef
    from layauto_v2.domain.geometry import GeometryRecordId, GeometryRef, Rect
    from layauto_v2.domain.identifiers import CellId
    from layauto_v2.domain.local_connectivity import ContactComponent, ContactNode, LocalRef
    from layauto_v2.domain.net_annotation import (
        AnnotationBinding, AnnotationFragment, AnnotationTargetId, LayerCoverage,
        NetComponentSummary, RecordClassification, TargetEvidence,
    )
    from layauto_v2.domain.regions import ExactRegion, RegionRef
    from layauto_v2.state.annotation import AnnotationDraft
    from w005_cases import read_json, sha
    def h(label):
        return hashlib.sha256(label.encode()).hexdigest()
    def owner(name):
        path = FIXTURE / 'tech' / (name + '.json')
        return EvidenceRecord(name, freeze_map(read_json(path)), (SourceRef('tech/' + name + '.json', sha(path)),))
    derived, drawn = owner('derived'), owner('drawn')
    count = 1 if change == 'node_component' else 2
    gds_hash = sha(FIXTURE / 'source.gds')
    sources = tuple(SourceRef('source.gds', gds_hash, record_index=i) for i in range(count))
    cdl = SourceRef('source.cdl', sha(FIXTURE / 'source.cdl'))
    unit = GeometryRef('unit', h('one-unit'))
    capture = freeze_map({'schema': 'layauto-net-capture-binding/1',
        'normalization_input_sha256': h('neutral-only-not-a-receipt'),
        'sources': tuple({'uri': row.uri, 'sha256': row.sha256}
                         for row in (sources[0], cdl, derived.sources[0], drawn.sources[0])),
        'readback': None})
    def leaves(altered):
        region_labels = ['one-effective-owner'] * count
        node_labels = ['one-contact-owner'] * count
        component_labels = ['one-contact-owner'] * count
        if altered and change == 'node_component':
            component_labels[0] = 'other-contact-owner'
        if altered and change == 'multiple_contacts':
            node_labels[1] = component_labels[1] = 'other-contact-owner'
        if altered and change == 'multiple_regions':
            region_labels[1] = 'other-effective-owner'
        regions = tuple(ExactRegion(GeometryRecordId(h('record-' + str(i))), 'effective', (), unit,
                    RegionRef('operators', h(region_labels[i])), (Rect(i * 20, 0, i * 20 + 10, 1),))
                        for i in range(count))
        nodes = tuple(ContactNode('LI', region, LocalRef('operators', h(node_labels[i])))
                      for i, region in enumerate(regions))
        components = tuple(sorted((ContactComponent((node.ref,), LocalRef('operators', h(component_labels[i])))
                                   for i, node in enumerate(nodes)), key=lambda row: row.ref.sha256))
        return regions, nodes, components
    good_regions, good_nodes, good_components = leaves(False)
    binding = AnnotationBinding(LocalRef('draft', h('one-local')), RegionRef('draft', h('one-effective')),
        GeometryRef('layout', h('one-layout')), unit, GeometryRef('base_partition', h('one-partition')),
        1, 'INV_M1_SYNTH', CellId('INV_M1_SYNTH'), h('semantic'), cdl, derived, drawn, good_components,
        tuple(sorted((region.owner_id for region in good_regions), key=lambda row: row.sha256)), (), capture)
    def tables(current_binding, nodes, components):
        by_node = {member: component for component in components for member in component.members}
        targets = tuple(sorted((TargetEvidence(
            AnnotationTargetId(current_binding.ref, node.layer, node.region.owner_id, node.region.ref), node,
            by_node[node.ref].ref, RationalRect(*(Fraction(v) for v in node.region.rectangles[0].bounds)), sources[i], 1)
            for i, node in enumerate(nodes)), key=lambda row: row.ref.sha256))
        fragments = tuple(sorted((AnnotationFragment(target.ref, target.rectangles, (), (), 'unknown')
                                  for target in targets), key=lambda row: row.ref.sha256))
        classifications = tuple(sorted((RecordClassification(target.target_id.record_id, 'LI', 'interconnect',
                'target_conductor', target.drawn_rectangle, target.source, ()) for target in targets),
                key=lambda row: row.record_id.sha256))
        source_refs = tuple(sorted(sources, key=lambda source: canonical_bytes(
            {'uri': source.uri, 'sha': source.sha256, 'record': source.record_index})))
        coverage = LayerCoverage('LI', count, 0, count, Fraction(count * 10), Fraction(0),
                                  Fraction(count * 10), Fraction(0), Fraction(0), source_refs, ())
        summaries = tuple(NetComponentSummary(component.ref, component.members,
                        tuple(target.ref for target in targets if target.component_ref == component.ref),
                        (), (), (), 'unknown') for component in components)
        return {'binding': current_binding, 'evidence': (), 'targets': targets, 'matches': (),
                'fragments': fragments, 'coverage': (coverage,), 'components': summaries,
                'classifications': classifications, 'issues': ()}
    good = AnnotationDraft(**tables(binding, good_nodes, good_components))
    _, bad_nodes, bad_components = leaves(True)
    bad_binding = unchecked_replace(binding, topology=bad_components)
    bad = unchecked_replace(good, **tables(bad_binding, bad_nodes, bad_components))
    return good, bad


@pytest.mark.parametrize('change', ('node_component', 'multiple_contacts', 'multiple_regions'))
def test_cr01_neutral_graph_requires_one_coherent_contact_and_region_operator_owner(change):
    from dataclasses import is_dataclass
    from layauto_v2.domain.codec import FrozenMap
    from layauto_v2.normalization.net_annotation_codec import WIRE_VERSION, decode_record, encode_record
    good, bad = _neutral_operator_control_and_forgery(change)
    assert decode_record(encode_record(good)) == good
    with pytest.raises(ValueError):
        replace(bad)
    with pytest.raises(ValueError):
        encode_record(bad)
    # Author a negative packet independently of the validating public encoder.
    # The public decoder must reject the same retained contradiction as the
    # public DTO constructor, even though every local wire tag is well formed.
    def packet_value(value):
        if type(value) is FrozenMap:
            return {'map': value}
        if type(value) is tuple:
            return {'tuple': tuple(packet_value(item) for item in value)}
        if is_dataclass(value):
            return {'record': type(value).__name__,
                    'fields': {field.name: packet_value(getattr(value, field.name)) for field in fields(value)}}
        return {'scalar': value}
    wire = canonical_bytes({'wire_schema': WIRE_VERSION, 'record': packet_value(bad)})
    with pytest.raises(ValueError):
        decode_record(wire)


def _cr02_forged_frozen_map(shape):
    """Create an exact FrozenMap shell whose private representation is unsafe."""
    from layauto_v2.domain.codec import FrozenMap
    value = object.__new__(FrozenMap)
    if shape == 'list_backing':
        storage = [('supported', False), ('reason', 'unknown_policy')]
    elif shape == 'list_entry':
        storage = (['supported', False], ('reason', 'unknown_policy'))
    elif shape == 'nested_tuple':
        nested, _ = _cr02_forged_frozen_map('list_backing')
        storage = (('supported', False), ('nested', (nested,)))
    elif shape == 'duplicate_key':
        storage = (('supported', False), ('supported', True))
    else:
        assert shape == 'cycle'
        storage = (('self', value),)
    object.__setattr__(value, '_entries', storage)
    return value, storage


@pytest.mark.parametrize('shape', ('list_backing', 'list_entry', 'nested_tuple', 'duplicate_key', 'cycle'))
def test_cr02_new_dto_constructor_and_codec_reject_unsafe_exact_frozen_map_shells(shape):
    from layauto_v2.domain.codec import FrozenMap
    from layauto_v2.domain.net_annotation import AnnotationRef, MatchEvidence
    from layauto_v2.normalization.net_annotation_codec import encode_record
    unsafe, backing = _cr02_forged_frozen_map(shape)
    assert type(unsafe) is FrozenMap  # exact class alone does not prove immutability
    good = MatchEvidence(AnnotationRef('evidence', '1' * 64), (), (), (), (),
                         FrozenMap({'supported': False, 'reason': 'unknown_policy'}), 'unsupported')
    stable_ref = good.ref
    with pytest.raises(ValueError):
        replace(good, policy=unsafe)
    with pytest.raises(ValueError):
        encode_record(unchecked_replace(good, policy=unsafe))
    if shape == 'list_backing':
        backing.append(('external_mutation', True))
    assert good.ref == stable_ref and good.policy.get('external_mutation') is None


def test_cr02_captured_input_rejects_mutable_map_backing_before_old_codec_can_copy_it(monkeypatch):
    from layauto_v2.domain.codec import FrozenMap
    from layauto_v2.normalization import local_connectivity_codec
    from layauto_v2.normalization.net_annotation import NetAnnotationResult, build_net_annotation
    from layauto_v2.normalization.net_annotation_codec import encode_record
    result = normal_capture()
    local = result.input
    original_owner = local.value.binding.drawn
    backing = list(original_owner.payload.items())
    unsafe = object.__new__(FrozenMap)
    object.__setattr__(unsafe, '_entries', backing)
    owner = unchecked_replace(original_owner, payload=unsafe)
    graph = unchecked_replace(local.value, binding=unchecked_replace(local.value.binding, drawn=owner))
    borrowed = unchecked_replace(local, value=graph)
    forged_result = unchecked_replace(result, input=borrowed)
    def copied_before_validation(*args, **kwargs):
        pytest.fail('old codec was entered before malformed FrozenMap backing was rejected')
    monkeypatch.setattr(local_connectivity_codec, 'encode_record', copied_before_validation)
    for entry in (lambda: build_net_annotation(borrowed), lambda: NetAnnotationResult(borrowed),
                  lambda: encode_record(forged_result)):
        with pytest.raises(ValueError):
            entry()
    backing.append(('external_mutation', True))
    assert original_owner.payload.get('external_mutation') is None
    assert result.input is local and result.input.value.binding.drawn is original_owner
