"""
Post-selection for the MSI protocol.

A shot is accepted if, for every boundary stabilizer, the syndrome ancilla
readout matches the parity of the corresponding final data qubit measurements.
"""

# (syndrome_cbit, final_measurement_cbits)
BOUNDARY_CHECKS: list[tuple[int, tuple[int, ...]]] = [
    (0, (10,)),               # Z{0}       : cbit 0  vs qubit 0
    (1, (11,)),               # Z{2}       : cbit 1  vs qubit 2
    (2, (10, 11, 13, 14)),    # Z{0,2,7,8} : cbit 2  vs qubits {0,2,7,8}
    (3, (12, 15)),            # X{5,13}    : cbit 3  vs qubits {5,13}
    (8, (17, 20)),            # X{16,23}   : cbit 8  vs qubits {16,23}
    (9, (18, 19)),            # Z{20,22}   : cbit 9  vs qubits {20,22}
]


def _bit(bitstring: str, cbit: int) -> int:
    """Extract bit `cbit` from a Qiskit bitstring (cbit 0 is rightmost)."""
    return int(bitstring[-(cbit + 1)])


def passes(bitstring: str) -> bool:
    """Return True if this shot satisfies all post-selection criteria."""
    for syndrome_cbit, final_cbits in BOUNDARY_CHECKS:
        syndrome = _bit(bitstring, syndrome_cbit)
        if syndrome != 0:
            return False
        parity = 0
        for c in final_cbits:
            parity ^= _bit(bitstring, c)
        if parity != syndrome:
            return False
    return True


def post_select(counts: dict[str, int]) -> dict[str, int]:
    """Filter a counts dict to only accepted shots."""
    return {bs: c for bs, c in counts.items() if passes(bs)}


def acceptance_rate(counts: dict[str, int]) -> float:
    """Return the fraction of shots that pass post-selection."""
    total = sum(counts.values())
    accepted = sum(c for bs, c in counts.items() if passes(bs))
    return accepted / total if total > 0 else 0.0
