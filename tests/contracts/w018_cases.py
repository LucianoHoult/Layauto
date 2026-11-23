"""Select a complete test technology owner in temporary W003/W004 captures."""
from __future__ import annotations

import shutil
from pathlib import Path

import yaml

from layauto_v2.importers import read_inputs
from layauto_v2.normalization import build_geometry, geometry_from_parse_result
from w005_cases import read_json, rebind, write_json

SAMPLE = Path(__file__).resolve().parents[2] / 'docs/tasks/W018/layer-discretization.example.yaml'
COORDINATE_URI = 'tech/layer-discretization.yaml'


def select_projection(root, *, mutate=None):
    """Bind the reviewed YAML bytes, or an explicit test variant, by normal tech selection."""
    owner = root / COORDINATE_URI
    if mutate is None:
        shutil.copyfile(SAMPLE, owner)
    else:
        document = yaml.safe_load(SAMPLE.read_bytes())
        mutate(document['coordinate_projection'])
        write_json(owner, document)

    bundle = read_json(root / 'tech.json')
    old_uri = bundle['owners']['coordinate']['path']
    bundle['owners']['coordinate']['path'] = COORDINATE_URI
    write_json(root / 'tech.json', bundle)
    header = read_json(root / 'query/header.json')
    entry = next(entry for entry in header['closure']['entries'] if entry['uri'] == old_uri)
    entry['uri'] = COORDINATE_URI
    write_json(root / 'query/header.json', header)
    rebind(root)


def build_geometry_from_site(root):
    parsed = read_inputs(root / 'site_config.yaml')
    assert parsed.status == 'success', parsed.issues
    geometry = build_geometry(geometry_from_parse_result(parsed))
    assert geometry.status == 'success' and geometry.value is not None, geometry.issues
    return geometry
