"""
Visualize the d=3 rotated surface code layout on ibm_fez.

Produces a Fig. S2-style plot of the 25 physical qubits color-coded by role
(data / syndrome / bridge), with the heavy-hex connectivity drawn as edges.
The central |psi> qubit (14) and the two weight-1 "collapsed" data qubits
(13 and 23) are highlighted so they're easy to sanity-check by eye before
we build the circuit.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Circle

from .qubit_mapping import (
    CENTRAL_DATA_QUBIT,
    EDGES,
    QUBIT_COORDS,
    QUBIT_ROLE,
    QubitRole,
    WEIGHT_ONE_DATA_QUBITS,
)

# ------------------------------------------------------------------
# Palette
# ------------------------------------------------------------------
# Chosen to match the paper's Fig. 1b conventions:
#   green    = data
#   magenta  = syndrome
#   black    = bridge
_ROLE_FACE_COLOR: dict[QubitRole, str] = {
    QubitRole.DATA: "#4CAF50",      # green
    QubitRole.SYNDROME: "#E91E63",   # magenta/pink
    QubitRole.BRIDGE: "#333333",     # near-black
}
_ROLE_LABEL: dict[QubitRole, str] = {
    QubitRole.DATA: "Data",
    QubitRole.SYNDROME: "Syndrome",
    QubitRole.BRIDGE: "Bridge",
}


def plot_layout(
    ax: Optional[Axes] = None,
    *,
    highlight_central: bool = True,
    highlight_weight_one: bool = True,
    node_radius: float = 0.22,
    save_path: Optional[str | Path] = None,
) -> tuple[Figure, Axes]:
    """Draw the qubit role map.

    Parameters
    ----------
    ax
        Existing matplotlib Axes to draw on. If None, a new Figure+Axes is
        created at a sensible default size.
    highlight_central
        If True, draw a gold ring around qubit 14 (the |psi> injection target).
    highlight_weight_one
        If True, draw dashed blue rings around qubits 13 and 23 (the "extra"
        data qubits that get collapsed each round by weight-1 Z measurements).
    node_radius
        Radius of each qubit circle in data units. Increase for smaller
        figures or finer detail.
    save_path
        If given, save the figure there (parent directories are created as
        needed). The extension determines the format (.png, .pdf, .svg...).

    Returns
    -------
    (Figure, Axes)
        For further customization by the caller.
    """
    # 1. Set up the canvas. ----------------------------------------------
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 7))
    else:
        fig = ax.figure

    # 2. Draw the connectivity edges first (zorder=1) so they sit behind
    #    the qubit nodes.
    for u, v in EDGES:
        x0, y0 = QUBIT_COORDS[u]
        x1, y1 = QUBIT_COORDS[v]
        ax.plot(
            [x0, x1],
            [y0, y1],
            color="#BBBBBB",
            linewidth=2.0,
            zorder=1,
            solid_capstyle="round",
        )

    # 3. Draw each qubit as a filled circle colored by role, with the
    #    qubit index rendered inside it in white.
    for q, (x, y) in QUBIT_COORDS.items():
        role = QUBIT_ROLE[q]
        node = Circle(
            (x, y),
            radius=node_radius,
            facecolor=_ROLE_FACE_COLOR[role],
            edgecolor="black",
            linewidth=1.2,
            zorder=3,
        )
        ax.add_patch(node)
        ax.text(
            x, y, str(q),
            ha="center", va="center",
            color="white", fontsize=9, fontweight="bold",
            zorder=4,
        )

    # 4. Highlight the central |psi> target qubit with a gold ring.
    if highlight_central:
        cx, cy = QUBIT_COORDS[CENTRAL_DATA_QUBIT]
        ring = Circle(
            (cx, cy),
            radius=node_radius * 1.55,
            fill=False,
            edgecolor="#FFC107",     # amber/gold
            linewidth=2.5,
            zorder=2,
        )
        ax.add_patch(ring)

    # 5. Highlight the weight-1 collapsed data qubits with dashed blue rings.
    if highlight_weight_one:
        for q in WEIGHT_ONE_DATA_QUBITS:
            x, y = QUBIT_COORDS[q]
            ring = Circle(
                (x, y),
                radius=node_radius * 1.35,
                fill=False,
                edgecolor="#2196F3",  # blue
                linewidth=2.0,
                linestyle="--",
                zorder=2,
            )
            ax.add_patch(ring)

    # 6. Axes cosmetics: equal aspect ratio, sensible padding, no ticks/spines.
    ax.set_aspect("equal")
    xs = [p[0] for p in QUBIT_COORDS.values()]
    ys = [p[1] for p in QUBIT_COORDS.values()]
    pad = 0.7
    ax.set_xlim(min(xs) - pad, max(xs) + pad)
    ax.set_ylim(min(ys) - pad, max(ys) + pad)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    # 7. Legend, built by hand from proxy artists.
    legend_items: list[Line2D] = [
        Line2D(
            [0], [0],
            marker="o", linestyle="",
            markerfacecolor=_ROLE_FACE_COLOR[role],
            markeredgecolor="black",
            markersize=12,
            label=_ROLE_LABEL[role],
        )
        for role in (QubitRole.DATA, QubitRole.SYNDROME, QubitRole.BRIDGE)
    ]
    if highlight_central:
        legend_items.append(
            Line2D(
                [0], [0],
                marker="o", linestyle="",
                markerfacecolor="none",
                markeredgecolor="#FFC107",
                markeredgewidth=2.5,
                markersize=14,
                label=f"Central |ψ⟩ target (q{CENTRAL_DATA_QUBIT})",
            )
        )
    if highlight_weight_one:
        legend_items.append(
            Line2D(
                [0], [0],
                marker="o", linestyle="--",
                markerfacecolor="none",
                markeredgecolor="#2196F3",
                markeredgewidth=2.0,
                markersize=14,
                label="Weight-1 collapsed data",
            )
        )
    ax.legend(
        handles=legend_items,
        loc="upper left",
        bbox_to_anchor=(1.02, 1.0),
        frameon=False,
        fontsize=9,
    )

    ax.set_title(
        "Distance-3 rotated surface code on ibm_fez\n",
        fontsize=12,
    )

    fig.tight_layout()

    # 8. Persist to disk if requested.
    if save_path is not None:
        p = Path(save_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(p, dpi=150, bbox_inches="tight")
        print(f"[visualize] saved layout figure -> {p}")

    return fig, ax