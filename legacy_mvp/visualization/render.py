"""
Shared rectangle renderer used by all matplotlib-based viz modules.

The motivation is a single source of truth for:
  - which order layers are drawn in (back-to-front),
  - what color each layer gets (LAYER_COLORS + a deterministic fallback so
    LVS seed-layer names like 'ngate_lvt' / 'pgate_lvt' also get stable colors
    that don't collide with the GDS-layer palette),
  - how the coordinate window is computed when plots want to share axes across
    multiple datasets (original GDS, resized GDS, target, device_info, net_shapes),
  - and the actual ``add_patch(Rectangle)`` loop with optional net labels.

Plot files in this package import ``render_layers`` instead of re-implementing
the rectangle loop.

All shape inputs use the same dict shape used elsewhere in the codebase:
``{layer_name: [ {'x1','y1','x2','y2', 'net'?, 'desc'?}, ... ]}`` with
coordinates in nanometers.
"""

import os
import sys
import zlib
import colorsys

import matplotlib
matplotlib.use('Agg')
import matplotlib.patches as patches

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from tech.layer_map import LAYER_COLORS, LAYER_MAP


CANONICAL_DRAW_ORDER = (
    'BOUNDARY', 'NWELL', 'OD', 'FIN', 'POLY', 'LI', 'VIA0', 'M1',
)

LABEL_LAYERS_DEFAULT = ('VIA0', 'M1', 'LI')


_GOLDEN_RATIO_CONJUGATE = 0.6180339887498949


def resolve_color(layer_name: str) -> tuple:
    """Return an (r, g, b, a) tuple in [0, 1] for ``layer_name``.

    Known layers (those listed in ``tech/layer_map.yaml`` with a color)
    return the configured color. Unknown layers — typically LVS seed-layer
    names such as ``ngate_lvt`` / ``pgate_lvt`` that surface from
    ``device_info.yaml`` — get a deterministic fallback derived from
    ``zlib.crc32`` of the name (NOT ``hash()``, which is salted per
    process). The fallback is stable across processes so unit tests can
    assert exact RGBA values.
    """
    known = LAYER_COLORS.get(layer_name)
    if known is not None:
        return tuple(known)
    h = (zlib.crc32(layer_name.encode('utf-8')) * _GOLDEN_RATIO_CONJUGATE) % 1.0
    r, g, b = colorsys.hsv_to_rgb(h, 0.55, 0.85)
    return (r, g, b, 0.45)


def draw_order_for(layers, draw_order=None) -> list:
    """Return the draw order to use for the given iterable of layer names.

    Layers that appear in ``draw_order`` (default: ``CANONICAL_DRAW_ORDER``)
    are emitted first in that order; any remaining (unknown) layer names
    are appended in sorted order. This is what lets LVS seed-layer names
    coexist with the canonical GDS layers without colliding.
    """
    base = list(draw_order or CANONICAL_DRAW_ORDER)
    present = set(layers)
    ordered = [l for l in base if l in present]
    extras = sorted(l for l in present if l not in base)
    return ordered + extras


def compute_view_window(*shape_sets, margin_frac: float = 0.05,
                        square: bool = False) -> tuple:
    """Compute a shared (x0, y0, x1, y1) window covering all input shape sets.

    Each argument is a ``{layer: [bbox-dict, ...]}`` map. The returned window
    is the union bbox over every shape, expanded by ``margin_frac`` times the
    longer span. With ``square=True`` the shorter axis is padded so the window
    is square (useful when plots are meant to be flipped without their
    aspect-equal axes resizing). Empty input → ``(0.0, 0.0, 1.0, 1.0)``.
    """
    xs1, ys1, xs2, ys2 = [], [], [], []
    for sbl in shape_sets:
        if not sbl:
            continue
        for slist in sbl.values():
            for s in slist or ():
                xs1.append(s['x1']); ys1.append(s['y1'])
                xs2.append(s['x2']); ys2.append(s['y2'])
    if not xs1:
        return (0.0, 0.0, 1.0, 1.0)
    x0, y0 = min(xs1), min(ys1)
    x1, y1 = max(xs2), max(ys2)
    span = max(x1 - x0, y1 - y0) or 1.0
    m = span * margin_frac
    x0, y0, x1, y1 = x0 - m, y0 - m, x1 + m, y1 + m
    if square:
        w, h = x1 - x0, y1 - y0
        if w < h:
            cx = (x0 + x1) / 2.0
            x0, x1 = cx - h / 2.0, cx + h / 2.0
        elif h < w:
            cy = (y0 + y1) / 2.0
            y0, y1 = cy - w / 2.0, cy + w / 2.0
    return (x0, y0, x1, y1)


def render_layers(ax, shapes_by_layer: dict, *,
                  view_window=None, draw_order=None,
                  title: str = '',
                  label_layers=LABEL_LAYERS_DEFAULT,
                  show_labels: bool = True,
                  alpha_override=None,
                  edge_only: bool = False,
                  linewidth: float = 0.8) -> set:
    """Draw ``shapes_by_layer`` onto ``ax`` using consistent colors / order.

    Parameters
    ----------
    view_window : (x0, y0, x1, y1) or None
        When provided, ``ax.set_xlim`` / ``ax.set_ylim`` are set from it and
        ``ax.set_aspect('equal')`` is called. When ``None`` the caller is
        responsible for setting the limits (used by the legacy ``draw_layout``
        path that derives limits from ``params['cell_width']``).
    draw_order : sequence[str] or None
        Override ``CANONICAL_DRAW_ORDER``. Unknown layers always go last.
    label_layers / show_labels :
        When ``show_labels=True`` and a shape has a ``net`` key, layers in
        ``label_layers`` get a centered text label (small font for vias).
    alpha_override / edge_only / linewidth :
        Used by overlay-style plots (e.g. faint-fill GDS vs bold-outlined LVS).

    Returns
    -------
    set of str
        The layer names actually drawn (skips layers whose shape list is empty).
    """
    if view_window is not None:
        x0, y0, x1, y1 = view_window
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
        ax.set_aspect('equal')
    if title:
        ax.set_title(title, fontsize=10, fontweight='bold')
    ax.set_xlabel('X (nm)', fontsize=8)
    ax.set_ylabel('Y (nm)', fontsize=8)

    drawn = set()
    label_set = set(label_layers or ())
    for layer in draw_order_for(shapes_by_layer.keys(), draw_order):
        slist = shapes_by_layer.get(layer) or []
        if not slist:
            continue
        drawn.add(layer)
        rgba = resolve_color(layer)
        a = alpha_override if alpha_override is not None else rgba[3]
        face = 'none' if edge_only else (rgba[0], rgba[1], rgba[2], a)
        for s in slist:
            x1s, y1s, x2s, y2s = s['x1'], s['y1'], s['x2'], s['y2']
            ax.add_patch(patches.Rectangle(
                (x1s, y1s), x2s - x1s, y2s - y1s,
                linewidth=linewidth,
                edgecolor=rgba[:3],
                facecolor=face,
            ))
            if show_labels and s.get('net') and layer in label_set:
                cx = (x1s + x2s) / 2.0
                cy = (y1s + y2s) / 2.0
                fs = 4 if layer == 'VIA0' else 5
                ax.text(cx, cy, str(s['net']), fontsize=fs,
                        ha='center', va='center',
                        fontweight='bold', alpha=0.85)
    return drawn


def legend_handles(layer_names, *, draw_order=None,
                   skip=('BOUNDARY',)) -> list:
    """Build a list of ``patches.Patch`` legend handles in canonical order.

    ``skip`` defaults to ``('BOUNDARY',)`` because the boundary layer is so
    faint and large that including it in the legend isn't useful.
    """
    skip_set = set(skip or ())
    out = []
    for layer in draw_order_for(layer_names, draw_order):
        if layer in skip_set:
            continue
        rgba = resolve_color(layer)
        out.append(patches.Patch(
            facecolor=(rgba[0], rgba[1], rgba[2], rgba[3]),
            edgecolor=rgba[:3],
            label=layer,
        ))
    return out


__all__ = [
    'CANONICAL_DRAW_ORDER',
    'LABEL_LAYERS_DEFAULT',
    'resolve_color',
    'draw_order_for',
    'compute_view_window',
    'render_layers',
    'legend_handles',
    'LAYER_COLORS',
    'LAYER_MAP',
]
