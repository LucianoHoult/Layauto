"""New analysis uses the same captured geometry/rule facts as the strict W014 chain."""
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'support'))
from analysis_inputs import materialize
from w005_cases import copy_input
from w014_cases import build
from layauto_v2.analysis import AnalysisRequest,analyze_cell


def test_same_source_body_geometry_paths_rules_and_terminals(tmp_path):
    root=copy_input(tmp_path)
    old=build(root)
    assert old.status=='success',old.issues
    materialize(root,body=True)
    new=analyze_cell(AnalysisRequest(root/'analysis.json'))
    assert new.request_status=='completed',new.findings
    assert new.local.facets.local_graph.value==old.value.local
    assert new.local.source==old.value.source
    body=new.external_body.value
    for key in ('local_bindings','active_audits','body_pair_audits','tap_audits','production_matched_body_evidence','lvs_status','local_graph_union'):
        assert body[key]==old.value.body[key],key
    assert len(body['paths'])==len(old.value.body['paths'])==2
    for a,b in zip(body['paths'],old.value.body['paths']):
        # Explicit new query header/run and annotation receipt produce new refs;
        # every physical/path/rule/claim field must still agree.
        assert set(a)==set(b)
        for key in set(a)-{'channel_ref','evidence_refs'}:
            assert a[key]==b[key],key
    old_rows={(r.target.device_id,r.expected.role):r for r in old.value.relations}
    for row in new.local.facets.terminals.value:
        other=old_rows[(row.device_id,row.expected.role)]
        for key in ('expected','node_refs','component_refs','local_observed_net_ids','observed_net_ids','support_status'):
            assert getattr(row,key)==getattr(other,key),key
        assert row.comparison==other.status
