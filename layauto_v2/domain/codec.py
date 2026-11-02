"""Small exact, immutable value codec used by input evidence (no IO)."""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from fractions import Fraction
from typing import TypeAlias

Value: TypeAlias = 'None | bool | int | str | bytes | Fraction | FrozenMap | tuple[Value, ...]'


@dataclass(frozen=True, init=False)
class FrozenMap(Mapping[str, Value]):
    """Tuple-backed map; never retains a writable caller alias."""
    _entries: tuple[tuple[str, Value], ...]

    def __init__(self, values: Mapping[str, object]) -> None:
        if any(type(k) is not str for k in values):
            raise ValueError('map keys must be strings')
        object.__setattr__(self, '_entries', tuple((k, freeze(v)) for k, v in values.items()))

    def __getitem__(self, key: str) -> Value:
        for k, value in self._entries:
            if key == k:
                return value
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return (k for k, _ in self._entries)

    def __len__(self) -> int:
        return len(self._entries)


def freeze(value: object) -> Value:
    if value is None or type(value) in (bool, int, str, bytes):
        if isinstance(value, (bool, int, str, bytes)) or value is None:
            return value
    if isinstance(value, Fraction):
        return Fraction(value.numerator, value.denominator)
    if isinstance(value, Mapping):
        copied: dict[str, object] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError('map keys must be strings')
            copied[key] = item
        return FrozenMap(copied)
    if isinstance(value, (list, tuple)):
        return tuple(freeze(v) for v in value)
    raise ValueError(f'unsupported exact value type: {type(value).__name__}')


def freeze_map(value: object) -> FrozenMap:
    result = freeze(value)
    if not isinstance(result, FrozenMap):
        raise ValueError('expected a map')
    return result


def _wire(value: Value) -> object:
    if isinstance(value, FrozenMap):
        return {'$map': {key: _wire(item) for key, item in value.items()}}
    if isinstance(value, tuple):
        return [_wire(item) for item in value]
    if isinstance(value, Fraction):
        return {'$rational': {'numerator': str(value.numerator), 'denominator': str(value.denominator)}}
    if isinstance(value, bytes):
        return {'$bytes': value.hex()}
    return value


def canonical_bytes(value: object) -> bytes:
    return json.dumps(_wire(freeze(value)), sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def rational(value: object) -> Fraction:
    """Decode the declared reduced rational representation, never via float."""
    if not isinstance(value, Mapping) or set(value) != {'numerator', 'denominator'}:
        raise ValueError('expected numerator/denominator rational')
    n, d = value['numerator'], value['denominator']
    if not isinstance(n, str) or not isinstance(d, str):
        raise ValueError('rational components must be decimal strings')
    if re.fullmatch(r'(?:0|-[1-9][0-9]*|[1-9][0-9]*)', n) is None or re.fullmatch(r'[1-9][0-9]*', d) is None:
        raise ValueError('noncanonical rational components')
    result = Fraction(int(n), int(d))
    if str(result.numerator) != n or str(result.denominator) != d:
        raise ValueError('rational must be reduced')
    return result


def _decode(value: object) -> Value:
    if value is None or type(value) in (bool, int, str):
        return freeze(value)
    if isinstance(value, list):
        return tuple(_decode(v) for v in value)
    if isinstance(value, dict):
        if set(value) == {'$map'} and isinstance(value['$map'], dict):
            return FrozenMap({k: _decode(v) for k, v in value['$map'].items()})
        if set(value) == {'$rational'}:
            return rational(value['$rational'])
        if set(value) == {'$bytes'} and isinstance(value['$bytes'], str):
            raw = value['$bytes']
            if re.fullmatch(r'(?:[0-9a-f]{2})*', raw):
                return bytes.fromhex(raw)
    raise ValueError('invalid exact wire value')


def decode(data: bytes) -> Value:
    def pairs(items: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for k, v in items:
            if k in result:
                raise ValueError('duplicate wire key')
            result[k] = v
        return result
    def bad_number(token: str) -> object:
        raise ValueError(f'non-exact JSON number: {token}')
    value = _decode(json.loads(data, object_pairs_hook=pairs, parse_float=bad_number,
                               parse_constant=bad_number))
    if canonical_bytes(value) != data:
        raise ValueError('noncanonical wire encoding')
    return value
