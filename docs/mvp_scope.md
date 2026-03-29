# MVP Scope

## Target Operation
Single-cell fin resize: reduce NMOS and PMOS fin count by 1 each
within a CMOS inverter (INV) cell.

- NMOS: 5fin → 4fin
- PMOS: 7fin → 6fin

## Layers Involved
| Layer | Role in Resize | Modification |
|-------|---------------|-------------|
| FIN/OD | Device body | Remove outermost fin, shrink OD |
| POLY | Gate | Shorten vertical extent |
| LI | S/D contact | Shorten bar height |
| VIA0 | LI-to-M1 | Position unchanged (via landing still covered) |
| M1 | Routing | Unchanged for MVP |

## What's NOT in Scope
- Cross-cell routing impact
- Cell height change / row adjustment
- M2 and above layers
- Buffer insertion/deletion
- Multi-patterning constraints
- Full from-scratch placement/routing

## Constraints
- Only process cell-internal modifications
- Cell boundary is fixed
- M1 routing positions don't change
- DRC subset: LI/M1 spacing, via enclosure
