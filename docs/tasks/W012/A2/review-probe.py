"""Independent bounded review witnesses; leaves original evidence untouched."""
from __future__ import annotations

import hashlib
import json
import platform
import statistics
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(HERE)]

from layauto_v2.domain.codec import FrozenMap, canonical_bytes, freeze
from layauto_v2.domain.channel_identity import ChannelRef
from layauto_v2.domain.evidence import EvidenceRecord, SourceRef
from layauto_v2.domain.geometry import GeometryRef
from layauto_v2.domain.identifiers import CellId, DeviceId
from layauto_v2.domain.local_connectivity import LocalRef
from layauto_v2.domain.regions import RegionRef
from layauto_v2.normalization import channel_identity_codec as channel
from layauto_v2.normalization import local_connectivity_codec as local
from reference_pack import encode_small, pack_small


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    manifest = json.loads((ROOT / 'docs/tasks/W012/A1/verification-r2/source-manifest.json').read_text())['files']
    for name, expected in manifest.items():
        assert sha((ROOT / name).read_bytes()) == expected, name
    result = json.loads((HERE / 'check-result.json').read_text())
    for name, expected in result['attachment_sha256'].items():
        assert sha((HERE / name).read_bytes()) == expected
    paths = subprocess.check_output(['git', 'diff', '--name-only',
                                    '842c5c1ea8f1d01bb3f04e4703f105e11f94158c',
                                    'cbf20807a85d8350928fc6a604612384cb2727fd'], cwd=ROOT, text=True).splitlines()
    assert all(name.startswith('docs/tasks/W012/A2/') or
               name == 'docs/tasks/W012-capture-wire-performance.md' for name in paths)
    task = 'docs/tasks/W012-capture-wire-performance.md'
    base = subprocess.check_output(['git', 'show', '842c5c1ea8f1d01bb3f04e4703f105e11f94158c:' + task], cwd=ROOT)
    current = (ROOT / task).read_bytes()
    start = current.index('### A2 兼容方案收敛执行交付'.encode())
    end = current.index('## PM 验收与交接（PM）'.encode(), start)
    assert current[:start] + current[end:] == base

    h = 'a' * 64
    source = SourceRef('review://source', h)
    values = [None, True, 1, Fraction(1), Fraction(-5, 7), b'', b'\x00\xff',
              '\n"\\汉字😀\u2028', (), (False, 0, Fraction(0)),
              FrozenMap({'record': 'opaque', 'fields': FrozenMap({'$bytes': 'still text'}),
                         'a': (Fraction(2, 3), b'abc')})]
    values.extend((LocalRef('node', h), GeometryRef('unit', h), RegionRef('region', h),
                   DeviceId(CellId('R'), 'M0'), EvidenceRecord('review-only', {}, (source,)), source))
    comparisons = []
    for owner in (local, channel):
        for value in values:
            # Local does not recognize DeviceId or SourceRef as delegates; its
            # original private pack rejects them, so compare that failure too.
            try:
                old = owner._pack(value)
            except ValueError as exc:
                try:
                    pack_small(owner, value)
                except ValueError as other:
                    assert type(exc) is type(other) and str(exc) == str(other)
                else:
                    raise AssertionError('reference widened private subvalue input')
                comparisons.append({'owner': owner.__name__, 'type': type(value).__name__, 'result': 'same rejection'})
                continue
            new = pack_small(owner, value)
            assert freeze(old) == freeze(new)
            old_wire, new_wire = canonical_bytes(old), canonical_bytes(new)
            assert old_wire == new_wire
            comparisons.append({'owner': owner.__name__, 'type': type(value).__name__,
                                'tag': next(iter(old)), 'bytes': len(old_wire), 'sha256': sha(old_wire)})
        # Numeric equality is not sufficient for byte equivalence.
        representations = [canonical_bytes(pack_small(owner, v)) for v in (True, 1, Fraction(1))]
        assert len(set(representations)) == 3
        # Detach the exact map at the leaf, before canonical() later consumes it.
        leaf = FrozenMap({'x': (1, 2)})
        old, new = owner._pack(leaf), pack_small(owner, leaf)
        object.__setattr__(leaf, '_entries', (('x', (99,)),))
        assert canonical_bytes(old) == canonical_bytes(new)
        assert new['map']['x'] == (1, 2) and new['map'] is not leaf
    root = ChannelRef('seed', h)
    assert channel.encode_record(root) == encode_small(channel, root)
    assert channel.decode_record(encode_small(channel, root)) == root
    class ForeignText(str):
        pass
    forged = object.__new__(ChannelRef)
    object.__setattr__(forged, 'kind', ForeignText('seed'))
    object.__setattr__(forged, 'sha256', h)
    failures = []
    for call in (lambda: channel.encode_record(forged), lambda: encode_small(channel, forged)):
        try:
            call()
        except ValueError as exc:
            failures.append((type(exc).__name__, str(exc)))
    assert len(failures) == 2 and failures[0] == failures[1]
    summary = {'status': 'passed', 'python': sys.version, 'platform': platform.platform(),
               'reviewed_head': 'cbf20807a85d8350928fc6a604612384cb2727fd',
               'manifest_files': len(manifest), 'changed_paths': paths,
               'task_outside_execution_insert_byte_identical': True,
               'private_subvalue_comparisons': comparisons,
               'scalar_types_have_distinct_bytes': True,
               'immediate_map_snapshot_survives_original_map_storage_replacement': True,
               'foreign_scalar_root_rejection': failures,
               'limits': 'Only bounded subvalues and one neutral leaf root; no full Result, runtime replacement, product timing or matrix.',
               'reviewed_files_sha256': {name: sha((ROOT / name).read_bytes()) for name in paths}}
    (HERE / 'review-probe-result.json').write_text(json.dumps(summary, ensure_ascii=True, indent=2) + '\n')
    print('PASS: 263 manifest files; task outside execution insert byte-identical to base')
    print('PASS:', len(comparisons), 'bounded private subvalue results, including delegated tags/rejections')
    print('PASS: distinct bool/int/rational bytes, immediate map snapshot, exact root preflight, old public leaf decode')
    print('No full product entry, monkeypatch, timing or engineering matrix run')


if __name__ == '__main__':
    main()
