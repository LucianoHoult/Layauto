"""
Calibre SVDB **Instance Cross Reference** ('iXref') parser.

The iXref artifact is produced by the Calibre executive module
command::

    INSTANCE XREF WRITE <path>

invoked inside ``calibre -query <svdb_dir>``. It is the
authoritative mapping between **schematic device names** (the
``M*`` instance names that appear in the source ``.cdl``) and
**SVDB-extracted device names** (the ``MMM*`` style names the
extractor minted while flattening the layout). LVS uses it to
prove that the matched netlists are really the same circuit; we
use it as the bridge that lets the dummy parser look up a
schematic-side device when the GDS / extractor side speaks a
different name.

Format (File format 1)::

    # SVDB: Instance Cross Reference (ixf) (File format 1)
    # SVDB: Layout Primary BUFLVT
    # SVDB: ... (other header lines)
    # SVDB: End of header.
    BUFLVT 6 BUFLVT 6
    0 M0 0 MMM3 X
    0 M1 0 MMM1
    0 M2 0 MMM0 X
    0 M3 0 MMM2

Header lines start with ``# SVDB:``. The first non-header line
is the *cell pair*: ``<layout_cell> <count_a> <source_cell>
<count_b>`` (in real iXref dumps the two counts are equal once
LVS clean; we surface both for diagnostic). Each remaining line
is one *instance pair*::

    <layout_lvl> <layout_name> <source_lvl> <source_name> [X]

The trailing ``X`` is a per-pair flag the extractor sets in
specific cases (in production it usually means "swapped /
permuted pin order during match"). The MVP doesn't act on it
yet, but we round-trip it so that downstream tooling has the
same field-set the production iXref carries.

Parsed-form (YAML/JSON middle file consumed by
``apply_lvs_overlay`` and any future LVS-feedback closure)::

    layout_cell:    BUFLVT
    source_cell:    BUFLVT
    layout_count:   6
    source_count:   6
    instances:
      - layout:  {level: 0, name: M0}
        source:  {level: 0, name: MMM3}
        flags:   [X]
      - layout:  {level: 0, name: M1}
        source:  {level: 0, name: MMM1}
        flags:   []
      ...
    by_source:    { MMM3: M0, MMM1: M1, MMM0: M2, MMM2: M3 }
    by_layout:    { M0: MMM3, M1: MMM1, M2: MMM0, M3: MMM2 }
    generated_ts: "20260507_113000"            # iso-ish; for audit
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

import yaml


HEADER_PREFIX = "# SVDB:"
HEADER_END    = "# SVDB: End of header."


@dataclass
class XrefInstance:
    """One ``<layout_lvl> <layout_name> <source_lvl> <source_name> [X]`` row."""
    layout_level: int
    layout_name:  str
    source_level: int
    source_name:  str
    flags:        List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            'layout': {'level': self.layout_level, 'name': self.layout_name},
            'source': {'level': self.source_level, 'name': self.source_name},
            'flags':  list(self.flags),
        }


@dataclass
class InstanceXref:
    """Parsed iXref artifact.

    Both directional indexes (``by_layout`` / ``by_source``) are
    pre-computed so callers don't have to scan the instance list.
    """
    layout_cell:    str
    source_cell:    str
    layout_count:   int
    source_count:   int
    instances:      List[XrefInstance] = field(default_factory=list)
    raw_header:     List[str]          = field(default_factory=list)
    source_path:    Optional[str]      = None
    generated_ts:   Optional[str]      = None

    @property
    def by_layout(self) -> Dict[str, str]:
        return {i.layout_name: i.source_name for i in self.instances}

    @property
    def by_source(self) -> Dict[str, str]:
        return {i.source_name: i.layout_name for i in self.instances}

    def to_dict(self) -> dict:
        return {
            'layout_cell':  self.layout_cell,
            'source_cell':  self.source_cell,
            'layout_count': self.layout_count,
            'source_count': self.source_count,
            'instances':    [i.to_dict() for i in self.instances],
            'by_layout':    self.by_layout,
            'by_source':    self.by_source,
            'raw_header':   list(self.raw_header),
            'source_path':  self.source_path,
            'generated_ts': self.generated_ts,
        }


# ----------------------------------------------------------------
# Parser
# ----------------------------------------------------------------
def parse_ixref(filepath: str) -> InstanceXref:
    """Parse an iXref.temp file into an ``InstanceXref``.

    Robust against:
      * blank lines and trailing whitespace,
      * extra header lines we don't recognise (preserved in
        ``raw_header`` for audit),
      * multiple flag tokens after the four required columns
        (each becomes one entry in ``flags``).

    Raises ``ValueError`` on a missing cell-pair line or on any
    instance row that has fewer than four columns — both signal
    a corrupt SVDB and should fail the pipeline loud.
    """
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"iXref file not found: {filepath}")

    raw_header: List[str] = []
    cell_line: Optional[str] = None
    instance_lines: List[str] = []

    with open(filepath) as f:
        in_header = True
        for raw in f:
            line = raw.rstrip('\n').rstrip()
            if not line:
                continue
            if in_header and line.startswith(HEADER_PREFIX):
                raw_header.append(line)
                if line.startswith(HEADER_END):
                    in_header = False
                continue
            # First non-header line is the cell pair.
            if cell_line is None:
                cell_line = line
                in_header = False
                continue
            instance_lines.append(line)

    if cell_line is None:
        raise ValueError(
            f"iXref {filepath!r}: no cell-pair line found after header"
        )

    cell_tokens = cell_line.split()
    if len(cell_tokens) < 4:
        raise ValueError(
            f"iXref {filepath!r}: cell-pair line malformed: {cell_line!r}"
        )
    try:
        layout_cell  = cell_tokens[0]
        layout_count = int(cell_tokens[1])
        source_cell  = cell_tokens[2]
        source_count = int(cell_tokens[3])
    except ValueError as e:
        raise ValueError(
            f"iXref {filepath!r}: cell-pair counts non-integer: {cell_line!r}"
        ) from e

    instances: List[XrefInstance] = []
    for ln, line in enumerate(instance_lines, start=1):
        tokens = line.split()
        if len(tokens) < 4:
            raise ValueError(
                f"iXref {filepath!r}: instance row #{ln} malformed: "
                f"{line!r} (expected ≥4 tokens)"
            )
        try:
            layout_level = int(tokens[0])
            source_level = int(tokens[2])
        except ValueError as e:
            raise ValueError(
                f"iXref {filepath!r}: instance row #{ln} non-integer "
                f"level: {line!r}"
            ) from e
        instances.append(XrefInstance(
            layout_level=layout_level,
            layout_name=tokens[1],
            source_level=source_level,
            source_name=tokens[3],
            flags=list(tokens[4:]),
        ))

    return InstanceXref(
        layout_cell=layout_cell,
        source_cell=source_cell,
        layout_count=layout_count,
        source_count=source_count,
        instances=instances,
        raw_header=raw_header,
        source_path=os.path.abspath(filepath),
        generated_ts=_file_mtime_stamp(filepath),
    )


def _file_mtime_stamp(filepath: str) -> str:
    ts = datetime.fromtimestamp(os.path.getmtime(filepath))
    return ts.strftime('%Y%m%d_%H%M%S')


# ----------------------------------------------------------------
# Middle-file emit
# ----------------------------------------------------------------
def write_xref_yaml(xref: InstanceXref, out_path: str) -> str:
    """Serialize the parsed xref to YAML (the consumed middle file).

    Returns the absolute path written. Creates parent dirs as
    needed; mirrors the JSON variant for callers who prefer it.
    """
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or '.',
                exist_ok=True)
    with open(out_path, 'w') as f:
        yaml.safe_dump(xref.to_dict(), f, sort_keys=False)
    return os.path.abspath(out_path)


def write_xref_json(xref: InstanceXref, out_path: str) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or '.',
                exist_ok=True)
    with open(out_path, 'w') as f:
        json.dump(xref.to_dict(), f, indent=2)
    return os.path.abspath(out_path)


def load_xref_yaml(path: str) -> InstanceXref:
    """Round-trip helper: re-hydrate an InstanceXref from the YAML."""
    with open(path) as f:
        d = yaml.safe_load(f)
    instances = [
        XrefInstance(
            layout_level=i['layout']['level'],
            layout_name=i['layout']['name'],
            source_level=i['source']['level'],
            source_name=i['source']['name'],
            flags=list(i.get('flags', [])),
        )
        for i in d.get('instances', [])
    ]
    return InstanceXref(
        layout_cell=d['layout_cell'],
        source_cell=d['source_cell'],
        layout_count=d['layout_count'],
        source_count=d['source_count'],
        instances=instances,
        raw_header=list(d.get('raw_header', [])),
        source_path=d.get('source_path'),
        generated_ts=d.get('generated_ts'),
    )


# ----------------------------------------------------------------
# Path-pattern expansion
# ----------------------------------------------------------------
def expand_ixref_pattern(pattern: str, *,
                          cell: str,
                          ts_format: str = '%Y%m%d_%H%M%S',
                          now: Optional[datetime] = None) -> str:
    """Expand ``{ts}`` / ``{cell}`` tokens in an iXref output pattern.

    Used by both the shell harness wrapper (when it passes
    ``--ixref-out`` to ``calibre_query_extract.sh``) and by
    Python tests that need a deterministic expansion.
    """
    now = now or datetime.now()
    ts  = now.strftime(ts_format)
    return pattern.format(ts=ts, cell=cell)


# ----------------------------------------------------------------
# CLI
# ----------------------------------------------------------------
def _build_arg_parser():
    import argparse
    p = argparse.ArgumentParser(
        description='Parse a Calibre iXref.temp into a YAML/JSON middle file.'
    )
    p.add_argument('ixref', help='Path to iXref.temp')
    p.add_argument('--yaml', dest='yaml_out', default=None,
                    help='Path to write YAML output')
    p.add_argument('--json', dest='json_out', default=None,
                    help='Path to write JSON output')
    return p


if __name__ == '__main__':
    args = _build_arg_parser().parse_args()
    xref = parse_ixref(args.ixref)
    print(f"Parsed iXref: {xref.layout_cell} ({xref.layout_count} instances)")
    print(f"  layout -> source pairs:")
    for inst in xref.instances:
        flag = (' ' + ' '.join(inst.flags)) if inst.flags else ''
        print(f"    {inst.layout_name:>8s} -> {inst.source_name}{flag}")
    if args.yaml_out:
        print(f"YAML written: {write_xref_yaml(xref, args.yaml_out)}")
    if args.json_out:
        print(f"JSON written: {write_xref_json(xref, args.json_out)}")
