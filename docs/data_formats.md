# Data Formats

## Calibre Device Query JSON
```json
[
  {
    "instance": "MN0",
    "device_type": "NMOS",
    "parameters": { "nfin": 5, "nf": 1, "l": 20, "w": 125 },
    "pins": { "G": "IN", "D": "OUT", "S": "VSS", "B": "VSS" },
    "bbox": { "x1": 27, "y1": 28, "x2": 81, "y2": 152 },
    "fin_y_positions": [40, 65, 90, 115, 140]
  }
]
```

## Calibre Net Query JSON
```json
{
  "VSS": {
    "type": "power",
    "pins": [["MN0", "S"], ["MN0", "B"]],
    "shapes": [
      { "layer": "LI", "x1": 18, "y1": 13, "x2": 35, "y2": 145, "desc": "li_nmos_source" },
      { "layer": "M1", "x1": 0, "y1": 8, "x2": 108, "y2": 28, "desc": "m1_vss" },
      { "layer": "VIA0", "x1": 18, "y1": 10, "x2": 35, "y2": 27, "desc": "via0_nmos_source" }
    ]
  }
}
```

## Bbox-by-Layer JSON
```json
{
  "FIN": [
    { "x1": 0, "y1": 37, "x2": 108, "y2": 44, "net": "", "desc": "nmos_fin_0" }
  ],
  "LI": [
    { "x1": 18, "y1": 13, "x2": 35, "y2": 145, "net": "VSS", "desc": "li_nmos_source" }
  ]
}
```

## Production Adaptation
In production, these JSONs come from Calibre SVDB queries. The exact format
may differ — adapt `io_adapters/parser.py` accordingly. The `core/` code
only sees `LayoutModel` objects, never raw JSON.
