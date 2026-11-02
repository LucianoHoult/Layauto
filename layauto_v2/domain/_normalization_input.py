"""Validation of already captured parser facts; never reacquires a source."""
from __future__ import annotations

import hashlib
import json
import re
from fractions import Fraction
from collections.abc import Mapping
from typing import cast

from .codec import FrozenMap, Value, canonical_bytes
from .evidence import EvidenceRecord, SourceFile, SourceRef
from .results import ParseResult

KINDS = ('config', 'tech', 'policies', 'header', 'gds', 'source_cdl', 'target_cdl', 'body', 'query')
CAPABILITIES = ('instance_xref', 'net_xref', 'device_regions', 'net_regions')


def mapping(value: object) -> FrozenMap:
    if not isinstance(value, FrozenMap):
        raise ValueError('expected immutable evidence map')
    return value


def sequence(value: object) -> tuple[Value, ...]:
    if not isinstance(value, tuple):
        raise ValueError('expected immutable evidence sequence')
    return cast('tuple[Value, ...]', value)


def string(value: object) -> str:
    if type(value) is not str or not value:
        raise ValueError('expected nonempty evidence string')
    value.encode('utf-8')
    return value


def ref_from_location(value: FrozenMap) -> SourceRef:
    uri = value.get('uri', value.get('path'))
    field = value.get('field', value.get('json_pointer'))
    return SourceRef(string(uri), string(value['sha256']),
                     cast('str | None', field), cast('int | None', value.get('line', value.get('line_1based'))),
                     cast('int | None', value.get('column')), cast('int | None', value.get('byte_offset')),
                     cast('int | None', value.get('record_index')))


def source_refs(value: Value) -> tuple[SourceRef, ...]:
    result: list[SourceRef] = []
    def walk(item: Value) -> None:
        if isinstance(item, FrozenMap):
            if 'sha256' in item and ('uri' in item or 'path' in item):
                ref = ref_from_location(item)
                if ref not in result:
                    result.append(ref)
            for child in item.values():
                walk(child)
        elif isinstance(item, tuple):
            for child in item:
                walk(child)
    walk(value)
    return tuple(result)


def validate_refs(value: Value, sources: Mapping[str, SourceFile]) -> None:
    for ref in source_refs(value):
        source = sources.get(ref.uri)
        if source is None or source.sha256 != ref.sha256:
            raise ValueError('nested evidence refers to uncaptured source bytes')
        if ref.byte_offset is not None and ref.byte_offset > len(source.data):
            raise ValueError('source location is outside captured bytes')
        if ref.line is not None:
            lines = source.data.splitlines()
            if ref.line > len(lines):
                raise ValueError('source line is outside captured bytes')
            if ref.column is not None:
                try:
                    line = lines[ref.line - 1].decode('utf-8')
                except UnicodeDecodeError as exc:
                    raise ValueError('text location points to non-text bytes') from exc
                if ref.column > len(line) + 1:
                    raise ValueError('source column is outside captured line')


def validate_locations(value: Value, sources: Mapping[str, SourceFile]) -> None:
    """Check preserved lexemes at their declared captured locations, without parsing."""
    if isinstance(value, FrozenMap):
        if 'sha256' in value and ('uri' in value or 'path' in value):
            ref = ref_from_location(value)
            source = sources[ref.uri]
            lexeme = value.get('lexeme')
            if isinstance(lexeme, str) and ref.line is not None:
                lines = source.data.decode('utf-8').splitlines(keepends=True)
                raw_line = lines[ref.line - 1].rstrip('\r\n')
                if 'token_0based' in value:
                    token = value['token_0based']
                    if token is None:
                        actual = raw_line
                    elif type(token) is int and 0 <= token < len(raw_line.split()):
                        actual = raw_line.split()[token]
                    else:
                        raise ValueError('query token location is outside captured line')
                    if lexeme != actual:
                        raise ValueError('query provenance lexeme differs from captured bytes')
                elif ref.column is not None:
                    if not raw_line[ref.column - 1:].startswith(lexeme):
                        raise ValueError('CDL field lexeme differs from captured bytes')
                    offset = len(''.join(lines[:ref.line - 1]).encode('utf-8')) + len(raw_line[:ref.column - 1].encode('utf-8'))
                    if ref.byte_offset != offset:
                        raise ValueError('CDL line/column/byte offset disagree')
        for child in value.values():
            validate_locations(child, sources)
    elif isinstance(value, tuple):
        for child in value:
            validate_locations(child, sources)


def _validate_cdl(doc: FrozenMap, tech: FrozenMap) -> None:
    if set(doc) != {'schema_version', 'dialect', 'tops', 'globals', 'raw_document', 'source', 'dependency_closure', 'preprocess', 'empty_closure_sha256', 'logical_record_count'}:
        raise ValueError('unknown or missing CDL evidence fields')
    if doc['empty_closure_sha256'] != hashlib.sha256(b'[]').hexdigest() or type(doc['logical_record_count']) is not int:
        raise ValueError('invalid CDL closure or logical record count')
    physical = mapping(tech['physical'])
    models = mapping(physical['models'])
    expected_axes = {'NFIN': 'fins_per_finger', 'NF': 'finger_count', 'M': 'multiplicity',
                     'L': 'channel_length', 'W': 'fin_width', 'VT': 'threshold_token'}
    for model_value in models.values():
        model = mapping(model_value)
        if (model['terminal_order'] != ('D', 'G', 'S', 'B') or model['parameter_axes'] != expected_axes
                or set(sequence(model['required_parameters'])) != set(expected_axes)
                or model['default_parameters'] != {} or model['sd_symmetry'] is not False):
            raise ValueError('unsupported or invalid captured model profile')
    tops = sequence(doc['tops'])
    if not tops:
        raise ValueError('CDL evidence has no cells')
    top_names: set[str] = set()
    for top_value in tops:
        top = mapping(top_value)
        if set(top) != {'name', 'pins', 'globals', 'devices', 'start_line', 'end_line', 'field_sources'}:
            raise ValueError('unknown or missing CDL top fields')
        name = string(top['name'])
        if name in top_names or top['globals'] != ():
            raise ValueError('duplicate top or unsupported globals')
        top_names.add(name)
        pins = sequence(top['pins'])
        if len(set(pins)) != len(pins):
            raise ValueError('duplicate ordered port')
        fields = mapping(top['field_sources'])
        if set(fields) != {'name', 'pins'} or mapping(fields['name'])['lexeme'] != name:
            raise ValueError('cell provenance differs from its identity')
        if tuple(mapping(item)['lexeme'] for item in sequence(fields['pins'])) != pins:
            raise ValueError('ordered port provenance differs')
        device_names: set[str] = set()
        for device_value in sequence(top['devices']):
            device = mapping(device_value)
            if set(device) != {'name', 'model', 'terminals', 'terminal_order', 'parameters', 'line', 'source', 'field_sources'}:
                raise ValueError('unknown or missing CDL device fields')
            device_name = string(device['name'])
            if device_name in device_names:
                raise ValueError('duplicate CDL device')
            device_names.add(device_name)
            model = mapping(models[string(device['model'])])
            if device['terminal_order'] != model['terminal_order'] or len(sequence(device['terminals'])) != 4:
                raise ValueError('device terminals differ from selected model')
            fields = mapping(device['field_sources'])
            if set(fields) != {'name', 'model', 'D', 'G', 'S', 'B'}:
                raise ValueError('device provenance fields differ')
            if (mapping(fields['name'])['lexeme'] != device_name or mapping(fields['model'])['lexeme'] != device['model']
                    or tuple(mapping(fields[role])['lexeme'] for role in ('D', 'G', 'S', 'B')) != device['terminals']):
                raise ValueError('device semantic fields differ from captured lexemes')
            parameters = mapping(device['parameters'])
            axes = mapping(model['parameter_axes'])
            if set(parameters) != set(axes):
                raise ValueError('device omits parameter axes')
            for token, parameter_value in parameters.items():
                parameter = mapping(parameter_value)
                if set(parameter) != {'lexeme', 'exact', 'unit', 'axis', 'source'} or parameter['axis'] != axes[token]:
                    raise ValueError('parameter interpretation differs from selected profile')
                lexeme = string(parameter['lexeme'])
                if mapping(parameter['source'])['lexeme'] != token + '=' + lexeme:
                    raise ValueError('parameter token and provenance disagree')
                axis = string(axes[token])
                if axis in ('fins_per_finger', 'finger_count', 'multiplicity'):
                    if re.fullmatch('[1-9][0-9]*', lexeme) is None or parameter['unit'] != 'count' or type(parameter['exact']) is not Fraction or parameter['exact'] != Fraction(int(lexeme)):
                        raise ValueError('count parameter exact value differs from literal')
                elif axis in ('channel_length', 'fin_width'):
                    if re.fullmatch('[1-9][0-9]*n', lexeme) is None or parameter['unit'] != 'metres' or type(parameter['exact']) is not Fraction or parameter['exact'] != Fraction(int(lexeme[:-1]), 1_000_000_000):
                        raise ValueError('length parameter exact value differs from literal')
                elif parameter['unit'] != 'token' or parameter['exact'] != 'toy' or lexeme != 'toy':
                    raise ValueError('token parameter differs from selected literal grammar')


def evidence_by_kind(result: ParseResult) -> dict[str, EvidenceRecord]:
    records = {record.kind: record for record in result.completed}
    if len(records) != len(result.completed) or set(records) != set(KINDS):
        raise ValueError('normalization requires one complete record for each parser role')
    return records


def _plain(value: Value) -> object:
    if isinstance(value, FrozenMap):
        return {key: _plain(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return [_plain(child) for child in value]
    if value is None or type(value) in (str, int, bool):
        return value
    raise ValueError('manifest contains a non-JSON value')


def manifest_digest(value: Value) -> str:
    return hashlib.sha256(json.dumps(_plain(value), sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()


def validate_parse(result: ParseResult) -> None:
    if type(result) is not ParseResult or result.status != 'success' or result.value is None:
        raise ValueError('normalization requires a successful ParseResult')
    value = result.value
    if set(value) != {'config', 'tech', 'tech_bundle', 'gds', 'source_cdl', 'target_cdl', 'query', 'body', 'header', 'policies'}:
        raise ValueError('unknown or missing successful parser fields')
    records = evidence_by_kind(result)
    sources = {source.uri: source for source in result.sources}
    for kind, record in records.items():
        expected = ({'bundle': value['tech_bundle'], 'owners': value['tech']}
                    if kind == 'tech' else value[kind])
        if canonical_bytes(record.payload) != canonical_bytes(expected):
            raise ValueError('parse value differs from completed evidence for ' + kind)
        for ref in record.sources:
            if ref.uri not in sources or sources[ref.uri].sha256 != ref.sha256:
                raise ValueError('completed evidence references uncaptured bytes')
    for kind in ('config', 'header', 'gds', 'source_cdl', 'target_cdl'):
        if len(records[kind].sources) != 1:
            raise ValueError('parser role must bind one captured source: ' + kind)
    for kind in ('source_cdl', 'target_cdl'):
        doc = mapping(value[kind])
        if doc.get('schema_version') != 'layauto-cdl-evidence/1' or doc.get('dialect') != 'toy_literal_cdl/1':
            raise ValueError('unsupported CDL evidence schema/dialect')
        ref = records[kind].sources[0]
        source = sources[ref.uri]
        if doc.get('raw_document') != source.data or mapping(doc['source']) != {'uri': ref.uri, 'sha256': ref.sha256}:
            raise ValueError('CDL preservation is not its captured role bytes')
        if doc.get('globals') != () or doc.get('dependency_closure') != () or doc.get('preprocess') != 'none':
            raise ValueError('unsupported CDL evidence dependency/global declaration')
        validate_refs(doc, sources)
        validate_locations(doc, sources)
        _validate_cdl(doc, mapping(value['tech']))
    header = mapping(value['header'])
    for header_role, kind in (('layout', 'gds'), ('source_netlist', 'source_cdl'), ('target', 'target_cdl')):
        declaration = mapping(header[header_role])
        # W005 already resolved aliases during acquisition. Role is NEVER chosen
        # by matching a hash or by resolving a pathname again here.
        if declaration['sha256'] != records[kind].sources[0].sha256:
            raise ValueError('header role hash differs from its completed evidence')
        string(declaration['uri'])
    closure = mapping(header['closure'])
    entries = sequence(closure['entries'])
    if closure['sha256'] != manifest_digest(entries):
        raise ValueError('header closure digest differs')
    declared_uris = [string(mapping(item)['uri']) for item in entries]
    if declared_uris != sorted(set(declared_uris)):
        raise ValueError('closure order/URI uniqueness differs')
    # Directly captured URIs must agree. An alias may be absent: its historic
    # resolution is a successful W005 fact, not reconstructable from bytes.
    for item in entries:
        declaration = mapping(item)
        captured = sources.get(string(declaration['uri']))
        if captured is not None and captured.sha256 != declaration['sha256']:
            raise ValueError('closure and captured source disagree')
        if declaration['sha256'] not in {source.sha256 for source in result.sources}:
            raise ValueError('closure declares bytes not present in this capture')
    query = mapping(value['query'])
    if set(query) != {*CAPABILITIES, '_format_metadata'}:
        raise ValueError('unknown/missing query evidence capability')
    raw = sequence(header['raw'])
    raw_pairs = {(string(mapping(item)['uri']), string(mapping(item)['sha256'])) for item in raw}
    if len(raw_pairs) != len(raw):
        raise ValueError('duplicate raw capture declaration')
    for uri, sha in raw_pairs:
        if uri not in sources or sources[uri].sha256 != sha:
            raise ValueError('query raw evidence was mixed with other captured sources')
    for cap in CAPABILITIES:
        document = mapping(query[cap])
        if (document.get('schema_version') != 'w004-query-normalized/2' or document.get('capability') != cap
                or document.get('dialect') != header['query_dialect_version'] or document.get('header_id') != header['header_id']):
            raise ValueError('query capability is from another capture/header')
        for item in sequence(document['raw_refs']):
            raw_ref = mapping(item)
            if (raw_ref['path'], raw_ref['sha256']) not in raw_pairs:
                raise ValueError('query capability raw reference is outside this bundle')
        sequence(document['records'])
    validate_refs(query, sources)
    validate_locations(query, sources)
    validate_refs(mapping(value['gds']), sources)
    # Require role captures to be present in the declared closure, including the
    # selected tech owners. This is membership, not alias→role reconstruction.
    closure_hashes = {mapping(item)['sha256'] for item in entries}
    for kind in ('config', 'tech', 'policies', 'gds', 'source_cdl', 'target_cdl', 'body'):
        if any(ref.sha256 not in closure_hashes for ref in records[kind].sources):
            raise ValueError('captured parser role absent from header dependency closure')
