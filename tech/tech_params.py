"""
Dummy technology parameters for a 7nm-class FinFET process.

Values are simplified but proportionally realistic.
All dimensions in nanometers (nm).

Layer orientation convention:
  - V (Vertical) = runs along Y axis
  - H (Horizontal) = runs along X axis

Grid convention:
  - Each layer has a pitch that defines its track grid
  - For V layers: pitch is in X direction, tracks run along Y
  - For H layers: pitch is in Y direction, tracks run along X

Cross-reference to real process concepts:
  - FIN:  Fin/Active (OD) stripes, horizontal
  - POLY: Gate poly, vertical
  - LI:   Local Interconnect (M0 / LIG), vertical, same dir as poly
  - VIA0: Via connecting LI to M1
  - M1:   First metal, horizontal
"""


# =============================================================
# Pitch definitions (nm)
# =============================================================
FIN_PITCH = 25          # Fin-to-fin pitch (Y direction)
GATE_PITCH = 54         # Contacted poly pitch / CPP (X direction)
LI_PITCH = 27           # LI track pitch (X direction, half gate pitch)
                        # This covers both S/D contacts (between gates)
                        # and gate contacts (at gate positions)
M1_PITCH = 36           # M1 track pitch (Y direction)

# =============================================================
# Width definitions (nm)
# =============================================================
FIN_WIDTH = 7           # Fin width
POLY_WIDTH = 20         # Gate poly width
LI_WIDTH = 17           # LI minimum width
M1_WIDTH = 20           # M1 minimum width (only min-width used in MVP)

# =============================================================
# Via dimensions (nm)
# =============================================================
VIA0_WIDTH = 17          # Via0 width (X)
VIA0_HEIGHT = 17         # Via0 height (Y)

# =============================================================
# Spacing rules (nm) - the DRC subset for MVP
# =============================================================
LI_MIN_SPACING = 17      # LI same-layer min space
M1_MIN_SPACING = 16      # M1 same-layer min space
VIA0_MIN_SPACING = 20    # Via0 to Via0 min space (same layer)

# =============================================================
# Enclosure rules (nm)
# =============================================================
VIA0_ENC_BY_LI_X = 1     # Via0 enclosure by LI in X (along LI width)
VIA0_ENC_BY_LI_Y = 5     # Via0 enclosure by LI in Y (along LI length)
VIA0_ENC_BY_M1_X = 5     # Via0 enclosure by M1 in X (along M1 length)
VIA0_ENC_BY_M1_Y = 1     # Via0 enclosure by M1 in Y (along M1 width)

# =============================================================
# OD (active region) parameters
# =============================================================
OD_EXTENSION_BEYOND_FIN = 10   # OD extends beyond outermost fin
POLY_EXTENSION_BEYOND_OD = 15  # Poly extends beyond OD edge

# =============================================================
# Device parameters for MVP inverter
# =============================================================
NMOS_NFIN = 5            # NMOS fin count (before resize)
PMOS_NFIN = 7            # PMOS fin count (before resize)
NMOS_NFIN_TARGET = 4     # NMOS fin count (after resize)
PMOS_NFIN_TARGET = 6     # PMOS fin count (after resize)

# =============================================================
# Cell-level parameters
# =============================================================
# Number of gate pitches in X (dummy_L + active + dummy_R = 3)
NUM_GATE_SLOTS = 3
# Gap between NMOS and PMOS fin regions (in fin pitches)
NP_GAP_FINS = 3          # 3 fin pitches gap between N and P regions

# =============================================================
# Layer orientations
# =============================================================
LAYER_ORIENTATION = {
    'FIN':  'H',   # Fins run horizontally
    'POLY': 'V',   # Poly runs vertically
    'LI':   'V',   # LI runs vertically (same as poly)
    'VIA0': None,   # Via is a point object (no orientation)
    'M1':   'H',   # M1 runs horizontally
}

# =============================================================
# Track pitch per layer (used for grid construction)
# For V layers: pitch in X, tracks extend along Y
# For H layers: pitch in Y, tracks extend along X
# =============================================================
LAYER_PITCH = {
    'FIN':  FIN_PITCH,     # 25nm Y-pitch
    'POLY': GATE_PITCH,    # 54nm X-pitch
    'LI':   LI_PITCH,      # 54nm X-pitch
    'M1':   M1_PITCH,      # 36nm Y-pitch
}

# =============================================================
# Derived: spacing in track units (for CSP stencils)
# spacing_tracks = ceil(physical_spacing / pitch)
# This tells us how many tracks apart two objects must be
# =============================================================
import math

def spacing_in_tracks(spacing_nm: float, pitch_nm: float) -> int:
    """Convert physical spacing to number of track intervals."""
    return math.ceil(spacing_nm / pitch_nm)

LI_SPACING_TRACKS = spacing_in_tracks(LI_MIN_SPACING + LI_WIDTH, LI_PITCH)
# LI center-to-center must be >= width + spacing = 17+17 = 34nm
# In LI tracks (pitch=54nm): ceil(34/54) = 1 → adjacent LI tracks are always legal
# This makes sense: at 54nm pitch with 17nm width, gap = 37nm > 17nm spacing

M1_SPACING_TRACKS = spacing_in_tracks(M1_MIN_SPACING + M1_WIDTH, M1_PITCH)
# M1 center-to-center must be >= 20+16 = 36nm
# In M1 tracks (pitch=36nm): ceil(36/36) = 1 → adjacent M1 tracks are legal
# At exactly 1 pitch, gap = 36-20 = 16nm = exactly min spacing


# =============================================================
# Convenience: collect all params in a dict for passing around
# =============================================================
TECH = {
    'fin_pitch': FIN_PITCH,
    'gate_pitch': GATE_PITCH,
    'li_pitch': LI_PITCH,
    'm1_pitch': M1_PITCH,
    'fin_width': FIN_WIDTH,
    'poly_width': POLY_WIDTH,
    'li_width': LI_WIDTH,
    'm1_width': M1_WIDTH,
    'via0_width': VIA0_WIDTH,
    'via0_height': VIA0_HEIGHT,
    'nmos_nfin': NMOS_NFIN,
    'pmos_nfin': PMOS_NFIN,
    'np_gap_fins': NP_GAP_FINS,
    'num_gate_slots': NUM_GATE_SLOTS,
    'od_ext': OD_EXTENSION_BEYOND_FIN,
    'poly_ext': POLY_EXTENSION_BEYOND_OD,
    'via0_enc_li_x': VIA0_ENC_BY_LI_X,
    'via0_enc_li_y': VIA0_ENC_BY_LI_Y,
    'via0_enc_m1_x': VIA0_ENC_BY_M1_X,
    'via0_enc_m1_y': VIA0_ENC_BY_M1_Y,
}
