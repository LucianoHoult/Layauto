"""Single immutable owner of drawn geometry in an evidence-consistent draft.

This is neither a committed snapshot nor an authenticated input receipt. The
normalization aggregate checks the preserved evidence against actual captures.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from layauto_v2.domain.codec import FrozenMap, digest, canonical_bytes
from layauto_v2.domain.evidence import EvidenceRecord, SourceRef
from layauto_v2.domain.geometry import (
    VERSION, GEOMETRY_COMPARATOR, DrawnRecord, GeometryRecordId, GeometryRef,
    LayerPolicy, Rect, StreamLayerKey, UnitBinding, evidence_value, integer,
    mapping, record_identity, sequence, text, version,
)
from layauto_v2.tech.schema import validate_payload


def _one(record: EvidenceRecord, kind: str) -> SourceRef:
    if type(record) is not EvidenceRecord or record.kind != kind or len(record.sources) != 1:
        raise ValueError('layout requires one preserved source for ' + kind)
    return record.sources[0]


def _materialize(gds: EvidenceRecord, drawn: EvidenceRecord, formats: EvidenceRecord
                 ) -> tuple[UnitBinding, tuple[LayerPolicy, ...], tuple[DrawnRecord, ...]]:
    gds_source, drawn_source, formats_source = _one(gds, 'gds'), _one(drawn, 'drawn'), _one(formats, 'formats')
    validate_payload(drawn.payload, 'drawn')
    validate_payload(formats.payload, 'formats')
    doc = gds.payload
    if (set(doc) != {'schema_version', 'top', 'library', 'library_timestamps', 'cell_timestamps',
                     'elements', 'units', 'stream_record_count', 'source', 'raw_document'}
            or doc['schema_version'] != 'layauto-gds-evidence/1'):
        raise ValueError('invalid preserved GDS schema')
    top = text(doc['top'])
    text(doc['library'])
    for name in ('library_timestamps', 'cell_timestamps'):
        timestamp = doc[name]
        if type(timestamp) is not bytes or len(timestamp) != 24:
            raise ValueError('invalid GDS timestamp preservation')
    raw = doc['raw_document']
    if type(raw) is not bytes or hashlib.sha256(raw).hexdigest() != gds_source.sha256:
        raise ValueError('GDS preservation bytes do not match source hash')
    if doc['source'] != {'uri': gds_source.uri, 'sha256': gds_source.sha256}:
        raise ValueError('GDS preservation belongs to another source')
    capability = mapping(formats.payload['geometry_capability'])
    if capability['comparator'] != GEOMETRY_COMPARATOR:
        raise ValueError('unsupported geometry semantic comparator')
    unit = UnitBinding(mapping(formats.payload['unit_scale_contract']), mapping(doc['units']),
                       SourceRef(formats_source.uri, formats_source.sha256, field='/unit_scale_contract'))
    policies = tuple(LayerPolicy(mapping(row), SourceRef(drawn_source.uri, drawn_source.sha256, field=f'/layers/{i}'))
                     for i, row in enumerate(sequence(drawn.payload['layers'])))
    by_name = {policy.name: policy for policy in policies}
    keys = [mapping(policy.declaration['stream_key']) for policy in policies]
    if len(by_name) != len(policies) or len({canonical_bytes(key) for key in keys}) != len(keys):
        raise ValueError('duplicate layout layer name or stream key')
    elements = sequence(doc['elements'])
    if integer(doc['stream_record_count']) != 8 + 5 * len(elements):
        raise ValueError('GDS record count disagrees with preserved elements')
    records: list[DrawnRecord] = []
    for i, value in enumerate(elements):
        row = mapping(value)
        if set(row) != {'element', 'layer', 'datatype', 'canonical_layer', 'xy', 'bbox',
                        'byte_offset', 'record_index', 'xy_byte_offset', 'xy_record_index', 'byte_length'}:
            raise ValueError('unknown or missing preserved BOUNDARY fields')
        layer = text(row['canonical_layer'])
        if layer not in by_name:
            raise ValueError('drawn record refers to an unknown layer policy')
        policy = by_name[layer]
        key = StreamLayerKey(text(row['element']), integer(row['layer']), integer(row['datatype']))
        if key.to_value() != policy.declaration['stream_key']:
            raise ValueError('drawn stream key differs from selected layer policy')
        offset, ordinal = integer(row['byte_offset']), integer(row['record_index'])
        if ordinal != 6 + 5 * i or offset < 0 or offset + integer(row['byte_length']) > len(raw):
            raise ValueError('drawn source record position is inconsistent')
        if integer(row['xy_record_index']) != ordinal + 3 or not offset < integer(row['xy_byte_offset']) < offset + integer(row['byte_length']):
            raise ValueError('drawn XY position is inconsistent')
        source = SourceRef(gds_source.uri, gds_source.sha256, byte_offset=offset, record_index=ordinal)
        pairs = tuple(sequence(pair) for pair in sequence(row['xy']))
        if any(len(pair) != 2 for pair in pairs):
            raise ValueError('drawn XY requires coordinate pairs')
        points = tuple((integer(pair[0]), integer(pair[1])) for pair in pairs)
        bounds = tuple(unit.source_to_canonical(integer(c)) for c in sequence(row['bbox']))
        if len(bounds) != 4:
            raise ValueError('drawn bounding rectangle requires four coordinates')
        records.append(DrawnRecord(record_identity(source, top), top, key, policy.name,
                                   text(policy.declaration['purpose']), source, points, Rect(*bounds),
                                   unit.ref, policy.ref, row))
    return unit, tuple(sorted(policies, key=lambda p: p.name)), tuple(records)


@dataclass(frozen=True)
class LayoutDraft:
    gds: EvidenceRecord
    drawn: EvidenceRecord
    formats: EvidenceRecord
    units: UnitBinding
    policies: tuple[LayerPolicy, ...]
    records: tuple[DrawnRecord, ...]
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        version(self.schema_version)
        for name, cls in (('policies', LayerPolicy), ('records', DrawnRecord)):
            values = getattr(self, name)
            if not isinstance(values, (tuple, list)) or any(type(v) is not cls for v in values):
                raise ValueError('invalid layout ' + name)
            object.__setattr__(self, name, tuple(values))
        if type(self.units) is not UnitBinding:
            raise ValueError('layout requires exact unit binding')
        expected_unit, expected_policies, expected_records = _materialize(self.gds, self.drawn, self.formats)
        if self.units != expected_unit or self.policies != expected_policies or self.records != expected_records:
            raise ValueError('layout omitted, duplicated or changed captured geometry/policy/unit facts')

    @property
    def top(self) -> str:
        return text(self.gds.payload['top'])

    @property
    def ref(self) -> GeometryRef:
        return GeometryRef('layout', digest(self.to_value()))

    @property
    def semantic_digest(self) -> str:
        # The declared comparator ignores stream order / rectangle start and
        # direction, but never top, stream keys, exact physical size or count.
        rows = [FrozenMap({'stream_key': record.stream_key.to_value(),
                           'bbox_nm': tuple(self.units.canonical_to_nm(c) for c in record.rect.bounds)})
                for record in self.records]
        return digest({'schema': 'layauto-geometry-semantic/1', 'comparator': GEOMETRY_COMPARATOR,
                       'top': self.top, 'records': tuple(sorted(rows, key=canonical_bytes))})

    def record(self, identity: GeometryRecordId) -> DrawnRecord:
        if type(identity) is not GeometryRecordId:
            raise ValueError('record lookup requires a typed geometry identity')
        for record in self.records:
            if record.id == identity:
                return record
        raise KeyError(identity)

    def policy(self, name: str) -> LayerPolicy:
        for policy in self.policies:
            if policy.name == name:
                return policy
        raise KeyError(name)

    def to_value(self) -> FrozenMap:
        return FrozenMap({'schema': self.schema_version, 'gds': evidence_value(self.gds),
                          'drawn': evidence_value(self.drawn), 'formats': evidence_value(self.formats),
                          'units': self.units.to_value(), 'policies': tuple(p.to_value() for p in self.policies),
                          'records': tuple(record.to_value() for record in self.records)})


def build_layout(gds: EvidenceRecord, drawn: EvidenceRecord, formats: EvidenceRecord) -> LayoutDraft:
    units, policies, records = _materialize(gds, drawn, formats)
    return LayoutDraft(gds, drawn, formats, units, policies, records)
