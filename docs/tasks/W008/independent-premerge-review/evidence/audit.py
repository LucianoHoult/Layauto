#!/usr/bin/env python3
"""Independent W008 archive/receipt audit; only writes beside this new script."""
from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import pathlib
import platform
import re
import subprocess
import sys
import tarfile
import zipfile
from datetime import datetime, timezone

ROOT = pathlib.Path(sys.argv[1]).resolve()
OUT = pathlib.Path(__file__).resolve().parent
DELIVERY = 'aced62b0adda35fe7bcd8284a7354badc5b03649'
EXPECTED = '131f66dfadd77b5fb9073db999d6939051c3addf'
PREFIX = 'docs/tasks/W008/'
TASK = 'docs/tasks/W008-geometry-base-occupancy.md'
VP = PREFIX + 'verification/'
CHECKS = []

def h(data): return hashlib.sha256(data).hexdigest()
def read(path): return (ROOT / path).read_bytes()
def doc(path): return json.loads(read(path))
def git(*args): return subprocess.check_output(['git', '-C', str(ROOT), *args])
def record(name, ok, **details):
    CHECKS.append({'check': name, 'passed': bool(ok), **details})
def blocks(raw):
    values = []
    remaining = raw.decode()
    while remaining.strip():
        remaining = remaining.lstrip()
        value, consumed = json.JSONDecoder().raw_decode(remaining)
        values.append(value)
        remaining = remaining[consumed:]
    return values

head = git('rev-parse', 'HEAD').decode().strip()
record('review_head', head == EXPECTED, head=head,
       tree=git('rev-parse', 'HEAD^{tree}').decode().strip())
source = doc(VP + 'source-manifest.json')
source_digest = h(read(VP + 'source-manifest.json'))
tracked = git('ls-tree', '-r', '--name-only', DELIVERY).decode().splitlines()
expected_paths = {p for p in tracked if p.startswith(('layauto_v2/', 'tests/'))}
expected_paths.update({'README.md', 'pyproject.toml', PREFIX+'plan.md', VP+'wheel_smoke.py'})
current_errors = [p for p, digest in source.items() if h(read(p)) != digest]
delivery_errors = [p for p, digest in source.items() if h(git('show', DELIVERY+':'+p)) != digest]
record('source_manifest_coverage_and_bytes', len(source) == 235 and source_digest ==
       '30b4e446ff6b38f8c06be92916576928b87abdf62d10bc58f1b22ffa34a5f881' and
       set(source) == expected_paths and not current_errors and not delivery_errors,
       entries=len(source), sha256=source_digest, current_mismatches=current_errors,
       delivery_mismatches=delivery_errors, missing=sorted(expected_paths-set(source)),
       extra=sorted(set(source)-expected_paths))

evidence = doc(VP+'evidence-manifest.json')
evidence_errors = []
current_task = h(read(TASK))
for p, digest in evidence.items():
    raw = git('show', DELIVERY+':'+p) if p == TASK else read(p)
    if h(raw) != digest: evidence_errors.append(p)
all_delivery_errors = [p for p, digest in evidence.items() if h(git('show', DELIVERY+':'+p)) != digest]
record('historical_evidence_manifest', len(evidence) == 84 and not evidence_errors and not all_delivery_errors,
       entries=len(evidence), sha256=h(read(VP+'evidence-manifest.json')),
       historical_task_digest=evidence[TASK], historical_task_git=h(git('show', DELIVERY+':'+TASK)),
       current_task_digest=current_task, task_historical_difference_expected=current_task!=evidence[TASK],
       current_other_entries=83, mismatches=evidence_errors, delivery_mismatches=all_delivery_errors)

old = doc(VP+'pre-cr01/source-manifest.json')
changed = sorted(p for p in source if source[p] != old[p])
record('pre_fix_and_final_separated', len(old)==235 and read(VP+'pre-cr01/source-manifest.json') ==
       read(PREFIX+'review/source-manifest-initial.json') and changed == sorted([
           'README.md', VP+'wheel_smoke.py', 'layauto_v2/normalization/geometry_input.py',
           'tests/contracts/test_w008_capture_binding.py', 'tests/contracts/test_w008_geometry_wire.py']),
       pre_fix_manifest_digest=h(read(VP+'pre-cr01/source-manifest.json')), changed=changed,
       pre_fix_adapter_matches_snapshot=h(read(PREFIX+'review/geometry_input-before.py.txt')) ==
                                      old['layauto_v2/normalization/geometry_input.py'])

receipt = doc(VP+'receipt.json')
record('receipt_manifest_and_count', receipt['source_manifest_sha256'] == source_digest and
       receipt['source_file_count']==235 and len(receipt['checks']) == 13,
       receipt_sha256=h(read(VP+'receipt.json')), commands=len(receipt['checks']))
for name, entry in receipt['checks'].items():
    output = read(VP+name+'.txt')
    record('command_binding_'+name, entry==doc(VP+name+'.json') and entry['returncode']==0 and
           entry['source_manifest_sha256']==source_digest and entry['output_sha256']==h(output),
           command=entry['command'], cwd=entry['cwd'], returncode=entry['returncode'],
           output_sha256=h(output), elapsed_seconds=entry['elapsed_seconds'])

environment = doc(VP+'environment.json')
env_by_exe = {e['executable']: e for e in environment['environments']}
for tag, version in [('310', '3.10.22'), ('311', '3.11.5')]:
    command = receipt['checks']['pytest-'+tag]['command']
    captured = env_by_exe[command[0]]
    final_summary = re.findall(r'(\d+) passed in ([0-9.]+)s',read(VP+'pytest-'+tag+'.txt').decode())
    old_summary = re.findall(r'(\d+) passed in ([0-9.]+)s',read(VP+'pre-cr01/pytest-'+tag+'.txt').decode())
    record('adopted_matrix_'+tag, final_summary[-1][0]=='730' and old_summary[-1][0]=='713' and
           captured['version'].startswith(version) and command[1:] ==
           ['-m','pytest','tests/unit','tests/contracts','-q','-p','no:cacheprovider'] and
           read(VP+'mypy-'+tag+'.txt').decode().strip() == 'Success: no issues found in 40 source files',
           version=captured['version'], platform=captured['platform'], final_summary=final_summary,
           old_summary=old_summary, basis='Adopted captured execution, not rerun by this audit')

runtime = {p:digest for p,digest in source.items() if p.startswith('layauto_v2/')}
packages = doc(VP+'package-identity.json')
record('package_manifest_binding', packages['source_manifest_sha256']==source_digest and len(runtime)==86,
       runtime_files=len(runtime))
for name, expected in packages['packages'].items():
    raw = read(VP+'packages/'+name)
    if name.endswith('.whl'):
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            members = {p:z.read(p) for p in z.namelist() if not p.endswith('/')}
        record_paths = [p for p in members if p.endswith('.dist-info/RECORD')]
        wheel_record = record_paths[0]
        rows = list(csv.reader(io.StringIO(members[wheel_record].decode())))
        row_errors = []
        if len(rows)!=len(members) or {r[0] for r in rows} != set(members): row_errors.append('member-set')
        for p, digest, length in rows:
            if p == wheel_record:
                if digest or length: row_errors.append(p)
            else:
                actual='sha256='+base64.urlsafe_b64encode(hashlib.sha256(members[p]).digest()).decode().rstrip('=')
                if digest!=actual or length!=str(len(members[p])): row_errors.append(p)
        record('wheel_RECORD_integrity', len(record_paths)==1 and not row_errors, errors=row_errors,
               member_count=len(members))
    else:
        with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as t:
            members={m.name.split('/',1)[1]: t.extractfile(m).read() for m in t.getmembers() if m.isfile()}
    embedded={p:h(data) for p,data in members.items() if p.startswith('layauto_v2/')}
    record('archive_bytes_'+name, h(raw)==expected['sha256'] and len(raw)==expected['size_bytes'] and
           embedded==runtime and len(embedded)==86, sha256=h(raw), size_bytes=len(raw), runtime_files=len(embedded),
           mismatches=sorted(p for p in set(embedded)|set(runtime) if embedded.get(p)!=runtime.get(p)),
           basis='Direct archive reads and full runtime byte hash equality; no build/install')

installs=doc(VP+'installation-identity.json')
for tag in ['310','311']:
    captured=blocks(read(VP+'smoke-'+tag+'.txt'))
    independent_review=blocks(read(PREFIX+'review/installed-smoke-'+tag+'.txt'))
    env=captured[0]['environment']
    result=captured[1]['checks']
    expected=installs['installations'][tag]
    prefix='/private/tmp/layauto-w008-final-installed-'+tag
    artifact='layauto-0.2.0-py3-none-any.whl' if tag=='311' else 'layauto-0.2.0.tar.gz'
    hashes={'layauto_v2/'+p:d for p,d in env['package_manifest'].items()}
    command=receipt['checks']['smoke-'+tag]['command']
    record('adopted_installed_origin_'+tag,
           installs['source_manifest_sha256']==source_digest and hashes==runtime and len(hashes)==86 and
           expected['installed_package']==env['installed_package'] and env['prefix']==prefix and
           env['executable']==command[0]==prefix+'/bin/python' and env['isolated']==1 and
           env['dont_write_bytecode'] is True and command[1:3]==['-I','-B'] and
           env['installed_package'].startswith(prefix+'/lib/python3.') and '/site-packages/' in env['installed_package'] and
           result==expected['checks'] and captured==independent_review and
           expected['input_artifact_actual_sha256']==packages['packages'][artifact]['sha256'] and
           expected['direct_url']['url'].endswith('/'+artifact) and
           receipt['checks']['install-'+tag]['command'][-1].endswith('/'+artifact) and
           receipt['checks']['create-install-'+tag]['command'][-1]==prefix and
           receipt['checks']['smoke-'+tag]['cwd']=='/private/tmp',
           installed_origin=env['installed_package'], runtime_hash_count=len(hashes),
           pip_archive_info=expected['direct_url']['archive_info'],
           exact_reviewer_execution_output_match=captured==independent_review,
           basis='Adopted installation/smoke execution; recorded hashes independently compared, original installation tree unavailable')

post_delivery=git('diff','--name-only',DELIVERY,EXPECTED).decode().splitlines()
product_changes=git('diff','--name-only',DELIVERY,EXPECTED,'--','layauto_v2','tests','pyproject.toml','README.md').decode().splitlines()
protected_changes=git('diff','--name-only','765ff864f4341b91996f70f25723411eebc0d6c2',EXPECTED,'--',
                     'tests/fixtures','tests/support','tests/unit','layauto_v2/importers','layauto_v2/pipeline.py',
                     'layauto_v2/repository','docs/architecture.md','legacy_mvp').decode().splitlines()
record('post_delivery_and_protected_scope', not product_changes and not protected_changes,
       post_delivery_paths=post_delivery, product_changes=product_changes, protected_changes=protected_changes)

review=doc(PREFIX+'review/final-receipt-audit.json')
record('prior_reviewer_audit_identity', review['source_manifest_sha256']==source_digest and
       review['receipt_sha256']==h(read(VP+'receipt.json')) and review['source_entries']==235 and
       review['verified_successful_command_count']==13 and review['all_output_hashes_match'] is True)
pm=doc(PREFIX+'pm-receipt.json')
pm_errors=[p for p,d in pm['saved_evidence_sha256'].items() if h(read(PREFIX+p))!=d]
record('PM_saved_evidence', not pm_errors, saved_entries=len(pm['saved_evidence_sha256']), mismatches=pm_errors)

result={'audit':'Independent W008 premerge evidence audit', 'utc':datetime.now(timezone.utc).isoformat(),
        'repository':str(ROOT),'head':head,'delivery':DELIVERY,
        'python':sys.version,'platform':platform.platform(),'script_sha256':h(pathlib.Path(__file__).read_bytes()),
        'checks_passed':sum(c['passed'] for c in CHECKS),'checks_total':len(CHECKS),
        'must_fix_findings':[c for c in CHECKS if not c['passed']], 'checks':CHECKS,
        'not_executed':['Product tests/typing','Build/install/smoke rerun','Original Mac installed trees'],
        'note':'No historical manifest/script/report modified. Historical task hash checked only at aced62b; other 83 current.'}
(OUT/'audit-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['head','delivery','checks_passed','checks_total','must_fix_findings']},indent=2))
sys.exit(bool(result['must_fix_findings']))
