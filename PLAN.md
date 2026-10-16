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
- [x] Derivation 01 (escape cone, trapping) and 02 (Fresnel, flat RCWA) written, with
      predict exercises and 3 check questions each
- [x] Escape-cone fraction η₁(n₁, n₂) implemented (Claude); cross-check by Argon pending
- [x] Analytic Fresnel r_s, r_p, t_s, t_p incl. TIR
- [x] torcwa flat interface reproduces Fresnel R, T (s and p) vs angle, tolerance stated
- [x] R + T = 1 for lossless materials within tolerance
- [x] Unpatterned LYSO→air, LYSO→n=1.5, BGO→air match the escape-cone estimate;
      numbers produced by `scripts/escape_cone.py` and `scripts/fresnel_vs_rcwa.py`
- [x] One RCWA solve benchmarked against Fourier order (`scripts/benchmark_rcwa.py`);
      grid sizes for M2 chosen from that measurement
- [x] Material constants cited in `docs/references.md` (PROVISIONAL until Aziz confirms)
- [x] xfail gate converted to normal tests
- [x] `docs/status.md` updated, PR merged after CI (PR #1)

## Infrastructure (2026-10-16)
- [x] History audited; emails rewritten to the noreply address (one approved rewrite)
- [x] MIT licence; README "work in progress"; actions pinned; read-only workflow token
- [x] Remote compute workflow (`compute.yml`) and job driver (`scripts/remote_job.py`)
- [ ] Repository public (blocked: PR #1 ref still exposes old commits; docs/status.md)
- [ ] Secret scanning push protection and branch protection (after publication)
- [x] First remote job: RCWA benchmark (run 38798175139); grids sized from it

## M2 — angle-resolved RCWA for a reference photonic crystal (by 22 Nov 2026) — done 2026-10-16
- [x] Derivation 03: k∥ + G, which orders propagate, trapped-mode escape
- [x] Square lattice of Si₃N₄ pillars on LYSO; outside medium grease (n = 1.46) or air
- [x] (θ, φ) sweep with C4v symmetry (φ in 0–45° for unpolarised light), both
      polarisations, T and R into each diffraction order
- [x] Convergence study in Fourier orders (remote run 38901900762), plot in `docs/figures/`
- [x] Coarse grid (θ 2° × φ 5°, order 7) built remotely in chunks, resumable; fine grid
      (θ 1° × φ 2.5°, order 9) planned for final evaluation
- [x] Lookup-table format defined and documented in `docs/decisions.md`

## M3 — Monte Carlo pixel model (by 6 Dec 2026) — done 2026-10-16
- [x] Derivation 04: bare-face expectation per wall model, transport time from path length
- [x] 3×3×20 mm³ pixel, random emission points, isotropic directions
- [x] Bulk absorption; wall models: specular / bare / air-gap mirror / air-gap diffuse / contact diffuse
- [x] Readout face sampled from the RCWA lookup table incl. reflected orders
- [x] Path length → transport time (group-index assumption stated)
- [x] Bare face, no absorption reproduces the analytic expectation for every wall model
      that keeps |w| (remote run 38902476498, all |z| < 2 at 1e6 photons)
- [x] Outputs: extraction efficiency, transport-time CDF, early-photon fraction
      (remote runs 38902480681, 38903357645)

## M4 — optimisation and comparison (by 20 Dec 2026)
- [x] Derivation 05: the differentiable early-arrival objective (corrected for side-wall
      losses, eq. 1a, after the Monte Carlo check)
- [x] Gradient-based optimisation over period, fill factor, height (coarse grid; remote
      runs 38905901930, 38905905490, air start recovered from the logs)
- [x] Final designs evaluated with the Monte Carlo on the fine grid (order 9, θ 1° × φ 5°;
      remote runs 38936853588, 38953882816; order check 38949360857)
- [x] Key figure: early vs total light, bare vs literature-style PhC vs optimised, LYSO
      (`docs/figures/key_figure.png`)

## Pause — 21 Dec 2026 to 3 Jan 2027

## M5 — final figures, README, public release (4 to 12 Jan 2027)
- [ ] All figures regenerated from scripts in one command
- [ ] README final, limitations stated explicitly
- [ ] Technical note written by Aziz (agents review for correctness and clarity only)
- [ ] Licence chosen; repo made public only with Aziz's explicit approval
