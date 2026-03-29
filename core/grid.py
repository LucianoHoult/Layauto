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
"""

import sys
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from tech.tech_params import (
    FIN_PITCH, GATE_PITCH, LI_PITCH, M1_PITCH,
    FIN_WIDTH, POLY_WIDTH, LI_WIDTH, M1_WIDTH,
)


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
    """
    layers: Dict[str, LayerGrid] = field(default_factory=dict)
    
    # Orthogonal layer pairs: for each layer, which layer provides
    # the along-track grid. E.g., LI (vertical) uses M1 (horizontal)
    # tracks as along-track anchors.
    ortho_pairs: Dict[str, str] = field(default_factory=dict)
    
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
    
    def summary(self) -> str:
        lines = ["MultiLayerGrid:"]
        for name, lg in self.layers.items():
            ortho = self.ortho_pairs.get(name, '-')
            lines.append(
                f"  {name:6s}: pitch={lg.pitch:3d}nm  orient={lg.orientation}  "
                f"offset={lg.offset:3d}nm  ortho={ortho}"
            )
        return '\n'.join(lines)


# =============================================================
# Factory: create the grid system from tech params
# =============================================================

def create_mvp_grid(nmos_fin_y: List[int] = None,
                    pmos_fin_y: List[int] = None,
                    m1_tracks_y: Dict[str, int] = None) -> MultiLayerGrid:
    """
    Create the multi-layer grid for the MVP inverter.
    
    Args:
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
        LayerGrid('FIN', pitch=FIN_PITCH, offset=fin_offset,
                  orientation='H', min_width=7),
        ortho_layer='POLY'  # Along-track anchors from POLY grid
    )
    
    # --- POLY grid (vertical, X-pitch) ---
    grid.add_layer(
        LayerGrid('POLY', pitch=GATE_PITCH, offset=0,
                  orientation='V', min_width=POLY_WIDTH),
        ortho_layer='FIN'  # Along-track anchors from FIN grid
    )
    
    # --- LI grid (vertical, X-pitch at half gate pitch) ---
    # With LI_PITCH = 27nm (half CPP), track positions are:
    #   t0=0 (dummy_L), t1=27 (S/D), t2=54 (gate), t3=81 (S/D), t4=108 (dummy_R)
    # This covers both S/D contacts and gate contacts on one grid.
    li_offset = 0
    grid.add_layer(
        LayerGrid('LI', pitch=LI_PITCH, offset=li_offset,
                  orientation='V', min_width=LI_WIDTH),
        ortho_layer='M1'  # Along-track anchors from M1 tracks
    )
    
    # --- M1 grid (horizontal, Y-pitch) ---
    m1_offset = M1_PITCH // 2  # = 18nm
    if m1_tracks_y:
        # Infer offset from actual track positions
        first_track_y = min(m1_tracks_y.values())
        m1_offset = first_track_y % M1_PITCH
    grid.add_layer(
        LayerGrid('M1', pitch=M1_PITCH, offset=m1_offset,
                  orientation='H', min_width=M1_WIDTH,
                  legal_widths=[M1_WIDTH]),
        ortho_layer='LI'  # Along-track anchors from LI tracks
    )
    
    return grid
