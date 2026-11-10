"""Independent guard regression on the current runner, with isolated temp paths."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

OUT = Path(__file__).resolve().parent
source = Path('/workspace/Layauto/docs/tasks/W012/A1/run_performance.py')
spec = importlib.util.spec_from_file_location('a1_fixed_runner', source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with tempfile.TemporaryDirectory(prefix='a1-review-fixed-runner-') as temp:
    root = Path(temp)
    for name in ('probe.py','run_performance.py'):
        (root/name).write_text('# independent lightweight substitute\n')
    digest = hashlib.sha256((root/'probe.py').read_bytes()).hexdigest()
    (root/'selfcheck.json').write_text(json.dumps({'tool_sha256':digest}))
    directory = root/'performance'
    directory.mkdir()
    originals = {'before-normal-direct-r1.stdout.txt':b'prior interrupted stdout\n',
                 'before-normal-direct-r1.stderr.txt':b'prior interrupted stderr\n',
                 'frozen-identity.json':b'{"original":"preserve"}\n'}
    for name,data in originals.items():
        (directory/name).write_bytes(data)
    before, after = root/'before',root/'after'
    module.ROOT = root
    module.OUT = root
    module.PROBE = root/'probe.py'
    module.RUNTIMES = {'before':before,'after':after}
    module.WORK = root/'work'
    module.identity = lambda path: ({'layauto_v2/domain/codec.py':'old'} if path == before else
                                   {'layauto_v2/domain/codec.py':'new','tests/contracts/test_w012_hex_validation.py':'test'})
    def forbidden(*args, **kwargs):
        raise AssertionError('must reject before launching any process')
    original = module.subprocess.Popen
    argv = sys.argv
    try:
        module.subprocess.Popen = forbidden
        sys.argv = ['run_performance.py','--stage','baseline']
        try:
            module.main()
        except (RuntimeError, AssertionError) as caught:
            failure = str(caught)
        else:
            raise AssertionError('existing stage was accepted')
    finally:
        module.subprocess.Popen = original
        sys.argv = argv
    assert failure != 'must reject before launching any process', failure
    assert {p.name:p.read_bytes() for p in directory.iterdir()} == originals
    result = {'status':'passed','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
              'refusal_message':failure,'all_prior_stage_files_preserved':True,
              'no_process_started':True,'scope':'isolated tempfile guard check; no performance run'}
    (OUT/'runner-R01-fix-verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
