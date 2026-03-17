"""CDL parser helpers for robust line-level manipulation."""

from __future__ import annotations

from pathlib import Path
from typing import List


class CDLParser:
    """Parse raw CDL while resolving SPICE/CDL line continuations."""

    @staticmethod
    def merge_continuation_lines(raw_text: str) -> List[str]:
        """Merge lines starting with ``+`` into the previous logical line.

        The continuation marker may be ``+`` or ``+ ``. Leading spaces are tolerated.
        """
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
        """Load a CDL file and return logical lines with continuations merged."""
        text = Path(cdl_path).read_text(encoding="utf-8")
        return cls.merge_continuation_lines(text)
