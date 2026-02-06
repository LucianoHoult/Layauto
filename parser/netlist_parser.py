"""Netlist parsing utilities for SPICE/CDL-like instance lines."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Instance:
    """Represents one parsed instance in a subcircuit."""

    name: str
    pins: list[str]
    cell_type: str


@dataclass(frozen=True)
class SubCircuit:
    """Represents one .SUBCKT / .ENDS block."""

    name: str
    ports: list[str]
    instances: list[Instance]


def parse_subcircuits(netlist_text: str) -> dict[str, SubCircuit]:
    """Parse SPICE/CDL text into named subcircuit objects.

    Supported syntax for MVP:
    - .SUBCKT <name> <ports...>
    - X* instances: Xname <pins...> <cell_type>
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

        if tokens[0].startswith("X"):
            if current_name is None:
                raise ValueError(f"Instance outside .SUBCKT: {line}")
            if len(tokens) < 3:
                raise ValueError(f"Invalid instance line: {line}")
            current_instances.append(
                Instance(name=tokens[0], pins=tokens[1:-1], cell_type=tokens[-1])
            )

    if current_name is not None:
        raise ValueError("Unterminated .SUBCKT block (missing .ENDS)")

    return subckts


def parse_subcircuits_file(path: str | Path) -> dict[str, SubCircuit]:
    """Load and parse netlist text from disk."""

    return parse_subcircuits(Path(path).read_text())
