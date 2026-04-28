"""
Writeback decoder: consumes EditOp stream + new device parameters,
produces a modified layout data dict that downstream writers (GDS / SKILL /
JSON) can serialize.

Per ``docs/architecture_roadmap.md`` (M1) this consolidates writeback
geometry into a single class. After M2 the EditOp surface widened: the
``device_resize`` L3 macro emits L1 records for FIN, OD, LI (post-shrink
+ post-via-coverage extent), and POLY (partial-bbox endpoint shifts).
M5 lifts NWELL / BOUNDARY out of the decoder's transitional Phase 2
into ``core/drc_derivator.py``, which emits the same modify_shape ops
the macro does — the decoder is now a pure L1 consumer.

Phases:

  1. **EditOp consumer** — apply explicit shape edits emitted by the
     macro and the M5 derivator: FIN remove, OD / LI / POLY / NWELL /
     BOUNDARY modify.
  2. **Metadata update** — params + device records.

The decoder is the sole place writeback geometry lives;
``pipeline/run_mvp.py`` only invokes ``WritebackDecoder.apply()``.
"""

import copy
from typing import List

from core.diff import EditOp
from core.grid import MultiLayerGrid


class WritebackDecoder:

    def __init__(self, grid: MultiLayerGrid, config):
        self.grid = grid
        self.config = config

    def apply(self,
              orig_data: dict,
              edit_ops: List[EditOp],
              new_nmos_nfin: int,
              new_pmos_nfin: int) -> dict:
        result = copy.deepcopy(orig_data)
        params = result['params']

        nmos_fin_y_old = params['nmos_fin_y']
        pmos_fin_y_old = params['pmos_fin_y']
        nmos_fin_y_new = nmos_fin_y_old[:new_nmos_nfin]
        pmos_fin_y_new = pmos_fin_y_old[:new_pmos_nfin]

        # Phase 1: apply explicit EditOps. FIN / OD / LI / POLY come
        # from the L3 ``device_resize`` macro; NWELL / BOUNDARY come
        # from the M5 ``DRCDerivator`` (which the pipeline runs after
        # the macro and prepends / appends to the same edit_ops list).
        self._apply_fin_removes(result, edit_ops)
        self._apply_od_modifies(result, edit_ops)
        self._apply_li_modifies(result, edit_ops)
        self._apply_poly_modifies(result, edit_ops)
        self._apply_nwell_modifies(result, edit_ops)
        self._apply_boundary_modifies(result, edit_ops)

        # Phase 2: update params + device metadata.
        self._update_metadata(result, new_nmos_nfin, new_pmos_nfin,
                              nmos_fin_y_new, pmos_fin_y_new)

        return result

    # --- Phase 1 ---

    def _apply_fin_removes(self, result: dict, edit_ops: List[EditOp]) -> None:
        # Match by center-Y because the solver and the layout generator
        # disagree on FIN_WIDTH//2 vs FIN_WIDTH/2; center-Y is invariant.
        removed_centers = set()
        for op in edit_ops:
            if op.op_type != 'remove_shape' or op.layer != 'FIN':
                continue
            if op.old_bbox is None:
                continue
            _, y1, _, y2 = op.old_bbox
            removed_centers.add(round((y1 + y2) / 2))
        if not removed_centers:
            return
        kept = []
        for s in result['shapes'].get('FIN', []):
            cy = round((s['y1'] + s['y2']) / 2)
            if cy in removed_centers:
                continue
            kept.append(s)
        result['shapes']['FIN'] = kept

    def _apply_od_modifies(self, result: dict, edit_ops: List[EditOp]) -> None:
        for op in edit_ops:
            if op.layer != 'OD':
                continue
            if op.op_type not in ('modify_shape', 'resize_device'):
                continue
            if op.old_bbox is None or op.new_bbox is None:
                continue
            ox1, oy1, ox2, oy2 = op.old_bbox
            nx1, ny1, nx2, ny2 = op.new_bbox
            for s in result['shapes'].get('OD', []):
                if (s['x1'], s['y1'], s['x2'], s['y2']) != (ox1, oy1, ox2, oy2):
                    continue
                s['x1'], s['y1'], s['x2'], s['y2'] = (
                    int(nx1), int(ny1), int(nx2), int(ny2),
                )
                break

    def _apply_li_modifies(self, result: dict, edit_ops: List[EditOp]) -> None:
        """Apply LI modify_shape ops emitted by the L3 macro (M2).

        The macro embeds the *final* bbox (post-shrink, post-via-coverage)
        so the decoder is a passive applier. Old code's
        ``_shrink_li_sd_bars`` + ``_extend_li_for_vias`` derivation is
        deleted.
        """
        for op in edit_ops:
            if op.layer != 'LI':
                continue
            if op.op_type not in ('modify_shape', 'resize_device'):
                continue
            if op.old_bbox is None or op.new_bbox is None:
                continue
            ox1, oy1, ox2, oy2 = op.old_bbox
            nx1, ny1, nx2, ny2 = op.new_bbox
            for s in result['shapes'].get('LI', []):
                if (s['x1'], s['y1'], s['x2'], s['y2']) != (ox1, oy1, ox2, oy2):
                    continue
                s['x1'], s['y1'], s['x2'], s['y2'] = (
                    int(nx1), int(ny1), int(nx2), int(ny2),
                )
                break

    def _apply_poly_modifies(self, result: dict, edit_ops: List[EditOp]) -> None:
        """Apply POLY modify_shape ops (M2).

        POLY ops are emitted with **partial bboxes**: ``None`` in slots
        the macro doesn't change. The convention is one endpoint per op
        (NMOS macro shifts y1; PMOS macro shifts y2). For each op, we
        find every POLY shape whose matching coord equals ``old`` and
        update it to ``new`` — the partial-edit pattern keeps the
        side-channel narrow until POLY enters the shape_pool in M3.
        Old ``_derive_poly_span`` derivation is deleted.
        """
        for op in edit_ops:
            if op.layer != 'POLY':
                continue
            if op.op_type not in ('modify_shape', 'resize_device'):
                continue
            if op.old_bbox is None or op.new_bbox is None:
                continue
            ox1, oy1, ox2, oy2 = op.old_bbox
            nx1, ny1, nx2, ny2 = op.new_bbox
            for s in result['shapes'].get('POLY', []):
                if oy1 is not None and ny1 is not None and s['y1'] == oy1:
                    s['y1'] = int(ny1)
                if oy2 is not None and ny2 is not None and s['y2'] == oy2:
                    s['y2'] = int(ny2)
                if ox1 is not None and nx1 is not None and s['x1'] == ox1:
                    s['x1'] = int(nx1)
                if ox2 is not None and nx2 is not None and s['x2'] == ox2:
                    s['x2'] = int(nx2)

    def _apply_nwell_modifies(self, result: dict, edit_ops: List[EditOp]) -> None:
        """Apply NWELL modify_shape ops (M5 — emitted by ``DRCDerivator``).

        Same passive-applier pattern as ``_apply_od_modifies``: match
        by exact ``old_bbox`` and replace. The M5 derivator runs after
        the L3 macro commits, so ``old_bbox`` is the *pre-derive* NWELL
        record from ``model.shape_pool`` (which mirrors the input
        layout JSON).
        """
        for op in edit_ops:
            if op.layer != 'NWELL':
                continue
            if op.op_type != 'modify_shape':
                continue
            if op.old_bbox is None or op.new_bbox is None:
                continue
            ox1, oy1, ox2, oy2 = op.old_bbox
            nx1, ny1, nx2, ny2 = op.new_bbox
            for s in result['shapes'].get('NWELL', []):
                if (s['x1'], s['y1'], s['x2'], s['y2']) != (ox1, oy1, ox2, oy2):
                    continue
                s['x1'], s['y1'], s['x2'], s['y2'] = (
                    int(nx1), int(ny1), int(nx2), int(ny2),
                )
                break

    def _apply_boundary_modifies(self, result: dict, edit_ops: List[EditOp]) -> None:
        """Apply BOUNDARY modify_shape ops (M5 — emitted by ``DRCDerivator``).

        Same shape as ``_apply_nwell_modifies``; tied to a different
        layer string. BOUNDARY is the cell-outline shape, not a real
        process layer in production, but it's geometrically derived
        from the same fin-position rule and so flows through the
        derivator's L1 stream alongside NWELL.
        """
        for op in edit_ops:
            if op.layer != 'BOUNDARY':
                continue
            if op.op_type != 'modify_shape':
                continue
            if op.old_bbox is None or op.new_bbox is None:
                continue
            ox1, oy1, ox2, oy2 = op.old_bbox
            nx1, ny1, nx2, ny2 = op.new_bbox
            for s in result['shapes'].get('BOUNDARY', []):
                if (s['x1'], s['y1'], s['x2'], s['y2']) != (ox1, oy1, ox2, oy2):
                    continue
                s['x1'], s['y1'], s['x2'], s['y2'] = (
                    int(nx1), int(ny1), int(nx2), int(ny2),
                )
                break

    # --- Phase 2: metadata ---

    def _update_metadata(self, result,
                         new_nmos_nfin, new_pmos_nfin,
                         nmos_fin_y_new, pmos_fin_y_new):
        params = result['params']
        params['nmos_nfin'] = new_nmos_nfin
        params['pmos_nfin'] = new_pmos_nfin
        params['nmos_fin_y'] = nmos_fin_y_new
        params['pmos_fin_y'] = pmos_fin_y_new
        # Cell height tracks the BOUNDARY's y2 (same derivation rule
        # as the M5 ``_derive_boundary`` helper). Reads from the same
        # config knob so a PDK swap cascades through both surfaces.
        params['cell_height'] = int(
            pmos_fin_y_new[-1] + self.config.BOUNDARY_MARGIN_BEYOND_FIN
        )
        for dev in result.get('devices', []):
            t = dev.get('type')
            if t == 'nmos':
                dev['nfin'] = new_nmos_nfin
                dev['fin_y_positions'] = nmos_fin_y_new
            elif t == 'pmos':
                dev['nfin'] = new_pmos_nfin
                dev['fin_y_positions'] = pmos_fin_y_new
