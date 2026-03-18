"""CDL parser helpers with continuation handling and subcircuit scope awareness."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class SubcktDef:
    """Lightweight representation of one `.SUBCKT` definition."""

    name: str
    ports: List[str]
    body: List[str]


@dataclass
class InstanceRecord:
    """Structured representation of an instance line.

    Attributes preserve the original optional parameter/value suffix so rewiring
    can change only node connectivity without disturbing model parameters.
    """

    name: str
    nodes: List[str]
    subckt_name: str
    params: List[str]
    raw_line: str


class CDLParser:
    """Parse raw CDL while resolving line continuations and subckt scopes."""

    @staticmethod
    def merge_continuation_lines(raw_text: str) -> List[str]:
        """Merge lines starting with `+` into the previous logical line."""
        merged: List[str] = []
        for raw in raw_text.splitlines():
            stripped = raw.lstrip()
            if stripped.startswith("+"):
                if not merged:
                    continue
                cont = stripped[1:].strip()
                if cont:
                    merged[-1] = f"{merged[-1]} {cont}".strip()
                continue
            merged.append(raw.rstrip())
        return merged

    @classmethod
    def load_and_merge(cls, cdl_path: str | Path) -> List[str]:
        """Load a CDL file and return merged logical lines."""
        text = Path(cdl_path).read_text(encoding="utf-8")
        return cls.merge_continuation_lines(text)

    @staticmethod
    def build_subckt_index(logical_lines: List[str]) -> Dict[str, SubcktDef]:
        """Build `{subckt_name: SubcktDef}` dictionary from logical lines."""
        subckts: Dict[str, SubcktDef] = {}
        current_name: Optional[str] = None
        current_ports: List[str] = []
        current_body: List[str] = []

        for line in logical_lines:
            stripped = line.strip()
            if not stripped:
                if current_name is not None:
                    current_body.append(line)
                continue

            upper = stripped.upper()
            if upper.startswith(".SUBCKT"):
                toks = stripped.split()
                if len(toks) < 2:
                    continue
                current_name = toks[1]
                current_ports = toks[2:]
                current_body = []
                continue

            if upper.startswith(".ENDS") and current_name is not None:
                subckts[current_name] = SubcktDef(
                    name=current_name,
                    ports=current_ports.copy(),
                    body=current_body.copy(),
                )
                current_name = None
                current_ports = []
                current_body = []
                continue

            if current_name is not None:
                current_body.append(line)

        return subckts

    @staticmethod
    def parse_instance_line(line: str, known_subckts: Optional[Dict[str, SubcktDef]] = None) -> Optional[InstanceRecord]:
        """Parse an instance line into structured tokens.

        The parser finds the subckt token by scanning from right to left,
        preferring known subckt names; otherwise it chooses the token before the
        first parameter assignment token (`key=value`).
        """
        stripped = line.strip()
        if not stripped or stripped.startswith("*") or stripped.startswith("."):
            return None

        toks = stripped.split()
        if not toks or not toks[0].startswith("X"):
            return None

        subckt_idx: Optional[int] = None
        if known_subckts:
            for i in range(len(toks) - 1, 0, -1):
                if toks[i] in known_subckts:
                    subckt_idx = i
                    break

        if subckt_idx is None:
            first_param = next((i for i, t in enumerate(toks) if "=" in t), len(toks))
            subckt_idx = first_param - 1

        if subckt_idx <= 1:
            return None

        return InstanceRecord(
            name=toks[0],
            nodes=toks[1:subckt_idx],
            subckt_name=toks[subckt_idx],
            params=toks[subckt_idx + 1 :],
            raw_line=line,
        )

    @staticmethod
    def format_instance(rec: InstanceRecord) -> str:
        """Reconstruct an instance line preserving parameter suffix ordering."""
        parts = [rec.name, *rec.nodes, rec.subckt_name, *rec.params]
        return " ".join(parts)
