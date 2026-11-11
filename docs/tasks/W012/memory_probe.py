"""Additional complete readback diagnostic: observe existing hex validation only.

No large synthetic input, extra encode, replacement matcher or runtime edits.
Original probe/tools stay frozen; this is explicitly not a baseline sample.
"""
import importlib.util
import hashlib
import json
from pathlib import Path
import re
import resource
import sys
import time

OUT = Path('/workspace/Layauto/docs/tasks/W012')


def memory():
    data = dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
    return {'VmRSS': data['VmRSS'].strip(), 'ru_maxrss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}


def observer(original, events, minimum=1_000_000):
    def observed(pattern, string, flags=0):
        if type(pattern) is not str or pattern != r'(?:[0-9a-f]{2})*' or type(string) is not str or len(string) < minimum:
            return original(pattern, string, flags)
        before = memory()
        start = time.perf_counter()
        try:
            return original(pattern, string, flags)
        finally:
            elapsed = time.perf_counter()-start
            events.append({'hex_characters':len(string), 'before':before, 'after':memory(),
                           'matcher_seconds':elapsed,
                           'caller':sys._getframe(1).f_code.co_filename,
                           'caller_function':sys._getframe(1).f_code.co_name})
    return observed


def selfcheck():
    events = []
    match = observer(re.fullmatch, events, minimum=1)
    assert match(r'(?:[0-9a-f]{2})*','ab01').group() == 'ab01'
    assert match(r'(?:[0-9a-f]{2})*','ABC') is None
    assert [row['hex_characters'] for row in events] == [4,3]
    failure = TypeError('selfcheck original matcher failure')
    cause, context = RuntimeError('existing cause'), LookupError('existing context')
    failure.__cause__, failure.__context__, failure.__suppress_context__ = cause, context, True
    def fail(*args, **kwargs):
        raise failure
    try:
        observer(fail, events, minimum=1)(r'(?:[0-9a-f]{2})*','ab')
    except TypeError as raised:
        assert raised is failure
        assert failure.__cause__ is cause and failure.__context__ is context and failure.__suppress_context__ is True
    else:
        raise AssertionError('original exception lost')
    (OUT/'memory-probe-selfcheck.json').write_text(json.dumps({'status':'passed',
        'tool_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'checks':['existing match/invalid match unchanged','length-only metadata','original exception object/cause/context/suppression propagated'],
        'events':events},indent=2)+'\n')
    print('memory observer lightweight selfcheck passed')


def main():
    assert json.loads((OUT/'memory-probe-selfcheck.json').read_text())['tool_sha256'] == hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    spec = importlib.util.spec_from_file_location('w012_probe', OUT/'probe.py')
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    original = re.fullmatch
    events = []
    observed = observer(original, events)
    re.fullmatch = observed
    try:
        probe.run('normal-readback','memory-profile',OUT/'memory-profile-normal-readback.json')
    finally:
        re.fullmatch = original
        probe.dump(OUT/'memory-profile-events.json',events)
    path = OUT/'memory-profile-normal-readback.json'
    receipt = json.loads(path.read_text())
    receipt.update({'mode':'memory-profile', 'instrumentation':'observe original re.fullmatch for existing hex strings >=1MB',
                    'memory_probe_sha256':probe.sha(Path(__file__).read_bytes()),
                    'baseline_warning':'Instrumented diagnostic; do not use these times as baseline',
                    'interpretation':'A new ru_maxrss reached between before/after occurred during this matcher call. Not an allocation delta or general RSS attribution.'})
    probe.dump(path,receipt)


if __name__ == '__main__':
    selfcheck() if '--selfcheck' in sys.argv else main()
