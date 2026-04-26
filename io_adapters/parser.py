"""
Parse dummy Calibre query outputs and bbox data into core data structures.

In production, these parsers would be adapted to match actual Calibre SVDB
query output formats. The core/ code they feed into remains unchanged.
"""

import json
import sys
import os
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.data_model import (
    Device, Net, TrackSegment, ViaInstance, LayoutModel,
    EndType, OccupantType, CellState, EMPTY,
)
from core.grid import MultiLayerGrid, create_mvp_grid
from tech.config_loader import get_tech_config


def parse_calibre_device_query(filepath: str) -> List[Device]:
    """
    Parse Calibre device query JSON into Device objects.
    
    Expected JSON format (list of devices):
    [
      {
        "instance": "MN0",
        "device_type": "NMOS",
        "parameters": {"nfin": 5, "nf": 1, "l": 20, "w": 125},
        "pins": {"G": "IN", "D": "OUT", "S": "VSS", "B": "VSS"},
        "bbox": {"x1": 27, "y1": 28, "x2": 81, "y2": 152},
        "fin_y_positions": [40, 65, 90, 115, 140]
      },
      ...
    ]
    """
    with open(filepath) as f:
        data = json.load(f)
    
    devices = []
    for entry in data:
        dev = Device(
            inst_name=entry['instance'],
            dev_type=entry['device_type'].lower(),
            nfin=entry['parameters']['nfin'],
            nf=entry['parameters']['nf'],
            pins=dict(entry['pins']),
            bbox_nm=dict(entry['bbox']),
        )
        # Store raw fin positions for grid mapping later
        dev._raw_fin_y = entry.get('fin_y_positions', [])
        devices.append(dev)
    
    return devices


def parse_calibre_net_query(filepath: str) -> Dict[str, dict]:
    """
    Parse Calibre net query JSON into raw net data.
    
    Returns dict of net_name -> {type, pins, shapes}
    where shapes = [{layer, x1, y1, x2, y2, desc}, ...]
    """
    with open(filepath) as f:
        return json.load(f)


def parse_bbox_by_layer(filepath: str) -> Dict[str, List[dict]]:
    """
    Parse bbox-by-layer JSON.
    
    Returns dict of layer_name -> [{x1, y1, x2, y2, net, desc}, ...]
    """
    with open(filepath) as f:
        return json.load(f)


def build_layout_model(device_query_path: str,
                       net_query_path: str,
                       bbox_path: str,
                       layout_json_path: str = None,
                       config=None) -> Tuple[LayoutModel, MultiLayerGrid]:
    """
    Build complete LayoutModel and grid system from parsed data.

    This is the main entry point for Stage 2.
    Takes raw parsed data -> grid-abstracted LayoutModel.

    Args:
        device_query_path: Path to Calibre device query JSON
        net_query_path: Path to Calibre net query JSON
        bbox_path: Path to bbox-by-layer JSON
        layout_json_path: Optional path to full layout JSON (for cell params)
        config: TechConfig instance (uses default if None)

    Returns:
        (LayoutModel, MultiLayerGrid)
    """
    if config is None:
        config = get_tech_config()

    # --- Parse raw data ---
    devices = parse_calibre_device_query(device_query_path)
    net_data = parse_calibre_net_query(net_query_path)
    bbox_data = parse_bbox_by_layer(bbox_path)

    # --- Extract layout parameters for grid construction ---
    # Get fin positions from devices
    nmos_fin_y = []
    pmos_fin_y = []
    for dev in devices:
        if hasattr(dev, '_raw_fin_y'):
            if dev.dev_type == 'nmos':
                nmos_fin_y = dev._raw_fin_y
            elif dev.dev_type == 'pmos':
                pmos_fin_y = dev._raw_fin_y

    # Get M1 track positions from net_data (calibre_net_query).
    # GDS-sourced bbox_by_layer does not contain net names, so we
    # extract M1 track positions from the net query shapes instead.
    m1_tracks_y = {}
    for net_name, nd in net_data.items():
        for shape in nd.get('shapes', []):
            if shape.get('layer') == 'M1':
                cy = (shape['y1'] + shape['y2']) / 2
                m1_tracks_y[net_name] = int(cy)

    # --- Create grid system ---
    grid = create_mvp_grid(
        config=config,
        nmos_fin_y=nmos_fin_y,
        pmos_fin_y=pmos_fin_y,
        m1_tracks_y=m1_tracks_y,
    )
    
    # --- Map devices to grid coordinates ---
    for dev in devices:
        if hasattr(dev, '_raw_fin_y') and dev._raw_fin_y:
            fin_grid = grid.get_layer('FIN')
            dev.fin_track_indices = [
                fin_grid.physical_to_track(fy) for fy in dev._raw_fin_y
            ]
        
        if dev.bbox_nm:
            poly_grid = grid.get_layer('POLY')
            gate_cx = (dev.bbox_nm['x1'] + dev.bbox_nm['x2']) / 2
            dev.gate_track_idx = poly_grid.physical_to_track(gate_cx)
    
    # --- Build net objects with track segments ---
    nets = {}
    
    for net_name, nd in net_data.items():
        net = Net(
            name=net_name,
            net_type=nd.get('type', 'signal'),
            pins=[(p[0], p[1]) for p in nd.get('pins', [])],
        )
        
        for shape in nd.get('shapes', []):
            layer = shape['layer']
            x1, y1, x2, y2 = shape['x1'], shape['y1'], shape['x2'], shape['y2']
            
            if layer == 'VIA0':
                # Via: map to layer track intersections
                via_cx = (x1 + x2) / 2
                via_cy = (y1 + y2) / 2
                li_grid = grid.get_layer('LI')
                m1_grid = grid.get_layer('M1')
                
                via = ViaInstance(
                    via_layer='VIA0',
                    lower_layer='LI',
                    upper_layer='M1',
                    lower_track_idx=li_grid.physical_to_track(via_cx),
                    upper_track_idx=m1_grid.physical_to_track(via_cy),
                    net_id=net_name,
                    desc=shape.get('desc', ''),
                )
                net.vias.append(via)
            
            elif layer in grid.layers:
                # Wire segment: map to track coordinates
                coords = grid.physical_to_segment_coords(layer, x1, y1, x2, y2)

                seg = TrackSegment(
                    layer=layer,
                    track_idx=coords['track_idx'],
                    start_anchor=coords['start_anchor'],
                    end_anchor=coords['end_anchor'],
                    net_id=net_name,
                    start_offset_nm=coords['start_offset_nm'],
                    end_offset_nm=coords['end_offset_nm'],
                    desc=shape.get('desc', ''),
                    bbox_nm=(int(x1), int(y1), int(x2), int(y2)),
                )
                net.segments.append(seg)
        
        nets[net_name] = net
    
    # --- Get cell dimensions ---
    cell_width = 0
    cell_height = 0
    if layout_json_path:
        with open(layout_json_path) as f:
            lj = json.load(f)
            cell_width = lj.get('cell_bbox', {}).get('x2', 0)
            cell_height = lj.get('cell_bbox', {}).get('y2', 0)
    elif 'BOUNDARY' in bbox_data and bbox_data['BOUNDARY']:
        b = bbox_data['BOUNDARY'][0]
        cell_width = b['x2']
        cell_height = b['y2']
    
    # --- Assemble LayoutModel ---
    model = LayoutModel(
        devices=devices,
        nets=nets,
        cell_name=f"INV_N{devices[0].nfin}_P{devices[1].nfin}" if len(devices) >= 2 else "INV",
        cell_width_nm=cell_width,
        cell_height_nm=cell_height,
    )
    
    return model, grid


def print_model_summary(model: LayoutModel, grid: MultiLayerGrid):
    """Print a readable summary of the parsed layout model."""
    print(model.summary())
    print()
    print(grid.summary())
    print()
    
    print("Track-segment details:")
    for net_name, net in model.nets.items():
        print(f"  Net: {net_name} ({net.net_type})")
        for seg in net.segments:
            print(f"    {seg}")
        for via in net.vias:
            print(f"    {via}")


# =============================================================
# CLI entry point for testing
# =============================================================
if __name__ == '__main__':
    fixture_dir = os.path.join(os.path.dirname(__file__), '..', 'dummy', 'fixtures')
    
    model, grid = build_layout_model(
        device_query_path=os.path.join(fixture_dir, 'calibre_device_query.json'),
        net_query_path=os.path.join(fixture_dir, 'calibre_net_query.json'),
        bbox_path=os.path.join(fixture_dir, 'bbox_by_layer.json'),
        layout_json_path=os.path.join(fixture_dir, 'buffer_original.json'),
    )
    
    print_model_summary(model, grid)
