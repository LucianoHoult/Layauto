"""Logic depth, loop handling, and frontend JSON export."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import networkx as nx

from layout.ccc_analyzer import group_ccc
from parser.netlist_parser import BoundingBox, Instance, SubCircuit


@dataclass(frozen=True)
class CellPinRole:
    input_indexes: tuple[int, ...]
    output_index: int


DEFAULT_CELL_ROLES: dict[str, CellPinRole] = {
    "INV": CellPinRole(input_indexes=(0,), output_index=1),
    "NAND2": CellPinRole(input_indexes=(0, 1), output_index=2),
    "NOR2": CellPinRole(input_indexes=(0, 1), output_index=2),
}


@dataclass(frozen=True)
class FeedbackEdge:
    src: str
    dst: str
    net: str
    is_feedback: bool = True


@dataclass(frozen=True)
class DepthResult:
    graph: nx.DiGraph
    instance_depths: dict[str, int]
    y_index: dict[str, int]
    feedback_edges: list[FeedbackEdge]

    def to_frontend_json(self, subckt: SubCircuit) -> dict:
        """Export frontend-ready JSON with id/type/x/y/parent/pin roles/feedbacks."""

        nodes = []
        for inst in subckt.instances:
            pins = []
            role = _resolve_pin_role(inst)
            for i, net in enumerate(inst.pins):
                if i == role.output_index:
                    pin_role = "Driver"
                elif i in role.input_indexes:
                    pin_role = "Load"
                else:
                    pin_role = "Load"
                pins.append({"name": net, "role": pin_role})

            node = {
                "id": inst.name,
                "type": "subckt" if inst.subckt_ref else ("transistor" if inst.name.upper().startswith("M") else "cell"),
                "x": self.instance_depths.get(inst.name, 0),
                "y": self.y_index.get(inst.name, 0),
                "parent_module": subckt.name,
                "pins": pins,
                "bounds": asdict(inst.bounds),
                "detail_level": inst.detail_level,
                "is_collapsed": inst.is_collapsed,
            }
            nodes.append(node)

        return {
            "module": subckt.name,
            "nodes": nodes,
            "feedback_edges": [asdict(e) for e in self.feedback_edges],
        }


def _is_transistor(inst: Instance) -> bool:
    return inst.name.upper().startswith("M")


def _is_transmission_gate(inst: Instance) -> bool:
    ct = inst.cell_type.lower()
    nm = inst.name.lower()
    return "tg" in ct or "pass" in ct or nm.startswith("mtg")


def _resolve_pin_role(inst: Instance) -> CellPinRole:
    if _is_transistor(inst):
        # D G S [B] ; logical influence enters via gate, output taken at D/S channel node.
        return CellPinRole(input_indexes=(1,), output_index=0)

    role = DEFAULT_CELL_ROLES.get(inst.cell_type.upper())
    if role is not None:
        return role

    if len(inst.pins) < 2:
        raise ValueError(f"Cell {inst.cell_type} needs at least 2 pins")
    return CellPinRole(input_indexes=tuple(range(len(inst.pins) - 1)), output_index=len(inst.pins) - 1)


def _instance_latency(inst: Instance) -> int:
    if inst.subckt_ref is None:
        return 1
    # Hierarchical leveling: use internal critical path length.
    internal = calculate_logic_depth(inst.subckt_ref)
    return max(internal.instance_depths.values(), default=1)


def build_instance_dag(
    subckt: SubCircuit,
    *,
    tg_transparent: bool = False,
) -> tuple[nx.DiGraph, list[FeedbackEdge]]:
    """Build graph with feedback-edge marking and optional TG transparency."""

    graph = nx.DiGraph()
    for inst in subckt.instances:
        graph.add_node(inst.name, cell_type=inst.cell_type)

    net_drivers: dict[str, list[str]] = {}
    net_loads: dict[str, list[str]] = {}

    # CCC grouping is computed now and available for downstream usage/inspection.
    _ = group_ccc(subckt)

    for inst in subckt.instances:
        role = _resolve_pin_role(inst)
        if _is_transistor(inst):
            # For transistor-level depth, only gate terminal increments stage.
            # Treat gate as load; D/S as pass-channel points (drivers).
            gate_net = inst.pins[1]
            net_loads.setdefault(gate_net, []).append(inst.name)
            d_net = inst.pins[0]
            s_net = inst.pins[2]
            if tg_transparent and _is_transmission_gate(inst):
                # Transparent TG can be bypassed in staging with zero-latency treatment.
                graph.nodes[inst.name]["latency"] = 0
            else:
                graph.nodes[inst.name]["latency"] = 1
            net_drivers.setdefault(d_net, []).append(inst.name)
            net_drivers.setdefault(s_net, []).append(inst.name)
            continue

        out_pin = inst.pins[role.output_index]
        net_drivers.setdefault(out_pin, []).append(inst.name)
        for idx in role.input_indexes:
            net_loads.setdefault(inst.pins[idx], []).append(inst.name)
        graph.nodes[inst.name]["latency"] = _instance_latency(inst)

    for net, drivers in net_drivers.items():
        for src in drivers:
            for dst in net_loads.get(net, []):
                if src != dst:
                    graph.add_edge(src, dst, net=net, is_feedback=False)

    feedback_edges: list[FeedbackEdge] = []
    dag = graph.copy()
    # Break back-edges iteratively and mark them as feedback for UI.
    while not nx.is_directed_acyclic_graph(dag):
        cycle = nx.find_cycle(dag)
        removed = False
        for src, dst in cycle:
            net = dag.edges[src, dst].get("net", "")
            # Prefer edges that feed transistor gate terminals.
            dst_inst = next((i for i in subckt.instances if i.name == dst), None)
            if dst_inst and _is_transistor(dst_inst) and len(dst_inst.pins) > 1 and dst_inst.pins[1] == net:
                feedback_edges.append(FeedbackEdge(src=src, dst=dst, net=net))
                dag.remove_edge(src, dst)
                removed = True
                break
        if removed:
            continue
        # Fallback: remove first edge in cycle.
        src, dst = cycle[0]
        net = dag.edges[src, dst].get("net", "")
        feedback_edges.append(FeedbackEdge(src=src, dst=dst, net=net))
        dag.remove_edge(src, dst)

    return dag, feedback_edges


def calculate_logic_depth(
    subckt: SubCircuit,
    primary_input_nets: set[str] | None = None,
    *,
    tg_transparent: bool = False,
) -> DepthResult:
    """Compute X-depth with loop handling and Y stacking."""

    graph, feedback_edges = build_instance_dag(subckt, tg_transparent=tg_transparent)
    primary_inputs = set(subckt.ports) if primary_input_nets is None else set(primary_input_nets)

    depths: dict[str, int] = {}
    y_index: dict[str, int] = {}
    stage_count: dict[int, int] = {}

    inst_map = {i.name: i for i in subckt.instances}

    for node in nx.topological_sort(graph):
        inst = inst_map[node]
        role = _resolve_pin_role(inst)

        predecessor_depths: list[int] = []
        for idx in role.input_indexes:
            in_net = inst.pins[idx]
            if in_net in primary_inputs:
                predecessor_depths.append(0)
                continue
            incoming = [u for u, _, d in graph.in_edges(node, data=True) if d.get("net") == in_net]
            predecessor_depths.extend(depths[u] for u in incoming)

        base = max(predecessor_depths) if predecessor_depths else 0
        latency = graph.nodes[node].get("latency", 1)
        depths[node] = base + latency

        stage = depths[node]
        y_index[node] = stage_count.get(stage, 0)
        stage_count[stage] = y_index[node] + 1

    # Bottom-up bounds per instance + module bounds.
    max_x = max(depths.values(), default=0)
    max_y = max(y_index.values(), default=0)
    for inst in subckt.instances:
        x = depths.get(inst.name, 0)
        y = y_index.get(inst.name, 0)
        inst.bounds = BoundingBox(xmin=x, ymin=y, xmax=x + 1, ymax=y + 1)
    subckt.bounds = BoundingBox(xmin=0, ymin=0, xmax=max_x + 1, ymax=max_y + 1)

    return DepthResult(graph=graph, instance_depths=depths, y_index=y_index, feedback_edges=feedback_edges)
