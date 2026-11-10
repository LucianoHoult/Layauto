import datetime, hashlib, json, os, pathlib, platform, resource, subprocess, sys, time
root = pathlib.Path('/workspace/work/w011-target-regression')
evidence = pathlib.Path('/workspace/work/w011-owner-regression-evidence')
label = sys.argv[1]
assert label in ('original', 'corrected')
output = evidence / (label + '-pytest.txt')
manifest_path = evidence / (label + '-manifest.json')
assert not output.exists() and not manifest_path.exists()
interpreter = '/workspace/work/w011-engineering/dev310/bin/python'
node = 'tests/contracts/test_w011_geometry.py::test_consumed_operator_changes_fail_at_located_component_boundary'
if label == 'original':
    node += '[physical-effective_fin_operator-foreign]'
cmd = [interpreter, '-B', '-m', 'pytest', '-p', 'no:cacheprovider', node, '-q', '--tb=short']
def git(*args):
    return subprocess.check_output(['git', *args], cwd=root, text=True).strip()
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
paths = subprocess.check_output(['git', 'ls-files', 'layauto_v2', 'tests', 'pyproject.toml'], cwd=root, text=True).splitlines()
manifest = {'label': label, 'source_commit': git('rev-parse', 'HEAD'), 'branch': git('branch', '--show-current'), 'worktree_status': git('status', '--short'), 'command': cmd, 'cwd': str(root), 'interpreter': subprocess.check_output([interpreter, '-c', 'import json, platform, sys; print(json.dumps({"executable": sys.executable, "version": sys.version, "platform": platform.platform()}))'], text=True).strip(), 'source_hashes': {p:sha(root/p) for p in paths}, 'start_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'resource_policy': 'Only this one targeted pytest process; 16 GiB shared container; no other child probes started.'}
manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
start = time.monotonic()
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
with output.open('w') as stream:
    process = subprocess.run(cmd, cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT)
manifest.update({'end_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'elapsed_seconds': time.monotonic()-start, 'exit_code': process.returncode, 'child_max_rss_kib': resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss, 'output_sha256': sha(output), 'final_worktree_status': git('status', '--short')})
manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
print(output.read_text())
print(json.dumps({k:manifest[k] for k in ('label', 'source_commit', 'elapsed_seconds', 'exit_code', 'child_max_rss_kib')}))
sys.exit(process.returncode)
