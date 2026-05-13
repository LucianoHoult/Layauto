"""
Layout viewer: matplotlib plots for inverter layouts plus the
multi-panel comparison plots used by the MVP pipeline.

The rectangle-drawing loop, color resolution, draw order and
view-window math all live in ``visualization.render``; this module is
just the layout-data-specific glue (grid lines from ``params``, fin
ticks, NMOS/PMOS labels) plus the multi-panel layouts.
"""

import json
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from tech.layer_map import LAYER_COLORS, LAYER_MAP
from tech.config_loader import get_tech_config
from visualization.render import (
    CANONICAL_DRAW_ORDER,
    compute_view_window,
    legend_handles,
    render_layers,
    resolve_color,
)

# Back-compat alias for callers that import ``DRAW_ORDER``.
DRAW_ORDER = list(CANONICAL_DRAW_ORDER)


def _decorate_layout(ax, params: dict, *, show_grid: bool = True):
    """Draw the layout-data-specific decorations onto ``ax``.

    Gate-pitch vlines, fin-pitch hlines and M1 track dashes only fire when
    the ``params`` dict has the keys that describe them (so device_info /
    net_shapes plots which don't have ``params`` skip this cleanly).
    """
    cell_w = params.get('cell_width')
    cell_h = params.get('cell_height')
    if show_grid and cell_w is not None:
        cfg = get_tech_config()
        for i in range(20):
            x = i * cfg.GATE_PITCH
            if x > cell_w + 20:
                break
            ax.axvline(x=x, color='gray', linewidth=0.3, linestyle=':', alpha=0.5)
        if params.get('nmos_fin_y'):
            for i in range(40):
                y = params['nmos_fin_y'][0] + i * cfg.FIN_PITCH
                if cell_h is not None and y > cell_h + 20:
                    break
                ax.axhline(y=y, color='gray', linewidth=0.3, linestyle=':', alpha=0.3)
        for _net, my in (params.get('m1_tracks') or {}).items():
            ax.axhline(y=my, color='orange', linewidth=0.5,
                       linestyle='--', alpha=0.4)

    for fy in params.get('nmos_fin_y', []) or []:
        ax.plot(-8, fy, '>', color='green', markersize=3)
    for fy in params.get('pmos_fin_y', []) or []:
        ax.plot(-8, fy, '>', color='green', markersize=3)

    if params.get('nmos_fin_y'):
        ny = params['nmos_fin_y']
        nmos_cy = (ny[0] + ny[-1]) / 2.0
        ax.text(-15, nmos_cy, f"NMOS\n{params.get('nmos_nfin','?')}fin",
                fontsize=6, ha='center', va='center',
                rotation=90, color='blue')
    if params.get('pmos_fin_y'):
        py = params['pmos_fin_y']
        pmos_cy = (py[0] + py[-1]) / 2.0
        ax.text(-15, pmos_cy, f"PMOS\n{params.get('pmos_nfin','?')}fin",
                fontsize=6, ha='center', va='center',
                rotation=90, color='red')


def draw_layout(ax, layout_data: dict, title: str = '',
                show_grid: bool = True, show_labels: bool = True,
                view_window=None):
    """Draw a single layout on a matplotlib axis.

    When ``view_window`` is ``None`` the axis window falls back to today's
    ``(-20, cell_w+20) × (-20, cell_h+20)`` so existing standalone callers
    (e.g. ``visualization/layout_viewer.py`` __main__) are byte-identical.
    The MVP pipeline passes an explicit window so all of its plots share
    axes.
    """
    shapes = layout_data['shapes']
    params = layout_data['params']

    if view_window is None:
        cell_w = params['cell_width']
        cell_h = params['cell_height']
        view_window = (-20.0, -20.0, cell_w + 20.0, cell_h + 20.0)

    render_layers(ax, shapes,
                  view_window=view_window,
                  title=title,
                  show_labels=show_labels)
    _decorate_layout(ax, params, show_grid=show_grid)


def generate_comparison_plot(orig_data: dict, target_data: dict,
                             output_path: str, view_window=None):
    """Generate side-by-side comparison of original and target layouts."""
    if view_window is None:
        view_window = compute_view_window(
            orig_data['shapes'], target_data['shapes'])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 8))
    draw_layout(ax1, orig_data,
                title=f"ORIGINAL (N={orig_data['params']['nmos_nfin']}fin, "
                      f"P={orig_data['params']['pmos_nfin']}fin)",
                view_window=view_window)
    draw_layout(ax2, target_data,
                title=f"TARGET (N={target_data['params']['nmos_nfin']}fin, "
                      f"P={target_data['params']['pmos_nfin']}fin)",
                view_window=view_window)

    handles = legend_handles(set(orig_data['shapes']) | set(target_data['shapes']))
    fig.legend(handles=handles, loc='lower center',
               ncol=len(handles), fontsize=8, framealpha=0.9)

    plt.suptitle('Dummy Inverter Layout - Fin Resize Comparison',
                 fontsize=14, fontweight='bold')
    plt.tight_layout(rect=[0, 0.06, 1, 0.95])
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"Comparison plot saved: {output_path}")


def generate_detail_plot(layout_data: dict, output_path: str,
                         title: str = '', view_window=None):
    """Generate a single detailed layout view with annotations."""
    fig, ax = plt.subplots(1, 1, figsize=(10, 12))
    draw_layout(ax, layout_data, title=title,
                show_grid=True, show_labels=True,
                view_window=view_window)

    handles = legend_handles(layout_data['shapes'].keys())
    ax.legend(handles=handles, loc='upper right', fontsize=7)

    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"Detail plot saved: {output_path}")


def generate_three_way_comparison(orig_data: dict, resized_data: dict,
                                   target_data: dict, output_path: str,
                                   config=None, view_window=None):
    """3-way comparison: Original → Resized → Target.

    Moved out of ``pipeline/run_mvp.py`` so the rectangle loop is shared.
    Keeps the existing filename / DPI / legend layout so the byte-golden
    test set and any consumer of the PNG are undisturbed.
    """
    if config is None:
        config = get_tech_config()
    if view_window is None:
        view_window = compute_view_window(
            orig_data['shapes'],
            resized_data['shapes'],
            target_data['shapes'],
        )

    fig, axes = plt.subplots(1, 3, figsize=(20, 9))
    datasets = [
        (orig_data,
         'ORIGINAL\n'
         f"(N={orig_data['params']['nmos_nfin']}fin, "
         f"P={orig_data['params']['pmos_nfin']}fin)", axes[0]),
        (resized_data,
         'RESIZED (solver output)\n'
         f"(N={resized_data['params']['nmos_nfin']}fin, "
         f"P={resized_data['params']['pmos_nfin']}fin)", axes[1]),
        (target_data,
         'TARGET (ground truth)\n'
         f"(N={target_data['params']['nmos_nfin']}fin, "
         f"P={target_data['params']['pmos_nfin']}fin)", axes[2]),
    ]

    for data, title, ax in datasets:
        render_layers(ax, data['shapes'],
                      view_window=view_window, title=title)
        # Gate-pitch vlines stay specific to this plot.
        params = data['params']
        cell_w = params.get('cell_width')
        if cell_w is not None:
            for i in range(20):
                x = i * config.GATE_PITCH
                if x > cell_w + 20:
                    break
                ax.axvline(x=x, color='gray', linewidth=0.3,
                           linestyle=':', alpha=0.4)
        _decorate_layout(ax, params, show_grid=False)

    handles = legend_handles(
        set(orig_data['shapes'])
        | set(resized_data['shapes'])
        | set(target_data['shapes']),
    )
    fig.legend(handles=handles, loc='lower center',
               ncol=len(handles), fontsize=8)

    plt.suptitle('Fin Resize MVP: Original -> Solver Output -> Target',
                 fontsize=14, fontweight='bold')
    plt.tight_layout(rect=[0, 0.06, 1, 0.95])
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"  3-way comparison saved: {output_path}")


def generate_diff_overlay(orig_data: dict, resized_data: dict,
                          output_path: str, view_window=None):
    """Overlay original and resized, highlighting changes.

    Gray = unchanged, red dashed = removed, green solid = added. The
    semantics are bespoke (not the LAYER_COLORS scheme), so this routine
    builds the rectangles directly rather than going through
    ``render_layers``. ``view_window`` controls the axes window only.
    """
    if view_window is None:
        view_window = compute_view_window(
            orig_data['shapes'], resized_data['shapes'])

    fig, ax = plt.subplots(1, 1, figsize=(10, 12))

    x0, y0, x1, y1 = view_window
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect('equal')
    ax.set_title('Resize Diff Overlay\n(Gray=unchanged, Red=removed, Green=added)',
                 fontsize=11, fontweight='bold')
    ax.set_xlabel('X (nm)')
    ax.set_ylabel('Y (nm)')

    diff_layers = ['FIN', 'OD', 'POLY', 'LI', 'VIA0', 'M1']
    for layer_name in diff_layers:
        orig_shapes = orig_data['shapes'].get(layer_name, [])
        new_shapes = resized_data['shapes'].get(layer_name, [])

        def _key(s):
            return (s['x1'], s['y1'], s['x2'], s['y2'], s.get('net', ''))

        orig_set = {_key(s) for s in orig_shapes}
        new_set = {_key(s) for s in new_shapes}

        for sx1, sy1, sx2, sy2, _net in orig_set & new_set:
            ax.add_patch(patches.Rectangle(
                (sx1, sy1), sx2 - sx1, sy2 - sy1,
                linewidth=0.5, edgecolor='gray',
                facecolor=(0.7, 0.7, 0.7, 0.2)))
        for sx1, sy1, sx2, sy2, _net in orig_set - new_set:
            ax.add_patch(patches.Rectangle(
                (sx1, sy1), sx2 - sx1, sy2 - sy1,
                linewidth=1.5, edgecolor='red',
                facecolor=(1, 0, 0, 0.15), linestyle='--'))
            cx, cy = (sx1 + sx2) / 2.0, (sy1 + sy2) / 2.0
            ax.text(cx, cy, f'-{layer_name}', fontsize=4,
                    ha='center', va='center',
                    color='red', fontweight='bold')
        for sx1, sy1, sx2, sy2, _net in new_set - orig_set:
            ax.add_patch(patches.Rectangle(
                (sx1, sy1), sx2 - sx1, sy2 - sy1,
                linewidth=1.5, edgecolor='green',
                facecolor=(0, 1, 0, 0.15), linestyle='-'))
            cx, cy = (sx1 + sx2) / 2.0, (sy1 + sy2) / 2.0
            ax.text(cx, cy, f'+{layer_name}', fontsize=4,
                    ha='center', va='center',
                    color='darkgreen', fontweight='bold')

    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"  Diff overlay saved: {output_path}")


if __name__ == '__main__':
    fixture_dir = os.path.join(os.path.dirname(__file__), '..', 'dummy', 'fixtures')

    with open(os.path.join(fixture_dir, 'buffer_original.json'), encoding='utf-8') as f:
        orig = json.load(f)
    with open(os.path.join(fixture_dir, 'buffer_target.json'), encoding='utf-8') as f:
        target = json.load(f)

    output_dir = os.path.join(os.path.dirname(__file__), '..', 'dummy', 'fixtures')

    generate_comparison_plot(orig, target,
                             os.path.join(output_dir, 'layout_comparison.png'))
    generate_detail_plot(orig,
                         os.path.join(output_dir, 'layout_original_detail.png'),
                         title='Original Inverter (NMOS=5fin, PMOS=7fin)')
