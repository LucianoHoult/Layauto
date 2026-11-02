"""Pure conversion from preserved field evidence to a located source reference."""
from __future__ import annotations

from typing import cast

from .codec import FrozenMap
from .evidence import SourceRef


def _string(value: object) -> str:
    if type(value) is not str or not value:
        raise ValueError('source location requires nonempty text')
    value.encode('utf-8')
    return value


def ref_from_location(value: FrozenMap) -> SourceRef:
    uri = value.get('uri', value.get('path'))
    field = value.get('field', value.get('json_pointer'))
    return SourceRef(_string(uri), _string(value['sha256']),
                     cast('str | None', field), cast('int | None', value.get('line', value.get('line_1based'))),
                     cast('int | None', value.get('column')), cast('int | None', value.get('byte_offset')),
                     cast('int | None', value.get('record_index')))

