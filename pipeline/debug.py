"""
Per-stage debug helper for the production-adaptation pipeline.

``DebugSession`` snapshots ``output_dir`` between stages and, on each
``with dbg.stage(name): ...`` exit, prints the files that appeared or
changed and (optionally) waits for a keypress so the user can inspect
the freshly generated intermediates before the next stage runs.

Disabled mode (the default in normal runs) is a true no-op: the
context manager just yields, so wrapping every stage costs nothing.

Non-TTY stdin → the pause is skipped silently. This matters because
``run_mvp.py`` is exercised by pytest and CI, and a blocking ``input()``
in that path would hang the suite.
"""

import os
import sys
import time
from contextlib import contextmanager


def _fmt_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 ** 2:
        return f"{n / 1024:.1f} KB"
    return f"{n / 1024 ** 2:.1f} MB"


class DebugSession:
    """Tracks file changes under ``output_dir`` between pipeline stages.

    Usage:
        dbg = DebugSession(output_dir, enabled=args.debug,
                           pause=not args.debug_no_pause)
        with dbg.stage("1.5", "LVS extract"):
            ...   # body writes intermediate files into output_dir

    Disabled (``enabled=False``) — ``stage()`` is a yield-only no-op.
    """

    def __init__(self, output_dir: str, *,
                 enabled: bool = False, pause: bool = True):
        self.output_dir = output_dir
        self.enabled = bool(enabled)
        self._pause_requested = bool(pause)
        self._abort_pauses = False
        self._snapshot: dict = {}
        if self.enabled:
            self._snapshot = self._scan()

    def _scan(self) -> dict:
        out: dict = {}
        if not os.path.isdir(self.output_dir):
            return out
        # Recursive: ``calibre.device_info_dir`` / ``net_shapes_dir`` can
        # redirect per-device / per-net dumps to a subdirectory.
        for root, _dirs, files in os.walk(self.output_dir):
            for name in files:
                p = os.path.join(root, name)
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                out[os.path.abspath(p)] = (st.st_mtime, st.st_size)
        return out

    def _diff_and_resnapshot(self):
        cur = self._scan()
        prev = self._snapshot
        new, modified = [], []
        for p, (mt, sz) in cur.items():
            if p not in prev:
                new.append(p)
            else:
                old_mt, old_sz = prev[p]
                if mt > old_mt + 1e-6 or sz != old_sz:
                    modified.append(p)
        self._snapshot = cur
        return sorted(new), sorted(modified)

    @contextmanager
    def stage(self, name: str, desc: str = ''):
        if not self.enabled:
            yield
            return
        bar = '-' * 70
        print('\n' + bar)
        title = f"[debug] >>> stage {name}"
        if desc:
            title += f"  - {desc}"
        print(title)
        print(bar)
        t0 = time.time()
        try:
            yield
        finally:
            dt = time.time() - t0
            new, modified = self._diff_and_resnapshot()
            self._report(name, dt, new, modified)
            self._maybe_pause(name)

    def _report(self, name, dt, new, modified):
        sizes = self._snapshot
        print(f"[debug] <<< stage {name} done in {dt:.2f}s")
        if new:
            print(f"[debug]   new files ({len(new)}):")
            for p in new:
                _mt, sz = sizes.get(os.path.abspath(p), (0, 0))
                print(f"      {p}  ({_fmt_size(sz)})")
        if modified:
            print(f"[debug]   modified files ({len(modified)}):")
            for p in modified:
                _mt, sz = sizes.get(os.path.abspath(p), (0, 0))
                print(f"      {p}  ({_fmt_size(sz)})")
        if not new and not modified:
            print("[debug]   (no file changes under output_dir)")

    def _maybe_pause(self, name):
        if not self._pause_requested or self._abort_pauses:
            return
        if not (sys.stdin and sys.stdin.isatty()):
            return
        try:
            ans = input(
                f"[debug] press Enter to continue past stage {name} "
                f"(q=abort, c=continue without further pauses): "
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n[debug] interrupted - aborting run.")
            raise SystemExit(130)
        if ans == 'q':
            print("[debug] aborting run at user request.")
            raise SystemExit(0)
        if ans == 'c':
            self._abort_pauses = True
            print("[debug] continuing - pauses disabled for the rest of this run.")
