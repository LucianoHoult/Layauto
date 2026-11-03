"""Adopt final installed smoke from a genuine directory outside the checkout."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor

ROOT = Path('/workspace/Layauto')
ENV = Path('/workspace/work/w009-env')
OUT = ROOT / 'docs/tasks/W009/verification'
CWD = ENV / 'installed-cwd'
CWD.mkdir(parents=True, exist_ok=True)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def documents(text):
    decoder = json.JSONDecoder()
    result = []
    while text.strip():
        value, count = decoder.raw_decode(text.lstrip())
        result.append(value)
        text = text.lstrip()[count:]
    return result


def run(tag):
    py = ENV / ('clean-final-' + tag) / 'bin/python'
    name = 'source-external-smoke-' + tag
    args = [str(py), '-I', '-B', str(OUT / 'installed_smoke.py'), str(ROOT / 'tests/fixtures/w003_m1')]
    start = time.time()
    with (OUT / (name + '.txt')).open('wb') as stream:
        completed = subprocess.run(args, cwd=CWD, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'),
                                   stdout=stream, stderr=subprocess.STDOUT)
    data = (OUT / (name + '.txt')).read_bytes()
    record = {'command': args, 'cwd': str(CWD), 'exit_code': completed.returncode,
              'elapsed_seconds': round(time.time() - start, 3), 'output': name + '.txt',
              'output_sha256': sha(data), 'scope': 'adopted final source-external smoke'}
    (OUT / (name + '.json')).write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(record), flush=True)
    assert completed.returncode == 0, 'Source-external smoke failed: ' + name
    payload = documents(data.decode())
    assert payload[1]['checks']['status'] == 'passed'
    expected = json.loads((OUT / 'source-manifest.json').read_text())['runtime_files']
    assert payload[0]['environment']['package_manifest'] == expected
    assert payload[1]['checks']['unsupported_operator_error']['issue'] == 'UnsupportedRegionOperator'
    return record


def main():
    receipt = json.loads((OUT / 'receipt.json').read_text())
    assert receipt['status'] == 'passed'
    with ThreadPoolExecutor(max_workers=2) as pool:
        records = list(pool.map(run, ('312', '310')))
    for command in receipt['commands']:
        if command['output'].startswith('installed-smoke-'):
            command['interpretation'] = ('Intermediate installed-package import/composition check; cwd inside repository. '
                                         'Final source-external evidence is source-external-smoke-*.')
    receipt['commands'].extend(records)
    receipt['adopted_source_external_smoke'] = {str(i): record['output'] for i, record in zip(('312', '310'), records)}
    source = json.loads((OUT / 'source-manifest.json').read_text())
    assert all(sha((ROOT / path).read_bytes()) == digest for path, digest in source['files'].items())
    receipt['source_identity_rechecked_after_external_smoke'] = True
    (OUT / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    manifest = {str(path.relative_to(OUT)): sha(path.read_bytes()) for path in sorted(OUT.rglob('*'))
                if path.is_file() and path.name != 'evidence-manifest.json'}
    (OUT / 'evidence-manifest.json').write_text(json.dumps({'sha256': manifest}, ensure_ascii=False, indent=2) + '\n')
    print('Adopted two final source-external installed smokes.', flush=True)


if __name__ == '__main__':
    main()
