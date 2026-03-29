"""
GDS I/O adapter with gdstk support.

Uses gdstk for reading/writing GDS when available.
Falls back to the manual gds_writer.py (stdlib-only) when not.

Key advantage of gdstk: enables READ-BACK of GDS files for
programmatic shape comparison (validation), which the manual
writer cannot do.

Install: pip install gdstk
"""

import os
import sys
from typing import Dict, List, Tuple, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from tech.layer_map import LAYER_MAP, GDS_TO_LAYER

# --- Detect gdstk availability ---
try:
    import gdstk
    HAS_GDSTK = True
except ImportError:
    HAS_GDSTK = False


def write_gds(layout_data: dict, filename: str):
    """
    Write layout data dict to GDS file.
    Uses gdstk if available, otherwise falls back to manual writer.
    """
    if HAS_GDSTK:
        _write_gds_gdstk(layout_data, filename)
    else:
        _write_gds_manual(layout_data, filename)


def read_gds(filename: str) -> Dict[str, List[dict]]:
    """
    Read GDS file and return shapes per layer.
    
    Returns:
        {layer_name: [{'x1','y1','x2','y2'}, ...]}
    
    Requires gdstk. Raises ImportError if not available.
    """
    if not HAS_GDSTK:
        raise ImportError(
            "gdstk is required for GDS reading. "
            "Install with: pip install gdstk"
        )
    return _read_gds_gdstk(filename)


def compare_gds(file_a: str, file_b: str, 
                layers: List[str] = None) -> dict:
    """
    Compare two GDS files shape-by-shape.
    
    Returns:
        {
            layer_name: {
                'match': bool,
                'only_a': [...],
                'only_b': [...],
                'common': int,
            }
        }
    
    Requires gdstk.
    """
    shapes_a = read_gds(file_a)
    shapes_b = read_gds(file_b)
    
    all_layers = set(shapes_a.keys()) | set(shapes_b.keys())
    if layers:
        all_layers &= set(layers)
    
    result = {}
    for layer in sorted(all_layers):
        set_a = {(s['x1'], s['y1'], s['x2'], s['y2']) 
                 for s in shapes_a.get(layer, [])}
        set_b = {(s['x1'], s['y1'], s['x2'], s['y2']) 
                 for s in shapes_b.get(layer, [])}
        
        result[layer] = {
            'match': set_a == set_b,
            'only_a': sorted(set_a - set_b),
            'only_b': sorted(set_b - set_a),
            'common': len(set_a & set_b),
        }
    
    return result


# =============================================================
# gdstk implementation
# =============================================================

def _write_gds_gdstk(layout_data: dict, filename: str):
    """Write GDS using gdstk."""
    lib = gdstk.Library(unit=1e-9, precision=1e-12)
    
    nfin_n = layout_data['params']['nmos_nfin']
    nfin_p = layout_data['params']['pmos_nfin']
    cell_name = f'INV_N{nfin_n}_P{nfin_p}'
    
    cell = lib.new_cell(cell_name)
    
    for layer_name, shape_list in layout_data['shapes'].items():
        if layer_name not in LAYER_MAP:
            continue
        gds_layer, gds_dtype = LAYER_MAP[layer_name]
        
        for s in shape_list:
            rect = gdstk.rectangle(
                (s['x1'], s['y1']),
                (s['x2'], s['y2']),
                layer=gds_layer,
                datatype=gds_dtype,
            )
            cell.add(rect)
    
    lib.write_gds(filename)
    print(f"  GDS written (gdstk): {filename} (cell: {cell_name})")


def _read_gds_gdstk(filename: str) -> Dict[str, List[dict]]:
    """Read GDS using gdstk, return shapes grouped by layer name."""
    lib = gdstk.read_gds(filename)
    
    result = {}
    
    for cell in lib.cells:
        for polygon in cell.polygons:
            layer_key = (polygon.layer, polygon.datatype)
            layer_name = GDS_TO_LAYER.get(layer_key)
            if layer_name is None:
                layer_name = f"L{polygon.layer}_D{polygon.datatype}"
            
            if layer_name not in result:
                result[layer_name] = []
            
            # Extract bounding box from polygon points
            pts = polygon.points
            x_coords = [p[0] for p in pts]
            y_coords = [p[1] for p in pts]
            
            result[layer_name].append({
                'x1': int(round(min(x_coords))),
                'y1': int(round(min(y_coords))),
                'x2': int(round(max(x_coords))),
                'y2': int(round(max(y_coords))),
            })
    
    return result


# =============================================================
# Manual fallback (uses dummy/gds_writer.py)
# =============================================================

def _write_gds_manual(layout_data: dict, filename: str):
    """Write GDS using the manual stdlib-only writer."""
    from dummy.gds_writer import GdsWriter
    
    gds = GdsWriter(filename)
    gds.begin_lib('BUFFER_LIB')
    
    nfin_n = layout_data['params']['nmos_nfin']
    nfin_p = layout_data['params']['pmos_nfin']
    cell_name = f'INV_N{nfin_n}_P{nfin_p}'
    
    gds.begin_cell(cell_name)
    
    for layer_name, shape_list in layout_data['shapes'].items():
        if layer_name not in LAYER_MAP:
            continue
        gds_layer, gds_dtype = LAYER_MAP[layer_name]
        for s in shape_list:
            gds.rectangle(gds_layer, gds_dtype,
                          s['x1'], s['y1'], s['x2'], s['y2'])
    
    gds.end_cell()
    gds.end_lib()
    print(f"  GDS written (manual): {filename} (cell: {cell_name})")


# =============================================================
# CLI: test GDS round-trip if gdstk available
# =============================================================
if __name__ == '__main__':
    print(f"gdstk available: {HAS_GDSTK}")
    
    if HAS_GDSTK:
        print(f"gdstk version: {gdstk.__version__}")
        
        # Round-trip test: read fixture GDS, dump shapes
        fixture_dir = os.path.join(os.path.dirname(__file__), 
                                    '..', 'dummy', 'fixtures')
        gds_path = os.path.join(fixture_dir, 'buffer_original.gds')
        
        if os.path.exists(gds_path):
            print(f"\nReading: {gds_path}")
            shapes = read_gds(gds_path)
            for layer, slist in sorted(shapes.items()):
                print(f"  {layer}: {len(slist)} shapes")
        
        # Compare original vs target
        target_path = os.path.join(fixture_dir, 'buffer_target.gds')
        if os.path.exists(target_path):
            print(f"\nComparing original vs target:")
            diff = compare_gds(gds_path, target_path)
            for layer, info in sorted(diff.items()):
                status = "MATCH" if info['match'] else "DIFF"
                print(f"  {layer}: {status} "
                      f"(common={info['common']}, "
                      f"+{len(info['only_b'])}, -{len(info['only_a'])})")
    else:
        print("Install gdstk for GDS read/compare: pip install gdstk")
        print("Manual GDS writer (write-only) is always available.")
