"""Finite W009 performance witnesses; no production-size admission claim.

Run one case per command, for example:
  python docs/tasks/W009/verification/performance.py --case pure --output /tmp/performance.json

The normal case uses actual W005/W008 captures. Stress drafts append integer
BOUNDARY bytes in memory to that GDS, reparse them, and construct neutral base
geometry. They deliberately make no query/body or capture-receipt admission
claim for the added shapes. No fixture, answer, or test helper is changed/read.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import platform
import struct
import sys
from time import perf_counter

from layauto_v2.domain.evidence import EvidenceRecord, SourceFile
from layauto_v2.domain.geometry import Rect, mapping
from layauto_v2.domain.regions import ExactRegion
from layauto_v2.importers import read_inputs
from layauto_v2.importers.gds import parse_gds
from layauto_v2.normalization import build_geometry, geometry_from_parse_result
from layauto_v2.normalization.effective import build_effective_geometry
from layauto_v2.state.coordinate import build_partition
from layauto_v2.state.layout_store import build_layout
from layauto_v2.state.occupancy import build_occupancy
from layauto_v2.state.regions import build_effective_draft, slab_difference

ROOT = Path(__file__).resolve().parents[4]
PRODUCT = ('layauto_v2/domain/regions.py', 'layauto_v2/state/regions.py',
           'layauto_v2/normalization/effective.py')


def pattern(kind: str, count: int):
    """Hand-selected integer arrangements, never an implementation oracle."""
    extent = 4 * count + 2
    target = Rect(1000, 1000, 1000 + extent, 1000 + extent)
    if kind == 'strips':
        cuts = tuple(Rect(1002 + 4 * i, 1000, 1003 + 4 * i, target.y1) for i in range(count))
    elif kind == 'crosscuts':
        vertical = count // 2
        horizontal = count - vertical
        cuts = (tuple(Rect(1002 + 4 * i, 1000, 1003 + 4 * i, target.y1) for i in range(vertical))
                + tuple(Rect(1000, 1002 + 4 * i, target.x1, 1003 + 4 * i) for i in range(horizontal)))
    elif kind == 'holes':
        cuts = tuple(Rect(1002 + 4 * i, 1002, 1003 + 4 * i, 1003) for i in range(count))
    elif kind == 'overlap':
        # Repeated and nested CUTs leave the same single hole coverage.
        cuts = tuple(Rect(1002, 1002, 1010 + i % 3, 1010 + i % 3) for i in range(count))
    else:
        raise ValueError(kind)
    return target, cuts


def measured(call):
    start = perf_counter()
    result = call()
    return result, perf_counter() - start


def pure_cases():
    rows = []
    for kind in ('strips', 'crosscuts', 'holes', 'overlap'):
        for count in (10, 50, 100, 200):
            target, cuts = pattern(kind, count)
            pieces, elapsed = measured(lambda: slab_difference(target, cuts))
            if kind == 'strips':
                expected = (count + 1, count + 1)
            elif kind == 'crosscuts':
                groups = (count // 2 + 1) * (count - count // 2 + 1)
                expected = (groups, groups)
            elif kind == 'holes':
                # m full-height gap slabs plus the last gap, and two pieces
                # above/below each of the m isolated holes.
                expected = (3 * count + 1, 1)
            else:
                expected = (4, 1)
            assert len(pieces) == expected[0], (kind, count, len(pieces), expected)
            rows.append({'case': kind, 'cut_count_m': count, 'output_rectangles_p': len(pieces),
                         'hand_expected_local_regions': expected[1],
                         'difference_seconds': elapsed, 'target_bounds': target.bounds})
    return rows


def boundary(layer: int, rect: Rect):
    def record(kind, dtype, payload=b''):
        return struct.pack('>HBB', len(payload) + 4, kind, dtype) + payload
    xy = (rect.x0, rect.y0, rect.x0, rect.y1, rect.x1, rect.y1,
          rect.x1, rect.y0, rect.x0, rect.y0)
    return (record(8, 0) + record(13, 2, struct.pack('>h', layer))
            + record(14, 2, struct.pack('>h', 0))
            + record(16, 3, struct.pack('>10i', *xy)) + record(17, 0))


def draft_case(name: str):
    site = ROOT / 'tests/fixtures/w003_m1/site_config.yaml'
    parsed, capture_seconds = measured(lambda: read_inputs(site))
    assert parsed.status == 'success'
    geometry, geometry_seconds = measured(lambda: build_geometry(geometry_from_parse_result(parsed)))
    assert geometry.status == 'success' and geometry.value is not None
    assert parsed.value is not None
    tech = mapping(parsed.value['tech'])
    owner = next(record for record in parsed.completed if record.kind == 'tech')
    physical = EvidenceRecord('physical', mapping(tech['physical']), (owner.sources[3],))
    base = geometry.value
    base_seconds = 0.0
    if name == 'normal':
        cuts = ()
        target = None
    else:
        kind, token = name.split('-')
        target, cuts = pattern(kind, int(token))
        raw = base.layout.gds.payload['raw_document']
        assert type(raw) is bytes and raw[-8:] == bytes.fromhex('0004070000040400')
        # Layer numbers come from the selected drawn declarations.
        li_layer = base.layout.policy('LI').declaration['stream_key']['layer']
        cut_layer = base.layout.policy('CUT').declaration['stream_key']['layer']
        stream = raw[:-8] + boundary(li_layer, target) + b''.join(boundary(cut_layer, cut) for cut in cuts) + raw[-8:]
        source = SourceFile('w009-performance-' + name + '.gds', stream)
        gds = EvidenceRecord('gds', parse_gds(source, tech), (source.ref(),))
        base, base_seconds = measured(lambda: build_occupancy(build_partition(build_layout(
            gds, geometry.value.layout.drawn, geometry.value.layout.formats))))
    draft, build_seconds = measured(lambda: build_effective_draft(base, physical))
    rebuilt, reconstruction_seconds = measured(lambda: replace(draft))
    assert rebuilt == draft
    public_build_seconds = None
    if name == 'normal':
        public, public_build_seconds = measured(lambda: build_effective_geometry(geometry))
        assert public.status == 'success' and public.value == draft
    selected = tuple(row for row in draft.records if target is None or base.layout.record(row.record_id).rect == target)
    pieces = tuple(rect for row in selected for region in row.regions for rect in region.rectangles)
    selected_regions = tuple(region for row in selected for region in row.regions)
    # This also includes public ExactRegion overlap, canonical-cover and
    # positive-length-edge connectedness checks on an already known region.
    region_rebuild_seconds = None
    if selected_regions:
        _, region_rebuild_seconds = measured(lambda: ExactRegion(
            **{field: getattr(selected_regions[0], field) for field in (
                'owner_id', 'role', 'contributors', 'unit_ref', 'operator_ref', 'rectangles', 'schema_version')}))
    return {'case': name, 'classification': 'actual_capture' if name == 'normal' else 'neutral_in_memory_stream_stress',
            'cut_count_m': len(cuts), 'selected_record_count': len(selected),
            'output_rectangles_p': len(pieces), 'local_region_count': len(selected_regions),
            'all_drawn_records': len(base.layout.records), 'raw_base_fragments': len(base.fragments),
            'w005_capture_seconds': capture_seconds, 'w008_geometry_seconds': geometry_seconds,
            'stress_base_preparation_seconds': base_seconds,
            'effective_build_seconds': build_seconds, 'draft_constructor_rebuild_seconds': reconstruction_seconds,
            'public_capture_bound_build_seconds': public_build_seconds,
            'one_region_constructor_rebuild_seconds': region_rebuild_seconds}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', required=True, choices=('pure', 'normal', 'strips-10', 'strips-50', 'strips-100',
                                                        'crosscuts-10', 'crosscuts-20', 'holes-10', 'holes-25', 'overlap-100'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    start = perf_counter()
    results = pure_cases() if args.case == 'pure' else [draft_case(args.case)]
    output = json.loads(args.output.read_text()) if args.output.exists() else {}
    output.update({'schema': 'layauto-w009-finite-performance/1', 'python': sys.version,
                   'interpreter': sys.executable, 'platform': platform.platform(),
                   'source_sha256': {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in PRODUCT},
                   'scope': 'finite synthetic witnesses, no new external limit or all-scale/production performance guarantee',
                   'complexity': {
                       'difference': 'm relevant CUTs: O(m) x slabs, O(m log m) interval work each, O(m²) possible output pieces',
                       'local_grouping': 'p pieces: O(p²) positive-length-edge comparisons in the worst case',
                       'region_validation': 'for each region with q pieces: pairwise overlap O(q²), canonical_cover O(q² log q) upper bound, connectedness O(q²)',
                       'aggregate': 'build materializes record results, EffectiveDraft constructor independently materializes them again; repeated constructors and decode repeat validation, with no memoization',
                       'strict_object_graph': 'validate_closed_graph traverses original retained Values and explicitly permitted DTO fields before any codec copying: a linear visit of retained value/field occurrences with a fixed known-type set, plus container access overhead; Fraction numerator and denominator must be native int. Shared retained objects may be visited again because there is no graph memoization. Owner, state base, public input, completed facts and issues each repeat the relevant traversal at their own validation boundary',
                       'retained_value_validation': 'each state _records materialization canonical-encodes the complete retained BaseOccupancy.to_value() chain to reject legacy equal-valued mutable literal objects; base/layout/partition refs recursively encode their retained values, adding work proportional to serialized retained geometry/evidence and allocation cost',
                       'public_input_validation': 'public build_effective_geometry first checks the strict original GeometryResult object graph and canonical wire encoding in _require_input; EffectiveGeometryResult constructor repeats input validation and checks completed facts/issues again. Capture size, retained parsed facts, strict graph traversal, wire serialization and allocation are therefore included in public_capture_bound_build_seconds, separately from neutral effective_build_seconds',
                       'upstream': 'stress base preparation includes W008 partition/occupancy construction and is timed separately; W005 existing stream record ceiling remains unchanged'},
                   'method': 'one timed sample per operation/case; perf_counter elapsed wall time; no warmup or statistical throughput claim'})
    executions = output.setdefault('executions', {})
    executions[args.case] = {'command': f'{sys.executable} docs/tasks/W009/verification/performance.py --case {args.case} --output {args.output}',
                             'source_sha256': output['source_sha256'].copy(),
                             'elapsed_seconds': perf_counter() - start, 'results': results}
    args.output.write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps({'case': args.case, 'elapsed_seconds': executions[args.case]['elapsed_seconds'], 'results': results}))


if __name__ == '__main__':
    main()
