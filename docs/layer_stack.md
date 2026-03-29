# Layer Stack (Dummy 7nm-class)

## Layer Orientations and Pitches
```
Layer   Orient  Pitch   Grid Offset   Ortho Layer
─────   ──────  ─────   ───────────   ───────────
FIN     H       25nm    40nm (Y)      POLY
POLY    V       54nm    0nm  (X)      FIN
LI      V       27nm    0nm  (X)      M1
VIA0    -       -       -             -
M1      H       36nm    18nm (Y)      LI
```

## Grid Convention
- V layers: pitch defines X spacing, tracks run along Y
- H layers: pitch defines Y spacing, tracks run along X
- LI pitch = half gate pitch (27nm) to cover both S/D and gate contacts

## Cross Section
```
M1 tracks (H, pitch=36nm):
  ═══ t0 ═══  ═══ t1 ═══  ═══ t2 ═══  ...
       │            │            │
      Via0         Via0
       │            │
LI tracks (V, pitch=27nm):
  t0(0) t1(27) t2(54) t3(81) t4(108)
  dummy  S/D   gate    S/D   dummy

POLY gates (V, pitch=54nm):
  t0(0)        t1(54)        t2(108)
  dummy_L      active        dummy_R

FIN (H, pitch=25nm):
  ─── f0 ───  ─── f1 ───  ... ─── fn ───
```

## GDS Layer Map
| Layer | GDS Layer:Datatype |
|-------|-------------------|
| FIN | 1:0 |
| POLY | 2:0 |
| LI | 3:0 |
| VIA0 | 4:0 |
| M1 | 5:0 |
| OD | 6:0 |
| NWELL | 7:0 |
| BOUNDARY | 10:0 |
