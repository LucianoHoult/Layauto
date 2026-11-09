import hashlib,io,json,pathlib,subprocess,tarfile
root=pathlib.Path('/workspace/work/w011-tests');out=pathlib.Path('/workspace/work/w011-tests-evidence')
known={}
def add(path,data):known[(path,hashlib.sha256(data).hexdigest())]=data
for name in ('geometry-r1-input.tar.gz','parallel-r1-input.tar.gz'):
 with tarfile.open(out/name) as tar:
  for member in tar.getmembers():
   if member.isfile():add(member.name,tar.extractfile(member).read())
for label in ('geometry-r2','contracts-r1','exceptions-r1','review-regressions-r1'):
 manifest=json.loads((out/(label+'.input.json')).read_text())
 for path in manifest['files']:
  for ref in ('dbf49ae','7c85fb4','a8d3987','f493233','f436f59','24e9995','736d4b8'):
   result=subprocess.run(['git','show',ref+':'+path],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
   if result.returncode==0:add(path,result.stdout)
geometry=subprocess.check_output(['git','show','24e9995:tests/contracts/test_w011_geometry.py'],cwd=root).decode()
geometry=geometry.split('\n\ndef test_actual_geometry_length_and_width_are_not_backfilled_from_profile_or_cdl')[0]+'\n'
begin=geometry.index("@pytest.mark.parametrize('failure', ('admission', 'identity'))")
end=geometry.index('    result = build(root)',begin)
geometry=geometry[:begin]+"def test_w007_unsupported_admission_is_retained_without_false_channel_success(tmp_path):\n    root = ready_copy(tmp_path)\n    change_cdl(root, 'source', 'NF=1', 'NF=2')\n"+geometry[end:]
for ending in ('','\n','\n\n'):
 add('tests/contracts/test_w011_geometry.py',geometry.rstrip('\n').encode()+ending.encode())
rows=[]
for label in ('geometry-r2','contracts-r1','exceptions-r1','review-regressions-r1'):
 manifest=json.loads((out/(label+'.input.json')).read_text());missing=[]
 for path,sha in manifest['files'].items():
  if (path,sha) not in known:missing.append(path)
 if not missing:
  with tarfile.open(out/(label+'.input.tar.gz'),'w:gz') as tar:
   for path,sha in manifest['files'].items():
    data=known[path,sha];info=tarfile.TarInfo(path);info.size=len(data);info.mtime=0;tar.addfile(info,io.BytesIO(data))
 rows.append({'label':label,'missing':missing,'snapshot_saved':not missing})
(out/'input-snapshot-reconstruction.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(rows,indent=2))
