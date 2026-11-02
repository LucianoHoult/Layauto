from pathlib import Path
from tempfile import TemporaryDirectory
from dataclasses import replace
from fractions import Fraction
from w007_cases import ready_copy, edit, normal, read
from w005_cases import rebind
from layauto_v2.normalization import normalize, from_parse_result

with TemporaryDirectory(prefix='w007-pm-scope-', dir='/workspace/work') as temporary:
    parent = Path(temporary)
    base = ready_copy(parent / 'base')
    baseline = normal(base)
    assert baseline.value.semantic_equal
    assert not any(hasattr(baseline, name) for name in ('no_change', 'terminal', 'baseline', 'body_complete'))
    target = ready_copy(parent / 'target')
    edit(target, 'target.cdl', 'VT=toy W=2n L=4n M=1 NF=1 NFIN=5', 'VT=toy W=3n L=5n M=2 NF=2 NFIN=5')
    rebind(target)
    result = normal(target)
    changed = {delta.axis: (delta.semantic_before.exact, delta.semantic_after.exact) for delta in result.value.differences}
    assert changed == {'fin_width': (Fraction(2, 10**9), Fraction(3, 10**9)), 'channel_length': (Fraction(4, 10**9), Fraction(5, 10**9)), 'multiplicity': (Fraction(1), Fraction(2)), 'finger_count': (Fraction(1), Fraction(2))}, changed
    assert not result.value.semantic_equal
    assert all('planner_admission_required' in delta.obligations for delta in result.value.differences)
    try:
        replace(result.value, differences=result.value.differences[:-1])
    except ValueError:
        pass
    else:
        raise AssertionError('incomplete public differences accepted')
    source = ready_copy(parent / 'source')
    edit(source, 'source.cdl', 'NF=1', 'NF=2')
    rebind(source)
    rejected = normalize(from_parse_result(read(source)))
    assert rejected.status == 'error' and rejected.issues[0].code == 'UnsupportedFingerCount'
    try:
        replace(rejected, status='success', value=rejected.completed, issues=())
    except ValueError:
        pass
    else:
        raise AssertionError('public success relabel accepted')
    print('PASS: baseline semantic equality makes no run-state claim; same NFIN retains exact L/W/M/NF target changes and planner obligations; incomplete public delta set rejected; source NF=2 yields located UnsupportedFingerCount and cannot be relabeled success.')
