"""
Post-selection for the MSI protocol.

A shot is accepted if all boundary stabilizer conditions are satisfied:

  1. Syndrome cbits from subround extraction (cbits 0,1,3,8,9) are all 0.
     These correspond to the boundary stabilizers:
       cbit 0: Z on qubit 0  (weight-1)
       cbit 1: Z on qubit 2  (weight-1)
       cbit 3: X on qubits {5, 13}  (weight-2)
       cbit 8: X on qubits {16, 23} (weight-2)
       cbit 9: Z on qubits {20, 22} (weight-2)

  2. Final Z measurements of the weight-1 data qubits (cbits 10, 11) are 0.
     These qubits (0 and 2) are reset during syndrome extraction, so this
     should always hold; included as an explicit sanity check.

  3. Parity of final measurements for each boundary stabilizer group is 0:
       cbits (12, 15) → X stabilizer on qubits {5, 13}
       cbits (18, 19) → Z stabilizer on qubits {20, 22}
       cbits (17, 20) → X stabilizer on qubits {16, 23}

     Note: the X stabilizer parity checks (12,15) and (17,20) are only valid
     when the corresponding qubits are measured in the X basis (H before
     measure). This holds for the X_L circuit. For Z_L and Y_L circuits,
     rely on syndrome cbits 3 and 8 respectively for those stabilizers.
"""

# Syndrome cbits that must be 0 (boundary stabilizers only).
BOUNDARY_SYNDROME_CBITS: list[int] = [0, 1, 3, 8, 9]

# Final measurement cbits that must be 0 individually (weight-1 data qubits).
WEIGHT_ONE_FINAL_CBITS: list[int] = [10, 11]

# Pairs of final measurement cbits whose XOR must be 0 (boundary stabilizer parities).
BOUNDARY_PARITY_PAIRS: list[tuple[int, int]] = [
    (12, 15),   # X stabilizer: qubits 5, 13
    (18, 19),   # Z stabilizer: qubits 20, 22
    (17, 20),   # X stabilizer: qubits 16, 23
]


def _bit(bitstring: str, cbit: int) -> int:
    """Extract bit `cbit` from a Qiskit bitstring (cbit 0 is rightmost)."""
    return int(bitstring[-(cbit + 1)])


def passes(bitstring: str) -> bool:
    """Return True if this shot satisfies all post-selection criteria."""
    for cbit in BOUNDARY_SYNDROME_CBITS:
        if _bit(bitstring, cbit) != 0:
            return False
    for cbit in WEIGHT_ONE_FINAL_CBITS:
        if _bit(bitstring, cbit) != 0:
            return False
    for c0, c1 in BOUNDARY_PARITY_PAIRS:
        if _bit(bitstring, c0) ^ _bit(bitstring, c1) != 0:
            return False
    return True


def post_select(counts: dict[str, int]) -> dict[str, int]:
    """Filter a counts dict to only accepted shots.

    Args:
        counts: raw counts dict from result.get_counts()

    Returns:
        Filtered counts dict. May be empty if all shots are discarded.
    """
    return {bitstring: count for bitstring, count in counts.items() if passes(bitstring)}


def acceptance_rate(counts: dict[str, int]) -> float:
    """Return the fraction of shots that pass post-selection."""
    total = sum(counts.values())
    accepted = sum(count for bs, count in counts.items() if passes(bs))
    return accepted / total if total > 0 else 0.0
