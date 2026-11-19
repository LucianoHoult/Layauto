"""Run with installed Python -I, copied outside the source checkout."""
from pathlib import Path
import json
import sys
import layauto_v2
from layauto_v2.analysis import AnalysisRequest, analyze_cell

root=Path(sys.argv[1]);source=Path(sys.argv[2]).resolve()
package=Path(layauto_v2.__file__).resolve()
assert not package.is_relative_to(source),package
invalid=analyze_cell(AnalysisRequest(Path('/tmp/\ud800.json')))
assert invalid.request_status=='rejected' and invalid.findings[0].code=='InvalidAnalysisRequest'
invalid.report_json.encode('utf-8')
rows=[]
for name,status in [('no_body','completed'),('body','completed'),('mismatch','completed'),('bad_body','rejected'),('manual','completed')]:
    result=analyze_cell(AnalysisRequest(root/name/'analysis.json'))
    assert result.request_status==status,(name,result.findings)
    assert result.local is not None
    if name=='mismatch':assert result.source_comparison=='mismatch'
    if name=='bad_body':assert result.external_body.status=='error'
    if name=='manual':
        assert result.manual_intent.status=='declared'
        assert '/assertions/0/expected_supply_label' in {r.field for r in result.manual_intent.evidence_refs}
    assert len(result.report_json.encode())>0
    rows.append({'case':name,'status':result.request_status,'source_comparison':result.source_comparison,'report_bytes':len(result.report_json.encode())})
print(json.dumps({'python':sys.version,'installed_package':str(package),'cases':rows},indent=2))
