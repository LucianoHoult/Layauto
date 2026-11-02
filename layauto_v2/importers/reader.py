"""Read and bind the supported synthetic input subset, without a pipeline."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from collections.abc import Generator
from typing import NoReturn

from layauto_v2.domain.acquisition import AcquisitionRequest, AcquisitionResponse
from layauto_v2.domain.codec import FrozenMap, Value, canonical_bytes, freeze_map
from layauto_v2.domain.evidence import EvidenceRecord, SourceFile, SourceRef
from layauto_v2.domain.results import EvidenceIssue, InputError, ParseResult
from ._access import exact, integer, mapping, sequence, string
from .calibre import parse_query
from .cdl import parse_cdl
from .config import load_document, validate_document, validate_tech
from .gds import parse_gds

_OWNERS = ('drawn', 'derived', 'physical', 'formats', 'coordinate', 'rules')
_CAPABILITIES = ('instance_xref', 'net_xref', 'device_regions', 'net_regions')


def _resolve(path: Path) -> Path:
    try:
        return path.resolve()
    except RuntimeError as exc:
        # Python 3.10/3.12 pathlib uses RuntimeError for a filesystem symlink loop.
        # Preserve unrelated unexpected exceptions, including injected failures.
        if not str(exc).startswith('Symlink loop from '):
            raise
        raise OSError(str(exc)) from exc


class _Files:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.files: dict[Path, SourceFile] = {}

    def path(self, uri: str) -> Path:
        try:
            if '\x00' in uri:
                raise ValueError('embedded NUL in input path')
            return _resolve(self.root / uri)
        except (ValueError, OSError) as exc:
            raise InputError('read', 'InvalidInputPath', str(exc), SourceRef(uri, field='path')) from exc

    def read(self, uri: str, *, missing_code: str = 'MissingInput') -> Generator[AcquisitionRequest, AcquisitionResponse, SourceFile]:
        path = self.path(uri)
        if path in self.files:
            return self.files[path]
        response = yield AcquisitionRequest(str(path), uri, missing_code=missing_code)
        if isinstance(response, EvidenceIssue):
            raise InputError(response.category, response.code, response.message, response.source)
        if not isinstance(response, SourceFile) or response.uri != uri:
            raise ValueError('acquisition driver returned an invalid source')
        self.files[path] = response
        return response

    def probe(self, path: Path) -> Generator[AcquisitionRequest, AcquisitionResponse, bool]:
        response = yield AcquisitionRequest(str(path), str(path), 'probe', 'InputReadError')
        if isinstance(response, EvidenceIssue):
            raise InputError(response.category, response.code, response.message, response.source)
        if type(response) is not bool:
            raise ValueError('acquisition driver returned an invalid probe')
        return response


def _doc(source: SourceFile, kind: str, max_bytes: int = 1_000_000,
         max_depth: int = 32) -> FrozenMap:
    value = load_document(source, max_bytes=max_bytes, max_depth=max_depth)
    validate_document(value, kind, source)
    return value


def _fail(source: SourceFile, code: str, message: str, field: str) -> NoReturn:
    raise InputError('binding', code, message, source.ref(field=field))


def _plain(value: Value) -> object:
    if isinstance(value, FrozenMap):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_plain(v) for v in value]
    if value is None or isinstance(value, (str, bool, int)):
        return value
    raise ValueError('manifest has a non-JSON value')


def _manifest_digest(value: Value) -> str:
    data = json.dumps(_plain(value), sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')
    return hashlib.sha256(data).hexdigest()


def _binding(files: _Files, declaration: FrozenMap, actual: SourceFile,
             header_file: SourceFile, field: str, code: str = 'InputBindingMismatch') -> None:
    if files.path(string(declaration['uri'])) != files.path(actual.uri):
        _fail(header_file, code, f'{field} selects a different file', field + '/uri')
    if declaration['sha256'] != actual.sha256:
        _fail(header_file, code, f'{field} SHA-256 differs from actual bytes: {actual.uri}', field + '/sha256')


def _header_status(header: FrozenMap, source: SourceFile, site: FrozenMap,
                   tech: FrozenMap) -> None:
    for name, expected in (('mode', site['mode']), ('classification', 'synthetic'),
                           ('assurance', 'synthetic'), ('hierarchy_mode', 'flat')):
        if header[name] != expected:
            _fail(source, 'EvidenceStatusConflict', f'invalid synthetic {name}', '/' + name)
    tool = mapping(header['tool'])
    if tool['executed'] is not False or tool['name'] is not None or tool['version'] is not None:
        _fail(source, 'EvidenceStatusConflict', 'dummy fixture cannot claim tool execution', '/tool')
    if header['query_database_id'] is not None or not header['query_database_absence_reason']:
        _fail(source, 'EvidenceStatusConflict', 'synthetic input must preserve database absence', '/query_database_id')
    completion, match = header['lvs_completion_status'], header['lvs_match_status']
    if (completion, match) not in (('not_run', 'not_run'), ('unknown', 'unknown')):
        _fail(source, 'EvidenceStatusConflict', 'synthetic LVS status conflicts with acquisition', '/lvs_match_status')
    if header['query_dialect_version'] != 'calibre_like_synthetic/2' or header['parser_contract_version'] != 'w004-query-normalized/2':
        _fail(source, 'ParserVersionMismatch', 'unsupported query dialect/parser contract', '/parser_contract_version')
    # The capture producer did not run a product parser. This component records its own version.
    if header['product_parser_version'] is not None:
        _fail(source, 'ParserVersionMismatch', 'capture cannot claim a product parser execution', '/product_parser_version')
    unit = mapping(header['query_unit'])
    if (unit['name'] != 'micrometres/precision' or unit['geometry_precision'] != 20000
            or unit['axis_order'] != ('y', 'x') or exact(unit['metres_per_unit']) != exact(mapping(mapping(tech['formats'])['unit_scale_contract'])['nominal_user_unit_m'])):
        _fail(source, 'UnitBindingMismatch', 'query unit declaration conflicts with dialect', '/query_unit')
    if header['geometry_unit_contract'] != mapping(mapping(tech['formats'])['unit_scale_contract'])['id']:
        _fail(source, 'UnitBindingMismatch', 'geometry unit contract mismatch', '/geometry_unit_contract')
    if not header['header_id'] or not header['query_run_id']:
        _fail(source, 'EvidenceStatusConflict', 'missing header or query run identity', '/query_run_id')


def _body(body: FrozenMap, body_file: SourceFile, files: _Files, gds_file: SourceFile,
          top: str, tech: FrozenMap) -> None:
    _binding(files, mapping(body['source_gds']), gds_file, body_file, '/source_gds', 'BodySourceBindingMismatch')
    if body['top'] != top:
        _fail(body_file, 'BodySourceBindingMismatch', 'body top differs from GDS', '/top')
    physical = mapping(tech['physical'])
    profile = mapping(physical['body_context_profile'])
    if body['profile_ref'] != profile['id'] or body['operator_ref'] != profile['operator_ref']:
        _fail(body_file, 'BodyProfileBindingMismatch', 'body profile/operator mismatch', '/profile_ref')
    unit = mapping(body['unit'])
    nominal = mapping(mapping(tech['formats'])['unit_scale_contract'])['nominal_tick_m']
    if unit['name'] != 'nm' or exact(unit['metres_per_tick']) != exact(nominal):
        _fail(body_file, 'UnitBindingMismatch', 'body unit differs from source nominal unit', '/unit')
    if (body['classification'] != 'synthetic' or body['read_only'] is not True or body['exported'] is not False
            or body['production_matched_body_evidence'] is not False or body['lvs_status'] not in ('not_run', 'unknown')):
        _fail(body_file, 'EvidenceStatusConflict', 'invalid synthetic body status', '/classification')
    if body['coordinate_frame'] != 'source local frame; identity transform':
        _fail(body_file, 'BodyProfileBindingMismatch', 'unsupported body transform', '/coordinate_frame')
    layer_roles = {string(mapping(x)['name']): string(mapping(x)['role']) for x in sequence(mapping(tech['drawn'])['layers'])}
    local: dict[str, FrozenMap] = {}
    external: dict[str, FrozenMap] = {}
    ids: set[str] = set()
    for key, dest in (('local_bindings', local), ('shapes', external)):
        for index, entry in enumerate(sequence(body[key])):
            shape = mapping(entry)
            identity = string(shape['id'])
            if identity in ids or shape['layer'] not in layer_roles:
                _fail(body_file, 'BodyReferenceMismatch', 'duplicate id or unknown declared layer', f'/{key}/{index}')
            ids.add(identity)
            dest[identity] = shape
    frame = string(body['frame_id'])
    if frame not in local or local[frame]['bbox'] != body['frame_bbox_nm'] or layer_roles[string(local[frame]['layer'])] != 'boundary':
        _fail(body_file, 'BodyReferenceMismatch', 'frame reference is not internally consistent', '/frame_id')
    devices: set[str] = set()
    for i, entry in enumerate(sequence(body['associations'])):
        association = mapping(entry)
        device = string(association['device'])
        if device in devices:
            _fail(body_file, 'BodyReferenceMismatch', 'duplicate body association', f'/associations/{i}/device')
        devices.add(device)
        for field in ('local_body', 'local_rail'):
            if association[field] not in local:
                _fail(body_file, 'BodyReferenceMismatch', 'dangling local context reference', f'/associations/{i}/{field}')
        for field in ('external_body', 'external_rail', 'tap'):
            if association[field] not in external:
                _fail(body_file, 'BodyReferenceMismatch', 'dangling external context reference', f'/associations/{i}/{field}')
        for field, role, table in (('local_body', 'body', local), ('external_body', 'body', external),
                                   ('tap', 'body_contact', external), ('local_rail', 'interconnect', local),
                                   ('external_rail', 'interconnect', external)):
            shape = table[string(association[field])]
            if layer_roles[string(shape['layer'])] != role:
                _fail(body_file, 'BodyReferenceTypeMismatch', 'context reference has an incompatible declared role', f'/associations/{i}/{field}')


class InputParser:
    """Incremental parser; the orchestrator supplies each requested capture.

    The completed snapshot survives unexpected exceptions for boundary diagnostics.
    This object is an in-flight session, never a published record.
    """
    def __init__(self, site_path: Path, *, tool_run_id: str | None = None) -> None:
        self.site_path = site_path
        self.tool_run_id = tool_run_id
        self.input_root: str | None = None
        self._completed: list[EvidenceRecord] = []
        self.requests = _parse_inputs(self)

    @property
    def completed(self) -> tuple[EvidenceRecord, ...]:
        return tuple(self._completed)


def _parse_inputs(session: InputParser) -> Generator[AcquisitionRequest, AcquisitionResponse, ParseResult]:
    requested = Path(session.site_path)
    tool_run_id = session.tool_run_id
    try:
        if '\x00' in str(requested):
            raise ValueError('embedded NUL in site path')
        site_path = _resolve(requested)
    except (ValueError, OSError) as exc:
        issue = InputError('read', 'InvalidInputPath', str(exc), SourceRef(str(requested), field='path')).issue
        return ParseResult('error', None, (issue,), (), (), tool_run_id)
    files = _Files(site_path.parent)
    session.input_root = str(site_path.parent)
    completed = session._completed

    def record(kind: str, payload: FrozenMap, *sources: SourceFile) -> None:
        completed.append(EvidenceRecord(kind, payload, tuple(s.ref() for s in sources)))

    try:
        site_file = yield from files.read(site_path.name)
        site = _doc(site_file, 'site')
        record('config', site, site_file)
        tech_file = yield from files.read(string(site['tech_ref']))
        tech_root = _doc(tech_file, 'tech')
        owners = mapping(tech_root['owners'])
        owner_sources: dict[str, SourceFile] = {}
        owner_data: dict[str, object] = {}
        paths: set[Path] = set()
        owned: set[str] = set()
        for name in _OWNERS:
            declaration = mapping(owners[name])
            owner_path = string(declaration['path'])
            if files.path(owner_path) in paths:
                _fail(tech_file, 'OwnerConflict', 'owner paths must be distinct', f'/owners/{name}/path')
            paths.add(files.path(owner_path))
            source = yield from files.read(owner_path)
            owner_sources[name] = source
            document = _doc(source, name)
            keys = tuple(string(x) for x in sequence(declaration['keys']))
            if len(set(keys)) != len(keys) or set(keys) & owned or set(keys) != set(document) - {'schema_version'}:
                _fail(tech_file, 'OwnerConflict', 'owner key declaration is duplicated or inconsistent', f'/owners/{name}/keys')
            owned.update(keys)
            owner_data[name] = document
        tech = freeze_map(owner_data)
        validate_tech(tech, owner_sources)
        limits = mapping(mapping(tech['formats'])['limits'])
        max_bytes, max_depth = integer(limits['max_bytes_per_text_file']), integer(limits['max_json_depth'])
        # Reapply profile limits to bootstrap documents as well.
        for source in (site_file, tech_file, *owner_sources.values()):
            load_document(source, max_bytes=max_bytes, max_depth=max_depth)
        record('tech', freeze_map({'bundle': tech_root, 'owners': tech}), tech_file, *owner_sources.values())
        policies: dict[str, object] = {}
        policy_sources: list[SourceFile] = []
        for kind, key in (('export_policy', 'export_policy_ref'), ('validation_policy', 'validation_policy_ref'), ('limitations', 'limitation_ref')):
            source = yield from files.read(string(site[key]))
            policies[kind] = _doc(source, kind, max_bytes, max_depth)
            policy_sources.append(source)
        policy = freeze_map(policies)
        export = mapping(policy['export_policy'])
        outputs = mapping(site['outputs'])
        artifact_names = tuple(mapping(x)['name'] for x in sequence(export['required_artifacts']))
        if outputs['directory'] != export['output_directory'] or outputs['core'] != artifact_names:
            _fail(policy_sources[0], 'OutputPolicyMismatch', 'duplicate output declarations differ', '/outputs')
        if export['profile_id'] != tech_root['profile_id'] or export['unit_equivalence_contract'] != mapping(mapping(tech['formats'])['unit_scale_contract'])['id'] or export['cdl_dialect'] != mapping(mapping(tech['formats'])['cdl_dialect'])['id']:
            _fail(policy_sources[0], 'PolicyProfileMismatch', 'export policy disagrees with selected tech', '/profile_id')
        record('policies', policy, *policy_sources)
        inputs = mapping(site['inputs'])
        gds_file = yield from files.read(string(inputs['gds']))
        source_file = yield from files.read(string(inputs['source_cdl']))
        target_file = yield from files.read(string(inputs['target_cdl']))
        header_file = yield from files.read(string(inputs['query_header']))
        header = _doc(header_file, 'header', max_bytes, max_depth)
        body_file = yield from files.read(string(inputs['body_context']), missing_code='RequiredBodyContextUnavailable')
        body = _doc(body_file, 'body', max_bytes, max_depth)
        _header_status(header, header_file, site, tech)
        if files.path(string(header['limitations_ref'])) != files.path(policy_sources[2].uri):
            _fail(header_file, 'InputBindingMismatch', 'limitations selection differs', '/limitations_ref')
        for key, source in (('layout', gds_file), ('source_netlist', source_file), ('target', target_file)):
            _binding(files, mapping(header[key]), source, header_file, '/' + key)
        netlist = mapping(header['source_netlist'])
        if netlist['include_library_preprocess_closure'] != () or netlist['preprocess'] != 'none' or netlist['empty_closure_sha256'] != _manifest_digest(()):
            _fail(header_file, 'DependencyClosureMismatch', 'selected literal dialect requires an explicitly bound empty closure', '/source_netlist')
        # Snapshot the selected required files before discovering the two query documents.
        required = set(files.files) - {files.path(header_file.uri)}
        closure = mapping(header['closure'])
        entries = sequence(closure['entries'])
        seen: set[Path] = set()
        uris: list[str] = []
        query_docs: dict[str, SourceFile] = {}
        for index, item in enumerate(entries):
            entry = mapping(item)
            uri = string(entry['uri'])
            path = files.path(uri)
            if path in seen:
                _fail(header_file, 'DuplicateBinding', 'duplicate closure file binding', f'/closure/entries/{index}')
            seen.add(path)
            uris.append(uri)
            source = yield from files.read(uri)
            _binding(files, entry, source, header_file, f'/closure/entries/{index}', 'ClosureHashMismatch')
            if path not in required:
                document = load_document(source, max_bytes=max_bytes, max_depth=max_depth)
                version = document.get('schema_version')
                query_kind = {'w004-query-requests/2': 'requests', 'w004-calibre-like-dialect/2': 'dialect'}.get(str(version))
                if query_kind is None or query_kind in query_docs:
                    _fail(header_file, 'DependencyClosureMismatch', 'unknown or duplicate closure dependency', f'/closure/entries/{index}')
                validate_document(document, query_kind, source)
                query_docs[query_kind] = source
        if not required <= seen or set(query_docs) != {'requests', 'dialect'}:
            _fail(header_file, 'DependencyClosureMismatch', 'closure omits selected required files or query contracts', '/closure/entries')
        if uris != sorted(uris) or closure['sha256'] != _manifest_digest(entries):
            _fail(header_file, 'ClosureHashMismatch', 'closure digest/order mismatch', '/closure/sha256')
        raw: list[SourceFile] = []
        raw_paths: set[Path] = set()
        capabilities: set[str] = set()
        for index, item in enumerate(sequence(header['raw'])):
            entry = mapping(item)
            path = files.path(string(entry['uri']))
            if path in raw_paths or path in seen or path == files.path(header_file.uri):
                _fail(header_file, 'DuplicateBinding', 'duplicate raw/dependency binding', f'/raw/{index}')
            raw_paths.add(path)
            capabilities.add(string(entry['capability']))
            source = yield from files.read(string(entry['uri']))
            if len(source.data) > max_bytes:
                raise InputError('parse', 'SizeLimitExceeded', 'raw text exceeds selected limit', source.ref())
            _binding(files, entry, source, header_file, f'/raw/{index}', 'RawHashMismatch')
            raw.append(source)
        if capabilities != set(_CAPABILITIES):
            _fail(header_file, 'MissingCapability', 'raw list lacks required capabilities', '/raw')
        record('header', header, header_file)
        gds = parse_gds(gds_file, tech)
        record('gds', gds, gds_file)
        source_cdl = parse_cdl(source_file, tech)
        record('source_cdl', source_cdl, source_file)
        target_cdl = parse_cdl(target_file, tech)
        record('target_cdl', target_cdl, target_file)
        top = string(gds['top'])
        identities = mapping(header['top_identities'])
        source_tops = {string(mapping(x)['name']) for x in sequence(source_cdl['tops'])}
        if identities['layout'] != top or identities['source'] not in source_tops:
            _fail(header_file, 'TopBindingMismatch', 'header top does not match source documents', '/top_identities')
        _body(body, body_file, files, gds_file, top, tech)
        record('body', body, body_file, gds_file)
        query = parse_query(tuple(raw), header, query_docs['requests'], query_docs['dialect'], tech,
                            derived_source=owner_sources['derived'])
        record('query', query, header_file, query_docs['requests'], query_docs['dialect'], *raw)
        # This captured dialect defines optional cache paths relative to the selected header.
        cache_dir = files.path(header_file.uri).parent / 'normalized'
        for capability in _CAPABILITIES:
            path = cache_dir / (capability + '.yaml')
            cache_present = yield from files.probe(path)
            if cache_present:
                source = yield from files.read(str(path))
                cache = load_document(source, max_bytes=max_bytes, max_depth=max_depth)
                if canonical_bytes(cache) != canonical_bytes(query[capability]):
                    _fail(source, 'NormalizedCacheMismatch', 'cache differs from reparsed raw evidence', '/')
        value = freeze_map({'config': site, 'tech': tech, 'tech_bundle': tech_root,
                            'gds': gds, 'source_cdl': source_cdl, 'target_cdl': target_cdl,
                            'query': query, 'body': body, 'header': header, 'policies': policy})
        return ParseResult('success', value, (), tuple(completed), tuple(files.files.values()), tool_run_id)
    except InputError as exc:
        return ParseResult('error', None, (exc.issue,), tuple(completed), tuple(files.files.values()), tool_run_id)


def _component_acquire(request: AcquisitionRequest) -> AcquisitionResponse:
    try:
        path = Path(request.path)
        if request.operation == 'probe':
            return path.exists()
        return SourceFile(request.uri, path.read_bytes())
    except OSError as exc:
        return EvidenceIssue('read', request.missing_code, str(exc), SourceRef(request.uri))


def read_inputs(site_path: Path, *, tool_run_id: str | None = None) -> ParseResult:
    """W005 component facade; unexpected exceptions and interrupts propagate.

    The same incremental parser is used by the run-aware pipeline. This facade
    owns no run or terminal lifecycle and preserves its original public API.
    """
    parser = InputParser(site_path, tool_run_id=tool_run_id)
    try:
        request = next(parser.requests)
    except StopIteration as done:
        result: ParseResult = done.value
        return result
    while True:
        response = _component_acquire(request)
        try:
            request = parser.requests.send(response)
        except StopIteration as done:
            result = done.value
            return result
