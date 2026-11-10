"""Independent lightweight W005 admission/progress witness; no W011 heavy build."""
from pathlib import Path
from dataclasses import asdict
import tempfile, shutil, hashlib, json, sys, subprocess, time

ROOT=Path(sys.argv[1]).resolve()
sys.path.insert(0,str(ROOT))
from layauto_v2.importers import read_inputs
from layauto_v2.domain.codec import canonical_bytes

fixture=ROOT/'tests/fixtures/w003_m1'
cases=(('physical','effective_fin_operator','foreign'),
       ('physical','qualification','positive overlap only'),
       ('derived','trim_operator','identity'),
       ('derived','annotation_match_tolerance_nm',1))
started=time.monotonic()
rows=[]
with tempfile.TemporaryDirectory(dir=sys.argv[2]) as td:
    for index,(owner,field,value) in enumerate(cases):
        root=Path(td)/str(index);shutil.copytree(fixture,root)
        shutil.rmtree(root/'query/normalized')
        path=root/'tech'/f'{owner}.json';doc=json.loads(path.read_text())
        selected=doc['fin_count_profile'] if owner=='physical' else doc['derived_registry'][0]
        selected[field]=value
        path.write_text(json.dumps(doc,indent=2)+'\n')
        p=root/'query/header.json';h=json.loads(p.read_text())
        for item in [h['layout'],h['source_netlist'],h['target'],*h['raw'],*h['closure']['entries']]:
            q=root/item['uri']
            if q.exists():item['sha256']=hashlib.sha256(q.read_bytes()).hexdigest()
        h['closure']['entries'].sort(key=lambda x:x['uri'])
        h['closure']['sha256']=hashlib.sha256(json.dumps(h['closure']['entries'],sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
        p.write_text(json.dumps(h,indent=2)+'\n')
        result=read_inputs(root/'site_config.yaml')
        entry={'owner':owner,'field':field,'value':value,'status':result.status,
               'issues':[asdict(issue) for issue in result.issues],
               'completed_kinds':[record.kind for record in result.completed],
               'captured_sources':[source.uri for source in result.sources]}
        if field=='effective_fin_operator':
            assert result.status=='error' and result.value is None
            assert len(result.issues)==1
            issue=result.issues[0]
            assert (issue.category,issue.code,issue.source.uri,issue.source.field)==('config','InvalidSchema','tech/physical.json','/fin_count_profile/effective_fin_operator')
            source=next(item for item in result.sources if item.uri=='tech/physical.json')
            assert source.data==path.read_bytes()
            assert source.sha256==issue.source.sha256==hashlib.sha256(path.read_bytes()).hexdigest()
            assert [record.kind for record in result.completed]==['config']
            assert canonical_bytes(result.completed[0].payload)==canonical_bytes(json.loads((root/'site_config.yaml').read_text()))
            assert result.completed[0].sources[0].sha256==hashlib.sha256((root/'site_config.yaml').read_bytes()).hexdigest()
            entry['bad_owner_bytes_hash_preserved']=True
            entry['completed_config_payload_and_source_preserved']=True
        else:
            assert result.status=='success' and not result.issues
        rows.append(entry)
print(json.dumps({'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    'runtime_matches_8917':not subprocess.check_output(['git','diff','8917d38','HEAD','--','layauto_v2'],cwd=ROOT,text=True),
    'argv':[sys.executable,'-B',*sys.argv],'cwd':str(Path.cwd()),'python':sys.version,
    'cases':rows,'elapsed_seconds':time.monotonic()-started,
    'scope':'Actual read_inputs only; schema-legal cases still require complete W011 tests. No product/fixture edits.'},ensure_ascii=False,indent=2))
