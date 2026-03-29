"""Test CSP engine: assign, propagation, checkpoint/restore."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core.csp_engine import ConstraintEngine
from core.data_model import CellState, OccupantType, EMPTY
from core.drc_constraints import SameLayerMinSpacing, SameLayerAlongTrackSpacing


def _make_engine():
    engine = ConstraintEngine()
    engine.add_layer('M1', n_tracks=5, n_ortho=5)
    engine.register_drc(SameLayerMinSpacing('M1', spacing_tracks=1))
    engine.initialize_domains({'A', 'B', 'C'})
    return engine


def test_assign_basic():
    engine = _make_engine()
    state_a = CellState(OccupantType.WIRE, net_id='A')
    assert engine.assign(('M1', 2, 2), state_a)
    cell = engine.get_cell(('M1', 2, 2))
    assert cell.assignment == state_a
    assert cell.domain_size == 1


def test_spacing_propagation():
    engine = _make_engine()
    state_a = CellState(OccupantType.WIRE, net_id='A')
    engine.assign(('M1', 2, 2), state_a)
    
    # Adjacent track should not allow different net
    state_b = CellState(OccupantType.WIRE, net_id='B')
    neighbor = engine.get_cell(('M1', 1, 2))
    assert state_b not in neighbor.domain
    
    # Same net on adjacent track should still be possible
    assert state_a in neighbor.domain


def test_assign_conflict():
    engine = _make_engine()
    state_a = CellState(OccupantType.WIRE, net_id='A')
    state_b = CellState(OccupantType.WIRE, net_id='B')
    
    engine.assign(('M1', 2, 2), state_a)
    result = engine.assign(('M1', 1, 2), state_b)
    assert result is False  # Should fail: spacing violation


def test_checkpoint_restore():
    engine = _make_engine()
    state_a = CellState(OccupantType.WIRE, net_id='A')
    
    cp = engine.checkpoint()
    engine.assign(('M1', 2, 2), state_a)
    
    # After assign, neighbor domain should be reduced
    neighbor = engine.get_cell(('M1', 1, 2))
    assert neighbor.domain_size < 4  # Was 4 (EMPTY + 3 wires)
    
    # Restore
    engine.restore(cp)
    neighbor = engine.get_cell(('M1', 1, 2))
    assert neighbor.domain_size == 4  # Back to full


def test_out_of_bounds():
    engine = _make_engine()
    state = CellState(OccupantType.WIRE, net_id='A')
    result = engine.assign(('M1', 99, 99), state)
    assert result is False


def test_domain_stats():
    engine = _make_engine()
    stats = engine.domain_stats('M1')
    assert stats['total_cells'] == 25
    assert stats['assigned'] == 0
    assert stats['empty_domain'] == 0


if __name__ == '__main__':
    test_assign_basic()
    test_spacing_propagation()
    test_assign_conflict()
    test_checkpoint_restore()
    test_out_of_bounds()
    test_domain_stats()
    print("All CSP engine tests passed!")
