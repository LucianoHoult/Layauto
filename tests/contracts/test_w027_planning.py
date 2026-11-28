"""Independent Stage 4 boundary and target-completeness probes."""
from dataclasses import replace

import pytest

from layauto_v2.constraints.drc_context import ConstraintContext
from layauto_v2.domain.publication import AuditBinding
from layauto_v2.domain.publication_codec import content_ref
from layauto_v2.planning import NoChangePlanningResult, RejectedPlanningResult, plan_no_change
from layauto_v2.repository import RepositoryConflict
from w005_cases import rebind
from w023_cases import sample
from w026_cases import inspect_published


def binding(view):
    v = view.version
    return AuditBinding(v.context_ref, content_ref(view.target), v.head_ref, v.snapshot_ref)


def test_selected_fields_and_extracted_terminals_bind_the_target(normal_rules):
    view, _, _ = normal_rules
    selected = binding(view)
    result = plan_no_change(view, selected)
    assert isinstance(result, NoChangePlanningResult)
    assert result.candidates == result.mutations == ()
    assert result.audit.binding == selected
    rows = result.audit.observations
    vt = [r for r in rows if r['kind'] == 'parameter' and r['object_ids'][-1] == 'threshold_token']
    assert len(vt) == 2
    assert all(r['facts']['current'] == r['facts']['target'] and r['facts']['target']['unit'] == 'token'
               for r in vt)
    terminals = [r for r in rows if r['kind'] == 'terminal_extraction']
    assert len(terminals) == 8
    assert all(r['facts']['observed_net_ids'] == (r['facts']['target'],) for r in terminals)
    wrong = replace(selected, target_ref=replace(selected.target_ref, digest='0' * 64))
    with pytest.raises(RepositoryConflict) as caught:
        plan_no_change(view, wrong)
    assert caught.value.code == 'BindingConflict'


def test_empty_delta_list_cannot_hide_an_undeclared_semantic_change(tmp_path):
    root = sample(tmp_path)
    # Ordered external pins are independent of the channel and terminal measurements.
    # Remove only the difference ledger in the planner input to isolate A2's
    # independent semantic comparison on the already published circuit operands.
    path = root / 'target.cdl'
    path.write_text(path.read_text().replace('.SUBCKT INV_M1_SYNTH A Y', '.SUBCKT INV_M1_SYNTH Y A'))
    rebind(root)
    view, _, _ = inspect_published(root, 'semantic-only')
    assert {d['op_type'] for d in view.target.differences} == {'ports_change', 'net_membership_change'}
    ledger_missing = replace(view.target, differences=())
    probe = ConstraintContext._published(view.version, view.snapshot, view.catalog, view.physical,
                                         view.inputs, view.source_circuit, ledger_missing, view.eco_commits)
    result = plan_no_change(probe, binding(probe))
    assert isinstance(result, RejectedPlanningResult)
    assert {issue.code for issue in result.audit.issues} == {'UnreportedTargetDifference'}
    assert any('ports' in issue.message for issue in result.audit.issues)
    for issue in result.audit.issues:
        assert {s.uri for s in issue.sources} == {'source.cdl', 'target.cdl'}
