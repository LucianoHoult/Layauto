"""W014 actual-capture inputs and independent terminal expectations.

Only temporary fixture copies are transformed. No body verifier or fixture
generator supplies product inputs or the expected terminal answers below.
"""
from __future__ import annotations

from functools import lru_cache

from w005_cases import FIXTURE, apply_case, copy_input, read_json, rebind, without_cache, write_json
from w010_cases import build_local
from w013_cases import normal_local


EXPECTED_TERMINALS = {
    ('MN0', 'D'): 'Y', ('MN0', 'G'): 'A', ('MN0', 'S'): 'VSS', ('MN0', 'B'): 'VSS',
    ('MP0', 'D'): 'Y', ('MP0', 'G'): 'A', ('MP0', 'S'): 'VDD', ('MP0', 'B'): 'VDD',
}


def build(root=FIXTURE):
    from layauto_v2.normalization import build_terminal_relations
    return build_terminal_relations(normal_local() if root == FIXTURE else build_local(root))


@lru_cache(maxsize=1)
def normal_capture():
    result = build()
    assert result.status == 'success', result.issues
    return result


@lru_cache(maxsize=1)
def normal_wire():
    from layauto_v2.normalization.terminal_relations_codec import encode_record
    return encode_record(normal_capture())


def relation_map(draft):
    return {(row.target.device_id.name, row.target.role): row for row in draft.relations}


def neutral_inputs(root, local):
    """Keep unchanged neutral local geometry, acquire all other real inputs.

    Query/body-only variants share a temporary URI and GDS/tech bytes with
    their local draft. Their source identities and provenance are rebuilt by
    the real reader and W007, not fabricated or copied from expected output.
    """
    from layauto_v2.domain.channel_identity import ChannelSeed
    from layauto_v2.domain.evidence import EvidenceRecord
    from layauto_v2.domain.net_annotation import NetEvidence
    from layauto_v2.normalization import from_parse_result, normalize
    from layauto_v2.normalization.net_annotation import _capture_binding
    from w007_cases import read
    parsed = read(root)
    input = from_parse_result(parsed)
    normalized = normalize(input)
    assert normalized.status == 'success', normalized.issues
    facts = normalized.value
    device_ids = {row.device_id: row for row in facts.device_identities}
    net_ids = {row.query_key: row for row in facts.net_identities}
    channel_seeds = tuple(ChannelSeed(row.semantic_id, row.query_key, row.record,
                                     device_ids[row.semantic_id].provenance)
                          for row in facts.device_seeds)
    net_evidence = tuple(NetEvidence(row.semantic_id, row.query_key, row.record,
                                    net_ids[row.query_key].provenance)
                         for row in facts.net_seeds)
    tech = next(row for row in parsed.completed if row.kind == 'tech')
    derived = EvidenceRecord('derived', input.value['tech']['derived'], (tech.sources[2],))
    body = next(row for row in parsed.completed if row.kind == 'body')
    return local, facts.source, channel_seeds, net_evidence, derived, body, _capture_binding(input)


def neutral(root, local):
    from layauto_v2.derive.terminal_relations import build_terminal_relations_draft
    return build_terminal_relations_draft(*neutral_inputs(root, local))


def change_body(root, mutate):
    path = root / 'body/context.json'
    value = read_json(path)
    mutate(value)
    write_json(path, value)
    rebind(root)


def failure_copy(tmp_path, case):
    root = copy_input(tmp_path)
    apply_case(root, case)
    without_cache(root)
    return root


@lru_cache(maxsize=1)
def readback_capture():
    from layauto_v2.domain.publication import InputsReady
    from layauto_v2.normalization import (build_effective_geometry, build_geometry,
                                           build_local_connectivity, build_terminal_relations)
    from layauto_v2.normalization.geometry_input import geometry_from_inputs_ready
    from layauto_v2.pipeline import prepare_inputs
    from layauto_v2.repository import PublicationRepository
    from w006_cases import caller_request
    repository = PublicationRepository()
    ready = prepare_inputs(repository, caller_request(FIXTURE, run_id='w014-contract-readback'))
    assert isinstance(ready, InputsReady)
    checkpoint = repository.load_checkpoint(ready.run_id)
    attempt = repository.load_attempt(ready.run_id)
    local = build_local_connectivity(build_effective_geometry(build_geometry(geometry_from_inputs_ready(
        ready, checkpoint, repository.read(ready.parse_ref), repository.read(ready.tool_ref),
        tuple(repository.read(ref) for ref in ready.evidence_refs)))))
    return build_terminal_relations(local), repository, ready, checkpoint, attempt
