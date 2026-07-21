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


# -------------------------------------------------------------------
# M2 transactional API: propose_assign / propose_release / commit_with_delta
# -------------------------------------------------------------------


def test_propose_assign_round_trip_restore():
    """propose_assign + restore returns the engine to its pre-checkpoint state.

    Covers the M1-era weakness: prior trail captured only domain, so a cell
    that flipped from EMPTY -> assigned -> restored could end up with a
    correct domain but a stale assignment. M2 trail captures both.
    """
    engine = _make_engine()
    state_a = CellState(OccupantType.WIRE, net_id='A')

    cp = engine.checkpoint()
    assert engine.propose_assign(('M1', 2, 2), state_a)
    assert engine.get_cell(('M1', 2, 2)).assignment == state_a

    engine.restore(cp)
    cell = engine.get_cell(('M1', 2, 2))
    assert cell.assignment == EMPTY
    assert cell.domain_size == 4  # 1 EMPTY + 3 wire states
    # Neighbour domain restored too.
    assert engine.get_cell(('M1', 1, 2)).domain_size == 4


def test_propose_release_then_restore_reinstates_assignment():
    """propose_release records prior assignment so restore puts it back."""
    engine = _make_engine()
    state_a = CellState(OccupantType.WIRE, net_id='A')

    # Pre-load: assign, then start a transaction.
    engine.propose_assign(('M1', 2, 2), state_a)
    cp = engine.checkpoint()

    assert engine.propose_release(('M1', 2, 2))
    assert engine.get_cell(('M1', 2, 2)).assignment == EMPTY

    engine.restore(cp)
    cell = engine.get_cell(('M1', 2, 2))
    assert cell.assignment == state_a
    assert state_a in cell.domain


def test_commit_with_delta_returns_assignment_changes():
    """commit_with_delta summarises (pos, prev, new) for cells that changed."""
    engine = _make_engine()
    state_a = CellState(OccupantType.WIRE, net_id='A')
    state_b = CellState(OccupantType.WIRE, net_id='B')

    cp = engine.checkpoint()
    assert engine.propose_assign(('M1', 2, 2), state_a)
    assert engine.propose_assign(('M1', 4, 4), state_b)

    delta = engine.commit_with_delta(cp)
    delta_map = {pos: (prev, new) for pos, prev, new in delta}

    assert delta_map[('M1', 2, 2)] == (EMPTY, state_a)
    assert delta_map[('M1', 4, 4)] == (EMPTY, state_b)
    # No spurious entries for neighbours whose only change was a domain shrink.
    assert all(pos in (('M1', 2, 2), ('M1', 4, 4)) for pos in delta_map)


def test_commit_with_delta_truncates_trail():
    """After commit, restore can only walk back to entries before the commit."""
    engine = _make_engine()
    state_a = CellState(OccupantType.WIRE, net_id='A')

    cp = engine.checkpoint()
    engine.propose_assign(('M1', 2, 2), state_a)
    engine.commit_with_delta(cp)
    # Trail past cp is gone.
    assert len(engine.trail) == cp


def test_propose_assign_failure_leaves_state_restorable():
    """A failed propose_assign + restore leaves no leaked state on neighbours."""
    engine = _make_engine()
    state_a = CellState(OccupantType.WIRE, net_id='A')
    state_b = CellState(OccupantType.WIRE, net_id='B')

    engine.propose_assign(('M1', 2, 2), state_a)
    cp = engine.checkpoint()

    # Adjacent track with a different net should be infeasible (spacing rule).
    ok = engine.propose_assign(('M1', 1, 2), state_b)
    assert ok is False

    engine.restore(cp)
    # Original assignment intact; neighbour domain back to whatever it was at cp.
    assert engine.get_cell(('M1', 2, 2)).assignment == state_a


def test_release_then_reassign_within_transaction():
    """Idempotent transaction: release a cell, then assign a new state, commit."""
    engine = _make_engine()
    state_a = CellState(OccupantType.WIRE, net_id='A')
    state_c = CellState(OccupantType.WIRE, net_id='C')

    engine.propose_assign(('M1', 2, 2), state_a)
    cp = engine.checkpoint()

    assert engine.propose_release(('M1', 2, 2))
    assert engine.propose_assign(('M1', 2, 2), state_c)

    delta = engine.commit_with_delta(cp)
    delta_map = {pos: (prev, new) for pos, prev, new in delta}
    # Net-net change: A -> C.
    assert delta_map[('M1', 2, 2)] == (state_a, state_c)


if __name__ == '__main__':
    test_assign_basic()
    test_spacing_propagation()
    test_assign_conflict()
    test_checkpoint_restore()
    test_out_of_bounds()
    test_domain_stats()
    test_propose_assign_round_trip_restore()
    test_propose_release_then_restore_reinstates_assignment()
    test_commit_with_delta_returns_assignment_changes()
    test_commit_with_delta_truncates_trail()
    test_propose_assign_failure_leaves_state_restorable()
    test_release_then_reassign_within_transaction()
    print("All CSP engine tests passed!")
