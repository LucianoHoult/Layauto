"""PM's independent small contract check of real before/current codec sources."""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

ROOT = Path('/workspace/Layauto')
OUT = Path(__file__).resolve().parent
BASE = '7f7c1304bdafd941791421cef64864fb1616303c'
CODEC = 'layauto_v2/domain/codec.py'
checks = 0


def verify(condition, description):
    global checks
    assert condition, description
    checks += 1


def load(name, data):
    path = OUT / (name + '.py')
    path.write_bytes(data)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def expected(text):
    return len(text) % 2 == 0 and all(character in '0123456789abcdef' for character in text)


def outcome(function, value):
    try:
        result = function(value)
    except ValueError as failure:
        return ('reject', str(failure))
    return ('accept', result)


before_source = subprocess.check_output(['git', 'show', BASE + ':' + CODEC], cwd=ROOT)
after_source = (ROOT / CODEC).read_bytes()
before, after = load('source_original_before', before_source), load('source_delivered_after', after_source)
old_condition = "re.fullmatch(r'(?:[0-9a-f]{2})*', raw)"
new_condition = "re.fullmatch(r'[0-9a-f]*', raw) and len(raw) % 2 == 0"
normalized = after_source.decode().replace(new_condition, old_condition)
verify(ast.dump(ast.parse(normalized)) == ast.dump(ast.parse(before_source)), 'all executable code unchanged except hex condition')
frozen = json.loads((ROOT / 'docs/tasks/W012/A1/performance/frozen-identity.json').read_bytes())
verify(hashlib.sha256(before_source).hexdigest() == frozen['sources']['before'][CODEC], 'real source-original-before matches measured frozen before identity')
verify(hashlib.sha256(after_source).hexdigest() == frozen['sources']['after'][CODEC], 'delivered after matches measured frozen after identity')

candidates = [''.join(pair) for pair in itertools.product(map(chr, range(128)), repeat=2)]
for length in range(5):
    candidates.extend(''.join(chars) for chars in itertools.product('0afF \n０', repeat=length))
candidates.extend(['', 'f', 'ＦＦ', 'ｆｆ', '١١', '𝟎𝟎', '\u00a0\u00a0', '\u2028\u2028', 'ff\x00'])
candidates.extend('0af9' * 1024 + suffix for suffix in ('', '0', 'F0', 'g0', '  ', '\n\n', '０0'))
for text in candidates:
    old = outcome(before._decode, {'$bytes': text})
    new = outcome(after._decode, {'$bytes': text})
    verify(old == new, 'real before/after branch result differs')
    verify((new[0] == 'accept') == expected(text), 'independent native-string language oracle')
    if expected(text):
        verify(new[1] == bytes.fromhex(text), 'accepted bytes value')

native_ingress = []
for module in (before, after):
    original_re = module.re
    def observe(pattern, text):
        native_ingress.append(type(text).__name__)
        verify(type(text) is str, 'public JSON ingress is a native str')
        return original_re.fullmatch(pattern, text)
    module.re = SimpleNamespace(fullmatch=observe)
    for text in ('', '0', '00', 'ff', 'F0', ' \n', '００'):
        wire = json.dumps({'$bytes': text}, ensure_ascii=False, separators=(',', ':')).encode()
        result = outcome(module.decode, wire)
        verify((result[0] == 'accept') == expected(text), 'public language')
        if expected(text):
            verify(module.canonical_bytes(result[1]) == wire, 'canonical bytes unchanged')
            verify(module.digest(result[1]) == hashlib.sha256(wire).hexdigest(), 'actual canonical digest unchanged')
    module.re = original_re

bad_wires = [b'{"$bytes":null}', b'{"$bytes":[]}', b'{"$bytes":0}', b'{"$bytes":true}',
             b'{"$bytes":"00","foreign":0}', b'{"$bytes":"00","$bytes":"00"}',
             b'{"$bytes": "00"}', b' {"$bytes":"00"}', b'{"$bytes":"00"}\n',
             b'{"$bytes":"\\u0030\\u0030"}', b'{"$bytes":"00"}{}', b'[NaN,{"$bytes":"00"}]']
for wire in bad_wires:
    verify(outcome(before.decode, wire) == outcome(after.decode, wire), 'public malformed/canonical behavior unchanged')
    verify(outcome(after.decode, wire)[0] == 'reject', 'public malformed/canonical rejection')
for data in (b'', bytes(range(256)), b'\x00\xff'):
    old_wire, new_wire = before.canonical_bytes(data), after.canonical_bytes(data)
    verify(old_wire == new_wire, 'encoder output unchanged')
    verify(before.decode(old_wire) == after.decode(new_wire) == data, 'public byte roundtrip')

fault_cases = 0
for module in (before, after):
    original_re = module.re
    for failure_type in (ValueError, TypeError, KeyError, KeyboardInterrupt, SystemExit):
        for suppression in (False, True):
            for site in ('matcher', 'fromhex'):
                for text in (('', '0', '00', 'F0') if site == 'matcher' else ('', '00')):
                    failure = failure_type('PM independent fault')
                    cause, context = RuntimeError('prior cause'), LookupError('prior context')
                    failure.__cause__, failure.__context__, failure.__suppress_context__ = cause, context, suppression
                    def fail(*args):
                        raise failure
                    if site == 'matcher':
                        module.re = SimpleNamespace(fullmatch=fail)
                    else:
                        module.bytes = SimpleNamespace(fromhex=fail)
                    try:
                        module.decode(json.dumps({'$bytes': text}, separators=(',', ':')).encode())
                    except BaseException as caught:
                        verify(caught is failure, 'exact injected exception identity')
                        verify(caught.__cause__ is cause and caught.__context__ is context, 'cause and context unchanged')
                        verify(caught.__suppress_context__ is suppression, 'suppression unchanged')
                    else:
                        raise AssertionError('fault lost')
                    module.re = original_re
                    if site == 'fromhex':
                        del module.bytes
                    fault_cases += 1

# Keep the already disclosed private-subclass behavioral difference explicit.
class Hostile(str):
    def __len__(self):
        raise LookupError('private str subclass length override')

verify(before._decode({'$bytes': Hostile('00')}) == b'\x00', 'old private subclass uses underlying string')
try:
    after._decode({'$bytes': Hostile('00')})
except LookupError:
    checks += 1
else:
    raise AssertionError('new private __len__ boundary not observed')

profile_counts = {}
profile_counts_entries = 0
selected = {'__init__', '__post_init__', '_require_input', '_evaluate', '_analyze', 'normalize', 'encode_record', 'decode_record'}
for side in ('before', 'after'):
    directory = ROOT / 'docs/tasks/W012/A1/profile'
    receipt = json.loads((directory / (side + '-normal-readback-r1.json')).read_bytes())
    profile = json.loads((directory / (side + '-normal-readback-r1.profile.json')).read_bytes())
    prefix = receipt['runtime_root'] + '/'
    profile_counts[side] = {
        phase: {(row['file'].removeprefix(prefix), row['line'], row['function']): (row['calls'], row['primitive_calls'])
                for row in data['functions'] if row['file'].startswith(prefix + 'layauto_v2/') and row['function'] in selected}
        for phase, data in profile.items()
    }
verify(profile_counts['before'] == profile_counts['after'], 'actual profile constructor/authentication call counts equal, phase by phase')
for counts in profile_counts['after'].values():
    profile_counts_entries += len(counts)

result = {
    'status': 'passed', 'checks': checks, 'finite_candidates': len(candidates), 'exception_cases': fault_cases,
    'base': BASE, 'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'before_source_sha256': hashlib.sha256(before_source).hexdigest(),
    'after_source_sha256': hashlib.sha256(after_source).hexdigest(),
    'actual_profile_phases': len(profile_counts['after']),
    'actual_profile_constructor_authentication_functions': profile_counts_entries,
    'actual_profile_constructor_authentication_counts_equal': True,
    'checker_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'python': sys.version, 'executable': sys.executable,
    'proof': 'For native strings, H={0..9,a..f}; (HH)* equals H* intersect even length, including empty string.',
    'private_boundary': 'Direct _decode with a str subclass overriding __len__ can differ, as already disclosed by plan review; public json.loads creates native str.',
    'scope': 'Small independent source-before/current language and exception contract probe; no full performance, product matrix or complete nested codec run.',
}
(OUT / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
