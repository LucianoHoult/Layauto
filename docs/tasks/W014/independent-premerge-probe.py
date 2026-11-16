"""Bounded independent premerge probes; no fixture/runtime changes or saved wire."""
from dataclasses import replace
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests/contracts')]
from w007_cases import ready_copy
from w010_cases import build_local
from w014_cases import neutral_inputs, change_body
from w013_cases import rewrite_net_response
from layauto_v2.derive.terminal_relations import build_terminal_relations_draft
from layauto_v2.normalization import build_terminal_relations
from layauto_v2.normalization.terminal_relations_codec import encode_record, decode_record


def summary(draft):
    return {'issues': [x.code for x in draft.issues],
            'terminals': {r.target.device_id.name + '.' + r.target.role:
                          {'status': r.status, 'observed': [n.name for n in r.observed_net_ids]}
                          for r in draft.relations},
            'paths': {p['device_id']['name']: {k: str(p[k]) for k in
                      ('chain_status', 'rule_status', 'claim_status', 'active_enclosure_nm',
                       'body_edge_length_nm', 'rail_edge_length_nm')}
                      for p in draft.body['paths']}}


def main():
    started = time.perf_counter()
    output = {'python': sys.version, 'cases': {}, 'hashes': {}}
    for path in ('domain/terminal_relations.py', 'derive/terminal_relations.py',
                 'derive/body_relations.py', 'normalization/terminal_relations.py',
                 'normalization/terminal_relations_codec.py'):
        output['hashes'][path] = hashlib.sha256((ROOT / 'layauto_v2' / path).read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix='w014-premerge-') as tmp:
        root = ready_copy(Path(tmp))
        local = build_local(root)
        print('public W010 capture ready', flush=True)
        result = build_terminal_relations(local)
        assert result.status == 'success', result.issues
        draft = result.value
        assert draft is not None
        expected = {'MN0.D':'Y', 'MN0.G':'A', 'MN0.S':'VSS', 'MN0.B':'VSS',
                    'MP0.D':'Y', 'MP0.G':'A', 'MP0.S':'VDD', 'MP0.B':'VDD'}
        report = summary(draft)
        assert len(draft.relations) == 8
        for name, net in expected.items():
            assert report['terminals'][name] == {'status':'equal', 'observed':[net]}
        assert (len(draft.local.nodes), len(draft.local.edges), len(draft.local.components)) == (14,8,6)
        assert all(not r.local_observed_net_ids for r in draft.relations if r.target.role == 'B')
        gates = [r for r in draft.relations if r.target.role == 'G']
        assert gates[0].node_refs == gates[1].node_refs and gates[0].target != gates[1].target
        # Hand differences from the actual context and drawn OD coordinates.
        active = {a['device_id']['name']: a for a in draft.body['active_audits']}
        assert active['MN0']['margins_nm'] == tuple(map(F, (20,20,20,20)))
        assert active['MP0']['margins_nm'] == tuple(map(F, (20,10,20,20)))
        assert all(min(t['body_margins_nm']) == 8 and min(t['rail_margins_nm']) == 2
                   for t in draft.body['tap_audits'])
        output['cases']['normal'] = report
        wire = encode_record(result)
        assert decode_record(wire) == result
        output['public_roundtrip'] = {'bytes':len(wire), 'sha256':hashlib.sha256(wire).hexdigest()}
        del wire
        print('public W014 build/encode/decode passed', flush=True)
        original = (root / 'body/context.json').read_bytes()
        def mutate_shape(doc, name, bounds):
            next(s for s in doc['shapes'] if s['id'] == name)['bbox'] = bounds
        variants = (
            ('false_claim', lambda d:d['associations'][0].__setitem__('expected_semantic_rail','VDD'), 'BodyTargetRailMismatch'),
            ('tap_enclosure_zero', lambda d:mutate_shape(d,'TN.ext',[-12,48,-8,54]), 'BodyTapEnclosureFailure'),
            ('orphan_tap', lambda d:d['shapes'].append({'id':'ORPHAN','layer':'BTAP_N','bbox':[-18,80,-16,82]}), 'BodyUniqueMatchFailure'),
            ('wrong_MN_selection', lambda d:d['associations'][0].__setitem__('local_body','BP'), 'BodyTypeMismatch'),
        )
        for name, mutation, code in variants:
            (root / 'body/context.json').write_bytes(original)
            change_body(root, mutation)
            candidate = build_terminal_relations_draft(*neutral_inputs(root, local.value))
            facts = summary(candidate)
            assert code in facts['issues'], facts
            assert facts['terminals']['MP0.B']['status'] == 'equal', facts
            if name in ('false_claim','tap_enclosure_zero','orphan_tap'):
                assert facts['terminals']['MN0.B'] == {'status':'equal','observed':['VSS']}, facts
            if name in ('false_claim','tap_enclosure_zero'):
                assert facts['paths']['MN0']['rule_status'] == 'violation', facts
            output['cases'][name] = facts
            print(name + ' passed', flush=True)
        (root / 'body/context.json').write_bytes(original)
        change_body(root, lambda d:None)
        rewrite_net_response(root, 'n_lo', [('toy_li',(28,30,34,55)), ('toy_m1',(0,48,F(901,20),58))])
        candidate = build_terminal_relations_draft(*neutral_inputs(root, local.value))
        facts = summary(candidate)
        assert 'BodyTargetRailMismatch' in facts['issues']
        assert facts['terminals']['MN0.B']['status'] == 'indeterminate'
        assert not facts['terminals']['MN0.B']['observed']
        output['cases']['exact_901_over_20'] = facts
        # Attack original retained storage; copying must not hide an alias.
        source = candidate.body_evidence.sources[0]
        object.__setattr__(source, 'extra', [])
        try:
            replace(candidate)
        except ValueError:
            output['retained_alias_rejected'] = True
        else:
            raise AssertionError('original source alias accepted')
    output['status'] = 'passed'
    output['elapsed_seconds'] = round(time.perf_counter() - started, 3)
    print(json.dumps(output, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
