# Magic State Injection on ibm_fez

Replication of:

> Kim, Sevior & Usman, *Magic State Injection on IBM Quantum Processors Above
> the Distillation Threshold*, [arXiv:2412.01446](https://arxiv.org/abs/2412.01446) (2024).

The paper embeds a distance-3 rotated surface code on IBM's heavy-hex lattice,
runs a magic-state-injection (MSI) protocol on 25 physical qubits of `ibm_fez`,
and reports logical fidelities above the distillation threshold for `|H_L⟩` and
`|T_L⟩`.

This repo implements the full injection pipeline — circuit construction,
post-selection, tomography, and fidelity — and can run against a local
statevector simulator, the `FakeFezV2` noise model, or real `ibm_fez` hardware.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .

python scripts/01_show_layout.py          # draw the qubit role map
python scripts/02_inject_single_state.py  # inject H and T states, run tomography
python scripts/03_run_injection_grid.py   # sweep 9×9 (θ, φ) grid → results/injection_grid.json
```

By default all scripts use a local AerSimulator (no API key needed). Set
environment variables to switch backends or tune shots:

```bash
IBM_BACKEND=fake_fez SHOTS=4000 python scripts/02_inject_single_state.py
IBM_BACKEND=ibm_fez  SHOTS=8192 python scripts/03_run_injection_grid.py
```

`ibm_fez` requires `IBM_QUANTUM_TOKEN` to be set. Copy `.env.example` to `.env`
and fill it in, or export the variable directly.

## Repository layout

```
├── pyproject.toml
├── scripts/
│   ├── 01_show_layout.py          # visualize qubit role map (Fig. S2)
│   ├── 02_inject_single_state.py  # single H / T injection + tomography
│   ├── 03_run_injection_grid.py   # full (θ, φ) sweep
│   ├── draw_msi_circuit.py        # render the injection circuit diagram
│   └── draw_gate_tomography.py    # gate-by-gate Bloch sphere tomography
│
└── src/msi/
    ├── layout/
    │   ├── qubit_mapping.py       # qubit roles, adjacency, FEZ_INITIAL_LAYOUT
    │   └── visualize.py           # matplotlib layout rendering
    ├── circuits/
    │   ├── subround.py            # syndrome-extraction sub-rounds (Fig. 1e/f)
    │   └── injection.py           # full MSI circuit for one (θ, φ)
    └── analysis/
        ├── post_selection.py      # bulk-syndrome post-selection
        ├── tomography.py          # Bloch vector + density matrix reconstruction
        ├── fidelity.py            # state fidelity
        └── show_grid.py           # visualize injection_grid.json results
```

## The 25-qubit mapping (Fig. S2)

| Role     | Count | Qubits                                |
|----------|-------|---------------------------------------|
| Data     | 11    | 0, 2, 5, 7, 8, 13, 14, 16, 20, 22, 23 |
| Syndrome | 6     | 1, 6, 12, 15, 21, 24                  |
| Bridge   | 8     | 3, 4, 9, 10, 11, 17, 18, 19           |

- **Central data qubit** (injection target, Fig. 3a): `q14`
- **Weight-1 data qubits**: `q13` (measured by syndrome `q12`) and `q23`
  (measured by syndrome `q24`)

Qubit labels follow the paper's Fig. S2 numbering. On `FakeFezV2` and real
hardware the circuit is pinned via `initial_layout` so no routing occurs.

## Dependencies

Core: `qiskit >= 2.0`, `qiskit-ibm-runtime >= 0.30`, `numpy`, `matplotlib`.

```bash
pip install -e .          # core only
pip install -e ".[dev]"   # + pytest, mypy, ruff
```
