"""M4b: net-equivalence union-find on ``ConstraintEngine``.

Covers:
  * ``mark_cut`` semantics — pin cell as ``OccupantType.CUT``, idempotent,
    refuses to overwrite an annotated assignment.
  * ``union`` preconditions — adjacency (Manhattan-1, same layer),
    same-net, neither endpoint CUT, both cells exist.
  * ``net_of`` / ``connected_to`` / ``connected_cells`` query API.
  * Union-find restores under ``checkpoint`` / ``restore``.
  * ``commit_with_full_delta`` returns both cell delta and union delta;
    legacy ``commit_with_delta`` keeps its single-list return.
  * "no CUT between adjacent cells" rule manifests as: a chain of
    unions along a track stops at a CUT cell — cells on opposite sides
    of the CUT cannot end up in the same equivalence class.

Roadmap: docs/architecture_roadmap.md §B and milestone M4.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core.csp_engine import CommitDelta, ConstraintEngine
from core.data_model import CellState, EMPTY, OccupantType


def _engine_with_li_track():
    """A minimal engine with one LI layer, 1 × 6 cells, no DRC rules."""
    engine = ConstraintEngine()
    engine.add_layer('LI', n_tracks=1, n_ortho=6)
    engine.initialize_domains({'A', 'B'})
    return engine


def _wire(net):
    return CellState(OccupantType.WIRE, net_id=net)


# =============================================================
# mark_cut
# =============================================================

def test_mark_cut_pins_cell():
    engine = _engine_with_li_track()
    pos = ('LI', 0, 2)
    assert engine.mark_cut(pos) is True
    cell = engine.get_cell(pos)
    assert cell.assignment.occ_type == OccupantType.CUT
    assert cell.fixed is True
    assert cell.domain == {CellState(OccupantType.CUT)}


def test_mark_cut_idempotent_on_existing_cut():
    engine = _engine_with_li_track()
    pos = ('LI', 0, 2)
    assert engine.mark_cut(pos) is True
    assert engine.mark_cut(pos) is True   # idempotent


def test_mark_cut_refuses_to_overwrite_annotated_assignment():
    """Conservative-default: don't silently re-stamp a routed cell.
    Mirrors the policy from ``mark_blockage`` (M3)."""
    engine = _engine_with_li_track()
    pos = ('LI', 0, 2)
    assert engine.assign(pos, _wire('A'))
    assert engine.mark_cut(pos) is False


def test_mark_cut_returns_false_for_out_of_grid():
    engine = _engine_with_li_track()
    assert engine.mark_cut(('LI', 99, 99)) is False


# =============================================================
# union preconditions
# =============================================================

def test_union_adjacent_same_net_succeeds():
    engine = _engine_with_li_track()
    a, b = ('LI', 0, 1), ('LI', 0, 2)
    engine.assign(a, _wire('A'))
    engine.assign(b, _wire('A'))
    assert engine.union(a, b) is True


def test_union_idempotent_on_already_unioned():
    engine = _engine_with_li_track()
    a, b = ('LI', 0, 1), ('LI', 0, 2)
    engine.assign(a, _wire('A'))
    engine.assign(b, _wire('A'))
    assert engine.union(a, b) is True
    assert engine.union(a, b) is True   # already same component


def test_union_rejects_different_nets():
    engine = _engine_with_li_track()
    a, b = ('LI', 0, 1), ('LI', 0, 2)
    engine.assign(a, _wire('A'))
    # Avoid spacing rules by picking distance-1 different nets — but
    # there are no DRC rules in this fixture.
    engine.assign(b, _wire('B'))
    assert engine.union(a, b) is False


def test_union_rejects_non_adjacent_cells():
    """Skipping a cell isn't union — distance-2 must go through the
    middle cell or fail. This makes the CUT rule emergent: a chain
    through a CUT cell requires unioning with the CUT cell itself,
    which is rejected."""
    engine = _engine_with_li_track()
    a, c = ('LI', 0, 1), ('LI', 0, 3)
    engine.assign(a, _wire('A'))
    engine.assign(c, _wire('A'))
    # Distance = 2; rejected.
    assert engine.union(a, c) is False


def test_union_rejects_cross_layer():
    engine = ConstraintEngine()
    engine.add_layer('LI', n_tracks=1, n_ortho=3)
    engine.add_layer('M1', n_tracks=1, n_ortho=3)
    engine.initialize_domains({'A'})
    engine.assign(('LI', 0, 0), _wire('A'))
    engine.assign(('M1', 0, 0), _wire('A'))
    assert engine.union(('LI', 0, 0), ('M1', 0, 0)) is False


def test_union_rejects_cut_endpoint():
    """A union step where either cell is a CUT is rejected — this is
    how §B's "no CUT between adjacent cells" rule fires for a chain
    crossing a CUT."""
    engine = _engine_with_li_track()
    a, mid, b = ('LI', 0, 1), ('LI', 0, 2), ('LI', 0, 3)
    engine.assign(a, _wire('A'))
    engine.mark_cut(mid)
    engine.assign(b, _wire('A'))
    # Adjacent unions through the CUT must each fail at the CUT step.
    assert engine.union(a, mid) is False
    assert engine.union(mid, b) is False
    # And the two endpoints end up in disjoint components.
    assert engine.connected_to(a) == [a]
    assert engine.connected_to(b) == [b]


def test_union_rejects_unknown_position():
    engine = _engine_with_li_track()
    a = ('LI', 0, 1)
    engine.assign(a, _wire('A'))
    assert engine.union(a, ('LI', 99, 99)) is False


# =============================================================
# query API
# =============================================================

def test_net_of_for_unassigned_cell():
    engine = _engine_with_li_track()
    assert engine.net_of(('LI', 0, 0)) is None
    assert engine.net_of(('LI', 99, 99)) is None


def test_net_of_for_assigned_singleton_cell():
    engine = _engine_with_li_track()
    a = ('LI', 0, 0)
    engine.assign(a, _wire('A'))
    assert engine.net_of(a) == 'A'


def test_net_of_after_union_chain():
    """Three adjacent A-net cells → all share net_of after pairwise
    union. The union-find should expose 'A' from every member."""
    engine = _engine_with_li_track()
    cells = [('LI', 0, 1), ('LI', 0, 2), ('LI', 0, 3)]
    for c in cells:
        engine.assign(c, _wire('A'))
    engine.union(cells[0], cells[1])
    engine.union(cells[1], cells[2])
    for c in cells:
        assert engine.net_of(c) == 'A'


def test_connected_to_returns_full_component():
    engine = _engine_with_li_track()
    cells = [('LI', 0, 1), ('LI', 0, 2), ('LI', 0, 3)]
    for c in cells:
        engine.assign(c, _wire('A'))
    engine.union(cells[0], cells[1])
    engine.union(cells[1], cells[2])
    component = engine.connected_to(cells[0])
    assert sorted(component) == sorted(cells)
    # Querying from any member returns the same set.
    assert engine.connected_to(cells[2]) == component


def test_connected_to_singleton_is_self():
    engine = _engine_with_li_track()
    pos = ('LI', 0, 0)
    engine.assign(pos, _wire('A'))
    assert engine.connected_to(pos) == [pos]


def test_connected_cells_returns_all_assigned_with_net():
    engine = _engine_with_li_track()
    a1 = ('LI', 0, 0)
    a2 = ('LI', 0, 5)   # not adjacent to a1; never unioned
    engine.assign(a1, _wire('A'))
    engine.assign(a2, _wire('A'))
    cells = engine.connected_cells('A')
    assert set(cells) == {a1, a2}


# =============================================================
# checkpoint / restore including union-find
# =============================================================

def test_restore_undoes_unions():
    engine = _engine_with_li_track()
    a, b = ('LI', 0, 1), ('LI', 0, 2)
    engine.assign(a, _wire('A'))
    engine.assign(b, _wire('A'))
    cp = engine.checkpoint()
    assert engine.union(a, b) is True
    assert engine.connected_to(a) == sorted([a, b])
    engine.restore(cp)
    # Both cells are back as singletons.
    assert engine.connected_to(a) == [a]
    assert engine.connected_to(b) == [b]


def test_restore_undoes_chain_in_reverse():
    engine = _engine_with_li_track()
    cells = [('LI', 0, 0), ('LI', 0, 1), ('LI', 0, 2), ('LI', 0, 3)]
    for c in cells:
        engine.assign(c, _wire('A'))
    cp = engine.checkpoint()
    engine.union(cells[0], cells[1])
    engine.union(cells[1], cells[2])
    engine.union(cells[2], cells[3])
    assert sorted(engine.connected_to(cells[0])) == sorted(cells)
    engine.restore(cp)
    # All four cells revert to singletons.
    for c in cells:
        assert engine.connected_to(c) == [c]


# =============================================================
# commit_with_full_delta
# =============================================================

def test_commit_with_full_delta_returns_cells_and_unions():
    engine = _engine_with_li_track()
    a, b = ('LI', 0, 1), ('LI', 0, 2)
    cp = engine.checkpoint()
    engine.assign(a, _wire('A'))
    engine.assign(b, _wire('A'))
    engine.union(a, b)

    delta = engine.commit_with_full_delta(cp)
    assert isinstance(delta, CommitDelta)
    # Cell delta: two assigns (EMPTY -> WIRE A) for a, b.
    assert len(delta.cells) == 2
    assert {pos for pos, _, _ in delta.cells} == {a, b}
    # Union delta: one entry covering the (a, b) merge.
    assert len(delta.unions) == 1
    pair = delta.unions[0]
    assert set(pair) == {a, b}


def test_commit_with_full_delta_truncates_both_trails():
    engine = _engine_with_li_track()
    a, b = ('LI', 0, 1), ('LI', 0, 2)
    cp = engine.checkpoint()
    engine.assign(a, _wire('A'))
    engine.assign(b, _wire('A'))
    engine.union(a, b)
    engine.commit_with_full_delta(cp)
    # A subsequent restore at the committed checkpoint must be a no-op
    # (commit is non-restorable; the trail was truncated).
    engine.restore(cp)
    # Union state remains committed.
    assert engine.connected_to(a) == sorted([a, b])


def test_legacy_commit_with_delta_still_returns_list():
    """The M2-era ``commit_with_delta`` must keep its list return — the
    solver's ``len(delta)`` call site at ``core/solver.py:351`` depends
    on it. M4b adds ``commit_with_full_delta`` as a parallel method;
    it does not break the legacy one."""
    engine = _engine_with_li_track()
    a = ('LI', 0, 1)
    cp = engine.checkpoint()
    engine.assign(a, _wire('A'))
    delta = engine.commit_with_delta(cp)
    assert isinstance(delta, list)
    assert len(delta) == 1


def test_legacy_commit_drops_union_trail():
    """``commit_with_delta`` doesn't surface unions but must still
    truncate the union trail so subsequent ``restore`` doesn't try to
    revert committed unions."""
    engine = _engine_with_li_track()
    a, b = ('LI', 0, 1), ('LI', 0, 2)
    cp = engine.checkpoint()
    engine.assign(a, _wire('A'))
    engine.assign(b, _wire('A'))
    engine.union(a, b)
    engine.commit_with_delta(cp)
    engine.restore(cp)
    assert engine.connected_to(a) == sorted([a, b])


if __name__ == '__main__':
    # mark_cut
    test_mark_cut_pins_cell()
    test_mark_cut_idempotent_on_existing_cut()
    test_mark_cut_refuses_to_overwrite_annotated_assignment()
    test_mark_cut_returns_false_for_out_of_grid()
    # union preconditions
    test_union_adjacent_same_net_succeeds()
    test_union_idempotent_on_already_unioned()
    test_union_rejects_different_nets()
    test_union_rejects_non_adjacent_cells()
    test_union_rejects_cross_layer()
    test_union_rejects_cut_endpoint()
    test_union_rejects_unknown_position()
    # query API
    test_net_of_for_unassigned_cell()
    test_net_of_for_assigned_singleton_cell()
    test_net_of_after_union_chain()
    test_connected_to_returns_full_component()
    test_connected_to_singleton_is_self()
    test_connected_cells_returns_all_assigned_with_net()
    # restore
    test_restore_undoes_unions()
    test_restore_undoes_chain_in_reverse()
    # commit_with_full_delta
    test_commit_with_full_delta_returns_cells_and_unions()
    test_commit_with_full_delta_truncates_both_trails()
    test_legacy_commit_with_delta_still_returns_list()
    test_legacy_commit_drops_union_trail()
    print("All M4b net-equivalence tests passed!")
