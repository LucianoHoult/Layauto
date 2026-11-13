"""Independent CR01-03 recheck using original probes and adversarial leaf values."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import sys
from fractions import Fraction

from layauto_v2.domain.codec import FrozenMap
from layauto_v2.domain.net_annotation import AnnotationRef, MatchEvidence, validate_annotation_graph
from layauto_v2.normalization.net_annotation_codec import encode_record, decode_record

FILES = ('layauto_v2/domain/net_annotation.py', 'layauto_v2/state/annotation.py',
         'layauto_v2/annotation/net_regions.py', 'layauto_v2/derive/net_annotation.py',
         'layauto_v2/normalization/net_annotation.py', 'layauto_v2/normalization/net_annotation_codec.py',
         'layauto_v2/normalization/__init__.py', 'pyproject.toml')


def forged(entries):
    value = object.__new__(FrozenMap)
    object.__setattr__(value, '_entries', entries)
    return value


def main():
    root = Path.cwd()
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    source = {name: sha(root / name) for name in FILES}
    prefix = root / 'docs/tasks/W013/review-evidence/neutral-static'
    rows = []
    def rejection(label, call):
        try:
            call()
        except ValueError as exc:
            rows.append({'case': label, 'outcome': 'ValueError', 'message': str(exc)})
        else:
            raise AssertionError('malformed case accepted: ' + label)
    single = runpy.run_path(str(prefix / 'operator_binding_probe.py'))
    multiple = runpy.run_path(str(prefix / 'multiple_owners_probe.py'))
    alias = runpy.run_path(str(prefix / 'map_backing_probe.py'))
    role = runpy.run_path(str(prefix / 'target_classification_probe.py'))
    contributor = runpy.run_path(str(prefix / 'contributor_closure_probe.py'))
    rejection('CR01 node/component owner mismatch', single['main'])
    rejection('CR01 multiple effective operators', lambda: multiple['build_case'](('one', 'one'), ('A', 'B')))
    rejection('CR01 multiple contact operators', lambda: multiple['build_case'](('A', 'B'), ('one', 'one')))
    rejection('CR02 original mutable policy backing', alias['main'])
    rejection('CR03 marker target', lambda: role['make_case']('marker', 'marker'))
    rejection('CR03 connector target', lambda: role['make_case']('contact', 'connector'))
    rejection('CR03 dangling region contributor', contributor['main'])
    valid = role['make_case']('interconnect', 'target_conductor')
    assert valid['public_codec_roundtrip_accepted']
    cycle = object.__new__(FrozenMap)
    object.__setattr__(cycle, '_entries', (('self', cycle),))
    missing = object.__new__(FrozenMap)
    for label, value in (
        ('nested mutable backing', forged((('outer', forged([('x', 1)])),))),
        ('duplicate map keys', forged((('x', 1), ('x', 2)))),
        ('native list entry', forged((['x', 1],))),
        ('map cycle', cycle), ('missing backing', missing),
    ):
        rejection('CR02 ' + label, lambda value=value: MatchEvidence(AnnotationRef('evidence', '1' * 64), (), (), (), (), value, 'unsupported'))
    shared = (AnnotationRef('evidence', '2' * 64),)
    invalid_payload = forged((('shared', shared),))
    rejection('CR02 value-only memo context', lambda: validate_annotation_graph((shared, invalid_payload), (AnnotationRef,)))
    unreduced = Fraction(1, 2)
    object.__setattr__(unreduced, '_numerator', 2)
    object.__setattr__(unreduced, '_denominator', 4)
    rejection('CR02 unreduced native Fraction shell', lambda: validate_annotation_graph(unreduced))
    safe = MatchEvidence(AnnotationRef('evidence', '1' * 64), (), (), (), (), FrozenMap({'supported': False}), 'unsupported')
    assert decode_record(encode_record(safe)) == safe
    assert source == {name: sha(root / name) for name in FILES}
    print(json.dumps({'classification': 'independent-neutral-findings-recheck-not-final-matrix',
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'python': sys.version, 'source_files': source, 'source_stable': True,
        'rejected_cases': rows, 'valid_neutral_target_roundtrip': valid,
        'valid_policy_roundtrip': True, 'not_run': ['captured result', 'resource probe', 'full regression']}, indent=2))


if __name__ == '__main__':
    main()
