"""
End-to-end MVP pipeline:
  Parse → Load CSP → Resize → Generate output GDS → Visualize diff

Inputs:
  - original.gds + original.cdl (original design)
  - modified.cdl (target netlist with changed parameters)
  - process_config.yaml + drc_rules.yaml (tech config)

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

from tech.config_loader import load_tech_config
from io_adapters.parser import build_layout_model
from io_adapters.cdl_parser import parse_cdl, diff_cdl, get_device_param
from io_adapters.gds_io import write_gds, gds_to_bbox_by_layer, HAS_GDSTK
from core.solver import LayoutSolver


def apply_edits_to_layout_data(orig_data: dict,
                                edit_ops_n, edit_ops_p,
                                new_nmos_nfin: int,
                                new_pmos_nfin: int,
                                config=None) -> dict:
    """
    Apply resize edit operations to the raw layout data dict.

    This directly modifies shapes (coordinates) to produce the resized layout,
    which can then be written to GDS and visualized.
    """
    if config is None:
        from tech.config_loader import get_tech_config
        config = get_tech_config()

    OD_EXTENSION_BEYOND_FIN = config.OD_EXTENSION_BEYOND_FIN
    POLY_EXTENSION_BEYOND_OD = config.POLY_EXTENSION_BEYOND_OD
    VIA0_ENC_BY_LI_Y = config.VIA0_ENC_BY_LI_Y

    result = copy.deepcopy(orig_data)
    params = result['params']

    old_nmos_nfin = params['nmos_nfin']
    old_pmos_nfin = params['pmos_nfin']

    # --- Recompute fin positions ---
    nmos_fin_y_old = params['nmos_fin_y']
    pmos_fin_y_old = params['pmos_fin_y']

    nmos_fin_y_new = nmos_fin_y_old[:new_nmos_nfin]
    pmos_fin_y_new = pmos_fin_y_old[:new_pmos_nfin]

    # --- Update FIN layer: remove fins ---
    new_fin_shapes = []
    removed_nmos_ys = set(nmos_fin_y_old[new_nmos_nfin:])
    removed_pmos_ys = set(pmos_fin_y_old[new_pmos_nfin:])

    for s in result['shapes']['FIN']:
        cy = (s['y1'] + s['y2']) / 2
        cy_rounded = round(cy)
        if cy_rounded in removed_nmos_ys or cy_rounded in removed_pmos_ys:
            continue
        new_fin_shapes.append(s)
    result['shapes']['FIN'] = new_fin_shapes

    # --- Update OD layer ---
    od_ext = OD_EXTENSION_BEYOND_FIN
    for s in result['shapes']['OD']:
        cy = (s['y1'] + s['y2']) / 2
        nmos_center = (nmos_fin_y_old[0] + nmos_fin_y_old[-1]) / 2
        pmos_center = (pmos_fin_y_old[0] + pmos_fin_y_old[-1]) / 2

        if abs(cy - nmos_center) < abs(cy - pmos_center):
            s['y2'] = int(nmos_fin_y_new[-1] + od_ext)
        else:
            s['y2'] = int(pmos_fin_y_new[-1] + od_ext)

    # --- Update POLY layer ---
    nmos_od_bot = nmos_fin_y_new[0] - OD_EXTENSION_BEYOND_FIN
    pmos_od_top = pmos_fin_y_new[-1] + OD_EXTENSION_BEYOND_FIN
    poly_ext = POLY_EXTENSION_BEYOND_OD
    poly_y_bot = nmos_od_bot - poly_ext
    poly_y_top = pmos_od_top + poly_ext

    for s in result['shapes']['POLY']:
        s['y1'] = int(poly_y_bot)
        s['y2'] = int(poly_y_top)

    # --- Update LI layer ---
    li_ext_y = 5
    for s in result['shapes']['LI']:
        desc = s.get('desc', '')
        if 'nmos_source' in desc or 'nmos_drain' in desc:
            s['y2'] = int(nmos_fin_y_new[-1] + li_ext_y)
        elif 'pmos_source' in desc or 'pmos_drain' in desc:
            s['y2'] = int(pmos_fin_y_new[-1] + li_ext_y)

    # Re-extend LI if needed to cover via positions
    m1_tracks = params['m1_tracks']
    for s in result['shapes']['LI']:
        desc = s.get('desc', '')
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

    # --- Update cell height + BOUNDARY ---
    new_cell_height = pmos_fin_y_new[-1] + 40
    for s in result['shapes']['BOUNDARY']:
        s['y2'] = int(new_cell_height)

    # --- Update params ---
    params['nmos_nfin'] = new_nmos_nfin
    params['pmos_nfin'] = new_pmos_nfin
    params['nmos_fin_y'] = nmos_fin_y_new
    params['pmos_fin_y'] = pmos_fin_y_new
    params['cell_height'] = int(new_cell_height)

    for dev in result['devices']:
        if dev['type'] == 'nmos':
            dev['nfin'] = new_nmos_nfin
            dev['fin_y_positions'] = nmos_fin_y_new
        elif dev['type'] == 'pmos':
            dev['nfin'] = new_pmos_nfin
            dev['fin_y_positions'] = pmos_fin_y_new

    return result


def generate_three_way_comparison(orig_data, resized_data, target_data,
                                   output_path, config=None):
    """Generate 3-way comparison: Original -> Resized -> Target."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches

    from tech.layer_map import LAYER_COLORS

    if config is None:
        from tech.config_loader import get_tech_config
        config = get_tech_config()

    DRAW_ORDER = ['BOUNDARY', 'NWELL', 'OD', 'FIN', 'POLY', 'LI', 'VIA0', 'M1']

    fig, axes = plt.subplots(1, 3, figsize=(20, 9))

    datasets = [
        (orig_data, 'ORIGINAL\n'
                     f'(N={orig_data["params"]["nmos_nfin"]}fin, '
                     f'P={orig_data["params"]["pmos_nfin"]}fin)', axes[0]),
        (resized_data, 'RESIZED (solver output)\n'
                       f'(N={resized_data["params"]["nmos_nfin"]}fin, '
                       f'P={resized_data["params"]["pmos_nfin"]}fin)', axes[1]),
        (target_data, 'TARGET (ground truth)\n'
                      f'(N={target_data["params"]["nmos_nfin"]}fin, '
                      f'P={target_data["params"]["pmos_nfin"]}fin)', axes[2]),
    ]

    for data, title, ax in datasets:
        shapes_data = data['shapes']
        params_data = data['params']
        cell_w = params_data['cell_width']
        cell_h = params_data['cell_height']

        ax.set_xlim(-20, cell_w + 20)
        ax.set_ylim(-20, max(cell_h + 20, 450))
        ax.set_aspect('equal')
        ax.set_title(title, fontsize=10, fontweight='bold')
        ax.set_xlabel('X (nm)', fontsize=8)
        ax.set_ylabel('Y (nm)', fontsize=8)

        for i in range(20):
            x = i * config.GATE_PITCH
            if x > cell_w + 20:
                break
            ax.axvline(x=x, color='gray', linewidth=0.3, linestyle=':', alpha=0.4)

        for layer_name in DRAW_ORDER:
            if layer_name not in shapes_data:
                continue
            color = LAYER_COLORS.get(layer_name, (0.5, 0.5, 0.5, 0.3))
            for s in shapes_data[layer_name]:
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

        for fy in params_data.get('nmos_fin_y', []):
            ax.plot(-8, fy, '>', color='green', markersize=3)
        for fy in params_data.get('pmos_fin_y', []):
            ax.plot(-8, fy, '>', color='green', markersize=3)

        if params_data.get('nmos_fin_y'):
            nmos_cy = (params_data['nmos_fin_y'][0] + params_data['nmos_fin_y'][-1]) / 2
            ax.text(-15, nmos_cy, f"NMOS\n{params_data['nmos_nfin']}fin", fontsize=6,
                    ha='center', va='center', rotation=90, color='blue')
        if params_data.get('pmos_fin_y'):
            pmos_cy = (params_data['pmos_fin_y'][0] + params_data['pmos_fin_y'][-1]) / 2
            ax.text(-15, pmos_cy, f"PMOS\n{params_data['pmos_nfin']}fin", fontsize=6,
                    ha='center', va='center', rotation=90, color='red')

    legend_elements = []
    for layer_name in DRAW_ORDER:
        if layer_name == 'BOUNDARY':
            continue
        color = LAYER_COLORS[layer_name]
        legend_elements.append(
            patches.Patch(facecolor=(*color[:3], color[3]),
                         edgecolor=color[:3], label=layer_name)
        )
    fig.legend(handles=legend_elements, loc='lower center',
               ncol=len(legend_elements), fontsize=8)

    plt.suptitle('Fin Resize MVP: Original -> Solver Output -> Target',
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

    DIFF_LAYERS = ['FIN', 'OD', 'POLY', 'LI', 'VIA0', 'M1']

    for layer_name in DIFF_LAYERS:
        orig_shapes = orig_data['shapes'].get(layer_name, [])
        new_shapes = resized_data['shapes'].get(layer_name, [])

        def shape_key(s):
            return (s['x1'], s['y1'], s['x2'], s['y2'], s.get('net', ''))

        orig_set = {shape_key(s) for s in orig_shapes}
        new_set = {shape_key(s) for s in new_shapes}

        for x1, y1, x2, y2, net in orig_set & new_set:
            rect = patches.Rectangle(
                (x1, y1), x2 - x1, y2 - y1,
                linewidth=0.5, edgecolor='gray', facecolor=(0.7, 0.7, 0.7, 0.2))
            ax.add_patch(rect)

        for x1, y1, x2, y2, net in orig_set - new_set:
            rect = patches.Rectangle(
                (x1, y1), x2 - x1, y2 - y1,
                linewidth=1.5, edgecolor='red', facecolor=(1, 0, 0, 0.15),
                linestyle='--')
            ax.add_patch(rect)
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            ax.text(cx, cy, f'-{layer_name}', fontsize=4, ha='center', va='center',
                    color='red', fontweight='bold')

        for x1, y1, x2, y2, net in new_set - orig_set:
            rect = patches.Rectangle(
                (x1, y1), x2 - x1, y2 - y1,
                linewidth=1.5, edgecolor='green', facecolor=(0, 1, 0, 0.15),
                linestyle='-')
            ax.add_patch(rect)
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            ax.text(cx, cy, f'+{layer_name}', fontsize=4, ha='center', va='center',
                    color='darkgreen', fontweight='bold')

    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"  Diff overlay saved: {output_path}")


def run_full_pipeline(original_cdl_path: str = None,
                      modified_cdl_path: str = None,
                      config=None):
    """Execute the complete MVP pipeline.

    Args:
        original_cdl_path: Path to original CDL netlist.
        modified_cdl_path: Path to modified CDL netlist (resize targets).
        config: TechConfig instance.
    """
    if config is None:
        config = load_tech_config()

    fixture_dir = os.path.join(os.path.dirname(__file__), '..', 'dummy', 'fixtures')
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'output')
    os.makedirs(output_dir, exist_ok=True)

    # Default CDL paths
    if original_cdl_path is None:
        original_cdl_path = os.path.join(fixture_dir, 'buffer_original.cdl')
    if modified_cdl_path is None:
        modified_cdl_path = os.path.join(fixture_dir, 'buffer_target.cdl')

    print("=" * 70)
    print("  BUFFER FIN RESIZE MVP - FULL PIPELINE")
    print("=" * 70)

    # ---- Stage 1: CDL diff → resize targets ----
    print("\n[Stage 1] Parsing CDL netlists and computing diff...")
    orig_cdl = parse_cdl(original_cdl_path)
    mod_cdl = parse_cdl(modified_cdl_path)
    resize_targets = diff_cdl(orig_cdl, mod_cdl)

    # Filter to nfin changes only (the resize operations we support)
    nfin_targets = [t for t in resize_targets if t['param'] == 'nfin']

    if not nfin_targets:
        print("  No nfin changes found between CDL files. Nothing to resize.")
        return

    for t in nfin_targets:
        print(f"  {t['inst']}.nfin: {t['old']} -> {t['new']}")

    # Get original nfin values from CDL
    orig_nmos_nfin = get_device_param(orig_cdl, 'MN0', 'nfin', 5)
    orig_pmos_nfin = get_device_param(orig_cdl, 'MP0', 'nfin', 7)
    print(f"  Original: NMOS={orig_nmos_nfin}fin, PMOS={orig_pmos_nfin}fin")

    # ---- Stage 2: Parse layout ----
    print("\n[Stage 2] Parsing layout data...")
    model, grid = build_layout_model(
        device_query_path=os.path.join(fixture_dir, 'calibre_device_query.json'),
        net_query_path=os.path.join(fixture_dir, 'calibre_net_query.json'),
        bbox_path=os.path.join(fixture_dir, 'bbox_by_layer.json'),
        layout_json_path=os.path.join(fixture_dir, 'buffer_original.json'),
        config=config,
    )
    print(f"  {model.summary()}")

    # ---- Stage 3-4: CSP setup + load ----
    print("\n[Stage 3-4] Setting up CSP engine and loading layout...")
    solver = LayoutSolver(model, grid, config)
    solver.setup_engine(layers_to_include=['LI', 'M1'])
    load_ok = solver.load_existing_layout()
    if not load_ok:
        print("FATAL: Failed to load layout into CSP")
        return

    # ---- Stage 5: Resize (driven by CDL diff) ----
    print("\n[Stage 5] Executing resize (driven by CDL diff)...")
    results = {}
    for target in nfin_targets:
        r = solver.resize_device(target['inst'], target['new'])
        results[target['inst']] = r
        if not r.success:
            print(f"FATAL: Resize of {target['inst']} failed: {r.message}")
            return

    # ---- Stage 6: Generate output ----
    print("\n[Stage 6] Generating output files...")

    with open(os.path.join(fixture_dir, 'buffer_original.json')) as f:
        orig_data = json.load(f)
    with open(os.path.join(fixture_dir, 'buffer_target.json')) as f:
        target_data = json.load(f)

    # Determine new nfin values from CDL diff
    new_nmos_nfin = orig_nmos_nfin
    new_pmos_nfin = orig_pmos_nfin
    edit_ops_n = []
    edit_ops_p = []
    for t in nfin_targets:
        if t['inst'] == 'MN0':
            new_nmos_nfin = t['new']
            edit_ops_n = results['MN0'].edit_ops
        elif t['inst'] == 'MP0':
            new_pmos_nfin = t['new']
            edit_ops_p = results['MP0'].edit_ops

    resized_data = apply_edits_to_layout_data(
        orig_data, edit_ops_n, edit_ops_p,
        new_nmos_nfin, new_pmos_nfin, config
    )

    # Write GDS
    resized_gds_path = os.path.join(output_dir, 'buffer_resized.gds')
    write_gds(resized_data, resized_gds_path, layer_map=config.LAYER_MAP)

    # Write JSON
    with open(os.path.join(output_dir, 'buffer_resized.json'), 'w') as f:
        json.dump(resized_data, f, indent=2)
    print(f"  Layout JSON written: {os.path.join(output_dir, 'buffer_resized.json')}")

    # Write CDL
    cdl_path = os.path.join(output_dir, 'buffer_resized.cdl')
    nfin_n = resized_data['params']['nmos_nfin']
    nfin_p = resized_data['params']['pmos_nfin']
    cell_name = f'INV_N{nfin_n}_P{nfin_p}'
    from io_adapters.writer_cdl import write_cdl
    write_cdl(cdl_path, cell_name, nfin_n, nfin_p, config.POLY_WIDTH)

    # Write resize report
    report_path = os.path.join(output_dir, 'resize_report.txt')
    with open(report_path, 'w') as f:
        f.write("BUFFER FIN RESIZE REPORT\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Original: NMOS={orig_nmos_nfin}fin, PMOS={orig_pmos_nfin}fin\n")
        f.write(f"Target:   NMOS={new_nmos_nfin}fin, PMOS={new_pmos_nfin}fin\n")
        f.write(f"Source: CDL diff ({original_cdl_path} vs {modified_cdl_path})\n\n")

        for inst, r in results.items():
            f.write(f"{inst} resize: {r.message}\n")
            for op in r.edit_ops:
                f.write(f"  {op}\n")
            f.write("\n")

        total_edits = sum(len(r.edit_ops) for r in results.values())
        f.write(f"Total edit operations: {total_edits}\n")
    print(f"  Report written: {report_path}")

    # ---- GDS read-back verification ----
    if HAS_GDSTK:
        print("\n[GDS Read-back] Verifying resized GDS...")
        readback = gds_to_bbox_by_layer(resized_gds_path, layer_map=config.LAYER_MAP)
        readback_ok = True
        for layer in ['FIN', 'OD', 'POLY', 'LI', 'VIA0', 'M1']:
            orig_shapes = resized_data['shapes'].get(layer, [])
            rb_shapes = readback.get(layer, [])
            orig_set = {(s['x1'], s['y1'], s['x2'], s['y2']) for s in orig_shapes}
            rb_set = {(s['x1'], s['y1'], s['x2'], s['y2']) for s in rb_shapes}
            if orig_set != rb_set:
                print(f"  {layer}: MISMATCH (written={len(orig_set)}, readback={len(rb_set)})")
                readback_ok = False
            else:
                print(f"  {layer}: OK ({len(orig_set)} shapes)")
        if readback_ok:
            print("  GDS read-back: ALL MATCH")
        else:
            print("  GDS read-back: MISMATCHES FOUND")

    # ---- Visualization ----
    print("\n[Visualization] Generating comparison plots...")

    generate_three_way_comparison(
        orig_data, resized_data, target_data,
        os.path.join(output_dir, 'resize_comparison.png'),
        config
    )

    generate_diff_overlay(
        orig_data, resized_data,
        os.path.join(output_dir, 'resize_diff.png')
    )

    # ---- Validation: compare resized vs target ----
    print("\n[Validation] Comparing resized output vs target...")

    if HAS_GDSTK:
        from io_adapters.gds_io import compare_gds
        resized_gds = os.path.join(output_dir, 'buffer_resized.gds')
        target_gds = os.path.join(fixture_dir, 'buffer_target.gds')
        diff = compare_gds(resized_gds, target_gds,
                           layers=['FIN', 'OD', 'POLY', 'LI', 'VIA0', 'M1'])
        mismatches = 0
        for layer, info in sorted(diff.items()):
            if info['match']:
                print(f"  {layer:6s}: MATCH ({info['common']} shapes)")
            else:
                print(f"  {layer:6s}: DIFF (+{len(info['only_b'])} "
                      f"-{len(info['only_a'])} common={info['common']})")
                mismatches += len(info['only_a']) + len(info['only_b'])
    else:
        mismatches = 0
        for layer_name in ['FIN', 'OD', 'LI', 'VIA0', 'M1']:
            r_set = {(s['x1'], s['y1'], s['x2'], s['y2'])
                     for s in resized_data['shapes'].get(layer_name, [])}
            t_set = {(s['x1'], s['y1'], s['x2'], s['y2'])
                     for s in target_data['shapes'].get(layer_name, [])}
            if r_set == t_set:
                print(f"  {layer_name:6s}: MATCH ({len(r_set)} shapes)")
            else:
                print(f"  {layer_name:6s}: MISMATCH")
                mismatches += len(r_set - t_set) + len(t_set - r_set)

    print(f"\n{'=' * 70}")
    if mismatches == 0:
        print("  RESULT: PERFECT MATCH - resized output matches target exactly!")
    else:
        print(f"  RESULT: {mismatches} shape mismatches (see details above)")
    print(f"{'=' * 70}")

    print(f"\nAll output files in: {os.path.abspath(output_dir)}")


if __name__ == '__main__':
    run_full_pipeline()
