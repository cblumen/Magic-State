"""
Full Magic State Injection (MSI) circuit.

Follows Kim, Sevior & Usman (arXiv:2412.01446), Section III.

Protocol steps:
    1. Initialization  — prepare data qubits; apply U3(theta, phi, 0) to
                         the central qubit (q14) to inject the target state
    2. Syndrome rounds — two sub-rounds of stabilizer measurement
    3. Logical measurement — measure X_L, Y_L, Z_L for tomography

Modules to fill in:
    initialization.py  — step 1
    subround.py        — step 2 (full_round already built)
    boundary.py        — boundary stabilizers (weight-1 and weight-2)
    logical_meas.py    — step 3
"""
from qiskit import QuantumCircuit

from msi.circuits.subround import full_round, N_CBITS #10

DBIT_MAPPING: dict[int, int] = {  # maps data qubits to classical bits for final measurement
    0: 10,
    2: 11,
    5: 12,
    7: 13,
    8: 14,
    13: 15,
    14: 16,
    16: 17,
    20: 18,
    22: 19,
    23: 20,
}

INIT_ZERO_STATES = {0,2,7,8,20,22}
INIT_PLUS_STATES = {5,13,16,23}
MAGIC_STATE_QUBIT = 14

def build_msi_circuit(theta: float, phi: float, logical_basis: str) -> QuantumCircuit:
    """Return the full MSI circuit for a target state U3(theta, phi, 0)|0>.

    Args:
        theta: polar angle of the target state on the Bloch sphere
        phi:   azimuthal angle of the target state on the Bloch sphere
        logical_basis: the logical measurement basis (X, Y, or Z)

    Returns:
        A 25-qubit QuantumCircuit ready for execution.
    """


    qc = QuantumCircuit(25, N_CBITS+11)  # +11 for final data qubit measurements

    # Step 1: initialization
    # TODO: call initialization circuit here
    # e.g. qc.compose(build_initialization(theta, phi), inplace=True)
    for q in INIT_ZERO_STATES:
        qc.reset(q)
    for q in INIT_PLUS_STATES:
        qc.reset(q)
        qc.h(q)
    qc.u(theta, phi, 0, MAGIC_STATE_QUBIT)
    # Step 2: syndrome extraction
    qc.compose(full_round(), inplace=True)



    # Step 3: logical measurement
    qc.compose(build_logical_measurement_circuit(logical_basis), inplace=True)

    return qc


def build_logical_measurement_circuit(logical_basis: str) -> QuantumCircuit:
    if logical_basis not in ("X", "Y", "Z"):
        raise ValueError(f"Invalid logical basis: {logical_basis}. Must be 'X', 'Y', or 'Z'.")

    qc = QuantumCircuit(25, N_CBITS+11)

    # Central qubit measured in the logical basis
    if logical_basis == "X":
        qc.h(MAGIC_STATE_QUBIT)
    elif logical_basis == "Y":
        qc.sdg(MAGIC_STATE_QUBIT)
        qc.h(MAGIC_STATE_QUBIT)
    qc.measure(MAGIC_STATE_QUBIT, DBIT_MAPPING[MAGIC_STATE_QUBIT])

    # All other data qubits measured in their initialization basis
    for q in INIT_ZERO_STATES:
        qc.measure(q, DBIT_MAPPING[q])
    for q in INIT_PLUS_STATES:
        qc.h(q)
        qc.measure(q, DBIT_MAPPING[q])

    return qc
