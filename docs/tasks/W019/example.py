"""Read the M1 line end from a W019 sample manifest."""
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from layauto_v2.analysis import AnalysisRequest, OccupancyRequest, analyze_cell


def example(manifest):
    result = analyze_cell(AnalysisRequest(manifest), occupancy=OccupancyRequest(fragment_budget=48))
    query = result.occupancy
    assert query is not None and query.status == 'success', query
    index = query.value
    assert index is not None
    fragment, = index.in_cell('M1', 2, 2, view='drawn')
    record = fragment.source.record
    pieces = index.for_record(record.id, view='drawn')
    widths = [p.rect.x1 - p.rect.x0 for p in pieces]
    print(record.source.uri, record.source.byte_offset, fragment.rect.bounds, fragment.rect.area, widths)
    assert (record.source.byte_offset, fragment.rect.bounds, fragment.rect.area, widths) == (
        2352, (32, 48, 45, 58), 130, [16, 16, 13])


if __name__ == '__main__':
    if len(sys.argv) > 1:
        example(Path(sys.argv[1]).resolve())
    else:
        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tests/support'))
        from analysis_projection_inputs import projected_manifest

        with TemporaryDirectory() as temp:
            example(projected_manifest(Path(temp)))
