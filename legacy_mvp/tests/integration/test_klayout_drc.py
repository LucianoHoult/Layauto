"""
Cross-validate CSP DRC results against KLayout's DRC engine.

This test reads the resized GDS and runs a simplified DRC rule deck
using KLayout's Python API. It verifies that the CSP engine's
"correct by construction" guarantee holds at the GDS level.

Requires: pip install klayout

Usage:
    python3 tests/integration/test_klayout_drc.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    import pya
    HAS_KLAYOUT = True
except ImportError:
    try:
        import klayout.db as pya
        HAS_KLAYOUT = True
    except ImportError:
        HAS_KLAYOUT = False

from tech.config_loader import get_tech_config
from tech.layer_map import LAYER_MAP


def run_klayout_drc(gds_path: str, report_path: str = None) -> dict:
    """
    Run simplified DRC on a GDS file using KLayout.
    
    Returns:
        {
            'rule_name': {
                'violations': int,
                'details': [...]
            }
        }
    """
    if not HAS_KLAYOUT:
        raise ImportError("klayout Python package required. Install: pip install klayout")
    
    layout = pya.Layout()
    layout.read(gds_path)
    
    # Get top cell
    top_cell = layout.top_cell()
    if top_cell is None:
        raise ValueError(f"No top cell found in {gds_path}")
    
    # Get layer indices
    def get_layer(name):
        gds_layer, gds_dtype = LAYER_MAP[name]
        return layout.layer(gds_layer, gds_dtype)
    
    cfg = get_tech_config()
    results = {}

    # --- Rule 1: LI min spacing ---
    li_layer = get_layer('LI')
    li_region = pya.Region(top_cell.begin_shapes_rec(li_layer))
    li_space_violations = li_region.space_check(cfg.LI_MIN_SPACING)
    results['LI_min_spacing'] = {
        'rule': f'LI spacing >= {cfg.LI_MIN_SPACING}nm',
        'violations': li_space_violations.size(),
    }

    # --- Rule 2: M1 min spacing ---
    m1_layer = get_layer('M1')
    m1_region = pya.Region(top_cell.begin_shapes_rec(m1_layer))
    m1_space_violations = m1_region.space_check(cfg.M1_MIN_SPACING)
    results['M1_min_spacing'] = {
        'rule': f'M1 spacing >= {cfg.M1_MIN_SPACING}nm',
        'violations': m1_space_violations.size(),
    }

    # --- Rule 3: LI min width ---
    li_width_violations = li_region.width_check(cfg.LI_WIDTH)
    results['LI_min_width'] = {
        'rule': f'LI width >= {cfg.LI_WIDTH}nm',
        'violations': li_width_violations.size(),
    }

    # --- Rule 4: M1 min width ---
    m1_width_violations = m1_region.width_check(cfg.M1_WIDTH)
    results['M1_min_width'] = {
        'rule': f'M1 width >= {cfg.M1_WIDTH}nm',
        'violations': m1_width_violations.size(),
    }

    # --- Rule 5: Via0 enclosure by LI ---
    via0_layer = get_layer('VIA0')
    via0_region = pya.Region(top_cell.begin_shapes_rec(via0_layer))

    via0_sized = via0_region.sized(cfg.VIA0_ENC_BY_LI_X, cfg.VIA0_ENC_BY_LI_Y)
    enc_violations = via0_sized.not_inside(li_region)
    results['Via0_enc_by_LI'] = {
        'rule': f'Via0 enclosed by LI ({cfg.VIA0_ENC_BY_LI_X}/{cfg.VIA0_ENC_BY_LI_Y}nm)',
        'violations': enc_violations.size(),
    }

    # --- Rule 6: Via0 enclosure by M1 ---
    via0_sized_m1 = via0_region.sized(cfg.VIA0_ENC_BY_M1_X, cfg.VIA0_ENC_BY_M1_Y)
    enc_violations_m1 = via0_sized_m1.not_inside(m1_region)
    results['Via0_enc_by_M1'] = {
        'rule': f'Via0 enclosed by M1 ({cfg.VIA0_ENC_BY_M1_X}/{cfg.VIA0_ENC_BY_M1_Y}nm)',
        'violations': enc_violations_m1.size(),
    }
    
    # Print results
    total_violations = sum(r['violations'] for r in results.values())
    
    print(f"\nKLayout DRC Results for: {os.path.basename(gds_path)}")
    print("=" * 55)
    for name, info in results.items():
        status = "PASS" if info['violations'] == 0 else f"FAIL ({info['violations']})"
        print(f"  {name:25s}: {status:15s}  [{info['rule']}]")
    print(f"\n  Total violations: {total_violations}")
    print(f"  Overall: {'CLEAN' if total_violations == 0 else 'VIOLATIONS FOUND'}")
    
    return results


def validate_resize_output():
    """Validate the resized GDS against DRC rules."""
    
    output_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'output')
    fixture_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'dummy', 'fixtures')
    
    resized_gds = os.path.join(output_dir, 'buffer_resized.gds')
    original_gds = os.path.join(fixture_dir, 'buffer_original.gds')
    target_gds = os.path.join(fixture_dir, 'buffer_target.gds')
    
    print("\n" + "=" * 55)
    print("  KLAYOUT DRC CROSS-VALIDATION")
    print("=" * 55)
    
    for label, path in [
        ("Original", original_gds),
        ("Resized (solver output)", resized_gds),
        ("Target (ground truth)", target_gds),
    ]:
        if os.path.exists(path):
            print(f"\n--- {label} ---")
            results = run_klayout_drc(path)
        else:
            print(f"\n--- {label} --- SKIPPED (file not found: {path})")


if __name__ == '__main__':
    if not HAS_KLAYOUT:
        print("klayout Python package not available.")
        print("Install with: pip install klayout")
        print("Then re-run this script to validate DRC.")
        sys.exit(0)
    
    validate_resize_output()
