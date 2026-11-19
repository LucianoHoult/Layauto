"""Read-only checkpoint accounting. No product import or computation rerun.

Token buckets are an accounting convention, not removable-byte estimates.
Repeated source string bytes are an overlapping gross upper bound before the
cost of dictionary entries/indexes and before semantic reconstruction checks.
"""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')

def main():
    raw = (HERE / 'local-diagnostic.json').read_bytes()
    report = json.loads(raw)
    assert encoded(report) == raw
    stages = []
    for name in ('local-probe-report', 'local-probe-report-reduced', 'local-probe-report-sources'):
        rows = [json.loads(line) for line in (HERE / (name + '.stdout.txt')).read_text().splitlines()]
        times = [r for r in rows if 'stage' in r]
        size = next(r for r in rows if 'report_bytes' in r)
        stages.append({'log': name + '.stdout.txt', **size,
            'stage_sum_seconds': sum(r['seconds'] for r in times),
            'report_seconds': next(r['seconds'] for r in times if r['stage'] == 'diagnostic_report'),
            'hwm_kib': max(r['hwm_kib'] for r in times), 'stages': times})
    # Exact disjoint lexical accounting, including every JSON key and delimiter.
    counts = Counter()
    strings = defaultdict(Counter)
    def visit(x, category='fact_values'):
        if isinstance(x, dict):
            if set(x) == {'ref'}:
                counts['graph_reference_tokens'] += len(encoded(x))
                return
            if ('capture' in x or 'payload_sha256' in x or
                (('sha256' in x) and ('path' in x or 'uri' in x)) or
                set(x) == {'derivation', 'sources'}):
                category = 'provenance_values'
            if x.get('type', '').endswith(('Ref', 'Id')):
                category = 'identity_reference_values'
            counts['presentation_keys_and_syntax'] += 2 + max(0, len(x) - 1)
            for key, val in x.items():
                counts['presentation_keys_and_syntax'] += len(encoded(key)) + 1
                child_category = 'presentation_type_and_version_values' if key in ('type', 'schema_version') else category
                visit(val, child_category)
        elif isinstance(x, list):
            counts['presentation_keys_and_syntax'] += 2 + max(0, len(x) - 1)
            for val in x:
                visit(val, category)
        else:
            counts[category] += len(encoded(x))
            if isinstance(x, str):
                strings[category][x] += 1
    visit(report)
    assert sum(counts.values()) == len(raw)
    table = report['objects']
    table_bytes = [encoded(row) for row in table]
    duplicates = len(table_bytes) - len(set(table_bytes))
    # Exact storage attribution by root reachability: shared rows counted once.
    def refs(x):
        if isinstance(x, dict):
            if set(x) == {'ref'}:
                yield x['ref']
            else:
                for v in x.values(): yield from refs(v)
        elif isinstance(x, list):
            for v in x: yield from refs(v)
    reach = {}
    for name, root in report['facets'].items():
        seen, pending = set(), list(refs(root))
        while pending:
            i = pending.pop()
            assert type(i) is int and 0 <= i < len(table)
            if i not in seen:
                seen.add(i); pending.extend(refs(table[i]))
        reach[name] = seen
    groups = defaultdict(lambda: {'rows': 0, 'bytes': 0})
    for i, row in enumerate(table_bytes):
        owners = [k for k, reachable in reach.items() if i in reachable]
        group = owners[0] if len(owners) == 1 else 'shared_by_multiple_facets' if owners else 'unreachable'
        groups[group]['rows'] += 1
        groups[group]['bytes'] += len(row)
    overhead = len(raw) - sum(map(len, table_bytes))
    provenance = strings['provenance_values']
    repeated = [(v, n) for v, n in provenance.items() if n > 1]
    output = {
        'report_sha256': hashlib.sha256(raw).hexdigest(), 'report_bytes': len(raw),
        'capture_bytes': sum(r['bytes'] for r in report['captures']), 'capture_count': len(report['captures']),
        'historical_measurements': stages,
        'lexical_buckets': {k: {'bytes': v, 'percent': 100*v/len(raw)} for k,v in sorted(counts.items())},
        'facet_storage': {k: {**v, 'percent': 100*v['bytes']/len(raw)} for k,v in sorted(groups.items())},
        'outer_capture_root_and_array_syntax_bytes': overhead,
        'duplicate_complete_table_rows': duplicates,
        'repeated_provenance_strings': {
            'distinct_repeated': len(repeated),
            'gross_repeated_bytes_after_first_occurrence': sum((n-1)*len(encoded(v)) for v,n in repeated),
            'interpretation': 'overlaps lexical buckets; not net savings; dictionary/ref overhead excluded',
            'largest': [{'value': v, 'occurrences': n, 'gross_repeated_bytes': (n-1)*len(encoded(v))}
                        for v,n in sorted(repeated, key=lambda p: -(p[1]-1)*len(encoded(p[0])))[:10]]},
        'caveats': ['fact_values includes source declarations as well as derived values',
                    'provenance and identity/reference tokens include necessary information, not all duplication',
                    'zero duplicate table rows does not establish zero semantic duplication or zero repeated inline values',
                    'historical timings are single observations, not controlled performance comparisons']}
    (HERE / 'checkpoint-metrics.json').write_text(json.dumps(output, indent=2, ensure_ascii=False)+'\n')
    print(json.dumps({k: output[k] for k in ('report_bytes','capture_bytes','lexical_buckets','facet_storage','outer_capture_root_and_array_syntax_bytes','duplicate_complete_table_rows')}, indent=2))
    print('repeated provenance gross bytes', output['repeated_provenance_strings']['gross_repeated_bytes_after_first_occurrence'])

if __name__ == '__main__':
    main()
