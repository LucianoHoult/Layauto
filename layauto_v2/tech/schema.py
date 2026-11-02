"""Closed schemas for the versioned synthetic input dialect.

This is a grammar, not a fixture template: names, paths, coordinates, thresholds
and array lengths are data. Cross-field validation checks interpretation claims.
"""
from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from layauto_v2.domain.codec import FrozenMap, Value, rational


class SchemaError(ValueError):
    def __init__(self, path: str, message: str, code: str = 'InvalidSchema') -> None:
        self.path, self.code = path, code
        super().__init__(message)


Check = Callable[[Value, str], None]


def _fail(path: str, message: str) -> None:
    raise SchemaError(path, message)


def text(value: Value, path: str) -> None:
    if not isinstance(value, str) or not value:
        _fail(path, 'expected nonempty string')


def integer(value: Value, path: str) -> None:
    if type(value) is not int:
        _fail(path, 'expected exact integer (not boolean)')


def boolean(value: Value, path: str) -> None:
    if type(value) is not bool:
        _fail(path, 'expected boolean')


def null(value: Value, path: str) -> None:
    if value is not None:
        _fail(path, 'expected null')


def natural(value: Value, path: str) -> None:
    integer(value, path)
    if isinstance(value, int) and value < 0:
        _fail(path, 'expected nonnegative integer')


def positive(value: Value, path: str) -> None:
    integer(value, path)
    if isinstance(value, int) and value <= 0:
        _fail(path, 'expected positive integer')


def enum(*choices: str) -> Check:
    def check(value: Value, path: str) -> None:
        text(value, path)
        if value not in choices:
            _fail(path, f'unsupported value; expected one of {choices!r}')
    return check


def literal(expected: Value) -> Check:
    def check(value: Value, path: str) -> None:
        if type(value) is not type(expected) or value != expected:
            _fail(path, f'expected {expected!r}')
    return check


def maybe(check: Check) -> Check:
    def wrapped(value: Value, path: str) -> None:
        if value is not None:
            check(value, path)
    return wrapped


def array(check: Check, *, length: int | None = None, nonempty: bool = False) -> Check:
    def wrapped(value: Value, path: str) -> None:
        if not isinstance(value, tuple):
            _fail(path, 'expected array')
            return
        if length is not None and len(value) != length:
            _fail(path, f'expected {length} items')
        if nonempty and not value:
            _fail(path, 'array must not be empty')
        for index, item in enumerate(value):
            check(item, f'{path}/{index}')
    return wrapped


def dictionary(check: Check) -> Check:
    def wrapped(value: Value, path: str) -> None:
        if not isinstance(value, FrozenMap):
            _fail(path, 'expected string-keyed map')
            return
        for key, item in value.items():
            if not key:
                _fail(path, 'map key must not be empty')
            check(item, f'{path}/{key}')
    return wrapped


def obj(required: dict[str, Check], optional: dict[str, Check] | None = None) -> Check:
    optional = optional or {}
    def wrapped(value: Value, path: str) -> None:
        if not isinstance(value, FrozenMap):
            _fail(path, 'expected object')
            return
        for key in value:
            if key not in required and key not in optional:
                raise SchemaError(f'{path}/{key}', 'unknown field', 'UnknownKey')
        for key in required:
            if key not in value:
                raise SchemaError(f'{path}/{key}', 'required field missing', 'MissingField')
        for key, item in value.items():
            check = required.get(key, optional.get(key))
            if check is None:
                raise AssertionError('closed schema check was not found')
            check(item, f'{path}/{key}')
    return wrapped


def exact(value: Value, path: str) -> None:
    try:
        rational(value)
    except ValueError as exc:
        raise SchemaError(path, str(exc), 'InvalidExactValue') from exc


def positive_exact(value: Value, path: str) -> None:
    exact(value, path)
    if rational(value) <= 0:
        _fail(path, 'exact scale must be positive')


def sha256(value: Value, path: str) -> None:
    if not isinstance(value, str) or re.fullmatch('[0-9a-f]{64}', value) is None:
        _fail(path, 'expected lowercase SHA-256')


def bbox(value: Value, path: str) -> None:
    array(integer, length=4)(value, path)
    assert isinstance(value, tuple)
    x0, y0, x1, y1 = value
    assert isinstance(x0, int) and isinstance(y0, int) and isinstance(x1, int) and isinstance(y1, int)
    if x0 >= x1 or y0 >= y1:
        _fail(path, 'bbox must have positive area')


STRINGS = array(text)
EMPTY = obj({})
OWNER_VERSION = literal('w004-tech-owner/2')
FILE_REF = obj({'uri': text, 'sha256': sha256})
SCHEMAS: dict[str, Check] = {}


def validate_payload(doc: FrozenMap, kind: str) -> None:
    try:
        check = SCHEMAS[kind]
    except KeyError as exc:
        raise SchemaError('', f'unsupported document kind: {kind}', 'UnsupportedSchema') from exc
    check(doc, '')


def validate_tech_payload(tech: FrozenMap) -> None:
    for kind, doc in tech.items():
        if not isinstance(doc, FrozenMap):
            raise SchemaError(f'/{kind}', 'owner must be an object')
        validate_payload(doc, kind)
