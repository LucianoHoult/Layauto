"""Independent closed synthetic analysis schemas; old schemas remain strict."""
from layauto_v2.domain.codec import FrozenMap
from .schema import (obj, literal, text, maybe, enum, FILE_REF, sha256, array,
                     boolean, positive_exact, positive, SchemaError, _index, _map, _unique, _array)

HEADER = obj({
    'schema_version': literal('layauto-analysis-query-header/1'), 'header_id': text, 'query_run_id': text,
    'query_database_id': maybe(text), 'query_database_absence_reason': maybe(text),
    'mode': enum('dummy_fixture', 'calibre'), 'classification': text, 'assurance': text,
    'lvs_completion_status': enum('not_run', 'unknown', 'completed', 'failed', 'error', 'incomplete'),
    'lvs_match_status': enum('not_run', 'unknown', 'matched', 'mismatched', 'unmatched'),
    'top_identities': obj({'layout': text, 'source': text}), 'hierarchy_mode': literal('flat'),
    'layout': FILE_REF,
    'source_netlist': obj({
        'uri': text, 'sha256': sha256, 'include_library_preprocess_closure': array(FILE_REF),
        'empty_closure_sha256': sha256, 'preprocess': literal('none'),
    }),
    'closure': obj({'entries': array(FILE_REF), 'canonical_encoding': literal('UTF-8 sorted-key compact JSON, array sorted by uri, no LF'), 'sha256': sha256}),
    'tool': obj({'name': maybe(text), 'version': maybe(text), 'executed': boolean}),
    'query_dialect_version': text, 'parser_contract_version': text, 'product_parser_version': maybe(text),
    'query_unit': obj({'name': text, 'metres_per_unit': positive_exact, 'geometry_precision': positive,
                       'axis_order': array(enum('x', 'y'), length=2)}),
    'geometry_unit_contract': text,
    'raw': array(obj({'capability': enum('instance_xref', 'net_xref', 'device_regions', 'net_regions'),
                     'uri': text, 'sha256': sha256}), nonempty=True),
    'limitations_ref': text,
})

def selection(value: object, path: str) -> None:
    if not isinstance(value, FrozenMap):
        raise SchemaError(path, 'selection requires an object')
    kind = value.get('kind')
    if kind == 'not_selected':
        obj({'kind': literal('not_selected')})(value, path)
    else:
        obj({'kind': enum('synthetic_context', 'trusted_lvs_freeze', 'geometry_window'), 'uri': text})(value, path)

MANIFEST = obj({
    'schema_version': literal('layauto-cell-analysis-request/1'),
    'purpose': text, 'mode': text,
    'inputs': obj({key: text for key in ('gds', 'source_cdl', 'query_header')}),
    'tech_ref': text, 'limitation_ref': text, 'external_body': selection,
}, {'manual_intent': lambda value, path: (
    obj({'kind': literal('not_selected')})(value, path)
    if isinstance(value, FrozenMap) and value.get('kind') == 'not_selected'
    else obj({'kind': literal('declaration'), 'uri': text})(value, path))})

def validate_analysis_payload(doc: FrozenMap, kind: str) -> None:
    if kind == 'analysis_manifest':
        MANIFEST(doc, '')
    elif kind == 'analysis_header':
        HEADER(doc, '')
        _index(doc['raw'], 'uri', '/raw')
        _index(_map(doc['closure'])['entries'], 'uri', '/closure/entries')
        _index(_map(doc['source_netlist'])['include_library_preprocess_closure'], 'uri', '/source_netlist/include_library_preprocess_closure')
        _unique(_array(_map(doc['query_unit'])['axis_order']), '/query_unit/axis_order')
    else:
        raise SchemaError('', 'unsupported analysis document kind', 'UnsupportedSchema')
