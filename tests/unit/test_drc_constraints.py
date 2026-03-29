"""Test DRC constraint templates: trigger, forbidden, stencil correctness."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core.csp_engine import ConstraintEngine
from core.data_model import CellState, OccupantType, EMPTY
from core.drc_constraints import (
    SameLayerMinSpacing, SameLayerAlongTrackSpacing, create_mvp_drc_rules
)


def test_spacing_trigger():
    rule = SameLayerMinSpacing('M1', spacing_tracks=1)
    assert rule.trigger(CellState(OccupantType.WIRE, net_id='A'))
    assert not rule.trigger(EMPTY)


def test_spacing_forbidden():
    rule = SameLayerMinSpacing('M1', spacing_tracks=1)
    trigger_state = CellState(OccupantType.WIRE, net_id='A')
    forbidden = rule.forbidden_states(trigger_state, {'A', 'B', 'C'})
    
    # Should forbid B and C wires, but NOT A wire
    assert CellState(OccupantType.WIRE, net_id='B') in forbidden
    assert CellState(OccupantType.WIRE, net_id='C') in forbidden
    assert CellState(OccupantType.WIRE, net_id='A') not in forbidden
    assert EMPTY not in forbidden


def test_spacing_stencil():
    rule = SameLayerMinSpacing('M1', spacing_tracks=1)
    # Should have two entries: (M1, -1, 0) and (M1, +1, 0)
    assert len(rule.stencil) == 2
    assert ('M1', -1, 0) in rule.stencil
    assert ('M1', +1, 0) in rule.stencil


def test_along_track_stencil():
    rule = SameLayerAlongTrackSpacing('LI', spacing_ortho=1)
    assert len(rule.stencil) == 2
    assert ('LI', 0, -1) in rule.stencil
    assert ('LI', 0, +1) in rule.stencil


def test_anchor_layer_filtering():
    """Verify that M1 rules don't fire on LI cells."""
    engine = ConstraintEngine()
    engine.add_layer('LI', n_tracks=3, n_ortho=5)
    engine.add_layer('M1', n_tracks=3, n_ortho=5)
    
    for rule in create_mvp_drc_rules():
        engine.register_drc(rule)
    
    engine.initialize_domains({'A', 'B'})
    
    # Assign on LI — M1 rules should NOT affect LI neighbors
    state_a = CellState(OccupantType.WIRE, net_id='A')
    success = engine.assign(('LI', 1, 2), state_a)
    assert success
    
    # LI neighbor at track 0 should still allow net B
    # (because LI cross-track spacing is not in MVP rules)
    li_neighbor = engine.get_cell(('LI', 0, 2))
    state_b = CellState(OccupantType.WIRE, net_id='B')
    assert state_b in li_neighbor.domain


def test_along_track_same_net_ok():
    """Same net on adjacent ortho positions should be fine."""
    engine = ConstraintEngine()
    engine.add_layer('LI', n_tracks=3, n_ortho=10)
    engine.register_drc(SameLayerAlongTrackSpacing('LI', spacing_ortho=1))
    engine.initialize_domains({'A', 'B'})
    
    state_a = CellState(OccupantType.WIRE, net_id='A')
    
    # Assign consecutive cells on same track, same net
    for o in range(5):
        success = engine.assign(('LI', 1, o), state_a)
        assert success, f"Failed at ortho {o}"


def test_along_track_diff_net_blocked():
    """Different net on adjacent ortho position should be blocked."""
    engine = ConstraintEngine()
    engine.add_layer('LI', n_tracks=3, n_ortho=10)
    engine.register_drc(SameLayerAlongTrackSpacing('LI', spacing_ortho=1))
    engine.initialize_domains({'A', 'B'})
    
    state_a = CellState(OccupantType.WIRE, net_id='A')
    state_b = CellState(OccupantType.WIRE, net_id='B')
    
    engine.assign(('LI', 1, 3), state_a)
    result = engine.assign(('LI', 1, 4), state_b)
    assert result is False


def test_create_mvp_rules():
    rules = create_mvp_drc_rules()
    assert len(rules) >= 3
    
    # All should have anchor_layer set
    for rule in rules:
        assert rule.anchor_layer is not None


if __name__ == '__main__':
    test_spacing_trigger()
    test_spacing_forbidden()
    test_spacing_stencil()
    test_along_track_stencil()
    test_anchor_layer_filtering()
    test_along_track_same_net_ok()
    test_along_track_diff_net_blocked()
    test_create_mvp_rules()
    print("All DRC constraint tests passed!")
