"""
Interactive single-page HTML viewer built on Plotly.

Given several "views" (each a ``{layer: [bbox-dict, ...]}`` shape map —
typically original GDS, resized GDS, target GDS, device_info-derived,
net_shapes-derived — all in the same coordinate frame), this writes one
self-contained ``.html`` file with:

  - a buttons row to flip between views (axes stay pinned, so shapes
    register visually across views — the user can flick A vs B vs C
    without the camera moving),
  - one legend entry per layer (clicking toggles that layer across
    whatever view is currently shown — solves the "too many overlapping
    layers" readability problem),
  - pan / zoom / hover tooltips (layer, net, exact bbox).

``plotly`` is an optional dependency (the ``viz`` extra). The import is
performed inside the function so callers can catch ``ImportError`` and
fall back to the matplotlib outputs.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from visualization.render import (
    compute_view_window, draw_order_for, resolve_color,
)


def _rgba_css(rgba) -> str:
    r, g, b, a = rgba
    return f"rgba({int(r * 255)},{int(g * 255)},{int(b * 255)},{a})"


def write_interactive_html(views: dict, output_path: str, *,
                           view_window=None,
                           title: str = 'Layauto debug view',
                           include_plotlyjs='cdn') -> str:
    """Write a self-contained interactive HTML viewer.

    ``views`` maps a label (e.g. ``'original'``, ``'resized'``,
    ``'device_info'``) to a ``{layer: [bbox-dict, ...]}`` map (the same
    format ``render_layers`` consumes). All shape coordinates must be
    in the same units (nm in the MVP pipeline).

    Layer fill / outline colors come from ``resolve_color`` so they
    match the matplotlib plots. The legend is keyed by ``layer`` (one
    entry per layer name across all views, via ``legendgroup``), so
    clicking ``M1`` hides ``M1`` everywhere.

    A buttons row sets ``visible`` per-trace by ``view`` label, so
    pressing ``resized`` shows only that view's traces; axes are
    pinned to ``view_window`` (computed if not provided) with
    ``yaxis.scaleanchor='x'`` so aspect ratio is locked.

    ``include_plotlyjs='cdn'`` keeps the file small (a few KB plus
    your shape data); pass ``True`` for a fully offline HTML.
    """
    import plotly.graph_objects as go  # noqa: F401  — caller guards ImportError

    if view_window is None:
        view_window = compute_view_window(*views.values())
    x0, y0, x1, y1 = view_window

    fig = go.Figure()
    trace_view: list = []
    legend_seen: set = set()
    labels = list(views.keys())
    first = labels[0] if labels else ''

    for label in labels:
        sbl = views[label] or {}
        for layer in draw_order_for(sbl.keys()):
            slist = sbl.get(layer) or []
            if not slist:
                continue
            xs: list = []
            ys: list = []
            hover: list = []
            for s in slist:
                a, b, c, d = s['x1'], s['y1'], s['x2'], s['y2']
                xs += [a, c, c, a, a, None]
                ys += [b, b, d, d, b, None]
                txt = f"{label} / {layer}"
                if s.get('net'):
                    txt += f" / net={s['net']}"
                if s.get('desc'):
                    txt += f" / {s['desc']}"
                txt += f"<br>bbox=({a:.2f}, {b:.2f}) - ({c:.2f}, {d:.2f})"
                hover += [txt] * 5 + [None]
            rgba = resolve_color(layer)
            fill_css = _rgba_css(rgba)
            line_css = _rgba_css((rgba[0], rgba[1], rgba[2], 1.0))
            fig.add_trace(go.Scatter(
                x=xs, y=ys,
                mode='lines',
                fill='toself',
                line=dict(color=line_css, width=1),
                fillcolor=fill_css,
                name=layer,
                legendgroup=layer,
                showlegend=(layer not in legend_seen),
                visible=(label == first),
                text=hover,
                hoverinfo='text',
            ))
            legend_seen.add(layer)
            trace_view.append(label)

    buttons = [
        dict(
            label=lbl,
            method='update',
            args=[
                {'visible': [tv == lbl for tv in trace_view]},
                {'title': f'{title} - {lbl}'},
            ],
        )
        for lbl in labels
    ]

    fig.update_layout(
        title=f'{title} - {first}' if first else title,
        updatemenus=[dict(
            type='buttons',
            direction='right',
            x=0, y=1.12,
            xanchor='left', yanchor='top',
            buttons=buttons,
            showactive=True,
        )],
        xaxis=dict(range=[x0, x1], title='X (nm)', constrain='domain'),
        yaxis=dict(range=[y0, y1], title='Y (nm)',
                   scaleanchor='x', scaleratio=1),
        legend=dict(title='layers (click to toggle)'),
        width=1000, height=900,
        margin=dict(t=110, l=70, r=30, b=60),
    )

    fig.write_html(output_path,
                   include_plotlyjs=include_plotlyjs,
                   full_html=True)
    print(f"  Interactive HTML written: {output_path}")
    return output_path
