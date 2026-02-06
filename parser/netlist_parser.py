"""Netlist parsing + hierarchical model utilities for SPICE/CDL-like text."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class BoundingBox:
    """Logic-unit bounds used for semantic zooming."""

    xmin: int = 0
    ymin: int = 0
    xmax: int = 0
    ymax: int = 0


@dataclass
class Instance:
    """Represents one parsed instance in a subcircuit."""

    name: str
    pins: list[str]
    cell_type: str
    # For hierarchical links resolved after parsing all subcircuits.
    subckt_ref: "SubCircuit | None" = None
    # UI-facing spatial and semantic metadata.
    bounds: BoundingBox = field(default_factory=BoundingBox)
    detail_level: int = 1
    is_collapsed: bool = True


@dataclass
class SubCircuit:
    """Represents one .SUBCKT / .ENDS block."""

    name: str
    ports: list[str]
    instances: list[Instance]
    bounds: BoundingBox = field(default_factory=BoundingBox)
    detail_level: int = 0
    is_collapsed: bool = False


def parse_subcircuits(netlist_text: str) -> dict[str, SubCircuit]:
    """Parse SPICE/CDL text into named hierarchical subcircuit objects.

    Supported syntax for current phases:
    - .SUBCKT <name> <ports...>
    - X* / x* subcircuit-style instances: Xname <pins...> <cell_type>
    - M* / m* transistor instances: Mname <d> <g> <s> <b> <model>
    - .ENDS
    """

    subckts: dict[str, SubCircuit] = {}
    current_name: str | None = None
    current_ports: list[str] = []
    current_instances: list[Instance] = []

    for raw_line in netlist_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("*"):
            continue

        tokens = line.split()
        head_upper = tokens[0].upper()

        if head_upper == ".SUBCKT":
            if len(tokens) < 2:
                raise ValueError(f"Invalid .SUBCKT line: {line}")
            current_name = tokens[1]
            current_ports = tokens[2:]
            current_instances = []
            continue

        if head_upper == ".ENDS":
            if current_name is None:
                raise ValueError(".ENDS found before any .SUBCKT")
            subckts[current_name] = SubCircuit(
                name=current_name,
                ports=current_ports,
                instances=current_instances,
            )
            current_name = None
            current_ports = []
            current_instances = []
            continue

        # SPICE/CDL is case-insensitive, so allow x*/X* and m*/M* prefixes.
        if tokens[0].upper().startswith(("X", "M")):
            if current_name is None:
                raise ValueError(f"Instance outside .SUBCKT: {line}")
            if len(tokens) < 3:
                raise ValueError(f"Invalid instance line: {line}")
            current_instances.append(
                Instance(name=tokens[0], pins=tokens[1:-1], cell_type=tokens[-1])
            )

    if current_name is not None:
        raise ValueError("Unterminated .SUBCKT block (missing .ENDS)")

    _resolve_hierarchy_links(subckts)
    return subckts


def _resolve_hierarchy_links(subckts: dict[str, SubCircuit]) -> None:
    """Resolve instance.subckt_ref when instance cell_type matches a known .SUBCKT."""

    lowered_map = {name.lower(): subckt for name, subckt in subckts.items()}
    for subckt in subckts.values():
        for inst in subckt.instances:
            inst.subckt_ref = lowered_map.get(inst.cell_type.lower())
            inst.detail_level = 1 if inst.subckt_ref else 2


def parse_subcircuits_file(path: str | Path) -> dict[str, SubCircuit]:
    """Load and parse netlist text from disk."""

    return parse_subcircuits(Path(path).read_text())
