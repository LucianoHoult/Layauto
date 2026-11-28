"""Read a Stage 5 decision and its witnesses from the process-local repository.

Run from the repository root:
    PYTHONPATH=.:tests/contracts python -B docs/tasks/W027/example.py
    PYTHONPATH=.:tests/contracts python -B docs/tasks/W027/example.py --all-evidence combined
"""
import argparse
import json
from collections import Counter
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory
from time import perf_counter

from docs.tasks.W026.example import json_value
from layauto_v2.domain.publication import Stage5Request
from layauto_v2.pipeline import prepare_stage5, publish_stage2
from layauto_v2.repository import PublicationRepository
from w005_cases import apply_case, copy_input, read_json, rebind, write_json
from w011_cases import change_cdl
from w018_cases import COORDINATE_URI, select_projection
from w022_cases import COMPLETE
from w023_cases import capture, sample
from w026_cases import stage_rules

CASES = ('normal', 'c13', 'multi', 'c16', 'c14', 'c15', 'combined', 'missing_t07')


def stage_sample(parent: Path, case: str) -> Path:
    """Prepare actual W003/W004 inputs with the W022 full grid before capture."""
    if case in ('c13', 'multi'):
        root = sample(parent, c13=True)
        if case == 'multi':
            change_cdl(root, 'target', 'NFIN=7 NF=1 M=1 L=4n W=2n', 'NFIN=7 NF=1 M=1 L=4n W=3n')
        return root
    if case == 'c16':
        root = copy_input(parent)
        apply_case(root, 'extraction_mismatch')
        select_projection(root)
        copyfile(COMPLETE, root / COORDINATE_URI)
        rebind(root)
        return root
    if case == 'missing_t07':
        root = stage_rules(parent, 'normal')
        path = root / 'tech/rules.json'
        document = read_json(path)
        document['rules'] = [row for row in document['rules'] if row['id'] != 'T07.m1_spacing']
        write_json(path, document)
        rebind(root)
        return root
    return stage_rules(parent, 'via_enclosure' if case == 'c15' else case)


def publish_sample(root: Path, run_id: str):
    repository = PublicationRepository()
    _, publication = capture(repository, root, run_id, lineage=run_id, budget=400)
    context = publish_stage2(repository, publication)
    attempt = repository.load_attempt(run_id)
    request = Stage5Request.from_sealed(attempt, context, idempotency_key='close-' + run_id)
    return repository, request


def inspect_sample(root: Path, run_id: str, all_evidence: bool = False):
    repository, request = publish_sample(root, run_id)
    seconds = {}
    prepared = prepare_stage5(repository, request, on_timing=seconds.__setitem__)
    start = perf_counter()
    repository.close_stage5(request, prepared)
    seconds['close'] = perf_counter() - start

    attempt = repository.load_attempt(run_id)
    closure = repository.read(attempt.closure_ref)
    record = repository.read(closure.run_record_ref)
    planning = repository.read(record.planning_ref)
    rules = repository.read(record.rule_ref) if record.rule_ref else None
    head = repository.read(record.binding.head_ref)
    snapshot = repository.read(record.final_snapshot_ref)
    failure = repository.read(record.failure_ref) if record.failure_ref else None

    # Default output identifies every checked rule, both FIN measurements, and
    # the located observations or pairs behind every non-pass result.
    targets = [o for o in planning.observations if o['kind'] == 'target_difference'
               or (o['kind'] == 'device_parameter' and o['facts']['axis'] == 'fins_per_finger'
                   and o['facts']['circuit'] == 'target')]
    rule_rows = []
    for check in rules.checks if rules else ():
        if all_evidence:
            rule_rows.append(check)
            continue
        row = {key: check[key] for key in ('id', 'status', 'source')}
        if check['status'] != 'pass':
            row.update(issue=check['issue'], policy_action=check['policy_action'],
                       observations=[o for o in check['observations'] if o['status'] == 'violation'],
                       threshold_nm=check['threshold_nm'],
                       pairs=[p for p in check['pairs'] if p['status'] == 'violation'])
        rule_rows.append(row)
    return {
        'sample': run_id, 'status': record.status, 'phase': attempt.phase,
        'closure': attempt.closure_ref.id, 'run_record': closure.run_record_ref.id,
        'checked_head': record.binding.head_ref.id, 'head_status': record.head_status_at_finalization,
        'snapshot': record.final_snapshot_ref.id, 'version': snapshot.version,
        'target': record.binding.target_ref.id, 'ordered_commit_ids': record.ordered_commit_ids,
        'head_eco_commits': head.eco_commits,
        'planning_audit': record.planning_ref.id,
        'planning_counts': Counter(o['kind'] for o in planning.observations),
        'planning_observations': planning.observations if all_evidence else targets,
        'planning_issues': planning.issues, 'rule_audit': record.rule_ref.id if record.rule_ref else None,
        'rule_checks': rule_rows, 'rule_issues': rules.issues if rules else (), 'failure': failure,
        'seconds': {name: round(value, 6) for name, value in seconds.items()},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cases', nargs='*', metavar='CASE', help=', '.join(CASES))
    parser.add_argument('--all-evidence', action='store_true', help='include all planning and rule observations')
    args = parser.parse_args()
    for case in args.cases or CASES:
        if case not in CASES:
            parser.error(f'unknown case {case!r}, choose from {", ".join(CASES)}')
        with TemporaryDirectory() as directory:
            root = stage_sample(Path(directory), case)
            result = inspect_sample(root, case, args.all_evidence)
            print(json.dumps(result, default=json_value, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
