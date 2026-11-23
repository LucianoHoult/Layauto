"""From the checkout: python -m docs.tasks.W018.example [--resources].

With an installed wheel: python -I example.py --site /path/to/site_config.yaml
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from time import perf_counter_ns
import tracemalloc

from layauto_v2.importers import read_inputs
from layauto_v2.normalization import build_geometry, geometry_from_parse_result
from layauto_v2.normalization.projection import build_discrete_occupancy
from layauto_v2.normalization.projection_model import bind_projection_model
from layauto_v2.state.discrete_occupancy import build_discrete_occupancy as project_layout


def read_geometry(site):
    parsed = read_inputs(site)
    if parsed.status != 'success':
        raise ValueError(parsed.issues)
    geometry = build_geometry(geometry_from_parse_result(parsed))
    if geometry.status != 'success':
        raise ValueError(geometry.issues)
    return geometry


def inspect(site):
    geometry = read_geometry(site)
    result = build_discrete_occupancy(geometry, fragment_budget=10_000)
    occupancy = result.value
    if occupancy is None:
        raise ValueError(f'required {result.required_fragments} fragments')
    layers = [{'layer': row.layer, 'record_count': row.record_count, 'projection': row.projection,
               'fragments': len(occupancy.for_layer(row.layer))} for row in occupancy.layers]
    examples = []
    for layer, indices in [('FIN', (0,)), ('LI', (1, 3)), ('M1', (2, 2))]:
        for fragment in occupancy.in_cell(layer, *indices, view='drawn'):
            record = occupancy.layout.record(fragment.record_id)
            examples.append({'layer': layer, 'indices': indices, 'bounds_dbu': fragment.rect.bounds,
                             'record_id': record.id.sha256, 'source': record.source.uri,
                             'byte_offset': record.source.byte_offset, 'record_bounds_dbu': record.rect.bounds,
                             'record_fragments': len(occupancy.for_record(record.id))})
    return {'coordinate_owner_sha256': occupancy.model.coordinate_source.sha256,
            'gds_sha256': geometry.value.layout.gds.sources[0].sha256,
            'unit_ref': occupancy.model.unit_ref.sha256, 'layers': layers,
            'fragments': len(occupancy.fragments), 'examples': examples}


def measure(call):
    tracemalloc.start()
    start = perf_counter_ns()
    try:
        result = call()
        elapsed = perf_counter_ns() - start
        peak = tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()
    return result, {'elapsed_ms': round(elapsed / 1_000_000, 3), 'python_peak_bytes': peak}


def resource_sample(site):
    def from_files():
        return build_discrete_occupancy(read_geometry(site), fragment_budget=10_000)

    result, total = measure(from_files)
    geometry = read_geometry(site)
    model = bind_projection_model(geometry)
    state, core = measure(lambda: project_layout(geometry.value.layout, model, fragment_budget=10_000))
    assert state.value is not None and result.value is not None
    fragments = state.value.fragments
    assert fragments == result.value.fragments
    return {'file_to_index': total, 'index_from_bound_model_and_layout': core,
            'drawn_fragments': dict(Counter(f.layer for f in fragments)),
            'occupied_cells': len({(f.layer, f.indices) for f in fragments})}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', type=Path, help='existing site with its selected coordinate owner')
    parser.add_argument('--resources', action='store_true', help='measure main, fine LI and large sparse LI inputs')
    args = parser.parse_args()
    if args.site:
        report = resource_sample(args.site) if args.resources else inspect(args.site)
    else:
        # Only the checkout demonstration prepares fixture copies. The installed
        # smoke supplies a site and never imports repository test helpers.
        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tests/contracts'))
        from w005_cases import copy_input
        from w018_cases import select_projection
        with TemporaryDirectory() as temp:
            root = copy_input(Path(temp))
            select_projection(root)
            site = root / 'site_config.yaml'
            if args.resources:
                report = {'reviewed_owner': resource_sample(site)}
                for label, x_pitch, y_pitch, xs, ys in (
                    ('fine_li', 1, 1, 160, 200),
                    ('large_sparse_li', 20, 10, 10**9, 10**9),
                ):
                    def variant(projection):
                        li = projection['layers']['LI']
                        li['x_edges'].update(pitch_dbu=x_pitch, cells=xs)
                        li['y_edges'].update(pitch_dbu=y_pitch, cells=ys)
                    select_projection(root, mutate=variant)
                    report[label] = resource_sample(site)
            else:
                report = inspect(site)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
