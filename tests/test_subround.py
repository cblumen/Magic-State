"""
Noiseless sanity checks for the full_round() syndrome extraction circuit.

Uses AerSimulator (statevector method). 
"""
import pytest
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

from msi.circuits.subround import full_round, N_CBITS
from msi.layout.qubit_mapping import DATA_QUBITS

_sim = AerSimulator(method="statevector")


SHOTS = 1

def run_syndrome(prepend: QuantumCircuit | None = None) -> str:
    """Run full_round() and return the dominant syndrome bitstring."""
    qc = QuantumCircuit(25, N_CBITS)
    if prepend is not None:
        qc.compose(prepend, inplace=True)
    qc.compose(full_round(), inplace=True)

    counts = _sim.run(transpile(qc, _sim), shots=SHOTS).result().get_counts()
    return max(counts, key=counts.get)


def error_circuit(qubit: int, gate: str) -> QuantumCircuit:
    """Return a 25-qubit circuit that applies a single Pauli error."""
    qc = QuantumCircuit(25)
    getattr(qc, gate)(qubit)
    return qc


S0 = None


def get_baseline() -> str:
    global S0
    if S0 is None:
        S0 = run_syndrome()
    return S0


# ── Test 2: single-qubit X errors ────────────────────────────────────────────

@pytest.mark.parametrize("qubit", DATA_QUBITS)
def test_x_error_detected(qubit):
    s0 = get_baseline()
    si = run_syndrome(error_circuit(qubit, "x"))
    assert si != s0, f"X error on q{qubit} was not detected (syndrome unchanged)"


# ── Test 3: single-qubit Z errors ────────────────────────────────────────────

@pytest.mark.parametrize("qubit", DATA_QUBITS)
def test_z_error_detected(qubit):
    s0 = get_baseline()
    si = run_syndrome(error_circuit(qubit, "z"))
    assert si != s0, f"Z error on q{qubit} was not detected (syndrome unchanged)"


# ── Test 4: distinct errors produce distinct syndromes ───────────────────────

def test_x_errors_unique():
    syndromes = {q: run_syndrome(error_circuit(q, "x")) for q in DATA_QUBITS}
    values = list(syndromes.values())
    assert len(values) == len(set(values)), (
        "Two different X errors produced the same syndrome — "
        f"collisions: {[q for q in DATA_QUBITS if values.count(syndromes[q]) > 1]}"
    )


def test_z_errors_unique():
    syndromes = {q: run_syndrome(error_circuit(q, "z")) for q in DATA_QUBITS}
    values = list(syndromes.values())
    assert len(values) == len(set(values)), (
        "Two different Z errors produced the same syndrome — "
        f"collisions: {[q for q in DATA_QUBITS if values.count(syndromes[q]) > 1]}"
    )
