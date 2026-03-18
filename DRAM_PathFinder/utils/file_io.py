"""File I/O helpers for DRAM_PathFinder run artifact management."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


def create_run_directory(base_dir: str | Path) -> Path:
    """Create and return a timestamped run directory under the provided base path.

    The returned directory follows the format ``run_YYYYMMDD_HHMMSS``.
    """
    base = Path(base_dir)
    base.mkdir(parents=True, exist_ok=True)
    run_name = datetime.now().strftime("run_%Y%m%d_%H%M%S")
    run_dir = base / run_name
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def read_text(path: str | Path) -> str:
    """Read UTF-8 text from disk."""
    return Path(path).read_text(encoding="utf-8")


def write_text(path: str | Path, content: str) -> None:
    """Write UTF-8 text to disk, creating parent directories as needed."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
