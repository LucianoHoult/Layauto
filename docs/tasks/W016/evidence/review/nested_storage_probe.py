"""Small independent native-storage probe against actual candidate inputs.

--expect-rejected is for a corrected implementation. No files are mutated;
only a newly acquired in-memory capture is deliberately forged.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from layauto_v2.importers.analysis_reader import acquire_analysis
from layauto_v2.normalization.analysis_input import LocalAnalysisReceipt

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--expect-rejected', action='store_true')
args = parser.parse_args()
path = ROOT / 'docs/tasks/W015/evidence/candidate-input/analysis.json'
evidence = acquire_analysis(path)
assert not evidence.issues
valid = LocalAnalysisReceipt(evidence)
object.__setattr__(evidence.captures[0], 'undeclared_mutable', [])
try:
    LocalAnalysisReceipt(evidence)
except ValueError as exc:
    result = {'rejected': True, 'error': str(exc)}
else:
    result = {'rejected': False, 'error': None}
result['valid_receipt_ref'] = valid.ref
result['source_hashes'] = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                         for path in sorted((ROOT / 'layauto_v2').rglob('*.py'))}
print(json.dumps(result, indent=2))
assert result['rejected'] is args.expect_rejected
