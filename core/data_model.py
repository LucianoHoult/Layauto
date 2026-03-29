"""
Core data structures for the layout abstraction layer.

Three-layer architecture:
  1. Physical coordinates (nm) - for GDS I/O
  2. TrackSegment - primary working representation
  3. CSP GridCell - for constraint propagation

This module defines layers 1 and 2.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List, Dict, Tuple


# =============================================================
# Enums
# =============================================================

class OccupantType(Enum):
    """What type of object occupies a grid cell."""
    EMPTY = auto()
    WIRE = auto()         # Metal or LI routing segment
    VIA = auto()          # Via connecting two layers
    DEVICE_GATE = auto()  # Poly gate over active
    DEVICE_DIFF = auto()  # Fin/OD (diffusion region)
    BLOCKAGE = auto()     # Cannot be used (dummy gate, boundary, etc.)


class EndType(Enum):
    """How a track segment terminates."""
    VIA_LANDING = auto()     # Ends at a via → position snaps to orthogonal track
    PIN_CONNECTION = auto()  # Connects to device pin → position from device geometry
    EXTENSION = auto()       # Line-end extension beyond last via/pin
    OPEN_END = auto()        # Free end (rare, avoid if possible)


class LayerOrientation(Enum):
    """Preferred routing direction for a layer."""
    HORIZONTAL = auto()  # Tracks run along X, pitch defines Y spacing
    VERTICAL = auto()    # Tracks run along Y, pitch defines X spacing


# =============================================================
# Immutable state for grid cells
# =============================================================

@dataclass(frozen=True)
class CellState:
    """
    State of a single grid cell. Immutable (used as dict key / set element).
    
    In CSP terms, this is an element of the domain D(g).
    A grid cell's domain is a set of CellState values it can take.
    """
    occ_type: OccupantType
    net_id: Optional[str] = None      # None for EMPTY/BLOCKAGE
    width_code: int = 0               # Index into layer's legal width set
    is_line_end: bool = False         # True if this cell is at a segment endpoint

    def __repr__(self):
        if self.occ_type == OccupantType.EMPTY:
            return "EMPTY"
        if self.occ_type == OccupantType.BLOCKAGE:
            return "BLOCK"
        parts = [self.occ_type.name]
        if self.net_id:
            parts.append(self.net_id)
        if self.is_line_end:
            parts.append("EOL")
        return f"({','.join(parts)})"


# Singleton for empty state
EMPTY = CellState(OccupantType.EMPTY)
BLOCKAGE = CellState(OccupantType.BLOCKAGE)


# =============================================================
# Width encoding
# =============================================================

@dataclass(frozen=True)
class WidthCode:
    """
    Discrete width encoding for a layer.
    Each layer has a small set of legal widths.
    """
    code: int           # Index (0 = min width)
    physical_nm: int    # Actual width in nm


# =============================================================
# Track Segment - the primary working representation
# =============================================================

@dataclass
class TrackSegment:
    """
    A wire/contact segment on a single track.
    
    The key abstraction: a shape is not a point on the grid,
    but an interval on a track, with discrete attributes.
    
    - Cross-track position: track_idx (fully discrete, defined by layer pitch)
    - Along-track extent: [start_anchor, end_anchor] in orthogonal track indices
    - Width: discrete code from layer's legal width set
    - Endpoints: type + small physical offset for precision
    """
    layer: str                    # Layer name ('LI', 'M1', etc.)
    track_idx: int                # This layer's track index (cross-track position)
    start_anchor: int             # Start position as orthogonal track index
    end_anchor: int               # End position as orthogonal track index
    net_id: str = ''              # Net this segment belongs to
    width_code: int = 0           # Width index
    
    # Endpoint refinement (physical offsets, not part of CSP search)
    start_type: EndType = EndType.OPEN_END
    start_offset_nm: int = 0      # Physical offset from start_anchor position
    end_type: EndType = EndType.OPEN_END
    end_offset_nm: int = 0        # Physical offset from end_anchor position
    
    # Metadata
    desc: str = ''                # Description for debugging
    
    @property
    def span(self) -> range:
        """Orthogonal track indices covered by this segment (inclusive)."""
        return range(self.start_anchor, self.end_anchor + 1)
    
    @property
    def length_tracks(self) -> int:
        """Length in orthogonal track units."""
        return self.end_anchor - self.start_anchor
    
    def __repr__(self):
        return (f"Seg({self.layer} t{self.track_idx} "
                f"[{self.start_anchor}→{self.end_anchor}] "
                f"net={self.net_id})")


# =============================================================
# Via representation
# =============================================================

@dataclass
class ViaInstance:
    """
    A via connecting two adjacent layers.
    Position defined by the intersection of tracks from each layer.
    """
    via_layer: str               # E.g., 'VIA0'
    lower_layer: str             # E.g., 'LI'
    upper_layer: str             # E.g., 'M1'
    lower_track_idx: int         # Track index on lower layer
    upper_track_idx: int         # Track index on upper layer
    net_id: str = ''
    desc: str = ''
    
    def __repr__(self):
        return (f"Via({self.via_layer} {self.lower_layer}:t{self.lower_track_idx}"
                f"→{self.upper_layer}:t{self.upper_track_idx} "
                f"net={self.net_id})")


# =============================================================
# Device representation
# =============================================================

@dataclass
class Device:
    """
    A transistor device in the layout.
    """
    inst_name: str               # Instance name (e.g., 'MN0')
    dev_type: str                # 'nmos' or 'pmos'
    nfin: int                    # Number of fins
    nf: int                      # Number of fingers
    
    # Pin-to-net mapping
    pins: Dict[str, str] = field(default_factory=dict)  # {'G':'IN', 'D':'OUT', ...}
    
    # Physical info (for cross-reference)
    gate_track_idx: int = 0      # Gate's track index on poly grid
    fin_track_indices: List[int] = field(default_factory=list)  # Fin track indices
    
    # Bounding box in physical coords (for reference)
    bbox_nm: Optional[Dict] = None
    
    def __repr__(self):
        return f"Dev({self.inst_name} {self.dev_type} nfin={self.nfin})"


# =============================================================
# Net representation
# =============================================================

@dataclass
class Net:
    """
    A net (electrical connection) in the layout.
    Composed of segments on various layers connected by vias.
    """
    name: str
    net_type: str = 'signal'     # 'signal', 'power', 'clock'
    
    # Connected device pins
    pins: List[Tuple[str, str]] = field(default_factory=list)  # [(dev_name, pin_name), ...]
    
    # Layout representation
    segments: List[TrackSegment] = field(default_factory=list)
    vias: List[ViaInstance] = field(default_factory=list)
    
    def __repr__(self):
        return (f"Net({self.name} {self.net_type} "
                f"segs={len(self.segments)} vias={len(self.vias)})")


# =============================================================
# Complete layout model
# =============================================================

@dataclass
class LayoutModel:
    """
    Complete abstracted layout representation.
    This is the central data structure that CSP operates on.
    """
    devices: List[Device] = field(default_factory=list)
    nets: Dict[str, Net] = field(default_factory=dict)
    
    # Cell-level info
    cell_name: str = ''
    cell_width_nm: int = 0
    cell_height_nm: int = 0
    
    def get_device(self, name: str) -> Optional[Device]:
        for d in self.devices:
            if d.inst_name == name:
                return d
        return None
    
    def get_net(self, name: str) -> Optional[Net]:
        return self.nets.get(name)
    
    def summary(self) -> str:
        lines = [f"LayoutModel: {self.cell_name}"]
        lines.append(f"  Cell: {self.cell_width_nm}nm x {self.cell_height_nm}nm")
        lines.append(f"  Devices: {len(self.devices)}")
        for d in self.devices:
            lines.append(f"    {d}")
        lines.append(f"  Nets: {len(self.nets)}")
        for n in self.nets.values():
            lines.append(f"    {n}")
        return '\n'.join(lines)
