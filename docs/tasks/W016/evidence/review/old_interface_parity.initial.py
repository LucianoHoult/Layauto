"""Independent W016 compatibility probe; run serially, one route per process.

Prepare one fixed actual-input directory once. Invoke this same script with
--root BASE then --root CANDIDATE and identical --site/--route; candidate also
uses --compare BASE_OUTPUT. Outputs are exclusive-create and are never updated.
Complete DTO structural bytes and public wire are compared byte-for-byte, with
length/SHA retained in report.json. No expected/spec answer supplies an input.
Large compressed snapshots belong in a local evidence directory; report.json
is the compact handoff. Do not run concurrently with resource/check matrices.
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
    parser.add_argument('--compare', type=Path)
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
        if is_dataclass(item):
            return {'type': type(item).__module__ + '.' + type(item).__qualname__,
                    'fields': tuple((member.name, structural(getattr(item, member.name)))
                                    for member in fields(item))}
        if type(item) is FrozenMap:
            return {'frozen_map': tuple((key, structural(value)) for key, value in item.items())}
        if type(item) is tuple:
            return tuple(structural(child) for child in item)
        if item is None or type(item) in (str, bool, int, bytes, Fraction):
            return item
        raise TypeError('Foreign DTO field: ' + str(type(item)))

    def retain(name: str, data: bytes) -> dict[str, object]:
        path = output / (name + '.gz')
        with path.open('xb') as stream:
            stream.write(gzip.compress(data, mtime=0))
        equal = None
        if args.compare is not None:
            previous = gzip.decompress((args.compare / path.name).read_bytes())
            equal = previous == data
            assert equal, name + ' changed across source revisions'
        return {'bytes': len(data), 'sha256': sha(data), 'exact_comparison': equal,
                'snapshot': path.name}

    def inspect(name, value, codec_name=None):
        started = time.perf_counter()
        row = {'stage': name, 'status': getattr(value, 'status', None),
               'issues': [issue.code for issue in getattr(value, 'issues', ())],
               'dto': retain(name + '.dto', canonical_bytes(structural(value)))}
        if codec_name is not None:
            codec = importlib.import_module('layauto_v2.normalization.' + codec_name)
            wire = codec.encode_record(value)
            row['wire'] = retain(name + '.wire', wire)
            # Each implementation must also reconstruct its own complete value;
            # equal hashes without successful closed decoding are insufficient.
            decoded = codec.decode_record(wire)
            assert decoded == value, name + ' public roundtrip mismatch'
            assert canonical_bytes(structural(decoded)) == canonical_bytes(structural(value))
            row['roundtrip_complete_dto_equal'] = True
            del decoded, wire
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
              'status': 'passed', 'limitations': ['Synthetic same-URI compatibility only; no production or EDA assurance.']}
    with (output / 'report.json').open('x') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')


if __name__ == '__main__':
    main()
