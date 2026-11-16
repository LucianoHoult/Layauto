"""Early internal local-chain measurement; not a delivered analysis API."""
from pathlib import Path
import json, resource, time, sys
from collections import Counter
counts=Counter()
def count_calls(frame, event, arg):
    if event == 'call' and '/layauto_v2/' in frame.f_code.co_filename:
        name=frame.f_code.co_name
        if name in ('__post_init__', 'parse_gds', 'parse_cdl', 'parse_query', 'parse_analysis', 'build_layout', 'build_partition', 'build_occupancy', 'build_effective_draft', 'build_local_connectivity_draft', 'build_channel_identity_draft', 'build_annotation_operands'):
            module=frame.f_code.co_filename.split('/layauto_v2/')[1]
            counts[module+':'+name]+=1
sys.setprofile(count_calls)
from layauto_v2.importers.analysis_reader import acquire_analysis
from layauto_v2.normalization.analysis_input import LocalAnalysisReceipt
from layauto_v2.normalization.semantic import build_source_operands
from layauto_v2.normalization.identity import join_source_operands
from layauto_v2.normalization._validation import source_admission_problem
from layauto_v2.domain.geometry import mapping
from layauto_v2.domain.evidence import EvidenceRecord
from layauto_v2.domain.channel_identity import ChannelSeed
from layauto_v2.state.layout_store import build_layout
from layauto_v2.state.coordinate import build_partition
from layauto_v2.state.occupancy import build_occupancy
from layauto_v2.state.regions import build_effective_draft
from layauto_v2.state.local_connectivity import build_local_connectivity_draft
from layauto_v2.derive.channel_identity import build_channel_identity_draft

start=time.monotonic(); timings={}
def stage(name):
    global start
    now=time.monotonic();timings[name]=now-start;start=now
    print(json.dumps({'stage':name,'seconds':timings[name], 'hwm_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}),flush=True)
e=acquire_analysis(Path('docs/tasks/W015/evidence/candidate-input/analysis.json').resolve());assert not e.issues,e.issues;stage('acquire')
r=LocalAnalysisReceipt(e);stage('authenticate')
v=e.value;records={x.kind:x for x in e.records};tech=mapping(v['tech'])
source=build_source_operands(records['source_cdl'],tech,mapping(v['header']),mapping(v['tech_bundle']))
assert source_admission_problem(v,source,records['tech'].sources,records['header'].sources[0]) is None
identities,nets,seeds,netseeds=join_source_operands(v,records['header'].sources[0],source);stage('source_identity')
def owner(name):
    return EvidenceRecord(name,mapping(tech[name]),(records['tech'].sources[1+('drawn','derived','physical','formats','coordinate','rules').index(name)],))
layout=build_layout(records['gds'],owner('drawn'),owner('formats'))
base=build_occupancy(build_partition(layout));stage('drawn')
effective=build_effective_draft(base,owner('physical'));stage('effective')
local=build_local_connectivity_draft(effective,owner('rules'));stage('local_graph')
by_id={i.device_id:i for i in identities}
channels=build_channel_identity_draft(local,source,tuple(ChannelSeed(s.semantic_id,s.query_key,s.record,by_id[s.semantic_id].provenance) for s in seeds),owner('derived'));stage('channel')
print(json.dumps({'capture_bytes':sum(len(s.data) for s in e.captures), 'measurements':repr(channels.measurements),'issues':repr(channels.issues),'timings':timings}),flush=True)
from layauto_v2.domain.net_annotation import NetEvidence
from layauto_v2.domain.analysis_annotation import AnalysisAnnotationBinding
from layauto_v2.state.analysis_annotation import AnalysisAnnotationDraft
from layauto_v2.annotation.net_regions import build_annotation_operands
from layauto_v2.domain.codec import FrozenMap,digest
from layauto_v2.domain.circuit import semantic_value
net_ids={i.net_id:i for i in nets}
net_evidence=tuple(sorted((NetEvidence(s.semantic_id,s.query_key,s.record,net_ids[s.semantic_id].provenance) for s in netseeds),key=lambda s:s.ref.sha256))
binding=AnalysisAnnotationBinding(local.ref,effective.ref,layout.ref,layout.units.ref,base.partition.ref,
 layout.units.canonical_tick_nm,layout.top,source.selected_cell,digest(semantic_value(source)),source.preservation.sources[0],
 owner('derived'),owner('drawn'),local.components,tuple(sorted((x.id for x in layout.records),key=lambda i:i.sha256)),
 tuple(s.ref for s in net_evidence),FrozenMap({'schema':'layauto-analysis-capture-binding/1','local_receipt_sha256':r.ref,
 'sources':tuple(FrozenMap({'uri':s.uri,'sha256':s.sha256}) for s in e.captures)}))
annotation=AnalysisAnnotationDraft(binding,net_evidence,*build_annotation_operands(local,source,net_evidence,binding));stage('annotation')
print(json.dumps({'annotation_issues':repr(annotation.issues),'components':len(annotation.components)}))
from layauto_v2.reporting.analysis import diagnostic_json
report=diagnostic_json({'source':source,'drawn':base,'effective':effective,'local_graph':local,'channel_fin':channels,'annotation':annotation},e.captures)
stage('diagnostic_report')
Path('/tmp/w016-local-diagnostic.json').write_text(report)
print(json.dumps({'report_bytes':len(report.encode()),'capture_bytes':sum(len(s.data) for s in e.captures),'ratio':len(report.encode())/sum(len(s.data) for s in e.captures),'objects':len(json.loads(report)['objects'])}))

sys.setprofile(None)
print(json.dumps({'call_counts':dict(sorted(counts.items())), 'note':'generator parse_analysis counts include resumes; not independent authentications'}))
