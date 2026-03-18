"""Tests for hierarchical CDL parsing and netlist transformation behavior."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.cdl_parser import CDLParser
from core.config_parser import ConfigParser
from core.netlist_engine import NetlistEngine


BASE = Path(__file__).resolve().parents[1]


def _cfg():
    return ConfigParser(BASE / "configs").load_all()


def _raw_cdl() -> str:
    return (BASE / "inputs" / "dummy_4x4_array.cdl").read_text(encoding="utf-8")


def test_cdl_continuation_and_subckt_index():
    lines = CDLParser.merge_continuation_lines(_raw_cdl())
    target = [ln for ln in lines if ln.startswith("XCELL_R2_C1")][0]
    assert "+" not in target
    assert "NF=2" in target

    subckts = CDLParser.build_subckt_index(lines)
    assert "DRAM_BANK" in subckts
    assert "MAT" in subckts
    assert subckts["DRAMCELL"].ports[:4] == ["WL", "BL", "CSL", "LIO"]


def test_hierarchical_macro_prune_and_rewire():
    config = _cfg()
    logical = CDLParser.merge_continuation_lines(_raw_cdl())
    result = NetlistEngine(config).transform(logical)
    out = result.netlist

    # Macro-level pruning: unselected arrays are replaced with macro lumped loads.
    assert "XARRAY_0 WL BL CSL LIO VDD VSS ARRAY_SECTION" not in out
    assert "XARRAY_2 WL BL CSL LIO VDD VSS ARRAY_SECTION" not in out
    assert "CMACRO_XARRAY_0_0 WL 0" in out
    assert "IMACRO_XARRAY_2_1 BL 0 DC" in out

    # Target cell rewiring is port-aware and retains params.
    assert "XCELL_R2_C1 WL BL CSL LIO VDD VSS DRAMCELL W=1u NF=2" not in out
    assert "XCELL_R2_C1 XBANK.XMATRIX.XARRAY_1.XMAT_0.XCELL_R2_C1.WL_n2 XBANK.XMATRIX.XARRAY_1.XMAT_0.XCELL_R2_C1.BL_n3" in out
    assert "DRAMCELL W=1u NF=2" in out

    # Active-cross non-target cells are linearized to dummy caps and removed as instances.
    assert "XCELL_R2_C2 WL BL CSL LIO VDD VSS DRAMCELL W=1u" not in out
    assert "CGATE_DUMMY_XCELL_R2_C2" in out
    assert "XCELL_R3_C1 WL BL CSL LIO VDD VSS DRAMCELL W=1u" not in out
    assert "CJUNC_DUMMY_XCELL_R3_C1" in out

    # Multi-route hierarchical RC is injected (WL/BL/CSL/LIO).
    assert "RWL_0" in out and "RBL_0" in out and "RCSL_0" in out and "RLIO_0" in out
