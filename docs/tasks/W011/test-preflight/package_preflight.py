import hashlib,io,json,pathlib,subprocess,tarfile
root=pathlib.Path('/workspace/work/w011-tests');out=pathlib.Path('/workspace/work/w011-tests-evidence')
def sha(data):return hashlib.sha256(data).hexdigest()
def git_files(ref):
 raw=subprocess.check_output(['git','archive',ref,'layauto_v2','tests','pyproject.toml'],cwd=root)
 with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
  return {member.name:archive.extractfile(member).read() for member in archive.getmembers() if member.isfile()}
def overlay(path):
 with tarfile.open(path) as archive:
  return {member.name:archive.extractfile(member).read() for member in archive.getmembers() if member.isfile()}
def save_tar(path,contents):
 with tarfile.open(path,'w:gz') as archive:
  for name,data in sorted(contents.items()):
   info=tarfile.TarInfo(name);info.size=len(data);info.mtime=0;info.mode=0o644
   archive.addfile(info,io.BytesIO(data))
# Last probe used a clean committed tree: retrieve every captured source file exactly.
label='cr04-regressions-r1';meta=json.loads((out/(label+'.input.json')).read_text())
files={path:subprocess.check_output(['git','show',meta['git_head']+':'+path],cwd=root) for path in meta['files']}
assert all(sha(data)==meta['files'][path] for path,data in files.items())
save_tar(out/(label+'.input.tar.gz'),files)
snapshots=out/'full-snapshots';snapshots.mkdir(exist_ok=True)
items=[
 ('geometry-r1','81e01da1e5a6ce8e7132f3cebf8ee92bc237246f','geometry-r1-input.tar.gz','geometry-r1-input.json'),
 ('contracts-r1','a8d3987bc3295c84ff2aa62be0350af51955fbeb','contracts-r1.input.tar.gz','contracts-r1.input.json'),
 ('exceptions-r1','a8d3987bc3295c84ff2aa62be0350af51955fbeb','exceptions-r1.input.tar.gz','exceptions-r1.input.json'),
 ('geometry-r2','f493233','geometry-r2.input.tar.gz','geometry-r2.input.json'),
 ('review-regressions-r1','736d4b8','review-regressions-r1.input.tar.gz','review-regressions-r1.input.json'),
 ('review-regressions-r2','a272a34','review-regressions-r2.input.tar.gz','review-regressions-r2.input.json'),
 ('cr04-regressions-r1',meta['git_head'],label+'.input.tar.gz',label+'.input.json'),
]
results=[]
for label,ref,archive_name,manifest_name in items:
 base=git_files(ref);base.update(overlay(out/archive_name));manifest=json.loads((out/manifest_name).read_text())
 assert all(sha(base[path])==expected for path,expected in manifest['files'].items())
 target=snapshots/(label+'.tar.gz');save_tar(target,base)
 identity={'basis_commit':subprocess.check_output(['git','rev-parse',ref],cwd=root,text=True).strip(),
 'overlay':archive_name,'scope':'all tracked layauto_v2, tests (including immutable fixtures/support), and pyproject.toml; task documentation is not in the tested-code snapshot',
 'files':{path:sha(data) for path,data in sorted(base.items())},'archive':target.name,'archive_sha256':sha(target.read_bytes())}
 (snapshots/(label+'.manifest.json')).write_text(json.dumps(identity,indent=2)+'\n')
 results.append({'probe':label,'archive':str(target.relative_to(out)),'files':len(base),'sha256':identity['archive_sha256']})
(out/'full-snapshots-index.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
