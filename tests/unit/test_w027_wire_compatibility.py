"""Addresses obtained by encoding the same records on the W027 starting commit."""
from layauto_v2.domain.publication import (
    BASELINE_VERSION, ContentRef, PipelineResult, RunAttempt, RunRecord, RunRequest,
    SealedContext, StageFailure, WithRunRecordClosure,
)
from layauto_v2.domain.publication_codec import decode_record, encode_record, record_digest


def test_w006_and_w023_content_addresses_still_resolve_to_the_same_wire():
    run = 'audit-codec-test'
    request = RunRequest(run, 'lineage', 'create', '/inputs/site')

    def ref(kind):
        return ContentRef(kind, run, 'a' * 64)

    # Produced by b94c03e83fe16b7037a103e1c76e24e14a5a2f56, before the Stage 5 types existed.
    records = (
        (request, '9e61a8cb0cf40b9ae3c465db383dfc08413b3c3ce2243d3b30b3621e06f294e0'),
        (RunAttempt(request), '744e2e5940a602e6f32dc2260c4c48df43790b9b911d48f0ff7080ada8eb028e'),
        (RunAttempt(request, 2, 'sealed_open', ref('checkpoint'), schema_version=BASELINE_VERSION,
                    context_ref=ref('sealed_context')), '10bf20b2498bd35fa1d567b6abe00236b66f04bbfbbb963efa9f730963d3244d'),
        (StageFailure(run, 'parse', 'Failure', 'invalid'), 'f5ea31a6a2198e4bbdffbcd497b41be865836aa03bb0a6878d12264a20d0aad1'),
        (RunRecord(run, ref('stage_failure'), (ref('tool_run'),)),
         '4b9e1563029eac4bf505e373b37a9a6fd544ce58f26145e17af0aa01378cf732'),
        (WithRunRecordClosure(run, ref('run_record'), ref('stage_failure'), (ref('tool_run'),)),
         '8191ee3f3de4a8a0c783023ddf9d8c2b5dd3e14ac49950059d501311c359c101'),
        (PipelineResult(run, ref('closure')), '5c8f766fdc02fb9ca479ad9f548966e6e2bd8d6a32810403cf113126ababcc31'),
        (SealedContext(run, ref('checkpoint'), ref('state_head'), ref('target_intent'), 'f' * 64),
         '40c4d573f05b529f4dff987418c03b119d010acc1b284c036d726e043fdc9b15'),
    )
    for record, original_digest in records:
        assert record_digest(record) == original_digest
        assert decode_record(encode_record(record)) == record
