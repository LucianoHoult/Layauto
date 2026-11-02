"""Fixed W004 fixture dependencies/owners only, not a product config loader."""
import hashlib,json
from pathlib import Path

def read(path):
 def unique(pairs):
  d={}
  for k,v in pairs:
   assert k not in d,('duplicate key',k)
   d[k]=v
  return d
 return json.loads(Path(path).read_text(),object_pairs_hook=unique,parse_float=lambda s: (_ for _ in ()).throw(ValueError('float forbidden')))
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def load_tech(root):
 b=read(root/'tech.json'); result={k:v for k,v in b.items() if k!='owners'}; seen=set(result)
 for o in b['owners'].values():
  d=read(root/o['path']);assert set(d)==set(o['keys'])|{'schema_version'},('OwnerFieldMismatch',o)
  for k in o['keys']:
   assert k not in seen,('DuplicateTechOwner',k)
   seen.add(k);result[k]=d[k]
 assert result['cdl_dialect']['models_ref']=='physical.json#/models','ModelOwnerRef'
 assert result['coordinate_projection']['unit_contract_ref']=='formats.json#/unit_scale_contract','CoordinateUnitOwnerRef'
 registry={r['id']:r for r in result['derived_registry']}
 assert len(registry)==len(result['derived_registry'])
 for layer in result['layers']:
  for ref in layer['derived_layer_refs']:assert ref in registry and registry[ref]['target_layer']==layer['name'],'DerivedOwnerRef'
 for ref in result['required_operator_refs']:
  assert ref in result['operators'], 'RequiredBodyOperatorUnavailable' if ref=='body_context/2' else 'RequiredOperatorUnavailable'
 assert len({r['id'] for r in result['rules']})==len(result['rules'])
 assert result['mandatory_rule_policy']['all_listed_rules_required'] and not result['mandatory_rule_policy']['site_may_disable']
 return result

def dependencies(root):
 site=read(root/'site_config.yaml');b=read(root/site['tech_ref'])
 return sorted(set([*site['inputs'].values(),site['tech_ref'],* [o['path'] for o in b['owners'].values()],site['export_policy_ref'],site['validation_policy_ref'],site['limitation_ref'],'site_config.yaml','query/dialect.json','query/requests.json'])-{'query/header.json'})
def bind_header(root, template):
 import copy
 h=copy.deepcopy(template)
 for o in [h['layout'],h['source_netlist'],h['target'],*h['raw']]:o['sha256']=sha(root/o['uri'])
 h['closure']['entries']=[{'uri':n,'sha256':sha(root/n)} for n in dependencies(root) if (root/n).exists()]
 h['closure']['sha256']=hashlib.sha256(canonical(h['closure']['entries'])).hexdigest()
 return h

def bindings(root, allow_missing_context=False):
 h=read(root/'query/header.json'); assert h['top_identities']=={'layout':'INV_M1_SYNTH','source':'INV_M1_SYNTH'},'TopBindingMismatch'
 for o in [h['layout'],h['source_netlist'],h['target'],*h['closure']['entries'],*h['raw']]:
  assert (root/o['uri']).is_file(),('MissingDependency',o['uri'])
  assert sha(root/o['uri'])==o['sha256'], 'RawHashMismatch' if o in h['raw'] else ('DependencyHashMismatch',o['uri'])
 d=read(root/'query/dialect.json')['geometry']
 assert h['query_dialect_version']==read(root/'query/dialect.json')['id'],'DialectBindingMismatch'
 assert h['query_unit']=={'name':'micrometres/precision','metres_per_unit':{'numerator':'1','denominator':'1000000'},'geometry_precision':d['precision'],'axis_order':d['raw_axis_order']},'QueryUnitDeclarationConflict'
 expected=dependencies(root)
 if allow_missing_context:expected=[n for n in expected if n!='body/context.json']
 assert [x['uri'] for x in h['closure']['entries']]==expected,'ClosureIncomplete'
 assert hashlib.sha256(canonical(h['closure']['entries'])).hexdigest()==h['closure']['sha256']
 site=read(root/'site_config.yaml');ex=read(root/site['export_policy_ref'])
 assert ex['profile_id']==read(root/'tech.json')['profile_id'],'ExportProfileMismatch'
 assert site['outputs']['core']==[r['name'] for r in ex['required_artifacts']] and site['outputs']['directory']==ex['output_directory'],'ConflictingDuplicatePolicy'
 assert h['lvs_completion_status']==h['lvs_match_status']=='not_run' and h['assurance']=='synthetic'
 return h
