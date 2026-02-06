"""Channel-Connected Component (CCC) analyzer for transistor-level circuits."""

from __future__ import annotations

from dataclasses import dataclass

from parser.netlist_parser import Instance, SubCircuit


@dataclass(frozen=True)
class CCCNode:
    id: str
    members: tuple[str, ...]


def _is_transistor(inst: Instance) -> bool:
    return inst.name.upper().startswith("M")


def _ds_nets(inst: Instance) -> tuple[str, str]:
    # SPICE MOS convention: D, G, S, B, MODEL
    if len(inst.pins) < 3:
        raise ValueError(f"Transistor {inst.name} must have at least D/G/S pins")
    return inst.pins[0], inst.pins[2]


def group_ccc(subckt: SubCircuit) -> list[CCCNode]:
    """Group transistors into CCCs by source/drain connectivity."""

    tx = [i for i in subckt.instances if _is_transistor(i)]
    if not tx:
        return []

    parent: dict[str, str] = {t.name: t.name for t in tx}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    by_net: dict[str, list[str]] = {}
    for t in tx:
        d, s = _ds_nets(t)
        by_net.setdefault(d, []).append(t.name)
        by_net.setdefault(s, []).append(t.name)

    for members in by_net.values():
        if len(members) > 1:
            root = members[0]
            for m in members[1:]:
                union(root, m)

    groups: dict[str, list[str]] = {}
    for t in tx:
        groups.setdefault(find(t.name), []).append(t.name)

    out: list[CCCNode] = []
    for idx, members in enumerate(sorted(groups.values(), key=lambda m: sorted(m)[0])):
        out.append(CCCNode(id=f"CCC{idx}", members=tuple(sorted(members))))
    return out
