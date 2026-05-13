"""
Tomography across four injected gates: I, H, S, T.

Outputs:
  figures/gate_bloch_grid.png   — 2x2 Bloch spheres, measured vs ideal per gate
  figures/gate_bloch_all.png    — all 4 gates on one Bloch sphere
  figures/gate_fidelity.png     — fidelity bar chart
"""

import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from qiskit import transpile

from msi.circuits.injection import build_msi_circuit
from msi.analysis.post_selection import post_select, acceptance_rate
from msi.analysis.tomography import bloch_vector, density_matrix
from msi.analysis.fidelity import state_fidelity
from msi.layout.qubit_mapping import FEZ_INITIAL_LAYOUT

SHOTS = int(os.environ.get("SHOTS", 10))
IBM_BACKEND = os.environ.get("IBM_BACKEND", "local")
FIGURES = Path(__file__).parents[1] / "figures"
FIGURES.mkdir(exist_ok=True)

GATES: dict[str, tuple[float, float]] = {
    "I": (0,          0),
    "H": (np.pi / 2,  0),
    "S": (np.pi / 2,  np.pi / 2),
    "T": (np.pi / 2,  np.pi / 4),
}

GATE_COLORS = {"I": "#4A90D9", "H": "#E67E22", "S": "#27AE60", "T": "#8E44AD"}


def get_backend():
    if IBM_BACKEND == "local":
        from qiskit_aer import AerSimulator
        return AerSimulator(method="statevector")
    elif IBM_BACKEND == "fake_fez":
        from qiskit_ibm_runtime.fake_provider import FakeFez
        return FakeFez()
    elif IBM_BACKEND == "ibm_fez":
        from qiskit_ibm_runtime import QiskitRuntimeService
        token = os.environ.get("IBM_QUANTUM_TOKEN")
        if not token:
            raise RuntimeError("IBM_QUANTUM_TOKEN env var not set")
        service = QiskitRuntimeService(channel="ibm_quantum", token=token)
        return service.backend("ibm_fez")
    else:
        raise ValueError(f"Unknown IBM_BACKEND: {IBM_BACKEND!r}")


def _layout():
    return FEZ_INITIAL_LAYOUT if IBM_BACKEND in ("fake_fez", "ibm_fez") else None


def run_circuit(qc, backend, shots: int) -> dict[str, int]:
    layout = _layout()
    opt = 1 if IBM_BACKEND == "ibm_fez" else 0
    tqc = transpile(qc, backend, initial_layout=layout, optimization_level=opt)
    if IBM_BACKEND == "ibm_fez":
        from qiskit_ibm_runtime import SamplerV2 as Sampler
        result = Sampler(backend).run([tqc], shots=shots).result()
        return result[0].data.c.get_counts()
    return backend.run(tqc, shots=shots).result().get_counts()


def ideal_bloch(theta: float, phi: float) -> np.ndarray:
    return np.array([
        np.sin(theta) * np.cos(phi),
        np.sin(theta) * np.sin(phi),
        np.cos(theta),
    ])


# ── Bloch sphere drawing ───────────────────────────────────────────────────────

def _sphere_surface(ax, alpha=0.04):
    u = np.linspace(0, 2 * np.pi, 60)
    v = np.linspace(0, np.pi, 60)
    ax.plot_surface(
        np.outer(np.cos(u), np.sin(v)),
        np.outer(np.sin(u), np.sin(v)),
        np.outer(np.ones_like(u), np.cos(v)),
        alpha=alpha, color="#B0C8E8", linewidth=0, antialiased=True,
    )


def _sphere_wireframe(ax):
    t = np.linspace(0, 2 * np.pi, 120)
    kw = dict(color="gray", alpha=0.25, linewidth=0.6)
    ax.plot(np.cos(t), np.sin(t), 0, **kw)
    ax.plot(np.cos(t), np.zeros_like(t), np.sin(t), **kw)
    ax.plot(np.zeros_like(t), np.cos(t), np.sin(t), **kw)


def _sphere_axes(ax):
    kw = dict(color="#888888", linewidth=0.8, alpha=0.6, arrow_length_ratio=0.08)
    for d in [(1,0,0),(0,1,0),(0,0,1)]:
        ax.quiver(-d[0],-d[1],-d[2], 2*d[0],2*d[1],2*d[2], **kw)
    offset = 1.35
    ax.text( offset, 0, 0, "X", ha="center", va="center", fontsize=9, color="#555")
    ax.text(0,  offset, 0, "Y", ha="center", va="center", fontsize=9, color="#555")
    ax.text(0, 0,  offset, "|0⟩", ha="center", va="bottom", fontsize=9, color="#555")
    ax.text(0, 0, -offset, "|1⟩", ha="center", va="top",    fontsize=9, color="#555")


def _add_vector(ax, v, color, label=None, linewidth=2.5):
    ax.quiver(0, 0, 0, v[0], v[1], v[2],
              color=color, linewidth=linewidth,
              arrow_length_ratio=0.18, label=label)


def _format_ax(ax, title=""):
    ax.set_xlim([-1.3, 1.3]); ax.set_ylim([-1.3, 1.3]); ax.set_zlim([-1.3, 1.3])
    ax.set_axis_off()
    ax.set_box_aspect([1, 1, 1])
    if title:
        ax.set_title(title, fontsize=13, fontweight="bold", pad=4)


def draw_single_bloch(ax, measured, ideal, gate_name):
    _sphere_surface(ax)
    _sphere_wireframe(ax)
    _sphere_axes(ax)
    _add_vector(ax, ideal,    "#E74C3C", label="Ideal")
    _add_vector(ax, measured, GATE_COLORS[gate_name], label="Measured")
    _format_ax(ax, title=f"Gate: {gate_name}")
    ax.legend(loc="upper left", fontsize=7, framealpha=0.6)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    backend = get_backend()

    measured_vecs = {}
    fidelities = {}

    print(f"Running tomography  (SHOTS={SHOTS}  backend={IBM_BACKEND})\n")
    for name, (theta, phi) in GATES.items():
        results = {}
        for basis in ("X", "Y", "Z"):
            qc = build_msi_circuit(theta, phi, basis)
            raw = run_circuit(qc, backend, SHOTS)
            results[basis] = post_select(raw)
        x, y, z = bloch_vector(results["X"], results["Y"], results["Z"])
        measured_vecs[name] = np.array([x, y, z])
        rho = density_matrix(results["X"], results["Y"], results["Z"])
        fidelities[name] = state_fidelity(rho, theta, phi)
        print(f"  {name}:  Bloch=({x:+.3f}, {y:+.3f}, {z:+.3f})  F={fidelities[name]:.4f}")

    # ── Plot 1: 2x2 Bloch grid ────────────────────────────────────────────────
    fig = plt.figure(figsize=(10, 10), facecolor="white")
    for idx, (name, (theta, phi)) in enumerate(GATES.items()):
        ax = fig.add_subplot(2, 2, idx + 1, projection="3d")
        ideal = ideal_bloch(theta, phi)
        draw_single_bloch(ax, measured_vecs[name], ideal, name)
    fig.suptitle("Magic State Injection Tomography", fontsize=15, fontweight="bold", y=1.01)
    fig.tight_layout()
    out = FIGURES / "gate_bloch_grid.png"
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"\nSaved → {out}")

    # ── Plot 2: all on one sphere ─────────────────────────────────────────────
    fig = plt.figure(figsize=(7, 7), facecolor="white")
    ax = fig.add_subplot(111, projection="3d")
    _sphere_surface(ax)
    _sphere_wireframe(ax)
    _sphere_axes(ax)
    for name, (theta, phi) in GATES.items():
        ideal = ideal_bloch(theta, phi)
        _add_vector(ax, ideal,            "#E74C3C",          linewidth=1.5)
        _add_vector(ax, measured_vecs[name], GATE_COLORS[name], label=name, linewidth=2.5)
    _format_ax(ax, title="All Gates — Measured vs Ideal")
    ax.legend(loc="upper left", fontsize=9, framealpha=0.7, title="Injected gate")
    out = FIGURES / "gate_bloch_all.png"
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved → {out}")

    # ── Plot 3: fidelity bar chart ────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(6, 4), facecolor="white")
    names = list(fidelities.keys())
    vals  = [fidelities[n] for n in names]
    bars  = ax.bar(names, vals,
                   color=[GATE_COLORS[n] for n in names],
                   edgecolor="white", linewidth=1.5, width=0.5)
    ax.axhline(1.0, color="gray", linestyle="--", linewidth=1, alpha=0.7, label="Ideal F=1")
    ax.set_ylim(0, max(1.2, max(vals) * 1.1))
    ax.set_ylabel("Fidelity", fontsize=12)
    ax.set_title("Injection Fidelity by Gate", fontsize=13, fontweight="bold")
    for bar, val in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                f"{val:.3f}", ha="center", va="bottom", fontsize=11)
    ax.legend(fontsize=10)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    out = FIGURES / "gate_fidelity.png"
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved → {out}")


if __name__ == "__main__":
    main()
