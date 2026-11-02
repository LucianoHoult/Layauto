"""Pure raw-query reading for calibre_like_synthetic/2.

The historical format description and accepted captures informed this grammar;
no legacy/helper code is imported. Formatting, association and rectangle proofs
are implemented here with complete consumption, exact arithmetic and typed errors.
This component never performs a GDS/CDL spatial or semantic join.
"""
from __future__ import annotations

from fractions import Fraction

from layauto_v2.domain.codec import FrozenMap, canonical_bytes, freeze_map, rational
from layauto_v2.domain.evidence import SourceFile
from layauto_v2.domain.results import InputError
from ._access import integer, mapping, sequence, string
from ._query_raw import NetNames, Polygon, Response, Text, Xref, parse_net_names, parse_response, parse_xref
from .config import load_document

CAPABILITIES = ('instance_xref', 'net_xref', 'device_regions', 'net_regions')
DIALECT = 'calibre_like_synthetic/2'


def _derived(rule: str, *sources: FrozenMap) -> FrozenMap:
    return freeze_map({'derivation': rule, 'sources': sources})


def _owner(source: SourceFile, pointer: str, value: object) -> FrozenMap:
    return freeze_map({'path': source.uri, 'sha256': source.sha256,
                       'json_pointer': pointer, 'lexeme': value})


def _rational(value: Fraction) -> FrozenMap:
    return freeze_map({'numerator': str(value.numerator), 'denominator': str(value.denominator)})


def _instance_records(xref: Xref) -> tuple[FrozenMap, ...]:
    return tuple(freeze_map({
        'layout_instance': row.layout, 'schematic_instance': row.source, 'sd_swap': row.swapped,
        'field_sources': {
            'layout_instance': _derived('verbatim', xref.text.location(row.line, 1)),
            'schematic_instance': _derived('verbatim', xref.text.location(row.line, 3)),
            'sd_swap': _derived('optional X token; absent is false', xref.text.location(row.line)),
        },
    }) for row in xref.rows)


def _net_records(xref: Xref, names: NetNames) -> tuple[FrozenMap, ...]:
    if {row.layout for row in xref.rows} != set(names.names):
        names.text.fail('NetJoinMismatch', 'nXref layout names and NET NAMES differ', 2, 'binding')
    indices = {name: ordinal for ordinal, name in enumerate(names.names)}
    records: list[FrozenMap] = []
    for row in xref.rows:
        ordinal = indices[row.layout]
        name_source = names.text.location(ordinal + 3)
        records.append(freeze_map({
            'lvs_name': row.layout, 'schematic_name': row.source, 'lvs_index': str(ordinal + 1),
            'field_sources': {
                'lvs_name': _derived('verbatim', xref.text.location(row.line, 1), name_source),
                'schematic_name': _derived('verbatim', xref.text.location(row.line, 3)),
                'lvs_index': _derived('one-based ordinal in this query-run NET NAMES; opaque across runs', name_source),
            },
        }))
    return tuple(records)


def _region_record(response: Response, polygon: Polygon, record_id: str, ordinal: int,
                   request: FrozenMap, request_index: int, request_source: SourceFile,
                   dialect_source: SourceFile, geometry: FrozenMap,
                   derived_source: SourceFile, registry_entry: FrozenMap, registry_index: int,
                   joined: FrozenMap, capability: str) -> FrozenMap:
    text = response.text
    layer_source = text.location(polygon.layer_line)
    registry_source = _owner(derived_source, f'/derived_registry/{registry_index}', registry_entry)
    geometry_source = _owner(dialect_source, '/geometry', geometry)
    precision_source = text.location(0, 1)
    vertex_sources = tuple(text.location(line, token)
                           for line in range(polygon.vertex_line, polygon.vertex_line + 4)
                           for token in (0, 1))
    conversion_sources = (precision_source, *vertex_sources, geometry_source)
    xs, ys = [p[0] for p in polygon.vertices], [p[1] for p in polygon.vertices]
    values: dict[str, object] = {
        'record_id': record_id,
        'derived_layer': polygon.layer,
        'geometry_kind': 'rectangle',
        'quality': registry_entry['quality'],
        'vertices_nm': tuple({'x': _rational(x), 'y': _rational(y)} for x, y in polygon.vertices),
        'bbox_nm': dict(zip(('x_min', 'y_min', 'x_max', 'y_max'),
                           (_rational(min(xs)), _rational(min(ys)), _rational(max(xs)), _rational(max(ys))))),
        'unit': 'nm', 'precision': response.precision,
        'metadata_opaque': tuple(text.lines[i] for i in response.metadata_lines),
        'section_header_opaque': text.lines[polygon.section_line],
    }
    sources: dict[str, object] = {
        'record_id': _derived('author ordinal label, not a raw identity',
                              _owner(request_source, f'/requests/{request_index}/record_ids/{ordinal}', record_id)),
        'derived_layer': _derived('verbatim', layer_source, registry_source),
        'geometry_kind': _derived('prove four distinct axis-aligned rectangle corners', *vertex_sources, registry_source),
        'quality': _derived('lossless rectangle proof + selected dialect/derived registry, not raw token', *vertex_sources, registry_source),
        'vertices_nm': _derived('raw(y,x) * 1000 / precision nm; preserve vertex order', *conversion_sources),
        'bbox_nm': _derived('extrema of proven exact vertices', *conversion_sources),
        'unit': _derived('dialect micrometres/precision converted to nm', precision_source, geometry_source),
        'precision': _derived('positive exact geometry precision', precision_source, geometry_source),
        'metadata_opaque': _derived('verbatim unknown metadata semantics', *(text.location(i) for i in response.metadata_lines)),
        'section_header_opaque': _derived('verbatim; count meanings unverified', text.location(polygon.section_line)),
    }
    identity_source = _owner(request_source, f'/requests/{request_index}/object', request['object'])
    identity_fields = ('layout_instance', 'schematic_instance') if capability == 'device_regions' else ('lvs_name', 'lvs_index', 'schematic_name')
    joined_sources = mapping(joined['field_sources'])
    for key in identity_fields:
        values[key] = joined[key]
        inherited = tuple(mapping(item) for item in sequence(mapping(joined_sources[key])['sources']))
        sources[key] = _derived('bound query object plus xref/NET NAMES join', identity_source, *inherited)
    values['field_sources'] = sources
    return freeze_map(values)


def _cache(header: FrozenMap, capability: str, records: tuple[FrozenMap, ...],
           sources: tuple[SourceFile, ...]) -> FrozenMap:
    by_uri = {source.uri: source for source in sources}
    return freeze_map({
        'schema_version': 'w004-query-normalized/2', 'header_id': header['header_id'],
        'dialect': DIALECT, 'capability': capability,
        'raw_refs': tuple({'path': uri, 'sha256': by_uri[uri].sha256} for uri in sorted(by_uri)),
        'records': records,
    })


def _xref_metadata(xref: Xref) -> FrozenMap:
    return freeze_map({
        'source': {'path': xref.text.source.uri, 'sha256': xref.text.source.sha256},
        'layout_top': xref.layout_top, 'source_top': xref.source_top,
        'layout_pin_count': xref.layout_pin_count, 'source_pin_count': xref.source_pin_count,
        'header_lines': xref.text.lines[:7], 'summary': xref.text.location(7),
    })


def parse_query(raw: tuple[SourceFile, ...], header: FrozenMap, requests: SourceFile,
                dialect: SourceFile, tech: FrozenMap, *, derived_source: SourceFile) -> FrozenMap:
    """Parse all four capabilities from bound bytes and validated profiles.

    The four capability values are freshly reconstructed cache-compatible maps.
    ``_format_metadata`` preserves summary and opaque information absent from the
    older cache schema. Root acquisition retains the complete SourceFiles.
    """
    limits = mapping(mapping(tech['formats'])['limits'])
    max_bytes, max_depth = integer(limits['max_bytes_per_text_file']), integer(limits['max_json_depth'])
    max_records = integer(limits['max_records'])
    request_doc = load_document(requests, max_bytes=max_bytes, max_depth=max_depth)
    dialect_doc = load_document(dialect, max_bytes=max_bytes, max_depth=max_depth)
    derived_doc = load_document(derived_source, max_bytes=max_bytes, max_depth=max_depth)
    if canonical_bytes(derived_doc) != canonical_bytes(tech['derived']):
        raise InputError('binding', 'RegistrySourceMismatch', 'derived profile differs from its actual bytes', derived_source.ref())
    if dialect_doc['id'] != DIALECT or header['query_dialect_version'] != DIALECT:
        raise InputError('unsupported', 'UnsupportedQueryDialect', 'unsupported query dialect', dialect.ref(field='/id'))
    if header['parser_contract_version'] != 'w004-query-normalized/2':
        raise InputError('unsupported', 'UnsupportedParserContract', 'unsupported normalized query contract', dialect.ref())
    geometry = mapping(dialect_doc['geometry'])
    precision = integer(geometry['precision'])
    tick_nm = rational(geometry['raw_tick_nm'])
    query_unit = mapping(header['query_unit'])
    if precision <= 0 or geometry['raw_axis_order'] != ('y', 'x') or geometry['raw_unit'] != 'micrometres / precision' or tick_nm != Fraction(1000, precision):
        raise InputError('binding', 'QueryUnitDeclarationConflict', 'dialect exact unit/axis/precision conflict', dialect.ref(field='/geometry'))
    if (query_unit['geometry_precision'] != precision or query_unit['axis_order'] != ('y', 'x')
            or query_unit['name'] != 'micrometres/precision'
            or rational(query_unit['metres_per_unit']) != Fraction(1, 1_000_000)):
        raise InputError('binding', 'UnitBindingMismatch', 'query header and dialect units disagree', dialect.ref(field='/geometry'))
    if not raw:
        raise InputError('read', 'MissingRaw', 'raw query inputs are required', requests.ref())
    files = {source.uri: source for source in raw}
    if len(files) != len(raw):
        raise InputError('binding', 'DuplicateRawBinding', 'duplicate raw URI', raw[0].ref())
    declarations: dict[str, str] = {}
    groups: dict[str, list[Text]] = {cap: [] for cap in CAPABILITIES}
    for entry_value in sequence(header['raw']):
        entry = mapping(entry_value)
        uri, cap = string(entry['uri']), string(entry['capability'])
        if uri in declarations or cap not in groups or uri not in files:
            raise InputError('binding', 'RawListMismatch', 'raw declarations are duplicate, missing or unsupported', requests.ref(field='/requests'))
        declarations[uri] = cap
        source = files[uri]
        if source.sha256 != entry['sha256']:
            raise InputError('binding', 'RawHashMismatch', 'raw bytes disagree with declared SHA-256', source.ref())
        groups[cap].append(Text.read(source, max_bytes))
    if set(declarations) != set(files):
        raise InputError('binding', 'RawListMismatch', 'unlisted raw source supplied', requests.ref())
    if len(groups['instance_xref']) != 1 or len(groups['net_xref']) != 2:
        raise InputError('binding', 'RawListMismatch', 'requires one instance xref and two net association captures', requests.ref())
    instance = parse_xref(groups['instance_xref'][0], 'instance', max_records)
    net_group = groups['net_xref']
    net_xref_candidates = [text for text in net_group if text.lines[0].startswith('# SVDB:')]
    if len(net_xref_candidates) != 1:
        net_group[0].fail('RawListMismatch', 'cannot uniquely select nXref capture')
    net_text = net_xref_candidates[0]
    net = parse_xref(net_text, 'net', max_records)
    names = parse_net_names(next(text for text in net_group if text is not net_text), max_records)
    top = mapping(header['top_identities'])
    for xref in (instance, net):
        if xref.layout_top != top['layout'] or xref.source_top != top['source']:
            xref.text.fail('TopBindingMismatch', 'xref top disagrees with bundle header', 7, 'binding')
    if (instance.layout_pin_count, instance.source_pin_count) != (net.layout_pin_count, net.source_pin_count):
        net.text.fail('XrefPinCountMismatch', 'instance and net xref summary pin counts differ', 7, 'binding')
    instance_records = _instance_records(instance)
    net_records = _net_records(net, names)
    instance_by_id = {string(record['layout_instance']): record for record in instance_records}
    nets_by_id = {string(record['lvs_name']): record for record in net_records}
    registry: dict[str, tuple[int, FrozenMap]] = {}
    for index, entry_value in enumerate(sequence(derived_doc['derived_registry'])):
        entry = mapping(entry_value)
        name = string(entry['id'])
        if name in registry:
            raise InputError('config', 'DuplicateDerivedLayer', 'ambiguous derived registry ID', derived_source.ref(field=f'/derived_registry/{index}'))
        if entry['quality'] != 'exact' or entry['accepted_geometry_kinds'] != ('rectangle',) or entry['source'] != DIALECT:
            raise InputError('binding', 'QueryQualityDeclarationConflict', 'unsupported derived geometry/quality declaration', derived_source.ref(field=f'/derived_registry/{index}'))
        registry[name] = index, entry
    region_records: dict[str, list[FrozenMap]] = {'device_regions': [], 'net_regions': []}
    seen_paths: set[str] = set()
    seen_ids: set[str] = set()
    opaque: list[FrozenMap] = []
    request_entries = sequence(request_doc['requests'])
    if len(request_entries) > max_records:
        raise InputError('config', 'RecordLimit', 'too many query requests', requests.ref(field='/requests'))
    for request_index, request_value in enumerate(request_entries):
        request = mapping(request_value)
        capability = string(request['capability'])
        uri, identity = string(request['path']), string(request['object'])
        if capability not in region_records or uri in seen_paths or declarations.get(uri) != capability:
            raise InputError('binding', 'RequestBindingMismatch', 'request does not uniquely bind a matching raw capture', requests.ref(field=f'/requests/{request_index}/path'))
        seen_paths.add(uri)
        expected_command = 'DEVICE INFO' if capability == 'device_regions' else 'NET SHAPES'
        if request['command_intent'] != expected_command:
            raise InputError('binding', 'RequestBindingMismatch', 'command intent disagrees with capability', requests.ref(field=f'/requests/{request_index}/command_intent'))
        identities = instance_by_id if capability == 'device_regions' else nets_by_id
        if identity not in identities:
            raise InputError('binding', 'QueryObjectMismatch', 'request object absent from associated xref', requests.ref(field=f'/requests/{request_index}/object'))
        text = next(text for text in groups[capability] if text.source.uri == uri)
        response = parse_response(text, capability, precision, tick_nm, max_records)
        ids = tuple(string(value) for value in sequence(request['record_ids']))
        if len(ids) != len(response.polygons):
            text.fail('ResponseShapeCountMismatch', 'request record count differs from consumed polygons')
        if not ids or len(set(ids)) != len(ids) or any(not value or value in seen_ids for value in ids):
            raise InputError('binding', 'DuplicateRecordId', 'record IDs must be nonempty and unique in the bundle', requests.ref(field=f'/requests/{request_index}/record_ids'))
        seen_ids.update(ids)
        for ordinal, polygon in enumerate(response.polygons):
            if polygon.layer not in registry:
                text.fail('UnknownDerivedLayer', 'response uses an undeclared derived layer', polygon.layer_line, 'binding')
            registry_index, entry = registry[polygon.layer]
            required_carry = 'device_id' if capability == 'device_regions' else 'net_id'
            if required_carry not in sequence(entry['carries']):
                text.fail('DerivedCapabilityMismatch', 'derived layer cannot carry requested identity kind', polygon.layer_line, 'binding')
            region_records[capability].append(_region_record(
                response, polygon, ids[ordinal], ordinal, request, request_index, requests,
                dialect, geometry, derived_source, entry, registry_index, identities[identity], capability))
        opaque.append(freeze_map({'source': {'path': uri, 'sha256': text.source.sha256},
                                  'count_header': text.location(2), 'timestamp': response.timestamp}))
    region_paths = {uri for uri, capability in declarations.items() if capability in region_records}
    if region_paths != seen_paths:
        raise InputError('binding', 'RequestBindingMismatch', 'every raw region response needs an explicit request', requests.ref(field='/requests'))
    if any(len(records) > max_records for records in region_records.values()):
        raise InputError('parse', 'RecordLimit', 'capability exceeds profile record limit', requests.ref())
    result: dict[str, object] = {
        'instance_xref': _cache(header, 'instance_xref', instance_records, (instance.text.source,)),
        'net_xref': _cache(header, 'net_xref', net_records, (net.text.source, names.text.source)),
    }
    for capability, records in region_records.items():
        association_sources = (instance.text.source,) if capability == 'device_regions' else (net.text.source, names.text.source)
        result[capability] = _cache(header, capability, tuple(records),
                                    (*association_sources, *(text.source for text in groups[capability])))
    result['_format_metadata'] = {
        'instance_xref': _xref_metadata(instance), 'net_xref': _xref_metadata(net),
        'net_names': {'opener_opaque': names.opener, 'count_header': names.text.location(2), 'timestamp': names.timestamp},
        'responses': opaque,
    }
    return freeze_map(result)
