"""Independent lightweight witness for the W011 target-only test setup fix."""
from pathlib import Path
from fractions import Fraction
import tempfile, shutil, hashlib, json, sys, time, subprocess

ROOT=Path(sys.argv[1]).resolve()
sys.path.insert(0,str(ROOT))
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import from_parse_result, normalize

fixture=ROOT/'tests/fixtures/w003_m1'
old='NFIN=5 NF=1 M=1 L=4n W=2n VT=toy'
before='VT=toy W=2n L=4n M=1 NF=1 NFIN=5'
after='VT=toy W=3n L=6n M=1 NF=1 NFIN=3'
started=time.monotonic()
with tempfile.TemporaryDirectory(dir=sys.argv[2]) as td:
    root=Path(td)/'input';shutil.copytree(fixture,root)
    source_before=(root/'source.cdl').read_bytes()
    target=(root/'target.cdl').read_text()
    assert old not in target
    assert target.count(before)==1
    changed=target.replace(before,after)
    assert sum(a!=b for a,b in zip(target.splitlines(),changed.splitlines()))==1
    assert next(x for x in target.splitlines() if x.startswith('MP0'))==next(x for x in changed.splitlines() if x.startswith('MP0'))
    (root/'target.cdl').write_text(changed)
    p=root/'query/header.json';h=json.loads(p.read_text())
    for item in [h['layout'],h['source_netlist'],h['target'],*h['raw'],*h['closure']['entries']]:
        q=root/item['uri']
        if q.exists():item['sha256']=hashlib.sha256(q.read_bytes()).hexdigest()
    h['closure']['entries'].sort(key=lambda x:x['uri'])
    h['closure']['sha256']=hashlib.sha256(json.dumps(h['closure']['entries'],sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    p.write_text(json.dumps(h,indent=2)+'\n')
    parsed=read_inputs(root/'site_config.yaml');assert parsed.status=='success',parsed.issues
    semantic=normalize(from_parse_result(parsed));assert semantic.status=='success',semantic.issues
    actual=[(x.operand_ref.name,x.axis,str(x.semantic_before.exact),str(x.semantic_after.exact)) for x in semantic.value.differences]
    expected=[('MN0','channel_length',str(Fraction(4,10**9)),str(Fraction(6,10**9))),
              ('MN0','fin_width',str(Fraction(2,10**9)),str(Fraction(3,10**9))),
              ('MN0','fins_per_finger','5','3')]
    assert actual==expected,(actual,expected)
    assert (root/'source.cdl').read_bytes()==source_before
    print(json.dumps({'candidate_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'runtime_matches_8917':not subprocess.check_output(['git','diff','8917d38','HEAD','--','layauto_v2'],cwd=ROOT,text=True),
        'python':sys.version,'executable':sys.executable,'argv':[sys.executable,'-B',*sys.argv],'cwd':str(Path.cwd()),
        'old_before_absent':True,'corrected_before_occurrences':1,'only_mn0_target_line_changed':True,
        'source_bytes_unchanged':True,'mp0_target_line_unchanged':True,'differences':actual,
        'comparison_order_basis':'W007 build_differences sorts op/operand/axis; W011 source comparisons use unchanged source associations and geometry.',
        'elapsed_seconds':time.monotonic()-started,'limit':'Actual read+W007 normalization only; no W011 heavy/full codec or full matrix run.'},ensure_ascii=False,indent=2))
