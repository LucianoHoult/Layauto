"""
C1 derivator (M5).

Per ``docs/architecture_roadmap.md`` §B / §C, C1 layers (NWELL, VT, PP,
NP, BOUNDARY, DNW) are *derived markings* — pure-function geometry
synthesised from A/B-tier state + ``Device`` metadata + a rule table
(today the per-layer margins live in ``tech/process_config.yaml`` under
``derivation:``). They never enter CSP and are never edited by L3
macros directly: edit a fin / OD / poly through the L2 atomics and the
derivator regenerates the C1 markings to match.

Pre-M5 the derivation hid inside ``core/decoder.py`` as a transitional
Phase 2 (``_derive_nwell`` + ``_derive_boundary``). M5 lifts the same
geometry into this module, but expressed as L1 ``EditOp`` records that
flow through the same Phase 1 path the L3 macros use for FIN / OD /
LI / POLY. Three architectural wins:

1. The derivator and the macro speak the same L1 vocabulary, so the
   decoder no longer needs a special-case Phase 2.
2. The derivator stamps ``ShapeRecord.is_derived = True`` on the
   shapes it owns — the M3 seam (``core/data_model.py:124``) is now
   load-bearing. Future M6 macros that try to directly edit a derived
   shape can be rejected at the decoder seam.
3. The C1 → L1 surface is the natural plug-in point for cell-delta-
   driven affected-neighborhood recomputation when fixtures grow large
   enough that full recompute starts costing real time. M5 ships full
   recompute (the MVP fixture is one cell — recompute is trivial); the
   subscription model lands in a follow-up.

The MVP fixture only carries NWELL + BOUNDARY shapes. VT / PP / NP /
DNW exist as tier markers in ``tech/layer_map.py`` but no fixture
geometry exercises them yet; the derivator's seams support them
without code change once shapes show up.

Subscription contract (lightweight for M5):
  * Pipeline calls ``DRCDerivator.derive_c1`` *after* the L3 ``device_resize``
    macro commits, with the post-commit ``nmos_fin_y_new`` /
    ``pmos_fin_y_new`` lists.
  * The returned ``List[EditOp]`` is appended to the macro's edit-op
    stream; the decoder applies them in Phase 1 just like macro-emitted
    ops.
  * Every emitted op corresponds to a ``ShapeRecord`` in
    ``model.shape_pool``; the derivator stamps ``is_derived=True`` and
    ``provenance`` on that record so future direct-edit attempts can
    be caught.
"""

from typing import List, Optional

from core.data_model import LayoutModel, ShapeRecord
from core.diff import EditOp
from core.grid import MultiLayerGrid


class DRCDerivator:
    """Derive C1 markings from A/B-tier state + Device metadata.

    Stateless across calls — the ``LayoutModel`` carries any state the
    derivator needs (``shape_pool`` for the geometric truth; the
    ``Device`` list for nfin / fin positions). Each ``derive_c1`` call
    walks the pool and emits one ``EditOp`` per shape whose derived
    bbox actually changed; idempotent on a steady-state fixture.
    """

    def __init__(self, model: LayoutModel,
                  grid: MultiLayerGrid,
                  config) -> None:
        self.model = model
        self.grid = grid
        self.config = config

    # =========================================================
    # Public API
    # =========================================================

    def derive_c1(self,
                    nmos_fin_y_new: List[int],
                    pmos_fin_y_new: List[int]) -> List[EditOp]:
        """Recompute every C1 marking and return the L1 EditOps.

        Args:
            nmos_fin_y_new: Y positions of the post-resize NMOS fins
                (low → high). Currently unused — the MVP's NWELL +
                BOUNDARY both key off the topmost PMOS fin only — but
                kept on the signature so VT / PP additions don't have
                to reshape callers.
            pmos_fin_y_new: Y positions of the post-resize PMOS fins;
                ``pmos_fin_y_new[-1]`` is the topmost.

        Returns:
            List of ``EditOp``s the decoder's Phase 1 should apply.
            Empty when no derived shape's bbox actually changes
            (idempotent re-call on a steady-state fixture).

        Side effects:
            For every shape the derivator emits an op for, sets
            ``ShapeRecord.is_derived = True`` and writes a
            ``provenance`` string identifying the rule. The decoder
            (M6) can then reject macro-emitted edits to the same
            shape.
        """
        ops: List[EditOp] = []
        ops.extend(self._derive_nwell(pmos_fin_y_new))
        ops.extend(self._derive_boundary(pmos_fin_y_new))
        # VT / PP / NP / DNW: no fixture geometry yet. The seams below
        # would mirror the NWELL / BOUNDARY shape; activate them when
        # ``model.shape_pool`` starts carrying records on those layers.
        return ops

    # =========================================================
    # Per-layer derivation
    # =========================================================

    def _derive_nwell(self, pmos_fin_y_new: List[int]) -> List[EditOp]:
        """NWELL covers every PMOS fin with the configured margin.

        ``y2 = pmos_fin_y_new[-1] + config.NWELL_MARGIN_BEYOND_FIN``.
        The lower edge (``y1``) and the X span are inherited from
        the existing ShapeRecord — derived shifts are Y-only for the
        single-cell MVP. Multi-cell layouts will need a richer rule.
        """
        if not pmos_fin_y_new:
            return []
        margin = self.config.NWELL_MARGIN_BEYOND_FIN
        new_y2 = int(pmos_fin_y_new[-1] + margin)
        return self._emit_y2_shift_ops(
            layer='NWELL', new_y2=new_y2,
            provenance='drc_derivator._derive_nwell',
        )

    def _derive_boundary(self, pmos_fin_y_new: List[int]) -> List[EditOp]:
        """BOUNDARY (cell outline) extends past the topmost PMOS fin.

        ``y2 = pmos_fin_y_new[-1] + config.BOUNDARY_MARGIN_BEYOND_FIN``.
        Same shape as NWELL; the constant differs.
        """
        if not pmos_fin_y_new:
            return []
        margin = self.config.BOUNDARY_MARGIN_BEYOND_FIN
        new_y2 = int(pmos_fin_y_new[-1] + margin)
        return self._emit_y2_shift_ops(
            layer='BOUNDARY', new_y2=new_y2,
            provenance='drc_derivator._derive_boundary',
        )

    # =========================================================
    # Internal: emit a Y2-only modify_shape per shape on a layer
    # =========================================================

    def _emit_y2_shift_ops(self, layer: str,
                             new_y2: int,
                             provenance: str) -> List[EditOp]:
        """Walk ``shape_pool`` for ``layer``; for each shape whose
        ``bbox_nm`` y2 differs from ``new_y2``, emit a
        ``modify_shape`` op (full bbox, not partial — the decoder's
        Phase 1 NWELL/BOUNDARY apply paths match by exact old bbox).

        Stamps ``is_derived=True`` + ``provenance`` on every shape
        the derivator owns *regardless of whether the y2 changed* —
        the M3 seam should reflect "this shape is owned by the
        derivator", not "the derivator just changed it". An
        idempotent re-call on a steady-state fixture leaves the seam
        set without emitting any op.
        """
        ops: List[EditOp] = []
        for sr in self.model.shape_pool:
            if sr.layer != layer:
                continue
            self._mark_derived(sr, provenance)
            old_bbox = sr.bbox_nm
            if old_bbox[3] == new_y2:
                continue
            new_bbox = (old_bbox[0], old_bbox[1], old_bbox[2], new_y2)
            ops.append(EditOp(
                op_type='modify_shape',
                layer=layer,
                old_bbox=old_bbox,
                new_bbox=new_bbox,
                desc=f'derived_{layer.lower()}_y2_shift',
            ))
            # Update geometric truth so subsequent derivator calls
            # see the new bbox (idempotency on re-invocation).
            sr.bbox_nm = new_bbox
        return ops

    @staticmethod
    def _mark_derived(sr: ShapeRecord, provenance: str) -> None:
        """Stamp the M3 ``is_derived`` seam + provenance backlink."""
        sr.is_derived = True
        sr.provenance = provenance


__all__ = ['DRCDerivator']
