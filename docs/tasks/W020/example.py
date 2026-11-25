"""Run the W020 synthetic full-input example; stdout is one provenance report."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import resource
import sys
from tempfile import TemporaryDirectory
from time import perf_counter

from layauto_v2.domain.circuit import Parameter
from layauto_v2.domain.publication import PipelineResult, PublicationUnavailable, RunRequest
from layauto_v2.pipeline import assemble_stage2, prepare_inputs
from layauto_v2.repository import PublicationRepository

from scope_report import scope_summary
from trace import conductor_trace


def parameter_value(parameter):
    return {'token': parameter.token, 'lexeme': parameter.lexeme, 'unit': parameter.unit,
            'exact': str(parameter.exact),
            'source': {k: v for k, v in asdict(parameter.source).items() if v is not None}}


def intent_summary(facts):
    semantic = facts.terminals.semantic_facts
    channels = facts.terminals.value.channel_observations
    measured = {r['fields']['device_id']['name']: r['fields']
                for r in channels['comparisons'] if r['fields']['axis'] == 'fins_per_finger'}
    target = next(c for c in semantic.target.cells if c.id == semantic.source.selected_cell)
    fins = {}
    for device in target.devices:
        desired = next(p for p in device.parameters if p.axis == 'fins_per_finger')
        row = measured[device.id.name]
        fins[device.id.name] = {'source': int(row['declared']['exact']), 'target': int(desired.exact),
                                'measured': int(row['measured'])}
    differences = []
    for delta in semantic.differences:
        # The W003 challenge changes one parameter. The assembly itself retains every typed delta.
        assert isinstance(delta.semantic_before, Parameter) and isinstance(delta.semantic_after, Parameter)
        differences.append({'delta': delta.delta_id.id, 'op': delta.op_type, 'device': delta.operand_ref.name,
                            'axis': delta.axis, 'before': parameter_value(delta.semantic_before),
                            'after': parameter_value(delta.semantic_after),
                            'required_capability': delta.required_capability, 'obligations': delta.obligations})
    return {'fins_per_finger': fins, 'stage4_differences': differences}


def run(parent, case):
    # These two established test helpers only stage actual input files and rebind their hashes.
    contracts = Path(__file__).resolve().parents[3] / 'tests/contracts'
    sys.path.insert(0, str(contracts))
    from w005_cases import apply_case, copy_input
    from w018_cases import select_projection

    root = copy_input(parent)
    if case == 'unsupported_target':
        apply_case(root, case)
    if case != 'original':
        select_projection(root)
    site = (root / 'site_config.yaml').resolve()
    repository = PublicationRepository()
    request = RunRequest('w020-' + case, 'w020-example', 'create', str(site))
    start = perf_counter()
    ready = prepare_inputs(repository, request)
    if isinstance(ready, PipelineResult):
        raise RuntimeError(f'{ready.run_id}: input rejected, closure {ready.closure_ref.id}')
    if isinstance(ready, PublicationUnavailable):
        raise RuntimeError(f'{ready.run_id}: {ready.operation}: {ready.message}')
    before = repository.load_attempt(ready.run_id)
    started_assembly = perf_counter()
    facts = assemble_stage2(repository, ready, fragment_budget=68)
    assembled = perf_counter()
    after = repository.load_attempt(ready.run_id)
    assert before == ready.attempt == after and repository.read_terminal(ready.run_id) is None

    def attempt(row):
        return {'phase': row.phase, 'revision': row.revision, 'ref': row.ref.id}

    report = {'case': case, 'run_id': ready.run_id, 'before': attempt(before), 'after': attempt(after),
              'checkpoint': ready.checkpoint_ref.id, 'parse': ready.parse_ref.id, 'tool': ready.tool_ref.id,
              'budget': 68, 'scope': scope_summary(facts), 'intent': intent_summary(facts)}
    if case != 'original':
        report['trace'] = conductor_trace(facts)
    payload = (json.dumps(report, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    elapsed = perf_counter() - start
    sys.stdout.buffer.write(payload)
    # ru_maxrss on Linux is KiB and on macOS is bytes. It includes process startup.
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(json.dumps({'case': case, 'python': sys.version.split()[0], 'platform': sys.platform,
                      'prepare_seconds': round(started_assembly - start, 3),
                      'assembly_seconds': round(assembled - started_assembly, 3),
                      'prepare_through_report_seconds': round(elapsed, 3),
                      'process_peak_rss_bytes': rss if sys.platform == 'darwin' else rss * 1024,
                      'report_bytes': len(payload)}), file=sys.stderr)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=('layered', 'original', 'unsupported_target'), default='layered')
    parser.add_argument('--keep-input', type=Path, metavar='DIRECTORY',
                        help='create DIRECTORY/input and retain the exact files for inspection')
    args = parser.parse_args()
    if args.keep_input is None:
        with TemporaryDirectory() as temp:
            run(Path(temp), args.case)
    else:
        args.keep_input.mkdir(parents=True, exist_ok=True)
        run(args.keep_input, args.case)
