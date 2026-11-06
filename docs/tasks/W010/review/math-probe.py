"""Independent W010 review oracle: integer pixels and rational rectangle peeling.

No product predicate or formal-test oracle supplies expected geometry. Existing
test helpers only copy/rebind temporary captured GDS bytes for real integration.
"""
from __future__ import annotations

import hashlib
import json
import random
import subprocess
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests/contracts'))

from layauto_v2.domain.evidence import EvidenceRecord
from layauto_v2.domain.geometry import Rect
from layauto_v2.domain.local_connectivity import ContactProblem
from layauto_v2.normalization import build_local_connectivity
from layauto_v2.state.local_connectivity import (
    build_local_connectivity_draft, encloses_connector, same_layer_contact,
)
from w005_cases import apply_case
from w007_cases import ready_copy
from w009_cases import rewrite_geometry, special_input
from w010_cases import build_effective


def pixels(boxes):
    return {(x, y) for x0, y0, x1, y1 in boxes
            for x in range(x0, x1) for y in range(y0, y1)}


def pixel_contact(first, second):
    """Unit open squares overlap or share a positive-length unit edge."""
    a, b = pixels(first), pixels(second)
    if a & b:
        return True
    return any((x + dx, y + dy) in b for x, y in a
               for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))


def subtract(uncovered, cover):
    """Peel one closed rectangle from all currently uncovered open areas."""
    out = []
    for x0, y0, x1, y1 in uncovered:
        a, b, c, d = max(x0, cover[0]), max(y0, cover[1]), min(x1, cover[2]), min(y1, cover[3])
        if a >= c or b >= d:
            out.append((x0, y0, x1, y1))
            continue
        for piece in ((x0, y0, a, y1), (c, y0, x1, y1),
                      (a, y0, c, b), (a, d, c, y1)):
            if piece[0] < piece[2] and piece[1] < piece[3]:
                out.append(piece)
    return out


def peeling_enclosure(cover, connector, margin):
    # A finite union of closed rectangles covers the closed target iff no
    # positive-area residual remains; a missing boundary cannot occur alone.
    x0, y0, x1, y1 = connector
    remaining = [(x0 - margin, y0 - margin, x1 + margin, y1 + margin)]
    for piece in cover:
        remaining = subtract(remaining, piece)
    return not remaining


def random_box(rng, low=-6, high=7):
    x0, x1 = sorted(rng.sample(range(low, high), 2))
    y0, y1 = sorted(rng.sample(range(low, high), 2))
    return x0, y0, x1, y1


def shifted(boxes, dx, dy):
    return tuple((a + dx, b + dy, c + dx, d + dy) for a, b, c, d in boxes)


def check_predicates():
    rng = random.Random(202611050010)
    contact_count = enclosure_count = 0
    contact_outcomes, enclosure_outcomes = Counter(), Counter()
    for case in range(5000):
        first = tuple(random_box(rng) for _ in range(rng.randrange(7)))
        second = tuple(random_box(rng) for _ in range(rng.randrange(7)))
        expected = pixel_contact(first, second)
        for dx, dy in ((0, 0), (2 ** 120, -(2 ** 120))):
            a, b = shifted(first, dx, dy), shifted(second, dx, dy)
            actual = same_layer_contact(tuple(Rect(*v) for v in a), tuple(Rect(*v) for v in b))
            assert actual == expected, ('contact', case, first, second, expected, actual)
            contact_count += 1
            contact_outcomes[str(actual)] += 1
        cover = tuple(random_box(rng) for _ in range(rng.randrange(9)))
        target = random_box(rng, -4, 5)
        margin = Fraction(rng.randrange(8), rng.randrange(1, 8))
        expected = peeling_enclosure(cover, target, margin)
        for dx, dy in ((0, 0), (-(2 ** 120), 2 ** 120)):
            moved_cover = shifted(cover, dx, dy)
            moved_target = shifted((target,), dx, dy)[0]
            actual = encloses_connector(tuple(Rect(*v) for v in moved_cover), Rect(*moved_target), margin)
            assert actual == expected, ('enclosure', case, cover, target, str(margin), expected, actual)
            enclosure_count += 1
            enclosure_outcomes[str(actual)] += 1
    return {'random_seed': 202611050010, 'contact_comparisons': contact_count,
            'enclosure_comparisons': enclosure_count, 'contact_outcomes': dict(contact_outcomes),
            'enclosure_outcomes': dict(enclosure_outcomes),
            'coordinate_translation_magnitude': str(2 ** 120),
            'oracle_contact': 'occupied unit square sets and four-neighbor shared unit edges',
            'oracle_enclosure': 'sequential exact rational uncovered-rectangle peeling'}


def rules_for(effective):
    tech = next(record for record in effective.completed if record.kind == 'tech')
    return EvidenceRecord('rules', effective.input.input.value['tech']['rules'], (tech.sources[6],))


def node_key(owner_id, layer, role, boxes):
    return owner_id.sha256, layer, role, tuple(tuple(v) for v in boxes)


def prove_graph(effective, public=False):
    if public:
        result = build_local_connectivity(effective)
        assert result.status == 'success', result.issues
        draft = result.value
    else:
        draft = build_local_connectivity_draft(effective.value, rules_for(effective))
    assert draft is not None
    expected_nodes = {}
    for record in effective.value.base.layout.records:
        if record.layer in ('OD', 'LI'):
            for region in effective.value.for_record(record.id).regions:
                if region.role != 'channel':
                    key = node_key(record.id, record.layer, region.role, (r.bounds for r in region.rectangles))
                    expected_nodes[key] = tuple(r.bounds for r in region.rectangles)
        elif record.layer in ('POLY', 'M1', 'BODY_N', 'BODY_P'):
            key = node_key(record.id, record.layer, 'effective', (record.rect.bounds,))
            expected_nodes[key] = (record.rect.bounds,)
    actual_nodes = {n.ref: node_key(n.region.owner_id, n.layer, n.region.role,
                                  (r.bounds for r in n.region.rectangles)) for n in draft.nodes}
    assert Counter(actual_nodes.values()) == Counter(expected_nodes.keys())
    keys = sorted(expected_nodes)
    expected_edges, expected_audits = [], []
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            if a[1] == b[1] and pixel_contact(expected_nodes[a], expected_nodes[b]):
                expected_edges.append(('same_layer', tuple(sorted((a, b))), None))
    pairs = {'CONTACT': ('OD', 'LI'), 'VIA0': ('LI', 'M1'), 'GCONTACT': ('POLY', 'M1')}
    for connector in effective.value.base.layout.records:
        if connector.layer not in pairs:
            continue
        ends = []
        cut_pixels = pixels((connector.rect.bounds,))
        for layer in pairs[connector.layer]:
            candidates = [k for k in keys if k[1] == layer and pixels(expected_nodes[k]) & cut_pixels]
            assert len(candidates) == 1, ('oracle ambiguity', connector, candidates)
            key = candidates[0]
            ends.append(key)
            margin = Fraction(1, effective.value.base.layout.units.canonical_tick_nm)
            status = 'pass' if peeling_enclosure(expected_nodes[key], connector.rect.bounds, margin) else 'violation'
            expected_audits.append((connector.id.sha256, key, layer, margin, status))
        expected_edges.append(('connector', tuple(sorted(ends)), connector.id.sha256))
    actual_edges = [(e.kind, tuple(sorted(actual_nodes[r] for r in e.endpoints)),
                     None if e.connector_id is None else e.connector_id.sha256) for e in draft.edges]
    assert Counter(actual_edges) == Counter(expected_edges)
    actual_audits = [(a.connector_id.sha256, actual_nodes[a.node_ref], a.layer, a.margin_ticks, a.status)
                     for a in draft.audits]
    assert Counter(actual_audits) == Counter(expected_audits)
    # Independent all-pairs boolean transitive closure, rather than DFS/union.
    reach = {(a, a) for a in keys}
    for _, (a, b), _ in expected_edges:
        reach.update(((a, b), (b, a)))
    for pivot in keys:
        reach.update((a, b) for a in keys for b in keys if (a, pivot) in reach and (pivot, b) in reach)
    expected_components = {frozenset(b for b in keys if (a, b) in reach) for a in keys}
    actual_components = {frozenset(actual_nodes[r] for r in c.members) for c in draft.components}
    assert actual_components == expected_components
    return {'nodes': len(keys), 'edges': len(expected_edges), 'components': len(expected_components),
            'audits': len(expected_audits), 'enclosure_status': draft.local_enclosure_status,
            'public_capture_result': public, 'semantic_digest': draft.semantic_digest}


def check_actual_graphs():
    outcomes = {}
    rng = random.Random(202611051010)
    with tempfile.TemporaryDirectory(prefix='w010-math-review-', dir='/workspace/work') as scratch:
        parent = Path(scratch)
        root = ready_copy(parent / 'normal')
        outcomes['normal'] = prove_graph(build_effective(root), public=True)
        root = ready_copy(parent / 'via-violation')
        apply_case(root, 'via_enclosure')
        outcomes['via_enclosure'] = prove_graph(build_effective(root))
        assert outcomes['via_enclosure']['enclosure_status'] == 'violation'
        root = ready_copy(parent / 'cut-islands')
        special_input(root)
        outcomes['cut_islands'] = prove_graph(build_effective(root))
        root = ready_copy(parent / 'generated-topology')
        extra = [('M1', tuple(v + 200 for v in random_box(rng, 0, 12)))
                 for _ in range(16)]
        extra.extend([('M1', (220, 200, 224, 204)), ('M1', (224, 204, 228, 208)),
                      ('M1', (220, 200, 224, 204)), ('M1', (224, 201, 226, 203)),
                      ('LI', (300, 300, 320, 320)), ('CUT', (307, 307, 313, 313)),
                      ('M1', (298, 298, 322, 322)), ('VIA0', (302, 304, 318, 306)),
                      ('VIA0', (303, 303, 307, 307)), ('VIA0', (29, 50, 33, 54))])
        rewrite_geometry(root, append=extra)
        outcomes['generated_topology_hole_duplicate_connector'] = prove_graph(build_effective(root))
        # Same-layer connected or duplicate records remain independent sides;
        # enclosure cannot discard a second positive-area candidate.
        bad_cases = {'duplicate_region': [('LI', (28, 30, 34, 55))],
                     'connected_two_regions': [('LI', (30, 35, 36, 60))],
                     'second_candidate_fails_enclosure': [('LI', (32, 41, 35, 45))]}
        for name, extra in bad_cases.items():
            root = ready_copy(parent / name)
            rewrite_geometry(root, append=extra)
            effective = build_effective(root)
            try:
                build_local_connectivity_draft(effective.value, rules_for(effective))
            except ContactProblem as exc:
                assert exc.issue.code == 'AmbiguousConnectorEndpoint'
                assert 'found 2' in exc.issue.message
                outcomes[name] = {'status': 'located_rejection', 'code': exc.issue.code,
                                  'field': exc.issue.source.field, 'message': exc.issue.message}
            else:
                raise AssertionError(('unexpected graph success', name))
        for name, box in {'edge_only': (34, 50, 38, 54), 'corner_only': (34, 55, 38, 59)}.items():
            root = ready_copy(parent / name)
            rewrite_geometry(root, replace_layers={'VIA0': (box,)})
            effective = build_effective(root)
            try:
                build_local_connectivity_draft(effective.value, rules_for(effective))
            except ContactProblem as exc:
                assert exc.issue.code == 'AmbiguousConnectorEndpoint'
                assert 'found 0' in exc.issue.message
                outcomes[name] = {'status': 'located_rejection', 'code': exc.issue.code,
                                  'field': exc.issue.source.field, 'message': exc.issue.message}
            else:
                raise AssertionError(('unexpected graph success', name))
    return outcomes


def main():
    started = datetime.now(timezone.utc).isoformat()
    tick = time.perf_counter()
    modules = ['layauto_v2/state/local_connectivity.py', 'layauto_v2/domain/local_connectivity.py',
               'layauto_v2/normalization/local_connectivity.py']
    result = {'status': 'running', 'started_at_utc': started, 'python': sys.version,
              'executable': sys.executable, 'cwd': str(Path.cwd()),
              'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'source_sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in modules}}
    result['predicates'] = check_predicates()
    result['actual_graphs'] = check_actual_graphs()
    result.update(status='passed', elapsed_seconds=time.perf_counter() - tick,
                  finished_at_utc=datetime.now(timezone.utc).isoformat())
    path = Path(__file__).with_name('math-result.json')
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
