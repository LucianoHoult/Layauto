"""Fixed W013 direct/readback/mismatch checkpoint, without a W011 capture.

Run each case in a fresh process from /workspace/Layauto. All original upstream
roots stay alive through public W013 build/encode/decode. Historical A1 timings
are not same-machine measurements. Existing output paths are never overwritten.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gc
import hashlib
import json
from pathlib import Path
import platform
import resource
import sys
import time

ROOT = Path('/workspace/Layauto')
NORMAL = ROOT / 'tests/fixtures/w003_m1'
MISMATCH = Path('/workspace/w012-inputs/extraction-mismatch')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def prepare_mismatch():
    """Restore exactly the old fixed input URI and its original 35 byte hashes."""
    manifest = json.loads((ROOT / 'docs/tasks/W012/A1/preflight.json').read_text())
    assert len(manifest['inputs']) == 35
    restored = []
    for row in manifest['inputs']:
        origin, target = Path(row['origin']), Path(row['target'])
        assert target.is_relative_to(MISMATCH)
        data = origin.read_bytes()
        assert len(data) == row['bytes'] and sha(data) == row['sha256']
        if target.exists():
            assert target.read_bytes() == data, 'existing fixed input differs: ' + str(target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        restored.append({'uri': str(target), 'sha256': sha(data), 'bytes': len(data)})
    return restored


def run(case, output, terminal):
    sys.path.insert(0, str(ROOT))
    sys.path.insert(1, str(ROOT / 'docs/tasks/W013/verification-tools'))
    from source_identity import files_manifest, runtime_manifest, source_id, source_names
    import layauto_v2
    from layauto_v2.domain.codec import canonical_bytes, decode
    from layauto_v2.domain.publication import InputsReady, RunRequest
    from layauto_v2.importers import read_inputs
    from layauto_v2.normalization import (
        build_geometry, build_effective_geometry, build_local_connectivity,
        geometry_from_parse_result, geometry_from_inputs_ready,
    )
    if terminal == 'w013':
        from layauto_v2.normalization import build_net_annotation
        from layauto_v2.normalization import net_annotation_codec as codec
    else:
        from layauto_v2.normalization import local_connectivity_codec as codec
    from layauto_v2.normalization import local_connectivity_codec, net_annotation
    from layauto_v2.pipeline import prepare_inputs
    from layauto_v2.repository import PublicationRepository

    assert Path(layauto_v2.__file__).resolve().is_relative_to(ROOT / 'layauto_v2')
    selected = MISMATCH if case == 'extraction-mismatch' else NORMAL
    if selected == MISMATCH:
        for row in json.loads((ROOT / 'docs/tasks/W012/A1/preflight.json').read_text())['inputs']:
            assert sha(Path(row['target']).read_bytes()) == row['sha256']
    identity = files_manifest(ROOT, source_names(ROOT))
    started = datetime.now(timezone.utc).isoformat()
    gc.collect()
    phases = {}
    observed_calls = []
    current_phase = ['acquisition']

    def observe(module, name, label):
        original = getattr(module, name)
        def observed(*args, **kwargs):
            tick = time.perf_counter()
            try:
                return original(*args, **kwargs)
            finally:
                observed_calls.append({'phase': current_phase[0], 'call': label,
                                       'inclusive_seconds': time.perf_counter() - tick})
        setattr(module, name, observed)

    # Observe only calls that the public paths already make. No extra capture,
    # encoding, authentication, or weakened API is introduced by these timers.
    observe(local_connectivity_codec, 'decode_record', 'W010_public_decode')
    observe(net_annotation, '_require_input', 'W013_full_input_requirement')
    observe(net_annotation, 'normalize', 'W007_source_normalization')
    observe(net_annotation, '_capture_binding', 'W013_capture_binding_digest')
    observe(net_annotation, 'build_net_annotation_draft', 'W013_neutral_draft_build')

    def measure(name, call):
        print('START ' + name, flush=True)
        current_phase[0] = name
        tick = time.perf_counter()
        result = call()
        phases[name] = {'seconds': time.perf_counter() - tick,
                        'process_hwm_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
        print('DONE ' + name + ' ' + str(phases[name]['seconds']), flush=True)
        return result

    repository = ready = checkpoint = parse = tool = audits = attempt = None
    if case == 'normal-readback':
        repository = PublicationRepository()
        request = RunRequest(proposed_run_id='w012-investigation-run',
                             lineage_id='w012-investigation-lineage',
                             idempotency_key='create-w012',
                             site_path=str(selected / 'site_config.yaml'))
        ready = measure('W006_prepare_inputs', lambda: prepare_inputs(repository, request))
        assert isinstance(ready, InputsReady)

        def caller_reads():
            return (repository.load_checkpoint(ready.run_id), repository.read(ready.parse_ref),
                    repository.read(ready.tool_ref), tuple(repository.read(ref) for ref in ready.evidence_refs),
                    repository.load_attempt(ready.run_id))
        checkpoint, parse, tool, audits, attempt = measure('W006_caller_reads', caller_reads)
        parsed = parse.result
        geometry = measure('W008_adapter_and_build', lambda: build_geometry(
            geometry_from_inputs_ready(ready, checkpoint, parse, tool, audits)))
    else:
        parsed = measure('W005_read_inputs', lambda: read_inputs(selected / 'site_config.yaml'))
        assert parsed.status == 'success', parsed.issues
        geometry = measure('W008_adapter_and_build', lambda: build_geometry(geometry_from_parse_result(parsed)))
    effective = measure('W009_build', lambda: build_effective_geometry(geometry))
    local = measure('W010_build', lambda: build_local_connectivity(effective))
    assert local.status == 'success' and local.value is not None
    net_result = measure('W013_build', lambda: build_net_annotation(local)) if terminal == 'w013' else local
    assert net_result.status == 'success' and net_result.value is not None, net_result.issues
    prefix = 'W013' if terminal == 'w013' else 'W010_reference'
    net_wire = measure(prefix + '_result_encode', lambda: codec.encode_record(net_result))
    net_restored = measure(prefix + '_result_decode', lambda: codec.decode_record(net_wire))
    assert net_restored == net_result
    assert net_restored.body_evidence == local.body_evidence
    if terminal == 'w013':
        assert net_restored.input == local
        assert len(net_result.value.targets) == 14 and len(net_result.value.components) == 6
    if ready is not None:
        assert repository.load_attempt(ready.run_id) == attempt and attempt.phase == 'unsealed'
        assert repository.load_checkpoint(ready.run_id) == checkpoint
        assert repository.read_terminal(ready.run_id) is None
        assert local.input.input.input.readback is not None
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if terminal == 'w013':
        actual_counts = {name: sum(row['phase'] == name and row['call'] == 'W010_public_decode'
                                  for row in observed_calls)
                         for name in ('W013_build', 'W013_result_encode', 'W013_result_decode')}
        assert actual_counts == {'W013_build': 1, 'W013_result_encode': 1, 'W013_result_decode': 2}, actual_counts
    # Keep this tuple alive until after the fixed peak, matching the reviewed
    # replacement of old W011 result/restored/wire with their W013 siblings.
    retained = (parsed, geometry, effective, local, net_result, net_restored, net_wire,
                repository, ready, checkpoint, parse, tool, audits, attempt)
    tree = decode(net_wire)  # Post-measurement packet decomposition, not another product call.
    old_wire = canonical_bytes(tree['captured_input_wire']) if terminal == 'w013' else net_wire
    body = {key: value for key, value in tree.items() if key != 'captured_input_wire'} if terminal == 'w013' else {}
    report = {
        'classification': 'W013-first-complete-fixed-combination-resource-checkpoint' if terminal == 'w013'
                          else 'same-machine-W010-reference-workload-not-W013-product',
        'terminal_component': terminal,
        'case': case, 'started_at_utc': started,
        'argv': sys.argv, 'cwd': str(Path.cwd()),
        'python': sys.version, 'executable': sys.executable, 'platform': platform.platform(),
        'runtime_root': str(ROOT), 'package': str(layauto_v2.__file__),
        'input_site': str(selected / 'site_config.yaml'), 'probe_sha256': sha(Path(__file__).read_bytes()),
        'source_id': source_id(identity), 'files': identity,
        'runtime_files': runtime_manifest(ROOT / 'layauto_v2'),
        'phases': phases, 'process_peak_rss_kib_before_postmeasurement_analysis': peak,
        'observed_existing_calls': observed_calls,
        'observation_note': 'Inclusive timers overlap; never sum nested call buckets as disjoint costs.',
        'wire_bytes': len(net_wire), 'wire_sha256': sha(net_wire),
        'retained_W010_wire_bytes': len(old_wire), 'retained_W010_wire_sha256': sha(old_wire),
        'W013_compact_envelope_bytes_without_input_field': len(canonical_bytes(body)),
        'wire_input_field_occurrences': 1 if terminal == 'w013' else 0, 'W011_result_instances': 0,
        'retained_roots': ['parsed', 'geometry', 'effective', 'local', 'net_result', 'net_restored',
                           'net_wire', 'repository', 'ready', 'checkpoint', 'parse', 'tool', 'audits', 'attempt'],
        'gc_enabled': gc.isenabled(), 'gc_threshold': gc.get_threshold(),
        'capture_sources': [{'uri': item.uri, 'sha256': item.sha256, 'bytes': len(item.data)} for item in parsed.sources],
        'local_counts': {'nodes': len(local.value.nodes), 'edges': len(local.value.edges),
                         'components': len(local.value.components)},
        'public_roundtrip_equal': True,
        'readback_unsealed_checkpoint_unchanged_no_terminal': ready is not None,
        'limitations': ['One fresh-process sample per case is not a stable performance improvement claim.',
                       'Unchanged upstream and new W013 phases are separately reported.',
                       'The primary HWM was fixed before packet decomposition/source identity bookkeeping.',
                       'No complete W011 capture is constructed by this workload.'],
    }
    assert retained[4] is net_result
    assert files_manifest(ROOT, source_names(ROOT)) == identity, 'source changed during resource probe'
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as stream:
        stream.write(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'case': case, 'wire_bytes': len(net_wire), 'peak_kib': peak,
                      'new_seconds': sum(row['seconds'] for key, row in phases.items() if key.startswith('W013'))}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-fixed-mismatch', action='store_true')
    parser.add_argument('--case', choices=('normal-direct', 'normal-readback', 'extraction-mismatch'))
    parser.add_argument('--terminal', choices=('w013', 'w010'), default='w013')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error('Output exists; preserve the original attempt and choose a new path')
    if args.prepare_fixed_mismatch:
        restored = prepare_mismatch()
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open('x') as stream:
            stream.write(json.dumps({'classification': 'same-original-fixed-input-restoration',
                                     'inputs': restored}, indent=2) + '\n')
    elif args.case is not None:
        run(args.case, args.out, args.terminal)
    else:
        parser.error('--case or --prepare-fixed-mismatch is required')


if __name__ == '__main__':
    main()
