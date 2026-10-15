# Plan

Target: evidence of capability for the CERN Summer Student Programme 2027 application
(planned submission ~15 Jan 2027). Direction: scintillator R&D, Crystal Clear
Collaboration (CERN EP-CMX).

Rule: code is not trusted until the validation tests in M1 to M3 pass.
Dates revised 2026-10-15 (Aziz): pause 21 Dec 2026 to 3 Jan 2027.

## M0 — repo skeleton (by 25 Oct 2026) — done 2026-10-15
- [x] Local git repo, `src/` layout, `pyproject.toml` with pinned deps
- [x] `README.md` with goal and AI-use disclosure
- [x] `AGENTS.md`, `PLAN.md`, `docs/decisions.md`, `docs/references.md`
- [x] `docs/derivations/` with the first predict exercise
- [x] pytest + ruff, GitHub Actions CI on CPU
- [x] Private GitHub repo created under `aziz-bek-coder` and pushed
- [x] Argon works through Aziz's account; branch prefixes `claude/*`, `argon/*`, `aziz/*`

## M1 — analytic baseline + flat-interface RCWA (by 8 Nov 2026)
- [ ] Derivation 01 (escape cone, trapping) and 02 (Fresnel, flat RCWA) written, with
      predict exercises and 3 check questions each
- [ ] Escape-cone fraction η₁(n₁, n₂) implemented (Claude); cross-check by Argon pending
- [ ] Analytic Fresnel r_s, r_p, t_s, t_p incl. TIR
- [ ] torcwa flat interface reproduces Fresnel R, T (s and p) vs angle, tolerance stated
- [ ] R + T = 1 for lossless materials within tolerance
- [ ] Unpatterned LYSO→air, LYSO→n=1.5, BGO→air match the escape-cone estimate;
      numbers produced by `scripts/escape_cone.py` and `scripts/fresnel_vs_rcwa.py`
- [ ] One RCWA solve benchmarked against Fourier order (`scripts/benchmark_rcwa.py`);
      grid sizes for M2 chosen from that measurement
- [ ] Material constants cited in `docs/references.md` (PROVISIONAL until Aziz confirms)
- [ ] xfail gate converted to normal tests
- [ ] `docs/status.md` updated, PR merged after CI

## M2 — angle-resolved RCWA for a reference photonic crystal (by 22 Nov 2026)
- [ ] Derivation 03: k∥ + G, which orders propagate, trapped-mode escape
- [ ] Square lattice of TiO₂ (or Si₃N₄) pillars on LYSO; outside medium grease (n≈1.5) or air
- [ ] (θ, φ) sweep with C4v symmetry (φ in 0–45° for unpolarised light), both
      polarisations, T and R into each diffraction order
- [ ] Convergence study in Fourier orders, plot saved under `docs/figures/`
- [ ] Coarse grid for optimisation, fine grid for final evaluation; lookup tables cached
      to disk and runs resumable; peak RAM under 4 GB
- [ ] Lookup-table format defined and documented in `docs/decisions.md`

## M3 — Monte Carlo pixel model (by 6 Dec 2026)
- [ ] Derivation 04: bare-face expectation per wall model, transport time from path length
- [ ] 3×3×20 mm³ pixel, random emission points, isotropic directions
- [ ] Bulk absorption; wall models: specular / Lambertian / wrapped
- [ ] Readout face sampled from the RCWA lookup table incl. reflected orders
- [ ] Path length → transport time (group-index assumption stated)
- [ ] Bare face, no absorption reproduces the analytic expectation for the chosen wall model
- [ ] Outputs: extraction efficiency, transport-time CDF, early-photon fraction

## M4 — optimisation and comparison (by 20 Dec 2026)
- [ ] Derivation 05: the differentiable early-arrival objective
- [ ] Gradient-based optimisation over period, fill factor, height (coarse grid)
- [ ] Final designs evaluated with the Monte Carlo on the fine grid
- [ ] Key figure: efficiency and time CDF, bare vs literature-style PhC vs optimised, LYSO

## Pause — 21 Dec 2026 to 3 Jan 2027

## M5 — final figures, README, public release (4 to 12 Jan 2027)
- [ ] All figures regenerated from scripts in one command
- [ ] README final, limitations stated explicitly
- [ ] Technical note written by Aziz (agents review for correctness and clarity only)
- [ ] Licence chosen; repo made public only with Aziz's explicit approval
