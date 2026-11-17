"""Independent local acquisition; no target, export, validation or body reads."""
from __future__ import annotations
from pathlib import Path
from collections.abc import Generator
from layauto_v2.domain.acquisition import AcquisitionRequest, AcquisitionResponse
from layauto_v2.domain.analysis import LocalAnalysisEvidence
from layauto_v2.domain.codec import FrozenMap, canonical_bytes, freeze_map
from layauto_v2.domain.evidence import EvidenceRecord, SourceFile
from layauto_v2.domain.results import InputError, EvidenceIssue
from layauto_v2.tech.analysis_schema import validate_analysis_payload
from layauto_v2.tech.schema import SchemaError
from ._access import mapping, sequence, string, integer
from .config import load_document, validate_document, validate_tech
from .gds import parse_gds
from .cdl import parse_cdl
from .calibre import parse_query
from .reader import (_Files, _doc, _fail, _binding, _header_status, _manifest_digest,
                     _OWNERS, _CAPABILITIES, _component_acquire)

class AnalysisFiles(_Files):
    def __init__(self, root: Path) -> None:
        super().__init__(root)
        self.probes: dict[str, bool] = {}

    def probe(self, path: Path) -> Generator[AcquisitionRequest, AcquisitionResponse, bool]:
        present = yield from super().probe(path)
        self.probes[str(path)] = present
        return present


class _CapturedFiles(AnalysisFiles):
    lookup: dict[str, Path]

    def path(self, uri: str) -> Path:
        # Never resolve symlinks again: this is the acquisition-time alias table.
        if uri not in self.lookup:
            raise ValueError('analysis alias is missing from acquisition facts')
        self.paths[uri] = self.lookup[uri]
        return self.lookup[uri]


def captured_analysis_files(root: str, aliases: FrozenMap) -> AnalysisFiles:
    """Pure acquisition-time path replay. Never resolve or read the filesystem."""
    if type(root) is not str or not Path(root).is_absolute():
        raise ValueError('captured analysis root requires an absolute native path')
    if any(type(path) is not str or not Path(path).is_absolute() for path in aliases.values()):
        raise ValueError('captured analysis aliases require absolute native paths')
    files = _CapturedFiles(Path(root))
    files.lookup = {uri: Path(str(path)) for uri, path in aliases.items()}
    return files


def _analysis_doc(source: SourceFile, kind: str, max_bytes: int = 1_000_000,
                  max_depth: int = 32) -> FrozenMap:
    doc = load_document(source, max_bytes=max_bytes, max_depth=max_depth)
    if kind == 'analysis_header' and doc.get('schema_version') == 'w004-query-header/2':
        raise InputError('unsupported', 'LegacyFullHeaderRequiresExplicitMigration',
                         'legacy full header requires explicit synthetic migration', source.ref())
    if kind in ('analysis_header', 'analysis_manifest'):
        expected = 'layauto-analysis-query-header/1' if kind == 'analysis_header' else 'layauto-cell-analysis-request/1'
        if doc.get('schema_version') not in (None, expected):
            raise InputError('unsupported', 'UnsupportedAnalysisSchemaVersion', 'unsupported independent analysis schema version', source.ref(field='/schema_version'))
    try:
        validate_analysis_payload(doc, kind)
    except SchemaError as exc:
        raise InputError('config', exc.code, str(exc), source.ref(field=exc.path)) from exc
    return doc


def parse_analysis(files: AnalysisFiles, manifest_uri: str) -> Generator[AcquisitionRequest, AcquisitionResponse, LocalAnalysisEvidence]:
    completed: list[EvidenceRecord] = []
    def record(kind: str, payload: FrozenMap, *sources: SourceFile) -> None:
        completed.append(EvidenceRecord(kind, payload, tuple(s.ref() for s in sources)))
    try:
        site_file = yield from files.read(manifest_uri)
        site = _analysis_doc(site_file, 'analysis_manifest')
        record('config', site, site_file)
        if site['purpose'] != 'local_readonly' or site['mode'] != 'dummy_fixture':
            raise InputError('unsupported', 'UnsupportedAnalysisPurpose' if site['purpose'] != 'local_readonly' else 'UnsupportedAnalysisMode',
                             'only synthetic local read-only analysis is supported', site_file.ref())
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
        limitation_file = yield from files.read(string(site['limitation_ref']))
        limitations = _doc(limitation_file, 'limitations', max_bytes, max_depth)
        record('limitations', limitations, limitation_file)
        inputs = mapping(site['inputs'])
        gds_file = yield from files.read(string(inputs['gds']))
        source_file = yield from files.read(string(inputs['source_cdl']))
        header_file = yield from files.read(string(inputs['query_header']))
        header = _analysis_doc(header_file, 'analysis_header', max_bytes, max_depth)
        _header_status(header, header_file, site, tech)
        if files.path(string(header['limitations_ref'])) != files.path(limitation_file.uri):
            _fail(header_file, 'InputBindingMismatch', 'limitations selection differs', '/limitations_ref')
        for key, source in (('layout', gds_file), ('source_netlist', source_file)):
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
        top = string(gds['top'])
        identities = mapping(header['top_identities'])
        source_tops = {string(mapping(x)['name']) for x in sequence(source_cdl['tops'])}
        if identities['layout'] != top or identities['source'] not in source_tops:
            _fail(header_file, 'TopBindingMismatch', 'header top does not match source documents', '/top_identities')
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
                            'gds': gds, 'source_cdl': source_cdl,
                            'query': query, 'header': header, 'limitations': limitations})
        return LocalAnalysisEvidence(str(files.root), manifest_uri, tuple(files.files.values()),
                                     freeze_map({k: str(v) for k, v in files.paths.items()}),
                                     freeze_map(files.probes), tuple(completed), value)
    except InputError as exc:
        return LocalAnalysisEvidence(str(files.root), manifest_uri, tuple(files.files.values()),
                                     freeze_map({k: str(v) for k, v in files.paths.items()}),
                                     freeze_map(files.probes), tuple(completed), None, (exc.issue,))


def acquire_analysis(path: Path) -> LocalAnalysisEvidence:
    files = AnalysisFiles(path.parent)
    parser = parse_analysis(files, path.name)
    try:
        request = next(parser)
        while True:
            request = parser.send(_component_acquire(request))
    except StopIteration as done:
        result: LocalAnalysisEvidence = done.value
        return result


def acquire_selections(evidence: LocalAnalysisEvidence) -> tuple[
        tuple[SourceFile, ...], SourceFile | None, SourceFile | None,
        tuple[EvidenceIssue, ...], FrozenMap]:
    """Acquire selected external bytes once, independently from the local closure.

    Unsupported kinds are never opened. Parsing/authentication is owned by
    normalization and cannot add external shapes to the local capture scope.
    """
    files = AnalysisFiles(Path(evidence.root))
    files.paths = {uri: Path(str(path)) for uri, path in evidence.aliases.items()}
    files.files = {files.path(source.uri): source for source in evidence.captures}
    selected: list[SourceFile | None] = []
    issues: list[EvidenceIssue] = []
    config = None if evidence.value is None else mapping(evidence.value['config'])
    for field, kind in (('external_body', 'synthetic_context'), ('manual_intent', 'declaration')):
        selection = None if config is None else config.get(field)
        if not isinstance(selection, FrozenMap) or selection['kind'] != kind:
            selected.append(None)
            continue
        parser = files.read(string(selection['uri']), missing_code='SelectedBodyUnavailable' if field == 'external_body' else 'SelectedManualUnavailable')
        try:
            try:
                request = next(parser)
                while True:
                    request = parser.send(_component_acquire(request))
            except StopIteration as done:
                selected.append(done.value)
                try:
                    doc = load_document(done.value)
                except InputError as exc:
                    issues.append(exc.issue)
                else:
                    for key in ('source_gds', 'source_layout', 'source_netlist'):
                        declaration = doc.get(key)
                        if isinstance(declaration, FrozenMap) and isinstance(declaration.get('uri'), str):
                            try:
                                files.path(string(declaration['uri']))
                            except InputError as exc:
                                issues.append(EvidenceIssue(exc.issue.category, exc.issue.code, exc.issue.message,
                                    done.value.ref(field='/' + key + '/uri')))

        except InputError as exc:
            issues.append(exc.issue)
            selected.append(None)
    return (tuple(files.files.values()), selected[0], selected[1], tuple(issues),
            freeze_map({uri: str(path) for uri, path in files.paths.items()}))
