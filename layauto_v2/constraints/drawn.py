"""Frame and FIN constraints on the drawn records of a published cell."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from fractions import Fraction
from typing import Literal

from layauto_v2.domain.codec import FrozenMap
from layauto_v2.domain.geometry import integer, mapping, sequence, text
from layauto_v2.domain.source_location import ref_from_location
from layauto_v2.state.projection_axes import TrackAxis
from layauto_v2.tech.rules import RuleRecord
from .drc_context import ConstraintContext
from .operands import _at, _drawn_layer, _geometry, side_margins_nm
from .result import Observation, RuleCheck, RuleGap, observed


def _roles(context: ConstraintContext) -> dict[str, str]:
    with _at(context, '/layers'):
        layers = mapping(context.snapshot.state['layers'])
        return {name: text(mapping(mapping(mapping(row)['policy'])['declaration'])['role'])
                for name, row in layers.items()}


def _unique_layer(context: ConstraintContext, roles: dict[str, str], role: str) -> str:
    with _at(context, '/layers'):
        selected, = (layer for layer, declared in roles.items() if declared == role)
        return selected


def evaluate_frame(context: ConstraintContext, rule: RuleRecord) -> RuleCheck:
    geometry, scale = _geometry(context)
    roles = _roles(context)
    layer = _unique_layer(context, roles, 'boundary')
    frames = _drawn_layer(context, geometry, layer, 'boundary')
    with _at(context, '/geometry/records'):
        frame, = frames.values()
    margin = integer(mapping(rule.declaration['parameters'])['margin_nm'])
    rows: list[Observation] = []
    for name, role in roles.items():
        if name == layer:
            continue
        for shape in _drawn_layer(context, geometry, name, role).values():
            r, f = shape.rect, frame.rect
            margins = side_margins_nm(f, r, scale)
            rows.append(Observation('frame_containment', (shape.record_id, frame.record_id),
                                    'pass' if min(margins) >= margin else 'violation',
                                    FrozenMap({'layer': name, 'bbox_dbu': r.bounds, 'frame_dbu': f.bounds,
                                               'side_margins_nm': margins, 'required_nm': margin}),
                                    (shape.source, frame.source, rule.location('parameters/margin_nm'))))
    return observed(rule, tuple(rows))


def evaluate_fin(context: ConstraintContext, rule: RuleRecord) -> RuleCheck:
    geometry, scale = _geometry(context)
    layer = _unique_layer(context, _roles(context), 'fin')
    with _at(context, '/layers/' + layer + '/projection/declaration'):
        projection = mapping(mapping(mapping(context.snapshot.state['layers'])[layer])['projection'])
        coord_source = ref_from_location(mapping(projection['declaration']))
    profile_source = replace(context.physical.sources[0], field='/fin_count_profile')
    try:
        profile = mapping(context.physical.payload['fin_count_profile'])
        width = integer(profile['fin_width_nm'])
        pitch = integer(profile['fin_pitch_nm'])
        phase = integer(profile['fin_lower_edge_offset_nm'])
    except (KeyError, ValueError) as exc:
        raise RuleGap('InvalidFinProfile', str(exc), profile_source) from exc
    with _at(context, '/coordinates'):
        coords = mapping(context.snapshot.state['coordinates'])
        origin = sequence(coords['origin_nm'])
        raw_axis = mapping(coords['axes']).get(layer)
    if not isinstance(raw_axis, FrozenMap) or raw_axis.get('index_axis') not in ('x', 'y'):
        raise RuleGap('MissingFinTrackDomain', 'full FIN sequence requires a finite track domain', coord_source)
    direction: Literal['x', 'y'] = 'x' if raw_axis['index_axis'] == 'x' else 'y'
    low = integer(origin[0 if direction == 'x' else 1]) + phase
    with _at(context, '/coordinates/axes/' + layer):
        axis = TrackAxis(direction, Fraction(low) + Fraction(width, 2), Fraction(pitch), Fraction(width),
                         integer(raw_axis['first_index']), integer(raw_axis['last_index']))
    if (axis.first_centre_nm, axis.pitch_nm, axis.width_nm) != (
            raw_axis['first_centre_nm'], raw_axis['pitch_nm'], raw_axis['width_nm']):
        raise RuleGap('IncompatibleFinProfile', 'selected projection disagrees with physical FIN profile', coord_source)
    tracks: dict[int, list[str]] = defaultdict(list)
    rows = []
    shapes = _drawn_layer(context, geometry, layer, 'fin').values()
    ordered = sorted(shapes, key=lambda s: (s.rect.y0 if direction == 'y' else s.rect.x0, s.record_id))
    previous_lower_nm: int | None = None
    for shape in ordered:
        rect = shape.rect
        bottom, top = (rect.y0, rect.y1) if direction == 'y' else (rect.x0, rect.x1)
        lower_nm = bottom * scale
        observed_pitch = None if previous_lower_nm is None else lower_nm - previous_lower_nm
        previous_lower_nm = lower_nm
        loc = axis.strip(rect, scale)
        index = loc.neighbours[0][0] if loc.status == 'on_track' else None
        if index is not None:
            tracks[index].append(shape.record_id)
        rows.append(Observation('fin_strip', (shape.record_id,), 'pass' if index is not None else 'violation',
                                FrozenMap({'bbox_dbu': rect.bounds, 'width_nm': (top - bottom) * scale,
                                           'required_width_nm': width, 'lower_nm': lower_nm,
                                           'pitch_from_previous_nm': observed_pitch,
                                           'phase_residual_nm': (lower_nm - low) % pitch,
                                           'first_lower_nm': low, 'pitch_nm': pitch, 'track': index,
                                           'position_nm': loc.position_nm, 'location': loc.status}),
                                (shape.source, coord_source, profile_source)))
    # A declared range may be much larger than the drawn inventory. Report
    # intervals between occupied tracks without enumerating unoccupied tracks.
    indices = [axis.first_index - 1, *sorted(tracks), axis.last_index + 1]
    missing = tuple((a + 1, b - 1) for a, b in zip(indices, indices[1:]) if b > a + 1)
    duplicates = tuple(i for i in sorted(tracks) if len(tracks[i]) > 1)
    rows.append(Observation('fin_sequence', tuple(i for t in sorted(tracks) for i in tracks[t]),
                            'violation' if missing or duplicates else 'pass',
                            FrozenMap({'index_range': (axis.first_index, axis.last_index),
                                       'missing_ranges': missing, 'duplicate_indices': duplicates,
                                       'first_lower_nm': low, 'pitch_nm': pitch}),
                            (coord_source, profile_source)))
    return observed(rule, tuple(rows))
