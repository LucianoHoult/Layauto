"""Tests for PWL stimulus generation."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.config_parser import ConfigParser
from core.pwl_builder import PWLBuilder


def test_pwl_generation_and_monotonic_time():
    config = ConfigParser(Path(__file__).resolve().parents[1] / "configs").load_all()
    stimulus = PWLBuilder().build(config)

    assert "VACT_CMD ACT_CMD 0 PWL(" in stimulus
    assert "VREAD_CMD READ_CMD 0 PWL(" in stimulus
    assert "2.000000e-11 1.200" in stimulus

    for line in stimulus.splitlines():
        if "PWL(" not in line:
            continue
        body = line.split("PWL(", 1)[1].rstrip(")")
        vals = [float(x) for x in re.findall(r"[-+]?\d+\.\d+e[+-]\d+", body)]
        times = vals[0::2]
        assert times == sorted(times)


def test_build_testbench_links_commands_to_route_drivers():
    from main import build_testbench

    config = ConfigParser(Path(__file__).resolve().parents[1] / "configs").load_all()
    stimulus = PWLBuilder().build(config)
    testbench = build_testbench("* netlist", stimulus, 2, config["array_topology"]["routing_targets"])

    assert "E_DRV_WL DRV_WL 0 ACT_CMD 0 1" in testbench
    assert "E_DRV_BL DRV_BL 0 READ_CMD 0 1" in testbench
    assert "E_DRV_CSL DRV_CSL 0 READ_CMD 0 1" in testbench
    assert "E_DRV_LIO DRV_LIO 0 READ_CMD 0 1" in testbench
