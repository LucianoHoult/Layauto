"""Run the preserved original CR-01 reproducer; require its repaired rejection."""
from __future__ import annotations
import json
import runpy
from pathlib import Path
import sys

repo = Path(sys.argv[1]).resolve()
sys.path[:0] = [str(repo), str(repo / 'tests/contracts')]
from layauto_v2.normalization.geometry_input import GeometryInputError

try:
    runpy.run_path(str(repo / 'docs/tasks/W008/review/cr01-reproducer.py'), run_name='__main__')
except GeometryInputError as exc:
    assert exc.issue.code == 'GeometryCaptureBindingMismatch', exc.issue
    assert exc.issue.source.uri == 'site_config.yaml', exc.issue
    assert exc.issue.source.field == '/inputs/gds', exc.issue
    assert len(exc.completed) == 9, exc.completed
    print(json.dumps({'result': 'expected_rejection', 'code': exc.issue.code,
                      'source': exc.issue.source.uri, 'field': exc.issue.source.field,
                      'completed_count': len(exc.completed)}, indent=2))
else:
    raise AssertionError('CR-01 forgery was not rejected')
