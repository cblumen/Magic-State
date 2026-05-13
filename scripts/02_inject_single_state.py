"""
Script 02: run the full single state injection circuit, error correct, and
perform tomography with SHOTS shots.

Backend selection (set IBM_BACKEND to switch):
    local      — AerSimulator statevector, no API key needed (default)
    fake_fez   — FakeFezV2 noise model, no API key needed
    ibm_fez    — real ibm_fez hardware, requires IBM_QUANTUM_TOKEN env var
"""

import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from qiskit import transpile
from qiskit.visualization import plot_bloch_vector

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from msi.circuits.injection import build_msi_circuit
from msi.analysis.post_selection import post_select, acceptance_rate
from msi.analysis.tomography import bloch_vector, density_matrix
from msi.analysis.fidelity import state_fidelity
from msi.layout.qubit_mapping import FEZ_INITIAL_LAYOUT

SHOTS = int(os.environ.get("SHOTS", 1000))
IBM_BACKEND = os.environ.get("IBM_BACKEND", "local")
RESULTS = Path(__file__).parents[1] / "results_T"



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
        service = QiskitRuntimeService(channel="ibm_quantum_platform", token=token)
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


def ideal_bloch(theta: float, phi: float) -> list[float]:
    return [
        float(np.sin(theta) * np.cos(phi)),
        float(np.sin(theta) * np.sin(phi)),
        float(np.cos(theta)),
    ]


def save_bloch_plot(x: float, y: float, z: float, theta: float, phi: float) -> None:
    figures = Path(__file__).parents[1] / "figures"
    figures.mkdir(exist_ok=True)
    fig = plot_bloch_vector([x, y, z], title="Injected vs Ideal")
    ax = fig.axes[0]
    ix, iy, iz = ideal_bloch(theta, phi)
    ax.quiver(0, 0, 0, ix, iy, iz, color="red", linewidth=2, arrow_length_ratio=0.15)
    out = figures / "bloch.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Bloch plot saved → {out}")


def run_basis(backend, theta: float, phi: float, basis: str) -> tuple[dict[str, int], float]:
    qc = build_msi_circuit(theta, phi, basis)
    raw = run_circuit(qc, backend, SHOTS)
    accepted = post_select(raw)
    rate = acceptance_rate(raw)
    print(
        f"  {basis}: {sum(accepted.values())}/{sum(raw.values())} shots accepted "
        f"({rate:.1%})"
    )
    return accepted, rate


_T_THETA = float(np.arccos(1 / np.sqrt(3)))
_T_PHI   = float(np.pi / 4)
_T_TOL   = 1e-4


def _is_T_state(theta: float, phi: float) -> bool:
    return abs(theta - _T_THETA) < _T_TOL and abs(phi - _T_PHI) < _T_TOL


def main() -> int:
    import json
    theta = float(np.arccos(1 / np.sqrt(3)))  # T magic state polar angle
    phi   = float(np.pi / 4)                  # T magic state azimuthal angle

    print(f"Target state: U3({theta}, {phi}, 0)|0>")
    print(f"Shots: {SHOTS}  Backend: {IBM_BACKEND}\n")

    backend = get_backend()

    counts_x, acc_x = run_basis(backend, theta, phi, "X")
    counts_y, acc_y = run_basis(backend, theta, phi, "Y")
    counts_z, acc_z = run_basis(backend, theta, phi, "Z")

    x, y, z = bloch_vector(counts_x, counts_y, counts_z)
    print(f"\nBloch vector: <X_L>={x:.4f}  <Y_L>={y:.4f}  <Z_L>={z:.4f}")

    rho = density_matrix(counts_x, counts_y, counts_z)
    F = state_fidelity(rho, theta, phi)
    print(f"Fidelity: {F:.4f}")

    save_bloch_plot(x, y, z, theta, phi)

    results_dir = Path(__file__).parents[1] / "results"
    results_dir.mkdir(exist_ok=True)

    entry = {
        f"({theta:.6f}, {phi:.6f})": {
            "theta": theta, "phi": phi,
            "X_L": x, "Y_L": y, "Z_L": z,
            "fidelity": F,
            "X_acc": acc_x, "Y_acc": acc_y, "Z_acc": acc_z,
        }
    }

    out = results_dir / "single_injection.json"
    with open(out, "w") as f:
        json.dump(entry, f, indent=2)
    print(f"Results saved → {out}")

    if _is_T_state(theta, phi):
        out_t = results_dir / "T_injection.json"
        with open(out_t, "w") as f:
            json.dump(entry, f, indent=2)
        print(f"T state results saved → {out_t}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
