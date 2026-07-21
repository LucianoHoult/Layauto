"""
Verification: compare resized layout output against ground truth target.

Three levels of verification:
1. JSON-level: compare shape coordinates from layout data dicts
2. GDS-level: read back GDS and compare (requires gdstk)
3. DRC-level: run KLayout DRC on output (requires klayout)
"""

import json
import os
import sys
from typing import Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.diff import compute_shape_diff


def verify_json(resized_data: dict, target_data: dict,
                layers: List[str] = None) -> dict:
    """
    Compare resized vs target layout data at JSON level.
    
    Returns: {layer: {match, only_resized, only_target, common}}
    """
    if layers is None:
        layers = ['FIN', 'OD', 'LI', 'VIA0', 'M1']
    
    results = {}
    total_mismatches = 0
    
    for layer in layers:
        r_shapes = resized_data.get('shapes', {}).get(layer, [])
        t_shapes = target_data.get('shapes', {}).get(layer, [])
        
        r_set = {(s['x1'], s['y1'], s['x2'], s['y2']) for s in r_shapes}
        t_set = {(s['x1'], s['y1'], s['x2'], s['y2']) for s in t_shapes}
        
        only_r = r_set - t_set
        only_t = t_set - r_set
        
        results[layer] = {
            'match': r_set == t_set,
            'only_resized': sorted(only_r),
            'only_target': sorted(only_t),
            'common': len(r_set & t_set),
        }
        total_mismatches += len(only_r) + len(only_t)
    
    results['_summary'] = {
        'total_mismatches': total_mismatches,
        'all_match': total_mismatches == 0,
    }
    
    return results


def verify_gds(resized_gds: str, target_gds: str,
               layers: List[str] = None) -> Optional[dict]:
    """
    Compare at GDS level using gdstk read-back.
    Returns None if gdstk not available.
    """
    try:
        from io_adapters.gds_io import compare_gds
        return compare_gds(resized_gds, target_gds, layers=layers)
    except ImportError:
        return None


def verify_drc(gds_path: str) -> Optional[dict]:
    """
    Run KLayout DRC on GDS.
    Returns None if klayout not available.
    """
    try:
        from tests.integration.test_klayout_drc import run_klayout_drc
        return run_klayout_drc(gds_path)
    except ImportError:
        return None


def print_verification_report(results: dict):
    """Print formatted verification results."""
    print("\n[Verification Report]")
    for layer, info in sorted(results.items()):
        if layer.startswith('_'):
            continue
        if info['match']:
            print(f"  {layer:6s}: MATCH ({info['common']} shapes)")
        else:
            print(f"  {layer:6s}: MISMATCH "
                  f"(+{len(info.get('only_target', []))} "
                  f"-{len(info.get('only_resized', []))})")
    
    summary = results.get('_summary', {})
    if summary.get('all_match'):
        print("  Overall: PASS")
    else:
        print(f"  Overall: {summary.get('total_mismatches', '?')} mismatches")
