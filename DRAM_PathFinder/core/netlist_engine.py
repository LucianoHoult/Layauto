"""Netlist transformation engine for DRAM_PathFinder."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class TransformResult:
    """Container for transformed netlist and transformation metadata."""

    netlist: str
    removed_instances: List[str]
    rewired_target_instance: str
    wl_target_node: str
    bl_target_node: str


class NetlistEngine:
    """Apply peripheral pruning, active-cross reduction, dummy linearization, and RC rewiring."""

    def __init__(self, config: Dict):
        """Store merged configuration for subsequent transformations."""
        self.config = config

    def transform(self, logical_lines: List[str]) -> TransformResult:
        """Transform logical CDL lines and return final modified netlist text."""
        topo = self.config["array_topology"]
        active_row = topo["active_target"]["row"]
        active_col = topo["active_target"]["col"]
        rows = topo["rows"]
        cols = topo["cols"]
        pattern = re.compile(topo["cell_instance_pattern"])
        dummy_caps = topo["dummy_linear_caps"]

        pruning_map = {e["instance"]: e for e in self.config.get("peripheral_pruning", [])}
        static_loads = self.config.get("static_loads", {})

        wl_node = f"wl_{active_row}"
        bl_node = f"bl_{active_col}"
        wl_far_end = f"wl_end_{active_row}"
        bl_far_end = f"bl_end_{active_col}"

        wl_target_node = self._segment_node_for_index("WL", cols, active_col, wl_far_end)
        bl_target_node = self._segment_node_for_index("BL", rows, active_row, bl_far_end)

        out: List[str] = []
        removed: List[str] = []
        rewired_target = ""

        for raw in logical_lines:
            stripped = raw.strip()
            if not stripped or stripped.startswith("*"):
                out.append(raw)
                continue

            inst = stripped.split()[0]

            if inst in pruning_map:
                p = pruning_map[inst]
                load = static_loads[p["load"]]
                node = p["node"]
                out.append(f"* pruned {inst}")
                out.append(f"CLOAD_{inst} {node} 0 {load['Cload']:.6e}")
                out.append(f"ILEAK_{inst} {node} 0 DC {load['Ileak']:.6e}")
                removed.append(inst)
                continue

            m = pattern.match(inst)
            if not m:
                out.append(raw)
                continue

            row = int(m.group("row"))
            col = int(m.group("col"))
            if row >= rows or col >= cols:
                raise ValueError(f"Array index out of bounds for {inst}")

            tokens = stripped.split()
            if len(tokens) < 6:
                out.append(raw)
                continue

            # Expected token order for dummy input: inst wl bl vdd vss subckt
            cur_wl = tokens[1]
            cur_bl = tokens[2]

            if row == active_row and col == active_col:
                tokens[1] = wl_target_node
                tokens[2] = bl_target_node
                rewired_target = " ".join(tokens)
                out.append(rewired_target)
                continue

            # Keep only active-cross cells; all others are removed.
            if row == active_row or col == active_col:
                removed.append(inst)
                out.append(f"* linearized active-cross dummy {inst}")
                if row == active_row:
                    out.append(f"CGATE_DUMMY_{inst} {cur_wl} 0 {dummy_caps['wl_gate_cap']:.6e}")
                if col == active_col:
                    out.append(f"CJUNC_DUMMY_{inst} {cur_bl} 0 {dummy_caps['bl_junc_cap']:.6e}")
                continue

            removed.append(inst)
            out.append(f"* removed inactive cell {inst}")

        out.append("")
        out.extend(self._inject_pi("WL", wl_node, wl_far_end, cols))
        out.extend(self._inject_pi("BL", bl_node, bl_far_end, rows))

        return TransformResult(
            netlist="\n".join(out).strip() + "\n",
            removed_instances=removed,
            rewired_target_instance=rewired_target,
            wl_target_node=wl_target_node,
            bl_target_node=bl_target_node,
        )

    def _inject_pi(self, prefix: str, start_node: str, end_node: str, span_count: int) -> List[str]:
        """Generate distributed pi-model lines for WL/BL with configurable segmentation."""
        segs = self.config["precision"]["pi_segments_per_wire"]
        rc_cfg = self.config["rc_constants"]["WL_M3" if prefix == "WL" else "BL_M2"]
        pitch_key = "col_pitch_um" if prefix == "WL" else "row_pitch_um"
        pitch = self.config["array_topology"].get(pitch_key, 1.0)
        length_um = span_count * pitch

        total_r = rc_cfg["R_per_um"] * length_um
        total_c = rc_cfg["C_per_um"] * length_um
        r_seg = total_r / segs
        c_seg = total_c / segs

        nodes = [start_node] + [f"{prefix}_n{i}" for i in range(1, segs)] + [end_node]
        lines = [f"* PI model {prefix} {start_node}->{end_node}", f"C{prefix}_0 {nodes[0]} 0 {c_seg/2:.6e}"]
        for idx in range(segs):
            n1 = nodes[idx]
            n2 = nodes[idx + 1]
            lines.append(f"R{prefix}_{idx} {n1} {n2} {r_seg:.6e}")
            lines.append(f"C{prefix}_{idx+1} {n2} 0 {c_seg/2:.6e}")
        return lines

    def _segment_node_for_index(self, prefix: str, total_count: int, idx: int, far_end_node: str) -> str:
        """Map a physical array index to the corresponding distributed RC node name."""
        segs = self.config["precision"]["pi_segments_per_wire"]
        # Convert 0-based physical index into 1..segs segment bucket.
        segment = int((idx + 1) * segs / total_count)
        segment = max(1, min(segs, segment))
        if segment == segs:
            return far_end_node
        return f"{prefix}_n{segment}"
