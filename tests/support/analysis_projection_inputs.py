"""Select the W018 coordinate owner in a temporary W016 analysis manifest."""
import shutil
from pathlib import Path

from analysis_inputs import load, materialize, rebind, write

SAMPLE = Path(__file__).resolve().parents[2] / 'docs/tasks/W018/layer-discretization.example.yaml'
COORDINATE = 'tech/layer-discretization.yaml'


def projected_manifest(root, *, body=False):
    manifest = materialize(root, body=body)
    bundle = load(root / 'tech.json')
    old_uri = bundle['owners']['coordinate']['path']
    shutil.copyfile(SAMPLE, root / COORDINATE)
    bundle['owners']['coordinate']['path'] = COORDINATE
    write(root / 'tech.json', bundle)
    header = load(root / 'query/local-header.json')
    entry = next(row for row in header['closure']['entries'] if row['uri'] == old_uri)
    entry['uri'] = COORDINATE
    header['closure']['entries'].sort(key=lambda row: row['uri'])
    write(root / 'query/local-header.json', header)
    rebind(root)
    return manifest
