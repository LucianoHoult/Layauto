"""Complete, immutable CDL target differences awaiting later planner admission."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, TypeAlias

from .circuit import (
    Cell, Device, Net, Parameter, SemanticCircuitDraft, TargetCircuit, Terminal,
    semantic_value,
)
from .codec import FrozenMap, Value, digest, freeze_map
from .evidence import SourceRef
from .identifiers import CellId, DeltaId, DeviceId, NetId, _text, identity_value

DifferenceOp: TypeAlias = Literal[
    'cell_add', 'cell_remove', 'ports_change', 'globals_change',
    'device_add', 'device_remove', 'model_change', 'terminals_change',
    'parameter_change', 'net_add', 'net_remove', 'net_membership_change',
]
Operand: TypeAlias = CellId | DeviceId | NetId
DifferenceValue: TypeAlias = Cell | Device | Net | Parameter | tuple[NetId, ...] | tuple[Terminal, ...] | str | None


def difference_id(op_type: DifferenceOp, operand_ref: Operand,
                  semantic_before: DifferenceValue, semantic_after: DifferenceValue,
                  axis: str | None = None) -> DeltaId:
    if op_type not in ('cell_add', 'cell_remove', 'ports_change', 'globals_change',
                       'device_add', 'device_remove', 'model_change', 'terminals_change',
                       'parameter_change', 'net_add', 'net_remove', 'net_membership_change'):
        raise ValueError('unknown difference operation')
    if axis is not None:
        _text(axis, 'parameter axis')
    if type(operand_ref) not in (CellId, DeviceId, NetId):
        raise ValueError('difference operand must be a semantic typed id')
    return DeltaId(digest({'schema': 'layauto-target-delta-id/1', 'op_type': op_type,
                           'operand': identity_value(operand_ref), 'axis': axis,
                           'before': semantic_value(semantic_before),
                           'after': semantic_value(semantic_after)}))


def _refs(value: object) -> tuple[SourceRef, ...]:
    """Preserved locations, including both declared and member-derived evidence."""
    refs: list[SourceRef] = []
    if type(value) is SourceRef:
        refs.append(value)
    elif isinstance(value, (Parameter, Terminal)):
        refs.append(value.source)
    elif type(value) is Net:
        refs.extend(value.sources)
    elif type(value) is Device:
        refs.extend(_refs(value.field_sources))
        refs.extend(_refs(value.parameters))
    elif type(value) is Cell:
        refs.extend(_refs(value.field_sources))
        refs.extend(_refs(value.devices))
        refs.extend(_refs(value.nets))
    elif isinstance(value, FrozenMap):
        uri, sha = value.get('uri'), value.get('sha256')
        if isinstance(uri, str) and isinstance(sha, str):
            kwargs: dict[str, int | None] = {}
            for name in ('line', 'column', 'byte_offset', 'record_index'):
                number = value.get(name)
                if number is not None and type(number) is not int:
                    raise ValueError('invalid preserved source location')
                kwargs[name] = number if isinstance(number, int) else None
            refs.append(SourceRef(uri, sha, line=kwargs['line'], column=kwargs['column'],
                                  byte_offset=kwargs['byte_offset'], record_index=kwargs['record_index']))
        else:
            for item in value.values():
                refs.extend(_refs(item))
    elif isinstance(value, tuple):
        for item in value:
            refs.extend(_refs(item))
    return tuple(sorted(set(refs), key=lambda s: (s.uri, s.sha256 or '', s.line or 0, s.column or 0,
                                                 s.byte_offset or 0, s.record_index or 0, s.field or '')))


@dataclass(frozen=True)
class TargetDifference:
    delta_id: DeltaId
    op_type: DifferenceOp
    operand_ref: Operand
    scope: Literal['cell', 'device', 'net']
    semantic_before: DifferenceValue
    semantic_after: DifferenceValue
    required_capability: str
    obligations: tuple[str, ...]
    provenance: tuple[SourceRef, ...]
    axis: str | None = None
    hard_constraints: FrozenMap = field(default_factory=lambda: FrozenMap({}))
    preferences: FrozenMap = field(default_factory=lambda: FrozenMap({}))
    source: Literal['cdl_diff'] = 'cdl_diff'
    schema_version: str = 'layauto-target-difference/1'

    def __post_init__(self) -> None:
        if self.schema_version != 'layauto-target-difference/1' or self.source != 'cdl_diff':
            raise ValueError('unknown target difference schema/source')
        if type(self.delta_id) is not DeltaId or type(self.operand_ref) not in (CellId, DeviceId, NetId):
            raise ValueError('difference requires typed identities')
        _text(self.required_capability, 'required capability')
        before, after = self.semantic_before, self.semantic_after
        operand = self.operand_ref
        op = self.op_type
        if op in ('cell_add', 'cell_remove'):
            expected: type[Cell] | type[Device] | type[Net] = Cell
            id_type: type[CellId] | type[DeviceId] | type[NetId] = CellId
            scope = 'cell'
        elif op in ('device_add', 'device_remove'):
            expected, id_type, scope = Device, DeviceId, 'device'
        elif op in ('net_add', 'net_remove'):
            expected, id_type, scope = Net, NetId, 'net'
        else:
            expected, id_type, scope = Cell, CellId, 'cell'
        if op in ('cell_add', 'cell_remove', 'device_add', 'device_remove', 'net_add', 'net_remove'):
            actual = after if op.endswith('_add') else before
            absent = before if op.endswith('_add') else after
            if type(operand) is not id_type or type(actual) is not expected or absent is not None:
                raise ValueError('add/remove difference has invalid operand/value combination')
            if not isinstance(actual, (Cell, Device, Net)) or actual.id != operand:
                raise ValueError('add/remove value belongs to another operand')
        elif op in ('ports_change', 'globals_change'):
            scope = 'cell'
            if type(operand) is not CellId or not isinstance(before, tuple) or not isinstance(after, tuple):
                raise ValueError('port/global change requires cell and two ordered net-id sequences')
            if any(type(n) is not NetId or n.cell != operand for n in (*before, *after)):
                raise ValueError('port/global change references foreign net')
            if len(set(before)) != len(before) or len(set(after)) != len(after):
                raise ValueError('duplicate port/global identity')
        elif op == 'model_change':
            scope = 'device'
            if type(operand) is not DeviceId or type(before) is not str or type(after) is not str:
                raise ValueError('model change requires device and model tokens')
            _text(before, 'before model')
            _text(after, 'after model')
        elif op == 'terminals_change':
            scope = 'device'
            if type(operand) is not DeviceId or not isinstance(before, tuple) or not isinstance(after, tuple):
                raise ValueError('terminal change requires device and two ordered terminal sequences')
            if not before or not after or any(type(t) is not Terminal or t.net_id.cell != operand.cell for t in (*before, *after)):
                raise ValueError('terminal change references foreign net')
            if (len({t.role for t in before if isinstance(t, Terminal)}) != len(before)
                    or len({t.role for t in after if isinstance(t, Terminal)}) != len(after)):
                raise ValueError('terminal roles are duplicated')
        elif op == 'parameter_change':
            scope = 'device'
            if type(operand) is not DeviceId or (before is None and after is None):
                raise ValueError('parameter change requires device and at least one axis value')
            _text(self.axis, 'parameter axis')
            if any(p is not None and (type(p) is not Parameter or p.axis != self.axis) for p in (before, after)):
                raise ValueError('parameter difference axis/value mismatch')
        elif op == 'net_membership_change':
            scope = 'net'
            if type(operand) is not NetId or type(before) is not Net or type(after) is not Net:
                raise ValueError('net change requires net and two semantic net records')
            if before.id != operand or after.id != operand:
                raise ValueError('net change values belong to another operand')
        else:
            raise ValueError('unsupported target difference operation')
        expected_capability = 'resize:' + self.axis if self.axis is not None else op
        if self.required_capability != expected_capability:
            raise ValueError('required capability conflicts with difference operation')
        if self.scope != scope or (op != 'parameter_change' and self.axis is not None):
            raise ValueError('difference scope/axis conflicts with its operation')
        if semantic_value(before) == semantic_value(after):
            raise ValueError('target difference must express unequal semantic values')
        if self.delta_id != difference_id(op, operand, before, after, self.axis):
            raise ValueError('target difference id disagrees with semantic operands')
        if not isinstance(self.obligations, (tuple, list)) or not self.obligations:
            raise ValueError('difference must retain downstream planning obligations')
        for obligation in self.obligations:
            _text(obligation, 'planning obligation')
        if 'planner_admission_required' not in self.obligations:
            raise ValueError('difference cannot claim that planner admission already happened')
        object.__setattr__(self, 'obligations', tuple(sorted(set(self.obligations))))
        if not isinstance(self.provenance, (tuple, list)) or not self.provenance or any(type(s) is not SourceRef or s.sha256 is None for s in self.provenance):
            raise ValueError('difference requires captured provenance')
        provenance = _refs(tuple(self.provenance))
        if not set(_refs((before, after))) <= set(provenance):
            raise ValueError('difference omits before/after provenance')
        object.__setattr__(self, 'provenance', provenance)
        object.__setattr__(self, 'hard_constraints', freeze_map(self.hard_constraints))
        object.__setattr__(self, 'preferences', freeze_map(self.preferences))


def build_differences(source: SemanticCircuitDraft, target: TargetCircuit) -> tuple[TargetDifference, ...]:
    """Enumerate all supported CDL semantic changes without planner filtering."""
    if type(source) is not SemanticCircuitDraft or type(target) is not TargetCircuit:
        raise ValueError('difference construction requires source draft and immutable target')
    if source.profile_id != target.profile_id or source.dialect != target.dialect:
        raise ValueError('source and target semantic comparators differ')
    differences: list[TargetDifference] = []

    def add(op: DifferenceOp, operand: Operand, before: DifferenceValue,
            after: DifferenceValue, *, axis: str | None = None,
            extra_sources: tuple[SourceRef, ...] = ()) -> None:
        if semantic_value(before) == semantic_value(after):
            return
        scope: Literal['cell', 'device', 'net'] = ('cell' if type(operand) is CellId else
                                                  'device' if type(operand) is DeviceId else 'net')
        capability = 'resize:' + axis if axis is not None else op
        differences.append(TargetDifference(difference_id(op, operand, before, after, axis),
                                            op, operand, scope, before, after, capability,
                                            ('planner_admission_required',),
                                            _refs((before, after, extra_sources)), axis))

    before_cells = {cell.id: cell for cell in source.cells}
    after_cells = {cell.id: cell for cell in target.cells}
    for cell_id in sorted(set(before_cells) | set(after_cells), key=lambda c: c.name):
        before_cell, after_cell = before_cells.get(cell_id), after_cells.get(cell_id)
        if before_cell is None:
            add('cell_add', cell_id, None, after_cell)
            continue
        if after_cell is None:
            add('cell_remove', cell_id, before_cell, None)
            continue
        cell_sources = _refs((before_cell.field_sources, after_cell.field_sources))
        add('ports_change', cell_id, before_cell.ports, after_cell.ports, extra_sources=cell_sources)
        add('globals_change', cell_id, before_cell.globals, after_cell.globals, extra_sources=cell_sources)
        before_devices = {d.id: d for d in before_cell.devices}
        after_devices = {d.id: d for d in after_cell.devices}
        for device_id in sorted(set(before_devices) | set(after_devices), key=lambda d: d.name):
            before_device, after_device = before_devices.get(device_id), after_devices.get(device_id)
            if before_device is None:
                add('device_add', device_id, None, after_device)
                continue
            if after_device is None:
                add('device_remove', device_id, before_device, None)
                continue
            device_sources = _refs((before_device.field_sources, after_device.field_sources))
            add('model_change', device_id, before_device.model, after_device.model, extra_sources=device_sources)
            add('terminals_change', device_id, before_device.terminals, after_device.terminals)
            before_parameters = {p.axis: p for p in before_device.parameters}
            after_parameters = {p.axis: p for p in after_device.parameters}
            for axis in sorted(set(before_parameters) | set(after_parameters)):
                add('parameter_change', device_id, before_parameters.get(axis), after_parameters.get(axis), axis=axis)
        before_nets = {n.id: n for n in before_cell.nets}
        after_nets = {n.id: n for n in after_cell.nets}
        for net_id in sorted(set(before_nets) | set(after_nets), key=lambda n: n.name):
            before_net, after_net = before_nets.get(net_id), after_nets.get(net_id)
            if before_net is None:
                add('net_add', net_id, None, after_net)
            elif after_net is None:
                add('net_remove', net_id, before_net, None)
            else:
                add('net_membership_change', net_id, before_net, after_net)
    return tuple(sorted(differences, key=lambda d: (d.op_type, d.operand_ref.id, d.axis or '', d.delta_id.value)))
