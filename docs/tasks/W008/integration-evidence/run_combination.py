from __future__ import annotations
import datetime,importlib.metadata,json,os,pathlib,platform,subprocess,sys,time
root=pathlib.Path('/workspace/Layauto');out=pathlib.Path(__file__).resolve().parent
nodes=[
 'tests/contracts/test_w008_capture_binding.py::test_actual_capture_complete_geometry_and_semantics_remain_separate_without_io',
 'tests/contracts/test_w008_capture_binding.py::test_cr01_absent_first_uri_cannot_be_forged_into_a_historical_alias',
 'tests/contracts/test_w008_capture_binding.py::test_actual_gds_aliases_preserve_w005_acquisition_identity',
 'tests/contracts/test_w008_capture_binding.py::test_actual_owner_alias_and_gds_site_alias_are_not_resolved_again',
 'tests/contracts/test_w008_capture_binding.py::test_actual_target_can_reuse_earlier_source_under_a_later_alias',
 'tests/contracts/test_w008_capture_binding.py::test_actual_w006_readback_is_equivalent_without_io_or_attempt_changes',
 'tests/contracts/test_w008_capture_binding.py::test_wrong_run_readback_keeps_w007_receipt_rejection',
 'tests/contracts/test_w008_capture_binding.py::test_expected_decoder_failure_retains_issue_and_prior_facts',
 'tests/contracts/test_w008_capture_binding.py::test_prior_reader_failures_are_not_relabelled_as_geometry_success',
 'tests/contracts/test_w008_geometry.py::test_real_w006_readback_and_w007_combine_without_publishing',
 'tests/contracts/test_w008_geometry.py::test_closed_codec_roundtrip_for_all_geometry_records',
 'tests/contracts/test_w008_geometry.py::test_unsupported_comparator_is_located_error_with_completed_capture_facts',
 'tests/contracts/test_w008_geometry_wire.py::test_geometry_input_and_result_wire_recheck_capture_and_cross_document_bindings',
 'tests/contracts/test_w006_pipeline.py::test_f1_full_caller_request_ready_is_unsealed_and_all_refs_resolve',
 'tests/contracts/test_w006_pipeline.py::test_f2_real_missing_terminator_has_same_run_bytes_and_failure_chain',
 'tests/contracts/test_w007_inputs.py::test_c13_retains_exact_channel_length_target_obligation_and_no_run_terminal',
 'tests/contracts/test_w007_contracts.py::test_normalization_and_new_domain_keep_pure_dependency_boundaries',
 'tests/contracts/test_w006_ipmr01.py',
]
cmd=[sys.executable,'-B','-m','pytest','-p','no:cacheprovider','-q',*nodes]
env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1';env['PYTHONPATH']=str(root)
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
assert head=='16159c7edb2d085ab4987bff27ec11c5b5f53294'
start=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic()
p=subprocess.run(cmd,cwd=root,env=env,capture_output=True,text=True)
r={'tested_head':head,'command':cmd,'cwd':str(root),'started_utc':start,'elapsed_seconds':time.monotonic()-t,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'environment':{'python':sys.version,'executable':sys.executable,'platform':platform.platform(),'pytest':importlib.metadata.version('pytest'),'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(root),'clean_install':False,'note':'Existing PM environment; current merged checkout source. Full suite/typing/packages adopted from byte-identical reviewed tree.'}}
(out/'combination-check.json').write_text(json.dumps(r,indent=2)+'\n')
print(p.stdout);print(p.stderr);sys.exit(p.returncode)
