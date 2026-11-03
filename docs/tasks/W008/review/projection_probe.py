"""Independent W008 reviewer probes; no expected/spec/oracle input."""
from pathlib import Path
import random
import struct
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'tests/contracts'))
from fractions import Fraction
from layauto_v2.state.coordinate import LayerPartition
from layauto_v2.domain.geometry import Rect
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import geometry_from_parse_result, build_geometry
from layauto_v2.normalization.geometry_codec import encode_record, decode_record
from w005_cases import copy_input, rebind, without_cache

rng = random.Random(8173)
for iteration in range(1000):
    xs = sorted(set([-20, 20] + [rng.randint(-19, 19) for _ in range(rng.randrange(0, 10))]))
    ys = sorted(set([-20, 20] + [rng.randint(-19, 19) for _ in range(rng.randrange(0, 10))]))
    x0, x1 = sorted(rng.sample(range(-20, 21), 2))
    y0, y1 = sorted(rng.sample(range(-20, 21), 2))
    layer = LayerPartition('review-math-only', xs, ys)
    pieces = layer.project(Rect(x0, y0, x1, y1))
    assert sum((r.x1-r.x0)*(r.y1-r.y0) for _,_,r in pieces) == (x1-x0)*(y1-y0)
    for i,j,r in pieces:
        assert r.bounds == (max(xs[i],x0), max(ys[j],y0), min(xs[i+1],x1), min(ys[j+1],y1))
        assert layer.point_to_index(Fraction(r.x0+r.x1,2), Fraction(r.y0+r.y1,2)) == (i,j)
        for ii,jj,s in pieces:
            if (i,j) != (ii,jj):
                assert max(r.x0,s.x0) >= min(r.x1,s.x1) or max(r.y0,s.y0) >= min(r.y1,s.y1)
    # Every half-integer lattice point in this tiny rectangle is covered once.
    for px in range(x0,x1):
        for py in range(y0,y1):
            assert sum(r.x0 <= px+Fraction(1,2) < r.x1 and r.y0 <= py+Fraction(1,2) < r.y1 for _,_,r in pieces) == 1
print('1000 independent arbitrary-boundary/negative-coordinate partition cases: passed')

with tempfile.TemporaryDirectory(prefix='w008-review-empty-') as temp:
    root = copy_input(Path(temp))
    without_cache(root)
    path = root/'source.gds'
    raw = path.read_bytes()
    output=[]
    offset=0
    in_element=False
    while offset < len(raw):
        size, kind, dtype=struct.unpack('>HBB',raw[offset:offset+4])
        part=raw[offset:offset+size]
        offset+=size
        if kind==8: in_element=True
        if not in_element: output.append(part)
        if kind==17: in_element=False
    path.write_bytes(b''.join(output))
    rebind(root)
    parsed=read_inputs(root/'site_config.yaml')
    assert parsed.status=='success', parsed.issues
    built=build_geometry(geometry_from_parse_result(parsed))
    assert built.status=='success' and built.value is not None
    assert not built.layout.records and not built.value.fragments
    assert all(not layer.xs and not layer.ys for layer in built.partition.layers)
    assert decode_record(encode_record(built))==built
print('Actual W005 empty drawn stream -> empty immutable layout/partition/occupancy + wire: passed')
