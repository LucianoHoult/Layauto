"""Independent FXR-01 single-snapshot compatibility control on real W005 input."""
from dataclasses import replace
import json
from pathlib import Path
import sys

from layauto_v2.importers import read_inputs

root = Path(__file__).resolve().parents[4]
parsed = read_inputs(root / 'tests/fixtures/w003_m1/site_config.yaml')
assert parsed.status == 'success'


class Alternating(list):
    def __init__(self, first, second):
        super().__init__(first)
        self.first, self.second, self.iterations = first, second, 0

    def __iter__(self):
        self.iterations += 1
        return iter(self.first if self.iterations == 1 else self.second)


rows = []
for record, field in [(parsed.completed[0], 'sources')] + [
        (parsed, field) for field in ('sources', 'completed', 'issues')]:
    values = getattr(record, field)
    for valid_first in (True, False):
        caller = Alternating(values if valid_first else [None], [None] if valid_first else values)
        try:
            result = replace(record, **{field: caller})
        except ValueError as exc:
            row = dict(passed=not valid_first and caller.iterations == 1,
                       exception=type(exc).__name__, diagnostic=str(exc))
        except BaseException as exc:
            row = dict(passed=False, exception=type(exc).__name__, diagnostic=str(exc))
        else:
            caller.first = [None]
            row = dict(passed=valid_first and caller.iterations == 1
                       and getattr(result, field) == values and result == record,
                       saved_type=type(getattr(result, field)).__name__)
        row.update(record=type(record).__name__, field=field, valid_first=valid_first,
                   iterations=caller.iterations)
        rows.append(row)
report = dict(python=sys.version, executable=sys.executable, cases=rows,
              status='passed' if all(row['passed'] for row in rows) else 'failed')
print(json.dumps(report, indent=2))
raise SystemExit(report['status'] != 'passed')
