"""
Layout solver: loads existing layout into CSP, performs fin resize.

Pipeline:
  1. Parse layout → LayoutModel + Grid
  2. Create CSP engine, register DRC rules
  3. Load existing segments into CSP (assign cells)
  4. Execute resize: release old cells, assign new cells, check feasibility
  5. Generate diff (list of changes)

M2 (see ``docs/architecture_roadmap.md``): ``resize_device`` is the L3
``device_resize`` macro. It:
  * brackets work in ``engine.checkpoint`` / ``engine.commit_with_delta``;
  * routes LI cell-level changes through L2 primitives in
    ``core/atomic_ops.py`` (which only call ``propose_assign`` /
    ``propose_release``);
  * emits L1 ``EditOp`` records with the **final** bbox (post-shrink and
    post-via-coverage extension), so the decoder's Phase 2 derivation
    helpers ``_shrink_li_sd_bars``, ``_extend_li_for_vias``, and
    ``_derive_poly_span`` are deleted in this milestone.

Layers not yet modelled in CSP (FIN / OD / POLY / NWELL / BOUNDARY) flow
through the "non-CSP side-channel" described in the roadmap: the macro
emits L1 records directly. M3 / M4 / M5 will pull them into CSP / cell
occupancy / the C1 derivator.
"""

import sys
import os
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.data_model import (
    LayoutModel, Device, Net, TrackSegment, ViaInstance,
    CellState, OccupantType, EMPTY, BLOCKAGE,
)
from core.grid import MultiLayerGrid
from core.csp_engine import ConstraintEngine, GridCell
from core.drc_constraints import create_mvp_drc_rules
from core.diff import EditOp
from core import atomic_ops


@dataclass
class ResizeResult:
    """Result of a resize operation."""
    success: bool
    message: str
    edit_ops: List[EditOp] = field(default_factory=list)
    old_model: Optional[LayoutModel] = None
    new_segments: Dict[str, List[TrackSegment]] = field(default_factory=dict)
    new_vias: Dict[str, List[ViaInstance]] = field(default_factory=dict)


class LayoutSolver:
    """
    Orchestrates CSP-based layout modification.
    """
    
    def __init__(self, model: LayoutModel, grid: MultiLayerGrid, config=None):
        self.model = model
        self.grid = grid
        self.config = config
        self.engine: Optional[ConstraintEngine] = None

        # Collect all net IDs
        self.net_ids: Set[str] = set(model.nets.keys())
    
    def setup_engine(self, layers_to_include: List[str] = None,
                      b_tier_layers: List[str] = None):
        """
        Create CSP engine and load existing layout.

        Args:
            layers_to_include: A-tier layers to model in CSP (default: LI, M1)
            b_tier_layers: M4e B-tier layers to also model in CSP
                (default: ``['OD', 'VIA0']`` if those layers exist on the
                grid's ``b_tier_axes``). Each B-tier layer's bounds are
                derived from ``grid.b_tier_cells`` so the engine spans
                exactly the cells the parser stamped.
        """
        if layers_to_include is None:
            layers_to_include = ['LI', 'M1']

        self.engine = ConstraintEngine()

        # Determine grid bounds from existing segments (A-tier path).
        for layer in layers_to_include:
            lg = self.grid.get_layer(layer)
            ortho = self.grid.get_ortho_layer(layer)

            # Find track and ortho ranges from existing segments
            tracks = set()
            orthos = set()

            for net in self.model.nets.values():
                for seg in net.segments:
                    if seg.layer == layer:
                        tracks.add(seg.track_idx)
                        for o in seg.span:
                            orthos.add(o)
                for via in net.vias:
                    if via.lower_layer == layer:
                        tracks.add(via.lower_track_idx)
                    if via.upper_layer == layer:
                        tracks.add(via.upper_track_idx)

            if not tracks or not orthos:
                continue

            # Add margin for possible rerouting
            margin = 2
            t_min = min(tracks) - margin
            t_max = max(tracks) + margin + 1
            o_min = min(orthos) - margin
            o_max = max(orthos) + margin + 1

            self.engine.add_layer(
                layer,
                n_tracks=t_max - t_min,
                n_ortho=o_max - o_min,
                track_range=(t_min, t_max),
                ortho_range=(o_min, o_max),
            )

        # M4e: also add B-tier layers to the engine if the parser
        # populated their cell-grid. The bounds come from the actual
        # populated cell positions plus a one-cell margin.
        if b_tier_layers is None:
            b_tier_layers = [layer for layer in ('OD', 'VIA0')
                              if layer in self.grid.b_tier_cells
                              and self.grid.b_tier_cells[layer]]

        layer_occ_types: Dict[str, set] = {}
        for layer in b_tier_layers:
            cells = self.grid.b_tier_cells.get(layer, {})
            if not cells:
                continue
            tas = [a for (a, _b) in cells.keys()]
            tbs = [b for (_a, b) in cells.keys()]
            margin = 1
            t_min, t_max = min(tas) - margin, max(tas) + margin + 1
            o_min, o_max = min(tbs) - margin, max(tbs) + margin + 1
            self.engine.add_layer(
                layer,
                n_tracks=t_max - t_min,
                n_ortho=o_max - o_min,
                track_range=(t_min, t_max),
                ortho_range=(o_min, o_max),
            )
            # Set the layer's allowed occupant types — DEVICE_DIFF for
            # OD, VIA for VIA0, CUT for cut layers. The B-tier domain
            # also keeps EMPTY so cells outside the populated region can
            # remain unassigned.
            if layer == 'OD':
                layer_occ_types[layer] = {OccupantType.EMPTY,
                                            OccupantType.DEVICE_DIFF}
            elif layer == 'VIA0':
                layer_occ_types[layer] = {OccupantType.EMPTY,
                                            OccupantType.VIA}
            else:
                # Cut layers (CPO / M0_CUT / FIN_CUT) — fixtures don't
                # use them yet, but the dispatch lands cleanly when
                # they show up.
                layer_occ_types[layer] = {OccupantType.EMPTY,
                                            OccupantType.CUT}

        # Register DRC rules
        for rule in create_mvp_drc_rules():
            if rule.layer if hasattr(rule, 'layer') else True:
                self.engine.register_drc(rule)

        # Initialize domains. M4e per-layer override controls B-tier
        # cells' allowed occupants without disturbing the A-tier WIRE
        # domain.
        self.engine.initialize_domains(
            self.net_ids,
            layer_occ_types=layer_occ_types,
        )
        
        print(f"CSP engine created:")
        for layer, dims in self.engine.layer_dims.items():
            print(f"  {layer}: tracks=[{dims[0]},{dims[1]}) ortho=[{dims[2]},{dims[3]})")
        print(f"  Total cells: {len(self.engine.cells)}")
    
    def project_unannotated_blockages(self) -> Dict[str, int]:
        """Project unannotated ``shape_pool`` entries into CSP as BLOCKAGE (M3).

        For every ``ShapeRecord`` in ``model.shape_pool`` that LVS did not
        annotate (``net_id is None``) and lives on a CSP-modelled layer,
        the shape's bbox is mapped to grid cells via the ``MultiLayerGrid``
        and each cell is marked ``BLOCKAGE`` on the engine.

        Per docs/architecture_roadmap.md §A and §D, this turns "GDS-known
        but LVS-unknown" geometry — filler, ESD stubs, dummy gates,
        hand-edits — into hard obstacles for the L2 ``propose_assign``
        path, instead of leaving the engine ignorant of them.

        The MVP fixture has zero unannotated LI / M1 shapes (the only two
        layers wired into CSP today), so this is a no-op for the
        byte-golden buffer-resize case. Tests inject a synthetic LI stub
        into shape_pool to exercise the projection end-to-end.

        Returns ``{layer: n_cells_marked, ..., 'skipped_conflict': n}``.
        ``skipped_conflict`` counts cells that were already non-EMPTY and
        therefore not overwritten — the conservative-default red flag.
        """
        result: Dict[str, int] = {}
        skipped = 0
        if self.engine is None:
            return result

        csp_layers = set(self.engine.layer_dims.keys())

        for sr in self.model.shape_pool:
            if sr.is_annotated:
                continue
            if sr.layer not in csp_layers:
                continue
            # M4e: ``physical_to_segment_coords`` is an A-tier projection
            # that uses ``MultiLayerGrid.layers`` (1D per-layer track
            # grid). B-tier layers (OD, VIA0, cuts) — newly added to the
            # engine in M4e via ``setup_engine`` — don't have a
            # ``LayerGrid`` entry; their cells are stamped directly via
            # ``load_b_tier_cells_into_engine``. Skip them here so the
            # A-tier-only blockage projection path stays sound.
            if sr.layer not in self.grid.layers:
                continue
            x1, y1, x2, y2 = sr.bbox_nm
            coords = self.grid.physical_to_segment_coords(
                sr.layer, x1, y1, x2, y2,
            )
            track_idx = coords['track_idx']
            for o in range(coords['start_anchor'], coords['end_anchor'] + 1):
                pos = (sr.layer, track_idx, o)
                cell = self.engine.get_cell(pos)
                if cell is None:
                    continue
                if self.engine.mark_blockage(pos):
                    result[sr.layer] = result.get(sr.layer, 0) + 1
                else:
                    skipped += 1

        if skipped:
            result['skipped_conflict'] = skipped
        return result

    def load_existing_layout(self) -> bool:
        """
        Load existing layout segments into CSP.
        
        Assigns each segment's grid cells in the CSP engine.
        Returns False if any existing shape violates DRC (shouldn't happen).
        """
        print("\nLoading existing layout into CSP...")
        
        assignment_count = 0
        
        for net_name, net in self.model.nets.items():
            for seg in net.segments:
                if seg.layer not in self.engine.layer_dims:
                    continue
                
                # Each segment occupies cells along its span
                for ortho_idx in seg.span:
                    pos = (seg.layer, seg.track_idx, ortho_idx)
                    cell = self.engine.get_cell(pos)
                    if cell is None:
                        continue
                    
                    state = CellState(OccupantType.WIRE, net_id=net_name)
                    success = self.engine.assign(pos, state)
                    
                    if not success:
                        print(f"  ERROR: Failed to assign {pos} = {state}")
                        print(f"    Cell domain: {cell.domain}")
                        return False
                    
                    assignment_count += 1
            
            # Load via positions
            for via in net.vias:
                # Via occupies cells on both layers
                for layer, track_idx in [
                    (via.lower_layer, via.lower_track_idx),
                    (via.upper_layer, via.upper_track_idx),
                ]:
                    if layer not in self.engine.layer_dims:
                        continue
                    
                    # Via on lower layer: position = (lower_layer, lower_track, m1_track)
                    # Via on upper layer: position = (upper_layer, upper_track, li_track)
                    if layer == via.lower_layer:
                        # LI layer: via at (LI, li_track, m1_track)
                        pos = (layer, via.lower_track_idx, via.upper_track_idx)
                    else:
                        # M1 layer: via at (M1, m1_track, li_track)
                        pos = (layer, via.upper_track_idx, via.lower_track_idx)
                    
                    cell = self.engine.get_cell(pos)
                    if cell is None:
                        continue
                    
                    # Don't re-assign if already assigned by segment
                    if cell.is_assigned and cell.assignment.net_id == net_name:
                        continue
                    
                    state = CellState(OccupantType.WIRE, net_id=net_name)
                    success = self.engine.assign(pos, state)
                    if not success and not cell.is_assigned:
                        print(f"  WARNING: Via assignment failed at {pos}")
        
        stats = self.engine.domain_stats()
        print(f"  Loaded {assignment_count} cell assignments")
        print(f"  CSP stats: {stats}")

        return True

    def load_b_tier_cells_into_engine(self) -> int:
        """Seed engine state from ``grid.b_tier_cells`` (M4e).

        For every populated ``CellOccupancy`` on a B-tier layer the
        engine modelled (OD / VIA0 / cut layers, when present), assigns
        the corresponding engine cell to its grid-side occupant via
        ``engine.assign``. Cells outside the engine's bounds are
        skipped silently — the engine bounds are already the populated
        region plus a 1-cell margin, so the only cells skipped are
        unannotated B-tier shapes that didn't make it into the parser
        projection.

        Returns the number of cells loaded. Called by the pipeline
        after ``load_existing_layout``; harmless to call when the
        engine doesn't model any B-tier layer (no-op).
        """
        loaded = 0
        for layer in ('OD', 'VIA0'):
            if layer not in self.engine.layer_dims:
                continue
            for cell in self.grid.b_tier_cells_of(layer):
                pos = cell.pos
                if self.engine.get_cell(pos) is None:
                    continue
                state = CellState(cell.occ_type, net_id=cell.net_id)
                if self.engine.get_cell(pos).is_assigned:
                    continue
                if self.engine.assign(pos, state):
                    loaded += 1
        return loaded

    def resize_device(self, device_name: str, new_nfin: int) -> ResizeResult:
        """L3 ``device_resize`` macro (M2).

        Reduces ``device_name``'s fin count to ``new_nfin``. Within one
        ``checkpoint`` / ``commit_with_delta`` transaction:

        * **LI** S/D contact bars are reshaped through L2 primitives
          (``atomic_ops.modify_segment``), which call ``propose_release``
          on the cells trailing past the new endpoint and ``propose_assign``
          on the cells that must remain (anchoring via-coverage). On any
          infeasible proposal, the engine is restored to the pre-call
          checkpoint and the macro returns ``infeasible``.
        * **FIN / OD / POLY** are not yet modelled in CSP (M3 / M4 / M5);
          the macro emits L1 ``EditOp`` records for them directly via the
          non-CSP side-channel.
        * The emitted L1 LI ``EditOp`` carries the **final** bbox
          (post-shrink + post-via-coverage extension) so the decoder no
          longer needs ``_shrink_li_sd_bars`` / ``_extend_li_for_vias``.
          Likewise, POLY ``EditOp`` records make ``_derive_poly_span``
          obsolete.
        """
        device = self.model.get_device(device_name)
        if device is None:
            return ResizeResult(False, f"Device {device_name} not found")

        if new_nfin >= device.nfin:
            return ResizeResult(False,
                f"new_nfin ({new_nfin}) must be less than current ({device.nfin})")

        delta_fins = device.nfin - new_nfin

        print(f"\n{'='*60}")
        print(f"Resizing {device_name}: {device.nfin}fin → {new_nfin}fin (Δ={-delta_fins})")
        print(f"{'='*60}")

        # --- Determine which fins are removed (top-down strategy) ---
        fin_grid = self.grid.get_layer('FIN')
        m1_grid = self.grid.get_layer('M1')
        old_fin_tracks = list(device.fin_track_indices)
        removed_fin_tracks = old_fin_tracks[-delta_fins:]
        remaining_fin_tracks = old_fin_tracks[:-delta_fins]

        print(f"  Old fin tracks: {old_fin_tracks}")
        print(f"  Removing: {removed_fin_tracks}")
        print(f"  Remaining: {remaining_fin_tracks}")

        old_top_fin_y = fin_grid.track_to_physical(old_fin_tracks[-1])
        new_top_fin_y = fin_grid.track_to_physical(remaining_fin_tracks[-1])
        old_bot_fin_y = fin_grid.track_to_physical(old_fin_tracks[0])
        new_bot_fin_y = fin_grid.track_to_physical(remaining_fin_tracks[0])

        # --- Open transaction; any infeasibility unwinds via restore() ---
        cp = self.engine.checkpoint() if self.engine else None

        # Transactional body. If a propose_assign returns False, we unwind
        # immediately. The macro never produces partial state.
        edit_ops: List[EditOp] = []
        new_segments: Dict[str, List[TrackSegment]] = {}

        try:
            # 1. FIN removes (non-CSP side-channel).
            self._emit_fin_removes(edit_ops, device_name,
                                    fin_grid, removed_fin_tracks)

            # 2. OD modify — routed through the M4d ``extend_od`` L2
            #    atomic so the B-tier cell-grid stays in sync with the
            #    new bbox; the L1 record is still emitted by the macro.
            self._emit_od_modify(edit_ops, device_name, device,
                                  old_bot_fin_y, old_top_fin_y, new_top_fin_y)

            # 3. LI S/D contact bars: route cell-level changes through L2,
            #    then emit the L1 EditOp with the final bbox.
            li_failure = self._reshape_li_sd_bars(
                edit_ops, new_segments, device,
                old_fin_tracks, removed_fin_tracks,
                new_top_fin_y, m1_grid,
            )
            if li_failure is not None:
                if cp is not None:
                    self.engine.restore(cp)
                return ResizeResult(False, li_failure)

            # 4. POLY span (non-CSP side-channel). Only emit when this
            #    device's owned poly endpoint actually moved.
            self._emit_poly_modify_if_endpoint_changed(
                edit_ops, device,
                old_bot_fin_y, new_bot_fin_y,
                old_top_fin_y, new_top_fin_y,
            )

            # 5. Commit transaction. M6 flipped to ``commit_with_full_delta``
            #    so the union-find delta (net-equivalence merges since
            #    the checkpoint) lands alongside the cell-level delta.
            #    The cell delta still drives the decoder's existing
            #    Phase 1 path (currently informational — the macro
            #    emits L1 directly); the union delta is the seam M6's
            #    ``share_diffusion`` / ``split_diffusion`` macros and
            #    the M5 derivator's incremental-recompute follow-up
            #    will subscribe to.
            if cp is not None:
                full_delta = self.engine.commit_with_full_delta(cp)
                print(f"  CSP commit: {len(full_delta.cells)} cell-level changes, "
                      f"{len(full_delta.unions)} union events")

        except Exception:
            if cp is not None:
                self.engine.restore(cp)
            raise

        print(f"\nResize plan: {len(edit_ops)} operations")
        for op in edit_ops:
            print(f"  {op}")

        return ResizeResult(
            success=True,
            message=f"Resize {device_name} {device.nfin}→{new_nfin} fin: "
                    f"{len(edit_ops)} edit operations",
            edit_ops=edit_ops,
            new_segments=new_segments,
        )

    # -------------------------------------------------------------
    # L3 macro helpers (M2). Each helper either emits L1 records
    # directly (non-CSP side-channel) or routes through L2 primitives
    # in core.atomic_ops (CSP-modelled layers).
    # -------------------------------------------------------------

    def _emit_fin_removes(self, edit_ops, device_name, fin_grid,
                           removed_fin_tracks):
        """Emit ``remove_shape`` FIN EditOps via the M4d L2 atomic.

        Each track is processed by ``atomic_ops.remove_fin_strip`` which
        mutates ``model.shape_pool`` (drops the matching ShapeRecord)
        and returns the removed shape's bbox + desc; the macro then
        builds the L1 record from that result. Byte-golden parity with
        the legacy inline emission is preserved by ``FinStripResult``
        carrying the same ``(0, fy - hw, cell_width, fy + hw)`` bbox
        the legacy helper computed.
        """
        for ft in removed_fin_tracks:
            res = atomic_ops.remove_fin_strip(
                self.model, fin_grid, ft,
                x1=0, x2=self.model.cell_width_nm,
                fin_width=self.config.FIN_WIDTH,
                owner_device_id=device_name,
            )
            edit_ops.append(EditOp(
                'remove_shape', 'FIN',
                old_bbox=res.bbox,
                desc=res.desc,
            ))

    def _emit_od_modify(self, edit_ops, device_name, device,
                         bot_fin_y, old_top_fin_y, new_top_fin_y):
        """Emit ``modify_shape`` OD EditOp via the M4d L2 atomic.

        Computes the old / new full-cell-width OD bbox the same way the
        legacy helper did. ``atomic_ops.extend_od`` re-projects the
        cell-grid coverage and updates the matching ShapeRecord's
        ``bbox_nm`` so post-resize queries reflect the new geometry.
        The L1 record is byte-identical to the legacy emission.
        """
        od_ext = self.config.OD_EXTENSION_BEYOND_FIN
        old_bbox = (0, bot_fin_y - od_ext,
                     self.model.cell_width_nm, old_top_fin_y + od_ext)
        new_bbox = (0, bot_fin_y - od_ext,
                     self.model.cell_width_nm, new_top_fin_y + od_ext)

        # Find the OD ShapeRecord this device owns; pass it to extend_od
        # so the cell-grid stays in sync. Skip if shape_pool wasn't
        # populated (legacy callers).
        target_sr = None
        for sr in self.model.shape_pool:
            if sr.layer != 'OD':
                continue
            if sr.device_id == device.inst_name or sr.bbox_nm == old_bbox:
                target_sr = sr
                break
        if target_sr is not None:
            atomic_ops.extend_od(
                self.grid, self.model.devices, target_sr, new_bbox,
            )

        edit_ops.append(EditOp(
            'modify_shape', 'OD',
            old_bbox=old_bbox,
            new_bbox=new_bbox,
            desc=f'{device_name}_od_shrink',
        ))

    def _reshape_li_sd_bars(self, edit_ops, new_segments, device,
                             old_fin_tracks, removed_fin_tracks,
                             new_top_fin_y, m1_grid) -> Optional[str]:
        """Reshape this device's LI S/D bars through CSP + emit L1 records.

        Returns ``None`` on success, or an error string on infeasible
        propose_assign (caller restores the checkpoint).
        """
        # S/D nets owned by this device.
        sd_nets = {device.pins.get(p, '') for p in ('S', 'D')}
        sd_nets.discard('')
        print(f"  S/D nets affected: {sd_nets}")

        li_ext_y = 5  # Layout-generator-side LI overshoot beyond top fin.
        enc_y = self.config.VIA0_ENC_BY_LI_Y

        for net_name in sd_nets:
            net = self.model.nets.get(net_name)
            if not net:
                continue

            for seg in list(net.segments):
                if seg.layer != 'LI':
                    continue
                # M4c: restrict to LI segments physically owned by *this*
                # device. The M3 ``ShapeRecord`` backlink, refined by the
                # M4c per-shape geometric ``device_id`` stamp in
                # ``io_adapters/parser.py::apply_lvs_overlay``, is the
                # source of truth. Pre-M4c (and the legacy ``desc``
                # substring filter ``device_y_marker not in seg.desc``)
                # this check fell back to ``li_nmos_*`` / ``li_pmos_*``
                # naming convention. The new path keys off geometry
                # (device-bbox containment of the shape's center) so
                # nets bridged across NMOS and PMOS (e.g. OUT) get the
                # correct per-segment device.
                if seg.shape_record is not None:
                    if seg.shape_record.device_id != device.inst_name:
                        continue
                else:
                    # Legacy fallback for callers that built TrackSegments
                    # directly without going through ``build_layout_model``
                    # (older tests, ad-hoc fixtures). The desc-substring
                    # check stays available for those paths until the
                    # last caller migrates.
                    if device.dev_type not in seg.desc:
                        continue

                if seg.bbox_nm is None:
                    # Parser didn't stamp a bbox (legacy data); fall back
                    # to the round-trip reconstruction. Off-by-1nm on
                    # odd-width layers is acceptable for non-byte-golden
                    # consumers.
                    old_bbox = self.grid.segment_to_physical(
                        seg.layer, seg.track_idx,
                        seg.start_anchor, seg.end_anchor,
                        self.config.LI_WIDTH,
                        seg.start_offset_nm, seg.end_offset_nm,
                    )
                else:
                    old_bbox = seg.bbox_nm
                old_x1, old_y1, old_x2, old_y2 = old_bbox
                old_y_max = max(old_y1, old_y2)

                # Compute the new top: shrink to (new fin top + extension),
                # then extend back if a via on this LI demands more cover.
                new_y_max = new_top_fin_y + li_ext_y

                via_y_positions = []
                for via in net.vias:
                    if via.lower_layer == 'LI' and via.lower_track_idx == seg.track_idx:
                        via_y_positions.append(
                            m1_grid.track_to_physical(via.upper_track_idx)
                        )
                if via_y_positions:
                    new_y_max = max(new_y_max, max(via_y_positions) + enc_y)

                if new_y_max == old_y_max:
                    continue  # No-op LI (e.g. via keeps it long).

                new_end_anchor = m1_grid.physical_to_track(new_y_max)
                new_end_offset = int(
                    new_y_max - m1_grid.track_to_physical(new_end_anchor)
                )

                # L2 cell-level proposal: release CSP cells trailing past
                # the new endpoint, then re-anchor cells that must remain
                # (i.e. those still inside the new range). For shrinks the
                # second step is a no-op; for extensions it's where a
                # via-collision would surface as ``failed_pos``.
                if self.engine is not None:
                    old_range = list(seg.span)
                    new_range = list(range(seg.start_anchor, new_end_anchor + 1))
                    res = atomic_ops.modify_segment(
                        self.engine, 'LI', seg.track_idx,
                        old_range, new_range, net_name,
                    )
                    if not res.success:
                        return (
                            f"LI {seg.desc}: cell-level conflict at "
                            f"{res.failed_pos} ({res.detail})"
                        )

                # New bbox preserves the layout's pixel-accurate x range;
                # only the changed endpoint moves. Mirrors how the GDS
                # generator first produced the shape.
                new_bbox = (old_x1, old_y1, old_x2, int(new_y_max))

                edit_ops.append(EditOp(
                    'modify_shape', 'LI',
                    old_bbox=old_bbox,
                    new_bbox=new_bbox,
                    net_id=net_name,
                    desc=f'{seg.desc}_resize',
                ))

                new_segments.setdefault(net_name, []).append(TrackSegment(
                    layer=seg.layer,
                    track_idx=seg.track_idx,
                    start_anchor=seg.start_anchor,
                    end_anchor=new_end_anchor,
                    net_id=seg.net_id,
                    start_offset_nm=seg.start_offset_nm,
                    end_offset_nm=new_end_offset,
                    desc=seg.desc + '_resized',
                    bbox_nm=new_bbox,
                ))

                print(f"    LI {seg.desc}: ortho [{seg.start_anchor}→{seg.end_anchor}] "
                      f"→ [{seg.start_anchor}→{new_end_anchor}]")
        return None

    def _emit_poly_modify_if_endpoint_changed(self, edit_ops, device,
                                                old_bot_fin_y, new_bot_fin_y,
                                                old_top_fin_y, new_top_fin_y):
        """Emit POLY modify_shape records when this device owns the moving endpoint.

        POLY span = [nmos_bot_fin_y - od_ext - poly_ext,
                     pmos_top_fin_y + od_ext + poly_ext]. NMOS owns y1
        (depends on its bottom fin), PMOS owns y2 (depends on its top
        fin). For the MVP top-down resize strategy, only the top fin
        moves — so PMOS resizes emit a y2 update and NMOS resizes emit
        nothing. Generalises cleanly to bottom-up removal in M3+.
        """
        od_ext = self.config.OD_EXTENSION_BEYOND_FIN
        poly_ext = self.config.POLY_EXTENSION_BEYOND_OD

        # Determine which endpoint this device owns and whether it moved.
        if device.dev_type == 'nmos':
            if new_bot_fin_y == old_bot_fin_y:
                return
            old_y1 = old_bot_fin_y - od_ext - poly_ext
            new_y1 = new_bot_fin_y - od_ext - poly_ext
            target = 'y1'
        else:  # pmos
            if new_top_fin_y == old_top_fin_y:
                return
            old_y2 = old_top_fin_y + od_ext + poly_ext
            new_y2 = new_top_fin_y + od_ext + poly_ext
            target = 'y2'

        # M4d: route partial-bbox endpoint updates through
        # ``atomic_ops.extend_poly`` so the L2 surface owns the
        # primitive. The macro then emits the L1 ``modify_shape``
        # EditOp with sentinel ``None`` for the unaffected coordinates
        # — the decoder's Phase 1 ``_apply_poly_modifies`` keys off
        # that pattern unchanged.
        if target == 'y1':
            res = atomic_ops.extend_poly('y1', old_y1, new_y1)
            edit_ops.append(EditOp(
                'modify_shape', 'POLY',
                old_bbox=(None, res.old_value, None, None),
                new_bbox=(None, res.new_value, None, None),
                desc=f'{device.inst_name}_poly_y1_shift',
            ))
        else:
            res = atomic_ops.extend_poly('y2', old_y2, new_y2)
            edit_ops.append(EditOp(
                'modify_shape', 'POLY',
                old_bbox=(None, None, None, res.old_value),
                new_bbox=(None, None, None, res.new_value),
                desc=f'{device.inst_name}_poly_y2_shift',
            ))
    
    def apply_resize_to_model(self, device_name: str, new_nfin: int,
                               result: ResizeResult) -> LayoutModel:
        """
        Apply resize result to create a new LayoutModel.
        (Does not modify the original model.)
        """
        import copy
        new_model = copy.deepcopy(self.model)
        
        # Update device
        dev = new_model.get_device(device_name)
        if dev:
            fin_grid = self.grid.get_layer('FIN')
            dev.nfin = new_nfin
            dev.fin_track_indices = dev.fin_track_indices[:new_nfin]
        
        # Update segments
        for net_name, new_segs in result.new_segments.items():
            net = new_model.nets.get(net_name)
            if not net:
                continue
            # Replace segments that were modified
            for new_seg in new_segs:
                for i, old_seg in enumerate(net.segments):
                    if (old_seg.layer == new_seg.layer and 
                        old_seg.track_idx == new_seg.track_idx and
                        old_seg.net_id == new_seg.net_id and
                        old_seg.desc.replace('_resized', '') in new_seg.desc):
                        net.segments[i] = new_seg
                        break
        
        return new_model


# =============================================================
# Entry point: run MVP resize
# =============================================================
def run_mvp_resize():
    """Run the complete MVP flow: parse → load CSP → resize → output diff."""
    
    from io_adapters.parser import build_layout_model
    
    fixture_dir = os.path.join(os.path.dirname(__file__), '..', 'dummy', 'fixtures')
    
    # --- Stage 2: Parse ---
    print("Stage 2: Parsing layout data...")
    model, grid = build_layout_model(
        device_query_path=os.path.join(fixture_dir, 'calibre_device_query.json'),
        net_query_path=os.path.join(fixture_dir, 'calibre_net_query.json'),
        bbox_path=os.path.join(fixture_dir, 'bbox_by_layer.json'),
        layout_json_path=os.path.join(fixture_dir, 'buffer_original.json'),
    )
    print(model.summary())
    
    # --- Stage 3+4: Setup CSP and load layout ---
    print("\nStage 3-4: Setting up CSP engine...")
    solver = LayoutSolver(model, grid)
    solver.setup_engine(layers_to_include=['LI', 'M1'])
    load_ok = solver.load_existing_layout()
    
    if not load_ok:
        print("ERROR: Failed to load existing layout into CSP")
        return None
    
    # Print CSP state
    print("\nCSP grid state after loading:")
    solver.engine.print_layer('LI')
    solver.engine.print_layer('M1')
    
    # --- Stage 5: Resize ---
    print("\n" + "="*60)
    print("Stage 5: Executing resize operations")
    print("="*60)
    
    results = []
    
    # Resize NMOS: 5 → 4 fin
    r1 = solver.resize_device('MN0', 4)
    results.append(r1)
    
    # Resize PMOS: 7 → 6 fin
    r2 = solver.resize_device('MP0', 6)
    results.append(r2)
    
    # --- Summary ---
    print("\n" + "="*60)
    print("RESIZE SUMMARY")
    print("="*60)
    all_ok = all(r.success for r in results)
    print(f"Overall: {'SUCCESS' if all_ok else 'FAILED'}")
    for r in results:
        print(f"  {r.message}")
    
    total_edits = sum(len(r.edit_ops) for r in results)
    print(f"Total edit operations: {total_edits}")
    
    return results


if __name__ == '__main__':
    run_mvp_resize()
