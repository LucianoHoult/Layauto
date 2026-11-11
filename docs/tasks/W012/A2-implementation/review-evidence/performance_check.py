"""Independent final finite-screen audit: full wire bytes, identities and raw arithmetic."""
import ast
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path

ROOT = Path('/workspace/Layauto')
HERE = Path(__file__).resolve().parent
PREFIX = ROOT / 'docs/tasks/W012/A2-implementation'
CASES = ('normal-direct', 'normal-readback', 'extraction-mismatch')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_text())


def function(source, name):
    tree = ast.parse(source)
    return ast.dump(next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name),
                    include_attributes=False)


def close(a, b):
    assert math.isclose(a, b, rel_tol=1e-11, abs_tol=1e-9), (a, b)


def main():
    output = HERE / 'performance-check.json'
    assert not output.exists()
    frozen_path = PREFIX / 'freeze-screen-attempt02/freeze.json'
    frozen = read(frozen_path)
    summary_path = PREFIX / 'screening-summary-attempt02.json'
    summary = read(summary_path)
    assert summary['reps'] == [1] and summary['samples_per_side_per_path'] == 1
    assert len(summary['all_observed_failed_commands']) == 1
    current_tools = {p.name: sha(p.read_bytes()) for p in (PREFIX / 'measurement').glob('*.py')}
    assert current_tools == frozen['tools']
    for side, files in frozen['sources'].items():
        root = Path(frozen['roots'][side])
        assert all(sha((root / name).read_bytes()) == expected for name, expected in files.items())
    for item in frozen['inputs']:
        assert sha(Path(item['origin']).read_bytes()) == sha(Path(item['target']).read_bytes()) == item['sha256']
        assert sha(Path(item['normal']).read_bytes()) == item['normal_sha256']
    probe = (PREFIX / 'measurement/probe.py').read_text()
    original_probe = (HERE / 'probe-before-I-R02.py.txt').read_text()
    assert function(probe, 'run') == function(original_probe, 'run'), 'product timers/roots changed in tool fix'
    assert function(probe, 'check_result') == function(original_probe, 'check_result')

    receipt = read(PREFIX / 'performance-attempt02/receipt-1.json')
    assert receipt['status'] == 'passed' and receipt['reps'] == [1]
    assert receipt['fresh_processes'] and receipt['serial'] and receipt['full_wire_byte_comparison']
    assert receipt['wire_reduction'] == 0 and receipt['freeze_sha256'] == sha(frozen_path.read_bytes())
    planned = [(case, side) for case in CASES for side in ('before', 'after')]
    assert [(r['case'], r['side']) for r in receipt['commands']] == planned
    rows, last_end = {}, None
    for (case, side), command in zip(planned, receipt['commands']):
        name = f'{side}-{case}-r1'
        prefix = PREFIX / 'performance-attempt02' / name
        raw_command = read(prefix.with_suffix('.command.json'))
        assert command == {**raw_command, 'actual_complete_wire_byte_comparison': read(prefix.with_suffix('.comparison.json'))}
        assert raw_command['exit_code'] == 0 and raw_command['tools'] == frozen['tools']
        assert raw_command['freeze_sha256'] == sha(frozen_path.read_bytes())
        begin, end = (datetime.fromisoformat(raw_command[k]) for k in ('started_at_utc', 'finished_at_utc'))
        assert end > begin and (last_end is None or begin >= last_end)
        last_end = end
        assert raw_command['argv'][0] == frozen['environment']['executable']
        assert raw_command['cwd'] == '/workspace/Layauto'
        for kind in ('stdout', 'stderr'):
            data = prefix.with_suffix('.' + kind + '.txt').read_bytes()
            assert sha(data) == raw_command[kind + '_sha256']
            if kind == 'stderr':
                assert data == b''
        sample = read(prefix.with_suffix('.json'))
        assert sample['case'] == case and sample['mode'] == 'baseline'
        assert sample['source_identity'] == frozen['sources'][side]
        assert sample['environment'] == frozen['environment']
        assert sample['input_identity'] == frozen['inputs']
        assert sample['tool_sha256'] == frozen['tools']['probe.py']
        assert sample['runtime_root'] == frozen['roots'][side]
        assert sample['package'] == str(Path(frozen['roots'][side]) / 'layauto_v2/__init__.py')
        expected_input = ('/workspace/w012-inputs/extraction-mismatch/site_config.yaml' if case == 'extraction-mismatch'
                          else '/workspace/Layauto/tests/fixtures/w003_m1/site_config.yaml')
        assert sample['input_site'] == expected_input
        assert sample['gc_enabled'] is True and sample['gc_threshold'] == [700, 10, 10]
        assert sample['public_roundtrip_equal'] is True
        assert sample['readback_unsealed_checkpoint_unchanged_no_terminal'] is (case == 'normal-readback')
        info = sample['result']
        assert info['counts'] == {'MN0': 4 if case == 'extraction-mismatch' else 5, 'MP0': 7}
        assert info['difference_count'] == (1 if case == 'extraction-mismatch' else 0)
        assert info['comparison_status'] == ('mismatch' if case == 'extraction-mismatch' else 'equal')
        assert info['complete_evaluations'] == 36 and info['T05_status'] == 'pass'
        assert (info['local_nodes'], info['local_edges'], info['local_components'], info['T05_audits']) == (14, 8, 6, 16)
        assert sample['sources_and_target'] == {'capture_count': 31, 'raw_bytes_sha_verified': True,
            'completed_sources_resolve': True, 'independent_target': True,
            'query_seed_provenance': True, 'body_shapes': 6}
        assert len(sample['capture_sources']) == 31 and len(sample['stored_refs']) > 0
        expected_stages = (['W006_prepare_inputs', 'W006_caller_reads'] if case == 'normal-readback'
                           else ['W005_read_inputs']) + ['W008_adapter_and_build', 'W009_build', 'W010_build',
                            'W011_build', 'W011_result_encode', 'W011_result_decode']
        stdout = prefix.with_suffix('.stdout.txt').read_text()
        assert [line.removeprefix('START ') for line in stdout.splitlines() if line.startswith('START ')] == expected_stages
        assert set(sample['wall_seconds']) == set(expected_stages)
        rows[(case, side)] = sample

    verified = {}
    for case in CASES:
        before, after = (rows[(case, side)] for side in ('before', 'after'))
        for key in ('capture_sources', 'result', 'sources_and_target', 'stored_refs', 'input_site',
                    'wire_bytes', 'wire_sha256', 'gc_enabled', 'gc_threshold'):
            assert before[key] == after[key]
        length, digests = 0, [hashlib.sha256(), hashlib.sha256()]
        with Path(before['wire_artifact']).open('rb') as left, Path(after['wire_artifact']).open('rb') as right:
            while True:
                a, b = left.read(1024 * 1024), right.read(1024 * 1024)
                assert a == b, 'actual complete before/after wire differs'
                length += len(a)
                digests[0].update(a); digests[1].update(b)
                if not a:
                    break
        assert length == before['wire_bytes'] and all(d.hexdigest() == before['wire_sha256'] for d in digests)
        assert length == {'normal-direct': 54050313, 'normal-readback': 136471701, 'extraction-mismatch': 54045042}[case]
        values = {}
        for side, sample in (('before', before), ('after', after)):
            stages = sample['wall_seconds']
            values[side] = {'W011_build_seconds': stages['W011_build'],
                'all_build_seconds': sum(v for k, v in stages.items() if k not in ('W011_result_encode', 'W011_result_decode')),
                'encode_seconds': stages['W011_result_encode'], 'decode_seconds': stages['W011_result_decode'],
                'total_seconds': sum(stages.values()), 'peak_rss_kib': sample['process_peak_rss_kib']}
        calculated = {}
        for key in values['before']:
            b, a = values['before'][key], values['after'][key]
            change = {'before': b, 'after': a, 'after_minus_before': a-b, 'improvement_percent': (1-a/b)*100}
            for field, value in change.items():
                close(value, summary['paths'][case]['medians_and_changes'][key][field])
            calculated[key] = change
        assert summary['paths'][case]['wire_reduction_percent'] == 0
        verified[case] = {'full_actual_wire_bytes_equal': length, 'wire_sha256': before['wire_sha256'],
            'stored_typed_refs_equal': len(before['stored_refs']), 'stage_arithmetic': calculated,
            'upstream_W010_seconds': [before['wall_seconds']['W010_build'], after['wall_seconds']['W010_build']]}

    failure = summary['all_observed_failed_commands'][0]
    original_failure_path = PREFIX / 'performance/before-normal-direct-r1.command.json'
    assert failure['path'] == str(original_failure_path)
    assert failure == {'path': str(original_failure_path), **read(original_failure_path)}
    assert failure['exit_code'] == 1
    old_prefix = original_failure_path.with_suffix('').with_suffix('')
    assert not (PREFIX / 'performance/before-normal-direct-r1.json').exists()
    assert not Path('/workspace/work/w012-a2/wires/before-normal-direct-r1.bin').exists()
    assert 'target.cdl' in (PREFIX / 'performance/before-normal-direct-r1.stderr.txt').read_text()
    for outer in ('performance-r1', 'performance-attempt02-r1'):
        command = read(PREFIX / f'development/{outer}.command.json')
        assert command['exit_code'] == (1 if outer == 'performance-r1' else 0)
        for kind in ('stdout', 'stderr'):
            assert sha((PREFIX / f'development/{outer}.{kind}.txt').read_bytes()) == command[kind + '_sha256']
    result = {'status': 'passed', 'freeze_sha256': sha(frozen_path.read_bytes()),
        'summary_sha256': sha(summary_path.read_bytes()), 'fresh_serial_commands': 6,
        'samples_per_side_per_path': 1, 'all_source_test_config_inputs_tools_unchanged': True,
        'original_failed_command_retained_not_reused': True,
        'paths': verified, 'scope': 'Finite r1 screening only; no three-repetition performance or final engineering acceptance.'}
    with output.open('x') as stream:
        stream.write(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print('PASS six raw fresh serial samples, all full wire bytes/hash/refs and identities, exact arithmetic, retained original failure')


if __name__ == '__main__':
    main()
