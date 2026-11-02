"""Independent test input transformations; never imported by the product."""
from __future__ import annotations

import hashlib
import json
import shutil
import struct
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures' / 'w003_m1'


def read_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob('*')) if p.is_file()}


def copy_input(tmp_path: Path) -> Path:
    root = tmp_path / 'input'
    shutil.copytree(FIXTURE, root)
    return root


def apply_case(root: Path, name: str) -> dict:
    case = next(x for x in read_json(FIXTURE / 'failures/cases.json')['cases'] if x['id'] == name)
    for target, source in case['replacement_files'].items():
        shutil.copyfile(FIXTURE / 'failures' / source, root / target)
    for target in case['remove_files']:
        (root / target).unlink()
    return case


def without_cache(root: Path) -> None:
    shutil.rmtree(root / 'query/normalized', ignore_errors=True)


def rebind(root: Path) -> None:
    """Recompute actual-byte bindings, retaining the supplied closure membership."""
    site = read_json(root / 'site_config.yaml')
    context_path = root / site['inputs']['body_context']
    if context_path.exists():
        body = read_json(context_path)
        body['source_gds']['uri'] = site['inputs']['gds']
        body['source_gds']['sha256'] = sha(root / site['inputs']['gds'])
        write_json(context_path, body)
    header_path = root / site['inputs']['query_header']
    header = read_json(header_path)
    for binding in [header['layout'], header['source_netlist'], header['target'], *header['raw'], *header['closure']['entries']]:
        path = root / binding['uri']
        if path.exists():
            binding['sha256'] = sha(path)
    header['closure']['entries'].sort(key=lambda x: x['uri'])
    canonical = json.dumps(header['closure']['entries'], sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    header['closure']['sha256'] = hashlib.sha256(canonical).hexdigest()
    write_json(header_path, header)


def renamed_input(root: Path) -> dict:
    """Independent byte transforms of the selected subset, with no parser/helper use."""
    old_top, new_top = 'INV_M1_SYNTH', 'SECOND_CELL'
    renames = {old_top: new_top, 'MN0': 'N_DEVICE', 'MP0': 'P_DEVICE', 'Q17': 'Q101', 'Q93': 'Q202',
               'n_a': 'sig_a', 'n_y': 'sig_y', 'n_lo': 'rail_lo', 'n_hi': 'rail_hi'}
    dx, dy = 10, -3
    raw = (root / 'source.gds').read_bytes()
    records = []
    offset = 0
    while offset < len(raw):
        size, kind, data_type = struct.unpack('>HBB', raw[offset:offset + 4])
        payload = raw[offset + 4:offset + size]
        if kind == 6:  # STRNAME
            payload = new_top.encode('ascii')
            payload += b'\0' * (len(payload) % 2)
        if kind == 16:  # XY
            coords = list(struct.unpack('>' + 'i' * (len(payload) // 4), payload))
            points = [(coords[i] + dx, coords[i + 1] + dy) for i in range(0, len(coords), 2)]
            corners = points[:-1][::-1]
            corners = corners[1:] + corners[:1]
            points = corners + corners[:1]
            payload = struct.pack('>' + 'i' * (2 * len(points)), *(v for point in points for v in point))
        records.append((kind, struct.pack('>HBB', len(payload) + 4, kind, data_type) + payload))
        offset += size
    prefix, elements, suffix = [], [], []
    current = None
    seen_elements = False
    for kind, record in records:
        if kind == 8:  # BOUNDARY
            current = [record]
            seen_elements = True
        elif current is not None:
            current.append(record)
            if kind == 17:  # ENDEL
                elements.append(b''.join(current))
                current = None
        elif seen_elements:
            suffix.append(record)
        else:
            prefix.append(record)
    (root / 'source.gds').write_bytes(b''.join(prefix + elements[::-1] + suffix))
    for name in ('source.cdl', 'target.cdl'):
        lines = []
        for line in (root / name).read_text().splitlines():
            for old, new in renames.items():
                line = line.replace(old, new)
            fields = line.split()
            if fields and fields[0] in ('N_DEVICE', 'P_DEVICE'):
                fields[6:] = fields[6:][::-1]
                line = '  '.join(fields).replace('NFIN=5', 'NFIN=6')
            lines.append(line)
        (root / name).write_text('\n'.join(lines) + '\n')
    header = read_json(root / 'query/header.json')
    requests = read_json(root / 'query/requests.json')
    paths = {}
    for i, ref in enumerate(header['raw']):
        old_path = ref['uri']
        path = root / old_path
        lines = []
        for line in path.read_text().splitlines():
            for old, new in renames.items():
                line = line.replace(old, new)
            fields = line.split()
            if ref['capability'] in ('device_regions', 'net_regions') and len(fields) == 2:
                try:
                    y, x = map(int, fields)
                except ValueError:
                    pass
                else:
                    line = f'{y + dy * 20} {x + dx * 20}'
            lines.append(line)
        new_path = f'query/raw/capture_{i}.txt'
        (root / new_path).write_text('\n'.join(lines) + '\n')
        path.unlink()
        paths[old_path] = new_path
        ref['uri'] = new_path
    for request in requests['requests']:
        request['path'] = paths[request['path']]
        request['object'] = renames.get(request['object'], request['object'])
        request['record_ids'] = ['SECOND_' + x for x in request['record_ids']]
    header['top_identities'] = {'layout': new_top, 'source': new_top}
    header['header_id'] = header['query_run_id'] = 'second.synthetic.query'
    write_json(root / 'query/requests.json', requests)
    write_json(root / 'query/header.json', header)
    body = read_json(root / 'body/context.json')
    body['top'] = new_top
    for key in ('frame_bbox_nm',):
        body[key] = [v + (dx if i % 2 == 0 else dy) for i, v in enumerate(body[key])]
    for obj in body['local_bindings'] + body['shapes']:
        obj['bbox'] = [v + (dx if i % 2 == 0 else dy) for i, v in enumerate(obj['bbox'])]
    for association in body['associations']:
        association['device'] = renames[association['device']]
    write_json(root / 'body/context.json', body)
    without_cache(root)
    rebind(root)
    return {'top': new_top, 'dx': dx, 'dy': dy, 'device': 'N_DEVICE', 'query_device': 'Q101', 'paths': paths}
