"""PM independent lightweight evidence audit. No repo writes or heavy paths."""
from __future__ import annotations

import ast
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile

ROOT = Path('/workspace/Layauto')
W = ROOT / 'docs/tasks/W012'
OUT = Path('/workspace/work/w012-pm-check/evidence')
BASE = 'f3698b7ffda3b0737a2eb61ca85dbf3b40bc89fe'
HEAD = '5085f994f0bd4b0c39f7ac1ccdbcacc43d281720'
checks = []
derived = {}


def read(path):
    return json.loads(path.read_text())


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(path):
    return sha(path.read_bytes())


def check(condition, label):
    assert condition, label
    checks.append(label)


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def blob_map(ref, names):
    specs = [f'{ref}:{n}' for n in names]
    raw = git('cat-file', '--batch') if not specs else subprocess.check_output(
        ['git','cat-file','--batch'], cwd=ROOT, input=('\n'.join(specs)+'\n').encode())
    result, pos = {}, 0
    for name in names:
        end = raw.index(b'\n',pos)
        header = raw[pos:end].split()
        assert header[1] == b'blob', (ref,name,header)
        size = int(header[2]); start = end+1
        result[name] = sha(raw[start:start+size]); pos = start+size+1
    assert pos == len(raw)
    return result


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def qualifier(row):
    path = Path(row['file'])
    if not path.is_file() or not str(path).startswith(str(ROOT/'layauto_v2')):
        return row['function']
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ClassDef):
            for method in node.body:
                if isinstance(method, ast.FunctionDef) and method.lineno == row['line']:
                    return node.name+'.'+method.name
    return row['function']


def main():
    check(git('rev-parse','HEAD').decode().strip() == HEAD, 'delivery HEAD identity')
    check(not git('status','--porcelain').strip(), 'clean repository before audit')
    changed = git('diff','--name-only',BASE,HEAD).decode().splitlines()
    check(all(p.startswith('docs/tasks/W012/') or p == 'docs/tasks/W012-capture-wire-performance.md' for p in changed), 'authorized investigation paths only')
    manifest = read(ROOT/'docs/tasks/W011/verification/source-manifest.json')
    files = manifest['files']
    check(len(files)==262 and len(manifest['runtime_files'])==100, '262 sources / 100 runtime manifest')
    check({'layauto_v2/'+n:d for n,d in manifest['runtime_files'].items()}=={n:d for n,d in files.items() if n.startswith('layauto_v2/')}, 'runtime identity covers exactly 100 layauto_v2 sources')
    for name, expected in files.items():
        check(digest(ROOT/name)==expected, 'current source SHA256 '+name)
    for ref in [manifest['git_head'],'0a3326aa363477724465886cd05874d0997fba3e',BASE,HEAD]:
        check(blob_map(ref,list(files))==files, '262 exact source hashes at '+ref)
    snapshot = ROOT/'docs/tasks/W011/verification/source-snapshot.tar.gz'
    with tarfile.open(snapshot) as archive:
        for name,expected in files.items():
            check(sha(archive.extractfile(name).read())==expected, 'snapshot source '+name)
    preflight = read(W/'preflight.json')
    check(preflight['files']==files and preflight['source_count']==262 and preflight['runtime_count']==100, 'preflight same source identity')
    check(preflight['snapshot_sha256']==digest(snapshot), 'preflight snapshot SHA256')
    check(preflight['source_manifest_sha256']==digest(ROOT/'docs/tasks/W011/verification/source-manifest.json'), 'preflight source manifest SHA256')
    for row in preflight['inputs']:
        check(digest(Path(row['origin']))==row['sha256'], 'fixed mismatch origin '+row['origin'])
        check(Path(row['origin']).stat().st_size==row['bytes'], 'fixed mismatch origin length '+row['origin'])
    check(len(preflight['inputs'])==35, 'fixed mismatch 35 input origins')
    derived['current_overlay_paths_present'] = sum(Path(r['target']).exists() for r in preflight['inputs'])
    delivery = read(W/'delivery-manifest.json')
    for name,expected in delivery['files'].items():
        check(digest(ROOT/name)==expected, 'delivery manifest '+name)
    reviewed = read(W/'review-evidence/reviewed-manifest.json')
    check(blob_map(reviewed['head'],list(reviewed['files']))==reviewed['files'], 'reviewed manifest matches exact reviewed Git snapshot')
    post_review = git('diff','--name-only',reviewed['head'],HEAD).decode().splitlines()
    derived['post_review_paths'] = post_review
    check(all(p in ['docs/tasks/W012-capture-wire-performance.md','docs/tasks/W012/independent-review.md','docs/tasks/W012/validation.json','docs/tasks/W012/validation.stdout.txt','docs/tasks/W012/delivery.md','docs/tasks/W012/delivery-manifest.json'] or p.startswith('docs/tasks/W012/review-evidence/') for p in post_review), 'post-review documentation and independent check additions only')
    history = ROOT/'docs/tasks/W011/verification'
    old = read(history/'receipt.json')
    check(old['actual_test_counts']=={'310':1605,'312':1605}, 'historical dual 1605 receipt')
    check(len(old['commands'])==21, 'historical 21 command receipt')
    for row in old['commands']:
        check(row['exit_code']==0, 'historical exit0 '+row['stdout'])
        for stream in ['stdout','stderr']:
            check(digest(history/row[stream])==row[stream+'_sha256'], 'historical raw '+row[stream])
    for name,expected in read(history/'evidence-manifest.json').items():
        check(digest(history/name)==expected, 'historical evidence manifest '+name)
    check(all('1605 passed' in (history/f'pytest-{v}.stdout.txt').read_text() for v in ['310','312']), 'historical raw pytest dual 1605 passed')
    check(all('54 source files' in (history/f'typing-{v}.stdout.txt').read_text() for v in ['310','312']), 'historical raw typing dual 54')
    tools = read(W/'tool-identity.json')
    for name,expected in tools.items():
        check(digest(W/name)==expected, 'frozen measurement tool '+name)
        check(blob_map('cfaf85e195fcbedb99fbd26b19787afb0577862d',[f'docs/tasks/W012/{name}'])[f'docs/tasks/W012/{name}']==expected, 'tool frozen before measurements '+name)
    check(read(W/'selfcheck.json')['tool_sha256']==digest(W/'probe.py'), 'original lightweight selfcheck identity')
    receipt = read(W/'measurement-receipt.json')
    commands = receipt['commands']
    check(len(commands)==6 and receipt['serial'] and receipt['fresh_process_per_path_per_mode'], 'six serial fresh declared paths')
    check(commands==read(W/'commands.json'), 'commands and receipt identical')
    previous = None
    check(datetime.fromisoformat(preflight['utc']) <= datetime.fromisoformat(commands[0]['started_at_utc']), 'preflight precedes first heavy command')
    for row in commands:
        start,finish = map(datetime.fromisoformat,[row['started_at_utc'],row['finished_at_utc']])
        check(previous is None or previous <= start, 'serial chronology '+row['argv'][-1])
        previous = finish
        check(row['exit_code']==0 and row['tools']==tools, 'command exit0 frozen tools '+row['argv'][-1])
        output = Path(row['argv'][-1]); prefix = output.with_suffix('')
        check(read(prefix.with_suffix('.command.json'))==row, 'per-path command equals receipt '+prefix.name)
        for stream in ['stdout','stderr']:
            check(digest(prefix.with_suffix('.'+stream+'.txt'))==row[stream+'_sha256'], 'raw stream '+prefix.name+' '+stream)
        data = read(output)
        check(start <= datetime.fromisoformat(data['started_at_utc']) <= datetime.fromisoformat(data['finished_at_utc']) <= finish, 'result chronology within command '+prefix.name)
        check(data['source_identity']['files']==files and data['tool_sha256']==tools['probe.py'], 'measured source and tool '+prefix.name)
        check(all(data[k]==preflight[k] for k in ['python','executable','platform']), 'same frozen environment in measured path '+prefix.name)
        check(data['public_roundtrip_equal'] and data['gc_enabled'] and data['gc_threshold']==[700,10,10], 'complete public roundtrip and GC '+prefix.name)
        stdout = prefix.with_suffix('.stdout.txt').read_text()
        raw = json.loads(stdout.strip().splitlines()[-1])
        check(all(raw[k]==data[k] for k in raw), 'raw stdout receipt matches '+prefix.name)
        for phase,seconds in data['wall_seconds'].items():
            check('DONE '+phase+' '+str(seconds) in stdout, 'raw measured stage '+prefix.name+' '+phase)
        check(len(data['capture_sources'])==31 and sum(s['bytes'] for s in data['capture_sources'])==280706, '31 captures / 280706 bytes '+prefix.name)
        info=data['result']; mismatch=data['case']=='extraction-mismatch'
        check(info['counts']=={'MN0':4 if mismatch else 5,'MP0':7}, '5/7 or mismatch 4/7 '+prefix.name)
        check(info['difference_count']==int(mismatch) and info['complete_evaluations']==36 and info['T05_status']=='pass' and info['local_edges']==8 and info['local_components']==6 and info['body_kind']=='body', 'full evaluated local/T05/body result '+prefix.name)
        check(data['readback_unsealed_checkpoint_unchanged_no_terminal']==(data['case']=='normal-readback'), 'readback invariant '+prefix.name)
        if mismatch:
            origin_by_target = {r['target']:r for r in preflight['inputs']}
            site_dir=Path(data['input_site']).parent
            check(all(str(site_dir/s['uri']) in origin_by_target and all(s[k]==origin_by_target[str(site_dir/s['uri'])][k] for k in ['sha256','bytes']) for s in data['capture_sources']), 'mismatch captures match reconstructable fixed overlay '+prefix.name)
        else:
            site_dir=Path(data['input_site']).parent
            check(all(digest(site_dir/s['uri'])==s['sha256'] and (site_dir/s['uri']).stat().st_size==s['bytes'] for s in data['capture_sources']), 'normal captures match actual repository inputs '+prefix.name)
    summary=read(W/'cost-summary.json')
    for i,case in enumerate(['normal-direct','normal-readback','extraction-mismatch']):
        b=read(W/f'baseline-{case}.json'); p=read(W/f'profile-{case}.json'); stages=read(W/f'profile-{case}.profile.json')
        check(all(b[k]==p[k] for k in ['wire_bytes','wire_sha256','capture_sources','input_site','result']), 'baseline/profile identical full wire/captures/results '+case)
        outer=stages['W011_result_encode']['wire']['bytes_to_hex']['normalization.channel_identity_codec.encode_record:ChannelIdentityResult']
        check(outer['calls']==[222,222,217][i] and outer['hex_characters']==2*outer['payload_bytes'], 'outer hex calls and length '+case)
        check(summary[case]['outer_hex_characters']==outer['hex_characters'] and summary[case]['outer_hex_fraction']==outer['hex_characters']/b['wire_bytes'], 'derived outer hex fraction '+case)
        total_exclusive=sum(r['exclusive_seconds'] for stage in stages.values() for r in stage['functions'])
        codec_exclusive=sum(r['exclusive_seconds'] for stage in stages.values() for r in stage['functions'] if r['file']==str(ROOT/'layauto_v2/domain/codec.py'))
        row={'baseline_total_seconds':sum(b['wall_seconds'].values()),'wire_bytes':b['wire_bytes'],'wire_sha256':b['wire_sha256'],'peak_rss_kib':b['process_peak_rss_kib'],'outer_hex_calls':outer['calls'],'outer_hex_characters':outer['hex_characters'],'outer_hex_percentage':100*outer['hex_characters']/b['wire_bytes'],'all_stages_codec_disjoint_exclusive_pct':100*codec_exclusive/total_exclusive,'result_bytes':{k:p['result_graph'][k] for k in ['unique_bytes_payload','content_unique_bytes_payload','logical_path_bytes_payload','equal_content_independent_bytes_extra']},'decoded_bytes':p['decoded_result_graph']['unique_bytes_payload']}
        phase_result={}
        for phase in ['W011_build','W011_result_decode']:
            funcs=stages[phase]['functions']; auth=[r for r in funcs if r['file']==str(ROOT/'layauto_v2/normalization/channel_identity.py') and r['function']=='_require_input']
            check(len(auth)==1 and auth[0]['calls']==(2 if phase=='W011_build' else 1), 'W011 actual auth count '+phase+' '+case)
            auth10=[r for r in funcs if r['file']==str(ROOT/'layauto_v2/normalization/local_connectivity.py') and r['function']=='_require_input']
            check(len(auth10)==1 and auth10[0]['calls']==2, 'W010 nested actual auth count '+phase+' '+case)
            constructors={qualifier(r):r['calls'] for r in funcs if r['function']=='__post_init__' and r['file'].startswith(str(ROOT/'layauto_v2'))}
            if phase=='W011_build':
                for name,calls in {'ChannelIdentityResult.__post_init__':1,'LocalConnectivityResult.__post_init__':2,'EffectiveGeometryResult.__post_init__':4,'GeometryResult.__post_init__':4,'ChannelIdentityDraft.__post_init__':3}.items():
                    check(constructors.get(name)==calls, 'actual constructor count '+name+' '+case)
            phase_result[phase]={'W011_auth':auth[0],'W010_auth':auth10[0],'codec_disjoint_exclusive_seconds':sum(r['exclusive_seconds'] for r in funcs if r['file']==str(ROOT/'layauto_v2/domain/codec.py')),'all_functions_exclusive_seconds':sum(r['exclusive_seconds'] for r in funcs),'constructors':constructors}
        row['profile_selected']=phase_result; derived[case]=row
    extra=read(W/'memory-profile.command.json'); mem=read(W/'memory-profile-normal-readback.json'); events=read(W/'memory-profile-events.json'); baseline=read(W/'baseline-normal-readback.json')
    check(datetime.fromisoformat(extra['started_at_utc'])>=previous and extra['exit_code']==0, 'memory diagnostic serial after six exit0')
    check(extra['tool_sha256']==digest(W/'memory_probe.py') and extra['original_probe_sha256']==tools['probe.py'] and extra['selfcheck_sha256']==digest(W/'memory-probe-selfcheck.json'), 'memory tool original-probe and selfcheck identity')
    check(read(W/'memory-probe-selfcheck.json')['tool_sha256']==digest(W/'memory_probe.py'), 'memory selfcheck exact observer identity')
    for stream in ['stdout','stderr']:
        check(extra[stream+'_sha256']==digest(W/f'memory-profile.{stream}.txt'), 'memory raw '+stream)
    check(all(mem[k]==baseline[k] for k in ['wire_bytes','wire_sha256','capture_sources','result','input_site','readback_unsealed_checkpoint_unchanged_no_terminal']), 'memory diagnostic same complete readback facts and wire')
    refresh=[i for i,e in enumerate(events) if e['after']['ru_maxrss_kib']>e['before']['ru_maxrss_kib']]
    check(len(events)==65 and len(refresh)==5, '65 existing hex windows / five HWM refreshes')
    check(all(e['caller']==str(ROOT/'layauto_v2/domain/codec.py') and e['caller_function']=='_decode' and e['hex_characters']>=1000000 for e in events), 'memory observed existing decoder calls only')
    check(events[34]['hex_characters']==118841892 and events[34]['after']['ru_maxrss_kib']==mem['process_peak_rss_kib']==7319108 and events[34]['after']['VmRSS']=='355960 kB', 'event34 reaches final HWM and returns low RSS')
    derived['memory']={'refresh_indices':refresh,'event34':events[34],'final_peak_rss_kib':mem['process_peak_rss_kib']}
    sys.path.insert(0,str(ROOT))
    probe=load_module('w012_pm_probe',W/'probe.py')
    shared=bytes(bytearray(b'abc')); equal=bytes(bytearray(b'abc')); graph=probe.census((shared,shared,equal))
    check(shared is not equal and graph['unique_bytes_payload']==6 and graph['content_unique_bytes_payload']==3 and graph['logical_path_bytes_payload']==9, 'independent tiny census shared / equal / logical accounting')
    from layauto_v2.domain import publication_codec
    from layauto_v2.domain.evidence import SourceRef
    value=SourceRef('pm-check','a'*64); plain=publication_codec.encode_record(value)
    original_encode=publication_codec.encode_record
    with probe.WireMeter().active() as meter:
        encoded=publication_codec.encode_record(value)
        check(encoded==plain and publication_codec.decode_record(encoded)==value, 'tiny transparent WireMeter complete source-ref roundtrip')
    check(publication_codec.encode_record is original_encode and not meter.stack, 'WireMeter hook restored')
    observer=load_module('w012_pm_memory',W/'memory_probe.py')
    observer_events=[]
    seen=[]
    def original(pattern,string,flags=0):
        seen.append((pattern,string,flags));return 'original-result'
    class ForeignPattern:
        def __ne__(self,other): raise AssertionError('foreign pattern comparison introduced')
    foreign=ForeignPattern()
    check(observer.observer(original,observer_events,minimum=1)(foreign,'ab',8)=='original-result' and not observer_events and seen[-1]==(foreign,'ab',8), 'foreign pattern bypass preserves original call without comparison')
    match=observer.observer(re.fullmatch,observer_events,minimum=1)
    check(match(r'(?:[0-9a-f]{2})*','ab01').group()=='ab01' and match(r'(?:[0-9a-f]{2})*','ABC') is None, 'memory observer valid / invalid hex unchanged')
    failure=TypeError('PM observer original failure');cause=RuntimeError('cause');context=LookupError('context')
    failure.__cause__=cause;failure.__context__=context;failure.__suppress_context__=True
    def fail(*args,**kwargs): raise failure
    try: observer.observer(fail,observer_events,minimum=1)(r'(?:[0-9a-f]{2})*','ab')
    except TypeError as raised:
        check(raised is failure and raised.__cause__ is cause and raised.__context__ is context and raised.__suppress_context__, 'observer original exception identity / cause / context / suppression')
    else: raise AssertionError('observer swallowed failure')
    finding=(W/'review-evidence/attempt01-stderr.txt').read_text()
    check('AssertionError: actual outer hex accounting: extraction-mismatch' in finding, 'R01 original failure retained')
    diff=git('diff','27280c4ef243a96578b78e9794ff52407be86eff^','27280c4ef243a96578b78e9794ff52407be86eff','--','docs/tasks/W012/cost-analysis.md').decode()
    check('222 / 222 / 217' in diff and len(git('diff','--name-only','27280c4ef243a96578b78e9794ff52407be86eff^','27280c4ef243a96578b78e9794ff52407be86eff').decode().splitlines())==1, 'R01 single-document correction exact Git diff')
    check('剩余 0' in (W/'independent-review.md').read_text(), 'R01 reviewer closure recorded')
    check(not git('status','--porcelain').strip(), 'repository still unchanged after audit')
    result={'status':'passed','utc':datetime.now(timezone.utc).isoformat(),'head':HEAD,'base':BASE,'script_sha256':digest(Path(__file__)),'check_count':len(checks),'checks':checks,'derived':derived,'findings':[],'not_run':['heavy baseline/profile/memory-profile','product regression or dual interpreter matrix','typing/build/install','wire regeneration; huge wire bytes not retained in Git'],'adopted_history':'W011 dual1605, typing54, build/dual install only after exact 262-source/100-runtime identity and raw evidence hashes; W012 measurements are historical outputs independently recomputed, not new timing samples.'}
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(f'{len(checks)} independent lightweight evidence checks passed; required findings 0; no repository changes')


if __name__=='__main__':
    main()
