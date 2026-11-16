"""Read-only W015 baseline probes. No oracle/helper or runtime mutation."""
from pathlib import Path
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import geometry_from_parse_result, build_geometry

FIX = ROOT / 'tests/fixtures/w003_m1'

def summary(result):
    return {'status': result.status, 'issues': [i.code for i in result.issues],
            'completed': [r.kind for r in result.completed],
            'captured_uris': [s.uri for s in result.sources]}

def main():
    normal = read_inputs(FIX / 'site_config.yaml')
    assert normal.status == 'success'
    cases = {'normal': summary(normal)}
    geometry = build_geometry(geometry_from_parse_result(normal))
    assert geometry.status == 'success' and geometry.value is not None
    local_sources = geometry.layout.gds.sources
    cases['geometry'] = {'status': geometry.status,
                         'local_gds_sources': [s.uri for s in local_sources],
                         'body_role_arity': len(geometry.body_evidence.sources),
                         'body_not_drawn_source': geometry.body_evidence.sources[0] not in local_sources}
    for name in ('no_body_key', 'missing_body_file', 'malformed_body',
                 'wrong_body_binding', 'missing_body_and_invalid_gds', 'body_enclosure'):
        with tempfile.TemporaryDirectory(prefix='w015-') as tmp:
            folder = Path(tmp)
            # Only captured reader inputs; do not copy answers/spec/helper data.
            for source in normal.sources:
                relative = Path(source.uri)
                if relative.is_absolute():
                    relative = relative.relative_to(FIX)
                target = folder / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.data)
            site_path = folder / 'site_config.yaml'
            site = json.loads(site_path.read_text())
            body_path = folder / 'body/context.json'
            header_path = folder / 'query/header.json'
            if name == 'no_body_key':
                del site['inputs']['body_context']
                site_path.write_text(json.dumps(site))
            elif name in ('missing_body_file', 'missing_body_and_invalid_gds'):
                body_path.unlink()
                if name.endswith('invalid_gds'):
                    (folder / 'source.gds').write_bytes(b'not a GDS stream')
            elif name == 'malformed_body':
                body_path.write_text('{')
            else:
                if name == 'wrong_body_binding':
                    body = json.loads(body_path.read_text())
                    body['source_gds']['sha256'] = '0' * 64
                    body_path.write_text(json.dumps(body))
                else:
                    body_path.write_bytes((FIX / 'failures/body_enclosure/body/context.json').read_bytes())
                header = json.loads(header_path.read_text())
                for entry in header['closure']['entries']:
                    entry['sha256'] = hashlib.sha256((folder / entry['uri']).read_bytes()).hexdigest()
                compact = json.dumps(header['closure']['entries'], sort_keys=True, separators=(',', ':'), ensure_ascii=False)
                header['closure']['sha256'] = hashlib.sha256(compact.encode()).hexdigest()
                header_path.write_text(json.dumps(header))
            result = read_inputs(site_path)
            cases[name] = summary(result)
    expected = {'no_body_key': ('error', 'SchemaValidationError'),
                'missing_body_file': ('error', 'RequiredBodyContextUnavailable'),
                'missing_body_and_invalid_gds': ('error', 'RequiredBodyContextUnavailable'),
                'malformed_body': ('error', None),
                'wrong_body_binding': ('error', 'BodySourceBindingMismatch'),
                'body_enclosure': ('success', None)}
    # Output raw observations before checking expectations; failure stays visible.
    print(json.dumps({'base': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                      'python': sys.version, 'platform': platform.platform(),
                      'command': 'python -B docs/tasks/W015/evidence/coupling_probe.py',
                      'cases': cases}, indent=2))
    for name, (status, code) in expected.items():
        assert cases[name]['status'] == status, (name, cases[name])
        if code is not None:
            assert cases[name]['issues'] == [code], (name, cases[name])

if __name__ == '__main__':
    main()
