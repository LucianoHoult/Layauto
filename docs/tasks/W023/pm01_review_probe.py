"""Independently check two close negative process coordinates through public readback."""
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import yaml

from layauto_v2.domain.codec import digest
from layauto_v2.domain.publication_codec import decode_record, encode_record
from layauto_v2.pipeline import publish_stage2
from layauto_v2.repository import PublicationRepository
from w005_cases import rebind, write_json
from w018_cases import COORDINATE_URI, build_geometry_from_site
from w023_cases import capture, sample


D = 2**7500
OWNERS = ('drawn', 'derived', 'physical', 'formats', 'coordinate', 'rules')


def independent_model(root, coordinates):
    """Form the W018 identity from selected file hashes and independently resolved axes."""
    bundle = json.loads((root / 'tech.json').read_bytes())['owners']
    profile = json.loads((root / bundle['physical']['path']).read_bytes())['fin_count_profile']
    source_paths = ['tech.json', *(bundle[name]['path'] for name in OWNERS)]
    sources = [{'uri': uri, 'sha256': sha256((root / uri).read_bytes()).hexdigest(), 'line': None,
                'column': None, 'byte_offset': None, 'record_index': None, 'field': None}
               for uri in source_paths]
    # W008 authenticates the GDS scale without invoking the W018 model or W023 codec.
    geometry = build_geometry_from_site(root)
    assert geometry.status == 'success'
    unit = geometry.value.layout.units
    assert unit.canonical_tick_nm == 1 and coordinates['frame_origin_nm'] == [0, 0]

    def length(owner, field):
        if field in owner:
            value = owner[field]
        else:
            reference = owner[field + '_ref']
            assert reference.startswith('physical#/fin_count_profile/')
            value = profile[reference.split('/')[-1]]
        if isinstance(value, int):
            return Fraction(value)
        return Fraction(int(value['numerator']), int(value['denominator']))

    def pair(number):
        return hex(number.numerator), hex(number.denominator)

    def grid_edges(row):
        return tuple(hex(row[key]) for key in ('offset_dbu', 'pitch_dbu', 'cells'))

    axes = {}
    for name, row in coordinates['layers'].items():
        kind = row['projection']
        if kind == 'none':
            axes[name] = ('none',)
        elif kind == '2d_cells':
            axes[name] = (kind, grid_edges(row['x_edges']), grid_edges(row['y_edges']))
        else:
            assert kind == '1d_track'
            lower = length(row['first_centre'], 'lower_edge_nm')
            width = length(row['first_centre'], 'width_nm')
            lengths = (pair(lower + width / 2), pair(length(row, 'pitch_nm')), pair(width))
            start, end = row['index_range_inclusive']
            axes[name] = (kind, row['index_axis'], lengths, hex(start), hex(end))

    return digest({'schema': 'layauto-bound-layer-projections/1', 'origin_nm': ('0x0', '0x0'),
                   'sources': sources, 'unit_ref': unit.ref.to_value(), 'layers': axes})


def publish(root, step):
    owner = root / COORDINATE_URI
    config = yaml.safe_load(owner.read_bytes())
    config['coordinate_projection']['layers']['BTAP_P'] = {
        'projection': '1d_track', 'index_axis': 'x', 'pitch_nm': 7, 'index_range_inclusive': [-2, 4],
        'first_centre': {'basis': 'lower_edge_plus_half_width',
                         'lower_edge_nm': {'numerator': str(1 - D), 'denominator': str(D)},
                         'width_nm': {'numerator': '2', 'denominator': str(D + step)}}}
    write_json(owner, config)
    rebind(root)
    selected = json.loads(owner.read_bytes())['coordinate_projection']
    model_id = independent_model(root, selected)
    # Single closed-form rational; both numerator and denominator exceed the
    # default decimal limit, while every original input component fits.
    expected = Fraction((1 - D) * (D + step) + D, D * (D + step))
    assert expected.numerator < -(10**4300) and expected.denominator > 10**4300
    repo = PublicationRepository()
    ready, request = capture(repo, root, 'review-pm01')
    assert repo.load_head('L') is None and ready.attempt.revision == 1
    context = publish_stage2(repo, request)
    head = repo.read(context.head_ref)
    snapshot = repo.read(head.snapshot_ref)
    restored = decode_record(encode_record(snapshot))
    assert restored == snapshot
    coord = restored.state['coordinates']
    axis = coord['axes']['BTAP_P']
    actual = axis['first_centre_nm']
    assert type(actual) is Fraction and actual == expected
    assert (axis['index_axis'], axis['first_index'], axis['last_index']) == ('x', -2, 4)
    assert type(axis['pitch_nm']) is Fraction and axis['pitch_nm'] == 7
    assert axis['width_nm'] == Fraction(2, D + step)
    assert coord['origin_nm'] == (0, 0) and all(type(n) is int for n in coord['origin_nm'])
    assert coord['model_id'] == model_id
    assert head.version == snapshot.version == 0 and head.eco_commits == ()
    assert restored.state['layers']['BTAP_P']['availability'] == 'no_local_records'
    assert len(restored.state['occupancy']) == 312
    attempt = repo.load_attempt(ready.run_id)
    assert (attempt.phase, attempt.revision) == ('sealed_open', 2)

    summary = {'width_denominator_offset': step, 'owner_bytes': owner.stat().st_size,
               'owner_sha256': sha256(owner.read_bytes()).hexdigest(), 'model_id': model_id,
               'version': snapshot.version, 'phase': attempt.phase, 'revision': attempt.revision,
               'numerator_bits': actual.numerator.bit_length(), 'denominator_bits': actual.denominator.bit_length(),
               'exact_pair_sha256': sha256(f'{hex(actual.numerator)}/{hex(actual.denominator)}'.encode()).hexdigest(),
               'snapshot': head.snapshot_ref.id}
    return actual, summary


if __name__ == '__main__':
    initial_limit = sys.get_int_max_str_digits()
    assert initial_limit == sys.int_info.default_max_str_digits == 4300
    with TemporaryDirectory() as tmp:
        root = sample(Path(tmp))
        first, row1 = publish(root, 1)
        second, row2 = publish(root, 3)
    assert first - second == Fraction(2, (D + 1) * (D + 3))
    assert float(first) == float(second) == -1.0
    assert row1['model_id'] != row2['model_id'] and row1['exact_pair_sha256'] != row2['exact_pair_sha256']
    assert sys.get_int_max_str_digits() == initial_limit
    print(json.dumps({'python': sys.version.split()[0], 'platform': sys.platform, 'decimal_limit': initial_limit,
                      'variants': [row1, row2], 'exact_delta_verified': True, 'both_round_to': -1.0}, indent=2))
