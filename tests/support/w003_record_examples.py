"""Author/check W003 document specimens only; never imports product/legacy runtime.

--write writes review specimens with hashes of actual *expected fixture* files.
Default verifies their closed field sets, references, policy and failure variants.
This does not run a pipeline, publish a repository root, or validate a product codec.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs/tasks/W003/examples'
FIX = ROOT / 'tests/fixtures/w003_m1'
VERSION = 'w003-example/1'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tid(kind, value):
    return {'type': kind, 'value': value}


def rec(kind, value, **fields):
    return {'schema_version': VERSION, 'example_only': True, 'kind': kind,
            'id': tid(kind + 'Id', value), **fields}


def file_ref(path, pointer=''):
    return {'path': path, 'json_pointer': pointer, 'scope': 'fixture_expected_only',
            'actual_byte_sha256': digest(FIX / path)}


# Independently listed allowed field sets, rather than inferred from instances.
# All unlisted fields are forbidden; variant-specific fields are required.
FIELDS = {
    'ToolRunResult': ('mode tool_name command input_refs raw_output_refs exit_status execution_status stdout_ref stderr_ref', 'execution_failure'),
    'ParseResult': ('tool_run_ref parser_version dialect_version raw_refs evidence_refs execution_status', ''),
    'EvidenceRecord': ('parse_ref header_ref raw_refs assurance exact_value_example source_backlink', ''),
    'ImmutableContext': ('tech_ref evidence_ref coordinate_ref capability_refs target_ref policy_refs', ''),
    'ProposedInitialState': ('context_ref component_refs current_semantic_ref target_ref lifecycle_audit_ref', ''),
    'PreparedBaseline': ('publication_kind proposed_ref snapshot_ref context_ref attempt_ref expected_state_head expected_attempt_revision lifecycle_audit_ref', ''),
    'Snapshot': ('state_lineage_id state_version parent_snapshot_ref initialization_ref context_ref component_refs assurance', ''),
    'InitializationEvent': ('run_id snapshot_ref state_version', ''),
    'RunAttempt/unsealed': ('variant run_id revision starting_state_head raw_request_descriptor raw_request_digest idempotency durability_profile', ''),
    'RunAttempt/sealed_open': ('variant run_id revision starting_state_head context_ref execution_mode snapshot_ref idempotency durability_profile', ''),
    'PlanningAuditRecord': ('run_id snapshot_ref outcome semantic_comparison extraction_oracle_ref unsupported_deltas candidate_refs', ''),
    'NoChangePlanningResult': ('run_id snapshot_ref target_ref all_delta_ledger planning_audit_ref required_constraint_audit_ref', ''),
    'ConstraintAuditRecord': ('run_id snapshot_ref scope rule_oracle_ref outcome', ''),
    'LifecycleAuditRecord': ('operator_profile_ref scope outcome no_derived_layers comparator', ''),
    'RunRecord/no_change': ('variant run_id input_summary context_ref final_snapshot_ref ordered_commit_ids stage_audit_refs planning_audit_ref constraint_audit_ref provenance', ''),
    'RunRecord/pre_context_failure': ('variant run_id completed_audit_refs failure_ref', ''),
    'RunRecord/sealed_no_publication_failure': ('variant run_id completed_audit_refs failure_ref stable_snapshot_ref context_ref ordered_commit_ids', ''),
    'Stage5Closure/with_run_record': ('variant run_id run_record_ref final_snapshot_ref ordered_commit_ids', ''),
    'Stage5Closure/run_record_freeze_failure': ('variant run_id failure_ref completed_audit_refs ordered_commit_ids', ''),
    'StageFailure': ('run_id stage category code reason completed_refs localized_refs', ''),
    'ArtifactManifest': ('run_id final_snapshot_ref ordered_commit_ids objects marker_meaning durability_profile', ''),
    'ValidationResult': ('run_id final_snapshot_ref ordered_commit_ids manifest_ref checks aggregate_disposition', ''),
    'ReportingResult': ('run_id execution_status required report_refs disposition', 'failure_ref'),
    'PipelineResult': ('run_id lifecycle_status deployment_disposition durability_profile', 'head_status_at_finalization closure_ref run_record_ref final_snapshot_ref manifest_ref validation_ref reporting_ref failure_ref'),
}


def schema():
    return {'schema_version': VERSION, 'scope': 'review_specimens_only',
            'common_required': ['schema_version', 'example_only', 'kind', 'id'],
            'additional_fields': 'forbidden',
            'variants': {k: {'required': a.split(), 'optional': b.split()}
                         for k, (a, b) in FIELDS.items()},
            'nested_types': {
                'TypedId': {'required': ['type', 'value'], 'type': 'nonempty string; discriminator specific', 'value': 'nonempty string'},
                'FixtureRef': {'required': ['path', 'json_pointer', 'scope', 'actual_byte_sha256'], 'scope': 'fixture_expected_only', 'path_base': 'tests/fixtures/w003_m1'},
                'ExactRational': {'required': ['numerator', 'denominator'], 'encoding': 'coprime integer strings; denominator positive'},
                'ArtifactObject': {'required': ['type', 'required', 'uri', 'sample_file', 'size_bytes', 'actual_byte_sha256'], 'hash': 'SHA-256 of actual sample_file bytes; not semantic hash'},
                'CheckResult': {'required': ['check_id', 'execution_status', 'coverage', 'finding_severity', 'policy_disposition', 'reason', 'evidence_refs', 'localized_refs', 'runtime_ms', 'return_code'], 'statuses': ['pass', 'fail', 'error', 'skipped', 'deferred'], 'coverages': ['complete', 'degraded', 'none']},
            }, 'canonical_encoding': 'UTF-8 sorted-key compact JSON; no float/NaN/Inf; SHA-256; no trailing LF'}


def build():
    run = tid('RunId', 'example-run')
    ids = {k: tid(k + 'Id', v) for k, v in [
        ('ToolRunResult', 'fixture-read'), ('ParseResult', 'query-parse'), ('EvidenceRecord', 'evidence'),
        ('ImmutableContext', 'context'), ('ProposedInitialState', 'proposed'), ('PreparedBaseline', 'prepared'),
        ('Snapshot', 'baseline-0'), ('InitializationEvent', 'init'), ('PlanningAuditRecord', 'planning'),
        ('ConstraintAuditRecord', 'mandatory'), ('LifecycleAuditRecord', 'lifecycle'),
        ('RunRecord', 'run-record'), ('Stage5Closure', 'closure'), ('ArtifactManifest', 'manifest'),
        ('ValidationResult', 'validation'), ('ReportingResult', 'reporting')]}
    refs = [file_ref('query/raw/' + n + '.txt') for n in
            ['instance_xref', 'net_xref', 'device_regions', 'net_regions']]
    # Ref fields link to hand-written oracle/expected view, never runtime bootstrap.
    components = {name: file_ref('expected/layout.json', '/' + pointer) for name, pointer in
                  [('current_semantic', 'current_semantic'), ('geometry', 'geometry'),
                   ('occupancy', 'occupancy_fragment_witnesses'), ('annotation', 'annotation'),
                   ('connectivity', 'connectivity'), ('lifecycle', 'lifecycle'), ('linkage', 'linkage')]}
    idem = {'operation_kind': 'create_attempt', 'proposed_run_id': run,
            'idempotency_key': 'example-create-1', 'request_digest_algorithm': 'sha256'}
    # Pre-context request contains only available raw byte identities/selections,
    # never canonical TargetIntent/tech/evidence IDs obtained by later parsing.
    descriptor = {'operation_kind': 'create_attempt', 'proposed_run_id': run,
                  'expected_state_head': None, 'proposed_lineage_id': tid('StateLineageId', 'example-lineage'),
                  'idempotency_key': 'example-create-1', 'requested_mode': 'dummy_fixture',
                  'raw_input_selections': [file_ref(p) for p in
                                           ['source.gds', 'source.cdl', 'target.cdl', 'query/header.json']],
                  'raw_capture_selections': refs,
                  'config_policy_selections': [file_ref(p) for p in
                                              ['site_config.yaml', 'tech.json', 'export_policy.json', 'validation_policy.json', 'limitations.json']]}
    idem['request_digest'] = hashlib.sha256(canonical(descriptor)).hexdigest()
    rows = [
        rec('ToolRunResult', 'fixture-read', mode='dummy_fixture', tool_name='fixture-reader',
            command=['read-preexisting-raw-captures'], input_refs=[file_ref('site_config.yaml')],
            raw_output_refs=refs, exit_status=0, execution_status='pass', stdout_ref=None, stderr_ref=None),
        rec('ParseResult', 'query-parse', tool_run_ref=ids['ToolRunResult'], parser_version='w003-query-normalized/1 (contract only; product parser not implemented)',
            dialect_version='synthetic_query_dialect/1', raw_refs=refs, evidence_refs=[ids['EvidenceRecord']], execution_status='pass'),
        rec('EvidenceRecord', 'evidence', parse_ref=ids['ParseResult'], header_ref=file_ref('query/header.json'),
            raw_refs=refs, assurance='synthetic', exact_value_example={'original_lexeme': '20', 'value_ticks': 20,
                'nominal_tick_m': {'numerator': '1', 'denominator': '1000000000'},
                'numeric_precision': 'exact integer lexeme; query unit 1 nm',
                'unit_contract_ref': file_ref('tech.json', '/unit_scale_contract')},
            source_backlink={'raw_ref': file_ref('query/raw/device_regions.txt'), 'line_1based': 3,
                             'token_0based': 7, 'meaning': 'D0 rectangle y_min',
                             'source_dbu_backlink': file_ref('query/header.json', '/geometry_unit_contract'),
                             'original_xy_ticks_preserved': True}),
        rec('ImmutableContext', 'context', tech_ref=file_ref('tech.json'), evidence_ref=ids['EvidenceRecord'],
            coordinate_ref=file_ref('tech.json', '/coordinate_projection'),
            capability_refs=[file_ref('tech.json', '/' + key) for key in
                             ['geometry_capability', 'cdl_dialect', 'fin_count_profile', 'device_extraction_contract']],
            target_ref=file_ref('target.cdl'), policy_refs=[file_ref('export_policy.json'), file_ref('validation_policy.json')]),
        rec('LifecycleAuditRecord', 'lifecycle', operator_profile_ref=file_ref('tech.json'), scope='all drawn records',
            outcome='pass', no_derived_layers=True, comparator='exact tagged layer/rectangle multiset; frame identity'),
        rec('ProposedInitialState', 'proposed', context_ref=ids['ImmutableContext'], component_refs=components,
            current_semantic_ref=file_ref('source.cdl'), target_ref=file_ref('target.cdl'), lifecycle_audit_ref=ids['LifecycleAuditRecord']),
        rec('RunAttempt', 'attempt-unsealed', variant='unsealed', run_id=run, revision=0, starting_state_head=None,
            raw_request_descriptor=descriptor, raw_request_digest=hashlib.sha256(canonical(descriptor)).hexdigest(),
            idempotency=idem, durability_profile='process_local'),
        rec('PreparedBaseline', 'prepared', publication_kind='baseline', proposed_ref=ids['ProposedInitialState'],
            snapshot_ref=ids['Snapshot'], context_ref=ids['ImmutableContext'], attempt_ref=tid('RunAttemptId', 'attempt-unsealed'),
            expected_state_head=None, expected_attempt_revision=0, lifecycle_audit_ref=ids['LifecycleAuditRecord']),
        rec('Snapshot', 'baseline-0', state_lineage_id=tid('StateLineageId', 'example-lineage'), state_version=0,
            parent_snapshot_ref=None, initialization_ref=ids['InitializationEvent'], context_ref=ids['ImmutableContext'],
            component_refs=components, assurance='synthetic'),
        rec('InitializationEvent', 'init', run_id=run, snapshot_ref=ids['Snapshot'], state_version=0),
        rec('RunAttempt', 'attempt-sealed', variant='sealed_open', run_id=run, revision=1, starting_state_head=None,
            context_ref=ids['ImmutableContext'], execution_mode='whole_intent', snapshot_ref=ids['Snapshot'],
            idempotency={**idem, 'operation_kind': 'initialize', 'idempotency_key': 'example-init-1',
                         'request_digest': hashlib.sha256(canonical({'expected_state_head': None, 'expected_attempt_revision': 0,
                                                                    'prepared_ref': ids['PreparedBaseline']})).hexdigest()}, durability_profile='process_local'),
        rec('PlanningAuditRecord', 'planning', run_id=run, snapshot_ref=ids['Snapshot'], outcome='no_change',
            semantic_comparison='all pins/models/terminals/parameters/top equal; target delta list empty',
            extraction_oracle_ref=file_ref('oracle.json'), unsupported_deltas=[], candidate_refs=[]),
        rec('ConstraintAuditRecord', 'mandatory', run_id=run, snapshot_ref=ids['Snapshot'], scope='whole_cell',
            rule_oracle_ref=file_ref('oracle.json'), outcome='feasible'),
        rec('NoChangePlanningResult', 'no-change', run_id=run, snapshot_ref=ids['Snapshot'], target_ref=file_ref('target.cdl'),
            all_delta_ledger=[], planning_audit_ref=ids['PlanningAuditRecord'], required_constraint_audit_ref=ids['ConstraintAuditRecord']),
        rec('RunRecord', 'run-record', variant='no_change', run_id=run,
            input_summary={'source_gds': file_ref('source.gds'), 'source_cdl': file_ref('source.cdl'),
                           'target_cdl': file_ref('target.cdl'), 'tech': file_ref('tech.json'), 'coordinate': file_ref('tech.json'),
                           'query_header': file_ref('query/header.json'), 'assurance': 'synthetic'},
            context_ref=ids['ImmutableContext'], final_snapshot_ref=ids['Snapshot'], ordered_commit_ids=[],
            stage_audit_refs=[ids['ParseResult'], ids['LifecycleAuditRecord'], ids['PlanningAuditRecord'], ids['ConstraintAuditRecord']],
            planning_audit_ref=ids['PlanningAuditRecord'], constraint_audit_ref=ids['ConstraintAuditRecord'], provenance='expected specimen; no product run'),
        rec('Stage5Closure', 'closure', variant='with_run_record', run_id=run, run_record_ref=ids['RunRecord'],
            final_snapshot_ref=ids['Snapshot'], ordered_commit_ids=[]),
    ]
    objects = []
    for kind, name in [('gds', 'output.gds'), ('cdl', 'output.cdl'), ('layout_json', 'layout.json')]:
        path = FIX / 'expected' / name
        h = digest(path)
        objects.append({'type': kind, 'required': True, 'uri': 'example-object:sha256:' + h,
                        'sample_file': 'expected/' + name, 'size_bytes': path.stat().st_size, 'actual_byte_sha256': h})
    checks = []
    for name in ['geometry_readback', 'cdl_semantics', 'json_components', 'fixture_oracle', 'audit_readiness', 'calibre_drc', 'calibre_lvs', 'virtuoso_dry_run']:
        deferred = name.startswith(('calibre', 'virtuoso'))
        checks.append({'check_id': name, 'execution_status': 'deferred' if deferred else 'pass',
                       'coverage': 'none' if deferred else 'complete', 'finding_severity': 'warning' if deferred else 'info',
                       'policy_disposition': 'requires_review' if deferred else 'accept',
                       'reason': 'post-MVP capability; not executed' if deferred else 'expected only within declared toy scope; no product run',
                       'evidence_refs': [file_ref('oracle.json')], 'localized_refs': [], 'runtime_ms': None, 'return_code': None})
    rows += [
        rec('ArtifactManifest', 'manifest', run_id=run, final_snapshot_ref=ids['Snapshot'], ordered_commit_ids=[], objects=objects,
            marker_meaning='sample export-set complete/addressable only; not a published product manifest', durability_profile='process_local'),
        rec('ValidationResult', 'validation', run_id=run, final_snapshot_ref=ids['Snapshot'], ordered_commit_ids=[], manifest_ref=ids['ArtifactManifest'],
            checks=checks, aggregate_disposition='requires_review'),
        rec('ReportingResult', 'reporting', run_id=run, execution_status='pass', required=True,
            report_refs=['report.expected.md', 'report.expected.json'], disposition='requires_review'),
        rec('PipelineResult', 'terminal', run_id=run, lifecycle_status='terminal', deployment_disposition='requires_review',
            head_status_at_finalization='current', durability_profile='process_local', closure_ref=ids['Stage5Closure'],
            run_record_ref=ids['RunRecord'], final_snapshot_ref=ids['Snapshot'], manifest_ref=ids['ArtifactManifest'],
            validation_ref=ids['ValidationResult'], reporting_ref=ids['ReportingResult']),
    ]
    failures = []
    for variant, stage, category, code in [
        ('pre_context', '1', 'evidence', 'RAW_TERMINATOR_MISSING'),
        ('sealed_no_publication', '3', 'constraint', 'MANDATORY_RULE_VIOLATION'),
        ('run_record_freeze', '5', 'record_construction', 'RUN_RECORD_FREEZE_FAILED'),
        ('export_failure', '6.export', 'export', 'OUTPUT_NOT_REPRESENTABLE'),
        ('check_fail', '6.validation', 'validation', 'SELF_CONSISTENCY_VIOLATION'),
        ('check_error', '6.validation', 'validation', 'REQUIRED_READER_ERROR'),
        ('reporting_failure', '6.reporting', 'reporting', 'REQUIRED_REPORT_WRITE_FAILED'),
        ('terminal_storage_failure', 'terminal', 'infrastructure', 'TERMINAL_ROOT_UNAVAILABLE')]:
        fail = rec('StageFailure', variant + '-failure', run_id=run, stage=stage, category=category, code=code,
                   reason='expected failure specimen; not injected into product runtime', completed_refs=[], localized_refs=[])
        rr = ids['RunRecord']; additions = [fail]; closure = ids['Stage5Closure']
        if variant in ['pre_context', 'sealed_no_publication']:
            fields = {'variant': variant + '_failure', 'run_id': run, 'completed_audit_refs': [], 'failure_ref': fail['id']}
            if variant == 'sealed_no_publication':
                fields.update(stable_snapshot_ref=ids['Snapshot'], context_ref=ids['ImmutableContext'], ordered_commit_ids=[])
            r = rec('RunRecord', variant + '-record', **fields); additions.append(r); rr = r['id']
            if variant == 'pre_context':
                malformed = file_ref('failures/missing_terminator/query/raw/instance_xref.txt')
                failed_header = file_ref('failures/missing_terminator/query/header.json')
                failed_read = rec('ToolRunResult', 'malformed-fixture-read', mode='dummy_fixture', tool_name='fixture-reader',
                                  command=['read-preexisting-raw-captures'], input_refs=[failed_header],
                                  raw_output_refs=[malformed], exit_status=0, execution_status='pass', stdout_ref=None, stderr_ref=None)
                parsed = rec('ParseResult', 'failed-parse', tool_run_ref=failed_read['id'],
                             parser_version='w003-query-normalized/1 (contract only)', dialect_version='synthetic_query_dialect/1',
                             raw_refs=[malformed], evidence_refs=[], execution_status='error')
                additions.extend([failed_read, parsed]); r['completed_audit_refs'] = [failed_read['id'], parsed['id']]
                fail['completed_refs'] = [failed_read['id'], parsed['id']]
                fail['localized_refs'] = [{'raw_ref': malformed, 'location': 'missing END W003_QUERY at EOF'}]
            else:
                closed = rec('Stage5Closure', 'sealed-failure-closure', variant='with_run_record', run_id=run,
                             run_record_ref=rr, final_snapshot_ref=ids['Snapshot'], ordered_commit_ids=[])
                additions.append(closed); closure = closed['id']
        if variant == 'run_record_freeze':
            rr = None
            additions.append(rec('Stage5Closure', variant + '-closure', variant='run_record_freeze_failure', run_id=run,
                                 failure_ref=fail['id'], completed_audit_refs=[ids['PlanningAuditRecord']], ordered_commit_ids=[]))
            closure = additions[-1]['id']
        post_manifest = variant in ['check_fail', 'check_error', 'reporting_failure', 'terminal_storage_failure']
        terminal_fields = dict(run_id=run, lifecycle_status='terminal', deployment_disposition='reject',
                               durability_profile='process_local', failure_ref=fail['id'])
        if rr is not None: terminal_fields['run_record_ref'] = rr
        if variant not in ['pre_context']:
            terminal_fields['head_status_at_finalization'] = 'current'
            terminal_fields['final_snapshot_ref'] = ids['Snapshot']
            terminal_fields['closure_ref'] = closure
        if post_manifest:
            terminal_fields.update(manifest_ref=ids['ArtifactManifest'], validation_ref=ids['ValidationResult'])
        if variant in ['check_fail', 'check_error']:
            check = dict(checks[0], execution_status='fail' if variant == 'check_fail' else 'error',
                         coverage='complete' if variant == 'check_fail' else 'none', finding_severity='error',
                         policy_disposition='reject', reason=code)
            validation = rec('ValidationResult', variant + '-validation', run_id=run, final_snapshot_ref=ids['Snapshot'],
                             ordered_commit_ids=[], manifest_ref=ids['ArtifactManifest'], checks=[check], aggregate_disposition='reject')
            additions.append(validation); terminal_fields['validation_ref'] = validation['id']
        if variant == 'reporting_failure':
            reporting = rec('ReportingResult', 'failed-report', run_id=run, execution_status='error', required=True,
                            report_refs=[], disposition='reject', failure_ref=fail['id'])
            additions.append(reporting); terminal_fields['reporting_ref'] = reporting['id']
        if variant != 'terminal_storage_failure': additions.append(rec('PipelineResult', variant + '-terminal', **terminal_fields))
        failures.append({'variant': variant, 'example_only': True, 'records': additions,
                         'existing_run_record_ref': rr, 'normal_geometry_export': post_manifest,
                         'core_manifest_present': post_manifest, 'validation_present': post_manifest,
                         'eco_commit_ids': [], 'terminal_pointer_published': variant != 'terminal_storage_failure',
                         'production_accept': False,
                         'diagnostic_reporting': 'optional best effort; no fabricated successful report',
                         'retained_snapshot': None if variant == 'pre_context' else ids['Snapshot']})
    return rows, failures


def validate_record(row):
    key = row['kind'] + ('/' + row['variant'] if 'variant' in row else '')
    required, optional = FIELDS[key]
    common = {'schema_version', 'example_only', 'kind', 'id'}
    assert common | set(required.split()) <= row.keys(), key
    assert row.keys() <= common | set(required.split()) | set(optional.split()), key
    assert row['schema_version'] == VERSION and row['example_only'] is True
    assert row['id']['type'] == row['kind'] + 'Id'
    assert isinstance(row['id']['value'], str) and row['id']['value']
    if row['kind'] in ['RunRecord', 'Stage5Closure', 'ArtifactManifest', 'ValidationResult'] and 'ordered_commit_ids' in row:
        assert row['ordered_commit_ids'] == [], 'M1 has no ECO envelopes'
    if row['kind'] == 'ValidationResult':
        ranks = {'accept': 0, 'requires_review': 1, 'reject': 2}
        for check in row['checks']:
            assert set(check) == set(schema()['nested_types']['CheckResult']['required'])
            assert check['execution_status'] in ['pass', 'fail', 'error', 'skipped', 'deferred']
            assert check['coverage'] in ['complete', 'degraded', 'none']
            if check['execution_status'] in ['skipped', 'deferred']: assert check['coverage'] == 'none'
            if check['execution_status'] in ['fail', 'error']: assert check['policy_disposition'] == 'reject'
        assert ranks[row['aggregate_disposition']] >= max(ranks[c['policy_disposition']] for c in row['checks'])
    if row['kind'] == 'PipelineResult':
        assert row['lifecycle_status'] == 'terminal'
        assert row['deployment_disposition'] in ['requires_review', 'reject']
    if key == 'RunAttempt/unsealed':
        payload = row['raw_request_descriptor']
        assert payload['proposed_run_id'] == row['run_id']
        assert payload['expected_state_head'] == row['starting_state_head']
        h = hashlib.sha256(canonical(payload)).hexdigest()
        assert row['raw_request_digest'] == row['idempotency']['request_digest'] == h
        assert payload['idempotency_key'] == row['idempotency']['idempotency_key']


def verify():
    rows = json.loads((OUT / 'records.json').read_text())['records']
    cases = json.loads((OUT / 'failures.json').read_text())['cases']
    assert json.loads((OUT / 'schema.json').read_text()) == schema()
    for row in rows: validate_record(row)
    for case in cases:
        for row in case['records']: validate_record(row)
        assert case['eco_commit_ids'] == [] and case['production_accept'] is False
        if case['variant'] == 'run_record_freeze':
            assert case['existing_run_record_ref'] is None
            assert not any(r['kind'] == 'RunRecord' for r in case['records'])
        if case['variant'] == 'pre_context':
            parsed = next(r for r in case['records'] if r['kind'] == 'ParseResult')
            tool = next(r for r in case['records'] if r['kind'] == 'ToolRunResult')
            assert parsed['tool_run_ref'] == tool['id'] and parsed['raw_refs'] == tool['raw_output_refs']
            raw = parsed['raw_refs'][0]
            assert 'END W003_QUERY' not in (FIX / raw['path']).read_text()
            header = json.loads((FIX / tool['input_refs'][0]['path']).read_text())
            assert next(r['sha256'] for r in header['raw'] if r['capability'] == 'instance_xref') == raw['actual_byte_sha256']
        if case['variant'] in ['pre_context', 'sealed_no_publication', 'run_record_freeze', 'export_failure']:
            assert not case['core_manifest_present'] and not case['validation_present']
        if case['variant'] == 'terminal_storage_failure':
            assert not case['terminal_pointer_published']
            assert not any(r['kind'] == 'PipelineResult' for r in case['records'])
        if case['variant'] in ['export_failure', 'check_fail', 'check_error', 'reporting_failure', 'terminal_storage_failure']:
            assert case['existing_run_record_ref'] == tid('RunRecordId', 'run-record')
    def check_refs(records):
        # Failure worlds may refer to completed immutable normal specimens.
        by_id = {canonical(r['id']): r for r in rows + records}
        def inspect(value):
            if isinstance(value, dict):
                if set(value) == {'type', 'value'} and value['type'] not in ['RunId', 'StateLineageId']:
                    assert canonical(value) in by_id, ('dangling typed ref', value)
                for child in value.values(): inspect(child)
            elif isinstance(value, list):
                for child in value: inspect(child)
        inspect(records)
        for row in records:
            if row['kind'] == 'PipelineResult' and 'closure_ref' in row:
                closure = by_id[canonical(row['closure_ref'])]
                if 'run_record_ref' in closure:
                    assert row['run_record_ref'] == closure['run_record_ref']
            if row['kind'] == 'PipelineResult' and 'validation_ref' in row:
                val = by_id[canonical(row['validation_ref'])]
                assert val['manifest_ref'] == row['manifest_ref']
    check_refs(rows)
    for case in cases: check_refs(case['records'])
    manifest = next(r for r in rows if r['kind'] == 'ArtifactManifest')
    for obj in manifest['objects']:
        assert set(obj) == set(schema()['nested_types']['ArtifactObject']['required'])
        p = FIX / obj['sample_file']
        assert digest(p) == obj['actual_byte_sha256']
        assert p.stat().st_size == obj['size_bytes']
        assert obj['uri'] == 'example-object:sha256:' + digest(p)
    checked = 0
    def walk(value):
        nonlocal checked
        assert not isinstance(value, float), 'no binary float in specimen wire'
        if isinstance(value, dict):
            if set(value) == {'path', 'json_pointer', 'scope', 'actual_byte_sha256'}:
                path = FIX / value['path']
                assert path.is_file() and digest(path) == value['actual_byte_sha256'], value
                if value['json_pointer']:
                    node = json.loads(path.read_text())
                    for part in value['json_pointer'].split('/')[1:]:
                        node = node[int(part)] if isinstance(node, list) else node[part.replace('~1', '/').replace('~0', '~')]
                checked += 1
            for child in value.values(): walk(child)
        elif isinstance(value, list):
            for child in value: walk(child)
    walk(rows); walk(cases)
    report = json.loads((OUT / 'report.expected.json').read_text())
    assert report['example_only'] is True and report['product_run_executed'] is False
    assert report['ordered_commit_ids'] == [] and report['deployment_disposition'] == 'requires_review'
    # Negative schema examples: these must be rejected, not silently admitted.
    import copy
    mutations = []
    unsealed = next(r for r in rows if r['kind'] == 'RunAttempt' and r['variant'] == 'unsealed')
    bad = copy.deepcopy(unsealed); bad['context_ref'] = tid('ImmutableContextId', 'context'); mutations.append(bad)
    bad = copy.deepcopy(unsealed); bad['run_id'] = tid('RunId', 'different-run'); mutations.append(bad)
    bad = copy.deepcopy(unsealed); bad['starting_state_head'] = tid('SnapshotId', 'other-head'); mutations.append(bad)
    bad = copy.deepcopy(unsealed); bad['raw_request_descriptor']['config_policy_selections'][0]['actual_byte_sha256'] = '0' * 64; mutations.append(bad)
    normal = next(r for r in rows if r['kind'] == 'RunRecord')
    bad = copy.deepcopy(normal); bad['ordered_commit_ids'] = [tid('CommitId', 'empty')]; mutations.append(bad)
    tool = copy.deepcopy(rows[0]); tool['parse_ref'] = rows[1]['id']; mutations.append(tool)
    val = copy.deepcopy(next(r for r in rows if r['kind'] == 'ValidationResult'))
    val['checks'][0].update(execution_status='error', policy_disposition='accept'); mutations.append(val)
    for bad in mutations:
        try: validate_record(bad)
        except AssertionError: pass
        else: raise AssertionError('invalid specimen accepted')
    print(json.dumps({'scope': 'W003 review specimens only; no product execution', 'records': len(rows),
                      'failure_variants': len(cases), 'fixture_refs_checked': checked,
                      'actual_sample_artifact_hashes_checked': len(manifest['objects']),
                      'invalid_combinations_rejected': len(mutations)}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    if args.write:
        OUT.mkdir(parents=True, exist_ok=True)
        rows, failures = build()
        for name, payload in [('schema.json', schema()), ('records.json', {'schema_version': VERSION, 'example_only': True, 'records': rows}),
                              ('failures.json', {'schema_version': VERSION, 'example_only': True, 'cases': failures})]:
            (OUT / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
        report = {'schema_version': VERSION, 'example_only': True, 'product_run_executed': False,
                  'kind': 'MachineReportExpected', 'cell': 'INV_M1_SYNTH', 'input_mode': 'dummy_fixture',
                  'input_refs': [file_ref(p) for p in ['source.gds', 'source.cdl', 'target.cdl', 'query/header.json', 'tech.json', 'site_config.yaml']],
                  'current_target_fin_counts': {'MN0': [5, 5], 'MP0': [7, 7]},
                  'all_delta_ledger': [], 'unsupported_deltas': [], 'candidate_selection': None,
                  'repair_requirements': [], 'constraint_scope': 'whole_cell', 'constraint_outcome': 'expected_feasible',
                  'baseline_version': 0, 'baseline_event': 'InitializationEvent', 'ordered_commit_ids': [],
                  'committed_changes': {'geometry': 0, 'current_semantic': 0, 'occupancy': 0, 'annotation': 0, 'connectivity': 0},
                  'derived_changes': [], 'view_refresh': 'baseline construction only; no ECO refresh',
                  'coverage': {'provenance': 'synthetic_source_evidence', 'unannotated_marker': 'MARK',
                               'disconnected_labelled_islands': ['LB.left', 'LB.right'],
                               'post_edit_lvs_match': 'not_run', 'production_rules': 'not_covered'},
                  'validation_ref': tid('ValidationResultId', 'validation'), 'manifest_ref': tid('ArtifactManifestId', 'manifest'),
                  'deployment_disposition': 'requires_review', 'reason': 'synthetic engineering specimen; real signoff deferred',
                  'deferred': ['real_calibre_drc', 'real_calibre_lvs', 'virtuoso_readback'],
                  'actual_product_generation_time': None, 'actual_tool_command': None,
                  'limitations_ref': file_ref('limitations.json')}
        (OUT / 'report.expected.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    verify()


if __name__ == '__main__':
    main()
