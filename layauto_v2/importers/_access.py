"""Checked access to already schema-validated immutable data."""
from __future__ import annotations
from fractions import Fraction
from layauto_v2.domain.codec import FrozenMap, Value, rational


def mapping(value: Value) -> FrozenMap:
    if not isinstance(value, FrozenMap):
        raise ValueError('expected mapping')
    return value


def sequence(value: Value) -> tuple[Value, ...]:
    if not isinstance(value, tuple):
        raise ValueError('expected sequence')
    return value


def string(value: Value) -> str:
    if not isinstance(value, str):
        raise ValueError('expected string')
    return value


def integer(value: Value) -> int:
    if type(value) is not int:
        raise ValueError('expected integer')
    return value


def exact(value: Value) -> Fraction:
    return value if isinstance(value, Fraction) else rational(value)
