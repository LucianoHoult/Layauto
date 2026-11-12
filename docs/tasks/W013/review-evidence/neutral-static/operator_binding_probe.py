"""Pure neutral internal-consistency probe; no captured component is built.

Known fake content refs below isolate a contradictory retained node/component
operator binding, rather than claim source authentication from a neutral DTO.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from fractions import Fraction

from layauto_v2.domain.channel_identity import RationalRect
from layauto_v2.domain.codec import freeze_map
from layauto_v2.domain.evidence import EvidenceRecord, SourceRef
from layauto_v2.domain.geometry import GeometryRecordId, GeometryRef, Rect
from layauto_v2.domain.identifiers import CellId
from layauto_v2.domain.local_connectivity import ContactComponent, ContactNode, LocalRef
from layauto_v2.domain.net_annotation import (
    AnnotationBinding, AnnotationFragment, AnnotationTargetId, LayerCoverage,
    NetComponentSummary, RecordClassification, TargetEvidence,
)
from layauto_v2.domain.regions import ExactRegion, RegionRef
from layauto_v2.normalization.net_annotation_codec import encode_record, decode_record
from layauto_v2.state.annotation import AnnotationDraft


def hash_text(value):
    return hashlib.sha256(value.encode()).hexdigest()


def main():
    root = Path.cwd()
    fixture = root / 'tests/fixtures/w003_m1'
    def owner(name):
        path = fixture / ('tech/' + name + '.json')
        source = SourceRef('tech/' + name + '.json', hashlib.sha256(path.read_bytes()).hexdigest())
        return EvidenceRecord(name, freeze_map(json.loads(path.read_text())), (source,))
    derived, drawn = owner('derived'), owner('drawn')
    source = SourceRef('source.gds', hashlib.sha256((fixture / 'source.gds').read_bytes()).hexdigest(), record_index=0)
    cdl = SourceRef('source.cdl', hashlib.sha256((fixture / 'source.cdl').read_bytes()).hexdigest())
    region = ExactRegion(GeometryRecordId(hash_text('record')), 'effective', (),
                         GeometryRef('unit', hash_text('unit')), RegionRef('operators', hash_text('region-operators')),
                         (Rect(0, 0, 10, 1),))
    node = ContactNode('LI', region, LocalRef('operators', hash_text('node-operators-A')))
    # The contradictory retained fact: a component says its operator owner is B,
    # while its sole member node says owner A. No hash preimage is forged.
    component = ContactComponent((node.ref,), LocalRef('operators', hash_text('component-operators-B')))
    capture = freeze_map({'schema': 'layauto-net-capture-binding/1',
                          'normalization_input_sha256': hash_text('neutral-only-not-a-receipt'),
                          'sources': tuple({'uri': s.uri, 'sha256': s.sha256} for s in
                                           (source, cdl, derived.sources[0], drawn.sources[0])),
                          'readback': None})
    binding = AnnotationBinding(LocalRef('draft', hash_text('local')), RegionRef('draft', hash_text('effective')),
        GeometryRef('layout', hash_text('layout')), region.unit_ref, GeometryRef('base_partition', hash_text('partition')),
        1, 'INV_M1_SYNTH', CellId('INV_M1_SYNTH'), hash_text('semantic'), cdl, derived, drawn,
        (component,), (region.owner_id,), (), capture)
    target = TargetEvidence(AnnotationTargetId(binding.ref, node.layer, region.owner_id, region.ref),
                            node, component.ref, RationalRect(Fraction(0), Fraction(0), Fraction(10), Fraction(1)), source, 1)
    fragment = AnnotationFragment(target.ref, target.rectangles, (), (), 'unknown')
    classification = RecordClassification(region.owner_id, 'LI', 'interconnect', 'target_conductor',
                                           target.drawn_rectangle, source, ())
    coverage = LayerCoverage('LI', 1, 0, 1, Fraction(10), Fraction(0), Fraction(10), Fraction(0), Fraction(0), (source,), ())
    summary = NetComponentSummary(component.ref, component.members, (target.ref,), (), (), (), 'unknown')
    draft = AnnotationDraft(binding, (), (target,), (), (fragment,), (coverage,), (summary,), (classification,), ())
    wire = encode_record(draft)
    restored = decode_record(wire)
    assert restored == draft
    result = {'classification': 'pure-neutral-operator-consistency-probe-not-captured-product',
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(), 'python': sys.version,
        'node_operator_binding': node.binding_ref.sha256, 'component_operator_binding': component.binding_ref.sha256,
        'operator_bindings_equal': node.binding_ref == component.binding_ref,
        'public_draft_constructed': True, 'public_codec_roundtrip_accepted': True,
        'wire_sha256': hashlib.sha256(wire).hexdigest(), 'wire_bytes': len(wire),
        'limits': 'Full-capture NetAnnotationResult was not built; fake neutral content refs do not claim any capture authority.'}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
