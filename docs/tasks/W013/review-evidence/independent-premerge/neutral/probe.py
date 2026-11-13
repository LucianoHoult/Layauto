"""Independent bounded W013 neutral/codec checks; no captured build or test helper."""
from __future__ import annotations

import ast
from dataclasses import fields, replace
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

from layauto_v2.domain.codec import FrozenMap, canonical_bytes, decode, freeze_map
from layauto_v2.domain.channel_identity import RationalRect
from layauto_v2.domain.evidence import EvidenceRecord, SourceRef
from layauto_v2.domain.geometry import GeometryRecordId, GeometryRef, Rect
from layauto_v2.domain.identifiers import CellId
from layauto_v2.domain.local_connectivity import ContactComponent, ContactNode, LocalRef
from layauto_v2.domain.net_annotation import (
    AnnotationBinding, AnnotationFragment, AnnotationRef, AnnotationTargetId,
    LayerCoverage, MatchEvidence, NetComponentSummary, RecordClassification,
    TargetEvidence, validate_annotation_graph,
)
from layauto_v2.domain.regions import ExactRegion, RegionRef
from layauto_v2.normalization.net_annotation_codec import encode_record, decode_record
from layauto_v2.state.annotation import AnnotationDraft


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def h(label):
    return sha(label.encode())


def forged(record, **changes):
    result = object.__new__(type(record))
    for field in fields(record):
        object.__setattr__(result, field.name, changes.get(field.name, getattr(record, field.name)))
    return result


def badmap(entries):
    result = object.__new__(FrozenMap)
    object.__setattr__(result, '_entries', entries)
    return result


def control():
    fixture = Path('tests/fixtures/w003_m1')
    owners = []
    for name in ('derived', 'drawn'):
        path = fixture / 'tech' / (name + '.json')
        raw = path.read_bytes()
        owners.append(EvidenceRecord(name, freeze_map(json.loads(raw)), (SourceRef('neutral/' + name, sha(raw)),)))
    derived, drawn = owners
    source = SourceRef('neutral/gds', h('one original M1'), record_index=0)
    cdl = SourceRef('neutral/cdl', h('source netlist'))
    unit = GeometryRef('unit', h('unit'))
    region = ExactRegion(GeometryRecordId(h('M1 record')), 'effective', (), unit,
                         RegionRef('operators', h('effective owner')), (Rect(-3, 1, 7, 3),))
    node = ContactNode('M1', region, LocalRef('operators', h('local owner')))
    component = ContactComponent((node.ref,), node.binding_ref)
    capture = freeze_map({'schema': 'layauto-net-capture-binding/1',
        'normalization_input_sha256': h('symbolic neutral input'),
        'sources': tuple({'uri': row.uri, 'sha256': row.sha256}
                         for row in (source, cdl, derived.sources[0], drawn.sources[0])), 'readback': None})
    binding = AnnotationBinding(LocalRef('draft', h('local')), RegionRef('draft', h('effective')),
        GeometryRef('layout', h('geometry')), unit, GeometryRef('base_partition', h('partition')),
        1, 'INV_M1_SYNTH', CellId('INV_M1_SYNTH'), h('source semantics'), cdl, derived, drawn,
        (component,), (region.owner_id,), (), capture)
    rectangle = RationalRect(*(Fraction(v) for v in (-3, 1, 7, 3)))
    target = TargetEvidence(AnnotationTargetId(binding.ref, 'M1', region.owner_id, region.ref),
                            node, component.ref, rectangle, source, 1)
    return AnnotationDraft(binding, (), (target,), (),
        (AnnotationFragment(target.ref, (rectangle,), (), (), 'unknown'),),
        (LayerCoverage('M1', 1, 1, 1, Fraction(20), Fraction(0), Fraction(20),
                       Fraction(0), Fraction(0), (source,), ()),),
        (NetComponentSummary(component.ref, component.members, (target.ref,), (), (), (), 'unknown'),),
        (RecordClassification(region.owner_id, 'M1', 'interconnect', 'target_conductor', rectangle, source, ((0, 0),)),), ())


def main():
    watched = [Path(p) for p in subprocess.check_output(['git', 'ls-files', 'layauto_v2', 'pyproject.toml', 'tests/contracts/test_w007_contracts.py'], text=True).splitlines()]
    before = {str(p): sha(p.read_bytes()) for p in watched}
    rows = []

    def rejected(label, call):
        try:
            call()
        except ValueError as exc:
            rows.append({'case': label, 'outcome': 'ValueError', 'message': str(exc)})
        else:
            raise AssertionError('accepted: ' + label)

    draft = control()
    wire = encode_record(draft)
    assert decode_record(wire) == draft
    # A shared immutable DAG is accepted; the same object must still be rejected
    # if it reappears under a FrozenMap value-only context containing a DTO.
    shared = (AnnotationRef('target', h('shared')),)
    validate_annotation_graph((shared, shared), (AnnotationRef,))
    rejected('same DAG under map value-only context', lambda: validate_annotation_graph(
        (shared, badmap((('child', shared),))), (AnnotationRef,)))
    for label, bad in (
        ('derived owner nested list backing', forged(draft.binding.derived,
            payload=badmap((('layer', badmap([('x', 1)])),)))),
        ('binding boolean DBU', forged(draft.binding, tick_nm=True)),
        ('binding source URI changed', forged(draft.binding, source_ref=SourceRef('neutral/foreign', h('foreign')))),
    ):
        rejected(label, lambda bad=bad: encode_record(forged(draft, binding=bad)))
    class Text(str):
        pass
    class Number(int):
        pass
    for label, leaf in (('text subclass', Text('x')), ('integer subclass', Number(1)), ('float', 0.5)):
        rejected(label, lambda leaf=leaf: MatchEvidence(AnnotationRef('evidence', h('e')), (), (), (), (), badmap((('x', leaf),)), 'unsupported'))
    malformed = Fraction(1, 2)
    object.__setattr__(malformed, '_numerator', True)
    rejected('Fraction boolean numerator', lambda: validate_annotation_graph(malformed))
    old_region = draft.targets[0].node.region
    alternate = replace(old_region, operator_ref=RegionRef('operators', h('alternate owner')))
    new_node = replace(draft.targets[0].node, region=alternate)
    rejected('target region ID changes with geometry operator', lambda: replace(draft.targets[0], node=new_node))
    rejected('classification nonconductor with original target', lambda: replace(draft,
        classifications=(replace(draft.classifications[0], classification='marker'),)))
    rejected('extra neutral wire envelope field', lambda: decode_record(canonical_bytes(
        FrozenMap({**dict(decode(wire)), 'unexpected': 1}))))
    packet = decode(wire)
    tag = packet['record']
    broken_fields = FrozenMap({**dict(tag['fields']), 'extra': FrozenMap({'scalar': 1})})
    rejected('extra neutral record field', lambda: decode_record(canonical_bytes({'wire_schema': packet['wire_schema'],
        'record': {'record': tag['record'], 'fields': broken_fields}})))
    for suppress in (False, True):
        cause, context, marker = LookupError('cause'), OSError('context'), RuntimeError('marker')
        marker.__cause__, marker.__context__, marker.__suppress_context__ = cause, context, suppress
        for label, call in (('constructor', lambda: replace(draft)), ('encoder', lambda: encode_record(draft)),
                            ('decoder', lambda: decode_record(wire))):
            with patch('layauto_v2.state.annotation.validate_members', side_effect=marker):
                try:
                    call()
                except RuntimeError as raised:
                    assert raised is marker
                    assert raised.__cause__ is cause and raised.__context__ is context
                    assert raised.__suppress_context__ is suppress
                else:
                    raise AssertionError('unexpected failure did not propagate')
            rows.append({'case': f'exception identity/{label}/suppress={suppress}', 'outcome': 'preserved'})
    tree = ast.parse(Path('tests/contracts/test_w007_contracts.py').read_text())
    expression = next(n.value for n in ast.walk(tree) if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == 'allowed_net_annotation_state' for t in n.targets))
    permits = []
    for filename in ('net_annotation.py', 'net_annotation_codec.py', 'other.py'):
        for module in ('layauto_v2.state.annotation', 'layauto_v2.state.publication'):
            for symbols in (('AnnotationDraft',), ('AnnotationDraft', 'MutableState'), ('MutableState',)):
                node = ast.ImportFrom(module=module, names=[ast.alias(name=s) for s in symbols], level=0)
                result = eval(compile(ast.Expression(expression), '<guard>', 'eval'), {'ast': ast},
                    {'path': Path('normalization') / filename, 'node': node})
                if result:
                    permits.append((filename, module, symbols))
    assert permits == [(f, 'layauto_v2.state.annotation', ('AnnotationDraft',))
                       for f in ('net_annotation.py', 'net_annotation_codec.py')]
    assert before == {str(p): sha(p.read_bytes()) for p in watched}
    print(json.dumps({'classification': 'new independent bounded neutral/codec probe',
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'python': sys.version, 'control_roundtrip': True, 'shared_immutable_DAG': True,
        'guard_only_two_exact_readonly_imports': permits,
        'checked_runtime_and_guard_files': len(before), 'source_stable': True,
        'checks': rows, 'not_run': ['captured construction/roundtrip', 'full matrix', 'resource timing']}, indent=2))


if __name__ == '__main__':
    main()
