"""Read-only independent current-oracle/raw-coordinate arithmetic audit.

No runtime import or generator: this audits expected local scope from authored
oracle/spec plus current raw NET SHAPES, without constructing a product result.
"""
from fractions import Fraction as F
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

root = Path('tests/fixtures/w003_m1')
paths = ['oracle.json','independent-design-answer.json','spec.json','query/requests.json',
         'tech/derived.json','special/cut_islands/oracle.json']
def load(name):
    return json.loads((root/name).read_text())
def area(box):
    return (box[2]-box[0])*(box[3]-box[1])
oracle, independent, spec = load(paths[0]), load(paths[1])['local_scope'], load(paths[2])
shapes = {row['id']:row for row in spec['shapes']}
regions = {row['id']:tuple(row['bbox']) for row in oracle['fragments']}
regions.update({name:tuple(row['bbox']) for name,row in shapes.items()
                if row['layer'] in ('BODY_N','BODY_P','POLY','LI','M1')})
assert regions=={name:tuple(box) for name,box in independent['regions'].items()}
assert len(shapes)==independent['drawn_shape_count']==40 and len(regions)==14
parents={name:name for name in regions}
def find(name):
    while parents[name]!=name:
        name=parents[name]
    return name
assert len(oracle['edges'])==8
for edge in oracle['edges']:
    a,b=edge['ends']
    parents[find(a)]=find(b)
components={frozenset(name for name in regions if find(name)==leader) for leader in map(find,regions)}
assert components=={frozenset(row['regions']) for row in oracle['components']}
assert components=={frozenset(row) for row in independent['local_components'].values()}
assert len(components)==6
registry={row['id']:row['target_layer'] for row in load('tech/derived.json')['derived_registry']}
direct=set()
for request in load('query/requests.json')['requests']:
    if request['capability']!='net_regions':
        continue
    paths.append(request['path'])
    lines=(root/request['path']).read_text().splitlines()
    count=0
    for i,line in enumerate(lines):
        if line!='p 1 4':
            continue
        layer=registry[lines[i-2]]
        points=[tuple(F(value,20) for value in point.split()) for point in lines[i+1:i+5]]
        ys,xs=zip(*points)
        box=(min(xs),min(ys),max(xs),max(ys))
        assert set(points)=={(box[y],box[x]) for y in (1,3) for x in (0,2)}
        candidates=[name for name,bounds in regions.items()
                    if bounds==box and shapes[name]['layer']==layer]
        assert len(candidates)==1
        direct.add(candidates[0]); count+=1
    assert count==len(request['record_ids'])
assert direct=={'G','MA','LN','LP','LY','MN','MP','MY'}
total=sum(area(box) for box in regions.values())
covered=sum(area(regions[name]) for name in direct)
assert (total,covered,total-covered)==(35090,3170,31920)
assert area(shapes['MARK']['bbox'])==25 and 'MARK' not in regions
body=[row for row in oracle['components'] if row['regions'] in (['BN'],['BP'])]
assert len(body)==2 and all(row['net'] is None for row in body)
cut=load('special/cut_islands/oracle.json')
assert cut['component_count']==3 and cut['edges']==[] and cut['shared_label']=='A'
assert [area(row['bbox_nm']) for row in cut['fragments']]==[36,36,40]
print(json.dumps({'status':'passed','python':sys.version,
  'head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
  'normal':{'targets':len(regions),'edges':8,'components':len(components),
            'direct_targets':sorted(direct),'unknown_direct':sorted(set(regions)-direct),
            'total_nm2':total,'direct_nm2':covered,'uncovered_nm2':total-covered,'marker_nm2':25},
  'cut_special':{'components':3,'edges':0,'shared_label':'A','areas_nm2':[36,36,40]},
  'scope':'independent local oracle/raw arithmetic; not product execution',
  'input_hashes':{name:sha256((root/name).read_bytes()).hexdigest() for name in paths}},indent=2))
