"""W007 test-only byte edits and hand-written circuit expectations.

These transformations do not call normalization or fixture generators. They edit
only pytest temporary copies and rebind the existing captured-input contract.
"""
from __future__ import annotations

from collections.abc import Mapping
from fractions import Fraction
from pathlib import Path

from w005_cases import copy_input, read_json, rebind, without_cache, write_json


EXPECTED_PARAMETERS = {
    'fins_per_finger': ('NFIN', Fraction(5), 'count', '5'),
    'finger_count': ('NF', Fraction(1), 'count', '1'),
    'multiplicity': ('M', Fraction(1), 'count', '1'),
    'channel_length': ('L', Fraction(4, 10**9), 'metres', '4n'),
    'fin_width': ('W', Fraction(2, 10**9), 'metres', '2n'),
    'threshold_token': ('VT', 'toy', 'token', 'toy'),
}
EXPECTED_MEMBERS = {
    'A': {('MN0', 'G'), ('MP0', 'G')},
    'Y': {('MN0', 'D'), ('MP0', 'D')},
    'VSS': {('MN0', 'S'), ('MN0', 'B')},
    'VDD': {('MP0', 'S'), ('MP0', 'B')},
}
EXPECTED_REGIONS = {
    'D0': ('MN0', 'toy_ngate', (58, 20, 62, 70)),
    'D1': ('MP0', 'toy_pgate', (58, 110, 62, 180)),
    'R00': ('A', 'toy_poly', (58, 10, 62, 190)),
    'R01': ('A', 'toy_m1', (50, 90, 75, 98)),
    'R02': ('Y', 'toy_li', (84, 30, 90, 165)),
    'R03': ('Y', 'toy_m1', (80, 90, 110, 98)),
    'R04': ('VSS', 'toy_li', (28, 30, 34, 55)),
    'R05': ('VSS', 'toy_m1', (0, 48, 45, 58)),
    'R06': ('VDD', 'toy_li', (28, 130, 34, 155)),
    'R07': ('VDD', 'toy_m1', (0, 148, 45, 158)),
}


def mutable(value):
    if isinstance(value, Mapping):
        return {key: mutable(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [mutable(item) for item in value]
    return value


def exact(value):
    if isinstance(value, Fraction):
        return value
    return Fraction(int(value['numerator']), int(value['denominator']))


def read(root):
    from layauto_v2.importers import read_inputs
    result = read_inputs(root / 'site_config.yaml')
    assert result.status == 'success', [(i.code, i.message) for i in result.issues]
    return result


def normal(root):
    from layauto_v2.normalization import from_parse_result, normalize
    result = normalize(from_parse_result(read(root)))
    assert result.status == 'success', [(i.code, i.message) for i in result.issues]
    assert result.value is not None and not result.issues
    return result


def edit(root: Path, path: str, old: str, new: str):
    target = root / path
    text = target.read_text(encoding='utf-8')
    assert old in text, (path, old)
    target.write_text(text.replace(old, new), encoding='utf-8')


def ready_copy(tmp_path: Path):
    root = copy_input(tmp_path)
    without_cache(root)
    return root


def query_only_rename(root: Path):
    """Change opaque query names, file paths, ordering and run identity only."""
    names = {'Q17': 'layout_alpha', 'Q93': 'layout_beta',
             'n_a': 'wire_z', 'n_y': 'wire_x', 'n_lo': 'wire_k', 'n_hi': 'wire_t'}
    header = read_json(root / 'query/header.json')
    requests = read_json(root / 'query/requests.json')
    paths = {}
    for index, entry in enumerate(header['raw']):
        old = entry['uri']
        data = (root / old).read_text()
        for before, after in names.items():
            data = data.replace(before, after)
        lines = data.splitlines()
        if old.endswith(('iXref.temp', 'nXref.temp')):
            lines[8:] = reversed(lines[8:])
        if old.endswith('net_names.txt'):
            lines[3:7] = reversed(lines[3:7])
        new = f'query/raw/renamed_capture_{index}.txt'
        (root / new).write_text('\n'.join(lines) + '\n')
        (root / old).unlink()
        paths[old] = new
        entry['uri'] = new
    header['header_id'] = 'alternate.header'
    header['query_run_id'] = 'alternate.query.run'
    for entry in requests['requests']:
        entry['path'] = paths[entry['path']]
        entry['object'] = names[entry['object']]
    requests['requests'].reverse()
    write_json(root / 'query/header.json', header)
    write_json(root / 'query/requests.json', requests)
    without_cache(root)
    rebind(root)
    return names
