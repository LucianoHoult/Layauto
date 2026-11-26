"""Check the declared 2D occupancy of POLY through the W022 full-run entry."""

from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

from layauto_v2.state.layer_checks import LayerInitializationChecks
from w005_cases import rebind, write_json
from w018_cases import COORDINATE_URI
from w022_cases import assemble, sample


def run(parent: Path) -> None:
    root = sample(parent, complete=True)
    owner = root / COORDINATE_URI
    model = yaml.safe_load(owner.read_bytes())
    layers = model["coordinate_projection"]["layers"]
    layers["POLY"] = layers["OD"].copy()  # Explicit 20 x 10 DBU grid, as already used by OD.
    write_json(owner, model)
    rebind(root)
    candidate, repository, before = assemble(root, 400)
    result = LayerInitializationChecks(candidate)
    gate = result.layers["POLY"]

    record, = (row for row in candidate.layout.records if row.layer == "POLY")
    assert record.source.byte_offset == 432 and record.rect.bounds == (58, 10, 62, 190)
    pieces = candidate.occupancy.for_record(record.id, view="drawn")
    # Drawn x=[58,62) crosses x=60. Drawn y=[10,190) covers 18 rows of height 10.
    expected = {(i, j): (x0, 10*j, x1, 10*(j+1))
                for i, x0, x1 in ((2, 58, 60), (3, 60, 62)) for j in range(1, 19)}
    assert len(pieces) == 36 and {f.indices: f.rect.bounds for f in pieces} == expected
    assert sum(f.rect.area for f in pieces) == record.rect.area == 720
    assert gate.initialization.projection.projection == "2d_cells"
    assert gate.initialization.availability == "reconstructed" and gate.lifecycle_passed
    assert all(row.passed for name, row in result.layers.items() if name != "POLY")
    assert repository.snapshot() == before
    print("POLY: 36 fragments, 720 DBU², record offset 432, 14 other layers passed")
    print("projection_passed =", gate.projection_passed, "overall =", result.passed,
          "projection_issues =", [issue.code for issue in gate.projection_issues])
    assert gate.projection_passed and result.passed, "explicit 2D occupancy rejected"


if __name__ == "__main__":
    with TemporaryDirectory() as directory:
        run(Path(directory))
