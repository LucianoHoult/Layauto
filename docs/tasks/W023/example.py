"""Measure one complete publication and resolve Stage 2 facts from repository refs."""
from __future__ import annotations

import gc
import json
from pathlib import Path
import resource
import sys
from tempfile import TemporaryDirectory
from time import perf_counter
from weakref import ref

from layauto_v2.domain.publication_codec import content_ref
from layauto_v2.normalization.initial_state import build_proposed_initial_state
from layauto_v2.pipeline import assemble_stage2, publish_stage2
from layauto_v2.repository import PublicationRepository
from layauto_v2.transactions.initialization import InitializationTransaction

from w023_cases import capture, sample


def memory():
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    point = {'peak_rss_bytes': peak if sys.platform == 'darwin' else peak * 1024}
    status = Path('/proc/self/status')
    if status.exists():
        row = next(line for line in status.read_text().splitlines() if line.startswith('VmRSS:'))
        point['current_rss_bytes'] = int(row.split()[1]) * 1024
    return point


def run(directory):
    repo = PublicationRepository()
    root = sample(directory)
    times, rss = {}, {}
    start = perf_counter()

    def mark(stage):
        nonlocal start
        now = perf_counter()
        times[stage] = round(now - start, 4)
        rss[stage] = memory()
        start = perf_counter()

    ready, request = capture(repo, root, 'w023-first')
    before = repo.snapshot()
    mark('capture')
    candidate = build_proposed_initial_state(assemble_stage2(repo, ready, fragment_budget=312))
    mark('existing_assembly')
    original = ref(candidate)
    prepared = InitializationTransaction.prepare(repo, request, ready, candidate)
    mark('checks_and_freeze')
    ctx = repo.initialize(request, prepared)
    mark('atomic_initialize')
    del prepared, candidate, ready
    gc.collect()
    assert original() is None
    mark('release')
    attempt = repo.load_attempt(request.run_id)
    context = repo.read(attempt.context_ref)
    head = repo.read(repo.load_head('L'))
    event = repo.read(head.event_ref)
    snapshot = repo.read(head.snapshot_ref)
    target = repo.read(context.target_ref)
    assert ctx == context and context.head_ref == content_ref(head) and event.snapshot_ref == head.snapshot_ref
    mark('readback')
    after = repo.snapshot()
    facts = snapshot.state
    line, = (f for f in facts['occupancy'] if (f['layer'], f['indices'], f['view']) == ('M1', (2, 2), 'drawn'))
    x0, y0, x1, y1 = line['rect']
    record = facts['geometry']['records'][line['record_id']]
    area, offset = (x1 - x0) * (y1 - y0), record['source']['byte_offset']
    assert (area, offset, head.version, len(head.eco_commits), len(target.differences)) == (130, 2352, 0, 0, 0)
    replay = publish_stage2(repo, request)
    assert replay == context and repo.snapshot() == after
    _, reuse = capture(repo, root, 'w023-reuse', head=context.head_ref.id)
    second = publish_stage2(repo, reuse)
    assert second.head_ref == context.head_ref
    return {
        'python': sys.version.split()[0], 'platform': sys.platform, 'capability': snapshot.binding['capability'],
        'times_seconds': times, 'rss_at_stage_end': rss,
        'content_bytes': {'after_capture': before.content_bytes, 'after_initialize': after.content_bytes,
                          'added': after.content_bytes - before.content_bytes},
        'run': attempt.run_id, 'checkpoint': request.checkpoint_ref.id, 'head': context.head_ref.id,
        'snapshot': head.snapshot_ref.id, 'target': head.target_ref.id, 'event': head.event_ref.id,
        'context': attempt.context_ref.id, 'reuse_context': content_ref(second).id,
        'reuse_head': second.head_ref.id, 'version': head.version, 'eco_commits': len(head.eco_commits),
        'before': [before.attempts[0].phase, before.attempts[0].revision],
        'after': [attempt.phase, attempt.revision], 'candidate_released': original() is None,
        'coordinates_sha256': facts['coordinates']['tech_owners'][4]['sha256'],
        'input_sha256': dict(snapshot.binding['sources']), 'cache_sha256': dict(snapshot.binding['normalized_caches']),
        'fragments': len(facts['occupancy']), 'layers': len(facts['layers']), 'target_differences': len(target.differences),
        'M1': {'indices': line['indices'], 'rect_dbu': line['rect'], 'area_dbu2': area, 'gds_offset': offset},
        'lvs_status': facts['body']['lvs_status'],
    }


if __name__ == '__main__':
    with TemporaryDirectory() as tmp:
        print(json.dumps(run(Path(tmp)), indent=2))
