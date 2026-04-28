"""
Layer-2 atomic operations.

Per ``docs/architecture_roadmap.md`` § C, L2 primitives only submit
cell-level proposals to the CSP engine. They do **not** produce L1
``EditOp`` records, do **not** mutate ``LayoutModel``, and do **not**
decide feasibility. The L3 macro brackets a sequence of L2 calls with
``engine.checkpoint`` / ``engine.commit_with_delta`` (or
``engine.restore`` on failure); the decoder synthesizes L1 from the
commit delta + macro-level intent.

M2 shipped the LI/M1 subset (``release_segment_cells``,
``assign_segment_cells``, ``modify_segment``).

M4d adds the B-tier and FIN/POLY primitives that were previously inline
inside the ``device_resize`` macro:

  * ``add_cut_cell`` / ``remove_cut_cell`` — CPO/M0_CUT/FIN_CUT cells
    that pin engine state to ``OccupantType.CUT`` and stamp the
    matching ``CellOccupancy``. ``add_cut_cell`` is the seam through
    which L3 macros enforce §B's "no CUT between adjacent cells" rule
    on the union-find.
  * ``mark_shared_diffusion`` — given two device instance names, walks
    every OD ``CellOccupancy`` whose owner is one and ``shared_with``
    contains the other (or vice versa); opportunistically calls
    ``engine.union`` on adjacent OD-cell engine pairs (no-op when OD
    is not yet in the engine — that's M5/M6's lift).
  * ``extend_od`` — re-projects an OD shape's cell coverage when its
    bbox changes during a resize. Re-stamps cell owners from
    device-bbox containment.
  * ``add_fin_strip`` / ``remove_fin_strip`` — mutate ``model.shape_pool``
    for FIN strips. Returns ``FinStripResult`` carrying enough geometry
    for the L3 macro to build a ``remove_shape`` / ``add_shape`` L1 record.
  * ``extend_poly`` — partial-bbox POLY endpoint update. Returns
    ``PolyExtendResult`` with the (target, old_value, new_value) triple
    so the macro can emit the ``modify_shape`` L1 record with sentinel
    ``None`` placeholders for the unaffected coordinates.

The M4d FIN/POLY primitives intentionally do not touch the engine:
those layers are not yet CSP-modelled (M5+ adds them). The L2 surface
is consistent so future engine integration can wire them in without
churning the L3 macro.
"""

from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Tuple

from core.csp_engine import ConstraintEngine
from core.data_model import (
    CellOccupancy, CellState, Device, LayoutModel, OccupantType, ShapeRecord,
)


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


@dataclass
class FinStripResult:
    """Result of ``add_fin_strip`` / ``remove_fin_strip`` (M4d).

    ``bbox`` is the strip's pixel-accurate ``(x1, y1, x2, y2)`` so the
    macro can emit a matching L1 ``EditOp.old_bbox`` / ``new_bbox``.
    ``desc`` is a stable identifier the layout-generator-side records
    (e.g. ``MN0_fin_track_4``); preserved for byte-golden parity with
    the legacy ``_emit_fin_removes`` helper.
    ``shape_record`` is the actual ``ShapeRecord`` removed from / added
    to ``model.shape_pool``, or ``None`` if the pool didn't carry a
    matching record (the legacy MVP fixture sometimes lacks per-track
    FIN entries — fall back to a synthesised bbox).
    """
    success: bool
    fin_track_idx: int
    bbox: Tuple[int, int, int, int]
    desc: str
    shape_record: Optional[ShapeRecord] = None


@dataclass
class PolyExtendResult:
    """Result of ``extend_poly`` (M4d).

    ``target`` is ``'y1'`` or ``'y2'`` — which endpoint moved.
    ``old_value`` / ``new_value`` are the partial-bbox coordinate values
    the macro emits with sentinel ``None`` for unaffected dimensions
    (preserves the M2-era partial-edit pattern in the decoder).
    """
    success: bool
    target: str
    old_value: int
    new_value: int


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


# =============================================================
# M4d B-tier + FIN/POLY primitives
# =============================================================

def add_cut_cell(engine: ConstraintEngine,
                  grid,
                  layer: str,
                  track_a: int,
                  track_b: int,
                  shape_record: Optional[ShapeRecord] = None) -> AtomicResult:
    """Stamp a CUT at ``(layer, track_a, track_b)`` in both engine and grid.

    Calls ``engine.mark_cut`` if the engine has a cell at this position
    (today: only when the layer was added via ``engine.add_layer``). On
    success, also records a ``CellOccupancy`` of type ``OccupantType.CUT``
    in the B-tier cell-grid storage so M4d's ``mark_shared_diffusion``
    and the M6 split-on-cut macros can find it later.

    Returns ``failed_pos`` on engine refusal (cell already carries an
    annotated assignment per the conservative-default rule §D);
    callers should ``restore`` the most recent checkpoint.
    """
    pos = (layer, track_a, track_b)
    if engine.get_cell(pos) is not None:
        if not engine.mark_cut(pos):
            return AtomicResult(
                success=False,
                failed_pos=pos,
                detail=f'mark_cut refused at {pos} (cell carries an annotated assignment)',
            )

    # Grid-side stamp (B-tier cell-grid storage). Skip if the layer
    # isn't B-tier or hasn't been registered yet — the engine call
    # alone is sufficient for some test fixtures that pre-date the
    # parser tier-dispatch.
    if grid is not None and grid.is_b_tier_layer(layer) and layer in grid.b_tier_axes:
        occ = CellOccupancy(
            layer=layer, track_a=track_a, track_b=track_b,
            occ_type=OccupantType.CUT, shape_record=shape_record,
        )
        grid.set_b_tier_cell(layer, track_a, track_b, occ)

    return AtomicResult(success=True)


def remove_cut_cell(grid, layer: str,
                     track_a: int, track_b: int) -> AtomicResult:
    """Remove a CUT cell from the B-tier cell-grid storage.

    The CSP engine side of removing a CUT (un-pinning ``cell.fixed`` and
    re-opening the domain) is intentionally NOT done here — undoing a
    CUT through the engine requires invalidating any prior unions that
    routed around it, which is M6's split-diffusion responsibility. M4d
    only ships the grid-side removal so macros can model the CDL-side
    intent (a future ``remove_cut`` macro).

    Returns ``success=True`` whether or not the cell was present;
    idempotent. ``detail`` reports which case fired.
    """
    if grid is None or layer not in grid.b_tier_cells:
        return AtomicResult(success=True, detail='layer not in cell-grid')
    layer_cells = grid.b_tier_cells.get(layer, {})
    if (track_a, track_b) not in layer_cells:
        return AtomicResult(success=True, detail='cell not present')
    del layer_cells[(track_a, track_b)]
    return AtomicResult(success=True, detail='removed')


def mark_shared_diffusion(grid,
                            engine: Optional[ConstraintEngine],
                            dev_a_inst: str,
                            dev_b_inst: str) -> AtomicResult:
    """Mark every OD cell that's shared between ``dev_a`` and ``dev_b``.

    Two pieces of work:
      1. Walks ``grid.b_tier_cells_of('OD')``; on every cell whose owner
         is one of the devices and whose ``shared_with`` already lists
         the other, no-op (the M4c parser stamping path already set it).
         For cells where the owner is one device and the other isn't yet
         on ``shared_with``, append. This handles the "L3 macro flips
         two previously-isolated devices into a shared-diffusion pair"
         case.
      2. If ``engine`` is non-None and the engine has cells on ``OD``,
         call ``engine.union`` on every adjacent OD-cell pair that lies
         inside the shared-diffusion region. The §B "no CUT between
         adjacent cells" rule fires through the union precondition.
         When OD is not yet engine-modelled (today's MVP), the engine
         loop no-ops — the grid-side stamp still lands so M5/M6 can
         observe the shared-diffusion intent.

    Returns ``detail`` summarising "{N stamped, M unioned}".
    """
    if grid is None:
        return AtomicResult(success=True, detail='no grid')

    layer = 'OD'
    if layer not in grid.b_tier_cells:
        return AtomicResult(success=True, detail='OD not in cell-grid')

    pair = {dev_a_inst, dev_b_inst}
    candidate_cells: List[CellOccupancy] = []
    stamped = 0
    for cell in grid.b_tier_cells_of(layer):
        if cell.owner_device_id is None:
            continue
        # Cell is owned by one of the pair; the other should be on shared_with.
        if cell.owner_device_id == dev_a_inst:
            if cell.add_sharer(dev_b_inst):
                stamped += 1
            candidate_cells.append(cell)
        elif cell.owner_device_id == dev_b_inst:
            if cell.add_sharer(dev_a_inst):
                stamped += 1
            candidate_cells.append(cell)

    unioned = 0
    if engine is not None:
        for i, ca in enumerate(candidate_cells):
            for cb in candidate_cells[i + 1:]:
                # Only adjacent (Manhattan-1) pairs can union — the
                # engine.union precondition enforces this anyway, but
                # short-circuit here for clarity.
                if abs(ca.track_a - cb.track_a) + abs(ca.track_b - cb.track_b) != 1:
                    continue
                if engine.get_cell(ca.pos) is None or engine.get_cell(cb.pos) is None:
                    continue
                if engine.union(ca.pos, cb.pos):
                    unioned += 1

    return AtomicResult(
        success=True,
        detail=f'stamped {stamped} cells, unioned {unioned} pairs',
    )


def extend_od(grid,
                devices: List[Device],
                shape_record: ShapeRecord,
                new_bbox: Tuple[int, int, int, int]) -> AtomicResult:
    """Re-project an OD shape's cell coverage when its bbox changes.

    Used by ``device_resize`` when an OD shape's Y extent shrinks (or
    extends). Walks the OLD cell set and the NEW cell set:
      * cells in OLD ∖ NEW are removed from the cell-grid;
      * cells in NEW ∖ OLD are stamped with owner from device-bbox
        containment;
      * cells in OLD ∩ NEW are left untouched (their ownership is
        unaffected).

    Updates ``shape_record.bbox_nm`` to the new bbox so subsequent
    queries reflect the post-resize geometry. Idempotent: calling
    twice with the same ``new_bbox`` is a no-op.
    """
    if grid is None or shape_record.layer != 'OD':
        return AtomicResult(success=True, detail='not an OD shape')
    if 'OD' not in grid.b_tier_axes:
        return AtomicResult(success=True, detail='OD axes not registered')

    old_bbox = shape_record.bbox_nm
    if old_bbox == new_bbox:
        return AtomicResult(success=True, detail='no-op (same bbox)')

    old_cells = set(grid.bbox_to_b_tier_cells('OD', *old_bbox))
    new_cells = set(grid.bbox_to_b_tier_cells('OD', *new_bbox))

    layer_cells = grid.b_tier_cells.setdefault('OD', {})
    removed = 0
    added = 0
    for ta, tb in old_cells - new_cells:
        if (ta, tb) in layer_cells:
            del layer_cells[(ta, tb)]
            removed += 1

    # New cells: pick owner via device-bbox containment of the cell's
    # physical center. For OD with axes (POLY, FIN), the cell center
    # is (poly.track_to_physical(ta), fin.track_to_physical(tb)).
    axis_a, axis_b = grid.get_b_tier_axes('OD')
    lg_a = grid.layers[axis_a]
    lg_b = grid.layers[axis_b]
    for ta, tb in new_cells - old_cells:
        cx = lg_a.track_to_physical(ta) if lg_a.orientation == 'V' else lg_b.track_to_physical(tb)
        cy = lg_b.track_to_physical(tb) if lg_b.orientation == 'H' else lg_a.track_to_physical(ta)
        owner: Optional[str] = None
        for dev in devices:
            if not dev.bbox_nm:
                continue
            if (dev.bbox_nm['x1'] <= cx <= dev.bbox_nm['x2'] and
                dev.bbox_nm['y1'] <= cy <= dev.bbox_nm['y2']):
                owner = dev.inst_name
                break
        occ = CellOccupancy(
            layer='OD', track_a=ta, track_b=tb,
            occ_type=OccupantType.DEVICE_DIFF,
            net_id=shape_record.net_id,
            owner_device_id=owner,
            shape_record=shape_record,
        )
        grid.set_b_tier_cell('OD', ta, tb, occ)
        added += 1

    # Update the geometric truth on the ShapeRecord itself.
    shape_record.bbox_nm = new_bbox

    return AtomicResult(
        success=True,
        detail=f'removed {removed} cells, added {added} cells',
    )


def add_fin_strip(model: LayoutModel,
                    fin_grid,
                    fin_track_idx: int,
                    x1: int,
                    x2: int,
                    fin_width: int,
                    owner_device_id: Optional[str] = None) -> FinStripResult:
    """Add a FIN strip at ``fin_track_idx`` spanning ``[x1, x2]``.

    Appends a ``ShapeRecord`` to ``model.shape_pool``. Returns
    ``FinStripResult`` with the strip's pixel-accurate bbox + a
    stable ``desc`` so the macro can emit a matching L1
    ``add_shape`` EditOp. ``owner_device_id`` is recorded as the
    record's ``device_id``.
    """
    fy = fin_grid.track_to_physical(fin_track_idx)
    hw = fin_width // 2
    bbox = (x1, fy - hw, x2, fy + hw)
    desc_owner = owner_device_id or ''
    desc = f'{desc_owner}_fin_track_{fin_track_idx}'.lstrip('_')
    sr = ShapeRecord(
        layer='FIN', bbox_nm=bbox, desc=desc,
        device_id=owner_device_id, provenance='atomic_ops.add_fin_strip',
    )
    model.shape_pool.append(sr)
    return FinStripResult(
        success=True, fin_track_idx=fin_track_idx,
        bbox=bbox, desc=desc, shape_record=sr,
    )


def remove_fin_strip(model: LayoutModel,
                      fin_grid,
                      fin_track_idx: int,
                      x1: int,
                      x2: int,
                      fin_width: int,
                      owner_device_id: Optional[str] = None) -> FinStripResult:
    """Remove the FIN strip at ``fin_track_idx``.

    Walks ``model.shape_pool`` for a FIN record whose center Y matches
    ``fin_grid.track_to_physical(fin_track_idx)`` (within 0.5 nm) and
    drops it. Returns ``FinStripResult`` with the removed record's
    bbox + desc so the macro can emit a matching ``remove_shape`` L1.

    If no matching record is found in the pool (e.g. a legacy fixture
    that didn't enumerate FIN strips), returns ``shape_record=None``
    and a synthesised bbox / desc so the macro can still emit a valid
    L1 EditOp — this is the byte-golden path against the M4d-pre
    `_emit_fin_removes` helper.
    """
    fy = fin_grid.track_to_physical(fin_track_idx)
    hw = fin_width // 2
    desc_owner = owner_device_id or ''
    desc = f'{desc_owner}_fin_track_{fin_track_idx}'.lstrip('_')

    for sr in list(model.shape_pool):
        if sr.layer != 'FIN':
            continue
        center_y = (sr.bbox_nm[1] + sr.bbox_nm[3]) / 2.0
        if abs(center_y - fy) <= 0.5:
            model.shape_pool.remove(sr)
            return FinStripResult(
                success=True, fin_track_idx=fin_track_idx,
                bbox=sr.bbox_nm, desc=desc, shape_record=sr,
            )

    # No pool record — return synthesised bbox so caller can still
    # emit an L1 EditOp.
    bbox = (x1, fy - hw, x2, fy + hw)
    return FinStripResult(
        success=True, fin_track_idx=fin_track_idx,
        bbox=bbox, desc=desc, shape_record=None,
    )


def extend_poly(target: str,
                  old_value: int,
                  new_value: int) -> PolyExtendResult:
    """Build a partial-bbox POLY endpoint update record.

    M4d does not yet mutate ``model.shape_pool`` for POLY — the existing
    decoder's Phase 1 ``_apply_poly_modifies`` path keys off the L1
    EditOp's partial-bbox sentinel pattern, so the macro emits the
    record and the decoder applies it across all matching POLY shapes.
    This helper exists to make the L2 surface complete: the macro
    builds its EditOp from this primitive's return value rather than
    constructing the partial bbox inline.

    ``target`` must be ``'y1'`` or ``'y2'`` — which Y endpoint moved.
    """
    if target not in ('y1', 'y2'):
        raise ValueError(f"extend_poly: target must be 'y1' or 'y2', got {target!r}")
    return PolyExtendResult(
        success=True, target=target,
        old_value=old_value, new_value=new_value,
    )


__all__ = [
    'AtomicResult',
    'FinStripResult',
    'PolyExtendResult',
    'release_segment_cells',
    'assign_segment_cells',
    'modify_segment',
    'add_cut_cell',
    'remove_cut_cell',
    'mark_shared_diffusion',
    'extend_od',
    'add_fin_strip',
    'remove_fin_strip',
    'extend_poly',
]
