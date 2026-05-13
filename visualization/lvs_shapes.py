"""
Visualizers for the LVS-derived middle files produced in Stage 1.5.

``device_info.yaml`` and ``net_shapes.yaml`` describe layer-shape bboxes
in micrometers (Calibre HDB units). The two ``*_to_shapes`` converters
here turn those nested dicts into the same ``{layer: [bbox-dict]}``
shape-map that the rest of the visualization package speaks, with
coordinates rescaled to nanometers so they land in the same coordinate
frame as the GDS / JSON layout dicts (cell origin at (0, 0)).

``plot_lvs_overlay`` then draws the LVS-derived shapes against the
original GDS shapes — side-by-side with a shared coordinate window, or
overlaid in one axis with the GDS faintly filled and the LVS shapes
bold-outlined.
"""

import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from visualization.render import (
    compute_view_window, legend_handles, render_layers,
)


def device_info_to_shapes(device_info: dict, *,
                          um_to_nm: float = 1000.0) -> dict:
    """``device_info.yaml`` dict -> ``{seed_layer_name: [bbox-dict, ...]}``.

    Layer names here are LVS *seed-layer* names (``ngate_lvt``,
    ``pgate_lvt``, ...) — NOT GDS layer names — so they won't match
    ``LAYER_COLORS``; ``resolve_color`` falls back to a deterministic
    HSV pick so they still render with stable distinct colors.

    Each emitted bbox carries ``net = layout_inst`` (e.g. ``'M0'``)
    and ``desc = '<inst> type=<device_type_number>'`` (0=NMOS, 1=PMOS).
    """
    out: dict = {}
    for dev in device_info.get('devices', []) or []:
        inst = dev.get('layout_inst', '?')
        dtn = dev.get('device_type_number')
        for layer in dev.get('layers', []) or []:
            bucket = out.setdefault(layer.get('name', '?'), [])
            for sh in layer.get('shapes', []) or []:
                bb = sh.get('bbox_um') or {}
                bucket.append({
                    'x1': bb.get('x1', 0.0) * um_to_nm,
                    'y1': bb.get('y1', 0.0) * um_to_nm,
                    'x2': bb.get('x2', 0.0) * um_to_nm,
                    'y2': bb.get('y2', 0.0) * um_to_nm,
                    'net': inst,
                    'desc': f'{inst} type={dtn}',
                })
    return out


def net_shapes_to_shapes(net_shapes: dict, *,
                         um_to_nm: float = 1000.0) -> dict:
    """``net_shapes.yaml`` dict -> ``{gds_layer_name: [bbox-dict, ...]}``.

    Layer names here ARE GDS layer names (``LI``, ``VIA0``, ``M1``) so
    ``LAYER_COLORS`` lights them up directly.

    Each emitted bbox carries ``net = lvs_name`` (``IN``/``OUT``/...)
    and ``desc = '<lvs_name> (#<lvs_index>)'``.
    """
    out: dict = {}
    for net in net_shapes.get('nets', []) or []:
        lname = net.get('lvs_name') or net.get('schematic_name') or '?'
        lidx = net.get('lvs_index')
        for layer in net.get('layers', []) or []:
            bucket = out.setdefault(layer.get('name', '?'), [])
            for sh in layer.get('shapes', []) or []:
                bb = sh.get('bbox_um') or {}
                bucket.append({
                    'x1': bb.get('x1', 0.0) * um_to_nm,
                    'y1': bb.get('y1', 0.0) * um_to_nm,
                    'x2': bb.get('x2', 0.0) * um_to_nm,
                    'y2': bb.get('y2', 0.0) * um_to_nm,
                    'net': lname,
                    'desc': f'{lname} (#{lidx})',
                })
    return out


def plot_lvs_overlay(gds_shapes: dict, lvs_shapes: dict, output_path: str, *,
                     view_window=None, title: str = 'LVS vs GDS',
                     mode: str = 'side_by_side'):
    """Compare original-GDS shapes against LVS-derived shapes.

    ``mode='side_by_side'`` draws two axes sharing ``view_window`` and
    ``set_aspect('equal')`` so the user can flip between them mentally —
    GDS left, LVS right.

    ``mode='overlay'`` collapses to one axis: GDS faint-filled
    (``alpha_override=0.15``, no labels), LVS bold-outlined
    (``edge_only=True``, thick linewidth) on top.
    """
    if view_window is None:
        view_window = compute_view_window(gds_shapes, lvs_shapes)

    if mode == 'side_by_side':
        fig, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(14, 8))
        render_layers(ax_l, gds_shapes,
                      view_window=view_window,
                      title=f'{title} - GDS')
        render_layers(ax_r, lvs_shapes,
                      view_window=view_window,
                      title=f'{title} - LVS')
        handles = legend_handles(set(gds_shapes) | set(lvs_shapes))
        fig.legend(handles=handles, loc='lower center',
                   ncol=min(len(handles), 8), fontsize=7)
        plt.tight_layout(rect=[0, 0.05, 1, 0.97])
    elif mode == 'overlay':
        fig, ax = plt.subplots(1, 1, figsize=(10, 12))
        render_layers(ax, gds_shapes,
                      view_window=view_window,
                      title=title,
                      alpha_override=0.15,
                      show_labels=False)
        render_layers(ax, lvs_shapes,
                      view_window=view_window,
                      edge_only=True,
                      linewidth=1.6)
        handles = legend_handles(set(gds_shapes) | set(lvs_shapes))
        ax.legend(handles=handles, loc='upper right', fontsize=7)
        plt.tight_layout()
    else:
        plt.close()
        raise ValueError(f"unknown mode {mode!r}; expected 'side_by_side' or 'overlay'")

    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"  LVS-shape plot saved: {output_path}")
