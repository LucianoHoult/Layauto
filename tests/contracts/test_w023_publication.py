"""Stage 2 contracts observed through content refs, real captures and root switches."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from threading import Barrier

import pytest
import yaml

from layauto_v2.domain.codec import FrozenMap
from layauto_v2.domain.publication import RunRequest
from layauto_v2.domain.publication_codec import content_ref, decode_record, encode_record
from layauto_v2.normalization.initial_state import build_proposed_initial_state
from layauto_v2.pipeline import assemble_stage2, publish_stage2
from layauto_v2.repository import PublicationRepository, RepositoryConflict
from layauto_v2.transactions.initialization import InitializationRejected, InitializationTransaction
from w005_cases import rebind, without_cache, write_json
from w008_geometry_cases import edit_geometry
from w018_cases import COORDINATE_URI
from w023_cases import capture, sample


def counts(repo):
    return Counter(ref.kind for ref in repo.snapshot().content_refs)


def conflict(code, operation, *args):
    with pytest.raises(RepositoryConflict) as caught:
        operation(*args)
    assert caught.value.code == code
    return str(caught.value)


def candidate(repo, ready, request):
    return build_proposed_initial_state(assemble_stage2(repo, ready, fragment_budget=request.fragment_budget))


def alter_grid(root, change):
    path = root / COORDINATE_URI
    doc = yaml.safe_load(path.read_bytes())
    change(doc['coordinate_projection']['layers'])
    write_json(path, doc)
    rebind(root)


@pytest.fixture(scope='module')
def published(tmp_path_factory):
    root = sample(tmp_path_factory.mktemp('baseline'))
    faults = set()

    def inject(point):
        if point in faults:
            faults.remove(point)
            raise OSError(point)

    repo = PublicationRepository(fault_injector=inject)
    a, ar = capture(repo, root, 'A')
    b, br = capture(repo, root, 'B')
    assert repo.load_head('L') is None
    ca = candidate(repo, a, ar)
    cb = candidate(repo, b, br)
    start = repo.snapshot()
    conflict('BindingConflict', InitializationTransaction.prepare, repo, ar, a, cb)
    other = PublicationRepository()
    a2, ar2 = capture(other, root, 'A')
    assert ar2 == ar and a2 == a
    conflict('BindingConflict', InitializationTransaction.prepare, other, ar2, a2, ca)
    conflict('BindingConflict', InitializationTransaction.prepare, repo, replace(ar, fragment_budget=0), a, ca)
    conflict('ReadbackConflict', InitializationTransaction.prepare, repo, ar, replace(a, evidence_refs=()), ca)
    conflict('ReadbackConflict', InitializationTransaction.prepare, repo, ar, replace(a, value=FrozenMap({})), ca)
    pa = InitializationTransaction.prepare(repo, ar, a, ca)
    pb = InitializationTransaction.prepare(repo, br, b, cb)
    del ca, cb
    conflict('BindingConflict', other.initialize, ar2, pa)
    with pytest.raises(ValueError):
        replace(pa, target=pb.target)
    assert repo.snapshot() == start
    faults.add('initialize.before_switch')
    with pytest.raises(OSError, match='before_switch'):
        repo.initialize(ar, pa)
    assert repo.snapshot() == start and repo.read(a.parse_ref).result.status == 'success'

    gate = Barrier(2)
    faults.add('initialize.after_switch')

    def compete(pair):
        req, prepared = pair
        gate.wait(timeout=20)
        try:
            repo.initialize(req, prepared)
        except RepositoryConflict as exc:
            assert exc.code == 'HeadConflict'
            return 'lost'
        except OSError as exc:
            assert str(exc) == 'initialize.after_switch'
            return 'won'
        pytest.fail('winning caller should lose its response')

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(compete, [(ar, pa), (br, pb)]))
    assert sorted(outcomes) == ['lost', 'won']
    win = outcomes.index('won')
    request, loser = ((ar, b), (br, a))[win]
    assert repo.load_attempt(loser.run_id) == loser.attempt
    assert repo.read(loser.checkpoint_ref).completed[-1] == loser.evidence_refs[-1]
    after = repo.snapshot()
    assert after.generation == start.generation + 1 and after.idempotency_count == start.idempotency_count + 1
    context = publish_stage2(repo, request)
    assert context == repo.read(repo.load_attempt(request.run_id).context_ref)
    assert repo.snapshot() == after and context.head_ref == repo.load_head('L')
    assert {kind: counts(repo)[kind] for kind in ('state_head', 'initialization_event', 'snapshot')} == {
        'state_head': 1, 'initialization_event': 1, 'snapshot': 1}
    return repo, request, context, faults


def test_competition_guards_and_response_recovery(published):
    repo, req, ctx, _ = published
    head = repo.read(ctx.head_ref)
    event = repo.read(head.event_ref)
    assert head.version == 0 and head.eco_commits == ()
    assert event.snapshot_ref == head.snapshot_ref and event.checkpoint_ref == req.checkpoint_ref
    assert event.lineage_id == head.lineage_id == req.lineage_id
    assert (repo.load_attempt(req.run_id).phase, repo.load_attempt(req.run_id).revision) == ('sealed_open', 2)
    assert repo.read_terminal(req.run_id) is None
    before = repo.snapshot()
    conflict('IdempotencyConflict', publish_stage2, repo, replace(req, fragment_budget=313))
    conflict('TransitionConflict', publish_stage2, repo, replace(req, idempotency_key='another'))
    conflict('HeadConflict', repo.create_attempt, RunRequest('late', 'L', 'create', '/nowhere'))
    assert repo.snapshot() == before


def test_snapshot_geometry_topology_identity_and_assurance(published):
    repo, req, ctx, _ = published
    head = repo.read(ctx.head_ref)
    snapshot = repo.read(head.snapshot_ref)
    s = snapshot.state
    assert repo.read(head.target_ref).differences == ()
    assert s['semantic_assurance'] == 'committed_unverified'
    assert Counter(f['view'] for f in s['occupancy']) == {'drawn': 220, 'effective': 92}
    geo, graph, ann = s['geometry'], s['connectivity'], s['annotation']
    assert len(geo['records']) == 40 and len(s['layers']) == 15
    assert s['layers']['POLY']['gate_track_numbers_available'] is True
    tip, = (f for f in s['occupancy'] if (f['layer'], f['indices'], f['view']) == ('M1', (2, 2), 'drawn'))
    assert tip['rect'] == (32, 48, 45, 58) and (45-32)*(58-48) == 130
    assert geo['records'][tip['record_id']]['source']['byte_offset'] == 2352
    li, = (f for f in s['occupancy'] if (f['layer'], f['indices'], f['view']) == ('LI', (1, 3), 'effective'))
    assert li['rect'] == (28, 30, 34, 40)
    assert geo['pieces'][li['piece_id']]['region_ref']['sha256'] == li['region_id']
    assert geo['regions'][li['region_id']]['owner_id'] == li['record_id']
    assert geo['records'][li['record_id']]['source']['byte_offset'] == 1648
    tid, = (k for k, v in ann['targets'].items() if v['id']['region_ref']['sha256'] == li['region_id'])
    t = ann['targets'][tid]
    assert graph['nodes'][t['node']]['region_id'] == li['region_id']
    members = graph['components'][t['component']]
    assert t['node'] in members and len(members) == 3
    assert (len(graph['nodes']), len(graph['edges']), len(graph['components'])) == (14, 8, 6)
    f, = (v for v in ann['fragments'].values() if v['target_ref']['sha256'] == tid and v['status'] == 'annotated')
    r, = f['rectangles']
    assert r['x0'] <= 28 < 34 <= r['x1'] and r['y0'] <= 30 < 40 <= r['y1']
    seed, = (ann['evidence'][e['sha256']] for e in f['evidence_refs'])
    assert (seed['record']['record_id'], seed['query_key']['identity'], seed['net_id']['name']) == ('R04', 'n_lo', 'VSS')
    assert seed['record']['field_sources']['vertices_nm']['sources'][0]['path'] == 'query/raw/net_shapes_n_lo.txt'
    assert any(f['status'] == 'unknown' and not f['net_ids'] for f in ann['fragments'].values())
    assert ann['unknown_conductor_policy'] == 'suspect_conductor'
    assert s['body']['local_graph_union'] is False and s['body']['lvs_status'] == 'not_run'
    bodies = [r for r in s['terminals'] if r['target']['role'] == 'B']
    assert {r['target']['device_id']['name']: r['observed_net_ids'][0]['name'] for r in bodies} == {
        'MN0': 'VSS', 'MP0': 'VDD'}
    assert all(not r['local_observed_net_ids'] and r['context_path'] for r in bodies)
    assert s['body_sources'][0]['uri'] == 'body/context.json'
    with pytest.raises(TypeError):
        s['occupancy'][0]['indices'] = (99,)
    with pytest.raises(FrozenInstanceError):
        head.version = 1
    for ref in (ctx.head_ref, head.snapshot_ref, head.event_ref, head.target_ref, repo.load_attempt(req.run_id).ref):
        record = repo.read(ref)
        assert content_ref(decode_record(encode_record(record))) == ref


def test_new_run_seals_own_checkpoint_and_replays(published, tmp_path):
    repo, _, old, faults = published
    root = sample(tmp_path)
    ready, request = capture(repo, root, 'reuse', head=old.head_ref.id)
    assert ready.checkpoint_ref != old.checkpoint_ref
    before = repo.snapshot()
    old_counts = counts(repo)
    faults.add('seal_context.before_switch')
    with pytest.raises(OSError, match='before_switch'):
        publish_stage2(repo, request)
    assert repo.snapshot() == before
    faults.add('seal_context.after_switch')
    with pytest.raises(OSError, match='after_switch'):
        publish_stage2(repo, request)
    sealed = repo.snapshot()
    ctx = publish_stage2(repo, request)
    assert ctx.head_ref == old.head_ref and ctx.target_ref == old.target_ref
    assert ctx.checkpoint_ref == ready.checkpoint_ref and ctx.binding_digest == old.binding_digest
    assert repo.read(repo.load_attempt('reuse').context_ref) == ctx
    assert counts(repo) - old_counts == {'attempt': 1, 'sealed_context': 1}
    assert repo.snapshot() == sealed and sealed.generation == before.generation + 1


@pytest.mark.parametrize('change', ['coordinate', 'query'])
def test_existing_head_rejects_rebound_input(published, tmp_path, change):
    repo, _, old, _ = published
    root = sample(tmp_path)
    if change == 'coordinate':
        alter_grid(root, lambda layers: layers['M1']['x_edges'].update(cells=12))
        changed = COORDINATE_URI
    else:
        changed = 'query/raw/net_shapes_n_lo.txt'
        raw = root / changed
        raw.write_bytes(raw.read_bytes().replace(b'600 560\n', b'1000 560\n').replace(b'600 680\n', b'1000 680\n'))
        without_cache(root)
        rebind(root)
    ready, req = capture(repo, root, change, head=old.head_ref.id)
    before = repo.snapshot()
    conflict('RevisionConflict', publish_stage2, repo, replace(req, expected_revision=0))
    conflict('HeadConflict', publish_stage2, repo, replace(req, expected_state_head='stale'))
    bad = replace(req.checkpoint_ref, digest='0'*64)
    conflict('RefConflict', publish_stage2, repo, replace(req, checkpoint_ref=bad))
    message = conflict('BindingConflict', publish_stage2, repo, req)
    assert changed in message and repo.snapshot() == before
    assert repo.load_attempt(change) == ready.attempt and repo.read(ready.parse_ref).result.status == 'success'
    head = repo.read(old.head_ref)
    sources = {s.uri: s.sha256 for s in repo.read(ready.tool_ref).sources}
    assert repo.read(head.snapshot_ref).binding['sources'][changed] != sources[changed]


@pytest.mark.parametrize('case', ['missing', 'outside'])
def test_failed_layers_keep_only_input_audits(tmp_path, case):
    root = sample(tmp_path)
    if case == 'missing':
        alter_grid(root, lambda layers: layers.pop('BTAP_N'))
    else:
        edit_geometry(root, append=[('MARKER', (159, 10, 161, 12))])
    repo = PublicationRepository()
    ready, req = capture(repo, root, case)
    before = repo.snapshot()
    with pytest.raises(InitializationRejected) as caught:
        publish_stage2(repo, req)
    checks = caught.value.checks
    if case == 'missing':
        issue, = checks.layers['BTAP_N'].projection_issues
        assert (issue.code, issue.source.field) == ('RequiredProjectionUnavailable', '/coordinate_projection/layers/BTAP_N')
    else:
        issue, = checks.layers['MARKER'].frame_issues
        assert issue.code == 'OutsideFrame' and issue.source.uri == 'source.gds' and issue.source.byte_offset
    assert repo.snapshot() == before and repo.load_head('L') is None
    assert repo.read(ready.parse_ref).result.status == 'success'


def test_c13_and_complete_two_dimensional_gate(tmp_path):
    root = sample(tmp_path, c13=True)
    alter_grid(root, lambda layers: layers.update(POLY=layers['OD']))
    repo = PublicationRepository()
    _, req = capture(repo, root, 'C13', budget=400)
    ctx = publish_stage2(repo, req)
    state = repo.read(repo.read(ctx.head_ref).snapshot_ref).state
    target = repo.read(ctx.target_ref)
    delta, = target.differences
    assert (delta['operand_ref']['name'], delta['axis'], delta['semantic_before']['lexeme'],
            delta['semantic_after']['lexeme']) == ('MN0', 'channel_length', '4n', '5n')
    for circuit, expected in ((state['current'], '4n'), (target.circuit, '5n')):
        mn, = (d for d in circuit['cells'][0]['devices'] if d['id']['name'] == 'MN0')
        length, = (p for p in mn['parameters'] if p['axis'] == 'channel_length')
        assert length['lexeme'] == expected
    assert 'planner_admission_required' in delta['obligations']
    assert state['layers']['POLY']['gate_track_numbers_available'] is False
    gate = [f for f in state['occupancy'] if f['layer'] == 'POLY']
    assert len(gate) == 36 and sum((x1-x0)*(y1-y0) for x0,y0,x1,y1 in [f['rect'] for f in gate]) == 720


def test_bad_stored_digest_refuses_seal_without_changing_root(published, tmp_path, monkeypatch):
    repo, _, original, _ = published
    root = sample(tmp_path)
    ready, request = capture(repo, root, 'bad-digest', head=original.head_ref.id)
    # Fault injection in the backend, with all valid public refs left intact.
    clean_root = repo._root
    damaged = replace(clean_root, contents=tuple(
        (ref, data + b' ' if ref == ready.parse_ref else data) for ref, data in clean_root.contents))
    with monkeypatch.context() as fault:
        fault.setattr(repo, '_root', damaged)
        message = conflict('RefConflict', publish_stage2, repo, request)
        assert ready.parse_ref.id in message and repo._root is damaged
        assert repo.load_attempt(ready.run_id) == ready.attempt and repo.load_head('L') == original.head_ref
    assert repo.read(ready.parse_ref).result.status == 'success'


def test_baseline_wire_rejects_invalid_version_or_missing_owner(published):
    from layauto_v2.domain.codec import canonical_bytes, decode
    repo, _, context, _ = published
    head = repo.read(context.head_ref)
    snapshot = repo.read(head.snapshot_ref)
    for version in (True, 1, -1):
        with pytest.raises(ValueError):
            replace(snapshot, version=version)
    with pytest.raises(ValueError):
        replace(snapshot, state=FrozenMap({k: v for k, v in snapshot.state.items() if k != 'annotation'}))
    wire = decode(encode_record(context))
    fields = dict(wire['value']['fields'])
    fields['schema_version'] = {'scalar': 'future/2'}
    with pytest.raises(ValueError):
        decode_record(canonical_bytes({'wire_schema': wire['wire_schema'],
                                       'value': {'record': 'SealedContext', 'fields': fields}}))
