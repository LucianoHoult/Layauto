"""R08 public request owner, frozen request, and actual no-body API smoke."""
import argparse
from dataclasses import FrozenInstanceError
import hashlib
import json
from pathlib import Path
import sys
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--root', type=Path, required=True)
a = p.parse_args()
root = a.root.resolve()
sys.path.insert(0, str(root))
sys.path.insert(0, str(root/'tests/support'))
from analysis_inputs import materialize
from layauto_v2.analysis import AnalysisRequest, analyze_cell
import layauto_v2.domain.analysis as domain_analysis

assert AnalysisRequest.__module__ == 'layauto_v2.analysis'
assert not hasattr(domain_analysis, 'AnalysisRequest')
with tempfile.TemporaryDirectory(prefix='w016-review-request-owner-') as tmp:
    manifest = materialize(Path(tmp))
    request = AnalysisRequest(manifest)
    try:
        request.manifest_path = Path('/tmp/changed')
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError('Public request lost frozen semantics')
    result = analyze_cell(request)
    assert result.request_status == 'completed' and result.local is not None
    assert result.local.facets.terminals.status == 'available'
    assert result.external_body.status == 'not_selected'
    assert result.source_comparison == 'indeterminate'
    assert len(result.local.facets.terminals.value) == 8
    invalid = analyze_cell(AnalysisRequest(Path('/tmp/\ud800.json')))
    assert invalid.request_status == 'rejected' and invalid.findings[0].code == 'InvalidAnalysisRequest'
print(json.dumps({'status': 'passed', 'public_owner': AnalysisRequest.__module__, 'request_frozen': True,
                  'domain_has_request': False, 'actual_no_body_status': result.request_status,
                  'terminal_count': len(result.local.facets.terminals.value), 'unicode_request_still_located': True,
                  'source_sha256': {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted((root/'layauto_v2').rglob('*.py'))}}, indent=2))
