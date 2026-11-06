"""PM geometry check using finite integer-pixel and scaled-cell oracles.

No fixture/answer/test helper or product geometry function supplies expected
values.  Product contact/enclosure predicates are only the subjects under test.
"""
from __future__ import annotations

from fractions import Fraction
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

from layauto_v2.domain.geometry import Rect
from layauto_v2.state.local_connectivity import same_layer_contact, encloses_connector

ROOT = Path('/workspace/Layauto')
started = time.monotonic()


def occupied(mask: int) -> frozenset[tuple[int, int]]:
    return frozenset((i % 3, i // 3) for i in range(9) if mask & (1 << i))


def tiles(cells: frozenset[tuple[int, int]], dx: int = 0, dy: int = 0) -> tuple[Rect, ...]:
    return tuple(Rect(x + dx, y + dy, x + dx + 1, y + dy + 1) for x, y in sorted(cells))


def row_cover(cells: frozenset[tuple[int, int]]) -> tuple[Rect, ...]:
    result = []
    for y in range(3):
        xs = sorted(x for x, row in cells if row == y)
        i = 0
        while i < len(xs):
            begin = end = xs[i]
            i += 1
            while i < len(xs) and xs[i] == end + 1:
                end = xs[i]
                i += 1
            result.append(Rect(begin, y, end + 1, y + 1))
    return tuple(result)


def contact_oracle(a: frozenset[tuple[int, int]], b: frozenset[tuple[int, int]]) -> bool:
    if a & b:
        return True
    return any((x + dx, y + dy) in b for x, y in a for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))


def enclosure_oracle(cells: frozenset[tuple[int, int]], margin: Fraction) -> bool:
    # Every cover boundary is integral and every target boundary is on a sixth
    # tick.  Checking all open scaled cells proves area containment.  Finite
    # unions of closed pixel rectangles also contain their covered closures.
    scale = 6
    lo, hi = (Fraction(1) - margin) * scale, (Fraction(2) + margin) * scale
    assert lo.denominator == hi.denominator == 1
    return all((x // scale, y // scale) in cells
               for x in range(int(lo), int(hi)) for y in range(int(lo), int(hi)))


probes = [frozenset({(x, y)}) for x, y in
          ((-1, -1), (-1, 0), (0, -1), (0, 0), (1, 1), (2, 2), (3, 2), (2, 3), (3, 3), (4, 1))]
probes.extend((frozenset({(0, 0), (2, 2)}), frozenset((x, 1) for x in range(-1, 4))))
translations = ((0, 0), (2**100, -(2**100)))
margins = (Fraction(0), Fraction(1, 3), Fraction(1, 2), Fraction(1), Fraction(3, 2))
contacts = enclosures = row_decompositions = 0
contact_outcomes = {False: 0, True: 0}
enclosure_outcomes = {False: 0, True: 0}
for mask in range(512):
    cells = occupied(mask)
    for other in probes:
        expected = contact_oracle(cells, other)
        for dx, dy in translations:
            actual = same_layer_contact(tiles(cells, dx, dy), tiles(other, dx, dy))
            assert actual is expected, ('contact', mask, other, dx, dy, expected, actual)
            contacts += 1
            contact_outcomes[actual] += 1
        actual = same_layer_contact(row_cover(cells), tiles(other))
        assert actual is expected, ('row-contact', mask, other, expected, actual)
        row_decompositions += 1
    for margin in margins:
        expected = enclosure_oracle(cells, margin)
        for dx, dy in translations:
            target = Rect(1 + dx, 1 + dy, 2 + dx, 2 + dy)
            actual = encloses_connector(tiles(cells, dx, dy), target, margin)
            assert actual is expected, ('enclosure', mask, margin, dx, dy, expected, actual)
            enclosures += 1
            enclosure_outcomes[actual] += 1
        actual = encloses_connector(row_cover(cells), Rect(1, 1, 2, 2), margin)
        assert actual is expected, ('row-enclosure', mask, margin, expected, actual)
        row_decompositions += 1

assert all(contact_outcomes.values()) and all(enclosure_outcomes.values())
paths = ('layauto_v2/domain/local_connectivity.py', 'layauto_v2/state/local_connectivity.py',
         'layauto_v2/normalization/local_connectivity.py', 'layauto_v2/normalization/local_connectivity_codec.py')
result = {
    'status': 'passed', 'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'scope': 'PM finite geometry check; not a complete premerge or production proof',
    'python': sys.version, 'executable': sys.executable, 'platform': platform.platform(), 'cwd': str(ROOT),
    'masks': 512, 'contact_comparisons': contacts, 'enclosure_comparisons': enclosures,
    'row_decomposition_comparisons': row_decompositions,
    'contact_outcomes': {str(k): v for k, v in contact_outcomes.items()},
    'enclosure_outcomes': {str(k): v for k, v in enclosure_outcomes.items()},
    'rational_margins': [str(m) for m in margins], 'translations': [list(t) for t in translations],
    'elapsed_seconds': round(time.monotonic() - started, 3),
    'source_sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
    'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
}
print(json.dumps(result, indent=2, sort_keys=True))
