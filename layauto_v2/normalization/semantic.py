"""Pure construction of complete semantic documents from captured CDL evidence."""
from __future__ import annotations

from fractions import Fraction
from typing import cast

from layauto_v2.domain._normalization_input import mapping, sequence, string, ref_from_location
from layauto_v2.domain.codec import FrozenMap
from layauto_v2.domain.evidence import EvidenceRecord, SourceRef
from layauto_v2.domain.identifiers import CellId, DeviceId, NetId
from layauto_v2.domain.circuit import (
    Parameter, Terminal, Membership, Device, Net, Cell, SemanticCircuitDraft, TargetCircuit,
)
from layauto_v2.domain.normalization import NormalizationInput



def _cells(evidence: EvidenceRecord, tech: FrozenMap) -> tuple[Cell, ...]:
    models = mapping(mapping(tech['physical'])['models'])
    result: list[Cell] = []
    for top_value in sequence(evidence.payload['tops']):
        top = mapping(top_value)
        cell_id = CellId(string(top['name']))
        ports = tuple(NetId(cell_id, string(pin)) for pin in sequence(top['pins']))
        globals_ = tuple(NetId(cell_id, string(pin)) for pin in sequence(top['globals']))
        devices: list[Device] = []
        memberships: dict[NetId, list[Membership]] = {net: [] for net in (*ports, *globals_)}
        sources: dict[NetId, list[SourceRef]] = {net: [] for net in (*ports, *globals_)}
        top_fields = mapping(top['field_sources'])
        for net, pin_source in zip(ports, sequence(top_fields['pins'])):
            sources[net].append(ref_from_location(mapping(pin_source)))
        for device_value in sequence(top['devices']):
            record = mapping(device_value)
            device_id = DeviceId(cell_id, string(record['name']))
            model_name = string(record['model'])
            model = mapping(models[model_name])
            order = tuple(string(role) for role in sequence(model['terminal_order']))
            if record['terminal_order'] != order:
                raise ValueError('captured terminal order differs from selected model')
            terminal_names = sequence(record['terminals'])
            if len(terminal_names) != len(order):
                raise ValueError('captured terminal count differs from selected model')
            fields = mapping(record['field_sources'])
            terminals: list[Terminal] = []
            for role, name in zip(order, terminal_names):
                net = NetId(cell_id, string(name))
                ref = ref_from_location(mapping(fields[role]))
                terminals.append(Terminal(role, net, ref))
                memberships.setdefault(net, []).append(Membership(device_id, role))
                sources.setdefault(net, []).append(ref)
            parameters: list[Parameter] = []
            axes = mapping(model['parameter_axes'])
            captured = mapping(record['parameters'])
            if set(captured) != set(axes) or set(captured) != set(sequence(model['required_parameters'])):
                raise ValueError('captured parameter axes differ from selected model')
            for token, parameter_value in captured.items():
                parameter = mapping(parameter_value)
                axis = string(axes[token])
                if parameter['axis'] != axis:
                    raise ValueError('captured parameter interpretation differs from selected model')
                exact = parameter['exact']
                if not isinstance(exact, (Fraction, str)):
                    raise ValueError('parameter requires exact rational or token')
                field = mapping(parameter['source'])
                parameters.append(Parameter(axis, token, exact, string(parameter['unit']),
                                            string(parameter['lexeme']), ref_from_location(field), field))
            devices.append(Device(device_id, model_name, tuple(terminals), tuple(parameters), fields, record))
        nets = tuple(Net(net, tuple(index for index, port in enumerate(ports) if port == net), net in globals_,
                         tuple(memberships[net]), tuple(sources[net])) for net in memberships)
        result.append(Cell(cell_id, ports, globals_, tuple(devices), nets, top_fields))
    return tuple(result)


def build_source(input: NormalizationInput) -> SemanticCircuitDraft:
    records = {record.kind: record for record in input.parse.completed}
    tech = mapping(input.value['tech'])
    header = mapping(input.value['header'])
    return SemanticCircuitDraft(_cells(records['source_cdl'], tech),
                                CellId(string(mapping(header['top_identities'])['source'])),
                                string(mapping(input.value['tech_bundle'])['profile_id']),
                                string(mapping(mapping(tech['formats'])['cdl_dialect'])['id']),
                                records['source_cdl'])


def build_target(input: NormalizationInput) -> TargetCircuit:
    record = next(record for record in input.parse.completed if record.kind == 'target_cdl')
    tech = mapping(input.value['tech'])
    return TargetCircuit(_cells(record, tech), string(mapping(input.value['tech_bundle'])['profile_id']),
                         string(mapping(mapping(tech['formats'])['cdl_dialect'])['id']), record)
