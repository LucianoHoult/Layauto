"""Independent exact body math and real owner scalar regression witnesses."""
from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

import pytest

from layauto_v2.derive.body_relations import BodyProblem, _owners, edge_length, enclosure, frame_edge_length, positive_area
from layauto_v2.domain.channel_identity import RationalRect
from layauto_v2.domain.codec import FrozenMap
from layauto_v2.domain.evidence import EvidenceRecord, SourceRef


def rectangle(bounds):
    return RationalRect(*(Fraction(value) for value in bounds))


@pytest.mark.parametrize('first,second,area,edge', [
    ((0, 0, 10, 10), (-20, 0, 0, 10), False, 10),
    ((0, 0, 10, 10), (-20, 10, 0, 20), False, 0),
    ((0, 0, 10, 10), (-20, 2, -1, 8), False, 0),
    ((0, 0, 10, 10), (-20, 2, 1, 8), True, 0),
    ((0, 0, 10, 10), (2, 10, 8, 12), False, 6),
    ((0, 0, 10, 10), (Fraction(1, 20), Fraction(1, 20), Fraction(3, 20), Fraction(3, 20)), True, 0),
])
def test_positive_area_and_positive_length_are_distinct_symmetric_facts(first, second, area, edge):
    left, right = rectangle(first), rectangle(second)
    assert positive_area(left, right) is area
    assert positive_area(right, left) is area
    assert edge_length(left, right) == edge_length(right, left) == Fraction(edge)


def test_all_four_margins_preserve_negative_and_fractional_values():
    assert enclosure(rectangle((-20, 48, 0, 58)), rectangle((-12, 50, -8, 54))) == (8, 2, 8, 4)
    assert enclosure(rectangle((0, 100, 120, 200)), rectangle((20, 110, 100, 180))) == (20, 10, 20, 20)
    margins = enclosure(rectangle((0, 48, 45, 58)), rectangle((0, 48, Fraction(901, 20), 58)))
    assert margins == (0, 0, Fraction(-1, 20), 0)
    assert min(margins) < 0


def test_generic_positive_boundary_contact_is_not_necessarily_frame_continuation():
    frame = rectangle((0, 0, 160, 200))
    local, external = rectangle((-10, 0, 120, 90)), rectangle((-20, 0, -10, 90))
    assert edge_length(local, external) == 90
    assert frame_edge_length(local, external, frame) == 0
    assert frame_edge_length(rectangle((0, 0, 120, 90)), rectangle((-20, 0, 0, 90)), frame) == 90
    assert frame_edge_length(rectangle((0, 0, 120, 90)), rectangle((-20, 90, 0, 100)), frame) == 0


def owners(mutate=None):
    root = Path(__file__).resolve().parents[1] / 'fixtures/w003_m1/tech'
    raw = {name: json.loads((root / (name + '.json')).read_text()) for name in ('physical', 'drawn', 'rules')}
    if mutate is not None:
        mutate(raw)
    records = {name: EvidenceRecord(name, FrozenMap(value), (SourceRef('tech/' + name + '.json', 'a' * 64),))
               for name, value in raw.items()}
    return SimpleNamespace(local=SimpleNamespace(binding=SimpleNamespace(**records)))


def test_actual_owner_integer_thresholds_are_exact_fractions_not_rational_wire_maps():
    active, tap = _owners(owners())
    assert type(active) is type(tap) is Fraction
    assert (active, tap) == (10, 1)


def test_body_tap_owner_is_executed_even_when_local_graph_does_not_use_it():
    def change(raw):
        tap = next(row for row in raw['drawn']['layers'] if row['name'] == 'BTAP_N')
        tap['electrical_connects'] = ['BODY_P', 'M1']
    with pytest.raises(BodyProblem) as caught:
        _owners(owners(change))
    issue = caught.value.issue
    assert issue.category == 'unsupported'
    assert issue.source.uri == 'tech/drawn.json'
    assert issue.source.field.endswith('/electrical_connects')
