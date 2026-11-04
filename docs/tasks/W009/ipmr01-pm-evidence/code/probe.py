"""Bounded independent PM probe of final IPMR-01/FXR-01 boundaries."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

from layauto_v2.domain.codec import canonical_bytes, decode
from layauto_v2.domain.evidence import EvidenceRecord, SourceFile
from layauto_v2.domain.results import EvidenceIssue, ParseResult
from layauto_v2.domain import publication_codec
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import build_effective_geometry, build_geometry, geometry_from_parse_result
from layauto_v2.normalization.effective_codec import encode_record, decode_record

ROOT = Path('/workspace/Layauto')
observations = []

class ChangingList(list):
    def __init__(self, first, later):
        super().__init__(first)
        self.later = later
        self.calls = 0
    def __iter__(self):
        self.calls += 1
        return super().__iter__() if self.calls == 1 else iter(self.later)

class ChangingTuple(tuple):
    def __new__(cls, first, later):
        self = super().__new__(cls, first)
        self.later = later
        self.calls = 0
        return self
    def __iter__(self):
        self.calls += 1
        return super().__iter__() if self.calls == 1 else iter(self.later)

source = SourceFile('pm-single-snapshot', b'x')
evidence = EvidenceRecord('example', {}, (source.ref(),))
issue = EvidenceIssue('binding', 'Example', 'example', source.ref())
items = {'evidence': source.ref(), 'sources': source, 'completed': evidence, 'issues': issue}
for cls in (ChangingList, ChangingTuple):
    for name, item in items.items():
        for valid_first in (True, False):
            values = cls((item,) if valid_first else (None,), (None,) if valid_first else (item,))
            try:
                if name == 'evidence':
                    snapshot = EvidenceRecord('example', {}, values).sources
                elif name == 'issues':
                    snapshot = ParseResult('error', None, values, (), (source,)).issues
                elif name == 'completed':
                    snapshot = ParseResult('success', {}, (), values, (source,)).completed
                else:
                    snapshot = ParseResult('success', {}, (), (), values).sources
            except ValueError:
                assert not valid_first
                outcome = 'explicit_rejection'
            else:
                assert valid_first and type(snapshot) is tuple and snapshot == (item,)
                if isinstance(values, list):
                    values.clear()
                assert snapshot == (item,)
                outcome = 'safe_snapshot'
            assert values.calls == 1
            observations.append({'probe': 'single_snapshot', 'container': cls.__name__, 'field': name,
                                 'valid_first': valid_first, 'iterations': values.calls, 'outcome': outcome})

parsed = read_inputs(ROOT / 'tests/fixtures/w003_m1/site_config.yaml')
result = build_effective_geometry(build_geometry(geometry_from_parse_result(parsed)))
assert result.status == 'success'
outer_wire = encode_record(result)
assert encode_record(decode_record(outer_wire)) == outer_wire
observations.append({'probe': 'normal_actual_w009', 'outcome': 'roundtrip_identical'})
source_wire = publication_codec.encode_record(source)
for where, wire, decoder in (('SourceFile', source_wire, publication_codec.decode_record),
                              ('W009_result', outer_wire, decode_record)):
    for cls in (RuntimeError, ValueError, TypeError, KeyError, AttributeError, IndexError,
                UnicodeError, KeyboardInterrupt, SystemExit):
        failure = cls('PM isolated source-hash failure')
        cause = OSError('existing cause')
        context = LookupError('existing context')
        failure.__cause__ = cause
        failure.__context__ = context
        failure.__suppress_context__ = False
        def broken(*args, **kwargs):
            raise failure
        with patch('layauto_v2.domain.evidence.hashlib', SimpleNamespace(sha256=broken)):
            try:
                decoder(wire)
            except BaseException as observed:
                assert observed is failure
                assert observed.__cause__ is cause and observed.__context__ is context
                assert observed.__suppress_context__ is False
            else:
                raise AssertionError('source hashing fault not reached')
        observations.append({'probe': 'source_hash', 'entry': where, 'exception': cls.__name__,
                             'same_object': True, 'prior_history_preserved': True})

def mutable(value):
    if hasattr(value, 'items'):
        return {k: mutable(v) for k, v in value.items()}
    if type(value) is tuple:
        return [mutable(v) for v in value]
    return value

for field, bad in (('uri', None), ('uri', 7), ('uri', ''), ('data', None), ('data', 7), ('data', 'text')):
    tree = mutable(decode(source_wire))
    tree['value']['fields'][field] = {'scalar': bad}
    try:
        publication_codec.decode_record(canonical_bytes(tree))
    except ValueError:
        observations.append({'probe': 'malformed_source_wire', 'field': field, 'bad': bad,
                             'outcome': 'explicit_rejection'})
    else:
        raise AssertionError((field, bad))

paths = subprocess.check_output(['git', 'diff', '--name-only', 'cdf3d2d', 'HEAD', '--', 'layauto_v2', 'tests'],
                                cwd=ROOT, text=True).splitlines()
print(json.dumps({'status': 'passed', 'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT,
             text=True).strip(), 'python': sys.version, 'executable': sys.executable,
             'platform': platform.platform(), 'cwd': str(Path.cwd()), 'case_count': len(observations),
             'source_sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
             'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             'observations': observations}, indent=2, sort_keys=True))
