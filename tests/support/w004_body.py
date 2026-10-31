"""Exact integer checks of the declared fixture-only external body domain."""
from w004_support import read,sha

def overlap(a,b):return min(a[2],b[2])>max(a[0],b[0]) and min(a[3],b[3])>max(a[1],b[1])
def edge(a,b):
 if a[2]==b[0] or b[2]==a[0]:return max(0,min(a[3],b[3])-max(a[1],b[1]))
 if a[3]==b[1] or b[3]==a[1]:return max(0,min(a[2],b[2])-max(a[0],b[0]))
 return 0
def margins(a,b):return [b[0]-a[0],b[1]-a[1],a[2]-b[2],a[3]-b[3]]
def check_body(root,shapes,tech,semantic):
 assert 'body_context/2' in tech['operators'],'RequiredBodyOperatorUnavailable'
 assert (root/'body/context.json').is_file(),'RequiredBodyContextUnavailable'
 c=read(root/'body/context.json');assert c['source_gds']=={'uri':'source.gds','sha256':sha(root/'source.gds')},'BodySourceBindingMismatch'
 assert c['top']==semantic['cell'] and c['frame_id']=='FRAME' and c['frame_bbox_nm']==shapes['FRAME']['bbox'],'BodyObjectBindingMismatch'
 assert c['profile_ref']==tech['body_context_profile']['id'] and c['operator_ref']=='body_context/2','BodyProfileMismatch'
 assert c['read_only'] and c['exported'] is False and c['production_matched_body_evidence'] is False and c['lvs_status']=='not_run'
 assert c['unit']=={'name':'nm','metres_per_tick':{'numerator':'1','denominator':'1000000000'}},'BodyUnitMismatch'
 for b in c['local_bindings']:assert shapes[b['id']]==b,'BodyObjectBindingMismatch'
 assert {b['id'] for b in c['local_bindings']}=={'FRAME','BN','BP','MN','MP'},'BodyObjectBindingMismatch'
 ext={x['id']:x for x in c['shapes']};assert len(ext)==len(c['shapes']),'BodyDuplicateIdentity'
 assert all(all(type(v) is int for v in s['bbox']) and s['bbox'][0]<s['bbox'][2]<=shapes['FRAME']['bbox'][0] and s['bbox'][1]<s['bbox'][3] for s in ext.values()),'BodyContextScope'
 for n in [s for s in ext.values() if s['layer']=='BODY_N']:
  for p in [s for s in ext.values() if s['layer']=='BODY_P']:assert not overlap(n['bbox'],p['bbox']),'BodyOppositeTypeOverlap'
 rules={x['id']:x for x in tech['rules']};out=[]
 assert len(c['associations'])==len(semantic['devices']) and {a['device'] for a in c['associations']}=={d['id'] for d in semantic['devices']},'BodyAssociationCardinality'
 for a in c['associations']:
  dev=next(d for d in semantic['devices'] if d['id']==a['device']);bt,tt=tech['body_context_profile']['types'][dev['model']]
  body=shapes[a['local_body']];eb=ext[a['external_body']];tap=ext[a['tap']];er=ext[a['external_rail']];rail=shapes[a['local_rail']]
  assert body['layer']==eb['layer']==bt and tap['layer']==tt and er['layer']==rail['layer']=='M1','BodyTypeMismatch'
  bmatches=[s['id'] for s in ext.values() if s['layer']==bt and edge(body['bbox'],s['bbox'])>0]
  assert bmatches,'BodyContinuationMismatch';assert bmatches==[eb['id']],'BodyUniqueMatchFailure'
  rmatches=[s['id'] for s in shapes.values() if s['layer']=='M1' and edge(s['bbox'],er['bbox'])>0]
  assert rmatches,'BodyContinuationMismatch';assert rmatches==[rail['id']],'BodyUniqueMatchFailure'
  for layer,chosen in [(bt,eb['id']),('M1',er['id'])]:
   matches=[s['id'] for s in ext.values() if s['layer']==layer and overlap(s['bbox'],tap['bbox'])]
   assert matches==[chosen],'BodyUniqueMatchFailure'
  bm=min(margins(eb['bbox'],tap['bbox']));rm=min(margins(er['bbox'],tap['bbox']))
  assert min(bm,rm)>=rules['T05.contact_enclosure']['parameters']['enclosure_nm'],'BodyTapEnclosureFailure'
  # Rail semantic identity is joined only after the physical continuation, via
  # actual raw net annotation on that local exact rail, never a name-made edge.
  from w004_query import normalize
  def val(r):return [int(r['bbox_nm'][k]['numerator'])//int(r['bbox_nm'][k]['denominator']) for k in ['x_min','y_min','x_max','y_max']]
  matched=[r['schematic_name'] for r in normalize(root,'net_regions')['records'] if r['derived_layer']=='toy_m1' and val(r)==rail['bbox']]
  assert len(matched)==1 and matched[0]==dev['terminals']['B']==a['expected_semantic_rail'],'BodyTargetRailMismatch'
  out.append({'device':dev['id'],'local_body':body['id'],'local_rail':rail['id'],'semantic_rail':matched[0],'body_edge_length_nm':edge(body['bbox'],eb['bbox']),'rail_edge_length_nm':edge(rail['bbox'],er['bbox']),'tap_body_enclosure_nm':bm,'tap_rail_enclosure_nm':rm,'local_graph_union':False})
 return out
