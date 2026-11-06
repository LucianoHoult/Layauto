"""Pure exact local contact graph and independent enclosure facts.

The finite scan uses effective regions directly, including CUT boundaries absent
from raw occupancy axes. This draft is neither published state nor net assurance.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Literal, cast

from layauto_v2.domain.codec import FrozenMap, canonical_bytes, digest
from layauto_v2.domain.evidence import EvidenceRecord
from layauto_v2.domain.geometry import Rect, mapping, sequence
from layauto_v2.domain.local_connectivity import (
    CONNECTOR_PAIRS, CONSUMED_PHYSICAL, LOCAL_TYPES, SCOPE, VERSION,
    ContactComponent, ContactEdge, ContactNode, EnclosureSide, LocalContactBinding,
    LocalRef, contact_problem, record_tuple,
)
from layauto_v2.domain.regions import (
    ExactRegion, OperatorBinding, RecordRegions, RegionPiece, validate_closed_graph,
)
from layauto_v2.tech.schema import SchemaError, validate_payload
from .regions import EffectiveDraft, _BASE_TYPES


def same_layer_contact(a: tuple[Rect, ...], b: tuple[Rect, ...]) -> bool:
    """Positive area or positive length shared edge; never point contact."""
    if type(a) is not tuple or type(b) is not tuple or any(type(rect) is not Rect for rect in a + b):
        raise ValueError('contact requires exact rectangle tuples')
    validate_closed_graph(a + b, (Rect,))
    for left in a:
        for right in b:
            width = min(left.x1, right.x1) - max(left.x0, right.x0)
            height = min(left.y1, right.y1) - max(left.y0, right.y0)
            if width > 0 and height >= 0 or height > 0 and width >= 0:
                return True
    return False


def encloses_connector(rectangles: tuple[Rect, ...], connector: Rect, margin_ticks: Fraction) -> bool:
    """Cover the exact rational expansion through x slabs and y intervals.

    Every target slab must have uninterrupted coverage of its whole y interval.
    This accepts coverage across pieces and rejects holes without a bbox/area
    proxy. No physical coordinate is floored, snapped or converted through float.
    """
    if (type(rectangles) is not tuple or any(type(rect) is not Rect for rect in rectangles)
            or type(connector) is not Rect or type(margin_ticks) is not Fraction):
        raise ValueError('enclosure requires exact rectangles and a nonnegative Fraction margin')
    validate_closed_graph((rectangles, connector, margin_ticks), (Rect,))
    if margin_ticks < 0:
        raise ValueError('enclosure margin must be nonnegative')
    x0, y0 = connector.x0 - margin_ticks, connector.y0 - margin_ticks
    x1, y1 = connector.x1 + margin_ticks, connector.y1 + margin_ticks
    xs = sorted({x0, x1} | {Fraction(x) for rect in rectangles for x in (rect.x0, rect.x1) if x0 < x < x1})
    for left, right in zip(xs, xs[1:]):
        intervals = sorted((max(y0, Fraction(rect.y0)), min(y1, Fraction(rect.y1)))
                           for rect in rectangles if rect.x0 <= left and right <= rect.x1
                           and max(y0, Fraction(rect.y0)) < min(y1, Fraction(rect.y1)))
        cursor = y0
        for low, high in intervals:
            if low > cursor:
                return False
            cursor = max(cursor, high)
            if cursor >= y1:
                break
        if cursor < y1:
            return False
    return True


_ROLES = {'OD': 'diffusion', 'LI': 'interconnect', 'POLY': 'gate', 'M1': 'interconnect',
          'BODY_N': 'body', 'BODY_P': 'body', 'CONTACT': 'contact', 'VIA0': 'via', 'GCONTACT': 'contact'}
_T05 = FrozenMap({
    'id': 'T05.contact_enclosure',
    'scope': 'local CONTACT,VIA0,GCONTACT; separately context BTAP_N/BTAP_P',
    'predicate': 'exactly one region on each side encloses connector >=1 nm on all sides',
    'relation_basis': 'geometry_only', 'schema_version': 'w004-toy-rule/2', 'unit': 'nm',
    'parameters': {'enclosure_nm': 1},
    'exact_evaluator_ref': 'w004-toy-predicate/T05.contact_enclosure/2',
    'required_relation_assurance': 'none', 'missing_context_policy': 'reject_indeterminate', 'required': True,
})


def _check_owners(binding: LocalContactBinding) -> None:
    for owner, kind in ((binding.physical, 'physical'), (binding.drawn, 'drawn'), (binding.rules, 'rules')):
        try:
            validate_payload(owner.payload, kind)
        except SchemaError as exc:
            raise contact_problem(owner.sources[0], exc.path or '/',
                                  'invalid local contact owner: ' + str(exc)) from exc
    operators = mapping(binding.physical.payload['operators'])
    required = sequence(binding.physical.payload['required_operator_refs'])
    for name, expected in CONSUMED_PHYSICAL.items():
        if operators.get(name) != expected or name not in required:
            raise contact_problem(binding.physical.sources[0], '/operators/' + name.replace('/', '~1'),
                                  'unsupported or unavailable consumed contact operator')
    rows = tuple(mapping(row) for row in sequence(binding.drawn.payload['layers']))
    for name, role in _ROLES.items():
        matches = [(index, row) for index, row in enumerate(rows) if row.get('name') == name]
        if len(matches) != 1:
            raise contact_problem(binding.drawn.sources[0], '/layers', 'local contact layer must resolve uniquely: ' + name)
        index, row = matches[0]
        for field, expected in (('role', role), ('purpose', 'drawing')):
            if row.get(field) != expected:
                raise contact_problem(binding.drawn.sources[0], f'/layers/{index}/{field}',
                                      'unsupported local contact layer semantics: ' + name)
        if name in CONNECTOR_PAIRS:
            for field, expected in (('electrical_connects', CONNECTOR_PAIRS[name]),
                                    ('contact_predicate', 'positive_area_overlap_with_exactly_one_effective_region_on_each_side'),
                                    ('enclosure_rule', 'T05.contact_enclosure')):
                if row.get(field) != expected:
                    raise contact_problem(binding.drawn.sources[0], f'/layers/{index}/{field}',
                                          'unsupported local connector declaration: ' + name)
        elif any(field in row for field in ('electrical_connects', 'contact_predicate', 'enclosure_rule')):
            raise contact_problem(binding.drawn.sources[0], f'/layers/{index}',
                                  'conductor cannot add an undeclared cross-layer contact')
    for index, row in enumerate(rows):
        if row['name'] in ('BTAP_N', 'BTAP_P'):
            continue  # External operator declarations are retained, not executed.
        if row['role'] in ('diffusion', 'interconnect', 'gate', 'body', 'contact', 'via', 'body_contact') and row['name'] not in _ROLES:
            raise contact_problem(binding.drawn.sources[0], f'/layers/{index}',
                                  'additional conductive/connector layer is outside the local subset')
        if row['name'] not in _ROLES and any(field in row for field in ('electrical_connects', 'contact_predicate', 'enclosure_rule')):
            raise contact_problem(binding.drawn.sources[0], f'/layers/{index}',
                                  'undeclared local cross-layer contact')
    rules = tuple(mapping(row) for row in sequence(binding.rules.payload['rules']))
    matches = [(index, row) for index, row in enumerate(rules) if row.get('id') == 'T05.contact_enclosure']
    if len(matches) != 1:
        raise contact_problem(binding.rules.sources[0], '/rules', 'local T05 rule must resolve uniquely')
    index, rule = matches[0]
    for field, expected in _T05.items():
        if rule.get(field) != expected:
            raise contact_problem(binding.rules.sources[0], f'/rules/{index}/{field}',
                                  'unsupported consumed local T05 enclosure semantics')


def _require_effective(effective: EffectiveDraft) -> None:
    if type(effective) is not EffectiveDraft:
        raise ValueError('local graph requires a complete neutral effective draft')
    validate_closed_graph(effective, DRAFT_TYPES)
    # Reconstruct neutral aggregate coverage; this does not authenticate captures.
    rebuilt = EffectiveDraft(effective.base, effective.operators, effective.records, effective.schema_version)
    if rebuilt != effective:
        raise ValueError('local graph input is not a self-consistent effective draft')


def _binding(effective: EffectiveDraft, rules: EvidenceRecord) -> LocalContactBinding:
    layout = effective.base.layout
    binding = LocalContactBinding(effective.physical, layout.drawn, rules, effective.ref,
                                  layout.units.ref, layout.top)
    _check_owners(binding)
    return binding


def _nodes(effective: EffectiveDraft, binding: LocalContactBinding) -> tuple[ContactNode, ...]:
    nodes: list[ContactNode] = []
    reference = binding.ref
    for record in effective.base.layout.records:
        if record.layer in ('BTAP_N', 'BTAP_P'):
            raise contact_problem(record.source, '/local_body_contact',
                                  'nonempty local BTAP requires a future body capability', 'UnsupportedLocalBodyContact')
        if record.layer in ('OD', 'LI'):
            regions = tuple(region for region in effective.for_record(record.id).regions if region.role != 'channel')
        elif record.layer in ('POLY', 'M1', 'BODY_N', 'BODY_P'):
            regions = (ExactRegion(record.id, 'effective', (), record.unit_ref, effective.operators.ref, (record.rect,)),)
        else:
            continue
        nodes.extend(ContactNode(record.layer, region, reference) for region in regions)
    return tuple(sorted(nodes, key=lambda node: node.ref.sha256))


def _edges(effective: EffectiveDraft, binding: LocalContactBinding, nodes: tuple[ContactNode, ...]
           ) -> tuple[tuple[ContactEdge, ...], tuple[EnclosureSide, ...]]:
    edges: list[ContactEdge] = []
    audits: list[EnclosureSide] = []
    reference = binding.ref
    node_refs = {node.ref: node for node in nodes}
    for index, node in enumerate(nodes):
        for other in nodes[index + 1:]:
            if node.layer == other.layer and same_layer_contact(node.region.rectangles, other.region.rectangles):
                endpoints = tuple(sorted((node.ref, other.ref), key=lambda ref: ref.sha256))
                edges.append(ContactEdge('same_layer', endpoints, reference))
    margin = Fraction(1, effective.base.layout.units.canonical_tick_nm)
    for connector in sorted(effective.base.layout.records, key=lambda record: record.id.sha256):
        if connector.layer not in CONNECTOR_PAIRS:
            continue
        ends: list[LocalRef] = []
        for side, layer in enumerate(cast(tuple[str, ...], CONNECTOR_PAIRS[connector.layer])):
            candidates = tuple(node.ref for node in nodes if node.layer == layer
                               and any(piece.intersection(connector.rect) is not None for piece in node.region.rectangles))
            if len(candidates) != 1:
                raise contact_problem(connector.source, f'/electrical_connects/{side}',
                                      f'connector requires exactly one independent {layer} region; found {len(candidates)}',
                                      'AmbiguousConnectorEndpoint')
            endpoint = candidates[0]
            node = node_refs[endpoint]
            ends.append(endpoint)
            status: Literal['pass', 'violation'] = ('pass' if encloses_connector(node.region.rectangles, connector.rect, margin)
                                                    else 'violation')
            audits.append(EnclosureSide(connector.id, endpoint, node.layer, margin, status, reference))
        edges.append(ContactEdge('connector', tuple(sorted(ends, key=lambda ref: ref.sha256)), reference, connector.id))
    return (tuple(sorted(edges, key=lambda edge: edge.ref.sha256)),
            tuple(sorted(audits, key=lambda audit: audit.ref.sha256)))


def _components(binding: LocalContactBinding, nodes: tuple[ContactNode, ...], edges: tuple[ContactEdge, ...]
                ) -> tuple[ContactComponent, ...]:
    neighbors: dict[LocalRef, set[LocalRef]] = {node.ref: set() for node in nodes}
    for edge in edges:
        left, right = edge.endpoints
        neighbors[left].add(right)
        neighbors[right].add(left)
    remaining = set(neighbors)
    groups: list[ContactComponent] = []
    while remaining:
        seed = min(remaining, key=lambda ref: ref.sha256)
        pending, members = [seed], set((seed,))
        remaining.remove(seed)
        while pending:
            for neighbor in neighbors[pending.pop()]:
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    members.add(neighbor)
                    pending.append(neighbor)
        groups.append(ContactComponent(tuple(sorted(members, key=lambda ref: ref.sha256)), binding.ref))
    return tuple(sorted(groups, key=lambda component: component.ref.sha256))


@dataclass(frozen=True)
class LocalConnectivityDraft:
    effective: EffectiveDraft
    binding: LocalContactBinding
    nodes: tuple[ContactNode, ...]
    edges: tuple[ContactEdge, ...]
    audits: tuple[EnclosureSide, ...]
    components: tuple[ContactComponent, ...]
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        if type(self.schema_version) is not str or self.schema_version != VERSION:
            raise ValueError('unsupported local connectivity draft schema')
        _require_effective(self.effective)
        if type(self.binding) is not LocalContactBinding:
            raise ValueError('local graph requires a typed operator binding')
        for name, cls in (('nodes', ContactNode), ('edges', ContactEdge), ('audits', EnclosureSide), ('components', ContactComponent)):
            object.__setattr__(self, name, record_tuple(getattr(self, name), cls, name))
        validate_closed_graph(self, DRAFT_TYPES)
        binding = _binding(self.effective, self.binding.rules)
        if self.binding != binding:
            raise ValueError('local graph contains foreign source/scope/unit/operator binding')
        nodes = _nodes(self.effective, binding)
        edges, audits = _edges(self.effective, binding, nodes)
        components = _components(binding, nodes, edges)
        if (self.nodes, self.edges, self.audits, self.components) != (nodes, edges, audits, components):
            raise ValueError('local graph omitted/added nodes, edges, components or independent enclosure facts')

    @property
    def ref(self) -> LocalRef:
        return LocalRef('draft', digest(self.to_value()))

    @property
    def local_enclosure_status(self) -> Literal['pass', 'violation']:
        return 'violation' if any(audit.status == 'violation' for audit in self.audits) else 'pass'

    @property
    def coverage(self) -> FrozenMap:
        required = sequence(self.binding.physical.payload['required_operator_refs'])
        return FrozenMap({'scope': SCOPE, 'executed_contact_operators': tuple(CONSUMED_PHYSICAL),
                          'executed_rules': ('T05.contact_enclosure:local CONTACT,VIA0,GCONTACT sides only',),
                          'unconsumed_operator_refs': tuple(ref for ref in required if ref not in CONSUMED_PHYSICAL),
                          'deferred': ('external_body_and_BTAP', 'complete_T05_and_mandatory_rule_set',
                                       'manufacturing_coordinates_and_region_occupancy', 'FIN_device_extraction',
                                       'semantic_net_join_and_annotation', 'lifecycle', 'baseline_publication',
                                       'no_change_terminal_and_Stage6'),
                          'node_count': len(self.nodes), 'edge_count': len(self.edges),
                          'connector_record_count': sum(edge.kind == 'connector' for edge in self.edges),
                          'enclosure_side_count': len(self.audits)})

    @property
    def semantic_digest(self) -> str:
        signatures = {node.ref: FrozenMap({'layer': node.layer, 'role': node.region.role,
                                          'rectangles': tuple(rect.bounds for rect in node.region.rectangles)})
                      for node in self.nodes}
        def connector(identity: object) -> FrozenMap | None:
            if identity is None:
                return None
            # The public aggregate has already proven every referenced record.
            for record in self.effective.base.layout.records:
                if record.id == identity:
                    return FrozenMap({'layer': record.layer, 'rect': record.rect.bounds})
            raise ValueError('foreign connector in semantic graph')
        edges = tuple(FrozenMap({'kind': edge.kind,
                                 'endpoints': tuple(sorted((signatures[ref] for ref in edge.endpoints), key=canonical_bytes)),
                                 'connector': connector(edge.connector_id)}) for edge in self.edges)
        components = tuple(tuple(sorted((signatures[ref] for ref in component.members), key=canonical_bytes))
                           for component in self.components)
        audits = tuple(FrozenMap({'connector': connector(audit.connector_id), 'node': signatures[audit.node_ref],
                                  'layer': audit.layer, 'margin_ticks': audit.margin_ticks, 'status': audit.status})
                       for audit in self.audits)
        return digest({'schema': 'layauto-local-connectivity-semantic/1', 'scope': SCOPE,
                       'effective_semantic': self.effective.semantic_digest,
                       'canonical_tick_nm': self.effective.base.layout.units.canonical_tick_nm,
                       'nodes': tuple(sorted(signatures.values(), key=canonical_bytes)),
                       'edges': tuple(sorted(edges, key=canonical_bytes)),
                       'components': tuple(sorted(components, key=canonical_bytes)),
                       'audits': tuple(sorted(audits, key=canonical_bytes))})

    def to_value(self) -> FrozenMap:
        return FrozenMap({'schema': self.schema_version, 'effective_ref': self.effective.ref.to_value(),
                          'binding': self.binding.to_value(), 'nodes': tuple(node.to_value() for node in self.nodes),
                          'edges': tuple(edge.to_value() for edge in self.edges),
                          'audits': tuple(audit.to_value() for audit in self.audits),
                          'components': tuple(component.to_value() for component in self.components),
                          'local_enclosure_status': self.local_enclosure_status, 'coverage': self.coverage})


DRAFT_TYPES = _BASE_TYPES + LOCAL_TYPES + (OperatorBinding, RecordRegions, RegionPiece, EffectiveDraft,
                                         LocalConnectivityDraft)


def build_local_connectivity_draft(effective: EffectiveDraft, rules: EvidenceRecord) -> LocalConnectivityDraft:
    _require_effective(effective)
    binding = _binding(effective, rules)
    nodes = _nodes(effective, binding)
    edges, audits = _edges(effective, binding, nodes)
    return LocalConnectivityDraft(effective, binding, nodes, edges, audits, _components(binding, nodes, edges))
