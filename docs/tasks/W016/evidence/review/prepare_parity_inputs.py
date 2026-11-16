"""Copy unchanged captures and declared failure replacements at fixed URIs.

No product parser, expected answer, fixture generator, or body verifier is used.
Invoke once before both source revisions: --fixture .../tests/fixtures/w003_m1
--out /tmp/w016-parity-inputs. Outputs must not preexist.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    fixture, output = args.fixture.resolve(), args.out.resolve()
    output.mkdir(parents=True, exist_ok=False)
    cases = json.loads((fixture / 'failures/cases.json').read_text())['cases']
    rows = {}
    for name in ('normal', 'extraction_mismatch', 'body_enclosure'):
        destination = output / name
        shutil.copytree(fixture, destination, ignore=shutil.ignore_patterns('failures', 'special'))
        if name != 'normal':
            declaration = next(row for row in cases if row['id'] == name)
            for target, source in declaration['replacement_files'].items():
                shutil.copyfile(fixture / 'failures' / source, destination / target)
            for target in declaration['remove_files']:
                (destination / target).unlink()
        rows[name] = {str(path.relative_to(destination)): hashlib.sha256(path.read_bytes()).hexdigest()
                      for path in sorted(destination.rglob('*')) if path.is_file()}
    (output / 'manifest.json').write_text(json.dumps({'fixture': str(fixture), 'files': rows}, indent=2) + '\n')


if __name__ == '__main__':
    main()
