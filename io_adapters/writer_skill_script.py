"""
Generate SKILL/Skillbridge scripts from edit operations.

Translates EditOp list → SKILL commands for Virtuoso.
In production, adapt the shape-finding logic to your PDK's cell structure.
"""

import os
import sys
from typing import List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.diff import EditOp


def generate_skill_script(edit_ops: List[EditOp],
                          lib_name: str = "YOUR_LIB",
                          cell_name: str = "INV_CELL",
                          view_name: str = "layout") -> str:
    """
    Generate a SKILL script string from edit operations.
    
    Args:
        edit_ops: List of EditOp from solver/diff
        lib_name: Virtuoso library name
        cell_name: Cell name
        view_name: View name
    
    Returns:
        SKILL script as string
    """
    lines = [
        f';;; Auto-generated SKILL script for fin resize',
        f';;; Edit operations: {len(edit_ops)}',
        f'',
        f'procedure(applyFinResize()',
        f'  let((cv)',
        f'    cv = dbOpenCellViewByType("{lib_name}" "{cell_name}" "{view_name}" nil "a")',
        f'    unless(cv error("Could not open cell"))',
        f'    printf("Applying {len(edit_ops)} edit operations...\\n")',
        f'',
    ]
    
    for i, op in enumerate(edit_ops):
        lines.append(f'    ;; Op {i+1}: {op}')
        
        if op.op_type == 'remove_shape':
            x1, y1, x2, y2 = op.old_bbox
            lines.append(
                f'    _removeShapeByBBox(cv "{op.layer}" '
                f'{x1}:{y1} {x2}:{y2})'
            )
        elif op.op_type == 'add_shape':
            x1, y1, x2, y2 = op.new_bbox
            lines.append(
                f'    dbCreateRect(cv list("{op.layer}" "drawing") '
                f'list({x1}:{y1} {x2}:{y2}))'
            )
        elif op.op_type == 'modify_shape':
            ox1, oy1, ox2, oy2 = op.old_bbox
            nx1, ny1, nx2, ny2 = op.new_bbox
            lines.append(
                f'    _resizeShapeByBBox(cv "{op.layer}" '
                f'{ox1}:{oy1} {ox2}:{oy2}  '
                f'{nx1}:{ny1} {nx2}:{ny2})'
            )
        lines.append('')
    
    lines.extend([
        '    dbSave(cv)',
        '    printf("Done. Run DRC to verify.\\n")',
        '  )',
        ')',
        '',
        ';;; Helper: find and remove shape by layer + bbox',
        'procedure(_removeShapeByBBox(cv layerName ll ur)',
        '  printf("  REMOVE %s at %L:%L\\n" layerName ll ur)',
        ')',
        '',
        ';;; Helper: resize shape by changing bbox',
        'procedure(_resizeShapeByBBox(cv layerName oldLL oldUR newLL newUR)',
        '  printf("  RESIZE %s %L:%L -> %L:%L\\n" layerName oldLL oldUR newLL newUR)',
        ')',
    ])
    
    return '\n'.join(lines)


def write_skill_script(edit_ops: List[EditOp], filepath: str, **kwargs):
    """Write SKILL script to file."""
    script = generate_skill_script(edit_ops, **kwargs)
    with open(filepath, 'w') as f:
        f.write(script)
    print(f"  SKILL script written: {filepath} ({len(edit_ops)} ops)")
