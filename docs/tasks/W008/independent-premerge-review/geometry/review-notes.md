# Independent geometry / occupancy review notes

Reviewer: `/root/geometry_review`; did not participate in W008 implementation,
plan design or the original review. Read-only product review of
`131f66dfadd77b5fb9073db999d6939051c3addf` against main
`765ff864f4341b91996f70f25723411eebc0d6c2`. Root AGENTS is the only instruction
file. Product, fixture/answers and original reports were not modified.

## Conclusion

No must-fix finding established in this specialist scope (A3–A5 and neutral
geometry/state constructor coverage within A6). Source code inspection and new
independent arithmetic / binary-input checks support the exact geometry and
multi-occupant index claims. Final aggregate input authentication, full test and
typing results, historical evidence adoption, and the overall merge verdict are
owned by the parent independent review.

## Actual checks

The exact commands, interpreter path, review HEAD, UTC timestamps, return codes,
script hashes and raw-output hashes are in `receipt.json`. `run_probes.py` can
regenerate the outputs using an explicit checkout and Python 3.10+ interpreter.
The final recorded runs use the parent-created independent Python 3.12.14 venv.

- `geometry_probe.py`: 600 deterministic finite partitions, 21,314 exact point
  membership checks, negative coordinates, boundaries, fractional interior
  points, out-of-range rejection, empty partition and very large integer math.
  The oracle enumerates every cell and compares interval membership; it does
  not use the product's bisection or project range construction.
- Independently unpacked all 40 source GDS BOUNDARY records with `struct`,
  checking raw XY, bbox, element/layer/datatype and record/byte locations against
  each resulting record. Independently decoded REAL8 raw bytes with rational
  arithmetic, checked exact/delta preservation and unit inverse conversions at
  signed 32-bit extremes and arithmetic-only ±2**100 values. The latter does
  not expand the accepted GDS coordinate range.
- For every projected record: fragment containment in the original rectangle,
  pairwise zero interior overlap, and area sum equal to source area. These
  properties prove the union covers the rectangle; bidirectional cell/record
  references and exact unit/cell bounds were also checked. The normal 38
  projected records / 41 fragments are corroborating counts, not the oracle.
- Four genuine W005 -> W008 derived-input builds, created only in a temporary
  fixture copy with independently written rectangle stream records and explicit
  header/body hash rebindings: eight-record negative-coordinate sample with
  partly overlapping LI and duplicate LI, reordered stream/reversed and rotated
  corners, removal of only one duplicate, and actual empty GDS. Hand areas are
  35, 30 and 35 for the three LI records; the common cell has three distinct
  occupants. Semantic digest survives only nonsemantic order/vertex changes,
  and changes when record multiplicity changes. C1/C2 remain stored and have no
  main occupancy, VIA0/CONTACT/CUT occupy only their own layers. Empty actual
  input retains valid empty layout/index and roundtrips through the codec.
- Public layout and occupancy omission/duplicate constructors reject; rebuild
  and canonical result roundtrip agree for the normal and all four derived
  builds. The tests do not import expected/spec/oracle or existing test helpers.

## Static reasoning

`coordinate.py:74` derives each projected layer's unique sorted edges solely
from that layer's drawn geometry and policy. `BasePartition` at line 96
regenerates that model, refusing arbitrary replacement axes/algorithm/boundary.
The supported cells tile the finite half-open domain. For any source rectangle,
its own four bounds appear in the axes, so the positive-area intersections at
line 54 cover exactly its interior, without internal overlap; closure preserves
the source closed polygon boundary. Gaps between other rectangles remain empty
index cells and are not legal-route claims.

`occupancy.py:63` iterates every record, retaining duplicate identities and
projecting only its own layer; its constructor at line 87 regenerates the entire
canonical fragment tuple. `layout_store.py:95` reconstructs complete records,
units and policies from bound neutral evidence. The semantic digest at line 117
sorts a tuple rather than a set, so duplicate records retain their multiplicity.
Record identity includes source URI/hash/top/position, independently of that
semantic multiset. Unit conversion at `domain/geometry.py:198` uses exact integer
and Fraction arithmetic with explicit nonintegral rejection. Domain/state have
no importer, normalization, repository, transaction or legacy implementation
dependency; coordinate owns no occupancy.

## Neutral draft boundary and limitations

The intentionally separate `unit_neutral_probe.py` confirms a standalone neutral
`UnitBinding`/codec does not re-decode REAL8 raw bytes: replacing its raw bytes
with eight zeros while preserving positive parsed exact metadata is accepted as
a neutral value. Substituting it into the bound layout is rejected. This is not
evidence of a false successful capture-authenticated aggregate, and is not
reported as a blocker under the task's explicit neutral-evidence versus capture
authentication split. Consumers must not promote standalone neutral DTOs to
verified capture receipts. The outer authentication review remains necessary.

These probes do not prove resource bounds for every maximum-size overlap set,
do not admit another unit/profile, and do not validate physical topology, CUT
Boolean, terminal split, body connectivity/extraction, legal routing coordinates,
publication or real EDA/PDK. Those remain outside W008. No product change is
requested by this specialist review.
