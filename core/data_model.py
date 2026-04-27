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
    DEVICE_GATE = auto()  # Poly gate over active (B-tier; activated in M4)
    DEVICE_DIFF = auto()  # Fin/OD (diffusion region; activated in M4)
    BLOCKAGE = auto()     # Cannot be used (dummy gate, boundary, etc.)
    # M4a seam: CPO / M0_CUT / FIN_CUT shapes occupy cells as cutters that
    # break net-equivalence across the cut location. The engine will treat
    # CUT as a hard barrier in the union-find work landing in M4b.
    CUT = auto()


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
# Shape record — geometric source of truth (M3)
# =============================================================
#
# Per docs/architecture_roadmap.md §A: GDS shape_pool is geometric truth,
# CDL Device/Net is semantic truth, LVS is incomplete annotation overlay.
# Every shape parsed from GDS lives in LayoutModel.shape_pool as a
# ShapeRecord. LVS net data stamps net_id / device_id / pin_role onto the
# matching record; shapes that LVS does not cover stay unannotated and
# (for CSP-modelled layers) project as OccupantType.BLOCKAGE.

@dataclass
class ShapeRecord:
    """A single rectangular shape from the GDS, with optional LVS overlay.

    ``layer`` + ``bbox_nm`` are the geometric truth. The other fields are
    annotation written by LVS or by downstream macros / derivators:

    - ``net_id`` / ``device_id`` / ``pin_role``: LVS overlay. ``net_id is
      None`` means LVS provided no annotation for this shape (filler,
      ESD, hand-edits, dummy gates, …). Per the conservative-defaults
      rule (§D), unannotated shapes are not silently merged or deleted.
    - ``provenance``: backlink string identifying which L3 macro / L2 op /
      derivator emitted or last touched this shape. Used by M7
      DRC/LVS-feedback closure to localise responsibility for a violation.
    - ``is_derived``: True for C1 markings synthesised by the M5 derivator
      (NWELL / VT / PP / NP / BOUNDARY / DNW). The decoder rejects direct
      edits to derived shapes once M5 lands. The flag is added in M3 so
      the seam exists when the derivator does.
    - ``suspect_tags``: cross-check labels like ``SUSPECT_CONNECTED_TO_VSS``
      assigned by the parser when an unannotated shape geometrically
      overlaps multiple LVS-tagged neighbours. Populated lazily when an
      ambiguity actually shows up; empty for the MVP fixture today.
    """
    layer: str
    bbox_nm: Tuple[int, int, int, int]   # (x1, y1, x2, y2)
    desc: str = ''
    net_id: Optional[str] = None
    device_id: Optional[str] = None
    pin_role: Optional[str] = None       # 'G' / 'D' / 'S' / 'B'
    is_derived: bool = False
    provenance: Optional[str] = None
    suspect_tags: List[str] = field(default_factory=list)

    @property
    def is_annotated(self) -> bool:
        """True iff LVS attached a net_id (annotation overlay covered it)."""
        return self.net_id is not None

    def __repr__(self):
        tag = self.net_id if self.net_id else '<unannotated>'
        return f"Shape({self.layer} {self.bbox_nm} net={tag})"


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
# Cell Occupancy — B-tier 2D-grid record (M4a)
# =============================================================
#
# Per docs/architecture_roadmap.md §B, B-tier layers (OD, VIA0, CPO,
# M0_CUT, FIN_CUT) are 2D-cell, not 1D-track. Each cell is keyed by a
# pair of orthogonal track indices (track_a, track_b) on its layer's
# tier-B grid. OD cells additionally carry diffusion-sharing metadata:
# ``owner_device_id`` is the primary device that owns the cell, and
# ``shared_with`` lists secondary devices that physically share the
# diffusion. SKILL/GDS still emits a single OD shape per contiguous
# cell run regardless of how many devices share it.
#
# CUT cells use ``occ_type=OccupantType.CUT``; ``owner_device_id`` /
# ``shared_with`` are unused for them (left as defaults).
#
# This dataclass is the M4a seam — it is *defined* here so that the
# M4b CSP-engine work, the M4c parser projection, and the M4d
# diffusion-share L2 op (``mark_shared_diffusion``) all have a stable
# target type. M4a does not yet wire it into the parser or engine, so
# ``LayoutModel`` still presents only ``shape_pool`` + ``nets`` to
# downstream code; the byte-golden pipeline is unaffected.

@dataclass
class CellOccupancy:
    """A single B-tier (2D) cell occupant.

    Position is identified by the layer plus a pair of orthogonal track
    indices ``(track_a, track_b)``. ``track_a`` is the layer's own track
    (cross-track for V layers, X-track for H layers); ``track_b`` is the
    orthogonal partner track that anchors the along-track position. This
    mirrors the M4 grid convention: a B-tier cell is a 2D rectangle, not a
    1D interval.

    For OD cells, ``owner_device_id`` is the primary device's
    ``Device.inst_name``; ``shared_with`` lists secondary devices that
    physically share the diffusion through this cell. Two adjacent gates
    that share S/D have the OD cells between them carrying both devices.

    For CUT cells (CPO / M0_CUT / FIN_CUT), ``occ_type`` is
    ``OccupantType.CUT``; ``owner_device_id`` / ``shared_with`` are unused
    and stay at their defaults. The CSP engine's net-equivalence
    union-find (M4b) will treat a CUT as a hard barrier between adjacent
    cells of the cut layer.

    The ``shape_record`` backlink mirrors the ``TrackSegment.shape_record``
    seam from M3: when the parser projects a B-tier ``ShapeRecord`` into a
    set of ``CellOccupancy`` records, every cell points back at the
    geometric source of truth for SKILL/DRC provenance closure (M7).
    """
    layer: str
    track_a: int
    track_b: int
    occ_type: OccupantType
    net_id: Optional[str] = None
    owner_device_id: Optional[str] = None
    shared_with: List[str] = field(default_factory=list)
    shape_record: Optional['ShapeRecord'] = None

    def __post_init__(self):
        if self.occ_type not in (
            OccupantType.DEVICE_DIFF,
            OccupantType.DEVICE_GATE,
            OccupantType.VIA,
            OccupantType.CUT,
            OccupantType.BLOCKAGE,
            OccupantType.EMPTY,
        ):
            raise ValueError(
                f"CellOccupancy is for B-tier occupants; got {self.occ_type!r}"
            )

    @property
    def pos(self) -> Tuple[str, int, int]:
        """``(layer, track_a, track_b)`` — the canonical grid key."""
        return (self.layer, self.track_a, self.track_b)

    def add_sharer(self, device_inst: str) -> bool:
        """Append ``device_inst`` to ``shared_with`` if not already present.

        Returns ``True`` if the list grew, ``False`` if it was a no-op.
        Refuses to share if the cell has no primary owner (caller must
        set ``owner_device_id`` first), since "shared with whom?" is
        ambiguous without an owner.
        """
        if self.owner_device_id is None:
            raise ValueError(
                f"{self!r} has no owner_device_id; cannot record a sharer"
            )
        if device_inst == self.owner_device_id:
            return False
        if device_inst in self.shared_with:
            return False
        self.shared_with.append(device_inst)
        return True

    def remove_sharer(self, device_inst: str) -> bool:
        """Remove ``device_inst`` from ``shared_with``. Returns whether it shrank."""
        if device_inst in self.shared_with:
            self.shared_with.remove(device_inst)
            return True
        return False

    def __repr__(self):
        owner = self.owner_device_id or '-'
        extra = f"+{','.join(self.shared_with)}" if self.shared_with else ''
        return (f"Cell({self.layer} ({self.track_a},{self.track_b}) "
                f"{self.occ_type.name} owner={owner}{extra})")


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
    # Original physical bbox (x1, y1, x2, y2) as parsed from the input
    # layout. Stored verbatim so L3 macros can emit ``EditOp.old_bbox``
    # that matches the layout's exact pixel-accurate rectangle, avoiding
    # half-width rounding drift on odd-width layers (e.g. LI = 17 nm).
    # M3 added ``shape_record`` as the canonical backlink; ``bbox_nm`` is
    # kept as a denormalised cache so byte-golden writeback paths and any
    # consumer that pre-dates M3 still work.
    bbox_nm: Optional[Tuple[int, int, int, int]] = None
    # M3 backlink: when the parser builds a TrackSegment from an LVS net
    # shape, it stamps the matching ShapeRecord here. Future milestones
    # (M4 cell occupancy, M5 derivator, M7 SKILL/DRC closure) walk this
    # link to identify the geometric source-of-truth shape and its
    # provenance. ``Optional`` because legacy callers can still build a
    # TrackSegment directly without going through the parser.
    shape_record: Optional['ShapeRecord'] = None
    
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

    # M3: GDS shape_pool — geometric source of truth. Built first by the
    # parser, then LVS net data is applied as an annotation overlay. Every
    # GDS rectangle has exactly one ShapeRecord here, regardless of LVS
    # coverage. See docs/architecture_roadmap.md §A and §C.
    shape_pool: List[ShapeRecord] = field(default_factory=list)

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
    
    def annotation_coverage(self) -> Dict[str, Dict[str, int]]:
        """Per-layer LVS annotation coverage stats over shape_pool.

        Returns ``{layer: {'total': N, 'annotated': K, 'unannotated': N-K}}``
        for every layer present in shape_pool. Empty dict if shape_pool is
        empty (legacy callers that bypassed the parser).
        """
        stats: Dict[str, Dict[str, int]] = {}
        for sr in self.shape_pool:
            entry = stats.setdefault(
                sr.layer, {'total': 0, 'annotated': 0, 'unannotated': 0}
            )
            entry['total'] += 1
            if sr.is_annotated:
                entry['annotated'] += 1
            else:
                entry['unannotated'] += 1
        return stats

    def summary(self) -> str:
        lines = [f"LayoutModel: {self.cell_name}"]
        lines.append(f"  Cell: {self.cell_width_nm}nm x {self.cell_height_nm}nm")
        lines.append(f"  Devices: {len(self.devices)}")
        for d in self.devices:
            lines.append(f"    {d}")
        lines.append(f"  Nets: {len(self.nets)}")
        for n in self.nets.values():
            lines.append(f"    {n}")
        if self.shape_pool:
            cov = self.annotation_coverage()
            total = sum(v['total'] for v in cov.values())
            unann = sum(v['unannotated'] for v in cov.values())
            lines.append(f"  Shape pool: {total} shapes, {unann} unannotated")
        return '\n'.join(lines)
