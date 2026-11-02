"""Validation of already captured parser facts; never reacquires a source."""
from __future__ import annotations

import hashlib
import json
import re
from fractions import Fraction
from collections.abc import Mapping
from typing import TYPE_CHECKING, Literal, cast

if TYPE_CHECKING:
    from .circuit import SemanticCircuitDraft

from .codec import FrozenMap, Value, canonical_bytes, rational
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
    raw_document = doc['raw_document']
    if type(raw_document) is not bytes:
        raise ValueError('CDL preservation requires captured bytes')
    raw_lines = raw_document.decode('utf-8').splitlines()
    expected_lines = {index for index, line in enumerate(raw_lines, 1) if line.strip() and not line.strip().startswith('*')}
    covered_lines: list[int] = []
    for top_value in tops:
        top = mapping(top_value)
        if set(top) != {'name', 'pins', 'globals', 'devices', 'start_line', 'end_line', 'field_sources'}:
            raise ValueError('unknown or missing CDL top fields')
        name = string(top['name'])
        if name in top_names or top['globals'] != ():
            raise ValueError('duplicate top or unsupported globals')
        top_names.add(name)
        start, end = top['start_line'], top['end_line']
        if type(start) is not int or type(end) is not int or not 1 <= start < end <= len(raw_lines):
            raise ValueError('invalid captured CDL top record span')
        covered_lines.extend((start, end))
        pins = sequence(top['pins'])
        if raw_lines[start - 1].split() != ['.SUBCKT', name, *pins] or raw_lines[end - 1].split() != ['.ENDS', name]:
            raise ValueError('CDL top declaration differs from captured record span')
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
            line = device['line']
            if (type(line) is not int or type(top['start_line']) is not int or type(top['end_line']) is not int
                    or not top['start_line'] < line < top['end_line']
                    or mapping(device['source']).get('line') != line
                    or any(mapping(location).get('line') != line for location in fields.values())):
                raise ValueError('CDL fields do not belong to their declared device record')
            covered_lines.append(line)
            parameters = mapping(device['parameters'])
            axes = mapping(model['parameter_axes'])
            if set(parameters) != set(axes):
                raise ValueError('device omits parameter axes')
            raw_tokens = raw_lines[line - 1].split()
            if (raw_tokens[:6] != [device_name, *sequence(device['terminals']), device['model']]
                    or sorted(raw_tokens[6:]) != sorted(string(mapping(mapping(parameter)['source'])['lexeme']) for parameter in parameters.values())):
                raise ValueError('CDL device fields do not completely cover their captured record')
            for token, parameter_value in parameters.items():
                parameter = mapping(parameter_value)
                if set(parameter) != {'lexeme', 'exact', 'unit', 'axis', 'source'} or parameter['axis'] != axes[token]:
                    raise ValueError('parameter interpretation differs from selected profile')
                lexeme = string(parameter['lexeme'])
                if mapping(parameter['source']).get('line') != line:
                    raise ValueError('parameter provenance belongs to another device record')
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

    if len(covered_lines) != len(set(covered_lines)) or set(covered_lines) != expected_lines or doc['logical_record_count'] != len(expected_lines):
        raise ValueError('CDL evidence omits or duplicates captured logical records')


def _field_sources(record: FrozenMap, field: str) -> tuple[FrozenMap, ...]:
    definition = mapping(mapping(record['field_sources'])[field])
    if set(definition) != {'derivation', 'sources'}:
        raise ValueError('invalid derived field provenance')
    string(definition['derivation'])
    refs = tuple(mapping(value) for value in sequence(definition['sources']))
    if not refs:
        raise ValueError('derived field must preserve its source operands')
    return refs


def _same_row(left: FrozenMap, right: FrozenMap) -> bool:
    return tuple(left.get(key) for key in ('path', 'sha256', 'line_1based')) == tuple(right.get(key) for key in ('path', 'sha256', 'line_1based'))


def _validate_query(query: FrozenMap, tech: FrozenMap, sources: Mapping[str, SourceFile], header: FrozenMap, query_sources: tuple[SourceRef, ...]) -> None:
    instance_rows = tuple(mapping(value) for value in sequence(mapping(query['instance_xref'])['records']))
    net_rows = tuple(mapping(value) for value in sequence(mapping(query['net_xref'])['records']))
    for row in instance_rows:
        if set(row) != {'layout_instance', 'schematic_instance', 'sd_swap', 'field_sources'} or set(mapping(row['field_sources'])) != {'layout_instance', 'schematic_instance', 'sd_swap'}:
            raise ValueError('invalid instance xref evidence fields')
        layout, schematic, swap = (_field_sources(row, field) for field in ('layout_instance', 'schematic_instance', 'sd_swap'))
        if (len(layout) != 1 or len(schematic) != 1 or len(swap) != 1
                or layout[0]['lexeme'] != row['layout_instance'] or schematic[0]['lexeme'] != row['schematic_instance']
                or layout[0].get('token_0based') != 1 or schematic[0].get('token_0based') != 3
                or not _same_row(layout[0], schematic[0]) or not _same_row(layout[0], swap[0])
                or type(row['sd_swap']) is not bool or row['sd_swap'] != (len(string(swap[0]['lexeme']).split()) == 5 and string(swap[0]['lexeme']).split()[-1] == 'X')):
            raise ValueError('instance identity fields disagree with their captured xref row')
    for row in net_rows:
        if set(row) != {'lvs_name', 'schematic_name', 'lvs_index', 'field_sources'} or set(mapping(row['field_sources'])) != {'lvs_name', 'schematic_name', 'lvs_index'}:
            raise ValueError('invalid net xref evidence fields')
        layout, schematic, index = (_field_sources(row, field) for field in ('lvs_name', 'schematic_name', 'lvs_index'))
        if (len(layout) != 2 or len(schematic) != 1 or len(index) != 1
                or layout[0]['lexeme'] != row['lvs_name'] or layout[1]['lexeme'] != row['lvs_name']
                or schematic[0]['lexeme'] != row['schematic_name']
                or layout[0].get('token_0based') != 1 or schematic[0].get('token_0based') != 3
                or not _same_row(layout[0], schematic[0]) or index[0] != layout[1]):
            raise ValueError('net identity fields disagree with xref and NET NAMES operands')
        ordinal_line = index[0].get('line_1based')
        if type(ordinal_line) is not int or ordinal_line < 4 or row['lvs_index'] != str(ordinal_line - 3):
            raise ValueError('LVS index is not its captured NET NAMES ordinal')
    metadata = mapping(query['_format_metadata'])
    for capability, rows, field in (('instance_xref', instance_rows, 'layout_instance'), ('net_xref', net_rows, 'lvs_name')):
        reference = mapping(mapping(metadata[capability])['source'])
        source = sources[string(reference['path'])]
        positions = [(_field_sources(row, field)[0]['path'], _field_sources(row, field)[0]['line_1based']) for row in rows]
        expected_positions = [(source.uri, line) for line in range(9, len(source.data.splitlines()) + 1)]
        if sorted(positions) != sorted(expected_positions):
            raise ValueError('xref evidence omits or duplicates captured rows')
    names_reference = mapping(mapping(metadata['net_names'])['count_header'])
    names_source = sources[string(names_reference['path'])]
    names_positions = [(_field_sources(row, 'lvs_index')[0]['path'], _field_sources(row, 'lvs_index')[0]['line_1based']) for row in net_rows]
    if sorted(names_positions) != [(names_source.uri, line) for line in range(4, len(names_source.data.splitlines()))]:
        raise ValueError('net identity evidence omits or duplicates NET NAMES records')
    response_metadata = tuple(mapping(entry) for entry in sequence(metadata['responses']))
    response_sources: list[tuple[str, str]] = []
    for response in response_metadata:
        reference = mapping(response['source'])
        count_header = mapping(response['count_header'])
        pair = (string(reference['path']), string(reference['sha256']))
        if (pair != (count_header['path'], count_header['sha256']) or count_header.get('line_1based') != 3
                or string(count_header['lexeme']).split(maxsplit=3)[-1] != response['timestamp']):
            raise ValueError('response metadata differs from its captured response')
        response_sources.append(pair)
    expected_response_sources = [(string(mapping(item)['uri']), string(mapping(item)['sha256'])) for item in sequence(header['raw'])
                                 if mapping(item)['capability'] in ('device_regions', 'net_regions')]
    if sorted(response_sources) != sorted(expected_response_sources):
        raise ValueError('request-ordered response metadata does not cover declared captures')
    response_capabilities = {string(mapping(item)['uri']): string(mapping(item)['capability']) for item in sequence(header['raw'])}
    request_source = query_sources[1]
    observed_requests: set[int] = set()
    registry = {string(mapping(entry)['id']): mapping(entry) for entry in sequence(mapping(tech['derived'])['derived_registry'])}
    for capability, associations in (('device_regions', instance_rows), ('net_regions', net_rows)):
        key = 'layout_instance' if capability == 'device_regions' else 'lvs_name'
        identity_fields = ('layout_instance', 'schematic_instance') if capability == 'device_regions' else ('lvs_name', 'schematic_name', 'lvs_index')
        actual_positions: list[tuple[str, int]] = []
        for row_value in sequence(mapping(query[capability])['records']):
            row = mapping(row_value)
            matches = [candidate for candidate in associations if candidate[key] == row[key]]
            # Duplicate association/cardinality remains the normalizer's typed
            # admission error; never repair it by silently picking another row.
            if len(matches) == 1:
                association = matches[0]
                for field in identity_fields:
                    refs = _field_sources(row, field)
                    if (row[field] != association[field] or refs[0]['lexeme'] != row[key]
                            or refs[1:] != _field_sources(association, field)):
                        raise ValueError('region identity differs from its declared association sources')
            vertices_sources = _field_sources(row, 'vertices_nm')
            if len(vertices_sources) != 10:
                raise ValueError('region vertices require precision, eight coordinates and dialect')
            precision_source, geometry_source = vertices_sources[0], vertices_sources[-1]
            coordinate_sources = vertices_sources[1:-1]
            precision = row['precision']
            if type(precision) is not int or precision <= 0 or precision_source['lexeme'] != str(precision):
                raise ValueError('region precision differs from captured precision token')
            geometry = mapping(geometry_source['lexeme'])
            if (geometry['raw_axis_order'] != ('y', 'x') or geometry['raw_unit'] != 'micrometres / precision'
                    or geometry['precision'] != precision or rational(geometry['raw_tick_nm']) != Fraction(1000, precision)):
                raise ValueError('region geometry dialect operands disagree')
            layer_sources = _field_sources(row, 'derived_layer')
            if len(layer_sources) != 2 or layer_sources[0]['lexeme'] != row['derived_layer']:
                raise ValueError('derived layer differs from captured raw layer')
            actual_positions.append((string(layer_sources[0]['path']), cast(int, layer_sources[0]['line_1based'])))
            object_source = _field_sources(row, key)[0]
            record_source = _field_sources(row, 'record_id')[0]
            object_pointer = string(object_source['json_pointer'])
            record_pointer = string(record_source['json_pointer'])
            object_match = re.fullmatch(r'/requests/(0|[1-9][0-9]*)/object', object_pointer)
            record_match = re.fullmatch(r'/requests/(0|[1-9][0-9]*)/record_ids/(0|[1-9][0-9]*)', record_pointer)
            if object_match is None or record_match is None or object_match.group(1) != record_match.group(1):
                raise ValueError('seed object and record ID belong to different query requests')
            request_index, polygon_index = int(object_match.group(1)), int(record_match.group(2))
            if request_index >= len(response_metadata):
                raise ValueError('seed references an absent captured query request')
            observed_requests.add(request_index)
            expected_path, expected_sha = response_sources[request_index]
            first_layer_line = 5 if capability == 'device_regions' else 4
            if (response_capabilities[expected_path] != capability
                    or layer_sources[0]['path'] != expected_path or layer_sources[0]['sha256'] != expected_sha
                    or layer_sources[0]['line_1based'] != first_layer_line + polygon_index * 7):
                raise ValueError('seed geometry belongs to another request capture or polygon ordinal')
            for field in identity_fields:
                if _field_sources(row, field)[0] != object_source:
                    raise ValueError('seed identity fields refer to different requests')
            if any(ref.get('path') != request_source.uri or ref.get('sha256') != request_source.sha256 for ref in (object_source, record_source)):
                raise ValueError('seed request provenance is outside the captured requests role')
            registry_entry = mapping(layer_sources[1]['lexeme'])
            if registry.get(string(row['derived_layer'])) != registry_entry or row['quality'] != registry_entry['quality']:
                raise ValueError('seed quality/derived layer differs from selected registry')
            coords: list[tuple[Fraction, Fraction]] = []
            for vertex_index in range(4):
                y, x = coordinate_sources[vertex_index * 2:vertex_index * 2 + 2]
                if (not _same_row(x, y) or y.get('token_0based') != 0 or x.get('token_0based') != 1
                        or x.get('path') != layer_sources[0].get('path') or x.get('sha256') != layer_sources[0].get('sha256')
                        or x.get('line_1based') != cast(int, layer_sources[0]['line_1based']) + 3 + vertex_index):
                    raise ValueError('vertex provenance belongs to another region record')
                coords.append((Fraction(string(x['lexeme'])) * 1000 / precision,
                               Fraction(string(y['lexeme'])) * 1000 / precision))
            actual = tuple((rational(mapping(point)['x']), rational(mapping(point)['y'])) for point in sequence(row['vertices_nm']))
            if actual != tuple(coords):
                raise ValueError('seed exact vertices disagree with captured coordinate operands')
            bbox = mapping(row['bbox_nm'])
            expected_box = (min(x for x, y in coords), min(y for x, y in coords), max(x for x, y in coords), max(y for x, y in coords))
            if tuple(rational(bbox[field]) for field in ('x_min', 'y_min', 'x_max', 'y_max')) != expected_box:
                raise ValueError('seed bbox differs from exact coordinate extrema')
            if _field_sources(row, 'bbox_nm') != vertices_sources or row['geometry_kind'] != 'rectangle' or row['unit'] != 'nm':
                raise ValueError('seed geometry/provenance differs from declared exact conversion')
            if (_field_sources(row, 'precision') != (precision_source, geometry_source)
                    or _field_sources(row, 'unit') != (precision_source, geometry_source)
                    or _field_sources(row, 'geometry_kind') != (*coordinate_sources, layer_sources[1])
                    or _field_sources(row, 'quality') != (*coordinate_sources, layer_sources[1])):
                raise ValueError('seed derived fields do not retain their declared operands')
            if (tuple(ref['lexeme'] for ref in _field_sources(row, 'metadata_opaque')) != row['metadata_opaque']
                    or _field_sources(row, 'section_header_opaque')[0]['lexeme'] != row['section_header_opaque']
                    or _field_sources(row, 'record_id')[0]['lexeme'] != row['record_id']):
                raise ValueError('seed opaque/author fields differ from their captured operands')

        expected_regions: list[tuple[str, int]] = []
        for declaration_value in sequence(header['raw']):
            declaration = mapping(declaration_value)
            if declaration['capability'] != capability:
                continue
            source = sources[string(declaration['uri'])]
            # This selected captured dialect has seven lines per rectangle,
            # after its declared device/net metadata, then one final terminator.
            first_layer_line = 5 if capability == 'device_regions' else 4
            expected_regions.extend((source.uri, line) for line in range(first_layer_line, len(source.data.splitlines()), 7))
        if sorted(actual_positions) != sorted(expected_regions):
            raise ValueError('region evidence omits or duplicates captured polygon records')
    if observed_requests != set(range(len(response_metadata))):
        raise ValueError('seed evidence omits captured query requests')


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
    if len(records['tech'].sources) != 7:
        raise ValueError('tech evidence requires bundle plus six declared owner captures')
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
    if len(records['query'].sources) != 3 + len(raw):
        raise ValueError('query evidence requires header, requests, dialect and all raw captures')
    _validate_query(query, mapping(value['tech']), sources, header, records['query'].sources)
    validate_refs(mapping(value['gds']), sources)
    # Require role captures to be present in the declared closure, including the
    # selected tech owners. This is membership, not alias→role reconstruction.
    closure_hashes = {mapping(item)['sha256'] for item in entries}
    for kind in ('config', 'tech', 'policies', 'gds', 'source_cdl', 'target_cdl', 'body'):
        if any(ref.sha256 not in closure_hashes for ref in records[kind].sources):
            raise ValueError('captured parser role absent from header dependency closure')


SEMANTIC_COMPARATOR = ('cell, ordered pins, globals, device identities, models, ordered terminals and every '
                       'parameter axis equal; line/parameter order, full-line comments and whitespace irrelevant')
AdmissionProblem = tuple[Literal['unsupported', 'identity'], str, str, SourceRef]


def source_admission_problem(value: FrozenMap, source: SemanticCircuitDraft,
                             tech_sources: tuple[SourceRef, ...], header_ref: SourceRef) -> AdmissionProblem | None:
    """The same source-only admission guard serves the component and success DTO."""
    tech = mapping(value['tech'])
    physical = mapping(tech['physical'])
    dialect = mapping(mapping(tech['formats'])['cdl_dialect'])
    owner_order = ('drawn', 'derived', 'physical', 'formats', 'coordinate', 'rules')
    formats_ref = tech_sources[1 + owner_order.index('formats')]
    physical_ref = tech_sources[1 + owner_order.index('physical')]
    if dialect['semantic_comparator'] != SEMANTIC_COMPARATOR or dialect['id'] != 'toy_literal_cdl/1':
        return ('unsupported', 'UnsupportedSemanticComparator', 'selected comparator is not implemented',
                SourceRef(formats_ref.uri, formats_ref.sha256, field='/cdl_dialect/semantic_comparator'))
    contract = mapping(physical['device_extraction_contract'])
    if contract['cardinality'] != 'one_to_one' or contract['device_reduction'] != 'forbidden' or contract['mapping_missing_or_ambiguous'] != 'typed_fail':
        return ('unsupported', 'UnsupportedIdentityProfile', 'unsupported identity admission policy',
                SourceRef(physical_ref.uri, physical_ref.sha256, field='/device_extraction_contract'))
    fin = mapping(physical['fin_count_profile'])
    for cell in source.cells:
        for device in cell.devices:
            by_axis = {parameter.axis: parameter for parameter in device.parameters}
            for axis, required_key, code in (('finger_count', 'finger_count_required', 'UnsupportedFingerCount'),
                                            ('multiplicity', 'multiplicity_required', 'UnsupportedMultiplicity')):
                parameter = by_axis[axis]
                if parameter.exact != Fraction(cast(int, fin[required_key])):
                    return ('unsupported', code, axis + ' is outside the selected source subset', parameter.source)
    query = mapping(value['query'])
    selected = next(cell for cell in source.cells if cell.id == source.selected_cell)
    metadata = mapping(query['_format_metadata'])
    for capability in ('instance_xref', 'net_xref'):
        summary = mapping(metadata[capability])
        if summary['source_top'] != selected.id.name or summary['source_pin_count'] != len(selected.ports):
            locations = source_refs(mapping(summary['summary']))
            return ('identity', 'SourceTopIdentityMismatch', 'query summary differs from source cell/ordered port count',
                    locations[0] if locations else header_ref)
    return None
