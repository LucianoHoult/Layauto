"""Independent W012 evidence/observer checks; no heavy product combinations."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'docs/tasks/W012'
EVIDENCE = OUT / 'review-evidence'
BASE = 'f3698b7ffda3b0737a2eb61ca85dbf3b40bc89fe'
HEAD = '27280c4ef243a96578b78e9794ff52407be86eff'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name):
    return json.loads((OUT / name).read_text())


def main():
    checks = []
    def check(condition, label):
        assert condition, label
        checks.append(label)
    check(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == HEAD,
          'reviewed frozen commit')
    paths = subprocess.check_output(['git', 'diff', '--name-only', BASE, HEAD], cwd=ROOT, text=True).splitlines()
    check(all(name.startswith('docs/tasks/W012/') or name == 'docs/tasks/W012-capture-wire-performance.md'
              for name in paths), 'only authorized W012 diff paths')
    manifest = json.loads((ROOT / 'docs/tasks/W011/verification/source-manifest.json').read_text())
    check(len(manifest['files']) == 262 and len(manifest['runtime_files']) == 100, '262 sources / 100 runtime')
    for name, digest in manifest['files'].items():
        check(sha(ROOT / name) == digest, 'source same as W011: ' + name)
    for ref in (BASE, '0a3326aa363477724465886cd05874d0997fba3e', manifest['git_head']):
        for name, digest in manifest['files'].items():
            data = subprocess.check_output(['git', 'show', f'{ref}:{name}'], cwd=ROOT)
            check(hashlib.sha256(data).hexdigest() == digest, 'source identity ' + ref + ':' + name)
    with tarfile.open(ROOT / 'docs/tasks/W011/verification/source-snapshot.tar.gz') as archive:
        for name, digest in manifest['files'].items():
            check(hashlib.sha256(archive.extractfile(name).read()).hexdigest() == digest, 'snapshot: ' + name)
    history = ROOT / 'docs/tasks/W011/verification'
    inherited = json.loads((history / 'receipt.json').read_text())
    check(inherited['actual_test_counts'] == {'310': 1605, '312': 1605}, 'inherited dual1605')
    for row in inherited['commands']:
        check(row['exit_code'] == 0, 'inherited command exit0: ' + row['stdout'])
        for stream in ('stdout', 'stderr'):
            check(sha(history / row[stream]) == row[stream + '_sha256'], 'inherited raw: ' + row[stream])
    for row in load('preflight.json')['inputs']:
        check(Path(row['origin']).read_bytes() == Path(row['target']).read_bytes(), 'fixed overlay bytes: ' + row['target'])
        check(hashlib.sha256(Path(row['target']).read_bytes()).hexdigest() == row['sha256'], 'overlay identity: ' + row['target'])
    command_rows = load('measurement-receipt.json')['commands']
    check(len(command_rows) == 6, 'six complete actual baseline/profile paths')
    finish = None
    for row in command_rows:
        check(row['exit_code'] == 0, 'measurement exit0: ' + str(row['argv']))
        start = datetime.fromisoformat(row['started_at_utc'])
        if finish:
            check(start >= finish, 'serial fresh process chronology')
        finish = datetime.fromisoformat(row['finished_at_utc'])
        prefix = Path(row['argv'][-1]).name.removesuffix('.json')
        for stream in ('stdout', 'stderr'):
            check(sha(OUT / (prefix + '.' + stream + '.txt')) == row[stream + '_sha256'], 'measurement raw: ' + prefix + stream)
        for name, digest in row['tools'].items():
            check(sha(OUT / name) == digest, 'measurement tool frozen: ' + name)
    derived = {}
    for case in ('normal-direct', 'normal-readback', 'extraction-mismatch'):
        baseline = load('baseline-' + case + '.json')
        profile = load('profile-' + case + '.json')
        phases = load('profile-' + case + '.profile.json')
        check(baseline['wire_sha256'] == profile['wire_sha256'] and baseline['wire_bytes'] == profile['wire_bytes'], 'same actual wire: ' + case)
        check(baseline['capture_sources'] == profile['capture_sources'], 'same actual captures: ' + case)
        check(len(baseline['capture_sources']) == 31 and sum(r['bytes'] for r in baseline['capture_sources']) == 280706, '31 captures / 280706 bytes: ' + case)
        expected = {'MN0': 4 if case == 'extraction-mismatch' else 5, 'MP0': 7}
        check(baseline['result']['counts'] == expected and baseline['result']['complete_evaluations'] == 36, 'actual counts / complete FIN set: ' + case)
        check(baseline['result']['difference_count'] == (1 if case == 'extraction-mismatch' else 0), 'source mismatch cardinality: ' + case)
        check(baseline['public_roundtrip_equal'] and profile['public_roundtrip_equal'], 'complete DTO equality: ' + case)
        if case == 'normal-readback':
            check(baseline['readback_unsealed_checkpoint_unchanged_no_terminal'], 'readback state boundary')
        outer = phases['W011_result_encode']['wire']['bytes_to_hex']['normalization.channel_identity_codec.encode_record:ChannelIdentityResult']
        check(outer['calls'] == (217 if case == 'extraction-mismatch' else 222)
              and outer['hex_characters'] == 2 * outer['payload_bytes'], 'actual outer hex accounting: ' + case)
        all_self = sum(r['exclusive_seconds'] for p in phases.values() for r in p['functions'])
        codec_self = sum(r['exclusive_seconds'] for p in phases.values() for r in p['functions'] if r['file'].endswith('/domain/codec.py'))
        derived[case] = {'baseline_stage_seconds': sum(baseline['wall_seconds'].values()),
                         'baseline_peak_rss_kib': baseline['process_peak_rss_kib'],
                         'all_phase_domain_codec_self_fraction': codec_self / all_self,
                         'outer_hex_fraction': outer['hex_characters'] / baseline['wire_bytes']}
    extra = load('memory-profile.command.json')
    check(extra['exit_code'] == 0 and datetime.fromisoformat(extra['started_at_utc']) >= finish, 'extra memory diagnostic serial after six')
    check(extra['tool_sha256'] == sha(OUT / 'memory_probe.py'), 'memory observer tool identity')
    check(extra['selfcheck_sha256'] == sha(OUT / 'memory-probe-selfcheck.json'), 'memory observer selfcheck identity')
    for stream in ('stdout', 'stderr'):
        check(sha(OUT / ('memory-profile.' + stream + '.txt')) == extra[stream + '_sha256'], 'memory diagnostic raw: ' + stream)
    mem = load('memory-profile-normal-readback.json')
    baseline = load('baseline-normal-readback.json')
    check(mem['wire_sha256'] == baseline['wire_sha256'] and mem['capture_sources'] == baseline['capture_sources'], 'memory diagnostic same complete result wire/captures')
    events = load('memory-profile-events.json')
    refreshed = [i for i, event in enumerate(events) if event['after']['ru_maxrss_kib'] > event['before']['ru_maxrss_kib']]
    check(len(events) == 65 and len(refreshed) == 5, '65 existing hex calls / five HWM refreshes')
    check(events[34]['hex_characters'] == 118841892 and events[34]['after']['ru_maxrss_kib'] == mem['process_peak_rss_kib'] == 7319108,
          'event34 reaches actual final process HWM')
    sys.path.insert(0, str(ROOT))
    def module(name):
        spec = importlib.util.spec_from_file_location('review_' + name, OUT / (name + '.py'))
        value = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(value)
        return value
    probe, observer = module('probe'), module('memory_probe')
    shared, equal = bytes(bytearray(b'abc')), bytes(bytearray(b'abc'))
    check(shared is not equal, 'independent equal bytes have distinct identities')
    graph = probe.census((shared, shared, equal))
    check((graph['unique_bytes_payload'], graph['content_unique_bytes_payload'], graph['logical_path_bytes_payload']) == (6, 3, 9),
          'independent census sharing vs content vs logical paths')
    from layauto_v2.domain import publication_codec
    from layauto_v2.domain.evidence import SourceRef
    from layauto_v2.domain.codec import canonical_bytes, decode
    original = publication_codec.encode_record
    value = SourceRef('independent-review', 'a' * 64)
    plain = original(value)
    with probe.WireMeter().active() as meter:
        check(publication_codec.encode_record(value) == plain and publication_codec.decode_record(plain) == value,
              'small codec hook preserves bytes and DTO')
        check(decode(canonical_bytes(b'abc')) == b'abc', 'small exact bytes roundtrip')
    check(publication_codec.encode_record is original and not meter.stack, 'codec hooks restored')
    check(meter.result()['bytes_to_hex']['<root>']['payload_bytes'] == 6, 'canonical decode re-encode accounted separately')
    sentinel = object()
    class ForeignPattern:
        def __ne__(self, other):
            raise AssertionError('foreign pattern compared by diagnostic hook')
    def passthrough(*args):
        return sentinel
    check(observer.observer(passthrough, [], minimum=1)(ForeignPattern(), 'ab') is sentinel, 'optional native-pattern suggestion verified')
    failure = TypeError('independent sentinel failure')
    cause, context = RuntimeError('cause'), LookupError('context')
    failure.__cause__, failure.__context__, failure.__suppress_context__ = cause, context, True
    def fail(*args):
        raise failure
    try:
        observer.observer(fail, [], minimum=1)(r'(?:[0-9a-f]{2})*', 'ab')
    except TypeError as raised:
        check(raised is failure and raised.__cause__ is cause and raised.__context__ is context and raised.__suppress_context__ is True,
              'memory observer preserves original exception history')
    else:
        raise AssertionError('lost original exception')
    reviewed = {name: sha(ROOT / name) for name in paths if (ROOT / name).is_file()}
    (EVIDENCE / 'reviewed-manifest.json').write_text(json.dumps({'base': BASE, 'head': HEAD, 'files': reviewed}, indent=2) + '\n')
    result = {'status': 'passed', 'utc': datetime.now(timezone.utc).isoformat(), 'python': sys.version,
              'cwd': str(ROOT), 'base': BASE, 'head': HEAD, 'count': len(checks), 'checks': checks,
              'derived': derived, 'memory_hwm_refresh_events': refreshed,
              'script_sha256': sha(Path(__file__)), 'not_run': 'No heavy product combinations or inherited full matrices rerun.'}
    (EVIDENCE / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(str(len(checks)) + ' independent lightweight evidence/observer checks passed')


if __name__ == '__main__':
    main()
