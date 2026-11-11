"""Independent small-value/scope review; no complete builds or performance timers."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path('/workspace/Layauto')
HERE = Path(__file__).resolve().parent
BASE = '0213c346ac03b7b7282aae522c299155958ac8f6'
OWNERS = ('normalization/local_connectivity_codec.py',
          'normalization/channel_identity_codec.py')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    output = HERE / 'runtime-check.json'
    if output.exists():
        raise RuntimeError('retain prior review evidence; choose a new output name')
    runtime = {}
    names = subprocess.check_output(
        ['git', 'ls-tree', '-r', '--name-only', BASE, 'layauto_v2'], cwd=ROOT,
        text=True).splitlines()
    changes = []
    for name in names:
        current = (ROOT / name).read_bytes()
        before = subprocess.check_output(['git', 'show', f'{BASE}:{name}'], cwd=ROOT)
        runtime[name] = sha(current)
        if current != before:
            changes.append(name)
            assert name.removeprefix('layauto_v2/') in OWNERS
            text = current.decode()
            start = text.index('def _pack_for_encode(')
            end = text.index('def _unpack(', start)
            restored = text[:start] + text[end:]
            assert restored.count("'record': _pack_for_encode(record)") == 1
            restored = restored.replace("'record': _pack_for_encode(record)", "'record': _pack(record)")
            assert restored.encode() == before, 'out-of-scope owner code changed'
    assert sorted(changes) == sorted('layauto_v2/' + owner for owner in OWNERS)

    sys.path.insert(0, str(ROOT))
    from fractions import Fraction
    from layauto_v2.domain.codec import FrozenMap, canonical_bytes
    from layauto_v2.domain.channel_identity import ChannelRef, RationalRect
    from layauto_v2.domain.local_connectivity import LocalRef
    from layauto_v2.normalization import channel_identity_codec as channel
    from layauto_v2.normalization import local_connectivity_codec as local

    scalars = [None, False, True, 0, 1, -1, 10 ** 300, Fraction(-4, 6),
               '', '中😀e\u0301\u2028', '\x00\n\\"', b'', bytes(range(256))]
    payload = FrozenMap({'record': True, 'fields': (Fraction(1), 1, True),
                         '$map': {'b': b'\x00\xff'}, '😀': '中'})
    subvalues = scalars + [(), tuple(scalars), payload,
                           (payload, ('nested', Fraction(1, 3), b'\xff'))]
    observations = []
    for codec in (local, channel):
        for value in subvalues:
            old = canonical_bytes(codec._pack(value))
            new = canonical_bytes(codec._pack_for_encode(value))
            assert old == new
        distinct = [canonical_bytes(codec._pack_for_encode(value)) for value in (True, 1, Fraction(1))]
        assert len(set(distinct)) == 3
        assert distinct == [b'{"$map":{"scalar":true}}',
                            b'{"$map":{"scalar":1}}',
                            b'{"$map":{"scalar":{"$rational":{"denominator":"1","numerator":"1"}}}}']
        # Hostile mutation of the exact map's storage does not alter either snapshot.
        leaf = FrozenMap({'snapshot': (b'a', Fraction(2, 3))})
        old_snapshot, new_snapshot = codec._pack(leaf), codec._pack_for_encode(leaf)
        expected = canonical_bytes(old_snapshot)
        object.__setattr__(leaf, '_entries', (('changed', True),))
        assert canonical_bytes(old_snapshot) == canonical_bytes(new_snapshot) == expected
        for value in ('\ud800', ('\ud800', 10 ** 5000)):
            errors = []
            for pack in (codec._pack, codec._pack_for_encode):
                try:
                    canonical_bytes(pack(value))
                except (ValueError, UnicodeEncodeError) as exc:
                    errors.append((type(exc), str(exc), getattr(exc, 'object', None),
                                   getattr(exc, 'start', None), getattr(exc, 'end', None),
                                   getattr(exc, 'reason', None), exc.__cause__, exc.__context__,
                                   exc.__suppress_context__))
                else:
                    raise AssertionError('expected canonical failure')
            assert errors[0] == errors[1]
        observations.append({'module': codec.__name__, 'finite_subvalues': len(subvalues),
                             'typed_scalars_distinct': True, 'immediate_map_snapshot': True,
                             'unicode_integer_exception_order': True})

    roots = [(local, LocalRef('node', 'a' * 64), 'layauto-local-connectivity-wire/1'),
             (channel, ChannelRef('seed', 'b' * 64), 'layauto-channel-identity-wire/1'),
             (channel, RationalRect(Fraction(0), Fraction(-2, 3), Fraction(7, 3), Fraction(5)),
              'layauto-channel-identity-wire/1')]
    for codec, record, schema in roots:
        accepted = canonical_bytes({'wire_schema': schema, 'record': codec._pack(record)})
        assert codec.encode_record(record) == accepted
        assert codec.encode_record(codec.decode_record(accepted)) == accepted
        for bad in (None, {}, (), record.__class__):
            try:
                codec.encode_record(bad)
            except ValueError:
                pass
            else:
                raise AssertionError('foreign public root accepted')

    output.write_text(json.dumps({'status': 'passed', 'base': BASE,
        'runtime_files_sha256': runtime, 'runtime_changed': changes,
        'checks': observations, 'public_roots_old_pack_byte_roundtrip': len(roots),
        'limitations': 'Small independent witness, no full Result/build/decode or benchmark; formal regressions and complete performance evidence reviewed separately',
        'script_sha256': sha(Path(__file__).read_bytes())}, indent=2, sort_keys=True) + '\n')
    print('PASS: exact owner scope, unchanged original functions, typed bytes/snapshots/errors, small public roots')


if __name__ == '__main__':
    main()
