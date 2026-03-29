"""
Visualize the CSP grid state: track segments, domain sizes, and assignments.

Useful for debugging CSP loading and constraint propagation.
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from typing import Optional

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.csp_engine import ConstraintEngine


def plot_csp_layer(engine: ConstraintEngine, layer: str,
                   output_path: str, show_domain: bool = True,
                   title: str = ''):
    """
    Plot a single layer's CSP grid state.
    
    Color coding:
    - White: unassigned, full domain
    - Light green: unassigned, reduced domain
    - Blue shades: assigned (color by net)
    - Red: empty domain (contradiction)
    """
    dims = engine.layer_dims.get(layer)
    if not dims:
        print(f"Layer {layer} not found")
        return
    
    t_start, t_end, o_start, o_end = dims
    n_tracks = t_end - t_start
    n_ortho = o_end - o_start
    
    fig, ax = plt.subplots(figsize=(max(8, n_ortho * 0.6), max(4, n_tracks * 0.8)))
    
    # Color map for nets
    net_colors = {}
    color_cycle = ['#4477AA', '#EE6677', '#228833', '#CCBB44',
                   '#66CCEE', '#AA3377', '#BBBBBB']
    color_idx = 0
    
    for t in range(t_start, t_end):
        for o in range(o_start, o_end):
            pos = (layer, t, o)
            cell = engine.get_cell(pos)
            if cell is None:
                continue
            
            x = o - o_start
            y = t - t_start
            
            if cell.is_assigned and cell.assignment.net_id:
                net = cell.assignment.net_id
                if net not in net_colors:
                    net_colors[net] = color_cycle[color_idx % len(color_cycle)]
                    color_idx += 1
                color = net_colors[net]
                alpha = 0.8
                label = net[:3]
            elif not cell.is_feasible:
                color = 'red'
                alpha = 0.9
                label = 'X'
            else:
                ds = cell.domain_size
                max_ds = len(engine.net_ids) * 2 + 1
                intensity = 1.0 - (ds / max_ds) * 0.5
                color = (intensity, 1.0, intensity)
                alpha = 0.5
                label = str(ds) if show_domain else ''
            
            rect = patches.Rectangle(
                (x - 0.4, y - 0.4), 0.8, 0.8,
                facecolor=color, edgecolor='gray',
                alpha=alpha, linewidth=0.5)
            ax.add_patch(rect)
            
            if label:
                ax.text(x, y, label, ha='center', va='center',
                        fontsize=6, fontweight='bold')
    
    ax.set_xlim(-1, n_ortho)
    ax.set_ylim(-1, n_tracks)
    ax.set_xticks(range(n_ortho))
    ax.set_xticklabels(range(o_start, o_end), fontsize=6)
    ax.set_yticks(range(n_tracks))
    ax.set_yticklabels(range(t_start, t_end), fontsize=6)
    ax.set_xlabel('Ortho track index')
    ax.set_ylabel('Track index')
    ax.set_title(title or f'CSP Grid: {layer}', fontweight='bold')
    ax.set_aspect('equal')
    ax.invert_yaxis()
    
    # Legend for nets
    if net_colors:
        legend_patches = [patches.Patch(color=c, label=n)
                         for n, c in net_colors.items()]
        ax.legend(handles=legend_patches, loc='upper right', fontsize=7)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  CSP grid plot saved: {output_path}")
