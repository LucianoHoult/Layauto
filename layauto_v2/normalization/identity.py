"""Profile-directed source admission and query-to-semantic identity joins."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

from ._validation import mapping, sequence, string, source_refs, source_admission_problem
from layauto_v2.domain.codec import FrozenMap
from layauto_v2.domain.source_location import ref_from_location
from layauto_v2.domain.evidence import SourceRef
from layauto_v2.domain.identifiers import DeviceId, NetId, QueryKey
from layauto_v2.domain.circuit import SemanticCircuitDraft
from .contracts import (
    NormalizationInput, NormalizationIssue, DeviceIdentity, NetIdentity,
    DeviceAnnotationSeed, NetAnnotationSeed,
)


class NormalizationError(Exception):
    """Only this private expected component failure is caught by normalize."""
    def __init__(self, issue: NormalizationIssue) -> None:
        self.issue = issue
        self.progress: _JoinProgress | None = None
        super().__init__(issue.message)


def fail(code: str, message: str, source: SourceRef, *, unsupported: bool = False) -> None:
    raise NormalizationError(NormalizationIssue('unsupported' if unsupported else 'identity', code, message, source))


def _located(record: FrozenMap, fallback: SourceRef) -> SourceRef:
    refs = source_refs(record)
    return refs[0] if refs else fallback


def admit_source(input: NormalizationInput, source: SemanticCircuitDraft) -> None:
    records = {record.kind: record for record in input.parse.completed}
    problem = source_admission_problem(input.value, source, records['tech'].sources, records['header'].sources[0])
    if problem is not None:
        raise NormalizationError(NormalizationIssue(*problem))


@dataclass
class _JoinProgress:
    devices: list[DeviceIdentity] = field(default_factory=list)
    nets: list[NetIdentity] = field(default_factory=list)
    device_seeds: list[DeviceAnnotationSeed] = field(default_factory=list)
    net_seeds: list[NetAnnotationSeed] = field(default_factory=list)


def join_identities(input: NormalizationInput, source: SemanticCircuitDraft) -> tuple[
        tuple[DeviceIdentity, ...], tuple[NetIdentity, ...], tuple[DeviceAnnotationSeed, ...], tuple[NetAnnotationSeed, ...]]:
    progress = _JoinProgress()
    try:
        return _join_identities(input, source, progress)
    except NormalizationError as exc:
        exc.progress = progress
        raise


def _join_identities(input: NormalizationInput, source: SemanticCircuitDraft, progress: _JoinProgress) -> tuple[
        tuple[DeviceIdentity, ...], tuple[NetIdentity, ...], tuple[DeviceAnnotationSeed, ...], tuple[NetAnnotationSeed, ...]]:
    header = mapping(input.value['header'])
    query = mapping(input.value['query'])
    physical = mapping(mapping(input.value['tech'])['physical'])
    models = mapping(physical['models'])
    header_ref = next(record.sources[0] for record in input.parse.completed if record.kind == 'header')
    selected = next(cell for cell in source.cells if cell.id == source.selected_cell)
    devices = {device.id.name: device for device in selected.devices}
    nets = {net.id.name: net for net in selected.nets}
    instance_rows = tuple(mapping(row) for row in sequence(mapping(query['instance_xref'])['records']))
    layout_seen: set[str] = set()
    source_seen: set[str] = set()
    repeated: list[FrozenMap] = []
    for row in instance_rows:
        layout, schematic = string(row['layout_instance']), string(row['schematic_instance'])
        if layout in layout_seen:
            fail('ConflictingDeviceIdentity', 'query layout device is associated more than once', _located(row, header_ref))
        layout_seen.add(layout)
        if schematic not in devices:
            fail('UnknownDeviceIdentity', 'xref names a device absent from source CDL', _located(row, header_ref))
        if schematic in source_seen:
            repeated.append(row)
        source_seen.add(schematic)
    if source_seen != set(devices):
        missing = sorted(set(devices) - source_seen)
        location = _located(repeated[0], header_ref) if repeated else ref_from_location(mapping(devices[missing[0]].field_sources['name']))
        fail('UnsupportedDeviceCardinality' if repeated else 'MissingDeviceIdentity',
             'source devices lack a complete one-to-one query association: ' + ','.join(missing), location, unsupported=bool(repeated))
    if repeated:
        fail('UnsupportedDeviceReduction', 'additional layout devices require forbidden reduction', _located(repeated[0], header_ref), unsupported=True)
    device_identities = progress.devices
    by_layout: dict[str, DeviceIdentity] = {}
    for row in instance_rows:
        device = devices[string(row['schematic_instance'])]
        key = QueryKey(string(header['header_id']), string(header['query_run_id']), cast('str | None', header['query_database_id']), 'device', string(row['layout_instance']))
        swapped = row['sd_swap']
        if type(swapped) is not bool:
            raise ValueError('captured swap flag must be boolean')
        identity = DeviceIdentity(device.id, key, swapped, row)
        device_identities.append(identity)
        by_layout[key.identity] = identity
        if swapped and mapping(models[device.model])['sd_symmetry'] is not True:
            fail('UnsupportedTerminalSwap', 'selected model declares ordered S/D terminals; swap is unsupported', _located(mapping(mapping(row['field_sources'])['sd_swap']), header_ref), unsupported=True)
    net_rows = tuple(mapping(row) for row in sequence(mapping(query['net_xref'])['records']))
    net_identities = progress.nets
    by_net: dict[str, NetIdentity] = {}
    names: set[str] = set()
    indices: set[str] = set()
    for row in net_rows:
        layout, schematic, index = string(row['lvs_name']), string(row['schematic_name']), string(row['lvs_index'])
        if layout in by_net or schematic in names or index in indices:
            fail('ConflictingNetIdentity', 'net xref contains duplicate/conflicting names or indices', _located(row, header_ref))
        if schematic not in nets:
            fail('UnknownNetIdentity', 'xref names a net absent from source CDL', _located(row, header_ref))
        names.add(schematic)
        indices.add(index)
        key = QueryKey(string(header['header_id']), string(header['query_run_id']), cast('str | None', header['query_database_id']), 'net', layout, index)
        net_identity = NetIdentity(nets[schematic].id, key, row)
        net_identities.append(net_identity)
        by_net[layout] = net_identity
    if names != set(nets):
        missing_net = nets[sorted(set(nets) - names)[0]]
        fail('MissingNetIdentity', 'source net has no query association', missing_net.sources[0])
    device_seeds = progress.device_seeds
    for row_value in sequence(mapping(query['device_regions'])['records']):
        row = mapping(row_value)
        association = by_layout.get(string(row['layout_instance']))
        if association is None or association.device_id.name != row['schematic_instance']:
            fail('ConflictingDeviceSeed', 'device region does not agree with xref join', _located(row, header_ref))
        assert association is not None
        device_seeds.append(DeviceAnnotationSeed(association.device_id, association.query_key, row))
    net_seeds = progress.net_seeds
    for row_value in sequence(mapping(query['net_regions'])['records']):
        row = mapping(row_value)
        net_association = by_net.get(string(row['lvs_name']))
        if net_association is None or net_association.net_id.name != row['schematic_name'] or net_association.query_key.index != row['lvs_index']:
            fail('ConflictingNetSeed', 'net region does not agree with xref/NET NAMES join', _located(row, header_ref))
        assert net_association is not None
        net_seeds.append(NetAnnotationSeed(net_association.net_id, net_association.query_key, row))
    return (tuple(sorted(device_identities, key=lambda item: item.device_id.name)),
            tuple(sorted(net_identities, key=lambda item: item.net_id.name)),
            tuple(sorted(device_seeds, key=lambda item: string(item.record['record_id']))),
            tuple(sorted(net_seeds, key=lambda item: string(item.record['record_id']))))
