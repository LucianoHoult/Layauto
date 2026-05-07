"""Unit tests for the Calibre iXref parser + apply_lvs_overlay xref hook."""

import os
import sys
import textwrap

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from io_adapters.lvs_xref_parser import (
    InstanceXref, XrefInstance,
    expand_ixref_pattern,
    load_xref_yaml,
    parse_ixref,
    write_xref_json,
    write_xref_yaml,
)
from io_adapters.parser import (
    apply_lvs_overlay,
    build_layout_model,
    build_shape_pool,
    parse_calibre_device_query,
    parse_calibre_net_query,
    parse_bbox_by_layer,
)


FIXTURE_DIR = os.path.join(
    os.path.dirname(__file__), '..', '..', 'dummy', 'fixtures'
)
IXREF_PATH = os.path.join(FIXTURE_DIR, 'iXref.temp')


# ----------------------------------------------------------------
# Parser
# ----------------------------------------------------------------
def test_parse_fixture_ixref_header_and_counts():
    x = parse_ixref(IXREF_PATH)
    assert x.layout_cell == 'INV_N5_P7'
    assert x.source_cell == 'INV_N5_P7'
    assert x.layout_count == 2
    assert x.source_count == 2
    # End-of-header line preserved verbatim.
    assert x.raw_header[0].startswith('# SVDB: Instance Cross Reference')
    assert x.raw_header[-1] == '# SVDB: End of header.'


def test_parse_fixture_ixref_instances_and_flags():
    x = parse_ixref(IXREF_PATH)
    names = [(i.layout_name, i.source_name, list(i.flags))
             for i in x.instances]
    assert names == [
        ('MN0', 'MMM1', ['X']),
        ('MP0', 'MMM0', []),
    ]


def test_parse_fixture_ixref_indexes():
    x = parse_ixref(IXREF_PATH)
    assert x.by_layout == {'MN0': 'MMM1', 'MP0': 'MMM0'}
    assert x.by_source == {'MMM1': 'MN0', 'MMM0': 'MP0'}


def test_parse_ignores_blank_lines_and_extra_headers(tmp_path):
    p = tmp_path / 'with_extras.temp'
    p.write_text(textwrap.dedent("""\
        # SVDB: Instance Cross Reference (ixf) (File format 1)
        # SVDB: Layout Primary FOO
        # SVDB: extra unrecognised header line
        # SVDB: End of header.

        FOO 3 BAR 3
        0 A 0 X1
        0 B 0 X2 X
        0 C 0 X3 X SWAP
    """))
    x = parse_ixref(str(p))
    assert x.layout_cell == 'FOO'
    assert x.source_cell == 'BAR'
    assert len(x.instances) == 3
    # Multiple flag tokens are all preserved.
    assert x.instances[2].flags == ['X', 'SWAP']


def test_parse_missing_cell_line_raises(tmp_path):
    p = tmp_path / 'no_cell.temp'
    p.write_text(textwrap.dedent("""\
        # SVDB: Instance Cross Reference (ixf) (File format 1)
        # SVDB: End of header.
    """))
    with pytest.raises(ValueError, match='no cell-pair line'):
        parse_ixref(str(p))


def test_parse_malformed_instance_row_raises(tmp_path):
    p = tmp_path / 'bad_inst.temp'
    p.write_text(textwrap.dedent("""\
        # SVDB: Instance Cross Reference (ixf) (File format 1)
        # SVDB: End of header.
        FOO 1 FOO 1
        0 OnlyThree
    """))
    with pytest.raises(ValueError, match='malformed'):
        parse_ixref(str(p))


def test_parse_non_integer_count_raises(tmp_path):
    p = tmp_path / 'bad_count.temp'
    p.write_text(textwrap.dedent("""\
        # SVDB: Instance Cross Reference (ixf) (File format 1)
        # SVDB: End of header.
        FOO N FOO N
    """))
    with pytest.raises(ValueError, match='non-integer'):
        parse_ixref(str(p))


def test_parse_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        parse_ixref(str(tmp_path / 'does_not_exist.temp'))


# ----------------------------------------------------------------
# Middle-file emit + round-trip
# ----------------------------------------------------------------
def test_yaml_round_trip(tmp_path):
    x = parse_ixref(IXREF_PATH)
    p = tmp_path / 'mid.yaml'
    write_xref_yaml(x, str(p))
    x2 = load_xref_yaml(str(p))
    assert x2.layout_cell == x.layout_cell
    assert x2.source_cell == x.source_cell
    assert x2.by_layout == x.by_layout
    assert x2.by_source == x.by_source
    flags2 = [list(i.flags) for i in x2.instances]
    flags1 = [list(i.flags) for i in x.instances]
    assert flags1 == flags2


def test_json_emit_creates_file(tmp_path):
    x = parse_ixref(IXREF_PATH)
    p = tmp_path / 'sub' / 'mid.json'
    out = write_xref_json(x, str(p))
    assert os.path.exists(out)
    assert os.path.getsize(out) > 0


# ----------------------------------------------------------------
# Pattern expansion
# ----------------------------------------------------------------
def test_expand_ixref_pattern_substitutes_tokens():
    from datetime import datetime
    now = datetime(2026, 5, 7, 11, 30, 0)
    out = expand_ixref_pattern(
        '/o/iXref_{cell}_{ts}.temp',
        cell='INV_N5_P7',
        now=now,
    )
    assert out == '/o/iXref_INV_N5_P7_20260507_113000.temp'


def test_expand_ixref_pattern_custom_format():
    from datetime import datetime
    now = datetime(2026, 1, 2, 3, 4, 5)
    out = expand_ixref_pattern(
        '/o/{cell}.{ts}',
        cell='X', ts_format='%Y',
        now=now,
    )
    assert out == '/o/X.2026'


# ----------------------------------------------------------------
# apply_lvs_overlay xref hook
# ----------------------------------------------------------------
def test_apply_lvs_overlay_translates_svdb_names():
    """Pin names that come from the SVDB side should round-trip
    back to the schematic name via the iXref before the per-shape
    device pick runs."""
    devices = parse_calibre_device_query(
        os.path.join(FIXTURE_DIR, 'calibre_device_query.json')
    )
    bbox_data = parse_bbox_by_layer(
        os.path.join(FIXTURE_DIR, 'bbox_by_layer.json')
    )
    net_data = parse_calibre_net_query(
        os.path.join(FIXTURE_DIR, 'calibre_net_query.json')
    )
    # Rewrite VSS pin entries to use the SVDB-side names so the
    # overlay only succeeds if the xref translation kicks in.
    svdb_renames = {'MN0': 'MMM1', 'MP0': 'MMM0'}
    for nd in net_data.values():
        nd['pins'] = [(svdb_renames.get(d, d), pin)
                      for d, pin in nd['pins']]

    pool = build_shape_pool(bbox_data)
    xref = parse_ixref(IXREF_PATH)
    matched = apply_lvs_overlay(pool, net_data, devices, xref=xref)
    # Sanity: every net got at least one shape stamped.
    assert set(matched.keys()) >= {'VSS', 'VDD', 'IN', 'OUT'}
    # Ownership stamped using schematic names, not SVDB names.
    owners = {sr.device_id for sr in pool if sr.device_id}
    assert owners == {'MN0', 'MP0'}
    # No SVDB-side leakage.
    assert 'MMM0' not in owners
    assert 'MMM1' not in owners


def test_apply_lvs_overlay_no_xref_keeps_old_behaviour():
    """Without xref, apply_lvs_overlay matches shapes directly
    against schematic-named pins (the pre-iXref MVP behaviour).
    """
    devices = parse_calibre_device_query(
        os.path.join(FIXTURE_DIR, 'calibre_device_query.json')
    )
    bbox_data = parse_bbox_by_layer(
        os.path.join(FIXTURE_DIR, 'bbox_by_layer.json')
    )
    net_data = parse_calibre_net_query(
        os.path.join(FIXTURE_DIR, 'calibre_net_query.json')
    )
    pool = build_shape_pool(bbox_data)
    matched = apply_lvs_overlay(pool, net_data, devices, xref=None)
    assert set(matched.keys()) >= {'VSS', 'VDD', 'IN', 'OUT'}


def test_build_layout_model_accepts_ixref_path():
    """The build_layout_model entry point forwards ixref_path to
    apply_lvs_overlay; the resulting model must look the same as
    the no-xref baseline because the dummy fixture's pins already
    speak schematic names (no-op translation)."""
    base, _ = build_layout_model(
        device_query_path=os.path.join(FIXTURE_DIR, 'calibre_device_query.json'),
        net_query_path=os.path.join(FIXTURE_DIR, 'calibre_net_query.json'),
        bbox_path=os.path.join(FIXTURE_DIR, 'bbox_by_layer.json'),
    )
    with_xref, _ = build_layout_model(
        device_query_path=os.path.join(FIXTURE_DIR, 'calibre_device_query.json'),
        net_query_path=os.path.join(FIXTURE_DIR, 'calibre_net_query.json'),
        bbox_path=os.path.join(FIXTURE_DIR, 'bbox_by_layer.json'),
        ixref_path=IXREF_PATH,
    )
    assert sorted(base.nets) == sorted(with_xref.nets)
    base_owners = {sr.device_id for sr in base.shape_pool if sr.device_id}
    xref_owners = {sr.device_id for sr in with_xref.shape_pool if sr.device_id}
    assert base_owners == xref_owners


def test_build_layout_model_accepts_yaml_middle_file(tmp_path):
    """build_layout_model autodetects the YAML middle file via
    extension and consumes it identically to the raw .temp."""
    yaml_mid = tmp_path / 'mid.yaml'
    write_xref_yaml(parse_ixref(IXREF_PATH), str(yaml_mid))
    model_temp, _ = build_layout_model(
        device_query_path=os.path.join(FIXTURE_DIR, 'calibre_device_query.json'),
        net_query_path=os.path.join(FIXTURE_DIR, 'calibre_net_query.json'),
        bbox_path=os.path.join(FIXTURE_DIR, 'bbox_by_layer.json'),
        ixref_path=IXREF_PATH,
    )
    model_yaml, _ = build_layout_model(
        device_query_path=os.path.join(FIXTURE_DIR, 'calibre_device_query.json'),
        net_query_path=os.path.join(FIXTURE_DIR, 'calibre_net_query.json'),
        bbox_path=os.path.join(FIXTURE_DIR, 'bbox_by_layer.json'),
        ixref_path=str(yaml_mid),
    )
    a = sorted((sr.layer, sr.bbox_nm, sr.device_id) for sr in model_temp.shape_pool)
    b = sorted((sr.layer, sr.bbox_nm, sr.device_id) for sr in model_yaml.shape_pool)
    assert a == b


def test_build_layout_model_missing_ixref_path_is_noop():
    """Pointing at a non-existent ixref path should be silently
    treated as 'no xref' rather than crashing the pipeline."""
    model, _ = build_layout_model(
        device_query_path=os.path.join(FIXTURE_DIR, 'calibre_device_query.json'),
        net_query_path=os.path.join(FIXTURE_DIR, 'calibre_net_query.json'),
        bbox_path=os.path.join(FIXTURE_DIR, 'bbox_by_layer.json'),
        ixref_path='/no/such/file.temp',
    )
    assert {d.inst_name for d in model.devices} == {'MN0', 'MP0'}


# ----------------------------------------------------------------
# Site-config integration
# ----------------------------------------------------------------
def test_site_config_resolves_calibre_paths():
    from tech.config_loader import load_site_config
    site_yaml = os.path.join(
        os.path.dirname(__file__), '..', '..', 'tech', 'site_config.yaml'
    )
    cfg = load_site_config(site_yaml)
    cal = cfg['calibre']
    # Path-valued fields are absolute after resolution.
    assert os.path.isabs(cal['svdb_dir'])
    assert os.path.isabs(cal['dummy_fixture_dir'])
    assert os.path.isabs(cal['ixref']['output'])
    assert os.path.isabs(cal['ixref']['parsed_yaml'])
    # The {ts}/{cell} pattern tokens survived intact.
    assert '{ts}'   in cal['ixref']['output']
    assert '{cell}' in cal['ixref']['output']


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
