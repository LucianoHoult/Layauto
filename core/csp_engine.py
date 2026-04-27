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

        # Truncate trail; commit is non-restorable.
        del self.trail[checkpoint:]
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
        """Return current trail position for backtracking."""
        return len(self.trail)

    def restore(self, checkpoint: int):
        """
        Undo all domain *and* assignment changes back to the given checkpoint.

        Restores entries in reverse order of modification. Each trail entry
        carries the prior (domain, assignment) pair, so the post-restore
        state is exactly the pre-checkpoint state.
        """
        while len(self.trail) > checkpoint:
            pos, old_domain, old_assignment = self.trail.pop()
            cell = self.cells.get(pos)
            if cell is not None:
                cell.domain = set(old_domain)
                cell.assignment = old_assignment
    
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
