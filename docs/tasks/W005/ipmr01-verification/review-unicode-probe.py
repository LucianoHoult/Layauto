"""Independent review probe; run from the reviewed checkout, not a fixture writer."""
import hashlib
import json
from pathlib import Path
import random
import shutil
import subprocess
import tempfile

from layauto_v2.domain.codec import canonical_bytes, digest, freeze_map
from layauto_v2.domain.evidence import SourceFile
from layauto_v2.domain.results import InputError
from layauto_v2.importers import read_inputs
from layauto_v2.importers.config import load_document


print('review_head=' + subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip())
rng = random.Random(5001)
valid = [0x10000, 0x10001, 0x1F600, 0x10FFFE, 0x10FFFF]
valid += [rng.randrange(0x10000, 0x110000) for _ in range(251)]
for value in valid:
    text = 'prefix 字' + chr(value) + ' tail'
    obj = {text: [text, {'inner': text}]}
    escaped = load_document(SourceFile('escaped', json.dumps(obj, ensure_ascii=True).encode()))
    literal = load_document(SourceFile('literal', json.dumps(obj, ensure_ascii=False).encode()))
    assert escaped == literal == freeze_map(obj)
    assert canonical_bytes(escaped) == canonical_bytes(literal) == canonical_bytes(obj)
print('valid_nested_key_value_scalar_pairs=256: independently constructed scalar and canonical bytes match')

for value in range(0xD800, 0xE000):
    for position in ('key', 'value'):
        key = '\\u%04x' % value if position == 'key' else 'x'
        val = '1' if position == 'key' else '"\\u%04x"' % value
        source = SourceFile('invalid', ('{\n  "' + key + '": ' + val + '\n}').encode())
        try:
            load_document(source)
        except InputError as exc:
            assert exc.issue.code == 'InvalidUnicodeScalar'
            assert exc.issue.source == source.ref(line=2, column=3 if position == 'key' else 8)
        else:
            raise AssertionError(hex(value))
print('single_surrogate_key_value_cases=4096: located InvalidUnicodeScalar with source hash')

for value in valid[:32]:
    key = json.dumps(chr(value), ensure_ascii=True)
    literal = json.dumps(chr(value), ensure_ascii=False)
    for first, second in ((key, literal), (literal, key)):
        source = SourceFile('duplicate', ('{\n ' + first + ': 1,\n ' + second + ': 2\n}').encode())
        try:
            load_document(source)
        except InputError as exc:
            assert exc.issue.code == 'DuplicateKey'
            assert exc.issue.source == source.ref(line=3, column=2)
        else:
            raise AssertionError('duplicate accepted')
print('decoded_duplicate_key_cases=64: DuplicateKey at second token')

out_of_range = [0x110000, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF]
out_of_range += [rng.randrange(0x110000, 0x100000000) for _ in range(60)]
for value in out_of_range:
    for position in ('key', 'value'):
        escape = '\\U%08X' % value
        line = f'  "{escape}": 1' if position == 'key' else f'  "key": "{escape}"'
        source = SourceFile('range', ('{\n' + line + '\n}').encode())
        try:
            load_document(source)
        except InputError as exc:
            assert exc.issue.code == 'InvalidDocumentSyntax'
            assert exc.issue.category == 'parse'
            assert exc.issue.source == source.ref(line=2, column=line.index(escape) + 3)
            assert 'U+10FFFF' in exc.issue.message
        else:
            raise AssertionError('out-of-range escape accepted')
print('out_of_range_key_value_cases=128: located InvalidDocumentSyntax')

literal_escape = b"single: '\\UFFFFFFFF'\nplain: \\U00110000\ndouble: \"\\\\UFFFFFFFF\"\n"
assert load_document(SourceFile('literal', literal_escape)) == freeze_map({
    'single': r'\UFFFFFFFF', 'plain': r'\U00110000', 'double': r'\UFFFFFFFF',
})
maximum = load_document(SourceFile('maximum', br'{"\U0010FFFF":"\U0010FFFF"}'))
assert maximum == freeze_map({chr(0x10FFFF): chr(0x10FFFF)})
assert len(digest(maximum)) == 64
print('literal_backslash_and_maximum_scalar: preserved')

expected_kinds = ['config', 'tech', 'policies', 'header', 'gds', 'source_cdl', 'target_cdl', 'body', 'query']
with tempfile.TemporaryDirectory(prefix='w005-independent-unicode-') as tmp:
    for index, (position, escape) in enumerate(
        (position, escape) for position in ('key', 'value')
        for escape in (r'\U00110000', r'\UFFFFFFFF')
    ):
        root = Path(tmp) / str(index)
        shutil.copytree('tests/fixtures/w003_m1', root)
        path = root / 'query/normalized/device_regions.yaml'
        cache = json.loads(path.read_text())
        if position == 'key':
            cache['MARKER'] = cache.pop('schema_version')
        else:
            cache['schema_version'] = 'MARKER'
        raw = (json.dumps(cache).replace('MARKER', escape) + '\n').encode()
        path.write_bytes(raw)
        result = read_inputs(root / 'site_config.yaml')
        assert result.status == 'error' and result.value is None
        issue, = result.issues
        assert issue.code == 'InvalidDocumentSyntax' and issue.category == 'parse'
        assert Path(issue.source.uri) == path
        assert (issue.source.line, issue.source.column) == (1, raw.decode().index(escape) + 3)
        assert issue.source.sha256 == hashlib.sha256(raw).hexdigest()
        source = next(source for source in result.sources if source.uri == issue.source.uri)
        assert source.data == raw
        assert [record.kind for record in result.completed] == expected_kinds
        for record in result.completed:
            assert len(digest(record.payload)) == 64
print('public_cache_out_of_range_cases=4: actual bytes/hash, location, 9 completed payloads retained')
print('all_independent_probes_passed')
