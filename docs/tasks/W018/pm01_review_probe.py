"""Resolve the reported field against the selected owner's captured bytes."""
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory

repo = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[3]
sys.path[:0] = [str(repo), str(repo / 'tests/contracts')]

from layauto_v2.normalization.projection import build_discrete_occupancy
from layauto_v2.normalization.projection_model import ProjectionConfigError
from w005_cases import copy_input
from w018_cases import COORDINATE_URI, build_geometry_from_site, select_projection


def resolve(owner, pointer):
    assert pointer.startswith('/')
    for token in pointer[1:].split('/'):
        assert re.search(r'~(?![01])', token) is None
        key = re.sub(r'~([01])', lambda match: '~/'[int(match[1])], token)
        owner = owner[key]
    return owner


def inspect(path, key, marker):
    def inject(model):
        parent = model['layers']['LI']
        for segment in path:
            parent = parent[segment]
        parent[key] = marker

    with TemporaryDirectory() as work:
        site = copy_input(Path(work))
        original = build_geometry_from_site(site)
        select_projection(site, mutate=inject)
        receipt = build_geometry_from_site(site)
        try:
            build_discrete_occupancy(receipt, fragment_budget=100)
        except ProjectionConfigError as error:
            assert error.issue.code == 'InvalidProjectionDeclaration'
            assert error.geometry is receipt and receipt.value == original.value
            assert len(receipt.layout.records) == 40
            ref = error.issue.source
            assert ref.uri == COORDINATE_URI
            captured, = [s for s in receipt.input.parse.sources if s.uri == ref.uri]
            assert captured.data == (site / ref.uri).read_bytes()
            assert ref.sha256 == captured.sha256 == sha256(captured.data).hexdigest()
            owner = json.loads(captured.data)
            good = resolve(owner, '/coordinate_projection/layers/LI/x_edges/pitch_dbu')
            assert good == 20
            try:
                found = resolve(owner, ref.field)
            except KeyError:
                found = 'unresolved'
            print(key, ref.field, found, good, ref.sha256)
            return found == marker
        raise AssertionError('literal key was accepted')


if __name__ == '__main__':
    checks = [inspect(path, key, n) for path, key, n in (
        ((), 'x_edges/pitch_dbu', 987),
        (('x_edges',), 'pitch~1dbu', 988),
        (('y_edges',), '~0/pitch~1_dbu', 989),
    )]
    assert checks == [True, True, True], checks
