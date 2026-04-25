"""
Writeback decoder: consumes EditOp stream + new device parameters,
produces a modified layout data dict that downstream writers (GDS / SKILL /
JSON) can serialize.

Per docs/architecture_roadmap.md (M1), this consolidates writeback geometry
into a single class. Two paths run in sequence:

  1. EditOp consumer — apply explicit shape edits emitted by the solver
     (FIN removes, OD resize). Identifies target shapes by old_bbox.
  2. Derived synthesis — recompute geometry the solver does not yet emit
     (POLY span, LI shrink + via-coverage extension, NWELL/BOUNDARY
     extents). M5 will move C1 derivation (NWELL/BOUNDARY/etc.) to
     core/drc_derivator.py; M2 will let CSP-emitted EditOps cover more
     A/B-tier geometry, shrinking the derivation surface.

The decoder is the sole place writeback geometry lives; pipeline/run_mvp.py
only invokes WritebackDecoder.apply().
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

        # Phase 1: apply explicit EditOps from the solver.
        self._apply_fin_removes(result, edit_ops)
        self._apply_od_modifies(result, edit_ops)

        # Phase 2: derive layer geometry not yet emitted as EditOps.
        self._shrink_li_sd_bars(result, nmos_fin_y_new, pmos_fin_y_new)
        self._derive_poly_span(result, nmos_fin_y_new, pmos_fin_y_new)
        self._extend_li_for_vias(result, params)
        self._derive_nwell(result, pmos_fin_y_new)
        self._derive_boundary(result, pmos_fin_y_new)

        # Phase 3: update params + device metadata.
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

    # --- Phase 2 ---

    def _shrink_li_sd_bars(self, result, nmos_fin_y_new, pmos_fin_y_new):
        li_ext_y = 5
        for s in result['shapes'].get('LI', []):
            desc = s.get('desc', '')
            if 'nmos_source' in desc or 'nmos_drain' in desc:
                s['y2'] = int(nmos_fin_y_new[-1] + li_ext_y)
            elif 'pmos_source' in desc or 'pmos_drain' in desc:
                s['y2'] = int(pmos_fin_y_new[-1] + li_ext_y)

    def _derive_poly_span(self, result, nmos_fin_y_new, pmos_fin_y_new):
        od_ext = self.config.OD_EXTENSION_BEYOND_FIN
        poly_ext = self.config.POLY_EXTENSION_BEYOND_OD
        nmos_od_bot = nmos_fin_y_new[0] - od_ext
        pmos_od_top = pmos_fin_y_new[-1] + od_ext
        poly_y_bot = nmos_od_bot - poly_ext
        poly_y_top = pmos_od_top + poly_ext
        for s in result['shapes'].get('POLY', []):
            s['y1'] = int(poly_y_bot)
            s['y2'] = int(poly_y_top)

    def _extend_li_for_vias(self, result, params):
        m1_tracks = params.get('m1_tracks', {})
        enc = self.config.VIA0_ENC_BY_LI_Y
        for s in result['shapes'].get('LI', []):
            desc = s.get('desc', '')
            via_y = None
            if 'nmos_source' in desc and 'VSS' in m1_tracks:
                via_y = m1_tracks['VSS']
            elif 'pmos_source' in desc and 'VDD' in m1_tracks:
                via_y = m1_tracks['VDD']
            elif 'drain' in desc and 'OUT' in m1_tracks:
                via_y = m1_tracks['OUT']
            elif 'gate' in desc and 'IN' in m1_tracks:
                via_y = m1_tracks['IN']
            if via_y is None:
                continue
            needed_bot = via_y - enc
            needed_top = via_y + enc
            if s['y1'] > needed_bot:
                s['y1'] = int(needed_bot)
            if s['y2'] < needed_top:
                s['y2'] = int(needed_top)

    def _derive_nwell(self, result, pmos_fin_y_new):
        nwell_margin = 30
        for s in result['shapes'].get('NWELL', []):
            s['y2'] = int(pmos_fin_y_new[-1] + nwell_margin)

    def _derive_boundary(self, result, pmos_fin_y_new):
        new_cell_height = pmos_fin_y_new[-1] + 40
        for s in result['shapes'].get('BOUNDARY', []):
            s['y2'] = int(new_cell_height)

    # --- Phase 3 ---

    def _update_metadata(self, result,
                         new_nmos_nfin, new_pmos_nfin,
                         nmos_fin_y_new, pmos_fin_y_new):
        params = result['params']
        params['nmos_nfin'] = new_nmos_nfin
        params['pmos_nfin'] = new_pmos_nfin
        params['nmos_fin_y'] = nmos_fin_y_new
        params['pmos_fin_y'] = pmos_fin_y_new
        params['cell_height'] = int(pmos_fin_y_new[-1] + 40)
        for dev in result.get('devices', []):
            t = dev.get('type')
            if t == 'nmos':
                dev['nfin'] = new_nmos_nfin
                dev['fin_y_positions'] = nmos_fin_y_new
            elif t == 'pmos':
                dev['nfin'] = new_pmos_nfin
                dev['fin_y_positions'] = pmos_fin_y_new
