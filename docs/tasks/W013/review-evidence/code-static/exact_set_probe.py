"""Independent finite-arrangement oracle for W013 rational set operations."""
from __future__ import annotations

from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys

from layauto_v2.domain.channel_identity import RationalRect
from layauto_v2.domain.net_annotation import canonical_cover, difference, intersections


def contains(rect, x, y):
    return rect.x0 < x < rect.x1 and rect.y0 < y < rect.y1


def oracle(a, b, operation):
    boxes = a + b
    if not boxes:
        return F(), []
    xs = sorted({x for row in boxes for x in (row.x0, row.x1)})
    ys = sorted({y for row in boxes for y in (row.y0, row.y1)})
    included = []
    total = F()
    for left, right in zip(xs, xs[1:]):
        for low, high in zip(ys, ys[1:]):
            x, y = (left + right) / 2, (low + high) / 2
            hit_a, hit_b = any(contains(row, x, y) for row in a), any(contains(row, x, y) for row in b)
            if operation(hit_a, hit_b):
                total += (right - left) * (high - low)
                included.append((x, y))
    return total, included


def main():
    rng = random.Random(130013)
    cases = 0
    for _ in range(160):
        a, b = [], []
        offset = rng.choice((0, 0, -10**30, 10**30))
        for group in (a, b):
            for _ in range(rng.randrange(5)):
                x0, x1 = sorted(rng.sample(range(-10, 11), 2))
                y0, y1 = sorted(rng.sample(range(-10, 11), 2))
                group.append(RationalRect(F(offset) + F(x0, 20), F(y0, 7), F(offset) + F(x1, 20), F(y1, 7)))
        a, b = tuple(a), tuple(b)
        for name, call, predicate in (
            ('union', lambda: canonical_cover(a + b), lambda x, y: x or y),
            ('intersection', lambda: intersections(a, b), lambda x, y: x and y),
            ('difference', lambda: difference(a, b), lambda x, y: x and not y),
        ):
            actual = call()
            expected_area, witnesses = oracle(a, b, predicate)
            assert sum((row.area for row in actual), F()) == expected_area, name
            assert all(sum(contains(row, x, y) for row in actual) == 1 for x, y in witnesses), name
            assert canonical_cover(actual) == actual, name
            # Distinct canonical output pieces may share boundaries, never area.
            assert all(first.intersection(second) is None for i, first in enumerate(actual) for second in actual[i + 1:]), name
            cases += 1
    root = Path.cwd()
    path = root / 'layauto_v2/domain/net_annotation.py'
    print(json.dumps({'classification': 'independent-exact-set-review-not-full-product-matrix',
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'python': sys.version, 'seed': 130013, 'random_inputs': 160, 'set_operation_checks': cases,
        'runtime_module_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'scope': ['Fraction 1/20 and 1/7 nm', 'negative and 10^30-offset coordinates', 'overlapping/redundant rectangles',
                  'union/intersection/difference area and coverage', 'disjoint canonical output'],
        'not_run': ['captured W010/W013 construction', 'resource costs', 'full regression']}, indent=2))


if __name__ == '__main__':
    main()
