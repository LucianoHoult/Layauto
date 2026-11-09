"""W011 actual-capture transforms and independent exact interval witnesses.

Only pytest temporary inputs are changed. Hand-written sets below are checked
against the accepted independent oracle; product helpers never supply answers.
"""
from __future__ import annotations

from fractions import Fraction

from w005_cases import FIXTURE, read_json, rebind, write_json
from w010_cases import build_local


EXPECTED_FIN_Y = {
    'MN0': ((24, 26), (34, 36), (44, 46), (54, 56), (64, 66)),
    'MP0': ((114, 116), (124, 126), (134, 136), (144, 146),
            (154, 156), (164, 166), (174, 176)),
}
EXPECTED_CHANNELS = {'MN0': (58, 20, 62, 70), 'MP0': (58, 110, 62, 180)}


def build(root=FIXTURE):
    from layauto_v2.normalization.channel_identity import build_channel_identity
    return build_channel_identity(build_local(root))


def change_seeds(root, object_name, rectangles):
    """Write the declared Calibre-like exact polygon syntax, including fractions.

    A missing device seed removes its response/request from the selected capture;
    it does not introduce a parser-unsupported empty polygon response.
    """
    requests_path, header_path = root / 'query/requests.json', root / 'query/header.json'
    requests, header = read_json(requests_path), read_json(header_path)
    request = next(row for row in requests['requests']
                   if row['capability'] == 'device_regions' and row['object'] == object_name)
    path = root / request['path']
    lines = path.read_text().splitlines()
    tag = lines[4]
    if rectangles:
        output = lines[:4]
        for bounds in rectangles:
            scaled = [Fraction(value) * 20 for value in bounds]
            assert all(value.denominator == 1 for value in scaled)
            x0, y0, x1, y1 = map(int, scaled)
            output.extend((tag, lines[5], 'p 1 4', f'{y0} {x0}', f'{y1} {x0}',
                           f'{y1} {x1}', f'{y0} {x1}'))
        output.append('END OF RESPONSE')
        path.write_text('\n'.join(output) + '\n')
        old = request['record_ids'][0]
        request['record_ids'] = [old] + [old + '_extra_' + str(i) for i in range(1, len(rectangles))]
    else:
        requests['requests'].remove(request)
        header['raw'] = [row for row in header['raw'] if row['uri'] != request['path']]
        path.unlink()
    write_json(requests_path, requests)
    write_json(header_path, header)
    rebind(root)


def change_cdl(root, which, before, after):
    path = root / (which + '.cdl')
    text = path.read_text()
    assert before in text
    path.write_text(text.replace(before, after))
    rebind(root)


def independent_fin_verdict(active, channel, fin):
    """Closed endpoint order and open-interval overlap, no product arithmetic."""
    horizontal = sorted((channel[0], channel[2], fin[0], fin[2]))
    vertical = sorted((channel[1], channel[3], fin[1], fin[3]))
    xw = [Fraction(a + b, 2) for a, b in zip(horizontal, horizontal[1:]) if a < b]
    yw = [Fraction(a + b, 2) for a, b in zip(vertical, vertical[1:]) if a < b]
    positive = any(channel[0] < x < channel[2] and fin[0] < x < fin[2]
                   and channel[1] < y < channel[3] and fin[1] < y < fin[3]
                   for x in xw for y in yw)
    if not positive:
        contact = (max(channel[0], fin[0]) <= min(channel[2], fin[2])
                   and max(channel[1], fin[1]) <= min(channel[3], fin[3]))
        return 'touch' if contact else 'outside'
    return ('qualified' if fin[0] <= channel[0] and channel[2] <= fin[2]
            and active[1] <= fin[1] and fin[3] <= active[3] else 'partial')


def unchecked_replace(record, **changes):
    """External tampering must be rejected when a public aggregate is rebuilt."""
    from dataclasses import fields
    value = object.__new__(type(record))
    for field in fields(record):
        object.__setattr__(value, field.name, changes.get(field.name, getattr(record, field.name)))
    return value
