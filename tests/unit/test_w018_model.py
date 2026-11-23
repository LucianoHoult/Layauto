"""The model digest preserves exact derived coordinates beyond decimal IO limits."""
from dataclasses import replace
from fractions import Fraction

from layauto_v2.domain.evidence import SourceRef
from layauto_v2.domain.geometry import GeometryRef
from layauto_v2.state.projection_axes import TrackAxis
from layauto_v2.state.projection_model import ProjectionModel


def test_digest_supports_large_derived_rational_without_losing_adjacent_centres():
    # Each source denominator fits Python's default 4300-digit decimal limit.
    # Their combination in lower_edge + width/2 has over 4400 decimal digits.
    lower = Fraction(1, 10**2200)
    width = Fraction(1, 10**2200 + 1)
    centre = lower + width / 2
    track = TrackAxis('y', centre, Fraction(10), width, 0, 17)
    sources = tuple(SourceRef(owner, '1' * 64) for owner in
                    ('bundle', 'drawn', 'derived', 'physical', 'formats', 'coordinate', 'rules'))
    model = ProjectionModel((0, 0), {'stripe': track}, GeometryRef('unit', '2' * 64), sources)
    assert model.layers['stripe'].centre(0) == centre
    assert model.model_id == replace(model).model_id
    shifted = replace(track, first_centre_nm=centre + width)
    assert model.model_id != replace(model, layers={'stripe': shifted}).model_id
