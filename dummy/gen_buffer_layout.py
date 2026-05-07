"""
Generate a dummy FinFET inverter layout as GDS.

Topology:
  - Single-finger inverter (1 active gate, 2 boundary dummy gates)
  - NMOS at bottom, PMOS at top
  - Fin (H), Poly (V), LI (V), Via0, M1 (H)
  - Slot contacts for S/D
  - Nets: VSS (NMOS source), VDD (PMOS source), IN (gate), OUT (drains)

Coordinate system:
  - X: horizontal (along fin direction)
  - Y: vertical (along poly/LI direction)
  - Origin: cell lower-left corner
  - All units: nanometers

Can generate layouts with arbitrary NMOS/PMOS fin counts,
enabling before/after comparison for fin resizing.
"""

import sys
import os
import json

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tech.config_loader import get_tech_config
from tech.layer_map import LAYER_MAP
from dummy.gds_writer import GdsWriter, rect_centered


# =========================================================
# Cell-template constants (dummy fixture only).
#
# These describe how the dummy generator builds the inverter layout —
# they are not DRC rules, not foundry parameters, and not consumed by
# any production code path. The production parser sees the cell
# topology directly from the input GDS / Calibre device query (gate
# count, NMOS-PMOS gap, etc.).
# =========================================================
NUM_GATE_SLOTS = 3   # gate pitches per cell (dummy_L + active + dummy_R)
NP_GAP_FINS    = 3   # gap between NMOS and PMOS in fin pitches


def generate_inverter_layout(nmos_nfin: int, pmos_nfin: int, config=None) -> dict:
    """
    Compute all shapes for the inverter layout.
    
    Returns a dict of:
      {
        'shapes': {layer_name: [{'x1','y1','x2','y2','net','desc'}, ...]},
        'devices': [...],
        'nets': {...},
        'cell_bbox': {'x1','y1','x2','y2'},
        'params': {...}
      }
    
    This is the "ground truth" from which we generate GDS, Calibre JSONs, etc.
    """
    if config is None:
        config = get_tech_config()

    FIN_PITCH = config.FIN_PITCH
    GATE_PITCH = config.GATE_PITCH
    LI_PITCH = config.LI_PITCH
    M1_PITCH = config.M1_PITCH
    FIN_WIDTH = config.FIN_WIDTH
    POLY_WIDTH = config.POLY_WIDTH
    LI_WIDTH = config.LI_WIDTH
    M1_WIDTH = config.M1_WIDTH
    VIA0_WIDTH = config.VIA0_WIDTH
    VIA0_HEIGHT = config.VIA0_HEIGHT
    OD_EXTENSION_BEYOND_FIN = config.OD_EXTENSION_BEYOND_FIN
    POLY_EXTENSION_BEYOND_OD = config.POLY_EXTENSION_BEYOND_OD
    VIA0_ENC_BY_LI_Y = config.VIA0_ENC_BY_LI_Y

    shapes = {layer: [] for layer in LAYER_MAP}

    def add_shape(layer, x1, y1, x2, y2, net='', desc=''):
        shapes[layer].append({
            'x1': int(x1), 'y1': int(y1),
            'x2': int(x2), 'y2': int(y2),
            'net': net, 'desc': desc
        })

    # =========================================================
    # Y-axis layout planning
    # =========================================================
    # Leave margin at bottom for VSS M1 rail
    y_margin_bot = 40
    y_margin_top = 40

    # NMOS fin positions (bottom to top)
    nmos_fin_y = [y_margin_bot + i * FIN_PITCH for i in range(nmos_nfin)]
    nmos_fin_bot = nmos_fin_y[0]
    nmos_fin_top = nmos_fin_y[-1]
    
    # Gap between NMOS and PMOS
    np_gap = NP_GAP_FINS * FIN_PITCH
    
    # PMOS fin positions
    pmos_fin_y = [nmos_fin_top + np_gap + FIN_PITCH + i * FIN_PITCH 
                  for i in range(pmos_nfin)]
    pmos_fin_bot = pmos_fin_y[0]
    pmos_fin_top = pmos_fin_y[-1]
    
    # Cell height
    cell_height = pmos_fin_top + y_margin_top
    
    # =========================================================
    # X-axis layout planning  
    # =========================================================
    # Gate positions (3 slots: dummy_L, active, dummy_R)
    gate_x = [i * GATE_PITCH for i in range(NUM_GATE_SLOTS)]
    # x=0 (dummy_L), x=54 (active), x=108 (dummy_R)
    
    # S/D LI contact positions (between gates)
    sd_li_x = [(gate_x[i] + gate_x[i+1]) / 2 for i in range(NUM_GATE_SLOTS - 1)]
    # x=27 (left S/D), x=81 (right S/D)
    
    cell_width = gate_x[-1]  # = 108nm
    
    # =========================================================
    # M1 track positions (Y coordinates, pitch=36nm)
    # Choose tracks that are useful for routing
    # =========================================================
    m1_offset = M1_PITCH // 2  # = 18nm, first track at y=18
    
    # Find the M1 track closest to desired Y positions
    def nearest_m1_track(target_y):
        idx = round((target_y - m1_offset) / M1_PITCH)
        return m1_offset + idx * M1_PITCH
    
    m1_y_vss = nearest_m1_track(10)           # Bottom rail
    m1_y_vdd = nearest_m1_track(cell_height - 10)  # Top rail
    
    # For OUT and IN, find tracks in the N-P gap
    gap_center = (nmos_fin_top + pmos_fin_bot) / 2
    m1_y_out = nearest_m1_track(gap_center + M1_PITCH // 2)
    m1_y_in  = nearest_m1_track(gap_center - M1_PITCH // 2)
    
    # Ensure IN and OUT are on different tracks
    if m1_y_in == m1_y_out:
        m1_y_in = m1_y_out - M1_PITCH
    
    # =========================================================
    # Generate shapes layer by layer
    # =========================================================
    
    # --- CELL BOUNDARY ---
    add_shape('BOUNDARY', 0, 0, cell_width, cell_height, desc='cell_boundary')
    
    # --- NWELL (covers PMOS region) ---
    nwell_margin = 30
    add_shape('NWELL', 
              -nwell_margin, pmos_fin_bot - nwell_margin,
              cell_width + nwell_margin, pmos_fin_top + nwell_margin,
              desc='nwell')
    
    # --- FIN layer (individual fin stripes) ---
    hw = FIN_WIDTH / 2
    for i, fy in enumerate(nmos_fin_y):
        add_shape('FIN', 0, fy - hw, cell_width, fy + hw,
                  desc=f'nmos_fin_{i}')
    for i, fy in enumerate(pmos_fin_y):
        add_shape('FIN', 0, fy - hw, cell_width, fy + hw,
                  desc=f'pmos_fin_{i}')
    
    # --- OD layer (active region blocks) ---
    od_ext = OD_EXTENSION_BEYOND_FIN
    add_shape('OD', 0, nmos_fin_bot - od_ext, cell_width, nmos_fin_top + od_ext,
              desc='nmos_od')
    add_shape('OD', 0, pmos_fin_bot - od_ext, cell_width, pmos_fin_top + od_ext,
              desc='pmos_od')
    
    # --- POLY layer (vertical gate stripes) ---
    pw = POLY_WIDTH / 2
    poly_ext = POLY_EXTENSION_BEYOND_OD
    poly_y_bot = nmos_fin_bot - od_ext - poly_ext
    poly_y_top = pmos_fin_top + od_ext + poly_ext
    
    for i, gx in enumerate(gate_x):
        net = 'IN' if i == 1 else ''
        desc = 'active_gate' if i == 1 else f'dummy_gate_{i}'
        add_shape('POLY', gx - pw, poly_y_bot, gx + pw, poly_y_top,
                  net=net, desc=desc)
    
    # --- LI layer (vertical contact bars for S/D) ---
    liw = LI_WIDTH / 2
    li_ext_y = 5  # Small extension beyond fin region
    
    # NMOS source LI (left S/D, x=27) → net VSS
    add_shape('LI', 
              sd_li_x[0] - liw, nmos_fin_bot - li_ext_y,
              sd_li_x[0] + liw, nmos_fin_top + li_ext_y,
              net='VSS', desc='li_nmos_source')
    
    # PMOS source LI (left S/D, x=27) → net VDD
    add_shape('LI',
              sd_li_x[0] - liw, pmos_fin_bot - li_ext_y,
              sd_li_x[0] + liw, pmos_fin_top + li_ext_y,
              net='VDD', desc='li_pmos_source')
    
    # NMOS drain LI (right S/D, x=81) → net OUT
    # Extend through gap to enable M1 connection
    add_shape('LI',
              sd_li_x[1] - liw, nmos_fin_bot - li_ext_y,
              sd_li_x[1] + liw, nmos_fin_top + li_ext_y,
              net='OUT', desc='li_nmos_drain')
    
    # PMOS drain LI (right S/D, x=81) → net OUT
    add_shape('LI',
              sd_li_x[1] - liw, pmos_fin_bot - li_ext_y,
              sd_li_x[1] + liw, pmos_fin_top + li_ext_y,
              net='OUT', desc='li_pmos_drain')
    
    # Gate contact LI (at gate x=54, in the N-P gap) → net IN
    gate_li_height = 30  # Short LI bar in the gap
    gate_li_center_y = (nmos_fin_top + pmos_fin_bot) / 2
    add_shape('LI',
              gate_x[1] - liw, gate_li_center_y - gate_li_height / 2,
              gate_x[1] + liw, gate_li_center_y + gate_li_height / 2,
              net='IN', desc='li_gate_contact')
    
    # --- VIA0 layer (LI to M1 connections) ---
    vw = VIA0_WIDTH / 2
    vh = VIA0_HEIGHT / 2
    
    via0_list = [
        # (x, y, net, desc)
        (sd_li_x[0], m1_y_vss, 'VSS', 'via0_nmos_source'),    # NMOS source → VSS
        (sd_li_x[0], m1_y_vdd, 'VDD', 'via0_pmos_source'),    # PMOS source → VDD
        (sd_li_x[1], m1_y_out, 'OUT', 'via0_drain'),           # Drain → OUT
        (gate_x[1],  m1_y_in,  'IN',  'via0_gate'),            # Gate → IN
    ]
    
    for vx, vy, net, desc in via0_list:
        add_shape('VIA0', vx - vw, vy - vh, vx + vw, vy + vh,
                  net=net, desc=desc)
    
    # --- Extend LI bars to reach Via0 positions ---
    # NMOS source LI needs to reach m1_y_vss (might be below fin region)
    nmos_src_li = next(s for s in shapes['LI'] if s['desc'] == 'li_nmos_source')
    if m1_y_vss < nmos_src_li['y1']:
        nmos_src_li['y1'] = int(m1_y_vss - VIA0_ENC_BY_LI_Y)
    
    # PMOS source LI needs to reach m1_y_vdd (might be above fin region)
    pmos_src_li = next(s for s in shapes['LI'] if s['desc'] == 'li_pmos_source')
    if m1_y_vdd > pmos_src_li['y2']:
        pmos_src_li['y2'] = int(m1_y_vdd + VIA0_ENC_BY_LI_Y)
    
    # Gate contact LI needs to reach m1_y_in
    gate_li = next(s for s in shapes['LI'] if s['desc'] == 'li_gate_contact')
    gate_li['y1'] = int(min(gate_li['y1'], m1_y_in - VIA0_ENC_BY_LI_Y))
    gate_li['y2'] = int(max(gate_li['y2'], m1_y_in + VIA0_ENC_BY_LI_Y))
    
    # Drain LIs need to reach m1_y_out
    for desc in ['li_nmos_drain', 'li_pmos_drain']:
        li = next(s for s in shapes['LI'] if s['desc'] == desc)
        li['y1'] = int(min(li['y1'], m1_y_out - VIA0_ENC_BY_LI_Y))
        li['y2'] = int(max(li['y2'], m1_y_out + VIA0_ENC_BY_LI_Y))
    
    # --- M1 layer (horizontal routing) ---
    m1_ext_x = 10  # Small extension beyond via in X
    
    # VSS rail (full width)
    add_shape('M1', 0, m1_y_vss - M1_WIDTH // 2,
              cell_width, m1_y_vss + M1_WIDTH // 2,
              net='VSS', desc='m1_vss')
    
    # VDD rail (full width)
    add_shape('M1', 0, m1_y_vdd - M1_WIDTH // 2,
              cell_width, m1_y_vdd + M1_WIDTH // 2,
              net='VDD', desc='m1_vdd')
    
    # OUT (connects drain via at x=81, short segment)
    add_shape('M1',
              sd_li_x[1] - m1_ext_x, m1_y_out - M1_WIDTH // 2,
              sd_li_x[1] + m1_ext_x, m1_y_out + M1_WIDTH // 2,
              net='OUT', desc='m1_out')
    
    # IN (connects gate via at x=54, short segment)
    add_shape('M1',
              gate_x[1] - m1_ext_x, m1_y_in - M1_WIDTH // 2,
              gate_x[1] + m1_ext_x, m1_y_in + M1_WIDTH // 2,
              net='IN', desc='m1_in')
    
    # =========================================================
    # Compile metadata
    # =========================================================
    devices = [
        {
            'name': 'MN0',
            'type': 'nmos',
            'nfin': nmos_nfin,
            'nf': 1,  # number of fingers
            'pins': {'G': 'IN', 'D': 'OUT', 'S': 'VSS', 'B': 'VSS'},
            'fin_y_positions': nmos_fin_y,
            'gate_x': gate_x[1],
        },
        {
            'name': 'MP0',
            'type': 'pmos',
            'nfin': pmos_nfin,
            'nf': 1,
            'pins': {'G': 'IN', 'D': 'OUT', 'S': 'VDD', 'B': 'VDD'},
            'fin_y_positions': pmos_fin_y,
            'gate_x': gate_x[1],
        },
    ]
    
    nets = {
        'VSS': {'type': 'power', 'pins': [('MN0', 'S'), ('MN0', 'B')]},
        'VDD': {'type': 'power', 'pins': [('MP0', 'S'), ('MP0', 'B')]},
        'IN':  {'type': 'signal', 'pins': [('MN0', 'G'), ('MP0', 'G')]},
        'OUT': {'type': 'signal', 'pins': [('MN0', 'D'), ('MP0', 'D')]},
    }
    
    params = {
        'nmos_nfin': nmos_nfin,
        'pmos_nfin': pmos_nfin,
        'gate_x': gate_x,
        'sd_li_x': sd_li_x,
        'm1_tracks': {
            'VSS': m1_y_vss, 'VDD': m1_y_vdd,
            'OUT': m1_y_out, 'IN': m1_y_in,
        },
        'nmos_fin_y': nmos_fin_y,
        'pmos_fin_y': pmos_fin_y,
        'cell_width': cell_width,
        'cell_height': cell_height,
    }
    
    return {
        'shapes': shapes,
        'devices': devices,
        'nets': nets,
        'cell_bbox': {'x1': 0, 'y1': 0, 'x2': cell_width, 'y2': cell_height},
        'params': params,
    }


def write_gds(layout_data: dict, filename: str):
    """Write layout data to GDS file."""
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
    print(f"  GDS written: {filename} (cell: {cell_name})")


def write_layout_json(layout_data: dict, filename: str):
    """Save full layout data as JSON (for debugging and downstream use)."""
    with open(filename, 'w') as f:
        json.dump(layout_data, f, indent=2)
    print(f"  Layout JSON written: {filename}")


def generate_calibre_device_query(layout_data: dict, config=None) -> list:
    """
    Simulate Calibre SVDB device query output.

    Format mimics what you'd get from:
      calibrequery -device -type MOS -param ...
    """
    if config is None:
        config = get_tech_config()

    devices = []
    for dev in layout_data['devices']:
        fin_ys = dev['fin_y_positions']
        gate_x = dev['gate_x']

        dev_entry = {
            'instance': dev['name'],
            'device_type': dev['type'].upper(),
            'parameters': {
                'nfin': dev['nfin'],
                'nf': dev['nf'],
                'l': config.POLY_WIDTH,
                'w': dev['nfin'] * config.FIN_PITCH,
            },
            'pins': dev['pins'],
            'bbox': {
                'x1': int(gate_x - config.GATE_PITCH // 2),
                'y1': int(fin_ys[0] - config.FIN_PITCH // 2),
                'x2': int(gate_x + config.GATE_PITCH // 2),
                'y2': int(fin_ys[-1] + config.FIN_PITCH // 2),
            },
            'fin_y_positions': fin_ys,
        }
        devices.append(dev_entry)

    return devices


def generate_calibre_net_query(layout_data: dict) -> dict:
    """
    Simulate Calibre SVDB net query output.
    
    Format mimics:
      calibrequery -net <net_name> -layer ...
    
    For each net, returns the shapes (layer, bbox) that belong to it.
    """
    net_shapes = {}
    
    for net_name in layout_data['nets']:
        net_shapes[net_name] = {
            'type': layout_data['nets'][net_name]['type'],
            'pins': layout_data['nets'][net_name]['pins'],
            'shapes': [],
        }
    
    # Collect shapes tagged with net names
    for layer_name, shape_list in layout_data['shapes'].items():
        for s in shape_list:
            if s['net'] and s['net'] in net_shapes:
                net_shapes[s['net']]['shapes'].append({
                    'layer': layer_name,
                    'x1': s['x1'], 'y1': s['y1'],
                    'x2': s['x2'], 'y2': s['y2'],
                    'desc': s['desc'],
                })
    
    return net_shapes


def generate_bbox_by_layer(layout_data: dict) -> dict:
    """
    Extract all shapes as bbox per layer.
    This mimics what you'd extract from the layout directly.
    """
    result = {}
    for layer_name, shape_list in layout_data['shapes'].items():
        result[layer_name] = [
            {
                'x1': s['x1'], 'y1': s['y1'],
                'x2': s['x2'], 'y2': s['y2'],
                'net': s.get('net', ''),
                'desc': s.get('desc', ''),
            }
            for s in shape_list
        ]
    return result


def generate_cdl(layout_data: dict, filename: str, config=None):
    """Generate a simple CDL (SPICE) netlist."""
    if config is None:
        config = get_tech_config()

    nfin_n = layout_data['params']['nmos_nfin']
    nfin_p = layout_data['params']['pmos_nfin']
    cell_name = f'INV_N{nfin_n}_P{nfin_p}'

    with open(filename, 'w') as f:
        f.write(f"* CDL netlist for {cell_name}\n")
        f.write(f".SUBCKT {cell_name} VDD VSS IN OUT\n")
        f.write(f"MN0 OUT IN VSS VSS nmos_finfet nfin={nfin_n} l={config.POLY_WIDTH}n\n")
        f.write(f"MP0 OUT IN VDD VDD pmos_finfet nfin={nfin_p} l={config.POLY_WIDTH}n\n")
        f.write(f".ENDS {cell_name}\n")
    print(f"  CDL written: {filename}")


def generate_calibre_ixref(layout_data: dict, filename: str):
    """Simulate Calibre HDB ``INSTANCE XREF WRITE`` output.

    Writes an ixf (instance cross-reference) file in file format 1,
    matching what ``calibre -query <svdb_dir>`` would produce for the
    inverter layout. Layout-side ids run M0..M(n-1) (NMOS first, PMOS
    next); source-side ids come from each device's ``name`` field
    (matching the CDL fixture's MN0 / MP0). The PMOS device is flagged
    with the ``X`` swap marker to exercise the parser's swap branch.
    """
    nfin_n = layout_data['params']['nmos_nfin']
    nfin_p = layout_data['params']['pmos_nfin']
    cell_name = f'INV_N{nfin_n}_P{nfin_p}'
    pin_count = 4   # VDD, VSS, IN, OUT

    devices = layout_data['devices']
    with open(filename, 'w') as f:
        f.write('# SVDB: Instance Cross Reference (ixf) (File format 1)\n')
        f.write(f'# SVDB: Layout Primary {cell_name}\n')
        f.write(f'# SVDB: Source Primary {cell_name}\n')
        f.write('# SVDB: Layout system: GDSII\n')
        f.write('# SVDB: Source system: SPICE\n')
        f.write('# SVDB: Generated by Calibre LVS (dummy fixture)\n')
        f.write('# SVDB: End of header.\n')
        f.write(f'{cell_name} {pin_count} {cell_name} {pin_count}\n')
        for layout_idx, dev in enumerate(devices):
            swap = ' X' if dev['type'].lower() == 'pmos' else ''
            f.write(f'0 M{layout_idx} 0 {dev["name"]}{swap}\n')
    print(f"  iXref.temp written: {filename}")


# Net-name ordering used by both the dummy nXref and dummy NET NAMES
# fixtures. Putting it module-level lets the two generators stay
# byte-consistent without duplicating the order in each function. The
# inverter has only external pins (no internal nets), so layout and
# source net names match one-to-one.
DUMMY_NET_ORDER = ['IN', 'OUT', 'VSS', 'VDD']


def generate_calibre_nxref(layout_data: dict, filename: str):
    """Simulate Calibre HDB ``NET XREF WRITE`` output (file format 1).

    Each row maps a layout net to its source-netlist net:
    ``<layout_idx> <layout_net> <source_idx> <source_net>``. The
    cell-summary line carries the ``%`` prefix per format spec. For
    the inverter cell every net is an external pin so layout and
    source names coincide; the renumbering case (``0 2 0 net9``) is
    exercised in unit tests via synthetic input.
    """
    nfin_n = layout_data['params']['nmos_nfin']
    nfin_p = layout_data['params']['pmos_nfin']
    cell_name = f'INV_N{nfin_n}_P{nfin_p}'
    pin_count = 4

    with open(filename, 'w') as f:
        f.write('# SVDB: Net Cross Reference (nxf) (File format 1)\n')
        f.write(f'# SVDB: Layout Primary {cell_name}\n')
        f.write(f'# SVDB: Source Primary {cell_name}\n')
        f.write('# SVDB: Layout system: GDSII\n')
        f.write('# SVDB: Source system: SPICE\n')
        f.write('# SVDB: Generated by Calibre LVS (dummy fixture)\n')
        f.write('# SVDB: End of header.\n')
        f.write(f'% {cell_name} {pin_count} {cell_name} {pin_count}\n')
        # nXref is sorted differently in the committed fixture
        # (VDD/VSS/IN/OUT) for human-readability; the join logic does
        # not depend on row order, so we keep that visual order.
        for net in ['VDD', 'VSS', 'IN', 'OUT']:
            f.write(f'0 {net} 0 {net}\n')
    print(f"  nXref.temp written: {filename}")


def generate_calibre_net_names(layout_data: dict, filename: str,
                                timestamp: str = 'May 07 03:00:00 2026'):
    """Simulate Calibre HDB ``NET NAMES`` query response (stdout-only).

    The output is the verbatim block Calibre would stream to stdout
    between ``Net_Names <id>`` and ``END OF RESPONSE``. Net rows are
    1-indexed in the order specified by :data:`DUMMY_NET_ORDER`; for
    the inverter (4 nets, all external pins), that means
    IN=1, OUT=2, VSS=3, VDD=4.
    """
    count = len(DUMMY_NET_ORDER)
    with open(filename, 'w') as f:
        f.write('Net_Names 20000\n')
        f.write('Nets:\n')
        f.write(f'0 0 {count} {timestamp}\n')
        for name in DUMMY_NET_ORDER:
            f.write(f'{name}\n')
        f.write('END OF RESPONSE\n')
    print(f"  net_names.txt written: {filename}")


# =========================================================
# Main: generate all dummy fixtures
# =========================================================
def generate_all_fixtures(output_dir: str,
                          nmos_nfin_orig: int = 5, pmos_nfin_orig: int = 7,
                          nmos_nfin_target: int = 4, pmos_nfin_target: int = 6,
                          config=None):
    """Generate original and target layout fixtures.

    Args:
        output_dir: Directory to write fixture files.
        nmos_nfin_orig: Original NMOS fin count.
        pmos_nfin_orig: Original PMOS fin count.
        nmos_nfin_target: Target NMOS fin count (after resize).
        pmos_nfin_target: Target PMOS fin count (after resize).
        config: TechConfig instance.
    """
    if config is None:
        config = get_tech_config()

    os.makedirs(output_dir, exist_ok=True)

    # --- GDS truth source path: write GDS first, then read back for bbox ---
    from io_adapters.gds_io import write_gds as gds_write, gds_to_bbox_by_layer

    print("=" * 60)
    print(f"Generating ORIGINAL layout (NMOS={nmos_nfin_orig}fin, PMOS={pmos_nfin_orig}fin)")
    print("=" * 60)
    orig = generate_inverter_layout(nmos_nfin_orig, pmos_nfin_orig, config)

    orig_gds_path = os.path.join(output_dir, 'buffer_original.gds')
    gds_write(orig, orig_gds_path, layer_map=config.LAYER_MAP)
    write_layout_json(orig, os.path.join(output_dir, 'buffer_original.json'))
    generate_cdl(orig, os.path.join(output_dir, 'buffer_original.cdl'), config)

    # Calibre query simulations (dummy LVS output)
    cal_dev = generate_calibre_device_query(orig, config)
    with open(os.path.join(output_dir, 'calibre_device_query.json'), 'w') as f:
        json.dump(cal_dev, f, indent=2)
    print(f"  Calibre device query JSON written")

    cal_net = generate_calibre_net_query(orig)
    with open(os.path.join(output_dir, 'calibre_net_query.json'), 'w') as f:
        json.dump(cal_net, f, indent=2)
    print(f"  Calibre net query JSON written")

    # iXref (instance cross-reference) — only the original layout has
    # an LVS run associated with it. Target is a future-state CDL diff
    # input, not a layout LVS would run against.
    generate_calibre_ixref(orig, os.path.join(output_dir, 'iXref.temp'))

    # nXref (net cross-reference) + NET NAMES (net-index association).
    # Same scope rule: original layout only.
    generate_calibre_nxref(orig, os.path.join(output_dir, 'nXref.temp'))
    generate_calibre_net_names(orig, os.path.join(output_dir, 'net_names.txt'))

    # bbox_by_layer: GDS round-trip (truth source is GDS, not Python dict)
    bbox_data = gds_to_bbox_by_layer(orig_gds_path, layer_map=config.LAYER_MAP)
    with open(os.path.join(output_dir, 'bbox_by_layer.json'), 'w') as f:
        json.dump(bbox_data, f, indent=2)
    print(f"  Bbox-by-layer JSON written (from GDS read-back)")

    print()
    print("=" * 60)
    print(f"Generating TARGET layout (NMOS={nmos_nfin_target}fin, PMOS={pmos_nfin_target}fin)")
    print("=" * 60)
    target = generate_inverter_layout(nmos_nfin_target, pmos_nfin_target, config)

    target_gds_path = os.path.join(output_dir, 'buffer_target.gds')
    gds_write(target, target_gds_path, layer_map=config.LAYER_MAP)
    write_layout_json(target, os.path.join(output_dir, 'buffer_target.json'))
    generate_cdl(target, os.path.join(output_dir, 'buffer_target.cdl'), config)

    print()
    print("All fixtures generated successfully.")
    print(f"Output directory: {output_dir}")
    return orig, target


if __name__ == '__main__':
    fixture_dir = os.path.join(os.path.dirname(__file__), 'fixtures')
    generate_all_fixtures(fixture_dir)
