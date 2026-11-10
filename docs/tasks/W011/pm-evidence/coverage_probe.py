"""Independent finite atom checks for exact rational seed coverage."""
import hashlib
import json
import random
from fractions import Fraction
from pathlib import Path
import time

from layauto_v2.annotation.channel_identity import rational_cover
from layauto_v2.domain.channel_identity import RationalRect

start = time.monotonic()
rng = random.Random(11010)
cases = 0
atom_checks = 0
for offset in (0, 2**80, -(2**80)):
    for _ in range(128):
        boxes = []
        for _ in range(rng.randrange(1, 9)):
            x0, x1 = sorted(rng.sample(range(5), 2))
            y0, y1 = sorted(rng.sample(range(5), 2))
            boxes.append((x0, y0, x1, y1))
        expected = {(x, y) for x in range(4) for y in range(4)
                    if any(a <= x < c and b <= y < d for a, b, c, d in boxes)}
        source = tuple(RationalRect(*(Fraction(offset) + Fraction(v, 20) for v in b)) for b in boxes)
        result = rational_cover(source)
        expected_area = Fraction(len(expected), 400)
        assert sum((r.area for r in result), Fraction(0)) == expected_area
        for x in range(4):
            for y in range(4):
                px, py = Fraction(offset) + Fraction(2*x+1, 40), Fraction(offset) + Fraction(2*y+1, 40)
                hits = sum(r.x0 < px < r.x1 and r.y0 < py < r.y1 for r in result)
                assert hits == int((x, y) in expected)
                atom_checks += 1
        assert rational_cover(tuple(reversed(source)) + source[:1]) == result
        # Replace each rectangle by two exact halves; representation must not
        # affect the canonical union or its rational area.
        halves = tuple(part for r in source for part in (
            RationalRect(r.x0, r.y0, (r.x0+r.x1)/2, r.y1),
            RationalRect((r.x0+r.x1)/2, r.y0, r.x1, r.y1)))
        assert rational_cover(halves) == result
        cases += 1
print(json.dumps(dict(status='passed', cases=cases, independent_atom_membership_checks=atom_checks,
                      permutation_duplicate_and_subdivision_controls=cases,
                      scales='1/20 with offsets 0,+/-2**80', elapsed_seconds=time.monotonic()-start,
                      probe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()), indent=2))
