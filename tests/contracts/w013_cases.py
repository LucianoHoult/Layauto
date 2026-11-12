"""Independent W013 hand cases and captured-input transformations.

Only pytest temporary captures are edited. No fixture generator or product
matcher is used to obtain expected areas, identities or physical components.
"""
from __future__ import annotations

from fractions import Fraction
from functools import lru_cache

from w005_cases import FIXTURE, read_json, rebind, write_json
from w010_cases import build_local


DIRECT_AREAS = {'POLY': Fraction(720), 'LI': Fraction(1110), 'M1': Fraction(1340)}
TARGET_AREAS = {**DIRECT_AREAS, 'OD': Fraction(9120),
                'BODY_N': Fraction(10800), 'BODY_P': Fraction(12000)}
DIRECT_TARGET_NETS = {'G': 'A', 'MA': 'A', 'LN': 'VSS', 'LP': 'VDD',
                      'LY': 'Y', 'MN': 'VSS', 'MP': 'VDD', 'MY': 'Y'}
LOCAL_COMPONENTS = {
    frozenset(('ON.S', 'LN', 'MN')): 'VSS',
    frozenset(('OP.S', 'LP', 'MP')): 'VDD',
    frozenset(('ON.D', 'OP.D', 'LY', 'MY')): 'Y',
    frozenset(('G', 'MA')): 'A',
    frozenset(('BN',)): None,
    frozenset(('BP',)): None,
}
REAL_QUERY_IDENTITIES = {'n_a': ('A', '1'), 'n_y': ('Y', '2'),
                         'n_lo': ('VSS', '3'), 'n_hi': ('VDD', '4')}


def build(root=FIXTURE):
    from layauto_v2.normalization.net_annotation import build_net_annotation
    return build_net_annotation(normal_local() if root == FIXTURE else build_local(root))


@lru_cache(maxsize=1)
def normal_local():
    return build_local()


@lru_cache(maxsize=1)
def normal_capture():
    """One shared real direct receipt per interpreter, no W011 construction."""
    result = build()
    assert result.status == 'success', result.issues
    return result


@lru_cache(maxsize=1)
def normal_wire():
    from layauto_v2.normalization.net_annotation_codec import encode_record
    return encode_record(normal_capture())


@lru_cache(maxsize=1)
def readback_capture():
    from layauto_v2.domain.publication import InputsReady
    from layauto_v2.normalization import build_effective_geometry, build_geometry, build_local_connectivity
    from layauto_v2.normalization.geometry_input import geometry_from_inputs_ready
    from layauto_v2.normalization.net_annotation import build_net_annotation
    from layauto_v2.pipeline import prepare_inputs
    from layauto_v2.repository import PublicationRepository
    from w006_cases import caller_request
    repository = PublicationRepository()
    ready = prepare_inputs(repository, caller_request(FIXTURE, run_id='w013-contract-readback'))
    assert isinstance(ready, InputsReady)
    checkpoint = repository.load_checkpoint(ready.run_id)
    attempt = repository.load_attempt(ready.run_id)
    local = build_local_connectivity(build_effective_geometry(build_geometry(geometry_from_inputs_ready(
        ready, checkpoint, repository.read(ready.parse_ref), repository.read(ready.tool_ref),
        tuple(repository.read(ref) for ref in ready.evidence_refs)))))
    return build_net_annotation(local), repository, ready, checkpoint, attempt


def neutral_inputs(root, local):
    """Use real W007 rows with an existing unchanged local geometry draft.

    A caller may rewrite query captures at the same temporary URI between
    calls. This exercises the neutral spatial component without rebuilding
    the unchanged complete W010 receipt for every hand arithmetic case.
    """
    from layauto_v2.domain.codec import FrozenMap
    from layauto_v2.domain.evidence import EvidenceRecord
    from layauto_v2.domain.net_annotation import NetEvidence
    from layauto_v2.importers import read_inputs
    from layauto_v2.normalization import from_parse_result, normalize
    from layauto_v2.normalization.codec import record_digest
    parsed = read_inputs(root / 'site_config.yaml')
    assert parsed.status == 'success', parsed.issues
    input = from_parse_result(parsed)
    normalized = normalize(input)
    assert normalized.status == 'success', normalized.issues
    facts = normalized.value
    identities = {identity.query_key: identity for identity in facts.net_identities}
    evidence = tuple(NetEvidence(seed.semantic_id, seed.query_key, seed.record,
                                 identities[seed.query_key].provenance)
                     for seed in facts.net_seeds)
    tech = next(row for row in parsed.completed if row.kind == 'tech')
    derived = EvidenceRecord('derived', input.value['tech']['derived'], (tech.sources[2],))
    binding = FrozenMap({
        'schema': 'layauto-net-capture-binding/1',
        'normalization_input_sha256': record_digest(input),
        'sources': tuple(FrozenMap({'uri': source.uri, 'sha256': source.sha256})
                         for source in parsed.sources),
        'readback': None,
    })
    return local, facts.source, evidence, derived, binding


def neutral(root, local):
    from layauto_v2.annotation.net_regions import build_net_annotation_draft
    return build_net_annotation_draft(*neutral_inputs(root, local))


def rewrite_net_response(root, object_name, rows):
    """Write exact declared NET SHAPES rectangles, retaining real raw grammar.

    ``rows`` is a sequence of (derived_layer, nm bounds). Coordinates must be
    representable at the captured dialect's 1/20 nm precision. Record labels
    are explicit authored request identifiers, never inferred from a filename.
    """
    request_path, header_path = root / 'query/requests.json', root / 'query/header.json'
    requests, header = read_json(request_path), read_json(header_path)
    request = next(row for row in requests['requests']
                   if row['capability'] == 'net_regions' and row['object'] == object_name)
    path = root / request['path']
    lines = path.read_text().splitlines()
    if rows:
        output = lines[:3]
        section = next(line for line in lines if line.startswith('1 1 0 '))
        for layer, bounds in rows:
            scaled = tuple(Fraction(value) * 20 for value in bounds)
            assert all(value.denominator == 1 for value in scaled)
            x0, y0, x1, y1 = map(int, scaled)
            assert x0 < x1 and y0 < y1
            output.extend((layer, section, 'p 1 4', f'{y0} {x0}', f'{y1} {x0}',
                           f'{y1} {x1}', f'{y0} {x1}'))
        output.append('END OF RESPONSE')
        path.write_text('\n'.join(output) + '\n')
        request['record_ids'] = [f'W013_{object_name}_{index}' for index in range(len(rows))]
    else:
        requests['requests'].remove(request)
        header['raw'] = [row for row in header['raw'] if row['uri'] != request['path']]
        path.unlink()
    write_json(request_path, requests)
    write_json(header_path, header)
    rebind(root)


def independent_areas(targets, labelled_rectangles):
    """Exhaust finite open arrangement atoms, independent of canonical covers.

    Return total/covered/uncovered/net-conflict areas. Input targets are the
    rectangles of one physical region; duplicate evidence is counted once.
    """
    all_boxes = tuple(targets) + tuple(box for _, box in labelled_rectangles)
    xs = sorted({Fraction(value) for box in all_boxes for value in (box[0], box[2])})
    ys = sorted({Fraction(value) for box in all_boxes for value in (box[1], box[3])})
    totals = dict.fromkeys(('total', 'covered', 'uncovered', 'conflict'), Fraction(0))
    for left, right in zip(xs, xs[1:]):
        for bottom, top in zip(ys, ys[1:]):
            x, y = (left + right) / 2, (bottom + top) / 2
            if not any(box[0] < x < box[2] and box[1] < y < box[3] for box in targets):
                continue
            names = {name for name, box in labelled_rectangles
                     if box[0] < x < box[2] and box[1] < y < box[3]}
            area = (right - left) * (top - bottom)
            totals['total'] += area
            totals['covered' if names else 'uncovered'] += area
            if len(names) > 1:
                totals['conflict'] += area
    return totals


def unchecked_replace(instance, **changes):
    """External tampering controls; no test bypasses a public final boundary."""
    from dataclasses import fields
    value = object.__new__(type(instance))
    for field in fields(instance):
        object.__setattr__(value, field.name, changes.get(field.name, getattr(instance, field.name)))
    return value
