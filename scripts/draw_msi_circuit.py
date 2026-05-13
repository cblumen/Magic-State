"""
Draw the full MSI circuit with collapsed subrounds and color-coded sections.
Saves to figures/msi_circuit.png.
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from qiskit import QuantumCircuit
from qiskit.circuit import QuantumRegister, ClassicalRegister

from msi.circuits.subround import N_CBITS, subround_1, subround_2
from msi.circuits.injection import (
    INIT_ZERO_STATES, INIT_PLUS_STATES, MAGIC_STATE_QUBIT,
)
from msi.layout.qubit_mapping import DATA_QUBITS, SYNDROME_QUBITS, BRIDGE_QUBITS

COLORS = {
    "Subround 1": ("#E67E22", "#FFFFFF"),
    "Subround 2": ("#27AE60", "#FFFFFF"),
}

# --- qubit labels by role ---
def _label(q: int) -> str:
    if q in DATA_QUBITS:
        return f"d{q}*" if q == MAGIC_STATE_QUBIT else f"d{q}"
    if q in SYNDROME_QUBITS:
        return f"s{q}"
    return f"b{q}"

QUBIT_LABELS = [_label(i) for i in range(25)]


def build(logical_basis: str = "Z") -> QuantumCircuit:
    regs = [QuantumRegister(1, QUBIT_LABELS[i]) for i in range(25)]
    c = ClassicalRegister(1, "c")
    qc = QuantumCircuit(*regs, c)

    def q(i):
        return regs[i][0]

    # --- Init ---
    for i in INIT_ZERO_STATES:
        qc.reset(q(i))
    for i in INIT_PLUS_STATES:
        qc.reset(q(i))
        qc.h(q(i))
    qc.reset(q(MAGIC_STATE_QUBIT))
    qc.u(0, 0, 0, q(MAGIC_STATE_QUBIT))

    # --- Subrounds (collapsed) ---
    n_sr = N_CBITS - 6
    sr_c = ClassicalRegister(n_sr, "sr")
    qc.add_register(sr_c)
    for name, fn in [("Subround 1", subround_1), ("Subround 2", subround_2)]:
        full = QuantumCircuit(25, N_CBITS)
        fn(full)
        display = QuantumCircuit(25, n_sr, name=name)
        for inst in full.data:
            mapped = [display.clbits[full.find_bit(c).index % n_sr]
                      for c in inst.clbits]
            display.append(inst.operation, inst.qubits, mapped)
        qc.append(display.to_instruction(), [q(i) for i in range(25)], list(sr_c))

    # --- Logical measurement ---
    if logical_basis == "X":
        qc.h(q(MAGIC_STATE_QUBIT))
    elif logical_basis == "Y":
        qc.sdg(q(MAGIC_STATE_QUBIT))
        qc.h(q(MAGIC_STATE_QUBIT))
    qc.measure(q(MAGIC_STATE_QUBIT), c[0])
    for i in INIT_ZERO_STATES:
        qc.measure(q(i), c[0])
    for i in INIT_PLUS_STATES:
        qc.h(q(i))
        qc.measure(q(i), c[0])

    return qc


def main():
    figures = Path(__file__).parents[1] / "figures"
    figures.mkdir(exist_ok=True)
    out = figures / "msi_circuit.png"

    qc = build("Z")

    fig = qc.draw(
        output="mpl",
        fold=-1,
        style={"displaycolor": COLORS, "backgroundcolor": "#F8F8F8"},
    )
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved → {out}")


if __name__ == "__main__":
    main()
