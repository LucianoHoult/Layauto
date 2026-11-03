"""Independent premerge fault injection across the complete W009 decode path.

Run at repository root with PYTHONDONTWRITEBYTECODE=1 and PYTHONPATH=.; stdout
is the observation JSON. No source or fixture is changed. The injected faults
are programmer/infrastructure failures while decoding an otherwise valid wire.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
from unittest.mock import patch

from layauto_v2.importers import read_inputs
from layauto_v2.normalization import (
    build_effective_geometry, build_geometry, geometry_from_parse_result,
)
from layauto_v2.normalization.effective_codec import decode_record, encode_record


def main():
    root = Path.cwd()
    parsed = read_inputs(root / 'tests/fixtures/w003_m1/site_config.yaml')
    assert parsed.status == 'success', parsed.issues
    result = build_effective_geometry(build_geometry(geometry_from_parse_result(parsed)))
    assert result.status == 'success', result.issues
    wires = {'draft': encode_record(result.value), 'result': encode_record(result)}
    # The first two exercise W009-owned reconstruction. The next three are
    # algorithms reused by its nested base. The last tests capture re-decoding.
    targets = (
        'layauto_v2.state.regions.slab_difference',
        'layauto_v2.domain.regions.canonical_cover',
        'layauto_v2.state.occupancy._fragments',
        'layauto_v2.state.coordinate._layers',
        'layauto_v2.state.layout_store._materialize',
        'layauto_v2.normalization.geometry_input.parse_gds',
    )
    rows = []
    for enclosing, wire in wires.items():
        for target in targets:
            if enclosing == 'draft' and target.endswith('.parse_gds'):
                # A neutral draft carries base evidence, not GeometryInput.
                continue
            for cls in (RuntimeError, ValueError, TypeError, KeyError,
                        AttributeError, IndexError, UnicodeError,
                        KeyboardInterrupt, SystemExit):
                failure = cls('independent premerge injected internal failure')

                def broken(*args, **kwargs):
                    raise failure

                with patch(target, broken):
                    try:
                        decode_record(wire)
                    except BaseException as observed:
                        rows.append({
                            'enclosing': enclosing, 'target': target,
                            'injected': cls.__name__,
                            'observed': type(observed).__name__,
                            'message': str(observed),
                            'same_object': observed is failure,
                            'cause_same_object': observed.__cause__ is failure,
                        })
                    else:
                        raise AssertionError('fault injection unexpectedly succeeded')
    source_paths = (
        'layauto_v2/normalization/effective_codec.py',
        'layauto_v2/normalization/effective.py',
        'layauto_v2/domain/regions.py', 'layauto_v2/state/regions.py',
        'layauto_v2/normalization/geometry_codec.py',
        'layauto_v2/normalization/geometry_input.py',
        'layauto_v2/state/occupancy.py', 'layauto_v2/state/coordinate.py',
        'layauto_v2/state/layout_store.py',
    )
    output = {
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'python': sys.version, 'executable': sys.executable,
        'platform': platform.platform(), 'cwd': str(root),
        'sources': {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in source_paths},
        'wire_sha256': {k: hashlib.sha256(v).hexdigest() for k, v in wires.items()},
        'observations': rows,
        'case_count': len(rows),
        'same_object_count': sum(row['same_object'] for row in rows),
        'identity_failures': [row for row in rows if not row['same_object']],
    }
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
