"""Independent finite language/control-flow review; no runtime change or benchmark."""
from contextlib import redirect_stdout
import hashlib
import io
import itertools
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
OLD = r'(?:[0-9a-f]{2})*'
NEW = r'[0-9a-f]*'
checks = 0


def verify(condition, message):
    global checks
    assert condition, message
    checks += 1


def independent(raw):
    return len(raw) % 2 == 0 and all(c in '0123456789abcdef' for c in raw)


def branch(raw, new, matcher=re.fullmatch, converter=bytes.fromhex):
    match = matcher(NEW if new else OLD, raw)
    if match and (not new or len(raw) % 2 == 0):
        return converter(raw)
    raise ValueError('invalid exact wire value')


def main():
    global checks
    candidates = 0
    # All ASCII pairs cover every lower-hex pair and every ASCII invalid pair.
    for left in range(128):
        for right in range(128):
            raw = chr(left) + chr(right)
            expected = independent(raw)
            verify(bool(re.fullmatch(OLD, raw)) == expected, 'old ASCII pair oracle')
            verify((bool(re.fullmatch(NEW, raw)) and len(raw) % 2 == 0) == expected, 'new ASCII pair oracle')
            candidates += 1
    alphabet = ('0', 'a', 'f', 'F', ' ', '\n', '０')
    for length in range(7):
        for chars in itertools.product(alphabet, repeat=length):
            raw = ''.join(chars)
            expected = independent(raw)
            verify(bool(re.fullmatch(OLD, raw)) == expected, 'old finite oracle')
            verify((bool(re.fullmatch(NEW, raw)) and len(raw) % 2 == 0) == expected, 'new finite oracle')
            candidates += 1
    extra = ['', '0', 'f', 'aa', 'abcdef0123456789', 'é0', '٠0', 'ａ0', '𝟎0', '\u00a00', '\u200b0',
             '\u20280', '0\r\n', '\x000', 'ab' * 32768, 'ab' * 32768 + '0', 'ab' * 32768 + 'F0']
    for raw in extra:
        expected = independent(raw)
        verify(bool(re.fullmatch(OLD, raw)) == expected, 'old boundary oracle')
        verify((bool(re.fullmatch(NEW, raw)) and len(raw) % 2 == 0) == expected, 'new boundary oracle')
        candidates += 1
    for byte in range(256):
        data = bytes((byte,))
        verify(branch(data.hex(), False) == data == branch(data.hex(), True), 'all byte conversions')
    data = bytes(range(256))
    verify(branch(data.hex(), False) == data == branch(data.hex(), True), 'all bytes sequence')

    # Observe only candidate condition flow, not a monkeypatched product module.
    for raw in ('', '00', '0', 'F0', ' \n', 'é0'):
        for new in (False, True):
            calls = []
            def match(pattern, value):
                calls.append(('matcher', value))
                return re.fullmatch(pattern, value)
            def convert(value):
                calls.append(('fromhex', value))
                return bytes.fromhex(value)
            try:
                branch(raw, new, match, convert)
            except ValueError:
                verify(not independent(raw), 'rejection only outside language')
            verify([c[0] for c in calls] == (['matcher', 'fromhex'] if independent(raw) else ['matcher']),
                   'matcher called once before fromhex, including odd and invalid')
    for failure_type in (ValueError, TypeError, KeyError, KeyboardInterrupt, SystemExit):
        for suppression in (False, True):
            for site in ('matcher', 'fromhex'):
                for new in (False, True):
                    failure = failure_type('independent review injected fault')
                    cause, context = RuntimeError('existing cause'), LookupError('existing context')
                    failure.__cause__, failure.__context__, failure.__suppress_context__ = cause, context, suppression
                    def fail(*args):
                        raise failure
                    try:
                        branch('00', new, fail if site == 'matcher' else re.fullmatch,
                               fail if site == 'fromhex' else bytes.fromhex)
                    except BaseException as caught:
                        verify(caught is failure, 'original exception object')
                        verify(caught.__cause__ is cause, 'original exception cause')
                        verify(caught.__context__ is context, 'original exception context')
                        verify(caught.__suppress_context__ is suppression, 'original suppression')
                    else:
                        raise AssertionError('injected fault lost')

    debug = {}
    for label, pattern in (('old', OLD), ('new', NEW)):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            re.compile(pattern, re.DEBUG)
        debug[label] = buffer.getvalue()
    verify('REPEAT_ONE' in debug['new'], 'CPython current single-character repeat opcode')
    verify(' REPEAT ' in debug['old'], 'old grouped repeat structure recorded')
    verify(' REPEAT ' not in debug['new'], 'new matcher has no grouped repeat opcode')
    sys.path.insert(0, str(ROOT))
    from layauto_v2.domain import codec
    # Public parser produces native str fields even for str/bytes subclasses as data.
    class Text(str):
        pass
    class Binary(bytes):
        pass
    for encoded in (b'{"$bytes":""}', b'{"$bytes":"00ff"}'):
        verify(type(json.loads(encoded)['$bytes']) is str, 'JSON native string')
        verify(codec.decode(Binary(encoded)) == bytes.fromhex(json.loads(encoded)['$bytes']), 'bytes subclass input unchanged')
    invalid = (b'{"$bytes":"FF"}', b'{"$bytes":"0"}', b'{"$bytes":"00 "}',
               b'{"$bytes":"00","$bytes":"00"}', b'{"$bytes":"00","extra":0}',
               b'{"$bytes":0}', b'{ "$bytes":"00"}', b'{"$bytes":"\\u0030\\u0030"}',
               b'{"$bytes":"00"}\n', b'{"$bytes":"00"} true', b'{"$bytes":NaN}')
    for encoded in invalid:
        try:
            codec.decode(encoded)
        except ValueError:
            checks += 1
        else:
            raise AssertionError('current public malformed/canonical rejection changed')
    for encoded in ('{"$bytes":"00"}', Text('{"$bytes":"00"}')):
        try:
            codec.decode(encoded)
        except ValueError:
            checks += 1
        else:
            raise AssertionError('original bytes-equality requirement not present')
    result = {'status':'passed', 'checks':checks, 'finite_candidates':candidates,
              'python':sys.version, 'executable':sys.executable,
              'review_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              'plan_sha256':hashlib.sha256((ROOT/'docs/tasks/W012/A1/plan.md').read_bytes()).hexdigest(),
              'codec_sha256':hashlib.sha256((ROOT/'layauto_v2/domain/codec.py').read_bytes()).hexdigest(),
              'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'regex_debug':debug,
              'scope':'finite language/control-flow and current public parser checks; not product implementation or performance proof'}
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(f'{checks} independent lightweight plan checks passed across {candidates} finite language candidates')


if __name__ == '__main__':
    main()
