"""Independent read-only review witnesses for W013's pre-implementation gate."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

from layauto_v2.domain.codec import freeze_map
from layauto_v2.domain.identifiers import QueryKey
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import from_parse_result, normalize


def plain(value):
    if isinstance(value, Mapping):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [plain(item) for item in value]
    return value


def overwrite_a_index(value):
    if isinstance(value, Mapping):
        return {key: ('007' if key == 'lvs_index' and value.get('lvs_name') == 'n_a'
                      else overwrite_a_index(item)) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(overwrite_a_index(item) for item in value)
    return value


def outcome(call):
    try:
        call()
    except ValueError as exc:
        return {'outcome': 'ValueError', 'message': str(exc)}
    raise AssertionError('expected rejection did not occur')


def area(box):
    return (box[2] - box[0]) * (box[3] - box[1])


def main():
    root = Path.cwd()
    fixture = root / 'tests/fixtures/w003_m1'
    parsed = read_inputs(fixture / 'site_config.yaml')
    assert parsed.status == 'success'
    semantic = normalize(from_parse_result(parsed))
    assert semantic.status == 'success'
    forged = replace(parsed,
                     value=freeze_map(overwrite_a_index(parsed.value)),
                     completed=tuple(replace(record, payload=freeze_map(overwrite_a_index(record.payload)))
                                     for record in parsed.completed))
    authenticated_007 = outcome(lambda: from_parse_result(forged))
    assert authenticated_007['message'] == 'LVS index is not its captured NET NAMES ordinal'
    key_007 = outcome(lambda: QueryKey('header', 'run', None, 'net', 'n_a', '007'))
    seed = semantic.value.net_seeds[0]
    quality = {}
    for value in ('approximate_bbox', 'untrimmed'):
        record = dict(seed.record)
        record['quality'] = value
        quality[value] = outcome(lambda: replace(seed, record=freeze_map(record)))
        assert quality[value]['message'] == 'unsupported annotation seed geometry/quality/unit'
    spec = json.loads((fixture / 'spec.json').read_text())
    oracle = json.loads((fixture / 'oracle.json').read_text())
    names = {row['id']: row for row in spec['shapes']}
    target_shapes = ['G', 'LN', 'LP', 'LY', 'MN', 'MP', 'MA', 'MY']
    covered = {}
    for name in target_shapes:
        row = names[name]
        covered[row['layer']] = covered.get(row['layer'], 0) + area(row['bbox'])
    node_area = sum(area(row['bbox']) for row in oracle['fragments'])
    node_area += sum(area(names[name]['bbox']) for component in oracle['components']
                     for name in component['regions'] if '.' not in name)
    assert covered == {'POLY': 720, 'LI': 1110, 'M1': 1340}
    assert node_area == 35090
    assert len({name for row in oracle['components'] for name in row['regions']}) == 14
    assert len(oracle['edges']) == 8 and len(oracle['components']) == 6
    files = ('docs/tasks/W013/interface-plan.md', 'docs/tasks/W013/pm-decision.md',
             'docs/tasks/W013/input-boundary-probe.py', 'docs/tasks/W013/input-boundary-probe.stdout.json')
    result = {
        'classification': 'independent-preimplementation-review-not-W013-validation',
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'python': sys.version, 'executable': sys.executable, 'platform': platform.platform(),
        'fixture': str(fixture),
        'reviewed_files': {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in files},
        'real_indices': {identity.query_key.identity: identity.query_key.index for identity in semantic.value.net_identities},
        'query_key_007': key_007,
        'forged_007_same_captured_sources': authenticated_007,
        'quality_seed_rejections': quality,
        'independent_spec_oracle_arithmetic': {
            'direct_covered_area_nm2_by_layer': covered, 'all_local_node_area_nm2': node_area,
            'nodes': 14, 'edges': 8, 'components': 6,
            'scope_note': 'body_associations external; no direct net mapping to OD/BODY',
        },
    }
    print(json.dumps(plain(result), indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
