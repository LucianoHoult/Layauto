"""Deduplicated diagnostic graph prototype; deliberately has no decoder.

Captures appear only as identities and lengths. Integer references are report
local addresses, never executable content references or trusted receipts.
"""
from dataclasses import fields, is_dataclass
from fractions import Fraction
import hashlib
import json
from typing import Mapping
from layauto_v2.domain.codec import FrozenMap, digest
from layauto_v2.domain.evidence import SourceFile, SourceRef, EvidenceRecord


def diagnostic_json(facets: Mapping[str, object], captures: tuple[SourceFile, ...]) -> str:
    capture_ids = {(s.uri, s.sha256): i for i, s in enumerate(captures)}
    rows: list[object] = []
    indexes: dict[str, int] = {}
    identities: dict[int, object] = {}

    def value(item: object) -> object:
        if item is None or type(item) in (str, int, bool):
            return item
        if type(item) is Fraction:
            return {'rational': [item.numerator, item.denominator]}
        if type(item) is bytes:
            # Even numeric encoding bytes are referenced, not embedded as raw.
            return {'sha256': hashlib.sha256(item).hexdigest(), 'bytes': len(item)}
        if type(item) is SourceRef:
            identity = (item.uri, item.sha256)
            if identity not in capture_ids:
                raise ValueError('report source is outside capture table')
            return {'capture': capture_ids[identity], **{f.name: getattr(item, f.name)
                for f in fields(item) if f.name not in ('uri', 'sha256') and getattr(item, f.name) is not None}}
        if type(item) is SourceFile:
            return {'uri': item.uri, 'sha256': item.sha256, 'bytes': len(item.data)}
        if type(item) is EvidenceRecord:
            # Parsed owner/capture payloads are not report facets. Keep identity,
            # source locations and digest; the actual computed facts follow separately.
            return {'kind': item.kind, 'payload_sha256': digest(item.payload),
                    'sources': value(item.sources)}
        if id(item) in identities:
            return identities[id(item)]
        if type(item) is tuple:
            rendered: object = [value(x) for x in item]
        elif type(item) is FrozenMap:
            rendered = {k: value(v) for k, v in item.items()}
        elif is_dataclass(item) and not isinstance(item, type):
            rendered = {'type': type(item).__name__, 'fields': {
                f.name: value(getattr(item, f.name)) for f in fields(item)}}
        else:
            raise ValueError('unsupported diagnostic value')
        key = json.dumps(rendered, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        if key not in indexes:
            indexes[key] = len(rows)
            rows.append(rendered)
        result = {'ref': indexes[key]}
        identities[id(item)] = result
        return result

    roots = {name: value(item) for name, item in facets.items()}
    return json.dumps({'schema_version': 'layauto-analysis-diagnostic-view/1',
        'captures': [value(s) for s in captures], 'facets': roots, 'objects': rows},
        sort_keys=True, separators=(',', ':'), ensure_ascii=False)
