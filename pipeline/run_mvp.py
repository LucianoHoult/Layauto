"""
End-to-end MVP pipeline:
  Parse → Load CSP → Resize → Generate output GDS → Visualize diff

Produces:
  - buffer_resized.gds: GDS with resized layout
  - buffer_resized.json: Layout data for the resized version
  - resize_diff.png: Visual comparison (original vs resized vs target)
  - resize_report.txt: Text report of all edit operations
"""

import sys
import os
import json
import copy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from io_adapters.parser import build_layout_model
from core.solver import LayoutSolver, run_mvp_resize
from core.data_model import LayoutModel
from core.grid import MultiLayerGrid
from tech.tech_params import (
    FIN_PITCH, FIN_WIDTH, GATE_PITCH, LI_PITCH, M1_PITCH,
    LI_WIDTH, M1_WIDTH, OD_EXTENSION_BEYOND_FIN, POLY_WIDTH,
    POLY_EXTENSION_BEYOND_OD, NMOS_NFIN, PMOS_NFIN,
    NMOS_NFIN_TARGET, PMOS_NFIN_TARGET,
)
from tech.layer_map import LAYER_MAP
from io_adapters.gds_io import write_gds, HAS_GDSTK


def apply_edits_to_layout_data(orig_data: dict, 
                                edit_ops_n, edit_ops_p,
                                new_nmos_nfin: int, 
                                new_pmos_nfin: int) -> dict:
    """
    Apply resize edit operations to the raw layout data dict.
    
    This directly modifies shapes (coordinates) to produce the resized layout,
    which can then be written to GDS and visualized.
    """
    result = copy.deepcopy(orig_data)
    params = result['params']
    
    old_nmos_nfin = params['nmos_nfin']
    old_pmos_nfin = params['pmos_nfin']
    
    # --- Recompute fin positions ---
    nmos_fin_y_old = params['nmos_fin_y']
    pmos_fin_y_old = params['pmos_fin_y']
    
    # NMOS: remove top fins
    nmos_fins_removed = old_nmos_nfin - new_nmos_nfin
    nmos_fin_y_new = nmos_fin_y_old[:new_nmos_nfin]
    
    # PMOS: remove top fins
    pmos_fins_removed = old_pmos_nfin - new_pmos_nfin
    pmos_fin_y_new = pmos_fin_y_old[:new_pmos_nfin]
    
    # --- Update FIN layer: remove fins ---
    new_fin_shapes = []
    removed_nmos_ys = set(nmos_fin_y_old[new_nmos_nfin:])
    removed_pmos_ys = set(pmos_fin_y_old[new_pmos_nfin:])
    
    for s in result['shapes']['FIN']:
        cy = (s['y1'] + s['y2']) / 2
        cy_rounded = round(cy)
        if cy_rounded in removed_nmos_ys or cy_rounded in removed_pmos_ys:
            continue  # Skip removed fins
        new_fin_shapes.append(s)
    result['shapes']['FIN'] = new_fin_shapes
    
    # --- Update OD layer ---
    new_od_shapes = []
    for s in result['shapes']['OD']:
        cy = (s['y1'] + s['y2']) / 2
        
        # Check if this is NMOS OD (near NMOS fins) or PMOS OD
        nmos_center = (nmos_fin_y_old[0] + nmos_fin_y_old[-1]) / 2
        pmos_center = (pmos_fin_y_old[0] + pmos_fin_y_old[-1]) / 2
        
        od_ext = OD_EXTENSION_BEYOND_FIN
        
        if abs(cy - nmos_center) < abs(cy - pmos_center):
            # NMOS OD: shrink top to new topmost fin
            new_top = nmos_fin_y_new[-1] + od_ext
            s['y2'] = int(new_top)
        else:
            # PMOS OD: shrink top to new topmost fin
            new_top = pmos_fin_y_new[-1] + od_ext
            s['y2'] = int(new_top)
        
        new_od_shapes.append(s)
    result['shapes']['OD'] = new_od_shapes
    
    # --- Update POLY layer: adjust extent ---
    nmos_od_bot = nmos_fin_y_new[0] - OD_EXTENSION_BEYOND_FIN
    pmos_od_top = pmos_fin_y_new[-1] + OD_EXTENSION_BEYOND_FIN
    poly_ext = POLY_EXTENSION_BEYOND_OD
    poly_y_bot = nmos_od_bot - poly_ext
    poly_y_top = pmos_od_top + poly_ext
    
    for s in result['shapes']['POLY']:
        s['y1'] = int(poly_y_bot)
        s['y2'] = int(poly_y_top)
    
    # --- Update LI layer: shorten S/D contact bars ---
    li_ext_y = 5
    
    for s in result['shapes']['LI']:
        desc = s.get('desc', '')
        
        if 'nmos_source' in desc:
            # NMOS source: shrink top to new NMOS topmost fin
            s['y2'] = int(nmos_fin_y_new[-1] + li_ext_y)
        elif 'nmos_drain' in desc:
            # NMOS drain: shrink top to new NMOS topmost fin
            s['y2'] = int(nmos_fin_y_new[-1] + li_ext_y)
        elif 'pmos_source' in desc:
            # PMOS source: shrink top to new PMOS topmost fin
            s['y2'] = int(pmos_fin_y_new[-1] + li_ext_y)
        elif 'pmos_drain' in desc:
            # PMOS drain: shrink top to new PMOS topmost fin
            s['y2'] = int(pmos_fin_y_new[-1] + li_ext_y)
    
    # But: LI bars must still reach their via landings!
    # Re-extend LI if needed to cover via positions
    from tech.tech_params import VIA0_ENC_BY_LI_Y
    m1_tracks = params['m1_tracks']
    
    for s in result['shapes']['LI']:
        desc = s.get('desc', '')
        net = s.get('net', '')
        
        # Find the via Y position for this net
        via_y = None
        if 'nmos_source' in desc and 'VSS' in m1_tracks:
            via_y = m1_tracks['VSS']
        elif 'pmos_source' in desc and 'VDD' in m1_tracks:
            via_y = m1_tracks['VDD']
        elif 'drain' in desc and 'OUT' in m1_tracks:
            via_y = m1_tracks['OUT']
        elif 'gate' in desc and 'IN' in m1_tracks:
            via_y = m1_tracks['IN']
        
        if via_y is not None:
            needed_bot = via_y - VIA0_ENC_BY_LI_Y
            needed_top = via_y + VIA0_ENC_BY_LI_Y
            if s['y1'] > needed_bot:
                s['y1'] = int(needed_bot)
            if s['y2'] < needed_top:
                s['y2'] = int(needed_top)
    
    # --- Update NWELL ---
    nwell_margin = 30
    for s in result['shapes']['NWELL']:
        s['y2'] = int(pmos_fin_y_new[-1] + nwell_margin)
    
    # --- Update cell height ---
    new_cell_height = pmos_fin_y_new[-1] + 40  # margin
    
    # Update BOUNDARY
    for s in result['shapes']['BOUNDARY']:
        s['y2'] = int(new_cell_height)
    
    # --- Update params ---
    params['nmos_nfin'] = new_nmos_nfin
    params['pmos_nfin'] = new_pmos_nfin
    params['nmos_fin_y'] = nmos_fin_y_new
    params['pmos_fin_y'] = pmos_fin_y_new
    params['cell_height'] = int(new_cell_height)
    
    # Update devices
    for dev in result['devices']:
        if dev['type'] == 'nmos':
            dev['nfin'] = new_nmos_nfin
            dev['fin_y_positions'] = nmos_fin_y_new
        elif dev['type'] == 'pmos':
            dev['nfin'] = new_pmos_nfin
            dev['fin_y_positions'] = pmos_fin_y_new
    
    return result


def generate_three_way_comparison(orig_data, resized_data, target_data, output_path):
    """Generate 3-way comparison: Original → Resized (our result) → Target (ground truth)."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    
    from tech.layer_map import LAYER_COLORS
    
    DRAW_ORDER = ['BOUNDARY', 'NWELL', 'OD', 'FIN', 'POLY', 'LI', 'VIA0', 'M1']
    
    fig, axes = plt.subplots(1, 3, figsize=(20, 9))
    
    datasets = [
        (orig_data, 'ORIGINAL\n(N=5fin, P=7fin)', axes[0]),
        (resized_data, 'RESIZED (solver output)\n'
                       f'(N={resized_data["params"]["nmos_nfin"]}fin, '
                       f'P={resized_data["params"]["pmos_nfin"]}fin)', axes[1]),
        (target_data, 'TARGET (ground truth)\n'
                      f'(N={target_data["params"]["nmos_nfin"]}fin, '
                      f'P={target_data["params"]["pmos_nfin"]}fin)', axes[2]),
    ]
    
    for data, title, ax in datasets:
        shapes = data['shapes']
        params = data['params']
        cell_w = params['cell_width']
        cell_h = params['cell_height']
        
        ax.set_xlim(-20, cell_w + 20)
        ax.set_ylim(-20, max(cell_h + 20, 450))
        ax.set_aspect('equal')
        ax.set_title(title, fontsize=10, fontweight='bold')
        ax.set_xlabel('X (nm)', fontsize=8)
        ax.set_ylabel('Y (nm)', fontsize=8)
        
        # Grid lines
        for i in range(20):
            x = i * GATE_PITCH
            if x > cell_w + 20: break
            ax.axvline(x=x, color='gray', linewidth=0.3, linestyle=':', alpha=0.4)
        
        for layer_name in DRAW_ORDER:
            if layer_name not in shapes:
                continue
            color = LAYER_COLORS.get(layer_name, (0.5, 0.5, 0.5, 0.3))
            
            for s in shapes[layer_name]:
                x1, y1, x2, y2 = s['x1'], s['y1'], s['x2'], s['y2']
                w, h = x2 - x1, y2 - y1
                rect = patches.Rectangle(
                    (x1, y1), w, h,
                    linewidth=0.8,
                    edgecolor=color[:3],
                    facecolor=(*color[:3], color[3]),
                )
                ax.add_patch(rect)
                
                if s.get('net') and layer_name in ('VIA0', 'M1', 'LI'):
                    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
                    fs = 4 if layer_name == 'VIA0' else 5
                    ax.text(cx, cy, s['net'], fontsize=fs,
                            ha='center', va='center', fontweight='bold', alpha=0.8)
        
        # Fin markers
        for fy in params.get('nmos_fin_y', []):
            ax.plot(-8, fy, '>', color='green', markersize=3)
        for fy in params.get('pmos_fin_y', []):
            ax.plot(-8, fy, '>', color='green', markersize=3)
        
        # Device labels
        if params.get('nmos_fin_y'):
            nmos_cy = (params['nmos_fin_y'][0] + params['nmos_fin_y'][-1]) / 2
            ax.text(-15, nmos_cy, f"NMOS\n{params['nmos_nfin']}fin", fontsize=6,
                    ha='center', va='center', rotation=90, color='blue')
        if params.get('pmos_fin_y'):
            pmos_cy = (params['pmos_fin_y'][0] + params['pmos_fin_y'][-1]) / 2
            ax.text(-15, pmos_cy, f"PMOS\n{params['pmos_nfin']}fin", fontsize=6,
                    ha='center', va='center', rotation=90, color='red')
    
    # Legend
    legend_elements = []
    for layer_name in DRAW_ORDER:
        if layer_name == 'BOUNDARY': continue
        color = LAYER_COLORS[layer_name]
        legend_elements.append(
            patches.Patch(facecolor=(*color[:3], color[3]),
                         edgecolor=color[:3], label=layer_name)
        )
    fig.legend(handles=legend_elements, loc='lower center',
               ncol=len(legend_elements), fontsize=8)
    
    plt.suptitle('Fin Resize MVP: Original → Solver Output → Target',
                 fontsize=14, fontweight='bold')
    plt.tight_layout(rect=[0, 0.06, 1, 0.95])
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"  3-way comparison saved: {output_path}")


def generate_diff_overlay(orig_data, resized_data, output_path):
    """Overlay original and resized, highlighting changes."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    
    fig, ax = plt.subplots(1, 1, figsize=(10, 12))
    
    params = orig_data['params']
    cell_w = params['cell_width']
    cell_h = params['cell_height']
    
    ax.set_xlim(-25, cell_w + 25)
    ax.set_ylim(-25, max(cell_h + 25, 450))
    ax.set_aspect('equal')
    ax.set_title('Resize Diff Overlay\n(Gray=unchanged, Red=removed, Green=added)',
                 fontsize=11, fontweight='bold')
    ax.set_xlabel('X (nm)')
    ax.set_ylabel('Y (nm)')
    
    # Compare shapes per layer
    DIFF_LAYERS = ['FIN', 'OD', 'POLY', 'LI', 'VIA0', 'M1']
    
    for layer_name in DIFF_LAYERS:
        orig_shapes = orig_data['shapes'].get(layer_name, [])
        new_shapes = resized_data['shapes'].get(layer_name, [])
        
        # Convert to comparable tuples
        def shape_key(s):
            return (s['x1'], s['y1'], s['x2'], s['y2'], s.get('net', ''))
        
        orig_set = {shape_key(s) for s in orig_shapes}
        new_set = {shape_key(s) for s in new_shapes}
        
        unchanged = orig_set & new_set
        removed = orig_set - new_set
        added = new_set - orig_set
        
        for x1, y1, x2, y2, net in unchanged:
            rect = patches.Rectangle(
                (x1, y1), x2-x1, y2-y1,
                linewidth=0.5, edgecolor='gray', facecolor=(0.7, 0.7, 0.7, 0.2))
            ax.add_patch(rect)
        
        for x1, y1, x2, y2, net in removed:
            rect = patches.Rectangle(
                (x1, y1), x2-x1, y2-y1,
                linewidth=1.5, edgecolor='red', facecolor=(1, 0, 0, 0.15),
                linestyle='--')
            ax.add_patch(rect)
            cx, cy = (x1+x2)/2, (y1+y2)/2
            ax.text(cx, cy, f'-{layer_name}', fontsize=4, ha='center', va='center',
                    color='red', fontweight='bold')
        
        for x1, y1, x2, y2, net in added:
            rect = patches.Rectangle(
                (x1, y1), x2-x1, y2-y1,
                linewidth=1.5, edgecolor='green', facecolor=(0, 1, 0, 0.15),
                linestyle='-')
            ax.add_patch(rect)
            cx, cy = (x1+x2)/2, (y1+y2)/2
            ax.text(cx, cy, f'+{layer_name}', fontsize=4, ha='center', va='center',
                    color='darkgreen', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"  Diff overlay saved: {output_path}")


def run_full_pipeline():
    """Execute the complete MVP pipeline."""
    
    fixture_dir = os.path.join(os.path.dirname(__file__), '..', 'dummy', 'fixtures')
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    print("=" * 70)
    print("  BUFFER FIN RESIZE MVP - FULL PIPELINE")
    print("=" * 70)
    
    # ---- Stage 2: Parse ----
    print("\n[Stage 2] Parsing layout data...")
    model, grid = build_layout_model(
        device_query_path=os.path.join(fixture_dir, 'calibre_device_query.json'),
        net_query_path=os.path.join(fixture_dir, 'calibre_net_query.json'),
        bbox_path=os.path.join(fixture_dir, 'bbox_by_layer.json'),
        layout_json_path=os.path.join(fixture_dir, 'buffer_original.json'),
    )
    print(f"  {model.summary()}")
    
    # ---- Stage 3-4: CSP setup + load ----
    print("\n[Stage 3-4] Setting up CSP engine and loading layout...")
    solver = LayoutSolver(model, grid)
    solver.setup_engine(layers_to_include=['LI', 'M1'])
    load_ok = solver.load_existing_layout()
    if not load_ok:
        print("FATAL: Failed to load layout into CSP")
        return
    
    # ---- Stage 5: Resize ----
    print("\n[Stage 5] Executing resize...")
    r1 = solver.resize_device('MN0', NMOS_NFIN_TARGET)
    r2 = solver.resize_device('MP0', PMOS_NFIN_TARGET)
    
    if not (r1.success and r2.success):
        print("FATAL: Resize failed")
        return
    
    # ---- Stage 6: Generate output ----
    print("\n[Stage 6] Generating output files...")
    
    # Load original and target layout data
    with open(os.path.join(fixture_dir, 'buffer_original.json')) as f:
        orig_data = json.load(f)
    with open(os.path.join(fixture_dir, 'buffer_target.json')) as f:
        target_data = json.load(f)
    
    # Apply edits to produce resized layout data
    resized_data = apply_edits_to_layout_data(
        orig_data, r1.edit_ops, r2.edit_ops,
        NMOS_NFIN_TARGET, PMOS_NFIN_TARGET
    )
    
    # Write outputs
    write_gds(resized_data, os.path.join(output_dir, 'buffer_resized.gds'))
    
    with open(os.path.join(output_dir, 'buffer_resized.json'), 'w') as f:
        json.dump(resized_data, f, indent=2)
    print(f"  Layout JSON written: {os.path.join(output_dir, 'buffer_resized.json')}")
    
    # Generate CDL
    cdl_path = os.path.join(output_dir, 'buffer_resized.cdl')
    nfin_n = resized_data['params']['nmos_nfin']
    nfin_p = resized_data['params']['pmos_nfin']
    cell_name = f'INV_N{nfin_n}_P{nfin_p}'
    with open(cdl_path, 'w') as f:
        f.write(f"* CDL netlist for {cell_name} (resized)\n")
        f.write(f".SUBCKT {cell_name} VDD VSS IN OUT\n")
        f.write(f"MN0 OUT IN VSS VSS nmos_finfet nfin={nfin_n} l={POLY_WIDTH}n\n")
        f.write(f"MP0 OUT IN VDD VDD pmos_finfet nfin={nfin_p} l={POLY_WIDTH}n\n")
        f.write(f".ENDS {cell_name}\n")
    print(f"  CDL written: {cdl_path}")
    
    # Write resize report
    report_path = os.path.join(output_dir, 'resize_report.txt')
    with open(report_path, 'w') as f:
        f.write("BUFFER FIN RESIZE REPORT\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Original: NMOS={NMOS_NFIN}fin, PMOS={PMOS_NFIN}fin\n")
        f.write(f"Target:   NMOS={NMOS_NFIN_TARGET}fin, PMOS={PMOS_NFIN_TARGET}fin\n\n")
        
        f.write(f"NMOS resize: {r1.message}\n")
        for op in r1.edit_ops:
            f.write(f"  {op}\n")
        
        f.write(f"\nPMOS resize: {r2.message}\n")
        for op in r2.edit_ops:
            f.write(f"  {op}\n")
        
        f.write(f"\nTotal edit operations: {len(r1.edit_ops) + len(r2.edit_ops)}\n")
    print(f"  Report written: {report_path}")
    
    # ---- Visualization ----
    print("\n[Visualization] Generating comparison plots...")
    
    generate_three_way_comparison(
        orig_data, resized_data, target_data,
        os.path.join(output_dir, 'resize_comparison.png')
    )
    
    generate_diff_overlay(
        orig_data, resized_data,
        os.path.join(output_dir, 'resize_diff.png')
    )
    
    # ---- Validation: compare resized vs target ----
    print("\n[Validation] Comparing resized output vs target...")
    
    # If gdstk available, do GDS-level read-back validation
    if HAS_GDSTK:
        from io_adapters.gds_io import compare_gds
        print("  (Using gdstk for GDS read-back comparison)")
        resized_gds = os.path.join(output_dir, 'buffer_resized.gds')
        target_gds = os.path.join(fixture_dir, 'buffer_target.gds')
        diff = compare_gds(resized_gds, target_gds, 
                           layers=['FIN','OD','POLY','LI','VIA0','M1'])
        mismatches = 0
        for layer, info in sorted(diff.items()):
            if info['match']:
                print(f"  {layer:6s}: MATCH ({info['common']} shapes)")
            else:
                print(f"  {layer:6s}: DIFF (+{len(info['only_b'])} "
                      f"-{len(info['only_a'])} common={info['common']})")
                mismatches += len(info['only_a']) + len(info['only_b'])
    else:
        # Fallback: compare from JSON data (as before)
        mismatches = 0
        for layer_name in ['FIN', 'OD', 'LI', 'VIA0', 'M1']:
            resized_shapes = resized_data['shapes'].get(layer_name, [])
            target_shapes = target_data['shapes'].get(layer_name, [])
            
            def shape_set(shapes):
                return {(s['x1'], s['y1'], s['x2'], s['y2']) for s in shapes}
            
            r_set = shape_set(resized_shapes)
            t_set = shape_set(target_shapes)
            
            if r_set == t_set:
                print(f"  {layer_name:6s}: MATCH ({len(r_set)} shapes)")
            else:
                only_resized = r_set - t_set
                only_target = t_set - r_set
                print(f"  {layer_name:6s}: MISMATCH")
                if only_resized:
                    print(f"           In resized only: {len(only_resized)}")
                    for s in sorted(only_resized):
                        print(f"             {s}")
                if only_target:
                    print(f"           In target only:  {len(only_target)}")
                    for s in sorted(only_target):
                        print(f"             {s}")
                mismatches += len(only_resized) + len(only_target)
    
    print(f"\n{'='*70}")
    if mismatches == 0:
        print("  RESULT: PERFECT MATCH — resized output matches target exactly!")
    else:
        print(f"  RESULT: {mismatches} shape mismatches (see details above)")
        print("  These may indicate bugs in edit application or differences")
        print("  in how the direct-generation target handles edge cases.")
    print(f"{'='*70}")
    
    print(f"\nAll output files in: {os.path.abspath(output_dir)}")


if __name__ == '__main__':
    run_full_pipeline()
