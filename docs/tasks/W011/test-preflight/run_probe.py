import hashlib,json,pathlib,subprocess,sys,time,os,resource
root=pathlib.Path('/workspace/work/w011-tests');out=pathlib.Path('/workspace/work/w011-tests-evidence')
label=sys.argv[1]
cmd=['/workspace/work/w011-engineering/dev312/bin/python','-B','-m','pytest','-p','no:cacheprovider',*sys.argv[2:],'-q']
paths=[*root.glob('layauto_v2/*/channel_identity*.py'),root/'layauto_v2/derive/fin_count.py',root/'layauto_v2/domain/source_location.py',root/'layauto_v2/normalization/codec.py',root/'layauto_v2/normalization/component.py',*root.glob('tests/contracts/*w011*.py')]
manifest={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
start=time.time(); identity={'cwd':str(root),'argv':cmd,'files':manifest,'git_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'git_tree':subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=root,text=True).strip(),'git_status':subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True),'python':sys.version,'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(start))}
(out/(label+'.input.json')).write_text(json.dumps(identity,indent=2)+'\n')
with (out/(label+'.stdout.txt')).open('wb') as stdout,(out/(label+'.stderr.txt')).open('wb') as stderr:
 p=subprocess.run(cmd,cwd=root,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),stdout=stdout,stderr=stderr)
identity.update(exit_code=p.returncode,elapsed_seconds=time.time()-start,max_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
identity['outputs']={suffix:hashlib.sha256((out/(label+suffix)).read_bytes()).hexdigest() for suffix in ('.stdout.txt','.stderr.txt')}
(out/(label+'.result.json')).write_text(json.dumps(identity,indent=2)+'\n')
print(json.dumps({'label':label,'exit_code':p.returncode,'elapsed_seconds':identity['elapsed_seconds']}),flush=True)
sys.exit(p.returncode)
