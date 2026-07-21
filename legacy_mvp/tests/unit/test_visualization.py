"""Unit tests for the visualization helpers."""

import os
import sys

import pytest
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from tech.layer_map import LAYER_COLORS
from visualization.render import (
    CANONICAL_DRAW_ORDER,
    compute_view_window,
    draw_order_for,
    legend_handles,
    render_layers,
    resolve_color,
)
from visualization.lvs_shapes import (
    device_info_to_shapes,
    net_shapes_to_shapes,
    plot_lvs_overlay,
)


FIXTURE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'dummy', 'fixtures')


# ----- render.py -----

def test_resolve_color_known_layer():
    """Known layers return exactly their ``LAYER_COLORS`` entry."""
    assert resolve_color('FIN') == tuple(LAYER_COLORS['FIN'])
    assert resolve_color('M1') == tuple(LAYER_COLORS['M1'])


def test_resolve_color_unknown_layer_is_deterministic_and_in_range():
    """Unknown layer names get a stable HSV fallback color."""
    c1 = resolve_color('ngate_lvt')
    c2 = resolve_color('pgate_lvt')
    assert c1 != c2
    assert resolve_color('ngate_lvt') == c1  # stable across calls
    assert len(c1) == 4
    assert all(0.0 <= v <= 1.0 for v in c1)


def test_draw_order_for_canonical_first_then_extras_sorted():
    """Known layers in canonical order, unknown layers appended sorted."""
    assert draw_order_for(['M1', 'ngate_lvt', 'OD', 'pgate_lvt']) == [
        'OD', 'M1', 'ngate_lvt', 'pgate_lvt',
    ]
    assert draw_order_for([]) == []


def test_compute_view_window_union_with_no_margin():
    """Union bbox over two shape sets with ``margin_frac=0`` is exact."""
    w = compute_view_window(
        {'A': [{'x1': 0, 'y1': 0, 'x2': 10, 'y2': 4}]},
        {'B': [{'x1': -2, 'y1': 1, 'x2': 3, 'y2': 9}]},
        margin_frac=0.0,
    )
    assert w == (-2.0, 0.0, 10.0, 9.0)


def test_compute_view_window_with_margin():
    """``margin_frac=0.1`` expands by 0.1 * max-span on every side."""
    w = compute_view_window(
        {'A': [{'x1': 0, 'y1': 0, 'x2': 10, 'y2': 4}]},
        margin_frac=0.1,
    )
    # span = max(10, 4) = 10; margin = 1.0
    assert w == (-1.0, -1.0, 11.0, 5.0)


def test_compute_view_window_empty_input():
    """No shapes → default unit window so plot code never crashes."""
    assert compute_view_window(margin_frac=0.1) == (0.0, 0.0, 1.0, 1.0)


def test_compute_view_window_square_widens_shorter_axis():
    """``square=True`` pads the shorter dimension symmetrically."""
    w = compute_view_window(
        {'A': [{'x1': 0, 'y1': 0, 'x2': 10, 'y2': 4}]},
        margin_frac=0.0, square=True,
    )
    x0, y0, x1, y1 = w
    assert (x1 - x0) == pytest.approx(y1 - y0)
    assert x0 == 0.0 and x1 == 10.0  # x-axis already the longer one
    # y-window is centered around the original (0, 4) midpoint
    assert (y0 + y1) / 2.0 == pytest.approx(2.0)


def test_render_layers_returns_drawn_layer_set():
    """Empty layer lists are skipped; the rest get drawn and reported back."""
    fig, ax = plt.subplots()
    drawn = render_layers(ax, {
        'M1': [{'x1': 0, 'y1': 0, 'x2': 10, 'y2': 2, 'net': 'VDD'}],
        'ngate_lvt': [{'x1': 1, 'y1': 1, 'x2': 3, 'y2': 5}],
        'EMPTY_LAYER': [],
    }, view_window=(-1, -1, 11, 6))
    assert drawn == {'M1', 'ngate_lvt'}
    plt.close(fig)


def test_legend_handles_skips_boundary():
    """``BOUNDARY`` is dropped from the legend even when present."""
    handles = legend_handles({'BOUNDARY', 'M1', 'FIN'})
    labels = [h.get_label() for h in handles]
    assert 'BOUNDARY' not in labels
    assert set(labels) == {'M1', 'FIN'}


def test_canonical_draw_order_has_expected_layers():
    """Sanity: the shipped canonical order matches the MVP layer stack."""
    assert CANONICAL_DRAW_ORDER[0] == 'BOUNDARY'
    assert CANONICAL_DRAW_ORDER[-1] == 'M1'
    assert set(CANONICAL_DRAW_ORDER) == {
        'BOUNDARY', 'NWELL', 'OD', 'FIN', 'POLY', 'LI', 'VIA0', 'M1',
    }


# ----- lvs_shapes.py converters -----

def test_device_info_to_shapes_units_and_metadata():
    with open(os.path.join(FIXTURE_DIR, 'device_info.yaml'), encoding='utf-8') as f:
        d = yaml.safe_load(f)
    out = device_info_to_shapes(d)
    assert set(out) == {'ngate_lvt', 'pgate_lvt'}
    ng = out['ngate_lvt'][0]
    assert ng == {
        'x1': 44.0, 'y1': 27.5, 'x2': 64.0, 'y2': 152.5,
        'net': 'M0', 'desc': 'M0 type=0',
    }
    pg = out['pgate_lvt'][0]
    assert pg['net'] == 'M1' and pg['desc'] == 'M1 type=1'


def test_net_shapes_to_shapes_units_and_metadata():
    with open(os.path.join(FIXTURE_DIR, 'net_shapes.yaml'), encoding='utf-8') as f:
        n = yaml.safe_load(f)
    out = net_shapes_to_shapes(n)
    assert {'LI', 'VIA0', 'M1'} <= set(out)
    li_in = out['LI'][0]
    assert li_in == {
        'x1': 45.0, 'y1': 157.0, 'x2': 62.0, 'y2': 205.0,
        'net': 'IN', 'desc': 'IN (#1)',
    }
    # Multiple nets land in the same layer bucket:
    li_nets = {s['net'] for s in out['LI']}
    assert {'IN', 'OUT', 'VSS', 'VDD'} <= li_nets


def test_plot_lvs_overlay_side_by_side_writes_png(tmp_path):
    out_path = tmp_path / 'lvs_side.png'
    gds = {'LI': [{'x1': 0, 'y1': 0, 'x2': 10, 'y2': 2, 'net': 'IN'}]}
    lvs = {'ngate_lvt': [{'x1': 1, 'y1': 1, 'x2': 5, 'y2': 5, 'net': 'M0'}]}
    plot_lvs_overlay(gds, lvs, str(out_path), title='t', mode='side_by_side')
    assert out_path.exists() and out_path.stat().st_size > 0


def test_plot_lvs_overlay_overlay_writes_png(tmp_path):
    out_path = tmp_path / 'lvs_overlay.png'
    gds = {'LI': [{'x1': 0, 'y1': 0, 'x2': 10, 'y2': 2, 'net': 'IN'}]}
    lvs = {'ngate_lvt': [{'x1': 1, 'y1': 1, 'x2': 5, 'y2': 5, 'net': 'M0'}]}
    plot_lvs_overlay(gds, lvs, str(out_path), title='t', mode='overlay')
    assert out_path.exists() and out_path.stat().st_size > 0


def test_plot_lvs_overlay_invalid_mode_raises(tmp_path):
    with pytest.raises(ValueError):
        plot_lvs_overlay({}, {}, str(tmp_path / 'x.png'), mode='not-a-mode')


# ----- interactive.py (optional) -----

def test_write_interactive_html_optional(tmp_path):
    pytest.importorskip('plotly')
    from visualization.interactive import write_interactive_html
    out = tmp_path / 'view.html'
    write_interactive_html(
        {
            'a': {'M1': [{'x1': 0, 'y1': 0, 'x2': 10, 'y2': 2, 'net': 'VDD'}]},
            'b': {'M1': [{'x1': 0, 'y1': 1, 'x2': 10, 'y2': 3, 'net': 'VDD'}]},
        },
        str(out),
    )
    assert out.exists() and out.stat().st_size > 0
    html = out.read_text()
    assert '<html' in html.lower()
    assert 'plotly' in html.lower()


# ----- layout_viewer back-compat -----

def test_layout_viewer_draw_order_reexported():
    """Existing ``from visualization.layout_viewer import DRAW_ORDER`` must work."""
    from visualization.layout_viewer import DRAW_ORDER
    assert DRAW_ORDER[0] == 'BOUNDARY' and DRAW_ORDER[-1] == 'M1'
