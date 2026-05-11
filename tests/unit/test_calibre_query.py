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
    parse_nxref,
    parse_net_names,
    join_net_xref,
    write_net_xref_yaml,
    run_dummy_nxref,
    run_dummy_net_names,
    run_calibre_nxref,
    run_calibre_net_names,
    extract_net_xref,
    parse_device_info,
    write_device_info_yaml,
    run_dummy_device_info,
    run_calibre_device_info,
    extract_device_info,
    parse_net_shapes,
    write_net_shapes_yaml,
    run_dummy_net_shapes,
    run_calibre_net_shapes,
    extract_net_shapes,
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
    with open(out, encoding='utf-8') as f:
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
    assert dst.read_text() == open(ixref_temp_path, encoding='utf-8').read()


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

    assert out.read_text() == open(ixref_temp_path, encoding='utf-8').read()


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
    with open(reference, encoding='utf-8') as f:
        ref_dict = yaml.safe_load(f)
    with open(out, encoding='utf-8') as f:
        written_dict = yaml.safe_load(f)
    assert written_dict == ref_dict


# =====================================================================
# nXref parser
# =====================================================================

def _write_nxref(tmp_path, body, header=None):
    if header is None:
        header = (
            "# SVDB: Net Cross Reference (nxf) (File format 1)\n"
            "# SVDB: Layout Primary CELL\n"
            "# SVDB: End of header.\n"
        )
    path = tmp_path / "in.nxf"
    path.write_text(header + body)
    return str(path)


def test_parse_nxref_committed_fixture(nxref_temp_path):
    """Committed dummy nXref.temp parses into the expected schema."""
    parsed = parse_nxref(nxref_temp_path)
    assert parsed['cell'] == {
        'layout_name':       'INV_N5_P7',
        'source_name':       'INV_N5_P7',
        'layout_pin_count':  4,
        'source_pin_count':  4,
    }
    nets = {n['layout_net']: n for n in parsed['nets']}
    assert set(nets) == {'VDD', 'VSS', 'IN', 'OUT'}
    for n in parsed['nets']:
        # Inverter cell has only external pins → layout name == source name.
        assert n['source_net'] == n['layout_net']
        assert n['layout_idx'] == 0
        assert n['source_idx'] == 0


def test_parse_nxref_renumbered_internal_net(tmp_path):
    """Schematic 'net9' renumbered to LVS layout-side '2' (the user's
    canonical example for an internal net)."""
    body = "% BUFLVT 6 BUFLVT 6\n0 VDD 0 VDD\n0 2 0 net9\n"
    path = _write_nxref(tmp_path, body)
    parsed = parse_nxref(path)
    assert parsed['cell']['layout_pin_count'] == 6
    by_src = {n['source_net']: n for n in parsed['nets']}
    assert by_src['net9']['layout_net'] == '2'
    assert by_src['VDD']['layout_net'] == 'VDD'


def test_parse_nxref_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        parse_nxref(str(tmp_path / "nope.nxf"))


def test_parse_nxref_missing_terminator_raises(tmp_path):
    path = tmp_path / "bad.nxf"
    path.write_text(
        "# SVDB: Net Cross Reference (nxf) (File format 1)\n"
        "% CELL 4 CELL 4\n0 VDD 0 VDD\n"
    )
    with pytest.raises(ValueError, match="missing required terminator"):
        parse_nxref(str(path))


def test_parse_nxref_empty_body_raises(tmp_path):
    path = _write_nxref(tmp_path, "")
    with pytest.raises(ValueError, match="body is empty"):
        parse_nxref(path)


def test_parse_nxref_summary_without_percent_prefix(tmp_path):
    """The ``%`` prefix is conventional but optional; parser tolerates
    either to handle real-world Calibre output variations."""
    body = "CELL 4 CELL 4\n0 VDD 0 VDD\n"
    path = _write_nxref(tmp_path, body)
    parsed = parse_nxref(path)
    assert parsed['cell']['layout_name'] == 'CELL'


def test_parse_nxref_malformed_summary_raises(tmp_path):
    body = "% CELL 4 CELL\n0 VDD 0 VDD\n"
    path = _write_nxref(tmp_path, body)
    with pytest.raises(ValueError, match="cell-summary line malformed"):
        parse_nxref(path)


def test_parse_nxref_summary_non_int_pin_count_raises(tmp_path):
    body = "% CELL four CELL 4\n0 VDD 0 VDD\n"
    path = _write_nxref(tmp_path, body)
    with pytest.raises(ValueError, match="pin counts not int"):
        parse_nxref(path)


def test_parse_nxref_malformed_net_row_raises(tmp_path):
    body = "% CELL 4 CELL 4\n0 VDD 0 VDD EXTRA\n"
    path = _write_nxref(tmp_path, body)
    with pytest.raises(ValueError, match="net row malformed"):
        parse_nxref(path)


def test_parse_nxref_non_int_idx_raises(tmp_path):
    body = "% CELL 4 CELL 4\nfoo VDD 0 VDD\n"
    path = _write_nxref(tmp_path, body)
    with pytest.raises(ValueError, match="net row index not int"):
        parse_nxref(path)


# =====================================================================
# NET NAMES parser
# =====================================================================

def _write_net_names(tmp_path, names, count=None, prefix='Net_Names 20000\nNets:\n',
                     suffix='END OF RESPONSE\n', timestamp='Jan 01 00:00:00 2026'):
    if count is None:
        count = len(names)
    path = tmp_path / "net_names.txt"
    body = prefix + f'0 0 {count} {timestamp}\n'
    body += '\n'.join(names)
    if names:
        body += '\n'
    body += suffix
    path.write_text(body)
    return str(path)


def test_parse_net_names_committed_fixture(net_names_path):
    parsed = parse_net_names(net_names_path)
    assert parsed['count'] == 4
    # Committed fixture order: IN(1), OUT(2), VSS(3), VDD(4).
    assert parsed['index_to_name'] == {1: 'IN', 2: 'OUT',
                                        3: 'VSS', 4: 'VDD'}
    assert parsed['name_to_index'] == {'IN': 1, 'OUT': 2,
                                        'VSS': 3, 'VDD': 4}


def test_parse_net_names_user_buflvt_example(tmp_path):
    """Reproduces the user's BUFLVT NET NAMES example: 19 nets where
    'I' is at index 1, 'Z' at 3, 'VSS' at 4, etc."""
    names = ['I', '2', 'Z', 'VSS', 'VDD',
             '6', '7', '8', '9', '10',
             '11', '12', '13', '14', '15',
             'VPP', 'VBB', '18', '19']
    path = _write_net_names(tmp_path, names,
                            timestamp='Feb 27 14:38:27 2026')
    parsed = parse_net_names(path)
    assert parsed['count'] == 19
    assert parsed['name_to_index']['I'] == 1
    assert parsed['name_to_index']['Z'] == 3
    assert parsed['name_to_index']['VSS'] == 4
    assert parsed['name_to_index']['VPP'] == 16


def test_parse_net_names_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        parse_net_names(str(tmp_path / "nope.txt"))


def test_parse_net_names_missing_anchor_raises(tmp_path):
    path = tmp_path / "bad.txt"
    path.write_text("Net_Names 20000\n0 0 1 ts\nIN\nEND OF RESPONSE\n")
    with pytest.raises(ValueError, match="missing 'Nets:' anchor"):
        parse_net_names(str(path))


def test_parse_net_names_missing_count_line_raises(tmp_path):
    path = tmp_path / "bad.txt"
    path.write_text("Net_Names 20000\nNets:\n")
    with pytest.raises(ValueError, match="count line missing"):
        parse_net_names(str(path))


def test_parse_net_names_malformed_count_line_raises(tmp_path):
    path = tmp_path / "bad.txt"
    path.write_text(
        "Net_Names 20000\nNets:\nNOT A COUNT LINE\nIN\nEND OF RESPONSE\n"
    )
    with pytest.raises(ValueError, match="malformed count line"):
        parse_net_names(str(path))


def test_parse_net_names_count_mismatch_raises(tmp_path):
    """Declared count=5 but only 2 names listed."""
    path = _write_net_names(tmp_path, ['IN', 'OUT'], count=5)
    with pytest.raises(ValueError, match="declared count=5"):
        parse_net_names(path)


def test_parse_net_names_no_terminator_uses_count(tmp_path):
    """If 'END OF RESPONSE' is missing the parser still reads exactly
    ``count`` names (defends against stdout truncation in practice)."""
    body = (
        "Net_Names 20000\nNets:\n0 0 2 ts\nIN\nOUT\n"
    )
    path = tmp_path / "no_terminator.txt"
    path.write_text(body)
    parsed = parse_net_names(str(path))
    assert parsed['count'] == 2


# =====================================================================
# Joiner
# =====================================================================

def test_join_net_xref_committed_fixtures(nxref_temp_path, net_names_path):
    nxref = parse_nxref(nxref_temp_path)
    nn    = parse_net_names(net_names_path)
    joined = join_net_xref(nxref, nn)
    by_src = {n['schematic_name']: n for n in joined['nets']}
    assert by_src['IN']  == {'schematic_name': 'IN',  'lvs_name': 'IN',  'lvs_index': 1}
    assert by_src['OUT'] == {'schematic_name': 'OUT', 'lvs_name': 'OUT', 'lvs_index': 2}
    assert by_src['VSS'] == {'schematic_name': 'VSS', 'lvs_name': 'VSS', 'lvs_index': 3}
    assert by_src['VDD'] == {'schematic_name': 'VDD', 'lvs_name': 'VDD', 'lvs_index': 4}
    assert joined['cell'] == nxref['cell']


def test_join_net_xref_renumbered_internal_net(tmp_path):
    """Synthetic case: schematic ``net9`` → layout ``2`` → LVS index 2.
    Encodes the user's canonical 1.2+1.3 example
    ('for inner net9, record net9, 2, 2')."""
    nxref_body = "% CELL 4 CELL 4\n0 VDD 0 VDD\n0 2 0 net9\n"
    nxref_path = _write_nxref(tmp_path, nxref_body)
    names_path = _write_net_names(tmp_path, ['VDD', '2'])
    joined = join_net_xref(parse_nxref(nxref_path),
                           parse_net_names(names_path))
    by_src = {n['schematic_name']: n for n in joined['nets']}
    assert by_src['net9'] == {'schematic_name': 'net9',
                              'lvs_name': '2', 'lvs_index': 2}
    assert by_src['VDD']  == {'schematic_name': 'VDD',
                              'lvs_name': 'VDD', 'lvs_index': 1}


def test_join_net_xref_missing_lvs_name_raises(tmp_path):
    """An nXref layout net not present in NET NAMES is a real LVS
    inconsistency — fail loud, don't paper over."""
    nxref_body = "% CELL 4 CELL 4\n0 VDD 0 VDD\n0 STRANGE 0 net9\n"
    nxref_path = _write_nxref(tmp_path, nxref_body)
    names_path = _write_net_names(tmp_path, ['VDD'])
    with pytest.raises(KeyError, match="STRANGE"):
        join_net_xref(parse_nxref(nxref_path),
                      parse_net_names(names_path))


def test_write_net_xref_yaml_roundtrip(nxref_temp_path, net_names_path,
                                        tmp_path):
    nxref = parse_nxref(nxref_temp_path)
    nn    = parse_net_names(net_names_path)
    joined = join_net_xref(nxref, nn)
    out = tmp_path / "net_xref.yaml"
    write_net_xref_yaml(joined, str(out))
    with open(out, encoding='utf-8') as f:
        reloaded = yaml.safe_load(f)
    assert reloaded == joined


def test_net_xref_yaml_matches_committed_reference(
        nxref_temp_path, net_names_path, fixture_dir, tmp_path):
    nxref = parse_nxref(nxref_temp_path)
    nn    = parse_net_names(net_names_path)
    joined = join_net_xref(nxref, nn)
    out = tmp_path / "net_xref.yaml"
    write_net_xref_yaml(joined, str(out))
    reference = os.path.join(fixture_dir, 'net_xref.yaml')
    with open(reference, encoding='utf-8') as f:
        ref_dict = yaml.safe_load(f)
    with open(out, encoding='utf-8') as f:
        written_dict = yaml.safe_load(f)
    assert written_dict == ref_dict


# =====================================================================
# Dummy net dispatchers
# =====================================================================

def test_run_dummy_nxref_copies_fixture(nxref_temp_path, tmp_path):
    dst = tmp_path / "nXref.temp"
    run_dummy_nxref(svdb_dir=None, nxref_path=str(dst),
                    dummy_source=nxref_temp_path)
    assert dst.exists()
    assert dst.read_text() == open(nxref_temp_path, encoding='utf-8').read()


def test_run_dummy_net_names_copies_fixture(net_names_path, tmp_path):
    dst = tmp_path / "net_names.txt"
    run_dummy_net_names(svdb_dir=None, net_names_path=str(dst),
                        dummy_source=net_names_path)
    assert dst.exists()
    assert dst.read_text() == open(net_names_path, encoding='utf-8').read()


def test_run_dummy_nxref_missing_source_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        run_dummy_nxref(svdb_dir=None,
                        nxref_path=str(tmp_path / "out.nxf"),
                        dummy_source=str(tmp_path / "missing.nxf"))


def test_run_dummy_net_names_missing_source_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        run_dummy_net_names(svdb_dir=None,
                            net_names_path=str(tmp_path / "out.txt"),
                            dummy_source=str(tmp_path / "missing.txt"))


# =====================================================================
# extract_net_xref orchestrator
# =====================================================================

def test_extract_net_xref_dummy_mode_end_to_end(
        nxref_temp_path, net_names_path, tmp_path):
    nxref_out = tmp_path / "nXref.temp"
    nn_out    = tmp_path / "net_names.txt"
    joined = extract_net_xref(
        mode='dummy',
        svdb_dir='/nonexistent',
        nxref_path=str(nxref_out),
        net_names_path=str(nn_out),
        dummy_nxref_source=nxref_temp_path,
        dummy_net_names_source=net_names_path,
    )
    assert nxref_out.exists()
    assert nn_out.exists()
    assert joined['cell']['layout_name'] == 'INV_N5_P7'
    assert len(joined['nets']) == 4
    assert all('lvs_index' in n for n in joined['nets'])


def test_extract_net_xref_unknown_mode_raises(tmp_path):
    with pytest.raises(ValueError, match="unknown mode"):
        extract_net_xref(mode='gibberish', svdb_dir=None,
                         nxref_path=str(tmp_path / "x"),
                         net_names_path=str(tmp_path / "y"))


def test_extract_net_xref_dummy_mode_requires_sources(tmp_path):
    with pytest.raises(ValueError, match="requires both"):
        extract_net_xref(mode='dummy', svdb_dir=None,
                         nxref_path=str(tmp_path / "x"),
                         net_names_path=str(tmp_path / "y"))


def test_extract_net_xref_calibre_mode_requires_svdb(tmp_path):
    with pytest.raises(ValueError, match="requires svdb_dir"):
        extract_net_xref(mode='calibre', svdb_dir=None,
                         nxref_path=str(tmp_path / "x"),
                         net_names_path=str(tmp_path / "y"))


# =====================================================================
# Real-mode dispatchers (mocked subprocess) — nXref + NET NAMES
# =====================================================================

def test_run_calibre_nxref_subprocess_invocation(
        tmp_path, nxref_temp_path):
    svdb = tmp_path / "svdb_dir"
    svdb.mkdir()
    out = tmp_path / "out.nxf"
    captured = {}

    def fake_run(cmd, **kwargs):
        captured['cmd'] = cmd
        captured['input'] = kwargs.get('input')
        shutil.copyfile(nxref_temp_path, str(out))
        return _FakeCompleted(returncode=0)

    with patch('io_adapters.calibre_query.shutil.which',
               return_value='/usr/bin/calibre'), \
         patch('io_adapters.calibre_query.subprocess.run',
               side_effect=fake_run):
        run_calibre_nxref(str(svdb), str(out))

    assert captured['cmd'] == ['calibre', '-query', str(svdb)]
    assert captured['input'] == f"NET XREF WRITE {out}\nEXIT\n"


def test_run_calibre_nxref_missing_binary_raises(tmp_path):
    with patch('io_adapters.calibre_query.shutil.which', return_value=None):
        with pytest.raises(CalibreNotFoundError):
            run_calibre_nxref(str(tmp_path), str(tmp_path / "x.nxf"))


def test_run_calibre_nxref_no_output_file_raises(tmp_path):
    svdb = tmp_path / "svdb_dir"
    svdb.mkdir()
    with patch('io_adapters.calibre_query.shutil.which',
               return_value='/usr/bin/calibre'), \
         patch('io_adapters.calibre_query.subprocess.run',
               return_value=_FakeCompleted(returncode=0)):
        with pytest.raises(CalibreQueryError, match="did not"):
            run_calibre_nxref(str(svdb), str(tmp_path / "x.nxf"))


def test_run_calibre_ixref_rejects_stale_output(tmp_path):
    """Pre-existing iXref.temp from a prior run must be deleted before
    invoking Calibre, so the post-subprocess existence check catches
    Calibre exiting 0 without rewriting (e.g., query-version mismatch
    or silently ignored output path)."""
    svdb = tmp_path / "svdb_dir"
    svdb.mkdir()
    out = tmp_path / "iXref.temp"
    out.write_text("STALE CONTENT FROM PRIOR RUN\n")

    seen_during_subprocess = {}

    def fake_run(cmd, **kwargs):
        # By the time the subprocess is invoked, the stale file must
        # already be gone — otherwise a Calibre that silently no-ops
        # would let stale data through.
        seen_during_subprocess['out_exists'] = out.exists()
        return _FakeCompleted(returncode=0)

    with patch('io_adapters.calibre_query.shutil.which',
               return_value='/usr/bin/calibre'), \
         patch('io_adapters.calibre_query.subprocess.run',
               side_effect=fake_run):
        with pytest.raises(CalibreQueryError, match="did not"):
            run_calibre_ixref(str(svdb), str(out))
    assert seen_during_subprocess['out_exists'] is False


def test_run_calibre_nxref_rejects_stale_output(tmp_path):
    """Same stale-output protection as ixref — required so a Calibre
    silent failure can't leak stale nets into the join with NET NAMES."""
    svdb = tmp_path / "svdb_dir"
    svdb.mkdir()
    out = tmp_path / "nXref.temp"
    out.write_text("STALE CONTENT FROM PRIOR RUN\n")

    seen_during_subprocess = {}

    def fake_run(cmd, **kwargs):
        seen_during_subprocess['out_exists'] = out.exists()
        return _FakeCompleted(returncode=0)

    with patch('io_adapters.calibre_query.shutil.which',
               return_value='/usr/bin/calibre'), \
         patch('io_adapters.calibre_query.subprocess.run',
               side_effect=fake_run):
        with pytest.raises(CalibreQueryError, match="did not"):
            run_calibre_nxref(str(svdb), str(out))
    assert seen_during_subprocess['out_exists'] is False


def test_run_calibre_net_names_subprocess_invocation(
        tmp_path, net_names_path):
    svdb = tmp_path / "svdb_dir"
    svdb.mkdir()
    out = tmp_path / "out.txt"
    captured = {}

    fake_stdout = (
        "Some leading interactive banner...\n"
        + open(net_names_path, encoding='utf-8').read()
        + "\nQuery server exiting.\n"
    )

    def fake_run(cmd, **kwargs):
        captured['cmd'] = cmd
        captured['input'] = kwargs.get('input')
        return _FakeCompleted(returncode=0, stdout=fake_stdout)

    with patch('io_adapters.calibre_query.shutil.which',
               return_value='/usr/bin/calibre'), \
         patch('io_adapters.calibre_query.subprocess.run',
               side_effect=fake_run):
        run_calibre_net_names(str(svdb), str(out))

    assert captured['cmd'] == ['calibre', '-query', str(svdb)]
    assert captured['input'] == "NET NAMES\nEXIT\n"
    # Captured block is parseable and contains the same nets.
    parsed = parse_net_names(str(out))
    assert parsed['count'] == 4


def test_run_calibre_net_names_missing_block_raises(tmp_path):
    """If stdout doesn't contain a 'Net_Names' header, fail loud."""
    svdb = tmp_path / "svdb_dir"
    svdb.mkdir()
    with patch('io_adapters.calibre_query.shutil.which',
               return_value='/usr/bin/calibre'), \
         patch('io_adapters.calibre_query.subprocess.run',
               return_value=_FakeCompleted(returncode=0,
                                            stdout='garbage\n')):
        with pytest.raises(CalibreQueryError, match="Net_Names"):
            run_calibre_net_names(str(svdb), str(tmp_path / "x.txt"))


def test_run_calibre_net_names_missing_terminator_raises(tmp_path):
    svdb = tmp_path / "svdb_dir"
    svdb.mkdir()
    truncated = "Net_Names 20000\nNets:\n0 0 1 ts\nIN\n"
    with patch('io_adapters.calibre_query.shutil.which',
               return_value='/usr/bin/calibre'), \
         patch('io_adapters.calibre_query.subprocess.run',
               return_value=_FakeCompleted(returncode=0, stdout=truncated)):
        with pytest.raises(CalibreQueryError, match="END OF RESPONSE"):
            run_calibre_net_names(str(svdb), str(tmp_path / "x.txt"))


def test_extract_net_xref_calibre_mode_end_to_end(
        tmp_path, nxref_temp_path, net_names_path):
    """Full calibre-mode path with mocked subprocess for both queries."""
    svdb = tmp_path / "svdb_dir"
    svdb.mkdir()
    nxref_out = tmp_path / "out.nxf"
    nn_out    = tmp_path / "out.txt"

    fake_stdout_net_names = open(net_names_path, encoding='utf-8').read()

    def fake_run(cmd, **kwargs):
        stdin = kwargs.get('input', '')
        if 'NET XREF WRITE' in stdin:
            shutil.copyfile(nxref_temp_path, str(nxref_out))
            return _FakeCompleted(returncode=0)
        elif 'NET NAMES' in stdin:
            return _FakeCompleted(returncode=0, stdout=fake_stdout_net_names)
        return _FakeCompleted(returncode=1, stderr='unexpected stdin')

    with patch('io_adapters.calibre_query.shutil.which',
               return_value='/usr/bin/calibre'), \
         patch('io_adapters.calibre_query.subprocess.run',
               side_effect=fake_run):
        joined = extract_net_xref(
            mode='calibre',
            svdb_dir=str(svdb),
            nxref_path=str(nxref_out),
            net_names_path=str(nn_out),
        )
    assert len(joined['nets']) == 4
    assert {n['lvs_index'] for n in joined['nets']} == {1, 2, 3, 4}


# =====================================================================
# Generator vs committed-fixture parity (nXref + NET NAMES)
# =====================================================================

def test_nxref_generator_matches_committed_fixture(
        nxref_temp_path, tmp_path):
    """``generate_calibre_nxref`` reproduces the committed fixture
    byte-for-byte. Drift detector for fin-count regen scenarios."""
    from dummy.gen_buffer_layout import (
        generate_inverter_layout, generate_calibre_nxref,
    )
    layout = generate_inverter_layout(nmos_nfin=5, pmos_nfin=7)
    out = tmp_path / "nXref.temp"
    generate_calibre_nxref(layout, str(out))
    assert out.read_text() == open(nxref_temp_path, encoding='utf-8').read()


def test_net_names_generator_matches_committed_fixture(
        net_names_path, tmp_path):
    from dummy.gen_buffer_layout import (
        generate_inverter_layout, generate_calibre_net_names,
    )
    layout = generate_inverter_layout(nmos_nfin=5, pmos_nfin=7)
    out = tmp_path / "net_names.txt"
    generate_calibre_net_names(layout, str(out),
                                timestamp='May 07 03:00:00 2026')
    assert out.read_text() == open(net_names_path, encoding='utf-8').read()


# =====================================================================
# DEVICE INFO parser
# =====================================================================

def _write_device_info(tmp_path,
                        seed_layer='ngate_lvt',
                        n_metadata=11,
                        metadata_lines=None,
                        layer_blocks=None,
                        precision=20000,
                        timestamp='May 07 03:00:00 2026'):
    """Build a synthetic DEVICE INFO response file.

    ``metadata_lines`` defaults to 9 lines (4 pin nets + 5 properties)
    so the total block lands at n_metadata=11 (1 device_type +
    9 + seed_layer).

    ``layer_blocks`` is a list of ``(layer_name, [list_of_vertex_lists])``;
    if None, a single ngate_lvt with one 4-vertex shape is used.
    """
    if metadata_lines is None:
        metadata_lines = ['IN', 'OUT', 'VSS', 'VSS',
                          '2e-08', '1.25e-07', '5', '1', '1']
    if layer_blocks is None:
        layer_blocks = [
            (seed_layer, [[(560, 880), (3040, 880),
                            (3040, 1280), (560, 1280)]]),
        ]

    lines = [f'Device_Info {precision}', 'Info:',
             f'0 0 {n_metadata} {timestamp}', '0']
    lines.extend(metadata_lines)
    # First layer name is the last metadata line.
    lines.append(layer_blocks[0][0])
    for li, (name, shapes) in enumerate(layer_blocks):
        if li > 0:
            lines.append(name)
        lines.append(f'{len(shapes)} 1 0 {timestamp}')
        for si, verts in enumerate(shapes, start=1):
            lines.append(f'p {si} {len(verts)}')
            for y, x in verts:
                lines.append(f'{y} {x}')
    lines.append('END OF RESPONSE')

    path = tmp_path / 'device_info.txt'
    path.write_text('\n'.join(lines) + '\n')
    return str(path)


def test_parse_device_info_committed_M0(device_info_M0_path):
    """Committed M0 dummy parses into the expected schema and bbox."""
    parsed = parse_device_info(device_info_M0_path)
    assert parsed['precision'] == 20000
    assert parsed['device_type_number'] == 0
    assert len(parsed['layers']) == 1
    layer = parsed['layers'][0]
    assert layer['name'] == 'ngate_lvt'
    assert len(layer['shapes']) == 1
    bbox = layer['shapes'][0]['bbox_um']
    # 1 unit = 0.05 nm = 5e-5 um, so /20000 yields um directly.
    assert bbox == {'x1': 0.044, 'y1': 0.0275,
                    'x2': 0.064, 'y2': 0.1525}


def test_parse_device_info_committed_M1(device_info_M1_path):
    parsed = parse_device_info(device_info_M1_path)
    assert parsed['device_type_number'] == 1
    layer = parsed['layers'][0]
    assert layer['name'] == 'pgate_lvt'
    bbox = layer['shapes'][0]['bbox_um']
    assert bbox == {'x1': 0.044, 'y1': 0.2275,
                    'x2': 0.064, 'y2': 0.4025}


def test_parse_device_info_metadata_block_opaque(device_info_M0_path):
    """Pin nets and property values stay in ``metadata_lines`` as raw
    strings (we don't know per-device-type pin/property counts)."""
    parsed = parse_device_info(device_info_M0_path)
    assert parsed['metadata_lines'] == [
        'IN', 'OUT', 'VSS', 'VSS',
        '2e-08', '1.25e-07', '5', '1', '1',
    ]


def test_parse_device_info_user_buflvt_example(tmp_path):
    """Reproduces the user's BUFLVT DEVICE INFO example: pins
    [I, 2, VSS, VBB], 5 properties, ngate_lvt with one 4-vertex
    shape at (1800,630)..(1800,1890)."""
    path = _write_device_info(
        tmp_path,
        n_metadata=11,
        metadata_lines=['I', '2', 'VSS', 'VBB',
                        '9e-09', '4e-08', '1', '2', '1'],
        layer_blocks=[(
            'ngate_lvt',
            [[(1800, 630), (1980, 630), (1980, 1890), (1800, 1890)]],
        )],
        timestamp='Feb 27 11:36:00 2026',
    )
    parsed = parse_device_info(path)
    assert parsed['layers'][0]['name'] == 'ngate_lvt'
    bbox = parsed['layers'][0]['shapes'][0]['bbox_um']
    # x range 630..1890 → 0.0315..0.0945 um;
    # y range 1800..1980 → 0.09..0.099 um.
    assert bbox == {'x1': 0.0315, 'y1': 0.09,
                    'x2': 0.0945, 'y2': 0.099}


def test_parse_device_info_multiple_shapes_one_layer(tmp_path):
    path = _write_device_info(
        tmp_path,
        layer_blocks=[(
            'ngate_lvt',
            [
                [(0, 0), (200, 0), (200, 100), (0, 100)],
                [(400, 0), (600, 0), (600, 100), (400, 100)],
            ],
        )],
    )
    parsed = parse_device_info(path)
    layer = parsed['layers'][0]
    assert len(layer['shapes']) == 2
    assert layer['shapes'][0]['bbox_um'] == {'x1': 0.0, 'y1': 0.0,
                                              'x2': 0.005, 'y2': 0.01}
    assert layer['shapes'][1]['bbox_um'] == {'x1': 0.0, 'y1': 0.02,
                                              'x2': 0.005, 'y2': 0.03}


def test_parse_device_info_multiple_layers(tmp_path):
    path = _write_device_info(
        tmp_path,
        layer_blocks=[
            ('ngate_lvt',
             [[(560, 880), (3040, 880), (3040, 1280), (560, 1280)]]),
            ('od_seed',
             [[(0, 0), (200, 0), (200, 100), (0, 100)]]),
        ],
    )
    parsed = parse_device_info(path)
    assert [l['name'] for l in parsed['layers']] == ['ngate_lvt',
                                                       'od_seed']
    assert len(parsed['layers'][1]['shapes']) == 1


def test_parse_device_info_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        parse_device_info(str(tmp_path / 'nope.txt'))


def test_parse_device_info_missing_header_raises(tmp_path):
    path = tmp_path / 'bad.txt'
    path.write_text('Info:\n0 0 1 ts\n0\nngate_lvt\n'
                    '1 1 0 ts\np 1 4\n0 0\n10 0\n10 10\n0 10\n'
                    'END OF RESPONSE\n')
    with pytest.raises(ValueError, match="missing 'Device_Info'"):
        parse_device_info(str(path))


def test_parse_device_info_missing_info_anchor_raises(tmp_path):
    path = tmp_path / 'bad.txt'
    path.write_text('Device_Info 20000\n0 0 1 ts\n0\nngate_lvt\n'
                    '1 1 0 ts\np 1 4\n0 0\n10 0\n10 10\n0 10\n'
                    'END OF RESPONSE\n')
    with pytest.raises(ValueError, match="missing 'Info:' anchor"):
        parse_device_info(str(path))


def test_parse_device_info_malformed_count_line_raises(tmp_path):
    path = tmp_path / 'bad.txt'
    path.write_text('Device_Info 20000\nInfo:\nNOT A COUNT\n0\n'
                    'ngate_lvt\n1 1 0 ts\np 1 4\n0 0\n10 0\n'
                    '10 10\n0 10\nEND OF RESPONSE\n')
    with pytest.raises(ValueError, match="malformed count line"):
        parse_device_info(str(path))


def test_parse_device_info_truncated_metadata_raises(tmp_path):
    """Declared n=20 but only 3 metadata lines available."""
    path = tmp_path / 'bad.txt'
    path.write_text('Device_Info 20000\nInfo:\n0 0 20 ts\n0\nIN\n'
                    'ngate_lvt\nEND OF RESPONSE\n')
    with pytest.raises(ValueError, match="metadata line"):
        parse_device_info(str(path))


def test_parse_device_info_truncated_vertex_raises(tmp_path):
    """Shape declares 4 vertices but the next non-vertex line
    (`END OF RESPONSE`) shows up after only 2 — surface the malformed
    vertex line so the caller can localise the truncation."""
    path = tmp_path / 'bad.txt'
    path.write_text('Device_Info 20000\nInfo:\n0 0 1 ts\n0\n'
                    'ngate_lvt\n1 1 0 ts\np 1 4\n0 0\n10 0\n'
                    'END OF RESPONSE\n')
    with pytest.raises(ValueError, match='vertex line malformed'):
        parse_device_info(str(path))


def test_parse_device_info_non_int_vertex_raises(tmp_path):
    path = _write_device_info(tmp_path)
    # Corrupt one vertex line.
    text = open(path, encoding='utf-8').read().replace('560 880', 'foo 880', 1)
    open(path, 'w', encoding='utf-8').write(text)
    with pytest.raises(ValueError, match="vertex tokens"):
        parse_device_info(path)


def test_parse_device_info_missing_terminator_raises(tmp_path):
    """A capture truncated after a complete shape (no END OF RESPONSE)
    must fail loud — otherwise a partial Calibre stdout-grab silently
    persists an incomplete device_info.yaml."""
    path = tmp_path / 'truncated.txt'
    path.write_text(
        'Device_Info 20000\n'
        'Info:\n'
        '0 0 1 ts\n'
        '0\n'
        'ngate_lvt\n'
        '1 1 0 ts\n'
        'p 1 4\n'
        '0 0\n'
        '10 0\n'
        '10 10\n'
        '0 10\n'
        # No END OF RESPONSE.
    )
    with pytest.raises(ValueError, match="END OF RESPONSE"):
        parse_device_info(str(path))


def test_parse_device_info_terminator_at_eof_ok(tmp_path):
    """Sanity check: terminator present (even without trailing
    newline) parses cleanly."""
    path = tmp_path / 'ok.txt'
    # n_metadata=2: device_type_number + seed_layer_name (no
    # pin nets / property values for this synthetic input).
    path.write_text(
        'Device_Info 20000\n'
        'Info:\n'
        '0 0 2 ts\n'
        '0\n'
        'ngate_lvt\n'
        '1 1 0 ts\n'
        'p 1 4\n'
        '0 0\n'
        '10 0\n'
        '10 10\n'
        '0 10\n'
        'END OF RESPONSE'
    )
    parsed = parse_device_info(str(path))
    assert parsed['layers'][0]['name'] == 'ngate_lvt'


# =====================================================================
# DEVICE INFO YAML writer
# =====================================================================

def test_device_info_yaml_matches_committed_reference(
        device_info_M0_path, device_info_M1_path,
        fixture_dir, tmp_path):
    parsed_M0 = parse_device_info(device_info_M0_path)
    parsed_M1 = parse_device_info(device_info_M1_path)
    payload = {
        'devices': [
            {'layout_inst': 'M0', **parsed_M0},
            {'layout_inst': 'M1', **parsed_M1},
        ],
    }
    out = tmp_path / 'device_info.yaml'
    write_device_info_yaml(payload, str(out))
    reference = os.path.join(fixture_dir, 'device_info.yaml')
    with open(reference, encoding='utf-8') as f:
        ref_dict = yaml.safe_load(f)
    with open(out, encoding='utf-8') as f:
        written_dict = yaml.safe_load(f)
    assert written_dict == ref_dict


def test_write_device_info_yaml_drops_metadata_and_vertices(
        device_info_M0_path, tmp_path):
    """The middle file deliberately serialises only what the user
    asked for (per-device layer name + bbox_um); raw vertices and
    opaque pin / property metadata are intentionally omitted."""
    parsed = parse_device_info(device_info_M0_path)
    out = tmp_path / 'di.yaml'
    write_device_info_yaml(
        {'devices': [{'layout_inst': 'M0', **parsed}]},
        str(out),
    )
    with open(out, encoding='utf-8') as f:
        loaded = yaml.safe_load(f)
    dev = loaded['devices'][0]
    assert 'metadata_lines' not in dev
    shape = dev['layers'][0]['shapes'][0]
    assert set(shape.keys()) == {'bbox_um'}


# =====================================================================
# Dummy + Calibre dispatchers
# =====================================================================

def test_run_dummy_device_info_copies_fixture(device_info_M0_path,
                                                tmp_path):
    dst = tmp_path / 'device_info_M0.txt'
    run_dummy_device_info(svdb_dir=None, layout_inst='M0',
                          out_path=str(dst),
                          dummy_source=device_info_M0_path)
    assert dst.exists()
    assert dst.read_text() == open(device_info_M0_path, encoding='utf-8').read()


def test_run_dummy_device_info_missing_source_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        run_dummy_device_info(svdb_dir=None, layout_inst='M0',
                              out_path=str(tmp_path / 'out.txt'),
                              dummy_source=str(tmp_path / 'missing.txt'))


def test_run_calibre_device_info_subprocess_invocation(
        tmp_path, device_info_M0_path):
    svdb = tmp_path / 'svdb_dir'
    svdb.mkdir()
    out = tmp_path / 'out.txt'
    captured = {}
    fake_stdout = (
        "Some banner...\n"
        + open(device_info_M0_path, encoding='utf-8').read()
        + "\nQuery server exiting.\n"
    )

    def fake_run(cmd, **kwargs):
        captured['cmd'] = cmd
        captured['input'] = kwargs.get('input')
        return _FakeCompleted(returncode=0, stdout=fake_stdout)

    with patch('io_adapters.calibre_query.shutil.which',
               return_value='/usr/bin/calibre'), \
         patch('io_adapters.calibre_query.subprocess.run',
               side_effect=fake_run):
        run_calibre_device_info(str(svdb), 'M0', str(out))

    assert captured['cmd'] == ['calibre', '-query', str(svdb)]
    assert captured['input'] == "DEVICE INFO M0\nEXIT\n"
    parsed = parse_device_info(str(out))
    assert parsed['layers'][0]['name'] == 'ngate_lvt'


def test_run_calibre_device_info_missing_binary_raises(tmp_path):
    with patch('io_adapters.calibre_query.shutil.which',
               return_value=None):
        with pytest.raises(CalibreNotFoundError):
            run_calibre_device_info(str(tmp_path), 'M0',
                                     str(tmp_path / 'x.txt'))


def test_run_calibre_device_info_missing_block_raises(tmp_path):
    svdb = tmp_path / 'svdb_dir'
    svdb.mkdir()
    with patch('io_adapters.calibre_query.shutil.which',
               return_value='/usr/bin/calibre'), \
         patch('io_adapters.calibre_query.subprocess.run',
               return_value=_FakeCompleted(returncode=0,
                                            stdout='garbage\n')):
        with pytest.raises(CalibreQueryError, match='Device_Info'):
            run_calibre_device_info(str(svdb), 'M0',
                                     str(tmp_path / 'x.txt'))


def test_run_calibre_device_info_missing_terminator_raises(tmp_path):
    svdb = tmp_path / 'svdb_dir'
    svdb.mkdir()
    truncated = "Device_Info 20000\nInfo:\n"
    with patch('io_adapters.calibre_query.shutil.which',
               return_value='/usr/bin/calibre'), \
         patch('io_adapters.calibre_query.subprocess.run',
               return_value=_FakeCompleted(returncode=0,
                                            stdout=truncated)):
        with pytest.raises(CalibreQueryError, match='END OF RESPONSE'):
            run_calibre_device_info(str(svdb), 'M0',
                                     str(tmp_path / 'x.txt'))


# =====================================================================
# extract_device_info orchestrator
# =====================================================================

def test_extract_device_info_dummy_mode_end_to_end(
        fixture_dir, tmp_path):
    out_dir = tmp_path / 'out'
    parsed = extract_device_info(
        mode='dummy',
        svdb_dir=None,
        layout_insts=['M0', 'M1'],
        out_dir=str(out_dir),
        dummy_source_dir=fixture_dir,
    )
    assert (out_dir / 'device_info_M0.txt').exists()
    assert (out_dir / 'device_info_M1.txt').exists()
    assert len(parsed['devices']) == 2
    assert parsed['devices'][0]['layout_inst'] == 'M0'
    assert parsed['devices'][0]['layers'][0]['name'] == 'ngate_lvt'
    assert parsed['devices'][1]['layout_inst'] == 'M1'
    assert parsed['devices'][1]['layers'][0]['name'] == 'pgate_lvt'


def test_extract_device_info_calibre_mode_end_to_end(
        tmp_path, device_info_M0_path, device_info_M1_path):
    svdb = tmp_path / 'svdb_dir'
    svdb.mkdir()
    out_dir = tmp_path / 'out'
    payloads = {
        'M0': open(device_info_M0_path, encoding='utf-8').read(),
        'M1': open(device_info_M1_path, encoding='utf-8').read(),
    }

    def fake_run(cmd, **kwargs):
        stdin = kwargs.get('input', '')
        for inst, payload in payloads.items():
            if f'DEVICE INFO {inst}' in stdin:
                return _FakeCompleted(returncode=0, stdout=payload)
        return _FakeCompleted(returncode=1, stderr='unexpected stdin')

    with patch('io_adapters.calibre_query.shutil.which',
               return_value='/usr/bin/calibre'), \
         patch('io_adapters.calibre_query.subprocess.run',
               side_effect=fake_run):
        parsed = extract_device_info(
            mode='calibre', svdb_dir=str(svdb),
            layout_insts=['M0', 'M1'],
            out_dir=str(out_dir),
        )
    assert parsed['devices'][0]['layers'][0]['name'] == 'ngate_lvt'
    assert parsed['devices'][1]['layers'][0]['name'] == 'pgate_lvt'


def test_extract_device_info_unknown_mode_raises(tmp_path):
    with pytest.raises(ValueError, match='unknown mode'):
        extract_device_info(mode='gibberish', svdb_dir=None,
                            layout_insts=['M0'],
                            out_dir=str(tmp_path / 'o'))


def test_extract_device_info_dummy_mode_requires_source_dir(tmp_path):
    with pytest.raises(ValueError, match='requires dummy_source_dir'):
        extract_device_info(mode='dummy', svdb_dir=None,
                            layout_insts=['M0'],
                            out_dir=str(tmp_path / 'o'))


def test_extract_device_info_calibre_mode_requires_svdb(tmp_path):
    with pytest.raises(ValueError, match='requires svdb_dir'):
        extract_device_info(mode='calibre', svdb_dir=None,
                            layout_insts=['M0'],
                            out_dir=str(tmp_path / 'o'))


def test_extract_device_info_empty_inst_list_returns_empty(tmp_path):
    parsed = extract_device_info(
        mode='dummy', svdb_dir=None, layout_insts=[],
        out_dir=str(tmp_path / 'out'),
        dummy_source_dir=str(tmp_path),
    )
    assert parsed == {'devices': []}


# =====================================================================
# Generator vs committed-fixture parity
# =====================================================================

def test_device_info_generator_matches_committed_M0(
        device_info_M0_path, tmp_path):
    from dummy.gen_buffer_layout import (
        generate_inverter_layout, generate_calibre_device_info,
    )
    layout = generate_inverter_layout(nmos_nfin=5, pmos_nfin=7)
    out = tmp_path / 'device_info_M0.txt'
    generate_calibre_device_info(layout, 'M0', str(out),
                                  timestamp='May 07 03:00:00 2026')
    assert out.read_text() == open(device_info_M0_path, encoding='utf-8').read()


def test_device_info_generator_matches_committed_M1(
        device_info_M1_path, tmp_path):
    from dummy.gen_buffer_layout import (
        generate_inverter_layout, generate_calibre_device_info,
    )
    layout = generate_inverter_layout(nmos_nfin=5, pmos_nfin=7)
    out = tmp_path / 'device_info_M1.txt'
    generate_calibre_device_info(layout, 'M1', str(out),
                                  timestamp='May 07 03:00:00 2026')
    assert out.read_text() == open(device_info_M1_path, encoding='utf-8').read()


def test_device_info_generator_invalid_inst_raises(tmp_path):
    from dummy.gen_buffer_layout import (
        generate_inverter_layout, generate_calibre_device_info,
    )
    layout = generate_inverter_layout(nmos_nfin=5, pmos_nfin=7)
    with pytest.raises(ValueError, match='out of range'):
        generate_calibre_device_info(layout, 'M99',
                                      str(tmp_path / 'x.txt'))


# =====================================================================
# NET SHAPES parser
# =====================================================================

def _write_net_shapes(tmp_path, layer_blocks, n_metadata=1,
                       precision=20000,
                       timestamp='May 07 03:00:00 2026',
                       extra_metadata=None):
    """Build a synthetic NET SHAPES response file.

    ``layer_blocks`` is a list of ``(layer_name, [list_of_vertex_lists])``.
    """
    if extra_metadata is None:
        extra_metadata = []
    lines = [f'Net_Shapes {precision}', 'Info:',
             f'0 0 {n_metadata} {timestamp}']
    lines.extend(extra_metadata)
    lines.append(layer_blocks[0][0])
    for li, (name, shapes) in enumerate(layer_blocks):
        if li > 0:
            lines.append(name)
        lines.append(f'{len(shapes)} 1 0 {timestamp}')
        for si, verts in enumerate(shapes, start=1):
            lines.append(f'p {si} {len(verts)}')
            for y, x in verts:
                lines.append(f'{y} {x}')
    lines.append('END OF RESPONSE')
    path = tmp_path / 'net_shapes.txt'
    path.write_text('\n'.join(lines) + '\n')
    return str(path)


def test_parse_net_shapes_committed_OUT(net_shapes_OUT_path):
    """Committed OUT-net dummy parses into the expected schema and
    bbox set (2 LI bars, 1 VIA0, 1 M1)."""
    parsed = parse_net_shapes(net_shapes_OUT_path)
    assert parsed['precision'] == 20000
    by_name = {l['name']: l for l in parsed['layers']}
    assert set(by_name) == {'LI', 'VIA0', 'M1'}
    assert len(by_name['LI']['shapes']) == 2
    assert len(by_name['VIA0']['shapes']) == 1
    assert len(by_name['M1']['shapes']) == 1
    # First LI bar (NMOS drain side) — bbox in um.
    assert by_name['LI']['shapes'][0]['bbox_um'] == {
        'x1': 0.072, 'y1': 0.035,
        'x2': 0.089, 'y2': 0.203,
    }


def test_parse_net_shapes_committed_VDD_full_width_M1(
        net_shapes_VDD_path):
    """VDD power rail spans full cell width on M1 — 0.0 to 0.108 um.
    Catches a regression that would shrink the rail to its
    intersection with the device footprint."""
    parsed = parse_net_shapes(net_shapes_VDD_path)
    by_name = {l['name']: l for l in parsed['layers']}
    m1 = by_name['M1']['shapes'][0]['bbox_um']
    assert m1 == {'x1': 0.0, 'y1': 0.404,
                  'x2': 0.108, 'y2': 0.424}


def test_parse_net_shapes_user_renumbered_internal_net(tmp_path):
    """Synthetic case mirroring the user's BUFLVT example: lvs_name
    is the numeric '2' (LVS-renumbered net9). Parser doesn't care
    about the lvs_name itself — only the file structure — so the
    same shape rules apply."""
    path = _write_net_shapes(
        tmp_path,
        layer_blocks=[
            ('M1', [[(1800, 630), (1980, 630), (1980, 1890),
                     (1800, 1890)]]),
        ],
    )
    parsed = parse_net_shapes(path)
    assert parsed['layers'][0]['name'] == 'M1'
    assert parsed['layers'][0]['shapes'][0]['bbox_um'] == {
        'x1': 0.0315, 'y1': 0.09,
        'x2': 0.0945, 'y2': 0.099,
    }


def test_parse_net_shapes_multi_layer_multi_shape(tmp_path):
    path = _write_net_shapes(
        tmp_path,
        layer_blocks=[
            ('LI', [
                [(0, 0), (200, 0), (200, 100), (0, 100)],
                [(400, 0), (600, 0), (600, 100), (400, 100)],
            ]),
            ('M1', [[(0, 0), (200, 0), (200, 100), (0, 100)]]),
        ],
    )
    parsed = parse_net_shapes(path)
    assert [(l['name'], len(l['shapes'])) for l in parsed['layers']] \
        == [('LI', 2), ('M1', 1)]


def test_parse_net_shapes_missing_terminator_raises(tmp_path):
    path = tmp_path / 'truncated.txt'
    path.write_text(
        'Net_Shapes 20000\nInfo:\n0 0 1 ts\nM1\n1 1 0 ts\np 1 4\n'
        '0 0\n10 0\n10 10\n0 10\n'   # no END OF RESPONSE
    )
    with pytest.raises(ValueError, match='END OF RESPONSE'):
        parse_net_shapes(str(path))


def test_parse_net_shapes_missing_header_raises(tmp_path):
    path = tmp_path / 'bad.txt'
    path.write_text('Info:\n0 0 1 ts\nM1\n1 1 0 ts\np 1 4\n'
                    '0 0\n10 0\n10 10\n0 10\nEND OF RESPONSE\n')
    with pytest.raises(ValueError, match="missing 'Net_Shapes'"):
        parse_net_shapes(str(path))


def test_parse_net_shapes_missing_anchor_raises(tmp_path):
    path = tmp_path / 'bad.txt'
    path.write_text('Net_Shapes 20000\n0 0 1 ts\nM1\n1 1 0 ts\n'
                    'p 1 4\n0 0\n10 0\n10 10\n0 10\n'
                    'END OF RESPONSE\n')
    with pytest.raises(ValueError, match="missing 'Info:' anchor"):
        parse_net_shapes(str(path))


def test_parse_net_shapes_blank_seed_layer_raises(tmp_path):
    path = tmp_path / 'bad.txt'
    path.write_text('Net_Shapes 20000\nInfo:\n0 0 1 ts\n\n'
                    '1 1 0 ts\np 1 4\n0 0\n10 0\n10 10\n0 10\n'
                    'END OF RESPONSE\n')
    # Blank metadata lines are dropped by the loop; the file's
    # n_metadata=1 then can't supply a non-blank seed name.
    with pytest.raises(ValueError):
        parse_net_shapes(str(path))


# =====================================================================
# NET SHAPES YAML writer
# =====================================================================

def test_write_net_shapes_yaml_matches_committed_reference(
        fixture_dir, tmp_path):
    parsed = extract_net_shapes(
        mode='dummy', svdb_dir=None,
        nets=[
            {'lvs_index': 1, 'lvs_name': 'IN',  'schematic_name': 'IN'},
            {'lvs_index': 2, 'lvs_name': 'OUT', 'schematic_name': 'OUT'},
            {'lvs_index': 3, 'lvs_name': 'VSS', 'schematic_name': 'VSS'},
            {'lvs_index': 4, 'lvs_name': 'VDD', 'schematic_name': 'VDD'},
        ],
        out_dir=str(tmp_path / 'out'),
        dummy_source_dir=fixture_dir,
    )
    out = tmp_path / 'net_shapes.yaml'
    write_net_shapes_yaml(parsed, str(out))
    reference = os.path.join(fixture_dir, 'net_shapes.yaml')
    with open(reference, encoding='utf-8') as f:
        ref_dict = yaml.safe_load(f)
    with open(out, encoding='utf-8') as f:
        written_dict = yaml.safe_load(f)
    assert written_dict == ref_dict


def test_write_net_shapes_yaml_drops_vertices(net_shapes_OUT_path,
                                                tmp_path):
    parsed = parse_net_shapes(net_shapes_OUT_path)
    out = tmp_path / 'ns.yaml'
    write_net_shapes_yaml(
        {'nets': [{'lvs_index': 2, 'lvs_name': 'OUT',
                   'schematic_name': 'OUT', **parsed}]},
        str(out),
    )
    with open(out, encoding='utf-8') as f:
        loaded = yaml.safe_load(f)
    shape = loaded['nets'][0]['layers'][0]['shapes'][0]
    assert set(shape.keys()) == {'bbox_um'}


# =====================================================================
# Dummy + Calibre dispatchers (NET SHAPES)
# =====================================================================

def test_run_dummy_net_shapes_copies_fixture(net_shapes_OUT_path,
                                                tmp_path):
    dst = tmp_path / 'net_shapes_OUT.txt'
    run_dummy_net_shapes(svdb_dir=None, lvs_name='OUT',
                         out_path=str(dst),
                         dummy_source=net_shapes_OUT_path)
    assert dst.exists()
    assert dst.read_text() == open(net_shapes_OUT_path, encoding='utf-8').read()


def test_run_dummy_net_shapes_missing_source_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        run_dummy_net_shapes(svdb_dir=None, lvs_name='OUT',
                             out_path=str(tmp_path / 'out.txt'),
                             dummy_source=str(tmp_path / 'missing.txt'))


def test_run_calibre_net_shapes_subprocess_invocation(
        tmp_path, net_shapes_OUT_path):
    svdb = tmp_path / 'svdb_dir'
    svdb.mkdir()
    out = tmp_path / 'out.txt'
    captured = {}
    fake_stdout = (
        "Some banner...\n"
        + open(net_shapes_OUT_path, encoding='utf-8').read()
        + "\nQuery server exiting.\n"
    )

    def fake_run(cmd, **kwargs):
        captured['cmd'] = cmd
        captured['input'] = kwargs.get('input')
        return _FakeCompleted(returncode=0, stdout=fake_stdout)

    with patch('io_adapters.calibre_query.shutil.which',
               return_value='/usr/bin/calibre'), \
         patch('io_adapters.calibre_query.subprocess.run',
               side_effect=fake_run):
        run_calibre_net_shapes(str(svdb), 'OUT', str(out))

    assert captured['cmd'] == ['calibre', '-query', str(svdb)]
    assert captured['input'] == "NET SHAPES OUT\nEXIT\n"
    parsed = parse_net_shapes(str(out))
    by_name = {l['name']: l for l in parsed['layers']}
    assert set(by_name) == {'LI', 'VIA0', 'M1'}


def test_run_calibre_net_shapes_numeric_lvs_name_passes_through(
        tmp_path):
    """User's BUFLVT example queries `NET SHAPES 2` for the
    LVS-renumbered net9. The runner just forwards lvs_name verbatim."""
    svdb = tmp_path / 'svdb_dir'
    svdb.mkdir()
    captured = {}
    payload = (
        "Net_Shapes 20000\nInfo:\n0 0 1 ts\nM1\n"
        "1 1 0 ts\np 1 4\n0 0\n10 0\n10 10\n0 10\n"
        "END OF RESPONSE\n"
    )

    def fake_run(cmd, **kwargs):
        captured['input'] = kwargs.get('input')
        return _FakeCompleted(returncode=0, stdout=payload)

    with patch('io_adapters.calibre_query.shutil.which',
               return_value='/usr/bin/calibre'), \
         patch('io_adapters.calibre_query.subprocess.run',
               side_effect=fake_run):
        run_calibre_net_shapes(str(svdb), '2',
                                str(tmp_path / 'out.txt'))
    assert captured['input'] == "NET SHAPES 2\nEXIT\n"


def test_run_calibre_net_shapes_missing_binary_raises(tmp_path):
    with patch('io_adapters.calibre_query.shutil.which',
               return_value=None):
        with pytest.raises(CalibreNotFoundError):
            run_calibre_net_shapes(str(tmp_path), 'OUT',
                                     str(tmp_path / 'x.txt'))


def test_run_calibre_net_shapes_missing_block_raises(tmp_path):
    svdb = tmp_path / 'svdb_dir'
    svdb.mkdir()
    with patch('io_adapters.calibre_query.shutil.which',
               return_value='/usr/bin/calibre'), \
         patch('io_adapters.calibre_query.subprocess.run',
               return_value=_FakeCompleted(returncode=0,
                                            stdout='garbage\n')):
        with pytest.raises(CalibreQueryError, match='Net_Shapes'):
            run_calibre_net_shapes(str(svdb), 'OUT',
                                     str(tmp_path / 'x.txt'))


def test_run_calibre_net_shapes_missing_terminator_raises(tmp_path):
    svdb = tmp_path / 'svdb_dir'
    svdb.mkdir()
    truncated = "Net_Shapes 20000\nInfo:\n"
    with patch('io_adapters.calibre_query.shutil.which',
               return_value='/usr/bin/calibre'), \
         patch('io_adapters.calibre_query.subprocess.run',
               return_value=_FakeCompleted(returncode=0,
                                            stdout=truncated)):
        with pytest.raises(CalibreQueryError, match='END OF RESPONSE'):
            run_calibre_net_shapes(str(svdb), 'OUT',
                                     str(tmp_path / 'x.txt'))


# =====================================================================
# extract_net_shapes orchestrator
# =====================================================================

def test_extract_net_shapes_dummy_mode_end_to_end(fixture_dir,
                                                    tmp_path):
    out_dir = tmp_path / 'out'
    parsed = extract_net_shapes(
        mode='dummy', svdb_dir=None,
        nets=[
            {'lvs_index': 2, 'lvs_name': 'OUT', 'schematic_name': 'OUT'},
            {'lvs_index': 4, 'lvs_name': 'VDD', 'schematic_name': 'VDD'},
        ],
        out_dir=str(out_dir),
        dummy_source_dir=fixture_dir,
    )
    assert (out_dir / 'net_shapes_OUT.txt').exists()
    assert (out_dir / 'net_shapes_VDD.txt').exists()
    assert len(parsed['nets']) == 2
    out_net = parsed['nets'][0]
    assert out_net['lvs_index'] == 2
    assert out_net['lvs_name'] == 'OUT'
    assert out_net['schematic_name'] == 'OUT'
    assert {l['name'] for l in out_net['layers']} == {'LI', 'VIA0', 'M1'}


def test_extract_net_shapes_calibre_mode_end_to_end(
        tmp_path, net_shapes_OUT_path, net_shapes_VDD_path):
    svdb = tmp_path / 'svdb_dir'
    svdb.mkdir()
    out_dir = tmp_path / 'out'
    payloads = {
        'OUT': open(net_shapes_OUT_path, encoding='utf-8').read(),
        'VDD': open(net_shapes_VDD_path, encoding='utf-8').read(),
    }

    def fake_run(cmd, **kwargs):
        stdin = kwargs.get('input', '')
        for nm, payload in payloads.items():
            if f'NET SHAPES {nm}' in stdin:
                return _FakeCompleted(returncode=0, stdout=payload)
        return _FakeCompleted(returncode=1, stderr='unexpected stdin')

    with patch('io_adapters.calibre_query.shutil.which',
               return_value='/usr/bin/calibre'), \
         patch('io_adapters.calibre_query.subprocess.run',
               side_effect=fake_run):
        parsed = extract_net_shapes(
            mode='calibre', svdb_dir=str(svdb),
            nets=[
                {'lvs_index': 2, 'lvs_name': 'OUT',
                 'schematic_name': 'OUT'},
                {'lvs_index': 4, 'lvs_name': 'VDD',
                 'schematic_name': 'VDD'},
            ],
            out_dir=str(out_dir),
        )
    assert {n['lvs_name'] for n in parsed['nets']} == {'OUT', 'VDD'}


def test_extract_net_shapes_unknown_mode_raises(tmp_path):
    with pytest.raises(ValueError, match='unknown mode'):
        extract_net_shapes(mode='gibberish', svdb_dir=None,
                            nets=[],
                            out_dir=str(tmp_path / 'o'))


def test_extract_net_shapes_dummy_mode_requires_source_dir(tmp_path):
    with pytest.raises(ValueError, match='requires dummy_source_dir'):
        extract_net_shapes(mode='dummy', svdb_dir=None,
                            nets=[{'lvs_index': 1, 'lvs_name': 'IN',
                                    'schematic_name': 'IN'}],
                            out_dir=str(tmp_path / 'o'))


def test_extract_net_shapes_calibre_mode_requires_svdb(tmp_path):
    with pytest.raises(ValueError, match='requires svdb_dir'):
        extract_net_shapes(mode='calibre', svdb_dir=None,
                            nets=[{'lvs_index': 1, 'lvs_name': 'IN',
                                    'schematic_name': 'IN'}],
                            out_dir=str(tmp_path / 'o'))


def test_extract_net_shapes_empty_nets_returns_empty(tmp_path):
    parsed = extract_net_shapes(
        mode='dummy', svdb_dir=None, nets=[],
        out_dir=str(tmp_path / 'out'),
        dummy_source_dir=str(tmp_path),
    )
    assert parsed == {'nets': []}


# =====================================================================
# Generator parity (NET SHAPES)
# =====================================================================

def test_net_shapes_generator_matches_committed_OUT(
        net_shapes_OUT_path, tmp_path):
    from dummy.gen_buffer_layout import (
        generate_inverter_layout, generate_calibre_net_shapes,
    )
    layout = generate_inverter_layout(nmos_nfin=5, pmos_nfin=7)
    out = tmp_path / 'net_shapes_OUT.txt'
    generate_calibre_net_shapes(layout, 'OUT', str(out))
    assert out.read_text() == open(net_shapes_OUT_path, encoding='utf-8').read()


def test_net_shapes_generator_matches_committed_VDD(
        net_shapes_VDD_path, tmp_path):
    from dummy.gen_buffer_layout import (
        generate_inverter_layout, generate_calibre_net_shapes,
    )
    layout = generate_inverter_layout(nmos_nfin=5, pmos_nfin=7)
    out = tmp_path / 'net_shapes_VDD.txt'
    generate_calibre_net_shapes(layout, 'VDD', str(out))
    assert out.read_text() == open(net_shapes_VDD_path, encoding='utf-8').read()


def test_net_shapes_generator_unknown_net_raises(tmp_path):
    from dummy.gen_buffer_layout import (
        generate_inverter_layout, generate_calibre_net_shapes,
    )
    layout = generate_inverter_layout(nmos_nfin=5, pmos_nfin=7)
    with pytest.raises(ValueError, match='not in'):
        generate_calibre_net_shapes(layout, 'NOPE',
                                      str(tmp_path / 'x.txt'))
