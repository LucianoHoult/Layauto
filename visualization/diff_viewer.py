"""
Diff viewer: overlay original and modified layouts, highlighting changes.

Red dashed = removed shapes, Green solid = added shapes, Gray = unchanged.
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

from core.diff import compute_shape_diff


def plot_diff_overlay(orig_data: dict, modified_data: dict,
                      output_path: str, title: str = 'Layout Diff',
                      view_window=None):
    """Generate diff overlay visualization.

    When ``view_window`` is provided it controls the axes window; otherwise
    the legacy ``(-25, cell_w+25) × (-25, cell_h+25)`` fallback is used so
    existing callers stay byte-identical.
    """
    fig, ax = plt.subplots(1, 1, figsize=(10, 12))

    if view_window is None:
        cell_w = orig_data['params']['cell_width']
        cell_h = max(orig_data['params']['cell_height'],
                     modified_data['params']['cell_height'])
        x0, y0, x1, y1 = -25, -25, cell_w + 25, cell_h + 25
    else:
        x0, y0, x1, y1 = view_window

    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect('equal')
    ax.set_title(f'{title}\n(Gray=unchanged, Red=removed, Green=added)',
                 fontsize=11, fontweight='bold')
    
    diff = compute_shape_diff(orig_data, modified_data)
    
    for layer, info in diff.items():
        for bbox in info['unchanged']:
            x1, y1, x2, y2 = bbox
            ax.add_patch(patches.Rectangle(
                (x1, y1), x2-x1, y2-y1,
                linewidth=0.5, edgecolor='gray',
                facecolor=(0.7, 0.7, 0.7, 0.2)))
        
        for bbox in info['removed']:
            x1, y1, x2, y2 = bbox
            ax.add_patch(patches.Rectangle(
                (x1, y1), x2-x1, y2-y1,
                linewidth=1.5, edgecolor='red',
                facecolor=(1, 0, 0, 0.15), linestyle='--'))
        
        for bbox in info['added']:
            x1, y1, x2, y2 = bbox
            ax.add_patch(patches.Rectangle(
                (x1, y1), x2-x1, y2-y1,
                linewidth=1.5, edgecolor='green',
                facecolor=(0, 1, 0, 0.15)))
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"  Diff overlay saved: {output_path}")
