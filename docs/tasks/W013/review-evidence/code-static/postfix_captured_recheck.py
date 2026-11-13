"""One actual direct receipt plus early old-codec exception and alias controls."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch

from layauto_v2.domain.codec import canonical_bytes, decode
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import (build_geometry, geometry_from_parse_result,
    build_effective_geometry, build_local_connectivity, build_net_annotation)
from layauto_v2.normalization.net_annotation import NetAnnotationResult
from layauto_v2.normalization import local_connectivity_codec as old_codec
from layauto_v2.normalization import net_annotation_codec as codec

FILES = ('layauto_v2/domain/net_annotation.py', 'layauto_v2/state/annotation.py',
         'layauto_v2/annotation/net_regions.py', 'layauto_v2/derive/net_annotation.py',
         'layauto_v2/normalization/net_annotation.py', 'layauto_v2/normalization/net_annotation_codec.py',
         'layauto_v2/normalization/__init__.py', 'pyproject.toml')


def main():
    root, started = Path.cwd(), time.perf_counter()
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    source = {name: sha(root / name) for name in FILES}
    parsed = read_inputs(root / 'tests/fixtures/w003_m1/site_config.yaml')
    assert parsed.status == 'success'
    local = build_local_connectivity(build_effective_geometry(build_geometry(geometry_from_parse_result(parsed))))
    result = build_net_annotation(local)
    assert result.status == 'success' and result.input is local
    assert len(local.value.nodes) == 14 and len(local.value.edges) == 8 and len(result.value.components) == 6
    assert sum(row.total_area for row in result.value.coverage) == 35090
    assert sum(row.covered_area for row in result.value.coverage) == 3170
    assert sum(row.uncovered_area for row in result.value.coverage) == 31920
    assert sum(row.covered_area for row in result.value.coverage if row.layer in ('OD', 'BODY_N', 'BODY_P')) == 0
    assert len([row for row in result.value.classifications if row.classification == 'marker']) == 1
    retained = local.input.input.input.semantic_input.parse.value
    original = retained._entries
    object.__setattr__(retained, '_entries', list(original))
    rejected = []
    try:
        for name, call in (
            ('builder', lambda: build_net_annotation(local)),
            ('constructor', lambda: NetAnnotationResult(local)),
            ('encoder', lambda: codec.encode_record(result)),
        ):
            try:
                call()
            except ValueError as exc:
                assert 'immutable tuple' in str(exc)
                rejected.append({'entry': name, 'type': type(exc).__name__, 'message': str(exc)})
            else:
                raise AssertionError('captured malformed backing accepted by ' + name)
    finally:
        object.__setattr__(retained, '_entries', original)
    # A complete real old input Value is retained. Output below is intentionally
    # unreachable: this isolates unexpected exceptions at the old public decoder.
    old_wire = old_codec.encode_record(local)
    old_value = decode(old_wire)
    failure_packet = canonical_bytes({'wire_schema': codec.WIRE_VERSION,
        'captured_input_wire': old_value, 'record': None})
    chains = []
    for name, failure_type, suppress, call in (
        ('builder', RuntimeError, False, lambda: build_net_annotation(local)),
        ('constructor', ValueError, True, lambda: NetAnnotationResult(local)),
        ('encoder', KeyboardInterrupt, False, lambda: codec.encode_record(result)),
        ('decoder', SystemExit, True, lambda: codec.decode_record(failure_packet)),
    ):
        failure = failure_type('independent old-codec boundary failure')
        cause, context = LookupError('existing cause'), ArithmeticError('existing context')
        failure.__cause__, failure.__context__, failure.__suppress_context__ = cause, context, suppress
        def broken(*args, **kwargs):
            raise failure
        with patch.object(old_codec, 'decode_record', broken):
            try:
                call()
            except BaseException as exc:
                assert exc is failure
                assert exc.__cause__ is cause and exc.__context__ is context
                assert exc.__suppress_context__ is suppress
                chains.append({'entry': name, 'type': failure_type.__name__, 'same_object': True,
                    'same_cause': True, 'same_context': True, 'same_suppression': True})
            else:
                raise AssertionError('unexpected boundary failure swallowed: ' + name)
    assert source == {name: sha(root / name) for name in FILES}
    print(json.dumps({'classification': 'independent-captured-correctness-review-not-resource-or-matrix',
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'python': sys.version, 'seconds': time.perf_counter() - started,
        'source_files': source, 'source_stable': True, 'direct_counts': [14, 8, 6],
        'direct_covered_uncovered_total_area_nm2': [3170, 31920, 35090],
        'malformed_captured_alias_rejections': rejected, 'old_decoder_exception_chains': chains,
        'not_run': ['full W013 successful public wire roundtrip', 'readback independent rebuild',
                    'resource measurement', 'full regression'],
        'limitations': ['The intentionally incomplete output in the exception packet is never consumed: the injected original old decoder failure occurs first.',
                       'One direct actual build checks local source evidence only; no terminal or EDA assurance.']}, indent=2))


if __name__ == '__main__':
    main()
