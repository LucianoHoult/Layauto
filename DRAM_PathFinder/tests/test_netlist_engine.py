"""Tests for CDL parsing and netlist transformation behavior."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.cdl_parser import CDLParser
from core.config_parser import ConfigParser
from core.netlist_engine import NetlistEngine


def _cfg():
    return ConfigParser(Path(__file__).resolve().parents[1] / "configs").load_all()


def _raw_cdl() -> str:
    return (Path(__file__).resolve().parents[1] / "inputs" / "dummy_4x4_array.cdl").read_text(encoding="utf-8")


def test_cdl_continuation_merge():
    lines = CDLParser.merge_continuation_lines(_raw_cdl())
    target = [ln for ln in lines if ln.startswith("XCELL_R2_C1")][0]
    assert "+" not in target
    assert target.endswith("DRAMCELL")


def test_netlist_transformation_and_rewiring():
    config = _cfg()
    logical = CDLParser.merge_continuation_lines(_raw_cdl())
    result = NetlistEngine(config).transform(logical)
    out = result.netlist

    assert "XDEC1 ndec1 vdd vss DECODER" not in out
    assert "CLOAD_XDEC1 ndec1 0" in out
    assert "ILEAK_XDEC1 ndec1 0 DC" in out

    # Active-cross dummies are linearized and original instances are removed.
    assert "XCELL_R2_C0 wl_2 bl_0 vdd vss DRAMCELL" not in out
    assert "CGATE_DUMMY_XCELL_R2_C0 wl_2 0" in out
    assert "XCELL_R0_C1 wl_0 bl_1 vdd vss DRAMCELL" not in out
    assert "CJUNC_DUMMY_XCELL_R0_C1 bl_1 0" in out

    # Target cell must be rewired from global wl_2/bl_1 to segment nodes.
    assert "XCELL_R2_C1 wl_2 bl_1 vdd vss DRAMCELL" not in out
    assert "XCELL_R2_C1 WL_n2 BL_n3 vdd vss DRAMCELL" in out
    assert result.wl_target_node == "WL_n2"
    assert result.bl_target_node == "BL_n3"

    # PI segments are created from real decoder/sense-amplifier nets.
    assert "* PI model WL wl_2->wl_end_2" in out
    assert "* PI model BL bl_1->bl_end_1" in out

    # PI segments are created and numbered.
    for idx in range(4):
        assert f"RWL_{idx}" in out
        assert f"RBL_{idx}" in out
    for idx in range(5):
        assert f"CWL_{idx}" in out
        assert f"CBL_{idx}" in out
