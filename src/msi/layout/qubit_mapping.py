"""
Qubit role mapping for the distance-3 rotated surface code on ibm_fez.

Follows Kim, Sevior & Usman, "Magic State Injection on IBM Quantum Processors
Above the Distillation Threshold" (arXiv:2412.01446). Specifically Fig. 1b
(rotated surface code embedded in the heavy-hex lattice) and Fig. S2 (the
25 physical qubits chosen on ibm_fez).

Each of the 25 physical qubits plays one of three roles:

    DATA (11):      carries the logical quantum information. Green circles
                    in Fig. 1b. These are the qubits whose Pauli operators
                    appear in the code's stabilizers and logical operators.

    SYNDROME (6):   ancilla qubits that we prepare, interact with data
                    qubits via CNOTs, and measure each sub-round to extract
                    error syndromes. Pink/magenta in Fig. 1b.

    BRIDGE (8):     helper qubits that route long-range interactions through
                    the heavy-hex connectivity. Black circles in Fig. 1b.
                    Bridges are used to "fold" a weight-4 stabilizer like
                    Z_A Z_C Z_E Z_G down into a weight-2 stabilizer
                    Z_C Z_E (eq. 1a of the paper) so a single syndrome
                    qubit can measure it, then "unfolded" to restore the
                    original stabilizer. Bridges are not measured.

The paper's mapping (Table I) for a d=3 rotated surface code on heavy-hex:
    # data qubits  = d^2 + d - 1       =  9 + 3 - 1 = 11
    # total qubits = 5/2 d^2 + 2d - 7/2 = 22.5 + 6 - 3.5 = 25

Two of the 11 data qubits (13 and 23 in our numbering) are "extras"
introduced by the heavy-hex embedding. Each full round they get collapsed
back to |0> by a weight-1 Z measurement from their only neighbor (which
happens to be a syndrome qubit of degree 1: qubits 12 and 24). After
collapse, the remaining 9 data qubits span the code space of a standard
d=3 rotated surface code.

Qubit 14 is the CENTRAL data qubit. In the magic state injection protocol
(Fig. 3a), this is the qubit initialized in the arbitrary single-qubit
state |psi> = cos(theta/2)|0> + e^{i phi} sin(theta/2)|1>. Its preparation
at the physical level, combined with the syndrome extraction, produces the
logical state |psi_L> on the d=3 code.

IMPORTANT: The qubit labels 0..24 used here are the labels from the paper's
Fig. S2, which (per the project owner) appear to have been RENUMBERED relative
to ibm_fez's actual hardware labels. When we later transpile for the real
backend we will need a translation table from these labels to the real
hardware indices. For now, the simulator (FakeFezV2) is indifferent to this
as long as we pin the circuit to a fixed initial_layout.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


# ======================================================================
# Roles
# ======================================================================

class QubitRole(Enum):
    """What each physical qubit does in the d=3 rotated surface code."""
    DATA = auto()
    SYNDROME = auto()
    BRIDGE = auto()


# Role assignments (user-verified against Fig. 1b of the paper).
DATA_QUBITS: list[int] = [0, 2, 5, 7, 8, 13, 14, 16, 20, 22, 23]
SYNDROME_QUBITS: list[int] = [1, 6, 12, 15, 21, 24]
BRIDGE_QUBITS: list[int] = [3, 4, 9, 10, 11, 17, 18, 19]

# Reverse lookup: qubit index -> role.
QUBIT_ROLE: dict[int, QubitRole] = {
    **{q: QubitRole.DATA for q in DATA_QUBITS},
    **{q: QubitRole.SYNDROME for q in SYNDROME_QUBITS},
    **{q: QubitRole.BRIDGE for q in BRIDGE_QUBITS},
}

# --- Sanity checks that run on import. ---
# If any of these fail we've introduced a typo in the role lists.
_ALL = set(DATA_QUBITS) | set(SYNDROME_QUBITS) | set(BRIDGE_QUBITS)
assert _ALL == set(range(25)), (
    "Qubit role assignments must partition exactly {0, 1, ..., 24}. "
    f"Missing: {set(range(25)) - _ALL}; extra: {_ALL - set(range(25))}"
)
assert len(DATA_QUBITS) + len(SYNDROME_QUBITS) + len(BRIDGE_QUBITS) == 25, (
    "A qubit has been assigned to more than one role."
)
assert len(DATA_QUBITS) == 11, (
    f"Paper specifies d^2+d-1=11 data qubits for d=3; got {len(DATA_QUBITS)}."
)


# ======================================================================
# Special data-qubit roles
# ======================================================================

# The central data qubit, where the arbitrary single-qubit state |psi> is
# prepared via a physical U3(theta, phi, 0) gate in step 1 of the MSI
# protocol (paper Section III, "Initialization").
CENTRAL_DATA_QUBIT: int = 14

# Data qubits that the heavy-hex embedding forces us to "collapse" each
# round via a weight-1 Z measurement. They each have exactly one physical
# neighbor, which is the syndrome qubit that performs the measurement.
WEIGHT_ONE_DATA_QUBITS: list[int] = [13, 23]

# Which syndrome qubit performs the weight-1 Z measurement on each
# collapsed data qubit. Built from the heavy-hex connectivity below.
WEIGHT_ONE_SYNDROMES: dict[int, int] = {13: 12, 23: 24}


# ======================================================================
# Heavy-hex connectivity (the physical CZ coupling map of our 25 qubits)
# ======================================================================
# Read off from Fig. S2. Each edge (u, v) with u < v means a native
# two-qubit gate can be applied directly between u and v on ibm_fez.
# All CNOTs we schedule in the syndrome extraction circuits must go
# along one of these edges.
EDGES: list[tuple[int, int]] = [
    # Top horizontal strip (0-1-2)
    (0, 1), (1, 2),
    # Bridges leading down from 1 and 2
    (0, 3), (2, 4),
    # Bridges continuing down from 3 and 4 to the upper horizontal strip
    (3, 7), (4, 8),
    # Upper horizontal strip (5-6-7), plus 8 sitting at the same row but
    # disconnected from 7 (no 7-8 edge; 8 only touches 4 above and 11 below)
    (5, 6), (6, 7),
    # Bridges from the upper strip down to the middle strip
    (5, 9), (7, 10), (8, 11),
    # Bridges continuing down
    (9, 13), (10, 14), (11, 16),
    # Middle horizontal strip (12-13-14-15-16)
    (12, 13), (14, 15), (15, 16),
    # Bridges leading down from the middle strip
    (13, 17), (14, 18), (16, 19),
    # Bridges continuing to the bottom
    (17, 20), (18, 22), (19, 23),
    # Bottom horizontal strips: 20-21-22 on the left, 23-24 on the right
    (20, 21), (21, 22), (23, 24),
]


def neighbors(q: int) -> set[int]:
    """Return the physical neighbors of qubit q in the heavy-hex subgraph.

    Uses the EDGES list above. Complexity is O(|E|) per call, which is fine
    here because |E| = 25. If we ever need high-throughput access we can
    cache this into an adjacency dict.
    """
    out: set[int] = set()
    for u, v in EDGES:
        if u == q:
            out.add(v)
        elif v == q:
            out.add(u)
    return out


# --- Consistency check: the SYNDROME qubits that perform weight-1 Z
#     measurements must themselves have degree 1 in the heavy-hex subgraph,
#     and their only neighbor must be the data qubit they're measuring.
#     (The data qubit has plenty of other neighbors because it also
#     participates in the weight-4 and weight-2 bulk/boundary stabilizers.)
#     This catches mapping typos early: if anyone changes the role lists or
#     EDGES, and the weight-1 story breaks, import fails loudly.
for _d, _s in WEIGHT_ONE_SYNDROMES.items():
    assert QUBIT_ROLE[_s] is QubitRole.SYNDROME, (
        f"Weight-1 syndrome {_s} is marked as {QUBIT_ROLE[_s].name}, "
        "not SYNDROME."
    )
    _s_nbrs = neighbors(_s)
    assert _s_nbrs == {_d}, (
        f"Weight-1 syndrome q{_s} must have exactly one neighbor (the data "
        f"qubit q{_d} it measures); got {_s_nbrs}."
    )
    assert QUBIT_ROLE[_d] is QubitRole.DATA, (
        f"Weight-1 target {_d} is marked as {QUBIT_ROLE[_d].name}, not DATA."
    )


# ======================================================================
# Visualization coordinates
# ======================================================================
# (x, y) positions used by layout.visualize for plotting. These only affect
# how the figure looks; they do not enter any circuit logic.
#
# They approximate the heavy-hex geometry of Fig. S2. Note the two "long"
# horizontal edges: 13-14 and 21-22. In the real heavy-hex the horizontal
# strip is locally straight but the two halves (left of the central column
# and right of it) are offset so the bridges above and below land cleanly.
# Rendering each edge as a straight line is close enough for a layout check.
QUBIT_COORDS: dict[int, tuple[float, float]] = {
    # Top horizontal strip (y=6)
    0: (1, 6), 1: (2, 6), 2: (3, 6),
    # Bridges going down (y=5)
    3: (1, 5), 4: (3, 5),
    # Upper horizontal strip 5-6-7 plus separate 8 (y=4)
    5: (-1, 4), 6: (0, 4), 7: (1, 4), 8: (3, 4),
    # Bridges going down (y=3)
    9: (-1, 3), 10: (1, 3), 11: (3, 3),
    # Middle horizontal strip 12-13-14-15-16 (y=2)
    12: (-2, 2), 13: (-1, 2), 14: (1, 2), 15: (2, 2), 16: (3, 2),
    # Bridges going down (y=1)
    17: (-1, 1), 18: (1, 1), 19: (3, 1),
    # Bottom horizontal strips 20-21-22 and 23-24 (y=0)
    20: (-1, 0), 21: (0, 0), 22: (1, 0), 23: (3, 0), 24: (4, 0),
}
assert set(QUBIT_COORDS.keys()) == set(range(25))


# ======================================================================
# Convenience accessor for downstream modules
# ======================================================================

@dataclass(frozen=True)
class Layout:
    """Snapshot of the 25-qubit role mapping.

    This is a frozen dataclass so downstream code can pass it around as a
    single immutable object rather than importing six module-level names.
    Future work (syndrome-extraction circuits, stabilizer definitions) will
    read from instances of this class.
    """
    data: tuple[int, ...]
    syndrome: tuple[int, ...]
    bridge: tuple[int, ...]
    central: int
    weight_one_data: tuple[int, ...]
    weight_one_syndromes: dict[int, int]
    edges: tuple[tuple[int, int], ...]

    @property
    def all_qubits(self) -> tuple[int, ...]:
        return tuple(range(25))


def get_layout() -> Layout:
    """Return the canonical d=3 heavy-hex rotated surface code layout."""
    return Layout(
        data=tuple(DATA_QUBITS),
        syndrome=tuple(SYNDROME_QUBITS),
        bridge=tuple(BRIDGE_QUBITS),
        central=CENTRAL_DATA_QUBIT,
        weight_one_data=tuple(WEIGHT_ONE_DATA_QUBITS),
        weight_one_syndromes=dict(WEIGHT_ONE_SYNDROMES),
        edges=tuple(EDGES),
    )