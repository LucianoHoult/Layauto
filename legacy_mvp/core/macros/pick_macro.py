"""L4 macro dispatch (M6b).

Per docs/architecture_roadmap.md §C, the L4 (pipeline) layer's job is
``diff_cdl → pick_macro → apply → writeback``. The first arrow's
output (a list of CDL deltas) feeds ``pick_macro``, which picks the
right L3 macro for each delta and binds its arguments.

For the MVP, the only CDL-expressible delta is parameter-level
(today: ``nfin`` count for fin resize). Other M6 macros — share
diffusion, split diffusion, add/remove cut — operate on layout-side
intent that is *not* expressible in CDL. They are exposed as
importable Python API; a future "layout intent" file format (out of
M6b scope) would route them through this dispatch table.

Device add / device remove deltas are out of M6b scope because they
require routing (see [§ Routing scope](../../docs/architecture_roadmap.md#routing-scope-mvp-bound)).
M6d will extend this dispatch to cover them once M6c's router lands.
"""

from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Tuple


@dataclass
class MacroCall:
    """A bound macro invocation.

    ``macro_name`` is a stable string identifier (e.g. ``'device_resize'``).
    ``args`` and ``kwargs`` are the macro's arguments. The pipeline calls
    ``execute(solver)`` to dispatch — the wrapper looks up the macro on
    the solver / module surface and invokes it.

    The ``MacroCall`` indirection lets the pipeline batch-execute a
    list of calls (each potentially in its own engine transaction)
    without leaking macro-specific knowledge into the dispatch loop.
    """
    macro_name: str
    args: tuple = ()
    kwargs: dict = None
    diff: Optional[dict] = None  # backlink to the source CDL delta entry

    def __post_init__(self):
        if self.kwargs is None:
            self.kwargs = {}

    def execute(self, solver) -> Any:
        """Look up the macro on the solver and invoke it.

        For the MVP, only ``device_resize`` lives on
        ``LayoutSolver``; future macros (M6d) may live in
        ``core/macros/`` and need a richer dispatch surface.
        """
        macro = getattr(solver, self.macro_name, None)
        if macro is None:
            raise ValueError(
                f"MacroCall: solver has no macro {self.macro_name!r}"
            )
        return macro(*self.args, **self.kwargs)

    def __repr__(self):
        if self.diff is not None:
            return (f"MacroCall({self.macro_name} {self.args} "
                    f"from {self.diff!r})")
        return f"MacroCall({self.macro_name} {self.args})"


def pick_macro(diff_entry: dict, model=None) -> Optional[MacroCall]:
    """Pick the right L3 macro for a CDL diff entry.

    A diff entry has the shape produced by ``io_adapters.cdl_parser.diff_cdl``:

        {'inst': 'MN0', 'param': 'nfin', 'old': 5, 'new': 4}

    Returns a ``MacroCall`` bound to the right macro + arguments, or
    ``None`` if the delta isn't dispatchable (unknown parameter, or
    one that requires routing — both are MVP-out-of-scope).

    Today's table:
      * ``param == 'nfin'`` → ``device_resize(inst, new)`` on the solver.

    Out of MVP scope (returns ``None`` with a comment for the caller to log):
      * Device add / device remove (delta detection itself is M6d).
      * Parameter changes other than ``nfin`` (no L3 macro yet).
    """
    param = diff_entry.get('param')

    if param == 'nfin':
        return MacroCall(
            macro_name='resize_device',
            args=(diff_entry['inst'], diff_entry['new']),
            diff=diff_entry,
        )

    # Other parameters (l, w, vt-flavor, ...) have no L3 macro today.
    # Returning ``None`` signals the pipeline to log + skip.
    return None


def pick_macros(diffs: List[dict], model=None) -> List[MacroCall]:
    """Apply ``pick_macro`` over a list of diffs and filter ``None``.

    Convenience for the pipeline; preserves diff order (deterministic).
    """
    out: List[MacroCall] = []
    for d in diffs:
        call = pick_macro(d, model=model)
        if call is not None:
            out.append(call)
    return out
