"""Single public read-only cell analysis entry. No publication or continuation API."""
from __future__ import annotations

from dataclasses import dataclass, fields, replace
from pathlib import Path
from typing import cast, Literal

from layauto_v2.domain.analysis import (
    AnalysisResult, AnalysisFinding, SelectedAnalysis, AnalysisFacets,
)
from layauto_v2.domain.codec import FrozenMap
from layauto_v2.domain.evidence import SourceRef
from layauto_v2.domain.results import EvidenceIssue
from layauto_v2.domain.geometry import mapping
from layauto_v2.importers.analysis_reader import acquire_analysis, acquire_selections
from layauto_v2.normalization.analysis_input import LocalAnalysisReceipt
from layauto_v2.normalization.analysis import analyze_local, selected_analysis, analyze_terminals
from layauto_v2.normalization.analysis_occupancy import OccupancyRequest, OccupancyUnavailable, _project_local
from layauto_v2.state.discrete_occupancy import OccupancyResult
from layauto_v2.reporting.analysis import diagnostic_json, occupancy_summary


@dataclass(frozen=True)
class AnalysisRequest:
    manifest_path: Path


@dataclass(frozen=True)
class CellAnalysisResult(AnalysisResult):
    occupancy: OccupancyResult | OccupancyUnavailable | None = None


__all__ = ['AnalysisRequest', 'OccupancyRequest', 'analyze_cell']

_BLOCKED = ('full_run_admission', 'baseline', 'no_change', 'geometry_commit', 'export_publish', 'parent_voltage_exemption')
_MISSING = ('parent_instance_mapping', 'global_voltage_domain', 'remaining_mandatory')


def _finding(issue: EvidenceIssue, *, violation: bool = False, computation_error: bool = False) -> AnalysisFinding:
    severity: Literal['error', 'unsupported', 'violation', 'mismatch', 'info'] = 'error' if computation_error else 'unsupported' if issue.category == 'unsupported' else 'violation' if violation else 'error'
    return AnalysisFinding('violation' if violation else issue.category, issue.code, issue.source, (issue.source.uri + ('#' + issue.source.field if issue.source.field else ''),), severity, issue.message)


def _finish(result: CellAnalysisResult, request: OccupancyRequest | None,
            receipt: LocalAnalysisReceipt | None = None,
            issues: tuple[EvidenceIssue, ...] = ()) -> CellAnalysisResult:
    roots = {field.name: getattr(result, field.name) for field in fields(result)
             if field.name not in ('report_json', 'captures', 'occupancy')}
    query: OccupancyResult | OccupancyUnavailable | None = None
    if request is not None:
        if receipt is None or result.local is None:
            query = OccupancyUnavailable('not_evaluated', ('local_authentication',), issues)
        else:
            query = _project_local(receipt, result.local, request)
        roots['occupancy'] = occupancy_summary(request, query)
    return replace(result, occupancy=query, report_json=diagnostic_json(roots, result.captures))


def _valid_request(request: AnalysisRequest) -> bool:
    if (type(request) is not AnalysisRequest or set(vars(request)) != {'manifest_path'}
            or not isinstance(request.manifest_path, Path) or not request.manifest_path.is_absolute()
            or not request.manifest_path.name or '\x00' in str(request.manifest_path)):
        return False
    try:
        str(request.manifest_path).encode('utf-8')
    except UnicodeEncodeError:
        return False
    return True


def analyze_cell(request: AnalysisRequest, *, occupancy: OccupancyRequest | None = None) -> CellAnalysisResult:
    """Acquire once and analyze declared synthetic flat-cell evidence.

    Select occupancy to index the local drawn and optionally effective geometry
    within a caller-supplied budget. Inspect its status separately.

    Expected input failures return located diagnostics. Unexpected exceptions,
    KeyboardInterrupt and SystemExit propagate. completed denotes computation,
    never complete verification, a baseline or permission to modify/publish.
    """
    if occupancy is not None and type(occupancy) is not OccupancyRequest:
        raise TypeError('occupancy requires an OccupancyRequest')
    absent = SelectedAnalysis('not_selected', FrozenMap({'kind': 'not_selected'}))
    if not _valid_request(request):
        issue = EvidenceIssue('config', 'InvalidAnalysisRequest', 'requires an exact AnalysisRequest with an absolute manifest Path', SourceRef('<analysis-request>', field='/manifest_path'))
        rejected = CellAnalysisResult('rejected', issue.source, (), (), None, absent, absent,
            (_finding(issue),), _MISSING + ('body_path_proof',), _BLOCKED, 'indeterminate', '')
        return _finish(rejected, occupancy, issues=(issue,))
    evidence = acquire_analysis(request.manifest_path)
    manifest = next((s.ref() for s in evidence.captures if s.uri == evidence.manifest_uri), SourceRef(str(request.manifest_path)))
    if evidence.value is None:
        findings = tuple(_finding(i) for i in evidence.issues)
        status: Literal['completed', 'rejected', 'unsupported'] = 'rejected' if any(f.severity == 'error' for f in findings) else 'unsupported'
        config = next((r.payload for r in evidence.records if r.kind == 'config'), FrozenMap({}))
        def blocked_selection(name: str) -> SelectedAnalysis:
            selected = mapping(config.get(name, FrozenMap({'kind': 'not_selected'})))
            return absent if selected['kind'] == 'not_selected' else SelectedAnalysis('not_evaluated', selected, dependencies=('local_authentication',))
        blocked = CellAnalysisResult(status, manifest, evidence.captures, evidence.records, None,
            blocked_selection('external_body'), blocked_selection('manual_intent'), findings,
            _MISSING + ('body_path_proof',), _BLOCKED, 'indeterminate', '')
        return _finish(blocked, occupancy, issues=evidence.issues)
    captures, body_capture, manual_capture, read_issues, aliases = acquire_selections(evidence)
    receipt = LocalAnalysisReceipt(evidence)
    local = analyze_local(receipt)
    external = selected_analysis(receipt, local, 'external_body', body_capture, read_issues, aliases)
    manual = selected_analysis(receipt, local, 'manual_intent', manual_capture, read_issues, aliases)
    terminals = analyze_terminals(local, external)
    local = replace(local, facets=replace(local.facets, terminals=terminals))
    # Multiple dependent facets can report the same source prerequisite.
    # Keep each distinct located finding once in the request summary.
    local_facets = (local.facets[field.name] for field in fields(AnalysisFacets))
    findings_list = list(dict.fromkeys(
        _finding(issue, computation_error=facet.value is not None)
        for facet in local_facets
        for issue in facet.issues
    ))
    findings_list.extend(_finding(i, violation=external.status == 'evaluated' and i.category != 'unsupported') for i in external.issues)
    findings_list.extend(_finding(i) for i in manual.issues)
    # Source parameter differences and local T05 violations remain diagnostics;
    # they do not turn a supported completed analysis into a parse failure.
    from layauto_v2.derive.channel_identity import ChannelIdentityDraft
    from layauto_v2.state.local_connectivity import LocalConnectivityDraft
    channel = local.facets.channel_fin.value
    if isinstance(channel, ChannelIdentityDraft):
        for difference in channel.differences:
            # Keep the complete measurement DTO in the facet, with a located
            # finding per mismatch rather than replacing it with a boolean.
            findings_list.append(AnalysisFinding('mismatch', 'SourceParameterMismatch', difference.declared.source, (difference.channel_ref.sha256, difference.binding_ref.sha256), 'mismatch', difference.device_id.name + '/' + difference.axis + ': ' + str(difference.measured) + ' vs ' + str(difference.declared.exact)))
    graph = local.facets.local_graph.value
    if isinstance(graph, LocalConnectivityDraft) and graph.local_enclosure_status == 'violation':
        findings_list.append(AnalysisFinding('violation', 'LocalEnclosureViolation', manifest, (), 'info', 'local T05 enclosure violation; see complete graph audits'))
    from layauto_v2.domain.analysis import AnalysisTerminal
    terminal_rows = cast(tuple[AnalysisTerminal, ...], terminals.value) if terminals.value is not None else ()
    for row in terminal_rows:
        if row.comparison == 'mismatch':
            findings_list.append(AnalysisFinding('mismatch', 'SourceTerminalMismatch', row.expected.source, (row.binding_ref,), 'mismatch', row.device_id.name + '/' + row.expected.role))
    # Source model/VT extraction and parent/global support remain unproved even
    # when the finite synthetic D/G/S/B comparisons agree.
    comparison = 'mismatch' if any(f.severity == 'mismatch' for f in findings_list) else 'indeterminate'
    status = ('rejected' if any(f.severity in ('error', 'violation') for f in findings_list)
              else 'unsupported' if any(f.severity == 'unsupported' for f in findings_list) else 'completed')
    missing: tuple[str, ...] = _MISSING
    if external.status != 'evaluated' or external.issues:
        missing += ('body_path_proof',)
    for field in fields(AnalysisFacets):
        facet = local.facets[field.name]
        if facet.status == 'not_evaluated':
            missing += tuple(field.name + ':' + reason for reason in facet.dependencies)
    result = CellAnalysisResult(status, manifest, captures, evidence.records, local, external, manual,
        tuple(findings_list), missing, _BLOCKED, comparison, '')
    return _finish(result, occupancy, receipt)
