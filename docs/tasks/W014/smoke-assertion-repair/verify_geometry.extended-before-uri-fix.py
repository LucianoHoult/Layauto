"""Independent stdlib-only raw GDS/body audit for installed-smoke expectations.

No runtime, fixture helpers, oracle, spec or expected file is imported/read.
The accepted format owner supplies the sole nominal tick; raw REAL8 is checked
against that candidate with exact half-ULP arithmetic, and XY is never rounded.
"""
from __future__ import annotations

from collections import Counter
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[4]
FIXTURE = ROOT / 'tests/fixtures/w003_m1'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def real8(data: bytes) -> tuple[Fraction, Fraction]:
    assert len(data) == 8 and any(data)
    power = (data[0] & 0x7f) - 64
    exponent = Fraction(16) ** power
    mantissa = int.from_bytes(data[1:], 'big')
    assert 2 ** 52 <= mantissa < 2 ** 56
    value = Fraction(mantissa, 2 ** 56) * exponent
    return (-value if data[0] & 0x80 else value), exponent / 2 ** 56


def boundary_records(path: Path, nominal: tuple[Fraction, Fraction], tick_nm: Fraction) -> tuple[list[dict[str, object]], dict[str, object]]:
    data, offset = path.read_bytes(), 0
    output: list[dict[str, object]] = []
    current = None
    units = None
    while offset < len(data):
        length, kind, dtype = struct.unpack('>HBB', data[offset:offset + 4])
        assert length >= 4 and length % 2 == 0 and offset + length <= len(data)
        payload = data[offset + 4:offset + length]
        if (kind, dtype) == (3, 5):
            assert units is None and len(payload) == 16
            units = []
            for index, target in enumerate(nominal):
                actual, ulp = real8(payload[index * 8:(index + 1) * 8])
                assert abs(actual - target) <= ulp / 2
                units.append({'raw_hex': payload[index * 8:(index + 1) * 8].hex(),
                              'exact': str(actual), 'nominal': str(target), 'ulp': str(ulp)})
        if (kind, dtype) == (8, 0):
            assert current is None
            current = {'offset': offset}
        elif current is not None:
            if (kind, dtype) == (13, 2):
                current['layer'] = struct.unpack('>h', payload)[0]
            elif (kind, dtype) == (14, 2):
                current['datatype'] = struct.unpack('>h', payload)[0]
            elif (kind, dtype) == (16, 3):
                values = struct.unpack('>' + 'i' * (len(payload) // 4), payload)
                xy = tuple(zip(values[::2], values[1::2]))
                assert len(xy) == 5 and xy[0] == xy[-1]
                xs, ys = {x for x, _ in xy}, {y for _, y in xy}
                assert len(xs) == len(ys) == 2
                current['bbox_nm'] = tuple(Fraction(value) * tick_nm for value in (min(xs), min(ys), max(xs), max(ys)))
            elif (kind, dtype) == (17, 0):
                output.append(current)
                current = None
        offset += length
    assert current is None and units is not None and offset == len(data)
    return output, {'source_gds_sha256': sha(data), 'raw_units_binding': units}


def margins(outer: tuple[Fraction, ...], inner: tuple[Fraction, ...]) -> tuple[Fraction, ...]:
    return inner[0] - outer[0], inner[1] - outer[1], outer[2] - inner[2], outer[3] - inner[3]


def main() -> None:
    formats = json.loads((FIXTURE / 'tech/formats.json').read_text())['unit_scale_contract']
    tick = formats['nominal_tick_m']
    tick_nm = Fraction(int(tick['numerator']), int(tick['denominator'])) * 10 ** 9
    first = formats['gds_units_first_nominal']
    nominal = Fraction(int(first['numerator']), int(first['denominator'])), tick_nm / 10 ** 9
    layers = json.loads((FIXTURE / 'tech/drawn.json').read_text())['layers']
    names = {(row['stream_key']['layer'], row['stream_key']['datatype']): row['name'] for row in layers}
    cases = {}
    geometry = {}
    for label, folder in (('normal', FIXTURE), ('extraction-mismatch', FIXTURE / 'failures/extraction_mismatch')):
        records, metadata = boundary_records(folder / 'source.gds', nominal, tick_nm)
        assert len(records) == 40
        for row in records:
            row['name'] = names[(row['layer'], row['datatype'])]
        body_bytes = (folder / 'body/context.json').read_bytes()
        body = json.loads(body_bytes)
        assert body['source_gds']['sha256'] == metadata['source_gds_sha256']
        local = {row['id']: row for row in body['local_bindings']}
        external = {row['id']: row for row in body['shapes']}
        for row in local.values():
            matches = [record for record in records if record['name'] == row['layer'] and record['bbox_nm'] == tuple(row['bbox'])]
            assert len(matches) == 1
        actives = sorted((row['bbox_nm'] for row in records if row['name'] == 'OD'), key=lambda box: box[1])
        assert len(actives) == 2
        active_margins = {'MN0': margins(tuple(local['BN']['bbox']), actives[0]),
                          'MP0': margins(tuple(local['BP']['bbox']), actives[1])}
        assert active_margins['MN0'] == ((20, 20, 20, 26) if label == 'extraction-mismatch' else (20, 20, 20, 20))
        assert active_margins['MP0'] == (20, 10, 20, 20)
        taps = {}
        for association in body['associations']:
            device = association['device']
            tap_box = tuple(external[association['tap']]['bbox'])
            bm = margins(tuple(external[association['external_body']]['bbox']), tap_box)
            rm = margins(tuple(external[association['external_rail']]['bbox']), tap_box)
            assert min(bm) == 8 and min(rm) == 2
            taps[device] = {'body_margins_nm': bm, 'rail_margins_nm': rm}
        def area(box: tuple[Fraction, ...]) -> Fraction:
            return (box[2] - box[0]) * (box[3] - box[1])
        poly = tuple(record['bbox_nm'] for record in records if record['name'] == 'POLY')
        assert len(poly) == 1
        def intersection(a: tuple[Fraction, ...], b: tuple[Fraction, ...]) -> tuple[Fraction, ...] | None:
            box = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
            return box if box[2] > box[0] and box[3] > box[1] else None
        channels = tuple(intersection(active, poly[0]) for active in actives)
        assert all(channel is not None for channel in channels)
        fins = tuple(record['bbox_nm'] for record in records if record['name'] == 'FIN')
        counts = {device: sum(fin[0] <= channel[0] and fin[2] >= channel[2]
                              and fin[1] >= active[1] and fin[3] <= active[3]
                              and intersection(fin, channel) is not None for fin in fins)
                  for device, active, channel in zip(('MN0', 'MP0'), actives, channels)}
        assert counts == {'MN0': 4 if label == 'extraction-mismatch' else 5, 'MP0': 7}
        local_area = sum((area(record['bbox_nm']) for record in records
                          if record['name'] in ('BODY_N', 'BODY_P', 'OD', 'POLY', 'LI', 'M1')), Fraction())
        local_area -= sum((area(channel) for channel in channels), Fraction())
        assert local_area == (34634 if label == 'extraction-mismatch' else 35090)
        cases[label] = {**metadata, 'body_context_sha256': sha(body_bytes), 'boundary_record_count': len(records),
                        'layer_counts': dict(Counter(row['name'] for row in records)),
                        'raw_FIN_qualified_counts': counts, 'local_target_area_nm2_from_raw_rectangles': local_area,
                        'actives_nm': {'MN0': actives[0], 'MP0': actives[1]}, 'active_margins_nm': active_margins,
                        'tap_margins_nm': taps, 'local_bindings': body['local_bindings'],
                        'external_shapes': body['shapes'], 'associations': body['associations']}
        geometry[label] = records
    differences = []
    for before, after in zip(geometry['normal'], geometry['extraction-mismatch']):
        assert before['layer'] == after['layer'] and before['datatype'] == after['datatype']
        if before['bbox_nm'] != after['bbox_nm']:
            differences.append({'layer': before['name'], 'normal_bbox_nm': before['bbox_nm'], 'mismatch_bbox_nm': after['bbox_nm']})
    assert len(differences) == 1 and differences[0]['layer'] == 'OD'
    assert cases['normal']['local_bindings'] == cases['extraction-mismatch']['local_bindings']
    assert cases['normal']['external_shapes'] == cases['extraction-mismatch']['external_shapes']
    assert cases['normal']['associations'] == cases['extraction-mismatch']['associations']
    # Existing resource captures bind the same raw bytes; no new product chain is run.
    for case, folder in (('normal-direct', FIXTURE), ('extraction-mismatch', FIXTURE / 'failures/extraction_mismatch')):
        report = json.loads((ROOT / 'docs/tasks/W014/resources-r2' / ('w014-' + case + '.json')).read_text())
        selected_gds = [source for source in report['capture_sources'] if Path(source['uri']).name == 'source.gds']
        assert len(selected_gds) == 1 and selected_gds[0]['sha256'] == sha((folder / 'source.gds').read_bytes())
    normal_capture = json.loads((ROOT / 'docs/tasks/W014/resources-r2/w014-normal-direct.json').read_text())
    mismatch_capture = json.loads((ROOT / 'docs/tasks/W014/resources-r2/w014-extraction-mismatch.json').read_text())
    normal_sources = {row['uri']: row['sha256'] for row in normal_capture['capture_sources']}
    mismatch_sources = {row['uri']: row['sha256'] for row in mismatch_capture['capture_sources']}
    assert set(normal_sources) == set(mismatch_sources) and len(normal_sources) == 31
    changed_capture_uris = sorted(uri for uri in normal_sources if normal_sources[uri] != mismatch_sources[uri])
    assert changed_capture_uris == ['body/context.json', 'query/header.json', 'query/normalized/device_regions.yaml', 'query/raw/device_info_Q17.txt', 'source.gds']
    result = {'classification': 'stdlib-raw-GDS-body-math-not-product-smoke', 'status': 'passed',
              'script_sha256': sha(Path(__file__).read_bytes()), 'python': sys.version,
              'nominal_tick_nm': tick_nm, 'cases': cases, 'only_drawn_bbox_difference': differences,
              'captured_source_count_each': 31, 'changed_capture_uris': changed_capture_uris,
              'audit': ['40 raw BOUNDARY records in each source', 'all body local bindings uniquely match actual raw GDS',
                        'only lower OD active changes; BODY_N/P, local rails and external bodies/taps/rails are unchanged',
                        'normal MN0 margins 20/20/20/20; mismatch 20/20/20/26; both min20',
                        'MP0 margins remain20/10/20/20; external tap min8/2 unchanged',
                        'R2 existing captured GDS hashes agree; no product chain rerun'],
              'not_run': ['reader', 'normalization', 'resource product chain', 'installed smoke', 'final matrices']}
    def default(value: object) -> object:
        if type(value) is Fraction:
            return int(value) if value.denominator == 1 else str(value)
        raise TypeError(type(value).__name__)
    print(json.dumps(result, indent=2, default=default))


if __name__ == '__main__':
    main()
