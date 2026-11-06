# W010 independent geometry/topology review

Reviewer: `/root/code_review/math_review`, not involved in design, implementation,
or formal tests. Reviewed base `9758a157115cc22d91ce095ac2002209b9f210d3` through
frozen product `0f5029df935bc0acd106aad1bc2be81304d4f442` after the parent confirmed
the complete engineering matrix had passed. This is a scoped review result, not
PM acceptance, merge authorization, or a full W010 review conclusion.

No must-fix finding was identified in the inspected mathematics and topology.
The new `state/local_connectivity.py` and neutral graph DTOs were read in full,
with the actual captured-result composition entry and relevant existing `Rect`,
W009 region and fixture-transform contracts. The comparison was against W010
A2–A5 and geometry portions of A3/A6/A7, architecture §3.6/4.7/8.4/8.5, and the
captured physical/drawn/local T05 meanings. No product or formal test was changed.

The same-layer test uses positive rectangle intersection width with nonnegative
height, or the converse, so a shared point produces no edge. The graph performs
the test once per independent region pair. Connector selection tests each node's
exact pieces for positive area and requires one region on each declared side
before any grouping or enclosure decision. Duplicate source records therefore
remain distinct candidates. Each connector receives its own edge and two audits;
enclosure violations do not remove edges. Every node initializes the component
adjacency map, preserving isolated local BODY nodes. Local channel regions and
the external body scope do not become local conductor nodes or implicit edges.

Enclosure expands the connector with an exact `Fraction(1, canonical_tick_nm)`.
Its x-slab/y-interval union coverage proves containment across multiple pieces;
gaps and holes fail, while equality and contiguous coverage pass. This is exact
set containment rather than a region bbox, one-piece or area-only test.

Independent script [math-probe.py](math-probe.py), output
[math-result.json](math-result.json), raw [stdout](math-stdout.txt), empty
[stderr](math-stderr.txt), and [artifact/source receipt](math-receipt.json) retain
the actual run identity and material hashes. Command was
`/workspace/.venvs/w010-dev312/bin/python -B docs/tasks/W010/review/math-probe.py`
from `/workspace/Layauto`, Python 3.12.14, 2026-11-05 03:00 UTC, approximately
20.03 seconds. The probe and final hash check leave the inspected product bytes
unchanged.

- **10,000 contact comparisons:** 5,000 seeded random rectangle-set pairs,
  including empty, overlapping and repeated pieces, each at original coordinates
  and translated by `(2**120, -2**120)`. Expected contact comes from occupied unit
  square sets and four-neighbor shared unit edges. It calls no product contact or
  formal-test arrangement oracle to compute expected outcomes.
- **10,000 enclosure comparisons:** 5,000 seeded covers/targets and exact margins
  (denominators 1–7, including zero), each at original and large negative/positive
  translated coordinates. Expected containment comes from successively peeling
  each covering rectangle from rational uncovered target rectangles, a different
  algorithm from the implementation's slab sweep. Both true and false outcomes
  occurred in each predicate family.
- **Four actual captured graphs:** normal **14 nodes / 8 edges / 6 components**;
  `via_enclosure` **14 / 8 / 6**, retaining the connector edge with local status
  `violation`; cut-islands **3 / 0 / 3**; a generated topology with duplicates,
  point contact, edge contact, overlaps, a multi-piece LI hole and repeated
  connectors **36 / 67 / 10** with **22** per-side enclosure audits. Every node,
  complete edge multiset, audit, and component membership was compared, using
  independent pixel contact/positive-area sets, rational peeling, and all-pairs
  boolean transitive closure for grouping. The normal case also ran the public
  capture-bound result constructor; the other three used the public neutral
  builder on successful actual W005→W008→W009 captures.
- **Five actual located rejections:** duplicate LI source, two same-layer
  connected LI candidates, a second LI candidate failing enclosure, edge-only
  VIA contact and corner-only VIA contact. The first three report two independent
  regions, the last two zero; all reject with `AmbiguousConnectorEndpoint`.

Existing fixture-transform helpers were used only to copy/rebind temporary
captured bytes; their geometry oracles were not used. Expected W010 node scope
was derived from the accepted W009 upstream regions and original record
identities, then independently checked against the emitted node multiset. The
tests exercise finite samples, not maximum supported-input resource bounds or
production performance. Capture forgery, full nested exceptions, codec closure,
package/install identity and total engineering evidence are left to the parent
reviewer's separate coverage.
