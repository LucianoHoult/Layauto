"""
Slice 1.6: GDS↔LVS layer-mapping consumption.

Loads the per-GDS-layer ``derived_layers`` map from ``tech/layer_map.yaml``
plus the derived-layer reference registry ``tech/calibre_layer_map.yaml``
(where ``multi_patterning`` colour metadata lives). Joins the two and
exposes a ``LayerMapTable`` that the new annotation pass consumes.

The annotation pass itself is :func:`apply_calibre_layer_overlay`. It runs
*after* the parser has built ``TrackSegment``s (in ``model.nets[*].
segments``) and ``CellOccupancy`` cells (in ``grid.b_tier_cells``), and
stamps per-cell ``device_id`` / ``color`` (and verifies ``net_id``
consistency) from the LVS-side ``device_info.yaml`` / ``net_shapes.yaml``
middle files. The per-layer ``derived_layers`` map tells the pass which
derived-shape sets to query for each GDS layer's cells.

Containment rules:
  * A-tier track segments: segment-center inside derived-shape bbox.
  * B-tier 2D cells: ≥ 50 % intersection-area overlap.

Conflict policy:
  * Two different ``net_id`` values on the same cell → raise
    ``LayerOverlayConflictError`` (real short circuit).
  * Two different A-tier ``device_id`` values on the same cell → raise.
  * Two B-tier ``owner_device_id`` matches → recorded as diffusion
    sharing via ``CellOccupancy.shared_with``, not a conflict.
  * Co-occurrence of ``device_id`` from one derived layer + ``net_id``
    from another on the same cell → allowed (active gate's normal state).

After the per-cell pass, ``_summarise_back_to_shape_record`` derives
best-effort summaries onto ``ShapeRecord.{net_id, device_id}`` so the
load-bearing solver consumers (``core/solver.py::resize_device`` line
527 etc.) keep working without a larger refactor. Shapes whose cells
disagree (cut metal, shared OD) leave the summary ``None``.

Slice scope (1.6): the new pass runs **alongside** the legacy
``apply_lvs_overlay`` for now. Cutover (delete legacy) is a follow-up
slice (1.6b) gated on the parity script in
``tests/unit/test_calibre_layer_map.py``.
"""

import os
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import yaml


class LayerOverlayConflictError(RuntimeError):
    """Two derived layers disagree on a per-cell annotation."""


# =====================================================================
# Loader
# =====================================================================

def load_layer_map_with_derived(
        layer_yaml_path: str,
        calibre_layer_map_yaml_path: Optional[str] = None) -> dict:
    """Load + join ``tech/layer_map.yaml`` and ``tech/calibre_layer_map.yaml``.

    Returns:
        {
          'gds_to_derived': {gds_layer: [{name, carries, color,
                                          exclude_from_grid}, ...]},
          'derived_to_gds': {derived_layer: primary_gds_layer},
          'derived_meta':   {derived_layer: {multi_patterning,
                                              semantic_role, ...}},
          'missing_registry_entries': [str, ...],   # informational
        }

    ``calibre_layer_map_yaml_path=None`` skips the registry load (the
    GDS-only path is still usable; ``derived_meta`` ends up empty).
    """
    with open(layer_yaml_path) as f:
        layer_data = yaml.safe_load(f) or {}
    layers = layer_data.get('layers', [])

    gds_to_derived: Dict[str, List[dict]] = {}
    derived_to_gds: Dict[str, str] = {}
    for L in layers:
        gds_name = L['name']
        derived_list = list(L.get('derived_layers') or [])
        if not derived_list:
            continue
        gds_to_derived[gds_name] = []
        for d in derived_list:
            entry = {
                'name':              d['name'],
                'carries':           list(d.get('carries') or []),
                'color':             d.get('color'),
                'exclude_from_grid': bool(d.get('exclude_from_grid',
                                                 False)),
            }
            gds_to_derived[gds_name].append(entry)
            # First mention wins for the reverse map: each derived
            # layer has one primary GDS source per the user's guidance.
            derived_to_gds.setdefault(d['name'], gds_name)

    derived_meta: Dict[str, dict] = {}
    missing: List[str] = []
    if (calibre_layer_map_yaml_path
            and os.path.exists(calibre_layer_map_yaml_path)):
        with open(calibre_layer_map_yaml_path) as f:
            calibre_data = yaml.safe_load(f) or []
        if isinstance(calibre_data, dict):
            calibre_data = calibre_data.get('derived_layers', [])
        for d in calibre_data:
            derived_meta[d['name']] = {
                'multi_patterning':  d.get('multi_patterning'),
                'semantic_role':     d.get('semantic_role'),
                'exclude_from_grid': bool(d.get('exclude_from_grid',
                                                 False)),
                'derivation_doc':    d.get('derivation_doc'),
                'pin_role_hint':     d.get('pin_role_hint'),
                'device_type_hint':  d.get('device_type_hint'),
            }
        for derived in derived_to_gds:
            if derived not in derived_meta:
                missing.append(derived)

    return {
        'gds_to_derived':           gds_to_derived,
        'derived_to_gds':           derived_to_gds,
        'derived_meta':             derived_meta,
        'missing_registry_entries': missing,
    }


# =====================================================================
# Bbox helpers
# =====================================================================

_BBox = Tuple[float, float, float, float]


def _bbox_um_to_nm(bbox_um: dict) -> _BBox:
    """Convert ``{x1, y1, x2, y2}`` µm dict to a nm tuple."""
    return (bbox_um['x1'] * 1000.0,
            bbox_um['y1'] * 1000.0,
            bbox_um['x2'] * 1000.0,
            bbox_um['y2'] * 1000.0)


def _center_in_bbox(cx: float, cy: float, bbox: _BBox) -> bool:
    bx1, by1, bx2, by2 = bbox
    return bx1 <= cx <= bx2 and by1 <= cy <= by2


def _area_overlap_ratio(cell: _BBox, shape: _BBox) -> float:
    cx1, cy1, cx2, cy2 = cell
    sx1, sy1, sx2, sy2 = shape
    ox1, oy1 = max(cx1, sx1), max(cy1, sy1)
    ox2, oy2 = min(cx2, sx2), min(cy2, sy2)
    if ox2 <= ox1 or oy2 <= oy1:
        return 0.0
    overlap = (ox2 - ox1) * (oy2 - oy1)
    cell_area = (cx2 - cx1) * (cy2 - cy1)
    return overlap / cell_area if cell_area > 0 else 0.0


# =====================================================================
# LVS-side shape index builders
# =====================================================================

def _shapes_by_layer_from_device_info(
        device_info_yaml_path: Optional[str]) -> Dict[str, List[dict]]:
    if (not device_info_yaml_path
            or not os.path.exists(device_info_yaml_path)):
        return {}
    with open(device_info_yaml_path) as f:
        data = yaml.safe_load(f) or {}
    out: Dict[str, List[dict]] = {}
    for dev in data.get('devices', []):
        layout_inst = dev.get('layout_inst')
        for layer in dev.get('layers', []):
            for sh in layer.get('shapes', []):
                out.setdefault(layer['name'], []).append({
                    'bbox_nm':   _bbox_um_to_nm(sh['bbox_um']),
                    'device_id': layout_inst,
                    'net_id':    None,
                })
    return out


def _shapes_by_layer_from_net_shapes(
        net_shapes_yaml_path: Optional[str]) -> Dict[str, List[dict]]:
    if (not net_shapes_yaml_path
            or not os.path.exists(net_shapes_yaml_path)):
        return {}
    with open(net_shapes_yaml_path) as f:
        data = yaml.safe_load(f) or {}
    out: Dict[str, List[dict]] = {}
    for net in data.get('nets', []):
        # schematic_name is the engineer-recognisable string; lvs_name
        # is the LVS-side string (may be numeric). Net.segments today
        # are keyed by schematic_name, so use that.
        net_id = net.get('schematic_name') or net.get('lvs_name')
        for layer in net.get('layers', []):
            for sh in layer.get('shapes', []):
                out.setdefault(layer['name'], []).append({
                    'bbox_nm':   _bbox_um_to_nm(sh['bbox_um']),
                    'device_id': None,
                    'net_id':    net_id,
                })
    return out


def _merge_shape_indexes(*idxs: Dict[str, List[dict]]
                          ) -> Dict[str, List[dict]]:
    out: Dict[str, List[dict]] = {}
    for idx in idxs:
        for k, v in idx.items():
            out.setdefault(k, []).extend(v)
    return out


# =====================================================================
# Per-cell bbox computation
# =====================================================================

def _track_segment_center(grid, seg) -> Tuple[float, float]:
    """Center point of an A-tier TrackSegment in physical (x, y) nm."""
    lg = grid.layers[seg.layer]
    ortho = grid.get_ortho_layer(seg.layer)
    cross = lg.track_to_physical(seg.track_idx)
    along = ortho.track_to_physical(
        (seg.start_anchor + seg.end_anchor) // 2)
    if lg.orientation == 'V':
        return (cross, along)
    return (along, cross)


def _b_tier_cell_bbox(grid, layer: str, ta: int, tb: int) -> _BBox:
    """Physical bbox of a B-tier cell at ``(track_a, track_b)``."""
    ax_a_name, ax_b_name = grid.b_tier_axes[layer]
    lga = grid.layers[ax_a_name]
    lgb = grid.layers[ax_b_name]
    a_center = lga.track_to_physical(ta)
    b_center = lgb.track_to_physical(tb)
    half_a = lga.pitch / 2.0
    half_b = lgb.pitch / 2.0
    if lga.orientation == 'V':
        x_lo, x_hi = a_center - half_a, a_center + half_a
        y_lo, y_hi = b_center - half_b, b_center + half_b
    else:
        x_lo, x_hi = b_center - half_b, b_center + half_b
        y_lo, y_hi = a_center - half_a, a_center + half_a
    return (x_lo, y_lo, x_hi, y_hi)


# =====================================================================
# Per-cell stampers
# =====================================================================

def _stamp_track_segment(seg, derived_entry: dict, shape: dict,
                           coverage: dict) -> None:
    """Stamp annotation onto a TrackSegment per a single matching shape."""
    for field in derived_entry['carries']:
        new_val = shape.get(field)
        if new_val is None:
            continue
        existing = getattr(seg, field, None)
        if existing in (None, ''):
            setattr(seg, field, new_val)
            coverage['stamped'] += 1
        elif existing != new_val:
            raise LayerOverlayConflictError(
                f"TrackSegment {seg!r} field {field!r}: existing "
                f"{existing!r} != new {new_val!r} from derived layer "
                f"{derived_entry['name']!r}"
            )
    if derived_entry.get('color') and getattr(seg, 'color', None) is None:
        seg.color = derived_entry['color']


def _stamp_b_tier_cell(cell, derived_entry: dict, shape: dict,
                         coverage: dict) -> None:
    """Stamp annotation onto a CellOccupancy. ``device_id`` accumulates
    into ``owner_device_id`` + ``shared_with``; ``net_id`` raises on
    conflict."""
    for field in derived_entry['carries']:
        new_val = shape.get(field)
        if new_val is None:
            continue
        if field == 'device_id':
            if cell.owner_device_id is None:
                cell.owner_device_id = new_val
                coverage['stamped'] += 1
            elif cell.owner_device_id == new_val:
                pass
            elif new_val not in cell.shared_with:
                cell.shared_with.append(new_val)
                coverage['shared'] += 1
        else:
            existing = getattr(cell, field, None)
            if existing is None:
                setattr(cell, field, new_val)
                coverage['stamped'] += 1
            elif existing != new_val:
                raise LayerOverlayConflictError(
                    f"CellOccupancy {cell!r} field {field!r}: existing "
                    f"{existing!r} != new {new_val!r} from derived "
                    f"layer {derived_entry['name']!r}"
                )
    if derived_entry.get('color') and getattr(cell, 'color', None) is None:
        cell.color = derived_entry['color']


# =====================================================================
# ShapeRecord summary derivation
# =====================================================================

def _summarise_back_to_shape_record(model, grid) -> None:
    """Set ``ShapeRecord.{net_id, device_id}`` from per-cell consensus.

    Walks every TrackSegment / CellOccupancy that has a ``shape_record``
    backlink and aggregates per-shape sets. Sets the ShapeRecord field
    only when the aggregate has exactly one non-None value (consensus);
    leaves it ``None`` when cells disagree.
    """
    net_by_shape: Dict[int, set] = defaultdict(set)
    dev_by_shape: Dict[int, set] = defaultdict(set)

    def consume(carrier):
        sr = getattr(carrier, 'shape_record', None)
        if sr is None:
            return
        key = id(sr)
        nid = getattr(carrier, 'net_id', None)
        if nid:
            net_by_shape[key].add(nid)
        did = (getattr(carrier, 'device_id', None)
               or getattr(carrier, 'owner_device_id', None))
        if did:
            dev_by_shape[key].add(did)

    for net in model.nets.values():
        for seg in net.segments:
            consume(seg)
    for cells in grid.b_tier_cells.values():
        for cell in cells.values():
            consume(cell)

    for sr in model.shape_pool:
        nets = net_by_shape.get(id(sr), set())
        devs = dev_by_shape.get(id(sr), set())
        # Set net_id consensus; leave existing value if no consensus
        # (legacy apply_lvs_overlay may have stamped it already).
        if len(nets) == 1:
            sr.net_id = next(iter(nets))
        if len(devs) == 1:
            sr.device_id = next(iter(devs))


# =====================================================================
# Top-level pass
# =====================================================================

def apply_calibre_layer_overlay(
        model,
        grid,
        device_info_yaml_path: Optional[str],
        net_shapes_yaml_path: Optional[str],
        layer_map_table: dict,
        *,
        area_overlap_threshold: float = 0.5) -> dict:
    """Stamp per-cell annotations onto the grid from LVS middle files.

    Returns a coverage-stats dict:

        {'stamped': int,        # cell-field stamps applied
         'shared':  int,        # B-tier diffusion-sharing additions
         'cells_visited': int,
         'derived_shape_count': int}
    """
    shape_idx = _merge_shape_indexes(
        _shapes_by_layer_from_device_info(device_info_yaml_path),
        _shapes_by_layer_from_net_shapes(net_shapes_yaml_path),
    )

    gds_to_derived: Dict[str, List[dict]] = (
        layer_map_table.get('gds_to_derived', {}))

    coverage = {
        'stamped':             0,
        'shared':              0,
        'cells_visited':       0,
        'derived_shape_count': sum(len(v) for v in shape_idx.values()),
    }

    # ---- A-tier TrackSegments (iterate per net) ----
    for net in model.nets.values():
        for seg in net.segments:
            derived_entries = gds_to_derived.get(seg.layer, [])
            if not derived_entries:
                continue
            coverage['cells_visited'] += 1
            cx, cy = _track_segment_center(grid, seg)
            for entry in derived_entries:
                if entry['exclude_from_grid']:
                    continue
                for shape in shape_idx.get(entry['name'], []):
                    if _center_in_bbox(cx, cy, shape['bbox_nm']):
                        _stamp_track_segment(seg, entry, shape, coverage)

    # ---- B-tier CellOccupancy ----
    for layer, cells in grid.b_tier_cells.items():
        derived_entries = gds_to_derived.get(layer, [])
        if not derived_entries:
            continue
        if layer not in grid.b_tier_axes:
            continue
        for (ta, tb), cell in cells.items():
            coverage['cells_visited'] += 1
            cell_bbox = _b_tier_cell_bbox(grid, layer, ta, tb)
            for entry in derived_entries:
                if entry['exclude_from_grid']:
                    continue
                for shape in shape_idx.get(entry['name'], []):
                    if (_area_overlap_ratio(cell_bbox, shape['bbox_nm'])
                            >= area_overlap_threshold):
                        _stamp_b_tier_cell(cell, entry, shape, coverage)

    # ---- ShapeRecord summary ----
    _summarise_back_to_shape_record(model, grid)

    return coverage
