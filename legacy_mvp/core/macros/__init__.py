"""L3 macro family (M6).

Per docs/architecture_roadmap.md §C, an L3 macro is a transactional unit:
it brackets its work in ``engine.checkpoint`` /
``engine.commit_with_full_delta`` (or ``engine.restore`` on failure),
calls only L2 atomic ops in ``core/atomic_ops.py``, and returns L1
``EditOp`` records. It does not mutate ``LayoutModel`` directly, does
not produce L1 records inline, and does not decide DRC feasibility —
those are the engine's job.

* M6a Done: ``add_cut`` / ``remove_cut`` (``cut_ops``), ``share_diffusion``
  (``share_diffusion.py``).
* M6b Done: ``split_diffusion`` (``split_diffusion.py``), ``pick_macro``
  dispatch table (``pick_macro.py``).

The historical L3 ``device_resize`` macro lives in
``core/solver.py::LayoutSolver`` for backwards compatibility — M6d may
move it here as part of consolidation. ``pick_macro`` already routes
the MVP fixture's ``nfin`` deltas to it.

M6c (routing subsystem) and M6d (routing-dependent macros — device_add
/ device_remove / net_reroute / buffer_insert) are deferred per the
MVP's "no maze routing" ground rule (see roadmap § Routing scope).
"""

from core.macros.cut_ops import (
    add_cut,
    remove_cut,
    CutMacroResult,
)
from core.macros.pick_macro import (
    MacroCall,
    pick_macro,
    pick_macros,
)
from core.macros.share_diffusion import (
    share_diffusion,
    ShareDiffusionResult,
)
from core.macros.split_diffusion import (
    split_diffusion,
    SplitDiffusionResult,
)

__all__ = [
    'add_cut',
    'remove_cut',
    'CutMacroResult',
    'share_diffusion',
    'ShareDiffusionResult',
    'split_diffusion',
    'SplitDiffusionResult',
    'pick_macro',
    'pick_macros',
    'MacroCall',
]
