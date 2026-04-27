"""
GDS layer/datatype mapping for the dummy process.

In production, these would come from the foundry's layer map file.
For the dummy, we assign simple sequential numbers.
"""

from typing import Tuple

# (layer_number, datatype)
LAYER_MAP = {
    'FIN':      (1, 0),    # Fin / Active (OD) 
    'POLY':     (2, 0),    # Poly gate
    'LI':       (3, 0),    # Local Interconnect
    'VIA0':     (4, 0),    # Via0 (LI to M1)
    'M1':       (5, 0),    # Metal 1
    'OD':       (6, 0),    # Active region (continuous OD block)
    'NWELL':    (7, 0),    # N-well (for PMOS)
    'BOUNDARY': (10, 0),   # Cell boundary
}

# Reverse lookup
GDS_TO_LAYER = {v: k for k, v in LAYER_MAP.items()}

# Display colors for visualization (R, G, B, alpha)
LAYER_COLORS = {
    'FIN':      (0.2, 0.8, 0.2, 0.5),   # Green
    'POLY':     (0.8, 0.2, 0.2, 0.6),   # Red
    'LI':       (0.2, 0.2, 0.9, 0.5),   # Blue
    'VIA0':     (0.9, 0.9, 0.0, 0.8),   # Yellow
    'M1':       (0.8, 0.4, 0.0, 0.5),   # Orange
    'OD':       (0.2, 0.6, 0.2, 0.2),   # Light green
    'NWELL':    (0.6, 0.6, 0.6, 0.1),   # Gray
    'BOUNDARY': (0.5, 0.5, 0.5, 0.3),   # Gray
}


# =============================================================
# Tier markers (M4a)
# =============================================================
#
# Per ``docs/architecture_roadmap.md`` §B, layers are dispatched by
# *tier* — physical role determines the right abstraction:
#
#   A  — 1D track  (FIN, POLY, LI, M1)            -> ``TrackSegment`` + CSP
#   B  — 2D cell   (OD, VIA0, CPO, M0_CUT, FIN_CUT) -> ``CellOccupancy`` + CSP
#   C1 — derived   (NWELL, VT, PP, NP, BOUNDARY, DNW) -> M5 derivator, no grid
#   C2 — annotation (DIODE, ESD, TEXT)            -> direct shape edit, no grid
#
# This table is the M4a seam — it is *consulted* here so M4b/c parser
# tier-dispatch and the M5 derivator gate know where each layer lives,
# but no current pipeline path keys off it. CPO / M0_CUT / FIN_CUT,
# VT / PP / NP / DNW, DIODE / ESD / TEXT do not yet have GDS numbers
# in ``LAYER_MAP`` — they are listed below to lock in tier intent
# before geometry shows up.

# Possible tier values, in dependency order.
TIERS = ('A', 'B', 'C1', 'C2')

# Layer-name -> tier marker. Every layer that the parser may encounter
# must appear here, including layers without a ``LAYER_MAP`` entry yet
# (so M4b's tier dispatch can fail-loud on an unmapped layer).
LAYER_TIER = {
    # A — 1D track
    'FIN':      'A',
    'POLY':     'A',
    'LI':       'A',
    'M1':       'A',
    # B — 2D cell
    'OD':       'B',
    'VIA0':     'B',
    'CPO':      'B',   # poly cut
    'M0_CUT':   'B',   # M0 cut
    'FIN_CUT':  'B',   # fin cut
    # C1 — derived (M5 derivator)
    'NWELL':    'C1',
    'VT':       'C1',
    'PP':       'C1',
    'NP':       'C1',
    'BOUNDARY': 'C1',
    'DNW':      'C1',
    # C2 — editable annotation, never enters CSP
    'DIODE':    'C2',
    'ESD':      'C2',
    'TEXT':     'C2',
}

# Subsets exposed for tier dispatch in M4b/c and the M5 derivator.
A_TIER_LAYERS = tuple(L for L, t in LAYER_TIER.items() if t == 'A')
B_TIER_LAYERS = tuple(L for L, t in LAYER_TIER.items() if t == 'B')
C1_TIER_LAYERS = tuple(L for L, t in LAYER_TIER.items() if t == 'C1')
C2_TIER_LAYERS = tuple(L for L, t in LAYER_TIER.items() if t == 'C2')

# Cut layers (subset of B-tier) — distinguished because the CSP
# net-equivalence union-find treats CUT cells as hard barriers.
CUT_LAYERS = ('CPO', 'M0_CUT', 'FIN_CUT')


def tier_of(layer: str) -> str:
    """Return the tier marker for ``layer``.

    Raises ``KeyError`` rather than returning ``None`` — an unmapped
    layer is a parser bug we want to surface loudly so M4b/c can keep
    its tier-dispatch table honest.
    """
    return LAYER_TIER[layer]


def layers_in_tier(tier: str) -> Tuple[str, ...]:
    """Return all layer names in the given tier (sorted by ``LAYER_TIER`` insertion order)."""
    if tier not in TIERS:
        raise ValueError(
            f"unknown tier {tier!r}; expected one of {TIERS}"
        )
    return tuple(L for L, t in LAYER_TIER.items() if t == tier)


def is_cut_layer(layer: str) -> bool:
    """True iff ``layer`` is a cut layer (CPO / M0_CUT / FIN_CUT)."""
    return layer in CUT_LAYERS
