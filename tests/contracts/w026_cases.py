"""Stage the W026 contrasts before capture and query each publication exactly once."""
from pathlib import Path
from shutil import copyfile

from docs.tasks.W026.example import inspect_published as inspect_published
from w005_cases import FIXTURE, apply_case, copy_input, read_json, rebind, write_json
from w008_geometry_cases import blocks
from w018_cases import COORDINATE_URI, select_projection
from w022_cases import COMPLETE
from w025_cases import stage_spacing


def stage_rules(parent: Path, case: str) -> Path:
    if case == 'cut_gap':
        return stage_spacing(parent, 1)
    root = copy_input(parent)
    if case in ('c14', 'combined'):
        apply_case(root, 'count_correct_rule_wrong')
    if case == 'combined':
        path = root / 'source.gds'
        prefix, elements, suffix = blocks(path.read_bytes())
        original = blocks((FIXTURE / 'source.gds').read_bytes())[1]
        shifted = blocks((FIXTURE / 'failures/via_enclosure/source.gds').read_bytes())[1]
        # Preserve the C14 metal geometry and corresponding net query captures.
        # Take just the one changed VN element from the independently bound case.
        index, = (i for i, (a, b) in enumerate(zip(original, shifted, strict=True)) if a != b)
        assert elements[index] == original[index]
        elements[index] = shifted[index]
        path.write_bytes(prefix + b''.join(elements) + suffix)
    elif case == 'external_equality':
        path = root / 'body/context.json'
        document = read_json(path)
        tap, = (s for s in document['shapes'] if s['id'] == 'TN.ext')
        tap['bbox'] = [-12, 49, -8, 53]
        write_json(path, document)
    elif case in ('via_enclosure', 'body_enclosure'):
        apply_case(root, case)
    elif case not in ('normal', 'c14'):
        raise ValueError(case)
    select_projection(root)
    copyfile(COMPLETE, root / COORDINATE_URI)
    rebind(root)
    return root
