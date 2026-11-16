"""Audit original R4 reports against final source without assuming live R4 tests."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'docs/tasks/W014'
def sha(data):
    return hashlib.sha256(data).hexdigest()
def load(path):
    return json.loads((ROOT / path).read_bytes())

selection = load('docs/tasks/W014/resource-adoption-r4/final-selection.json')
frozen = load('docs/tasks/W014/verification/source-manifest.json')
checked = set()
def refs(value):
    if isinstance(value, dict):
        if {'path','sha256','bytes'} <= value.keys():
            data = (ROOT / value['path']).read_bytes()
            assert sha(data) == value['sha256'] and len(data) == value['bytes'], value['path']
            checked.add(value['path'])
        for child in value.values():
            refs(child)
    elif isinstance(value, list):
        for child in value:
            refs(child)
refs(selection)
for name, record in selection['evidence_files'].items():
    data = (ROOT / name).read_bytes()
    assert sha(data) == record['sha256'] and len(data) == record['bytes'], name
    checked.add(name)
summary = {}
for case, sample in selection['selected_samples'].items():
    measured = load(sample['report']['path'])
    reference = load(sample['baseline_report']['path'])
    assert measured['source_id'] == selection['current_source_id']
    assert reference['source_id'] == selection['reference_source_id']
    diff = [n for n in frozen['files'] if measured['files'].get(n) != frozen['files'][n]]
    assert diff == ['tests/contracts/test_w014_contracts.py'], diff
    current = (ROOT / diff[0]).read_text()
    new = ("        from layauto_v2.domain.source_location import ref_from_location\n"
           "        # A coordinate operand identifies the actual per-device/per-net raw\n"
           "        # response. ChannelSeed does not expose NetEvidence's source property.\n"
           "        reference = ref_from_location(seed.record['field_sources']['vertices_nm']['sources'][1])\n")
    assert current.count(new) == 1
    old = current.replace(new, '        reference = seed.source\n').encode()
    assert sha(old) == measured['files'][diff[0]]
    assert set(measured['files']) == set(frozen['files'])
    assert all(sha((ROOT / n).read_bytes()) == h for n,h in frozen['files'].items())
    added = {'layauto_v2/' + n for n in ('derive/body_relations.py',
             'derive/terminal_relations.py', 'domain/terminal_relations.py',
             'normalization/terminal_relations.py', 'normalization/terminal_relations_codec.py')}
    old_runtime = {n:h for n,h in reference['files'].items()
                   if n.startswith('layauto_v2/') and n not in added}
    assert len(old_runtime) == 106
    assert all(measured['files'][n] == h == frozen['files'][n] for n,h in old_runtime.items())
    after = sum(p['seconds'] for n,p in measured['phases'].items() if n.startswith('W014'))
    before = sum(p['seconds'] for n,p in reference['phases'].items() if n.startswith('W013'))
    cmp = selection['comparison'][case]
    assert after / before == cmp['component_seconds_ratio']
    assert measured['wire_bytes'] - reference['wire_bytes'] == cmp['wire_added_bytes']
    assert list(sample['authentication_calls_by_phase'].values()) == [1,1,2]
    summary[case] = {'ratio':after/before, 'added_wire_bytes':cmp['wire_added_bytes'],
                     'peak_MiB':sample['process_peak_rss_kib']/1024}
assert selection['selected_samples']['normal-direct']['report']['path'] != selection['original_R4_direct_overlap_and_exclusion']['original_direct_report']['path']
print(json.dumps({'status':'passed','referenced_files':len(checked),
                  'measured_source':selection['current_source_id'],
                  'frozen_source':frozen['source_id'],
                  'exact_test_only_delta':diff, 'unchanged_old_runtime':len(old_runtime),
                  'cases':summary, 'new_benchmark':False},indent=2))
