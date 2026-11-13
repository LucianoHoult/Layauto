"""Check preserved independent before/after outputs without rerunning product code."""
import json
from pathlib import Path
P=Path(__file__).resolve().parent

def read(name):
 s=(P/name).read_text()
 return json.loads(s[s.index('{'):])

def case(report,name):return next(row for row in report['cases'] if row['case']==name)
def path(row,name):return next(p for p in row['paths'] if p['device']==name)
def terminal(row,name):return next(p for p in row['terminals'] if p['device']==name)

before=read('body_scope_probe.first.stdout.txt')
after=read('body_scope_probe.after.stdout.txt')
assert path(case(before,'mn_wrong_body_only'),'MP0')['observed']==[]
assert path(case(after,'mn_wrong_body_only'),'MP0')['observed']==['VDD']
for name in ('raw_uri_selects_source_cdl','global_wrong_top'):
 assert all(p['rule']=='satisfied' and p['chain']=='indeterminate' for p in case(before,name)['paths'])
 assert all(p['rule']=='indeterminate' and p['chain']=='indeterminate' for p in case(after,name)['paths'])
assert case(after,'unknown_lvs')['coverage_lvs']==case(after,'unknown_lvs')['body_lvs']=='unknown'
old=read('body_conflict_frame_probe.before-r2.stdout.txt')
new=read('body_conflict_frame_probe.after.stdout.txt')
name='full_VSS_with_partial_VDD'
assert terminal(case(old,name),'MN0')['status']=='equal'
assert terminal(case(new,name),'MN0')['status']=='conflict'
assert set(path(case(new,name),'MN0')['observed'])=={'VDD','VSS'}
name='continuation_at_minus10_frame_at_zero'
assert not case(old,name)['issues'] and terminal(case(old,name),'MN0')['status']=='equal'
assert 'BodyContinuationMismatch' in case(new,name)['issues']
assert terminal(case(new,name),'MN0')['status']=='indeterminate'
assert terminal(case(new,name),'MP0')['status']=='equal'
assert all(row['rejected'] for row in read('leaf_storage_probe.after-r2.stdout.json')['results'])
assert all(row['rejected'] for row in read('map_storage_probe.after-r2.stdout.json')['results'])
assert all(row['accepted'] for row in read('readback_default_storage_probe.after.stdout.json')['results'])
assert read('foreign_root_probe.before.stdout.json')['error_type']=='TypeError'
assert read('foreign_root_probe.after.stdout.json')['error_type']=='ValueError'
print(json.dumps({'finding_implementation_repairs':'CR01-CR09','preserved_before_after_checks':'passed'}))
