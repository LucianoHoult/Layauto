"""Small independent checks of the delivered diagnostic observer; no profiling."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import sys

ROOT=Path('/workspace/Layauto')
OUT=Path('/workspace/work/w012-pm-check')
checks=[]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module
observer_module=load('w012_delivered_memory',ROOT/'docs/tasks/W012/memory_probe.py')
# Avoid resource observations in this transparency test; returned values are
# deterministic sentinels. The original production matcher is never replaced.
observer_module.memory=lambda:{'VmRSS':'sentinel','ru_maxrss_kib':1}
events=[]
observed=observer_module.observer(re.fullmatch,events,minimum=1)
for value in ('ab01','ABC','a','00','f0','\uFF10\uFF10','aa\n',' '):
    plain=re.fullmatch(r'(?:[0-9a-f]{2})*',value)
    wrapped=observed(r'(?:[0-9a-f]{2})*',value)
    assert (plain is None)==(wrapped is None)
    if plain is not None:assert plain.group()==wrapped.group()
    checks.append('matcher transparency '+repr(value))
class Foreign:
    def __ne__(self,other):raise AssertionError('observer compared foreign pattern')
marker=object();calls=[]
def original(*args):calls.append(args);return marker
foreign=Foreign();events2=[]
assert observer_module.observer(original,events2,minimum=1)(foreign,'ab') is marker
assert calls==[(foreign,'ab',0)] and not events2
checks.append('foreign pattern delegated without extra comparison')
for kind in (TypeError,KeyError,KeyboardInterrupt,SystemExit):
    for suppressed in (False,True):
        error=kind('original failure');cause=RuntimeError('cause');context=LookupError('context')
        error.__cause__=cause;error.__context__=context;error.__suppress_context__=suppressed
        def broken(*args):raise error
        try:observer_module.observer(broken,[],minimum=1)(r'(?:[0-9a-f]{2})*','ab')
        except BaseException as caught:
            assert caught is error and caught.__cause__ is cause and caught.__context__ is context
            assert caught.__suppress_context__ is suppressed
        else:raise AssertionError('original failure lost')
        checks.append('exception history '+kind.__name__+' suppression='+str(suppressed))
probe=load('w012_delivered_probe',ROOT/'docs/tasks/W012/probe.py')
probe.OUT=OUT/'original-selfcheck'
probe.OUT.mkdir(exist_ok=True)
probe.selfcheck()
assert json.loads((probe.OUT/'selfcheck.json').read_text())['status']=='passed'
checks.append('delivered probe lightweight selfcheck with output redirected')
result={'status':'passed','checks':checks,'count':len(checks),
        'scope':'Diagnostic/tool transparency only; no heavy product capture, full baseline/profile, or candidate optimization',
        'tool_hashes':{name:hashlib.sha256((ROOT/'docs/tasks/W012'/name).read_bytes()).hexdigest()
                       for name in ('probe.py','memory_probe.py')}}
(OUT/'observer-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':'passed','count':len(checks)}))
