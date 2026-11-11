"""Read-only A1 evidence integrity, scope, source and completed engineering audit."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

ROOT = Path('/workspace/Layauto')
OUT = ROOT/'docs/tasks/W012/A1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    checks = []
    def check(condition, label):
        assert condition, label
        checks.append(label)
    perf = json.loads((OUT/'performance/receipt.json').read_text())
    check(perf['status']=='passed' and len(perf['commands'])==18, '18 completed fresh baseline samples')
    finish = None
    for row in perf['commands']:
        check(row['exit_code']==0, 'sample exit0 '+str(row['argv']))
        check(row['actual_complete_wire_byte_comparison']['equal'], 'actual full byte comparison '+str(row['case']))
        start = datetime.fromisoformat(row['started_at_utc'])
        check(finish is None or finish<=start, 'serial sample chronology '+str(start))
        finish = datetime.fromisoformat(row['finished_at_utc'])
        prefix = Path(row['argv'][row['argv'].index('--output')+1]).with_suffix('')
        for stream in ('stdout','stderr'):
            check(sha(prefix.with_suffix('.'+stream+'.txt'))==row[stream+'_sha256'], 'sample original '+str(prefix)+stream)
    for name,digest in perf['tools'].items():
        check(sha(OUT/name)==digest, 'frozen measurement tool '+name)
    source = perf['sources']['after']
    for name,digest in source.items():
        check(sha(ROOT/name)==digest, 'frozen product/test/config '+name)
    profile = json.loads((OUT/'profile-summary.json').read_text())
    check(profile['status']=='passed' and profile['constructor_authentication_call_counts_equal'], 'profile constructor/authentication calls equal')
    check(len(profile['matcher_windows']['before']['peak_refreshes'])==5, 'before actual matcher peak refreshes')
    check(len(profile['matcher_windows']['after']['peak_refreshes'])==0, 'after actual matcher peak refreshes eliminated')
    eng = OUT/'verification-r2'
    receipt = json.loads((eng/'receipt.json').read_text())
    check(receipt['status']=='passed', 'new complete engineering attempt passed')
    check(receipt['actual_test_counts']=={'310':1656,'312':1656}, 'dual full1656')
    check(receipt['retained_baseline_test_count']==1605, 'all original1605 retained')
    for row in receipt['commands']:
        check(row['exit_code']==0, 'engineering command '+row['stdout'])
        for stream in ('stdout','stderr'):
            check(sha(eng/row[stream])==row[stream+'_sha256'], 'engineering original '+row[stream])
    manifest = json.loads((eng/'source-manifest.json').read_text())
    check(manifest['files']==source, 'engineering source equals all measured after source')
    with tarfile.open(eng/'source-snapshot.tar.gz') as archive:
        for name,digest in manifest['files'].items():
            check(hashlib.sha256(archive.extractfile(name).read()).hexdigest()==digest, 'frozen source snapshot '+name)
    for tag in ('310','312'):
        smoke = json.loads((eng/('installed-smoke-'+tag+'.stdout.txt')).read_text())
        check(smoke['attempt_unchanged'] and smoke['checkpoint_unchanged'] and smoke['terminal_absent'], 'installed readback boundaries '+tag)
        check('/site-packages/layauto_v2/' in smoke['package'], 'installed package source outside checkout '+tag)
    interrupted = json.loads((OUT/'interruption-01.json').read_text())
    for name,digest in interrupted['files'].items():
        check(sha(OUT/'verification-attempt-01'/name)==digest, 'original interrupted attempt retained '+name)
    before = OUT/'before-package'
    for name,digest in json.loads((before/'evidence-manifest.json').read_text()).items():
        check(sha(before/name)==digest, 'before rebuilt package evidence '+name)
    packages = json.loads((OUT/'package-comparison.json').read_text())
    check(packages['status']=='passed', 'actual before/after package comparison passed')
    for side, artifacts in packages['artifacts'].items():
        for kind, row in artifacts.items():
            check(sha(OUT/row['path'])==row['sha256'], 'accessible actual package '+side+' '+kind)
            check(row['actual_runtime_members']==100, 'complete package runtime members '+side+' '+kind)
    for kind, names in packages['runtime_payload_differences'].items():
        check(names==['domain/codec.py'], 'only authorized package payload change '+kind)
    paths = subprocess.check_output(['git','diff','--name-only','7f7c1304bdafd941791421cef64864fb1616303c'],cwd=ROOT,text=True).splitlines()
    paths += subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=ROOT,text=True).splitlines()
    check(all(name.startswith('docs/tasks/W012/A1/') or name in
              ('layauto_v2/domain/codec.py','tests/contracts/test_w012_hex_validation.py',
               'docs/tasks/W012-capture-wire-performance.md') for name in paths), 'authorized A1 scope only')
    (OUT/'delivery-validation.json').write_text(json.dumps({'status':'passed','count':len(checks),'checks':checks},indent=2)+'\n')
    print(str(len(checks))+' completed evidence/source/scope checks passed; no additional product tests run')


if __name__ == '__main__':
    main()
