"""Light checks for A2 measurement identities, original inputs, bytecmp and guards."""
from __future__ import annotations

import argparse
import ast
import copy
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

from common import BASE, FIXED_ROOT, OVERLAYS, baseline, dump_new, environment, inputs, same_bytes, sha
from prepare import tools


def main(args):
    assert not args.output.exists(), 'never overwrite prior selfcheck'
    before = baseline(args.before_root.resolve())
    fixed_inputs = inputs(rebuild=True)
    assert len(fixed_inputs) == 35
    assert {str(Path(row['target']).relative_to('/workspace/w012-inputs/extraction-mismatch'))
            for row in fixed_inputs if row['overlay']} == OVERLAYS
    here = Path(__file__).resolve().parent
    for path in here.glob('*.py'):
        compile(path.read_text(), str(path), 'exec')
    old = ast.parse((FIXED_ROOT / 'docs/tasks/W012/A1/probe.py').read_text())
    new = ast.parse((here / 'probe.py').read_text())
    def function(tree, name):
        return next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)
    assert ast.dump(function(old, 'check_result'), include_attributes=False) == ast.dump(function(new, 'check_result'), include_attributes=False)
    # The original stage calls, explicit retention variables, request and GC ordering remain visible.
    code = (here / 'probe.py').read_text()
    assert "gc.collect()" in code and code.count('gc.collect()') == 1
    for stage in ('W006_prepare_inputs', 'W006_caller_reads', 'W005_read_inputs', 'W008_adapter_and_build',
                  'W009_build', 'W010_build', 'W011_build', 'W011_result_encode', 'W011_result_decode'):
        assert stage in code
    for text in ("proposed_run_id='w012-investigation-run'", "lineage_id='w012-investigation-lineage'",
                 "idempotency_key='create-w012'", "repository = ready = attempt = checkpoint = parse = tool = audits = None"):
        assert text in code
    assert code.index('peak = resource.getrusage') < code.index('source_target = check_sources_target')
    with tempfile.TemporaryDirectory(prefix='w012-a2-tools-') as temp:
        directory = Path(temp)
        left, right = directory / 'a', directory / 'b'
        left.write_bytes(b'\x00\xffsame'); right.write_bytes(b'\x00\xffsame')
        assert same_bytes(left, right) == 6
        right.write_bytes(b'\x00\xffother')
        try:
            same_bytes(left, right)
        except AssertionError:
            pass
        else:
            raise AssertionError('wire byte mismatch was not rejected')
        receipt = directory / 'receipt.json'
        dump_new(receipt, {'first': True})
        original = receipt.read_bytes()
        try:
            dump_new(receipt, {'overwrite': True})
        except FileExistsError:
            pass
        else:
            raise AssertionError('evidence overwrite not rejected')
        assert receipt.read_bytes() == original
        from analyze import failed_commands
        failed_dir, success_dir = directory / 'failed', directory / 'success'
        failed_dir.mkdir(); success_dir.mkdir()
        dump_new(failed_dir / 'original.command.json', {'exit_code': 1, 'case': 'original-failure'})
        dump_new(success_dir / 'retry.command.json', {'exit_code': 0, 'case': 'retry-success'})
        failures = failed_commands((success_dir, failed_dir, failed_dir))
        assert len(failures) == 1 and failures[0]['case'] == 'original-failure'
        assert failures[0]['path'] == str((failed_dir / 'original.command.json').resolve())
    # Exercise the real immutable A1 reader/normalizer, including legal relative URIs.
    sys.path.insert(0, str(args.before_root.resolve()))
    from layauto_v2.importers import read_inputs
    from layauto_v2.normalization import from_parse_result, normalize
    from probe import check_preservation
    import layauto_v2
    assert Path(layauto_v2.__file__).resolve().parent == args.before_root.resolve() / 'layauto_v2'
    preservation_witnesses = []
    for site in (FIXED_ROOT / 'tests/fixtures/w003_m1/site_config.yaml',
                 Path('/workspace/w012-inputs/extraction-mismatch/site_config.yaml')):
        parsed = read_inputs(site)
        assert parsed.status == 'success'
        semantic = normalize(from_parse_result(parsed))
        assert semantic.status == 'success' and semantic.value is not None
        facts = semantic.value
        check_preservation(facts, parsed)
        assert facts.source.preservation.sources[0].uri == 'source.cdl'
        assert facts.target.preservation.sources[0].uri == 'target.cdl'
        # Shallow forged clones preserve exact public classes; the original receipts remain untouched.
        swapped_source, swapped_target = copy.copy(facts.source), copy.copy(facts.target)
        object.__setattr__(swapped_source, 'preservation', facts.target.preservation)
        object.__setattr__(swapped_target, 'preservation', facts.source.preservation)
        try:
            check_preservation(SimpleNamespace(source=swapped_source, target=swapped_target), parsed)
        except AssertionError:
            pass
        else:
            raise AssertionError('swapped complete source/target evidence was accepted')
        check_preservation(facts, parsed)
        preservation_witnesses.append({'site': str(site), 'legitimate_relative_uris': ['source.cdl', 'target.cdl'],
                                       'full_original_evidence_equal': True, 'swapped_evidence_rejected': True})
    dump_new(args.output, {'status': 'passed', 'tools': tools(), 'environment': environment(),
                          'base': BASE, 'baseline_source_count': len(before), 'inputs': fixed_inputs,
                          'preservation_witnesses': preservation_witnesses,
                          'checks': ['actual local A1 baseline equals 263 original source/test/config entries',
                                     'all source hashes also checked against exact A1 Git tree',
                                     'original 35 inputs rebuilt byte for byte with exact five overlays',
                                     'all measurement scripts compile', 'A1 functional check_result AST unchanged',
                                     'original request/stages/roots/GC and post-peak diagnostics present',
                                     'complete bytecmp accepts equal and rejects unequal bytes',
                                     'exclusive evidence creation rejects overwrite and preserves original bytes',
                                     'actual normal/mismatch reader and normalizer retain complete original source/target receipts',
                                     'legal relative URIs accepted and swapped exact-type preservation rejected',
                                     'failure aggregation retains original failed command alongside successful retry and deduplicates paths'],
                          'tool_selfcheck_scope': 'No complete public build/decode, product performance or final engineering check run.'})
    print('PASS A2 measurement light selfcheck: exact local A1, 35/5 inputs, bytecmp, guards, A1 assertions')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    main(parser.parse_args())
