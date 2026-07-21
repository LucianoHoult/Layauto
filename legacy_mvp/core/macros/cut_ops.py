"""L3 ``add_cut`` / ``remove_cut`` macros (M6).

Per docs/architecture_roadmap.md §B and §M6, a CPO / M0_CUT / FIN_CUT
shape on the cut layer breaks net-equivalence across the cut location.
The L3 ``add_cut`` macro:

  * opens a checkpoint on the engine,
  * calls ``atomic_ops.add_cut_cell`` (which routes through
    ``engine.mark_cut`` when the cut layer is engine-modelled and stamps
    a B-tier ``CellOccupancy`` of type ``OccupantType.CUT``),
  * on success, calls ``engine.commit_with_full_delta`` and surfaces
    the cell + union deltas through ``CutMacroResult``;
  * on failure (the cell already carries an annotated assignment, per
    the conservative-defaults rule §D), restores to the checkpoint and
    returns ``success=False``.

``remove_cut`` is the inverse on the grid side: drops the
``CellOccupancy`` from the B-tier cell-grid storage. Per the M4d
contract on ``atomic_ops.remove_cut_cell``, it does NOT un-pin the
engine cell — undoing a CUT through the engine requires invalidating
any prior unions that routed around it, which is M6's
``split_diffusion`` responsibility (deferred). For the macro contract,
``remove_cut`` is grid-only and idempotent; the engine cell stays
``fixed=True`` until the next ``initialize_domains`` call.

Both macros emit no L1 ``EditOp``s today: cut layers (CPO / M0_CUT /
FIN_CUT) have no ``LAYER_MAP`` GDS-number entries in ``tech/layer_map.py``
and so don't appear in the GDS or SKILL writeback yet (the §M4 note
flags this). When the cut layers grow GDS-number entries, the macros
will start emitting ``add_shape`` / ``remove_shape`` records that
flow through the decoder's Phase 1 — the seam stays consistent because
the macros already build their ``CutMacroResult`` from the L2 atomic's
return value.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from core import atomic_ops
from core.csp_engine import CommitDelta, ConstraintEngine
from core.data_model import ShapeRecord
from core.diff import EditOp


@dataclass
class CutMacroResult:
    """Outcome of ``add_cut`` / ``remove_cut``.

    ``success`` mirrors the L2 atomic's verdict.
    ``edit_ops`` is the L1 stream the macro emits (empty today; see
    module docstring).
    ``commit_delta`` is the engine's ``CommitDelta`` for ``add_cut``
    (cells + unions changed since the checkpoint), or ``None`` for
    ``remove_cut`` (which does not interact with the engine today).
    ``failed_pos`` is set when ``success=False`` so the caller can
    localise the conflict.
    ``detail`` is a free-form string mirroring the L2 atomic's detail.
    """
    success: bool
    edit_ops: List[EditOp] = field(default_factory=list)
    commit_delta: Optional[CommitDelta] = None
    failed_pos: Optional[Tuple] = None
    detail: str = ''


def add_cut(engine: ConstraintEngine,
              grid,
              layer: str,
              track_a: int,
              track_b: int,
              shape_record: Optional[ShapeRecord] = None) -> CutMacroResult:
    """Add a CUT cell at ``(layer, track_a, track_b)`` transactionally.

    Brackets the L2 ``add_cut_cell`` call in
    ``engine.checkpoint`` / ``engine.commit_with_full_delta``. On the
    L2 atomic's failure (engine refused to overwrite an annotated
    assignment), the engine is restored to the pre-call checkpoint
    and the result reports ``failed_pos`` from the atomic.

    The §B "no CUT between adjacent cells" rule fires through the
    union-find: any subsequent ``engine.union`` across this cell is
    rejected by the precondition check, so a chain of unions cannot
    cross the new CUT. The L2 atomic's ``engine.mark_cut`` pins the
    cell directly (bypassing the trail), so ``CommitDelta.cells`` is
    typically empty for ``add_cut`` — the actual change lives on the
    engine cell's ``fixed`` flag, not in the trail-replay delta.

    ``engine`` must be a real ``ConstraintEngine`` (it can be empty —
    a grid-only stamp still happens because ``add_cut_cell`` skips its
    engine branch when the cut layer is not in ``engine.layer_dims``).
    """
    cp = engine.checkpoint()
    atomic = atomic_ops.add_cut_cell(
        engine=engine, grid=grid, layer=layer,
        track_a=track_a, track_b=track_b,
        shape_record=shape_record,
    )
    if not atomic.success:
        engine.restore(cp)
        return CutMacroResult(
            success=False,
            failed_pos=atomic.failed_pos,
            detail=atomic.detail,
        )
    delta = engine.commit_with_full_delta(cp)
    return CutMacroResult(
        success=True,
        commit_delta=delta,
        detail=atomic.detail,
    )


def remove_cut(grid,
                 layer: str,
                 track_a: int,
                 track_b: int) -> CutMacroResult:
    """Remove the CUT cell at ``(layer, track_a, track_b)`` from the grid.

    Idempotent: returns ``success=True`` whether or not the cell was
    present. The engine side is intentionally NOT reverted (see module
    docstring); the macro's contract is grid-only for now.
    """
    atomic = atomic_ops.remove_cut_cell(
        grid=grid, layer=layer,
        track_a=track_a, track_b=track_b,
    )
    return CutMacroResult(
        success=atomic.success,
        detail=atomic.detail,
    )
