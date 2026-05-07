"""
Calibre LVS query stage.

Two run modes (selected via ``site_config.calibre.mode`` or the
``--lvs-mode`` CLI flag on ``pipeline/run_mvp.py``):

  * ``dummy``   — copy a pre-staged ``dummy/fixtures/iXref.temp`` into
                  the run-output ``iXref.temp`` path. No subprocess.
                  Used by the default pipeline run and the test suite.
  * ``calibre`` — spawn ``calibre -query <svdb_dir>`` and stream the
                  HDB query commands ``INSTANCE XREF WRITE <path>`` +
                  ``EXIT`` over stdin. Production-only. Captures
                  stdout/stderr; raises informative errors for
                  missing binary / non-zero exit / missing output.

Either way, the resulting ``iXref.temp`` file is parsed into a
structured dict and written as a YAML middle file (``ixref.yaml``).
The middle file is "saved for later use" — Stage 2's
``build_layout_model`` does not consume it today. The seam exists so
M7's LVS feedback closure (net-equivalence overrides for swapped
S/D, layout-vs-source device-identity reconciliation) can wire it in
without touching the dummy path or the parser.

Format reference (Calibre HDB ``INSTANCE XREF`` file format 1):

    # SVDB: Instance Cross Reference (ixf) (File format 1)
    # SVDB: Layout Primary INV_N5_P7
    # SVDB: ...
    # SVDB: End of header.
    INV_N5_P7 4 INV_N5_P7 4
    0 M0 0 MN0
    0 M1 0 MP0 X

Header lines start with ``# SVDB:`` and terminate with
``# SVDB: End of header.``. The first body line is the cell summary
(``<layout_cell> <layout_pin_count> <source_cell> <source_pin_count>``).
Each subsequent line is one device row:
``<layout_idx> <layout_inst> <source_idx> <source_inst> [X]``;
trailing ``X`` flags an LVS-detected S/D swap (MOS only).
"""

import os
import shutil
import subprocess
from typing import Optional

import yaml


_HEADER_END = '# SVDB: End of header.'


# =====================================================================
# Parser
# =====================================================================

def parse_ixref(filepath: str) -> dict:
    """Parse an iXref.temp file into a structured dict.

    Returns:
        {
          'cell': {
            'layout_name': str,
            'source_name': str,
            'layout_pin_count': int,
            'source_pin_count': int,
          },
          'devices': [
            {'layout_idx': int,
             'layout_inst': str,
             'source_idx': int,
             'source_inst': str,
             'sd_swapped': bool},
            ...
          ],
          'header_lines': [str, ...],   # raw header lines, preserved
        }

    Raises:
        FileNotFoundError: if ``filepath`` does not exist.
        ValueError: on malformed header / cell / device rows.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"iXref file not found: {filepath!r}")

    with open(filepath) as f:
        lines = [ln.rstrip('\n') for ln in f]

    # Walk header until "End of header." sentinel.
    header_lines = []
    header_end_idx = None
    for i, ln in enumerate(lines):
        header_lines.append(ln)
        if ln.strip() == _HEADER_END:
            header_end_idx = i
            break
    if header_end_idx is None:
        raise ValueError(
            f"iXref {filepath!r}: missing required terminator "
            f"{_HEADER_END!r}"
        )

    body = [ln for ln in lines[header_end_idx + 1:]
            if ln.strip() and not ln.lstrip().startswith('#')]
    if not body:
        raise ValueError(
            f"iXref {filepath!r}: body is empty after header"
        )

    # Cell summary: <layout_cell> <layout_pin_count>
    #               <source_cell> <source_pin_count>
    summary_tokens = body[0].split()
    if len(summary_tokens) != 4:
        raise ValueError(
            f"iXref {filepath!r}: cell-summary line malformed: "
            f"{body[0]!r} (expected 4 tokens, got {len(summary_tokens)})"
        )
    try:
        cell = {
            'layout_name':       summary_tokens[0],
            'layout_pin_count':  int(summary_tokens[1]),
            'source_name':       summary_tokens[2],
            'source_pin_count':  int(summary_tokens[3]),
        }
    except ValueError as e:
        raise ValueError(
            f"iXref {filepath!r}: cell-summary pin counts not int: "
            f"{body[0]!r}"
        ) from e

    devices = []
    for raw in body[1:]:
        tokens = raw.split()
        # <layout_idx> <layout_inst> <source_idx> <source_inst> [X]
        if len(tokens) not in (4, 5):
            raise ValueError(
                f"iXref {filepath!r}: device row malformed: {raw!r} "
                f"(expected 4 or 5 tokens, got {len(tokens)})"
            )
        if len(tokens) == 5 and tokens[4].upper() != 'X':
            raise ValueError(
                f"iXref {filepath!r}: device row 5th token is "
                f"{tokens[4]!r}; expected 'X' (S/D swap marker)"
            )
        try:
            layout_idx = int(tokens[0])
            source_idx = int(tokens[2])
        except ValueError as e:
            raise ValueError(
                f"iXref {filepath!r}: device row index not int: {raw!r}"
            ) from e
        devices.append({
            'layout_idx':  layout_idx,
            'layout_inst': tokens[1],
            'source_idx':  source_idx,
            'source_inst': tokens[3],
            'sd_swapped':  len(tokens) == 5,
        })

    # Reorder cell keys for stable YAML output
    cell_ordered = {
        'layout_name':       cell['layout_name'],
        'source_name':       cell['source_name'],
        'layout_pin_count':  cell['layout_pin_count'],
        'source_pin_count':  cell['source_pin_count'],
    }

    return {
        'cell':         cell_ordered,
        'devices':      devices,
        'header_lines': header_lines,
    }


# =====================================================================
# YAML middle-file writer
# =====================================================================

def write_ixref_yaml(parsed: dict, out_path: str) -> None:
    """Persist a parsed iXref dict as YAML.

    Stable key ordering (cell first, then devices, then header_lines)
    so the file is diffable across runs.
    """
    out_dir = os.path.dirname(os.path.abspath(out_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(out_path, 'w') as f:
        yaml.safe_dump(parsed, f, sort_keys=False, default_flow_style=False)


# =====================================================================
# Subprocess runner
# =====================================================================

class CalibreNotFoundError(FileNotFoundError):
    """Raised when the ``calibre`` binary cannot be found on PATH."""


class CalibreQueryError(RuntimeError):
    """Raised when ``calibre -query`` fails or produces no output."""


def run_calibre_ixref(svdb_dir: str,
                      ixref_path: str,
                      *,
                      timeout: float = 300.0,
                      calibre_bin: str = 'calibre') -> None:
    """Spawn ``calibre -query <svdb_dir>`` and write iXref to ``ixref_path``.

    The subprocess receives the following commands on stdin:

        INSTANCE XREF WRITE <ixref_path>
        EXIT

    Captures stdout/stderr; on timeout, non-zero exit, or missing
    output file, raises ``CalibreQueryError`` with the captured streams
    in the message. Pre-spawn, raises ``CalibreNotFoundError`` if
    ``shutil.which(calibre_bin)`` returns ``None``.
    """
    if shutil.which(calibre_bin) is None:
        raise CalibreNotFoundError(
            f"Calibre binary {calibre_bin!r} not found on PATH. "
            f"For dummy mode, pass --lvs-mode=dummy or set "
            f"calibre.mode=dummy in site_config.yaml."
        )
    if not os.path.isdir(svdb_dir):
        raise CalibreQueryError(
            f"SVDB directory not found: {svdb_dir!r}"
        )

    cmds = (
        f"INSTANCE XREF WRITE {ixref_path}\n"
        f"EXIT\n"
    )
    try:
        result = subprocess.run(
            [calibre_bin, '-query', svdb_dir],
            input=cmds,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        raise CalibreQueryError(
            f"calibre -query {svdb_dir!r} timed out after {timeout}s"
        ) from e

    if result.returncode != 0:
        raise CalibreQueryError(
            f"calibre -query {svdb_dir!r} exited {result.returncode}\n"
            f"--- stdout ---\n{result.stdout}\n"
            f"--- stderr ---\n{result.stderr}"
        )
    if not os.path.exists(ixref_path):
        raise CalibreQueryError(
            f"calibre -query {svdb_dir!r} completed but did not "
            f"produce {ixref_path!r}.\n"
            f"--- stdout ---\n{result.stdout}\n"
            f"--- stderr ---\n{result.stderr}"
        )


def run_dummy_ixref(svdb_dir: Optional[str],
                    ixref_path: str,
                    dummy_source: str) -> None:
    """Stage the dummy iXref.temp at ``ixref_path``.

    ``svdb_dir`` is ignored (kept for API symmetry with
    ``run_calibre_ixref``). If ``dummy_source == ixref_path``, this is
    a no-op (the file is already where the rest of the flow expects).
    Otherwise copies via ``shutil.copyfile``.
    """
    if not os.path.exists(dummy_source):
        raise FileNotFoundError(
            f"Dummy iXref source not found: {dummy_source!r}"
        )
    abs_src = os.path.abspath(dummy_source)
    abs_dst = os.path.abspath(ixref_path)
    if abs_src == abs_dst:
        return
    out_dir = os.path.dirname(abs_dst)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    shutil.copyfile(abs_src, abs_dst)


# =====================================================================
# Top-level orchestrator
# =====================================================================

def extract_ixref(*,
                  mode: str,
                  svdb_dir: Optional[str],
                  ixref_path: str,
                  dummy_source: Optional[str] = None,
                  timeout: float = 300.0,
                  calibre_bin: str = 'calibre') -> dict:
    """Run the LVS query stage end to end.

    Dispatches to ``run_dummy_ixref`` or ``run_calibre_ixref`` to
    populate ``ixref_path``, then parses the file and returns the
    parsed dict. The caller is responsible for calling
    ``write_ixref_yaml`` if a YAML middle file is wanted.

    Args:
        mode: 'dummy' or 'calibre'.
        svdb_dir: Required for 'calibre' mode. Ignored in 'dummy'.
        ixref_path: Where the raw iXref.temp lives after this call.
            In 'calibre' mode, calibre writes here. In 'dummy' mode,
            the dummy fixture is copied here.
        dummy_source: Required for 'dummy' mode. Path to the staged
            dummy iXref.temp fixture (committed in dummy/fixtures/).
        timeout: subprocess timeout in seconds (calibre mode only).
        calibre_bin: name of the Calibre binary on PATH ('calibre').

    Returns:
        The parsed iXref dict (see ``parse_ixref``).
    """
    if mode == 'dummy':
        if dummy_source is None:
            raise ValueError(
                "extract_ixref(mode='dummy') requires dummy_source"
            )
        run_dummy_ixref(svdb_dir, ixref_path, dummy_source)
    elif mode == 'calibre':
        if svdb_dir is None:
            raise ValueError(
                "extract_ixref(mode='calibre') requires svdb_dir"
            )
        run_calibre_ixref(
            svdb_dir, ixref_path,
            timeout=timeout, calibre_bin=calibre_bin,
        )
    else:
        raise ValueError(
            f"extract_ixref: unknown mode {mode!r} "
            f"(expected 'dummy' or 'calibre')"
        )

    return parse_ixref(ixref_path)
