"""Closed immutable contracts for the semantic normalization component."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .codec import FrozenMap, canonical_bytes, freeze_map, rational
from .evidence import SourceRef
from .results import ParseResult
from .publication import InputsReady, InputCheckpoint, ParseAudit, ToolRunResult, EvidenceAudit
from .publication_codec import content_ref
from .identifiers import DeviceId, NetId, QueryKey
from .circuit import SemanticCircuitDraft, TargetCircuit
from .intent import TargetDifference, build_differences
from ._normalization_input import mapping, sequence, string, source_refs, validate_parse, validate_refs

VERSION = 'layauto-normalization/1'


def _tuple(owner: object, name: str, cls: type[object]) -> None:
    value = getattr(owner, name)
    if not isinstance(value, (tuple, list)) or any(type(item) is not cls for item in value):
        raise ValueError('invalid ' + name)
    object.__setattr__(owner, name, tuple(value))


def _version(version: str) -> None:
    if version != VERSION:
        raise ValueError('unsupported normalization schema version')


@dataclass(frozen=True)
class ReadbackBinding:
    ready: InputsReady
    checkpoint: InputCheckpoint
    parse_audit: ParseAudit
    tool_run: ToolRunResult
    evidence_audits: tuple[EvidenceAudit, ...]
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        _version(self.schema_version)
        if (type(self.ready) is not InputsReady or type(self.checkpoint) is not InputCheckpoint
                or type(self.parse_audit) is not ParseAudit or type(self.tool_run) is not ToolRunResult):
            raise ValueError('invalid normalization readback records')
        _tuple(self, 'evidence_audits', EvidenceAudit)
        ready, checkpoint, parse, tool = self.ready, self.checkpoint, self.parse_audit, self.tool_run
        if (content_ref(checkpoint) != ready.checkpoint_ref or content_ref(parse) != ready.parse_ref
                or content_ref(tool) != ready.tool_ref
                or tuple(content_ref(record) for record in self.evidence_audits) != ready.evidence_refs):
            raise ValueError('readback content does not match ready references')
        if (checkpoint.run_id != ready.run_id or checkpoint.revision != ready.attempt.revision
                or checkpoint.outcome != 'inputs_ready' or checkpoint.tool_ref != ready.tool_ref
                or checkpoint.parse_ref != ready.parse_ref or checkpoint.evidence_refs != ready.evidence_refs
                or checkpoint.ready_value != ready.value or parse.result.value != ready.value):
            raise ValueError('readback checkpoint/value differs from ready attempt')
        if (parse.run_id != ready.run_id or tool.run_id != ready.run_id or parse.tool_ref != ready.tool_ref
                or parse.result.tool_run_id != tool.tool_run_id or tool.execution_status != 'completed'):
            raise ValueError('readback run/tool association differs')
        if canonical_bytes(tuple((s.uri, s.data) for s in parse.result.sources)) != canonical_bytes(tuple((s.uri, s.data) for s in tool.sources)):
            raise ValueError('readback tool and parse captured sources differ')
        if tuple(record.evidence for record in self.evidence_audits) != parse.result.completed:
            raise ValueError('readback evidence is not the completed parse evidence')
        if any(record.run_id != ready.run_id or record.tool_ref != ready.tool_ref
               or record.parse_ref != ready.parse_ref for record in self.evidence_audits):
            raise ValueError('readback evidence belongs to another run/parse')


@dataclass(frozen=True)
class NormalizationInput:
    parse: ParseResult
    readback: ReadbackBinding | None = None
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        _version(self.schema_version)
        try:
            validate_parse(self.parse)
        except (KeyError, TypeError, AttributeError, UnicodeError, IndexError) as exc:
            raise ValueError('invalid captured normalization input fields') from exc
        if self.readback is not None:
            if type(self.readback) is not ReadbackBinding or self.readback.parse_audit.result != self.parse:
                raise ValueError('input parse is not the bound readback parse')

    @property
    def value(self) -> FrozenMap:
        assert self.parse.value is not None
        return self.parse.value


@dataclass(frozen=True)
class NormalizationIssue:
    category: Literal['unsupported', 'identity', 'binding']
    code: str
    message: str
    source: SourceRef
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        _version(self.schema_version)
        if self.category not in ('unsupported', 'identity', 'binding'):
            raise ValueError('invalid normalization issue category')
        string(self.code)
        string(self.message)
        if type(self.source) is not SourceRef or self.source.sha256 is None:
            raise ValueError('normalization issue must locate captured evidence')


@dataclass(frozen=True)
class DeviceIdentity:
    device_id: DeviceId
    query_key: QueryKey
    sd_swap: bool
    provenance: FrozenMap

    def __post_init__(self) -> None:
        if type(self.device_id) is not DeviceId or type(self.query_key) is not QueryKey or self.query_key.kind != 'device' or type(self.sd_swap) is not bool:
            raise ValueError('invalid device identity association')
        object.__setattr__(self, 'provenance', freeze_map(self.provenance))
        if (set(self.provenance) != {'layout_instance', 'schematic_instance', 'sd_swap', 'field_sources'}
                or self.provenance['layout_instance'] != self.query_key.identity
                or self.provenance['schematic_instance'] != self.device_id.name
                or self.provenance['sd_swap'] != self.sd_swap
                or set(mapping(self.provenance['field_sources'])) != {'layout_instance', 'schematic_instance', 'sd_swap'}
                or not source_refs(self.provenance)):
            raise ValueError('device identity disagrees with its captured association')


@dataclass(frozen=True)
class NetIdentity:
    net_id: NetId
    query_key: QueryKey
    provenance: FrozenMap

    def __post_init__(self) -> None:
        if type(self.net_id) is not NetId or type(self.query_key) is not QueryKey or self.query_key.kind != 'net':
            raise ValueError('invalid net identity association')
        object.__setattr__(self, 'provenance', freeze_map(self.provenance))
        if (set(self.provenance) != {'lvs_name', 'schematic_name', 'lvs_index', 'field_sources'}
                or self.provenance['lvs_name'] != self.query_key.identity
                or self.provenance['schematic_name'] != self.net_id.name
                or self.provenance['lvs_index'] != self.query_key.index
                or set(mapping(self.provenance['field_sources'])) != {'lvs_name', 'schematic_name', 'lvs_index'}
                or not source_refs(self.provenance)):
            raise ValueError('net identity disagrees with its captured association')


def _seed(record: FrozenMap, key: QueryKey, semantic_name: str, kind: str) -> None:
    required = {'record_id', 'derived_layer', 'geometry_kind', 'quality', 'vertices_nm', 'bbox_nm',
                'unit', 'precision', 'metadata_opaque', 'section_header_opaque', 'field_sources'}
    required |= {'layout_instance', 'schematic_instance'} if kind == 'device' else {'lvs_name', 'lvs_index', 'schematic_name'}
    if set(record) != required or key.kind != kind:
        raise ValueError('invalid annotation seed record fields')
    for field in ('record_id', 'derived_layer', 'section_header_opaque'):
        string(record[field])
    if (record['geometry_kind'] != 'rectangle' or record['quality'] != 'exact' or record['unit'] != 'nm'
            or type(record['precision']) is not int or record['precision'] <= 0):
        raise ValueError('unsupported annotation seed geometry/quality/unit')
    vertices = sequence(record['vertices_nm'])
    if len(vertices) != 4:
        raise ValueError('rectangle seed requires four exact vertices')
    if any(set(mapping(point)) != {'x', 'y'} for point in vertices):
        raise ValueError('invalid exact seed vertex fields')
    coords = tuple((rational(mapping(point)['x']), rational(mapping(point)['y'])) for point in vertices)
    if any((left[0] == right[0]) == (left[1] == right[1]) for left, right in zip(coords, (*coords[1:], coords[0]))):
        raise ValueError('seed vertices must trace orthogonal nonzero rectangle edges')
    box = mapping(record['bbox_nm'])
    if set(box) != {'x_min', 'y_min', 'x_max', 'y_max'}:
        raise ValueError('invalid exact seed box')
    xmin, ymin, xmax, ymax = (rational(box[name]) for name in ('x_min', 'y_min', 'x_max', 'y_max'))
    if xmin >= xmax or ymin >= ymax or set(coords) != {(xmin, ymin), (xmin, ymax), (xmax, ymin), (xmax, ymax)}:
        raise ValueError('annotation seed polygon/box disagree')
    if any(not isinstance(value, str) for value in sequence(record['metadata_opaque'])):
        raise ValueError('invalid seed opaque metadata')
    if set(mapping(record['field_sources'])) != set(record) - {'field_sources'} or not source_refs(record):
        raise ValueError('seed field provenance is incomplete')
    if kind == 'device':
        if record['layout_instance'] != key.identity or record['schematic_instance'] != semantic_name:
            raise ValueError('device seed does not match identity join')
    elif record['lvs_name'] != key.identity or record['lvs_index'] != key.index or record['schematic_name'] != semantic_name:
        raise ValueError('net seed does not match identity join')


@dataclass(frozen=True)
class DeviceAnnotationSeed:
    semantic_id: DeviceId
    query_key: QueryKey
    record: FrozenMap

    def __post_init__(self) -> None:
        if type(self.semantic_id) is not DeviceId or type(self.query_key) is not QueryKey:
            raise ValueError('invalid device seed identity')
        object.__setattr__(self, 'record', freeze_map(self.record))
        _seed(self.record, self.query_key, self.semantic_id.name, 'device')


@dataclass(frozen=True)
class NetAnnotationSeed:
    semantic_id: NetId
    query_key: QueryKey
    record: FrozenMap

    def __post_init__(self) -> None:
        if type(self.semantic_id) is not NetId or type(self.query_key) is not QueryKey:
            raise ValueError('invalid net seed identity')
        object.__setattr__(self, 'record', freeze_map(self.record))
        _seed(self.record, self.query_key, self.semantic_id.name, 'net')


@dataclass(frozen=True)
class NormalizationFacts:
    source: SemanticCircuitDraft
    target: TargetCircuit
    differences: tuple[TargetDifference, ...]
    device_identities: tuple[DeviceIdentity, ...] = ()
    net_identities: tuple[NetIdentity, ...] = ()
    device_seeds: tuple[DeviceAnnotationSeed, ...] = ()
    net_seeds: tuple[NetAnnotationSeed, ...] = ()
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        _version(self.schema_version)
        if type(self.source) is not SemanticCircuitDraft or type(self.target) is not TargetCircuit:
            raise ValueError('normalization facts require source draft and independent target')
        for name, cls in (('differences', TargetDifference), ('device_identities', DeviceIdentity),
                          ('net_identities', NetIdentity), ('device_seeds', DeviceAnnotationSeed), ('net_seeds', NetAnnotationSeed)):
            _tuple(self, name, cls)
        object.__setattr__(self, 'differences', tuple(sorted(self.differences, key=lambda item: (item.op_type, item.operand_ref.id, item.axis or '', item.delta_id.value))))
        object.__setattr__(self, 'device_identities', tuple(sorted(self.device_identities, key=lambda item: item.device_id.name)))
        object.__setattr__(self, 'net_identities', tuple(sorted(self.net_identities, key=lambda item: item.net_id.name)))
        object.__setattr__(self, 'device_seeds', tuple(sorted(self.device_seeds, key=lambda item: string(item.record['record_id']))))
        object.__setattr__(self, 'net_seeds', tuple(sorted(self.net_seeds, key=lambda item: string(item.record['record_id']))))
        if self.differences != build_differences(self.source, self.target):
            raise ValueError('differences do not completely describe this source and target')
        selected = next(cell for cell in self.source.cells if cell.id == self.source.selected_cell)
        device_ids = {device.id for device in selected.devices}
        net_ids = {net.id for net in selected.nets}
        dkeys = {identity.query_key: identity.device_id for identity in self.device_identities}
        nkeys = {identity.query_key: identity.net_id for identity in self.net_identities}
        if (len(dkeys) != len(self.device_identities) or len({identity.device_id for identity in self.device_identities}) != len(self.device_identities)
                or len(nkeys) != len(self.net_identities) or len({identity.net_id for identity in self.net_identities}) != len(self.net_identities)
                or not set(dkeys.values()) <= device_ids or not set(nkeys.values()) <= net_ids):
            raise ValueError('duplicate or foreign semantic identity associations')
        all_keys = tuple(dkeys) + tuple(nkeys)
        if len({(key.header_id, key.query_run_id, key.database_id) for key in all_keys}) > 1:
            raise ValueError('identity facts mix query runs')
        if len({key.identity for key in dkeys}) != len(dkeys) or len({key.identity for key in nkeys}) != len(nkeys) or len({key.index for key in nkeys}) != len(nkeys):
            raise ValueError('duplicate query identity/index')
        records: list[str] = []
        for seed in self.device_seeds:
            if dkeys.get(seed.query_key) != seed.semantic_id:
                raise ValueError('device seed references an absent or different identity')
            records.append(string(seed.record['record_id']))
        for net_seed in self.net_seeds:
            if nkeys.get(net_seed.query_key) != net_seed.semantic_id:
                raise ValueError('net seed references an absent or different identity')
            records.append(string(net_seed.record['record_id']))
        if len(records) != len(set(records)):
            raise ValueError('duplicate annotation seed record identity')

    @property
    def semantic_equal(self) -> bool:
        return not self.differences


@dataclass(frozen=True)
class NormalizationResult:
    status: Literal['success', 'error']
    value: NormalizationFacts | None
    issues: tuple[NormalizationIssue, ...]
    completed: NormalizationFacts
    input: NormalizationInput
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _tuple(self, 'issues', NormalizationIssue)
        if type(self.input) is not NormalizationInput or type(self.completed) is not NormalizationFacts:
            raise ValueError('normalization result requires its input and completed facts')
        if self.status == 'success':
            if type(self.value) is not NormalizationFacts or self.issues or self.value != self.completed:
                raise ValueError('success requires complete facts and no issues')
        elif self.status == 'error':
            if self.value is not None or not self.issues:
                raise ValueError('error requires issues and no successful value')
        else:
            raise ValueError('invalid normalization result discriminator')
        records = {record.kind: record for record in self.input.parse.completed}
        facts = self.completed
        if facts.source.preservation != records['source_cdl'] or facts.target.preservation != records['target_cdl']:
            raise ValueError('normalization result was mixed with another input')
        sources = {source.uri: source for source in self.input.parse.sources}
        profile_id = mapping(self.input.value['tech_bundle'])['profile_id']
        if facts.source.profile_id != profile_id or facts.target.profile_id != profile_id:
            raise ValueError('semantic facts use a different selected profile')
        for issue in self.issues:
            source = sources.get(issue.source.uri)
            if source is None or source.sha256 != issue.source.sha256:
                raise ValueError('normalization issue refers to another input')
        header = mapping(self.input.value['header'])
        query = mapping(self.input.value['query'])
        if facts.source.selected_cell.name != mapping(header['top_identities'])['source']:
            raise ValueError('semantic selected cell differs from query source top')
        device_rows = {string(mapping(row)['layout_instance']): mapping(row) for row in sequence(mapping(query['instance_xref'])['records'])}
        net_rows = {string(mapping(row)['lvs_name']): mapping(row) for row in sequence(mapping(query['net_xref'])['records'])}
        for device_identity in facts.device_identities:
            row = device_rows.get(device_identity.query_key.identity)
            if row is None or row != device_identity.provenance or row['schematic_instance'] != device_identity.device_id.name or row['sd_swap'] != device_identity.sd_swap:
                raise ValueError('device identity is not the captured xref association')
        for net_identity in facts.net_identities:
            row = net_rows.get(net_identity.query_key.identity)
            if row is None or row != net_identity.provenance or row['schematic_name'] != net_identity.net_id.name or row['lvs_index'] != net_identity.query_key.index:
                raise ValueError('net identity is not the captured xref association')
        identities: tuple[DeviceIdentity | NetIdentity, ...] = facts.device_identities + facts.net_identities
        for identity in identities:
            key = identity.query_key
            if (key.header_id, key.query_run_id, key.database_id) != (header['header_id'], header['query_run_id'], header['query_database_id']):
                raise ValueError('normalization identity belongs to another query run')
            validate_refs(identity.provenance, sources)
        seeds: tuple[DeviceAnnotationSeed | NetAnnotationSeed, ...] = facts.device_seeds + facts.net_seeds
        for seed in seeds:
            validate_refs(seed.record, sources)
        if self.status == 'success':
            selected = next(cell for cell in facts.source.cells if cell.id == facts.source.selected_cell)
            if ({item.device_id for item in facts.device_identities} != {device.id for device in selected.devices}
                    or {item.net_id for item in facts.net_identities} != {net.id for net in selected.nets}):
                raise ValueError('successful normalization omits source identity associations')
            for cap, seeds in (('device_regions', facts.device_seeds), ('net_regions', facts.net_seeds)):
                expected = {string(mapping(item)['record_id']): mapping(item) for item in sequence(mapping(query[cap])['records'])}
                actual = {string(seed.record['record_id']): seed.record for seed in seeds}
                if actual != expected:
                    raise ValueError('successful normalization omitted or altered query seeds')
