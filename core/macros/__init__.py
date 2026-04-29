"""L3 macro family (M6).

Per docs/architecture_roadmap.md §C, an L3 macro is a transactional unit:
it brackets its work in ``engine.checkpoint`` /
``engine.commit_with_full_delta`` (or ``engine.restore`` on failure),
calls only L2 atomic ops in ``core/atomic_ops.py``, and returns L1
``EditOp`` records. It does not mutate ``LayoutModel`` directly, does
not produce L1 records inline, and does not decide DRC feasibility —
those are the engine's job.

M6 Done: ``add_cut``, ``remove_cut`` (this file's ``cut_ops``),
``share_diffusion`` (``share_diffusion.py``). The historical L3
``device_resize`` macro lives in ``core/solver.py::LayoutSolver`` for
backwards compatibility — M6+ may move it here as part of consolidation.
"""

from core.macros.cut_ops import (
    add_cut,
    remove_cut,
    CutMacroResult,
)
from core.macros.share_diffusion import (
    share_diffusion,
    ShareDiffusionResult,
)

__all__ = [
    'add_cut',
    'remove_cut',
    'CutMacroResult',
    'share_diffusion',
    'ShareDiffusionResult',
]
