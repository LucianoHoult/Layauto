"""Compare individual and combined W019 diagnostics through the public API."""
import hashlib
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tests/support'))
from analysis_inputs import load, rebind, write
from analysis_projection_inputs import COORDINATE, SAMPLE, projected_manifest
from layauto_v2.analysis import AnalysisRequest, OccupancyRequest, analyze_cell


def observe(label, manifest, include_effective):
    result = analyze_cell(AnalysisRequest(manifest), occupancy=OccupancyRequest(100, include_effective))
    query = result.occupancy
    assert query is not None and query.value is None
    assert result.local is not None and len(result.local.facets.drawn.value.layout.records) == 40
    locations = {}
    for item in (*result.findings, *query.issues):
        if item.code not in ('InvalidProjectionDeclaration', 'UnsupportedRegionOperator'):
            continue
        ref = item.source
        assert ref.sha256 == hashlib.sha256((manifest.parent / ref.uri).read_bytes()).hexdigest()
        locations[item.code] = (ref.uri, ref.field, ref.sha256)
    print(label, result.request_status, query.status, sorted(locations))
    return locations, result.report_json


def main():
    with TemporaryDirectory() as temp:
        observations = {}
        for case in ('axis', 'operator', 'combined'):
            root = Path(temp) / case
            manifest = projected_manifest(root)
            if case != 'operator':
                coord = yaml.safe_load(SAMPLE.read_bytes())
                del coord['coordinate_projection']['layers']['M1']['y_edges']
                write(root / COORDINATE, coord)
            if case != 'axis':
                path = root / 'tech/physical.json'
                physical = load(path)
                physical['operators']['rectangle_set_difference/1'] = 'unsupported test operator'
                write(path, physical)
            rebind(root)
            observations[case] = observe(case, manifest, True)
            if case == 'combined':
                observations['combined_drawn'] = observe('combined_drawn', manifest, False)
        axis = observations['axis'][0]
        operator = observations['operator'][0]
        assert axis['InvalidProjectionDeclaration'][:2] == (COORDINATE, '/coordinate_projection/layers/M1/y_edges')
        assert operator['UnsupportedRegionOperator'][:2] == ('tech/physical.json', '/operators/rectangle_set_difference~11')
        assert observations['combined_drawn'][0] == axis | operator
        locations, report = observations['combined']
        if locations != axis | operator or any(code not in report for code in (*axis, *operator)):
            raise SystemExit('combined query lost a diagnostic or its original location')


if __name__ == '__main__':
    main()
