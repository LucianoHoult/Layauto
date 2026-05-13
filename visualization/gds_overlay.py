"""
GDS overlay: visual comparison of two GDS files.

When klayout is available, generates an overlay image.
Otherwise, falls back to coordinate-based text comparison.

For klayout GUI usage, this can also generate a .lym macro script.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from io_adapters.gds_io import compare_gds, read_gds, HAS_GDSTK
except ImportError:
    HAS_GDSTK = False


def print_gds_comparison(file_a: str, file_b: str,
                         layers=None):
    """Print text-based GDS comparison."""
    if not HAS_GDSTK:
        print("gdstk not available. Install with: pip install gdstk")
        return
    
    name_a = os.path.basename(file_a)
    name_b = os.path.basename(file_b)
    
    print(f"\nGDS Comparison: {name_a} vs {name_b}")
    print("=" * 55)
    
    diff = compare_gds(file_a, file_b, layers=layers)
    total_diff = 0
    for layer, info in sorted(diff.items()):
        if info['match']:
            print(f"  {layer:8s}: MATCH ({info['common']} shapes)")
        else:
            n_add = len(info['only_b'])
            n_del = len(info['only_a'])
            print(f"  {layer:8s}: DIFF  +{n_add} -{n_del} (common={info['common']})")
            total_diff += n_add + n_del
    
    print(f"\n  Total differences: {total_diff}")


def generate_klayout_macro(file_a: str, file_b: str,
                           output_path: str):
    """
    Generate a KLayout macro (.lym) that opens both GDS files
    as overlaid layers for visual comparison.
    """
    macro = f"""<?xml version="1.0" encoding="utf-8"?>
<klayout-macro>
 <description>GDS Overlay Comparison</description>
 <format>general</format>
 <autorun>true</autorun>
 <text>
import pya

app = pya.Application.instance()
mw = app.main_window()

# Load first layout
view = mw.load_layout("{os.path.abspath(file_a)}", 1)
# Load second layout as overlay  
mw.load_layout("{os.path.abspath(file_b)}", 2)

print("Overlay loaded. Compare visually.")
 </text>
</klayout-macro>"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(macro)
    print(f"  KLayout macro written: {output_path}")
    print(f"  Open in KLayout: klayout -rm {output_path}")


if __name__ == '__main__':
    fixture_dir = os.path.join(os.path.dirname(__file__), '..', 'dummy', 'fixtures')
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'output')
    
    orig = os.path.join(fixture_dir, 'buffer_original.gds')
    resized = os.path.join(output_dir, 'buffer_resized.gds')
    target = os.path.join(fixture_dir, 'buffer_target.gds')
    
    if os.path.exists(resized):
        print_gds_comparison(orig, resized, 
                            layers=['FIN','OD','POLY','LI','VIA0','M1'])
