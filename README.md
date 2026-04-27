# Magic State Injection on ibm_fez

Replication project for:

> Kim, Sevior & Usman, *Magic State Injection on IBM Quantum Processors Above
> the Distillation Threshold*, [arXiv:2412.01446](https://arxiv.org/abs/2412.01446) (2024).

The paper embeds a distance-3 **rotated** surface code on IBM's heavy-hex
lattice, runs a magic-state-injection protocol on 25 physical qubits of
`ibm_fez`, and reports logical fidelities above the distillation threshold
for both `|H_L⟩` and `|T_L⟩`.

## Current status

| Milestone | Paper ref | Status |
|---|---|---|
| 1. Qubit role map (data / syndrome / bridge) | Fig. 1b, S2 | ✅ |
| 2. Layout visualization | Fig. S2 | ✅ |
| 3. Initialization layout for MSI | Fig. 3a | ⏳ (needs stabilizer groups) |
| 4. Sub-round syndrome extraction circuit | Fig. 1e, 1f | ⏳ |
| 5. Full magic state injection circuit | Fig. 3b | ⏳ |
| 6. Post-selection + tomography | eq. 2, Fig. 4 | ⏳ |
| 7. Threshold simulation (Stim + PyMatching) | Fig. 2 | ⏳ |

## Quick start

```bash
# Create a virtual env (any modern Python 3.11+)
python -m venv .venv
source .venv/bin/activate

# Editable install so imports resolve from src/
pip install -e .

# Show the qubit role map (also saves figures/01_layout.png)
python scripts/01_show_layout.py
```

## Repository layout

```
msi-project/
├── pyproject.toml             # Package metadata + pinned deps (qiskit >= 2.0)
├── README.md                  # This file
│
├── src/msi/
│   ├── __init__.py
│   └── layout/                # Milestones 1-2
│       ├── __init__.py
│       ├── qubit_mapping.py   # roles, adjacency, coords (no Qiskit)
│       └── visualize.py       # matplotlib rendering of the layout
│
├── scripts/
│   └── 01_show_layout.py      # First sanity check: draw the role map
│
├── figures/                   # Generated plots live here
└── tests/                     # (empty for now)
```

Planned additions as we work through the paper:

```
src/msi/
├── code/                      # Backend-agnostic code theory
│   ├── stabilizers.py         # weight-4 / weight-2 / weight-1 X and Z stabs
│   └── logical_ops.py         # X_L, Z_L, Y_L = i X_L Z_L
├── circuits/                  # Qiskit circuits
│   ├── subround.py            # Fig. 1e sub-round extraction (fold/unfold)
│   ├── boundary.py            # Fig. 1f weight-2 / weight-1 top & bottom
│   ├── initialization.py      # Fig. 3a data-qubit init + central U3
│   ├── logical_meas.py        # X_L / Y_L / Z_L projective measurement
│   └── injection.py           # glue: full MSI circuit for one (θ, φ)
├── analysis/                  # Post-selection, tomography, fidelity
└── threshold/                 # Stim circuits + PyMatching decoding
```

## The 25-qubit mapping (Fig. S2)

| Role      | Count | Qubits                                          |
| --------- | ----- | ----------------------------------------------- |
| Data      | 11    | 0, 2, 5, 7, 8, 13, 14, 16, 20, 22, 23           |
| Syndrome  | 6     | 1, 6, 12, 15, 21, 24                            |
| Bridge    | 8     | 3, 4, 9, 10, 11, 17, 18, 19                     |

- **Central data qubit** (the `|ψ⟩` injection target in Fig. 3a): `q14`
- **Weight-1 "collapsed" data qubits** (heavy-hex extras): `q13` (measured by
  syndrome `q12`) and `q23` (measured by syndrome `q24`)

These labels are the paper's Fig. S2 labels, which may differ from
`ibm_fez`'s current hardware labels. When we move to the real device we'll
introduce a translation table; on `FakeFezV2` we pin everything with
`initial_layout` so nothing moves.