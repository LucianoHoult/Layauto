"""Logic depth levelization for parsed subcircuit instances."""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from parser.netlist_parser import SubCircuit


@dataclass(frozen=True)
class CellPinRole:
    """Defines which pin indexes are treated as inputs and output."""

    input_indexes: tuple[int, ...]
    output_index: int


DEFAULT_CELL_ROLES: dict[str, CellPinRole] = {
    # Simple digital abstraction for common standard cells.
    "INV": CellPinRole(input_indexes=(0,), output_index=1),
    "NAND2": CellPinRole(input_indexes=(0, 1), output_index=2),
    "NOR2": CellPinRole(input_indexes=(0, 1), output_index=2),
}


@dataclass(frozen=True)
class DepthResult:
    """Levelization output values used by later layout phases."""

    graph: nx.DiGraph
    instance_depths: dict[str, int]


def _resolve_pin_role(cell_type: str, pin_count: int) -> CellPinRole:
    """Resolve pin role by known library entry or a safe fallback.

    Fallback assumes all pins except the last are inputs and the final pin is output.
    """

    role = DEFAULT_CELL_ROLES.get(cell_type.upper())
    if role is not None:
        return role
    if pin_count < 2:
        raise ValueError(f"Cell {cell_type} needs at least 2 pins for fallback role")
    return CellPinRole(input_indexes=tuple(range(pin_count - 1)), output_index=pin_count - 1)


def build_instance_dag(subckt: SubCircuit) -> nx.DiGraph:
    """Build directed graph where edges indicate signal flow between instances."""

    graph = nx.DiGraph()
    for inst in subckt.instances:
        graph.add_node(inst.name, cell_type=inst.cell_type)

    net_drivers: dict[str, list[str]] = {}
    net_loads: dict[str, list[str]] = {}

    # Classify each pin as input/load or output/driver to infer directed connectivity.
    for inst in subckt.instances:
        role = _resolve_pin_role(inst.cell_type, len(inst.pins))
        out_pin = inst.pins[role.output_index]
        net_drivers.setdefault(out_pin, []).append(inst.name)

        for idx in role.input_indexes:
            net_loads.setdefault(inst.pins[idx], []).append(inst.name)

    # Create directed edges driver -> load for each net.
    for net, drivers in net_drivers.items():
        loads = net_loads.get(net, [])
        for src in drivers:
            for dst in loads:
                if src != dst:
                    graph.add_edge(src, dst, net=net)

    return graph


def calculate_logic_depth(subckt: SubCircuit, primary_input_nets: set[str] | None = None) -> DepthResult:
    """Compute logic depth X-levels for each instance in DAG order.

    Depth rule: X_i = max(X_inputs) + 1, with primary inputs anchored at level 0.
    """

    graph = build_instance_dag(subckt)

    if not nx.is_directed_acyclic_graph(graph):
        cycle = nx.find_cycle(graph)
        raise ValueError(f"Feedback loop found in MVP depth engine: {cycle}")

    primary_inputs = primary_input_nets or set(subckt.ports)
    depths: dict[str, int] = {}

    for node in nx.topological_sort(graph):
        inst = next(i for i in subckt.instances if i.name == node)
        role = _resolve_pin_role(inst.cell_type, len(inst.pins))

        predecessor_depths: list[int] = []
        for idx in role.input_indexes:
            in_net = inst.pins[idx]
            # Nets from module primary inputs start at logic level 0.
            if in_net in primary_inputs:
                predecessor_depths.append(0)
                continue
            incoming_edges = [u for u, _, d in graph.in_edges(node, data=True) if d.get("net") == in_net]
            predecessor_depths.extend(depths[u] for u in incoming_edges)

        depths[node] = (max(predecessor_depths) if predecessor_depths else 0) + 1

    return DepthResult(graph=graph, instance_depths=depths)
