"""L3 ``share_diffusion`` macro (M6).

Per docs/architecture_roadmap.md §B and §M6, two devices share S/D when
the OD cells between them carry one device as ``owner_device_id`` and
the other on ``shared_with[]``. The L3 ``share_diffusion`` macro takes
two ``Device.inst_name`` strings and:

  * opens a checkpoint on the engine,
  * calls ``atomic_ops.mark_shared_diffusion`` (which walks
    ``grid.b_tier_cells_of('OD')``, stamps ``shared_with`` on every
    cell whose owner is one of the pair, and opportunistically calls
    ``engine.union`` on adjacent OD-cell engine pairs — M4e wired OD
    into the engine so the unions actually fire today),
  * on success, calls ``engine.commit_with_full_delta`` and surfaces
    the cell + union deltas through ``ShareDiffusionResult``;
  * on failure (no engine, or no OD cells, or any union precondition
    that explicitly fails — the L2 atomic doesn't currently surface
    this case but the macro is robust to it), restores to the
    checkpoint and returns ``success=False``.

The §B "no CUT between adjacent cells" rule fires naturally: a CUT
cell between two OD cells fails the union precondition (cells with
``occ_type=CUT`` cannot union), so the chain of unions inside the
shared region stops at the cut. The cells past the cut keep their
own component, which is the correct net-equivalence outcome.

The macro emits no L1 ``EditOp``s today: shared diffusion is a metadata
relationship, not a new shape. SKILL/GDS still emits a single OD shape
per contiguous run regardless of how many devices share it. M6+ may
add a ``share_diffusion_metadata`` EditOp variant if downstream
SKILL emission needs to surface ``shared_with`` provenance.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from core import atomic_ops
from core.csp_engine import CommitDelta, ConstraintEngine
from core.diff import EditOp


@dataclass
class ShareDiffusionResult:
    """Outcome of ``share_diffusion``.

    ``success`` mirrors the L2 atomic's verdict.
    ``edit_ops`` is the L1 stream the macro emits (empty today; see
    module docstring).
    ``commit_delta`` carries the engine's cell + union deltas; M6
    follow-ups (``split_diffusion``, decoder consumption of unions)
    will read from this. ``None`` when the macro short-circuits before
    opening a transaction (``engine is None``).
    ``cells_stamped`` and ``cells_unioned`` mirror the L2 atomic's
    detail counts so the pipeline can log "stamped N, unioned M"
    without re-parsing the detail string.
    """
    success: bool
    edit_ops: List[EditOp] = field(default_factory=list)
    commit_delta: Optional[CommitDelta] = None
    cells_stamped: int = 0
    cells_unioned: int = 0
    detail: str = ''


def share_diffusion(engine: Optional[ConstraintEngine],
                      grid,
                      dev_a_inst: str,
                      dev_b_inst: str) -> ShareDiffusionResult:
    """Mark every OD cell shared between ``dev_a_inst`` and ``dev_b_inst``.

    Brackets ``atomic_ops.mark_shared_diffusion`` in
    ``engine.checkpoint`` / ``engine.commit_with_full_delta`` so the
    union events lands in the commit delta the macro returns. When
    ``engine`` is None, the call routes straight to the L2 atomic
    (grid-side stamp only), which is the M4d MVP-fixture path.
    """
    if grid is None:
        return ShareDiffusionResult(
            success=True,
            detail='no grid',
        )

    if engine is None:
        atomic = atomic_ops.mark_shared_diffusion(
            grid=grid, engine=None,
            dev_a_inst=dev_a_inst, dev_b_inst=dev_b_inst,
        )
        stamped, unioned = _parse_detail(atomic.detail)
        return ShareDiffusionResult(
            success=atomic.success,
            cells_stamped=stamped,
            cells_unioned=unioned,
            detail=atomic.detail,
        )

    cp = engine.checkpoint()
    atomic = atomic_ops.mark_shared_diffusion(
        grid=grid, engine=engine,
        dev_a_inst=dev_a_inst, dev_b_inst=dev_b_inst,
    )
    if not atomic.success:
        engine.restore(cp)
        stamped, unioned = _parse_detail(atomic.detail)
        return ShareDiffusionResult(
            success=False,
            cells_stamped=stamped,
            cells_unioned=unioned,
            detail=atomic.detail,
        )
    delta = engine.commit_with_full_delta(cp)
    stamped, unioned = _parse_detail(atomic.detail)
    return ShareDiffusionResult(
        success=True,
        commit_delta=delta,
        cells_stamped=stamped,
        cells_unioned=unioned,
        detail=atomic.detail,
    )


def _parse_detail(detail: str) -> tuple:
    """Parse the L2 atomic's "stamped N cells, unioned M pairs" detail.

    Returns ``(stamped, unioned)``. Falls back to ``(0, 0)`` on
    unrecognised formats — the L2 atomic is the source of truth, so we
    don't validate the format strictly.
    """
    stamped = 0
    unioned = 0
    if not detail:
        return stamped, unioned
    # Format: "stamped {N} cells, unioned {M} pairs"
    parts = detail.split(',')
    for part in parts:
        tokens = part.strip().split()
        if len(tokens) >= 2 and tokens[0] == 'stamped':
            try:
                stamped = int(tokens[1])
            except ValueError:
                pass
        elif len(tokens) >= 2 and tokens[0] == 'unioned':
            try:
                unioned = int(tokens[1])
            except ValueError:
                pass
    return stamped, unioned
