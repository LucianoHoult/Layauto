import hashlib
import json
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from layauto_v2.domain.codec import digest
from layauto_v2.importers import read_inputs

fixture = Path('tests/fixtures/w003_m1').resolve()
with TemporaryDirectory(prefix='w005-review-') as tmp:
    for case in ('cache', 'escaped_note', 'literal_note'):
        root = Path(tmp) / case
        shutil.copytree(fixture, root)
        if case == 'cache':
            path = root / 'query/normalized/device_regions.yaml'
            data = json.loads(path.read_text(encoding='utf-8'))
            data['schema_version'] = chr(0xD800)
            path.write_text(json.dumps(data) + '\n', encoding='utf-8')
        else:
            path = root / 'site_config.yaml'
            data = json.loads(path.read_text(encoding='utf-8'))
            data['note'] = 'example ' + chr(0x1F600)
            path.write_text(json.dumps(data, ensure_ascii=(case == 'escaped_note')) + '\n', encoding='utf-8')
            header_path = root / 'query/header.json'
            header = json.loads(header_path.read_text(encoding='utf-8'))
            for entry in header['closure']['entries']:
                if entry['uri'] == 'site_config.yaml':
                    entry['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
            closure = json.dumps(header['closure']['entries'], sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
            header['closure']['sha256'] = hashlib.sha256(closure).hexdigest()
            header_path.write_text(json.dumps(header) + '\n', encoding='utf-8')
        try:
            result = read_inputs(root / 'site_config.yaml')
            print(case, 'status=', result.status, 'issues=', [x.code for x in result.issues])
            if result.value is not None:
                print(case, 'note=', ascii(result.value['config']['note']))
                digest(result.value)
                print(case, 'digest_ok')
        except UnicodeEncodeError as exc:
            print(case, type(exc).__name__, str(exc))
