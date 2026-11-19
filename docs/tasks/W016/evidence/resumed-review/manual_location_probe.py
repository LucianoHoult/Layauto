"""Independent actual declaration field provenance and non-observation probe."""
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
sys.path.insert(0, str(root / 'tests/support'))
from analysis_inputs import materialize, manual_for, write, load, rebind
from layauto_v2.analysis import AnalysisRequest, analyze_cell

with tempfile.TemporaryDirectory(prefix='w016-review-manual-ref-') as tmp:
    directory = Path(tmp)
    manifest = materialize(directory)
    doc = manual_for(directory)
    doc['assertions'].append({'device': 'MP0', 'role': 'B', 'expected_supply_label': 'PWR1'})
    config = load(manifest)
    config['manual_intent'] = {'kind': 'declaration', 'uri': 'manual.json'}
    write(manifest, config)
    rebind(directory)
    manual = directory / 'manual.json'
    write(manual, doc)
    first = analyze_cell(AnalysisRequest(manifest))
    assert first.request_status == 'completed' and first.manual_intent.status == 'declared'
    wanted = {'/author', '/created_at', '/cell', '/instance_hint'}
    wanted |= {f'/{binding}/{field}' for binding in ('source_layout', 'source_netlist') for field in ('uri', 'sha256')}
    wanted |= {f'/assertions/{index}/{field}' for index in range(2) for field in ('device', 'role', 'expected_supply_label')}
    refs = first.manual_intent.evidence_refs
    found = {ref.field for ref in refs}
    assert wanted <= found, sorted(wanted - found)
    capture = next(c for c in first.captures if c.sha256 == hashlib.sha256(manual.read_bytes()).hexdigest())
    for ref in refs:
        assert ref.uri == capture.uri and ref.sha256 == capture.sha256
    assert all(field in first.report_json for field in wanted)
    before = first.report_json
    doc['assertions'][0]['expected_supply_label'] = 'SECOND_DECLARATION_ONLY'
    write(manual, doc)
    second = analyze_cell(AnalysisRequest(manifest))
    assert second.request_status == 'completed'
    assert second.local.receipt_ref == first.local.receipt_ref
    assert second.local.facets.terminals == first.local.facets.terminals
    assert first.report_json == before
    result = {'status': 'passed', 'declaration_field_refs': sorted(wanted), 'all_refs_match_actual_capture': True,
              'report_contains_all_field_refs': True, 'changed_declaration_leaves_terminals_and_local_receipt_equal': True,
              'prior_result_unchanged': True}
result['source_sha256'] = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted((root/'layauto_v2').rglob('*.py'))}
print(json.dumps(result, indent=2))
