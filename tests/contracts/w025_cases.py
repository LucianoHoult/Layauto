"""Stage a full W025 input before capture; used by the contracts and worked example."""
from pathlib import Path

import yaml

from w005_cases import read_json, rebind, write_json
from w010_cases import append_records
from w018_cases import COORDINATE_URI
from w024_cases import stage


def stage_spacing(parent: Path, gap_nm: int, threshold_nm: int = 2) -> Path:
    root = stage(parent, 'normal')
    path = root / COORDINATE_URI
    grid = yaml.safe_load(path.read_bytes())
    li = grid['coordinate_projection']['layers']['LI']
    li['x_edges'].update(pitch_dbu=32, cells=5)
    li['y_edges'].update(pitch_dbu=16, cells=13)
    path.write_text(yaml.safe_dump(grid), encoding='utf-8')
    append_records(root, [('LI', (130, 20, 150, 24)), ('CUT', (139, 18, 139 + gap_nm, 26))])
    if threshold_nm != 2:
        owner = root / 'tech/rules.json'
        rules = read_json(owner)
        t06 = next(r for r in rules['rules'] if r['id'] == 'T06.li_spacing')
        t06['parameters']['min_distance_nm'] = threshold_nm
        t06['predicate'] = f'distance>={threshold_nm} nm unless actual same-layer contact makes one region'
        write_json(owner, rules)
        rebind(root)
    return root
