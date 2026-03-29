"""
DRC rules encoded as CSP constraint templates.

MVP rule set:
  1. Same-layer min spacing (LI, M1)
  2. Via enclosure by metal
  
Each rule is a (Stencil, Trigger, Forbidden) triple.
Adding a new DRC = adding a new class here + registering it with the engine.
No changes to the engine itself.
"""

import sys
import os
from typing import Set, List, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.csp_engine import DRCConstraintTemplate
from core.data_model import CellState, OccupantType, EMPTY


class SameLayerMinSpacing(DRCConstraintTemplate):
    """
    Same-layer minimum spacing rule.
    
    If a grid cell is occupied by net_A, then cells within
    'spacing_tracks' distance on the same layer cannot be occupied
    by a different net (net_B ≠ net_A).
    
    Same-net adjacent cells are allowed (they form wider wires or
    continuous segments).
    
    Stencil: same-layer cells within Manhattan distance ≤ spacing_tracks
    Trigger: any WIRE or VIA occupancy
    Forbidden: WIRE or VIA of a different net
    """
    
    def __init__(self, layer: str, spacing_tracks: int):
        """
        Args:
            layer: Layer this rule applies to
            spacing_tracks: Minimum spacing in track units (cross-track direction)
        """
        # Generate stencil: same-layer, cross-track neighbors within spacing
        # For routing layers, spacing is primarily in the cross-track direction
        # Along-track spacing is typically not an issue (same track = same wire)
        stencil = []
        for dt in range(-spacing_tracks, spacing_tracks + 1):
            if dt == 0:
                continue
            # Same layer, shift in track direction, no ortho shift
            stencil.append((layer, dt, 0))
        
        super().__init__(
            name=f"min_spacing_{layer}_{spacing_tracks}trk",
            stencil=stencil,
            anchor_layer=layer
        )
        self.layer = layer
    
    def trigger(self, state: CellState) -> bool:
        return state.occ_type in (OccupantType.WIRE, OccupantType.VIA)
    
    def forbidden_states(self, trigger_state: CellState,
                         all_net_ids: Set[str]) -> Set[CellState]:
        """Forbid: any wire/via of a DIFFERENT net."""
        my_net = trigger_state.net_id
        forbidden = set()
        for net_id in all_net_ids:
            if net_id != my_net:
                forbidden.add(CellState(OccupantType.WIRE, net_id=net_id))
                forbidden.add(CellState(OccupantType.VIA, net_id=net_id))
        return forbidden


class SameLayerAlongTrackSpacing(DRCConstraintTemplate):
    """
    Along-track spacing between different nets on the same track.
    
    Prevents two different nets from being on adjacent ortho positions
    of the same track without sufficient gap.
    
    This is essentially end-to-end spacing for segments on the same track.
    """
    
    def __init__(self, layer: str, spacing_ortho: int):
        stencil = []
        for do in range(-spacing_ortho, spacing_ortho + 1):
            if do == 0:
                continue
            stencil.append((layer, 0, do))
        
        super().__init__(
            name=f"along_track_spacing_{layer}_{spacing_ortho}",
            stencil=stencil,
            anchor_layer=layer
        )
        self.layer = layer
    
    def trigger(self, state: CellState) -> bool:
        return state.occ_type in (OccupantType.WIRE, OccupantType.VIA)
    
    def forbidden_states(self, trigger_state: CellState,
                         all_net_ids: Set[str]) -> Set[CellState]:
        my_net = trigger_state.net_id
        forbidden = set()
        for net_id in all_net_ids:
            if net_id != my_net:
                forbidden.add(CellState(OccupantType.WIRE, net_id=net_id))
                forbidden.add(CellState(OccupantType.VIA, net_id=net_id))
        return forbidden


class SameNetContinuity(DRCConstraintTemplate):
    """
    Enforce that a wire segment has same-net neighbors along the track.
    
    This is a "positive constraint": if a cell is a wire for net_A,
    then the adjacent cell along-track should also be net_A (or empty at segment ends).
    
    Note: This is optional for MVP. Without it, the solver can place
    isolated single-cell wires, which is geometrically invalid but
    will be caught by the segment-level validation.
    
    For now, we skip this and rely on the solver placing complete segments.
    """
    pass


def create_mvp_drc_rules(layers: dict = None) -> List[DRCConstraintTemplate]:
    """
    Create the MVP DRC rule set.
    
    For the MVP (fin resize within a single cell), the relevant DRC checks are:
    - LI along-track spacing: VSS and VDD share LI track 1, need gap between them
    - M1 cross-track spacing: different nets on adjacent M1 tracks
    - M1 along-track spacing: different nets on same M1 track
    
    LI cross-track spacing is NOT included because:
    - At half-pitch (27nm), adjacent LI tracks (S/D vs gate contact) are
      physically closer than min spacing, but their Y extents don't overlap.
    - LI X positions don't change during resize (only Y extents change).
    - This will be validated by post-DRC (Calibre) in production.
    """
    rules = []
    
    # --- LI along-track spacing (same track, different nets) ---
    # Critical: VSS and VDD share LI track 1 at different Y positions.
    # They must maintain min spacing along-track.
    rules.append(SameLayerAlongTrackSpacing('LI', spacing_ortho=1))
    
    # --- M1 same-layer min spacing ---
    # M1 pitch=36nm, width=20nm, spacing=16nm
    # Center-to-center min = 20+16 = 36nm = exactly one pitch
    # → adjacent M1 tracks are at exactly min spacing (legal but tight)
    # → spacing_tracks = 1
    rules.append(SameLayerMinSpacing('M1', spacing_tracks=1))
    rules.append(SameLayerAlongTrackSpacing('M1', spacing_ortho=1))
    
    return rules


# =============================================================
# Test helper
# =============================================================
def test_spacing_rule():
    """Quick sanity test of spacing constraint."""
    from core.csp_engine import ConstraintEngine
    
    print("Testing SameLayerMinSpacing on a 3-track M1 grid...")
    
    engine = ConstraintEngine()
    engine.add_layer('M1', n_tracks=3, n_ortho=5)
    
    rule = SameLayerMinSpacing('M1', spacing_tracks=1)
    engine.register_drc(rule)
    
    net_ids = {'VSS', 'VDD', 'OUT'}
    engine.initialize_domains(net_ids)
    
    print(f"Initial domain size per cell: {engine.domain_stats('M1')}")
    
    # Assign track 1, ortho 2 to VSS wire
    state_vss = CellState(OccupantType.WIRE, net_id='VSS')
    success = engine.assign(('M1', 1, 2), state_vss)
    print(f"Assign (M1, t1, o2) = VSS wire: success={success}")
    
    # Check neighbor domains
    for t in range(3):
        cell = engine.get_cell(('M1', t, 2))
        print(f"  (M1, t{t}, o2): assignment={cell.assignment}, domain_size={cell.domain_size}")
        if t != 1:
            # Adjacent tracks should have VDD and OUT wire states removed
            has_vdd_wire = CellState(OccupantType.WIRE, net_id='VDD') in cell.domain
            has_vss_wire = CellState(OccupantType.WIRE, net_id='VSS') in cell.domain
            print(f"    VDD wire in domain: {has_vdd_wire} (should be False)")
            print(f"    VSS wire in domain: {has_vss_wire} (should be True)")
    
    # Try to assign adjacent track to a different net
    state_vdd = CellState(OccupantType.WIRE, net_id='VDD')
    success2 = engine.assign(('M1', 0, 2), state_vdd)
    print(f"Assign (M1, t0, o2) = VDD wire: success={success2} (should be False)")
    
    # Same net on adjacent track should work
    cp = engine.checkpoint()
    engine.restore(cp)  # Restore after failed assign attempt
    
    state_vss2 = CellState(OccupantType.WIRE, net_id='VSS')
    success3 = engine.assign(('M1', 0, 2), state_vss2)
    print(f"Assign (M1, t0, o2) = VSS wire: success={success3} (should be True)")
    
    print("\nSpacing rule test complete.")


if __name__ == '__main__':
    test_spacing_rule()
