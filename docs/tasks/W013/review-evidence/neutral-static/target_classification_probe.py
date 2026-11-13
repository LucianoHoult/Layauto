"""Pure neutral target-versus-retained-drawn-role consistency witness."""
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
from layauto_v2.tech.schema import validate_payload


def h(value):
    return hashlib.sha256(value.encode()).hexdigest()


def make_case(role, classification):
    fixture = Path.cwd() / 'tests/fixtures/w003_m1'
    def owner(name):
        doc = json.loads((fixture / ('tech/' + name + '.json')).read_text())
        if name == 'drawn':
            row = next(row for row in doc['layers'] if row['name'] == 'M1')
            row['role'] = role
        payload = freeze_map(doc)
        validate_payload(payload, name)
        # Actual bytes for this synthetic neutral owner are declared here; this
        # is not the unchanged accepted fixture owner/source pair.
        raw = (json.dumps(doc, sort_keys=True) + '\n').encode()
        return EvidenceRecord(name, payload, (SourceRef('review/' + name + '.json', hashlib.sha256(raw).hexdigest()),))
    derived, drawn = owner('derived'), owner('drawn')
    source = SourceRef('review/source.gds', h('neutral geometry'), record_index=0)
    cdl = SourceRef('review/source.cdl', h('neutral source CDL'))
    region = ExactRegion(GeometryRecordId(h('record')), 'effective', (),
                         GeometryRef('unit', h('unit')), RegionRef('operators', h('region-operators')),
                         (Rect(0, 0, 10, 1),))
    node = ContactNode('M1', region, LocalRef('operators', h('one-contact-owner')))
    component = ContactComponent((node.ref,), node.binding_ref)
    capture = freeze_map({'schema': 'layauto-net-capture-binding/1',
                          'normalization_input_sha256': h('neutral-only-not-a-receipt'),
                          'sources': tuple({'uri': s.uri, 'sha256': s.sha256} for s in
                                           (source, cdl, derived.sources[0], drawn.sources[0])), 'readback': None})
    binding = AnnotationBinding(LocalRef('draft', h('local')), RegionRef('draft', h('effective')),
        GeometryRef('layout', h('layout')), region.unit_ref, GeometryRef('base_partition', h('partition')),
        1, 'INV_M1_SYNTH', CellId('INV_M1_SYNTH'), h('semantic'), cdl, derived, drawn,
        (component,), (region.owner_id,), (), capture)
    target = TargetEvidence(AnnotationTargetId(binding.ref, 'M1', region.owner_id, region.ref), node,
                            component.ref, RationalRect(Fraction(0), Fraction(0), Fraction(10), Fraction(1)), source, 1)
    fragment = AnnotationFragment(target.ref, target.rectangles, (), (), 'unknown')
    record = RecordClassification(region.owner_id, 'M1', role, classification, target.drawn_rectangle, source, ())
    coverage = LayerCoverage('M1', 1, 0, 1, Fraction(10), Fraction(0), Fraction(10), Fraction(0), Fraction(0), (source,), ())
    summary = NetComponentSummary(component.ref, component.members, (target.ref,), (), (), (), 'unknown')
    draft = AnnotationDraft(binding, (), (target,), (), (fragment,), (coverage,), (summary,), (record,), ())
    wire = encode_record(draft)
    assert decode_record(wire) == draft
    return {'declared_drawn_role': role, 'classification': classification,
            'retained_node_layer': node.layer, 'retained_target_count': len(draft.targets),
            'coverage_denominator_area_nm2': str(draft.coverage[0].total_area),
            'public_draft_constructed': True, 'public_codec_roundtrip_accepted': True,
            'drawn_owner_schema_validated': True, 'wire_sha256': hashlib.sha256(wire).hexdigest()}


def main():
    result = {'classification': 'pure-neutral-target-role-consistency-not-captured-validation',
              'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(), 'python': sys.version,
              'cases': [make_case('marker', 'marker'), make_case('contact', 'connector')],
              'limitations': 'No original fixture bytes or product source were changed. Pure synthetic owner/target DTOs do not claim capture authority.'}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
