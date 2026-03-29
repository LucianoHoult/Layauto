"""
Visualize inverter layout with layer colors, net labels, and grid overlay.

Generates a side-by-side comparison of original vs target layouts,
and individual detailed views with grid lines.
"""

import json
import os
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from tech.layer_map import LAYER_COLORS, LAYER_MAP
from tech.tech_params import *


# Layer draw order (back to front)
DRAW_ORDER = ['BOUNDARY', 'NWELL', 'OD', 'FIN', 'POLY', 'LI', 'VIA0', 'M1']


def draw_layout(ax, layout_data: dict, title: str = '', 
                show_grid: bool = True, show_labels: bool = True):
    """Draw a single layout on a matplotlib axis."""
    
    shapes = layout_data['shapes']
    params = layout_data['params']
    cell_w = params['cell_width']
    cell_h = params['cell_height']
    
    ax.set_xlim(-20, cell_w + 20)
    ax.set_ylim(-20, cell_h + 20)
    ax.set_aspect('equal')
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.set_xlabel('X (nm)')
    ax.set_ylabel('Y (nm)')
    
    # Draw grid lines
    if show_grid:
        # Gate pitch grid (vertical)
        for i in range(20):
            x = i * GATE_PITCH
            if x > cell_w + 20:
                break
            ax.axvline(x=x, color='gray', linewidth=0.3, linestyle=':', alpha=0.5)
        
        # Fin pitch grid (horizontal) 
        for i in range(40):
            y = params['nmos_fin_y'][0] + i * FIN_PITCH
            if y > cell_h + 20:
                break
            ax.axhline(y=y, color='gray', linewidth=0.3, linestyle=':', alpha=0.3)
        
        # M1 tracks (horizontal, dashed)
        for net, my in params['m1_tracks'].items():
            ax.axhline(y=my, color='orange', linewidth=0.5, linestyle='--', alpha=0.4)
    
    # Draw shapes layer by layer
    for layer_name in DRAW_ORDER:
        if layer_name not in shapes:
            continue
        color = LAYER_COLORS.get(layer_name, (0.5, 0.5, 0.5, 0.3))
        
        for s in shapes[layer_name]:
            x1, y1, x2, y2 = s['x1'], s['y1'], s['x2'], s['y2']
            w = x2 - x1
            h = y2 - y1
            
            rect = patches.Rectangle(
                (x1, y1), w, h,
                linewidth=0.8,
                edgecolor=color[:3],
                facecolor=(*color[:3], color[3]),
                label=layer_name if s == shapes[layer_name][0] else None,
            )
            ax.add_patch(rect)
            
            # Add net label for small shapes (via, short M1)
            if show_labels and s.get('net') and layer_name in ('VIA0', 'M1', 'LI'):
                cx = (x1 + x2) / 2
                cy = (y1 + y2) / 2
                fontsize = 4 if layer_name == 'VIA0' else 5
                ax.text(cx, cy, s['net'], fontsize=fontsize,
                        ha='center', va='center', color='black',
                        fontweight='bold', alpha=0.8)
    
    # Mark fin positions with small ticks
    for fy in params.get('nmos_fin_y', []):
        ax.plot(-8, fy, '>', color='green', markersize=3)
    for fy in params.get('pmos_fin_y', []):
        ax.plot(-8, fy, '>', color='green', markersize=3)
    
    # Add device labels
    if params.get('nmos_fin_y'):
        nmos_cy = (params['nmos_fin_y'][0] + params['nmos_fin_y'][-1]) / 2
        ax.text(-15, nmos_cy, f"NMOS\n{params['nmos_nfin']}fin", fontsize=6,
                ha='center', va='center', rotation=90, color='blue')
    if params.get('pmos_fin_y'):
        pmos_cy = (params['pmos_fin_y'][0] + params['pmos_fin_y'][-1]) / 2
        ax.text(-15, pmos_cy, f"PMOS\n{params['pmos_nfin']}fin", fontsize=6,
                ha='center', va='center', rotation=90, color='red')


def generate_comparison_plot(orig_data: dict, target_data: dict, 
                             output_path: str):
    """Generate side-by-side comparison of original and target layouts."""
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 8))
    
    draw_layout(ax1, orig_data, 
                title=f"ORIGINAL (N={orig_data['params']['nmos_nfin']}fin, "
                      f"P={orig_data['params']['pmos_nfin']}fin)")
    draw_layout(ax2, target_data,
                title=f"TARGET (N={target_data['params']['nmos_nfin']}fin, "
                      f"P={target_data['params']['pmos_nfin']}fin)")
    
    # Add legend (shared)
    legend_elements = []
    for layer_name in DRAW_ORDER:
        if layer_name in ('BOUNDARY',):
            continue
        color = LAYER_COLORS[layer_name]
        legend_elements.append(
            patches.Patch(facecolor=(*color[:3], color[3]),
                         edgecolor=color[:3],
                         label=layer_name)
        )
    fig.legend(handles=legend_elements, loc='lower center', ncol=len(legend_elements),
               fontsize=8, framealpha=0.9)
    
    plt.suptitle('Dummy Inverter Layout - Fin Resize Comparison', 
                 fontsize=14, fontweight='bold')
    plt.tight_layout(rect=[0, 0.06, 1, 0.95])
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"Comparison plot saved: {output_path}")


def generate_detail_plot(layout_data: dict, output_path: str, title: str = ''):
    """Generate a single detailed layout view with annotations."""
    
    fig, ax = plt.subplots(1, 1, figsize=(10, 12))
    draw_layout(ax, layout_data, title=title, show_grid=True, show_labels=True)
    
    # Add legend
    legend_elements = []
    for layer_name in DRAW_ORDER:
        if layer_name in ('BOUNDARY',):
            continue
        color = LAYER_COLORS[layer_name]
        legend_elements.append(
            patches.Patch(facecolor=(*color[:3], color[3]),
                         edgecolor=color[:3],
                         label=layer_name)
        )
    ax.legend(handles=legend_elements, loc='upper right', fontsize=7)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"Detail plot saved: {output_path}")


if __name__ == '__main__':
    fixture_dir = os.path.join(os.path.dirname(__file__), '..', 'dummy', 'fixtures')
    
    with open(os.path.join(fixture_dir, 'buffer_original.json')) as f:
        orig = json.load(f)
    with open(os.path.join(fixture_dir, 'buffer_target.json')) as f:
        target = json.load(f)
    
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'dummy', 'fixtures')
    
    generate_comparison_plot(orig, target,
                            os.path.join(output_dir, 'layout_comparison.png'))
    generate_detail_plot(orig,
                        os.path.join(output_dir, 'layout_original_detail.png'),
                        title='Original Inverter (NMOS=5fin, PMOS=7fin)')
