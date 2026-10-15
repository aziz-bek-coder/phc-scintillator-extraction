# Plan

Target: evidence of capability for the CERN Summer Student Programme 2027 application
(planned submission ~15 Jan 2027). Direction: scintillator R&D, Crystal Clear
Collaboration (CERN EP-CMX).

Rule: code is not trusted until the validation tests in M1 to M3 pass.

## M0 — repo skeleton (by 25 Oct 2026)
- [x] Local git repo, `src/` layout, `pyproject.toml` with pinned deps
- [x] `README.md` with goal and AI-use disclosure
- [x] `AGENTS.md`, `PLAN.md`, `docs/decisions.md`, `docs/references.md`
- [x] `docs/derivations/` with the first predict exercise
- [x] pytest + ruff, GitHub Actions CI on CPU
- [ ] Private GitHub repo created under `aziz-bek-coder` (needs Aziz's go-ahead)
- [ ] Argon given access; branch protection on `main` (no direct pushes)
- [ ] Aziz writes `docs/derivations/01-escape-cone-and-trapping.md`

## M1 — analytic baseline + flat-interface RCWA (by 8 Nov 2026)
- [ ] Escape-cone fraction η₁(n₁, n₂) implemented (Claude) and cross-checked (Argon)
- [ ] Analytic Fresnel r_s, r_p, t_s, t_p incl. TIR; both implementations agree
- [ ] torcwa flat interface reproduces Fresnel R, T (s and p) vs angle, tolerance stated
- [ ] R + T = 1 for lossless materials within tolerance
- [ ] Unpatterned LYSO→air, LYSO→n=1.5, BGO→air match the escape-cone estimate
  (expected ≈ 8.2 %, 21.7 %, 5.7 %; the repo numbers come from `scripts/`, not from memory)
- [ ] Material constants (n, emission peak) cited in `docs/references.md`
- [ ] Predict exercise + 3 check questions done for Fresnel/RCWA

## M2 — angle-resolved RCWA for a reference photonic crystal (by 22 Nov 2026)
- [ ] Square lattice of TiO₂ (or Si₃N₄) pillars on LYSO; outside medium grease (n≈1.5) or air
- [ ] (θ, φ) sweep, both polarisations, T and R into each diffraction order
- [ ] Convergence study in Fourier orders, plot saved under `docs/figures/`
- [ ] Reciprocal-lattice argument |k∥ + G| < n₂k₀ checked against which orders propagate
- [ ] Lookup-table format defined and documented in `docs/decisions.md`

## M3 — Monte Carlo pixel model (by 13 Dec 2026)
- [ ] 3×3×20 mm³ pixel, random emission points, isotropic directions
- [ ] Bulk absorption; wall models: specular / Lambertian / wrapped
- [ ] Readout face sampled from the RCWA lookup table incl. reflected orders
- [ ] Path length → transport time (group-index assumption stated)
- [ ] Bare face, no absorption reproduces the analytic expectation for the chosen wall model
- [ ] Outputs: extraction efficiency, transport-time CDF, early-photon fraction

## M4 — optimisation and comparison (by 27 Dec 2026)
- [ ] Differentiable objective: angle-weighted transmission of trapped modes, weighted toward early arrival
- [ ] Gradient-based optimisation over period, fill factor, height
- [ ] Final designs evaluated with the Monte Carlo
- [ ] Key figure: efficiency and time CDF, bare vs literature-style PhC vs optimised, LYSO

## M5 — final figures, README, public release (by 10 Jan 2027)
- [ ] All figures regenerated from scripts in one command
- [ ] README final, limitations stated explicitly
- [ ] Technical note written by Aziz (agents review for correctness and clarity only)
- [ ] Licence chosen, repo made public (~10 Jan 2027)
