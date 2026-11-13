"""CR-02 old-boundary captured input alias witness; preserve original output."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

from layauto_v2.importers import read_inputs
from layauto_v2.normalization import (build_geometry, geometry_from_parse_result,
    build_effective_geometry, build_local_connectivity, build_net_annotation)


def main():
    root = Path.cwd()
    clock = time.perf_counter()
    parsed = read_inputs(root / 'tests/fixtures/w003_m1/site_config.yaml')
    assert parsed.status == 'success'
    geometry = build_geometry(geometry_from_parse_result(parsed))
    effective = build_effective_geometry(geometry)
    local = build_local_connectivity(effective)
    assert local.status == 'success'
    retained = local.input.input.input.semantic_input.parse.value
    # Keep all original logical fields/values byte-equivalent while making the
    # exact FrozenMap shell's backing mutable. No codec or validator is patched.
    backing = list(retained._entries)
    object.__setattr__(retained, '_entries', backing)
    try:
        result = build_net_annotation(local)
    except ValueError as exc:
        result_row = {'public_result_rejected': True, 'type': type(exc).__name__, 'message': str(exc)}
    else:
        assert result.status == 'success'
        backing.append(('review_external_alias', True))
        seen = result.input.input.input.input.semantic_input.parse.value
        result_row = {'public_result_rejected': False, 'public_result_status_after_external_mutation': result.status,
                      'retained_input_identity': result.input is local,
                      'external_alias_changed_result_input': seen['review_external_alias'] is True}
    print(json.dumps({'classification': 'independent-captured-alias-review-probe-not-resource-measurement',
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'python': sys.version, 'seconds': time.perf_counter() - clock,
        'scope': 'one real direct W005/W010/W013 build; no W013 public wire roundtrip',
        'limitations': 'Forged backing was installed via object.__setattr__; safe public FrozenMap constructor is not alleged to leak an alias.',
        **result_row}, indent=2))


if __name__ == '__main__':
    main()
