"""Isolated interruption-output repro; substitutes lightweight process, no runtime."""
from importlib.machinery import SourceFileLoader
import importlib.util
import hashlib
import json
from pathlib import Path
import sys
import tempfile

OUT = Path(__file__).resolve().parent
source = OUT/'run_performance-before-R01.py.txt'
loader = SourceFileLoader('a1_early_runner', str(source))
spec = importlib.util.spec_from_loader(loader.name, loader)
module = importlib.util.module_from_spec(spec)
loader.exec_module(module)

with tempfile.TemporaryDirectory(prefix='a1-review-runner-') as temp:
    root = Path(temp)
    for name in ('probe.py','run_performance.py'):
        (root/name).write_text('# independent lightweight substitute\n')
    digest = hashlib.sha256((root/'probe.py').read_bytes()).hexdigest()
    (root/'selfcheck.json').write_text(json.dumps({'tool_sha256':digest}))
    directory = root/'performance'
    directory.mkdir()
    old_stdout = b'prior interrupted attempt stdout; must not be overwritten\n'
    old_identity = b'{"original_interrupted_attempt":"must preserve"}\n'
    (directory/'before-normal-direct-r1.stdout.txt').write_bytes(old_stdout)
    (directory/'frozen-identity.json').write_bytes(old_identity)
    before, after = root/'before',root/'after'
    module.ROOT = root
    module.OUT = root
    module.PROBE = root/'probe.py'
    module.RUNTIMES = {'before':before,'after':after}
    module.WORK = root/'work'
    module.identity = lambda path: ({'layauto_v2/domain/codec.py':'old'} if path == before else
                                   {'layauto_v2/domain/codec.py':'new','tests/contracts/test_w012_hex_validation.py':'test'})
    class Process:
        returncode = 1
        def __init__(self, argv, **kwargs):
            kwargs['stdout'].write(b'new failed attempt stdout\n')
        def poll(self):
            return self.returncode
    original = module.subprocess.Popen
    argv = sys.argv
    try:
        module.subprocess.Popen = Process
        sys.argv = ['run_performance.py','--stage','baseline']
        try:
            module.main()
        except AssertionError as caught:
            failure = str(caught)
        else:
            raise AssertionError('substituted failed process did not stop runner')
    finally:
        module.subprocess.Popen = original
        sys.argv = argv
    result = {'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
              'interrupted_stdout_overwritten':(directory/'before-normal-direct-r1.stdout.txt').read_bytes()!=old_stdout,
              'frozen_identity_overwritten':(directory/'frozen-identity.json').read_bytes()!=old_identity,
              'runner_stop':failure,
              'scope':'isolated temp paths and substituted failing process; no product or performance run'}
    assert result['interrupted_stdout_overwritten'] and result['frozen_identity_overwritten']
    (OUT/'runner-R01-reproduction.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
