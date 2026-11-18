"""Actual-file W016 contract probes, independent numeric expectations."""
import hashlib
import json
from pathlib import Path
import sys
from dataclasses import replace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'support'))
from analysis_inputs import materialize, load, write, rebind, manual_for
from layauto_v2.analysis import AnalysisRequest, analyze_cell
from layauto_v2.domain.analysis import AnalysisResult
from layauto_v2.importers.analysis_reader import acquire_analysis
from layauto_v2.normalization.analysis_input import LocalAnalysisReceipt


def run(root):
    return analyze_cell(AnalysisRequest(root / 'analysis.json'))


def test_no_body_end_to_end(tmp_path):
    materialize(tmp_path)
    result = run(tmp_path)
    assert result.request_status == 'completed'
    assert result.target_comparison == 'not_requested' and result.parent_global == 'unknown'
    assert not any((tmp_path / p).exists() for p in ('target.cdl','body/context.json','export_policy.json','validation_policy.json'))
    local = result.local
    assert local is not None
    assert len(local.facets.local_graph.value.nodes) == 14
    assert len(local.facets.local_graph.value.edges) == 8
    assert len(local.facets.local_graph.value.components) == 6
    assert sorted(m.count for m in local.facets.channel_fin.value.measurements) == [5,7]
    terms = local.facets.terminals.value
    assert len(terms) == 8
    assert all(t.comparison == 'equal' for t in terms if t.expected.role != 'B')
    assert all(t.comparison == 'indeterminate' and t.observed_net_ids == () for t in terms if t.expected.role == 'B')
    assert result.source_comparison == 'indeterminate'
    assert 'body_path_proof' in result.missing_context
    report = json.loads(result.report_json)
    assert len(report['captures']) == len(result.captures)
    assert not any('data' in r for r in report['captures'])
    assert {'baseline','no_change','geometry_commit','export_publish'} <= set(result.blocked_operations)


def test_body_preserves_local_and_supports_only_external_scope(tmp_path):
    materialize(tmp_path, body=True)
    with_body = run(tmp_path)
    assert with_body.request_status == 'completed', with_body.findings
    assert with_body.external_body.status == 'evaluated'
    assert with_body.external_body.value['local_graph_union'] is False
    assert with_body.external_body.value['production_matched_body_evidence'] is False
    assert all(t.comparison == 'equal' for t in with_body.local.facets.terminals.value)
    manifest = load(tmp_path/'analysis.json'); manifest['external_body']={'kind':'not_selected'}
    write(tmp_path/'analysis.json', manifest);rebind(tmp_path)
    without = run(tmp_path)
    assert without.local.facets.drawn.value == with_body.local.facets.drawn.value
    assert without.local.facets.local_graph.value == with_body.local.facets.local_graph.value
    assert with_body.parent_global == 'unknown'
    assert with_body.source_comparison == 'indeterminate'
    assert without.local.receipt_ref != with_body.local.receipt_ref
    assert all(t.comparison == 'equal' for t in with_body.local.facets.terminals.value)


@pytest.mark.parametrize('kind', ['trusted_lvs_freeze','geometry_window'])
def test_future_selection_never_reads_file(tmp_path, monkeypatch, kind):
    materialize(tmp_path, external={'kind':kind,'uri':'forbidden.json'})
    actual = Path.read_bytes
    def read(path):
        assert path.name != 'forbidden.json'
        return actual(path)
    monkeypatch.setattr(Path,'read_bytes',read)
    result=run(tmp_path)
    assert result.request_status == 'unsupported' and result.local is not None
    assert result.external_body.status == 'unsupported'


@pytest.mark.parametrize('bad', ['missing','syntax','hash','top','role','binding_uri','unknown_field','unit'])
def test_selected_body_errors_keep_local(tmp_path,bad):
    materialize(tmp_path,body=True)
    p=tmp_path/'body/context.json';doc=load(p)
    if bad=='missing': p.unlink()
    elif bad=='syntax': p.write_text('{')
    else:
        if bad=='hash': doc['source_gds']['sha256']='0'*64
        elif bad=='top': doc['top']='other'
        elif bad=='role': doc['source_gds']['uri']='source.cdl'
        elif bad=='binding_uri': doc['source_gds']['uri']='missing-alias.gds'
        elif bad=='unknown_field': doc['instance']='TOP/U8'
        elif bad=='unit': doc['unit']['metres_per_tick']={'num':2,'den':1000000000}
        write(p,doc)
    result=run(tmp_path)
    assert result.request_status=='rejected'
    assert result.local is not None and result.local.facets.channel_fin.status=='available'
    assert result.external_body.status=='error'
    assert any(f.source.uri.endswith('context.json') for f in result.findings)


@pytest.mark.parametrize('case', ['body_enclosure','body_disconnected','body_wrong_rail'])
def test_body_rule_failures_remain_violations(tmp_path,case):
    # Available named corpus cases are actual bytes, not expected answers.
    cases=load(Path(__file__).resolve().parents[1]/'fixtures/w003_m1/failures/cases.json')['cases']
    if case not in {c['id'] for c in cases}:
        pytest.skip('not a named corpus variant')
    materialize(tmp_path,body=True,case=case)
    result=run(tmp_path)
    assert result.request_status=='rejected'
    assert result.local is not None and result.external_body.issues


def test_manual_is_only_declared_expectation_and_reacquires(tmp_path):
    materialize(tmp_path)
    before=run(tmp_path)
    doc=manual_for(tmp_path)
    write(tmp_path/'manual.json',doc)
    manifest=load(tmp_path/'analysis.json');manifest['manual_intent']={'kind':'declaration','uri':'manual.json'}
    write(tmp_path/'analysis.json',manifest)
    # Manifest changes need an explicitly rebuilt synthetic closure.
    stale=run(tmp_path)
    assert stale.request_status=='rejected' and stale.local is None
    rebind(tmp_path)
    after=run(tmp_path)
    assert after.request_status=='completed' and after.manual_intent.status=='declared'
    assert after.manual_intent.value['assertions'][0]['expected_supply_label']=='GND1'
    assert after.local.source==before.local.source
    assert all(t.observed_net_ids==() for t in after.local.facets.terminals.value if t.expected.role=='B')
    assert before.manual_intent.status=='not_selected'
    assert after.parent_global=='unknown'


@pytest.mark.parametrize('bad',['extra','hash','cell','device','timestamp','duplicate'])
def test_manual_errors_do_not_supply_observations(tmp_path,bad):
    materialize(tmp_path)
    doc=manual_for(tmp_path)
    if bad=='extra':doc['assurance']='matched'
    elif bad=='hash':doc['source_layout']['sha256']='0'*64
    elif bad=='cell':doc['cell']='wrong'
    elif bad=='device':doc['assertions'][0]['device']='foreign'
    elif bad=='timestamp':doc['created_at']='2026-11-17T00:00:00+08:00'
    elif bad=='duplicate':doc['assertions']*=2
    write(tmp_path/'manual.json',doc)
    m=load(tmp_path/'analysis.json');m['manual_intent']={'kind':'declaration','uri':'manual.json'};write(tmp_path/'analysis.json',m);rebind(tmp_path)
    result=run(tmp_path)
    assert result.request_status=='rejected' and result.local is not None
    assert result.manual_intent.status=='error'


def test_fin_four_against_five_is_completed_mismatch(tmp_path):
    materialize(tmp_path,case='extraction_mismatch')
    result=run(tmp_path)
    assert result.request_status=='completed' and result.source_comparison=='mismatch'
    assert sorted(m.count for m in result.local.facets.channel_fin.value.measurements)==[4,7]
    assert any(f.code=='SourceParameterMismatch' for f in result.findings)


@pytest.mark.parametrize('case', ['missing_terminator','unit_mismatch','gds_nonrectangle'])
def test_early_input_error_has_no_local_receipt(tmp_path,case):
    cases=load(Path(__file__).resolve().parents[1]/'fixtures/w003_m1/failures/cases.json')['cases']
    if case not in {c['id'] for c in cases}:pytest.skip('not a named corpus variant')
    materialize(tmp_path,case=case)
    result=run(tmp_path)
    assert result.request_status in ('rejected','unsupported') and result.local is None


@pytest.mark.parametrize('input_request',[None,{},AnalysisRequest(Path('relative.json')),AnalysisRequest('absolute'),AnalysisRequest(Path('/')),AnalysisRequest(Path('/tmp/\ud800.json'))])
def test_request_errors_are_located(input_request):
    result=analyze_cell(input_request)
    assert result.request_status=='rejected' and result.findings[0].code=='InvalidAnalysisRequest'


@pytest.mark.parametrize('exception',[RuntimeError('unexpected'),KeyboardInterrupt(),SystemExit()])
def test_unexpected_exceptions_propagate(tmp_path,monkeypatch,exception):
    materialize(tmp_path)
    import layauto_v2.analysis as facade
    def fail(*args): raise exception
    monkeypatch.setattr(facade,'analyze_local',fail)
    with pytest.raises(type(exception)):
        run(tmp_path)


def test_receipt_does_not_accept_unused_alias(tmp_path):
    evidence=acquire_analysis(materialize(tmp_path))
    from layauto_v2.domain.codec import FrozenMap
    evidence=replace(evidence,aliases=FrozenMap({**dict(evidence.aliases),'never-requested':str(tmp_path/'source.gds')}))
    with pytest.raises(ValueError):LocalAnalysisReceipt(evidence)


def append_rect(root,layer,bounds):
    # Authored GDS rectangle bytes; no observed geometry algorithm or oracle.
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'contracts'))
    from w008_geometry_cases import rectangle_bytes,STREAM_LAYER
    data=(root/'source.gds').read_bytes()
    # Last stream records are ENDSTR and ENDLIB (four bytes each).
    assert data[-8:]==b'\x00\x04\x07\x00\x00\x04\x04\x00'
    (root/'source.gds').write_bytes(data[:-8]+rectangle_bytes(STREAM_LAYER[layer],bounds)+data[-8:])


def append_seed(root,net,bounds):
    requests=load(root/'query/requests.json')
    request=next(r for r in requests['requests'] if r['capability']=='net_regions' and r['object']==net)
    path=root/request['path'];lines=path.read_text().splitlines();assert lines[-1]=='END OF RESPONSE'
    x0,y0,x1,y1=(v*20 for v in bounds)
    lines[-1:]=['toy_m1','1 1 0 May 07 03:00:00 2026','p 1 4',f'{y0} {x0}',f'{y1} {x0}',f'{y1} {x1}',f'{y0} {x1}','END OF RESPONSE']
    path.write_text('\n'.join(lines)+'\n')
    request['record_ids'].append('W016_'+net+'_authored')
    write(root/'query/requests.json',requests)


@pytest.mark.parametrize('conflict',[False,True])
def test_hand_area_gap_and_conflict_in_real_query(tmp_path,conflict):
    materialize(tmp_path,body=True)
    append_rect(tmp_path,'M1',(130,20,140,24))  # target 10*4=40
    append_seed(tmp_path,'n_a',(130,20,136,24)) # 6*4=24
    if conflict:append_seed(tmp_path,'n_y',(134,20,140,24)) # overlap 2*4=8
    # Rebind external GDS independently as well as the local raw/closure header.
    body=load(tmp_path/'body/context.json');body['source_gds']['sha256']=hashlib.sha256((tmp_path/'source.gds').read_bytes()).hexdigest();write(tmp_path/'body/context.json',body)
    rebind(tmp_path)
    result=run(tmp_path)
    assert result.local is not None
    annotation=result.local.facets.annotation.value
    targets=[t for t in annotation.targets if t.drawn_rectangle.bounds==(130,20,140,24)]
    assert len(targets)==1
    fragments=[f for f in annotation.fragments if f.target_ref==targets[0].ref]
    assert sum(f.area_nm2 for f in fragments)==40
    if conflict:
        assert sum(f.area_nm2 for f in fragments if f.status=='conflict')==8
        assert result.request_status=='rejected' and result.local.facets.annotation.status=='error'
        assert result.local.facets.terminals.value is not None
    else:
        assert sum(f.area_nm2 for f in fragments if f.status=='unknown')==16
        assert result.request_status=='completed'
    # Annotation conflict on an isolated M1 target does not suppress T04/T05.
    assert result.external_body.status=='evaluated'
    assert len(result.external_body.value['paths'])==2


def test_new_analysis_values_are_rejected_by_old_boundaries(tmp_path):
    materialize(tmp_path)
    result=run(tmp_path)
    from layauto_v2.normalization import build_terminal_relations
    from layauto_v2.normalization.terminal_relations_codec import encode_record
    from layauto_v2.normalization.net_annotation_codec import encode_record as annotation_encode
    from layauto_v2.normalization import from_parse_result
    for consumer,value in ((build_terminal_relations,result),(encode_record,result),
                           (annotation_encode,result.local.facets.annotation.value),(from_parse_result,result)):
        with pytest.raises(ValueError):consumer(value)


def test_acquisition_once_per_actual_path_and_pure_compute(tmp_path,monkeypatch):
    materialize(tmp_path,body=True)
    import layauto_v2.analysis as facade
    actual_read=Path.read_bytes;reads={}
    def read(path):
        key=str(path);reads[key]=reads.get(key,0)+1
        return actual_read(path)
    monkeypatch.setattr(Path,'read_bytes',read)
    actual_local=facade.analyze_local
    def pure(receipt):
        def forbidden(*a,**k):raise AssertionError('pure computation performed IO')
        monkeypatch.setattr(Path,'read_bytes',forbidden)
        monkeypatch.setattr(Path,'resolve',forbidden)
        return actual_local(receipt)
    monkeypatch.setattr(facade,'analyze_local',pure)
    result=run(tmp_path)
    assert result.request_status=='completed'
    assert len(reads)==len(result.captures) and set(reads.values())=={1}


def test_partial_fin_keeps_diagnostic_and_real_dependencies(tmp_path):
    materialize(tmp_path)
    append_rect(tmp_path,'FIN',(59,27,110,29))
    rebind(tmp_path)
    result=run(tmp_path)
    assert result.request_status=='rejected'
    facet=result.local.facets.channel_fin
    assert facet.status=='error' and facet.value is not None
    assert any(m.count is None for m in facet.value.measurements)
    assert any(e.status=='partial' for m in facet.value.measurements for e in m.evaluations)
    assert result.local.facets.annotation.status=='available'
    assert result.local.facets.terminals.status=='not_evaluated'
    assert result.local.facets.terminals.dependencies==('channel_fin','annotation')


def test_unsupported_effective_operator_keeps_drawn_and_dependency_chain(tmp_path):
    materialize(tmp_path)
    tech=load(tmp_path/'tech.json');p=tmp_path/tech['owners']['physical']['path'];doc=load(p)
    # Schema-valid owner declaration with unsupported consumed operator text.
    doc['operators']['li_cut/1']='unsupported changed evaluator'
    write(p,doc);rebind(tmp_path)
    result=run(tmp_path)
    assert result.request_status in ('rejected','unsupported')
    if result.local is not None:
        assert result.local.facets.drawn.status=='available'
        assert result.local.facets.local_graph.dependencies==('effective',)
        assert result.local.facets.terminals.dependencies==('channel_fin','annotation')


def test_local_t05_violation_is_completed_with_audit(tmp_path):
    materialize(tmp_path,case='via_enclosure')
    result=run(tmp_path)
    assert result.request_status=='completed',result.findings
    assert result.local.facets.local_graph.value.local_enclosure_status=='violation'
    assert any(f.code=='LocalEnclosureViolation' for f in result.findings)


@pytest.mark.parametrize('bad',['payload','backing','extra_ref','same_hash_role'])
def test_new_receipt_payload_and_native_storage_guards(tmp_path,bad):
    evidence=acquire_analysis(materialize(tmp_path))
    from layauto_v2.domain.codec import FrozenMap
    if bad=='payload':
        record=next(r for r in evidence.records if r.kind=='gds')
        object.__setattr__(record,'payload',FrozenMap({'top':'fabricated'}))
    elif bad=='backing':object.__setattr__(evidence.value,'_entries',list(evidence.value._entries))
    elif bad=='extra_ref':object.__setattr__(evidence.records[-1].sources[0],'extra',[])
    else:
        captures=list(evidence.captures)
        a,b=next((i,j) for i,x in enumerate(captures) for j,y in enumerate(captures) if i!=j and x.uri.endswith('source.cdl') and y.uri.endswith('source.gds'))
        captures[b]=type(captures[b])(captures[b].uri,captures[a].data)
        object.__setattr__(evidence,'captures',tuple(captures))
    with pytest.raises(ValueError):LocalAnalysisReceipt(evidence)


def test_selected_syntax_preserves_original_parser_location(tmp_path):
    materialize(tmp_path,body=True)
    path=tmp_path/'body/context.json';path.write_text('{\n"broken":\n')
    from layauto_v2.domain.evidence import SourceFile
    from layauto_v2.domain.results import InputError
    from layauto_v2.importers.config import load_document
    with pytest.raises(InputError) as original:load_document(SourceFile('body/context.json',path.read_bytes()))
    result=run(tmp_path)
    assert result.external_body.issues==(original.value.issue,)


def test_manual_each_field_retains_actual_source_location(tmp_path):
    materialize(tmp_path)
    doc=manual_for(tmp_path)
    doc['assertions'].append({'device':'MP0','role':'B','expected_supply_label':'PWR1'})
    write(tmp_path/'manual.json',doc)
    manifest=load(tmp_path/'analysis.json');manifest['manual_intent']={'kind':'declaration','uri':'manual.json'}
    write(tmp_path/'analysis.json',manifest);rebind(tmp_path)
    result=run(tmp_path)
    assert result.request_status=='completed'
    refs={ref.field:ref for ref in result.manual_intent.evidence_refs}
    expected={'/author','/created_at','/cell','/instance_hint','/source_layout/uri','/source_layout/sha256',
              '/source_netlist/uri','/source_netlist/sha256'}
    expected.update('/assertions/'+str(i)+suffix for i in range(2) for suffix in ('','/device','/role','/expected_supply_label'))
    assert set(refs)==expected|{None}
    digest=hashlib.sha256((tmp_path/'manual.json').read_bytes()).hexdigest()
    assert all(ref.uri=='manual.json' and ref.sha256==digest for ref in refs.values())
    assert all(pointer in result.report_json for pointer in expected)
    assert all(t.observed_net_ids==() for t in result.local.facets.terminals.value if t.expected.role=='B')


def test_analysis_pure_modules_and_captured_path_replay_have_no_io_calls():
    import ast
    root=Path(__file__).resolve().parents[2]/'layauto_v2'
    for name in ('normalization/analysis.py','normalization/analysis_input.py','domain/analysis.py',
                 'domain/analysis_annotation.py','state/analysis_annotation.py'):
        tree=ast.parse((root/name).read_text())
        for node in ast.walk(tree):
            if isinstance(node,ast.ImportFrom):
                assert not (node.module or '').startswith(('pathlib','os','io','subprocess','layauto_v2.repository','layauto_v2.pipeline'))
            if isinstance(node,ast.Call):
                if isinstance(node.func,ast.Name):assert node.func.id not in ('open','eval','exec','__import__')
                if isinstance(node.func,ast.Attribute):
                    assert node.func.attr not in ('read_bytes','read_text','open','resolve','exists','write_bytes','write_text','mkdir','unlink','rename','rmdir')
    tree=ast.parse((root/'importers/analysis_reader.py').read_text())
    replay_nodes=[n for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in ('_CapturedFiles','captured_analysis_files')]
    assert len(replay_nodes)==2
    for tree in replay_nodes:
        for node in ast.walk(tree):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):
                assert node.func.attr not in ('resolve','exists','open','read_bytes','read_text')


@pytest.mark.parametrize('kind',['root','raw_alias'])
def test_captured_path_facts_cannot_be_forged_as_relative(tmp_path,kind):
    evidence=acquire_analysis(materialize(tmp_path))
    if kind=='root':evidence=replace(evidence,root='relative')
    else:
        from layauto_v2.domain.codec import FrozenMap
        raw=next(k for k in evidence.aliases if '/raw/' in k)
        evidence=replace(evidence,aliases=FrozenMap({**dict(evidence.aliases),raw:'relative-raw.txt'}))
    with pytest.raises(ValueError):LocalAnalysisReceipt(evidence)


@pytest.mark.parametrize(('pin_error', 'failed_stage', 'expected_status'), [
    (False, 'drawn', 'unsupported'),
    (True, None, 'rejected'),
    (True, 'drawn', 'rejected'),
    (True, 'effective', 'rejected'),
    (True, 'local_graph', 'rejected'),
])
def test_independent_identity_and_geometry_diagnostics(tmp_path, pin_error, failed_stage, expected_status):
    materialize(tmp_path)
    if pin_error:
        cdl = tmp_path / 'source.cdl'
        pins = '.SUBCKT INV_M1_SYNTH A Y VSS VDD'
        assert cdl.read_text().count(pins) == 1
        cdl.write_text(cdl.read_text().replace(pins, '.SUBCKT INV_M1_SYNTH A Y VSS'))

    expected = {}
    if failed_stage == 'effective':
        # A second gate stripe crosses the same active rectangle.
        append_rect(tmp_path, 'POLY', (78, 10, 82, 190))
        expected['AmbiguousGateStripe'] = ('source.gds', 'unsupported')
    elif failed_stage:
        if failed_stage == 'drawn':
            uri, group, key = 'tech/formats.json', 'geometry_capability', 'comparator'
            code = 'UnsupportedGeometryComparator'
        else:
            uri, group, key = 'tech/physical.json', 'operators', 'same_layer_contact/1'
            code = 'UnsupportedLocalContactOperator'
        owner = load(tmp_path / uri)
        owner[group][key] = 'unsupported test variant'
        write(tmp_path / uri, owner)
        expected[code] = (uri, 'unsupported')
    if pin_error:
        expected['SourceTopIdentityMismatch'] = ('query/raw/iXref.temp', 'error')
    rebind(tmp_path)

    result = run(tmp_path)
    assert result.request_status == expected_status
    assert len(result.findings) == len(expected)
    assert {f.code: (f.source.uri, f.severity) for f in result.findings} == expected
    for finding in result.findings:
        assert finding.source.sha256 == hashlib.sha256((tmp_path / finding.source.uri).read_bytes()).hexdigest()
        if finding.code == 'SourceTopIdentityMismatch':
            assert finding.source.line == 8

    local = result.local
    assert local.source.selected_cell.name == 'INV_M1_SYNTH'
    stages = ('drawn', 'effective', 'local_graph')
    for index, name in enumerate(stages):
        facet = local.facets[name]
        if failed_stage is None or index < stages.index(failed_stage):
            assert facet.status == 'available' and facet.value is not None
        elif name == failed_stage:
            assert facet.status == 'error' and facet.value is None
        else:
            assert facet.status == 'not_evaluated' and facet.dependencies == (stages[index - 1],)
    for name in ('channel_fin', 'annotation'):
        facet = local.facets[name]
        assert facet.value is None
        if failed_stage:
            assert facet.status == 'not_evaluated' and facet.dependencies == ('local_graph', 'source_identity')
    assert local.facets.terminals.status == 'not_evaluated'
    assert local.facets.terminals.dependencies == ('channel_fin', 'annotation')
