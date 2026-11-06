"""Offline finite W010 resource probe; never imported by the runtime.

Run from the checkout with its development interpreter:
  python -B docs/tasks/W010/performance_probe.py

The specimen writer below edits only temporary copies of the public synthetic
captures. It does not import test helpers, load an oracle, or invoke EDA. Added
M1 rectangles and duplicate CONTACT records are hand-selected pressure inputs;
the retained query/body evidence is not a proof of their device/net semantics.
"""
from __future__ import annotations

import argparse
from collections import Counter
import datetime
from fractions import Fraction
import gc
import hashlib
import json
from pathlib import Path
import platform
import resource
import shutil
import struct
import sys
import tempfile
import time


REPO = Path(__file__).resolve().parents[3]
# A direct script invocation otherwise searches docs/tasks/W010 first.
sys.path.insert(0, str(REPO))

from layauto_v2.domain.evidence import EvidenceRecord
from layauto_v2.domain.geometry import mapping
from layauto_v2.domain.local_connectivity import CONNECTOR_PAIRS
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import (
    build_effective_geometry, build_geometry, build_local_connectivity,
    geometry_from_parse_result,
)
from layauto_v2.normalization.local_connectivity_codec import decode_record, encode_record
from layauto_v2.state.local_connectivity import build_local_connectivity_draft


FIXTURE = REPO / 'tests/fixtures/w003_m1'


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha_file(path):
    return sha_bytes(path.read_bytes())


def manifest(root):
    return {str(path.relative_to(root)): sha_file(path)
            for path in sorted(root.rglob('*')) if path.is_file() and '__pycache__' not in path.parts}


def source_manifest():
    paths = list((REPO / 'layauto_v2').rglob('*.py')) + [REPO / 'layauto_v2/py.typed', REPO / 'pyproject.toml']
    return {str(path.relative_to(REPO)): sha_file(path) for path in sorted(paths)}


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def rebind(root):
    """Refresh only declared actual-byte hash links, preserving memberships."""
    site = read_json(root / 'site_config.yaml')  # This selected synthetic YAML is JSON syntax.
    body_path = root / site['inputs']['body_context']
    body = read_json(body_path)
    body['source_gds'] = {'uri': site['inputs']['gds'], 'sha256': sha_file(root / site['inputs']['gds'])}
    write_json(body_path, body)
    header_path = root / site['inputs']['query_header']
    header = read_json(header_path)
    for binding in (header['layout'], header['source_netlist'], header['target'],
                    *header['raw'], *header['closure']['entries']):
        binding['sha256'] = sha_file(root / binding['uri'])
    header['closure']['entries'].sort(key=lambda row: row['uri'])
    closure = json.dumps(header['closure']['entries'], sort_keys=True, separators=(',', ':'),
                         ensure_ascii=False).encode('utf-8')
    header['closure']['sha256'] = sha_bytes(closure)
    write_json(header_path, header)


def gds_records(data):
    offset = 0
    while offset < len(data):
        size, kind, datatype = struct.unpack('>HBB', data[offset:offset + 4])
        assert size >= 4 and offset + size <= len(data)
        yield kind, datatype, data[offset:offset + size]
        offset += size
    assert offset == len(data)


def gds_blocks(data):
    prefix, elements, suffix = [], [], []
    current = None
    seen = False
    for kind, datatype, record in gds_records(data):
        if kind == 8:
            assert current is None
            current, seen = [record], True
        elif current is not None:
            current.append(record)
            if kind == 17:
                elements.append(b''.join(current))
                current = None
        elif seen:
            suffix.append(record)
        else:
            prefix.append(record)
    assert current is None
    return b''.join(prefix), elements, b''.join(suffix)


def gds_record(kind, datatype, payload=b''):
    return struct.pack('>HBB', len(payload) + 4, kind, datatype) + payload


def rectangle_record(layer, bounds):
    x0, y0, x1, y1 = bounds
    xy = (x0, y0, x1, y0, x1, y1, x0, y1, x0, y0)
    return b''.join((gds_record(8, 0), gds_record(13, 2, struct.pack('>h', layer)),
                     gds_record(14, 2, struct.pack('>h', 0)),
                     gds_record(16, 3, struct.pack('>10i', *xy)), gds_record(17, 0)))


def element_layer(element):
    for kind, datatype, record in gds_records(element):
        if kind == 13:
            return struct.unpack('>h', record[4:])[0]
    raise AssertionError('specimen BOUNDARY has no layer')


def prepare_case(root, name):
    shutil.copytree(FIXTURE, root)
    # Rebinding raw captures is enough for the component. Remove optional caches
    # rather than manufacture query answers for altered geometry.
    shutil.rmtree(root / 'query/normalized', ignore_errors=True)
    changes = []
    if name == 'special_cut_islands':
        (root / 'source.gds').write_bytes((FIXTURE / 'special/cut_islands/source.gds').read_bytes())
        header = read_json(root / 'query/header.json')
        header['top_identities']['layout'] = 'CUT_ISLANDS_SYNTH'
        write_json(root / 'query/header.json', header)
        body = read_json(root / 'body/context.json')
        body['top'] = 'CUT_ISLANDS_SYNTH'
        write_json(root / 'body/context.json', body)
        for name in ('iXref.temp', 'nXref.temp'):
            path = root / 'query/raw' / name
            lines = path.read_text(encoding='utf-8').splitlines()
            lines[1] = '# SVDB: Layout Primary CUT_ISLANDS_SYNTH'
            lines[7] = lines[7].replace('INV_M1_SYNTH', 'CUT_ISLANDS_SYNTH', 1)
            path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        changes.append('Existing special GDS, temporary layout top/raw/body header rebinding; no extraction claim.')
    elif name == 'extra_20_isolated_M1':
        path = root / 'source.gds'
        prefix, elements, suffix = gds_blocks(path.read_bytes())
        bounds = [(130 + 2 * (index % 10), 190 + 3 * (index // 10),
                   131 + 2 * (index % 10), 191 + 3 * (index // 10)) for index in range(20)]
        elements.extend(rectangle_record(9, box) for box in bounds)
        path.write_bytes(prefix + b''.join(elements) + suffix)
        changes.append({'appended_M1_rectangles_nm': bounds, 'purpose': '20 isolated local geometric nodes, away from connectors'})
    elif name == 'extra_8_duplicate_CONTACT':
        path = root / 'source.gds'
        prefix, elements, suffix = gds_blocks(path.read_bytes())
        original = next(element for element in elements if element_layer(element) == 7)
        elements.extend([original] * 8)
        path.write_bytes(prefix + b''.join(elements) + suffix)
        changes.append('Append eight exact copies of the first drawn CONTACT BOUNDARY; retain each new record identity/audit.')
    elif name != 'normal':
        raise ValueError('unknown performance case: ' + name)
    rebind(root)
    return changes


def measure(function):
    started = time.perf_counter()
    result = function()
    return result, time.perf_counter() - started


def counts(draft):
    by_layer = Counter(node.layer for node in draft.nodes)
    by_ref = {node.ref: node for node in draft.nodes}
    records = draft.effective.base.layout.records
    connector_records = tuple(record for record in records if record.layer in CONNECTOR_PAIRS)
    same_piece_upper = sum(len(node.region.rectangles) * len(other.region.rectangles)
                           for index, node in enumerate(draft.nodes) for other in draft.nodes[index + 1:]
                           if node.layer == other.layer)
    connector_candidates = sum(by_layer[layer] for record in connector_records
                               for layer in CONNECTOR_PAIRS[record.layer])
    connector_piece_upper = sum(len(node.region.rectangles) for record in connector_records
                                for layer in CONNECTOR_PAIRS[record.layer] for node in draft.nodes if node.layer == layer)
    enclosure_slabs = 0
    enclosure_piece_scan_upper = 0
    for audit in draft.audits:
        node = by_ref[audit.node_ref]
        record = next(record for record in connector_records if record.id == audit.connector_id)
        left, right = record.rect.x0 - audit.margin_ticks, record.rect.x1 + audit.margin_ticks
        xs = {left, right} | {Fraction(x) for piece in node.region.rectangles for x in (piece.x0, piece.x1)
                             if left < x < right}
        slab_count = len(xs) - 1
        enclosure_slabs += slab_count
        enclosure_piece_scan_upper += slab_count * len(node.region.rectangles)
    return {'drawn_records': len(records), 'nodes': len(draft.nodes), 'edges': len(draft.edges),
            'same_layer_edges': sum(edge.kind == 'same_layer' for edge in draft.edges),
            'connector_edges': len(connector_records), 'components': len(draft.components),
            'enclosure_sides': len(draft.audits), 'local_enclosure_status': draft.local_enclosure_status,
            'nodes_per_layer': dict(sorted(by_layer.items())),
            'pieces_per_region': sorted(len(node.region.rectangles) for node in draft.nodes),
            'max_pieces_per_region': max((len(node.region.rectangles) for node in draft.nodes), default=0),
            'same_layer_region_pair_candidates': sum(count * (count - 1) // 2 for count in by_layer.values()),
            'same_layer_piece_pair_upper_bound': same_piece_upper,
            'connector_side_region_candidates': connector_candidates,
            'connector_side_piece_checks_upper_bound': connector_piece_upper,
            'enclosure_x_slabs': enclosure_slabs,
            'enclosure_piece_scan_upper_bound': enclosure_piece_scan_upper}


def run_case(root, name):
    changes = prepare_case(root, name)
    parsed, reader_s = measure(lambda: read_inputs(root / 'site_config.yaml'))
    assert parsed.status == 'success', parsed.issues
    geometry, w008_s = measure(lambda: build_geometry(geometry_from_parse_result(parsed)))
    assert geometry.status == 'success', geometry.issues
    effective, w009_s = measure(lambda: build_effective_geometry(geometry))
    assert effective.status == 'success', effective.issues
    rules_source = next(record for record in effective.completed if record.kind == 'tech').sources[6]
    rules = EvidenceRecord('rules', mapping(mapping(geometry.input.value['tech'])['rules']), (rules_source,))
    neutral, neutral_s = measure(lambda: build_local_connectivity_draft(effective.value, rules))
    result, public_s = measure(lambda: build_local_connectivity(effective))
    assert result.status == 'success' and result.value == neutral, result.issues
    wire, encode_s = measure(lambda: encode_record(result))
    restored, decode_s = measure(lambda: decode_record(wire))
    assert restored == result
    data = {'case': name, 'specimen_changes': changes,
            'capture_sources_sha256': {str(source.uri): source.sha256 for source in parsed.sources},
            'source_gds_bytes': (root / 'source.gds').stat().st_size,
            'source_gds_sha256': sha_file(root / 'source.gds'),
            'counts': counts(result.value),
            'wall_seconds': {'W005_read_inputs': reader_s, 'W008_adapter_and_build': w008_s,
                             'W009_build_effective_geometry': w009_s, 'neutral_builder': neutral_s,
                             'public_build_local_connectivity': public_s,
                             'result_encode': encode_s, 'result_decode': decode_s,
                             'result_roundtrip_encode_plus_decode': encode_s + decode_s},
            'result_wire_bytes': len(wire), 'result_wire_sha256': sha_bytes(wire),
            'wire_roundtrip_equal': restored == result,
            'process_peak_rss_kib_cumulative': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'semantic_digest': result.value.semantic_digest}
    del restored, wire, result, neutral, effective, geometry, parsed
    gc.collect()
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path(__file__).with_name('performance.json'))
    parser.add_argument('--cases', nargs='+', default=['normal', 'special_cut_islands',
                                                      'extra_20_isolated_M1', 'extra_8_duplicate_CONTACT'])
    args = parser.parse_args()
    before = source_manifest()
    fixture_before = manifest(FIXTURE)
    receipt = {'schema': 'layauto-w010-finite-performance/1',
               'actor': '/root/graph_implementation (implementation role, not independent reviewer)',
               'started_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'command_argv': [sys.executable, '-B', *sys.argv], 'cwd': str(Path.cwd()),
               'python': sys.version, 'platform': platform.platform(), 'executable': sys.executable,
               'probe_sha256': sha_file(Path(__file__)), 'source_files_sha256': before,
               'source_manifest_sha256': sha_bytes(json.dumps(before, sort_keys=True, separators=(',', ':')).encode()),
               'fixture_manifest_sha256': sha_bytes(json.dumps(fixture_before, sort_keys=True, separators=(',', ':')).encode()),
               'method': 'Single warm-process sample per case; no statistical or production performance assurance. No test helper imports. All altered specimens are temporary actual captures, rebound before W005/W008/W009. Codec times include full nested old receipt reconstruction and new graph validation.',
               'complexity': {'core_candidates': 'N nodes, C connector records, P maximum pieces per region. O(N^2 P^2 + C N P) contact scan; independent enclosure up to O(C P^2 log P); components O(N+E).',
                              'aggregate_and_authentication': 'Neutral builder calculates graph and then constructor reconstructs it. Public builder authenticates complete W009 wire input before work, then result constructor authenticates it again and rebuilds expected neutral graph. Decode rebuilds nested W009/W008/captured direct/readback records and graph constructors; source data is retained repeatedly across nested receipt wire. Thus measured public/codec cost includes repeated capture authentication, parsing, canonical encoding, hashing and memory allocations beyond core candidate complexity.',
                              'memory': 'Stored graph O(N+E+C) plus exact region pieces and complete retained input. Wire retains nested full captured receipts; reported wire size is actual encoded bytes. Linux ru_maxrss is a cumulative process high watermark, not a per-case incremental allocation measurement.'},
               'cases': [], 'status': 'running'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.output, receipt)
    (REPO / 'work').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='w010-performance-', dir=REPO / 'work') as temp:
        for index, name in enumerate(args.cases):
            print('running ' + name, flush=True)
            receipt['cases'].append(run_case(Path(temp) / ('case-' + str(index)), name))
            write_json(args.output, receipt)
            print(json.dumps({'case': name, 'counts': receipt['cases'][-1]['counts'],
                              'wall_seconds': receipt['cases'][-1]['wall_seconds'],
                              'wire_bytes': receipt['cases'][-1]['result_wire_bytes']}, sort_keys=True), flush=True)
    receipt['source_unchanged_during_probe'] = source_manifest() == before
    receipt['fixture_unchanged_during_probe'] = manifest(FIXTURE) == fixture_before
    receipt['finished_at_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    receipt['status'] = 'pass' if receipt['source_unchanged_during_probe'] and receipt['fixture_unchanged_during_probe'] else 'source_changed'
    write_json(args.output, receipt)
    assert receipt['status'] == 'pass', 'source changed during resource observation; rerun on the final source'


if __name__ == '__main__':
    main()
