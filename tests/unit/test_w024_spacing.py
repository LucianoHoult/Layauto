"""Hand-computed distances and direct contact on closed rectangles."""
import pytest

from layauto_v2.constraints.result import ShapeWitness
from layauto_v2.constraints.rules import measure_pair
from layauto_v2.domain.evidence import SourceRef
from layauto_v2.domain.geometry import Rect


@pytest.mark.parametrize('second,scale,threshold,squared,exact,status', [
    ((5, 6, 8, 8), 1, 5, 25, 5, 'pass'),           # dx=3, dy=4
    ((5, 5, 8, 8), 1, 5, 18, None, 'violation'),    # sqrt(18) < 5
    ((5, 6, 8, 8), 2, 10, 100, 10, 'pass'),
    ((5, 6, 8, 8), 2, 11, 100, 10, 'violation'),
    ((2, 2, 8, 8), 1, 5, 0, 0, 'violation'),       # point
    ((2, 1, 8, 8), 1, 5, 0, 0, 'same_layer_contact'),
    ((1, 1, 8, 8), 1, 5, 0, 0, 'same_layer_contact'),
    ((0, 0, 2, 2), 1, 5, 0, 0, 'same_layer_contact'),  # coincident, distinct records
])
def test_exact_spacing(second, scale, threshold, squared, exact, status):
    a = ShapeWitness('a', Rect(0, 0, 2, 2), SourceRef('drawing'))
    b = ShapeWitness('b', Rect(*second), SourceRef('drawing'))
    for first, last in ((a, b), (b, a)):
        pair = measure_pair(first, last, scale, threshold)
        assert (pair.distance_squared_nm2, pair.distance_nm, pair.status) == (squared, exact, status)
