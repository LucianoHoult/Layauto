"""Baseline-only transaction over neutral candidates and same-capture layer checks."""
from __future__ import annotations

from layauto_v2.domain.codec import FrozenMap
from layauto_v2.domain.geometry import mapping, sequence, text
from layauto_v2.domain.publication import (
    BaselineSnapshot, BaselineTarget, ContentRef, InputsReady, PreparedBaseline, SealedContext, Stage2Request,
)
from layauto_v2.repository import PublicationRepository, RepositoryConflict
from layauto_v2.state.layer_checks import LayerInitializationChecks
from layauto_v2.state.mutation import ProposedInitialState
from layauto_v2.state.snapshot import snapshot_state, target_values


class InitializationRejected(ValueError):
    """The original layer diagnostics retain the source field or stream offset."""
    def __init__(self, checks: LayerInitializationChecks) -> None:
        self.checks = checks
        failures = []
        for name, row in checks.layers.items():
            if not row.passed:
                issues = (*row.drawn_issues, *row.lifecycle_issues, *row.frame_issues, *row.projection_issues)
                reasons = [f'{i.code} at {i.source}' for i in issues]
                reasons.extend(f'{i.status} at {i.source.record_source}' for i in row.initialization.diagnostics)
                failures.append(f'{name}: {", ".join(reasons) or row.initialization.availability}')
        super().__init__('; '.join(failures))


def _pointer(ref: ContentRef) -> FrozenMap:
    return FrozenMap({'kind': ref.kind, 'run_id': ref.run_id, 'digest': ref.digest})


class InitializationTransaction:
    @staticmethod
    def prepare(repository: PublicationRepository, request: Stage2Request, ready: InputsReady,
                candidate: ProposedInitialState) -> PreparedBaseline:
        if candidate.occupancy.budget != request.fragment_budget:
            raise RepositoryConflict('BindingConflict', 'candidate fragment budget differs from the publication request')
        attempt = ready.attempt
        readback = FrozenMap({'run_id': ready.run_id, 'request_digest': attempt.request.digest,
                              'attempt_digest': attempt.ref.digest, 'checkpoint_ref': _pointer(ready.checkpoint_ref),
                              'parse_ref': _pointer(ready.parse_ref), 'tool_ref': _pointer(ready.tool_ref)})
        if (request.operation != 'initialize' or not ProposedInitialState.belongs_to(candidate, repository._scope)
                or request.checkpoint_ref != ready.checkpoint_ref or candidate.capture_binding['readback'] != readback
                or candidate.annotation.binding.capture_binding != candidate.capture_binding):
            raise RepositoryConflict('BindingConflict', f'{request.checkpoint_ref.id}: foreign candidate or capture')
        sources = {text(mapping(s)['uri']): mapping(s)['sha256'] for s in sequence(candidate.capture_binding['sources'])}
        binding = repository.stage2_binding(request, ready, FrozenMap(sources))
        checks = LayerInitializationChecks(candidate)
        if not checks.passed:
            raise InitializationRejected(checks)
        snapshot = BaselineSnapshot(request.run_id, request.checkpoint_ref, binding, snapshot_state(checks))
        circuit, differences = target_values(candidate)
        target = BaselineTarget(request.run_id, request.checkpoint_ref, circuit, differences)
        return PreparedBaseline._checked(repository._scope, request, snapshot, target)

    @classmethod
    def initialize(cls, repository: PublicationRepository, request: Stage2Request, ready: InputsReady,
                   candidate: ProposedInitialState) -> SealedContext:
        return repository.initialize(request, cls.prepare(repository, request, ready, candidate))

    @staticmethod
    def reuse(repository: PublicationRepository, request: Stage2Request) -> SealedContext:
        return repository.seal_context(request)
