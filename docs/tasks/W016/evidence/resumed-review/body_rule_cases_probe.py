"""Actual new-entry body type/ambiguity violations, preserving located diagnostics."""
import argparse
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

rows = []
with tempfile.TemporaryDirectory(prefix='w016-review-body-rules-') as tmp:
    for case, code in (('body_wrong_type', 'BodyTypeMismatch'), ('body_ambiguous', 'BodyUniqueMatchFailure')):
        folder = Path(tmp)/case
        manifest = materialize(folder, case=case, body=True)
        result = analyze_cell(AnalysisRequest(manifest))
        assert result.request_status == 'rejected' and result.local is not None
        assert result.external_body.status == 'evaluated'
        issues = tuple(i for i in result.external_body.issues if i.code == code)
        assert issues, result.external_body.issues
        actual = (folder/'body/context.json').read_bytes()
        capture = next(c for c in result.captures if c.sha256 == hashlib.sha256(actual).hexdigest())
        for issue in issues:
            assert issue.source.uri == capture.uri and issue.source.sha256 == capture.sha256
            assert issue.source.field and issue.source.field.startswith(('/associations/', '/shapes/'))
            assert any(f.code == issue.code and f.source == issue.source and f.severity == 'violation' for f in result.findings)
        rows.append({'case': case, 'status': result.request_status, 'body_status': result.external_body.status,
                     'local_retained': True, 'issues': [{'code': i.code, 'source_uri': i.source.uri, 'sha256': i.source.sha256, 'field': i.source.field} for i in issues],
                     'input_sha256': {str(path.relative_to(folder)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(folder.rglob('*')) if path.is_file()}})
print(json.dumps({'cases': rows, 'source_sha256': {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted((root/'layauto_v2').rglob('*.py'))}}, indent=2))
