"""Serial public API resource probe; timed and counted runs are separate.

Run from repository root with PYTHONPATH=tests/support:. Each case is a fresh
process. No expected answers enter the product. JSON report is fully encoded.
"""
from collections import Counter
import argparse
from dataclasses import fields
import hashlib
import importlib.metadata
import json
from pathlib import Path
import resource
import sys
import time

from analysis_inputs import materialize
import layauto_v2.analysis as facade
import layauto_v2.normalization.analysis as normalization
from layauto_v2.analysis import AnalysisRequest


def main():
    cli=argparse.ArgumentParser();cli.add_argument('--case',choices=['no_body','body','mismatch'],required=True)
    cli.add_argument('--root',type=Path,required=True);cli.add_argument('--counted',action='store_true');args=cli.parse_args()
    if not (args.root/'analysis.json').exists():
        materialize(args.root,body=args.case=='body',case='extraction_mismatch' if args.case=='mismatch' else 'normal')
    timers=Counter();counts=Counter()
    def wrap(module,name,label):
        original=getattr(module,name)
        def measured(*a,**kw):
            start=time.monotonic()
            try:return original(*a,**kw)
            finally:timers[label]+=time.monotonic()-start
        setattr(module,name,measured)
    for module,names in ((facade,('acquire_analysis','acquire_selections','LocalAnalysisReceipt','analyze_local','selected_analysis','analyze_terminals','diagnostic_json')),
                         (normalization,('build_source_operands','join_source_operands','build_layout','build_partition','build_occupancy','build_effective_draft','build_local_connectivity_draft','build_channel_identity_draft','build_annotation_operands','evaluate_body_operands','terminal_operands'))):
        for name in names:wrap(module,name,name)
    def profile(frame,event,arg):
        if event=='call' and '/layauto_v2/' in frame.f_code.co_filename:
            name=frame.f_code.co_name
            if name=='__post_init__' or name in ('parse_gds','parse_cdl','parse_query','build_layout','build_partition','build_occupancy','build_effective_draft','build_local_connectivity_draft','build_channel_identity_draft','build_annotation_operands','evaluate_body_operands','terminal_operands'):
                counts[frame.f_code.co_filename.split('/layauto_v2/')[1]+':'+name]+=1
    if args.counted:sys.setprofile(profile)
    start=time.monotonic();result=facade.analyze_cell(AnalysisRequest(args.root/'analysis.json'));elapsed=time.monotonic()-start
    sys.setprofile(None)
    capture_bytes=sum(len(s.data) for s in result.captures);report_bytes=len(result.report_json.encode('utf-8'))
    source={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('layauto_v2','tests') for p in sorted(Path(folder).rglob('*.py'))}
    source['pyproject.toml']=hashlib.sha256(Path('pyproject.toml').read_bytes()).hexdigest()
    print(json.dumps({'case':args.case,'counted':args.counted,'python':sys.version,'platform':sys.platform,
        'dependencies':{d.metadata['Name']:d.version for d in importlib.metadata.distributions()},
        'source':source,'inputs':{str(p.relative_to(args.root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(args.root.rglob('*')) if p.is_file()},
        'request_status':result.request_status,'source_comparison':result.source_comparison,
        'whole_public_call_seconds':elapsed,'stages_seconds':dict(timers),
        'stage_note':'analyze_local includes nested source/neutral times; do not sum inclusive nested stages; selected_analysis sums body and manual',
        'hwm_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'capture_count':len(result.captures),'capture_bytes':capture_bytes,
        'report_bytes':report_bytes,'report_capture_ratio':report_bytes/capture_bytes,'counts':dict(counts),
        'report_sha256':hashlib.sha256(result.report_json.encode()).hexdigest(),
        'facets':{f.name:getattr(result.local.facets,f.name).status for f in fields(result.local.facets)},
        'findings':[(f.code,f.severity) for f in result.findings]},sort_keys=True,indent=2))

if __name__=='__main__':main()
