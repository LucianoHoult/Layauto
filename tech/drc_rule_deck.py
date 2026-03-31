"""
DRC rule parameter table.

Loads DRC numerical values from YAML via TechConfig.
In production, these values come from the foundry DRM.
"""

import math


def _spacing_tracks(spacing_nm, width_nm, pitch_nm):
    """Center-to-center distance in track units."""
    return math.ceil((spacing_nm + width_nm) / pitch_nm)


def build_drc_rules(config) -> dict:
    """Build DRC rule table from a TechConfig instance.

    Returns the same dict structure as the old DRC_RULES constant,
    but with values sourced from YAML config.
    """
    return {
        'LI_along_track_spacing': {
            'type': 'along_track',
            'layer': 'LI',
            'spacing_ortho': 1,
            'physical_nm': config.LI_MIN_SPACING,
        },
        'M1_cross_track_spacing': {
            'type': 'cross_track',
            'layer': 'M1',
            'spacing_tracks': _spacing_tracks(
                config.M1_MIN_SPACING, config.M1_WIDTH, config.M1_PITCH),
            'physical_nm': config.M1_MIN_SPACING,
        },
        'M1_along_track_spacing': {
            'type': 'along_track',
            'layer': 'M1',
            'spacing_ortho': 1,
            'physical_nm': config.M1_MIN_SPACING,
        },
        'Via0_enclosure_LI': {
            'type': 'enclosure',
            'via_layer': 'VIA0',
            'metal_layer': 'LI',
            'enc_x_nm': config.VIA0_ENC_BY_LI_X,
            'enc_y_nm': config.VIA0_ENC_BY_LI_Y,
        },
        'Via0_enclosure_M1': {
            'type': 'enclosure',
            'via_layer': 'VIA0',
            'metal_layer': 'M1',
            'enc_x_nm': config.VIA0_ENC_BY_M1_X,
            'enc_y_nm': config.VIA0_ENC_BY_M1_Y,
        },
    }
