"""Hand-calculated finite axis examples, independent of the configuration reader."""
from dataclasses import replace
from fractions import Fraction

import pytest

from layauto_v2.domain.geometry import Rect
from layauto_v2.state.projection_axes import CellGrid, EdgeAxis, TrackAxis


def test_half_open_edges_on_finite_negative_domain():
    grid = CellGrid(EdgeAxis(-6, 10, 2), EdgeAxis(-3, 4, 2))
    assert grid.spans(Rect(-2, -1, 6, 3)) == (0, 1, 0, 1)
    assert grid.spans(Rect(-2, -1, 4, 1)) == (0, 0, 0, 0)
    assert grid.spans(Rect(4, 1, 14, 5)) == (1, 1, 1, 1)
    assert grid.point(-6, -3) == (0, 0)
    assert grid.point(Fraction(399, 100), Fraction(99, 100)) == (0, 0)
    assert grid.point(4, 1) == (1, 1)
    for point in ((14, 0), (0, 5), (-7, -3)):
        with pytest.raises(IndexError):
            grid.point(*point)
    with pytest.raises(IndexError):
        grid.spans(Rect(-7, -1, 6, 3))


def test_cell_physical_conversions_with_exact_nonunit_scale():
    grid = CellGrid(EdgeAxis(-8, 10, 3), EdgeAxis(3, 2, 4))
    scale = Fraction(3, 2)
    assert grid.cell_bounds(1, 2) == Rect(2, 7, 12, 9)
    assert grid.index_to_physical(1, 2, scale) == (3, Fraction(21, 2), 18, Fraction(27, 2))
    assert grid.physical_to_index(3, Fraction(21, 2), scale) == (1, 2)
    assert grid.physical_to_index(Fraction(299, 100), Fraction(21, 2), scale) == (0, 2)


def test_exact_tracks_with_signed_numbering_and_rational_pitch():
    tracks = TrackAxis('x', Fraction(-3, 2), Fraction(5, 2), Fraction(1), -2, 1)
    assert [tracks.centre(k) for k in range(-2, 2)] == [Fraction(-3, 2), 1, Fraction(7, 2), 6]
    assert tracks.locate(Fraction(-3, 2)).neighbours == ((-2, 0),)
    between = tracks.locate(-1)
    assert between.status == 'off_track'
    assert between.position_nm == -1
    assert between.neighbours == ((-2, Fraction(1, 2)), (-1, -2))
    assert tracks.locate(6).neighbours == ((1, 0),)
    for outside in (Fraction(-151, 100), Fraction(601, 100)):
        result = tracks.locate(outside)
        assert (result.status, result.position_nm, result.neighbours) == ('outside_range', outside, ())
    with pytest.raises(IndexError):
        tracks.centre(-3)


def test_strip_checks_normal_dimension_physical_width_and_length():
    # With 2 nm/DBU, x=[-2,-1) is a vertical strip 2 nm wide centred at -3 nm.
    tracks = TrackAxis('x', -3, 10, 2, 8, 9)
    assert tracks.strip(Rect(-2, -4, -1, 2), 2).neighbours == ((8, 0),)
    assert tracks.strip(Rect(0, -4, 1, 2), 2).neighbours == ((8, 4), (9, -6))
    assert tracks.strip(Rect(-3, -4, -2, 2), 2).status == 'outside_range'
    for rect in (Rect(-2, -4, 0, 2), Rect(-2, 0, -1, 1)):
        assert tracks.strip(rect, 2).status == 'unsupported_strip'
    swapped = replace(tracks, index_axis='y')
    assert swapped.strip(Rect(-4, -2, 2, -1), 2).neighbours == ((8, 0),)
    assert swapped.strip(Rect(-2, -4, -1, 2), 2).status == 'unsupported_strip'


def test_large_track_and_edge_indices_preserve_one_dbu_and_half_steps():
    large = 10**30
    axis = EdgeAxis(-large, 2, large)
    assert axis.index(large - 1) == large - 1
    assert axis.span(large - 2, large) == (large - 1, large - 1)
    tracks = TrackAxis('y', large, 1, 1, -large, large)
    half = large + Fraction(1, 2)
    assert tracks.locate(half).neighbours == ((-large, Fraction(1, 2)), (1 - large, Fraction(-1, 2)))


@pytest.mark.parametrize('bad', (True, 0.5, '1'))
def test_inexact_axis_queries_rejected(bad):
    grid = CellGrid(EdgeAxis(0, 2, 4), EdgeAxis(0, 1, 4))
    tracks = TrackAxis('y', 0, 1, 1, 0, 7)
    for operation in (
        lambda: grid.point(bad, 0), lambda: grid.point(0, bad),
        lambda: grid.x_edges.span(0, bad), lambda: grid.cell_bounds(bad, 0),
        lambda: grid.physical_to_index(0, bad, 1), lambda: grid.index_to_physical(0, 0, bad),
        lambda: tracks.locate(bad), lambda: tracks.centre(bad),
        lambda: tracks.strip(Rect(0, 0, 3, 1), bad),
    ):
        with pytest.raises(ValueError):
            operation()


def test_degenerate_axes_or_nonpositive_unit_scale_are_invalid():
    with pytest.raises(ValueError):
        EdgeAxis(0, 0, 3)
    with pytest.raises(ValueError):
        EdgeAxis(0, 3, -1)
    tracks = TrackAxis('x', 0, 1, 2, 0, 0)
    assert tracks.locate(0).status == 'on_track'
    assert tracks.locate(1).status == 'outside_range'
    for change in ({'index_axis': 'z'}, {'last_index': -1}, {'pitch_nm': True}, {'width_nm': 0}):
        with pytest.raises(ValueError):
            replace(tracks, **change)
    with pytest.raises(ValueError):
        tracks.strip(Rect(0, 0, 1, 6), 0)
