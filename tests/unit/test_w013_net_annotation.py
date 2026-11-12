"""Independent finite-arrangement witnesses for exact W013 set arithmetic."""
from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import random

import pytest

from layauto_v2.domain.channel_identity import RationalRect
from layauto_v2.domain.net_annotation import (
    AnnotationRef, LayerCoverage, area, canonical_cover, difference, intersections,
)


def rectangles(boxes):
    return tuple(RationalRect(*(Fraction(value) for value in box)) for box in boxes)


def inside(boxes, x, y):
    return any(box.x0 < x < box.x1 and box.y0 < y < box.y1 for box in boxes)


def prove_region(first, second, result, operation):
    """Membership is constant on each open atom; midpoint sampling is exact.

    This checker uses a full Cartesian arrangement, not the product slab union
    or subtraction functions. It checks the complete set as well as its area.
    """
    boxes = first + second + result
    if not boxes:
        assert result == ()
        return Fraction(0)
    xs = sorted({value for box in boxes for value in (box.x0, box.x1)})
    ys = sorted({value for box in boxes for value in (box.y0, box.y1)})
    expected_area = Fraction(0)
    for left, right in zip(xs, xs[1:]):
        for bottom, top in zip(ys, ys[1:]):
            x, y = (left + right) / 2, (bottom + top) / 2
            a, b = inside(first, x, y), inside(second, x, y)
            expected = (a or b) if operation == 'union' else (a and b) if operation == 'intersection' else (a and not b)
            occupants = sum(box.x0 < x < box.x1 and box.y0 < y < box.y1 for box in result)
            assert occupants == int(expected), (operation, x, y)
            if expected:
                expected_area += (right - left) * (top - bottom)
    assert area(result) == expected_area
    assert tuple(box.bounds for box in result) == tuple(sorted(box.bounds for box in result))
    return expected_area


@pytest.mark.parametrize('left,right,union_area,intersection_area,difference_area', [
    (((0, 0, 6, 2),), ((4, 0, 8, 2),), 16, 4, 8),
    (((0, 0, 10, 2),), ((10, 0, 12, 2),), 24, 0, 20),
    (((0, 0, 2, 2),), ((2, 2, 4, 4),), 8, 0, 4),
    (((130, 20, 150, 24),), ((139, 18, 141, 26),), 88, 8, 72),
    (((0, 0, 10, 10),), ((2, 2, 8, 8),), 100, 36, 64),
    (((Fraction(1, 20), 0, Fraction(3, 20), 2),),
     ((Fraction(2, 20), 0, Fraction(4, 20), 2),),
     Fraction(3, 10), Fraction(1, 10), Fraction(1, 10)),
    (((-10, -8, -2, -1),), ((-5, -10, 0, -4),), 74, 12, 44),
    ((), ((0, 0, 2, 3),), 6, 0, 0),
])
def test_exact_set_hand_cases_preserve_holes_touch_and_fractional_area(
        left, right, union_area, intersection_area, difference_area):
    first, second = rectangles(left), rectangles(right)
    outputs = (canonical_cover(first + second), intersections(first, second), difference(first, second))
    expected = (Fraction(union_area), Fraction(intersection_area), Fraction(difference_area))
    for result, operation, measured in zip(outputs, ('union', 'intersection', 'difference'), expected):
        assert prove_region(first, second, result, operation) == measured


def test_overlapping_or_duplicate_same_net_evidence_never_double_counts_area():
    pieces = rectangles(((0, 0, 6, 2), (4, 0, 8, 2), (0, 0, 6, 2)))
    result = canonical_cover(pieces)
    assert tuple(box.bounds for box in result) == ((0, 0, 8, 2),)
    assert area(result) == 16
    assert canonical_cover(tuple(reversed(pieces))) == result


def test_fractional_seeded_set_operations_match_complete_arrangements():
    rng = random.Random(13013)
    for _ in range(36):
        groups = []
        for _ in range(2):
            boxes = []
            for _ in range(rng.randrange(1, 5)):
                xs = sorted(rng.sample(range(-12, 13), 2))
                ys = sorted(rng.sample(range(-12, 13), 2))
                boxes.append(tuple(Fraction(value, 20) for value in (xs[0], ys[0], xs[1], ys[1])))
            groups.append(rectangles(boxes))
        first, second = groups
        for result, operation in ((canonical_cover(first + second), 'union'),
                                  (intersections(first, second), 'intersection'),
                                  (difference(first, second), 'difference')):
            prove_region(first, second, result, operation)
        assert difference(first, second) == difference(tuple(reversed(first)), tuple(reversed(second)))


class MutableText(str):
    pass


class MutableFraction(Fraction):
    pass


def test_typed_refs_and_measures_require_native_scalars():
    with pytest.raises(ValueError):
        AnnotationRef(MutableText('binding'), 'a' * 64)
    with pytest.raises(ValueError):
        AnnotationRef('binding', MutableText('a' * 64))
    coverage = LayerCoverage('LI', 0, 0, 0, Fraction(0), Fraction(0), Fraction(0),
                             Fraction(0), Fraction(0), (), ())
    for field, value in (('drawn_shape_count', False), ('cell_count', True),
                         ('target_count', False), ('total_area', MutableFraction(0)),
                         ('covered_area', 0), ('unit', MutableText('nm2'))):
        with pytest.raises(ValueError):
            replace(coverage, **{field: value})
