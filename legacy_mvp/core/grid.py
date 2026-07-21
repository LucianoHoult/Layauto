"""
Multi-layer grid system for FinFET layout abstraction.

Each layer has its own 1D track grid defined by pitch and offset.
A 2D grid cell is identified by (own_track_idx, ortho_track_idx, layer).

Key insight: the along-track dimension of one layer uses the
orthogonal layer's tracks as discrete anchor points.

Layer stack for MVP:
  Layer   Orientation   Pitch    Cross-track axis
  FIN     H             25nm     Y (fin positions)
  POLY    V             54nm     X (gate positions)
  LI      V             54nm     X (contact positions)
  M1      H             36nm     Y (M1 track positions)
  VIA0    -             -        At LI×M1 intersections

M4b cell-grid axis (B-tier layers): in addition to the per-layer 1D
``LayerGrid`` track abstractions used by A-tier layers, ``MultiLayerGrid``
holds a parallel 2D cell-grid for B-tier layers (OD, VIA0, CPO, M0_CUT,
FIN_CUT). A B-tier cell is keyed by ``(layer, track_a, track_b)`` where
``track_a`` and ``track_b`` are integer indices on a pair of orthogonal
A-tier track grids supplied by the parser. The parser's tier-dispatch
work in M4c will project ``ShapeRecord``s on B-tier layers through
``bbox_to_b_tier_cells`` and stamp each cell as a ``CellOccupancy``.
"""

import sys
import os
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.data_model import CellOccupancy


@dataclass
class LayerGrid:
    """
    1D track grid for a single layer.
    
    For Vertical layers (POLY, LI): tracks are at X positions, extending along Y
      - pitch defines X spacing between tracks
      - offset is the X position of track 0
      
    For Horizontal layers (FIN, M1): tracks are at Y positions, extending along X
      - pitch defines Y spacing between tracks
      - offset is the Y position of track 0
    """
    name: str
    pitch: int             # nm between adjacent tracks
    offset: int            # nm, position of track index 0
    orientation: str       # 'H' or 'V'
    min_width: int         # nm, minimum wire width on this layer
    
    # Legal widths (discrete set), code 0 = min width
    legal_widths: List[int] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.legal_widths:
            self.legal_widths = [self.min_width]
    
    def physical_to_track(self, coord_nm: float) -> int:
        """
        Convert physical coordinate to nearest track index.
        
        For V layers: coord_nm is an X coordinate
        For H layers: coord_nm is a Y coordinate
        """
        return round((coord_nm - self.offset) / self.pitch)
    
    def track_to_physical(self, track_idx: int) -> int:
        """
        Convert track index to physical coordinate (center of track).
        """
        return self.offset + track_idx * self.pitch
    
    def is_on_track(self, coord_nm: float, tolerance: float = 0.5) -> bool:
        """Check if a physical coordinate snaps to a track within tolerance."""
        idx = self.physical_to_track(coord_nm)
        back = self.track_to_physical(idx)
        return abs(coord_nm - back) <= tolerance
    
    def track_range(self, coord_min: float, coord_max: float) -> range:
        """
        Get range of track indices covered by a physical coordinate range.
        Returns inclusive range.
        """
        t_min = self.physical_to_track(coord_min)
        t_max = self.physical_to_track(coord_max)
        # Ensure correct order
        if t_min > t_max:
            t_min, t_max = t_max, t_min
        return range(t_min, t_max + 1)


@dataclass
class MultiLayerGrid:
    """
    Complete multi-layer grid system.

    Manages coordinate transformations across all layers
    and computes via landing positions (layer intersections).

    Two parallel grid axes co-exist:
      * ``layers`` / ``ortho_pairs`` — A-tier 1D track grids (existing).
      * ``b_tier_axes`` / ``b_tier_cells`` — M4b B-tier 2D cell grids
        (OD, VIA0, CPO, M0_CUT, FIN_CUT). A B-tier cell is identified by
        ``(layer, track_a, track_b)`` where ``track_a`` and ``track_b``
        are integer indices on a pair of A-tier ``LayerGrid``s registered
        as the layer's axes (e.g., OD might use POLY × FIN; VIA0 uses
        LI × M1). The parser's tier-dispatch work in M4c stamps a
        ``CellOccupancy`` into ``b_tier_cells[layer][(a, b)]`` for every
        cell a B-tier ``ShapeRecord`` covers.

    M4b ships the storage + projection helpers; the parser doesn't yet
    populate them, so the byte-golden pipeline is unaffected.
    """
    layers: Dict[str, LayerGrid] = field(default_factory=dict)

    # Orthogonal layer pairs: for each layer, which layer provides
    # the along-track grid. E.g., LI (vertical) uses M1 (horizontal)
    # tracks as along-track anchors.
    ortho_pairs: Dict[str, str] = field(default_factory=dict)

    # B-tier axis registry (M4b). Maps ``b_tier_layer -> (axis_a_layer,
    # axis_b_layer)`` where the two axis layers are A-tier LayerGrid
    # names whose track indices key the 2D cell grid. Set via
    # ``register_b_tier_axes``; consumed by ``bbox_to_b_tier_cells``.
    b_tier_axes: Dict[str, Tuple[str, str]] = field(default_factory=dict)

    # B-tier cell storage (M4b). ``b_tier_cells[layer][(track_a, track_b)]``
    # is a ``CellOccupancy``. Sparse: only populated cells are present.
    b_tier_cells: Dict[str, Dict[Tuple[int, int], CellOccupancy]] = field(
        default_factory=dict
    )

    def add_layer(self, grid: LayerGrid, ortho_layer: Optional[str] = None):
        """Register a layer grid and its orthogonal partner."""
        self.layers[grid.name] = grid
        if ortho_layer:
            self.ortho_pairs[grid.name] = ortho_layer
    
    def get_layer(self, name: str) -> LayerGrid:
        return self.layers[name]
    
    def get_ortho_layer(self, name: str) -> Optional[LayerGrid]:
        """Get the orthogonal layer that provides along-track anchors."""
        ortho_name = self.ortho_pairs.get(name)
        if ortho_name:
            return self.layers.get(ortho_name)
        return None
    
    def physical_to_segment_coords(self, layer: str,
                                    x1: int, y1: int, 
                                    x2: int, y2: int) -> dict:
        """
        Convert a physical rectangle (bbox) to track-segment coordinates.
        
        Returns:
            {
                'track_idx': int,       # Cross-track position
                'start_anchor': int,    # Along-track start (ortho track idx)
                'end_anchor': int,      # Along-track end (ortho track idx)
                'cross_track_coord': float,  # Physical coord of track center
                'along_start_physical': float,
                'along_end_physical': float,
                'start_offset_nm': int,  # Residual offset at start
                'end_offset_nm': int,    # Residual offset at end
            }
        """
        lg = self.layers[layer]
        ortho = self.get_ortho_layer(layer)
        
        if lg.orientation == 'V':
            # Vertical layer: cross-track = X, along-track = Y
            cross_coord = (x1 + x2) / 2   # X center
            along_min = y1
            along_max = y2
        else:
            # Horizontal layer: cross-track = Y, along-track = X
            cross_coord = (y1 + y2) / 2   # Y center
            along_min = x1
            along_max = x2
        
        track_idx = lg.physical_to_track(cross_coord)
        
        if ortho:
            start_anchor = ortho.physical_to_track(along_min)
            end_anchor = ortho.physical_to_track(along_max)
            
            # Compute residual offsets
            start_snapped = ortho.track_to_physical(start_anchor)
            end_snapped = ortho.track_to_physical(end_anchor)
            start_offset = int(along_min - start_snapped)
            end_offset = int(along_max - end_snapped)
        else:
            # No orthogonal layer defined; use raw coordinates
            start_anchor = int(along_min)
            end_anchor = int(along_max)
            start_offset = 0
            end_offset = 0
        
        # Ensure start <= end
        if start_anchor > end_anchor:
            start_anchor, end_anchor = end_anchor, start_anchor
            start_offset, end_offset = end_offset, start_offset
        
        return {
            'track_idx': track_idx,
            'start_anchor': start_anchor,
            'end_anchor': end_anchor,
            'start_offset_nm': start_offset,
            'end_offset_nm': end_offset,
        }
    
    def segment_to_physical(self, layer: str, track_idx: int,
                            start_anchor: int, end_anchor: int,
                            width_nm: int,
                            start_offset_nm: int = 0,
                            end_offset_nm: int = 0) -> Tuple[int, int, int, int]:
        """
        Convert track-segment coordinates back to physical bbox.
        
        Returns: (x1, y1, x2, y2) in nm
        """
        lg = self.layers[layer]
        ortho = self.get_ortho_layer(layer)
        
        cross_center = lg.track_to_physical(track_idx)
        half_w = width_nm // 2
        
        if ortho:
            along_min = ortho.track_to_physical(start_anchor) + start_offset_nm
            along_max = ortho.track_to_physical(end_anchor) + end_offset_nm
        else:
            along_min = start_anchor + start_offset_nm
            along_max = end_anchor + end_offset_nm
        
        if lg.orientation == 'V':
            return (cross_center - half_w, along_min,
                    cross_center + half_w, along_max)
        else:
            return (along_min, cross_center - half_w,
                    along_max, cross_center + half_w)
    
    def via_position_physical(self, lower_layer: str, upper_layer: str,
                               lower_track_idx: int, 
                               upper_track_idx: int) -> Tuple[int, int]:
        """
        Get physical (x, y) center of a via at the intersection 
        of two layer tracks.
        """
        lower_lg = self.layers[lower_layer]
        upper_lg = self.layers[upper_layer]
        
        lower_coord = lower_lg.track_to_physical(lower_track_idx)
        upper_coord = upper_lg.track_to_physical(upper_track_idx)
        
        if lower_lg.orientation == 'V':
            # Lower is V (x-tracks), Upper is H (y-tracks)
            return (lower_coord, upper_coord)
        else:
            # Lower is H (y-tracks), Upper is V (x-tracks)
            return (upper_coord, lower_coord)
    
    # ---------------------------------------------------------------
    # B-tier cell-grid axis (M4b)
    # ---------------------------------------------------------------

    def is_b_tier_layer(self, layer: str) -> bool:
        """True iff ``layer`` is a B-tier layer per ``tech.layer_map``.

        Deferred import to avoid a module-load-time ``core <-> tech``
        cycle. Mirrors the pattern used by ``CellOccupancy.__post_init__``.
        ``KeyError`` from ``tier_of`` propagates — an unmapped layer is
        a parser bug we want loud.
        """
        from tech.layer_map import tier_of
        return tier_of(layer) == 'B'

    def register_b_tier_axes(self, layer: str,
                              axis_a_layer: str, axis_b_layer: str):
        """Register the two A-tier ``LayerGrid``s that define the cell axes.

        After this call, ``bbox_to_b_tier_cells(layer, ...)`` projects a
        physical bbox to a list of ``(track_a, track_b)`` cell positions
        using ``axis_a_layer`` for the first index and ``axis_b_layer``
        for the second. The two axis layers must already be registered
        via ``add_layer``.

        Raises:
            ValueError: ``layer`` is not B-tier per ``tech.layer_map``,
                or either axis layer is not registered.
        """
        if not self.is_b_tier_layer(layer):
            raise ValueError(
                f"register_b_tier_axes: {layer!r} is not a B-tier layer"
            )
        for axis_name in (axis_a_layer, axis_b_layer):
            if axis_name not in self.layers:
                raise ValueError(
                    f"register_b_tier_axes: axis {axis_name!r} not registered "
                    f"on this MultiLayerGrid (call add_layer first)"
                )
        self.b_tier_axes[layer] = (axis_a_layer, axis_b_layer)
        self.b_tier_cells.setdefault(layer, {})

    def get_b_tier_axes(self, layer: str) -> Tuple[str, str]:
        """Return ``(axis_a_layer, axis_b_layer)`` for a B-tier layer.

        Raises:
            KeyError: layer has not been registered via
                ``register_b_tier_axes``.
        """
        return self.b_tier_axes[layer]

    def bbox_to_b_tier_cells(self, layer: str,
                              x1: int, y1: int,
                              x2: int, y2: int) -> List[Tuple[int, int]]:
        """Project a physical bbox to the B-tier cells it covers.

        For each integer ``(track_a, track_b)`` whose center on the
        registered axis grids falls inside ``[x1, x2] x [y1, y2]``,
        emit a cell tuple. ``track_a`` runs along ``axis_a_layer``'s
        cross-track axis; ``track_b`` runs along ``axis_b_layer``'s.
        For OD (axes POLY × FIN) this means ``track_a`` is the gate
        index and ``track_b`` is the fin index.

        Output is sorted by ``(track_a, track_b)`` for determinism.

        Raises:
            KeyError: ``layer`` has not been registered via
                ``register_b_tier_axes``.
        """
        axis_a_name, axis_b_name = self.b_tier_axes[layer]
        lg_a = self.layers[axis_a_name]
        lg_b = self.layers[axis_b_name]

        # ``axis_a_layer``'s tracks are perpendicular to its orientation
        # — V layers (POLY/LI) have X-coordinate tracks, H layers
        # (FIN/M1) have Y-coordinate tracks. Pick the right pair for
        # each axis.
        a_min, a_max = self._axis_track_range(lg_a, x1, y1, x2, y2)
        b_min, b_max = self._axis_track_range(lg_b, x1, y1, x2, y2)

        cells: List[Tuple[int, int]] = []
        for ta in range(a_min, a_max + 1):
            for tb in range(b_min, b_max + 1):
                cells.append((ta, tb))
        return cells

    @staticmethod
    def _axis_track_range(lg: 'LayerGrid',
                           x1: int, y1: int,
                           x2: int, y2: int) -> Tuple[int, int]:
        """Return ``(t_min, t_max)`` track indices on ``lg`` that the bbox
        covers along ``lg``'s cross-track axis. V layers project the
        X-extent, H layers project the Y-extent."""
        if lg.orientation == 'V':
            return (lg.physical_to_track(x1), lg.physical_to_track(x2))
        else:
            return (lg.physical_to_track(y1), lg.physical_to_track(y2))

    def set_b_tier_cell(self, layer: str,
                         track_a: int, track_b: int,
                         occ: CellOccupancy) -> None:
        """Stamp a ``CellOccupancy`` into the B-tier grid.

        ``occ.layer`` / ``occ.track_a`` / ``occ.track_b`` must agree
        with the explicit arguments — guards against pasting a cell
        record at the wrong key.
        """
        if (occ.layer, occ.track_a, occ.track_b) != (layer, track_a, track_b):
            raise ValueError(
                f"set_b_tier_cell: occ.pos {occ.pos} disagrees with key "
                f"({layer!r}, {track_a}, {track_b})"
            )
        if layer not in self.b_tier_cells:
            self.b_tier_cells[layer] = {}
        self.b_tier_cells[layer][(track_a, track_b)] = occ

    def get_b_tier_cell(self, layer: str,
                         track_a: int, track_b: int) -> Optional[CellOccupancy]:
        """Return the cell at the position, or ``None`` if unstamped."""
        layer_cells = self.b_tier_cells.get(layer)
        if layer_cells is None:
            return None
        return layer_cells.get((track_a, track_b))

    def b_tier_cells_of(self, layer: str) -> Iterable[CellOccupancy]:
        """Iterate the populated cells on a B-tier layer in (a, b) order."""
        layer_cells = self.b_tier_cells.get(layer, {})
        for key in sorted(layer_cells.keys()):
            yield layer_cells[key]

    def summary(self) -> str:
        lines = ["MultiLayerGrid:"]
        for name, lg in self.layers.items():
            ortho = self.ortho_pairs.get(name, '-')
            lines.append(
                f"  {name:6s}: pitch={lg.pitch:3d}nm  orient={lg.orientation}  "
                f"offset={lg.offset:3d}nm  ortho={ortho}"
            )
        if self.b_tier_axes:
            lines.append("  B-tier axes:")
            for layer, (a, b) in self.b_tier_axes.items():
                n_cells = len(self.b_tier_cells.get(layer, {}))
                lines.append(f"    {layer:6s}: {a} x {b}  ({n_cells} cells)")
        return '\n'.join(lines)


# =============================================================
# Factory: create the grid system from tech params
# =============================================================

def create_mvp_grid(config,
                    nmos_fin_y: List[int] = None,
                    pmos_fin_y: List[int] = None,
                    m1_tracks_y: Dict[str, int] = None) -> MultiLayerGrid:
    """
    Create the multi-layer grid for the MVP inverter.

    Args:
        config: TechConfig instance with process parameters.
        nmos_fin_y: Y positions of NMOS fins (to determine FIN grid offset)
        pmos_fin_y: Y positions of PMOS fins
        m1_tracks_y: Dict of M1 track Y positions (to determine M1 offset)

    The offsets are inferred from actual layout positions when available,
    or use defaults when not.
    """
    grid = MultiLayerGrid()

    # --- FIN grid (horizontal, Y-pitch) ---
    fin_offset = nmos_fin_y[0] if nmos_fin_y else 40
    grid.add_layer(
        LayerGrid('FIN', pitch=config.FIN_PITCH, offset=fin_offset,
                  orientation='H', min_width=config.FIN_WIDTH),
        ortho_layer='POLY'
    )

    # --- POLY grid (vertical, X-pitch) ---
    grid.add_layer(
        LayerGrid('POLY', pitch=config.GATE_PITCH, offset=0,
                  orientation='V', min_width=config.POLY_WIDTH),
        ortho_layer='FIN'
    )

    # --- LI grid (vertical, X-pitch at half gate pitch) ---
    li_offset = 0
    grid.add_layer(
        LayerGrid('LI', pitch=config.LI_PITCH, offset=li_offset,
                  orientation='V', min_width=config.LI_WIDTH),
        ortho_layer='M1'
    )

    # --- M1 grid (horizontal, Y-pitch) ---
    m1_offset = config.M1_PITCH // 2
    if m1_tracks_y:
        first_track_y = min(m1_tracks_y.values())
        m1_offset = first_track_y % config.M1_PITCH
    grid.add_layer(
        LayerGrid('M1', pitch=config.M1_PITCH, offset=m1_offset,
                  orientation='H', min_width=config.M1_WIDTH,
                  legal_widths=[config.M1_WIDTH]),
        ortho_layer='LI'
    )

    return grid
