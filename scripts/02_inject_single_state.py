"""
Script 02: run the full single state injection circuit, error correct, and
perform tomography with SHOTS shots.

Backend selection (set IBM_BACKEND to switch):
    local      — AerSimulator statevector, no API key needed (default)
    fake_fez   — FakeFezV2 noise model, no API key needed
    ibm_fez    — real ibm_fez hardware, requires IBM_QUANTUM_TOKEN env var
"""

import os

from qiskit import transpile

from msi.circuits.injection import build_msi_circuit
from msi.analysis.post_selection import post_select, acceptance_rate
from msi.analysis.tomography import bloch_vector, density_matrix
from msi.analysis.fidelity import state_fidelity

SHOTS = 1
IBM_BACKEND = os.environ.get("IBM_BACKEND", "local")


def get_backend():
    if IBM_BACKEND == "local":
        from qiskit_aer import AerSimulator
        return AerSimulator(method="statevector")
    elif IBM_BACKEND == "fake_fez":
        from qiskit_ibm_runtime.fake_provider import FakeFezV2
        return FakeFezV2()
    elif IBM_BACKEND == "ibm_fez":
        from qiskit_ibm_runtime import QiskitRuntimeService
        token = os.environ.get("IBM_QUANTUM_TOKEN")
        if not token:
            raise RuntimeError("IBM_QUANTUM_TOKEN env var not set")
        service = QiskitRuntimeService(channel="ibm_quantum", token=token)
        return service.backend("ibm_fez")
    else:
        raise ValueError(f"Unknown IBM_BACKEND: {IBM_BACKEND!r}")


def run_basis(backend, theta: float, phi: float, basis: str) -> dict[str, int]:
    qc = build_msi_circuit(theta, phi, basis)
    job = backend.run(transpile(qc, backend), shots=SHOTS)
    raw = job.result().get_counts()
    accepted = post_select(raw)
    print(
        f"  {basis}: {sum(accepted.values())}/{sum(raw.values())} shots accepted "
        f"({acceptance_rate(raw):.1%})"
    )
    return accepted


def main() -> int:
    theta = 0.3
    phi = 1.2

    print(f"Target state: U3({theta}, {phi}, 0)|0>")
    print(f"Shots: {SHOTS}  Backend: {IBM_BACKEND}\n")

    backend = get_backend()

    counts_x = run_basis(backend, theta, phi, "X")
    counts_y = run_basis(backend, theta, phi, "Y")
    counts_z = run_basis(backend, theta, phi, "Z")

    x, y, z = bloch_vector(counts_x, counts_y, counts_z)
    print(f"\nBloch vector: <X_L>={x:.4f}  <Y_L>={y:.4f}  <Z_L>={z:.4f}")

    rho = density_matrix(counts_x, counts_y, counts_z)
    F = state_fidelity(rho, theta, phi)
    print(f"Fidelity: {F:.4f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
