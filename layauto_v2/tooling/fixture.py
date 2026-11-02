"""Capture the bytes actually read; never infer parse or EDA outcomes."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from layauto_v2.domain.acquisition import AcquisitionRequest, AcquisitionResponse
from layauto_v2.domain.evidence import SourceFile, SourceRef
from layauto_v2.domain.publication import AcquisitionEvent, ToolRunResult
from layauto_v2.domain.results import EvidenceIssue


class FixtureCapture:
    def __init__(self, run_id: str, tool_run_id: str) -> None:
        self.run_id = run_id
        self.tool_run_id = tool_run_id
        self._sources: list[SourceFile] = []
        self._events: list[AcquisitionEvent] = []

    def acquire(self, request: AcquisitionRequest) -> AcquisitionResponse:
        try:
            path = Path(request.path)
            if request.operation == 'probe':
                present = path.exists()
                self._events.append(AcquisitionEvent(
                    request.uri, request.path, 'probe', 'present' if present else 'absent'))
                return present
            source = SourceFile(request.uri, path.read_bytes())
            self._sources.append(source)
            self._events.append(AcquisitionEvent(
                request.uri, request.path, 'read', 'success', source.sha256))
            return source
        except OSError as exc:
            self._events.append(AcquisitionEvent(
                request.uri, request.path, request.operation, 'error',
                exception_type=type(exc).__name__, message=str(exc) or type(exc).__name__))
            return EvidenceIssue('read', request.missing_code, str(exc) or type(exc).__name__,
                                 SourceRef(request.uri))
        except (KeyboardInterrupt, SystemExit) as exc:
            self._events.append(AcquisitionEvent(
                request.uri, request.path, request.operation, 'interrupted',
                exception_type=type(exc).__name__, message=str(exc) or type(exc).__name__))
            raise
        except Exception as exc:
            self._events.append(AcquisitionEvent(
                request.uri, request.path, request.operation, 'error',
                exception_type=type(exc).__name__, message=str(exc) or type(exc).__name__))
            raise

    def freeze(self) -> ToolRunResult:
        status: Literal['completed', 'error', 'interrupted']
        if any(event.status == 'interrupted' for event in self._events):
            status = 'interrupted'
        elif any(event.status == 'error' for event in self._events):
            status = 'error'
        else:
            status = 'completed'
        return ToolRunResult(self.run_id, self.tool_run_id, tuple(self._sources),
                             tuple(self._events), execution_status=status)
