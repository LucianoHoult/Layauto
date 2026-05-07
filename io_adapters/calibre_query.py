"""
Calibre LVS query stage.

Two run modes (selected via ``site_config.calibre.mode`` or the
``--lvs-mode`` CLI flag on ``pipeline/run_mvp.py``):

  * ``dummy``   — copy a pre-staged ``dummy/fixtures/iXref.temp`` (and
                  its sibling ``nXref.temp`` / ``net_names.txt``) into
                  the run-output paths. No subprocess. Used by the
                  default pipeline run and the test suite.
  * ``calibre`` — spawn ``calibre -query <svdb_dir>`` and stream the
                  HDB query commands ``INSTANCE XREF WRITE <path>`` /
                  ``NET XREF WRITE <path>`` / ``NET NAMES`` + ``EXIT``
                  over stdin. Production-only. Captures stdout/stderr;
                  raises informative errors for missing binary /
                  non-zero exit / missing output.

Three queries land middle files for "later use" by Stage 2:

  * ``ixref.yaml``     — device cross-reference (M0 ↔ MN0, …)
  * ``net_xref.yaml``  — joined net cross-reference + LVS index
                         (schematic_name → lvs_name → lvs_index)

Stage 2's ``build_layout_model`` does not consume the YAMLs today;
the seam exists so M7's LVS feedback closure can wire them in
without touching the dummy path or the parsers.

Format reference:

  iXref.temp (file format 1 — ``INSTANCE XREF``):

    # SVDB: Instance Cross Reference (ixf) (File format 1)
    # SVDB: Layout Primary INV_N5_P7
    # SVDB: ...
    # SVDB: End of header.
    INV_N5_P7 4 INV_N5_P7 4
    0 M0 0 MN0
    0 M1 0 MP0 X

  nXref.temp (file format 1 — ``NET XREF``):

    # SVDB: Net Cross Reference (nxf) (File format 1)
    # SVDB: ...
    # SVDB: End of header.
    % INV_N5_P7 4 INV_N5_P7 4
    0 VDD 0 VDD
    0 IN  0 IN
    0 2   0 net9            <- LVS renumbered an unnamed schematic net

  NET NAMES output (stdout-only; Calibre never writes a file for this):

    Net_Names 20000
    Nets:
    0 0 4 May 07 03:00:00 2026
    IN
    OUT
    VSS
    VDD
    END OF RESPONSE

  Net rows are 1-indexed: position 1 → IN, position 2 → OUT, …

Header lines for the ``XREF`` files start with ``# SVDB:`` and
terminate with ``# SVDB: End of header.``. nXref's cell-summary line
carries a leading ``%`` (per Calibre file format 1); iXref's does
not. Net rows mirror device rows:
``<layout_idx> <layout_net> <source_idx> <source_net>``.
"""

import os
import re
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

    Any pre-existing file at ``ixref_path`` is removed before the
    subprocess runs so the post-spawn existence check actually
    verifies that *this* invocation wrote the file (Calibre is known
    to exit 0 without rewriting on query-version mismatch or silently
    ignored output paths).
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

    if os.path.exists(ixref_path):
        os.remove(ixref_path)

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


# =====================================================================
# nXref parser (NET XREF WRITE)
# =====================================================================

def parse_nxref(filepath: str) -> dict:
    """Parse an nXref.temp file (Calibre HDB ``NET XREF`` output).

    Returns:
        {
          'cell': {
            'layout_name': str,
            'source_name': str,
            'layout_pin_count': int,
            'source_pin_count': int,
          },
          'nets': [
            {'layout_idx': int,
             'layout_net': str,
             'source_idx': int,
             'source_net': str},
            ...
          ],
          'header_lines': [str, ...],
        }

    The cell-summary line carries a leading ``%`` per Calibre file
    format 1 (e.g. ``% INV_N5_P7 4 INV_N5_P7 4``); the parser strips
    it. Each subsequent row is one net mapping
    ``<layout_idx> <layout_net> <source_idx> <source_net>``.

    Raises:
        FileNotFoundError: if ``filepath`` does not exist.
        ValueError: on malformed header / cell / net rows.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"nXref file not found: {filepath!r}")

    with open(filepath) as f:
        lines = [ln.rstrip('\n') for ln in f]

    header_lines = []
    header_end_idx = None
    for i, ln in enumerate(lines):
        header_lines.append(ln)
        if ln.strip() == _HEADER_END:
            header_end_idx = i
            break
    if header_end_idx is None:
        raise ValueError(
            f"nXref {filepath!r}: missing required terminator "
            f"{_HEADER_END!r}"
        )

    body = [ln for ln in lines[header_end_idx + 1:]
            if ln.strip() and not ln.lstrip().startswith('#')]
    if not body:
        raise ValueError(
            f"nXref {filepath!r}: body is empty after header"
        )

    # Cell summary: ``% <layout_cell> <layout_pin_count>
    #                  <source_cell> <source_pin_count>``
    summary_raw = body[0].lstrip()
    if summary_raw.startswith('%'):
        summary_raw = summary_raw[1:].strip()
    summary_tokens = summary_raw.split()
    if len(summary_tokens) != 4:
        raise ValueError(
            f"nXref {filepath!r}: cell-summary line malformed: "
            f"{body[0]!r} (expected 4 tokens after optional '%', "
            f"got {len(summary_tokens)})"
        )
    try:
        cell = {
            'layout_name':       summary_tokens[0],
            'source_name':       summary_tokens[2],
            'layout_pin_count':  int(summary_tokens[1]),
            'source_pin_count':  int(summary_tokens[3]),
        }
    except ValueError as e:
        raise ValueError(
            f"nXref {filepath!r}: cell-summary pin counts not int: "
            f"{body[0]!r}"
        ) from e

    nets = []
    for raw in body[1:]:
        tokens = raw.split()
        # <layout_idx> <layout_net> <source_idx> <source_net>
        if len(tokens) != 4:
            raise ValueError(
                f"nXref {filepath!r}: net row malformed: {raw!r} "
                f"(expected 4 tokens, got {len(tokens)})"
            )
        try:
            layout_idx = int(tokens[0])
            source_idx = int(tokens[2])
        except ValueError as e:
            raise ValueError(
                f"nXref {filepath!r}: net row index not int: {raw!r}"
            ) from e
        nets.append({
            'layout_idx':  layout_idx,
            'layout_net':  tokens[1],
            'source_idx':  source_idx,
            'source_net':  tokens[3],
        })

    return {
        'cell':         cell,
        'nets':         nets,
        'header_lines': header_lines,
    }


# =====================================================================
# NET NAMES parser
# =====================================================================

_NET_NAMES_HEADER_RE = re.compile(
    r'^\s*\d+\s+\d+\s+(?P<count>\d+)\s+'
)


def parse_net_names(filepath: str) -> dict:
    """Parse a NET NAMES Calibre HDB query response (stdout-only).

    The response shape is fixed:

        Net_Names <id>
        Nets:
        <cell_idx> <0> <count> <timestamp...>
        <name at index 1>
        <name at index 2>
        ...
        <name at index count>
        END OF RESPONSE

    Returns:
        {
          'count': int,            # net count from the count line
          'index_to_name': {int: str, ...},   # 1-indexed
          'name_to_index': {str: int, ...},
        }

    Raises:
        FileNotFoundError: if ``filepath`` does not exist.
        ValueError: if the structure does not match the expected
            ``Nets: / count line / N names / END OF RESPONSE`` form.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"NET NAMES file not found: {filepath!r}")

    with open(filepath) as f:
        lines = [ln.rstrip('\n') for ln in f]

    # Locate the "Nets:" anchor line.
    try:
        nets_idx = next(i for i, ln in enumerate(lines)
                        if ln.strip() == 'Nets:')
    except StopIteration:
        raise ValueError(
            f"NET NAMES {filepath!r}: missing 'Nets:' anchor"
        )

    if nets_idx + 1 >= len(lines):
        raise ValueError(
            f"NET NAMES {filepath!r}: count line missing after 'Nets:'"
        )

    count_line = lines[nets_idx + 1]
    m = _NET_NAMES_HEADER_RE.match(count_line)
    if not m:
        raise ValueError(
            f"NET NAMES {filepath!r}: malformed count line "
            f"{count_line!r} (expected '<int> <int> <count> "
            f"<timestamp>')"
        )
    count = int(m.group('count'))

    body = lines[nets_idx + 2:]
    # Trim at END OF RESPONSE if present, else read exactly ``count``.
    end_idx = None
    for i, ln in enumerate(body):
        if ln.strip() == 'END OF RESPONSE':
            end_idx = i
            break
    name_lines = body[:end_idx] if end_idx is not None else body
    # Filter out blank lines so accidental trailing newlines don't
    # break the count check.
    names = [ln.strip() for ln in name_lines if ln.strip()]

    if len(names) != count:
        raise ValueError(
            f"NET NAMES {filepath!r}: declared count={count} but "
            f"found {len(names)} net name(s) before END OF RESPONSE"
        )

    index_to_name = {i + 1: name for i, name in enumerate(names)}
    name_to_index = {name: i + 1 for i, name in enumerate(names)}

    return {
        'count':         count,
        'index_to_name': index_to_name,
        'name_to_index': name_to_index,
    }


# =====================================================================
# Joiner: nXref ⊕ NET NAMES → schematic-to-LVS-index middle file
# =====================================================================

def join_net_xref(nxref: dict, net_names: dict) -> dict:
    """Combine parsed ``nXref`` + parsed ``NET NAMES`` into the middle
    structure that maps schematic_net → lvs_name → lvs_index.

    Returns:
        {
          'cell': {... copied from nxref ...},
          'nets': [
            {'schematic_name': str,    # nXref source_net
             'lvs_name':       str,    # nXref layout_net
             'lvs_index':      int},   # NET NAMES index of lvs_name
            ...
          ],
        }

    Raises:
        KeyError: if any nXref ``layout_net`` is missing from the
            ``NET NAMES`` index. That's a real LVS bug — the two
            outputs come from the same SVDB and must agree.
    """
    name_to_index = net_names['name_to_index']
    joined_nets = []
    for n in nxref['nets']:
        lvs_name = n['layout_net']
        if lvs_name not in name_to_index:
            raise KeyError(
                f"join_net_xref: layout net {lvs_name!r} is not in "
                f"NET NAMES (have: {sorted(name_to_index)!r})"
            )
        joined_nets.append({
            'schematic_name': n['source_net'],
            'lvs_name':       lvs_name,
            'lvs_index':      name_to_index[lvs_name],
        })

    return {
        'cell': dict(nxref['cell']),
        'nets': joined_nets,
    }


def write_net_xref_yaml(joined: dict, out_path: str) -> None:
    """Persist the joined net-xref dict as YAML.

    Same key-order policy as ``write_ixref_yaml``: cell first, then
    nets.
    """
    out_dir = os.path.dirname(os.path.abspath(out_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(out_path, 'w') as f:
        yaml.safe_dump(joined, f, sort_keys=False, default_flow_style=False)


# =====================================================================
# Calibre subprocess runners (nXref + NET NAMES)
# =====================================================================

_NET_NAMES_BEGIN_RE = re.compile(r'^\s*Net_Names\b')
_NET_NAMES_END     = 'END OF RESPONSE'


def _extract_net_names_block(stdout: str) -> str:
    """Pull the ``Net_Names ... END OF RESPONSE`` block out of stdout.

    Calibre's HDB query server may interleave other output before /
    after the NET NAMES response. Slice the block bounded by the
    ``Net_Names`` opener and the ``END OF RESPONSE`` terminator.
    """
    lines = stdout.splitlines()
    begin = None
    for i, ln in enumerate(lines):
        if _NET_NAMES_BEGIN_RE.match(ln):
            begin = i
            break
    if begin is None:
        raise CalibreQueryError(
            "calibre stdout did not contain a 'Net_Names' response.\n"
            f"--- stdout (truncated) ---\n{stdout[:2000]}"
        )
    end = None
    for j in range(begin + 1, len(lines)):
        if lines[j].strip() == _NET_NAMES_END:
            end = j
            break
    if end is None:
        raise CalibreQueryError(
            "calibre stdout missing 'END OF RESPONSE' terminator after "
            "'Net_Names'.\n"
            f"--- stdout (truncated) ---\n{stdout[:2000]}"
        )
    return '\n'.join(lines[begin:end + 1]) + '\n'


def run_calibre_nxref(svdb_dir: str,
                      nxref_path: str,
                      *,
                      timeout: float = 300.0,
                      calibre_bin: str = 'calibre') -> None:
    """Spawn ``calibre -query <svdb_dir>`` and write nXref to ``nxref_path``.

    Stdin commands:

        NET XREF WRITE <nxref_path>
        EXIT

    Same diagnostics as :func:`run_calibre_ixref`, including stale-
    output protection: any pre-existing file at ``nxref_path`` is
    removed before the subprocess runs, so a Calibre-side silent
    failure (exit 0 but no rewrite) cannot leak stale data into the
    downstream join.
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

    if os.path.exists(nxref_path):
        os.remove(nxref_path)

    cmds = (
        f"NET XREF WRITE {nxref_path}\n"
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
    if not os.path.exists(nxref_path):
        raise CalibreQueryError(
            f"calibre -query {svdb_dir!r} completed but did not "
            f"produce {nxref_path!r}.\n"
            f"--- stdout ---\n{result.stdout}\n"
            f"--- stderr ---\n{result.stderr}"
        )


def run_calibre_net_names(svdb_dir: str,
                          net_names_path: str,
                          *,
                          timeout: float = 300.0,
                          calibre_bin: str = 'calibre') -> None:
    """Spawn ``calibre -query <svdb_dir>``, run ``NET NAMES``, and save
    the response block to ``net_names_path``.

    Unlike ``INSTANCE XREF`` / ``NET XREF``, the ``NET NAMES`` query
    streams its response over stdout — Calibre never writes a file.
    This function captures stdout, slices the
    ``Net_Names ... END OF RESPONSE`` block, and writes that block to
    ``net_names_path`` so downstream parsing has the same
    file-on-disk shape as the dummy fixture.

    Stdin commands:

        NET NAMES
        EXIT
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
        f"NET NAMES\n"
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

    block = _extract_net_names_block(result.stdout)
    out_dir = os.path.dirname(os.path.abspath(net_names_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(net_names_path, 'w') as f:
        f.write(block)


def run_dummy_nxref(svdb_dir: Optional[str],
                    nxref_path: str,
                    dummy_source: str) -> None:
    """Stage the dummy nXref.temp at ``nxref_path``."""
    if not os.path.exists(dummy_source):
        raise FileNotFoundError(
            f"Dummy nXref source not found: {dummy_source!r}"
        )
    abs_src = os.path.abspath(dummy_source)
    abs_dst = os.path.abspath(nxref_path)
    if abs_src == abs_dst:
        return
    out_dir = os.path.dirname(abs_dst)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    shutil.copyfile(abs_src, abs_dst)


def run_dummy_net_names(svdb_dir: Optional[str],
                        net_names_path: str,
                        dummy_source: str) -> None:
    """Stage the dummy NET NAMES output at ``net_names_path``."""
    if not os.path.exists(dummy_source):
        raise FileNotFoundError(
            f"Dummy NET NAMES source not found: {dummy_source!r}"
        )
    abs_src = os.path.abspath(dummy_source)
    abs_dst = os.path.abspath(net_names_path)
    if abs_src == abs_dst:
        return
    out_dir = os.path.dirname(abs_dst)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    shutil.copyfile(abs_src, abs_dst)


# =====================================================================
# Top-level orchestrator (net cross-reference)
# =====================================================================

def extract_net_xref(*,
                     mode: str,
                     svdb_dir: Optional[str],
                     nxref_path: str,
                     net_names_path: str,
                     dummy_nxref_source: Optional[str] = None,
                     dummy_net_names_source: Optional[str] = None,
                     timeout: float = 300.0,
                     calibre_bin: str = 'calibre') -> dict:
    """Run the net-xref half of the LVS query stage end to end.

    Dispatches to dummy / calibre runners for both ``NET XREF`` and
    ``NET NAMES``, parses each output, and joins them via
    :func:`join_net_xref`. The caller is responsible for
    :func:`write_net_xref_yaml` if a YAML middle file is wanted.

    Args:
        mode: 'dummy' or 'calibre'.
        svdb_dir: Required for 'calibre' mode.
        nxref_path: Where the raw nXref.temp lives after this call.
        net_names_path: Where the raw NET NAMES response lives after
            this call.
        dummy_nxref_source: Required for 'dummy' mode. Path to the
            committed dummy nXref.temp.
        dummy_net_names_source: Required for 'dummy' mode. Path to
            the committed dummy NET NAMES output.
        timeout: subprocess timeout in seconds (calibre mode only).
        calibre_bin: Calibre binary name on PATH.

    Returns:
        Joined dict (see :func:`join_net_xref`).
    """
    if mode == 'dummy':
        if dummy_nxref_source is None or dummy_net_names_source is None:
            raise ValueError(
                "extract_net_xref(mode='dummy') requires both "
                "dummy_nxref_source and dummy_net_names_source"
            )
        run_dummy_nxref(svdb_dir, nxref_path, dummy_nxref_source)
        run_dummy_net_names(svdb_dir, net_names_path,
                            dummy_net_names_source)
    elif mode == 'calibre':
        if svdb_dir is None:
            raise ValueError(
                "extract_net_xref(mode='calibre') requires svdb_dir"
            )
        run_calibre_nxref(svdb_dir, nxref_path,
                          timeout=timeout, calibre_bin=calibre_bin)
        run_calibre_net_names(svdb_dir, net_names_path,
                              timeout=timeout, calibre_bin=calibre_bin)
    else:
        raise ValueError(
            f"extract_net_xref: unknown mode {mode!r} "
            f"(expected 'dummy' or 'calibre')"
        )

    nxref     = parse_nxref(nxref_path)
    net_names = parse_net_names(net_names_path)
    return join_net_xref(nxref, net_names)


# =====================================================================
# DEVICE INFO parser (per-device LVS-derived-shape bbox)
# =====================================================================
#
# Calibre HDB ``DEVICE INFO <layout_inst>`` returns the device's LVS-
# annotated metadata plus the seed shapes of every layer attached to
# the device. The layout_inst here is the *LVS* device name (e.g. M0,
# M1) — the same name iXref's ``layout_inst`` field carries — not the
# schematic instance name (MN0, MP0).
#
# Response shape (stdout-only; Calibre never writes a file):
#
#   Device_Info <precision>
#   Info:
#   0 0 <n_metadata> <date>
#   <device_type_number>           |
#   <pin_net_1>                    |
#   <pin_net_2>                    |
#   ...                            | n_metadata lines (1 + n_pins +
#   <property_value_1>             | n_props + optional text_model_name
#   <property_value_2>             | + seed_layer_name)
#   ...                            |
#   [<text_model_name>]            |
#   <seed_layer_name>              |
#   <a> <b> [c] <date>             ← per-layer count line (1+ ints + date)
#   p <shape_idx> <n_vertices>
#   <vert_1_y> <vert_1_x>          ← user spec: pairs are (y, x)
#   <vert_2_y> <vert_2_x>          (each in `precision`-units; um =
#   ...                              value / precision)
#   <vert_n_y> <vert_n_x>
#   p <shape_idx_2> <n_vertices_2>
#   ...                            ← additional shapes for same layer
#   <new_layer_name>               ← additional layer
#   <a> <b> [c] <date>
#   p 1 <n_vertices>
#   ...
#   END OF RESPONSE
#
# We don't know the per-device-type pin count or property count, so the
# n_metadata block (between device_type_number and seed_layer_name) is
# preserved as opaque text. The seed_layer_name is always the last line
# of the metadata block — that's the convention the parser anchors on.

_DEVICE_INFO_HEADER_RE = re.compile(r'^\s*Device_Info\s+(?P<precision>\d+)')
_DEVICE_INFO_COUNT_RE = re.compile(
    r'^\s*\d+\s+\d+\s+(?P<n>\d+)\s+'
)


def _looks_like_count_line(tokens):
    """True if ``tokens`` matches the per-layer count line shape:
    1+ leading ints followed by a date that uses month-name + numbers.
    Examples: "1 1 0 May 07 03:00:00 2026", "11 0 Feb 27 11:36:00 2026".
    """
    if len(tokens) < 2:
        return False
    # First two tokens are ints.
    for t in tokens[:2]:
        if not (t.lstrip('-').isdigit()):
            return False
    return True


def _looks_like_shape_header(tokens):
    """True for ``p <shape_idx> <n_vertices>`` rows."""
    return (len(tokens) == 3
            and tokens[0] == 'p'
            and tokens[1].isdigit()
            and tokens[2].isdigit())


def parse_device_info(filepath: str) -> dict:
    """Parse a Calibre HDB ``DEVICE INFO`` response (stdout-only).

    Returns:
        {
          'precision':            int,
          'device_type_number':   int,
          'metadata_lines':       [str, ...],   # opaque pin nets +
                                                # property values +
                                                # optional text_model_name
          'layers': [
            {
              'name': str,
              'shapes': [
                {
                  'vertices_unit': [(y, x), ...],  # per user spec
                  'bbox_um': {'x1': float, 'y1': float,
                              'x2': float, 'y2': float},
                },
                ...
              ],
            },
            ...
          ],
        }

    Coordinate convention (per user / Calibre manual): each vertex line
    is two integers ``<y> <x>`` in units of ``1 / precision`` micrometers
    (for ``precision=20000`` that's 0.05 nm). Vertices for one shape are
    listed as four corners (LL, LR, UR, UL) for rectangles; the parser
    just takes ``min / max`` of each coordinate to derive the bbox, so
    the corner-ordering convention is irrelevant for the saved bbox.

    Raises:
        FileNotFoundError: if ``filepath`` does not exist.
        ValueError: on header / count-line / metadata / vertex
            malformation.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"DEVICE INFO file not found: {filepath!r}"
        )

    with open(filepath) as f:
        lines = [ln.rstrip('\n') for ln in f]

    # Header: ``Device_Info <precision>``.
    di_idx = None
    precision = None
    for i, ln in enumerate(lines):
        m = _DEVICE_INFO_HEADER_RE.match(ln)
        if m:
            di_idx = i
            precision = int(m.group('precision'))
            break
    if di_idx is None:
        raise ValueError(
            f"DEVICE INFO {filepath!r}: missing 'Device_Info' header"
        )

    # Anchor: ``Info:``
    info_idx = None
    for j in range(di_idx + 1, len(lines)):
        if lines[j].strip() == 'Info:':
            info_idx = j
            break
    if info_idx is None:
        raise ValueError(
            f"DEVICE INFO {filepath!r}: missing 'Info:' anchor"
        )

    # Count line: ``0 0 <n_metadata> <date>``
    if info_idx + 1 >= len(lines):
        raise ValueError(
            f"DEVICE INFO {filepath!r}: count line missing after 'Info:'"
        )
    count_line = lines[info_idx + 1]
    m = _DEVICE_INFO_COUNT_RE.match(count_line)
    if not m:
        raise ValueError(
            f"DEVICE INFO {filepath!r}: malformed count line "
            f"{count_line!r} (expected '<int> <int> <n> <timestamp>')"
        )
    n_metadata = int(m.group('n'))

    # n_metadata lines follow.
    metadata_start = info_idx + 2
    metadata_end = metadata_start + n_metadata
    if metadata_end > len(lines):
        raise ValueError(
            f"DEVICE INFO {filepath!r}: only "
            f"{len(lines) - metadata_start} metadata line(s) "
            f"available, expected {n_metadata}"
        )
    metadata = [lines[i] for i in range(metadata_start, metadata_end)]
    if not metadata:
        raise ValueError(
            f"DEVICE INFO {filepath!r}: empty metadata block"
        )

    try:
        device_type_number = int(metadata[0].strip())
    except ValueError as e:
        raise ValueError(
            f"DEVICE INFO {filepath!r}: device_type_number "
            f"not int: {metadata[0]!r}"
        ) from e

    first_layer_name = metadata[-1].strip()
    if not first_layer_name:
        raise ValueError(
            f"DEVICE INFO {filepath!r}: seed layer name (last "
            f"metadata line) is blank"
        )

    metadata_lines = metadata[1:-1]   # opaque, may be empty

    # Walk the post-metadata block, collecting shapes per layer.
    layers: list = [{'name': first_layer_name, 'shapes': []}]

    def _bbox_um(verts_unit):
        ys = [v[0] for v in verts_unit]
        xs = [v[1] for v in verts_unit]
        return {
            'x1': min(xs) / precision,
            'y1': min(ys) / precision,
            'x2': max(xs) / precision,
            'y2': max(ys) / precision,
        }

    i = metadata_end
    saw_terminator = False
    while i < len(lines):
        raw = lines[i]
        ln = raw.strip()
        if not ln:
            i += 1
            continue
        if ln == 'END OF RESPONSE':
            saw_terminator = True
            break

        tokens = ln.split()

        if _looks_like_shape_header(tokens):
            n_verts = int(tokens[2])
            verts: list = []
            for j in range(n_verts):
                if i + 1 + j >= len(lines):
                    raise ValueError(
                        f"DEVICE INFO {filepath!r}: shape declared "
                        f"{n_verts} vertices but file ended early"
                    )
                vt = lines[i + 1 + j].split()
                if len(vt) != 2:
                    raise ValueError(
                        f"DEVICE INFO {filepath!r}: vertex line "
                        f"malformed (expected 2 ints): "
                        f"{lines[i + 1 + j]!r}"
                    )
                try:
                    verts.append((int(vt[0]), int(vt[1])))
                except ValueError as e:
                    raise ValueError(
                        f"DEVICE INFO {filepath!r}: vertex tokens "
                        f"not int: {lines[i + 1 + j]!r}"
                    ) from e
            layers[-1]['shapes'].append({
                'vertices_unit': verts,
                'bbox_um':       _bbox_um(verts),
            })
            i += 1 + n_verts
            continue

        if _looks_like_count_line(tokens):
            # Per-layer count line. We don't try to validate the
            # declared shape count against actually-parsed shapes (the
            # spec is ambiguous between "1 1 0 <date>" and "11 0
            # <date>" forms). Skip and continue.
            i += 1
            continue

        # Anything else that isn't blank / END OF RESPONSE / shape /
        # count line is a new layer name. Single-token strings like
        # "ngate_lvt" / "pgate_lvt" / "od_seed" land here.
        layers.append({'name': ln, 'shapes': []})
        i += 1

    if not saw_terminator:
        # Falling off EOF without a terminator means the capture was
        # truncated mid-response. The shape-count line is ambiguous in
        # the manual (``1 1 0`` vs ``11 0`` forms) so we can't fall
        # back to per-layer shape-count validation; require the
        # terminator instead. ``run_calibre_device_info`` already
        # guards this for the live subprocess path; this protects the
        # dummy / pre-saved-file path.
        raise ValueError(
            f"DEVICE INFO {filepath!r}: missing 'END OF RESPONSE' "
            f"terminator (truncated capture?)"
        )

    return {
        'precision':           precision,
        'device_type_number':  device_type_number,
        'metadata_lines':      metadata_lines,
        'layers':              layers,
    }


def write_device_info_yaml(parsed: dict, out_path: str) -> None:
    """Persist the joined DEVICE INFO middle dict as YAML.

    Schema:

        devices:
          - layout_inst: str            # M0, M1, ...
            device_type_number: int
            layers:
              - name: str
                shapes:
                  - bbox_um:
                      x1: float          # micrometers
                      y1: float
                      x2: float
                      y2: float

    Per-shape ``vertices_unit`` and per-device ``metadata_lines``
    (pin nets + property values) are intentionally *not* serialised —
    the user's stated need is "each device's related layers' name
    and shapes' bbox(converted to original values in um)".
    """
    out_dir = os.path.dirname(os.path.abspath(out_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    devices_out = []
    for d in parsed['devices']:
        layers_out = []
        for layer in d['layers']:
            layers_out.append({
                'name':   layer['name'],
                'shapes': [{'bbox_um': sh['bbox_um']}
                           for sh in layer['shapes']],
            })
        devices_out.append({
            'layout_inst':         d['layout_inst'],
            'device_type_number':  d['device_type_number'],
            'layers':              layers_out,
        })

    payload = {'devices': devices_out}
    with open(out_path, 'w') as f:
        yaml.safe_dump(payload, f, sort_keys=False,
                       default_flow_style=False)


# =====================================================================
# Calibre subprocess runner (DEVICE INFO)
# =====================================================================

_DEVICE_INFO_BEGIN_RE = re.compile(r'^\s*Device_Info\b')


def _extract_device_info_block(stdout: str, layout_inst: str) -> str:
    """Slice the ``Device_Info ... END OF RESPONSE`` block out of stdout.

    Calibre's HDB query server may interleave other output around the
    response (banners, prompts). Identify the block bounded by the
    ``Device_Info`` opener and the next ``END OF RESPONSE``.
    """
    lines = stdout.splitlines()
    begin = None
    for i, ln in enumerate(lines):
        if _DEVICE_INFO_BEGIN_RE.match(ln):
            begin = i
            break
    if begin is None:
        raise CalibreQueryError(
            f"calibre stdout did not contain a 'Device_Info' "
            f"response for {layout_inst!r}.\n"
            f"--- stdout (truncated) ---\n{stdout[:2000]}"
        )
    end = None
    for j in range(begin + 1, len(lines)):
        if lines[j].strip() == 'END OF RESPONSE':
            end = j
            break
    if end is None:
        raise CalibreQueryError(
            f"calibre stdout missing 'END OF RESPONSE' terminator "
            f"after 'Device_Info' for {layout_inst!r}.\n"
            f"--- stdout (truncated) ---\n{stdout[:2000]}"
        )
    return '\n'.join(lines[begin:end + 1]) + '\n'


def run_calibre_device_info(svdb_dir: str,
                             layout_inst: str,
                             out_path: str,
                             *,
                             timeout: float = 300.0,
                             calibre_bin: str = 'calibre') -> None:
    """Spawn ``calibre -query <svdb_dir>``, run ``DEVICE INFO <inst>``.

    ``DEVICE INFO`` streams its response over stdout — Calibre never
    writes a file. This function captures stdout, slices the bounded
    ``Device_Info ... END OF RESPONSE`` block, and writes that block
    to ``out_path`` so downstream parsing has the same file-on-disk
    shape as the dummy fixture. ``layout_inst`` is the LVS device name
    (e.g. ``M0`` / ``M1``) — *not* the schematic instance name.

    Stdin commands:

        DEVICE INFO <layout_inst>
        EXIT

    Same diagnostics as :func:`run_calibre_ixref` (missing binary,
    missing svdb dir, non-zero exit, timeout). No stale-output
    protection is required: the function captures stdout and writes
    ``out_path`` itself with ``'w'`` mode.
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
        f"DEVICE INFO {layout_inst}\n"
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

    block = _extract_device_info_block(result.stdout, layout_inst)
    out_dir = os.path.dirname(os.path.abspath(out_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(out_path, 'w') as f:
        f.write(block)


def run_dummy_device_info(svdb_dir: Optional[str],
                           layout_inst: str,
                           out_path: str,
                           dummy_source: str) -> None:
    """Stage a dummy DEVICE INFO output at ``out_path``.

    ``svdb_dir`` and ``layout_inst`` are accepted for API symmetry with
    :func:`run_calibre_device_info` (they're ignored — the dummy file
    is the source of truth). ``dummy_source`` is the per-instance
    fixture path (e.g. ``dummy/fixtures/device_info_M0.txt``).
    """
    if not os.path.exists(dummy_source):
        raise FileNotFoundError(
            f"Dummy DEVICE INFO source not found: {dummy_source!r}"
        )
    abs_src = os.path.abspath(dummy_source)
    abs_dst = os.path.abspath(out_path)
    if abs_src == abs_dst:
        return
    out_dir = os.path.dirname(abs_dst)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    shutil.copyfile(abs_src, abs_dst)


# =====================================================================
# Top-level orchestrator (DEVICE INFO across all layout devices)
# =====================================================================

def extract_device_info(*,
                         mode: str,
                         svdb_dir: Optional[str],
                         layout_insts: list,
                         out_dir: str,
                         dummy_source_dir: Optional[str] = None,
                         timeout: float = 300.0,
                         calibre_bin: str = 'calibre') -> dict:
    """Run ``DEVICE INFO`` for each layout instance, collect results.

    One subprocess per device in ``calibre`` mode; one file copy per
    device in ``dummy`` mode. Per-device raw responses land at
    ``<out_dir>/device_info_<inst>.txt``.

    Args:
        mode: 'dummy' or 'calibre'.
        svdb_dir: Required for 'calibre' mode.
        layout_insts: List of LVS device names (e.g. ['M0', 'M1']).
            Typically read from a parsed iXref middle file's
            ``devices[*].layout_inst``.
        out_dir: Directory to write per-instance ``device_info_*.txt``
            files into.
        dummy_source_dir: Required for 'dummy' mode. Directory holding
            ``device_info_<inst>.txt`` fixtures.
        timeout: subprocess timeout in seconds (calibre mode only).
        calibre_bin: Calibre binary name on PATH.

    Returns:
        {
          'devices': [
            {
              'layout_inst':         str,
              'precision':           int,
              'device_type_number':  int,
              'metadata_lines':      [str, ...],
              'layers':              [...],   # see parse_device_info
            },
            ...
          ],
        }
    """
    if mode == 'dummy':
        if dummy_source_dir is None:
            raise ValueError(
                "extract_device_info(mode='dummy') requires "
                "dummy_source_dir"
            )
    elif mode == 'calibre':
        if svdb_dir is None:
            raise ValueError(
                "extract_device_info(mode='calibre') requires svdb_dir"
            )
    else:
        raise ValueError(
            f"extract_device_info: unknown mode {mode!r} "
            f"(expected 'dummy' or 'calibre')"
        )

    os.makedirs(out_dir, exist_ok=True)
    devices = []
    for inst in layout_insts:
        out_path = os.path.join(out_dir, f'device_info_{inst}.txt')
        if mode == 'dummy':
            src = os.path.join(dummy_source_dir,
                               f'device_info_{inst}.txt')
            run_dummy_device_info(svdb_dir, inst, out_path, src)
        else:
            run_calibre_device_info(
                svdb_dir, inst, out_path,
                timeout=timeout, calibre_bin=calibre_bin,
            )
        parsed = parse_device_info(out_path)
        devices.append({'layout_inst': inst, **parsed})

    return {'devices': devices}


# =====================================================================
# NET SHAPES parser (per-net LVS-derived metal/via-shape bboxes)
# =====================================================================
#
# Calibre HDB ``NET SHAPES <lvs_name_or_index>`` returns the set of
# routing-layer (LI / VIA0 / M1 / ...) shapes that belong to one net.
# The layer names match the GDS layer names directly (M1, VIA0, LI),
# and each shape's bbox represents the *effective* conducting region
# (the LVS-mapped sub-rectangle of the GDS shape — cuts and extension
# margins are excluded; layer-name mapping is M7's job, see backlog).
#
# The query argument ``<lvs_name>`` is whatever NET NAMES gave for that
# net's index — top-level pins keep their schematic names ('VDD', 'IN',
# ...); LVS-renumbered internal nets surface as numeric strings ('2',
# '6', ...).
#
# Response shape (stdout-only; Calibre never writes a file):
#
#   Net_Shapes <precision>
#   Info:
#   0 0 <n_metadata> <date>
#   <metadata_line_1>              | n_metadata lines, last one is the
#   ...                            | first layer name (same anchor
#   <seed_layer_name>              | convention as DEVICE INFO).
#   <a> <b> [c] <date>             ← per-layer count line
#   p <shape_idx> <n_vertices>
#   <vert_1_y> <vert_1_x>          ← (y, x) pairs in 1/precision µm
#   ...
#   p <shape_idx_2> <n_vertices_2>
#   ...
#   <new_layer_name>
#   ...
#   END OF RESPONSE
#
# We don't validate per-layer shape counts (the count line is ambiguous
# in the manual — see DEVICE INFO note); the END OF RESPONSE terminator
# is required.

_NET_SHAPES_HEADER_RE = re.compile(r'^\s*Net_Shapes\s+(?P<precision>\d+)')
_NET_SHAPES_COUNT_RE  = re.compile(
    r'^\s*\d+\s+\d+\s+(?P<n>\d+)\s+'
)


def parse_net_shapes(filepath: str) -> dict:
    """Parse a Calibre HDB ``NET SHAPES`` response (stdout-only).

    Returns:
        {
          'precision':       int,
          'metadata_lines':  [str, ...],  # opaque (excluding seed layer)
          'layers': [
            {
              'name': str,
              'shapes': [
                {'vertices_unit': [(y, x), ...],
                 'bbox_um': {'x1': float, 'y1': float,
                             'x2': float, 'y2': float}},
                ...
              ],
            },
            ...
          ],
        }

    Coordinate convention matches DEVICE INFO: each vertex is a
    ``<y> <x>`` pair in ``1 / precision`` µm. ``END OF RESPONSE`` is
    required — falling off EOF without seeing it raises ``ValueError``.

    Raises:
        FileNotFoundError, ValueError.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"NET SHAPES file not found: {filepath!r}"
        )

    with open(filepath) as f:
        lines = [ln.rstrip('\n') for ln in f]

    ns_idx = None
    precision = None
    for i, ln in enumerate(lines):
        m = _NET_SHAPES_HEADER_RE.match(ln)
        if m:
            ns_idx = i
            precision = int(m.group('precision'))
            break
    if ns_idx is None:
        raise ValueError(
            f"NET SHAPES {filepath!r}: missing 'Net_Shapes' header"
        )

    info_idx = None
    for j in range(ns_idx + 1, len(lines)):
        if lines[j].strip() == 'Info:':
            info_idx = j
            break
    if info_idx is None:
        raise ValueError(
            f"NET SHAPES {filepath!r}: missing 'Info:' anchor"
        )

    if info_idx + 1 >= len(lines):
        raise ValueError(
            f"NET SHAPES {filepath!r}: count line missing after 'Info:'"
        )
    count_line = lines[info_idx + 1]
    m = _NET_SHAPES_COUNT_RE.match(count_line)
    if not m:
        raise ValueError(
            f"NET SHAPES {filepath!r}: malformed count line "
            f"{count_line!r} (expected '<int> <int> <n> <timestamp>')"
        )
    n_metadata = int(m.group('n'))

    metadata_start = info_idx + 2
    metadata_end = metadata_start + n_metadata
    if metadata_end > len(lines):
        raise ValueError(
            f"NET SHAPES {filepath!r}: only "
            f"{len(lines) - metadata_start} metadata line(s) "
            f"available, expected {n_metadata}"
        )
    metadata = [lines[i] for i in range(metadata_start, metadata_end)]
    if not metadata:
        raise ValueError(
            f"NET SHAPES {filepath!r}: empty metadata block"
        )

    first_layer_name = metadata[-1].strip()
    if not first_layer_name:
        raise ValueError(
            f"NET SHAPES {filepath!r}: seed layer name (last "
            f"metadata line) is blank"
        )
    metadata_lines = metadata[:-1]   # opaque, may be empty

    layers: list = [{'name': first_layer_name, 'shapes': []}]

    def _bbox_um(verts_unit):
        ys = [v[0] for v in verts_unit]
        xs = [v[1] for v in verts_unit]
        return {
            'x1': min(xs) / precision,
            'y1': min(ys) / precision,
            'x2': max(xs) / precision,
            'y2': max(ys) / precision,
        }

    i = metadata_end
    saw_terminator = False
    while i < len(lines):
        ln = lines[i].strip()
        if not ln:
            i += 1
            continue
        if ln == 'END OF RESPONSE':
            saw_terminator = True
            break

        tokens = ln.split()

        if _looks_like_shape_header(tokens):
            n_verts = int(tokens[2])
            verts: list = []
            for j in range(n_verts):
                if i + 1 + j >= len(lines):
                    raise ValueError(
                        f"NET SHAPES {filepath!r}: shape declared "
                        f"{n_verts} vertices but file ended early"
                    )
                vt = lines[i + 1 + j].split()
                if len(vt) != 2:
                    raise ValueError(
                        f"NET SHAPES {filepath!r}: vertex line "
                        f"malformed (expected 2 ints): "
                        f"{lines[i + 1 + j]!r}"
                    )
                try:
                    verts.append((int(vt[0]), int(vt[1])))
                except ValueError as e:
                    raise ValueError(
                        f"NET SHAPES {filepath!r}: vertex tokens "
                        f"not int: {lines[i + 1 + j]!r}"
                    ) from e
            layers[-1]['shapes'].append({
                'vertices_unit': verts,
                'bbox_um':       _bbox_um(verts),
            })
            i += 1 + n_verts
            continue

        if _looks_like_count_line(tokens):
            i += 1
            continue

        # New layer name (single token like "M1", "VIA0", "LI", or a
        # numeric LVS layer id like "11").
        layers.append({'name': ln, 'shapes': []})
        i += 1

    if not saw_terminator:
        raise ValueError(
            f"NET SHAPES {filepath!r}: missing 'END OF RESPONSE' "
            f"terminator (truncated capture?)"
        )

    return {
        'precision':       precision,
        'metadata_lines':  metadata_lines,
        'layers':          layers,
    }


def write_net_shapes_yaml(parsed: dict, out_path: str) -> None:
    """Persist the joined NET SHAPES middle dict as YAML.

    Schema:

        nets:
          - lvs_index: int            # NET NAMES position (1-indexed)
            lvs_name: str             # 'OUT', '2', ...
            schematic_name: str       # net_xref join: 'OUT', 'net9', ...
            layers:
              - name: str             # GDS layer name (LI / VIA0 / M1)
                shapes:
                  - bbox_um:
                      x1: float       # micrometers
                      y1: float
                      x2: float
                      y2: float

    Vertex tuples and opaque metadata stay in memory but aren't
    serialised — same policy as DEVICE INFO.
    """
    out_dir = os.path.dirname(os.path.abspath(out_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    nets_out = []
    for net in parsed['nets']:
        layers_out = []
        for layer in net['layers']:
            layers_out.append({
                'name':   layer['name'],
                'shapes': [{'bbox_um': sh['bbox_um']}
                           for sh in layer['shapes']],
            })
        nets_out.append({
            'lvs_index':       net['lvs_index'],
            'lvs_name':        net['lvs_name'],
            'schematic_name':  net['schematic_name'],
            'layers':          layers_out,
        })

    payload = {'nets': nets_out}
    with open(out_path, 'w') as f:
        yaml.safe_dump(payload, f, sort_keys=False,
                       default_flow_style=False)


# =====================================================================
# Calibre subprocess runner (NET SHAPES)
# =====================================================================

_NET_SHAPES_BEGIN_RE = re.compile(r'^\s*Net_Shapes\b')


def _extract_net_shapes_block(stdout: str, lvs_name: str) -> str:
    """Slice the ``Net_Shapes ... END OF RESPONSE`` block out of stdout."""
    lines = stdout.splitlines()
    begin = None
    for i, ln in enumerate(lines):
        if _NET_SHAPES_BEGIN_RE.match(ln):
            begin = i
            break
    if begin is None:
        raise CalibreQueryError(
            f"calibre stdout did not contain a 'Net_Shapes' "
            f"response for {lvs_name!r}.\n"
            f"--- stdout (truncated) ---\n{stdout[:2000]}"
        )
    end = None
    for j in range(begin + 1, len(lines)):
        if lines[j].strip() == 'END OF RESPONSE':
            end = j
            break
    if end is None:
        raise CalibreQueryError(
            f"calibre stdout missing 'END OF RESPONSE' terminator "
            f"after 'Net_Shapes' for {lvs_name!r}.\n"
            f"--- stdout (truncated) ---\n{stdout[:2000]}"
        )
    return '\n'.join(lines[begin:end + 1]) + '\n'


def run_calibre_net_shapes(svdb_dir: str,
                            lvs_name: str,
                            out_path: str,
                            *,
                            timeout: float = 300.0,
                            calibre_bin: str = 'calibre') -> None:
    """Spawn ``calibre -query <svdb_dir>``, run ``NET SHAPES <lvs_name>``.

    Stdin commands:

        NET SHAPES <lvs_name>
        EXIT

    ``lvs_name`` is the LVS-side net name from NET NAMES — top-level
    pins keep their schematic strings ('VDD', 'OUT'); LVS-renumbered
    internal nets surface as numeric strings ('2', '6', ...). Captures
    stdout, slices the bounded block, writes to ``out_path``. Same
    error semantics as :func:`run_calibre_device_info`.
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
        f"NET SHAPES {lvs_name}\n"
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

    block = _extract_net_shapes_block(result.stdout, lvs_name)
    out_dir = os.path.dirname(os.path.abspath(out_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(out_path, 'w') as f:
        f.write(block)


def run_dummy_net_shapes(svdb_dir: Optional[str],
                          lvs_name: str,
                          out_path: str,
                          dummy_source: str) -> None:
    """Stage a dummy NET SHAPES output at ``out_path``."""
    if not os.path.exists(dummy_source):
        raise FileNotFoundError(
            f"Dummy NET SHAPES source not found: {dummy_source!r}"
        )
    abs_src = os.path.abspath(dummy_source)
    abs_dst = os.path.abspath(out_path)
    if abs_src == abs_dst:
        return
    out_dir = os.path.dirname(abs_dst)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    shutil.copyfile(abs_src, abs_dst)


# =====================================================================
# Top-level orchestrator (NET SHAPES across selected nets)
# =====================================================================

def extract_net_shapes(*,
                        mode: str,
                        svdb_dir: Optional[str],
                        nets: list,
                        out_dir: str,
                        dummy_source_dir: Optional[str] = None,
                        timeout: float = 300.0,
                        calibre_bin: str = 'calibre') -> dict:
    """Run ``NET SHAPES <lvs_name>`` for each net, collect results.

    One subprocess per net in ``calibre`` mode; one file copy per net
    in ``dummy`` mode. Per-net raw responses land at
    ``<out_dir>/net_shapes_<lvs_name>.txt``.

    Args:
        mode: 'dummy' or 'calibre'.
        svdb_dir: Required for 'calibre' mode.
        nets: List of dicts with at least
            ``{'lvs_name', 'lvs_index', 'schematic_name'}`` — typically
            taken straight from a parsed net_xref middle file's
            ``nets`` list.
        out_dir: Directory to write per-net ``net_shapes_*.txt`` into.
        dummy_source_dir: Required for 'dummy' mode. Holds
            ``net_shapes_<lvs_name>.txt`` fixtures.
        timeout: subprocess timeout in seconds (calibre mode only).
        calibre_bin: Calibre binary name on PATH.

    Returns:
        {
          'nets': [
            {
              'lvs_index':       int,
              'lvs_name':        str,
              'schematic_name':  str,
              'precision':       int,
              'metadata_lines':  [str, ...],
              'layers':          [...],   # see parse_net_shapes
            },
            ...
          ],
        }
    """
    if mode == 'dummy':
        if dummy_source_dir is None:
            raise ValueError(
                "extract_net_shapes(mode='dummy') requires "
                "dummy_source_dir"
            )
    elif mode == 'calibre':
        if svdb_dir is None:
            raise ValueError(
                "extract_net_shapes(mode='calibre') requires svdb_dir"
            )
    else:
        raise ValueError(
            f"extract_net_shapes: unknown mode {mode!r} "
            f"(expected 'dummy' or 'calibre')"
        )

    os.makedirs(out_dir, exist_ok=True)
    out_nets = []
    for net in nets:
        lvs_name = net['lvs_name']
        out_path = os.path.join(out_dir,
                                 f'net_shapes_{lvs_name}.txt')
        if mode == 'dummy':
            src = os.path.join(dummy_source_dir,
                               f'net_shapes_{lvs_name}.txt')
            run_dummy_net_shapes(svdb_dir, lvs_name, out_path, src)
        else:
            run_calibre_net_shapes(
                svdb_dir, lvs_name, out_path,
                timeout=timeout, calibre_bin=calibre_bin,
            )
        parsed = parse_net_shapes(out_path)
        out_nets.append({
            'lvs_index':       net['lvs_index'],
            'lvs_name':        lvs_name,
            'schematic_name':  net['schematic_name'],
            **parsed,
        })

    return {'nets': out_nets}
