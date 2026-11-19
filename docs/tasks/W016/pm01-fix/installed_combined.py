"""Exercise PM-01 using the installed wheel and prepared input files."""
from hashlib import sha256
from pathlib import Path
import json
import sys
from layauto_v2.analysis import AnalysisRequest, analyze_cell
import layauto_v2

package = Path(layauto_v2.__file__).resolve()
assert package.is_relative_to(Path(sys.prefix).resolve())
root = Path(sys.argv[1])
result = analyze_cell(AnalysisRequest(root / 'analysis.json'))
assert result.request_status == 'rejected'
assert len(result.findings) == 2
expected = {'UnsupportedGeometryComparator': 'tech/formats.json', 'SourceTopIdentityMismatch': 'query/raw/iXref.temp'}
assert {f.code: f.source.uri for f in result.findings} == expected
for finding in result.findings:
    assert finding.source.sha256 == sha256((root / finding.source.uri).read_bytes()).hexdigest()
    if finding.code == 'SourceTopIdentityMismatch':
        assert finding.source.line == 8
assert result.local.source.selected_cell.name == 'INV_M1_SYNTH'
assert result.local.facets.drawn.status == 'error'
assert result.local.facets.channel_fin.status == 'not_evaluated'
print(json.dumps({'installed': str(package), 'status': result.request_status,
                  'findings': [{'code': f.code, 'source': vars(f.source)} for f in result.findings]}, indent=2))
