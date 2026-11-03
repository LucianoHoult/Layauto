"""Bounded independent PM math/aggregate probe; no fixture or repo writes."""
from dataclasses import fields, replace
from fractions import Fraction
from itertools import combinations
from pathlib import Path

from layauto_v2.importers import read_inputs
from layauto_v2.normalization.geometry import build_geometry
from layauto_v2.normalization.geometry_input import geometry_from_parse_result
from layauto_v2.domain.geometry import Rect
from layauto_v2.state.coordinate import LayerPartition

checks = []
def reject(name, operation):
    try:
        operation()
    except ValueError:
        checks.append(name)
    else:
        raise AssertionError(name + ' was accepted')

# Deliberately beyond binary64 exact consecutive integers. This is mathematical
# DTO testing only and does not claim this range is admitted as GDS input.
n = 2**80
xs, ys = (-n, -n + 1, 0, n, n + 1), (-2, 0, 3, 5)
partition = LayerPartition('independent-math', xs, ys)
rect = Rect(-n, -1, n + 1, 4)
actual = partition.project(rect)
expected = {(i, j, (xs[i], a, xs[i+1], b))
            for i in range(4) for j, (a, b) in enumerate(((-1, 0), (0, 3), (3, 4)))}
assert {(i, j, r.bounds) for i, j, r in actual} == expected
assert len(actual) == 12
assert sum((r.x1-r.x0)*(r.y1-r.y0) for _, _, r in actual) == (2*n+1)*5
for (_, _, a), (_, _, b) in combinations(actual, 2):
    assert max(a.x0, b.x0) >= min(a.x1, b.x1) or max(a.y0, b.y0) >= min(a.y1, b.y1)
for i in range(4):
    x = Fraction(xs[i] + xs[i+1], 2)
    assert partition.point_to_index(x, Fraction(1, 2)) == (i, 1)
    assert partition.point_to_index(xs[i], 0) == (i, 1)
checks.append('12 huge-integer fragments: exact hand intervals, area, disjointness and 8 boundary/midpoint lookups')
reject('outer max boundary is excluded', lambda: partition.point_to_index(n+1, 0))
reject('bool coordinate rejected', lambda: partition.point_to_index(True, 0))
reject('fractional rectangle tick rejected', lambda: Rect(Fraction(1, 2), 0, 1, 1))

# Actual accepted capture; fixture reads end before pure geometry construction.
parsed = read_inputs(Path('tests/fixtures/w003_m1/site_config.yaml'))
assert parsed.status == 'success'
result = build_geometry(geometry_from_parse_result(parsed))
assert result.status == 'success' and result.value is not None
occupancy = result.value
layout = occupancy.layout
assert len(layout.records) == 40 and len(occupancy.fragments) == 41
assert len({record.id for record in layout.records}) == 40
projected = {record.id for record in layout.records if layout.policy(record.layer).projected}
assert len(projected) == 38
assert {fragment.record_id for fragment in occupancy.fragments} == projected
for record in layout.records:
    fragments = occupancy.for_record(record.id)
    if record.id not in projected:
        assert not fragments
        continue
    assert sum((f.rect.x1-f.rect.x0)*(f.rect.y1-f.rect.y0) for f in fragments) == record.rect.area
    for f in fragments:
        assert record.rect.x0 <= f.rect.x0 < f.rect.x1 <= record.rect.x1
        assert record.rect.y0 <= f.rect.y0 < f.rect.y1 <= record.rect.y1
    for a, b in combinations(fragments, 2):
        assert max(a.rect.x0,b.rect.x0) >= min(a.rect.x1,b.rect.x1) or max(a.rect.y0,b.rect.y0) >= min(a.rect.y1,b.rect.y1)
checks.append('actual capture: 40 distinct local records / 38 projected / 41 fragments with independent per-record coverage')
assert len(result.body_evidence.payload['shapes']) == 6
assert all(record.layer not in ('BTAP_N','BTAP_P') for record in layout.records)
checks.append('six external body shapes remain separate from local geometry')
reject('omitted drawn record rejected', lambda: replace(layout, records=layout.records[:-1]))
reject('duplicate drawn record rejected', lambda: replace(layout, records=layout.records + (layout.records[0],)))
reject('omitted fragment rejected', lambda: replace(occupancy, fragments=occupancy.fragments[:-1]))
reject('duplicate fragment rejected', lambda: replace(occupancy, fragments=occupancy.fragments + (occupancy.fragments[0],)))
reject('omitted partition layer rejected', lambda: replace(occupancy.partition, layers=occupancy.partition.layers[:-1]))
reject('invented algorithm rejected', lambda: replace(occupancy.partition, algorithm='invented/1'))
reject('success missing value rejected', lambda: replace(result, value=None))
unit = layout.units
for tick in (-2**31, -1, 0, 1, 2**31-1):
    assert unit.source_to_nm(tick) == Fraction(tick)
    assert unit.canonical_to_source(unit.source_to_canonical(tick)) == tick
reject('nonintegral canonical nm rejected', lambda: unit.nm_to_canonical(Fraction(901, 20)))
checks.append('selected scale: signed-int32 endpoints and exact inverse, no 45.05-to-45 truncation')
for value in (result, layout, occupancy.partition, occupancy):
    assert not {'no_change','physical_edges','terminal','coordinate_ref','body_complete'} & {f.name for f in fields(value)}
checks.append('base draft exposes no full-physical, body-proof or terminal field')
print('PASS: ' + str(len(checks)) + ' bounded checks')
for check in checks:
    print('- ' + check)
