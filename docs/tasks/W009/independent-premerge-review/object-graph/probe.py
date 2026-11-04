"""Independent retained-object checks, without the product closed-graph helper.

Run from the repository root with PYTHONDONTWRITEBYTECODE=1 and PYTHONPATH=.
The only test-helper use is copying/rebinding a temporary captured fixture for
one expected error; it supplies no object-graph or rejection oracle.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import fields, is_dataclass, replace
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

from layauto_v2.domain.codec import FrozenMap
from layauto_v2.domain.evidence import SourceRef
from layauto_v2.domain.regions import RegionRef
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import build_effective_geometry, build_geometry, geometry_from_parse_result
from layauto_v2.normalization.effective_codec import decode_record, encode_record
from layauto_v2.state.regions import build_effective_draft

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / 'tests/contracts'))
from w007_cases import ready_copy, read
from w009_cases import change_owner


def inspect_graph(root):
    """Inspect backing storage too, and reject all mutable/subclass atoms.

    This uses dataclass metadata, native storage types and field traversal, not
    the production validator or codec as its immutability oracle.
    """
    seen = set()
    counts = Counter()
    def visit(value):
        cls = type(value)
        counts[cls.__module__ + '.' + cls.__qualname__] += 1
        if value is None or any(cls is atom for atom in (bool, int, str, bytes)):
            return
        if id(value) in seen:
            return
        seen.add(id(value))
        if cls is Fraction:
            assert type(value.numerator) is int and type(value.denominator) is int
        elif cls is tuple:
            for item in value:
                visit(item)
        elif cls is FrozenMap:
            assert type(value._entries) is tuple
            for entry in value._entries:
                assert type(entry) is tuple and len(entry) == 2
                key, child = entry
                assert type(key) is str
                visit(child)
        else:
            assert is_dataclass(value) and cls.__dataclass_params__.frozen, cls
            assert cls.__module__.startswith('layauto_v2.'), cls
            for field in fields(value):
                visit(getattr(value, field.name))
    visit(root)
    return {'distinct_nonatomic_objects': len(seen), 'class_occurrences': dict(sorted(counts.items()))}


observations = []
def rejects(label, call):
    try:
        call()
    except ValueError as exc:
        observations.append({'case': label, 'result': 'ValueError', 'message': str(exc)})
    else:
        raise AssertionError('accepted foreign retained object: ' + label)


class TrapText(str):
    def __eq__(self, other):
        raise AssertionError('foreign equality executed before rejection')
    def __ne__(self, other):
        raise AssertionError('foreign inequality executed before rejection')
    __hash__ = str.__hash__


class TrapList(list):
    def __iter__(self):
        raise AssertionError('foreign iteration executed before rejection')


class TrapTuple(tuple):
    def __iter__(self):
        raise AssertionError('foreign iteration executed before rejection')


class PretendRef:
    """isinstance accepts __class__; identity-based graph checks must not."""
    def __init__(self, actual):
        self.actual = actual
        self.mutable = []
    @property
    def __class__(self):
        return SourceRef
    def __getattr__(self, key):
        return getattr(self.actual, key)
    def __eq__(self, other):
        return self.actual == other


accepted = build_effective_geometry(build_geometry(geometry_from_parse_result(
    read_inputs(ROOT / 'tests/fixtures/w003_m1/site_config.yaml'))))
assert accepted.status == 'success'
draft = accepted.value
row = next(item for item in draft.records if item.operation == 'terminal')
region = row.regions[0]
objects = [accepted, draft, draft.operators, row, region, region.pieces[0], region.ref]
positive = []
for original in objects:
    reconstructed = type(original)(**{field.name: getattr(original, field.name) for field in fields(original)})
    decoded = decode_record(encode_record(original))
    assert reconstructed == decoded == original
    positive.append({'type': type(original).__name__, 'constructor': inspect_graph(reconstructed),
                     'decode': inspect_graph(decoded)})

# Guard ordering: a rejection must happen before a foreign equality method or
# iteration can run. These subclasses are intentionally more hostile than a
# merely equal mutable literal or switching iterator.
for owner, field in [(region.ref, 'kind'), (region, 'role'), (row, 'operation'),
                     (draft.operators, 'schema_version'), (region.pieces[0], 'schema_version'),
                     (region, 'schema_version'), (row, 'schema_version'),
                     (draft, 'schema_version'), (accepted, 'schema_version'), (accepted, 'status')]:
    rejects(type(owner).__name__ + '.' + field + '/trap-equality',
            lambda owner=owner, field=field: replace(owner, **{field: TrapText(getattr(owner, field))}))
for owner, field in [(region, 'contributors'), (region, 'rectangles'), (row, 'contributors'),
                     (row, 'regions'), (draft, 'records'), (accepted, 'completed'), (accepted, 'issues')]:
    for container in (TrapList, TrapTuple):
        bad = container(getattr(owner, field))
        rejects(type(owner).__name__ + '.' + field + '/' + container.__name__,
                lambda owner=owner, field=field, bad=bad: replace(owner, **{field: bad}))
    native = list(getattr(owner, field))
    snapshot = replace(owner, **{field: native})
    native.clear()
    assert snapshot == owner
    inspect_graph(snapshot)

# An object can claim SourceRef identity for isinstance while having writable
# state. Legacy EvidenceRecord accepts it through a public constructor; the
# W009 binding seam must reject the original graph before codec conversion.
physical = draft.physical
pretender = PretendRef(physical.sources[0])
assert isinstance(pretender, SourceRef) and type(pretender) is not SourceRef
borrowed_physical = replace(physical, sources=(pretender,))
assert borrowed_physical.sources[0] is pretender
rejects('owner/source-__class__-impersonation/binding',
        lambda: replace(draft.operators, physical=borrowed_physical))
rejects('owner/source-__class__-impersonation/state-builder',
        lambda: build_effective_draft(draft.base, borrowed_physical))
first_fact = accepted.completed[0]
borrowed_fact = replace(first_fact, sources=(PretendRef(first_fact.sources[0]),) + first_fact.sources[1:])
rejects('completed/source-__class__-impersonation/result',
        lambda: replace(accepted, completed=(borrowed_fact,) + accepted.completed[1:]))

# Nested source URI is outside the old SourceRef exact-string contract. The
# outer W009 seam checks the retained native type, including unconsumed fields.
class MutableText(str):
    pass
source = physical.sources[0]
bad_uri = MutableText(source.uri)
bad_uri.mutable = []
bad_source = replace(source, uri=bad_uri)
bad_physical = replace(physical, sources=(bad_source,))
assert bad_physical.sources[0].uri is bad_uri
rejects('owner/nested-source-uri/binding', lambda: replace(draft.operators, physical=bad_physical))

with tempfile.TemporaryDirectory(prefix='w009-object-graph-', dir=ROOT.parent) as scratch:
    fixture = ready_copy(Path(scratch) / 'fixture')
    change_owner(fixture, 'physical', lambda document: document['operators'].__setitem__('terminal_split/1', 'unsupported'))
    rejected = build_effective_geometry(build_geometry(geometry_from_parse_result(read(fixture))))
    assert rejected.status == 'error'
    inspect_graph(rejected)
    inspect_graph(decode_record(encode_record(rejected)))
    bad_issue_source = replace(rejected.issues[0].source, uri=MutableText(rejected.issues[0].source.uri))
    bad_issue = replace(rejected.issues[0], source=bad_issue_source)
    rejects('error/nested-source-uri/result', lambda: replace(rejected, issues=(bad_issue,)))
    for container in (TrapList, TrapTuple):
        bad = container(rejected.issues)
        rejects('error/issues/' + container.__name__, lambda bad=bad: replace(rejected, issues=bad))

result = {
    'reviewed_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
    'python': sys.version,
    'platform': platform.platform(),
    'source_sha256': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in map(Path, [
        'layauto_v2/domain/regions.py', 'layauto_v2/state/regions.py',
        'layauto_v2/normalization/effective.py', 'layauto_v2/normalization/effective_codec.py'])},
    'positive_constructor_and_decode': positive,
    'independent_success_graph_census': inspect_graph(accepted),
    'rejected_cases': observations,
    'rejection_count': len(observations),
    'native_list_defensive_copies': 7,
    'conclusion': 'No retained mutable or foreign object found; all targeted adversarial inputs rejected.'
}
print(json.dumps(result, indent=2))
