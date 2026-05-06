"""
End-to-end MVP pipeline:
  Parse → Load CSP → Resize → Generate output GDS → Visualize diff

Inputs (composed via tech/site_config.yaml):
  - original.cdl + modified.cdl (CDL diff drives resize targets)
  - calibre_device_query.json + calibre_net_query.json + bbox_by_layer.json
  - tech/drc_rules.yaml + tech/layer_map.yaml (tech bundle)

Produces:
  - buffer_resized.gds: GDS with resized layout
  - buffer_resized.json: Layout data for the resized version
  - resize_diff.png: Visual comparison (original vs resized vs target)
  - resize_report.txt: Text report of all edit operations

Usage:
  # default site_config (tech/site_config.yaml)
  python3 pipeline/run_mvp.py

  # custom site_config
  python3 pipeline/run_mvp.py --config /path/to/my_site.yaml
"""

import argparse
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tech.config_loader import (
    load_tech_config, load_tech_config_from_site, load_site_config,
)
from io_adapters.parser import build_layout_model
from io_adapters.cdl_parser import parse_cdl, diff_cdl, get_device_param
from io_adapters.gds_io import write_gds, gds_to_bbox_by_layer, HAS_GDSTK
from core.solver import LayoutSolver
from core.decoder import WritebackDecoder
from core.drc_derivator import DRCDerivator


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


def _default_site_config_path() -> str:
    return os.path.join(
        os.path.dirname(__file__), '..', 'tech', 'site_config.yaml'
    )


def run_full_pipeline(site_config_path: str = None,
                      config=None):
    """Execute the complete MVP pipeline.

    Args:
        site_config_path: Path to a site_config.yaml that lists
            tech sources (drc_rules, layer_map) and run inputs/outputs.
            If None, uses ``tech/site_config.yaml`` next to the repo.
        config: Pre-loaded TechConfig (skips tech reload). Useful for
            tests that already have a config in hand.
    """
    if site_config_path is None:
        site_config_path = _default_site_config_path()

    site = load_site_config(site_config_path)

    if config is None:
        config = load_tech_config_from_site(site_config_path)

    inputs = site.get('inputs', {})
    output_dir = site.get('output', {}).get('dir')
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), '..', 'output')
    os.makedirs(output_dir, exist_ok=True)

    original_cdl_path = inputs.get('original_cdl')
    modified_cdl_path = inputs.get('modified_cdl')
    device_query_path = inputs.get('device_query')
    net_query_path    = inputs.get('net_query')
    bbox_path         = inputs.get('bbox_by_layer')
    layout_json_path  = inputs.get('layout_json')
    target_json_path  = inputs.get('target_json')
    target_gds_path   = inputs.get('target_gds')

    print("=" * 70)
    print("  BUFFER FIN RESIZE MVP - FULL PIPELINE")
    print(f"  site_config: {site_config_path}")
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
        device_query_path=device_query_path,
        net_query_path=net_query_path,
        bbox_path=bbox_path,
        layout_json_path=layout_json_path,
        config=config,
    )
    print(f"  {model.summary()}")

    # ---- Stage 3-4: CSP setup + load ----
    print("\n[Stage 3-4] Setting up CSP engine and loading layout...")
    solver = LayoutSolver(model, grid, config)
    # M4e: ``setup_engine`` now also lifts OD/VIA0 into CSP when the
    # parser populated their B-tier cell-grid. ``load_b_tier_cells_into_engine``
    # follows ``load_existing_layout`` to seed the new engine cells from
    # the M4c parser stamps.
    solver.setup_engine(layers_to_include=['LI', 'M1'])
    load_ok = solver.load_existing_layout()
    if not load_ok:
        print("FATAL: Failed to load layout into CSP")
        return
    n_b_tier = solver.load_b_tier_cells_into_engine()
    if n_b_tier:
        print(f"  Loaded {n_b_tier} B-tier cell assignments into CSP")
    # M3: project unannotated GDS shapes into CSP as BLOCKAGE so they
    # obstruct any subsequent propose_assign rather than being silently
    # overwritten. No-op for the MVP fixture (zero unannotated LI/M1
    # shapes), but the seam exists for hand-edited / filler-bearing
    # production layouts.
    blockage_stats = solver.project_unannotated_blockages()
    if blockage_stats:
        print(f"  Unannotated blockage projection: {blockage_stats}")

    # ---- Stage 5: Resize (driven by CDL diff via pick_macro) ----
    # M6b: route CDL deltas through ``core/macros/pick_macro.py`` so the
    # L4 ``diff_cdl → pick_macro → apply`` pattern from
    # ``docs/architecture_roadmap.md`` §C is wired through. The dispatch
    # table currently routes only ``nfin`` parameter changes to
    # ``device_resize``; layout-side intent (share/split/cut) is exposed
    # as importable Python API and not auto-invoked from CDL.
    print("\n[Stage 5] Executing resize (driven by CDL diff via pick_macro)...")
    from core.macros import pick_macros
    macro_calls = pick_macros(nfin_targets, model=model)
    results = {}
    for call in macro_calls:
        print(f"  dispatch: {call}")
        r = call.execute(solver)
        results[call.diff['inst']] = r
        if not r.success:
            print(f"FATAL: {call} failed: {r.message}")
            return

    # ---- Stage 6: Generate output ----
    print("\n[Stage 6] Generating output files...")

    with open(layout_json_path) as f:
        orig_data = json.load(f)
    with open(target_json_path) as f:
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

    # M5: run the C1 derivator after the L3 macro commits. The derivator
    # walks model.shape_pool for NWELL / BOUNDARY shapes and emits
    # modify_shape EditOps the decoder's Phase 1 applies alongside
    # the macro's FIN / OD / LI / POLY ops. Replaces the decoder's
    # transitional Phase 2 ``_derive_*`` helpers.
    nmos_fin_y_new = orig_data['params']['nmos_fin_y'][:new_nmos_nfin]
    pmos_fin_y_new = orig_data['params']['pmos_fin_y'][:new_pmos_nfin]
    derivator = DRCDerivator(model, grid, config)
    edit_ops_c1 = derivator.derive_c1(nmos_fin_y_new, pmos_fin_y_new)

    decoder = WritebackDecoder(grid, config)
    resized_data = decoder.apply(
        orig_data, edit_ops_n + edit_ops_p + edit_ops_c1,
        new_nmos_nfin, new_pmos_nfin,
        model=model,
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

    # M3: emit per-layer LVS annotation coverage report. Helps spot the
    # parser-inversion failure mode: a production GDS where most LI/M1
    # shapes are unannotated would surface here as low coverage and
    # feed straight into the BLOCKAGE projection budget.
    coverage = model.annotation_coverage()
    coverage_path = os.path.join(output_dir, 'annotation_coverage.txt')
    with open(coverage_path, 'w') as f:
        f.write("LVS ANNOTATION COVERAGE REPORT\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"{'Layer':<10} {'Total':>6} {'Annotated':>10} {'Unannotated':>12}\n")
        f.write("-" * 50 + "\n")
        for layer in sorted(coverage):
            s = coverage[layer]
            f.write(f"{layer:<10} {s['total']:>6} {s['annotated']:>10} {s['unannotated']:>12}\n")
        total = sum(s['total'] for s in coverage.values())
        ann = sum(s['annotated'] for s in coverage.values())
        unann = sum(s['unannotated'] for s in coverage.values())
        f.write("-" * 50 + "\n")
        f.write(f"{'TOTAL':<10} {total:>6} {ann:>10} {unann:>12}\n")
    print(f"  Coverage report written: {coverage_path}")

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

    if HAS_GDSTK and target_gds_path and os.path.exists(target_gds_path):
        from io_adapters.gds_io import compare_gds
        resized_gds = os.path.join(output_dir, 'buffer_resized.gds')
        diff = compare_gds(resized_gds, target_gds_path,
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


def _build_arg_parser():
    p = argparse.ArgumentParser(
        description='Buffer fin-resize MVP pipeline.'
    )
    p.add_argument(
        '--config', '-c', dest='site_config', default=None,
        help='Path to site_config.yaml (default: tech/site_config.yaml)',
    )
    return p


if __name__ == '__main__':
    args = _build_arg_parser().parse_args()
    run_full_pipeline(site_config_path=args.site_config)
