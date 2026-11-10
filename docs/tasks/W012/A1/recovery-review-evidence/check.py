"""Recovery identity/parser guard review; never launches matrix or package work."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path('/workspace/Layauto')
A1 = ROOT/'docs/tasks/W012/A1'
OUT = Path(__file__).resolve().parent
checks = 0


def check(condition, label):
    global checks
    assert condition,label
    checks += 1


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    plan = json.loads((A1/'recovery-plan.json').read_text())
    interruption = json.loads((A1/'interruption-01.json').read_text())
    tool = A1/'verification-tools/prepare_final.py'
    check(sha(tool) == plan['runner_sha256'], 'new recovery runner identity')
    archive = A1/'verification-attempt-01'
    check(len(interruption['files']) == 26, 'complete interrupted26 archive manifest')
    for name,digest in interruption['files'].items():
        check(sha(archive/name) == digest, 'original interrupted archive '+name)
    check(sha(archive/'prepare_final.py') == '2a796148c68616894d1fafbfb5832765121e3bb7873a08f2e3cd10d0df641e53', 'old reviewed runner retained')
    check(not (archive/'receipt.json').exists(), 'interrupted matrix not represented as completed receipt')
    source = json.loads((archive/'source-manifest.json').read_text())
    for name,digest in source['files'].items():
        check(sha(ROOT/name) == digest, 'unchanged actual runtime/test/config '+name)
    check(plan['source_commit_unchanged'] == 'ca1f810c3c97376f71089d8b4054760ff198012f', 'same source freeze')
    check(plan['matrix_workers'] == 2 and plan['gate'] is None
          and plan['explicit_flag'] == '--allow-parallel-without-gate', 'explicit recovery scheduling metadata')
    check(plan['work'] == '/workspace/w012-a1-final-r2' and plan['engineering_attempt'] == 'verification-r2', 'new attempt namespace')
    results = []
    with tempfile.TemporaryDirectory(prefix='a1-review-recovery-') as temporary:
        temp = Path(temporary)
        work = temp/'existing-work'
        work.mkdir()
        for name,flags,expected_exit,expected_message in (
            ('default-two-worker-guard',['--matrix-workers','2'],2,'requires --resource-gate'),
            ('explicit-two-worker-optin',['--matrix-workers','2','--allow-parallel-without-gate'],1,'Work directory must be absent'),
            ('default-single-worker',[],1,'Work directory must be absent'),
        ):
            out = temp/name
            argv = [sys.executable,'-B',str(tool),'--root',str(ROOT),'--out',str(out),'--work',str(work),
                    '--smoke',str(A1/'verification-tools/installed_smoke.py'),
                    '--python310',sys.executable,'--python312',sys.executable,'--expected-tests','1656',
                    '--baseline-test-count','1605',*flags]
            started = datetime.now(timezone.utc).isoformat()
            process = subprocess.run(argv,cwd=ROOT,capture_output=True)
            (OUT/(name+'.stdout.txt')).write_bytes(process.stdout)
            (OUT/(name+'.stderr.txt')).write_bytes(process.stderr)
            row = {'argv':argv,'cwd':str(ROOT),'started_at_utc':started,
                   'finished_at_utc':datetime.now(timezone.utc).isoformat(),'exit_code':process.returncode,
                   'stdout_sha256':hashlib.sha256(process.stdout).hexdigest(),
                   'stderr_sha256':hashlib.sha256(process.stderr).hexdigest(),
                   'scope':'deliberate early parser/work-directory refusal; no matrix launched'}
            (OUT/(name+'.command.json')).write_text(json.dumps(row,indent=2)+'\n')
            check(process.returncode == expected_exit, 'guard expected exit '+name)
            check(expected_message in process.stderr.decode(), 'guard expected message '+name)
            check(not out.exists(), 'guard caused no output creation '+name)
            results.append(row)
    result = {'status':'passed','checks':checks,'new_runner_sha256':sha(tool),'source_count':len(source['files']),
              'plan_sha256':sha(A1/'recovery-plan.json'),'interruption_sha256':sha(A1/'interruption-01.json'),
              'commands':results,'scope':'recovery plan/archive/source and parser guards; not final matrix correctness/performance'}
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(str(checks)+' independent recovery identity/guard checks passed; no matrix launched')


if __name__ == '__main__':
    main()
