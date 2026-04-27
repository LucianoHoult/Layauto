"""
Layer-2 atomic operations.

Per ``docs/architecture_roadmap.md`` § C, L2 primitives only submit
cell-level proposals to the CSP engine. They do **not** produce L1
``EditOp`` records, do **not** mutate ``LayoutModel``, and do **not**
decide feasibility. The L3 macro brackets a sequence of L2 calls with
``engine.checkpoint`` / ``engine.commit_with_delta`` (or
``engine.restore`` on failure); the decoder synthesizes L1 from the
commit delta + macro-level intent.

M2 ships the subset needed by the ``device_resize`` macro: track-segment
release/assign/modify on CSP-modeled layers (today: LI / M1). The
remaining primitives listed in the roadmap (``extend_od``, ``extend_poly``,
``add/remove_fin_strip``, ``add/remove_cut_cell``,
``mark_shared_diffusion``) wait for B-tier ``CellOccupancy`` (M4); FIN /
OD / POLY / NWELL / BOUNDARY remain on the non-CSP side-channel for now
and the macro emits their L1 records directly.
"""

from dataclasses import dataclass, field
from typing import Iterable, List, Tuple

from core.csp_engine import ConstraintEngine
from core.data_model import CellState, OccupantType


@dataclass
class AtomicResult:
    """Outcome of a single L2 primitive.

    ``success`` is the engine's feasibility verdict. ``failed_pos`` records
    the cell position that triggered an infeasible ``propose_assign``,
    helping the L3 macro localise conflicts (e.g. LI-vs-VIA collisions).
    """
    success: bool
    failed_pos: Tuple = None
    detail: str = ''


def release_segment_cells(engine: ConstraintEngine,
                           layer: str,
                           track_idx: int,
                           ortho_indices: Iterable[int]) -> AtomicResult:
    """Release a contiguous (or arbitrary) set of cells along one track.

    Always succeeds for cells inside the engine's grid; cells outside the
    grid are silently skipped (the engine never modelled them).
    """
    for o in ortho_indices:
        pos = (layer, track_idx, o)
        if engine.get_cell(pos) is None:
            continue
        engine.propose_release(pos)
    return AtomicResult(success=True)


def assign_segment_cells(engine: ConstraintEngine,
                          layer: str,
                          track_idx: int,
                          ortho_indices: Iterable[int],
                          net_id: str) -> AtomicResult:
    """Assign WIRE cells along one track. First infeasible cell aborts.

    A short-circuit on the first failure leaves the trail intact so the
    macro can ``restore`` the most recent checkpoint.
    """
    state = CellState(OccupantType.WIRE, net_id=net_id)
    for o in ortho_indices:
        pos = (layer, track_idx, o)
        if engine.get_cell(pos) is None:
            continue
        if not engine.propose_assign(pos, state):
            return AtomicResult(
                success=False,
                failed_pos=pos,
                detail=f'propose_assign infeasible at {pos} for net {net_id!r}',
            )
    return AtomicResult(success=True)


def modify_segment(engine: ConstraintEngine,
                    layer: str,
                    track_idx: int,
                    old_ortho_indices: Iterable[int],
                    new_ortho_indices: Iterable[int],
                    net_id: str) -> AtomicResult:
    """Resize a track segment by releasing dropped cells and assigning new ones.

    The macro is responsible for ordering: this primitive does not commit;
    it just stages proposals. Cells in both ranges are left untouched.
    """
    old_set = set(old_ortho_indices)
    new_set = set(new_ortho_indices)
    drop = old_set - new_set
    add = new_set - old_set

    rel = release_segment_cells(engine, layer, track_idx, sorted(drop))
    if not rel.success:
        return rel
    return assign_segment_cells(engine, layer, track_idx, sorted(add), net_id)


__all__ = [
    'AtomicResult',
    'release_segment_cells',
    'assign_segment_cells',
    'modify_segment',
]
