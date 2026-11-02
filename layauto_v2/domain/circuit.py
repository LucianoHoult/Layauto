"""Immutable semantic drafts, distinct from physical or committed layout state."""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import TypeVar

from .codec import FrozenMap, Value, digest, freeze_map
from .evidence import EvidenceRecord, SourceRef
from .identifiers import CellId, DeltaId, DeviceId, NetId, QueryKey, _text, identity_value

_T = TypeVar('_T')


def _items(value: object, cls: type[_T], label: str) -> tuple[_T, ...]:
    if not isinstance(value, (tuple, list)) or any(type(x) is not cls for x in value):
        raise ValueError(f'invalid {label}')
    return tuple(value)


def _source(value: object) -> None:
    if type(value) is not SourceRef or value.sha256 is None:
        raise ValueError('semantic field requires captured source provenance')


def _location(value: object, source: SourceRef) -> None:
    if not isinstance(value, FrozenMap) or value.get('uri') != source.uri or value.get('sha256') != source.sha256:
        raise ValueError('field evidence and source reference disagree')
    for name in ('line', 'column', 'byte_offset'):
        location = getattr(source, name)
        if location is not None and value.get(name) != location:
            raise ValueError('field evidence location disagrees with source reference')


def _map(value: Value) -> FrozenMap:
    if not isinstance(value, FrozenMap):
        raise ValueError('expected evidence map')
    return value


def _array(value: Value) -> tuple[Value, ...]:
    if not isinstance(value, tuple):
        raise ValueError('expected evidence array')
    return value


def _records(value: Value) -> dict[str, FrozenMap]:
    result: dict[str, FrozenMap] = {}
    for item in _array(value):
        record = _map(item)
        name = record.get('name')
        if type(name) is not str or not name or name in result:
            raise ValueError('preserved identities must be nonempty and unique')
        result[name] = record
    return result


def _capture_sources(value: Value, allowed: set[tuple[str, str | None]]) -> None:
    if isinstance(value, FrozenMap):
        if 'sha256' in value and ('uri' in value or 'path' in value):
            uri = value.get('uri', value.get('path'))
            sha = value['sha256']
            if not isinstance(uri, str) or not isinstance(sha, str) or (uri, sha) not in allowed:
                raise ValueError('semantic provenance references another capture')
        for item in value.values():
            _capture_sources(item, allowed)
    elif isinstance(value, tuple):
        for item in value:
            _capture_sources(item, allowed)


@dataclass(frozen=True)
class Parameter:
    axis: str
    token: str
    exact: Fraction | str
    unit: str
    lexeme: str
    source: SourceRef
    field_evidence: FrozenMap

    def __post_init__(self) -> None:
        for name in ('axis', 'token', 'unit', 'lexeme'):
            _text(getattr(self, name), name)
        if type(self.exact) not in (Fraction, str):
            raise ValueError('parameter requires an exact rational or token')
        if isinstance(self.exact, str):
            _text(self.exact, 'parameter token value')
            if self.unit != 'token' or self.exact != self.lexeme:
                raise ValueError('token parameter value/unit/lexeme disagree')
        elif self.exact <= 0 or self.unit not in ('metres', 'count'):
            raise ValueError('numeric parameter requires positive exact count or metres')
        elif self.unit == 'count' and self.exact.denominator != 1:
            raise ValueError('count parameter must be integral')
        _source(self.source)
        object.__setattr__(self, 'field_evidence', freeze_map(self.field_evidence))
        _location(self.field_evidence, self.source)
        if self.field_evidence.get('lexeme') != self.token + '=' + self.lexeme:
            raise ValueError('parameter evidence does not preserve its original token')


@dataclass(frozen=True)
class Terminal:
    role: str
    net_id: NetId
    source: SourceRef

    def __post_init__(self) -> None:
        _text(self.role, 'terminal role')
        if type(self.net_id) is not NetId:
            raise ValueError('terminal requires a typed net id')
        _source(self.source)


@dataclass(frozen=True)
class Membership:
    device_id: DeviceId
    terminal: str

    def __post_init__(self) -> None:
        if type(self.device_id) is not DeviceId:
            raise ValueError('membership requires typed device identity')
        _text(self.terminal, 'terminal role')


@dataclass(frozen=True)
class Device:
    id: DeviceId
    model: str
    terminals: tuple[Terminal, ...]
    parameters: tuple[Parameter, ...]
    field_sources: FrozenMap
    preservation: FrozenMap

    def __post_init__(self) -> None:
        if type(self.id) is not DeviceId:
            raise ValueError('device requires typed identity')
        _text(self.model, 'model')
        terminals = _items(self.terminals, Terminal, 'terminals')
        parameters = _items(self.parameters, Parameter, 'parameters')
        if not terminals or len({t.role for t in terminals}) != len(terminals):
            raise ValueError('device terminal roles must be nonempty and unique')
        if any(t.net_id.cell != self.id.cell for t in terminals):
            raise ValueError('device terminal references another cell')
        if not parameters or len({p.axis for p in parameters}) != len(parameters) or len({p.token for p in parameters}) != len(parameters):
            raise ValueError('device parameter axes/tokens must be nonempty and unique')
        object.__setattr__(self, 'terminals', terminals)
        object.__setattr__(self, 'parameters', tuple(sorted(parameters, key=lambda p: p.axis)))
        object.__setattr__(self, 'field_sources', freeze_map(self.field_sources))
        object.__setattr__(self, 'preservation', freeze_map(self.preservation))
        expected_fields = {'name', 'model', *(t.role for t in terminals)}
        if set(self.field_sources) != expected_fields:
            raise ValueError('device field sources must cover identity, model and every terminal')
        if _map(self.field_sources['name']).get('lexeme') != self.id.name or _map(self.field_sources['model']).get('lexeme') != self.model:
            raise ValueError('device identity/model differs from preserved evidence')
        for terminal in terminals:
            evidence = _map(self.field_sources[terminal.role])
            _location(evidence, terminal.source)
            if evidence.get('lexeme') != terminal.net_id.name:
                raise ValueError('terminal differs from its preserved field')
        raw = self.preservation
        if (raw.get('name') != self.id.name or raw.get('model') != self.model
                or raw.get('terminals') != tuple(t.net_id.name for t in terminals)
                or raw.get('terminal_order') != tuple(t.role for t in terminals)
                or raw.get('field_sources') != self.field_sources):
            raise ValueError('device preservation disagrees with semantic fields')
        raw_parameters = _map(raw.get('parameters'))
        if set(raw_parameters) != {p.token for p in parameters}:
            raise ValueError('device parameter preservation is incomplete')
        for parameter in parameters:
            original = _map(raw_parameters[parameter.token])
            if (original.get('axis') != parameter.axis or original.get('exact') != parameter.exact
                    or original.get('unit') != parameter.unit or original.get('lexeme') != parameter.lexeme
                    or original.get('source') != parameter.field_evidence):
                raise ValueError('parameter differs from preservation evidence')


@dataclass(frozen=True)
class Net:
    id: NetId
    port_indices: tuple[int, ...]
    global_net: bool
    memberships: tuple[Membership, ...]
    sources: tuple[SourceRef, ...]

    def __post_init__(self) -> None:
        if type(self.id) is not NetId or type(self.global_net) is not bool:
            raise ValueError('invalid semantic net identity/global marker')
        indices = _items(self.port_indices, int, 'port indices')
        if any(i < 0 for i in indices) or len(set(indices)) != len(indices):
            raise ValueError('port indices must be distinct nonnegative integers')
        members = _items(self.memberships, Membership, 'net memberships')
        if any(m.device_id.cell != self.id.cell for m in members) or len(set(members)) != len(members):
            raise ValueError('duplicate or foreign net membership')
        sources = _items(self.sources, SourceRef, 'net sources')
        if not sources:
            raise ValueError('net requires declaration or terminal provenance')
        for source in sources:
            _source(source)
        object.__setattr__(self, 'port_indices', tuple(sorted(indices)))
        object.__setattr__(self, 'memberships', tuple(sorted(members, key=lambda m: (m.device_id.name, m.terminal))))
        object.__setattr__(self, 'sources', tuple(sorted(set(sources), key=lambda s: (s.uri, s.sha256 or '', s.line or 0, s.column or 0, s.byte_offset or 0, s.field or '', s.record_index or 0))))


@dataclass(frozen=True)
class Cell:
    id: CellId
    ports: tuple[NetId, ...]
    globals: tuple[NetId, ...]
    devices: tuple[Device, ...]
    nets: tuple[Net, ...]
    field_sources: FrozenMap

    def __post_init__(self) -> None:
        if type(self.id) is not CellId:
            raise ValueError('cell requires typed identity')
        ports = _items(self.ports, NetId, 'ports')
        globals_ = _items(self.globals, NetId, 'globals')
        devices = _items(self.devices, Device, 'devices')
        nets = _items(self.nets, Net, 'nets')
        if (len(set(ports)) != len(ports) or len(set(globals_)) != len(globals_)
                or len({d.id for d in devices}) != len(devices) or len({n.id for n in nets}) != len(nets)):
            raise ValueError('duplicate semantic identity in cell')
        if (any(n.cell != self.id for n in (*ports, *globals_)) or any(d.id.cell != self.id for d in devices)
                or any(n.id.cell != self.id for n in nets)):
            raise ValueError('cell contains foreign semantic identity')
        net_ids = {n.id for n in nets}
        terminals = [(d.id, t) for d in devices for t in d.terminals]
        expected_ids = set(ports) | set(globals_) | {t.net_id for _, t in terminals}
        if net_ids != expected_ids:
            raise ValueError('net set differs from complete semantic references')
        for net in nets:
            expected_members = {Membership(device, t.role) for device, t in terminals if t.net_id == net.id}
            if set(net.memberships) != expected_members:
                raise ValueError('terminal/net membership relation is incomplete or inconsistent')
            if net.port_indices != tuple(i for i, n in enumerate(ports) if n == net.id) or net.global_net != (net.id in globals_):
                raise ValueError('net declaration markers disagree with cell ports/globals')
        object.__setattr__(self, 'ports', ports)
        object.__setattr__(self, 'globals', tuple(sorted(globals_, key=lambda n: n.name)))
        object.__setattr__(self, 'devices', tuple(sorted(devices, key=lambda d: d.id.name)))
        object.__setattr__(self, 'nets', tuple(sorted(nets, key=lambda n: n.id.name)))
        object.__setattr__(self, 'field_sources', freeze_map(self.field_sources))
        if set(self.field_sources) != {'name', 'pins'}:
            raise ValueError('cell fields require name and ordered pin provenance')
        if _map(self.field_sources['name']).get('lexeme') != self.id.name:
            raise ValueError('cell identity differs from field evidence')
        raw_pins = _array(self.field_sources['pins'])
        if tuple(_map(p).get('lexeme') for p in raw_pins) != tuple(p.name for p in ports):
            raise ValueError('ordered ports differ from field evidence')


def _circuit(cells: object, preservation: EvidenceRecord, kind: str) -> tuple[Cell, ...]:
    values = _items(cells, Cell, 'cells')
    if not values or len({c.id for c in values}) != len(values):
        raise ValueError('circuit cells must be nonempty and unique')
    if type(preservation) is not EvidenceRecord or preservation.kind != kind or len(preservation.sources) != 1:
        raise ValueError('circuit requires its own single-source CDL preservation evidence')
    allowed = {(s.uri, s.sha256) for s in preservation.sources}
    _capture_sources(preservation.payload, allowed)
    original_cells = _records(preservation.payload.get('tops'))
    if set(original_cells) != {c.id.name for c in values}:
        raise ValueError('circuit does not preserve all source tops')
    for cell in values:
        original = original_cells[cell.id.name]
        if (original.get('pins') != tuple(p.name for p in cell.ports)
                or original.get('globals') != tuple(g.name for g in cell.globals)
                or original.get('field_sources') != cell.field_sources):
            raise ValueError('cell declarations disagree with preservation')
        raw_devices = _records(original.get('devices'))
        if set(raw_devices) != {d.id.name for d in cell.devices}:
            raise ValueError('circuit does not preserve every device')
        _capture_sources(cell.field_sources, allowed)
        for device in cell.devices:
            if raw_devices[device.id.name] != device.preservation:
                raise ValueError('device preservation references another source')
            for ref in (*(t.source for t in device.terminals), *(p.source for p in device.parameters)):
                if (ref.uri, ref.sha256) not in allowed:
                    raise ValueError('device source is outside circuit capture')
        for net in cell.nets:
            if any((s.uri, s.sha256) not in allowed for s in net.sources):
                raise ValueError('net source is outside circuit capture')
    return tuple(sorted(values, key=lambda c: c.id.name))


@dataclass(frozen=True)
class SemanticCircuitDraft:
    cells: tuple[Cell, ...]
    selected_cell: CellId
    profile_id: str
    dialect: str
    preservation: EvidenceRecord
    schema_version: str = 'layauto-semantic-draft/1'

    def __post_init__(self) -> None:
        if self.schema_version != 'layauto-semantic-draft/1':
            raise ValueError('unknown semantic draft schema')
        for name in ('profile_id', 'dialect'):
            _text(getattr(self, name), name)
        cells = _circuit(self.cells, self.preservation, 'source_cdl')
        if type(self.selected_cell) is not CellId or self.selected_cell not in {c.id for c in cells}:
            raise ValueError('selected source top is absent')
        if self.preservation.payload.get('dialect') != self.dialect:
            raise ValueError('semantic draft dialect differs from evidence')
        object.__setattr__(self, 'cells', cells)

    @property
    def semantic_digest(self) -> str:
        return semantic_digest(self)


@dataclass(frozen=True)
class TargetCircuit:
    cells: tuple[Cell, ...]
    profile_id: str
    dialect: str
    preservation: EvidenceRecord
    schema_version: str = 'layauto-target-circuit/1'

    def __post_init__(self) -> None:
        if self.schema_version != 'layauto-target-circuit/1':
            raise ValueError('unknown target circuit schema')
        for name in ('profile_id', 'dialect'):
            _text(getattr(self, name), name)
        object.__setattr__(self, 'cells', _circuit(self.cells, self.preservation, 'target_cdl'))
        if self.preservation.payload.get('dialect') != self.dialect:
            raise ValueError('target circuit dialect differs from evidence')

    @property
    def semantic_digest(self) -> str:
        return semantic_digest(self)


def semantic_value(value: object) -> Value:
    """Project declared semantics; source bytes, lexemes and locations stay separate."""
    if value is None or type(value) is str:
        return value
    if isinstance(value, (CellId, DeviceId, NetId, DeltaId, QueryKey)):
        return identity_value(value)
    if isinstance(value, (SemanticCircuitDraft, TargetCircuit)):
        return FrozenMap({'schema': 'layauto-circuit-semantics/1', 'profile_id': value.profile_id,
                          'dialect': value.dialect, 'cells': tuple(semantic_value(c) for c in value.cells)})
    if type(value) is Cell:
        return FrozenMap({'id': identity_value(value.id), 'ports': tuple(semantic_value(p) for p in value.ports),
                          'globals': tuple(semantic_value(g) for g in value.globals),
                          'devices': tuple(semantic_value(d) for d in value.devices),
                          'nets': tuple(semantic_value(n) for n in value.nets)})
    if type(value) is Device:
        return FrozenMap({'id': identity_value(value.id), 'model': value.model,
                          'terminals': tuple(semantic_value(t) for t in value.terminals),
                          'parameters': tuple(semantic_value(p) for p in value.parameters)})
    if type(value) is Parameter:
        return FrozenMap({'axis': value.axis, 'exact': value.exact, 'unit': value.unit})
    if type(value) is Terminal:
        return FrozenMap({'role': value.role, 'net_id': identity_value(value.net_id)})
    if type(value) is Membership:
        return FrozenMap({'device_id': identity_value(value.device_id), 'terminal': value.terminal})
    if type(value) is Net:
        return FrozenMap({'id': identity_value(value.id), 'port_indices': value.port_indices,
                          'global_net': value.global_net,
                          'memberships': tuple(semantic_value(m) for m in value.memberships)})
    if isinstance(value, tuple):
        return tuple(semantic_value(item) for item in value)
    raise ValueError('unsupported semantic value type')


def semantic_digest(circuit: SemanticCircuitDraft | TargetCircuit) -> str:
    if type(circuit) not in (SemanticCircuitDraft, TargetCircuit):
        raise ValueError('semantic digest requires a circuit')
    return digest(semantic_value(circuit))
