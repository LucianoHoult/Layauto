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
from pipeline.debug import DebugSession


def _default_site_config_path() -> str:
    return os.path.join(
        os.path.dirname(__file__), '..', 'tech', 'site_config.yaml'
    )


def run_full_pipeline(site_config_path: str = None,
                      config=None,
                      lvs_mode: str = None,
                      debug: bool = False,
                      pause: bool = True):
    """Execute the complete MVP pipeline.

    Args:
        site_config_path: Path to a site_config.yaml that lists
            tech sources (drc_rules, layer_map) and run inputs/outputs.
            If None, uses ``tech/site_config.yaml`` next to the repo.
        config: Pre-loaded TechConfig (skips tech reload). Useful for
            tests that already have a config in hand.
        lvs_mode: Override ``site_config.calibre.mode`` ('dummy' or
            'calibre'). When None, the value from site_config is used.
        debug: When True, after each pipeline stage list newly written
            files under output_dir and (if pause and stdin is a TTY)
            wait for a keypress before the next stage starts.
        pause: When False, debug mode still prints the per-stage file
            listing but never pauses (useful for one-shot inspection
            of intermediates without ten Enter-presses).
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

    dbg = DebugSession(output_dir, enabled=debug, pause=pause)

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
    with dbg.stage("1", "CDL diff -> resize targets"):
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

    # ---- Stage 1.5: LVS extract (iXref + nXref + NET NAMES middles) ----
    # First pre-Stage-2 step that touches Calibre as a tool. In
    # mode='dummy', pre-staged iXref / nXref / NET-NAMES fixtures are
    # copied into the run-output paths; in mode='calibre',
    # `calibre -query <svdb_dir>` is invoked with `INSTANCE XREF
    # WRITE`, `NET XREF WRITE`, and `NET NAMES` streamed over stdin.
    # Either way each file is parsed and a YAML middle file is
    # written; the parsed dicts are "saved for later use" — Stage 2
    # does not consume them today (M7 will).
    from io_adapters.calibre_query import (
        extract_ixref, write_ixref_yaml,
        extract_net_xref, write_net_xref_yaml,
        extract_device_info, write_device_info_yaml,
        extract_net_shapes, write_net_shapes_yaml,
    )
    calibre_cfg = site.get('calibre', {}) or {}
    effective_lvs_mode = lvs_mode or calibre_cfg.get('mode') or 'dummy'

    ixref_temp_path = (calibre_cfg.get('ixref_temp')
                       or os.path.join(output_dir, 'iXref.temp'))
    nxref_temp_path = (calibre_cfg.get('nxref_temp')
                       or os.path.join(output_dir, 'nXref.temp'))
    net_names_path  = (calibre_cfg.get('net_names_txt')
                       or os.path.join(output_dir, 'net_names.txt'))
    ixref_yaml_path = (inputs.get('ixref_yaml')
                       or os.path.join(output_dir, 'ixref.yaml'))
    net_xref_yaml_path = (inputs.get('net_xref_yaml')
                          or os.path.join(output_dir, 'net_xref.yaml'))
    device_info_yaml_path = (inputs.get('device_info_yaml')
                              or os.path.join(output_dir, 'device_info.yaml'))
    device_info_dir = (calibre_cfg.get('device_info_dir')
                       or output_dir)
    net_shapes_yaml_path = (inputs.get('net_shapes_yaml')
                             or os.path.join(output_dir, 'net_shapes.yaml'))
    net_shapes_dir = (calibre_cfg.get('net_shapes_dir')
                      or output_dir)

    # Fall back to committed dummy fixtures so legacy site_configs
    # without a populated calibre: block still resolve a sensible
    # source. Defaults sit next to the repo under dummy/fixtures/.
    fixture_dir = os.path.join(
        os.path.dirname(__file__), '..', 'dummy', 'fixtures',
    )
    dummy_ixref = calibre_cfg.get('dummy_ixref')
    dummy_nxref = calibre_cfg.get('dummy_nxref')
    dummy_net_names = calibre_cfg.get('dummy_net_names')
    dummy_device_info_dir = calibre_cfg.get('dummy_device_info_dir')
    dummy_net_shapes_dir = calibre_cfg.get('dummy_net_shapes_dir')
    if effective_lvs_mode == 'dummy':
        if not dummy_ixref:
            dummy_ixref = os.path.join(fixture_dir, 'iXref.temp')
        if not dummy_nxref:
            dummy_nxref = os.path.join(fixture_dir, 'nXref.temp')
        if not dummy_net_names:
            dummy_net_names = os.path.join(fixture_dir, 'net_names.txt')
        if not dummy_device_info_dir:
            dummy_device_info_dir = fixture_dir
        if not dummy_net_shapes_dir:
            dummy_net_shapes_dir = fixture_dir

    print(f"\n[Stage 1.5] Extracting LVS xrefs (mode={effective_lvs_mode})...")
    with dbg.stage("1.5", "LVS extract"):
        parsed_ixref = extract_ixref(
            mode=effective_lvs_mode,
            svdb_dir=calibre_cfg.get('svdb_dir'),
            ixref_path=ixref_temp_path,
            dummy_source=dummy_ixref,
            timeout=calibre_cfg.get('timeout_s', 300),
        )
        write_ixref_yaml(parsed_ixref, ixref_yaml_path)
        n_devs = len(parsed_ixref['devices'])
        n_swap = sum(1 for d in parsed_ixref['devices'] if d['sd_swapped'])
        print(f"  iXref:  cell={parsed_ixref['cell']['layout_name']!r}  "
              f"devices={n_devs}  S/D-swaps={n_swap}")

        parsed_net_xref = extract_net_xref(
            mode=effective_lvs_mode,
            svdb_dir=calibre_cfg.get('svdb_dir'),
            nxref_path=nxref_temp_path,
            net_names_path=net_names_path,
            dummy_nxref_source=dummy_nxref,
            dummy_net_names_source=dummy_net_names,
            timeout=calibre_cfg.get('timeout_s', 300),
        )
        write_net_xref_yaml(parsed_net_xref, net_xref_yaml_path)
        n_nets = len(parsed_net_xref['nets'])
        n_renumbered = sum(1 for n in parsed_net_xref['nets']
                           if n['schematic_name'] != n['lvs_name'])
        print(f"  nXref:  cell={parsed_net_xref['cell']['layout_name']!r}  "
              f"nets={n_nets}  renumbered={n_renumbered}")

        # DEVICE INFO — one query per layout instance, driven by iXref.
        layout_insts = [d['layout_inst'] for d in parsed_ixref['devices']]
        parsed_device_info = extract_device_info(
            mode=effective_lvs_mode,
            svdb_dir=calibre_cfg.get('svdb_dir'),
            layout_insts=layout_insts,
            out_dir=device_info_dir,
            dummy_source_dir=dummy_device_info_dir,
            timeout=calibre_cfg.get('timeout_s', 300),
        )
        write_device_info_yaml(parsed_device_info, device_info_yaml_path)
        n_total_layers = sum(len(d['layers']) for d in parsed_device_info['devices'])
        n_total_shapes = sum(
            len(layer['shapes'])
            for d in parsed_device_info['devices']
            for layer in d['layers']
        )
        print(f"  DevInfo: devices={len(layout_insts)}  "
              f"layers={n_total_layers}  shapes={n_total_shapes}")

        # NET SHAPES — one query per net, driven by net_xref.
        parsed_net_shapes = extract_net_shapes(
            mode=effective_lvs_mode,
            svdb_dir=calibre_cfg.get('svdb_dir'),
            nets=parsed_net_xref['nets'],
            out_dir=net_shapes_dir,
            dummy_source_dir=dummy_net_shapes_dir,
            timeout=calibre_cfg.get('timeout_s', 300),
        )
        write_net_shapes_yaml(parsed_net_shapes, net_shapes_yaml_path)
        n_net_layers = sum(len(n['layers'])
                           for n in parsed_net_shapes['nets'])
        n_net_shape_total = sum(
            len(layer['shapes'])
            for n in parsed_net_shapes['nets']
            for layer in n['layers']
        )
        print(f"  NetShapes: nets={len(parsed_net_shapes['nets'])}  "
              f"layers={n_net_layers}  shapes={n_net_shape_total}")

        print(f"  iXref.temp:        {ixref_temp_path}")
        print(f"  nXref.temp:        {nxref_temp_path}")
        print(f"  net_names.txt:     {net_names_path}")
        print(f"  device_info_*.txt: {device_info_dir}")
        print(f"  net_shapes_*.txt:  {net_shapes_dir}")
        print(f"  ixref.yaml:        {ixref_yaml_path}")
        print(f"  net_xref.yaml:     {net_xref_yaml_path}")
        print(f"  device_info.yaml:  {device_info_yaml_path}")
        print(f"  net_shapes.yaml:   {net_shapes_yaml_path}")

    # ---- Stage 2: Parse layout ----
    print("\n[Stage 2] Parsing layout data...")
    # Slice 1.6: pass the LVS middle files + per-layer derived_layers
    # map so the new apply_calibre_layer_overlay pass runs alongside
    # the legacy apply_lvs_overlay. Site config can override the
    # calibre_layer_map.yaml location via tech.calibre_layer_map.
    # ixref_yaml_path is forwarded so device_info.yaml's LVS-side
    # layout_inst (M0/M1) gets translated to schematic Device.inst_name
    # (MN0/MP0) before stamping.
    tech_block = site.get('tech', {}) or {}
    layer_yaml_path = tech_block.get('layer_map')
    calibre_layer_map_yaml_path = tech_block.get('calibre_layer_map')
    with dbg.stage("2", "parse layout"):
        model, grid = build_layout_model(
            device_query_path=device_query_path,
            net_query_path=net_query_path,
            bbox_path=bbox_path,
            layout_json_path=layout_json_path,
            config=config,
            device_info_yaml_path=device_info_yaml_path,
            net_shapes_yaml_path=net_shapes_yaml_path,
            layer_yaml_path=layer_yaml_path,
            calibre_layer_map_yaml_path=calibre_layer_map_yaml_path,
            ixref_yaml_path=ixref_yaml_path,
        )
        print(f"  {model.summary()}")
        overlay = getattr(model, 'calibre_layer_overlay_coverage', None)
        if overlay is not None:
            print(f"  Calibre-layer overlay: "
                  f"stamped={overlay['stamped']} "
                  f"shared={overlay['shared']} "
                  f"visited={overlay['cells_visited']} "
                  f"(derived shapes loaded: "
                  f"{overlay['derived_shape_count']})")

    # ---- Stage 3-4: CSP setup + load ----
    print("\n[Stage 3-4] Setting up CSP engine and loading layout...")
    with dbg.stage("3-4", "CSP setup + load"):
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
    with dbg.stage("5", "resize via pick_macro"):
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

    # 6a: writeback -> GDS / JSON / CDL
    with dbg.stage("6a", "writeback -> GDS / JSON / CDL"):
        with open(layout_json_path, encoding='utf-8') as f:
            orig_data = json.load(f)
        with open(target_json_path, encoding='utf-8') as f:
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
        with open(os.path.join(output_dir, 'buffer_resized.json'), 'w', encoding='utf-8') as f:
            json.dump(resized_data, f, indent=2)
        print(f"  Layout JSON written: {os.path.join(output_dir, 'buffer_resized.json')}")

        # Write CDL
        cdl_path = os.path.join(output_dir, 'buffer_resized.cdl')
        nfin_n = resized_data['params']['nmos_nfin']
        nfin_p = resized_data['params']['pmos_nfin']
        cell_name = f'INV_N{nfin_n}_P{nfin_p}'
        from io_adapters.writer_cdl import write_cdl
        write_cdl(cdl_path, cell_name, nfin_n, nfin_p, config.POLY_WIDTH)

    # 6b: text reports (annotation coverage + resize report)
    with dbg.stage("6b", "reports"):
        # M3: emit per-layer LVS annotation coverage report. Helps spot the
        # parser-inversion failure mode: a production GDS where most LI/M1
        # shapes are unannotated would surface here as low coverage and
        # feed straight into the BLOCKAGE projection budget.
        coverage = model.annotation_coverage()
        coverage_path = os.path.join(output_dir, 'annotation_coverage.txt')
        with open(coverage_path, 'w', encoding='utf-8') as f:
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
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("BUFFER FIN RESIZE REPORT\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Original: NMOS={orig_nmos_nfin}fin, PMOS={orig_pmos_nfin}fin\n")
            f.write(f"Target:   NMOS={new_nmos_nfin}fin, PMOS={new_pmos_nfin}fin\n")
            # Basename only — keeps the report reproducible across
            # environments (md5-stable for the byte-golden test).
            f.write(f"Source: CDL diff "
                    f"({os.path.basename(original_cdl_path)} vs "
                    f"{os.path.basename(modified_cdl_path)})\n\n")

            for inst, r in results.items():
                f.write(f"{inst} resize: {r.message}\n")
                for op in r.edit_ops:
                    f.write(f"  {op}\n")
                f.write("\n")

            total_edits = sum(len(r.edit_ops) for r in results.values())
            f.write(f"Total edit operations: {total_edits}\n")
        print(f"  Report written: {report_path}")

    # 6c: GDS read-back verification (no files written)
    with dbg.stage("6c", "GDS read-back check"):
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

    # 6d: visualization (PNGs + LVS-shape comparisons + optional Plotly HTML)
    with dbg.stage("6d", "visualization"):
        print("\n[Visualization] Generating comparison plots...")

        from visualization.render import compute_view_window
        from visualization.layout_viewer import (
            generate_three_way_comparison, generate_diff_overlay,
        )
        from visualization.lvs_shapes import (
            device_info_to_shapes, net_shapes_to_shapes, plot_lvs_overlay,
        )

        device_info_shapes = device_info_to_shapes(parsed_device_info)
        net_shapes_shapes = net_shapes_to_shapes(parsed_net_shapes)

        # One coordinate window for every plot in this stage, so flipping
        # between the PNGs / HTML views the user sees shapes in the same
        # spot across original / resized / target / LVS-derived images.
        view_window = compute_view_window(
            orig_data['shapes'],
            resized_data['shapes'],
            target_data['shapes'],
            device_info_shapes,
            net_shapes_shapes,
            margin_frac=0.05,
        )

        generate_three_way_comparison(
            orig_data, resized_data, target_data,
            os.path.join(output_dir, 'resize_comparison.png'),
            config, view_window=view_window,
        )
        generate_diff_overlay(
            orig_data, resized_data,
            os.path.join(output_dir, 'resize_diff.png'),
            view_window=view_window,
        )
        try:
            plot_lvs_overlay(
                orig_data['shapes'], device_info_shapes,
                os.path.join(output_dir, 'lvs_device_info.png'),
                view_window=view_window,
                title='device_info vs GDS',
                mode='side_by_side',
            )
            plot_lvs_overlay(
                orig_data['shapes'], net_shapes_shapes,
                os.path.join(output_dir, 'lvs_net_shapes.png'),
                view_window=view_window,
                title='net_shapes vs GDS',
                mode='side_by_side',
            )
        except Exception as e:
            print(f"  (LVS-shape plots skipped: {e})")

        try:
            from visualization.interactive import write_interactive_html
            write_interactive_html(
                {
                    'original':    orig_data['shapes'],
                    'resized':     resized_data['shapes'],
                    'target':      target_data['shapes'],
                    'device_info': device_info_shapes,
                    'net_shapes':  net_shapes_shapes,
                },
                os.path.join(output_dir, 'debug_view.html'),
                view_window=view_window,
            )
        except ImportError:
            print("  (plotly not installed - skipping debug_view.html; "
                  "pip install -e .[viz] to enable)")
        except Exception as e:
            print(f"  (interactive HTML skipped: {e})")

    # 6e: validation - compare resized vs target
    with dbg.stage("6e", "validation vs target"):
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
    p.add_argument(
        '--lvs-mode', dest='lvs_mode', default=None,
        choices=['dummy', 'calibre'],
        help="Override calibre.mode in site_config "
             "(dummy=copy fixture, calibre=invoke `calibre -query`). "
             "Default: read from site_config.calibre.mode.",
    )
    p.add_argument(
        '--debug', action='store_true',
        help="Debug mode: after each pipeline stage list newly written "
             "intermediate files and pause for a keypress (skipped when "
             "stdin is not a TTY). Stage 6 is split into 6a-6e sub-steps.",
    )
    p.add_argument(
        '--debug-no-pause', action='store_true',
        help="With --debug, print the per-stage file listing but never pause.",
    )
    return p


if __name__ == '__main__':
    args = _build_arg_parser().parse_args()
    env_debug = os.environ.get('LAYAUTO_DEBUG', '').lower() in (
        '1', 'true', 'yes', 'on',
    )
    run_full_pipeline(
        site_config_path=args.site_config,
        lvs_mode=args.lvs_mode,
        debug=args.debug or env_debug,
        pause=not args.debug_no_pause,
    )
