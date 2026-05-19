"""
Technology configuration loader.

Sources (composable):
  * tech/drc_rules.yaml   — unified DRC rule-record format
  * tech/layer_map.yaml   — per-layer record format (also loaded by
                            tech.layer_map for module-level constants)
  * optional .layermap    — foundry-supplied gds-pair override; only
                            patches the `gds:` field of matching rows
  * optional site_config  — composes the bundle with input/output
                            paths for one pipeline run (paths-only)

The TechConfig public API is unchanged from pre-refactor: every
property name (FIN_PITCH, LI_MIN_SPACING, VIA0_ENC_BY_LI_X,
LAYER_MAP, ...) resolves through the new YAML format, so existing
callers don't need any update.

Usage:
    config = load_tech_config()
    config = load_tech_config(drc_yaml='/x/drc.yaml',
                              layer_yaml='/x/lm.yaml')
    site   = load_site_config('tech/site_config.yaml')   # → dict
"""

import math
import os
from typing import Optional

import yaml

from tech.layermap_parser import parse_layermap


# ---------------------------------------------------------------
# TechConfig
# ---------------------------------------------------------------
class TechConfig:
    """Central technology configuration, loaded from YAML files.

    All numerical access goes through DRC rule records (looked up
    by ASAP7-style rule id, e.g. ``FIN.P.1`` for the fin pitch).
    Layer attributes (gds, tier, orientation, color) come from
    ``layer_map.yaml``.
    """

    def __init__(self, drc_yaml: str, layer_yaml: str = None,
                 layermap_override: str = None):
        with open(drc_yaml, encoding='utf-8') as f:
            self._drc = yaml.safe_load(f)

        if layer_yaml is None:
            tech_dir = os.path.dirname(os.path.abspath(__file__))
            layer_yaml = os.path.join(tech_dir, 'layer_map.yaml')
        with open(layer_yaml, encoding='utf-8') as f:
            self._layer_data = yaml.safe_load(f)

        # Build layer index by name. Apply optional .layermap override
        # (patches `gds:` only — other fields like tier/orientation
        # come from the YAML).
        self._layers_by_name = {
            l['name']: dict(l) for l in self._layer_data.get('layers', [])
        }
        if layermap_override and os.path.exists(layermap_override):
            override = parse_layermap(layermap_override)
            for name, gds in override['LAYER_MAP'].items():
                if name in self._layers_by_name:
                    self._layers_by_name[name]['gds'] = list(gds)

        # Index DRC rules by id (O(1) lookup for property accessors).
        self._rules_by_id = {
            r['id']: r for r in self._drc.get('rules', [])
        }

    # ===============================================================
    # DRC rule lookup helpers
    # ===============================================================
    def _rule(self, rule_id: str) -> dict:
        try:
            return self._rules_by_id[rule_id]
        except KeyError:
            proc = self._drc.get('process', {}).get('name', 'unknown')
            raise KeyError(
                f"DRC rule {rule_id!r} not found in deck {proc!r}"
            )

    def _rule_value(self, rule_id: str, axis: str = None):
        """Read a rule's ``value_nm``.

        Scalar rules return the same value regardless of ``axis``.
        Axis-keyed rules ({x: ..., y: ...}) require ``axis`` to be
        ``'x'`` or ``'y'``.
        """
        v = self._rule(rule_id)['value_nm']
        if isinstance(v, dict):
            if axis is None:
                raise ValueError(
                    f"rule {rule_id!r} has axis-keyed value; "
                    "specify axis='x' or axis='y'"
                )
            return v[axis]
        return v

    # ===============================================================
    # Pitch (also the CSP grid pitch)
    # ===============================================================
    @property
    def FIN_PITCH(self) -> int:  return self._rule_value('FIN.P.1')
    @property
    def GATE_PITCH(self) -> int: return self._rule_value('POLY.P.1')
    @property
    def LI_PITCH(self) -> int:   return self._rule_value('LI.P.1')
    @property
    def M1_PITCH(self) -> int:   return self._rule_value('M1.P.1')

    # ===============================================================
    # Width
    # ===============================================================
    @property
    def FIN_WIDTH(self) -> int:  return self._rule_value('FIN.W.1')
    @property
    def POLY_WIDTH(self) -> int: return self._rule_value('POLY.W.1')
    @property
    def LI_WIDTH(self) -> int:   return self._rule_value('LI.W.1')
    @property
    def M1_WIDTH(self) -> int:   return self._rule_value('M1.W.1')

    # ===============================================================
    # Via exact size
    # ===============================================================
    @property
    def VIA0_WIDTH(self) -> int:  return self._rule_value('V0.SZ.1', 'x')
    @property
    def VIA0_HEIGHT(self) -> int: return self._rule_value('V0.SZ.1', 'y')

    # ===============================================================
    # Extension (one layer past another)
    # ===============================================================
    @property
    def OD_EXTENSION_BEYOND_FIN(self) -> int:
        return self._rule_value('OD.X.FIN')

    @property
    def POLY_EXTENSION_BEYOND_OD(self) -> int:
        return self._rule_value('POLY.X.OD')

    @property
    def NWELL_MARGIN_BEYOND_FIN(self) -> int:
        return self._rule_value('NWELL.X.FIN')

    @property
    def BOUNDARY_MARGIN_BEYOND_FIN(self) -> int:
        return self._rule_value('BOUNDARY.X.FIN')

    # ===============================================================
    # Same-layer spacing
    # ===============================================================
    @property
    def LI_MIN_SPACING(self) -> int:   return self._rule_value('LI.S.1')
    @property
    def M1_MIN_SPACING(self) -> int:   return self._rule_value('M1.S.1')
    @property
    def VIA0_MIN_SPACING(self) -> int: return self._rule_value('V0.S.1')

    # ===============================================================
    # Via enclosure (axis-keyed)
    # ===============================================================
    @property
    def VIA0_ENC_BY_LI_X(self) -> int: return self._rule_value('V0.E.LI', 'x')
    @property
    def VIA0_ENC_BY_LI_Y(self) -> int: return self._rule_value('V0.E.LI', 'y')
    @property
    def VIA0_ENC_BY_M1_X(self) -> int: return self._rule_value('V0.E.M1', 'x')
    @property
    def VIA0_ENC_BY_M1_Y(self) -> int: return self._rule_value('V0.E.M1', 'y')

    # ===============================================================
    # Layer-derived dicts
    # ===============================================================
    @property
    def LAYER_ORIENTATION(self) -> dict:
        return {n: l.get('orientation')
                for n, l in self._layers_by_name.items()}

    @property
    def LAYER_PITCH(self) -> dict:
        return {
            'FIN': self.FIN_PITCH,
            'POLY': self.GATE_PITCH,
            'LI': self.LI_PITCH,
            'M1': self.M1_PITCH,
        }

    @property
    def LAYER_MAP(self) -> dict:
        return {n: tuple(l['gds'])
                for n, l in self._layers_by_name.items()
                if l.get('gds')}

    @property
    def GDS_TO_LAYER(self) -> dict:
        return {tuple(l['gds']): n
                for n, l in self._layers_by_name.items()
                if l.get('gds')}

    # ===============================================================
    # Track-unit conversions
    # ===============================================================
    @staticmethod
    def spacing_in_tracks(spacing_nm: float, pitch_nm: float) -> int:
        return math.ceil(spacing_nm / pitch_nm)

    @property
    def LI_SPACING_TRACKS(self) -> int:
        return self.spacing_in_tracks(
            self.LI_MIN_SPACING + self.LI_WIDTH, self.LI_PITCH)

    @property
    def M1_SPACING_TRACKS(self) -> int:
        return self.spacing_in_tracks(
            self.M1_MIN_SPACING + self.M1_WIDTH, self.M1_PITCH)

    # ===============================================================
    # DRC rule list access
    # ===============================================================
    def get_drc_rules(self, severity: str = None,
                      rule_type: str = None) -> list:
        """Return the rule list, optionally filtered by severity / type.

        Each entry is the raw rule dict from ``drc_rules.yaml``
        (with ``id``, ``type``, ``layers``, ``value_nm``, ...).
        """
        rules = list(self._drc.get('rules', []))
        if severity:
            rules = [r for r in rules if r.get('severity') == severity]
        if rule_type:
            rules = [r for r in rules if r.get('type') == rule_type]
        return rules

    # ===============================================================
    # Convenience
    # ===============================================================
    def to_dict(self) -> dict:
        """Flat dict export of the most-used numeric values."""
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
            'od_ext': self.OD_EXTENSION_BEYOND_FIN,
            'poly_ext': self.POLY_EXTENSION_BEYOND_OD,
            'nwell_ext': self.NWELL_MARGIN_BEYOND_FIN,
            'boundary_ext': self.BOUNDARY_MARGIN_BEYOND_FIN,
            'via0_enc_li_x': self.VIA0_ENC_BY_LI_X,
            'via0_enc_li_y': self.VIA0_ENC_BY_LI_Y,
            'via0_enc_m1_x': self.VIA0_ENC_BY_M1_X,
            'via0_enc_m1_y': self.VIA0_ENC_BY_M1_Y,
        }

    def __repr__(self):
        name = self._drc.get('process', {}).get('name', 'unknown')
        return f"TechConfig({name})"


# ---------------------------------------------------------------
# Module-level loaders
# ---------------------------------------------------------------
_default_config: Optional[TechConfig] = None


def load_tech_config(drc_yaml: str = None, layer_yaml: str = None,
                     layermap_override: str = None) -> TechConfig:
    """Load and cache the default TechConfig.

    Defaults to ``tech/drc_rules.yaml`` + ``tech/layer_map.yaml``
    next to this file.
    """
    global _default_config

    tech_dir = os.path.dirname(os.path.abspath(__file__))
    if drc_yaml is None:
        drc_yaml = os.path.join(tech_dir, 'drc_rules.yaml')
    if layer_yaml is None:
        layer_yaml = os.path.join(tech_dir, 'layer_map.yaml')

    _default_config = TechConfig(drc_yaml, layer_yaml, layermap_override)
    return _default_config


def get_tech_config() -> TechConfig:
    global _default_config
    if _default_config is None:
        return load_tech_config()
    return _default_config


def load_site_config(site_yaml: str) -> dict:
    """Load a site_config.yaml that composes tech sources + run paths.

    Returns the parsed dict with all path-valued fields resolved
    relative to the site_config file's directory (so paths inside
    the YAML can be relative to the YAML, not CWD).

    Top-level keys: ``tech``, ``inputs``, ``output``, plus optional
    ``calibre`` / ``virtuoso`` (deferred).
    """
    site_dir = os.path.dirname(os.path.abspath(site_yaml))
    with open(site_yaml, encoding='utf-8') as f:
        cfg = yaml.safe_load(f) or {}

    def resolve(p):
        if p is None:
            return None
        if os.path.isabs(p):
            return p
        return os.path.normpath(os.path.join(site_dir, p))

    tech = cfg.setdefault('tech', {})
    tech['drc_rules'] = resolve(tech.get('drc_rules'))
    tech['layer_map'] = resolve(tech.get('layer_map'))
    tech['layermap_override'] = resolve(tech.get('layermap_override'))
    tech['calibre_layer_map'] = resolve(tech.get('calibre_layer_map'))

    inputs = cfg.setdefault('inputs', {})
    for key, val in list(inputs.items()):
        inputs[key] = resolve(val)

    output = cfg.setdefault('output', {})
    output['dir'] = resolve(output.get('dir'))

    # Calibre block (Stage 1.5 — LVS extract). Path-valued keys are
    # resolved relative to the YAML; ``mode`` and ``timeout_s`` pass
    # through verbatim. ``mode`` defaults to ``'dummy'`` when absent so
    # legacy site_configs (pre-2026-05-07) continue to load.
    calibre = cfg.setdefault('calibre', {})
    calibre['svdb_dir']              = resolve(calibre.get('svdb_dir'))
    calibre['ixref_temp']            = resolve(calibre.get('ixref_temp'))
    calibre['nxref_temp']            = resolve(calibre.get('nxref_temp'))
    calibre['net_names_txt']         = resolve(calibre.get('net_names_txt'))
    calibre['device_info_dir']       = resolve(calibre.get('device_info_dir'))
    calibre['net_shapes_dir']        = resolve(calibre.get('net_shapes_dir'))
    calibre['dummy_ixref']           = resolve(calibre.get('dummy_ixref'))
    calibre['dummy_nxref']           = resolve(calibre.get('dummy_nxref'))
    calibre['dummy_net_names']       = resolve(calibre.get('dummy_net_names'))
    calibre['dummy_device_info_dir'] = resolve(
        calibre.get('dummy_device_info_dir'))
    calibre['dummy_net_shapes_dir']  = resolve(
        calibre.get('dummy_net_shapes_dir'))
    calibre.setdefault('mode', 'dummy')
    calibre.setdefault('timeout_s', 300)

    return cfg


def load_tech_config_from_site(site_yaml: str) -> TechConfig:
    """Convenience: read a site_config.yaml and load TechConfig from
    its referenced ``tech.drc_rules`` / ``tech.layer_map`` paths.
    """
    site = load_site_config(site_yaml)
    tech = site.get('tech', {})
    return load_tech_config(
        drc_yaml=tech.get('drc_rules'),
        layer_yaml=tech.get('layer_map'),
        layermap_override=tech.get('layermap_override'),
    )
