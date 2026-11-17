"""Actual missing device seed, unmatched net seed, and reachable SREF inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import struct
import sys
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--root', type=Path, required=True)
a = p.parse_args()
root = a.root.resolve()
sys.path.insert(0, str(root))
sys.path.insert(0, str(root/'tests/support'))
from analysis_inputs import materialize, rebind, load, write
from layauto_v2.analysis import AnalysisRequest, analyze_cell
helpers = runpy.run_path(str(root/'tests/unit/test_analysis_api.py'))

def record(kind, data_type, payload=b''):
    assert len(payload) % 2 == 0
    return struct.pack('>HBB', 4+len(payload), kind, data_type) + payload

with tempfile.TemporaryDirectory(prefix='w016-review-local-boundary-') as tmp:
    for case in ('missing_device_seed', 'unmatched_net_seed', 'reachable_sref'):
        folder = Path(tmp)/case
        manifest = materialize(folder)
        if case == 'missing_device_seed':
            requests = load(folder/'query/requests.json')
            missing = next(r for r in requests['requests'] if r['capability'] == 'device_regions' and r['object'] == 'Q17')
            requests['requests'].remove(missing)
            write(folder/'query/requests.json', requests)
            header = load(folder/'query/local-header.json')
            header['raw'] = [r for r in header['raw'] if r['uri'] != missing['path']]
            write(folder/'query/local-header.json', header)
            (folder/missing['path']).unlink()
        elif case == 'unmatched_net_seed':
            helpers['append_rect'](folder, 'M1', (130, 20, 140, 24))
            helpers['append_seed'](folder, 'n_a', (300, 300, 310, 310))
        else:
            path = folder/'source.gds'
            data = path.read_bytes()
            assert data[-8:] == b'\x00\x04\x07\x00\x00\x04\x04\x00'
            # A complete SREF element in the selected structure, with explicit
            # name and origin. Parser must report unsupported without flattening.
            sref = record(0x0A, 0) + record(0x12, 6, b'CHILD\0') + record(0x10, 3, struct.pack('>ii', 0, 0)) + record(0x11, 0)
            path.write_bytes(data[:-8] + sref + data[-8:])
        rebind(folder)
        result = analyze_cell(AnalysisRequest(manifest))
        row = {'case': case, 'status': result.request_status, 'local_present': result.local is not None,
               'findings': [{'category': f.category, 'severity': f.severity, 'code': f.code, 'uri': f.source.uri,
                             'sha256': f.source.sha256, 'record_index': f.source.record_index, 'field': f.source.field} for f in result.findings],
               'input_sha256': {str(path.relative_to(folder)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(folder.rglob('*')) if path.is_file()}}
        if case == 'missing_device_seed':
            assert result.request_status == 'rejected' and result.local is not None
            assert result.local.facets.channel_fin.status == 'error'
            assert result.local.facets.annotation.status == 'available'
            assert result.local.facets.terminals.status == 'not_evaluated'
            assert any(f.code == 'MissingDeviceSeed' and f.severity == 'error' for f in result.findings)
            row['terminal_dependencies'] = result.local.facets.terminals.dependencies
        elif case == 'unmatched_net_seed':
            assert result.request_status == 'completed' and result.local is not None
            annotation = result.local.facets.annotation.value
            unmatched = [r for m in annotation.matches for r in m.unmatched if r.bounds == (300, 300, 310, 310)]
            assert unmatched
            target = next(t for t in annotation.targets if t.drawn_rectangle.bounds == (130, 20, 140, 24))
            gaps = [f for f in annotation.fragments if f.target_ref == target.ref and f.status == 'unknown']
            assert sum(f.area_nm2 for f in gaps) == 40
            row['unmatched_area_nm2'] = 100
            row['independent_gap_area_nm2'] = 40
        else:
            assert result.request_status == 'unsupported' and result.local is None
            issue = next(f for f in result.findings if f.code == 'UnsupportedGdsElement:SREF')
            assert issue.source.record_index is not None and issue.source.sha256 == hashlib.sha256((folder/'source.gds').read_bytes()).hexdigest()
        print(json.dumps(row), flush=True)
print(json.dumps({'status': 'passed', 'source_sha256': {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted((root/'layauto_v2').rglob('*.py'))}}), flush=True)
