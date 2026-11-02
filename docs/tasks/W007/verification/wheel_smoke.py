"""Standalone installed-wheel smoke; no test/helper imports or expected answers."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path
from fractions import Fraction
from unittest.mock import patch

import layauto_v2
from layauto_v2.domain.publication import InputsReady, RunRequest
from layauto_v2.domain.circuit import semantic_digest
from layauto_v2.domain.normalization_codec import encode_record, decode_record, record_digest
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import from_inputs_ready, from_parse_result, normalize
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rebind(root: Path) -> None:
    path = root / 'query/header.json'
    header = json.loads(path.read_text())
    for entry in [header['layout'], header['source_netlist'], header['target'],
                  *header['raw'], *header['closure']['entries']]:
        entry['sha256'] = sha(root / entry['uri'])
    header['closure']['entries'].sort(key=lambda entry: entry['uri'])
    payload = json.dumps(header['closure']['entries'], sort_keys=True,
                         separators=(',', ':'), ensure_ascii=False).encode()
    header['closure']['sha256'] = hashlib.sha256(payload).hexdigest()
    path.write_text(json.dumps(header, indent=2) + '\n')


def checked(root: Path):
    parsed = read_inputs(root / 'site_config.yaml')
    assert parsed.status == 'success', parsed.issues
    with patch('builtins.open', side_effect=AssertionError('normalization attempted IO')), \
            patch.object(Path, 'read_bytes', side_effect=AssertionError('normalization attempted IO')), \
            patch.object(Path, 'resolve', side_effect=AssertionError('normalization resolved a path')):
        return normalize(from_parse_result(parsed))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('fixture', type=Path)
    args = parser.parse_args()
    installed = Path(layauto_v2.__file__).resolve()
    assert installed.is_relative_to(Path(sys.prefix).resolve()), installed
    outcomes = {}
    with tempfile.TemporaryDirectory(prefix='w007-wheel-smoke-') as temp:
        roots = []
        for name in ('normal', 'cardinality', 'target_length'):
            root = Path(temp) / name
            shutil.copytree(args.fixture, root, ignore=shutil.ignore_patterns(
                'expected', 'oracle.json', 'spec.json', 'independent-design-answer.json',
                'failures', 'special', 'normalized'))
            roots.append(root)
        normal, cardinality, target = roots
        accepted = checked(normal)
        assert accepted.status == 'success', accepted.issues
        assert accepted.value is not None
        assert accepted.value.differences == ()
        assert semantic_digest(accepted.value.source) == semantic_digest(accepted.value.target)
        assert len(accepted.value.device_seeds) == 2 and len(accepted.value.net_seeds) == 8
        assert decode_record(encode_record(accepted)) == accepted
        outcomes['normal'] = {'status': accepted.status, 'record_digest': record_digest(accepted)}
        raw = cardinality / 'query/raw/iXref.temp'
        raw.write_text(raw.read_text().replace('MP0', 'MN0'))
        rebind(cardinality)
        rejected = checked(cardinality)
        assert rejected.status == 'error'
        assert rejected.issues[0].code == 'UnsupportedDeviceCardinality'
        outcomes['cardinality'] = rejected.issues[0].code
        target_file = target / 'target.cdl'
        target_file.write_text(target_file.read_text().replace('L=4n', 'L=5n', 1))
        rebind(target)
        changed = checked(target)
        assert changed.status == 'success', changed.issues
        assert changed.value is not None and len(changed.value.differences) == 1
        delta = changed.value.differences[0]
        assert delta.op_type == 'parameter_change' and delta.axis == 'channel_length'
        assert delta.operand_ref.name == 'MN0'
        assert delta.semantic_before.exact == Fraction(4, 10**9)
        assert delta.semantic_after.exact == Fraction(5, 10**9)
        assert delta.required_capability and delta.obligations
        assert decode_record(encode_record(changed)) == changed
        outcomes['target_length'] = {'status': changed.status, 'axis': delta.axis,
                                    'delta_id': delta.delta_id.value}
        repository = PublicationRepository()
        ready = prepare_inputs(repository, RunRequest('wheel-run', 'wheel-lineage',
                               'create', str(normal / 'site_config.yaml')))
        assert isinstance(ready, InputsReady), ready
        before = repository.snapshot()
        adapted = from_inputs_ready(ready, repository.read(ready.checkpoint_ref),
            repository.read(ready.parse_ref), repository.read(ready.tool_ref),
            tuple(repository.read(ref) for ref in ready.evidence_refs))
        result = normalize(adapted)
        assert result.status == 'success', result.issues
        assert result.value is not None
        assert semantic_digest(result.value.source) == semantic_digest(accepted.value.source)
        assert decode_record(encode_record(adapted)) == adapted
        assert repository.snapshot() == before
        assert repository.read_terminal(ready.run_id) is None
        outcomes['w006_readback'] = result.status
    print(json.dumps({'python': sys.version, 'installed': str(installed),
                      'cwd': str(Path.cwd()), 'outcomes': outcomes}, indent=2))


if __name__ == '__main__':
    main()
