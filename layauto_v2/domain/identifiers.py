"""Typed, deterministic semantic identities and query-run backlinks (no IO)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from .codec import FrozenMap, digest


def _text(value: object, name: str) -> None:
    if type(value) is not str or not value:
        raise ValueError(f'{name} must be a nonempty string')
    try:
        value.encode('utf-8')
    except UnicodeError as exc:
        raise ValueError(f'{name} is not valid Unicode') from exc


def _name(value: object) -> None:
    _text(value, 'semantic name')
    if not isinstance(value, str) or re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', value) is None:
        raise ValueError('name is outside toy_literal_cdl/1 identifiers')


@dataclass(frozen=True)
class CellId:
    name: str

    def __post_init__(self) -> None:
        _name(self.name)

    @property
    def digest(self) -> str:
        return digest(identity_value(self))

    @property
    def id(self) -> str:
        return 'cell:' + self.digest


@dataclass(frozen=True)
class DeviceId:
    cell: CellId
    name: str

    def __post_init__(self) -> None:
        if type(self.cell) is not CellId:
            raise ValueError('device identity requires a typed cell')
        _name(self.name)

    @property
    def digest(self) -> str:
        return digest(identity_value(self))

    @property
    def id(self) -> str:
        return 'device:' + self.digest


@dataclass(frozen=True)
class NetId:
    cell: CellId
    name: str

    def __post_init__(self) -> None:
        if type(self.cell) is not CellId:
            raise ValueError('net identity requires a typed cell')
        _name(self.name)

    @property
    def digest(self) -> str:
        return digest(identity_value(self))

    @property
    def id(self) -> str:
        return 'net:' + self.digest


@dataclass(frozen=True)
class DeltaId:
    value: str

    def __post_init__(self) -> None:
        if type(self.value) is not str or re.fullmatch('[0-9a-f]{64}', self.value) is None:
            raise ValueError('delta identity requires lowercase SHA-256')

    @property
    def digest(self) -> str:
        return self.value

    @property
    def id(self) -> str:
        return 'delta:' + self.value


@dataclass(frozen=True)
class QueryKey:
    header_id: str
    query_run_id: str
    database_id: str | None
    kind: Literal['device', 'net']
    identity: str
    index: str | None = None

    def __post_init__(self) -> None:
        for name in ('header_id', 'query_run_id', 'identity'):
            _text(getattr(self, name), name)
        if self.database_id is not None:
            _text(self.database_id, 'query database id')
        if self.kind == 'device':
            if self.index is not None:
                raise ValueError('device query key has no NET NAMES index')
        elif self.kind == 'net':
            if type(self.index) is not str or re.fullmatch(r'[1-9][0-9]*', self.index) is None:
                raise ValueError('net query key requires a positive opaque decimal index')
        else:
            raise ValueError('unknown query identity kind')

    @property
    def digest(self) -> str:
        return digest(identity_value(self))

    @property
    def id(self) -> str:
        return 'query:' + self.digest


def identity_value(value: CellId | DeviceId | NetId | DeltaId | QueryKey) -> FrozenMap:
    if type(value) is CellId:
        return FrozenMap({'schema': 'layauto-semantic-id/1', 'kind': 'cell', 'name': value.name})
    if isinstance(value, (DeviceId, NetId)):
        return FrozenMap({'schema': 'layauto-semantic-id/1', 'kind': 'device' if type(value) is DeviceId else 'net',
                          'cell': value.cell.name, 'name': value.name})
    if type(value) is DeltaId:
        return FrozenMap({'schema': 'layauto-delta-id/1', 'value': value.value})
    if type(value) is QueryKey:
        return FrozenMap({'schema': 'layauto-query-key/1', 'header_id': value.header_id,
                          'query_run_id': value.query_run_id, 'database_id': value.database_id,
                          'kind': value.kind, 'identity': value.identity, 'index': value.index})
    raise ValueError('unsupported typed identity')
