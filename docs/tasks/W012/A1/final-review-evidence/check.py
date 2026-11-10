"""Bind the independent review to the final committed snapshot; no product run."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path('/workspace/w012-a1-review')
OUT = Path(__file__).resolve().parent
BASE = '7f7c1304bdafd941791421cef64864fb1616303c'
HEAD = '44a91c472fdeba5bb4b8a6071c0580313336c379'
SOURCE = 'ca1f810c3c97376f71089d8b4054760ff198012f'
TASK = 'docs/tasks/W012-capture-wire-performance.md'
A1 = 'docs/tasks/W012/A1/'
checks = 0


def check(condition, label):
    global checks
    assert condition, label
    checks += 1


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def at(revision, name):
    return git('show', revision+':'+name)


def main():
    check(git('rev-parse', 'HEAD').decode().strip() == HEAD, 'actual reviewed HEAD')
    changed = git('diff', '--name-only', '-z', BASE, HEAD).decode().split('\0')[:-1]
    check(len(changed) == len(set(changed)) == 372, 'complete committed changed file list')
    outside = sorted(name for name in changed if not name.startswith(A1))
    check(outside == [TASK, 'layauto_v2/domain/codec.py',
                      'tests/contracts/test_w012_hex_validation.py'], 'authorized paths only')
    records = {}
    for name in changed:
        content = at(HEAD, name)
        check((ROOT/name).read_bytes() == content, 'actual final committed bytes '+name)
        records[name] = {'sha256':sha(content), 'bytes':len(content)}
    source = json.loads((ROOT/A1/'verification-r2/source-manifest.json').read_text())
    frozen = json.loads((ROOT/A1/'performance/frozen-identity.json').read_text())
    check(source['files'] == frozen['sources']['after'], 'measured and final engineering source identical')
    check(len(source['files']) == 263 and len(source['runtime_files']) == 100, '263 source and100 runtime')
    for name, digest in source['files'].items():
        check(sha(at(SOURCE, name)) == digest == sha(at(HEAD, name)), 'product/test/config freeze '+name)
    runtime_changed = sorted(name for name in frozen['sources']['before']
                             if name.startswith('layauto_v2/') and
                             frozen['sources']['before'][name] != frozen['sources']['after'][name])
    check(runtime_changed == ['layauto_v2/domain/codec.py'], 'single actual runtime member changed')
    old_task = at(BASE, TASK).decode()
    new_task = at(HEAD, TASK).decode()
    start = new_task.index('### A1 执行结果（待PM核验）\n')
    end = new_task.index('## Review 结论（reviewer）', start)
    check(new_task[:start]+new_task[end:] == old_task, 'only execution addition in pre-review task; PM and original review unchanged')
    blobs = [A1+'before-package/dist/layauto-0.2.0-py3-none-any.whl',
             A1+'before-package/dist/layauto-0.2.0.tar.gz',
             A1+'verification-r2/dist/layauto-0.2.0-py3-none-any.whl',
             A1+'verification-r2/dist/layauto-0.2.0.tar.gz']
    check(all(name in records and records[name]['bytes'] > 0 for name in blobs), 'all four actual package blobs committed')
    evidence = json.loads((ROOT/A1/'verification-r2/evidence-manifest.json').read_text())
    actual_names = {str(p.relative_to(ROOT/A1/'verification-r2'))
                    for p in (ROOT/A1/'verification-r2').rglob('*') if p.is_file()
                    and p.name != 'evidence-manifest.json'}
    check(set(evidence) == actual_names and len(evidence) == 78, 'final78 attachment manifest covers actual directory')
    diff = subprocess.run(['git','diff','--check',BASE,HEAD],cwd=ROOT,capture_output=True)
    expected_warnings = [
        A1+'before-package/build.stderr.txt:9: new blank line at EOF.',
        A1+'verification-r2/build.stderr.txt:19: new blank line at EOF.',
    ]
    check(diff.returncode == 2 and diff.stdout.decode().splitlines() == expected_warnings
          and not diff.stderr, 'only two retained raw-tool EOF warnings')
    manifest = {'review_base':BASE,'review_head':HEAD,'product_test_freeze':SOURCE,
                'files':records, 'scope':'committed reviewed input, excluding newly authored final review'}
    (OUT/'reviewed-manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
    result = {'status':'passed','checks':checks,'review_head':HEAD,'changed_files':len(changed),
              'source_files':263,'runtime_files':100,'final_attachment_count':78,
              'retained_raw_output_diff_check_warnings':expected_warnings,
              'reviewed_manifest_sha256':sha((OUT/'reviewed-manifest.json').read_bytes()),
              'recorded_at_utc':datetime.now(timezone.utc).isoformat(),
              'scope':'read committed/current bytes and Git scope; no product/test/performance rerun'}
    (OUT/'result.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(str(checks)+' independent final snapshot checks passed; no product run')


if __name__ == '__main__':
    main()
