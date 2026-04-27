"""
Constraint Satisfaction Problem (CSP) engine for layout DRC enforcement.

Core mechanism:
  - Each grid cell has a 'domain': the set of states it can legally take
  - When a cell is assigned a state, constraints propagate to neighbors,
    shrinking their domains
  - If any domain becomes empty → contradiction → infeasible path
  - Solutions found by the engine are DRC-correct by construction

Grid cells are indexed as (track_idx, ortho_track_idx, layer_name).

Transactional API (M2): ``propose_assign`` / ``propose_release`` are the
public interface for L2 atomic ops. They append trail entries that capture
both prior domain *and* prior assignment, so ``restore`` reverts both.
``commit_with_delta`` summarises the cell-level changes since a checkpoint
and truncates the trail (commit is non-restorable). See
``docs/architecture_roadmap.md`` § M2.

Net-equivalence (M4b): the engine now keeps an internal union-find over
cell positions to track which routed cells are electrically connected.
``union(pos_a, pos_b)`` merges two adjacent same-net cells into one
equivalence class; ``net_of(pos)`` and ``connected_to(pos)`` query the
class. The union precondition "no CUT between adjacent cells" is
enforced by refusing to union when either endpoint's assignment is a
CUT — combined with adjacent-only union, this means a chain of unions
along an axis cannot cross a CUT cell. ``commit_with_full_delta``
returns both the cell delta and the union delta atomically; the
M2-era ``commit_with_delta`` is preserved for backward compatibility.
``restore`` undoes unions performed since the checkpoint along with
the cell-level changes, so transactional rollback covers both axes.
See ``docs/architecture_roadmap.md`` § B and § M4.
"""

from collections import deque
from dataclasses import dataclass, field
from typing import Dict, Set, List, Optional, Tuple, FrozenSet
from copy import deepcopy

from core.data_model import CellState, OccupantType, EMPTY, BLOCKAGE


# Trail entry: (pos, prev_domain, prev_assignment). Captures enough state to
# fully revert a cell, including its assignment — the M1-era trail saved only
# domain, which left ``unassign`` unable to restore neighbour assignments.
TrailEntry = Tuple[Tuple, FrozenSet[CellState], CellState]


@dataclass
class CommitDelta:
    """Return value of ``ConstraintEngine.commit_with_full_delta`` (M4b).

    ``cells``: same shape as the legacy ``commit_with_delta`` return —
    one ``(pos, prev_assignment, new_assignment)`` tuple per cell whose
    assignment changed since the checkpoint, sorted by ``(layer,
    track, ortho)``.

    ``unions``: chronological list of ``(child_root, parent_root)``
    pairs for every successful ``union`` since the checkpoint. The
    original argument order to ``union`` is not preserved — the engine
    always stores the smaller-tree root as ``child`` for union-by-size.
    Consumers (M4d ``mark_shared_diffusion``, M6 ``share_diffusion`` /
    ``split_diffusion``) treat this as an unordered "these two cells
    became electrically equivalent" record.
    """
    cells: List[Tuple[Tuple, CellState, CellState]] = field(default_factory=list)
    unions: List[Tuple[Tuple, Tuple]] = field(default_factory=list)


@dataclass
class GridCell:
    """
    A single cell in the CSP grid.
    
    assignment: current actual state (EMPTY if unassigned)
    domain: set of states this cell can still legally take
    
    Key invariant: assignment ∈ domain (always)
    """
    pos: Tuple                     # (track_idx, ortho_track_idx, layer_name)
    assignment: CellState = EMPTY
    domain: Set[CellState] = field(default_factory=lambda: {EMPTY})
    fixed: bool = False            # If True, cannot be changed (boundary condition)
    
    @property
    def is_assigned(self) -> bool:
        """Has a non-EMPTY assignment."""
        return self.assignment != EMPTY
    
    @property
    def is_feasible(self) -> bool:
        """Domain is non-empty (at least one legal state exists)."""
        return len(self.domain) > 0
    
    @property
    def domain_size(self) -> int:
        return len(self.domain)
    
    def __repr__(self):
        return f"Cell{self.pos}: {self.assignment} dom={self.domain_size}"


class DRCConstraintTemplate:
    """
    Base class for DRC rules encoded as CSP constraints.
    
    Each DRC rule = (Stencil, Trigger, Forbidden):
      - Stencil: relative offsets defining the rule's spatial scope
      - Trigger: which anchor states activate this rule
      - Forbidden: which neighbor states become illegal when triggered
    
    To add a new DRC rule: subclass this and implement trigger() + forbidden_states().
    The engine doesn't need any modification.
    """
    
    def __init__(self, name: str, stencil: List[Tuple[int, int, str]],
                 anchor_layer: str = None):
        """
        Args:
            name: Rule name (for debugging)
            stencil: List of (layer_name, d_track, d_ortho) offsets.
            anchor_layer: Layer this rule applies to. If set, the rule
                          only fires when the anchor cell is on this layer.
        """
        self.name = name
        self.stencil = stencil
        self.anchor_layer = anchor_layer
    
    def trigger(self, state: CellState) -> bool:
        """Does this state at the anchor cell activate the rule?"""
        raise NotImplementedError
    
    def forbidden_states(self, trigger_state: CellState,
                         all_net_ids: Set[str]) -> Set[CellState]:
        """
        Given the trigger state, return the set of states that become
        forbidden at stencil positions.
        """
        raise NotImplementedError
    
    def __repr__(self):
        return f"DRC({self.name}, stencil_size={len(self.stencil)})"


class ConstraintEngine:
    """
    CSP engine: maintains grid cells with domains, performs constraint propagation.
    
    Usage:
        engine = ConstraintEngine()
        engine.add_layer('LI', n_tracks=3, n_ortho=12)
        engine.register_drc(SameLayerMinSpacing('LI', 1))
        engine.initialize_domains(net_ids={'VSS', 'VDD', 'IN', 'OUT'})
        
        success = engine.assign(('LI', 0, 5), some_state)
        if not success:
            print("Assignment leads to DRC violation!")
    """
    
    def __init__(self):
        self.cells: Dict[Tuple, GridCell] = {}
        self.constraints: List[DRCConstraintTemplate] = []
        self.net_ids: Set[str] = set()

        # Layer dimensions for iteration
        self.layer_dims: Dict[str, Tuple[int, int]] = {}  # layer -> (n_tracks, n_ortho)

        # Trail for incremental backtracking. Each entry is a ``TrailEntry``:
        # (pos, prev_domain, prev_assignment). See module docstring.
        self.trail: List[TrailEntry] = []

        # M4b net-equivalence union-find. ``_uf_parent[pos]`` is the cell
        # parent (self for a root); ``_uf_size[root]`` is the component
        # size. Cells appear lazily — a position is in the union-find
        # only after it has been part of a ``union`` call. Path
        # compression is intentionally NOT used so that ``restore`` can
        # undo unions by simply popping the trail; the size penalty is
        # bounded by the number of unions per checkpoint, which is small
        # for the M4 fan-out.
        self._uf_parent: Dict[Tuple, Tuple] = {}
        self._uf_size: Dict[Tuple, int] = {}

        # Per-checkpoint union trail. Each entry is
        # ``(child_root, prev_parent_of_child_root, parent_root, prev_size_of_parent)``
        # so ``_uf_undo_one`` can fully revert one union step. Truncated
        # by ``commit_with_full_delta`` (commit is non-restorable);
        # popped pair-wise by ``restore``.
        self._uf_trail: List[Tuple[Tuple, Tuple, Tuple, int]] = []

        # Maps each ``checkpoint()`` return value (``len(self.trail)`` at
        # checkpoint time) to the matching ``len(self._uf_trail)`` so
        # ``restore`` and ``commit_with_full_delta`` can bracket union
        # events without expanding the public ``checkpoint`` return type.
        self._uf_checkpoints: Dict[int, int] = {}
    
    def add_layer(self, layer_name: str, n_tracks: int, n_ortho: int,
                  track_range: Tuple[int, int] = None,
                  ortho_range: Tuple[int, int] = None):
        """
        Add a layer to the grid.
        
        Args:
            layer_name: Layer identifier
            n_tracks: Number of tracks (cross-track dimension)
            n_ortho: Number of orthogonal positions (along-track dimension)
            track_range: Optional (start, end) for track indices (default 0-based)
            ortho_range: Optional (start, end) for ortho indices
        """
        t_start = track_range[0] if track_range else 0
        t_end = track_range[1] if track_range else n_tracks
        o_start = ortho_range[0] if ortho_range else 0
        o_end = ortho_range[1] if ortho_range else n_ortho
        
        self.layer_dims[layer_name] = (t_start, t_end, o_start, o_end)
        
        for t in range(t_start, t_end):
            for o in range(o_start, o_end):
                pos = (layer_name, t, o)
                self.cells[pos] = GridCell(pos=pos)
    
    def register_drc(self, constraint: DRCConstraintTemplate):
        """Register a DRC rule. Can be called anytime (before or after initialize)."""
        self.constraints.append(constraint)
    
    def initialize_domains(self, net_ids: Set[str], 
                           occ_types: Set[OccupantType] = None):
        """
        Initialize all cell domains with the full set of possible states.
        
        Must be called after add_layer() and before assign().
        
        Args:
            net_ids: Set of net IDs that can appear in this region
            occ_types: Occupant types to include (default: EMPTY + WIRE)
        """
        self.net_ids = net_ids
        if occ_types is None:
            occ_types = {OccupantType.EMPTY, OccupantType.WIRE}
        
        # Build the full state set
        all_states = {EMPTY}
        for net_id in net_ids:
            for ot in occ_types:
                if ot == OccupantType.EMPTY:
                    continue
                all_states.add(CellState(ot, net_id=net_id))
        
        for cell in self.cells.values():
            if not cell.fixed:
                cell.domain = set(all_states)
                cell.assignment = EMPTY
    
    def get_cell(self, pos: Tuple) -> Optional[GridCell]:
        """Get cell at position, or None if out of bounds."""
        return self.cells.get(pos)
    
    def assign(self, pos: Tuple, state: CellState,
               record_trail: bool = True) -> bool:
        """
        Assign a state to a cell and propagate constraints.

        Returns False if the assignment leads to any domain becoming empty
        (DRC violation detected). In that case, use restore() to undo.

        Args:
            pos: (layer_name, track_idx, ortho_track_idx)
            state: State to assign
            record_trail: If True, record domain + assignment changes for backtracking
        """
        cell = self.cells.get(pos)
        if cell is None:
            return False

        if cell.fixed:
            # Fixed cells can only keep their current assignment
            return cell.assignment == state

        if state not in cell.domain:
            return False  # Already ruled out by constraints

        # Record previous domain AND assignment for trail (M2: trail captures
        # both, so restore can revert assignment, not just domain).
        if record_trail:
            self.trail.append((pos, frozenset(cell.domain), cell.assignment))

        # Collapse domain to single value
        cell.assignment = state
        cell.domain = {state}

        # Propagate constraints
        return self._propagate(pos, record_trail)

    # ---------------------------------------------------------------
    # Transactional API (M2)
    #
    # ``propose_assign`` and ``propose_release`` are the public interface
    # used by L2 atomic ops in ``core/atomic_ops.py``. They are thin wrappers
    # over the underlying ``assign`` / domain-rebuild machinery, but the
    # naming makes the contract explicit: a proposal can fail (DRC
    # violation), and the caller is expected to bracket related proposals
    # with ``checkpoint()`` / ``commit_with_delta()`` (or ``restore()``).
    # ---------------------------------------------------------------

    def propose_assign(self, pos: Tuple, state: CellState) -> bool:
        """Propose a cell assignment within an open transaction.

        Identical to ``assign`` with trail recording. Returns ``False`` if
        the assignment is infeasible; the caller should ``restore`` the
        most recent checkpoint.
        """
        return self.assign(pos, state, record_trail=True)

    def propose_release(self, pos: Tuple) -> bool:
        """Propose releasing a cell back to EMPTY within an open transaction.

        Unlike the legacy ``unassign``, this method records a trail entry
        that captures both the prior domain and the prior assignment, so
        ``restore`` can put the cell back exactly. The cell's domain is
        rebuilt from the engine's allowed-state set so future propagation
        can re-shrink it.
        """
        cell = self.cells.get(pos)
        if cell is None:
            return False
        if cell.fixed:
            return False
        # No-op fast-path: cell is already EMPTY *and* its domain is the
        # full state set. Saves trail churn during repeated calls.
        full_domain = self._initial_domain()
        if cell.assignment == EMPTY and cell.domain == full_domain:
            return True

        # Record prior state for restore.
        self.trail.append((pos, frozenset(cell.domain), cell.assignment))

        cell.assignment = EMPTY
        cell.domain = set(full_domain)
        return True

    def commit_with_delta(self, checkpoint: int) -> List[Tuple[Tuple, CellState, CellState]]:
        """Finalize all proposals made since ``checkpoint`` and return the cell delta.

        Returns a list of ``(pos, prev_assignment, new_assignment)`` tuples,
        one per cell whose *assignment* (not just domain) changed since the
        checkpoint. The trail is truncated past the checkpoint; commit is
        non-restorable.

        Decoder consumes this delta to synthesize L1 ``EditOp``s.
        """
        cell_delta = self._compute_cell_delta(checkpoint)

        # Truncate trail; commit is non-restorable.
        del self.trail[checkpoint:]
        # Drop union-trail entries since the checkpoint and matching
        # checkpoint stash entries — committing without surfacing the
        # union delta is allowed (callers that don't care about
        # net-equivalence stay on this method).
        uf_target = self._uf_checkpoints.pop(checkpoint, 0)
        del self._uf_trail[uf_target:]
        stale = [k for k in self._uf_checkpoints if k > checkpoint]
        for k in stale:
            self._uf_checkpoints.pop(k, None)
        return cell_delta

    def commit_with_full_delta(self, checkpoint: int) -> 'CommitDelta':
        """Finalize and return both the cell delta *and* the net-equivalence delta (M4b).

        ``CommitDelta.cells`` is the same list ``commit_with_delta``
        returns. ``CommitDelta.unions`` is the list of ``(pos_a, pos_b)``
        union events — one per successful ``union`` call since the
        checkpoint, in chronological order. Decoder / L3 macro
        consumers that need to track net-equivalence (M4d's
        ``mark_shared_diffusion``, M6's ``share_diffusion`` /
        ``split_diffusion`` macros) call this variant; M2-era callers
        stay on ``commit_with_delta``.

        Trail truncation semantics match ``commit_with_delta``: both
        the cell trail and the union-find trail are truncated past
        the checkpoint. Commit is non-restorable.
        """
        cell_delta = self._compute_cell_delta(checkpoint)

        uf_target = self._uf_checkpoints.pop(checkpoint, 0)
        # Each entry on ``_uf_trail`` was appended by a successful
        # ``union(child, parent)``. The original argument order is not
        # preserved (we always store the smaller-tree root as
        # ``child``); for the public delta we surface ``(child,
        # parent)`` which is sufficient for "these two cells were
        # merged" — the L3 consumer doesn't depend on argument order.
        union_delta: List[Tuple[Tuple, Tuple]] = [
            (entry[0], entry[2]) for entry in self._uf_trail[uf_target:]
        ]

        # Truncate trails; commit is non-restorable.
        del self.trail[checkpoint:]
        del self._uf_trail[uf_target:]
        stale = [k for k in self._uf_checkpoints if k > checkpoint]
        for k in stale:
            self._uf_checkpoints.pop(k, None)

        return CommitDelta(cells=cell_delta, unions=union_delta)

    def _compute_cell_delta(self, checkpoint: int) -> List[Tuple[Tuple, CellState, CellState]]:
        """Inner helper: build the (pos, prev, new) cell delta for a checkpoint.

        Pulled out of ``commit_with_delta`` so ``commit_with_full_delta``
        can reuse the same logic without duplicating the
        first-prev-per-cell tracking.
        """
        first_prev: Dict[Tuple, CellState] = {}
        for entry in self.trail[checkpoint:]:
            pos, _prev_domain, prev_assignment = entry
            # Keep the *earliest* prev_assignment for each cell so the delta
            # reflects assignment(checkpoint) -> assignment(now).
            if pos not in first_prev:
                first_prev[pos] = prev_assignment

        delta: List[Tuple[Tuple, CellState, CellState]] = []
        # Deterministic ordering: by (layer, track, ortho).
        for pos in sorted(first_prev.keys()):
            cell = self.cells.get(pos)
            if cell is None:
                continue
            prev = first_prev[pos]
            cur = cell.assignment
            if prev != cur:
                delta.append((pos, prev, cur))
        return delta

    def _initial_domain(self) -> Set[CellState]:
        """Reconstruct the full per-cell allowed-state set used at init time."""
        domain = {EMPTY}
        for net_id in self.net_ids:
            domain.add(CellState(OccupantType.WIRE, net_id=net_id))
        return domain
    
    def _propagate(self, changed_pos: Tuple, record_trail: bool) -> bool:
        """
        Constraint propagation from changed_pos.
        
        CRITICAL: Only propagate from DETERMINED cells (domain size = 1).
        
        Why: If a cell has domain {EMPTY, VSS} (not yet assigned), we cannot
        propagate VSS's spacing constraints — the cell might end up EMPTY.
        Propagating from undetermined cells causes false constraint cascading
        (e.g., removing VDD from a distant cell just because an intermediate
        cell MIGHT be VSS).
        
        Cascade only occurs when propagation causes a neighbor's domain to
        collapse to size 1 (auto-determined), which then triggers further
        propagation from that newly-determined cell.
        """
        queue = deque([changed_pos])
        
        while queue:
            pos = queue.popleft()
            
            cell = self.cells.get(pos)
            if cell is None or not cell.is_feasible:
                return False
            
            # ONLY propagate from determined cells (domain = 1 value)
            if cell.domain_size != 1:
                continue
            
            determined_state = next(iter(cell.domain))
            
            for constraint in self.constraints:
                # Skip constraints that don't apply to this cell's layer
                if (constraint.anchor_layer is not None and 
                    constraint.anchor_layer != pos[0]):
                    continue
                
                if not constraint.trigger(determined_state):
                    continue
                
                forbidden = constraint.forbidden_states(determined_state, self.net_ids)
                if not forbidden:
                    continue
                
                for delta in constraint.stencil:
                    d_layer, d_track, d_ortho = delta
                    
                    # Compute neighbor position
                    if d_layer == pos[0]:
                        n_pos = (pos[0], pos[1] + d_track, pos[2] + d_ortho)
                    else:
                        n_pos = (d_layer, pos[1] + d_track, pos[2] + d_ortho)
                    
                    neighbor = self.cells.get(n_pos)
                    if neighbor is None or neighbor.fixed:
                        continue
                    
                    # Remove forbidden states from neighbor's domain
                    new_domain = neighbor.domain - forbidden

                    if new_domain != neighbor.domain:
                        if record_trail:
                            self.trail.append(
                                (n_pos, frozenset(neighbor.domain), neighbor.assignment)
                            )

                        neighbor.domain = new_domain
                        
                        if not neighbor.is_feasible:
                            return False  # Contradiction!
                        
                        # If neighbor just became determined, auto-assign
                        # and add to queue for cascading propagation
                        if len(new_domain) == 1:
                            neighbor.assignment = next(iter(new_domain))
                            queue.append(n_pos)
        
        return True
    
    def checkpoint(self) -> int:
        """Return current trail position for backtracking.

        The returned integer indexes into ``self.trail``. M4b also
        snapshots the union-find trail length under the same key so
        ``restore`` and ``commit_with_full_delta`` can revert / report
        union events landed since the checkpoint, without changing
        this method's return type (callers stash an int).
        """
        cp = len(self.trail)
        # Stash the matching ``_uf_trail`` length so a later ``restore``
        # or ``commit_with_full_delta(cp)`` can bracket union events.
        # Indexing by the cell-trail length is safe because the cell
        # trail is append-only between checkpoints; if the same length
        # is reused (e.g., back-to-back checkpoints with no cell
        # changes), the latest value wins, which is also the one we
        # want — the second checkpoint logically supersedes the first.
        self._uf_checkpoints[cp] = len(self._uf_trail)
        return cp

    def restore(self, checkpoint: int):
        """
        Undo all domain *and* assignment changes back to the given checkpoint.

        Also undoes any union-find merges performed since the checkpoint,
        in reverse order, so net-equivalence is consistent with the
        cell-level state on rollback.
        """
        # Undo union-find first so any subsequent ``net_of`` queries
        # during rollback see a consistent component graph.
        uf_target = self._uf_checkpoints.get(checkpoint, 0)
        while len(self._uf_trail) > uf_target:
            self._uf_undo_one()

        while len(self.trail) > checkpoint:
            pos, old_domain, old_assignment = self.trail.pop()
            cell = self.cells.get(pos)
            if cell is not None:
                cell.domain = set(old_domain)
                cell.assignment = old_assignment

        # Drop checkpoint stash entries past the restore point.
        stale = [k for k in self._uf_checkpoints if k > checkpoint]
        for k in stale:
            self._uf_checkpoints.pop(k, None)
    
    def snapshot(self) -> Dict[Tuple, Tuple[CellState, FrozenSet[CellState]]]:
        """Full state snapshot (expensive, use checkpoint/restore when possible)."""
        return {
            pos: (cell.assignment, frozenset(cell.domain))
            for pos, cell in self.cells.items()
        }
    
    def restore_snapshot(self, snap: Dict):
        """Restore from full snapshot."""
        for pos, (assignment, domain) in snap.items():
            cell = self.cells.get(pos)
            if cell is not None:
                cell.assignment = assignment
                cell.domain = set(domain)
    
    def mark_blockage(self, pos: Tuple) -> bool:
        """Mark a cell as ``BLOCKAGE`` — an immovable obstacle (M3).

        Projects an unannotated GDS shape into CSP. After marking,
        subsequent ``propose_assign(pos, *)`` returns ``False`` because
        the cell becomes ``fixed`` with a singleton ``{BLOCKAGE}`` domain
        — the ``assign`` short-circuit at the top of the method
        ("``if cell.fixed: return cell.assignment == state``") rejects
        any non-BLOCKAGE state.

        Returns:
          ``True`` if the cell was marked (or was already a blockage).
          ``False`` if the position is outside the grid, or the cell
          already carries a non-EMPTY annotated assignment — that
          signals a parser-level conflict between LVS coverage and the
          unannotated shape pool, and the conservative-defaults rule
          (§D) says "treat collisions as real conflicts." The caller
          should surface the conflict; we do not silently overwrite.
        """
        cell = self.cells.get(pos)
        if cell is None:
            return False
        if cell.fixed and cell.assignment == BLOCKAGE:
            return True  # idempotent
        if cell.assignment != EMPTY:
            return False  # see docstring — caller reconciles
        cell.assignment = BLOCKAGE
        cell.domain = {BLOCKAGE}
        cell.fixed = True
        return True

    # =========================================================
    # Net-equivalence union-find (M4b)
    # =========================================================

    def mark_cut(self, pos: Tuple) -> bool:
        """Mark a cell as ``CUT`` — a cutter that breaks net-equivalence.

        Mirrors ``mark_blockage`` (M3). Sets ``cell.assignment`` to a
        synthetic ``CellState(CUT)``, collapses ``cell.domain`` to a
        singleton, and pins the cell as ``fixed=True``. After marking,
        the cell can no longer participate in ``union`` (the cut layer
        check below rejects it), so a chain of unions along the cut
        axis cannot cross this cell — the §B "no CUT between adjacent
        cells" rule.

        Returns:
            ``True`` if the cell was marked (or was already CUT).
            ``False`` if the position is outside the grid, or carries a
            non-EMPTY annotated assignment — same conservative-defaults
            stance as ``mark_blockage``.
        """
        cell = self.cells.get(pos)
        if cell is None:
            return False
        cut_state = CellState(OccupantType.CUT)
        if cell.fixed and cell.assignment == cut_state:
            return True
        if cell.assignment != EMPTY:
            return False
        cell.assignment = cut_state
        cell.domain = {cut_state}
        cell.fixed = True
        return True

    def _uf_find(self, pos: Tuple) -> Tuple:
        """Walk parent pointers to the component root.

        No path compression — keeps ``restore`` simple by making every
        union reversible by popping its trail entry. Lazy: positions
        not yet in the union-find are treated as their own root.
        """
        if pos not in self._uf_parent:
            return pos
        cur = pos
        while self._uf_parent[cur] != cur:
            cur = self._uf_parent[cur]
        return cur

    @staticmethod
    def _adjacent(pos_a: Tuple, pos_b: Tuple) -> bool:
        """True iff both cells are on the same layer with Manhattan-1 spacing."""
        if pos_a[0] != pos_b[0]:
            return False
        d_track = abs(pos_a[1] - pos_b[1])
        d_ortho = abs(pos_a[2] - pos_b[2])
        return (d_track + d_ortho) == 1

    def union(self, pos_a: Tuple, pos_b: Tuple) -> bool:
        """Merge two adjacent same-net cells into one equivalence class.

        Preconditions:
          * Both cells exist (``get_cell(pos) is not None``).
          * Same layer + Manhattan-1 adjacency.
          * Neither cell's assignment is ``OccupantType.CUT`` — that
            enforces §B's "no CUT between adjacent cells" rule (a chain
            of adjacent unions cannot cross a CUT cell because the
            union step *at* the CUT would be rejected here).
          * Both cells share the same ``net_id`` (or both are EMPTY,
            which is a no-op success).

        Returns ``True`` on a successful union (or a no-op when both
        cells are already in the same component); ``False`` when any
        precondition fails.

        The union is recorded on ``_uf_trail`` so ``restore`` can undo
        it. Path compression is intentionally not used.
        """
        cell_a = self.cells.get(pos_a)
        cell_b = self.cells.get(pos_b)
        if cell_a is None or cell_b is None:
            return False
        if not self._adjacent(pos_a, pos_b):
            return False
        for cell in (cell_a, cell_b):
            if cell.assignment.occ_type == OccupantType.CUT:
                return False
        # Same-net check: both EMPTY is OK; both same non-empty net_id is OK.
        if cell_a.assignment.net_id != cell_b.assignment.net_id:
            return False

        root_a = self._uf_find(pos_a)
        root_b = self._uf_find(pos_b)
        if root_a == root_b:
            return True  # already unioned

        # Union by size: smaller tree hangs under larger.
        size_a = self._uf_size.get(root_a, 1)
        size_b = self._uf_size.get(root_b, 1)
        if size_a < size_b:
            child, parent = root_a, root_b
            child_size, parent_size = size_a, size_b
        else:
            child, parent = root_b, root_a
            child_size, parent_size = size_b, size_a

        # Materialise both roots before mutating so ``_uf_undo_one``
        # can restore the prior state (a root has parent==self).
        prev_child_parent = self._uf_parent.get(child, child)
        self._uf_parent[child] = parent
        self._uf_parent.setdefault(parent, parent)
        self._uf_size[parent] = parent_size + child_size
        # Drop the child's size entry; not needed once it's not a root.
        self._uf_size.pop(child, None)

        self._uf_trail.append((child, prev_child_parent, parent, parent_size))
        return True

    def _uf_undo_one(self):
        """Pop one entry off ``_uf_trail`` and revert the corresponding union."""
        if not self._uf_trail:
            return
        child, prev_child_parent, parent, prev_parent_size = self._uf_trail.pop()
        # Restore the child's parent pointer.
        if prev_child_parent == child:
            # Was a root; reinstate the root entry and its size.
            self._uf_parent[child] = child
            # Recover the lost size by subtracting child component from
            # parent's running size — what we stored was parent's size
            # *before* this union, so we can directly restore.
            current_parent_size = self._uf_size.get(parent, 1)
            child_size = current_parent_size - prev_parent_size
            self._uf_size[child] = max(1, child_size)
        else:
            self._uf_parent[child] = prev_child_parent
        # Restore parent size.
        self._uf_size[parent] = prev_parent_size

    def net_of(self, pos: Tuple) -> Optional[str]:
        """Return the net_id of the cell's union-find component.

        Falls back to the cell's own assignment net_id when the position
        is not yet in the union-find (single-cell component). Returns
        ``None`` for unassigned / out-of-grid cells.
        """
        cell = self.cells.get(pos)
        if cell is None:
            return None
        root = self._uf_find(pos)
        root_cell = self.cells.get(root)
        if root_cell is None:
            return cell.assignment.net_id
        return root_cell.assignment.net_id

    def connected_to(self, pos: Tuple) -> List[Tuple]:
        """All cells in the same union-find component as ``pos``.

        Output is sorted for determinism. A cell that has never been
        unioned is its own singleton component, so this returns
        ``[pos]`` in that case (provided ``pos`` is a valid cell).
        """
        if self.cells.get(pos) is None:
            return []
        root = self._uf_find(pos)
        members: List[Tuple] = []
        if root not in self._uf_parent:
            # Singleton: the cell is its own root; nothing else has been
            # unioned to it.
            return [pos]
        for p in self._uf_parent.keys():
            if self._uf_find(p) == root:
                members.append(p)
        # ``pos`` itself may not be in ``_uf_parent`` keys yet if it's a
        # root that hasn't been unioned *from*; ensure it's included.
        if pos not in members:
            members.append(pos)
        return sorted(members)

    def connected_cells(self, net_id: str) -> List[Tuple]:
        """Return all assigned cells whose ``net_of`` agrees on ``net_id``.

        Walks every cell with a matching assignment net_id; the
        union-find is consulted only to disambiguate when CUT-driven
        splits land in M4d. For now this is approximately ``[c.pos for
        c in cells if c.assignment.net_id == net_id]``, sorted.
        """
        out: List[Tuple] = []
        for pos, cell in self.cells.items():
            if cell.assignment.net_id == net_id:
                out.append(pos)
        return sorted(out)

    def unassign(self, pos: Tuple):
        """
        Release a cell assignment (set back to EMPTY) without trail recording.

        WARNING: This does NOT automatically restore neighbor domains and
        does NOT participate in checkpoint/restore. New code should use
        :meth:`propose_release` (M2) which records a trail entry and lets
        the engine drive cell-delta computation on commit.
        """
        cell = self.cells.get(pos)
        if cell is not None and not cell.fixed:
            cell.assignment = EMPTY
            # Don't modify domain here - it will be rebuilt on re-propagation
    
    # =========================================================
    # Query / inspection methods
    # =========================================================
    
    def is_feasible(self) -> bool:
        """Check if any cell has an empty domain."""
        return all(cell.is_feasible for cell in self.cells.values())
    
    def domain_stats(self, layer: str = None) -> dict:
        """Get statistics about domain sizes."""
        cells = self.cells.values()
        if layer:
            cells = [c for c in cells if c.pos[0] == layer]
        
        domains = [c.domain_size for c in cells]
        if not domains:
            return {}
        
        return {
            'total_cells': len(domains),
            'assigned': sum(1 for d in domains if d == 1),
            'empty_domain': sum(1 for d in domains if d == 0),
            'avg_domain': sum(domains) / len(domains),
            'min_domain': min(domains),
            'max_domain': max(domains),
        }
    
    def get_assigned_cells(self, layer: str = None, 
                           net_id: str = None) -> List[GridCell]:
        """Get all cells with non-EMPTY assignments, optionally filtered."""
        result = []
        for cell in self.cells.values():
            if not cell.is_assigned:
                continue
            if layer and cell.pos[0] != layer:
                continue
            if net_id and cell.assignment.net_id != net_id:
                continue
            result.append(cell)
        return result
    
    def print_layer(self, layer: str, show_domain: bool = False):
        """Print a text visualization of a layer's grid state."""
        dims = self.layer_dims.get(layer)
        if not dims:
            print(f"Layer {layer} not found")
            return
        
        t_start, t_end, o_start, o_end = dims
        
        print(f"\n=== Layer: {layer} ===")
        print(f"  Track range: [{t_start}, {t_end})  Ortho range: [{o_start}, {o_end})")
        
        # Header: ortho indices
        header = "     " + "".join(f"{o:>5}" for o in range(o_start, o_end))
        print(header)
        
        for t in range(t_start, t_end):
            row = f"t{t:>3} "
            for o in range(o_start, o_end):
                cell = self.cells.get((layer, t, o))
                if cell is None:
                    row += "  ?  "
                elif cell.assignment == EMPTY:
                    if show_domain:
                        row += f" ({cell.domain_size:>2})"
                    else:
                        row += "  .  "
                else:
                    net = cell.assignment.net_id or '?'
                    row += f" {net[:3]:>3} "
            print(row)
