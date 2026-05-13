"""
Parse results/injection_grid.json and display a fidelity heatmap with statistics.
Also plots density matrices for H (and T as placeholder) magic states.

Usage:
    python src/msi/analysis/show_grid.py [path/to/injection_grid.json]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np

_ROOT = Path(__file__).parents[3]
_DEFAULT_RESULTS = _ROOT / "results" / "injection_grid.json"
_FIGURES = _ROOT / "figures"

# Magic state angles
H_THETA, H_PHI = np.pi / 4, 0.0
T_THETA, T_PHI = np.arccos(1 / np.sqrt(3)), np.pi / 4


def load(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def _lookup_exact(data: dict, theta: float, phi: float) -> dict | None:
    key = f"({theta:.6f}, {phi:.6f})"
    return data.get(key)


def _rho_from_bloch(x: float, y: float, z: float) -> np.ndarray:
    X = np.array([[0, 1], [1, 0]], dtype=complex)
    Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
    Z = np.array([[1, 0], [0, -1]], dtype=complex)
    return (np.eye(2, dtype=complex) + x * X + y * Y + z * Z) / 2


def _ideal_rho(theta: float, phi: float) -> np.ndarray:
    psi = np.array([np.cos(theta / 2), np.exp(1j * phi) * np.sin(theta / 2)], dtype=complex)
    return np.outer(psi, psi.conj())


_CARPET = 0.012  # minimum bar height so zero entries render as a flat carpet


def _draw_bar(ax, i: int, j: int, val: float, color: str, alpha: float, w: float = 0.45):
    dz = max(abs(float(val)), _CARPET)
    z0 = min(0.0, float(val))
    ax.bar3d(j - w / 2, i - w / 2, z0, w, w, dz,
             color=color, alpha=alpha, edgecolor="none", shade=True)


def _draw_ideal(ax, i: int, j: int, val: float, color: str, w: float = 0.50):
    dz = max(abs(float(val)), _CARPET)
    z0 = min(0.0, float(val))
    ax.bar3d(j - w / 2, i - w / 2, z0, w, w, dz,
             color=color, alpha=0.2, edgecolor=color, linewidth=1.2, shade=False)


def _setup_ax(ax):
    ax.set_xticks([0, 1]); ax.set_xticklabels([r"$|0\rangle_L$", r"$|1\rangle_L$"], fontsize=8)
    ax.set_yticks([0, 1]); ax.set_yticklabels([r"$|0\rangle_L$", r"$|1\rangle_L$"], fontsize=8)
    ax.set_zlim(-1, 1)
    ax.set_zlabel("Value", fontsize=7, labelpad=1)
    ax.tick_params(axis="z", labelsize=7)
    ax.view_init(elev=20, azim=-35)
    xx, yy = np.meshgrid([-0.5, 1.5], [-0.5, 1.5])
    ax.plot_surface(xx, yy, np.zeros_like(xx), alpha=0.10, color="grey")


def plot_density_matrix_panel(ax, rho_exp, rho_ideal, part_fn,
                               exp_color, ideal_color, part_label):
    for i in range(2):
        for j in range(2):
            _draw_ideal(ax, i, j, part_fn(rho_ideal[i, j]), ideal_color)
            _draw_bar(ax, i, j, part_fn(rho_exp[i, j]),   exp_color, alpha=0.85)
    _setup_ax(ax)
    ax.legend(handles=[
        mpatches.Patch(facecolor=exp_color,   alpha=0.85, label=f"{part_label}(ρ_exp)"),
        mpatches.Patch(facecolor=ideal_color, alpha=0.3,  label=f"{part_label}(ρ_ideal)"),
    ], loc="upper left", fontsize=7, framealpha=0.6)


def plot_density_matrices(data: dict, figures_dir: Path) -> None:
    entry_h = _lookup_exact(data, H_THETA, H_PHI)
    if entry_h is None:
        print(f"Warning: H state (θ={H_THETA:.4f}, φ={H_PHI:.4f}) not found in results — skipping density matrix plot")
        return

    rho_h_exp   = _rho_from_bloch(entry_h["X_L"], entry_h["Y_L"], entry_h["Z_L"])
    rho_h_ideal = _ideal_rho(H_THETA, H_PHI)

    # T: load from dedicated T_injection.json if available, else placeholder
    t_path = figures_dir.parent / "results" / "T_injection.json"
    entry_t = None
    if t_path.exists():
        t_data = load(t_path)
        entry_t = next(iter(t_data.values()))
        print(f"T state loaded from {t_path}")
    else:
        print(f"T state not yet run — showing ideal only (run script 02 with T angles to populate)")

    rho_t_exp   = (_rho_from_bloch(entry_t["X_L"], entry_t["Y_L"], entry_t["Z_L"])
                   if entry_t else np.zeros((2, 2), dtype=complex))
    rho_t_ideal = _ideal_rho(T_THETA, T_PHI)

    fig = plt.figure(figsize=(11, 9), facecolor="white")

    t_has_data = entry_t is not None
    t_title = r"$|T_L\rangle$" if t_has_data else r"$|T_L\rangle$  (no data)"

    specs = [
        (0, rho_h_exp, rho_h_ideal, r"$|H_L\rangle$"),
        (1, rho_t_exp, rho_t_ideal, t_title),
    ]

    for col, rho_exp, rho_ideal, col_title in specs:
        for row, (part_fn, exp_color, ideal_color, label) in enumerate([
            (np.real, "#3B6EC5", "#27AE60", "Re"),
            (np.imag, "#C0392B", "#8E44AD", "Im"),
        ]):
            ax = fig.add_subplot(2, 2, row * 2 + col + 1, projection="3d")
            plot_density_matrix_panel(ax, rho_exp, rho_ideal, part_fn,
                                      exp_color, ideal_color, label)
            if row == 0:
                ax.set_title(col_title, fontsize=13, fontweight="bold", pad=6)
            if col == 1 and not t_has_data:
                ax.text2D(0.5, 0.5, "no data", transform=ax.transAxes,
                          ha="center", va="center", fontsize=12, color="grey", alpha=0.7)

    fig.suptitle("Density matrices of logical magic states", fontsize=13, fontweight="bold")
    fig.tight_layout()
    figures_dir.mkdir(exist_ok=True)
    out = figures_dir / "density_matrices.png"
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved → {out}")


def main(results_path: Path = _DEFAULT_RESULTS) -> None:
    data = load(results_path)

    thetas = sorted(set(v["theta"] for v in data.values()))
    phis   = sorted(set(v["phi"]   for v in data.values()))

    fid_grid = np.zeros((len(thetas), len(phis)))
    x_accs, y_accs, z_accs, fids = [], [], [], []

    for i, theta in enumerate(thetas):
        for j, phi in enumerate(phis):
            key = f"({theta:.6f}, {phi:.6f})"
            v = data[key]
            fid_grid[i, j] = v["fidelity"]
            fids.append(v["fidelity"])
            x_accs.append(v["X_acc"])
            y_accs.append(v["Y_acc"])
            z_accs.append(v["Z_acc"])

    d = (phis[1] - phis[0]) / 2
    extent = [phis[0] - d, phis[-1] + d, thetas[0] - d, thetas[-1] + d]
    pi_ticks  = [k * np.pi / 2 for k in range(5)]
    pi_labels = ["0", "π/2", "π", "3π/2", "2π"]

    fig, (ax, ax_tbl) = plt.subplots(
        2, 1, figsize=(7, 8), facecolor="white",
        gridspec_kw={"height_ratios": [5, 1]},
    )
    im = ax.imshow(fid_grid, cmap="RdBu_r", aspect="auto",
                   origin="lower", extent=extent,
                   vmin=min(fids), vmax=max(fids))
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(r"$\mathcal{F}(\rho_\mathrm{ideal},\,\rho_\mathrm{exp})$", fontsize=11)
    ax.set_xlabel("Azimuthal angle (φ)", fontsize=11)
    ax.set_ylabel("Polar angle (θ)", fontsize=11)
    ax.set_xticks(pi_ticks); ax.set_xticklabels(pi_labels)
    ax.set_yticks(pi_ticks); ax.set_yticklabels(pi_labels)
    ax.set_title("Magic State Injection Fidelity", fontsize=13, fontweight="bold")

    ax_tbl.axis("off")
    tbl = ax_tbl.table(
        cellText=[
            ["Avg X acceptance", f"{np.mean(x_accs):.3f}"],
            ["Avg Y acceptance", f"{np.mean(y_accs):.3f}"],
            ["Avg Z acceptance", f"{np.mean(z_accs):.3f}"],
            ["Avg fidelity",     f"{np.mean(fids):.4f}"],
        ],
        colWidths=[0.5, 0.3], loc="center", cellLoc="center",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10)
    for (r, c), cell in tbl.get_celld().items():
        cell.set_edgecolor("#cccccc")
        if c == 0:
            cell.set_facecolor("#f0f0f0")

    fig.tight_layout()
    _FIGURES.mkdir(exist_ok=True)
    out = _FIGURES / "injection_grid.png"
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved → {out}")
    print(f"\nAvg acceptance:  X={np.mean(x_accs):.3f}  Y={np.mean(y_accs):.3f}  Z={np.mean(z_accs):.3f}")
    print(f"Avg fidelity:    {np.mean(fids):.4f}")

    plot_density_matrices(data, _FIGURES)


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else _DEFAULT_RESULTS
    main(path)
