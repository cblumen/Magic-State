"""
Logical-state tomography for the MSI protocol.

Each of the three circuits (X, Y, Z basis) measures the data qubits in a
rotated basis so that parity of specific cbits yields the expectation value of
the corresponding logical operator.

DBIT_MAPPING (from injection.py):
    qubit 0  → cbit 10      qubit 16 → cbit 17
    qubit 2  → cbit 11      qubit 20 → cbit 18
    qubit 5  → cbit 12      qubit 22 → cbit 19
    qubit 7  → cbit 13      qubit 23 → cbit 20
    qubit 8  → cbit 14
    qubit 13 → cbit 15
    qubit 14 → cbit 16

Logical operators and their measurement cbits:
    Z_L = Z5 Z13 Z20  → cbits (12, 15, 18)   [Z-basis circuit]
    X_L = X20 X22 X23 → cbits (18, 19, 20)   [X-basis circuit, H applied]
    Y_L = iX_L Z_L    → cbits (12, 15, 18, 19, 20)  [Y-basis circuit, S†H applied]
"""

from __future__ import annotations

import numpy as np

# cbits that contribute to each logical parity measurement
Z_L_CBITS: tuple[int, ...] = (12, 15, 18)        # Z5 Z13 Z20
X_L_CBITS: tuple[int, ...] = (18, 19, 20)        # X20 X22 X23
Y_L_CBITS: tuple[int, ...] = (12, 15, 18, 19, 20) # Y_L = X_L · Z_L


def _bit(bitstring: str, cbit: int) -> int:
    return int(bitstring[-(cbit + 1)])


def _parity(bitstring: str, cbits: tuple[int, ...]) -> int:
    """XOR of the specified cbits: 0 → +1 eigenvalue, 1 → −1 eigenvalue."""
    p = 0
    for c in cbits:
        p ^= _bit(bitstring, c)
    return p


def expectation_value(counts: dict[str, int], cbits: tuple[int, ...]) -> float:
    """Compute ⟨O⟩ = (N_+ - N_-) / N from counts, where O is measured via parity of cbits."""
    total = sum(counts.values())
    if total == 0:
        return 0.0
    signed = sum(
        count * (1 - 2 * _parity(bs, cbits))
        for bs, count in counts.items()
    )
    return signed / total


def bloch_vector(
    counts_x: dict[str, int],
    counts_y: dict[str, int],
    counts_z: dict[str, int],
) -> tuple[float, float, float]:
    """Return the logical Bloch vector (x, y, z) from post-selected counts.

    Args:
        counts_x: post-selected counts from the X-basis circuit
        counts_y: post-selected counts from the Y-basis circuit
        counts_z: post-selected counts from the Z-basis circuit

    Returns:
        (⟨X_L⟩, ⟨Y_L⟩, ⟨Z_L⟩)
    """
    x = expectation_value(counts_x, X_L_CBITS)
    y = expectation_value(counts_y, Y_L_CBITS)
    z = expectation_value(counts_z, Z_L_CBITS)
    return x, y, z


def density_matrix(
    counts_x: dict[str, int],
    counts_y: dict[str, int],
    counts_z: dict[str, int],
) -> np.ndarray:
    """Reconstruct the logical qubit density matrix from tomography counts.

    ρ = (I + x·X + y·Y + z·Z) / 2

    Returns:
        2×2 complex numpy array
    """
    x, y, z = bloch_vector(counts_x, counts_y, counts_z)
    I = np.eye(2, dtype=complex)
    X = np.array([[0, 1], [1, 0]], dtype=complex)
    Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
    Z = np.array([[1, 0], [0, -1]], dtype=complex)
    return (I + x * X + y * Y + z * Z) / 2
