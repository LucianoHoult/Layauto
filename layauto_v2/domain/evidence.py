"""Immutable, IO-independent input sources and component evidence."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

from .codec import FrozenMap, freeze_map


@dataclass(frozen=True)
class SourceRef:
    uri: str
    sha256: str | None = None
    field: str | None = None
    line: int | None = None
    column: int | None = None
    byte_offset: int | None = None
    record_index: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.uri, str) or not self.uri:
            raise ValueError('source URI must be nonempty')
        if self.sha256 is not None and (not isinstance(self.sha256, str) or re.fullmatch('[0-9a-f]{64}', self.sha256) is None):
            raise ValueError('invalid source SHA-256')
        if self.field is not None and not isinstance(self.field, str):
            raise ValueError('invalid source field')
        for name in ('line', 'column', 'byte_offset', 'record_index'):
            value = getattr(self, name)
            minimum = 1 if name in ('line', 'column') else 0
            if value is not None and (type(value) is not int or value < minimum):
                raise ValueError(f'invalid {name}')
        if any(v is not None for v in (self.line, self.column, self.byte_offset, self.record_index)) and self.sha256 is None:
            raise ValueError('located source must have actually read bytes')


@dataclass(frozen=True)
class SourceFile:
    uri: str
    data: bytes
    sha256: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.uri, str) or not self.uri or type(self.data) is not bytes:
            raise ValueError('source requires URI and immutable bytes')
        object.__setattr__(self, 'sha256', hashlib.sha256(self.data).hexdigest())

    def ref(self, *, field: str | None = None, line: int | None = None,
            column: int | None = None, byte_offset: int | None = None,
            record_index: int | None = None) -> SourceRef:
        return SourceRef(self.uri, self.sha256, field, line, column, byte_offset, record_index)


@dataclass(frozen=True)
class EvidenceRecord:
    kind: str
    payload: FrozenMap
    sources: tuple[SourceRef, ...]
    parser_version: str = 'layauto-input/1'
    schema_version: str = 'layauto-evidence/1'

    def __post_init__(self) -> None:
        if not isinstance(self.kind, str) or not self.kind or self.schema_version != 'layauto-evidence/1' or self.parser_version != 'layauto-input/1':
            raise ValueError('invalid evidence discriminator/version')
        object.__setattr__(self, 'payload', freeze_map(self.payload))
        if not isinstance(self.sources, (tuple, list)):
            raise ValueError('evidence requires read source references')
        sources = tuple(self.sources)
        if not sources or any(not isinstance(s, SourceRef) or s.sha256 is None for s in sources):
            raise ValueError('evidence requires read source references')
        object.__setattr__(self, 'sources', sources)
