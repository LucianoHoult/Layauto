"""Configuration loading for decoupled DRAM_PathFinder JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


class ConfigParser:
    """Load and normalize technology, topology, and stimulus JSON files."""

    def __init__(self, config_dir: str | Path):
        """Initialize parser with a directory containing config JSON files."""
        self.config_dir = Path(config_dir)

    def load_all(self) -> Dict:
        """Load ``tech_rc.json``, ``array_topo.json``, and ``stimulus.json`` into one dict."""
        tech = self._load_json("tech_rc.json")
        topo = self._load_json("array_topo.json")
        stimulus = self._load_json("stimulus.json")
        merged = {}
        merged.update(tech)
        merged.update(topo)
        merged.update(stimulus)
        return merged

    def _load_json(self, file_name: str) -> Dict:
        """Read a single JSON file from the configured directory."""
        path = self.config_dir / file_name
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
