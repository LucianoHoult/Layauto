"""
Parse dummy Calibre query outputs and bbox data into core data structures.

In production, these parsers would be adapted to match actual Calibre SVDB
query output formats. The core/ code they feed into remains unchanged.

M3 (see ``docs/architecture_roadmap.md`` §A): the parser is inverted from
*net-primary* to *shape_pool-primary*. ``parse_bbox_by_layer`` is now the
authoritative geometric pass — every GDS rectangle becomes a
``ShapeRecord``. ``parse_calibre_net_query`` is applied as an
**annotation overlay**: it stamps ``net_id`` / ``device_id`` / ``pin_role``
onto matching shapes, but cannot create geometry. Shapes that LVS does
not cover stay in the pool as unannotated records and (for CSP-modelled
layers) are projected as ``OccupantType.BLOCKAGE`` by the solver.
"""

import json
import sys
import os
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.data_model import (
    Device, Net, ShapeRecord, TrackSegment, ViaInstance, LayoutModel,
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


# =============================================================
# M3: shape_pool-primary helpers
# =============================================================
#
# Inversion contract:
#   build_shape_pool: bbox_data -> List[ShapeRecord], geometry-only.
#   apply_lvs_overlay: stamps net_id / device_id / pin_role onto matching
#     records by (layer, bbox) key. Records that no LVS shape mentions
#     stay unannotated. Conservative-defaults rule (§D): no traversal,
#     no silent merges.

def build_shape_pool(bbox_data: Dict[str, List[dict]]) -> List[ShapeRecord]:
    """Build the geometric ``ShapeRecord`` pool from GDS bbox-by-layer data.

    No annotation is applied here — every record starts with
    ``net_id=None``. That's the LVS overlay's job (see
    ``apply_lvs_overlay``).
    """
    pool: List[ShapeRecord] = []
    for layer, shapes in bbox_data.items():
        for s in shapes:
            pool.append(ShapeRecord(
                layer=layer,
                bbox_nm=(int(s['x1']), int(s['y1']),
                         int(s['x2']), int(s['y2'])),
                desc=s.get('desc', ''),
            ))
    return pool


def _device_pin_lookup(devices: List[Device]) -> Dict[Tuple[str, str], str]:
    """Map ``(device_inst, net_name) -> pin_role`` from Device.pins."""
    lookup: Dict[Tuple[str, str], str] = {}
    for dev in devices:
        for pin_role, net_name in dev.pins.items():
            # Multiple pins on the same device can map to the same net
            # (e.g. S and B both on VSS). Last writer wins; for the MVP
            # this is acceptable since pin_role is an annotation hint.
            lookup[(dev.inst_name, net_name)] = pin_role
    return lookup


def apply_lvs_overlay(pool: List[ShapeRecord],
                      net_data: Dict[str, dict],
                      devices: List[Device]) -> Dict[str, int]:
    """Stamp ``net_id`` / ``device_id`` / ``pin_role`` onto matching records.

    Matches by ``(layer, bbox_nm)`` — the same key the GDS round-trip uses,
    so by construction LVS shapes either align exactly with a GDS shape or
    they don't. Returns the per-net count of matched shapes (diagnostic
    for the coverage report).
    """
    by_key: Dict[Tuple[str, Tuple[int, int, int, int]], ShapeRecord] = {}
    for sr in pool:
        by_key[(sr.layer, sr.bbox_nm)] = sr

    pin_lookup = _device_pin_lookup(devices)
    matched_per_net: Dict[str, int] = {}

    for net_name, nd in net_data.items():
        # Pick a representative device for this net (first pin entry that
        # the device list resolves). This is best-effort metadata — the
        # B-tier owner_device_id work in M4 supersedes it once
        # CellOccupancy lands.
        owner_device: Optional[str] = None
        for dev_name, _pin in nd.get('pins', []):
            owner_device = dev_name
            break

        for shape in nd.get('shapes', []):
            layer = shape['layer']
            key = (
                layer,
                (int(shape['x1']), int(shape['y1']),
                 int(shape['x2']), int(shape['y2'])),
            )
            sr = by_key.get(key)
            if sr is None:
                # LVS reports a shape that the GDS pool does not know
                # about — log but don't fabricate. M3 conservative rule:
                # don't auto-merge, don't traverse, don't silently delete.
                continue
            sr.net_id = net_name
            if owner_device:
                sr.device_id = owner_device
                sr.pin_role = pin_lookup.get((owner_device, net_name))
            matched_per_net[net_name] = matched_per_net.get(net_name, 0) + 1

    return matched_per_net


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

    # --- M3: build geometric shape_pool first (GDS truth) ---
    shape_pool = build_shape_pool(bbox_data)
    apply_lvs_overlay(shape_pool, net_data, devices)
    # Index for stamping the per-segment backlink below.
    pool_by_key = {(sr.layer, sr.bbox_nm): sr for sr in shape_pool}

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

                bbox_key = (int(x1), int(y1), int(x2), int(y2))
                seg = TrackSegment(
                    layer=layer,
                    track_idx=coords['track_idx'],
                    start_anchor=coords['start_anchor'],
                    end_anchor=coords['end_anchor'],
                    net_id=net_name,
                    start_offset_nm=coords['start_offset_nm'],
                    end_offset_nm=coords['end_offset_nm'],
                    desc=shape.get('desc', ''),
                    bbox_nm=bbox_key,
                    shape_record=pool_by_key.get((layer, bbox_key)),
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
        shape_pool=shape_pool,
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
