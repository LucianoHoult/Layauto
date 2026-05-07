"""Unit tests for ``io_adapters.calibre_query``.

Covers:
  * iXref.temp parser (header skip, cell summary, device rows, S/D
    swap marker, malformed-input failure modes)
  * YAML middle-file round-trip
  * Dummy-mode dispatcher (copy + parse)
  * Real-mode dispatcher (mocked subprocess.run; missing-binary,
    non-zero-exit, timeout, missing-output diagnostics)
  * Generator vs committed-fixture parity
"""

import os
import shutil
import subprocess
import sys
from unittest.mock import patch

import pytest
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from io_adapters.calibre_query import (
    parse_ixref,
    write_ixref_yaml,
    run_dummy_ixref,
    run_calibre_ixref,
    extract_ixref,
    CalibreNotFoundError,
    CalibreQueryError,
)


# =====================================================================
# Helpers
# =====================================================================

def _write_ixref(tmp_path, body, header=None):
    """Write a synthetic iXref.temp at ``tmp_path / 'in.ixf'``."""
    if header is None:
        header = (
            "# SVDB: Instance Cross Reference (ixf) (File format 1)\n"
            "# SVDB: Layout Primary CELL\n"
            "# SVDB: End of header.\n"
        )
    path = tmp_path / "in.ixf"
    path.write_text(header + body)
    return str(path)


# =====================================================================
# Parser
# =====================================================================

def test_parse_committed_fixture(ixref_temp_path):
    """Committed dummy fixture parses into the expected schema."""
    parsed = parse_ixref(ixref_temp_path)

    assert parsed['cell'] == {
        'layout_name':       'INV_N5_P7',
        'source_name':       'INV_N5_P7',
        'layout_pin_count':  4,
        'source_pin_count':  4,
    }
    assert len(parsed['devices']) == 2

    nmos = parsed['devices'][0]
    assert nmos == {
        'layout_idx':  0,
        'layout_inst': 'M0',
        'source_idx':  0,
        'source_inst': 'MN0',
        'sd_swapped':  False,
    }

    pmos = parsed['devices'][1]
    assert pmos['layout_inst'] == 'M1'
    assert pmos['source_inst'] == 'MP0'
    assert pmos['sd_swapped'] is True

    # Header lines are preserved verbatim (used by the YAML middle file
    # so the iXref can be reconstructed from the YAML if needed).
    assert parsed['header_lines'][0].startswith('# SVDB: Instance Cross')
    assert parsed['header_lines'][-1].strip() == '# SVDB: End of header.'


def test_parse_skips_extra_header_lines(tmp_path):
    """All ``# SVDB:`` lines before the terminator are header lines."""
    header = (
        "# SVDB: Instance Cross Reference (ixf) (File format 1)\n"
        "# SVDB: Layout Primary CELL\n"
        "# SVDB: Source Primary CELL\n"
        "# SVDB: Layout system: GDSII\n"
        "# SVDB: Some other comment\n"
        "# SVDB: End of header.\n"
    )
    body = "CELL 4 CELL 4\n0 M0 0 MN0\n"
    path = _write_ixref(tmp_path, body, header)
    parsed = parse_ixref(path)
    # Six header lines including the terminator.
    assert len(parsed['header_lines']) == 6


def test_parse_device_row_no_swap_vs_swap(tmp_path):
    body = "CELL 2 CELL 2\n0 M0 0 MN0\n0 M1 0 MP0 X\n"
    path = _write_ixref(tmp_path, body)
    parsed = parse_ixref(path)
    assert parsed['devices'][0]['sd_swapped'] is False
    assert parsed['devices'][1]['sd_swapped'] is True


def test_parse_distinct_layout_and_source_cell_names(tmp_path):
    """Realistic case where layout cell name differs from source."""
    body = "BUFLVT 6 BUF 6\n0 M0 0 MMM3 X\n0 M1 0 MMM1\n"
    path = _write_ixref(tmp_path, body)
    parsed = parse_ixref(path)
    assert parsed['cell']['layout_name'] == 'BUFLVT'
    assert parsed['cell']['source_name'] == 'BUF'
    assert parsed['cell']['layout_pin_count'] == 6
    assert parsed['cell']['source_pin_count'] == 6


def test_parse_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        parse_ixref(str(tmp_path / "nonexistent.ixf"))


def test_parse_missing_header_terminator_raises(tmp_path):
    path = tmp_path / "bad.ixf"
    path.write_text(
        "# SVDB: Instance Cross Reference (ixf) (File format 1)\n"
        "CELL 4 CELL 4\n0 M0 0 MN0\n"
    )
    with pytest.raises(ValueError, match="missing required terminator"):
        parse_ixref(str(path))


def test_parse_empty_body_raises(tmp_path):
    path = _write_ixref(tmp_path, "")
    with pytest.raises(ValueError, match="body is empty"):
        parse_ixref(path)


def test_parse_malformed_summary_raises(tmp_path):
    path = _write_ixref(tmp_path, "CELL 4 CELL\n0 M0 0 MN0\n")
    with pytest.raises(ValueError, match="cell-summary line malformed"):
        parse_ixref(path)


def test_parse_summary_non_int_pin_count_raises(tmp_path):
    path = _write_ixref(tmp_path, "CELL four CELL 4\n0 M0 0 MN0\n")
    with pytest.raises(ValueError, match="pin counts not int"):
        parse_ixref(path)


def test_parse_malformed_device_row_raises(tmp_path):
    path = _write_ixref(tmp_path, "CELL 4 CELL 4\n0 M0 0 MN0 X EXTRA\n")
    with pytest.raises(ValueError, match="device row malformed"):
        parse_ixref(path)


def test_parse_unknown_swap_marker_raises(tmp_path):
    path = _write_ixref(tmp_path, "CELL 4 CELL 4\n0 M0 0 MN0 Y\n")
    with pytest.raises(ValueError, match="expected 'X'"):
        parse_ixref(path)


# =====================================================================
# YAML round-trip
# =====================================================================

def test_yaml_roundtrip_identity(ixref_temp_path, tmp_path):
    """parse → write_yaml → safe_load gives the same dict."""
    parsed = parse_ixref(ixref_temp_path)
    out = tmp_path / "ix.yaml"
    write_ixref_yaml(parsed, str(out))
    with open(out) as f:
        reloaded = yaml.safe_load(f)
    assert reloaded == parsed


def test_yaml_writer_creates_parent_dir(ixref_temp_path, tmp_path):
    parsed = parse_ixref(ixref_temp_path)
    nested = tmp_path / "a" / "b" / "ix.yaml"
    write_ixref_yaml(parsed, str(nested))
    assert nested.exists()


# =====================================================================
# Dummy dispatcher
# =====================================================================

def test_run_dummy_copies_fixture(ixref_temp_path, tmp_path):
    dst = tmp_path / "iXref.temp"
    run_dummy_ixref(svdb_dir=None, ixref_path=str(dst),
                    dummy_source=ixref_temp_path)
    assert dst.exists()
    assert dst.read_text() == open(ixref_temp_path).read()


def test_run_dummy_no_op_when_src_eq_dst(ixref_temp_path):
    """Same path on both sides should not raise or duplicate-write."""
    run_dummy_ixref(svdb_dir=None, ixref_path=ixref_temp_path,
                    dummy_source=ixref_temp_path)


def test_run_dummy_missing_source_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        run_dummy_ixref(svdb_dir=None,
                        ixref_path=str(tmp_path / "out.ixf"),
                        dummy_source=str(tmp_path / "missing.ixf"))


# =====================================================================
# extract_ixref orchestrator
# =====================================================================

def test_extract_ixref_dummy_mode_end_to_end(ixref_temp_path, tmp_path):
    out = tmp_path / "iXref.temp"
    parsed = extract_ixref(
        mode='dummy',
        svdb_dir='/nonexistent',  # ignored in dummy mode
        ixref_path=str(out),
        dummy_source=ixref_temp_path,
    )
    assert out.exists()
    assert parsed['cell']['layout_name'] == 'INV_N5_P7'
    assert len(parsed['devices']) == 2


def test_extract_ixref_unknown_mode_raises(tmp_path):
    with pytest.raises(ValueError, match="unknown mode"):
        extract_ixref(mode='nonsense', svdb_dir=None,
                      ixref_path=str(tmp_path / "x"))


def test_extract_ixref_dummy_mode_requires_source(tmp_path):
    with pytest.raises(ValueError, match="requires dummy_source"):
        extract_ixref(mode='dummy', svdb_dir='/x',
                      ixref_path=str(tmp_path / "x"),
                      dummy_source=None)


def test_extract_ixref_calibre_mode_requires_svdb(tmp_path):
    with pytest.raises(ValueError, match="requires svdb_dir"):
        extract_ixref(mode='calibre', svdb_dir=None,
                      ixref_path=str(tmp_path / "x"))


# =====================================================================
# Real-mode dispatcher (mocked subprocess)
# =====================================================================

class _FakeCompleted:
    def __init__(self, returncode=0, stdout='', stderr=''):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_run_calibre_missing_binary_raises(tmp_path):
    with patch('io_adapters.calibre_query.shutil.which', return_value=None):
        with pytest.raises(CalibreNotFoundError, match="not found on PATH"):
            run_calibre_ixref(str(tmp_path), str(tmp_path / "out.ixf"))


def test_run_calibre_invalid_svdb_raises(tmp_path):
    with patch('io_adapters.calibre_query.shutil.which',
               return_value='/usr/bin/calibre'):
        with pytest.raises(CalibreQueryError, match="SVDB directory not found"):
            run_calibre_ixref(str(tmp_path / "no_such_dir"),
                              str(tmp_path / "out.ixf"))


def test_run_calibre_subprocess_invocation(tmp_path, ixref_temp_path):
    """Subprocess is invoked with the right args and stdin commands."""
    svdb = tmp_path / "svdb_dir"
    svdb.mkdir()
    out = tmp_path / "out.ixf"
    captured = {}

    def fake_run(cmd, **kwargs):
        captured['cmd'] = cmd
        captured['input'] = kwargs.get('input')
        captured['kwargs'] = kwargs
        # Simulate Calibre writing the output file.
        shutil.copyfile(ixref_temp_path, str(out))
        return _FakeCompleted(returncode=0)

    with patch('io_adapters.calibre_query.shutil.which',
               return_value='/usr/bin/calibre'), \
         patch('io_adapters.calibre_query.subprocess.run', side_effect=fake_run):
        run_calibre_ixref(str(svdb), str(out))

    assert captured['cmd'] == ['calibre', '-query', str(svdb)]
    assert captured['input'] == (
        f"INSTANCE XREF WRITE {out}\n"
        f"EXIT\n"
    )
    assert captured['kwargs']['capture_output'] is True
    assert captured['kwargs']['text'] is True


def test_run_calibre_nonzero_exit_raises(tmp_path):
    svdb = tmp_path / "svdb_dir"
    svdb.mkdir()
    with patch('io_adapters.calibre_query.shutil.which',
               return_value='/usr/bin/calibre'), \
         patch('io_adapters.calibre_query.subprocess.run',
               return_value=_FakeCompleted(returncode=2,
                                           stdout='out', stderr='err')):
        with pytest.raises(CalibreQueryError, match="exited 2"):
            run_calibre_ixref(str(svdb), str(tmp_path / "x.ixf"))


def test_run_calibre_timeout_raises(tmp_path):
    svdb = tmp_path / "svdb_dir"
    svdb.mkdir()

    def fake_run(*a, **kw):
        raise subprocess.TimeoutExpired(cmd='calibre', timeout=1)

    with patch('io_adapters.calibre_query.shutil.which',
               return_value='/usr/bin/calibre'), \
         patch('io_adapters.calibre_query.subprocess.run',
               side_effect=fake_run):
        with pytest.raises(CalibreQueryError, match="timed out"):
            run_calibre_ixref(str(svdb), str(tmp_path / "x.ixf"),
                              timeout=1.0)


def test_run_calibre_no_output_file_raises(tmp_path):
    svdb = tmp_path / "svdb_dir"
    svdb.mkdir()
    with patch('io_adapters.calibre_query.shutil.which',
               return_value='/usr/bin/calibre'), \
         patch('io_adapters.calibre_query.subprocess.run',
               return_value=_FakeCompleted(returncode=0)):
        with pytest.raises(CalibreQueryError, match="did not"):
            run_calibre_ixref(str(svdb), str(tmp_path / "x.ixf"))


def test_extract_ixref_calibre_mode_end_to_end(tmp_path, ixref_temp_path):
    """Full extract_ixref(mode='calibre') with mocked subprocess."""
    svdb = tmp_path / "svdb_dir"
    svdb.mkdir()
    out = tmp_path / "iXref.temp"

    def fake_run(cmd, **kwargs):
        shutil.copyfile(ixref_temp_path, str(out))
        return _FakeCompleted(returncode=0)

    with patch('io_adapters.calibre_query.shutil.which',
               return_value='/usr/bin/calibre'), \
         patch('io_adapters.calibre_query.subprocess.run',
               side_effect=fake_run):
        parsed = extract_ixref(
            mode='calibre',
            svdb_dir=str(svdb),
            ixref_path=str(out),
        )
    assert parsed['cell']['layout_name'] == 'INV_N5_P7'
    assert len(parsed['devices']) == 2


# =====================================================================
# Generator vs committed-fixture parity
# =====================================================================

def test_generator_matches_committed_fixture(ixref_temp_path, tmp_path):
    """``generate_calibre_ixref`` reproduces the committed fixture byte-for-byte.

    Drift between the parametric generator and the hand-committed
    fixture is the most likely failure mode when fin counts are bumped
    in future fixture regenerations.
    """
    from dummy.gen_buffer_layout import (
        generate_inverter_layout, generate_calibre_ixref,
    )

    layout = generate_inverter_layout(nmos_nfin=5, pmos_nfin=7)
    out = tmp_path / "iXref.temp"
    generate_calibre_ixref(layout, str(out))

    assert out.read_text() == open(ixref_temp_path).read()


def test_pipeline_legacy_site_config_without_calibre_block(tmp_path,
                                                            fixture_dir):
    """A site_config.yaml that predates Stage 1.5 (no ``calibre:`` block)
    must still run end-to-end. The pipeline falls back to the repo's
    default dummy iXref fixture."""
    legacy_cfg = tmp_path / "legacy_site_config.yaml"
    legacy_cfg.write_text(f"""\
tech:
  drc_rules:         {os.path.join('..', '..', 'tech', 'drc_rules.yaml')}
  layer_map:         {os.path.join('..', '..', 'tech', 'layer_map.yaml')}
inputs:
  original_cdl:   {os.path.join(fixture_dir, 'buffer_original.cdl')}
  modified_cdl:   {os.path.join(fixture_dir, 'buffer_target.cdl')}
  device_query:   {os.path.join(fixture_dir, 'calibre_device_query.json')}
  net_query:      {os.path.join(fixture_dir, 'calibre_net_query.json')}
  bbox_by_layer:  {os.path.join(fixture_dir, 'bbox_by_layer.json')}
  layout_json:    {os.path.join(fixture_dir, 'buffer_original.json')}
  target_json:    {os.path.join(fixture_dir, 'buffer_target.json')}
output:
  dir:            {tmp_path / 'out'}
""")
    # Resolve through the same loader the pipeline uses; verify the
    # ``calibre`` block is absent before defaults are filled in, and
    # that ``mode`` falls back to ``dummy`` while ``dummy_ixref`` stays
    # ``None`` (forcing the pipeline to provide its own default).
    from tech.config_loader import load_site_config
    cfg = load_site_config(str(legacy_cfg))
    assert cfg['calibre']['mode'] == 'dummy'
    assert cfg['calibre'].get('dummy_ixref') is None

    # And the pipeline-side fallback must yield a real fixture path.
    repo_root = os.path.join(os.path.dirname(__file__), '..', '..')
    fallback = os.path.join(
        repo_root, 'pipeline', '..', 'dummy', 'fixtures', 'iXref.temp')
    assert os.path.exists(fallback)


def test_yaml_matches_committed_reference(ixref_temp_path, fixture_dir,
                                           tmp_path):
    """Round-trip the committed iXref through the writer; result equals
    the committed ``dummy/fixtures/ixref.yaml`` reference copy.

    Catches drift between the parser/writer output and the staged
    reference (a regression here would mean either the parser changed
    its output schema or the YAML emitter changed its formatting).
    """
    parsed = parse_ixref(ixref_temp_path)
    out = tmp_path / "ix.yaml"
    write_ixref_yaml(parsed, str(out))

    reference = os.path.join(fixture_dir, 'ixref.yaml')
    with open(reference) as f:
        ref_dict = yaml.safe_load(f)
    with open(out) as f:
        written_dict = yaml.safe_load(f)
    assert written_dict == ref_dict
