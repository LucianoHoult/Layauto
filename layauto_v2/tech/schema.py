"""Closed schemas for the versioned synthetic input dialect.

This is a grammar, not a fixture template: names, paths, coordinates, thresholds
and array lengths are data. Cross-field validation checks interpretation claims.
"""
from __future__ import annotations

import re
from fractions import Fraction
from collections.abc import Callable

from layauto_v2.domain.codec import FrozenMap, Value, rational


class SchemaError(ValueError):
    def __init__(self, path: str, message: str, code: str = 'InvalidSchema') -> None:
        self.path, self.code = path, code
        super().__init__(message)


Check = Callable[[Value, str], None]


def _fail(path: str, message: str) -> None:
    raise SchemaError(path, message)


def text(value: Value, path: str) -> None:
    if not isinstance(value, str) or not value:
        _fail(path, 'expected nonempty string')


def integer(value: Value, path: str) -> None:
    if type(value) is not int:
        _fail(path, 'expected exact integer (not boolean)')


def boolean(value: Value, path: str) -> None:
    if type(value) is not bool:
        _fail(path, 'expected boolean')


def null(value: Value, path: str) -> None:
    if value is not None:
        _fail(path, 'expected null')


def natural(value: Value, path: str) -> None:
    integer(value, path)
    if isinstance(value, int) and value < 0:
        _fail(path, 'expected nonnegative integer')


def positive(value: Value, path: str) -> None:
    integer(value, path)
    if isinstance(value, int) and value <= 0:
        _fail(path, 'expected positive integer')


def enum(*choices: str) -> Check:
    def check(value: Value, path: str) -> None:
        text(value, path)
        if value not in choices:
            _fail(path, f'unsupported value; expected one of {choices!r}')
    return check


def literal(expected: Value) -> Check:
    def check(value: Value, path: str) -> None:
        if type(value) is not type(expected) or value != expected:
            _fail(path, f'expected {expected!r}')
    return check


def maybe(check: Check) -> Check:
    def wrapped(value: Value, path: str) -> None:
        if value is not None:
            check(value, path)
    return wrapped


def array(check: Check, *, length: int | None = None, nonempty: bool = False) -> Check:
    def wrapped(value: Value, path: str) -> None:
        if not isinstance(value, tuple):
            _fail(path, 'expected array')
            return
        if length is not None and len(value) != length:
            _fail(path, f'expected {length} items')
        if nonempty and not value:
            _fail(path, 'array must not be empty')
        for index, item in enumerate(value):
            check(item, f'{path}/{index}')
    return wrapped


def dictionary(check: Check) -> Check:
    def wrapped(value: Value, path: str) -> None:
        if not isinstance(value, FrozenMap):
            _fail(path, 'expected string-keyed map')
            return
        for key, item in value.items():
            if not key:
                _fail(path, 'map key must not be empty')
            check(item, f'{path}/{key}')
    return wrapped


def obj(required: dict[str, Check], optional: dict[str, Check] | None = None) -> Check:
    optional = optional or {}
    def wrapped(value: Value, path: str) -> None:
        if not isinstance(value, FrozenMap):
            _fail(path, 'expected object')
            return
        for key in value:
            if key not in required and key not in optional:
                raise SchemaError(f'{path}/{key}', 'unknown field', 'UnknownKey')
        for key in required:
            if key not in value:
                raise SchemaError(f'{path}/{key}', 'required field missing', 'MissingField')
        for key, item in value.items():
            check = required.get(key, optional.get(key))
            if check is None:
                raise AssertionError('closed schema check was not found')
            check(item, f'{path}/{key}')
    return wrapped


def exact(value: Value, path: str) -> None:
    try:
        rational(value)
    except ValueError as exc:
        raise SchemaError(path, str(exc), 'InvalidExactValue') from exc


def positive_exact(value: Value, path: str) -> None:
    exact(value, path)
    if rational(value) <= 0:
        _fail(path, 'exact scale must be positive')


def sha256(value: Value, path: str) -> None:
    if not isinstance(value, str) or re.fullmatch('[0-9a-f]{64}', value) is None:
        _fail(path, 'expected lowercase SHA-256')


def bbox(value: Value, path: str) -> None:
    array(integer, length=4)(value, path)
    assert isinstance(value, tuple)
    x0, y0, x1, y1 = value
    assert isinstance(x0, int) and isinstance(y0, int) and isinstance(x1, int) and isinstance(y1, int)
    if x0 >= x1 or y0 >= y1:
        _fail(path, 'bbox must have positive area')


STRINGS = array(text)
EMPTY = obj({})
OWNER_VERSION = literal('w004-tech-owner/2')
FILE_REF = obj({'uri': text, 'sha256': sha256})
SCHEMAS: dict[str, Check] = {}



OUTPUTS = obj({'directory': text, 'core': STRINGS, 'reports': STRINGS})
OWNER_KEYS: dict[str, tuple[str, ...]] = {
    'drawn': ('layers',), 'derived': ('derived_registry',),
    'physical': ('fin_count_profile', 'models', 'device_extraction_contract',
                 'body_context_profile', 'operators', 'capabilities', 'required_operator_refs'),
    'formats': ('geometry_capability', 'unit_scale_contract', 'cdl_dialect', 'limits'),
    'coordinate': ('coordinate_projection',), 'rules': ('rules', 'mandatory_rule_policy'),
}
OWNER_REF = obj({'path': text, 'keys': STRINGS})
SCHEMAS['site'] = obj({
    'schema_version': literal('w003-site/1'), 'mode': enum('dummy_fixture'),
    'relative_path_base': literal('this_file_parent'),
    'inputs': obj({key: text for key in ('gds', 'source_cdl', 'target_cdl', 'query_header', 'body_context')}),
    'tech_ref': text, 'export_policy_ref': text, 'validation_policy_ref': text,
    'limitation_ref': text, 'outputs': OUTPUTS,
    'tool': obj({key: maybe(text) for key in ('binary', 'version', 'query_database', 'production_platform')}),
    'note': text,
})
SCHEMAS['tech'] = obj({
    'schema_version': literal('w004-tech-bundle/2'), 'profile_id': text,
    'classification': enum('synthetic'), 'production_technology': null,
    'owners': obj({name: OWNER_REF for name in OWNER_KEYS}),
})
SCHEMAS['drawn'] = obj({
    'schema_version': OWNER_VERSION,
    'layers': array(obj({
        'name': text, 'stream_key': obj({'element': enum('BOUNDARY'), 'layer': natural, 'datatype': natural}),
        'purpose': text, 'tier': enum('A', 'B', 'C1', 'C2'),
        'role': enum('boundary', 'body', 'diffusion', 'gate', 'fin', 'interconnect', 'cut', 'contact', 'via', 'body_contact', 'marker'),
        'lifecycle': enum('preserve_drawn', 'frame_static'),
        'edit_policy': enum('no_direct_edit', 'fixed_for_this_no_change_capability'),
        'projection_kind': enum('none', 'exact_fragment_rectangles'),
        'derived_layer_refs': STRINGS,
    }, {
        'cut_target': text, 'effective_geometry_operator': text,
        'electrical_connects': array(text, length=2), 'contact_predicate': text,
        'enclosure_rule': text,
    }), nonempty=True),
})
SCHEMAS['derived'] = obj({
    'schema_version': OWNER_VERSION,
    'derived_registry': array(obj({
        'id': text, 'target_layer': text, 'carries': array(enum('device_id', 'net_id'), nonempty=True),
        'accepted_geometry_kinds': array(enum('rectangle'), nonempty=True),
        'quality': enum('exact', 'approximate_bbox', 'untrimmed'),
        'annotation_match_tolerance_nm': natural, 'trim_operator': text,
        'conflict_policy': enum('reject_ambiguous'), 'source': literal('calibre_like_synthetic/2'),
    }), nonempty=True),
})
PARAMETER_AXES = obj({
    'NFIN': literal('fins_per_finger'), 'NF': literal('finger_count'), 'M': literal('multiplicity'),
    'L': literal('channel_length'), 'W': literal('fin_width'), 'VT': literal('threshold_token'),
})
MODEL = obj({
    'terminal_order': literal(('D', 'G', 'S', 'B')), 'parameter_axes': PARAMETER_AXES,
    'required_parameters': STRINGS, 'default_parameters': EMPTY, 'sd_symmetry': literal(False),
})
SCHEMAS['physical'] = obj({
    'schema_version': OWNER_VERSION,
    'fin_count_profile': obj({
        'id': literal('toy_fin_crossing/1'),
        'fin_representation': literal('explicit_static_fin_plus_active_window'),
        'effective_fin_operator': literal('identity'), 'effective_active_operator': literal('identity_OD'),
        'recognized_channel_operator': text, 'qualification': text, 'count': text,
        'finger_count_required': literal(1), 'multiplicity_required': literal(1),
        'fin_width_nm': positive, 'fin_pitch_nm': positive, 'fin_lower_edge_offset_nm': integer,
    }),
    'models': dictionary(MODEL),
    'device_extraction_contract': obj({
        'id': literal('toy_device_terminal_context/2'), 'cardinality': literal('one_to_one'),
        'device_reduction': literal('forbidden'), 'layout_instance_names': text,
        'sd_policy': text, 'body_operator': text, 'gate_operator': text,
        'mapping_missing_or_ambiguous': literal('typed_fail'), 'body_operator_ref': text,
    }),
    'body_context_profile': obj({
        'id': literal('toy_readonly_tapcell_context/2'), 'operator_ref': text,
        'coordinates': text, 'geometry_scope': text, 'source_binding': text,
        'types': dictionary(array(text, length=2)), 'missing_support': text,
        'geometry_failure': text, 'unique_matches_required': literal(True),
    }),
    'operators': dictionary(text),
    'capabilities': obj({
        'no_change': literal(True), 'resize': literal(False), 'body_complete_for_toy': literal(True),
        'production_matched_body_evidence': literal(False), 'production_abutment': literal(False),
    }),
    'required_operator_refs': STRINGS,
})
SCHEMAS['formats'] = obj({
    'schema_version': OWNER_VERSION,
    'geometry_capability': obj({
        'id': literal('flat_boundary_rectangles/1'), 'stream': literal('GDSII'), 'version': literal(600),
        'top': literal('one_reachable_flat_cell'), 'supported_elements': literal(('BOUNDARY',)),
        'polygon': text, 'unsupported': STRINGS, 'handling': literal('typed_fail_before_baseline'), 'comparator': text,
    }),
    'unit_scale_contract': obj({
        'id': literal('toy_gds_real8_nm/1'), 'nominal_tick_m': positive_exact,
        'nominal_user_unit_m': positive_exact, 'canonical_tick_nm': positive,
        'gds_units_first_nominal': positive_exact,
        'encoding': literal('GDS base16 REAL8 round-nearest ties-to-even 56-bit mantissa'),
        'equivalence': text, 'geometry_quantization': literal('forbidden'),
        'source_tick_policy': literal('preserve integers without snap'),
        'output_xy_range': literal((-2147483648, 2147483647)),
        'output_nominal_selection': text,
        'nominal_source': obj({'identity': text, 'kind': enum('hand_authored_test_choice'), 'basis': text}),
    }),
    'cdl_dialect': obj({
        'id': literal('toy_literal_cdl/1'),
        'case_policy': literal('case_sensitive identifiers, directives and parameter names'),
        'identifier_regex': literal('[A-Za-z_][A-Za-z0-9_]*'),
        'escaping': literal('none; whitespace inside identifier unsupported'),
        'pin_order': literal('source declaration preserved'), 'globals': literal('empty only'),
        'numeric_suffixes': obj({'n': positive_exact}),
        'literal_grammar': literal('positive integer for NFIN,NF,M; positive integer followed by n for L,W; VT token toy'),
        'comments': literal('full-line star only'), 'continuation': literal('unsupported'),
        'supported_directives': literal(('.SUBCKT', '.ENDS')), 'unsupported': STRINGS,
        'dependency_closure': literal('empty, explicitly hashed; include/lib/preprocess unsupported'),
        'semantic_comparator': text, 'models_ref': literal('physical.json#/models'),
    }),
    'limits': obj({
        'max_records': positive, 'max_bytes_per_text_file': positive, 'max_json_depth': positive,
        'safe_json_yaml_subset_only': literal(True), 'duplicate_unknown_keys': literal('reject'),
        'floats_nan_inf_executable_tags': literal('reject'),
    }),
})
SCHEMAS['coordinate'] = obj({
    'schema_version': OWNER_VERSION,
    'coordinate_projection': obj({
        'id': literal('w004-coordinate-example/2'), 'example_only': literal(True),
        'is_complete_runtime_model': literal(False), 'unit_contract_ref': literal('formats.json#/unit_scale_contract'),
        'frame_origin_nm': array(integer, length=2), 'purpose': text,
    }),
})
RULE_PARAMETERS = obj({}, {
    'margin_nm': natural, 'active_enclosure_nm': natural, 'enclosure_nm': natural,
    'min_distance_nm': natural, 'terminal_order': literal(('D', 'G', 'S', 'B')),
    'ordered_eco_commit_count': natural, 'unknown_nonconductor_policy': text,
    'disconnected_label_policy': text,
})
SCHEMAS['rules'] = obj({
    'schema_version': OWNER_VERSION,
    'rules': array(obj({
        'id': text, 'scope': text, 'predicate': text,
        'relation_basis': enum('geometry_only', 'same_component', 'none'),
        'schema_version': enum('w003-toy-rule/1', 'w004-toy-rule/2'), 'unit': literal('nm'),
        'parameters': RULE_PARAMETERS,
        'source': obj({'classification': literal('hand_authored_synthetic'), 'version': text}),
        'exact_evaluator_ref': text, 'required_relation_assurance': enum('none', 'exact_local_components_plus_bound_context_association'),
        'missing_context_policy': literal('reject_indeterminate'), 'required': literal(True),
    }, {'profile_ref': literal('physical.json#/fin_count_profile')}), nonempty=True),
    'mandatory_rule_policy': obj({
        'all_listed_rules_required': literal(True), 'run_before_no_change_closure': literal(True),
        'missing_operator_or_context': literal('indeterminate_then_reject'),
        'predicate_execution_error': literal('error_then_reject'), 'scope': literal('whole_cell'),
        'site_may_disable': literal(False),
    }),
})
ARTIFACT = obj({'kind': enum('gds', 'cdl', 'json'), 'name': text})
SCHEMAS['export_policy'] = obj({
    'schema_version': literal('w003-export-policy/1'), 'profile_id': text,
    'classification': literal('expected_policy_sample'), 'required_artifacts': array(ARTIFACT, nonempty=True),
    'optional_artifacts': array(ARTIFACT), 'output_directory': text,
    'object_path_template': text, 'manifest_path_template': text, 'path_token_policy': text,
    'relative_path_base': literal('site_config.yaml parent'), 'overwrite': literal('reject_existing_final_objects'),
    'publish': text, 'gds_tick_nm': positive_exact, 'rounding': literal('forbidden'),
    'representability': text, 'unit_equivalence_contract': literal('toy_gds_real8_nm/1'),
    'cdl_dialect': literal('toy_literal_cdl/1'), 'hash': text,
})
SCHEMAS['validation_policy'] = obj({
    'schema_version': literal('w003-validation-policy/1'), 'classification': literal('synthetic expected policy sample'),
    'required': STRINGS, 'normal_terminal_disposition': literal('requires_review'),
    'required_violation_disposition': literal('reject'), 'required_execution_error_disposition': literal('reject'),
    'checks': STRINGS, 'deferred': STRINGS, 'deferred_coverage': literal('none'),
    'deferred_is_pass': literal(False), 'production_acceptance': literal(False),
    'check_obligations': array(obj({
        'check_id': text, 'inputs': STRINGS, 'expected_proof': text,
        'status': enum('expected_pass_not_product_run', 'deferred'), 'original_obligation': text,
    })),
})
SCHEMAS['limitations'] = obj({
    'schema_version': literal('w003-limitations/1'), 'classification': enum('synthetic'),
    'tool_captured': literal(False), 'real_tool_executed': literal(False),
    'production_checks': obj({key: text for key in (
        'model', 'unit_binding', 'query_dialect', 'tool_version', 'pdk', 'body', 'abutment',
        'real_lvs_match', 'real_drc', 'downstream_open_syntax', 'virtuoso_dry_run', 'legacy_virtuoso_readback_scope')}),
    'query_assurance': literal('synthetic'), 'parser_status': text,
    'normal_terminal': literal('requires_review'), 'local_only': literal(True),
    'unknown_permissions': STRINGS, 'intentional_geometry_cases': STRINGS, 'unsupported': STRINGS,
    'truth_inputs': STRINGS, 'oracle_not_input': STRINGS, 'generation': text,
    'no_product_acceptance_claim': literal(True),
})
SCHEMAS['header'] = obj({
    'schema_version': literal('w004-query-header/2'), 'header_id': text, 'query_run_id': text,
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
    'target': FILE_REF,
    'closure': obj({'entries': array(FILE_REF), 'canonical_encoding': text, 'sha256': sha256}),
    'tool': obj({'name': maybe(text), 'version': maybe(text), 'executed': boolean}),
    'query_dialect_version': text, 'parser_contract_version': text, 'product_parser_version': maybe(text),
    'query_unit': obj({'name': text, 'metres_per_unit': positive_exact, 'geometry_precision': positive,
                       'axis_order': array(enum('x', 'y'), length=2)}),
    'geometry_unit_contract': text,
    'raw': array(obj({'capability': enum('instance_xref', 'net_xref', 'device_regions', 'net_regions'),
                     'uri': text, 'sha256': sha256}), nonempty=True),
    'limitations_ref': text,
})
CONTEXT_SHAPE = obj({'id': text, 'layer': text, 'bbox': bbox})
SCHEMAS['body'] = obj({
    'schema_version': literal('w004-synthetic-tapcell-context/2'), 'classification': literal('synthetic'),
    'author': text, 'source': text, 'read_only': literal(True), 'exported': literal(False),
    'top': text, 'frame_id': text, 'frame_bbox_nm': bbox,
    'coordinate_frame': literal('source local frame; identity transform'),
    'unit': obj({'name': literal('nm'), 'metres_per_tick': positive_exact}),
    'profile_ref': text, 'operator_ref': text, 'production_matched_body_evidence': literal(False),
    'lvs_status': enum('not_run', 'unknown'), 'local_bindings': array(CONTEXT_SHAPE),
    'shapes': array(CONTEXT_SHAPE),
    'associations': array(obj({key: text for key in (
        'device', 'local_body', 'external_body', 'tap', 'external_rail', 'local_rail', 'expected_semantic_rail')})),
    'source_gds': FILE_REF,
})
SCHEMAS['requests'] = obj({
    'schema_version': literal('w004-query-requests/2'), 'source': text,
    'requests': array(obj({
        'capability': enum('device_regions', 'net_regions'), 'path': text, 'object': text,
        'command_intent': enum('DEVICE INFO', 'NET SHAPES'), 'record_ids': array(text, nonempty=True),
    })),
})
SCHEMAS['dialect'] = obj({
    'schema_version': literal('w004-calibre-like-dialect/2'), 'id': literal('calibre_like_synthetic/2'),
    'classification': literal('synthetic_from_legacy_format_description'), 'source_version': text,
    'source_refs': array(obj({'repository_path': text, 'sha256': sha256})),
    'tool_version': null, 'production_verified': literal(False),
    'encoding': text, 'xref': text, 'net_names': text, 'net_index': text, 'response': text, 'metadata': text,
    'geometry': obj({
        'raw_axis_order': literal(('y', 'x')), 'precision': positive, 'raw_unit': literal('micrometres / precision'),
        'raw_tick_nm': positive_exact, 'rectangle_proof': text, 'quality': text,
    }),
    'identity': text, 'unknown_structure': text, 'limits': text,
})


def _map(value: Value) -> FrozenMap:
    if not isinstance(value, FrozenMap):
        raise AssertionError('schema-checked object required')
    return value


def _array(value: Value) -> tuple[Value, ...]:
    if not isinstance(value, tuple):
        raise AssertionError('schema-checked array required')
    return value


def _str(value: Value) -> str:
    if not isinstance(value, str):
        raise AssertionError('schema-checked string required')
    return value


def _int(value: Value) -> int:
    if type(value) is not int:
        raise AssertionError('schema-checked integer required')
    return value


def _unique(values: tuple[Value, ...], path: str) -> None:
    # Values passed here have scalar string/integer schemas.
    if len(values) != len(set(values)):
        raise SchemaError(path, 'duplicate declaration', 'DuplicateDeclaration')


def _index(values: Value, key: str, path: str) -> dict[str, FrozenMap]:
    result: dict[str, FrozenMap] = {}
    for index, item in enumerate(_array(values)):
        row = _map(item)
        identity = _str(row[key])
        if identity in result:
            raise SchemaError(f'{path}/{index}/{key}', 'duplicate identity', 'DuplicateDeclaration')
        result[identity] = row
    return result


def validate_payload(doc: FrozenMap, kind: str) -> None:
    try:
        check = SCHEMAS[kind]
    except KeyError as exc:
        raise SchemaError('', f'unsupported document kind: {kind}', 'UnsupportedSchema') from exc
    check(doc, '')
    if kind == 'tech':
        owners = _map(doc['owners'])
        seen_paths: set[str] = set()
        for owner, fields in OWNER_KEYS.items():
            declaration = _map(owners[owner])
            keys = _array(declaration['keys'])
            _unique(keys, f'/owners/{owner}/keys')
            if set(keys) != set(fields):
                raise SchemaError(f'/owners/{owner}/keys', 'owner has missing or foreign fields', 'OwnerConflict')
            path = _str(declaration['path'])
            if path in seen_paths:
                raise SchemaError(f'/owners/{owner}/path', 'owner paths must be unique', 'OwnerConflict')
            seen_paths.add(path)
    elif kind == 'site':
        outputs = _map(doc['outputs'])
        _unique(_array(outputs['core']) + _array(outputs['reports']), '/outputs')
        if not _array(outputs['core']) or not _array(outputs['reports']):
            raise SchemaError('/outputs', 'core outputs and reports must be declared')
    elif kind == 'formats':
        limits = _map(doc['limits'])
        for field, ceiling in (('max_records', 1000), ('max_bytes_per_text_file', 1_000_000), ('max_json_depth', 32)):
            if _int(limits[field]) > ceiling:
                raise SchemaError(f'/limits/{field}', 'profile may tighten but not widen schema ceiling', 'InvalidLimit')
        unit = _map(doc['unit_scale_contract'])
        tick, user = rational(unit['nominal_tick_m']), rational(unit['nominal_user_unit_m'])
        if rational(unit['gds_units_first_nominal']) != tick / user:
            raise SchemaError('/unit_scale_contract/gds_units_first_nominal', 'tick/user unit declarations disagree', 'UnitDeclarationConflict')
        if tick * 1_000_000_000 != _int(unit['canonical_tick_nm']):
            raise SchemaError('/unit_scale_contract/canonical_tick_nm', 'nominal and canonical unit declarations disagree', 'UnitDeclarationConflict')
        suffix = _map(_map(doc['cdl_dialect'])['numeric_suffixes'])
        if rational(suffix['n']) != Fraction(1, 1_000_000_000):
            raise SchemaError('/cdl_dialect/numeric_suffixes/n', 'nano suffix must denote 1e-9 metres', 'UnitDeclarationConflict')
    elif kind == 'physical':
        models = _map(doc['models'])
        if not models:
            raise SchemaError('/models', 'at least one model is required')
        for name, model_value in models.items():
            model = _map(model_value)
            parameters = _array(model['required_parameters'])
            _unique(parameters, f'/models/{name}/required_parameters')
            if set(parameters) != set(_map(model['parameter_axes'])):
                raise SchemaError(f'/models/{name}/required_parameters', 'required parameters must match declared axes', 'ModelDeclarationConflict')
        fin = _map(doc['fin_count_profile'])
        if _int(fin['fin_width_nm']) >= _int(fin['fin_pitch_nm']):
            raise SchemaError('/fin_count_profile', 'fin width must be less than pitch', 'ProfileDeclarationConflict')
        _unique(_array(doc['required_operator_refs']), '/required_operator_refs')
    elif kind == 'rules':
        _index(doc['rules'], 'id', '/rules')
        _validate_rules(doc)
    elif kind == 'export_policy':
        required = _index(doc['required_artifacts'], 'kind', '/required_artifacts')
        optional = _index(doc['optional_artifacts'], 'kind', '/optional_artifacts')
        if set(required) != {'gds', 'cdl', 'json'} or set(required) & set(optional):
            raise SchemaError('/required_artifacts', 'required GDS/CDL/JSON core must be unique and complete')
        names = tuple(row['name'] for row in (*required.values(), *optional.values()))
        _unique(names, '/required_artifacts/name')
    elif kind == 'validation_policy':
        required_checks, deferred_checks = _array(doc['required']), _array(doc['deferred'])
        _unique(required_checks + deferred_checks, '/required')
        _unique(_array(doc['checks']), '/checks')
        _index(doc['check_obligations'], 'check_id', '/check_obligations')
    elif kind == 'header':
        _index(doc['raw'], 'uri', '/raw')
        _index(_map(doc['closure'])['entries'], 'uri', '/closure/entries')
        _index(_map(doc['source_netlist'])['include_library_preprocess_closure'], 'uri', '/source_netlist/include_library_preprocess_closure')
        _unique(_array(_map(doc['query_unit'])['axis_order']), '/query_unit/axis_order')
    elif kind == 'requests':
        requests = _index(doc['requests'], 'path', '/requests')
        all_ids: list[Value] = []
        for path, row in requests.items():
            command = 'DEVICE INFO' if row['capability'] == 'device_regions' else 'NET SHAPES'
            if row['command_intent'] != command:
                raise SchemaError(f'/requests/{path}/command_intent', 'command and capability disagree')
            all_ids.extend(_array(row['record_ids']))
        _unique(tuple(all_ids), '/requests/record_ids')
    elif kind == 'dialect':
        geometry = _map(doc['geometry'])
        if rational(geometry['raw_tick_nm']) != Fraction(1000, _int(geometry['precision'])):
            raise SchemaError('/geometry/raw_tick_nm', 'precision and tick unit disagree', 'UnitDeclarationConflict')


def _validate_rules(doc: FrozenMap) -> None:
    variants: dict[str, tuple[set[str], str, str, str]] = {
        'w003-toy-predicate/T01.frame/1': ({'margin_nm'}, 'geometry_only', 'none', 'w003-toy-rule/1'),
        'w003-toy-predicate/T02.fin_grid/1': (set(), 'geometry_only', 'none', 'w003-toy-rule/1'),
        'w003-toy-predicate/T03.recognition/1': (set(), 'geometry_only', 'none', 'w003-toy-rule/1'),
        'w004-toy-predicate/T04.body/2': ({'active_enclosure_nm'}, 'same_component', 'exact_local_components_plus_bound_context_association', 'w004-toy-rule/2'),
        'w004-toy-predicate/T05.contact_enclosure/2': ({'enclosure_nm'}, 'geometry_only', 'none', 'w004-toy-rule/2'),
        'w003-toy-predicate/T06.li_spacing/1': ({'min_distance_nm'}, 'geometry_only', 'none', 'w003-toy-rule/1'),
        'w003-toy-predicate/T07.m1_spacing/1': ({'min_distance_nm'}, 'geometry_only', 'none', 'w003-toy-rule/1'),
        'w004-toy-predicate/T08.terminal_graph/2': ({'terminal_order'}, 'same_component', 'exact_local_components_plus_bound_context_association', 'w004-toy-rule/2'),
        'w003-toy-predicate/T09.lifecycle/1': ({'ordered_eco_commit_count'}, 'geometry_only', 'none', 'w003-toy-rule/1'),
        'w003-toy-predicate/T10.coverage/1': ({'unknown_nonconductor_policy', 'disconnected_label_policy'}, 'none', 'none', 'w003-toy-rule/1'),
    }
    for index, item in enumerate(_array(doc['rules'])):
        row = _map(item)
        evaluator = _str(row['exact_evaluator_ref'])
        if evaluator not in variants:
            raise SchemaError(f'/rules/{index}/exact_evaluator_ref', 'unsupported rule variant', 'UnsupportedRuleVariant')
        keys, relation, assurance, version = variants[evaluator]
        if set(_map(row['parameters'])) != keys or row['relation_basis'] != relation or row['required_relation_assurance'] != assurance or row['schema_version'] != version:
            raise SchemaError(f'/rules/{index}', 'rule parameters/relation/assurance/version conflict with evaluator variant', 'RuleDeclarationConflict')
        needs_profile = evaluator in ('w003-toy-predicate/T02.fin_grid/1', 'w003-toy-predicate/T03.recognition/1')
        if ('profile_ref' in row) != needs_profile:
            raise SchemaError(f'/rules/{index}/profile_ref', 'rule profile reference missing or inappropriate', 'RuleDeclarationConflict')


def validate_tech_payload(tech: FrozenMap) -> None:
    if set(tech) != set(OWNER_KEYS):
        raise SchemaError('', 'exactly the six declared owners are required', 'OwnerConflict')
    for kind, doc in tech.items():
        if not isinstance(doc, FrozenMap):
            raise SchemaError(f'/{kind}', 'owner must be an object')
        try:
            validate_payload(doc, kind)
        except SchemaError as exc:
            raise SchemaError(f'/{kind}{exc.path}', str(exc), exc.code) from exc
    drawn = _map(tech['drawn'])
    derived = _map(tech['derived'])
    physical = _map(tech['physical'])
    rules = _index(_map(tech['rules'])['rules'], 'id', '/rules/rules')
    layers = _index(drawn['layers'], 'name', '/drawn/layers')
    registry = _index(derived['derived_registry'], 'id', '/derived/derived_registry')
    operators = _map(physical['operators'])
    required = _array(physical['required_operator_refs'])
    body_profile = _map(physical['body_context_profile'])
    body_operator = _str(body_profile['operator_ref'])
    extraction_body = _map(physical['device_extraction_contract'])['body_operator_ref']
    if body_operator != 'body_context/2' or extraction_body != body_operator or body_operator not in required or body_operator not in operators:
        raise SchemaError('/physical/body_context_profile/operator_ref', 'required body operator is unavailable or inconsistent', 'RequiredBodyOperatorUnavailable')
    supported_operators = {'rectangle_set_difference/1', 'same_layer_contact/1', 'cross_layer_contact/1', 'terminal_split/1', 'body_context/2', 'spacing/1', 'lifecycle/1'}
    if set(required) != supported_operators or set(operators) != supported_operators:
        raise SchemaError('/physical/required_operator_refs', 'required operators must resolve to the supported operator set', 'RequiredOperatorUnavailable')
    stream_keys: set[tuple[Value, Value, Value]] = set()
    for name, layer in layers.items():
        stream = _map(layer['stream_key'])
        key = (stream['element'], stream['layer'], stream['datatype'])
        if key in stream_keys:
            raise SchemaError(f'/drawn/layers/{name}/stream_key', 'duplicate stream key', 'LayerMapConflict')
        stream_keys.add(key)
        if _int(stream['layer']) > 32767 or _int(stream['datatype']) > 32767:
            raise SchemaError(f'/drawn/layers/{name}/stream_key', 'stream key exceeds signed GDS INT2 range')
        references = _array(layer['derived_layer_refs'])
        _unique(references, f'/drawn/layers/{name}/derived_layer_refs')
        for ref in references:
            target = registry.get(_str(ref))
            if target is None or target['target_layer'] != name:
                raise SchemaError(f'/drawn/layers/{name}/derived_layer_refs', 'derived reference missing or points to another layer', 'LayerMapConflict')
        role = layer['role']
        connector_fields = {'electrical_connects', 'contact_predicate', 'enclosure_rule'}
        cut_fields = {'cut_target', 'effective_geometry_operator'}
        if role in ('contact', 'via', 'body_contact'):
            if not connector_fields <= set(layer):
                raise SchemaError(f'/drawn/layers/{name}', 'connector declaration is incomplete')
            pair = _array(layer['electrical_connects'])
            _unique(pair, f'/drawn/layers/{name}/electrical_connects')
            if any(_str(ref) not in layers for ref in pair):
                raise SchemaError(f'/drawn/layers/{name}/electrical_connects', 'unknown conductor layer', 'LayerMapConflict')
            if _str(layer['enclosure_rule']) not in rules:
                raise SchemaError(f'/drawn/layers/{name}/enclosure_rule', 'unknown rule', 'RuleDeclarationConflict')
        elif connector_fields & set(layer):
            raise SchemaError(f'/drawn/layers/{name}', 'connector fields on nonconnector layer')
        if role == 'cut':
            if not cut_fields <= set(layer) or _str(layer['cut_target']) not in layers or layer['effective_geometry_operator'] not in operators:
                raise SchemaError(f'/drawn/layers/{name}', 'cut target/operator reference invalid', 'LayerMapConflict')
        elif cut_fields & set(layer):
            raise SchemaError(f'/drawn/layers/{name}', 'cut fields on noncut layer')
    for name, item in registry.items():
        target = layers.get(_str(item['target_layer']))
        if target is None or name not in _array(target['derived_layer_refs']):
            raise SchemaError(f'/derived/derived_registry/{name}/target_layer', 'derived/drawn references must agree in both directions', 'LayerMapConflict')
        _unique(_array(item['carries']), f'/derived/derived_registry/{name}/carries')
    models = _map(physical['models'])
    body_types = _map(body_profile['types'])
    if set(body_types) != set(models):
        raise SchemaError('/physical/body_context_profile/types', 'body type model references must match model registry', 'ModelDeclarationConflict')
    for model, pair_value in body_types.items():
        body, tap = _array(pair_value)
        if _str(body) not in layers or _str(tap) not in layers:
            raise SchemaError(f'/physical/body_context_profile/types/{model}', 'unknown body/tap layer', 'LayerMapConflict')
        if layers[_str(body)]['role'] != 'body' or layers[_str(tap)]['role'] != 'body_contact':
            raise SchemaError(f'/physical/body_context_profile/types/{model}', 'body/tap declaration has incompatible layer roles', 'LayerMapConflict')
