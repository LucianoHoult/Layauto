"""Stage the W003/W004 drawings before input capture; used by tests and the example only."""
from pathlib import Path
from shutil import copyfile

from w005_cases import apply_case, copy_input, rebind
from w018_cases import COORDINATE_URI, select_projection
from w022_cases import COMPLETE


def stage(parent: Path, case: str) -> Path:
    root = copy_input(parent)
    if case == 'c14':
        apply_case(root, 'count_correct_rule_wrong')
    elif case != 'normal':
        raise ValueError(case)
    select_projection(root)
    copyfile(COMPLETE, root / COORDINATE_URI)
    rebind(root)
    return root
