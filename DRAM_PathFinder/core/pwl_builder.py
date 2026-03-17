"""PWL stimulus construction for DRAM_PathFinder."""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

_TIME_UNITS = {"s": 1.0, "ms": 1e-3, "us": 1e-6, "ns": 1e-9, "ps": 1e-12, "fs": 1e-15}


class PWLBuilder:
    """Build causal SPICE PWL sources from operation sequence configuration."""

    @staticmethod
    def parse_time(time_text: str) -> float:
        """Parse engineering time literals (e.g., ``20ps``) into seconds."""
        m = re.fullmatch(r"\s*([0-9]*\.?[0-9]+)\s*([a-zA-Z]+)\s*", time_text)
        if not m:
            raise ValueError(f"Invalid time text: {time_text}")
        mag = float(m.group(1))
        unit = m.group(2).lower()
        if unit not in _TIME_UNITS:
            raise ValueError(f"Unsupported unit: {unit}")
        return mag * _TIME_UNITS[unit]

    def build(self, config: Dict, vdd: float = 1.2) -> str:
        """Build PWL strings for every operation while enforcing monotonic time points."""
        lines = ["* Auto-generated stimulus"]
        last_end = -1.0
        for op in config.get("operation_sequence", []):
            sig = op["signal"]
            start = self.parse_time(op["start"])
            duration = self.parse_time(op["duration"])
            tr = self.parse_time(op["tr"])
            tf = self.parse_time(op.get("tf", op["tr"]))
            end = start + duration
            if end <= start or tr <= 0 or tf <= 0:
                raise ValueError(f"Invalid edge timing for {sig}")
            if duration < tr + tf:
                raise ValueError(f"Duration too short for finite edges on {sig}")
            if start < last_end:
                raise ValueError(f"Non-overlapping sequence violation at {sig}")
            last_end = end

            pts: List[Tuple[float, float]] = [
                (0.0, 0.0),
                (start, 0.0),
                (start + tr, vdd),
                (end - tf, vdd),
                (end, 0.0),
            ]
            for i in range(1, len(pts)):
                if pts[i][0] < pts[i - 1][0]:
                    raise ValueError(f"Backward time step detected for {sig}")
            body = " ".join(f"{t:.6e} {v:.3f}" for t, v in pts)
            lines.append(f"V{sig} {sig} 0 PWL({body})")
        return "\n".join(lines) + "\n"
