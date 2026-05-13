"""
Script 03: run MSI tomography over a 9×9 grid of (theta, phi) angles.

Both angles step from 0 to 2π in increments of π/4 (9 values each = 81 states).
Results are written to results/injection_grid.json.

Backend selection via IBM_BACKEND env var:
    local      — AerSimulator statevector (default)
    fake_fez   — FakeFez noise model
    ibm_fez    — real hardware; all circuits batched into one SamplerV2 job
"""

import json
import os
import sys
from pathlib import Path

import numpy as np
from qiskit import transpile

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from msi.circuits.injection import build_msi_circuit
from msi.analysis.post_selection import post_select, acceptance_rate
from msi.analysis.tomography import bloch_vector, density_matrix
from msi.analysis.fidelity import state_fidelity
from msi.layout.qubit_mapping import FEZ_INITIAL_LAYOUT

SHOTS = int(os.environ.get("SHOTS", 1000))
IBM_BACKEND = os.environ.get("IBM_BACKEND", "local")
RESULTS = Path(__file__).parents[1] / "results"

ANGLES = np.arange(0, 2 * np.pi + 1e-9, np.pi / 4)  # 9 values: 0 … 2π


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


def run_circuit_local(qc, backend, shots: int) -> dict[str, int]:
    layout = _layout()
    opt = 0
    tqc = transpile(qc, backend, initial_layout=layout, optimization_level=opt)
    return backend.run(tqc, shots=shots).result().get_counts()


def run_grid_batched(backend) -> dict[tuple, dict[str, dict]]:
    """Build all 9×9×3=243 circuits and submit as one SamplerV2 job."""
    from qiskit_ibm_runtime import SamplerV2 as Sampler

    index = []
    pubs = []
    for theta in ANGLES:
        for phi in ANGLES:
            for basis in ("X", "Y", "Z"):
                qc = build_msi_circuit(theta, phi, basis)
                tqc = transpile(qc, backend, initial_layout=FEZ_INITIAL_LAYOUT,
                                optimization_level=1)
                index.append((float(theta), float(phi), basis))
                pubs.append(tqc)

    print(f"Submitting {len(pubs)} circuits as one batch job (SHOTS={SHOTS})...")
    job = Sampler(backend).run(pubs, shots=SHOTS)
    print(f"Job ID: {job.job_id()}")
    print("Waiting for results (check IBM Quantum dashboard for queue status)...")
    result = job.result()

    raw: dict[tuple, dict[str, dict]] = {}
    for i, (theta, phi, basis) in enumerate(index):
        raw.setdefault((theta, phi), {})[basis] = result[i].data.c.get_counts()
    return raw


def run_grid_sequential(backend) -> dict[tuple, dict[str, dict]]:
    """Run circuits sequentially (local / fake_fez)."""
    raw: dict[tuple, dict[str, dict]] = {}
    total = len(ANGLES) ** 2
    for n, (theta, phi) in enumerate((float(t), float(p))
                                     for t in ANGLES for p in ANGLES):
        print(f"  [{n+1}/{total}]  theta={theta:.4f}  phi={phi:.4f}")
        raw[(theta, phi)] = {}
        for basis in ("X", "Y", "Z"):
            qc = build_msi_circuit(theta, phi, basis)
            raw[(theta, phi)][basis] = run_circuit_local(qc, backend, SHOTS)
    return raw


def process(raw: dict[tuple, dict[str, dict]]) -> dict[str, dict]:
    output: dict[str, dict] = {}
    for (theta, phi), basis_counts in raw.items():
        acc_x = post_select(basis_counts["X"])
        acc_y = post_select(basis_counts["Y"])
        acc_z = post_select(basis_counts["Z"])
        x, y, z = bloch_vector(acc_x, acc_y, acc_z)
        rho = density_matrix(acc_x, acc_y, acc_z)
        fid = state_fidelity(rho, theta, phi)
        key = f"({theta:.6f}, {phi:.6f})"
        output[key] = {
            "theta": theta, "phi": phi,
            "X_L": x, "Y_L": y, "Z_L": z,
            "fidelity": fid,
            "X_acc": acceptance_rate(basis_counts["X"]),
            "Y_acc": acceptance_rate(basis_counts["Y"]),
            "Z_acc": acceptance_rate(basis_counts["Z"]),
        }
    return output


def main():
    RESULTS.mkdir(exist_ok=True)
    backend = get_backend()
    n = len(ANGLES)
    print(f"Injection grid  {n}×{n}={n**2} states  SHOTS={SHOTS}  backend={IBM_BACKEND}\n")

    if IBM_BACKEND == "ibm_fez":
        raw = run_grid_batched(backend)
    else:
        raw = run_grid_sequential(backend)

    output = process(raw)

    out_path = RESULTS / "injection_grid.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved → {out_path}")

    fids  = [v["fidelity"] for v in output.values()]
    x_acc = [v["X_acc"]   for v in output.values()]
    y_acc = [v["Y_acc"]   for v in output.values()]
    z_acc = [v["Z_acc"]   for v in output.values()]
    print(f"Average fidelity:    {np.mean(fids):.4f}")
    print(f"Average acceptance:  X={np.mean(x_acc):.3f}  Y={np.mean(y_acc):.3f}  Z={np.mean(z_acc):.3f}")


if __name__ == "__main__":
    main()
