"""
CSP constraint propagation debugger.

Captures snapshots during CSP loading/solving to visualize
how domains shrink step by step. Useful for diagnosing
constraint conflicts.

Usage:
    debugger = CSPDebugger(engine, output_dir)
    debugger.capture('after_load')
    # ... do some assigns ...
    debugger.capture('after_resize')
    debugger.generate_report()
"""

import os
import json
from typing import Optional

from core.csp_engine import ConstraintEngine
from visualization.grid_viewer import plot_csp_layer


class CSPDebugger:
    """Captures and visualizes CSP state at key points."""
    
    def __init__(self, engine: ConstraintEngine, output_dir: str):
        self.engine = engine
        self.output_dir = output_dir
        self.snapshots = []
        os.makedirs(output_dir, exist_ok=True)
    
    def capture(self, label: str):
        """Capture current CSP state with a label."""
        stats = {}
        for layer in self.engine.layer_dims:
            stats[layer] = self.engine.domain_stats(layer)
        
        self.snapshots.append({
            'label': label,
            'stats': stats,
        })
        
        # Generate grid plots for each layer
        for layer in self.engine.layer_dims:
            path = os.path.join(
                self.output_dir,
                f'csp_{label}_{layer}.png'
            )
            plot_csp_layer(
                self.engine, layer, path,
                title=f'{layer} — {label}'
            )
    
    def generate_report(self):
        """Write summary report of all snapshots."""
        report_path = os.path.join(self.output_dir, 'csp_debug_report.txt')
        with open(report_path, 'w') as f:
            f.write("CSP Debug Report\n")
            f.write("=" * 50 + "\n\n")
            for snap in self.snapshots:
                f.write(f"--- {snap['label']} ---\n")
                for layer, stats in snap['stats'].items():
                    f.write(f"  {layer}: {stats}\n")
                f.write("\n")
        print(f"  CSP debug report: {report_path}")
