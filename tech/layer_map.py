"""
Layer-map module-level constants, sourced from ``tech/layer_map.yaml``.

Loaded at import time so existing call sites (e.g.
``from tech.layer_map import LAYER_MAP, LAYER_TIER, tier_of``)
continue to work without modification. The YAML format itself is
documented in ``tech/layer_map.yaml``; this module is a thin
transformation layer that exposes the same constants the pre-YAML
hardcoded module exposed.

Tier assignment (per architecture roadmap §B):
  A  — 1D track  (FIN, POLY, LI, M1)            -> TrackSegment + CSP
  B  — 2D cell   (OD, VIA0, CPO, M0_CUT, FIN_CUT) -> CellOccupancy + CSP
  C1 — derived   (NWELL, VT, PP, NP, BOUNDARY, DNW) -> M5 derivator
  C2 — annotation (DIODE, ESD, TEXT)            -> direct shape edit
"""

import os
from typing import Tuple

import yaml

_DEFAULT_YAML = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'layer_map.yaml'
)


def _load_layers(yaml_path: str = _DEFAULT_YAML) -> list:
    with open(yaml_path, encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}
    return data.get('layers', [])


_LAYERS = _load_layers()

# (layer_number, datatype) tuples for layers with a GDS pair.
LAYER_MAP = {
    l['name']: tuple(l['gds'])
    for l in _LAYERS
    if l.get('gds')
}

# Reverse lookup
GDS_TO_LAYER = {v: k for k, v in LAYER_MAP.items()}

# Display colors (R, G, B, alpha) for visualization
LAYER_COLORS = {
    l['name']: tuple(l['color'])
    for l in _LAYERS
    if l.get('color')
}


# =============================================================
# Tier markers
# =============================================================
TIERS = ('A', 'B', 'C1', 'C2')

# Layer name → tier marker. Every layer in the YAML has a tier,
# including those without GDS geometry (CPO / VT / DIODE / ...).
LAYER_TIER = {l['name']: l['tier'] for l in _LAYERS}

A_TIER_LAYERS = tuple(L for L, t in LAYER_TIER.items() if t == 'A')
B_TIER_LAYERS = tuple(L for L, t in LAYER_TIER.items() if t == 'B')
C1_TIER_LAYERS = tuple(L for L, t in LAYER_TIER.items() if t == 'C1')
C2_TIER_LAYERS = tuple(L for L, t in LAYER_TIER.items() if t == 'C2')

# Cut layers — derived from ``role: cut`` in the YAML.
CUT_LAYERS = tuple(l['name'] for l in _LAYERS if l.get('role') == 'cut')

# Slice 1.6: per-GDS-layer ``derived_layers`` list. Consumed by
# ``io_adapters/calibre_layer_map.py::apply_calibre_layer_overlay`` to
# resolve "given this GDS layer, which Calibre-derived layers carry
# annotations back to it?". Entries that omit ``derived_layers`` (legacy
# YAMLs) surface as an empty list.
DERIVED_LAYERS = {
    l['name']: list(l.get('derived_layers') or [])
    for l in _LAYERS
}


def tier_of(layer: str) -> str:
    """Return the tier marker for ``layer``.

    Raises ``KeyError`` rather than returning ``None`` — an unmapped
    layer is a parser bug we want to surface loudly so the M4b/c
    tier-dispatch table stays honest.
    """
    return LAYER_TIER[layer]


def layers_in_tier(tier: str) -> Tuple[str, ...]:
    """Return all layer names in the given tier (in ``LAYER_TIER`` order)."""
    if tier not in TIERS:
        raise ValueError(
            f"unknown tier {tier!r}; expected one of {TIERS}"
        )
    return tuple(L for L, t in LAYER_TIER.items() if t == tier)


def is_cut_layer(layer: str) -> bool:
    """True iff ``layer`` is a cut layer (CPO / M0_CUT / FIN_CUT)."""
    return layer in CUT_LAYERS


def derived_layers_of(layer: str) -> list:
    """Return the ``derived_layers`` list for ``layer`` (slice 1.6).

    Each entry is a dict ``{name, carries, [color]}`` naming an LVS-side
    derived layer that carries annotations back onto cells of ``layer``.
    Empty for structural layers (FIN) or layers with no LVS overlay
    today (NWELL, BOUNDARY, cut markers).

    Raises ``KeyError`` for an unmapped layer — same loud-fail policy as
    ``tier_of``.
    """
    return list(DERIVED_LAYERS[layer])
