"""Reviewer-authored normal composition, malformed wire and history controls."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import subprocess
from unittest.mock import patch

from layauto_v2.domain.codec import FrozenMap, canonical_bytes, decode
from layauto_v2.domain import publication_codec
from layauto_v2.domain.publication import InputsReady, RunRequest
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import build_effective_geometry, build_geometry
from layauto_v2.normalization.geometry_input import geometry_from_inputs_ready, geometry_from_parse_result
from layauto_v2.normalization import effective_codec, geometry_codec
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository

def mutable(value):
    if type(value) is FrozenMap:
        return {key: mutable(child) for key, child in value.items()}
    if type(value) is tuple:
        return [mutable(child) for child in value]
    return value

root = Path.cwd()
parsed = read_inputs(root / 'tests/fixtures/w003_m1/site_config.yaml')
assert parsed.status == 'success'
direct_input = geometry_from_parse_result(parsed)
repository = PublicationRepository()
ready = prepare_inputs(repository, RunRequest(proposed_run_id='independent-ipmr01', lineage_id='independent-ipmr01-lineage', idempotency_key='independent-create', site_path=str(root / 'tests/fixtures/w003_m1/site_config.yaml')))
assert type(ready) is InputsReady
before = ready.attempt
readback_input = geometry_from_inputs_ready(ready, repository.load_checkpoint(ready.run_id), repository.read(ready.parse_ref), repository.read(ready.tool_ref), tuple(repository.read(ref) for ref in ready.evidence_refs))

def noio(*args, **kwargs):
    raise AssertionError('unexpected IO during pure W008/W009 composition')

with patch('builtins.open', noio), patch.object(Path, 'read_bytes', noio), patch.object(Path, 'read_text', noio), patch.object(PublicationRepository, 'read', noio):
    direct = build_effective_geometry(build_geometry(direct_input))
    readback = build_effective_geometry(build_geometry(readback_input))
assert direct.status == readback.status == 'success'
assert direct.value == readback.value and ready.attempt == before
base = direct.value.base
layout = base.layout
fragment = base.fragments[0]
records = [layout.units.ref, layout.records[0].id, fragment.id, layout.records[0].rect, layout.records[0].stream_key, layout.units, layout.policies[0], layout.records[0], layout, base.partition.layers[0], base.partition, fragment.cell, fragment, base, direct.input.input, direct.input]
observations = []
for record in records:
    wire = geometry_codec.encode_record(record)
    assert geometry_codec.encode_record(geometry_codec.decode_record(wire)) == wire
    tree = mutable(decode(wire))
    for field in tree['record']['fields']:
        for tag in ('missing', 'scalar', 'tuple', 'map'):
            changed = mutable(decode(wire))
            if tag == 'missing':
                del changed['record']['fields'][field]
            else:
                changed['record']['fields'][field] = {'scalar': None} if tag == 'scalar' else {'tuple': []} if tag == 'tuple' else {'map': {'unexpected': 1}}
                if changed['record']['fields'][field] == tree['record']['fields'][field]:
                    continue
            try:
                geometry_codec.decode_record(canonical_bytes(changed))
            except ValueError as exc:
                observations.append({'record':type(record).__name__, 'field':field, 'change':tag, 'observed':type(exc).__name__})
            else:
                raise AssertionError((type(record).__name__, field, tag, 'unexpected accepted malformed field'))
    for changed in (wire + b'\n', wire.replace(b'layauto-geometry-wire/1', b'layauto-geometry-wire/2')):
        try:
            geometry_codec.decode_record(changed)
        except ValueError:
            pass
        else:
            raise AssertionError('accepted noncanonical or unsupported schema')

for record in (direct.value, direct, readback):
    wire = effective_codec.encode_record(record)
    assert effective_codec.encode_record(effective_codec.decode_record(wire)) == wire

history_rows = []
targets = ('layauto_v2.normalization.contracts.request_decoder_input', 'layauto_v2.normalization._validation._validate_cdl', 'layauto_v2.normalization._validation._validate_query', 'layauto_v2.normalization.contracts.content_ref')
wire = effective_codec.encode_record(readback)
for target in targets:
    for cls in (RuntimeError, ValueError, TypeError, KeyError, AttributeError, IndexError, UnicodeError, KeyboardInterrupt, SystemExit):
        failure, cause, context = cls('independent complete receipt reconstruction fault'), OSError('prior cause'), LookupError('prior context')
        failure.__cause__, failure.__context__, failure.__suppress_context__ = cause, context, False
        def broken(*args, **kwargs):
            raise failure
        with patch(target, broken):
            try:
                effective_codec.decode_record(wire)
            except BaseException as observed:
                assert observed is failure and observed.__cause__ is cause and observed.__context__ is context and observed.__suppress_context__ is False
                history_rows.append({'target':target,'failure':cls.__name__,'same_object_and_history':True})
            else:
                raise AssertionError('injected fault unexpectedly succeeded')

print(json.dumps({'head':subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip(), 'normal':{'direct_and_readback_equal':True,'no_builder_io':True,'attempt_unchanged':True,'roundtrip_entries':3,'base_records':len(layout.records),'fragments':len(base.fragments)}, 'malformed_count':len(observations),'malformed':observations,'history_count':len(history_rows),'history':history_rows, 'wire_sha256':{'direct':hashlib.sha256(effective_codec.encode_record(direct)).hexdigest(),'readback':hashlib.sha256(wire).hexdigest()}},indent=2,sort_keys=True))
