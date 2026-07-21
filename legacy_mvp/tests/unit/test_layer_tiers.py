"""M4a: tier markers in ``tech.layer_map``.

These tests lock in the tier-dispatch table that M4b parser projection,
M5 derivator gating, and the M6 macro family will key off. The test
``test_every_layer_map_entry_has_a_tier`` is the structural guard — any
new ``LAYER_MAP`` entry must declare a tier in ``LAYER_TIER`` so M4b's
tier-dispatch can fail-loud on an unmapped layer.

Roadmap: docs/architecture_roadmap.md §B and milestone M4.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest

from tech.layer_map import (
    A_TIER_LAYERS,
    B_TIER_LAYERS,
    C1_TIER_LAYERS,
    C2_TIER_LAYERS,
    CUT_LAYERS,
    LAYER_MAP,
    LAYER_TIER,
    TIERS,
    is_cut_layer,
    layers_in_tier,
    tier_of,
)


def test_tier_of_known_layers():
    """Spot-check the canonical tier assignments from §B of the roadmap."""
    # A — 1D track
    assert tier_of('FIN') == 'A'
    assert tier_of('POLY') == 'A'
    assert tier_of('LI') == 'A'
    assert tier_of('M1') == 'A'
    # B — 2D cell
    assert tier_of('OD') == 'B'
    assert tier_of('VIA0') == 'B'
    assert tier_of('CPO') == 'B'
    assert tier_of('M0_CUT') == 'B'
    assert tier_of('FIN_CUT') == 'B'
    # C1 — derived
    assert tier_of('NWELL') == 'C1'
    assert tier_of('BOUNDARY') == 'C1'
    assert tier_of('VT') == 'C1'
    assert tier_of('PP') == 'C1'
    assert tier_of('NP') == 'C1'
    assert tier_of('DNW') == 'C1'
    # C2 — annotation
    assert tier_of('DIODE') == 'C2'
    assert tier_of('ESD') == 'C2'
    assert tier_of('TEXT') == 'C2'


def test_tier_of_unknown_raises():
    """Unmapped layer is a parser bug — surface loud, don't return None."""
    with pytest.raises(KeyError):
        tier_of('NO_SUCH_LAYER')


def test_layers_in_tier_partitions_layer_tier():
    """Every layer appears in exactly one tier subset, and the union is exhaustive."""
    seen = set()
    for tier in TIERS:
        members = layers_in_tier(tier)
        assert isinstance(members, tuple)
        for m in members:
            assert m not in seen, f"layer {m!r} listed in multiple tiers"
            seen.add(m)
    assert seen == set(LAYER_TIER.keys())


def test_layers_in_tier_rejects_unknown_tier():
    with pytest.raises(ValueError):
        layers_in_tier('Z')


def test_tier_subset_constants_match_helper():
    """The exported ``*_TIER_LAYERS`` constants must agree with ``layers_in_tier``."""
    assert A_TIER_LAYERS == layers_in_tier('A')
    assert B_TIER_LAYERS == layers_in_tier('B')
    assert C1_TIER_LAYERS == layers_in_tier('C1')
    assert C2_TIER_LAYERS == layers_in_tier('C2')


def test_cut_layers_are_b_tier():
    """Every CUT layer is also B-tier — CUTs project as B-tier cells with
    ``OccupantType.CUT`` rather than living on their own tier."""
    for cl in CUT_LAYERS:
        assert tier_of(cl) == 'B', f"{cl} should be B-tier"
        assert is_cut_layer(cl)
    assert not is_cut_layer('OD')   # OD is B-tier but not a cut
    assert not is_cut_layer('LI')   # LI is A-tier


def test_every_layer_map_entry_has_a_tier():
    """Structural guard: any layer with a GDS number must declare a tier so
    parser tier-dispatch (landing in M4b) doesn't silently miss it."""
    for layer in LAYER_MAP:
        assert layer in LAYER_TIER, \
            f"LAYER_MAP entry {layer!r} missing from LAYER_TIER"


if __name__ == '__main__':
    test_tier_of_known_layers()
    test_tier_of_unknown_raises()
    test_layers_in_tier_partitions_layer_tier()
    test_layers_in_tier_rejects_unknown_tier()
    test_tier_subset_constants_match_helper()
    test_cut_layers_are_b_tier()
    test_every_layer_map_entry_has_a_tier()
    print("All M4a tier-marker tests passed!")
