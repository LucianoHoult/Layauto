"""Necessary finite checks: inherited A1 identity, attribution, owned-pack witness."""
from __future__ import annotations

import cProfile
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
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from layauto_v2.domain.codec import FrozenMap, canonical_bytes, freeze
from layauto_v2.domain.channel_identity import ChannelRef, RationalRect, SeedIntersection, SeedLocation
from layauto_v2.domain.local_connectivity import ContactComponent, LocalRef
from layauto_v2.domain.regions import RegionRef
from layauto_v2.domain.evidence import EvidenceRecord, SourceRef
from layauto_v2.normalization import channel_identity_codec as channel
from layauto_v2.normalization import local_connectivity_codec as local
from reference_pack import ReferenceBoundExceeded, encode_small, pack_small


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def counted(call):
    profiler = cProfile.Profile()
    result = profiler.runcall(call)
    counts = {}
    for entry in profiler.getstats():
        code = entry.code
        if (not isinstance(code, str) and code.co_filename.endswith('/domain/codec.py')
                and code.co_name in ('freeze', '__init__')):
            counts[code.co_name] = entry.callcount
    return result, counts


def main() -> None:
    a1 = ROOT / 'docs/tasks/W012/A1'
    manifest = json.loads((a1 / 'verification-r2/source-manifest.json').read_text())['files']
    versions = ['ca1f810c3c97376f71089d8b4054760ff198012f',
                '08dd232139918dc97b0a6d255aad237eb844686a',
                '842c5c1ea8f1d01bb3f04e4703f105e11f94158c']
    for path, expected in manifest.items():
        assert sha((ROOT / path).read_bytes()) == expected, path
        for version in versions:
            assert sha(subprocess.check_output(['git', 'show', f'{version}:{path}'], cwd=ROOT)) == expected, path
    samples = {}
    for case in ('normal-direct', 'normal-readback', 'extraction-mismatch'):
        rows = [json.loads((a1 / f'performance/after-{case}-r{i}.json').read_text()) for i in (1, 2, 3)]
        assert all(row['source_identity']['files'] == manifest for row in rows)
        samples[case] = {name: statistics.median(row['wall_seconds'][name] for row in rows)
                         for name in ('W011_build', 'W011_result_decode', 'W011_result_encode')}
        samples[case]['total_of_each_sample_median'] = statistics.median(sum(row['wall_seconds'].values()) for row in rows)
    receipt = json.loads((a1 / 'profile/after-normal-readback-r1.json').read_text())
    assert receipt['source_identity']['files'] == manifest
    profile_path = a1 / 'profile/after-normal-readback-r1.profile.json'
    profile = json.loads(profile_path.read_text())
    attribution = {}
    for stage in ('W011_build', 'W011_result_decode', 'W011_result_encode'):
        rows = profile[stage]['functions']
        family = [r for r in rows if r['file'].endswith('/domain/codec.py')]
        attribution[stage] = {'domain_codec_exclusive_seconds': sum(r['exclusive_seconds'] for r in family),
                              'functions': family,
                              'two_owner_pack_and_encode': [r for r in rows if r['file'].endswith(
                                  ('/channel_identity_codec.py', '/local_connectivity_codec.py'))
                                  and r['function'] in ('_pack', 'encode_record', 'decode_record')]}
    h = '1' * 64
    rect = RationalRect(Fraction(-1, 2), Fraction(0), Fraction(7, 3), Fraction(5))
    seed = ChannelRef('seed', h)
    binding = ChannelRef('binding', '2' * 64)
    intersection = SeedIntersection(seed, RegionRef('region', '3' * 64), rect, Fraction(1, 2), binding)
    location = SeedLocation(seed, (intersection,), binding)
    component = ContactComponent(tuple(LocalRef('node', f'{i:064x}') for i in range(8)), LocalRef('operators', h))
    roots = [(channel, seed), (channel, rect), (channel, intersection), (channel, location),
             (local, LocalRef('operators', h)), (local, component)]
    witnesses = []
    for codec, record in roots:
        old, old_counts = counted(lambda: codec.encode_record(record))
        new, new_counts = counted(lambda: encode_small(codec, record))
        assert old == new
        # Public old decoder still reconstructs and checks the complete small DTO.
        assert codec.decode_record(new) == record
        witnesses.append({'owner': codec.__name__, 'root': type(record).__name__, 'bytes': len(old),
                          'sha256': sha(old), 'old_calls': old_counts, 'reference_calls': new_counts})
    payload = FrozenMap({'z': (b'\x00\xff', Fraction(-3, 7), True, 1, None),
                         'a\n"\\': '汉字😀\u2028', '$map': FrozenMap({'x': 'y'})})
    delegated = EvidenceRecord('reference-only', payload, (SourceRef('reference://source', h),))
    subvalues = [payload, (payload, payload), (), b'', b'\x00\xff', Fraction(1), False, 1, None,
                 '汉字😀\u2028\n"\\', delegated]
    for codec in (local, channel):
        for value in subvalues:
            old, new = codec._pack(value), pack_small(codec, value)
            assert freeze(new) == freeze(old)
            assert canonical_bytes(new) == canonical_bytes(old)
    # Alias defense is retained by the original freeze, including map-leaf detachment.
    mutable = {'x': [{'y': 1}]}
    frozen = FrozenMap(mutable)
    owned = pack_small(channel, frozen)
    mutable['x'][0]['y'] = 99
    assert owned['map']['x'][0]['y'] == 1 and owned['map'] is not frozen
    # Existing closed preflight rejects foreign equal text before either pack runs.
    class MutableText(str):
        pass
    forged = object.__new__(ChannelRef)
    object.__setattr__(forged, 'kind', MutableText('seed'))
    object.__setattr__(forged, 'sha256', h)
    for call in (lambda: channel.encode_record(forged), lambda: encode_small(channel, forged)):
        try:
            call()
        except ValueError as exc:
            assert str(exc) == 'foreign or mutable value in effective geometry graph'
        else:
            raise AssertionError('foreign scalar accepted')
    # A failed scalar snapshot must propagate the very same pre-existing exception.
    failure = TypeError('reference original scalar snapshot failure')
    cause, context = RuntimeError('cause'), LookupError('context')
    failure.__cause__, failure.__context__, failure.__suppress_context__ = cause, context, True
    from collections.abc import Mapping
    class BrokenMap(Mapping):
        def __iter__(self): return iter(('x',))
        def __len__(self): return 1
        def __getitem__(self, key): raise failure
    for call in (lambda: channel._pack(BrokenMap()), lambda: pack_small(channel, BrokenMap())):
        try:
            call()
        except TypeError as exc:
            assert exc is failure and exc.__cause__ is cause and exc.__context__ is context
            assert exc.__suppress_context__ is True
        else:
            raise AssertionError('snapshot failure swallowed')
    # UTF-8 behavior stays in unchanged canonical_bytes; no token writer is introduced.
    errors = []
    for call in (lambda: canonical_bytes(channel._pack('\ud800')),
                 lambda: canonical_bytes(pack_small(channel, '\ud800'))):
        try:
            call()
        except UnicodeEncodeError as exc:
            errors.append((exc.encoding, exc.object, exc.start, exc.end, exc.reason))
    assert len(errors) == 2 and errors[0] == errors[1]
    try:
        pack_small(channel, b'x' * 4097)
    except ReferenceBoundExceeded:
        pass
    else:
        raise AssertionError('reference bound failed')
    output = {'status': 'passed', 'python': sys.version, 'platform': platform.platform(),
              'runtime_root': str(ROOT / 'layauto_v2'), 'source_manifest_count': len(manifest),
              'runtime_count': sum(p.startswith('layauto_v2/') for p in manifest),
              'verified_git_versions': versions, 'a1_wall_medians_seconds': samples,
              'after_profile_sha256': sha(profile_path.read_bytes()), 'after_profile_attribution': attribution,
              'small_roots': witnesses, 'subvalues_per_owner': len(subvalues),
              'checks': ['263 disk/frozen/merge/PM-preparation blobs', '9 after samples + after profile same source',
                         '6 real small roots byte equality + unchanged public decode',
                         '22 private subvalue structural and byte comparisons', 'map snapshot detachment',
                         'closed preflight foreign scalar rejection', 'original scalar snapshot exception history',
                         'UTF-8 error attributes', 'reference bounds'],
              'limits': 'No full result entry, monkeypatch, product timing or benchmark; counts are small-reference counts.',
              'attachment_sha256': {p.name: sha(p.read_bytes()) for p in (HERE / 'check.py', HERE / 'reference_pack.py')}}
    (HERE / 'check-result.json').write_text(json.dumps(output, ensure_ascii=True, indent=2) + '\n')
    print('PASS: 263 source identities across disk + 3 Git versions; 9 after receipts + profile match')
    print('A1 readback wall medians:', json.dumps(samples['normal-readback'], sort_keys=True))
    for row in witnesses:
        print(row['root'], row['bytes'], 'bytes; calls old -> reference:', row['old_calls'], '->', row['reference_calls'])
    print('PASS: finite pack/bytes/alias/closed/exception/UTF-8/bound witnesses; no product performance claim')


if __name__ == '__main__':
    main()
