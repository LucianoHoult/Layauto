"""Netlist transformation engine for hierarchical DRAM CDL workflows."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List

from core.cdl_parser import CDLParser, InstanceRecord, SubcktDef


@dataclass
class TransformResult:
    """Container for transformed netlist and key transformation metadata."""

    netlist: str
    removed_instances: List[str]
    rewired_target_instance: str


class NetlistEngine:
    """Perform macro pruning, active-target rewiring, and hierarchical RC injection."""

    def __init__(self, config: Dict):
        """Initialize the engine with merged DRAM_PathFinder configuration."""
        self.config = config
        self.array_cfg = config["array_topology"]
        self.tech_cfg = config["rc_constants"]
        self.precision = config["precision"]

    def transform(self, logical_lines: List[str]) -> TransformResult:
        """Transform a merged CDL netlist using hierarchical-aware rewrite rules."""
        subckts = CDLParser.build_subckt_index(logical_lines)
        if not subckts:
            raise ValueError("No .SUBCKT definitions were found in input netlist")

        removed: List[str] = []
        rewired_target = ""

        # Macro-level pruning is done in the configured container subckt only.
        macro_cfg = self.array_cfg["macro_pruning"]
        container_name = macro_cfg["container_subckt"]
        if container_name in subckts:
            body, removed_macro = self._apply_macro_pruning(subckts[container_name], subckts)
            subckts[container_name].body = body
            removed.extend(removed_macro)

        # Target cell rewrite + active-cross dummy linearization.
        cell_cfg = self.array_cfg["active_target"]
        cell_container = cell_cfg["cell_container_subckt"]
        if cell_container in subckts:
            body, removed_cells, rewired = self._rewrite_cells(subckts[cell_container], subckts)
            subckts[cell_container].body = body
            removed.extend(removed_cells)
            rewired_target = rewired

        # Re-assemble the full deck, preserving non-subckt top-level lines.
        top_level = self._top_level_non_subckt_lines(logical_lines)
        out_lines = self._render_subckts(subckts)
        out_lines.extend(top_level)
        out_lines.append("")
        out_lines.extend(self._inject_hierarchical_rc_models())

        return TransformResult(
            netlist="\n".join(out_lines).strip() + "\n",
            removed_instances=removed,
            rewired_target_instance=rewired_target,
        )

    def _apply_macro_pruning(self, container: SubcktDef, subckts: Dict[str, SubcktDef]) -> tuple[List[str], List[str]]:
        """Prune unselected macro instances and replace them with lumped macro loads."""
        cfg = self.array_cfg["macro_pruning"]
        active_macro = cfg["active_macro_instance"]
        patt = re.compile(cfg["macro_instance_pattern"])
        load_key = cfg["replacement_load"]
        load = self.config["static_loads"][load_key]

        new_body: List[str] = []
        removed: List[str] = []
        for line in container.body:
            rec = CDLParser.parse_instance_line(line, subckts)
            if not rec:
                new_body.append(line)
                continue

            if patt.match(rec.name) and rec.name != active_macro:
                removed.append(rec.name)
                new_body.append(f"* macro-pruned {rec.name}")
                for idx, node in enumerate(rec.nodes):
                    new_body.append(f"CMACRO_{rec.name}_{idx} {node} 0 {load['Cload']:.6e}")
                    new_body.append(f"IMACRO_{rec.name}_{idx} {node} 0 DC {load['Ileak']:.6e}")
                continue

            new_body.append(line)

        return new_body, removed

    def _rewrite_cells(self, container: SubcktDef, subckts: Dict[str, SubcktDef]) -> tuple[List[str], List[str], str]:
        """Rewire the configured target cell and linearize non-target active-cross cells."""
        cfg = self.array_cfg
        target = cfg["active_target"]
        patt = re.compile(cfg["cell_instance_pattern"])
        target_name = target["cell_instance_name"]
        dummy_caps = cfg["dummy_linear_caps"]

        routing_nodes = {
            r["port_name"]: self._segment_node_for_route(r) for r in cfg["routing_targets"]
        }

        new_body: List[str] = []
        removed: List[str] = []
        rewired_target = ""

        for line in container.body:
            rec = CDLParser.parse_instance_line(line, subckts)
            if not rec:
                new_body.append(line)
                continue

            if not patt.match(rec.name):
                new_body.append(line)
                continue

            m = patt.match(rec.name)
            row = int(m.group("row"))
            col = int(m.group("col"))
            active_row = target["row"]
            active_col = target["col"]

            if rec.name == target_name:
                # Port-aware rewiring based on DRAMCELL subckt pin names.
                subckt_ports = subckts[rec.subckt_name].ports if rec.subckt_name in subckts else []
                node_by_port = {p: rec.nodes[i] for i, p in enumerate(subckt_ports) if i < len(rec.nodes)}
                for port_name, new_node in routing_nodes.items():
                    if port_name in node_by_port:
                        node_by_port[port_name] = new_node
                rec.nodes = [node_by_port.get(p, rec.nodes[i]) if i < len(rec.nodes) else node_by_port.get(p, "0") for i, p in enumerate(subckt_ports[: len(rec.nodes)])]
                rewired_target = CDLParser.format_instance(rec)
                new_body.append(rewired_target)
                continue

            if row == active_row or col == active_col:
                removed.append(rec.name)
                new_body.append(f"* linearized active-cross dummy {rec.name}")
                if row == active_row and "WL" in routing_nodes:
                    new_body.append(f"CGATE_DUMMY_{rec.name} {routing_nodes['WL']} 0 {dummy_caps['wl_gate_cap']:.6e}")
                if col == active_col and "BL" in routing_nodes:
                    new_body.append(f"CJUNC_DUMMY_{rec.name} {routing_nodes['BL']} 0 {dummy_caps['bl_junc_cap']:.6e}")
                continue

            removed.append(rec.name)
            new_body.append(f"* removed inactive cell {rec.name}")

        return new_body, removed, rewired_target

    def _segment_node_for_route(self, route_cfg: Dict) -> str:
        """Map route physical index to a segment node honoring simulator hierarchy syntax."""
        segs = self.precision["pi_segments_per_wire"]
        total = route_cfg["total_count"]
        idx = route_cfg["active_index"]
        seg = int((idx + 1) * segs / total)
        seg = max(1, min(segs, seg))

        sep = "." if self.array_cfg.get("simulator_syntax", "dot") == "dot" else "/"
        base = self.array_cfg["active_target_hier_path"]

        if seg == segs:
            return route_cfg["endpoint_node"]
        return f"{base}{sep}{route_cfg['name']}_n{seg}"

    def _inject_hierarchical_rc_models(self) -> List[str]:
        """Emit distributed RC pi-model lines for all configured long routing targets."""
        segs = self.precision["pi_segments_per_wire"]
        lines: List[str] = ["* Hierarchical distributed RC models"]
        for route in self.array_cfg["routing_targets"]:
            rc = self.tech_cfg[route["rc_key"]]
            total_r = rc["R_per_um"] * route["length_um"]
            total_c = rc["C_per_um"] * route["length_um"]
            r_seg = total_r / segs
            c_seg = total_c / segs
            start = route["driver_node"]
            end = route["endpoint_node"]

            sep = "." if self.array_cfg.get("simulator_syntax", "dot") == "dot" else "/"
            base = self.array_cfg["active_target_hier_path"]
            nodes = [start] + [f"{base}{sep}{route['name']}_n{i}" for i in range(1, segs)] + [end]

            lines.append(f"* PI {route['name']} {start}->{end}")
            lines.append(f"C{route['name']}_0 {nodes[0]} 0 {c_seg/2:.6e}")
            for i in range(segs):
                lines.append(f"R{route['name']}_{i} {nodes[i]} {nodes[i+1]} {r_seg:.6e}")
                lines.append(f"C{route['name']}_{i+1} {nodes[i+1]} 0 {c_seg/2:.6e}")
        return lines

    @staticmethod
    def _render_subckts(subckts: Dict[str, SubcktDef]) -> List[str]:
        """Render subckt dictionary back into netlist lines."""
        lines: List[str] = []
        for name, defn in subckts.items():
            lines.append(f".SUBCKT {name} {' '.join(defn.ports)}".rstrip())
            lines.extend(defn.body)
            lines.append(f".ENDS {name}")
            lines.append("")
        return lines

    @staticmethod
    def _top_level_non_subckt_lines(logical_lines: List[str]) -> List[str]:
        """Extract top-level lines outside `.SUBCKT`/`.ENDS` scopes."""
        out: List[str] = []
        in_subckt = False
        for line in logical_lines:
            stripped = line.strip().upper()
            if stripped.startswith(".SUBCKT"):
                in_subckt = True
                continue
            if stripped.startswith(".ENDS"):
                in_subckt = False
                continue
            if not in_subckt:
                out.append(line)
        return out
