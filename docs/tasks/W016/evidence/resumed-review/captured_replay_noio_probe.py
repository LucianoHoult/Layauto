"""R09 full actual-capture replay with filesystem access methods blocked."""
import argparse
import builtins
from contextlib import ExitStack
from dataclasses import replace
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

p = argparse.ArgumentParser()
p.add_argument('--root', type=Path, required=True)
a = p.parse_args()
root = a.root.resolve()
sys.path.insert(0, str(root))
sys.path.insert(0, str(root/'tests/support'))
from analysis_inputs import materialize, manual_for, load, write, rebind
from layauto_v2.domain.codec import FrozenMap
from layauto_v2.importers.analysis_reader import acquire_analysis, acquire_selections
from layauto_v2.normalization.analysis_input import LocalAnalysisReceipt
from layauto_v2.normalization.analysis import analyze_local, selected_analysis, analyze_terminals

blocked = []
def forbidden(*args, **kwargs):
    raise AssertionError('Filesystem access attempted after actual capture')

with tempfile.TemporaryDirectory(prefix='w016-review-noio-') as tmp:
    folder = Path(tmp)
    manifest = materialize(folder, body=True)
    config = load(manifest)
    config['manual_intent'] = {'kind': 'declaration', 'uri': 'manual.json'}
    write(manifest, config)
    write(folder/'manual.json', manual_for(folder))
    rebind(folder)
    evidence = acquire_analysis(manifest)
    assert evidence.value is not None and not evidence.issues
    captures, body_capture, manual_capture, read_issues, aliases = acquire_selections(evidence)
    assert not read_issues and body_capture is not None and manual_capture is not None
    inputs = {str(path.relative_to(folder)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(folder.rglob('*')) if path.is_file()}
    with ExitStack() as stack:
        for module, names in ((builtins, ('open',)), (io, ('open',)),
                              (os, ('open', 'stat', 'lstat', 'readlink', 'scandir', 'listdir')),
                              (Path, ('open', 'read_bytes', 'read_text', 'write_bytes', 'write_text', 'resolve', 'exists', 'is_file', 'is_dir', 'stat', 'lstat', 'readlink'))):
            for name in names:
                stack.enter_context(patch.object(module, name, forbidden))
                blocked.append(module.__name__ + '.' + name)
        receipt = LocalAnalysisReceipt(evidence)
        local = analyze_local(receipt)
        body = selected_analysis(receipt, local, 'external_body', body_capture, read_issues, aliases)
        manual = selected_analysis(receipt, local, 'manual_intent', manual_capture, read_issues, aliases)
        terminals = analyze_terminals(local, body)
        assert body.status == 'evaluated' and not body.issues
        assert manual.status == 'declared' and not manual.issues
        assert terminals.status == 'available' and len(terminals.value) == 8
        failures = []
        for name in ('unused_alias', 'swapped_gds_role', 'missing_alias', 'relative_root', 'relative_raw_alias'):
            altered = dict(evidence.aliases)
            if name == 'unused_alias':
                altered['never-requested-role'] = str(manifest)
            elif name == 'swapped_gds_role':
                altered['source.gds'] = altered['source.cdl']
            elif name == 'missing_alias':
                altered.pop(evidence.captures[0].uri)
            elif name == 'relative_raw_alias':
                altered['query/raw/device_info_Q17.txt'] = 'relative-raw-file.txt'
            try:
                LocalAnalysisReceipt(replace(evidence, aliases=FrozenMap(altered),
                                             root='relative-root' if name == 'relative_root' else evidence.root))
            except ValueError:
                failures.append(name)
            else:
                raise AssertionError('Forged alias accepted: ' + name)
print(json.dumps({'status': 'passed', 'blocked_filesystem_calls': blocked, 'body': body.status,
                  'manual': manual.status, 'terminal_count': len(terminals.value),
                  'forged_aliases_rejected': failures, 'input_sha256': inputs,
                  'source_sha256': {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted((root/'layauto_v2').rglob('*.py'))}}, indent=2))
