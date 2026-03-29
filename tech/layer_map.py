"""
GDS layer/datatype mapping for the dummy process.

In production, these would come from the foundry's layer map file.
For the dummy, we assign simple sequential numbers.
"""

# (layer_number, datatype)
LAYER_MAP = {
    'FIN':      (1, 0),    # Fin / Active (OD) 
    'POLY':     (2, 0),    # Poly gate
    'LI':       (3, 0),    # Local Interconnect
    'VIA0':     (4, 0),    # Via0 (LI to M1)
    'M1':       (5, 0),    # Metal 1
    'OD':       (6, 0),    # Active region (continuous OD block)
    'NWELL':    (7, 0),    # N-well (for PMOS)
    'BOUNDARY': (10, 0),   # Cell boundary
}

# Reverse lookup
GDS_TO_LAYER = {v: k for k, v in LAYER_MAP.items()}

# Display colors for visualization (R, G, B, alpha)
LAYER_COLORS = {
    'FIN':      (0.2, 0.8, 0.2, 0.5),   # Green
    'POLY':     (0.8, 0.2, 0.2, 0.6),   # Red
    'LI':       (0.2, 0.2, 0.9, 0.5),   # Blue
    'VIA0':     (0.9, 0.9, 0.0, 0.8),   # Yellow
    'M1':       (0.8, 0.4, 0.0, 0.5),   # Orange
    'OD':       (0.2, 0.6, 0.2, 0.2),   # Light green
    'NWELL':    (0.6, 0.6, 0.6, 0.1),   # Gray
    'BOUNDARY': (0.5, 0.5, 0.5, 0.3),   # Gray
}
