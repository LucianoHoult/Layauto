"""Independent finite oracle, real original/current source, and failure controls.

The oracle consumes nibbles with a pending-nibble state and builds bytes. It
does not use either regex, len/parity, fromhex, or the formal test's predicate.
This is finite synthetic evidence, not a production/input-size guarantee.
"""
from __future__ import annotations

from collections import Counter
import hashlib
from itertools import product
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType, SimpleNamespace

ROOT = Path(__file__).resolve().parents[6]
OUT = Path(__file__).resolve().parent
BASE = '0a3326aa363477724465886cd05874d0997fba3e'
HEAD = 'e4179dd42cc0de853df73bafd9140a363c8fa5be'
counts = Counter()


def check(condition, label):
    if not condition:
        raise AssertionError(label)
    counts[label] += 1


modules = []
source_hashes = {}
for name, rev in (('original', BASE), ('delivered', HEAD)):
    source = subprocess.check_output(['git', 'show', rev + ':layauto_v2/domain/codec.py'], cwd=ROOT)
    (OUT / (name + '-codec.py.txt')).write_bytes(source)
    module = ModuleType('premerge_' + name)
    sys.modules[module.__name__] = module
    exec(compile(source, module.__name__, 'exec'), module.__dict__)
    modules.append(module)
    source_hashes[name] = hashlib.sha256(source).hexdigest()

NIBBLES = {char: digit for digit, char in enumerate('0123456789abcdef')}


def oracle(text):
    pending = None
    output = bytearray()
    for char in text:
        digit = NIBBLES.get(char)
        if digit is None:
            return None
        if pending is None:
            pending = digit
        else:
            output.append(pending * 16 + digit)
            pending = None
    return bytes(output) if pending is None else None


def wire(text):
    return json.dumps({'$bytes': text}, ensure_ascii=False, separators=(',', ':')).encode()


def outcome(module, data):
    try:
        value = module.decode(data)
        return ('ok', module.canonical_bytes(value))
    except Exception as exc:
        return ('error', type(exc).__name__, exc.args)


def candidate(text):
    expected = oracle(text)
    data = wire(text)
    outcomes = []
    for module in modules:
        result = outcome(module, data)
        outcomes.append(result)
        check((result[0] == 'ok') == (expected is not None), 'finite-acceptance')
        if expected is not None:
            check(module.decode(data) == expected, 'finite-value')
            check(result[1] == data, 'finite-canonical')
    check(outcomes[0] == outcomes[1], 'finite-before-after-errors-and-bytes')
    counts['candidates'] += 1


# Complete Latin-1 pairs include all ASCII pairs, control characters and NBSP.
for pair in product(map(chr, range(256)), repeat=2):
    candidate(''.join(pair))
# Complete two-byte payload universe gives every valid four-nibble spelling.
for left, right in product(range(256), repeat=2):
    candidate(bytes((left, right)).hex())
# Non-pair-aligned finite words, including empty, and odd/even invalid tails.
for size in range(6):
    for chars in product('0afF \n１', repeat=size):
        candidate(''.join(chars))
for char in ('Ｆ', 'ｆ', '٠', '١', '𝟎', '\u2028', '\u200b', '\ufeff', 'é', 'K'):
    for text in (char, char + '0', '0' + char, '00' + char + '0'):
        candidate(text)
for suffix in ('', '0', 'F0', 'g0', '  ', '\n\n', '０0', '\x000'):
    candidate('0123456789abcdef' * 8192 + suffix)

# JSON syntax/tag/duplicate/canonical and expected failure error text controls.
json_cases = (
    b'{"$bytes":null}', b'{"$bytes":[]}', b'{"$bytes":{}}', b'{"$bytes":0}',
    b'{"$bytes":true}', b'{"$bytes":"00","foreign":0}', b'{"$bytes":"00","$bytes":"01"}',
    b'{"$map":{"x":1,"x":2}}', b'{"$bytes": "00"}', b' {"$bytes":"00"}',
    b'{"$bytes":"00"}\n', b'{"$bytes":"\\u0030\\u0030"}', b'{"$bytes":"00"}{}',
    b'[NaN,{"$bytes":"00"}]', b'[1.0,{"$bytes":"00"}]', b'null\n',
    b'{"$bytes":"0"}', b'{"$bytes":"FF"}', b'{"$bytes":"00",}',
)
for data in json_cases:
    before, after = [outcome(module, data) for module in modules]
    check(before == after and before[0] == 'error', 'json-failure-differential')

raw_type_results = {}
class InputBytes(bytes):
    pass
for data in (b'{"$bytes":"00"}', bytearray(b'{"$bytes":"00"}'),
             InputBytes(b'{"$bytes":"00"}'), '{"$bytes":"00"}',
             memoryview(b'{"$bytes":"00"}'), None, 7, []):
    a, b = [outcome(module, data) for module in modules]
    check(a == b, 'public-ingress-types-unchanged')
    raw_type_results[type(data).__name__] = {
        'outcome': a[0], 'detail': a[1].hex() if isinstance(a[1], bytes) else a[1]}

# Observe real json.loads result and ordering separately from canonical output.
for module in modules:
    original_re, original_canonical = module.re, module.canonical_bytes
    for text in ('', '0', '00', 'aff', 'F0', ' \n', '００'):
        calls = []
        def match(pattern, raw, flags=0):
            calls.append((type(raw), raw))
            return original_re.fullmatch(pattern, raw, flags)
        module.re = SimpleNamespace(fullmatch=match)
        outcome(module, wire(text))
        check(calls == [(str, text)], 'public-one-matcher-native-str')
    module.re = original_re
    calls = []
    def canonical(value):
        calls.append(value)
        return original_canonical(value)
    module.canonical_bytes = canonical
    check(outcome(module, b'{"$bytes":"\\u0030\\u0030"}')[0] == 'error', 'canonical-spelling-rejected')
    check(calls == [b'\x00'], 'canonical-check-after-json-and-hex')
    module.re, module.canonical_bytes = original_re, original_canonical

# Only legal words reach fromhex; its return is tested independently above.
for module in modules:
    original_re = module.re
    for text in ('', '0', '00', 'aff', 'F0', ' \n', '００'):
        calls = []
        def match(pattern, raw, flags=0):
            calls.append('matcher')
            return original_re.fullmatch(pattern, raw, flags)
        def fromhex(raw):
            calls.append('fromhex')
            return bytes.fromhex(raw)
        module.re = SimpleNamespace(fullmatch=match)
        module.bytes = SimpleNamespace(fromhex=fromhex)
        try:
            module._decode({'$bytes': text})
        except ValueError:
            pass
        check(calls == (['matcher', 'fromhex'] if oracle(text) is not None else ['matcher']),
              'matcher-first-fromhex-legal-only')
    module.re = original_re
    del module.bytes

# Original exceptions retain object, explicit cause, implicit context/suppression.
for module in modules:
    original_re = module.re
    for boundary, cls, suppress in product(('matcher', 'fromhex'),
            (ValueError, TypeError, KeyError, KeyboardInterrupt, SystemExit), (False, True)):
        failure = cls('independent premerge injected fault')
        cause, context = RuntimeError('prior cause'), LookupError('prior context')
        failure.__cause__, failure.__context__, failure.__suppress_context__ = cause, context, suppress
        def fail(*args, **kwargs):
            raise failure
        if boundary == 'matcher':
            module.re = SimpleNamespace(fullmatch=fail)
        else:
            module.bytes = SimpleNamespace(fromhex=fail)
        try:
            module.decode(wire('00'))
        except BaseException as caught:
            check(caught is failure and caught.__cause__ is cause and caught.__context__ is context
                  and caught.__suppress_context__ is suppress, 'exception-identity-history')
        else:
            raise AssertionError('injected fault was hidden')
        module.re = original_re
        module.__dict__.pop('bytes', None)

# Retain the documented private subclass distinction, without changing admission.
class LenFault(str):
    def __len__(self):
        raise RuntimeError('private len side effect')
private_results = []
for module in modules:
    try:
        module._decode({'$bytes': LenFault('00')})
        private_results.append('accepted')
    except RuntimeError as exc:
        private_results.append(str(exc))
check(private_results == ['accepted', 'private len side effect'], 'private-subclass-boundary-retained')

result = {
    'reviewed_base': BASE, 'reviewed_head': HEAD, 'source_sha256': source_hashes,
    'python': sys.version, 'executable': sys.executable, 'checks_by_kind': dict(counts),
    'public_ingress_type_results': raw_type_results, 'private_len_fault_before_after': private_results,
    'finite_scope': 'Latin-1 pairs, all 65536 two-byte spellings, 7-symbol words lengths 0..5, Unicode witnesses, 131072-character prefix tails',
    'limitations': 'Finite synthetic probes; no complete Result performance or production/max-input assurance.',
    'must_fix_findings': [],
}
(OUT / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(result, ensure_ascii=False, indent=2))
