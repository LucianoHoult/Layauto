"""Pure neutral same-graph owner-coherence witnesses; no captured build."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from fractions import Fraction

from layauto_v2.domain.channel_identity import RationalRect
from layauto_v2.domain.codec import canonical_bytes, freeze_map
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


def h(value):
    return hashlib.sha256(value.encode()).hexdigest()


def build_case(component_labels, region_labels):
    fixture = Path.cwd() / 'tests/fixtures/w003_m1'
    def owner(name):
        path = fixture / ('tech/' + name + '.json')
        source = SourceRef('tech/' + name + '.json', hashlib.sha256(path.read_bytes()).hexdigest())
        return EvidenceRecord(name, freeze_map(json.loads(path.read_text())), (source,))
    derived, drawn = owner('derived'), owner('drawn')
    gds_hash = hashlib.sha256((fixture / 'source.gds').read_bytes()).hexdigest()
    sources = tuple(SourceRef('source.gds', gds_hash, record_index=i) for i in range(2))
    cdl = SourceRef('source.cdl', hashlib.sha256((fixture / 'source.cdl').read_bytes()).hexdigest())
    unit = GeometryRef('unit', h('one-unit'))
    regions = tuple(ExactRegion(GeometryRecordId(h('record-' + str(i))), 'effective', (), unit,
                    RegionRef('operators', h(region_labels[i])), (Rect(i * 20, 0, i * 20 + 10, 1),)) for i in range(2))
    nodes = tuple(ContactNode('LI', region, LocalRef('operators', h(component_labels[i]))) for i, region in enumerate(regions))
    components = tuple(sorted((ContactComponent((node.ref,), node.binding_ref) for node in nodes), key=lambda item: item.ref.sha256))
    capture = freeze_map({'schema': 'layauto-net-capture-binding/1',
        'normalization_input_sha256': h('neutral-only-not-a-receipt'),
        'sources': tuple({'uri': s.uri, 'sha256': s.sha256} for s in (sources[0], cdl, derived.sources[0], drawn.sources[0])),
        'readback': None})
    binding = AnnotationBinding(LocalRef('draft', h('one-local')), RegionRef('draft', h('one-effective')),
        GeometryRef('layout', h('one-layout')), unit, GeometryRef('base_partition', h('one-partition')),
        1, 'INV_M1_SYNTH', CellId('INV_M1_SYNTH'), h('semantic'), cdl, derived, drawn, components,
        tuple(sorted((region.owner_id for region in regions), key=lambda item: item.sha256)), (), capture)
    component_by_node = {component.members[0]: component for component in components}
    targets = tuple(sorted((TargetEvidence(AnnotationTargetId(binding.ref, node.layer, node.region.owner_id, node.region.ref), node,
                  component_by_node[node.ref].ref, RationalRect(*(Fraction(v) for v in node.region.rectangles[0].bounds)), sources[i], 1)
                  for i, node in enumerate(nodes)), key=lambda item: item.ref.sha256))
    fragments = tuple(sorted((AnnotationFragment(target.ref, target.rectangles, (), (), 'unknown') for target in targets), key=lambda item: item.ref.sha256))
    classifications = tuple(sorted((RecordClassification(target.target_id.record_id, 'LI', 'interconnect', 'target_conductor',
            target.drawn_rectangle, target.source, ()) for target in targets), key=lambda item: item.record_id.sha256))
    source_refs = tuple(sorted(sources, key=lambda source: canonical_bytes({'uri': source.uri, 'sha': source.sha256, 'record': source.record_index})))
    coverage = LayerCoverage('LI', 2, 0, 2, Fraction(20), Fraction(0), Fraction(20), Fraction(0), Fraction(0), source_refs, ())
    summaries = tuple(NetComponentSummary(component.ref, component.members,
                    tuple(target.ref for target in targets if target.component_ref == component.ref), (), (), (), 'unknown') for component in components)
    draft = AnnotationDraft(binding, (), targets, (), fragments, (coverage,), summaries, classifications, ())
    wire = encode_record(draft)
    assert decode_record(wire) == draft
    return {'public_draft_constructed': True, 'public_codec_roundtrip_accepted': True,
        'node_component_pairs_match': all(node.binding_ref == component_by_node[node.ref].binding_ref for node in nodes),
        'local_operator_refs': sorted({node.binding_ref.sha256 for node in nodes}),
        'region_operator_refs': sorted({node.region.operator_ref.sha256 for node in nodes}),
        'wire_bytes': len(wire), 'wire_sha256': hashlib.sha256(wire).hexdigest()}


def main():
    result = {'classification': 'pure-neutral-owner-coherence-not-captured-validation',
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(), 'python': sys.version,
        'mixed_region_operators': build_case(('one-contact-owner', 'one-contact-owner'), ('effective-owner-A', 'effective-owner-B')),
        'mixed_local_operators': build_case(('local-owner-A', 'local-owner-B'), ('one-effective-owner', 'one-effective-owner')),
        'limitations': 'Pure neutral synthetic values with typed refs only; no source authenticity or complete W010/W013 result is claimed.'}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
