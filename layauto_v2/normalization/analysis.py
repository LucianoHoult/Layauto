"""Pure orchestration of authenticated single-cell analysis. No filesystem IO."""
from __future__ import annotations

from dataclasses import fields, replace
from datetime import datetime
from typing import cast

from layauto_v2.domain.analysis import (
    LocalAnalysis, AnalysisFacet, AnalysisFacets, AnalysisTerminal, SelectedAnalysis,
)
from layauto_v2.domain.analysis_annotation import AnalysisAnnotationBinding
from layauto_v2.domain.channel_identity import ChannelProblem, ChannelSeed
from layauto_v2.domain.circuit import semantic_value
from layauto_v2.domain.codec import FrozenMap, digest, Value
from layauto_v2.domain.evidence import EvidenceRecord, SourceFile
from layauto_v2.domain.geometry import GEOMETRY_COMPARATOR, mapping, sequence
from layauto_v2.domain.net_annotation import NetEvidence, AnnotationProblem
from layauto_v2.domain.regions import RegionProblem
from layauto_v2.domain.local_connectivity import ContactProblem
from layauto_v2.domain.results import InputError, EvidenceIssue, Category as LiteralCategory
from layauto_v2.domain.terminal_relations import validate_terminal_graph
from layauto_v2.importers.analysis_reader import _analysis_doc, captured_analysis_files
from layauto_v2.importers.reader import _body, _binding, _doc
from layauto_v2.state.analysis_annotation import AnalysisAnnotationDraft
from layauto_v2.state.layout_store import build_layout
from layauto_v2.state.coordinate import build_partition
from layauto_v2.state.occupancy import build_occupancy
from layauto_v2.state.regions import build_effective_draft
from layauto_v2.state.local_connectivity import build_local_connectivity_draft
from layauto_v2.annotation.net_regions import build_annotation_operands
from layauto_v2.derive.channel_identity import build_channel_identity_draft
from layauto_v2.derive.body_relations import BodyProblem, evaluate_body_operands
from layauto_v2.derive.terminal_relations import terminal_operands
from .analysis_input import LocalAnalysisReceipt
from .semantic import build_source_operands
from .identity import join_source_operands, NormalizationError
from ._validation import source_admission_problem


__all__: list[str] = []  # Internal wrappers; only the facade is public.


def analyze_local(receipt: LocalAnalysisReceipt) -> LocalAnalysis:
    evidence = receipt.evidence
    assert evidence.value is not None
    value = evidence.value
    records = {record.kind: record for record in evidence.records}
    tech = mapping(value['tech'])
    sources = records['tech'].sources
    def owner(name: str) -> EvidenceRecord:
        return EvidenceRecord(name, mapping(tech[name]), (sources[1 + ('drawn', 'derived', 'physical', 'formats', 'coordinate', 'rules').index(name)],))
    refs = tuple(s.ref() for s in evidence.captures)
    dependencies = {'drawn': ('authenticated_gds',), 'effective': ('drawn',), 'local_graph': ('effective',),
                    'channel_fin': ('local_graph', 'source_identity'), 'annotation': ('local_graph', 'source_identity'),
                    'terminals': ('channel_fin', 'annotation')}
    facets = {name: AnalysisFacet('not_evaluated', None, dependencies=dependencies[name], evidence_refs=refs)
              for name in ('drawn', 'effective', 'local_graph', 'channel_fin', 'annotation', 'terminals')}
    def available(name: str, result: object, issues: tuple[EvidenceIssue, ...] = ()) -> None:
        facets[name] = AnalysisFacet('error' if issues else 'available', result, issues, evidence_refs=refs)
    source = build_source_operands(records['source_cdl'], tech, mapping(value['header']), mapping(value['tech_bundle']))
    semantic_issue = source_admission_problem(value, source, sources, records['header'].sources[0])
    identities = None
    semantic_issues: tuple[EvidenceIssue, ...] = ()
    if semantic_issue is not None:
        category, code, message, ref = semantic_issue
        semantic_issues = (EvidenceIssue('binding' if category == 'identity' else cast('LiteralCategory', category), code, message, ref),)
    else:
        try:
            identities = join_source_operands(value, records['header'].sources[0], source)
        except NormalizationError as exc:
            issue = exc.issue
            semantic_issues = (EvidenceIssue('binding' if issue.category == 'identity' else issue.category, issue.code, issue.message, issue.source),)
    try:
        formats = mapping(tech['formats'])
        if mapping(formats['geometry_capability'])['comparator'] != GEOMETRY_COMPARATOR:
            raise InputError('unsupported', 'UnsupportedGeometryComparator', 'selected comparator is not implemented', owner('formats').sources[0])
        layout = build_layout(records['gds'], owner('drawn'), owner('formats'))
        base = build_occupancy(build_partition(layout))
        available('drawn', base)
        effective = build_effective_draft(base, owner('physical'))
        available('effective', effective)
        local = build_local_connectivity_draft(effective, owner('rules'))
        available('local_graph', local)
    except (RegionProblem, ContactProblem, InputError) as exc:
        name = 'drawn' if facets['drawn'].status == 'not_evaluated' else 'effective' if facets['effective'].status == 'not_evaluated' else 'local_graph'
        available(name, None, (exc.issue,))
        # Identity admission ran independently of geometry. Its consumers are
        # still blocked on the graph, but their source prerequisite was checked.
        if semantic_issues:
            for consumer in ('channel_fin', 'annotation'):
                facets[consumer] = replace(facets[consumer], issues=semantic_issues)
        return LocalAnalysis(receipt.ref, source, AnalysisFacets(**facets))
    if identities is None:
        available('channel_fin', None, semantic_issues)
        available('annotation', None, semantic_issues)
        return LocalAnalysis(receipt.ref, source, AnalysisFacets(**facets))
    devices, nets, device_seeds, net_seeds = identities
    by_device = {row.device_id: row for row in devices}
    channel_seeds = tuple(ChannelSeed(row.semantic_id, row.query_key, row.record, by_device[row.semantic_id].provenance) for row in device_seeds)
    try:
        channel = build_channel_identity_draft(local, source, channel_seeds, owner('derived'))
        available('channel_fin', channel, channel.issues)
    except ChannelProblem as exc:
        available('channel_fin', None, (exc.issue,))
    by_net = {row.net_id: row for row in nets}
    net_evidence = tuple(sorted((NetEvidence(row.semantic_id, row.query_key, row.record, by_net[row.semantic_id].provenance) for row in net_seeds), key=lambda row: row.ref.sha256))
    try:
        binding = AnalysisAnnotationBinding(local.ref, effective.ref, layout.ref, layout.units.ref,
            base.partition.ref, layout.units.canonical_tick_nm, layout.top, source.selected_cell,
            digest(semantic_value(source)), source.preservation.sources[0], owner('derived'), owner('drawn'),
            local.components, tuple(sorted((row.id for row in layout.records), key=lambda row: row.sha256)),
            tuple(row.ref for row in net_evidence), FrozenMap({'schema': 'layauto-analysis-capture-binding/1',
                'local_receipt_sha256': receipt.ref, 'sources': tuple(FrozenMap({'uri': s.uri, 'sha256': s.sha256}) for s in evidence.captures)}))
        annotation = AnalysisAnnotationDraft(binding, net_evidence, *build_annotation_operands(local, source, net_evidence, binding))
        available('annotation', annotation, tuple(row.issue for row in annotation.issues))
    except AnnotationProblem as exc:
        available('annotation', None, (exc.issue,))
    return LocalAnalysis(receipt.ref, source, AnalysisFacets(**facets))


def selected_analysis(receipt: LocalAnalysisReceipt, local: LocalAnalysis, field: str,
                      source: SourceFile | None, read_issues: tuple[EvidenceIssue, ...],
                      aliases: FrozenMap) -> SelectedAnalysis:
    evidence = receipt.evidence
    assert evidence.value is not None
    config = mapping(evidence.value['config'])
    selection = mapping(config.get(field, FrozenMap({'kind': 'not_selected'})))
    kind = selection['kind']
    scope = 'manual_expectation' if field == 'manual_intent' else 'external_readonly'
    if kind == 'not_selected':
        return SelectedAnalysis('not_selected', selection, scope=scope)
    if kind in ('trusted_lvs_freeze', 'geometry_window'):
        return SelectedAnalysis('unsupported', selection, issues=(EvidenceIssue('unsupported', 'UnsupportedExternalEvidenceKind',
            'no validator for selected external evidence kind', next(r.sources[0] for r in evidence.records if r.kind == 'config')),), scope=scope)
    if source is None:
        code = 'SelectedManualUnavailable' if field == 'manual_intent' else 'SelectedBodyUnavailable'
        issues = tuple(i for i in read_issues if i.code == code)
        if not issues:
            issues = tuple(i for i in read_issues if i.source.uri == selection['uri'])
        return SelectedAnalysis('error', selection, issues=issues, scope=scope)
    selected_read_issues = tuple(i for i in read_issues if i.source.uri == source.uri)
    if selected_read_issues:
        return SelectedAnalysis('error', selection, issues=selected_read_issues, evidence_refs=(source.ref(),), scope=scope)
    validate_terminal_graph(source, (SourceFile,))
    if SourceFile(source.uri, source.data) != source:
        raise ValueError('selected capture differs from actual bytes')
    files = captured_analysis_files(evidence.root, aliases)
    records = {r.kind: r for r in evidence.records}
    gds_ref = records['gds'].sources[0]
    gds = next(s for s in evidence.captures if s.ref() == gds_ref)
    netlist = next(s for s in evidence.captures if s.ref() == records['source_cdl'].sources[0])
    tech = mapping(evidence.value['tech'])
    formats = mapping(mapping(tech['formats'])['limits'])
    try:
        # New selected evidence must retain its first acquisition role. An alias
        # cannot reinterpret an already captured local role as a body/manual file.
        if source.uri in {s.uri for s in evidence.captures}:
            raise InputError('binding', 'SelectedEvidenceRoleMismatch', 'external document aliases a local input role', source.ref())
        max_bytes, max_depth = cast(int, formats['max_bytes_per_text_file']), cast(int, formats['max_json_depth'])
        if field == 'manual_intent':
            doc = _analysis_doc(source, 'analysis_manual', max_bytes, max_depth)
            _binding(files, mapping(doc['source_layout']), gds, source, '/source_layout', 'ManualSourceBindingMismatch')
            _binding(files, mapping(doc['source_netlist']), netlist, source, '/source_netlist', 'ManualSourceBindingMismatch')
            if local.source is None or doc['cell'] != local.source.selected_cell.name:
                raise InputError('binding', 'ManualSourceBindingMismatch', 'manual cell differs from selected source', source.ref(field='/cell'))
            devices = {d.id.name for c in local.source.cells if c.id == local.source.selected_cell for d in c.devices}
            seen: set[tuple[Value, Value]] = set()
            for row in (mapping(v) for v in sequence(doc['assertions'])):
                if row['device'] not in devices or (row['device'], row['role']) in seen:
                    raise InputError('binding', 'ManualDeviceBindingMismatch', 'manual device is foreign or repeated', source.ref(field='/assertions'))
                seen.add((row['device'], row['role']))
            try:
                created = datetime.fromisoformat(cast(str, doc['created_at']).replace('Z', '+00:00'))
            except ValueError as exc:
                raise InputError('config', 'InvalidDeclarationTimestamp', 'created_at requires a UTC timestamp', source.ref(field='/created_at')) from exc
            offset = created.utcoffset()
            if offset is None or offset.total_seconds() != 0:
                raise InputError('config', 'InvalidDeclarationTimestamp', 'created_at requires a UTC timestamp', source.ref(field='/created_at'))
            pointers = ['/author', '/created_at', '/cell', '/instance_hint',
                        '/source_layout/uri', '/source_layout/sha256',
                        '/source_netlist/uri', '/source_netlist/sha256']
            for index, _ in enumerate(sequence(doc['assertions'])):
                pointers.extend('/assertions/' + str(index) + suffix for suffix in
                                ('', '/device', '/role', '/expected_supply_label'))
            return SelectedAnalysis('declared', selection, doc,
                evidence_refs=(source.ref(),) + tuple(source.ref(field=pointer) for pointer in pointers), scope=scope)
        body = _doc(source, 'body', max_bytes, max_depth)
        _body(body, source, files, gds, cast(str, mapping(evidence.value['gds'])['top']), tech)
        if any(local.facets[n].value is None for n in ('channel_fin', 'annotation')):
            return SelectedAnalysis('not_evaluated', selection, body, evidence_refs=(source.ref(),),
                dependencies=('channel_fin', 'annotation'), scope=scope)
        from layauto_v2.derive.channel_identity import ChannelIdentityDraft
        from layauto_v2.state.analysis_annotation import AnalysisAnnotationDraft
        channels = cast(ChannelIdentityDraft, local.facets.channel_fin.value)
        annotation = cast(AnalysisAnnotationDraft, local.facets.annotation.value)
        allowed = {(s.uri, s.sha256) for s in (*evidence.captures, source)}
        result, issues = evaluate_body_operands(channels, annotation, EvidenceRecord('body', body, (source.ref(), gds.ref())), cast(set[tuple[Value, Value]], allowed))
        return SelectedAnalysis('evaluated', selection, result, issues, (source.ref(), gds.ref()), scope=scope)
    except (InputError, BodyProblem) as exc:
        return SelectedAnalysis('error', selection, issues=(exc.issue,), evidence_refs=(source.ref(),), scope=scope)


def analyze_terminals(local: LocalAnalysis, body: SelectedAnalysis) -> AnalysisFacet:
    if local.facets.channel_fin.status != 'available' or local.facets.annotation.value is None:
        return AnalysisFacet('not_evaluated', None, dependencies=('channel_fin', 'annotation'))
    from layauto_v2.derive.channel_identity import ChannelIdentityDraft
    from layauto_v2.state.local_connectivity import LocalConnectivityDraft
    assert local.source is not None
    channels = cast(ChannelIdentityDraft, local.facets.channel_fin.value)
    annotation = cast(AnalysisAnnotationDraft, local.facets.annotation.value)
    graph = cast(LocalConnectivityDraft, local.facets.local_graph.value)
    body_value = body.value if body.status == 'evaluated' else None
    binding = digest(FrozenMap({'schema': 'layauto-analysis-terminals/1', 'local_receipt_sha256': local.receipt_ref,
        'annotation': annotation.ref.to_value(), 'external_body': body_value}))
    rows = terminal_operands(graph, local.source, channels, annotation, body_value)
    terminals = tuple(AnalysisTerminal(binding, **{f.name: getattr(row, f.name) for f in fields(row)}) for row in rows)
    return AnalysisFacet('error' if local.facets.annotation.issues else 'available', terminals, local.facets.annotation.issues, evidence_refs=local.facets.annotation.evidence_refs + body.evidence_refs)
