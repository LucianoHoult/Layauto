#!/usr/bin/env python3
"""Read-only W008 delivery evidence audit; does not execute/import product code."""
from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import pathlib
import re
import subprocess
import sys
import tarfile
import zipfile
from datetime import datetime, timezone

ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else '/workspace/Layauto').resolve()
OUT = pathlib.Path(__file__).resolve().parent
DELIVERY = 'aced62b0adda35fe7bcd8284a7354badc5b03649'
BASE = '2560999021f2551793346187e3c4825276cba2ff'
EXPECTED_HEAD = 'baad5347627db194649430cf6b0f5ebf0aa1165e'
PREFIX = 'docs/tasks/W008/'
V = PREFIX + 'verification/'
findings: list[dict] = []
checks: list[dict] = []

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def git(*args: str) -> bytes:
    return subprocess.check_output(['git', '-C', str(ROOT), *args])

def read(path: str) -> bytes:
    return (ROOT/path).read_bytes()

def doc(path: str):
    return json.loads(read(path))

def check(name: str, ok: bool, **detail) -> None:
    result = {'name': name, 'passed': bool(ok), **detail}
    checks.append(result)
    if not ok:
        findings.append(result)

def json_blocks(data: bytes) -> list[dict]:
    remaining = data.decode()
    blocks = []
    while remaining.strip():
        remaining = remaining.lstrip()
        value, stop = json.JSONDecoder().raw_decode(remaining)
        blocks.append(value)
        remaining = remaining[stop:]
    return blocks

head = git('rev-parse', 'HEAD').decode().strip()
post_paths = git('diff', '--name-only', DELIVERY, head).decode().splitlines()
check('git_base_and_post_delivery',
      git('rev-parse', DELIVERY+'^').decode().strip() == BASE
      and head == EXPECTED_HEAD
      and sorted(post_paths) == ['docs/current-work.md', 'docs/roadmap.md'],
      integrated_pm_base=BASE, delivered_commit=DELIVERY, audit_head=head,
      post_delivery_paths=post_paths)

manifest = doc(V+'source-manifest.json')
manifest_hash = sha(read(V+'source-manifest.json'))
tracked = git('ls-tree', '-r', '--name-only', DELIVERY).decode().splitlines()
expected_paths = {p for p in tracked if p.startswith(('layauto_v2/', 'tests/'))}
expected_paths |= {'README.md', 'pyproject.toml', PREFIX+'plan.md', V+'wheel_smoke.py'}
local_mismatches = [p for p,h in manifest.items() if not (ROOT/p).is_file() or sha(read(p)) != h]
git_mismatches = [p for p,h in manifest.items() if sha(git('show', DELIVERY+':'+p)) != h]
check('final_source_manifest', len(manifest)==235 and not local_mismatches and not git_mismatches
      and set(manifest)==expected_paths
      and manifest_hash=='30b4e446ff6b38f8c06be92916576928b87abdf62d10bc58f1b22ffa34a5f881',
      sha256=manifest_hash, file_count=len(manifest), current_mismatches=local_mismatches,
      delivered_git_mismatches=git_mismatches, omitted_paths=sorted(expected_paths-set(manifest)),
      extra_paths=sorted(set(manifest)-expected_paths))

evidence_manifest=doc(V+'evidence-manifest.json')
evidence_mismatches=[p for p,h in evidence_manifest.items() if not (ROOT/p).is_file() or sha(read(p))!=h]
evidence_git_mismatches=[p for p,h in evidence_manifest.items() if sha(git('show', DELIVERY+':'+p))!=h]
check('attached_evidence_manifest', not evidence_mismatches and not evidence_git_mismatches,
      sha256=sha(read(V+'evidence-manifest.json')), file_count=len(evidence_manifest),
      current_mismatches=evidence_mismatches, delivered_git_mismatches=evidence_git_mismatches)

initial=doc(V+'pre-cr01/source-manifest.json')
changed=[p for p in sorted(set(manifest)|set(initial)) if manifest.get(p)!=initial.get(p)]
expected_changed=['README.md', V+'wheel_smoke.py', 'layauto_v2/normalization/geometry_input.py',
                  'tests/contracts/test_w008_capture_binding.py', 'tests/contracts/test_w008_geometry_wire.py']
check('pre_fix_identity_separate', len(initial)==235 and changed==sorted(expected_changed)
      and read(V+'pre-cr01/source-manifest.json')==read(PREFIX+'review/source-manifest-initial.json')
      and sha(read(PREFIX+'review/geometry_input-before.py.txt'))==initial['layauto_v2/normalization/geometry_input.py'],
      final_manifest_sha256=manifest_hash, initial_manifest_sha256=sha(read(V+'pre-cr01/source-manifest.json')),
      changed_paths=changed, corrected_input_sha256=manifest['layauto_v2/normalization/geometry_input.py'])

receipt=doc(V+'receipt.json')
environment=doc(V+'environment.json')
envs={e['executable']:e for e in environment['environments']}
check('receipt_summary_binding', receipt['source_manifest_sha256']==manifest_hash
      and receipt['source_file_count']==235 and receipt['tests_per_interpreter']==730
      and receipt['prior_tests_retained']==553 and receipt['added_tests']==177
      and receipt['strict_modules']==40 and receipt['pm_documentation_integrated']==BASE
      and len(receipt['checks'])==13,
      receipt_sha256=sha(read(V+'receipt.json')), environment_sha256=sha(read(V+'environment.json')))
for name, record in receipt['checks'].items():
    raw=read(V+name+'.txt')
    check('command_'+name, record==doc(V+name+'.json') and record['returncode']==0
          and record['source_manifest_sha256']==manifest_hash and record['output_sha256']==sha(raw),
          command=record['command'], cwd=record['cwd'], output_sha256=sha(raw),
          started_utc=record['started_utc'], elapsed_seconds=record['elapsed_seconds'])
for tag,version in [('310','3.10.22'),('311','3.11.5')]:
    raw=read(V+'pytest-'+tag+'.txt').decode()
    old=read(V+'pre-cr01/pytest-'+tag+'.txt').decode()
    command=receipt['checks']['pytest-'+tag]['command']
    environment_entry=envs[command[0]]
    count=re.findall(r'(\d+) passed in ([0-9.]+)s',raw)
    old_count=re.findall(r'(\d+) passed in ([0-9.]+)s',old)
    check('recorded_test_matrix_'+tag, count and count[-1][0]=='730' and old_count and old_count[-1][0]=='713'
          and environment_entry['version'].startswith(version)
          and command[1:]==['-m','pytest','tests/unit','tests/contracts','-q','-p','no:cacheprovider'],
          recorded_final=count, recorded_pre_fix=old_count,
          executable=command[0], version=environment_entry['version'], platform=environment_entry['platform'],
          evidence_basis='Adopted execution log; no suite rerun by this audit')
    type_log=read(V+'mypy-'+tag+'.txt').decode().strip()
    check('recorded_typing_'+tag, type_log=='Success: no issues found in 40 source files'
          and receipt['checks']['mypy-'+tag]['command'][0]==command[0],
          output=type_log, evidence_basis='Adopted execution log; no mypy rerun by this audit')

runtime={p:h for p,h in manifest.items() if p.startswith('layauto_v2/')}
package_identity=doc(V+'package-identity.json')
check('package_identity_binding',package_identity['source_manifest_sha256']==manifest_hash and len(runtime)==86,
      runtime_count=len(runtime))
for filename, identity in package_identity['packages'].items():
    package_path=V+'packages/'+filename
    data=read(package_path)
    if filename.endswith('.whl'):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            members={name:archive.read(name) for name in archive.namelist() if not name.endswith('/')}
        embedded={p:sha(b) for p,b in members.items() if p.startswith('layauto_v2/')}
        record_name=next(p for p in members if p.endswith('.dist-info/RECORD'))
        record_issues=[]
        for row in csv.reader(io.StringIO(members[record_name].decode())):
            p, hash_field, size=row
            if p==record_name:
                if hash_field or size:record_issues.append(p)
                continue
            actual='sha256='+base64.urlsafe_b64encode(hashlib.sha256(members[p]).digest()).decode().rstrip('=')
            if hash_field!=actual or size!=str(len(members[p])):record_issues.append(p)
        check('wheel_record',not record_issues, file_count=len(members), mismatches=record_issues)
    else:
        with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as archive:
            members={m.name.partition('/')[2]:archive.extractfile(m).read() for m in archive.getmembers() if m.isfile()}
        embedded={p:sha(b) for p,b in members.items() if p.startswith('layauto_v2/')}
    check('archive_'+filename,sha(data)==identity['sha256'] and len(data)==identity['size_bytes']
          and len(embedded)==identity['runtime_file_count']==86 and embedded==runtime,
          sha256=sha(data), size_bytes=len(data), runtime_count=len(embedded),
          mismatch_paths=sorted(p for p in set(embedded)|set(runtime) if embedded.get(p)!=runtime.get(p)),
          evidence_basis='Directly read actual attached archive bytes; no extraction/import/build')

installation=doc(V+'installation-identity.json')
check('installation_binding',installation['source_manifest_sha256']==manifest_hash,
      evidence_basis='Recorded installed manifests, not access to original Mac installation trees')
for tag in ['310','311']:
    identity=installation['installations'][tag]
    blocks=json_blocks(read(V+'smoke-'+tag+'.txt'))
    review_blocks=json_blocks(read(PREFIX+'review/installed-smoke-'+tag+'.txt'))
    env=blocks[0]['environment']; observed=blocks[1]['checks']
    installed={'layauto_v2/'+p:h for p,h in env['package_manifest'].items()}
    command=receipt['checks']['smoke-'+tag]['command']
    prefix='/private/tmp/layauto-w008-final-installed-'+tag
    package_name='layauto-0.2.0-py3-none-any.whl' if tag=='311' else 'layauto-0.2.0.tar.gz'
    package_hash=package_identity['packages'][package_name]['sha256']
    check('recorded_clean_install_'+tag, installed==runtime and len(installed)==86
          and identity['runtime_file_count']==86 and env['installed_package']==identity['installed_package']
          and env['installed_package'].startswith(prefix+'/lib/python3.') and '/site-packages/' in env['installed_package']
          and env['prefix']==prefix and env['executable']==command[0]==prefix+'/bin/python'
          and env['isolated']==1 and env['dont_write_bytecode'] is True and command[1:3]==['-I','-B']
          and receipt['checks']['smoke-'+tag]['cwd']=='/private/tmp'
          and receipt['checks']['create-install-'+tag]['command'][-1]==prefix
          and receipt['checks']['install-'+tag]['command'][-1].endswith('/'+package_name)
          and identity['input_artifact_actual_sha256']==package_hash
          and identity['direct_url']['url'].endswith('/'+package_name)
          and identity['checks']==observed and blocks==review_blocks
          and observed['status']=='passed' and observed['local_records']==40 and observed['base_fragments']==41
          and observed['independent_body_shapes']==6 and observed['projected_records']==38
          and observed['attempt_phase']=='unsealed' and observed['terminal'] is None
          and observed['false_first_acquisition_alias']=='GeometryCaptureBindingMismatch',
          installed_package=env['installed_package'], installed_runtime_hashes=len(installed),
          exact_execution_and_review_smoke_match=blocks==review_blocks,
          direct_url_records_archive_hash=identity['direct_url_records_archive_hash'],
          archive_info=identity['direct_url']['archive_info'],
          evidence_basis='Directly compared recorded installed-file hashes and smoke data; adopted actual install/smoke execution')

protected=doc(V+'delivery-checks.json')['protected_paths_unchanged_relative_to_integrated_pm_head']
protected+=['docs/tasks/W003','docs/tasks/W004-fixture-revision.md','docs/tasks/W005',
             'docs/tasks/W005-input-reading-binding.md','docs/tasks/W006', 'docs/tasks/W006-precontext-run-audit.md',
             'docs/tasks/W007', 'docs/tasks/W007-semantic-identity-normalization.md',
             'tests/unit','layauto_v2/domain/acquisition.py','layauto_v2/domain/publication.py',
             'layauto_v2/domain/publication_codec.py','layauto_v2/domain/evidence.py','layauto_v2/domain/results.py',
             'layauto_v2/domain/circuit.py','layauto_v2/domain/intent.py','layauto_v2/domain/source_location.py']
protected_changes=git('diff','--name-only',BASE,DELIVERY,'--',*protected).decode().splitlines()
check('protected_prior_deliveries_unchanged',not protected_changes, checked_paths=protected, changed_paths=protected_changes)
all_changed=git('diff','--name-status',BASE,DELIVERY,'--','tests','layauto_v2').decode().splitlines()
existing=[line.split('\t',1)[1] for line in all_changed if not line.startswith('A\t')]
allowed={'layauto_v2/domain/geometry.py','layauto_v2/normalization/__init__.py','layauto_v2/state/coordinate.py',
         'layauto_v2/state/layout_store.py','layauto_v2/state/occupancy.py','tests/contracts/test_w007_contracts.py'}
check('existing_runtime_and_test_change_scope',set(existing)==allowed,modified_existing=existing,
      note='W007 dependency guard only adds named W008 adapter decoders and three pure state imports; reviewed diff directly. Earlier normalizer modules unchanged.')

review_receipt=doc(PREFIX+'review/final-receipt-audit.json')
check('review_receipt_binding',review_receipt['source_manifest_sha256']==manifest_hash
      and review_receipt['receipt_sha256']==sha(read(V+'receipt.json'))
      and review_receipt['source_entries']==235 and review_receipt['verified_successful_command_count']==13
      and review_receipt['all_output_hashes_match'] is True)

result={
    'audit':'W008 read-only PM evidence audit', 'audited_utc':datetime.now(timezone.utc).isoformat(),
    'repository':str(ROOT),'delivery_commit':DELIVERY,'observed_head':head,
    'script_sha256':sha(pathlib.Path(__file__).read_bytes()),
    'must_fix_findings':len(findings),'checks_passed':sum(c['passed'] for c in checks),'checks_total':len(checks),
    'findings':findings,'checks':checks,
    'direct_checks':['Git delivery and current byte identity of 235 source/test/config files',
                     'All attached evidence-manifest hashes, 13 command receipt/log bindings',
                     'Actual wheel/sdist runtime bytes and wheel RECORD',
                     'Recorded installed-file hashes and site-packages origins against final manifest',
                     'Final vs pre-CR01 identity and protected path Git diffs'],
    'adopted_execution':['Python 3.10.22 and 3.11.5 each 730 passed; strict mypy each 40 modules',
                         'Fresh package build and two clean installs; execution and independent review smoke logs'],
    'not_performed':['Product test execution','Product imports or smoke execution','Build/install rerun',
                     'Access to original Mac installed directories','Repository mutation','PM acceptance'],
}
(OUT/'checks.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['must_fix_findings','checks_passed','checks_total','script_sha256']},indent=2))
if findings: print(json.dumps(findings,indent=2))
sys.exit(bool(findings))
