"""Locate the C16 mismatch in the published operands available to the planner."""
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory

from docs.tasks.W026.example import inspect_published
from w005_cases import apply_case, copy_input, rebind
from w018_cases import COORDINATE_URI, select_projection
from w022_cases import COMPLETE


def main() -> None:
    with TemporaryDirectory() as tmp:
        root = copy_input(Path(tmp))
        apply_case(root, 'extraction_mismatch')
        select_projection(root)
        copyfile(COMPLETE, root / COORDINATE_URI)
        rebind(root)
        ctx, report, _ = inspect_published(root, 'pm-c16')
    assert ctx.version.version == 0
    assert not ctx.target.differences
    recognition = report.for_rule('T03.recognition')
    assert recognition.status == 'violation'
    differences = [o for o in recognition.observations if o.kind == 'device_parameter'
                   and o.object_ids[0] == 'MN0' and o.facts['axis'] == 'fins_per_finger']
    assert {o.facts['circuit'] for o in differences} == {'source', 'target'}
    for item in differences:
        assert item.status == 'violation'
        assert item.facts['measured'] == (4,) and item.facts['declared'] == 5
        assert item.sources[0].uri == item.facts['circuit'] + '.cdl' and item.sources[0].line == 3
    print('C16 published version 0; source-target differences 0; MN0 extracted 4, both CDL declarations 5')


if __name__ == '__main__':
    main()
