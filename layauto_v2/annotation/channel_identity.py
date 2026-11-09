"""Exact device-seed localization; partial coverage is not full annotation."""
from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

from layauto_v2.domain.channel_identity import (
    ChannelAssociation, ChannelRef, ChannelSeed, RationalRect, SeedIntersection, SeedLocation,
)
from layauto_v2.domain.circuit import Device
from layauto_v2.domain.evidence import SourceRef
from layauto_v2.domain.geometry import mapping, sequence
from layauto_v2.domain.identifiers import DeviceId
from layauto_v2.domain.regions import ExactRegion, RegionRef
from layauto_v2.domain.results import EvidenceIssue
from layauto_v2.domain.source_location import ref_from_location


def rational_cover(rectangles: tuple[RationalRect, ...]) -> tuple[RationalRect, ...]:
    """Canonical disjoint x-slab union; overlapping seeds never double coverage."""
    xs = sorted({x for rect in rectangles for x in (rect.x0, rect.x1)})
    opened: dict[tuple[Fraction, Fraction], RationalRect] = {}
    result: list[RationalRect] = []
    for left, right in zip(xs, xs[1:]):
        intervals = sorted((rect.y0, rect.y1) for rect in rectangles if rect.x0 <= left and right <= rect.x1)
        merged: list[tuple[Fraction, Fraction]] = []
        for low, high in intervals:
            if merged and low <= merged[-1][1]:
                merged[-1] = merged[-1][0], max(merged[-1][1], high)
            else:
                merged.append((low, high))
        updated: dict[tuple[Fraction, Fraction], RationalRect] = {}
        for low, high in merged:
            previous = opened.pop((low, high), None)
            updated[low, high] = RationalRect(left if previous is None else previous.x0, low, right, high)
        result.extend(opened.values())
        opened = updated
    result.extend(opened.values())
    return tuple(sorted(result, key=lambda rect: rect.bounds))


def channel_rectangle(channel: ExactRegion, tick_nm: int) -> RationalRect:
    if (type(channel) is not ExactRegion or channel.role != 'channel' or len(channel.rectangles) != 1
            or type(tick_nm) is not int or tick_nm <= 0):
        raise ValueError('toy localization requires one exact channel rectangle and positive DBU')
    return RationalRect(*(Fraction(value * tick_nm) for value in channel.rectangles[0].bounds))


def seed_source(seed: ChannelSeed) -> SourceRef:
    derivation = mapping(mapping(seed.record['field_sources'])['record_id'])
    return ref_from_location(mapping(sequence(derivation['sources'])[0]))


def locate_channels(devices: tuple[Device, ...], channels: tuple[ExactRegion, ...],
                    seeds: tuple[ChannelSeed, ...], tick_nm: int, binding_ref: ChannelRef,
                    channel_sources: tuple[SourceRef, ...]
                    ) -> tuple[tuple[SeedLocation, ...], tuple[ChannelAssociation, ...], tuple[EvidenceIssue, ...]]:
    """Each seed must uniquely locate first; other seeds cannot disambiguate it."""
    if len(channel_sources) != len(channels):
        raise ValueError('each channel requires its actual active source location')
    boxes = {channel.ref: channel_rectangle(channel, tick_nm) for channel in channels}
    sources = {channel.ref: source for channel, source in zip(channels, channel_sources)}
    locations: list[SeedLocation] = []
    issues: list[EvidenceIssue] = []
    for seed in seeds:
        candidates = []
        for channel in channels:
            box = boxes[channel.ref]
            intersection = seed.rectangle.intersection(box)
            if intersection is not None:
                candidates.append(SeedIntersection(seed.ref, channel.ref, intersection,
                                                   intersection.area / box.area, binding_ref))
        intersections = tuple(sorted(candidates, key=lambda item: item.channel_ref.sha256))
        locations.append(SeedLocation(seed.ref, intersections, binding_ref))
        if len(intersections) != 1:
            code = 'MissingSeedChannel' if not intersections else 'AmbiguousSeedChannel'
            issues.append(EvidenceIssue('unsupported', code,
                          f'device seed has {len(intersections)} positive-area channel candidates',
                          replace(seed_source(seed), field='/recognized_channel_intersection')))
    by_seed = {location.seed_ref: location for location in locations}
    proposed: dict[DeviceId, ChannelAssociation] = {}
    known_devices = {device.id for device in devices}
    for seed in seeds:
        if seed.device_id not in known_devices:
            issues.append(EvidenceIssue('unsupported', 'ForeignDeviceSeed', 'seed references a device outside source top',
                                        seed_source(seed)))
    for device in devices:
        device_seeds = tuple(seed for seed in seeds if seed.device_id == device.id)
        if not device_seeds:
            source = ref_from_location(mapping(device.field_sources['name']))
            issues.append(EvidenceIssue('unsupported', 'MissingDeviceSeed', 'source device has no channel seed', source))
            continue
        if any(len(by_seed[seed.ref].intersections) != 1 for seed in device_seeds):
            continue
        channel_refs = {by_seed[seed.ref].intersections[0].channel_ref for seed in device_seeds}
        if len(channel_refs) != 1:
            issues.append(EvidenceIssue('unsupported', 'ConflictingDeviceSeeds',
                          'one source device has distinct uniquely located channels; reduction is unsupported',
                          seed_source(device_seeds[0])))
            continue
        channel_ref = next(iter(channel_refs))
        coverage = rational_cover(tuple(by_seed[seed.ref].intersections[0].intersection for seed in device_seeds))
        fraction = sum((rect.area for rect in coverage), Fraction(0)) / boxes[channel_ref].area
        proposed[device.id] = ChannelAssociation(device.id, channel_ref,
                tuple(sorted((seed.ref for seed in device_seeds), key=lambda ref: ref.sha256)),
                coverage, fraction, binding_ref)
    associations: list[ChannelAssociation] = []
    for channel in channels:
        matching = tuple(item for item in proposed.values() if item.channel_ref == channel.ref)
        if len(matching) == 1:
            associations.append(matching[0])
        else:
            code = 'UnassociatedChannel' if not matching else 'ConflictingChannelIdentities'
            issues.append(EvidenceIssue('unsupported', code,
                          f'recognized channel has {len(matching)} unambiguous source-device associations',
                          replace(sources[channel.ref], field='/device_channel_identity')))
    return (tuple(sorted(locations, key=lambda item: item.seed_ref.sha256)),
            tuple(sorted(associations, key=lambda item: (item.device_id.cell.name, item.device_id.name))),
            tuple(issues))
