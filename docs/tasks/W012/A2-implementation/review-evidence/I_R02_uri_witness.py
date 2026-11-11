"""Independent W005/W007 URI witness; no W008-W011 build or performance timing."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path('/workspace/Layauto')
HERE = Path(__file__).resolve().parent
sys.path.insert(0, '/workspace/work/w012-a2/review')
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import from_parse_result, normalize


def main():
    destination = HERE / 'I-R02-uri-witness.json'
    assert not destination.exists()
    parsed = read_inputs(ROOT / 'tests/fixtures/w003_m1/site_config.yaml')
    assert parsed.status == 'success'
    normalized = normalize(from_parse_result(parsed))
    assert normalized.status == 'success'
    facts = normalized.value
    refs = {}
    for name in ('source', 'target'):
        evidence = getattr(facts, name).preservation
        refs[name] = {'kind': evidence.kind,
                      'refs': [{'uri': ref.uri, 'sha256': ref.sha256} for ref in evidence.sources],
                      'matching_completed_records': sum(record == evidence for record in parsed.completed)}
        assert any(record == evidence for record in parsed.completed)
    assert refs['source']['kind'] == 'source_cdl' and refs['target']['kind'] == 'target_cdl'
    assert facts.source.preservation != facts.target.preservation
    assert [ref['uri'] for ref in refs['target']['refs']] == ['target.cdl']
    # The original newly added probe assertion rejects this valid retained URI.
    original_acceptance = any(ref.uri.endswith('/target.cdl') for ref in facts.target.preservation.sources)
    assert original_acceptance is False
    result = {'status': 'passed', 'valid_actual_W005_W007': True, 'preservation': refs,
              'old_probe_target_suffix_acceptance': original_acceptance,
              'original_failure_reproduced_without_complete_W011': True,
              'scope': 'Independent input/provenance witness only; no successful performance sample.'}
    destination.write_text(json.dumps(result, indent=2) + '\n')
    print('PASS valid W005/W007 retained target.cdl URI independently reproduces erroneous suffix check')


if __name__ == '__main__':
    main()
