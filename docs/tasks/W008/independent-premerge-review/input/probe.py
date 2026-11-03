"""Independent W008 premerge input-boundary probe; edits temporary inputs only.

Run from the reviewed repository with PYTHONPATH=.:tests/contracts.  Setup uses
existing fixture-copy/rebinding utilities, never expected/spec/oracle answers.
Assertions here target source-role identity, not output-count coincidence.
"""
from __future__ import annotations

import builtins
from contextlib import ExitStack
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import runpy
import shutil
import sys
import tempfile
from unittest.mock import patch

from layauto_v2.domain.codec import canonical_bytes, decode
from layauto_v2.domain.evidence import SourceFile
from layauto_v2.domain.publication import InputsReady, RunRequest
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import from_parse_result, normalize
from layauto_v2.normalization import codec as semantic_codec
from layauto_v2.normalization import geometry_input as gi
from layauto_v2.normalization.geometry import build_geometry
from layauto_v2.normalization.geometry_codec import encode_record, decode_record
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository
from w005_cases import FIXTURE, copy_input, read_json, write_json, without_cache, rebind
from w007_cases import mutable

checks = []


def checked(name):
    checks.append(name)
    print('PASS', name, flush=True)


def records(parsed):
    return {r.kind: r for r in parsed.completed}


def reject(parsed, field=None):
    try:
        gi.geometry_from_parse_result(parsed)
    except gi.GeometryInputError as exc:
        assert exc.completed == parsed.completed
        assert exc.issue.source.sha256 is not None
        if field is not None:
            assert exc.issue.source.field == field, exc.issue
        return exc
    raise AssertionError('forged input was accepted')


def replace_document(parsed, kind, mutate):
    """Author new captured JSON and rebind hashes without invoking a decoder."""
    value = mutable(parsed.value)
    mutate(value[kind])
    by_kind = records(parsed)
    old = next(s for s in parsed.sources if s.uri == by_kind[kind].sources[0].uri)
    replacements = {old.uri: SourceFile(old.uri, (json.dumps(value[kind]) + '\n').encode())}
    if kind != 'header':
        for item in value['header']['closure']['entries']:
            if item['uri'] == old.uri:
                item['sha256'] = replacements[old.uri].sha256
        value['header']['closure']['sha256'] = hashlib.sha256(json.dumps(
            value['header']['closure']['entries'], sort_keys=True, separators=(',', ':'),
            ensure_ascii=False).encode()).hexdigest()
        header_uri = by_kind['header'].sources[0].uri
        replacements[header_uri] = SourceFile(header_uri, (json.dumps(value['header']) + '\n').encode())
    completed = tuple(replace(r, payload=value[r.kind] if r.kind in (kind, 'header') else r.payload,
                              sources=tuple(replacements[x.uri].ref() if x.uri in replacements else x
                                            for x in r.sources)) for r in parsed.completed)
    return replace(parsed, value=value, completed=completed,
                   sources=tuple(replacements.get(s.uri, s) for s in parsed.sources))


def no_io():
    def forbidden(*args, **kwargs):
        raise AssertionError('construction performed IO/tool/repository access')
    stack = ExitStack()
    for name in ('open', 'read_bytes', 'read_text', 'resolve'):
        stack.enter_context(patch.object(Path, name, forbidden))
    stack.enter_context(patch.object(builtins, 'open', forbidden))
    stack.enter_context(patch('subprocess.run', forbidden))
    stack.enter_context(patch('subprocess.Popen', forbidden))
    stack.enter_context(patch.object(PublicationRepository, 'read', forbidden))
    return stack


parsed = read_inputs(FIXTURE / 'site_config.yaml')
assert parsed.status == 'success'
with no_io():
    original_input = gi.geometry_from_parse_result(parsed)
    original = build_geometry(original_input)
    assert original.status == 'success'
    assert decode_record(encode_record(original)) == original
checked('real W005 -> authenticated input/build/canonical wire without IO/tools/repository')

# The preserved original asserts old success. Check repaired rejection explicitly.
try:
    runpy.run_path(str(Path.cwd() / 'docs/tasks/W008/review/cr01-reproducer.py'))
except gi.GeometryInputError as exc:
    assert (exc.issue.code, exc.issue.source.uri, exc.issue.source.field) == (
        'GeometryCaptureBindingMismatch', 'site_config.yaml', '/inputs/gds')
    assert len(exc.completed) == len(parsed.completed)
else:
    raise AssertionError('original CR-01 attack did not reject')
checked('preserved CR-01 reproducer now rejects with location and completed facts')

# Same-byte source/target are semantically equal, but their acquisition roles differ.
by_kind = records(parsed)
with tempfile.TemporaryDirectory(prefix='w008-equal-cdl-') as scratch:
    equal_root = copy_input(Path(scratch))
    without_cache(equal_root)
    (equal_root / 'target.cdl').write_bytes((equal_root / 'source.cdl').read_bytes())
    rebind(equal_root)
    equal_cdl = read_inputs(equal_root / 'site_config.yaml')
    assert equal_cdl.status == 'success', equal_cdl.issues
equal_roles = records(equal_cdl)
assert equal_roles['source_cdl'].sources[0].sha256 == equal_roles['target_cdl'].sources[0].sha256
value = mutable(equal_cdl.value)
value['source_cdl'], value['target_cdl'] = value['target_cdl'], value['source_cdl']
swapped = replace(equal_cdl, value=value, completed=tuple(
    replace(r, payload=value[r.kind], sources=equal_roles[
        'target_cdl' if r.kind == 'source_cdl' else 'source_cdl'].sources)
    if r.kind in ('source_cdl', 'target_cdl') else r for r in equal_cdl.completed))
assert from_parse_result(swapped).value['source_cdl']['raw_document'] == value['source_cdl']['raw_document']
reject(swapped, '/inputs/source_cdl')
checked('same SHA source/target role swap rejects although semantic receipt accepts')

# A foreign GDS capture deliberately has the same bytes/hash as the selected one.
gds_ref = by_kind['gds'].sources[0]
gds_capture = next(s for s in parsed.sources if s.uri == gds_ref.uri)
sibling = SourceFile('same-byte-foreign-role.gds', gds_capture.data)
assert sibling.sha256 == gds_capture.sha256 and sibling.ref() != gds_capture.ref()
with_sibling = replace(parsed, sources=parsed.sources + (sibling,))
wrong_backlink = replace(with_sibling, completed=tuple(
    replace(r, sources=(r.sources[0], sibling.ref())) if r.kind == 'body' else r
    for r in parsed.completed))
reject(wrong_backlink, '/source_gds')
checked('body second source rejects foreign URI even with identical GDS bytes/hash')

for kind, role in (('header', 'layout'), ('body', 'source_gds')):
    bad = replace_document(with_sibling, kind, lambda doc, role=role: doc[role].update(uri=sibling.uri))
    reject(bad, '/' + role)
    checked(kind + ' declaration rejects an already captured foreign same-byte role')

# Change both value/completed while retaining captures: provenance is as binding
# as geometry, including positions on a middle record rather than only bbox/count.
for field, new in (('xy_record_index', 900), ('record_index', 901), ('byte_offset', 902)):
    value = mutable(parsed.value)
    value['gds']['elements'][19][field] = new
    forged = replace(parsed, value=value, completed=tuple(
        replace(r, payload=value['gds']) if r.kind == 'gds' else r for r in parsed.completed))
    reject(forged, '/gds')
    checked('coherent middle-record ' + field + ' forgery rejects unchanged capture')

# Direct DTO rejection must survive when buried within a successful result wire.
semantic = from_parse_result(wrong_backlink)
tree = mutable(decode(encode_record(original)))
def replace_nested_input(item):
    if isinstance(item, dict):
        if item.get('record') == 'GeometryInput':
            item['fields']['semantic_input'] = {'semantic_input': semantic_codec.encode_record(semantic)}
            return True
        return any(replace_nested_input(v) for v in item.values())
    if isinstance(item, list):
        return any(replace_nested_input(v) for v in item)
    return False
assert replace_nested_input(tree)
try:
    decode_record(canonical_bytes(tree))
except gi.GeometryInputError as exc:
    assert exc.issue.source.field == '/source_gds'
    assert exc.completed == wrong_backlink.completed
else:
    raise AssertionError('nested wire forgery accepted')
checked('nested successful-result wire reauthenticates same-hash wrong body backlink')

with tempfile.TemporaryDirectory(prefix='w008-input-independent-') as scratch:
    root = copy_input(Path(scratch))
    without_cache(root)
    # Simultaneous legitimate aliases across independent schema roles, plus
    # target reuse of the earlier source and absent late GDS/header declarations.
    site = read_json(root / 'site_config.yaml')
    bundle = read_json(root / site['tech_ref'])
    for name, spec in bundle['owners'].items():
        alias = f'alias-owner-{name}.json'
        (root / alias).symlink_to(spec['path'])
        spec['path'] = alias
    write_json(root / site['tech_ref'], bundle)
    for key in ('tech_ref', 'export_policy_ref', 'validation_policy_ref', 'limitation_ref'):
        old = site[key]
        alias = 'alias-' + key + '.json'
        (root / alias).symlink_to(old)
        site[key] = alias
    for key in ('gds', 'source_cdl', 'query_header', 'body_context'):
        old = site['inputs'][key]
        alias = 'alias-input-' + key
        (root / alias).symlink_to(old)
        site['inputs'][key] = alias
    (root / 'target.cdl').unlink()
    (root / 'target.cdl').symlink_to('source.cdl')
    write_json(root / 'site_config.yaml', site)
    header = read_json(root / 'query/header.json')
    header['closure']['entries'] = [entry for entry in header['closure']['entries'] if entry['uri'] != 'target.cdl']
    write_json(root / 'query/header.json', header)
    rebind(root)
    alias_parse = read_inputs(root / 'site_config.yaml')
    assert alias_parse.status == 'success', alias_parse.issues
    repo = PublicationRepository()
    request = RunRequest(proposed_run_id='independent-w008-aliases', lineage_id='independent-w008',
                         idempotency_key='read-aliases', site_path=str(root / 'site_config.yaml'))
    ready = prepare_inputs(repo, request)
    assert isinstance(ready, InputsReady), ready
    checkpoint = repo.load_checkpoint(ready.run_id)
    parse_audit, tool = repo.read(ready.parse_ref), repo.read(ready.tool_ref)
    evidence = tuple(repo.read(ref) for ref in ready.evidence_refs)
    attempt_before = repo.load_attempt(ready.run_id)
    with no_io():
        direct = build_geometry(gi.geometry_from_parse_result(alias_parse))
        rb_input = gi.geometry_from_inputs_ready(ready, checkpoint, parse_audit, tool, evidence)
        readback = build_geometry(rb_input)
        semantic_before = normalize(rb_input.semantic_input)
        assert decode_record(encode_record(readback)) == readback
        assert normalize(rb_input.semantic_input) == semantic_before
    assert direct.layout == readback.layout
    assert direct.value == readback.value
    assert direct.layout.semantic_digest == original.layout.semantic_digest
    assert repo.load_attempt(ready.run_id) == attempt_before
    assert repo.read_terminal(ready.run_id) is None and attempt_before.phase == 'unsealed'
    checked('simultaneous owner/policy/GDS/source/header/body aliases + target source reuse preserve geometry')
    checked('real W006 readback with all aliases builds without IO/tools/readback and leaves attempt unsealed')

# Include ValueError and process interrupts through the nested result decoder;
# these may not be translated into a located expected-input failure.
wire = encode_record(original)
for decoder in ('load_document', 'validate_document', 'validate_tech', 'parse_gds'):
    for failure in (ValueError('independent injected bug'), KeyboardInterrupt('independent'), SystemExit(73)):
        def broken(*args, **kwargs):
            raise failure
        with patch.object(gi, decoder, broken):
            try:
                decode_record(wire)
            except BaseException as caught:
                assert caught is failure, (decoder, type(caught), type(failure))
            else:
                raise AssertionError('unexpected exception was swallowed')
        checked(decoder + ' nested decoder propagates identical ' + type(failure).__name__)

print(json.dumps({'result': 'pass', 'checks': len(checks), 'python': sys.version,
                  'module': gi.__file__, 'check_names': checks}, indent=2))
