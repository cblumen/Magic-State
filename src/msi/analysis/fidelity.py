"""Fidelity of the reconstructed logical state against the ideal target."""

from __future__ import annotations

import numpy as np


def state_fidelity(rho: np.ndarray, theta: float, phi: float) -> float:
    """F = ⟨ψ_ideal|ρ|ψ_ideal⟩ where |ψ_ideal⟩ = U3(theta, phi, 0)|0⟩.

    Args:
        rho:   2×2 density matrix from tomography.density_matrix()
        theta: polar angle of the target state
        phi:   azimuthal angle of the target state

    Returns:
        Fidelity in [0, 1].
    """
    psi = np.array(
        [np.cos(theta / 2), np.exp(1j * phi) * np.sin(theta / 2)],
        dtype=complex,
    )
    return float(np.real(psi.conj() @ rho @ psi))
