"""IO-independent requests exchanged by a parser and its acquisition driver."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from .evidence import SourceFile
from .results import EvidenceIssue


@dataclass(frozen=True)
class AcquisitionRequest:
    path: str
    uri: str
    operation: Literal['read', 'probe'] = 'read'
    missing_code: str = 'MissingInput'

    def __post_init__(self) -> None:
        if any(type(x) is not str or not x for x in (self.path, self.uri, self.missing_code)):
            raise ValueError('acquisition requires explicit path, URI and error code')
        if not self.path.startswith('/') or self.path.startswith('//') or '\x00' in self.path:
            raise ValueError('acquisition path must be absolute POSIX without NUL')
        if self.operation not in ('read', 'probe'):
            raise ValueError('unsupported acquisition operation')


AcquisitionResponse: TypeAlias = 'SourceFile | EvidenceIssue | bool'
