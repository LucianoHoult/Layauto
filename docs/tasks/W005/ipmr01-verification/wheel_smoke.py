"""Run outside the source tree with -I -B against a clean wheel installation."""
import hashlib
import itertools
import json
from pathlib import Path
import shutil
import sys
import sysconfig
from tempfile import TemporaryDirectory

import layauto_v2
import layauto_v2.importers.config as config_module
from layauto_v2.domain.codec import canonical_bytes, digest
from layauto_v2.domain.evidence import SourceFile
from layauto_v2.domain.results import InputError
from layauto_v2.importers import read_inputs
from layauto_v2.importers.config import load_document


fixture = Path(sys.argv[1]).resolve()
installed = Path(config_module.__file__).resolve()
assert installed.is_relative_to(Path(sysconfig.get_path('purelib')).resolve()), installed
assert 'site-packages' in installed.parts
result = read_inputs(fixture / 'site_config.yaml')
assert result.status == 'success', result.issues
assert len(result.value['gds']['elements']) == 40
assert len(result.value['query']['net_regions']['records']) == 8
assert len(digest(result.value)) == 64

expected_kinds = ['config', 'tech', 'policies', 'header', 'gds', 'source_cdl', 'target_cdl', 'body', 'query']
with TemporaryDirectory(prefix='w005-ipmr01-wheel-') as directory:
    invalid_escapes = [(r'\ud800', 'InvalidUnicodeScalar'),
                       (r'\U00110000', 'InvalidDocumentSyntax'),
                       (r'\UFFFFFFFF', 'InvalidDocumentSyntax')]
    for index, (position, (escape, code)) in enumerate(itertools.product(('key', 'value'), invalid_escapes)):
        root = Path(directory) / str(index)
        shutil.copytree(fixture, root)
        path = root / 'query/normalized/device_regions.yaml'
        cache = json.loads(path.read_text())
        if position == 'key':
            cache['UNICODE_MARKER'] = cache.pop('schema_version')
        else:
            cache['schema_version'] = 'UNICODE_MARKER'
        raw = (json.dumps(cache).replace('UNICODE_MARKER', escape) + '\n').encode()
        path.write_bytes(raw)
        failed = read_inputs(root / 'site_config.yaml')
        assert failed.status == 'error' and failed.value is None
        issue = failed.issues[0]
        assert issue.code == code
        assert Path(issue.source.uri) == path
        assert issue.source.line == 1 and issue.source.column > 1
        assert issue.source.sha256 == hashlib.sha256(raw).hexdigest()
        assert next(source for source in failed.sources if source.uri == issue.source.uri).data == raw
        assert [record.kind for record in failed.completed] == expected_kinds
        for record in failed.completed:
            assert len(digest(record.payload)) == 64

    semantics = []
    hashes = []
    for escaped in (True, False):
        root = Path(directory) / str(escaped)
        shutil.copytree(fixture, root)
        path = root / 'site_config.yaml'
        site = json.loads(path.read_text())
        site['note'] = 'example ' + chr(0x1F600)
        path.write_text(json.dumps(site, ensure_ascii=escaped) + '\n', encoding='utf-8')
        hashes.append(hashlib.sha256(path.read_bytes()).hexdigest())
        header_path = root / 'query/header.json'
        header = json.loads(header_path.read_text())
        for entry in header['closure']['entries']:
            if entry['uri'] == 'site_config.yaml':
                entry['sha256'] = hashes[-1]
        closure = json.dumps(header['closure']['entries'], sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
        header['closure']['sha256'] = hashlib.sha256(closure).hexdigest()
        header_path.write_text(json.dumps(header) + '\n')
        accepted = read_inputs(path)
        assert accepted.status == 'success', accepted.issues
        assert accepted.value['config']['note'] == site['note']
        assert len(digest(accepted.value)) == 64
        semantics.append(canonical_bytes(accepted.value['config']))
        for record in accepted.completed:
            assert len(digest(record.payload)) == 64
    assert hashes[0] != hashes[1] and semantics[0] == semantics[1]

raw = '{"\\ud83d\\ude00": 1, "\U0001f600": 2}'.encode()
try:
    load_document(SourceFile('duplicate.json', raw))
except InputError as exc:
    assert exc.issue.code == 'DuplicateKey'
else:
    raise AssertionError('decoded duplicate key was accepted')

print(json.dumps({
    'python': sys.version,
    'installed_module': layauto_v2.__file__,
    'installed_config': str(installed),
    'installed_config_sha256': hashlib.sha256(installed.read_bytes()).hexdigest(),
    'accepted_shapes': 40,
    'net_regions': 8,
    'invalid_cache_key_and_value': 'surrogate and two out-of-range escapes: typed error; actual bytes/hash/location and 9 completed retained',
    'escaped_and_literal_note': 'equal parsed config; all successful payload digests computed',
    'decoded_duplicate_key': 'DuplicateKey',
}, indent=2))
