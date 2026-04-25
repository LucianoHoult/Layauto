"""
Layout diff: compare two LayoutModel instances and generate edit operations.

This module is the bridge between the solver (which works in abstract
track-segment space) and the writers (which need physical coordinates
for GDS/SKILL output).
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict

from core.data_model import LayoutModel, TrackSegment, ViaInstance
from core.grid import MultiLayerGrid


@dataclass
class EditOp:
    """A single layout edit operation.

    Canonical op_type values: 'remove_shape', 'add_shape', 'modify_shape',
    'resize_device'. This class is the L1 record consumed by writeback
    (GDS/SKILL emitters) — see docs/architecture_roadmap.md (M1).
    """
    op_type: str
    layer: str
    old_bbox: Optional[Tuple] = None  # (x1, y1, x2, y2) in nm
    new_bbox: Optional[Tuple] = None  # (x1, y1, x2, y2) in nm
    net_id: str = ''
    desc: str = ''

    def __repr__(self):
        if self.op_type == 'remove_shape':
            return f"REMOVE {self.layer} {self.desc} bbox={self.old_bbox}"
        elif self.op_type == 'add_shape':
            return f"ADD    {self.layer} {self.desc} bbox={self.new_bbox}"
        elif self.op_type == 'modify_shape':
            return f"MODIFY {self.layer} {self.desc} {self.old_bbox} → {self.new_bbox}"
        elif self.op_type == 'resize_device':
            return f"RESIZE {self.desc}"
        return f"{self.op_type} {self.desc}"


def compute_shape_diff(orig_data: dict, modified_data: dict,
                       layers: List[str] = None) -> Dict[str, dict]:
    """
    Compare two layout data dicts shape-by-shape.
    
    Returns per-layer diff: {layer: {unchanged, removed, added}}.
    """
    if layers is None:
        layers = ['FIN', 'OD', 'POLY', 'LI', 'VIA0', 'M1']
    
    result = {}
    for layer in layers:
        orig_shapes = orig_data.get('shapes', {}).get(layer, [])
        mod_shapes = modified_data.get('shapes', {}).get(layer, [])
        
        def shape_key(s):
            return (s['x1'], s['y1'], s['x2'], s['y2'])
        
        orig_set = {shape_key(s) for s in orig_shapes}
        mod_set = {shape_key(s) for s in mod_shapes}
        
        result[layer] = {
            'unchanged': sorted(orig_set & mod_set),
            'removed': sorted(orig_set - mod_set),
            'added': sorted(mod_set - orig_set),
        }
    
    return result


def diff_to_edit_ops(diff: Dict[str, dict]) -> List[EditOp]:
    """Convert shape diff to list of EditOp."""
    ops = []
    for layer, info in diff.items():
        for bbox in info['removed']:
            ops.append(EditOp('remove_shape', layer, old_bbox=bbox))
        for bbox in info['added']:
            ops.append(EditOp('add_shape', layer, new_bbox=bbox))
    return ops
