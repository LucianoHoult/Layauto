"""
Parser for standard .layermap files.

Supports common EDA layermap formats:
  1. Cadence style:  layer_name  layer_number  datatype  purpose
  2. Simple format:  layer_name  layer_number  datatype
  3. Comments: lines starting with # or *
  4. Blank lines are ignored

Example .layermap file:
    # Layer mapping
    FIN     1   0   drawing
    POLY    2   0   drawing
    LI      3   0   drawing
    VIA0    4   0   drawing
    M1      5   0   drawing
"""


def parse_layermap(filepath: str) -> dict:
    """Parse a .layermap file into layer mapping dicts.

    Args:
        filepath: Path to the .layermap file.

    Returns:
        {
            'LAYER_MAP': {layer_name: (layer_number, datatype), ...},
            'GDS_TO_LAYER': {(layer_number, datatype): layer_name, ...},
            'purposes': {layer_name: purpose_string, ...},
        }
    """
    layer_map = {}
    purposes = {}

    with open(filepath, encoding='utf-8') as f:
        for line in f:
            line = line.strip()

            # Skip comments and blank lines
            if not line or line.startswith('#') or line.startswith('*'):
                continue

            tokens = line.split()
            if len(tokens) < 3:
                continue  # Need at least: name, layer_number, datatype

            name = tokens[0]
            try:
                layer_num = int(tokens[1])
                datatype = int(tokens[2])
            except ValueError:
                continue  # Skip malformed lines

            layer_map[name] = (layer_num, datatype)

            if len(tokens) >= 4:
                purposes[name] = tokens[3]

    gds_to_layer = {v: k for k, v in layer_map.items()}

    return {
        'LAYER_MAP': layer_map,
        'GDS_TO_LAYER': gds_to_layer,
        'purposes': purposes,
    }


# =============================================================
# CLI: test with a sample layermap
# =============================================================
if __name__ == '__main__':
    import os
    import tempfile

    sample = """\
# Sample layermap for dummy 7nm process
FIN       1   0   drawing
POLY      2   0   drawing
LI        3   0   drawing
VIA0      4   0   drawing
M1        5   0   drawing
OD        6   0   drawing
NWELL     7   0   drawing
BOUNDARY  10  0   drawing
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.layermap', delete=False) as f:
        f.write(sample)
        tmp_path = f.name

    try:
        result = parse_layermap(tmp_path)
        print("LAYER_MAP:")
        for name, (ln, dt) in sorted(result['LAYER_MAP'].items()):
            purpose = result['purposes'].get(name, '')
            print(f"  {name:10s} → ({ln}, {dt})  {purpose}")
        print(f"\nGDS_TO_LAYER: {len(result['GDS_TO_LAYER'])} entries")
    finally:
        os.unlink(tmp_path)
