"""W016 candidate parity: complete DTO + public encode, exact baseline comparison.

Approved verification reuse: each baseline completed closed decode/DTO equality.
The candidate still builds and authenticates the complete old chain, encodes with
its real public codec and compares all bytes. It does not repeat large decoding
or store a duplicate equal gzip chain. Final frozen-source codec tests cover
candidate decode/rejection behavior. Baseline report and snapshot hashes are
verified before adoption; original failed attempts are never overwritten.
"""
from __future__ import annotations

import argparse
from dataclasses import fields, is_dataclass
from fractions import Fraction
import gc
import gzip
import hashlib
import importlib
import importlib.metadata
import json
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def inventory(root: Path, selected: tuple[str, ...]) -> dict[str, str]:
    rows: dict[str, str] = {}
    for name in selected:
        source = root / name
        paths = sorted(source.rglob('*')) if source.is_dir() else [source]
        for path in paths:
            if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
                rows[str(path.relative_to(root))] = sha(path.read_bytes())
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--site', type=Path, required=True)
    parser.add_argument('--route', choices=('direct', 'readback'), required=True)
    parser.add_argument('--case', required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--compare', type=Path, required=True)
    args = parser.parse_args()
    root, site, output = args.root.resolve(), args.site.resolve(), args.out.resolve()
    output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(root))
    import layauto_v2
    from layauto_v2.domain.codec import FrozenMap, canonical_bytes
    from layauto_v2.domain.publication import InputsReady, RunRequest
    from layauto_v2.importers import read_inputs
    from layauto_v2.normalization import (
        normalize, from_inputs_ready, from_parse_result, build_geometry,
        geometry_from_normalization_input, build_effective_geometry,
        build_local_connectivity, build_channel_identity, build_net_annotation,
        build_terminal_relations,
    )
    from layauto_v2.pipeline import prepare_inputs
    from layauto_v2.repository import PublicationRepository
    assert Path(layauto_v2.__file__).resolve() == root / 'layauto_v2/__init__.py'
    source_before = inventory(root, ('layauto_v2', 'tests', 'pyproject.toml'))
    input_before = inventory(site.parent, ('.',))
    phases: list[dict[str, object]] = []

    def structural(item):
        if type(item) is FrozenMap:
            return {'frozen_map': tuple((key, structural(value)) for key, value in sorted(item.items()))}
        if is_dataclass(item):
            return {'type': type(item).__module__ + '.' + type(item).__qualname__,
                    'fields': tuple((member.name, structural(getattr(item, member.name)))
                                    for member in fields(item))}
        if type(item) is tuple:
            return tuple(structural(child) for child in item)
        if item is None or type(item) in (str, bool, int, bytes, Fraction):
            return item
        raise TypeError('Foreign DTO field: ' + str(type(item)))

    baseline = json.loads((args.compare / 'report.json').read_text())
    assert baseline['status'] == 'passed' and baseline['route'] == args.route
    assert baseline['site'] == str(site) and baseline['case'] == args.case
    assert baseline['input_files'] == input_before, 'Baseline input bytes changed'
    baseline_rows = {row['stage']: row for row in baseline['phases']}

    def retain(name: str, data: bytes) -> dict[str, object]:
        stage, kind = name.split('.')
        path = args.compare / (name + '.gz')
        previous = gzip.decompress(path.read_bytes())
        identity = baseline_rows[stage][kind]
        assert sha(previous) == identity['sha256'] and len(previous) == identity['bytes'], 'Baseline snapshot identity mismatch'
        assert previous == data, name + ' changed across source revisions'
        return {'bytes': len(data), 'sha256': sha(data), 'exact_comparison': True,
                'adopted_equal_snapshot': str(path.resolve())}

    def inspect(name, value, codec_name=None):
        started = time.perf_counter()
        row = {'stage': name, 'status': getattr(value, 'status', None),
               'issues': [issue.code for issue in getattr(value, 'issues', ())],
               'dto': retain(name + '.dto', canonical_bytes(structural(value)))}
        if codec_name is not None:
            codec = importlib.import_module('layauto_v2.normalization.' + codec_name)
            wire = codec.encode_record(value)
            row['wire'] = retain(name + '.wire', wire)
            # Baseline already decoded this exact byte sequence to its complete
            # DTO. Candidate complete DTO and public encode are compared above;
            # final codec regressions cover decoder behavior on the frozen source.
            assert baseline_rows[name]['roundtrip_complete_dto_equal'] is True
            row['baseline_roundtrip_adopted_by_exact_bytes'] = True
            del wire
        row['inspection_seconds'] = time.perf_counter() - started
        row['hwm_kib'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        phases.append(row)
        print(json.dumps(row), flush=True)

    repository = ready = checkpoint = attempt = None
    if args.route == 'readback':
        repository = PublicationRepository()
        ready = prepare_inputs(repository, RunRequest(
            proposed_run_id='w016-old-parity', lineage_id='w016-old-parity',
            idempotency_key='w016-old-parity', site_path=str(site)))
        assert isinstance(ready, InputsReady), ready
        checkpoint = repository.load_checkpoint(ready.run_id)
        attempt = repository.load_attempt(ready.run_id)
        parsed_audit = repository.read(ready.parse_ref)
        parsed = parsed_audit.result
        normalized_input = from_inputs_ready(ready, checkpoint, parsed_audit,
            repository.read(ready.tool_ref), tuple(repository.read(ref) for ref in ready.evidence_refs))
    else:
        parsed = read_inputs(site)
        inspect('w005', parsed)
        if parsed.status != 'success':
            raise AssertionError('Use a reader-accepted body rule case for W007-W014 parity')
        normalized_input = from_parse_result(parsed)
    semantic = normalize(normalized_input)
    inspect('w007', semantic, 'codec')
    del semantic
    geometry = build_geometry(geometry_from_normalization_input(normalized_input))
    inspect('w008', geometry, 'geometry_codec')
    effective = build_effective_geometry(geometry)
    inspect('w009', effective, 'effective_codec')
    del geometry
    local = build_local_connectivity(effective)
    inspect('w010', local, 'local_connectivity_codec')
    del effective
    for stage, builder, codec in (
            ('w011', build_channel_identity, 'channel_identity_codec'),
            ('w013', build_net_annotation, 'net_annotation_codec'),
            ('w014', build_terminal_relations, 'terminal_relations_codec')):
        result = builder(local)
        inspect(stage, result, codec)
        del result
        gc.collect()
    if repository is not None:
        assert repository.load_checkpoint(ready.run_id) == checkpoint
        assert repository.load_attempt(ready.run_id) == attempt and attempt.phase == 'unsealed'
        assert repository.read_terminal(ready.run_id) is None
    assert source_before == inventory(root, ('layauto_v2', 'tests', 'pyproject.toml')), 'Source changed during probe'
    assert input_before == inventory(site.parent, ('.',)), 'Inputs changed during probe'
    report = {'case': args.case, 'route': args.route, 'site': str(site), 'root': str(root),
              'python': sys.version, 'executable': sys.executable, 'platform': platform.platform(),
              'dependencies': {item.metadata['Name']: item.version for item in importlib.metadata.distributions()},
              'source_files': source_before, 'input_files': input_before,
              'probe_sha256': sha(Path(__file__).read_bytes()), 'argv': sys.argv,
              'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
              'phases': phases, 'compare': None if args.compare is None else str(args.compare.resolve()),
              'readback_unchanged_unsealed': repository is not None,
              'status': 'passed', 'baseline_report_sha256': sha((args.compare / 'report.json').read_bytes()),
              'limitations': ['Synthetic same-URI compatibility only; no production or EDA assurance.', 'Candidate complete DTO/public encode compared exactly; baseline decode adopted, candidate decoder covered by final codec regressions.']}
    with (output / 'report.json').open('x') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')


if __name__ == '__main__':
    main()
