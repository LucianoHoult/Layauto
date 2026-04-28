"""
Technology configuration loader.

Loads process parameters and DRC rules from YAML files,
optionally loading layer map from a .layermap file.

Usage:
    config = load_tech_config('tech/process_config.yaml', 'tech/drc_rules.yaml')
    print(config.FIN_PITCH)  # 25
    rules = config.get_drc_rules(severity='critical')
"""

import math
import os
import yaml
from typing import Dict, List, Optional

from tech.layermap_parser import parse_layermap


class TechConfig:
    """Central technology configuration loaded from YAML files.

    Provides property access for all process parameters, DRC rules,
    and layer mapping data.
    """

    def __init__(self, process_yaml: str, drc_yaml: str,
                 layermap_path: str = None):
        """Load configuration from YAML files.

        Args:
            process_yaml: Path to process_config.yaml
            drc_yaml: Path to drc_rules.yaml
            layermap_path: Optional path to a .layermap file.
                          If None, uses built-in defaults from layer_map.py.
        """
        with open(process_yaml) as f:
            self._process = yaml.safe_load(f)
        with open(drc_yaml) as f:
            self._drc = yaml.safe_load(f)

        # Load layer map
        if layermap_path and os.path.exists(layermap_path):
            lm = parse_layermap(layermap_path)
            self._layer_map = lm['LAYER_MAP']
            self._gds_to_layer = lm['GDS_TO_LAYER']
            self._purposes = lm['purposes']
        else:
            # Fallback to built-in defaults
            from tech.layer_map import LAYER_MAP, GDS_TO_LAYER
            self._layer_map = dict(LAYER_MAP)
            self._gds_to_layer = dict(GDS_TO_LAYER)
            self._purposes = {}

    # =============================================================
    # Pitch properties
    # =============================================================
    @property
    def FIN_PITCH(self) -> int:
        return self._process['pitch']['FIN']

    @property
    def GATE_PITCH(self) -> int:
        return self._process['pitch']['GATE']

    @property
    def LI_PITCH(self) -> int:
        return self._process['pitch']['LI']

    @property
    def M1_PITCH(self) -> int:
        return self._process['pitch']['M1']

    # =============================================================
    # Width properties
    # =============================================================
    @property
    def FIN_WIDTH(self) -> int:
        return self._process['width']['FIN']

    @property
    def POLY_WIDTH(self) -> int:
        return self._process['width']['POLY']

    @property
    def LI_WIDTH(self) -> int:
        return self._process['width']['LI']

    @property
    def M1_WIDTH(self) -> int:
        return self._process['width']['M1']

    # =============================================================
    # Via properties
    # =============================================================
    @property
    def VIA0_WIDTH(self) -> int:
        return self._process['via']['VIA0']['width']

    @property
    def VIA0_HEIGHT(self) -> int:
        return self._process['via']['VIA0']['height']

    # =============================================================
    # Extension properties
    # =============================================================
    @property
    def OD_EXTENSION_BEYOND_FIN(self) -> int:
        return self._process['extension']['OD_beyond_FIN']

    @property
    def POLY_EXTENSION_BEYOND_OD(self) -> int:
        return self._process['extension']['POLY_beyond_OD']

    # =============================================================
    # C1 derivation margins (M5)
    #
    # Pure-function derivation rules consumed by
    # ``core/drc_derivator.py``. These were hardcoded literals
    # (30 / 40 nm) inline in ``core/decoder.py::_derive_*`` before
    # M5; lifted into config so the derivator reads named constants
    # and downstream PDK swaps stay tractable.
    # =============================================================
    @property
    def NWELL_MARGIN_BEYOND_FIN(self) -> int:
        return self._process['derivation']['nwell_margin_beyond_fin']

    @property
    def BOUNDARY_MARGIN_BEYOND_FIN(self) -> int:
        return self._process['derivation']['boundary_margin_beyond_fin']

    # =============================================================
    # Cell properties
    # =============================================================
    @property
    def NUM_GATE_SLOTS(self) -> int:
        return self._process['cell']['num_gate_slots']

    @property
    def NP_GAP_FINS(self) -> int:
        return self._process['cell']['np_gap_fins']

    # =============================================================
    # Layer orientation
    # =============================================================
    @property
    def LAYER_ORIENTATION(self) -> dict:
        return dict(self._process['layer_orientation'])

    @property
    def LAYER_PITCH(self) -> dict:
        """Layer name → pitch mapping (for grid construction)."""
        return {
            'FIN': self.FIN_PITCH,
            'POLY': self.GATE_PITCH,
            'LI': self.LI_PITCH,
            'M1': self.M1_PITCH,
        }

    # =============================================================
    # DRC spacing rules (from drc_rules.yaml)
    # =============================================================
    @property
    def LI_MIN_SPACING(self) -> int:
        return self._get_spacing_value('LI_min_spacing')

    @property
    def M1_MIN_SPACING(self) -> int:
        return self._get_spacing_value('M1_min_spacing')

    @property
    def VIA0_MIN_SPACING(self) -> int:
        return self._get_spacing_value('VIA0_min_spacing')

    # =============================================================
    # DRC enclosure rules (from drc_rules.yaml)
    # =============================================================
    @property
    def VIA0_ENC_BY_LI_X(self) -> int:
        return self._get_enclosure_value('VIA0_enc_by_LI', 'enc_x_nm')

    @property
    def VIA0_ENC_BY_LI_Y(self) -> int:
        return self._get_enclosure_value('VIA0_enc_by_LI', 'enc_y_nm')

    @property
    def VIA0_ENC_BY_M1_X(self) -> int:
        return self._get_enclosure_value('VIA0_enc_by_M1', 'enc_x_nm')

    @property
    def VIA0_ENC_BY_M1_Y(self) -> int:
        return self._get_enclosure_value('VIA0_enc_by_M1', 'enc_y_nm')

    # =============================================================
    # Layer map
    # =============================================================
    @property
    def LAYER_MAP(self) -> dict:
        return dict(self._layer_map)

    @property
    def GDS_TO_LAYER(self) -> dict:
        return dict(self._gds_to_layer)

    # =============================================================
    # Derived values
    # =============================================================
    def spacing_in_tracks(self, spacing_nm: float, pitch_nm: float) -> int:
        """Convert physical spacing to number of track intervals."""
        return math.ceil(spacing_nm / pitch_nm)

    @property
    def LI_SPACING_TRACKS(self) -> int:
        return self.spacing_in_tracks(
            self.LI_MIN_SPACING + self.LI_WIDTH, self.LI_PITCH)

    @property
    def M1_SPACING_TRACKS(self) -> int:
        return self.spacing_in_tracks(
            self.M1_MIN_SPACING + self.M1_WIDTH, self.M1_PITCH)

    # =============================================================
    # DRC rules access
    # =============================================================
    def get_drc_rules(self, severity: str = None) -> list:
        """Get DRC rules, optionally filtered by severity.

        Args:
            severity: If set, only return rules with this severity
                     ('critical', 'recommended', 'advisory').

        Returns:
            List of rule dicts from the YAML.
        """
        all_rules = []
        rules_section = self._drc.get('rules', {})
        for category, rule_list in rules_section.items():
            for rule in rule_list:
                rule_with_category = dict(rule)
                rule_with_category['category'] = category
                all_rules.append(rule_with_category)

        if severity:
            all_rules = [r for r in all_rules if r.get('severity') == severity]

        return all_rules

    def get_drc_rules_by_category(self, category: str) -> list:
        """Get DRC rules for a specific category (e.g. 'spacing', 'enclosure')."""
        return self._drc.get('rules', {}).get(category, [])

    # =============================================================
    # Convenience dict (replaces old TECH dict)
    # =============================================================
    def to_dict(self) -> dict:
        """Export all parameters as a flat dict."""
        return {
            'fin_pitch': self.FIN_PITCH,
            'gate_pitch': self.GATE_PITCH,
            'li_pitch': self.LI_PITCH,
            'm1_pitch': self.M1_PITCH,
            'fin_width': self.FIN_WIDTH,
            'poly_width': self.POLY_WIDTH,
            'li_width': self.LI_WIDTH,
            'm1_width': self.M1_WIDTH,
            'via0_width': self.VIA0_WIDTH,
            'via0_height': self.VIA0_HEIGHT,
            'np_gap_fins': self.NP_GAP_FINS,
            'num_gate_slots': self.NUM_GATE_SLOTS,
            'od_ext': self.OD_EXTENSION_BEYOND_FIN,
            'poly_ext': self.POLY_EXTENSION_BEYOND_OD,
            'via0_enc_li_x': self.VIA0_ENC_BY_LI_X,
            'via0_enc_li_y': self.VIA0_ENC_BY_LI_Y,
            'via0_enc_m1_x': self.VIA0_ENC_BY_M1_X,
            'via0_enc_m1_y': self.VIA0_ENC_BY_M1_Y,
        }

    # =============================================================
    # Internal helpers
    # =============================================================
    def _get_spacing_value(self, rule_name: str) -> int:
        for rule in self._drc.get('rules', {}).get('spacing', []):
            if rule['name'] == rule_name:
                return rule['value_nm']
        raise KeyError(f"DRC spacing rule '{rule_name}' not found")

    def _get_enclosure_value(self, rule_name: str, field: str) -> int:
        for rule in self._drc.get('rules', {}).get('enclosure', []):
            if rule['name'] == rule_name:
                return rule[field]
        raise KeyError(f"DRC enclosure rule '{rule_name}.{field}' not found")

    def __repr__(self):
        name = self._process.get('process', {}).get('name', 'unknown')
        return f"TechConfig({name})"


# =============================================================
# Module-level loader
# =============================================================
_default_config: Optional[TechConfig] = None


def load_tech_config(process_yaml: str = None, drc_yaml: str = None,
                     layermap_path: str = None) -> TechConfig:
    """Load and cache the default TechConfig.

    If paths are not specified, uses defaults relative to the tech/ directory.
    """
    global _default_config

    if process_yaml is None:
        tech_dir = os.path.dirname(os.path.abspath(__file__))
        process_yaml = os.path.join(tech_dir, 'process_config.yaml')
    if drc_yaml is None:
        tech_dir = os.path.dirname(os.path.abspath(__file__))
        drc_yaml = os.path.join(tech_dir, 'drc_rules.yaml')

    _default_config = TechConfig(process_yaml, drc_yaml, layermap_path)
    return _default_config


def get_tech_config() -> TechConfig:
    """Get the currently loaded TechConfig, loading defaults if needed."""
    global _default_config
    if _default_config is None:
        return load_tech_config()
    return _default_config
