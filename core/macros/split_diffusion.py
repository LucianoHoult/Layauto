"""L3 ``split_diffusion`` macro (M6b).

Inverse of M6a's ``share_diffusion``: walks the OD cells previously
shared between two devices and removes the sibling from each cell's
``shared_with`` list. Optionally calls ``add_cut`` on the boundary OD
cells to physically isolate the previously-shared region — per
docs/architecture_roadmap.md §C, when devices remain physically
adjacent the macro must add a CPO before clearing ``shared_with`` to
avoid a transient short circuit. The recipient pattern is
``add_cut`` first, ``remove_sharer`` second.

**Engine-side limitation.** The M4b union-find's ``_uf_undo_one``
undoes the *most recent* union; it does not selectively split a
component. This macro therefore does NOT actively un-merge engine
union-find state. Instead:

  * The §B "no CUT between adjacent cells" rule, fired through the
    optional ``add_cut`` step, prevents *future* unions across the
    cut location.
  * The next ``checkpoint`` / ``restore`` cycle resets the merged
    component naturally.

For the MVP fixture this is sufficient: there are no multi-step
diffusion split-then-share-elsewhere workloads where stale union
state would matter. M6d / M7 may need a path-aware union-find if
that workload appears.

The macro emits no L1 ``EditOp``s for the `shared_with` mutation
(it's metadata, not geometry). The optional cut step *may* emit L1
records once cut layers have GDS-number entries (M6d).
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from core.csp_engine import CommitDelta, ConstraintEngine
from core.data_model import OccupantType
from core.diff import EditOp
from core.macros.cut_ops import add_cut, CutMacroResult


@dataclass
class SplitDiffusionResult:
    """Outcome of ``split_diffusion``.

    ``cells_unshared`` is the number of OD cells whose ``shared_with``
    list shrank.
    ``cuts_added`` lists the cut macro results when boundary cuts were
    requested via ``add_cut_at_boundary=True``; empty otherwise.
    ``commit_delta`` carries the cut-step engine deltas (concatenated
    across all per-cut transactions).
    ``edit_ops`` is the L1 stream — empty for the MVP because cut
    layers don't yet have GDS-number entries; M6d lights this up.
    """
    success: bool
    cells_unshared: int = 0
    cuts_added: List[CutMacroResult] = field(default_factory=list)
    commit_delta: Optional[CommitDelta] = None
    edit_ops: List[EditOp] = field(default_factory=list)
    detail: str = ''


def split_diffusion(engine: Optional[ConstraintEngine],
                      grid,
                      dev_a_inst: str,
                      dev_b_inst: str,
                      cut_at_track_a: Optional[int] = None,
                      cut_layer: str = 'CPO') -> SplitDiffusionResult:
    """Remove the shared-diffusion link between two devices.

    Walks ``grid.b_tier_cells_of('OD')``. For every cell whose owner
    is ``dev_a_inst`` and whose ``shared_with`` lists ``dev_b_inst``
    (or vice versa), removes the sibling from the list. Tracks the
    count of cells affected.

    When ``cut_at_track_a`` is passed (an explicit POLY track index
    where the gate-cut should land), the macro calls ``add_cut`` on
    every cell in the affected region whose ``track_a == cut_at_track_a``.
    The §B rule then prevents future unions across the cut. When
    ``cut_at_track_a`` is None (the default), only the metadata
    mutation lands; callers are responsible for physical isolation
    if the layout requires it.

    Why explicit and not auto-detected: in the M4c projection, a
    single OD shape gets a single ``owner_device_id`` (the first
    matching device by geometric containment), so cell-ownership
    transitions don't reliably mark the gate boundary. The proper
    boundary is the POLY track between the two devices' gates —
    information that lives on ``Device.gate_track_idx`` once devices
    are placed with reliable gate metadata. The auto-detection rule
    is M6d's responsibility (when ``Device.gate_track_idx`` is wired
    up end-to-end through the parser); for M6b the explicit form
    keeps the macro testable without committing to a half-baked
    heuristic.

    The macro does not actively split the engine union-find — see
    module docstring. ``commit_delta`` is the merge of all per-cut
    sub-transactions when cuts are requested; ``None`` when no cuts
    were added (no transaction was opened).
    """
    if grid is None:
        return SplitDiffusionResult(success=True, detail='no grid')
    if 'OD' not in grid.b_tier_cells:
        return SplitDiffusionResult(success=True, detail='OD not in cell-grid')

    pair = {dev_a_inst, dev_b_inst}
    affected_cells = []  # (cell, paired_inst) — paired_inst is the one removed
    for cell in grid.b_tier_cells_of('OD'):
        if cell.owner_device_id not in pair:
            continue
        if cell.owner_device_id == dev_a_inst and dev_b_inst in cell.shared_with:
            affected_cells.append((cell, dev_b_inst))
        elif cell.owner_device_id == dev_b_inst and dev_a_inst in cell.shared_with:
            affected_cells.append((cell, dev_a_inst))

    cells_unshared = 0
    for cell, paired_inst in affected_cells:
        if cell.remove_sharer(paired_inst):
            cells_unshared += 1

    cuts_added: List[CutMacroResult] = []
    merged_cells: List = []
    merged_unions: List = []
    if cut_at_track_a is not None and engine is not None and affected_cells:
        cut_targets = _explicit_cut_cells(
            affected_cells, cut_at_track_a, cut_layer,
        )
        for layer, ta, tb in cut_targets:
            cut_res = add_cut(engine, grid, layer, ta, tb)
            cuts_added.append(cut_res)
            if cut_res.commit_delta is not None:
                merged_cells.extend(cut_res.commit_delta.cells)
                merged_unions.extend(cut_res.commit_delta.unions)

    commit_delta = None
    if cuts_added:
        commit_delta = CommitDelta(cells=merged_cells, unions=merged_unions)

    return SplitDiffusionResult(
        success=True,
        cells_unshared=cells_unshared,
        cuts_added=cuts_added,
        commit_delta=commit_delta,
        detail=f'unshared {cells_unshared} cells, added {len(cuts_added)} cuts',
    )


def _explicit_cut_cells(affected_cells: list,
                          cut_at_track_a: int,
                          cut_layer: str) -> List[Tuple[str, int, int]]:
    """Stamp a cut at every track_b row in the affected region whose
    track_a matches ``cut_at_track_a``.

    This is the single-track gate-cut pattern: one CPO line at the
    boundary POLY track, spanning every FIN row inside the shared
    region. Returns ``[(layer, track_a, track_b), ...]`` suitable
    for ``add_cut``.
    """
    if not affected_cells:
        return []
    track_bs = sorted({cell.track_b for cell, _ in affected_cells})
    return [(cut_layer, cut_at_track_a, tb) for tb in track_bs]
