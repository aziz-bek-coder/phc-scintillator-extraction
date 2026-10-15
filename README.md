# phc-scintillator-extraction

**Inverse-designed photonic-crystal readout layer for scintillator light extraction and fast timing.**

> **Work in progress.** Milestones, dates and what is validated so far are tracked in
> [PLAN.md](PLAN.md) and [docs/status.md](docs/status.md). Numbers in this repository are
> preliminary until the milestone that produces them is marked done.

Heavy inorganic scintillators such as LYSO (n ≈ 1.81) and BGO (n ≈ 2.15) trap most of
their scintillation light by total internal reflection, and the bouncing that follows
spreads photon arrival times at the photodetector. This project builds a reproducible
simulation chain for one scintillator pixel: angle-resolved RCWA (rigorous coupled-wave
analysis, via `torcwa`) of a periodic layer on the readout face, a Monte Carlo ray model
of the pixel that samples the RCWA lookup table including reflected diffraction orders,
and gradient-based optimisation of the layer geometry. The figures of merit are
light-extraction efficiency and the transport-time distribution of detected photons
(CDF and early-photon fraction). Unlike most published photonic-crystal designs, which
maximise total light yield, the objective here is weighted toward *early* photon
arrival, the quantity that matters for timing. Scope is photon transport only:
scintillation kinetics and the photodetector's single-photon time resolution are
outside the model and are stated as limitations.

## Quick start (CPU only)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -e ".[dev]"
pytest            # fast tests only; slow ones are skipped by default
ruff check .
```

Heavy computations (benchmarks, convergence studies, lookup tables, Monte Carlo runs,
optimisation) run on GitHub Actions through the `compute` workflow, not on a laptop:

```bash
gh workflow run compute.yml -f job=benchmark -f config=configs/benchmark.json
gh run watch <run-id>
gh run download <run-id> -D results/benchmark/<run-id>/
```

## Layout

```
src/phcscint/        main package (see AGENTS.md for module ownership)
src/phcscint/xcheck/ independent cross-check implementations (owned by Argon)
tests/               pytest suite; CI runs all of it, laptops skip @pytest.mark.slow
scripts/             every number or figure in the docs is produced by a script here
configs/             parameter files for remote jobs (scripts/remote_job.py)
docs/derivations/    derivations behind each physics module
docs/decisions.md    design-decision log
docs/status.md       progress, numbers produced, open issues
docs/references.md   references with DOIs and how each was verified
```

## Disclosure

AI coding assistants (Claude Code by Anthropic, and a second agent referred to as
"Argon") were used in this repository under the rules in [AGENTS.md](AGENTS.md). They
wrote code, tests and tooling, drafted the derivations in `docs/derivations/`, and
made the design decisions logged in `docs/decisions.md`, which I review. I work
through every derivation (predict exercises and check questions), I write the
technical note myself, and I (Azizbek Eshmominov) take full responsibility for the
correctness of the physics and the results reported here. Every quantitative claim in
the documentation is produced by a script in this repository or taken from a cited,
verified source.

No code, data or designs from any prior internship or employer are included.

## Licence

MIT, see [LICENSE](LICENSE).
