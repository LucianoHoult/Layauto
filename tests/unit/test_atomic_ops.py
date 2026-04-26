"""Test L2 atomic ops: cell-level proposals + conflict detection.

Per docs/architecture_roadmap.md M2: L2 primitives only submit
cell-level proposals to the CSP engine. They never produce L1 EditOps
or mutate the LayoutModel; the L3 macro brackets a sequence of L2
calls with engine.checkpoint / engine.commit_with_delta and consumes
the cell delta.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core.csp_engine import ConstraintEngine
from core.data_model import CellState, OccupantType, EMPTY
from core.drc_constraints import SameLayerMinSpacing
from core import atomic_ops


def _make_engine():
    engine = ConstraintEngine()
    engine.add_layer('LI', n_tracks=3, n_ortho=10)
    engine.register_drc(SameLayerMinSpacing('LI', spacing_tracks=1))
    engine.initialize_domains({'A', 'B'})
    return engine


def test_release_segment_cells_records_trail():
    engine = _make_engine()
    state_a = CellState(OccupantType.WIRE, net_id='A')
    engine.propose_assign(('LI', 1, 4), state_a)
    cp = engine.checkpoint()

    res = atomic_ops.release_segment_cells(engine, 'LI', 1, [4])
    assert res.success
    assert engine.get_cell(('LI', 1, 4)).assignment == EMPTY

    # Restore must put the cell back exactly where it was.
    engine.restore(cp)
    assert engine.get_cell(('LI', 1, 4)).assignment == state_a


def test_assign_segment_cells_succeeds_for_clean_path():
    engine = _make_engine()
    res = atomic_ops.assign_segment_cells(engine, 'LI', 1, [2, 3, 4], 'A')
    assert res.success
    state_a = CellState(OccupantType.WIRE, net_id='A')
    for o in (2, 3, 4):
        assert engine.get_cell(('LI', 1, o)).assignment == state_a


def test_modify_segment_extension_conflict_returns_failure():
    """Extending into a cell already assigned to a conflicting net fails.

    This is the M2 conflict scenario described in the roadmap acceptance:
    a cell-level proposal is rejected, the macro can localise via
    ``failed_pos``, and the engine state stays restorable.
    """
    engine = _make_engine()
    state_b = CellState(OccupantType.WIRE, net_id='B')
    # Pre-occupy ortho=7 on track 1 with net B.
    assert engine.propose_assign(('LI', 1, 7), state_b)
    cp = engine.checkpoint()

    # Net A tries to extend a segment from {3,4} to {3,4,5,6,7} — cell 7
    # is already net B's, so propose_assign fails there.
    res = atomic_ops.modify_segment(
        engine, 'LI', track_idx=1,
        old_ortho_indices=[3, 4],
        new_ortho_indices=[3, 4, 5, 6, 7],
        net_id='A',
    )
    assert not res.success
    assert res.failed_pos == ('LI', 1, 7)

    # Engine state restorable: the failure left a partial trail; the
    # caller restores to the pre-call checkpoint.
    engine.restore(cp)
    assert engine.get_cell(('LI', 1, 7)).assignment == state_b
    # No leakage on cells 5, 6.
    assert engine.get_cell(('LI', 1, 5)).assignment == EMPTY
    assert engine.get_cell(('LI', 1, 6)).assignment == EMPTY


def test_modify_segment_pure_shrink_no_assigns():
    """Shrinking a segment only releases cells; no propose_assign happens."""
    engine = _make_engine()
    state_a = CellState(OccupantType.WIRE, net_id='A')
    for o in (3, 4, 5, 6):
        assert engine.propose_assign(('LI', 1, o), state_a)

    res = atomic_ops.modify_segment(
        engine, 'LI', track_idx=1,
        old_ortho_indices=[3, 4, 5, 6],
        new_ortho_indices=[3, 4],
        net_id='A',
    )
    assert res.success
    assert engine.get_cell(('LI', 1, 5)).assignment == EMPTY
    assert engine.get_cell(('LI', 1, 6)).assignment == EMPTY
    # Surviving cells untouched.
    assert engine.get_cell(('LI', 1, 3)).assignment == state_a
    assert engine.get_cell(('LI', 1, 4)).assignment == state_a


if __name__ == '__main__':
    test_release_segment_cells_records_trail()
    test_assign_segment_cells_succeeds_for_clean_path()
    test_modify_segment_extension_conflict_returns_failure()
    test_modify_segment_pure_shrink_no_assigns()
    print("All atomic_ops tests passed!")
