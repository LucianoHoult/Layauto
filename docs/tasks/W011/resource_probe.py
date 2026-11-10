"""One finite W011 resource sample per fresh process; no production guarantee.

Run each case in a separate process, for example:
  python -B resource_probe.py --root /workspace/Layauto \
    --case normal-direct --output /absolute/normal-direct.json --work /absolute/work
Cases: normal-direct, normal-readback, extraction-mismatch.
No test/support imports, generated answers or EDA invocations.
"""
from __future__ import annotations

import argparse
import builtins
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import resource
import shutil
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch


def sha(data):
    return hashlib.sha256(data).hexdigest()



def source_manifest(root):
    paths = sorted((root / 'layauto_v2').rglob('*.py'))
    paths += [root / 'layauto_v2/py.typed', root / 'pyproject.toml']
    return {str(path.relative_to(root)): sha(path.read_bytes()) for path in paths}


def copied_mismatch(fixture, destination):
    # Copy original fixture bytes only; no oracle/spec/expected is parsed or
    # used as an answer. Complete owner/site inputs are retained unchanged.
    shutil.copytree(fixture, destination)
    for name in ('source.gds', 'query/header.json', 'query/raw/device_info_Q17.txt',
                 'query/normalized/device_regions.yaml', 'body/context.json'):
        shutil.copyfile(fixture / 'failures/extraction_mismatch' / name, destination / name)
    return destination


def forbidden(*args, **kwargs):
    raise AssertionError('pure W011 component or codec attempted IO/repository access')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--case', choices=('normal-direct', 'normal-readback', 'extraction-mismatch'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    args = parser.parse_args()
    args.work.mkdir(parents=True, exist_ok=True)
    root = args.root.resolve()
    fixture = root / 'tests/fixtures/w003_m1'
    sys.path.insert(0, str(root))
    import layauto_v2
    from layauto_v2.domain.publication import InputsReady, RunRequest
    from layauto_v2.importers import read_inputs
    from layauto_v2.normalization import (
        build_geometry, build_effective_geometry, build_local_connectivity,
        build_channel_identity, geometry_from_parse_result, geometry_from_inputs_ready,
    )
    from layauto_v2.normalization.channel_identity_codec import encode_record, decode_record
    from layauto_v2.pipeline import prepare_inputs
    from layauto_v2.repository import PublicationRepository
    assert Path(layauto_v2.__file__).resolve().parent == root / 'layauto_v2'
    before = source_manifest(root)
    times = {}

    def measure(name, call):
        started = time.perf_counter()
        result = call()
        times[name] = time.perf_counter() - started
        return result

    result_info = None
    started_at = datetime.now(timezone.utc).isoformat()
    with tempfile.TemporaryDirectory(prefix='w011-resource-', dir=args.work) as temp:
        selected = copied_mismatch(fixture, Path(temp) / 'input') if args.case == 'extraction-mismatch' else fixture
        repository = None
        ready = None
        attempt = None
        if args.case == 'normal-readback':
            repository = PublicationRepository()
            ready = measure('W006_prepare_inputs', lambda: prepare_inputs(repository, RunRequest(
                proposed_run_id='w011-resource-run', lineage_id='w011-resource-lineage',
                idempotency_key='create-resource', site_path=str(selected / 'site_config.yaml'))))
            assert isinstance(ready, InputsReady)
            checkpoint = repository.load_checkpoint(ready.run_id)
            parse, tool = repository.read(ready.parse_ref), repository.read(ready.tool_ref)
            audits = tuple(repository.read(ref) for ref in ready.evidence_refs)
            attempt = repository.load_attempt(ready.run_id)
            parsed = parse.result
            geometry = measure('W008_adapter_and_build', lambda: build_geometry(
                geometry_from_inputs_ready(ready, checkpoint, parse, tool, audits)))
        else:
            parsed = measure('W005_read_inputs', lambda: read_inputs(selected / 'site_config.yaml'))
            assert parsed.status == 'success', parsed.issues
            geometry = measure('W008_adapter_and_build', lambda: build_geometry(geometry_from_parse_result(parsed)))
        effective = measure('W009_build', lambda: build_effective_geometry(geometry))
        local = measure('W010_build', lambda: build_local_connectivity(effective))
        assert local.status == 'success', local.issues
        with ExitStack() as stack:
            for target in ('open', 'read_bytes', 'read_text', 'resolve'):
                stack.enter_context(patch.object(Path, target, forbidden))
            stack.enter_context(patch.object(builtins, 'open', forbidden))
            stack.enter_context(patch.object(io, 'open', forbidden))
            if repository is not None:
                for target in ('read', 'load_checkpoint', 'load_attempt'):
                    stack.enter_context(patch.object(repository, target, forbidden))
            result = measure('W011_build', lambda: build_channel_identity(local))
            assert result.status == 'success', result.issues
            draft = result.value
            assert draft is not None
            wire = measure('W011_result_encode', lambda: encode_record(result))
            restored = measure('W011_result_decode', lambda: decode_record(wire))
            assert restored == result
        if ready is not None and repository is not None:
            assert repository.load_attempt(ready.run_id) == attempt and attempt.phase == 'unsealed'
        measures = {measurement.channel_ref: measurement for measurement in draft.measurements}
        counts = {row.device_id.name: measures[row.channel_ref].count for row in draft.associations}
        expected = {'MN0': 4, 'MP0': 7} if args.case == 'extraction-mismatch' else {'MN0': 5, 'MP0': 7}
        assert counts == expected, counts
        captured_bytes = sum(len(source.data) for source in parsed.sources)
        result_info = {
            'status': result.status, 'comparison_status': draft.comparison_status,
            'difference_count': len(draft.differences), 'counts': counts,
            'device_seed_count': len(draft.seeds), 'association_count': len(draft.associations),
            'measurement_count': len(draft.measurements),
            'FIN_evaluations': sum(len(m.evaluations) for m in draft.measurements),
            'drawn_record_count': len(draft.local.effective.base.layout.records),
            'drawn_FIN_record_count': sum(r.layer == 'FIN' for r in draft.local.effective.base.layout.records),
            'local_nodes': len(draft.local.nodes), 'local_edges': len(draft.local.edges),
            'local_components': len(draft.local.components), 'T05_audits': len(draft.local.audits),
            'local_enclosure_status': draft.local.local_enclosure_status,
            'raw_capture_count': len(parsed.sources), 'raw_capture_bytes': captured_bytes,
            'capture_sources': [{'uri': source.uri, 'sha256': source.sha256, 'bytes': len(source.data)} for source in parsed.sources],
            'result_wire_bytes': len(wire), 'result_wire_sha256': sha(wire),
            'wire_over_unique_acquisition_bytes': {'numerator': len(wire), 'denominator': captured_bytes},
            'public_roundtrip_equal': True,
        }
    after = source_manifest(root)
    assert before == after, 'source changed during finite measurement'
    receipt = {
        'schema': 'layauto-w011-finite-resource-probe/1', 'case': args.case,
        'started_at_utc': started_at, 'finished_at_utc': datetime.now(timezone.utc).isoformat(),
        'command_argv': [sys.executable, '-B', *sys.argv], 'cwd': str(Path.cwd()),
        'python': sys.version, 'platform': platform.platform(), 'executable': sys.executable,
        'package': str(layauto_v2.__file__), 'probe_sha256': sha(Path(__file__).read_bytes()),
        'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
        'source_manifest': before, 'source_unchanged_during_probe': True,
        'wall_seconds': times, 'result': result_info,
        'process_peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'process_scope': 'Fresh process for this one case; RSS includes imports, all upstream acquisition/builds and complete W011 wire encode/decode. It is a whole-process high watermark, not an incremental allocation.',
        'resource_limits': {'cpu_count': os.cpu_count(), 'cgroup': {name: Path('/sys/fs/cgroup', name).read_text().strip()
                            for name in ('memory.max', 'cpu.max', 'memory.swap.max')},
                            'rlimits': {name: resource.getrlimit(getattr(resource, name))
                                        for name in ('RLIMIT_AS', 'RLIMIT_CPU', 'RLIMIT_DATA', 'RLIMIT_NOFILE', 'RLIMIT_STACK')}},
        'limitations': [
            'One finite synthetic sample in a shared executor; concurrent work can affect elapsed time.',
            'Public constructors/codecs authenticate and retain complete nested W010/W009/W008/W007 capture chains; measured wire/RSS include their repeated encoding and reconstruction.',
            'Not a maximum-input, asymptotic, multi-piece pressure or production performance guarantee.',
            'No full net/body/model/T02/all-rule, complete coordinate, publication, no_change or Stage 6 assurance.',
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'case': args.case, 'result': result_info, 'wall_seconds': times,
                      'process_peak_rss_kib': receipt['process_peak_rss_kib']}, indent=2))


if __name__ == '__main__':
    main()
