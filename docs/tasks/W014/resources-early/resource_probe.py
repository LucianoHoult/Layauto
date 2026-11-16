"""W014 fresh-process three-route resource probe, with a same-environment W013 reference.

Invoke one component/case per process. No product call is skipped or weakened.
All original upstream roots remain alive until after the public encode/decode peak.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gc
import hashlib
import importlib
import importlib.metadata
import json
from pathlib import Path
import platform
import resource
import sys
import time


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def prepare_mismatch(fixture: Path, destination: Path) -> list[dict[str, object]]:
    """Restore captured synthetic mismatch bytes at one URI for both components."""
    replacements = {'source.gds', 'query/header.json', 'query/raw/device_info_Q17.txt',
                    'query/normalized/device_regions.yaml', 'body/context.json'}
    sources = [path for path in fixture.rglob('*') if path.is_file() and
               not path.relative_to(fixture).parts[0] in ('failures', 'special')]
    rows: list[dict[str, object]] = []
    for path in sources:
        name = str(path.relative_to(fixture))
        origin = fixture / 'failures/extraction_mismatch' / name if name in replacements else path
        target, data = destination / name, origin.read_bytes()
        if target.exists():
            if target.read_bytes() != data:
                raise RuntimeError('Fixed mismatch URI already has different bytes: ' + str(target))
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        rows.append({'relative_path': name, 'uri': str(target), 'sha256': sha(data), 'bytes': len(data)})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--case', choices=('normal-direct', 'normal-readback', 'extraction-mismatch'))
    parser.add_argument('--component', choices=('w013', 'w014'), default='w014')
    parser.add_argument('--mismatch-dir', type=Path, default=Path('/workspace/work/w014-resource-inputs/extraction-mismatch'))
    parser.add_argument('--prepare-fixed-mismatch', action='store_true')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error('Output exists; choose a new path and preserve the original attempt')
    root, output = args.root.resolve(), args.out.resolve()
    fixture = root / 'tests/fixtures/w003_m1'
    mismatch = args.mismatch_dir.resolve()
    if args.prepare_fixed_mismatch:
        rows = prepare_mismatch(fixture, mismatch)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps({'classification': 'fixed-input-preparation-not-product-test',
                                     'inputs': rows}, indent=2) + '\n')
        return
    if args.case is None:
        parser.error('--case or --prepare-fixed-mismatch is required')
    sys.path.insert(0, str(root))
    from source_identity import files_manifest, runtime_manifest, source_id, source_names
    import layauto_v2
    from layauto_v2.domain.codec import canonical_bytes, decode
    from layauto_v2.domain.publication import InputsReady, RunRequest
    from layauto_v2.importers import read_inputs
    from layauto_v2.normalization import (
        build_geometry, build_effective_geometry, build_local_connectivity,
        geometry_from_parse_result, geometry_from_inputs_ready,
    )
    from layauto_v2.normalization import local_connectivity_codec
    from layauto_v2.pipeline import prepare_inputs
    from layauto_v2.repository import PublicationRepository
    module_name = 'net_annotation' if args.component == 'w013' else 'terminal_relations'
    component = importlib.import_module('layauto_v2.normalization.' + module_name)
    codec = importlib.import_module('layauto_v2.normalization.' + module_name + '_codec')
    builder = getattr(component, 'build_' + module_name)
    if not Path(layauto_v2.__file__).resolve().is_relative_to(root / 'layauto_v2'):
        raise RuntimeError('Resource probe imported a different runtime source')
    selected = mismatch if args.case == 'extraction-mismatch' else fixture
    identity = files_manifest(root, source_names(root))
    observed: list[dict[str, object]] = []
    current_phase = ['acquisition']
    phases: dict[str, dict[str, object]] = {}
    original_calls: list[tuple[object, str, object]] = []

    def observe(module: object, name: str, label: str) -> None:
        if not hasattr(module, name):
            return
        original = getattr(module, name)
        def wrapped(*positional: object, **keywords: object) -> object:
            tick = time.perf_counter()
            try:
                return original(*positional, **keywords)
            finally:
                observed.append({'phase': current_phase[0], 'call': label,
                                 'inclusive_seconds': time.perf_counter() - tick})
        original_calls.append((module, name, original))
        setattr(module, name, wrapped)

    observe(local_connectivity_codec, 'decode_record', 'W010_public_decode')
    for name in ('normalize', '_require_input', '_capture_binding',
                 'build_channel_identity_draft', 'build_net_annotation_draft', 'build_terminal_relations_draft'):
        observe(component, name, name)
    if args.component == 'w014':
        neutral = importlib.import_module('layauto_v2.derive.terminal_relations')
        for name, label in (('build_channel_identity_draft', 'W011_neutral_build'),
                            ('build_net_annotation_draft', 'W013_neutral_build'),
                            ('evaluate_body', 'body_evaluate')):
            observe(neutral, name, label)

    def measure(name: str, operation: object) -> object:
        print('START ' + name, flush=True)
        current_phase[0] = name
        tick = time.perf_counter()
        value = operation()
        phases[name] = {'seconds': time.perf_counter() - tick,
                        'process_hwm_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
        print('DONE ' + name + ' ' + str(phases[name]['seconds']), flush=True)
        return value

    started = datetime.now(timezone.utc).isoformat()
    gc.collect()
    repository = ready = checkpoint = parse = tool = audits = attempt = None
    if args.case == 'normal-readback':
        repository = PublicationRepository()
        request = RunRequest(proposed_run_id='w014-resource-run', lineage_id='w014-resource-lineage',
                             idempotency_key='w014-resource-create', site_path=str(selected / 'site_config.yaml'))
        ready = measure('W006_prepare_inputs', lambda: prepare_inputs(repository, request))
        assert isinstance(ready, InputsReady)
        def reads() -> tuple[object, ...]:
            return (repository.load_checkpoint(ready.run_id), repository.read(ready.parse_ref),
                    repository.read(ready.tool_ref), tuple(repository.read(ref) for ref in ready.evidence_refs),
                    repository.load_attempt(ready.run_id))
        checkpoint, parse, tool, audits, attempt = measure('W006_caller_reads', reads)
        parsed = parse.result
        geometry = measure('W008_adapter_build', lambda: build_geometry(
            geometry_from_inputs_ready(ready, checkpoint, parse, tool, audits)))
    else:
        parsed = measure('W005_read_inputs', lambda: read_inputs(selected / 'site_config.yaml'))
        assert parsed.status == 'success', parsed.issues
        geometry = measure('W008_adapter_build', lambda: build_geometry(geometry_from_parse_result(parsed)))
    effective = measure('W009_build', lambda: build_effective_geometry(geometry))
    local = measure('W010_build', lambda: build_local_connectivity(effective))
    assert local.status == 'success' and local.value is not None, local.issues
    prefix = args.component.upper()
    result = measure(prefix + '_build', lambda: builder(local))
    assert result.status == 'success' and result.value is not None, result.issues
    wire = measure(prefix + '_encode', lambda: codec.encode_record(result))
    restored = measure(prefix + '_decode', lambda: codec.decode_record(wire))
    assert restored == result and restored.input == local
    assert result.body_evidence is local.body_evidence
    if args.component == 'w014':
        assert len(result.value.relations) == 8
        assert result.value.comparison_status == 'equal'
    if ready is not None:
        assert repository.load_attempt(ready.run_id) == attempt and attempt.phase == 'unsealed'
        assert repository.load_checkpoint(ready.run_id) == checkpoint
        assert repository.read_terminal(ready.run_id) is None
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    authentication_counts = {name: sum(row['phase'] == name and row['call'] == 'W010_public_decode'
                              for row in observed) for name in (prefix + '_build', prefix + '_encode', prefix + '_decode')}
    assert authentication_counts == {prefix + '_build': 1, prefix + '_encode': 1, prefix + '_decode': 2}, authentication_counts
    retained = (parsed, geometry, effective, local, result, restored, wire,
                repository, ready, checkpoint, parse, tool, audits, attempt)
    for module, name, original in reversed(original_calls):
        setattr(module, name, original)
    tree = decode(wire)
    assert type(tree).__name__ == 'FrozenMap'
    input_field = 'captured_input_wire'
    if input_field not in tree:
        raise AssertionError('Expected single captured_input_wire field; update probe for actual public codec')
    old_wire = canonical_bytes(tree[input_field])
    compact = {key: value for key, value in tree.items() if key != input_field}
    report = {'classification': 'W014-resource-checkpoint' if args.component == 'w014' else 'same-environment-W013-reference',
              'component': args.component, 'case': args.case, 'started_at_utc': started,
              'argv': sys.argv, 'cwd': str(Path.cwd()), 'python': sys.version, 'executable': sys.executable,
              'platform': platform.platform(), 'package': str(layauto_v2.__file__), 'input_site': str(selected / 'site_config.yaml'),
              'distributions': {item.metadata['Name']: item.version for item in importlib.metadata.distributions()},
              'source_id': source_id(identity), 'files': identity, 'runtime_files': runtime_manifest(root / 'layauto_v2'),
              'probe_sha256': sha(Path(__file__).read_bytes()), 'phases': phases,
              'process_peak_rss_kib_before_postmeasurement_analysis': peak,
              'observed_existing_calls': observed,
              'authentication_calls_by_phase': authentication_counts,
              'neutral_builder_calls_by_phase': {name: {label: sum(row['phase'] == name and row['call'] == label for row in observed)
                  for label in ('W011_neutral_build', 'W013_neutral_build', 'body_evaluate')}
                  for name in (prefix + '_build', prefix + '_encode', prefix + '_decode')},
              'wire_bytes': len(wire), 'wire_sha256': sha(wire),
              'retained_W010_wire_bytes': len(old_wire), 'retained_W010_wire_sha256': sha(old_wire),
              'compact_envelope_bytes_without_input_field': len(canonical_bytes(compact)),
              'root_input_field_occurrences': sum(key == input_field for key in tree),
              'capture_sources': [{'uri': item.uri, 'sha256': item.sha256, 'bytes': len(item.data)} for item in parsed.sources],
              'local_counts': {'nodes': len(local.value.nodes), 'edges': len(local.value.edges), 'components': len(local.value.components)},
              'public_roundtrip_equal': True, 'readback_unsealed_unchanged_no_terminal': ready is not None,
              'retained_roots': ['parsed', 'geometry', 'effective', 'local', 'result', 'restored', 'wire',
                                 'repository', 'ready', 'checkpoint', 'parse', 'tool', 'audits', 'attempt'],
              'limitations': ['One fresh-process sample is not a stable performance improvement claim.',
                             'Inclusive observed call timers overlap and must not be summed as disjoint cost.',
                             'Peak is fixed before packet decomposition and source bookkeeping.',
                             'W013 reference and W014 use the same interpreter, fixed inputs and run identity.']}
    assert retained[4] is result
    assert files_manifest(root, source_names(root)) == identity, 'source changed during probe'
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as stream:
        stream.write(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'component': args.component, 'case': args.case, 'wire_bytes': len(wire), 'peak_kib': peak}), flush=True)


if __name__ == '__main__':
    main()
