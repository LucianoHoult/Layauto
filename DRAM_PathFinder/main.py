"""Entry point for DRAM_PathFinder automation flow."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from core.cdl_parser import CDLParser
from core.config_parser import ConfigParser
from core.netlist_engine import NetlistEngine
from core.pwl_builder import PWLBuilder
from utils.file_io import create_run_directory, read_text, write_text
from utils.logger_setup import setup_logger


def build_driver_links(routing_targets: List[Dict[str, str]]) -> str:
    """Create ideal command-to-driver links for the generated RC ladders."""
    command_map = {"WL": "ACT_CMD", "BL": "READ_CMD", "CSL": "READ_CMD", "LIO": "READ_CMD"}
    lines = ["* Ideal command-to-driver links"]
    for route in routing_targets:
        command_node = command_map.get(route["port_name"])
        if not command_node:
            continue
        lines.append(
            f"E_{route['driver_node']} {route['driver_node']} 0 {command_node} 0 1"
        )
    return "\n".join(lines) + "\n"


def build_testbench(modified_netlist: str, stimulus: str, active_row: int, routing_targets: List[Dict[str, str]]) -> str:
    """Build top-level SPICE testbench text including measurements."""
    driver_links = build_driver_links(routing_targets)
    return (
        "* DRAM_PathFinder generated testbench\n"
        ".option post=2\n"
        ".param vdd=1.2\n\n"
        f"{modified_netlist}\n"
        f"{stimulus}\n"
        f"{driver_links}\n"
        ".tran 1p 40n\n"
        f".meas tran t_act_to_wl trig v(ACT_CMD) val='vdd/2' rise=1 targ v(wl_{active_row}) val='vdd/2' rise=1\n"
        ".end\n"
    )


def main() -> None:
    """Run the complete DRAM_PathFinder flow and persist all generated artifacts."""
    base = Path(__file__).resolve().parent
    run_dir = create_run_directory(base / "runs")
    logger = setup_logger(run_dir)

    logger.info("Run directory created: %s", run_dir)
    config = ConfigParser(base / "configs").load_all()
    logger.info("Loaded decoupled JSON configuration files")

    cdl_path = base / "inputs" / "dummy_4x4_array.cdl"
    raw_cdl = read_text(cdl_path)
    logical_lines = CDLParser.merge_continuation_lines(raw_cdl)
    logger.info("Merged CDL continuation lines: %d logical lines", len(logical_lines))

    engine = NetlistEngine(config)
    result = engine.transform(logical_lines)
    logger.info("Netlist transformed; removed/linearized instances: %d", len(result.removed_instances))

    stimulus = PWLBuilder().build(config)
    logger.info("PWL stimulus generated")

    active_row = config["array_topology"]["active_target"]["row"]
    routing_targets = config["array_topology"]["routing_targets"]
    tb = build_testbench(result.netlist, stimulus, active_row, routing_targets)

    write_text(run_dir / "modified_netlist.sp", result.netlist)
    write_text(run_dir / "stimulus.sp", stimulus)
    write_text(run_dir / "testbench.sp", tb)
    logger.info("Artifacts saved under %s", run_dir)


if __name__ == "__main__":
    main()
