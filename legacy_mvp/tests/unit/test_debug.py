"""Unit tests for ``pipeline.debug.DebugSession``."""

import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from pipeline.debug import DebugSession


def test_disabled_session_is_noop(tmp_path):
    """``enabled=False`` skips snapshotting and prints nothing."""
    dbg = DebugSession(str(tmp_path), enabled=False)
    with dbg.stage("x", "noop"):
        (tmp_path / "a.txt").write_text("hi")
    # No assertion needed - the test passes iff no exception is raised
    # and the file write inside the `with` block is unaffected.
    assert (tmp_path / "a.txt").read_text() == "hi"


def test_detects_new_and_modified_files(tmp_path, capsys):
    """Two stages: first creates a.txt, second creates b.txt and bumps a.txt."""
    dbg = DebugSession(str(tmp_path), enabled=True, pause=False)
    with dbg.stage("1", "first"):
        (tmp_path / "a.txt").write_text("hi")
    out = capsys.readouterr().out
    assert "new files (1)" in out
    assert "a.txt" in out

    time.sleep(0.01)
    with dbg.stage("2", "second"):
        (tmp_path / "b.txt").write_text("there")
        # bump a.txt's mtime well into the future so the change is detected
        future = time.time() + 10
        os.utime(str(tmp_path / "a.txt"), (future, future))
    out = capsys.readouterr().out
    assert "new files (1)" in out
    assert "b.txt" in out
    assert "modified files (1)" in out
    assert "a.txt" in out


def test_pause_skipped_when_not_a_tty(tmp_path, monkeypatch):
    """Non-TTY → pause must be silently skipped (CI/pytest safety)."""
    def _boom(*_args, **_kw):
        raise AssertionError("input() must not be called when stdin is not a TTY")

    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    monkeypatch.setattr("builtins.input", _boom)

    dbg = DebugSession(str(tmp_path), enabled=True, pause=True)
    with dbg.stage("1", "no-pause"):
        pass  # nothing — and crucially no input() call


def test_pause_q_aborts_with_systemexit(tmp_path, monkeypatch):
    """Typing 'q' at the prompt raises ``SystemExit(0)``."""
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda *_a, **_kw: "q")

    dbg = DebugSession(str(tmp_path), enabled=True, pause=True)
    with pytest.raises(SystemExit) as excinfo:
        with dbg.stage("1", "abort"):
            pass
    assert excinfo.value.code == 0


def test_pause_c_disables_further_pauses(tmp_path, monkeypatch):
    """Typing 'c' once disables pausing for the rest of the session."""
    inputs = iter(["c", "should-not-be-consumed"])

    def _next_input(*_a, **_kw):
        return next(inputs)

    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", _next_input)

    dbg = DebugSession(str(tmp_path), enabled=True, pause=True)
    with dbg.stage("1"):
        pass
    with dbg.stage("2"):
        pass
    # If the second stage tried to pause, the iterator would advance and the
    # third call would raise StopIteration — so reaching here means pauses
    # really were disabled after the first 'c'.
    assert next(inputs) == "should-not-be-consumed"


def test_recursive_snapshot_catches_subdir_files(tmp_path):
    """device_info_*.txt may live in a subdir; the walker must descend."""
    sub = tmp_path / "subdir"
    sub.mkdir()
    dbg = DebugSession(str(tmp_path), enabled=True, pause=False)
    with dbg.stage("1"):
        (sub / "device_info_M0.txt").write_text("data")
    new, _modified = dbg._diff_and_resnapshot()
    assert new == []  # already reported in the stage exit, snapshot is current
    # repeat to confirm the file is now in the snapshot
    fp = os.path.abspath(str(sub / "device_info_M0.txt"))
    assert fp in dbg._snapshot
