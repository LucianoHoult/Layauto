"""Independent final engineering receipt/source/artifact/install review only."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import tarfile
import zipfile

ROOT = Path('/workspace/Layauto')
A1 = ROOT/'docs/tasks/W012/A1'
V = A1/'verification-r2'
OUT = Path(__file__).resolve().parent
checks = 0


def check(condition, label):
    global checks
    assert condition,label
    checks += 1


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    receipt = json.loads((V/'receipt.json').read_text())
    check(receipt['status'] == 'passed', 'new complete engineering receipt')
    check(receipt['actual_test_counts'] == {'310':1656,'312':1656}, 'dual actual1656')
    check(receipt['retained_baseline_test_count'] == 1605 and receipt['expected_test_count'] == 1656, 'full baseline1605 retained')
    check(receipt['matrix_workers'] == 2 and receipt['resource_gate'] is None, 'explicit new engineering scheduling')
    check('--allow-parallel-without-gate' in receipt['runner_command'], 'explicit concurrency opt-in recorded')
    source = json.loads((V/'source-manifest.json').read_text())
    check(len(source['files']) == receipt['source_file_count'] == 263, 'frozen source263')
    check(len(source['runtime_files']) == receipt['runtime_file_count'] == 100, 'frozen runtime100')
    frozen = json.loads((A1/'performance/frozen-identity.json').read_text())
    check(source['files'] == frozen['sources']['after'], 'engineering same as measured after source')
    for name,digest in source['files'].items():
        check(sha(ROOT/name) == digest, 'current source '+name)
    with tarfile.open(V/'source-snapshot.tar.gz') as archive:
        snapshot = {m.name:hashlib.sha256(archive.extractfile(m).read()).hexdigest() for m in archive if m.isfile()}
    check(snapshot == source['files'], 'complete reconstructable snapshot263')
    check(sha(V/'source-manifest.json') == receipt['source_manifest_sha256'], 'source manifest actual hash')
    check(sha(V/'source-snapshot.tar.gz') == receipt['source_snapshot_sha256'], 'source snapshot actual hash')
    check(receipt['source_identity_rechecked_after_all_commands'], 'runner final source recheck')
    check(sha(V/'prepare_final.py') == receipt['runner_sha256'], 'actual archived final runner hash')
    check(sha(V/'installed_smoke.py') == receipt['smoke_sha256'], 'actual archived final smoke hash')
    check(receipt['runner_sha256'] == json.loads((A1/'recovery-plan.json').read_text())['runner_sha256'], 'reviewed recovery runner')
    check(receipt['smoke_sha256'] == '471401c6f64d78c236d640bf15dbdeaed23dee5a62fc6a325e8192e480361960', 'reviewed strengthened installed smoke')
    names = [row['stdout'].removesuffix('.stdout.txt') for row in receipt['commands']]
    expected = {base+'-'+tag for base in ('environment','collection','pytest','typing','pip-check',
                  'create-install','install','installed-pip-check','installed-identity','installed-smoke') for tag in ('310','312')} | {'build'}
    check(len(names) == len(set(names)) == 21 and set(names) == expected, 'all21 required complete commands')
    rows = {name:row for name,row in zip(names,receipt['commands'])}
    for name,row in rows.items():
        check(row['exit_code'] == 0, 'command exit0 '+name)
        check(json.loads((V/(name+'.json')).read_text()) == row, 'per-command receipt '+name)
        for stream in ('stdout','stderr'):
            check(sha(V/row[stream]) == row[stream+'_sha256'], 'original '+stream+' '+name)
        check(datetime.fromisoformat(row['started_at_utc']) <= datetime.fromisoformat(row['finished_at_utc']), 'actual command chronology '+name)
    baseline_ids = {line for line in (V/'baseline-collection.txt').read_text().splitlines() if line.startswith('tests/') and '::' in line}
    check(len(baseline_ids) == 1605 and sha(V/'baseline-collection.txt') == receipt['baseline_collection_sha256'], 'actual baseline node set1605')
    for tag in ('310','312'):
        ids = {line for line in (V/('collection-'+tag+'.stdout.txt')).read_text().splitlines() if line.startswith('tests/') and '::' in line}
        check(len(ids) == 1656 and baseline_ids <= ids, 'actual retained collection '+tag)
        check(all('test_w012_hex_validation.py::' in item for item in ids-baseline_ids), 'only51 new hex cases '+tag)
        text = (V/('pytest-'+tag+'.stdout.txt')).read_text()
        check(re.findall(r'^(\d+) passed',text,re.MULTILINE) == ['1656'], 'actual full pytest output '+tag)
        check('Success: no issues found in 54 source files' in (V/('typing-'+tag+'.stdout.txt')).read_text(), 'actual strict typing54 '+tag)
        env = json.loads((V/('environment-'+tag+'.stdout.txt')).read_text())
        check(env['version'].startswith('3.'+('10' if tag == '310' else '12')+'.'), 'actual interpreter '+tag)
        check(Path(env['source_package']).parent == Path(rows['pytest-'+tag]['cwd'])/'layauto_v2', 'actual snapshot import '+tag)
    all_matrices_finish = max(datetime.fromisoformat(row['finished_at_utc']) for name,row in rows.items()
                              if name.startswith(('environment-','collection-','pytest-','typing-','pip-check-')))
    check(all_matrices_finish <= datetime.fromisoformat(rows['build']['started_at_utc']), 'build after both complete matrices')
    profile = json.loads((A1/'profile/receipt.json').read_text())
    check(datetime.fromisoformat(profile['commands'][-1]['finished_at_utc']) <=
          min(datetime.fromisoformat(rows['environment-'+tag]['started_at_utc']) for tag in ('310','312')), 'new matrices after completed profile')
    package = json.loads((V/'package-identity.json').read_text())
    package_rows = {}
    actual_final_payloads = {}
    for kind in ('wheel','sdist'):
        row = package[kind]
        artifact = Path(row['path'])
        check(sha(artifact) == row['sha256'], 'actual final '+kind+' hash')
        if kind == 'wheel':
            with zipfile.ZipFile(artifact) as archive:
                actual = {n.removeprefix('layauto_v2/'):hashlib.sha256(archive.read(n)).hexdigest()
                          for n in archive.namelist() if n.startswith('layauto_v2/') and (n.endswith('.py') or n.endswith('/py.typed'))}
        else:
            with tarfile.open(artifact) as archive:
                actual = {'/'.join(Path(m.name).parts[2:]):hashlib.sha256(archive.extractfile(m).read()).hexdigest()
                          for m in archive if m.isfile() and len(Path(m.name).parts)>2 and Path(m.name).parts[1]=='layauto_v2'
                          and (m.name.endswith('.py') or m.name.endswith('/py.typed'))}
        check(actual == row['runtime_files'] == source['runtime_files'] and len(actual) == 100, 'actual final100 runtime members '+kind)
        package_rows[kind] = {'sha256':row['sha256'],'runtime_files':len(actual)}
        actual_final_payloads[kind] = actual
    comparison = json.loads((A1/'package-comparison.json').read_text())
    before_identity = json.loads((A1/'before-package/package-identity.json').read_text())
    for kind in ('wheel','sdist'):
        row = before_identity[kind]
        artifact = A1/'before-package/dist'/Path(row['path']).name
        check(sha(artifact) == row['sha256'], 'actual before artifact still retained '+kind)
        if kind == 'wheel':
            with zipfile.ZipFile(artifact) as archive:
                before_payload = {n.removeprefix('layauto_v2/'):hashlib.sha256(archive.read(n)).hexdigest()
                                  for n in archive.namelist() if n.startswith('layauto_v2/') and (n.endswith('.py') or n.endswith('/py.typed'))}
        else:
            with tarfile.open(artifact) as archive:
                before_payload = {'/'.join(Path(m.name).parts[2:]):hashlib.sha256(archive.extractfile(m).read()).hexdigest()
                                  for m in archive if m.isfile() and len(Path(m.name).parts)>2 and Path(m.name).parts[1]=='layauto_v2'
                                  and (m.name.endswith('.py') or m.name.endswith('/py.typed'))}
        check(before_payload == row['runtime_files'] and len(before_payload) == 100, 'actual before100 members reread '+kind)
        differences = sorted(n for n in before_payload.keys() | actual_final_payloads[kind].keys()
                             if before_payload.get(n) != actual_final_payloads[kind].get(n))
        check(differences == ['domain/codec.py'] == comparison['runtime_payload_differences'][kind], 'only authorized actual package payload difference '+kind)
    installations = json.loads((V/'installation-identity.json').read_text())
    for tag in ('310','312'):
        identity = installations[tag]
        check(identity['fresh_environment'] and identity['isolated'] == 1, 'fresh isolated install '+tag)
        installed = Path(identity['package']).resolve().parent
        check('site-packages' in installed.parts and installed.is_relative_to(Path(identity['executable']).parents[1]), 'actual clean installed package '+tag)
        check(identity['runtime_files'] == source['runtime_files'], 'all installed100 actual hashes recorded '+tag)
        actual_installed = {str(p.relative_to(installed)):sha(p) for p in installed.rglob('*')
                            if p.is_file() and (p.suffix == '.py' or p.name == 'py.typed')}
        check(actual_installed == source['runtime_files'], 'current actual installed100 member bytes '+tag)
        check(identity['artifact_sha256'] == sha(Path(identity['artifact'])), 'installed artifact identity '+tag)
        smoke_row = rows['installed-smoke-'+tag]
        cwd = Path(smoke_row['cwd'])
        check('-I' in smoke_row['command'] and '-B' in smoke_row['command'], 'actual isolated smoke command '+tag)
        check(not cwd.is_relative_to(ROOT) and not cwd.is_relative_to(Path(rows['pytest-'+tag]['cwd'])), 'actual smoke cwd outside repo/snapshot '+tag)
        smoke = json.loads((V/smoke_row['stdout']).read_text())
        check(smoke['package'] == identity['package'], 'smoke uses verified installed runtime '+tag)
        check(smoke['attempt_unchanged'] and smoke['checkpoint_unchanged'] and smoke['terminal_absent'], 'smoke attempt/checkpoint/no terminal '+tag)
        for case in ('direct','readback','extraction_mismatch'):
            facts = smoke[case]
            mismatch = case == 'extraction_mismatch'
            check(facts['counts'] == {'MN0':4 if mismatch else 5,'MP0':7}, 'actual installed counts '+tag+case)
            check(facts['difference_count'] == (1 if mismatch else 0) and facts['comparison_status'] == ('mismatch' if mismatch else 'equal'), 'actual installed source comparison '+tag+case)
            check(facts['raw_FIN_records'] == 18 and facts['local_nodes'] == 14 and facts['local_edges'] == 8
                  and facts['local_components'] == 6 and facts['body_shapes'] == 6 and facts['local_enclosure_status'] == 'pass', 'actual installed retained facts '+tag+case)
    check(datetime.fromisoformat(rows['installed-smoke-310']['finished_at_utc']) <=
          datetime.fromisoformat(rows['create-install-312']['started_at_utc']), 'two clean package paths serial')
    evidence = json.loads((V/'evidence-manifest.json').read_text())
    for name,digest in evidence.items():
        check(sha(V/name) == digest, 'closed final engineering attachment '+name)
    result = {'status':'passed','checks':checks,'receipt_sha256':sha(V/'receipt.json'),
              'source_manifest_sha256':sha(V/'source-manifest.json'),'packages':package_rows,
              'actual_tests':receipt['actual_test_counts'],'runtime_files':100,'source_files':263,
              'scope':'actual completed new final engineering evidence; no product/test/performance sample rerun'}
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(str(checks)+' independent final engineering evidence checks passed; no sample rerun')


if __name__ == '__main__':
    main()
