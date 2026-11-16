"""Read the independent CR12 before/after receipts; never import the product."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]


def receipt(name: str) -> dict:
    text = (OUT / name).read_text()
    return json.loads(text[text.index('{'):])


def main() -> None:
    before = receipt('evidence_wrapper_versions_probe.before.stdout.txt')
    after = receipt('evidence_wrapper_versions.after.stdout.txt')
    checks: list[str] = []
    old = {(row['owner'], row['field']): row for row in before['cases']}
    new = {(row['owner'], row['field']): row for row in after['cases']}
    assert len(old) == len(new) == 6 and set(old) == set(new)
    for key, row in old.items():
        if key[0] == 'derived':
            assert row['constructor_accepted'] is False and row['constructor_error'] == 'ValueError'
            checks.append('.'.join(key) + ': old upstream control already rejected')
        else:
            assert row['constructor_accepted'] is True and row['encode_accepted'] is True
            assert row['decode_accepted'] is False and row['decode_error'] == 'ValueError'
            checks.append('.'.join(key) + ': original roundtrip failure preserved')
        assert new[key]['constructor_accepted'] is False
        assert new[key]['constructor_error'] == 'ValueError'
        assert new[key]['message'] == 'invalid evidence discriminator/version'
        checks.append('.'.join(key) + ': after rejects before encoding')
    for key, name in (('domain_sha256', 'layauto_v2/domain/terminal_relations.py'),
                      ('codec_sha256', 'layauto_v2/normalization/terminal_relations_codec.py')):
        assert after[key] == hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        checks.append(name + ': after runtime still current')
    result = {'status': 'passed', 'scope': 'existing CR12 independent receipts only',
              'checks': checks, 'check_count': len(checks),
              'after_domain_sha256': after['domain_sha256'],
              'after_codec_sha256': after['codec_sha256'],
              'limitations': ['No new product constructor, codec, capture or tests were executed.']}
    (OUT / 'evidence_metadata_outcome_audit.stdout.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
