"""Real installed W005/W006 -> W008/W009/W010 composition outside source.

Run with -I -B; no test/support, oracle, spec or expected input is imported.
"""
from __future__ import annotations

import builtins
from contextlib import ExitStack
from dataclasses import replace
import hashlib
import importlib.metadata
import io
import json
from pathlib import Path
import sys
import sysconfig
from unittest.mock import patch

import layauto_v2
from layauto_v2.domain.publication import InputsReady, RunRequest
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import (
    build_geometry, build_effective_geometry, build_local_connectivity,
    geometry_from_parse_result, geometry_from_inputs_ready,
)
from layauto_v2.normalization.local_connectivity_codec import encode_record, decode_record, record_digest
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository


def forbidden(*args, **kwargs):
    raise AssertionError('local connectivity attempted IO or repository access')


def verify(result):
    assert result.status == 'success' and not result.issues
    graph = result.value
    assert graph is not None
    assert (len(graph.nodes), len(graph.edges), len(graph.components)) == (14, 8, 6)
    assert len(graph.audits) == 16 and all(row.status == 'pass' for row in graph.audits)
    assert graph.local_enclosure_status == 'pass'
    assert sum(node.layer == 'OD' for node in graph.nodes) == 4
    assert sum(node.layer == 'POLY' for node in graph.nodes) == 1
    assert len(result.body_evidence.payload['shapes']) == 6
    assert len(graph.effective.base.layout.records) == 40
    assert not any(hasattr(graph, key) for key in ('net_id', 'device_id', 'baseline', 'terminal'))
    wire = encode_record(result)
    assert decode_record(wire) == result
    assert record_digest(result) == hashlib.sha256(wire).hexdigest()
    try:
        replace(graph, nodes=graph.nodes[1:])
    except ValueError:
        pass
    else:
        raise AssertionError('incomplete public graph accepted')
    return {'wire_sha256': record_digest(result), 'semantic_digest': graph.semantic_digest,
            'nodes': len(graph.nodes), 'edges': len(graph.edges), 'components': len(graph.components),
            'audits': len(graph.audits), 'local_enclosure_status': graph.local_enclosure_status}


def main():
    fixture = Path(sys.argv[1]).resolve()
    installed = Path(layauto_v2.__file__).resolve()
    purelib = Path(sysconfig.get_path('purelib')).resolve()
    assert installed.is_relative_to(purelib), (installed, purelib)
    parsed = read_inputs(fixture / 'site_config.yaml')
    assert parsed.status == 'success', parsed.issues
    direct_effective = build_effective_geometry(build_geometry(geometry_from_parse_result(parsed)))
    repository = PublicationRepository()
    ready = prepare_inputs(repository, RunRequest(
        proposed_run_id='w010-installed-run', lineage_id='w010-installed-lineage',
        idempotency_key='create-w010-installed', site_path=str(fixture / 'site_config.yaml')))
    assert isinstance(ready, InputsReady)
    checkpoint = repository.load_checkpoint(ready.run_id)
    parse, tool = repository.read(ready.parse_ref), repository.read(ready.tool_ref)
    audits = tuple(repository.read(ref) for ref in ready.evidence_refs)
    attempt = repository.load_attempt(ready.run_id)
    readback_effective = build_effective_geometry(build_geometry(
        geometry_from_inputs_ready(ready, checkpoint, parse, tool, audits)))
    with ExitStack() as stack:
        for target in ('open', 'read_bytes', 'read_text', 'resolve'):
            stack.enter_context(patch.object(Path, target, forbidden))
        stack.enter_context(patch.object(builtins, 'open', forbidden))
        stack.enter_context(patch.object(io, 'open', forbidden))
        stack.enter_context(patch.object(repository, 'read', forbidden))
        direct = build_local_connectivity(direct_effective)
        readback = build_local_connectivity(readback_effective)
        direct_checks, readback_checks = verify(direct), verify(readback)
    assert direct.value == readback.value
    assert direct.input is direct_effective and readback.input is readback_effective
    assert direct.completed == parsed.completed
    assert repository.load_attempt(ready.run_id) == attempt and attempt.phase == 'unsealed'
    print(json.dumps({'python': sys.version, 'executable': sys.executable,
                      'package': str(installed), 'distribution_version': importlib.metadata.version('layauto'),
                      'direct': direct_checks, 'readback': readback_checks,
                      'attempt_unchanged': True}, indent=2))


if __name__ == '__main__':
    main()
