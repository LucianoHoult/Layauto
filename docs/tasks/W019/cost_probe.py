"""Count actual reads and geometry builds, then time lookups on one stored index."""
from collections import Counter
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter_ns
from unittest.mock import patch

from layauto_v2.analysis import AnalysisRequest, OccupancyRequest, analyze_cell
from layauto_v2.normalization import analysis as local
from layauto_v2.normalization import analysis_occupancy as projection


def main(manifest):
    counts = Counter()
    original_read = Path.read_bytes
    paths = set()

    def read(path):
        paths.add(path)
        counts['read_bytes'] += 1
        return original_read(path)

    def counted(function):
        def call(*args, **kwargs):
            counts[function.__name__] += 1
            return function(*args, **kwargs)
        return call

    request = AnalysisRequest(manifest)
    rows = []

    def measure(label, operation):
        counts.clear()
        paths.clear()
        start = perf_counter_ns()
        result = operation()
        elapsed = perf_counter_ns() - start
        rows.append(dict(phase=label, elapsed_ms=round(elapsed / 1_000_000, 3),
                         distinct_paths=len(paths), calls=dict(counts),
                         report_bytes=len(result.report_json.encode()),
                         report_sha256=hashlib.sha256(result.report_json.encode()).hexdigest()))
        return result

    def first():
        result = analyze_cell(request, occupancy=OccupancyRequest(fragment_budget=48))
        fragment, = result.occupancy.value.in_cell('M1', 2, 2, view='drawn')
        assert fragment.rect.area == 130
        return result

    def repeat():
        index = queried.occupancy.value
        for _ in range(1000):
            fragment, = index.in_cell('M1', 2, 2, view='drawn')
            assert index.for_record(fragment.record_id, view='drawn')[-1] is fragment
        return queried

    with ExitStack() as stack:
        stack.enter_context(patch.object(Path, 'read_bytes', read))
        for module, names in ((local, ('build_layout', 'build_partition', 'build_occupancy', 'build_effective_draft')),
                              (projection, ('_bind_model', 'build_discrete_occupancy'))):
            for name in names:
                stack.enter_context(patch.object(module, name, counted(getattr(module, name))))
        plain = measure('no_query', lambda: analyze_cell(request))
        queried = measure('analysis_and_first_cell', first)
        measure('1000_cell_and_reverse_queries', repeat)
    assert plain.occupancy is None and plain.local == queried.local
    assert rows[0]['calls'] == dict.fromkeys(
        ('build_layout', 'build_partition', 'build_occupancy', 'build_effective_draft'), 1) | {
            'read_bytes': len(plain.captures)}
    assert rows[1]['calls'] == rows[0]['calls'] | {'_bind_model': 1, 'build_discrete_occupancy': 1}
    assert rows[0]['distinct_paths'] == rows[1]['distinct_paths'] == len(plain.captures)
    assert rows[2]['calls'] == {} and rows[1]['report_sha256'] == rows[2]['report_sha256']
    print(json.dumps(rows, indent=2))


if __name__ == '__main__':
    main(Path(sys.argv[1]).resolve())
