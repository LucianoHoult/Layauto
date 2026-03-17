"""DRAM_PathFinder: lightweight netlist/stimulus automation for DRAM timing studies."""

from __future__ import annotations

import json
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple


_TIME_UNITS = {"s": 1.0, "ms": 1e-3, "us": 1e-6, "ns": 1e-9, "ps": 1e-12, "fs": 1e-15}


@dataclass
class NetlistTransformResult:
    modified_netlist: str
    removed_instances: List[str]


def parse_time_to_seconds(time_text: str) -> float:
    """Convert SPICE-like time text (e.g. 5ns, 20ps) into seconds."""
    match = re.fullmatch(r"\s*([0-9]*\.?[0-9]+)\s*([a-zA-Z]+)\s*", time_text)
    if not match:
        raise ValueError(f"Invalid time value: {time_text}")
    mag = float(match.group(1))
    unit = match.group(2).lower()
    if unit not in _TIME_UNITS:
        raise ValueError(f"Unsupported time unit: {unit}")
    return mag * _TIME_UNITS[unit]


def load_config(config_path: str | Path) -> Dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _inject_pi_for_net(
    start_node: str,
    end_node: str,
    prefix: str,
    total_r: float,
    total_c: float,
    segments: int,
) -> List[str]:
    """Create distributed pi-segments: R-series + shunt C/2 at segment boundaries."""
    if segments < 1:
        raise ValueError("segments must be >= 1")

    lines: List[str] = [f"* PI model for {prefix} from {start_node} to {end_node}"]
    r_seg = total_r / segments
    c_seg = total_c / segments

    # Node chain n0 -> n1 -> ... -> nN
    nodes = [start_node] + [f"{prefix}_n{i}" for i in range(1, segments)] + [end_node]

    lines.append(f"C{prefix}_0 {nodes[0]} 0 {c_seg / 2:.6e}")
    for idx in range(segments):
        n1 = nodes[idx]
        n2 = nodes[idx + 1]
        lines.append(f"R{prefix}_{idx} {n1} {n2} {r_seg:.6e}")
        lines.append(f"C{prefix}_{idx+1} {n2} 0 {c_seg / 2:.6e}")
    return lines


def transform_netlist(netlist_text: str, config: Dict) -> NetlistTransformResult:
    """Apply peripheral pruning, active-cross array reduction, and RC pi-model injection."""
    rows = config["array_topology"]["rows"]
    cols = config["array_topology"]["cols"]
    active_row = config["array_topology"]["active_target"]["row"]
    active_col = config["array_topology"]["active_target"]["col"]

    removed_instances: List[str] = []
    pruning_map = {
        entry["instance"]: entry for entry in config.get("peripheral_pruning", [])
    }
    static_loads = config.get("static_loads", {})

    transformed_lines: List[str] = []
    for raw_line in netlist_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("*"):
            transformed_lines.append(raw_line)
            continue

        tokens = line.split()
        inst = tokens[0]

        # Peripheral instance replacement by equivalent C and leakage I.
        if inst in pruning_map:
            prune_cfg = pruning_map[inst]
            load_key = prune_cfg["load"]
            node = prune_cfg["node"]
            load = static_loads[load_key]
            transformed_lines.append(f"* pruned {inst}")
            transformed_lines.append(f"CLOAD_{inst} {node} 0 {load['Cload']:.6e}")
            transformed_lines.append(f"ILEAK_{inst} {node} 0 DC {load['Ileak']:.6e}")
            removed_instances.append(inst)
            continue

        # Active cross pruning for XCELL_R<r>_C<c> instances.
        m = re.match(r"^XCELL_R(\d+)_C(\d+)$", inst)
        if m:
            r_idx = int(m.group(1))
            c_idx = int(m.group(2))
            if r_idx >= rows or c_idx >= cols:
                raise ValueError(f"Cell index out of bounds in instance {inst}")
            if (r_idx != active_row) and (c_idx != active_col):
                removed_instances.append(inst)
                transformed_lines.append(f"* removed inactive cell {inst}")
                continue

        transformed_lines.append(raw_line)

    pi_segments = config["precision"]["pi_segments_per_wire"]
    row_pitch_um = config["array_topology"].get("row_pitch_um", 1.0)
    col_pitch_um = config["array_topology"].get("col_pitch_um", 1.0)

    wl_rc = config["rc_constants"].get("WL_M3", {"R_per_um": 0.0, "C_per_um": 0.0})
    bl_rc = config["rc_constants"].get("BL_M2", wl_rc)

    wl_total_r = wl_rc["R_per_um"] * (cols * col_pitch_um)
    wl_total_c = wl_rc["C_per_um"] * (cols * col_pitch_um)
    bl_total_r = bl_rc["R_per_um"] * (rows * row_pitch_um)
    bl_total_c = bl_rc["C_per_um"] * (rows * row_pitch_um)

    wl_net = f"wl_{active_row}"
    bl_net = f"bl_{active_col}"

    transformed_lines.append("")
    transformed_lines.extend(
        _inject_pi_for_net(f"drv_{wl_net}", wl_net, "WL", wl_total_r, wl_total_c, pi_segments)
    )
    transformed_lines.extend(
        _inject_pi_for_net(f"drv_{bl_net}", bl_net, "BL", bl_total_r, bl_total_c, pi_segments)
    )

    return NetlistTransformResult("\n".join(transformed_lines).strip() + "\n", removed_instances)


def generate_pwl_stimulus(config: Dict, vdd: float = 1.2) -> str:
    """Convert operation_sequence to causal PWL sources with finite rise/fall edges."""
    lines = ["* Auto-generated stimulus"]
    for op in config.get("operation_sequence", []):
        signal = op["signal"]
        t_start = parse_time_to_seconds(op["start"])
        t_dur = parse_time_to_seconds(op["duration"])
        tr = parse_time_to_seconds(op["tr"])
        t_end = t_start + t_dur
        if tr <= 0 or t_end <= t_start:
            raise ValueError(f"Invalid timing for signal {signal}")
        if t_dur < 2 * tr:
            raise ValueError(f"duration must be >= 2*tr for {signal}")

        points = [
            (0.0, 0.0),
            (t_start, 0.0),
            (t_start + tr, vdd),
            (t_end - tr, vdd),
            (t_end, 0.0),
        ]

        for i in range(1, len(points)):
            if points[i][0] < points[i - 1][0]:
                raise ValueError(f"Non-causal waveform for signal {signal}")

        point_text = " ".join(f"{t:.6e} {v:.3f}" for t, v in points)
        lines.append(f"V{signal} {signal} 0 PWL({point_text})")

    return "\n".join(lines) + "\n"


def build_testbench(modified_netlist: str, stimulus: str, active_row: int) -> str:
    """Assemble a runnable SPICE deck with netlist, stimulus, and timing measurements."""
    return (
        "* DRAM_PathFinder generated testbench\n"
        ".option post=2\n"
        ".param vdd=1.2\n\n"
        f"{modified_netlist}\n"
        f"{stimulus}\n"
        ".tran 1p 20n\n"
        f".meas tran t_act_to_wl trig v(ACT_CMD) val='vdd/2' rise=1 targ v(wl_{active_row}) val='vdd/2' rise=1\n"
        ".end\n"
    )


def demo_run() -> Tuple[Dict, str, str, str]:
    """Self-contained runnable demo using tempfile + multiline dummy input artifacts."""
    dummy_cfg = {
        "rc_constants": {
            "WL_M3": {"R_per_um": 0.5, "C_per_um": 0.2e-15},
            "BL_M2": {"R_per_um": 0.7, "C_per_um": 0.25e-15},
        },
        "precision": {"pi_segments_per_wire": 3},
        "array_topology": {
            "rows": 2,
            "cols": 2,
            "row_pitch_um": 2.0,
            "col_pitch_um": 1.5,
            "active_target": {"row": 1, "col": 0},
        },
        "static_loads": {"LWD_inactive": {"Cload": 10e-15, "Ileak": 1e-9}},
        "peripheral_pruning": [
            {"instance": "XDEC1", "load": "LWD_inactive", "node": "ndec1"}
        ],
        "operation_sequence": [
            {"signal": "ACT_CMD", "start": "0ns", "duration": "5ns", "tr": "20ps"},
            {"signal": "READ_CMD", "start": "5ns", "duration": "5ns", "tr": "20ps"},
        ],
    }

    dummy_cdl = """* tiny 2x2 dram
XDEC0 ndec0 vdd vss DECODER
XDEC1 ndec1 vdd vss DECODER
XCELL_R0_C0 wl_0 bl_0 vdd vss DRAMCELL
XCELL_R0_C1 wl_0 bl_1 vdd vss DRAMCELL
XCELL_R1_C0 wl_1 bl_0 vdd vss DRAMCELL
XCELL_R1_C1 wl_1 bl_1 vdd vss DRAMCELL
"""

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
        json.dump(dummy_cfg, tf)
        cfg_path = tf.name

    config = load_config(cfg_path)
    transformed = transform_netlist(dummy_cdl, config)
    stimulus = generate_pwl_stimulus(config)
    tb = build_testbench(transformed.modified_netlist, stimulus, config["array_topology"]["active_target"]["row"])
    return config, transformed.modified_netlist, stimulus, tb


if __name__ == "__main__":
    _, netlist_out, stim_out, tb_out = demo_run()
    print("=== Modified Netlist ===")
    print(netlist_out)
    print("=== Stimulus ===")
    print(stim_out)
    print("=== Testbench ===")
    print(tb_out)
