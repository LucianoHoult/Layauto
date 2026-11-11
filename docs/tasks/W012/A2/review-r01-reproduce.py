"""Reproduce the original link loop in a fixture with generated outputs absent."""
import hashlib
import json
import re
import tempfile
from pathlib import Path

ROOT = Path('/workspace/Layauto')
HERE = Path(__file__).resolve().parent
source = ROOT / 'docs/tasks/W012/A2/delivery.md'
checker = ROOT / 'docs/tasks/W012/A2/delivery_check-before-R01.py.txt'
if not checker.exists():
    checker = ROOT / 'docs/tasks/W012/A2/delivery_check.py'
generated = {'delivery-check.command.json', 'delivery-check.stdout.txt',
             'delivery-check.stderr.txt', 'delivery-check-result.json'}
links = re.findall(r'\[[^\]]+\]\(([^)]+)\)', source.read_text())
with tempfile.TemporaryDirectory(prefix='w012-a2-r01-', dir='/workspace/work') as directory:
    fixture = Path(directory)
    delivery = fixture / 'delivery.md'
    delivery.write_bytes(source.read_bytes())
    for target in links:
        if '://' in target or target in generated:
            continue
        path = fixture / target.split('#')[0]
        path.parent.mkdir(parents=True, exist_ok=True)
        original = source.parent / target.split('#')[0]
        if original.exists():
            path.write_bytes(original.read_bytes())
        else:
            # This file only satisfies a prior link in this throwaway existence
            # fixture. It contains no review or successful check conclusion.
            path.write_text('Link-existence fixture only; no approval or result.\n')
    assert not any((fixture / name).exists() for name in generated)
    print('Original checker SHA-256:', hashlib.sha256(checker.read_bytes()).hexdigest(), flush=True)
    print('Ordinary links exist in fixture; all four generated output paths absent', flush=True)
    # Original checker existence loop, restricted to its delivery.md iteration.
    for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', delivery.read_text()):
        if '://' not in target:
            assert (delivery.parent / target.split('#')[0]).exists(), (delivery.name, target)
