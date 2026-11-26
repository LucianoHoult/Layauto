"""Independent file/reader probe. Run from the checkout with tests/contracts on PYTHONPATH."""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
from shutil import rmtree
from struct import iter_unpack, unpack_from
from tempfile import TemporaryDirectory

import yaml

from layauto_v2.domain.codec import FrozenMap
from layauto_v2.domain.publication import InputsReady, RunRequest, Stage2Request
from layauto_v2.normalization.initial_state import build_proposed_initial_state
from layauto_v2.pipeline import assemble_stage2, prepare_inputs, publish_stage2
from layauto_v2.repository import PublicationRepository, RepositoryConflict
from layauto_v2.transactions.initialization import InitializationTransaction
from w018_cases import COORDINATE_URI
from w023_cases import sample


def stream_rectangles(data, wanted):
    """Decode BOUNDARY/LAYER/DATATYPE/XY/ENDEL directly from the original stream."""
    offset = 0
    start = layer = datatype = points = None
    while offset < len(data):
        size, tag = unpack_from('>HH', data, offset)
        assert size >= 4 and offset + size <= len(data)
        body = data[offset + 4:offset + size]
        if tag == 0x0800:
            start = offset
        elif tag == 0x0d02:
            layer, = unpack_from('>H', body)
        elif tag == 0x0e02:
            datatype, = unpack_from('>H', body)
        elif tag == 0x1003:
            points = list(iter_unpack('>ii', body))
        elif tag == 0x1100 and (layer, datatype) == wanted:
            assert points[0] == points[-1] and len(points) == 5
            xs, ys = zip(*points)
            yield start, (min(xs), min(ys), max(xs), max(ys))
        offset += size


def projected(raw, grid):
    expected = {}
    for offset, (left, bottom, right, top) in raw:
        for i in range(grid['x_edges']['cells']):
            x0 = grid['x_edges']['offset_dbu'] + i * grid['x_edges']['pitch_dbu']
            for j in range(grid['y_edges']['cells']):
                y0 = grid['y_edges']['offset_dbu'] + j * grid['y_edges']['pitch_dbu']
                rect = (max(left, x0), max(bottom, y0),
                        min(right, x0 + grid['x_edges']['pitch_dbu']), min(top, y0 + grid['y_edges']['pitch_dbu']))
                if rect[0] < rect[2] and rect[1] < rect[3]:
                    expected[offset, (i, j)] = rect
    return expected


def run(parent, expect_old_budget, check_origin):
    directory = sample(parent)
    raw = (directory / 'source.gds').read_bytes()
    drawn = json.loads((directory / 'tech/drawn.json').read_bytes())
    stream_key, = (l['stream_key'] for l in drawn['layers'] if l['name'] == 'M1')
    expected_raw = dict(stream_rectangles(raw, (stream_key['layer'], stream_key['datatype'])))
    grid = yaml.safe_load((directory / COORDINATE_URI).read_bytes())['coordinate_projection']['layers']['M1']
    expected_grid = projected(expected_raw.items(), grid)

    seen = {}
    def interrupt(point):
        if point in ('initialize.before_switch', 'initialize.after_switch'):
            seen[point] = repo.snapshot()
            if point == 'initialize.after_switch':
                raise KeyboardInterrupt(point)

    repo = PublicationRepository(fault_injector=interrupt)
    run_id, lineage = 'independent-reader', 'review-lineage'
    ready = prepare_inputs(repo, RunRequest(run_id, lineage, 'create-review', str(directory / 'site_config.yaml')))
    assert isinstance(ready, InputsReady)
    request = Stage2Request.from_ready(ready, idempotency_key='publish-review', fragment_budget=312)
    rmtree(directory)
    before = repo.snapshot()
    candidate = build_proposed_initial_state(assemble_stage2(repo, ready, fragment_budget=312))
    try:
        InitializationTransaction.prepare(repo, replace(request, fragment_budget=0), ready, candidate)
    except RepositoryConflict as exc:
        budget = exc.code
    else:
        budget = 'accepted'
    assert (budget == 'accepted') == expect_old_budget, budget
    assert repo.snapshot() == before

    if not expect_old_budget:
        for alternate in (replace(ready, evidence_refs=ready.evidence_refs[::-1]),
                          replace(ready, value=FrozenMap({}))):
            try:
                InitializationTransaction.prepare(repo, request, alternate, candidate)
            except RepositoryConflict as exc:
                assert exc.code == 'ReadbackConflict', exc
            else:
                raise AssertionError('mismatched input receipt allowed')
        assert repo.snapshot() == before

    prepared = InitializationTransaction.prepare(repo, request, ready, candidate)
    del candidate
    try:
        repo.initialize(request, prepared)
    except KeyboardInterrupt as exc:
        assert str(exc) == 'initialize.after_switch'
    else:
        raise AssertionError('expected interrupted response')
    del prepared
    sealed = repo.snapshot()
    assert seen == {'initialize.before_switch': before, 'initialize.after_switch': sealed}
    assert sealed.generation == before.generation + 1
    assert sealed.idempotency_count == before.idempotency_count + 1
    head = repo.read(repo.load_head(lineage))
    attempt = repo.load_attempt(run_id)
    context = repo.read(attempt.context_ref)
    snapshot = repo.read(head.snapshot_ref)
    assert (attempt.revision, attempt.phase) == (2, 'sealed_open')
    assert (head.version, head.eco_commits) == (0, ())
    assert repo.read(head.event_ref).snapshot_ref == head.snapshot_ref
    assert context.checkpoint_ref == ready.checkpoint_ref and context.head_ref == repo.load_head(lineage)
    assert publish_stage2(repo, request) == context and repo.snapshot() == sealed

    state = snapshot.state
    records = state['geometry']['records']
    observed_raw = {r['source']['byte_offset']: r['rect'] for r in records.values() if r['layer'] == 'M1'}
    observed_grid = {(records[f['record_id']]['source']['byte_offset'], f['indices']): f['rect']
                     for f in state['occupancy'] if f['view'] == 'drawn' and f['layer'] == 'M1'}
    assert observed_raw == expected_raw and observed_grid == expected_grid
    assert snapshot.binding['sources']['source.gds'] == sha256(raw).hexdigest()
    # A reader with a new, intact capture must not reuse an orphaned version.
    directory = sample(parent)
    new_ready = prepare_inputs(repo, RunRequest('reader-B', lineage, 'B', str(directory / 'site_config.yaml'),
                                               expected_state_head=context.head_ref.id))
    assert isinstance(new_ready, InputsReady)
    reuse = Stage2Request.from_ready(new_ready, idempotency_key='reuse', fragment_budget=312)
    original = repo._root
    origin_checks = {}
    for bad_ref in (ready.checkpoint_ref, ready.parse_ref, ready.evidence_refs[0]):
        # Simulate a missing content record in the backend. Keep every reference, and
        # all bytes acquired independently by B, intact. Only the fault uses internals.
        damaged = replace(original, contents=tuple((r, data) for r, data in original.contents if r != bad_ref))
        repo._root = damaged
        try:
            publish_stage2(repo, reuse)
        except RepositoryConflict as exc:
            assert exc.code == 'RefConflict' and bad_ref.id in str(exc)
            assert repo._root is damaged and repo.load_attempt('reader-B') == new_ready.attempt
            origin_checks[bad_ref.kind] = exc.code
        else:
            origin_checks[bad_ref.kind] = 'accepted'
        finally:
            repo._root = original
    if check_origin:
        assert set(origin_checks.values()) == {'RefConflict'}, origin_checks
    before_after = Counter(r.kind for r in sealed.content_refs) - Counter(r.kind for r in before.content_refs)
    print(json.dumps({'budget_zero_with_prebuilt_312': budget, 'input_removed_before_assembly': True,
                      'generations': [before.generation, sealed.generation], 'new_content': dict(before_after),
                      'attempt': [attempt.phase, attempt.revision], 'replay_same_context': True, 'missing_origin': origin_checks,
                      'GDS_sha256': sha256(raw).hexdigest(), 'M1_stream_records': len(expected_raw),
                      'M1_drawn_fragments': len(expected_grid), 'M1_cell_3_4_offset_2480': observed_grid[2480, (3, 4)],
                      'head': context.head_ref.id, 'snapshot': head.snapshot_ref.id}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--expect-old-budget', action='store_true', help='reproduce the budget finding on f1bcbda')
    parser.add_argument('--check-origin', action='store_true', help='require rejection for missing original capture records')
    args = parser.parse_args()
    with TemporaryDirectory() as temp:
        run(Path(temp), args.expect_old_budget, args.check_origin)
