"""Internal local authentication from captured bytes, with no filesystem access."""
from dataclasses import dataclass
from pathlib import Path

from layauto_v2.domain.analysis import LocalAnalysisEvidence
from layauto_v2.domain.codec import digest, FrozenMap
from layauto_v2.domain.evidence import SourceFile
from layauto_v2.domain.terminal_relations import validate_terminal_graph
from layauto_v2.domain.evidence import EvidenceRecord, SourceRef
from layauto_v2.domain.results import EvidenceIssue
from layauto_v2.importers.analysis_reader import AnalysisFiles, parse_analysis


class _CapturedFiles(AnalysisFiles):
    def path(self, uri: str) -> Path:
        # Never resolve symlinks again: this is the acquisition-time alias table.
        if uri not in self.paths:
            raise ValueError('analysis alias is missing from acquisition facts')
        return self.paths[uri]


@dataclass(frozen=True)
class LocalAnalysisReceipt:
    evidence: LocalAnalysisEvidence
    schema_version: str = 'layauto-local-analysis-receipt/1'

    def __post_init__(self) -> None:
        if type(self.evidence) is not LocalAnalysisEvidence or self.schema_version != 'layauto-local-analysis-receipt/1':
            raise ValueError('invalid local receipt type/version')
        evidence = self.evidence
        validate_terminal_graph(evidence, (LocalAnalysisEvidence, SourceFile, SourceRef, EvidenceRecord, EvidenceIssue))
        # Reconstruct the neutral shell before consuming retained storage.
        LocalAnalysisEvidence(**vars(evidence))
        if evidence.value is None or evidence.issues:
            raise ValueError('local receipt requires complete parse evidence')
        files = _CapturedFiles(Path(evidence.root))
        files.paths = {uri: Path(str(path)) for uri, path in evidence.aliases.items()}
        captures = {s.uri: s for s in evidence.captures}
        parser = parse_analysis(files, evidence.manifest_uri)
        try:
            request = next(parser)
            while True:
                if request.operation == 'probe':
                    if request.path not in evidence.probes:
                        raise ValueError('missing captured cache probe')
                    probe = evidence.probes[request.path]
                    if type(probe) is not bool:
                        raise ValueError('invalid captured probe')
                    response: SourceFile | bool = probe
                else:
                    if request.uri not in captures:
                        raise ValueError('missing raw capture or altered first URI')
                    response = captures[request.uri]
                request = parser.send(response)
        except StopIteration as done:
            rebuilt = done.value
        if rebuilt != evidence:
            raise ValueError('analysis evidence differs from full-byte reparse')

    @property
    def ref(self) -> str:
        return digest(FrozenMap({'version': self.schema_version,
            'root': self.evidence.root, 'manifest_uri': self.evidence.manifest_uri,
            'aliases': self.evidence.aliases, 'probes': self.evidence.probes,
            'captures': tuple(FrozenMap({'uri': s.uri, 'sha256': s.sha256}) for s in self.evidence.captures)}))
