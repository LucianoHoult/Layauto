import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import re

import pytest

from dram_pathfinder import generate_pwl_stimulus, transform_netlist


def _dummy_config():
    return {
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


def _dummy_netlist():
    return """* tiny 2x2 dram
XDEC0 ndec0 vdd vss DECODER
XDEC1 ndec1 vdd vss DECODER
XCELL_R0_C0 wl_0 bl_0 vdd vss DRAMCELL
XCELL_R0_C1 wl_0 bl_1 vdd vss DRAMCELL
XCELL_R1_C0 wl_1 bl_0 vdd vss DRAMCELL
XCELL_R1_C1 wl_1 bl_1 vdd vss DRAMCELL
"""


def test_netlist_transformation():
    config = _dummy_config()
    out = transform_netlist(_dummy_netlist(), config).modified_netlist

    assert "XDEC1 ndec1 vdd vss DECODER" not in out
    assert "CLOAD_XDEC1 ndec1 0" in out
    assert "ILEAK_XDEC1 ndec1 0 DC" in out

    assert "XCELL_R0_C1 wl_0 bl_1 vdd vss DRAMCELL" not in out
    assert "XCELL_R0_C0" in out
    assert "XCELL_R1_C0" in out
    assert "XCELL_R1_C1" in out

    for idx in range(3):
        assert f"RWL_{idx}" in out
        assert f"RBL_{idx}" in out
    for idx in range(4):
        assert f"CWL_{idx}" in out
        assert f"CBL_{idx}" in out

    wl_caps = [
        float(value)
        for value in re.findall(r"^CWL_\d+\s+\S+\s+0\s+([0-9.eE+-]+)$", out, re.MULTILINE)
    ]
    expected_wl_total_c = (
        config["rc_constants"]["WL_M3"]["C_per_um"]
        * config["array_topology"]["cols"]
        * config["array_topology"]["col_pitch_um"]
    )
    assert sum(wl_caps) == pytest.approx(expected_wl_total_c)


def test_pwl_generation():
    stimulus = generate_pwl_stimulus(_dummy_config())

    assert "VACT_CMD ACT_CMD 0 PWL(" in stimulus
    assert "VREAD_CMD READ_CMD 0 PWL(" in stimulus

    for line in stimulus.splitlines():
        if "PWL(" not in line:
            continue
        body = line.split("PWL(", 1)[1].rstrip(")")
        vals = [float(x) for x in re.findall(r"[-+]?\d+\.\d+e[+-]\d+", body)]
        times = vals[0::2]
        assert times == sorted(times)

    assert "2.000000e-11 1.200" in stimulus


def test_pwl_generation_merges_repeated_signal_events():
    config = _dummy_config()
    config["operation_sequence"] = [
        {"signal": "ACT_CMD", "start": "0ns", "duration": "5ns", "tr": "20ps"},
        {"signal": "ACT_CMD", "start": "7ns", "duration": "4ns", "tr": "20ps"},
    ]

    stimulus = generate_pwl_stimulus(config)
    lines = [line for line in stimulus.splitlines() if line.startswith("VACT_CMD")]
    assert len(lines) == 1
    assert "7.020000e-09 1.200" in lines[0]
