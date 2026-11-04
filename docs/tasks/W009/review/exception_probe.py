"""Independent W009 review: unexpected arithmetic exceptions across wire.

Run from a checkout with an installed Layauto development environment:
  python docs/tasks/W009/review/exception_probe.py > result.json
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from layauto_v2.importers import read_inputs
from layauto_v2.normalization.geometry_input import geometry_from_parse_result
from layauto_v2.normalization.geometry import build_geometry
from layauto_v2.normalization.effective import build_effective_geometry
from layauto_v2.normalization.effective_codec import encode_record, decode_record


def main():
    root = Path.cwd()
    result = build_effective_geometry(build_geometry(geometry_from_parse_result(
        read_inputs(root / 'tests/fixtures/w003_m1/site_config.yaml'))))
    wires = {'draft': encode_record(result.value), 'result': encode_record(result)}
    rows = []
    for where, wire in wires.items():
        for cls in (RuntimeError, ValueError, TypeError, KeyError, AttributeError,
                    IndexError, UnicodeError, KeyboardInterrupt, SystemExit):
            failure = cls('independent unexpected arithmetic probe')

            def broken(*args, **kwargs):
                raise failure

            with patch('layauto_v2.state.regions.slab_difference', broken):
                try:
                    decode_record(wire)
                except BaseException as observed:
                    rows.append({'enclosing': where, 'injected': cls.__name__,
                                 'observed': type(observed).__name__,
                                 'same_object': observed is failure,
                                 'cause_same_object': observed.__cause__ is failure})
                else:
                    raise AssertionError('injected arithmetic unexpectedly succeeded')
    source_paths = ('layauto_v2/domain/regions.py', 'layauto_v2/state/regions.py',
                    'layauto_v2/normalization/effective.py',
                    'layauto_v2/normalization/effective_codec.py')
    output = {'sources': {path: hashlib.sha256((root / path).read_bytes()).hexdigest()
                          for path in source_paths}, 'observations': rows,
              'all_same_object': all(row['same_object'] for row in rows)}
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
