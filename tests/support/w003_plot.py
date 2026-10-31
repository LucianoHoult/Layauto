"""Draw the W003 handwritten spec for review; figure is not a correctness oracle."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    spec = json.loads((args.fixture / 'spec.json').read_text())
    fig, axes = plt.subplots(1, 3, figsize=(13, 6), gridspec_kw={'width_ratios': [1, 1, 0.8]})
    colors = {'BODY_N': '#d9eef8', 'BODY_P': '#f5d9e6', 'OD': '#60b59a',
              'POLY': '#cb5959', 'FIN': '#435165', 'M1': '#659ad2',
              'LI': '#d69b45', 'CUT': '#d95656', 'BOUNDARY': '#263245',
              'CONTACT': '#3b3939', 'VIA0': '#744b9c', 'GCONTACT': '#744b9c',
              'BTAP_N': '#744b9c', 'BTAP_P': '#744b9c', 'MARKER': '#747474'}
    groups = [{'BOUNDARY', 'BODY_N', 'BODY_P', 'OD', 'POLY', 'FIN'},
              {'BOUNDARY', 'M1', 'LI', 'CUT', 'CONTACT', 'VIA0', 'GCONTACT', 'BTAP_N', 'BTAP_P', 'MARKER'},
              {'LI', 'CUT'}]
    for ax, group in zip(axes, groups):
        for shape in spec['shapes']:
            layer = shape['layer']
            if layer not in group: continue
            x0, y0, x1, y1 = shape['bbox']
            if ax is axes[2] and shape['id'] not in ['LB', 'CUTB']: continue
            ax.add_patch(Rectangle((x0, y0), x1-x0, y1-y0,
                         facecolor='none' if layer == 'BOUNDARY' else colors[layer],
                         edgecolor=colors[layer], alpha=0.6 if layer in ['M1', 'LI', 'OD'] else 0.9, linewidth=0.7))
            if layer not in ['FIN', 'BOUNDARY', 'BODY_N', 'BODY_P', 'CONTACT', 'VIA0', 'GCONTACT', 'BTAP_N', 'BTAP_P']:
                ax.text(x0, y1+2, shape['id'], fontsize=8)
        ax.set_aspect('equal'); ax.set_xlabel('x (integer nm ticks)'); ax.set_ylabel('y (integer nm ticks)')
        ax.set_xlim(-5, 165); ax.set_ylim(-5, 205); ax.grid(alpha=0.15)
    axes[0].set_title('FIN / active / gate / body')
    axes[0].text(24, 46, 'N: 5 crossings', fontsize=9, bbox={'facecolor': 'white', 'alpha': .8, 'edgecolor': 'none'})
    axes[0].text(24, 144, 'P: 7 crossings', fontsize=9, bbox={'facecolor': 'white', 'alpha': .8, 'edgecolor': 'none'})
    axes[1].set_title('Routing / contacts / CUT')
    axes[2].set_xlim(126, 154); axes[2].set_ylim(14, 33)
    axes[2].set_title('CUT witness (zoom)')
    axes[2].text(128, 29, 'Same A label; separate components', fontsize=8)
    axes[2].text(136, 16, '2 nm gap', fontsize=8)
    fig.suptitle('INV_M1_SYNTH | expected specimen, no product run', fontsize=14)
    fig.text(.5, .02, '18 static FIN stripes / 12 qualified crossings / integer source ticks preserved', ha='center', fontsize=10)
    fig.tight_layout(rect=[0, .10, 1, .95])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=150, metadata={'Software': 'W003 fixture review helper'})
    plt.close(fig)


if __name__ == '__main__':
    main()
