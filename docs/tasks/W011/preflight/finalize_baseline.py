from pathlib import Path
import hashlib,json,tarfile,io,re,shutil
w=Path('/workspace/work/w011-engineering');out=w/'baseline';source=w/'baseline-source'
receipts={tag:json.loads((out/f'pytest-{tag}.json').read_text()) for tag in ('310','312')}
for tag,row in receipts.items():
 assert row['exit_code']==0, row
 text=(out/f'pytest-{tag}.stdout.txt').read_text()
 counts=re.findall(r'^(\d+) passed',text,re.MULTILINE)
 assert counts==['1465'],(tag,counts)
ids={tag:{line for line in (out/f'collection-{tag}.stdout.txt').read_text().splitlines() if line.startswith('tests/') and '::' in line} for tag in ('310','312')}
assert len(ids['310'])==1465 and ids['310']==ids['312']
manifest=json.loads((w/'baseline-source-manifest.json').read_text())
for name,expected in manifest['files'].items():
 assert hashlib.sha256((source/name).read_bytes()).hexdigest()==expected,name
shutil.copyfile(w/'baseline-source-manifest.json',out/'source-manifest.json')
shutil.copyfile(w/'run_baseline.py',out/'run_baseline.py')
with tarfile.open(out/'source-snapshot.tar.gz','w:gz') as archive:
 for name in sorted(manifest['files']):
  data=(source/name).read_bytes();entry=tarfile.TarInfo(name);entry.mtime=0;entry.size=len(data);archive.addfile(entry,io.BytesIO(data))
receipt={'status':'passed','scope':'Original 1465-test baseline only; not final W011 verification','git_head':manifest['head'],'source_file_count':len(manifest['files']),'test_counts':{'310':1465,'312':1465},'collection_ids_equal':True,'source_unchanged':True,'commands':receipts,'source_manifest_sha256':hashlib.sha256((out/'source-manifest.json').read_bytes()).hexdigest(),'source_snapshot_sha256':hashlib.sha256((out/'source-snapshot.tar.gz').read_bytes()).hexdigest()}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
(out/'evidence-manifest.json').write_text(json.dumps({str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file() and p.name!='evidence-manifest.json'},indent=2)+'\n')
print(json.dumps(receipt,indent=2))
