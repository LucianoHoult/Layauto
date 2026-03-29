"""
DRC rule parameter table.

Separates DRC numerical values from tech_params.py for clarity.
In production, these values come from the foundry DRM.
"""

from tech.tech_params import (
    LI_MIN_SPACING, M1_MIN_SPACING, LI_WIDTH, M1_WIDTH,
    LI_PITCH, M1_PITCH,
    VIA0_WIDTH, VIA0_HEIGHT,
    VIA0_ENC_BY_LI_X, VIA0_ENC_BY_LI_Y,
    VIA0_ENC_BY_M1_X, VIA0_ENC_BY_M1_Y,
)
import math

# =============================================================
# Spacing rules in track units
# =============================================================

def _spacing_tracks(spacing_nm, width_nm, pitch_nm):
    """Center-to-center distance in track units."""
    return math.ceil((spacing_nm + width_nm) / pitch_nm)

DRC_RULES = {
    'LI_along_track_spacing': {
        'type': 'along_track',
        'layer': 'LI',
        'spacing_ortho': 1,
        'physical_nm': LI_MIN_SPACING,
    },
    'M1_cross_track_spacing': {
        'type': 'cross_track',
        'layer': 'M1',
        'spacing_tracks': _spacing_tracks(M1_MIN_SPACING, M1_WIDTH, M1_PITCH),
        'physical_nm': M1_MIN_SPACING,
    },
    'M1_along_track_spacing': {
        'type': 'along_track',
        'layer': 'M1',
        'spacing_ortho': 1,
        'physical_nm': M1_MIN_SPACING,
    },
    'Via0_enclosure_LI': {
        'type': 'enclosure',
        'via_layer': 'VIA0',
        'metal_layer': 'LI',
        'enc_x_nm': VIA0_ENC_BY_LI_X,
        'enc_y_nm': VIA0_ENC_BY_LI_Y,
    },
    'Via0_enclosure_M1': {
        'type': 'enclosure',
        'via_layer': 'VIA0',
        'metal_layer': 'M1',
        'enc_x_nm': VIA0_ENC_BY_M1_X,
        'enc_y_nm': VIA0_ENC_BY_M1_Y,
    },
}
