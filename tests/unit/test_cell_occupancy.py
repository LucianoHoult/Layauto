"""M4a: ``CellOccupancy`` B-tier 2D-cell record + ``OccupantType.CUT``.

Verifies the data-model surfaces that M4b (CSP cell-grid + net-equivalence
union-find), M4c (parser tier-dispatch projection), and M4d (diffusion-share
L2 op) plug into. M4a does not yet drive these through the pipeline, so the
tests are pure data-structure exercises.

Roadmap: docs/architecture_roadmap.md §B and milestone M4.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest

from core.data_model import CellOccupancy, OccupantType, ShapeRecord


def test_cut_occupant_type_exists():
    """``OccupantType.CUT`` is the marker for CPO / M0_CUT / FIN_CUT cells."""
    assert OccupantType.CUT is not None
    # Distinct from BLOCKAGE — CUT shapes break net-equivalence at a known
    # location; BLOCKAGE shapes simply forbid use of the cell.
    assert OccupantType.CUT != OccupantType.BLOCKAGE
    assert OccupantType.CUT.name == 'CUT'


def test_cell_occupancy_defaults():
    """A bare DEVICE_DIFF cell has no owner, no sharers, and exposes ``pos``."""
    cell = CellOccupancy(
        layer='OD', track_a=2, track_b=5, occ_type=OccupantType.DEVICE_DIFF,
    )
    assert cell.pos == ('OD', 2, 5)
    assert cell.owner_device_id is None
    assert cell.shared_with == []
    assert cell.shape_record is None
    assert cell.occ_type == OccupantType.DEVICE_DIFF


def test_cell_occupancy_rejects_non_b_tier_occupant():
    """``CellOccupancy`` is for B-tier occupants. WIRE belongs on a TrackSegment.

    The runtime check guards against silently mis-projecting an A-tier
    layer through the B-tier path. Other A-tier-ish types are not allowed
    here, but EMPTY / BLOCKAGE / VIA / CUT / DEVICE_* are fine.
    """
    with pytest.raises(ValueError):
        CellOccupancy(
            layer='LI', track_a=0, track_b=0, occ_type=OccupantType.WIRE,
        )


def test_cell_occupancy_accepts_cut():
    cell = CellOccupancy(
        layer='CPO', track_a=1, track_b=4, occ_type=OccupantType.CUT,
    )
    assert cell.occ_type == OccupantType.CUT
    # CUT cells do not need an owner or sharers — defaults stand.
    assert cell.owner_device_id is None


def test_add_sharer_requires_owner():
    """A cell with no ``owner_device_id`` cannot record a sharer — sharing is
    relative to a primary owner, so the question is ill-defined otherwise."""
    cell = CellOccupancy(
        layer='OD', track_a=0, track_b=0, occ_type=OccupantType.DEVICE_DIFF,
    )
    with pytest.raises(ValueError):
        cell.add_sharer('MN1')


def test_add_sharer_idempotent_and_owner_excluded():
    cell = CellOccupancy(
        layer='OD', track_a=0, track_b=0,
        occ_type=OccupantType.DEVICE_DIFF, owner_device_id='MN0',
    )
    # Adding the owner itself is a no-op.
    assert cell.add_sharer('MN0') is False
    assert cell.shared_with == []
    # First add grows the list.
    assert cell.add_sharer('MN1') is True
    assert cell.shared_with == ['MN1']
    # Second add of the same id is idempotent.
    assert cell.add_sharer('MN1') is False
    assert cell.shared_with == ['MN1']
    # Different id stacks on.
    assert cell.add_sharer('MP0') is True
    assert cell.shared_with == ['MN1', 'MP0']


def test_remove_sharer_round_trip():
    cell = CellOccupancy(
        layer='OD', track_a=0, track_b=0,
        occ_type=OccupantType.DEVICE_DIFF, owner_device_id='MN0',
    )
    cell.add_sharer('MN1')
    assert cell.remove_sharer('MN1') is True
    assert cell.shared_with == []
    # Removing a non-member is a no-op (False) — caller distinguishes.
    assert cell.remove_sharer('MN1') is False


def test_shape_record_backlink():
    """The M3 ``ShapeRecord`` backlink seam carries through to B-tier cells.
    M4c will stamp this on every projected cell so SKILL/DRC closure (M7)
    can walk back to the geometric source of truth."""
    sr = ShapeRecord(layer='OD', bbox_nm=(0, 0, 100, 50), desc='od_block')
    cell = CellOccupancy(
        layer='OD', track_a=0, track_b=0,
        occ_type=OccupantType.DEVICE_DIFF, shape_record=sr,
    )
    assert cell.shape_record is sr
    assert cell.shape_record.layer == cell.layer


def test_repr_shows_owner_and_sharers():
    cell = CellOccupancy(
        layer='OD', track_a=2, track_b=5,
        occ_type=OccupantType.DEVICE_DIFF, owner_device_id='MN0',
    )
    cell.add_sharer('MN1')
    s = repr(cell)
    assert 'OD' in s
    assert '(2,5)' in s
    assert 'MN0' in s
    assert 'MN1' in s


if __name__ == '__main__':
    test_cut_occupant_type_exists()
    test_cell_occupancy_defaults()
    test_cell_occupancy_rejects_non_b_tier_occupant()
    test_cell_occupancy_accepts_cut()
    test_add_sharer_requires_owner()
    test_add_sharer_idempotent_and_owner_excluded()
    test_remove_sharer_round_trip()
    test_shape_record_backlink()
    test_repr_shows_owner_and_sharers()
    print("All M4a CellOccupancy tests passed!")
