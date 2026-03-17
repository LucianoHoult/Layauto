"""Logging setup utilities for DRAM_PathFinder."""

from __future__ import annotations

import logging
from pathlib import Path


def setup_logger(run_dir: str | Path, logger_name: str = "dram_pathfinder") -> logging.Logger:
    """Create a logger that writes both to console and ``run.log`` in ``run_dir``."""
    run_path = Path(run_dir)
    log_file = run_path / "run.log"

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
