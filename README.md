# phc-scintillator-extraction

**Inverse-designed photonic-crystal readout layer for scintillator light extraction and fast timing.**

Heavy inorganic scintillators such as LYSO (n ≈ 1.82) and BGO (n ≈ 2.15) trap most of
their scintillation light by total internal reflection, and the bouncing that follows
spreads photon arrival times at the photodetector. This project builds a reproducible,
CPU-runnable simulation chain for one scintillator pixel: angle-resolved RCWA
(rigorous coupled-wave analysis, via `torcwa`) of a periodic layer on the readout face,
a Monte Carlo ray model of the pixel that samples the RCWA lookup table including
reflected diffraction orders, and gradient-based optimisation of the layer geometry.
The figures of merit are light-extraction efficiency and the transport-time
distribution of detected photons (CDF and early-photon fraction). Unlike most
published photonic-crystal designs, which maximise total light yield, the objective
here is weighted toward *early* photon arrival, the quantity that matters for timing.
Scope is photon transport only: scintillation kinetics and the photodetector's
single-photon time resolution are outside the model and are stated as limitations.

Status: **M0 (skeleton)**. See [PLAN.md](PLAN.md) for milestones and
[docs/decisions.md](docs/decisions.md) for the design-decision log.

## Quick start (CPU only)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -e ".[dev]"
pytest
ruff check .
```

## Layout

```
src/phcscint/        main package (see AGENTS.md for module ownership)
src/phcscint/xcheck/ independent cross-check implementations (owned by Argon)
tests/               pytest suite; CI runs it on CPU
scripts/             every number or figure in the docs is produced by a script here
docs/derivations/    hand derivations written by Aziz before each physics module
docs/decisions.md    design-decision log
docs/references.md   verified references with DOIs
```

## Disclosure

AI coding assistants (Claude Code by Anthropic, and a second agent referred to as
"Argon") were used to write code, tests and tooling in this repository, under the rules
in [AGENTS.md](AGENTS.md). All physics derivations, design choices, interpretation of
results and the accompanying technical note are my own, and I (Azizbek Eshmominov)
take full responsibility for the correctness of the physics and the results reported
here. Every quantitative claim in the documentation is produced by a script in this
repository or taken from a cited, verified publication.

No code, data or designs from any prior internship or employer are included.
