"""Named exact-boundary witnesses and actual captured policy rejections."""
import importlib.util
import json
import tempfile
import time
from fractions import Fraction
from pathlib import Path
path=Path(__file__).with_name('geometry-probe.py')
spec=importlib.util.spec_from_file_location('independent_geometry',path)
g=importlib.util.module_from_spec(spec); spec.loader.exec_module(g)
from w009_cases import change_owner
start=time.monotonic(); results=[]
for label,a,b,want in (
 ('positive_area',((0,0,10,10),),((5,5,15,15),),True),
 ('whole_edge',((0,0,10,10),),((10,0,20,10),),True),
 ('partial_edge',((0,0,10,10),),((10,4,20,6),),True),
 ('corner',((0,0,10,10),),((10,10,20,20),),False),
 ('gap',((0,0,10,10),),((11,0,20,10),),False),
 ('hole_no_contact',((0,0,3,10),(3,0,7,3),(3,7,7,10),(7,0,10,10)),((4,4,6,6),),False),
 ('hole_boundary_contact',((0,0,3,10),(3,0,7,3),(3,7,7,10),(7,0,10,10)),((3,4,6,6),),True),
 ('multi_pair_one_boolean',((0,0,3,10),(3,0,7,3),(3,7,7,10),(7,0,10,10)),((2,2,8,8),),True),
):
 assert g.contact(g.squares(a),g.squares(b))==want
 assert g.same_layer_contact(tuple(g.Rect(*r) for r in a),tuple(g.Rect(*r) for r in b))==want
 results.append({'case':label,'expected_contact':want})
for label,cover,target,margin,want in (
 ('threshold_equal',((0,0,10,10),),(1,1,9,9),Fraction(1),True),
 ('threshold_short_by_one_third',((0,0,10,10),),(1,1,9,9),Fraction(4,3),False),
 ('rational_below_threshold',((0,0,10,10),),(1,1,9,9),Fraction(2,3),True),
 ('across_pieces',((0,0,5,10),(5,0,10,10)),(1,1,9,9),Fraction(1),True),
 ('hole_fake_bbox',((0,0,4,10),(4,0,6,4),(4,6,6,10),(6,0,10,10)),(1,1,9,9),Fraction(1),False),
 ('hole_boundary_equal',((0,0,4,10),(4,0,6,4),(4,6,6,10),(6,0,10,10)),(1,1,3,3),Fraction(1),True),
 ('hole_fractional_intrusion',((0,0,4,10),(4,0,6,4),(4,6,6,10),(6,0,10,10)),(1,1,3,3),Fraction(4,3),False),
):
 assert g.enclosure(cover,target,margin)==want
 assert g.encloses_connector(tuple(g.Rect(*r) for r in cover),g.Rect(*target),margin)==want
 results.append({'case':label,'expected_enclosure':want,'margin':str(margin)})
print(json.dumps({'named_math':results}),flush=True)
with tempfile.TemporaryDirectory(prefix='w010-policy-geometry-',dir='/tmp') as temp:
 for layer,field,value in (
  ('VIA0','electrical_connects',['OD','M1']),
  ('CONTACT','contact_predicate','bbox_touch'),
  ('GCONTACT','role','via'),
 ):
  p=g.ready_copy(Path(temp)/(layer+'-'+field))
  def mutate(owner): next(r for r in owner['layers'] if r['name']==layer)[field]=value
  change_owner(p,'drawn',mutate)
  parsed=g.read_inputs(p/'site_config.yaml'); assert parsed.status=='success',parsed.issues
  geometry=g.build_geometry(g.geometry_from_parse_result(parsed)); assert geometry.status=='success',geometry.issues
  effective=g.build_effective_geometry(geometry); assert effective.status=='success',effective.issues
  local=g.build_local_connectivity(effective)
  assert local.status=='error' and local.value is None
  assert len(local.issues)==1 and local.issues[0].code=='UnsupportedLocalContactOperator'
  assert local.issues[0].source.uri=='tech/drawn.json'
  assert local.input is effective and local.completed==effective.completed
  row={'case':layer+'-'+field,'code':local.issues[0].code,'source':local.issues[0].source.uri,'field':local.issues[0].source.field}
  results.append(row); print(json.dumps(row),flush=True)
summary={'status':'passed','cases':results,'elapsed_seconds':time.monotonic()-start}
Path(__file__).with_name('geometry-boundary-result.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({'status':'passed','elapsed_seconds':summary['elapsed_seconds']}),flush=True)
