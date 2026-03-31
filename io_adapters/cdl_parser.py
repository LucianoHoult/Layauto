"""
CDL (SPICE) netlist parser and diff utility.

Parses CDL files to extract subcircuit definitions and device parameters,
then diffs two CDL files to identify parameter changes (e.g., nfin resize targets).
"""

import re
from typing import List, Optional


def _parse_value(raw: str):
    """Parse a parameter value string, handling SPICE unit suffixes.

    Supports: n (nano), u (micro), p (pico), m (milli), k (kilo), meg (mega)
    Returns int if the result is a whole number, else float.
    """
    raw = raw.strip()
    suffixes = {
        'meg': 1e6, 'k': 1e3, 'm': 1e-3,
        'u': 1e-6, 'n': 1e-9, 'p': 1e-12, 'f': 1e-15,
    }
    for suffix, mult in suffixes.items():
        if raw.lower().endswith(suffix):
            num = float(raw[:len(raw) - len(suffix)])
            val = num * mult
            return int(val) if val == int(val) else val
    # Try plain number
    try:
        val = float(raw)
        return int(val) if val == int(val) else val
    except ValueError:
        return raw


def parse_cdl(filepath: str) -> dict:
    """Parse a CDL/SPICE netlist file.

    Extracts .SUBCKT blocks and MOSFET device lines (M-prefix).

    Args:
        filepath: Path to the CDL file.

    Returns:
        {
            'subckt_name': str,
            'ports': [str, ...],
            'devices': [
                {
                    'inst': str,          # e.g. 'MN0'
                    'type': str,          # e.g. 'nmos_finfet'
                    'ports': [str, ...],  # D, G, S, B
                    'params': {str: value} # e.g. {'nfin': 5, 'l': 20e-9}
                },
                ...
            ]
        }
    """
    subckt_name = None
    ports = []
    devices = []
    in_subckt = False

    with open(filepath) as f:
        for line in f:
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith('*') or line.startswith('//'):
                continue

            upper = line.upper()

            # .SUBCKT line
            if upper.startswith('.SUBCKT'):
                tokens = line.split()
                subckt_name = tokens[1]
                ports = tokens[2:]
                in_subckt = True
                continue

            # .ENDS line
            if upper.startswith('.ENDS'):
                in_subckt = False
                continue

            # MOSFET device line (starts with M)
            if in_subckt and upper.startswith('M'):
                tokens = line.split()
                inst_name = tokens[0]
                # Standard MOSFET: Mname D G S B model [params...]
                node_ports = tokens[1:5]  # D G S B
                model_name = tokens[5] if len(tokens) > 5 else ''

                # Parse key=value parameters
                params = {}
                for token in tokens[6:]:
                    if '=' in token:
                        key, val = token.split('=', 1)
                        params[key.lower()] = _parse_value(val)

                devices.append({
                    'inst': inst_name,
                    'type': model_name,
                    'ports': node_ports,
                    'params': params,
                })

    return {
        'subckt_name': subckt_name or '',
        'ports': ports,
        'devices': devices,
    }


def diff_cdl(original: dict, modified: dict) -> list:
    """Compare two parsed CDL results and return parameter differences.

    Matches devices by instance name and compares all numeric parameters.

    Args:
        original: Result from parse_cdl() for the original netlist.
        modified: Result from parse_cdl() for the modified netlist.

    Returns:
        List of diffs:
        [
            {'inst': 'MN0', 'param': 'nfin', 'old': 5, 'new': 4},
            ...
        ]
    """
    orig_devs = {d['inst']: d for d in original['devices']}
    mod_devs = {d['inst']: d for d in modified['devices']}

    diffs = []
    for inst_name, orig_dev in orig_devs.items():
        mod_dev = mod_devs.get(inst_name)
        if mod_dev is None:
            continue

        # Compare parameters
        all_keys = set(orig_dev['params'].keys()) | set(mod_dev['params'].keys())
        for key in sorted(all_keys):
            old_val = orig_dev['params'].get(key)
            new_val = mod_dev['params'].get(key)
            if old_val != new_val:
                diffs.append({
                    'inst': inst_name,
                    'param': key,
                    'old': old_val,
                    'new': new_val,
                })

    return diffs


def get_device_param(cdl_data: dict, inst_name: str, param: str, default=None):
    """Convenience: get a specific parameter from a parsed CDL.

    Args:
        cdl_data: Result from parse_cdl().
        inst_name: Device instance name (e.g. 'MN0').
        param: Parameter name (e.g. 'nfin').
        default: Default value if not found.
    """
    for dev in cdl_data['devices']:
        if dev['inst'] == inst_name:
            return dev['params'].get(param, default)
    return default


# =============================================================
# CLI: test with fixture CDL files
# =============================================================
if __name__ == '__main__':
    import os
    fixture_dir = os.path.join(os.path.dirname(__file__), '..', 'dummy', 'fixtures')

    orig_path = os.path.join(fixture_dir, 'buffer_original.cdl')
    target_path = os.path.join(fixture_dir, 'buffer_target.cdl')

    print("Parsing original CDL...")
    orig = parse_cdl(orig_path)
    print(f"  Subckt: {orig['subckt_name']}, ports: {orig['ports']}")
    for d in orig['devices']:
        print(f"  {d['inst']}: type={d['type']}, params={d['params']}")

    print("\nParsing target CDL...")
    target = parse_cdl(target_path)
    print(f"  Subckt: {target['subckt_name']}, ports: {target['ports']}")
    for d in target['devices']:
        print(f"  {d['inst']}: type={d['type']}, params={d['params']}")

    print("\nDiff (original → target):")
    diffs = diff_cdl(orig, target)
    if diffs:
        for diff in diffs:
            print(f"  {diff['inst']}.{diff['param']}: {diff['old']} → {diff['new']}")
    else:
        print("  No differences found.")
