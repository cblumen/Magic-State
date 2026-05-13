from pathlib import Path
from typing import Literal

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from qiskit import QuantumCircuit

from msi.layout.qubit_mapping import SYNDROME_QUBITS

StabilizerType = Literal["X", "Z"]

N_CBITS = 10
CBIT: dict[tuple[int, ...], tuple[int, StabilizerType]] = {
    (0,):              [0, "Z"],
    (2,):              [1, "Z"],
    (0, 2, 7, 8):      [2, "Z"],
    (5, 13):           [3, "X"],
    (5, 7, 13, 14):    [4, "Z"],
    (7, 8, 14, 16):    [5, "X"],
    (13, 14, 20, 22):  [6, "X"],
    (14, 16, 22, 23):  [7, "Z"],
    (16, 23):          [8, "X"],
    (20, 22):          [9, "Z"],
}
WEIGHT_ONE_CBIT = len(SYNDROME_QUBITS)


def bulk_measure(
        A: int, B: int, C: int, D: int, E: int, F: int,
        G: int, H: int, I: int, J: int, K: int, L: int,
        qc: QuantumCircuit,draw: bool = False
) -> None:
    """Helper function to implement commonalities between subrounds.
    Qubits match with labeling from the paper, save for L: the right/left
    syndrome qubits."""
    # merging
    qc.cx(B, A)
    qc.cx(A, B)
    qc.cx(E, F)
    qc.cx(F, E)
    qc.cx(J, I)
    qc.cx(I, J)
    # folding
    qc.cx(B, C)
    qc.cx(G, F)
    qc.cx(F, E)
    qc.cx(J, K)
    qc.cx(I, J)
    qc.cx(A, B)

    # reset and measure D
    qc.reset(D)
    qc.cx(E, D)
    qc.cx(C, D)
    if draw:
        qc.measure(D, 0)  # placeholder for visualization; not a real CBIT assignment
    else:
        qc.measure(D, CBIT[tuple(sorted([E, C, G, A]))][0])

    # reset and measure H
    qc.reset(H)
    qc.h(H)
    qc.cx(H, G)
    qc.cx(H, I)
    qc.h(H)
    if draw:
        qc.measure(H, 1)  # placeholder for visualization; not a real CBIT assignment
    else:
        qc.measure(H, CBIT[tuple(sorted([K, I, G, E]))][0])

    # reset and measure L
    qc.reset(L)
    qc.h(L)
    qc.cx(L, A)
    qc.h(L)
    if draw:
        qc.measure(L, 2)  # placeholder for visualization; not a real CBIT assignment
    else:
        qc.measure(L, CBIT[tuple(sorted([A, C]))][0])

    # reverse folding
    qc.cx(A, B)
    qc.cx(I, J)
    qc.cx(J, K)
    qc.cx(F, E)
    qc.cx(G, F)
    qc.cx(B, C)
    # reverse merging
    qc.cx(I, J)
    qc.cx(J, I)
    qc.cx(F, E)
    qc.cx(E, F)
    qc.cx(A, B)
    qc.cx(B, A)


def subround_1(qc: QuantumCircuit) -> None:
    # Z7Z0Z2Z8 -> Z0Z2 (isolated from the rest of the subround)
    syndrome_qubit = 1

    # merging
    qc.cx(3, 7)
    qc.cx(7, 3)
    qc.cx(2, 4)
    qc.cx(4, 2)

    # folding
    qc.cx(3, 0)
    qc.cx(8, 4)
    qc.cx(4, 2)

    # reset and measure
    qc.reset(syndrome_qubit)
    qc.cx(0, syndrome_qubit)
    qc.cx(4, syndrome_qubit)
    qc.measure(syndrome_qubit, CBIT[(0, 2, 7, 8)][0])

    # reverse folding
    qc.cx(3, 0)
    qc.cx(4, 2)
    qc.cx(8, 4)

    # reverse merging
    qc.cx(7, 3)
    qc.cx(3, 7)
    qc.cx(4, 2)
    qc.cx(2, 4)

    # Z14Z16Z22Z23 -> Z14Z16, X13X14X20X22 -> X14X16, X16X23 -> X23
    bulk_measure(23, 19, 16, 15, 14, 18, 22, 21, 20, 17, 13, 24, qc)


def subround_2(qc: QuantumCircuit) -> None:
    # Z20Z22
    qc.reset(21)
    qc.cx(20, 21)
    qc.cx(22, 21)
    qc.measure(21, CBIT[(20, 22)][0])

    # Z0
    qc.measure(0, CBIT[(0,)][0])
    qc.reset(0)

    # Z2
    qc.measure(2, CBIT[(2,)][0])
    qc.reset(2)

    # Z13Z5Z7Z14 -> Z5Z7, X7X14X16X8 -> X14X16, X13X5 -> X13
    bulk_measure(13, 9, 5, 6, 7, 10, 14, 15, 16, 11, 8, 12, qc)


def full_round() -> QuantumCircuit:
    qc = QuantumCircuit(25, N_CBITS)
    subround_1(qc)
    subround_2(qc)
    return qc


def _save(qc: QuantumCircuit, out_path: str | Path, dpi: int) -> None:
    fig = qc.draw(output="mpl", fold=-1)
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved → {out_path}")


def draw(out_path: str | Path, *, dpi: int = 150) -> None:
    _save(full_round(), out_path, dpi)


def draw_bulk_measure(out_path: str | Path, *, dpi: int = 150) -> None:
    qc = QuantumCircuit(12,3)
    bulk_measure(0,1,2,3,4,5,6,7,8,9,10,11,qc,draw=True)
    _save(qc, out_path, dpi)




if __name__ == "__main__":
    figures = Path(__file__).parents[3] / "figures"
    figures.mkdir(exist_ok=True)
    draw_bulk_measure(figures / "bulk_measure.png")
    draw(figures / "full_round.png")
