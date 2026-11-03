"""Validation of already captured parser facts; never reacquires a source."""
from __future__ import annotations

import hashlib
import json
import re
from fractions import Fraction
from collections.abc import Mapping
from typing import TYPE_CHECKING, Literal, TypeVar, cast

if TYPE_CHECKING:
    from layauto_v2.domain.circuit import SemanticCircuitDraft

from layauto_v2.domain.codec import FrozenMap, Value, canonical_bytes, rational
from layauto_v2.domain.evidence import EvidenceRecord, SourceFile, SourceRef
from layauto_v2.domain.source_location import ref_from_location
from layauto_v2.domain.results import InputError, ParseResult
from layauto_v2.importers.config import load_document, validate_document

KINDS = ('config', 'tech', 'policies', 'header', 'gds', 'source_cdl', 'target_cdl', 'body', 'query')
CAPABILITIES = ('instance_xref', 'net_xref', 'device_regions', 'net_regions')

_Item = TypeVar('_Item')


def _required(values: Mapping[str, _Item], key: str) -> _Item:
    """Reject a missing input field before lookup, without catching code faults."""
    if key not in values:
        raise ValueError('missing captured evidence field/reference: ' + key)
    return values[key]


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
    try:
        value.encode('utf-8')
    except UnicodeEncodeError as exc:
        raise ValueError('evidence string must encode as UTF-8') from exc
    return value


def _text_bytes(value: bytes) -> str:
    try:
        return value.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise ValueError('text evidence must retain UTF-8 bytes') from exc


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
            source = _required(sources, ref.uri)
            lexeme = value.get('lexeme')
            if isinstance(lexeme, str) and ref.line is not None:
                lines = _text_bytes(source.data).splitlines(keepends=True)
                if ref.line > len(lines):
                    raise ValueError('source line is outside captured bytes')
                raw_line = lines[ref.line - 1].rstrip('\r\n')
                if 'token_0based' in value:
                    token = _required(value, 'token_0based')
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
    if _required(doc, 'empty_closure_sha256') != hashlib.sha256(b'[]').hexdigest() or type(_required(doc, 'logical_record_count')) is not int:
        raise ValueError('invalid CDL closure or logical record count')
    physical = mapping(_required(tech, 'physical'))
    models = mapping(_required(physical, 'models'))
    expected_axes = {'NFIN': 'fins_per_finger', 'NF': 'finger_count', 'M': 'multiplicity',
                     'L': 'channel_length', 'W': 'fin_width', 'VT': 'threshold_token'}
    for model_value in models.values():
        model = mapping(model_value)
        if (_required(model, 'terminal_order') != ('D', 'G', 'S', 'B') or _required(model, 'parameter_axes') != expected_axes
                or set(string(item) for item in sequence(_required(model, 'required_parameters'))) != set(expected_axes)
                or _required(model, 'default_parameters') != {} or _required(model, 'sd_symmetry') is not False):
            raise ValueError('unsupported or invalid captured model profile')
    tops = sequence(_required(doc, 'tops'))
    if not tops:
        raise ValueError('CDL evidence has no cells')
    top_names: set[str] = set()
    raw_document = _required(doc, 'raw_document')
    if type(raw_document) is not bytes:
        raise ValueError('CDL preservation requires captured bytes')
    raw_lines = _text_bytes(raw_document).splitlines()
    expected_lines = {index for index, line in enumerate(raw_lines, 1) if line.strip() and not line.strip().startswith('*')}
    covered_lines: list[int] = []
    for top_value in tops:
        top = mapping(top_value)
        if set(top) != {'name', 'pins', 'globals', 'devices', 'start_line', 'end_line', 'field_sources'}:
            raise ValueError('unknown or missing CDL top fields')
        name = string(_required(top, 'name'))
        if name in top_names or _required(top, 'globals') != ():
            raise ValueError('duplicate top or unsupported globals')
        top_names.add(name)
        start, end = _required(top, 'start_line'), _required(top, 'end_line')
        if type(start) is not int or type(end) is not int or not 1 <= start < end <= len(raw_lines):
            raise ValueError('invalid captured CDL top record span')
        covered_lines.extend((start, end))
        pins = tuple(string(item) for item in sequence(_required(top, 'pins')))
        if raw_lines[start - 1].split() != ['.SUBCKT', name, *pins] or raw_lines[end - 1].split() != ['.ENDS', name]:
            raise ValueError('CDL top declaration differs from captured record span')
        if len(set(pins)) != len(pins):
            raise ValueError('duplicate ordered port')
        fields = mapping(_required(top, 'field_sources'))
        if set(fields) != {'name', 'pins'} or _required(mapping(_required(fields, 'name')), 'lexeme') != name:
            raise ValueError('cell provenance differs from its identity')
        if tuple(_required(mapping(item), 'lexeme') for item in sequence(_required(fields, 'pins'))) != pins:
            raise ValueError('ordered port provenance differs')
        device_names: set[str] = set()
        for device_value in sequence(_required(top, 'devices')):
            device = mapping(device_value)
            if set(device) != {'name', 'model', 'terminals', 'terminal_order', 'parameters', 'line', 'source', 'field_sources'}:
                raise ValueError('unknown or missing CDL device fields')
            device_name = string(_required(device, 'name'))
            if device_name in device_names:
                raise ValueError('duplicate CDL device')
            device_names.add(device_name)
            model = mapping(_required(models, string(_required(device, 'model'))))
            if _required(device, 'terminal_order') != _required(model, 'terminal_order') or len(sequence(_required(device, 'terminals'))) != 4:
                raise ValueError('device terminals differ from selected model')
            fields = mapping(_required(device, 'field_sources'))
            if set(fields) != {'name', 'model', 'D', 'G', 'S', 'B'}:
                raise ValueError('device provenance fields differ')
            if (_required(mapping(_required(fields, 'name')), 'lexeme') != device_name or _required(mapping(_required(fields, 'model')), 'lexeme') != _required(device, 'model')
                    or tuple(_required(mapping(fields[role]), 'lexeme') for role in ('D', 'G', 'S', 'B')) != _required(device, 'terminals')):
                raise ValueError('device semantic fields differ from captured lexemes')
            line = _required(device, 'line')
            if (type(line) is not int or not start < line < end
                    or mapping(_required(device, 'source')).get('line') != line
                    or any(mapping(location).get('line') != line for location in fields.values())):
                raise ValueError('CDL fields do not belong to their declared device record')
            covered_lines.append(line)
            parameters = mapping(_required(device, 'parameters'))
            axes = mapping(_required(model, 'parameter_axes'))
            if set(parameters) != set(axes):
                raise ValueError('device omits parameter axes')
            raw_tokens = raw_lines[line - 1].split()
            if (raw_tokens[:6] != [device_name, *sequence(_required(device, 'terminals')), _required(device, 'model')]
                    or sorted(raw_tokens[6:]) != sorted(string(_required(mapping(_required(mapping(parameter), 'source')), 'lexeme')) for parameter in parameters.values())):
                raise ValueError('CDL device fields do not completely cover their captured record')
            for token, parameter_value in parameters.items():
                parameter = mapping(parameter_value)
                if set(parameter) != {'lexeme', 'exact', 'unit', 'axis', 'source'} or _required(parameter, 'axis') != _required(axes, token):
                    raise ValueError('parameter interpretation differs from selected profile')
                lexeme = string(_required(parameter, 'lexeme'))
                if mapping(_required(parameter, 'source')).get('line') != line:
                    raise ValueError('parameter provenance belongs to another device record')
                if _required(mapping(_required(parameter, 'source')), 'lexeme') != token + '=' + lexeme:
                    raise ValueError('parameter token and provenance disagree')
                axis = string(_required(axes, token))
                if axis in ('fins_per_finger', 'finger_count', 'multiplicity'):
                    if re.fullmatch('[1-9][0-9]*', lexeme) is None or _required(parameter, 'unit') != 'count' or type(_required(parameter, 'exact')) is not Fraction or _required(parameter, 'exact') != Fraction(int(lexeme)):
                        raise ValueError('count parameter exact value differs from literal')
                elif axis in ('channel_length', 'fin_width'):
                    if re.fullmatch('[1-9][0-9]*n', lexeme) is None or _required(parameter, 'unit') != 'metres' or type(_required(parameter, 'exact')) is not Fraction or _required(parameter, 'exact') != Fraction(int(lexeme[:-1]), 1_000_000_000):
                        raise ValueError('length parameter exact value differs from literal')
                elif _required(parameter, 'unit') != 'token' or _required(parameter, 'exact') != 'toy' or lexeme != 'toy':
                    raise ValueError('token parameter differs from selected literal grammar')

    if len(covered_lines) != len(set(covered_lines)) or set(covered_lines) != expected_lines or _required(doc, 'logical_record_count') != len(expected_lines):
        raise ValueError('CDL evidence omits or duplicates captured logical records')


def _field_sources(record: FrozenMap, field: str) -> tuple[FrozenMap, ...]:
    definition = mapping(_required(mapping(_required(record, 'field_sources')), field))
    if set(definition) != {'derivation', 'sources'}:
        raise ValueError('invalid derived field provenance')
    string(_required(definition, 'derivation'))
    refs = tuple(mapping(value) for value in sequence(_required(definition, 'sources')))
    if not refs:
        raise ValueError('derived field must preserve its source operands')
    for ref in refs:
        string(_required(ref, 'sha256'))
        if 'uri' not in ref and 'path' not in ref:
            raise ValueError('derived field requires a captured source location')
        ref_from_location(ref)
    return refs


def _same_row(left: FrozenMap, right: FrozenMap) -> bool:
    return tuple(left.get(key) for key in ('path', 'sha256', 'line_1based')) == tuple(right.get(key) for key in ('path', 'sha256', 'line_1based'))


def _validate_query(query: FrozenMap, tech: FrozenMap, sources: Mapping[str, SourceFile], header: FrozenMap, query_sources: tuple[SourceRef, ...], request_document: FrozenMap) -> None:
    request_source = query_sources[1]
    requests = tuple(mapping(request) for request in sequence(_required(request_document, 'requests')))
    instance_rows = tuple(mapping(value) for value in sequence(_required(mapping(_required(query, 'instance_xref')), 'records')))
    net_rows = tuple(mapping(value) for value in sequence(_required(mapping(_required(query, 'net_xref')), 'records')))
    for row in instance_rows:
        if set(row) != {'layout_instance', 'schematic_instance', 'sd_swap', 'field_sources'} or set(mapping(_required(row, 'field_sources'))) != {'layout_instance', 'schematic_instance', 'sd_swap'}:
            raise ValueError('invalid instance xref evidence fields')
        layout, schematic, swap = (_field_sources(row, field) for field in ('layout_instance', 'schematic_instance', 'sd_swap'))
        if (len(layout) != 1 or len(schematic) != 1 or len(swap) != 1
                or _required(layout[0], 'lexeme') != _required(row, 'layout_instance') or _required(schematic[0], 'lexeme') != _required(row, 'schematic_instance')
                or layout[0].get('token_0based') != 1 or schematic[0].get('token_0based') != 3
                or not _same_row(layout[0], schematic[0]) or not _same_row(layout[0], swap[0])
                or type(_required(row, 'sd_swap')) is not bool or _required(row, 'sd_swap') != (len(string(_required(swap[0], 'lexeme')).split()) == 5 and string(_required(swap[0], 'lexeme')).split()[-1] == 'X')):
            raise ValueError('instance identity fields disagree with their captured xref row')
    for row in net_rows:
        if set(row) != {'lvs_name', 'schematic_name', 'lvs_index', 'field_sources'} or set(mapping(_required(row, 'field_sources'))) != {'lvs_name', 'schematic_name', 'lvs_index'}:
            raise ValueError('invalid net xref evidence fields')
        layout, schematic, index = (_field_sources(row, field) for field in ('lvs_name', 'schematic_name', 'lvs_index'))
        if (len(layout) != 2 or len(schematic) != 1 or len(index) != 1
                or _required(layout[0], 'lexeme') != _required(row, 'lvs_name') or _required(layout[1], 'lexeme') != _required(row, 'lvs_name')
                or _required(schematic[0], 'lexeme') != _required(row, 'schematic_name')
                or layout[0].get('token_0based') != 1 or schematic[0].get('token_0based') != 3
                or not _same_row(layout[0], schematic[0]) or index[0] != layout[1]):
            raise ValueError('net identity fields disagree with xref and NET NAMES operands')
        ordinal_line = index[0].get('line_1based')
        if type(ordinal_line) is not int or ordinal_line < 4 or _required(row, 'lvs_index') != str(ordinal_line - 3):
            raise ValueError('LVS index is not its captured NET NAMES ordinal')
    metadata = mapping(_required(query, '_format_metadata'))
    for capability, rows, field in (('instance_xref', instance_rows, 'layout_instance'), ('net_xref', net_rows, 'lvs_name')):
        reference = mapping(_required(mapping(_required(metadata, capability)), 'source'))
        source = _required(sources, string(_required(reference, 'path')))
        positions = [(_required(_field_sources(row, field)[0], 'path'), _required(_field_sources(row, field)[0], 'line_1based')) for row in rows]
        expected_positions = [(source.uri, line) for line in range(9, len(source.data.splitlines()) + 1)]
        if sorted(positions) != sorted(expected_positions):
            raise ValueError('xref evidence omits or duplicates captured rows')
    names_reference = mapping(_required(mapping(_required(metadata, 'net_names')), 'count_header'))
    names_source = _required(sources, string(_required(names_reference, 'path')))
    names_positions = [(_required(_field_sources(row, 'lvs_index')[0], 'path'), _required(_field_sources(row, 'lvs_index')[0], 'line_1based')) for row in net_rows]
    if sorted(names_positions) != [(names_source.uri, line) for line in range(4, len(names_source.data.splitlines()))]:
        raise ValueError('net identity evidence omits or duplicates NET NAMES records')
    response_metadata = tuple(mapping(entry) for entry in sequence(_required(metadata, 'responses')))
    response_sources: list[tuple[str, str]] = []
    for response in response_metadata:
        reference = mapping(_required(response, 'source'))
        count_header = mapping(_required(response, 'count_header'))
        pair = (string(_required(reference, 'path')), string(_required(reference, 'sha256')))
        if (pair != (_required(count_header, 'path'), _required(count_header, 'sha256')) or count_header.get('line_1based') != 3
                or string(_required(count_header, 'lexeme')).split(maxsplit=3)[-1] != _required(response, 'timestamp')):
            raise ValueError('response metadata differs from its captured response')
        response_sources.append(pair)
    expected_response_sources = [(string(_required(mapping(item), 'uri')), string(_required(mapping(item), 'sha256'))) for item in sequence(_required(header, 'raw'))
                                 if _required(mapping(item), 'capability') in ('device_regions', 'net_regions')]
    if sorted(response_sources) != sorted(expected_response_sources):
        raise ValueError('request-ordered response metadata does not cover declared captures')
    response_capabilities = {string(_required(mapping(item), 'uri')): string(_required(mapping(item), 'capability')) for item in sequence(_required(header, 'raw'))}
    if len(requests) != len(response_sources):
        raise ValueError('response metadata count differs from captured requests')
    all_record_ids: list[str] = []
    for request, (path, sha) in zip(requests, response_sources):
        capability = string(_required(request, 'capability'))
        expected_command = 'DEVICE INFO' if capability == 'device_regions' else 'NET SHAPES'
        if _required(request, 'path') != path or _required(response_capabilities, path) != capability or _required(request, 'command_intent') != expected_command:
            raise ValueError('request-ordered response metadata differs from captured requests bytes')
        first_layer_line = 5 if capability == 'device_regions' else 4
        polygon_lines = len(_required(sources, path).data.splitlines()) - first_layer_line
        record_ids = sequence(_required(request, 'record_ids'))
        if polygon_lines < 7 or polygon_lines % 7 or len(record_ids) != polygon_lines // 7:
            raise ValueError('captured request record IDs do not cover their response polygons')
        all_record_ids.extend(string(record_id) for record_id in record_ids)
    if len(all_record_ids) != len(set(all_record_ids)):
        raise ValueError('captured request record IDs must be unique across responses')
    observed_requests: set[int] = set()
    registry = {string(_required(mapping(entry), 'id')): mapping(entry) for entry in sequence(_required(mapping(_required(tech, 'derived')), 'derived_registry'))}
    for capability, associations in (('device_regions', instance_rows), ('net_regions', net_rows)):
        key = 'layout_instance' if capability == 'device_regions' else 'lvs_name'
        identity_fields = ('layout_instance', 'schematic_instance') if capability == 'device_regions' else ('lvs_name', 'schematic_name', 'lvs_index')
        actual_positions: list[tuple[str, int]] = []
        for row_value in sequence(_required(mapping(_required(query, capability)), 'records')):
            row = mapping(row_value)
            matches = [candidate for candidate in associations if _required(candidate, key) == _required(row, key)]
            # Duplicate association/cardinality remains the normalizer's typed
            # admission error; never repair it by silently picking another row.
            if len(matches) == 1:
                association = matches[0]
                for field in identity_fields:
                    refs = _field_sources(row, field)
                    if (_required(row, field) != _required(association, field) or _required(refs[0], 'lexeme') != _required(row, key)
                            or refs[1:] != _field_sources(association, field)):
                        raise ValueError('region identity differs from its declared association sources')
            vertices_sources = _field_sources(row, 'vertices_nm')
            if len(vertices_sources) != 10:
                raise ValueError('region vertices require precision, eight coordinates and dialect')
            precision_source, geometry_source = vertices_sources[0], vertices_sources[-1]
            coordinate_sources = vertices_sources[1:-1]
            precision = _required(row, 'precision')
            if type(precision) is not int or precision <= 0 or _required(precision_source, 'lexeme') != str(precision):
                raise ValueError('region precision differs from captured precision token')
            geometry = mapping(_required(geometry_source, 'lexeme'))
            if (_required(geometry, 'raw_axis_order') != ('y', 'x') or _required(geometry, 'raw_unit') != 'micrometres / precision'
                    or _required(geometry, 'precision') != precision or rational(_required(geometry, 'raw_tick_nm')) != Fraction(1000, precision)):
                raise ValueError('region geometry dialect operands disagree')
            layer_sources = _field_sources(row, 'derived_layer')
            if len(layer_sources) != 2 or _required(layer_sources[0], 'lexeme') != _required(row, 'derived_layer'):
                raise ValueError('derived layer differs from captured raw layer')
            actual_positions.append((string(_required(layer_sources[0], 'path')), cast(int, _required(layer_sources[0], 'line_1based'))))
            object_source = _field_sources(row, key)[0]
            record_source = _field_sources(row, 'record_id')[0]
            object_pointer = string(_required(object_source, 'json_pointer'))
            record_pointer = string(_required(record_source, 'json_pointer'))
            object_match = re.fullmatch(r'/requests/(0|[1-9][0-9]*)/object', object_pointer)
            record_match = re.fullmatch(r'/requests/(0|[1-9][0-9]*)/record_ids/(0|[1-9][0-9]*)', record_pointer)
            if object_match is None or record_match is None or object_match.group(1) != record_match.group(1):
                raise ValueError('seed object and record ID belong to different query requests')
            request_index, polygon_index = int(object_match.group(1)), int(record_match.group(2))
            if request_index >= len(response_metadata):
                raise ValueError('seed references an absent captured query request')
            observed_requests.add(request_index)
            expected_path, expected_sha = response_sources[request_index]
            captured_request = requests[request_index]
            captured_ids = sequence(_required(captured_request, 'record_ids'))
            if (_required(captured_request, 'capability') != capability or _required(captured_request, 'object') != _required(row, key)
                    or _required(object_source, 'lexeme') != _required(captured_request, 'object')
                    or polygon_index >= len(captured_ids) or captured_ids[polygon_index] != _required(row, 'record_id')
                    or _required(record_source, 'lexeme') != captured_ids[polygon_index]):
                raise ValueError('seed request pointer values differ from captured requests bytes')
            first_layer_line = 5 if capability == 'device_regions' else 4
            if (_required(response_capabilities, expected_path) != capability
                    or _required(layer_sources[0], 'path') != expected_path or _required(layer_sources[0], 'sha256') != expected_sha
                    or _required(layer_sources[0], 'line_1based') != first_layer_line + polygon_index * 7):
                raise ValueError('seed geometry belongs to another request capture or polygon ordinal')
            for field in identity_fields:
                if _field_sources(row, field)[0] != object_source:
                    raise ValueError('seed identity fields refer to different requests')
            if any(ref.get('path') != request_source.uri or ref.get('sha256') != request_source.sha256 for ref in (object_source, record_source)):
                raise ValueError('seed request provenance is outside the captured requests role')
            registry_entry = mapping(_required(layer_sources[1], 'lexeme'))
            if registry.get(string(_required(row, 'derived_layer'))) != registry_entry or _required(row, 'quality') != _required(registry_entry, 'quality'):
                raise ValueError('seed quality/derived layer differs from selected registry')
            coords: list[tuple[Fraction, Fraction]] = []
            for vertex_index in range(4):
                y, x = coordinate_sources[vertex_index * 2:vertex_index * 2 + 2]
                if (not _same_row(x, y) or y.get('token_0based') != 0 or x.get('token_0based') != 1
                        or x.get('path') != layer_sources[0].get('path') or x.get('sha256') != layer_sources[0].get('sha256')
                        or x.get('line_1based') != cast(int, _required(layer_sources[0], 'line_1based')) + 3 + vertex_index):
                    raise ValueError('vertex provenance belongs to another region record')
                coords.append((Fraction(string(_required(x, 'lexeme'))) * 1000 / precision,
                               Fraction(string(_required(y, 'lexeme'))) * 1000 / precision))
            actual = tuple((rational(_required(mapping(point), 'x')), rational(_required(mapping(point), 'y'))) for point in sequence(_required(row, 'vertices_nm')))
            if actual != tuple(coords):
                raise ValueError('seed exact vertices disagree with captured coordinate operands')
            bbox = mapping(_required(row, 'bbox_nm'))
            expected_box = (min(x for x, y in coords), min(y for x, y in coords), max(x for x, y in coords), max(y for x, y in coords))
            if tuple(rational(_required(bbox, field)) for field in ('x_min', 'y_min', 'x_max', 'y_max')) != expected_box:
                raise ValueError('seed bbox differs from exact coordinate extrema')
            if _field_sources(row, 'bbox_nm') != vertices_sources or _required(row, 'geometry_kind') != 'rectangle' or _required(row, 'unit') != 'nm':
                raise ValueError('seed geometry/provenance differs from declared exact conversion')
            if (_field_sources(row, 'precision') != (precision_source, geometry_source)
                    or _field_sources(row, 'unit') != (precision_source, geometry_source)
                    or _field_sources(row, 'geometry_kind') != (*coordinate_sources, layer_sources[1])
                    or _field_sources(row, 'quality') != (*coordinate_sources, layer_sources[1])):
                raise ValueError('seed derived fields do not retain their declared operands')
            if (tuple(_required(ref, 'lexeme') for ref in _field_sources(row, 'metadata_opaque')) != _required(row, 'metadata_opaque')
                    or _required(_field_sources(row, 'section_header_opaque')[0], 'lexeme') != _required(row, 'section_header_opaque')
                    or _required(_field_sources(row, 'record_id')[0], 'lexeme') != _required(row, 'record_id')):
                raise ValueError('seed opaque/author fields differ from their captured operands')

        expected_regions: list[tuple[str, int]] = []
        for declaration_value in sequence(_required(header, 'raw')):
            declaration = mapping(declaration_value)
            if _required(declaration, 'capability') != capability:
                continue
            source = _required(sources, string(_required(declaration, 'uri')))
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


def request_decoder_input(result: ParseResult) -> tuple[SourceFile, int, int]:
    """Select the existing requests capture; this step never invokes a decoder."""
    if type(result) is not ParseResult or result.status != 'success' or result.value is None:
        raise ValueError('normalization requires a successful ParseResult')
    records = evidence_by_kind(result)
    query_sources = _required(records, 'query').sources
    if len(query_sources) < 3:
        raise ValueError('query receipt omits its requests capture')
    reference = query_sources[1]
    sources = {source.uri: source for source in result.sources}
    source = _required(sources, reference.uri)
    if source.sha256 != reference.sha256:
        raise ValueError('requests capture differs from its evidence reference')
    limits = mapping(_required(mapping(_required(mapping(_required(result.value, 'tech')), 'formats')), 'limits'))
    max_bytes, max_depth = _required(limits, 'max_bytes_per_text_file'), _required(limits, 'max_json_depth')
    if type(max_bytes) is not int or type(max_depth) is not int:
        raise ValueError('captured profile decoder limits must be exact integers')
    return source, max_bytes, max_depth


def decode_captured_requests(source: SourceFile, max_bytes: int, max_depth: int) -> FrozenMap:
    """Reuse the existing decoder on captured bytes, translating only its typed failures."""
    try:
        document = load_document(source, max_bytes=max_bytes, max_depth=max_depth)
        validate_document(document, 'requests', source)
    except InputError as exc:
        raise ValueError('captured requests do not satisfy the accepted document contract') from exc
    return document


def validate_parse(result: ParseResult, request_document: FrozenMap) -> None:
    if type(result) is not ParseResult or result.status != 'success' or result.value is None:
        raise ValueError('normalization requires a successful ParseResult')
    value = result.value
    if set(value) != {'config', 'tech', 'tech_bundle', 'gds', 'source_cdl', 'target_cdl', 'query', 'body', 'header', 'policies'}:
        raise ValueError('unknown or missing successful parser fields')
    records = evidence_by_kind(result)
    sources = {source.uri: source for source in result.sources}
    for kind, record in records.items():
        expected = ({'bundle': _required(value, 'tech_bundle'), 'owners': _required(value, 'tech')}
                    if kind == 'tech' else _required(value, kind))
        if canonical_bytes(record.payload) != canonical_bytes(expected):
            raise ValueError('parse value differs from completed evidence for ' + kind)
        for ref in record.sources:
            if ref.uri not in sources or _required(sources, ref.uri).sha256 != ref.sha256:
                raise ValueError('completed evidence references uncaptured bytes')
    if len(_required(records, 'tech').sources) != 7:
        raise ValueError('tech evidence requires bundle plus six declared owner captures')
    for kind in ('config', 'header', 'gds', 'source_cdl', 'target_cdl'):
        if len(_required(records, kind).sources) != 1:
            raise ValueError('parser role must bind one captured source: ' + kind)
    for kind in ('source_cdl', 'target_cdl'):
        doc = mapping(_required(value, kind))
        if doc.get('schema_version') != 'layauto-cdl-evidence/1' or doc.get('dialect') != 'toy_literal_cdl/1':
            raise ValueError('unsupported CDL evidence schema/dialect')
        ref = _required(records, kind).sources[0]
        source = _required(sources, ref.uri)
        if doc.get('raw_document') != source.data or mapping(_required(doc, 'source')) != {'uri': ref.uri, 'sha256': ref.sha256}:
            raise ValueError('CDL preservation is not its captured role bytes')
        if doc.get('globals') != () or doc.get('dependency_closure') != () or doc.get('preprocess') != 'none':
            raise ValueError('unsupported CDL evidence dependency/global declaration')
        validate_refs(doc, sources)
        validate_locations(doc, sources)
        _validate_cdl(doc, mapping(_required(value, 'tech')))
    header = mapping(_required(value, 'header'))
    for header_role, kind in (('layout', 'gds'), ('source_netlist', 'source_cdl'), ('target', 'target_cdl')):
        declaration = mapping(_required(header, header_role))
        # W005 already resolved aliases during acquisition. Role is NEVER chosen
        # by matching a hash or by resolving a pathname again here.
        if _required(declaration, 'sha256') != _required(records, kind).sources[0].sha256:
            raise ValueError('header role hash differs from its completed evidence')
        string(_required(declaration, 'uri'))
    closure = mapping(_required(header, 'closure'))
    entries = sequence(_required(closure, 'entries'))
    if _required(closure, 'sha256') != manifest_digest(entries):
        raise ValueError('header closure digest differs')
    declared_uris = [string(_required(mapping(item), 'uri')) for item in entries]
    if declared_uris != sorted(set(declared_uris)):
        raise ValueError('closure order/URI uniqueness differs')
    # Directly captured URIs must agree. An alias may be absent: its historic
    # resolution is a successful W005 fact, not reconstructable from bytes.
    for item in entries:
        declaration = mapping(item)
        captured = sources.get(string(_required(declaration, 'uri')))
        if captured is not None and captured.sha256 != _required(declaration, 'sha256'):
            raise ValueError('closure and captured source disagree')
        if string(_required(declaration, 'sha256')) not in {source.sha256 for source in result.sources}:
            raise ValueError('closure declares bytes not present in this capture')
    query = mapping(_required(value, 'query'))
    if set(query) != {*CAPABILITIES, '_format_metadata'}:
        raise ValueError('unknown/missing query evidence capability')
    raw = sequence(_required(header, 'raw'))
    raw_pairs = {(string(_required(mapping(item), 'uri')), string(_required(mapping(item), 'sha256'))) for item in raw}
    if len(raw_pairs) != len(raw):
        raise ValueError('duplicate raw capture declaration')
    for uri, sha in raw_pairs:
        if uri not in sources or sources[uri].sha256 != sha:
            raise ValueError('query raw evidence was mixed with other captured sources')
    for cap in CAPABILITIES:
        document = mapping(_required(query, cap))
        if (document.get('schema_version') != 'w004-query-normalized/2' or document.get('capability') != cap
                or document.get('dialect') != _required(header, 'query_dialect_version') or document.get('header_id') != _required(header, 'header_id')):
            raise ValueError('query capability is from another capture/header')
        for item in sequence(_required(document, 'raw_refs')):
            raw_ref = mapping(item)
            if (string(_required(raw_ref, 'path')), string(_required(raw_ref, 'sha256'))) not in raw_pairs:
                raise ValueError('query capability raw reference is outside this bundle')
        sequence(_required(document, 'records'))
    validate_refs(query, sources)
    validate_locations(query, sources)
    if len(_required(records, 'query').sources) != 3 + len(raw):
        raise ValueError('query evidence requires header, requests, dialect and all raw captures')
    _validate_query(query, mapping(_required(value, 'tech')), sources, header, _required(records, 'query').sources, request_document)
    validate_refs(mapping(_required(value, 'gds')), sources)
    # Require role captures to be present in the declared closure, including the
    # selected tech owners. This is membership, not alias→role reconstruction.
    closure_hashes = {string(_required(mapping(item), 'sha256')) for item in entries}
    for kind in ('config', 'tech', 'policies', 'gds', 'source_cdl', 'target_cdl', 'body'):
        if any(ref.sha256 not in closure_hashes for ref in _required(records, kind).sources):
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
