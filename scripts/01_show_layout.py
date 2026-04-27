"""
Script 01: show the qubit role map for the d=3 rotated surface code on ibm_fez.

Run from the project root:

    python scripts/01_show_layout.py

Produces figures/01_layout.png and, if your environment supports it, pops
up an interactive matplotlib window.

This is the first sanity check of the project: the role mapping is purely
data-driven and has nothing to do with Qiskit yet, so if this script runs
cleanly and the picture matches Fig. S2 of the paper, we're ready to move
on to the syndrome-extraction circuit.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make `src/` importable when running this script directly from the repo root,
# without having installed the package in editable mode.
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))

import matplotlib.pyplot as plt  # noqa: E402  (after sys.path edit)

from msi.layout import (  # noqa: E402
    BRIDGE_QUBITS,
    CENTRAL_DATA_QUBIT,
    DATA_QUBITS,
    SYNDROME_QUBITS,
    WEIGHT_ONE_DATA_QUBITS,
    WEIGHT_ONE_SYNDROMES,
    neighbors,
    plot_layout,
)


def _print_summary() -> None:
    """Print a textual summary of the mapping. Useful for logs and CI."""
    print("=" * 64)
    print("  Distance-3 rotated surface code on ibm_fez")
    print("=" * 64)
    print(f"  Data qubits     (n={len(DATA_QUBITS):>2}): {DATA_QUBITS}")
    print(f"  Syndrome qubits (n={len(SYNDROME_QUBITS):>2}): {SYNDROME_QUBITS}")
    print(f"  Bridge qubits   (n={len(BRIDGE_QUBITS):>2}): {BRIDGE_QUBITS}")
    print()
    print(f"  Central |ψ⟩ injection target: q{CENTRAL_DATA_QUBIT}")
    print(f"  Weight-1 collapsed data qubits: {WEIGHT_ONE_DATA_QUBITS}")
    print(f"  Weight-1 measurement assignments: {WEIGHT_ONE_SYNDROMES}")
    print()

    # Cross-check: each weight-1 data qubit's single neighbor should match
    # its assigned syndrome, and the central qubit should live comfortably
    # in the middle of the mesh.
    print("  --- adjacency checks ---")
    for q in WEIGHT_ONE_DATA_QUBITS:
        print(f"    neighbors(q{q}) = {sorted(neighbors(q))}")
    print(f"    neighbors(q{CENTRAL_DATA_QUBIT}) = "
          f"{sorted(neighbors(CENTRAL_DATA_QUBIT))}")
    print()


def main() -> int:
    _print_summary()

    save_path = _REPO_ROOT / "figures" / "01_layout.png"
    fig, ax = plot_layout(save_path=save_path)

    # If this is running in a non-interactive environment (CI, headless),
    # plt.show() is a no-op after savefig. No harm done.
    plt.show()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())