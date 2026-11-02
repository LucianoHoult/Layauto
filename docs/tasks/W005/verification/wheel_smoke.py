import json
import sys
from pathlib import Path
import tempfile
import shutil
import hashlib
import layauto_v2
from layauto_v2.importers import read_inputs

fixture = Path(sys.argv[1]).resolve()
assert 'site-packages' in str(layauto_v2.__file__), layauto_v2.__file__
result = read_inputs(fixture / 'site_config.yaml')
assert result.status == 'success', result.issues
assert len(result.value['gds']['elements']) == 40
assert len(result.value['query']['net_regions']['records']) == 8
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory) / 'input'
    shutil.copytree(fixture, root)
    shutil.rmtree(root / 'query/normalized')
    raw = root / 'query/raw/device_info_Q17.txt'
    raw.write_bytes(raw.read_bytes().replace(b'END OF RESPONSE\n', b''))
    header_path = root / 'query/header.json'
    header = json.loads(header_path.read_text())
    for entry in header['raw']:
        entry['sha256'] = hashlib.sha256((root / entry['uri']).read_bytes()).hexdigest()
    header_path.write_text(json.dumps(header))
    failed = read_inputs(root / 'site_config.yaml')
    assert failed.status == 'error' and failed.issues[0].code == 'MissingTerminator', failed.issues
print(json.dumps({'installed_module': layauto_v2.__file__, 'accepted_shapes': 40, 'net_regions': 8, 'rebound_bad_raw': 'MissingTerminator'}))
