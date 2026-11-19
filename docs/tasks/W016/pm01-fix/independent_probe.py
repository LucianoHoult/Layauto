"""Independent PM-01 public-API control/composition and source-location probe."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import runpy
import sys
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--root', type=Path, required=True)
a = p.parse_args()
root = a.root.resolve()
sys.path[:0] = [str(root), str(root/'tests/support')]
from analysis_inputs import materialize, load, write, rebind
from layauto_v2.analysis import AnalysisRequest, analyze_cell
append_rect = runpy.run_path(str(root/'tests/unit/test_analysis_api.py'))['append_rect']

results = {}
snapshots = {}
rows = []
cases = [('normal', False, None, False), ('pin_only', True, None, False)]
for stage in ('drawn', 'effective', 'local_graph'):
    cases.extend([(stage+'_only', False, stage, False), (stage+'_and_pin', True, stage, False)])
cases.extend([('finger_only', False, None, True), ('drawn_and_finger', False, 'drawn', True)])
codes = {'drawn': 'UnsupportedGeometryComparator', 'effective': 'AmbiguousGateStripe',
         'local_graph': 'UnsupportedLocalContactOperator'}

with tempfile.TemporaryDirectory(prefix='pm01-independent-') as tmp:
    for name, pin, stage, finger in cases:
        folder = Path(tmp)/name
        manifest = materialize(folder)
        cdl = folder/'source.cdl'
        data = cdl.read_text()
        if pin:
            before = '.SUBCKT INV_M1_SYNTH A Y VSS VDD'
            assert data.count(before) == 1
            data = data.replace(before, '.SUBCKT INV_M1_SYNTH A Y VSS')
        if finger:
            assert 'NF=1' in data
            data = data.replace('NF=1', 'NF=2', 1)
        cdl.write_text(data)
        if stage == 'effective':
            append_rect(folder, 'POLY', (78, 10, 82, 190))
        elif stage:
            if stage == 'drawn':
                path, group, key = folder/'tech/formats.json', 'geometry_capability', 'comparator'
            else:
                path, group, key = folder/'tech/physical.json', 'operators', 'same_layer_contact/1'
            owner = load(path)
            owner[group][key] = 'independent-pm01-unsupported/1'
            write(path, owner)
        rebind(folder)
        result = analyze_cell(AnalysisRequest(manifest))
        assert result.local is not None
        expected = ({'SourceTopIdentityMismatch'} if pin else set()) | ({codes[stage]} if stage else set()) | ({'UnsupportedFingerCount'} if finger else set())
        assert {f.code for f in result.findings} == expected
        assert len(result.findings) == len(expected), 'repeated top-level diagnostic'
        assert result.request_status == ('rejected' if pin else 'unsupported' if stage or finger else 'completed')
        local = result.local
        cell = next(c for c in local.source.cells if c.id == local.source.selected_cell)
        assert len(cell.ports) == (3 if pin else 4) and len(cell.devices) == 2
        for finding in result.findings:
            assert finding.source.sha256 == hashlib.sha256((folder/finding.source.uri).read_bytes()).hexdigest()
        if pin:
            finding = next(f for f in result.findings if f.code == 'SourceTopIdentityMismatch')
            assert finding.source.uri == 'query/raw/iXref.temp' and finding.source.line == 8
            if stage:
                assert finding == results['pin_only'].findings[0], 'identity diagnostic altered by geometry failure'
                assert next(f for f in result.findings if f.code == codes[stage]) == results[stage+'_only'].findings[0]
        if name == 'drawn_and_finger':
            assert next(f for f in result.findings if f.code == 'UnsupportedFingerCount') == results['finger_only'].findings[0]
        for index, facet_name in enumerate(('drawn', 'effective', 'local_graph')):
            facet = local.facets[facet_name]
            failure_index = ('drawn', 'effective', 'local_graph').index(stage) if stage else 3
            assert facet.status == ('available' if index < failure_index else 'error' if index == failure_index else 'not_evaluated')
            assert (facet.value is not None) == (index < failure_index)
        if stage:
            for consumer in ('channel_fin', 'annotation'):
                facet = local.facets[consumer]
                assert facet.status == 'not_evaluated' and facet.value is None
                assert facet.dependencies == ('local_graph', 'source_identity')
                assert {i.code for i in facet.issues} == expected - {codes[stage]}
        if stage or pin or finger:
            assert local.facets.terminals.status == 'not_evaluated' and local.facets.terminals.value is None
            assert local.facets.terminals.dependencies == ('channel_fin', 'annotation')
        else:
            assert sorted(m.count for m in local.facets.channel_fin.value.measurements) == [5, 7]
            assert sum(t.expected.role != 'B' and t.comparison == 'equal' for t in local.facets.terminals.value) == 6
            assert sum(t.expected.role == 'B' and t.comparison == 'indeterminate' for t in local.facets.terminals.value) == 2
        assert result.parent_global == 'unknown' and result.external_body.status == 'not_selected'
        results[name] = result
        snapshots[name] = (result.report_json, result.findings, result.local)
        assert all((old.report_json, old.findings, old.local) == snapshots[key] for key, old in results.items())
        row = {'case': name, 'status': result.request_status, 'source_port_count': len(cell.ports),
               'findings': [asdict(f) for f in result.findings],
               'facets': {key: {'status': local.facets[key].status, 'dependencies': local.facets[key].dependencies,
                                'issues': [asdict(i) for i in local.facets[key].issues], 'has_value': local.facets[key].value is not None}
                          for key in ('drawn', 'effective', 'local_graph', 'channel_fin', 'annotation', 'terminals')},
               'input_sha256': {str(path.relative_to(folder)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(folder.rglob('*')) if path.is_file()}}
        rows.append(row)
        print(json.dumps({'case': name, 'status': result.request_status, 'codes': sorted(expected)}), flush=True)
    assert all((old.report_json, old.findings, old.local) == snapshots[key] for key, old in results.items())
source = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for name in ('layauto_v2', 'tests') for path in sorted((root/name).rglob('*.py'))}
source['pyproject.toml'] = hashlib.sha256((root/'pyproject.toml').read_bytes()).hexdigest()
print(json.dumps({'status': 'passed', 'cases': rows, 'prior_results_unchanged': True, 'source_sha256': source}, indent=2))
