# Status

Updated by the agents. Newest first. Every number below comes from a file in
`results/` (named next to it), produced by the script named there, at the commit
recorded inside that file. Commit hashes from before 2026-10-16 are translated in
[history-rewrite.md](history-rewrite.md).

## Needs Aziz

1. **Publication is blocked (one decision needed).** The history rewrite worked, but
   GitHub still serves the old commits, with your Gmail address, through the merged
   pull request #1. Users cannot delete pull-request refs. Two ways out, either is
   enough; I will finish the checklist and publish as soon as one is done:
   - *Recreate (fastest, nothing lost):* approve renaming this repository to
     `phc-scintillator-extraction-archive` (it stays private, untouched) and creating a
     fresh `phc-scintillator-extraction` with the clean history. I need approval because
     a rename is a settings change and creating repositories was not in the approved
     list.
   - *Purge:* ask GitHub Support to remove `refs/pull/1/*` and cached views of the old
     commits for this repository, then tell me it is done.
2. **My mistake: two merge commits on main carry your Gmail again.** I merged PRs #2
   and #3 with `gh pr merge`, and GitHub authored those merge commits (`c7e7621`,
   `38bcdf6`) with your account's primary email. Removing them needs a second history
   rewrite, which you have not approved, so I have not done it. With the "recreate"
   option above, the fresh repository would get a clean history in one go (that
   rewrite also needs your approval). GitHub rejected the noreply address as a merge
   author, so from PR #4 on, pull requests are merged by fast-forward with no
   GitHub-authored commit (AGENTS.md). Worth knowing: your public
   GitHub profile itself shows this Gmail address; enabling "Keep my email addresses
   private" in your GitHub account settings would prevent this class of leak.
3. **Material constants are PROVISIONAL.** LYSO n = 1.81 at 420 nm, BGO n = 2.15 at
   480 nm (Luxium product pages), grease n = 1.46 (Eljen EJ-550). Please confirm.
4. **References not content-verified** beyond abstracts: Knapitsch 2012 (geometry not
   read; thesis PDF is copy-protected), Carr Delgado 2024. No citable reflectivity was
   found for mirror or diffuse wrapping films, so wall reflectivity 0.95 is an
   assumption in M3.
5. **Argon** has not started. No independent cross-check exists yet.
6. **GitHub Actions minutes.** This repository has used about 1,340 of the 2,000
   free private-repository minutes this month. The quota is shared with your other
   private repositories, which I cannot see; please check Settings → Billing →
   Usage. Making the repository public (item 1) would make standard runners free.

## M4 — optimisation and comparison (done 2026-10-16)

### Done
- Derivation 05, with predict exercise, 3 check questions and answers:
  - for τ below the direct transit time, the early-photon yield is a cos θ-weighted
    single-pass integral, eq. (1);
  - the pillar layer is solved with differentiable RCWA, using the exact Fourier
    coefficients of a disk, eq. (4);
  - correction after the Monte Carlo check: (1) is an upper bound when grazing light
    transmitted by the readout crosses a side escape cone on its way, and new eq. (1a)
    adds those side-wall losses.
- `optimize.py`: an analytic-disk layer on torcwa, the objective and its gradient, and
  Adam on bounded parameters, resumable.
- Remote jobs `optimize` and `ordercheck`.
- Light scripts:
  - `check_early_yield.py`, `make_m4_configs.py`, `recover_optimize_log.py`;
  - `m4_table_checks.py`, `plot_angular_transmission.py`, `key_figure.py`.
- Tests:
  - J₁ and its derivative against scipy;
  - the analytic disk against the pixel FFT, and the analytic layer against the FFT
    layer;
  - invisible pillars give Fresnel;
  - the gradient against finite differences;
  - exact resume;
  - closed incidences: two regression tests (Open issues 1);
  - smoke tests of the optimize and ordercheck jobs.

### Numbers produced
Setup:
- LYSO pixel 3 × 3 × 20 mm, n = 1.81 at 420 nm.
- Si₃N₄ pillars, n = 2.0906 (Luke 2015).
- Early yield E taken at τ = 100 ps (direct transit 120.8 ps).
- Monte Carlo: 10⁶ photons per case. Nominal walls: all five other faces polished +
  air gap + mirror film, reflectivity 0.95 (assumed).

**Eq. (1) against the M3 Monte Carlo, bare face** (`results/m4_early_yield_check.json`):
- grease: 12.78 % from (1), 12.77 ± 0.03 % from the Monte Carlo (z = −0.3);
- air: 5.46 % against 5.49 ± 0.02 % (z = +1.1).

**Optimisation**: Fourier order 5, 18 × 4 incidences, 30 Adam steps, lr 0.15. All
objectives are on that same angle grid.

| Medium, objective | Run, starts | Best design: period / fill / height (pillar radius) | Best objective (order-7 recheck) | Bare face | Reference design |
|---|---|---|---|---|---|
| Grease, E(100 ps) | 38905901930, 6 | 0.234 µm / 0.117 / 0.217 µm (45 nm) | 13.58 % (13.58 %) | 13.09 % | 13.17 % |
| Grease, single pass | 38905905490, 4 | 0.559 µm / 0.495 / 0.213 µm (222 nm) | 24.26 % (24.27 %) | 19.81 % | 21.73 % |
| Air, E(100 ps) | 38950528275 (after two failed attempts), 4 | 0.232 µm / 0.248 / 0.266 µm (65 nm), step 21 | 6.26 % | 5.78 % | 5.63 % |

Sources:
- `results/optimize-38905901930.json`, `results/optimize-38905905490.json`;
- `results/optimize-38950528275.json`, `results/m4_opt_air_early_start1_recovered.json`;
- figures `docs/figures/m4_opt_grease_*.png`.

Per-start results:
- Grease, E(100 ps): the other starts reach 12.96–13.27 %.
- Grease, single pass: two starts reach the same design.
- Air: the evaluated design is step 21 of the best start, recovered from the job logs
  before the fixed rerun finished (Open issues 1). The rerun's best, at step 29, is
  6.262 % (order 7: 6.261 %) at 0.2317 µm / 0.2485 / 0.2716 µm. That is 0.004 points
  above step 21, so the fine table and Monte Carlo of step 21 were kept. The other air
  starts reach at most 5.94 %.

**Fine tables, first pass**:
- Grid: order 9, θ 1° × φ 5°; node quadrature of (1) and of derivation 03, eq. 9.
- Energy conserved to 7e-10.
- ± is the angle-grid bound. For the flat face it exceeds the true grid error by 2–3 times
  (grease) and much more for air.

Sources: `results/m4_table_checks.json`, `results/lut-*.json`, figure
`docs/figures/m4_angular_transmission.png`.

| Readout | E(100 ps), eq. (1) | change from θ < θc | change from θ > θc | Single pass η₁ |
|---|---|---|---|---|
| Flat face, grease | 12.78 % | | | 19.20 % |
| Reference, grease | 12.87 ± 0.03 % | −1.27 | +1.36 | 21.08 ± 0.11 % |
| Optimised for E(100 ps), grease | 13.18 ± 0.06 % | +0.11 | +0.28 | 20.22 ± 0.14 % |
| Optimised for single pass, grease | 12.65 ± 0.10 % | −2.55 | +2.42 | 23.70 ± 0.43 % |
| Flat face, air | 5.46 % | | | 7.17 % |
| Reference, air | 5.59 ± 0.13 % | −2.04 | +2.17 | 8.75 ± 0.26 % |
| Optimised for E(100 ps), air | 5.88 ± 0.04 % | −0.37 | +0.79 | 8.16 ± 0.13 % |

The changes are in points of E(100 ps), relative to the flat face.

**Monte Carlo comparison**, with the gain relative to the bare face. Statistical σ of
each fraction ≤ 0.05 points.

Sources: `results/mc-38936853588.json`, `results/mc-38953882816.json`,
`results/key_figure.json`, figure `docs/figures/key_figure.png`.

| Readout | Detected by 100 ps | Gain | Detected by 5 ns | Gain | Median arrival |
|---|---|---|---|---|---|
| Bare, grease | 12.80 % | | 40.39 % | | 159 ps |
| Reference, grease | 12.76 % | −0.3 ± 0.4 % | 59.18 % | +46.5 % | 234 ps |
| Optimised for E(100 ps), grease | 13.16 % | **+2.9 ± 0.4 %** | 50.73 % | +25.6 % | 194 ps |
| Optimised for single pass, grease | 12.53 % | −2.1 ± 0.4 % | 64.62 % | +60.0 % | 266 ps |
| Bare, air | 5.47 % | | 16.05 % | | 148 ps |
| Reference, air | 5.54 % | +1.2 ± 0.6 % | 53.39 % | +233 % | 731 ps |
| Optimised for E(100 ps), air | 5.85 % | **+7.0 ± 0.6 %** | 37.88 % | +136 % | 553 ps |

**Eq. (1) and (1a) against the Monte Carlo** (`results/m4_table_checks.json`):
- The tables are integrated exactly as the Monte Carlo samples them.
- With lossless mirror walls, run 38938178392 against (1): z = −1.0, −0.7, −0.5.
- With the nominal wraps against (1a): z = −0.7, +1.7, −0.9 (grease) and +0.2, +0.7
  (air).
- Before (1a), the single-pass design with wraps was 3.8σ below (1). This finding led to
  the correction in derivation 05.

**Fourier order** (`results/ordercheck-38949360857.json`, figure
`docs/figures/m4_ordercheck.png`):
- Both integrated objectives of all five final designs were computed at orders 5, 7, 9
  and 11.
- Order 9 differs from 11 by at most 0.03 % (E) and 0.06 % (single pass), relative.
- So order 9 suffices for air too (decision of 2026-10-16).

### What this means
- **Optimising for early photons works, and optimising for light yield does not help
  timing.**
  - The design optimised with eq. (1) puts more photons into the first 100 ps:
    +2.9 ± 0.4 % with grease and +7.0 ± 0.6 % with air (Monte Carlo).
  - It keeps that lead until two transit times (about 240 ps; key figure, left).
  - The Knapitsch-style reference gives no early gain (−0.3 ± 0.4 %, grease;
    +1.2 ± 0.6 %, air).
  - The design optimised for single-pass extraction loses early photons (−2.1 ± 0.4 %)
    while it collects the most light by 5 ns (+60 %).
- **The two goals trade off** (key figure, right).
  - The early design also raises the light by 5 ns: +26 % (grease) and +136 % (air).
  - That is less than the reference (+46.5 %, +233 %) and the single-pass optimum (+60 %).
  - Choosing a readout for timing is a different choice from choosing it for light
    yield.
- **Why** (`docs/figures/m4_angular_transmission.png`; the near-normal values are in
  `results/m4_table_checks.json`):
  - The early designs keep most of the transmission inside the flat-face escape cone,
    where cos θ, and so the weight in (1), is largest.
  - With grease the early design even adds 0.11 points there.
  - With air it loses 0.37 points between about 20° and 33°, but acts as an
    anti-reflection layer near normal incidence (T = 0.97 against 0.92).
  - On top of that, the early designs open a band of transmission just beyond the
    critical angle.
  - The yield designs trade in-cone light for grazing light, which needs long paths and
    arrives late. The reference with air even blocks near-normal light (T ≈ 0.03 below
    2°).
- **Both early optima** have a period of 0.232–0.234 µm, close to λ/n_LYSO = 0.232 µm,
  and small pillars. Why the optimiser lands there has not been analysed yet.
- **In absolute terms, coupling matters more than the photonic crystal.**
  - Grease gives 13.2 % of the photons by 100 ps, air with the best crystal 5.9 %.
  - The crystal is a correction of a few per cent on top of good optical coupling.
- **Eq. (1) is a reliable fast objective.** Against the Monte Carlo it agrees to within
  2σ in every case once the side-wall losses (1a) are included. Those losses matter
  only for designs that transmit grazing light.

### Open issues
1. **The air optimisation needed three attempts.**
   - First, one start crashed: at small periods some incidences transmit into no order
     at all, and the code asked for a gradient of a constant. Fixed in dbbacf7, with a
     test.
   - That fix skipped the backward pass at such incidences but still built the solver.
     Its autograd graph then stayed in memory, about 20 MB per call (measured on the
     laptop: +1.2 GB for 60 calls, +0.9 MB after the fix). This filled the 7 GB runner
     at step 27, twice (runs 38930990269, 38935236970); the runner was shut down before
     the checkpoint upload. Fixed in c0be7cb, with a test.
   - The start's steps 0–26 were recovered from the job logs, identical in both runs
     (`scripts/recover_optimize_log.py`). The air design is its best step, 21,
     parameters to 4 decimals.
   - Rerun 38950528275 with the fix completed all 30 steps. It reproduces steps 0–26
     exactly. Its best point (step 29) is 0.004 points (0.06 % relative) above step 21
     on the optimisation grid, far inside the Monte Carlo uncertainty.
2. **Lookup-model error.** The Monte Carlo samples the tables with bilinear
   interpolation, masking of closed orders and renormalisation. This changes E(100 ps)
   by up to 0.07 points (0.5 % relative) against direct quadrature of the nodes.
   - That is larger than the Monte Carlo σ.
   - The bare face is exact, so gains relative to it carry this error in addition to
     the quoted statistics.
3. **The optimiser uses (1), not (1a).** It slightly overvalues designs that transmit
   grazing light: 0.004 points for the grease early optimum, 0.095 for the single-pass
   optimum.
4. **Local optimiser, few steps.**
   - The best grease early start was still improving at step 30, by about 0.005 points
     per step.
   - 4–6 starts per case. Better optima may exist.
5. **Angle grid.**
   - φ 5° instead of 2.5° (budget, docs/decisions.md). Grid bounds up to 0.13 points
     (air reference).
   - The optimisation grid (18 × 4) and the order check grid (9 × 2) are too coarse
     for absolute values. On the 9 × 2 grid the air early design even scores below the
     reference. Only the fine tables and the Monte Carlo give final numbers.
6. **Same assumptions as M3.**
   - Single wavelength. Sharp features near θc may make the early designs wavelength
     sensitive, so a check over the LYSO emission band is needed.
   - n_g = n.
   - Ideal photodetector.
   - Wall reflectivity 0.95 assumed. It affects the 5 ns totals, not the early yields.
7. **Fabrication.**
   - Grease early design: pillars 90 nm wide and 217 nm tall at a 234 nm pitch.
   - Air design: 131 nm wide and 266 nm tall at 232 nm.
   - Feasible with electron-beam or nanoimprint lithography, but not checked against
     any process.

### Actions usage so far
- About 1,340 runner-minutes in this repository so far (compute 1,325, CI 18), of which
  about 1,180 in M4.
- Estimated from job durations, each job rounded up to a minute. The billing API needs
  a token scope I do not have.
- The 2,000 free minutes per month are shared by all private repositories of the
  account (Needs Aziz, item 6).

### Next
M5:
- Spectral check of the final designs over the LYSO emission band.
- All figures regenerated by one command.
- README limitations.
- The technical note, written by Aziz.

Optional, if minutes allow:
- A longer early-photon run for grease.
- A single-pass optimisation for air.
- The Knapitsch geometry, once its parameters are read.

## M3 — Monte Carlo pixel model (done 2026-10-16)

### Done
- Derivation 04 (transport, five wall models, readout models, closed-form time-resolved
  expectation for boxes whose sides keep |w|), with predict exercise, 3 check questions
  and answers.
- `montecarlo.py` (vectorised ray tracer), `timing.py` (analytic CDF, figures of merit),
  the `mc` remote job (cases × seeded chunks, oracle residuals in the merge).
- 21 Monte Carlo tests (CI runs the slow ones; laptops run a fast smoke version).

### Numbers produced
All runs: LYSO 3 × 3 × 20 mm, n = 1.81, uniform emission, isotropic, n_g = n (direct
transit 120.8 ps), 1 000 000 photons per case.

Validation against the closed form, eq. (5) of derivation 04
(`results/mc-38902476498.json`, figure `docs/figures/m3_validation_cdf.png`), 200 time
points up to 2 ns, deviation in units of the binomial σ:

| Case | max abs z | Detected by 2 ns, MC | Analytic |
|---|---|---|---|
| Mirror walls, grease readout | 1.49 | 40.77 % | 40.80 % |
| Bare polished walls | 1.01 | 33.56 % | 33.53 % |
| Air-gap diffuse sides (ρ 0.95), mirror back | 1.38 | 40.81 % | 40.80 % |
| Air-gap mirror sides (ρ 0.95), mirror back | 1.07 | 40.85 % | 40.80 % |
| Mirror walls, absorption length 50 mm | 1.50 | 24.50 % | 24.54 % |
| Bare walls, readout into air | 1.87 | 8.29 % | 8.32 % |
| Negative control: contact-diffuse sides | 777 | 78.98 % | 40.80 % |

Wall models with a bare grease readout (`results/mc-38902480681.json`, figure
`docs/figures/m3_wall_models_cdf.png`); reflectivity 0.95 is assumed:

| Other five faces | Detected by 5 ns | by 100 ps |
|---|---|---|
| Mirror in contact | 28.64 % | 11.66 % |
| Bare polished, nothing outside | 33.53 % | 12.77 % |
| Polished + air gap + mirror film | 40.46 % | 12.77 % |
| Polished + air gap + diffuse wrap | 40.47 % | 12.78 % |
| Diffuse in contact | 25.32 % | 9.71 % |

Reference photonic crystal vs bare readout, all five other faces polished + air gap +
mirror film (ρ 0.95) (`results/mc-38903357645.json`, figure
`docs/figures/m3_reference_cdf.png`); statistical σ of each fraction ≤ 0.05 points:

| Readout | Detected by 5 ns | by 50 ps | by 100 ps | by 200 ps | Median arrival |
|---|---|---|---|---|---|
| Bare, grease | 40.42 % | 6.40 % | 12.77 % | 25.30 % | 159 ps |
| Photonic crystal, grease | 59.18 % | 6.40 % | 12.79 % | 25.33 % | 234 ps |
| Bare, air | 16.09 % | 2.74 % | 5.49 % | 10.75 % | 148 ps |
| Photonic crystal, air | 53.46 % | 2.78 % | 5.54 % | 10.90 % | 731 ps |

### What this means
- **The Monte Carlo is validated** against the closed form for every wall model that
  keeps |w|, with and without absorption, for grease and air readout, at 1 million
  photons (all |z| < 2), and the negative control fails as it must.
- **Air-gap wraps cannot rescue trapped light.** A polished face with an air gap
  returns light only into that face's own escape cone (derivation 04, 2d), so an
  air-gap diffuse wrap and an air-gap mirror film give identical results. Only
  contact-diffuse walls redistribute light between cones, and they cost early photons
  (12.8 % → 9.7 % at 100 ps).
- **The reference photonic crystal raises the total light a lot (grease 40.4 % →
  59.2 %, air 16.1 % → 53.5 % by 5 ns) but leaves the early photons unchanged** (grease
  12.77 % vs 12.79 % at 100 ps; air 5.49 % vs 5.54 %). The extra light comes from many
  passes and arrives late: the curves coincide until about 250 ps (two transits).
  For timing, a photonic crystal designed for total light yield does not help. This is
  the case for M4's early-photon objective.

### Open issues
1. **Wall reflectivity is assumed** (0.95): no citable value found for mirror films or
   diffuse wraps. The early-photon yields above do not depend on it (those photons see
   only total internal reflection at the sides); the totals by 5 ns do.
2. **No bulk absorption** in the reference runs (no citable LYSO absorption length), so
   recycled light is lost only at the wraps. The totals by 5 ns are upper bounds in
   that sense; early photons are unaffected.
3. **Coarse LUT (2°, order 7)** for the photonic-crystal cases. Final comparisons will
   use the fine order-9 table.
4. **Ideal photodetector:** every photon entering the grease or air counts, at any angle.
   The photonic crystal sends light out at more oblique angles than the bare face; a
   real detector window would reflect more of it (derivation 04, 2e).
5. **n_g = n** (no LYSO dispersion source): every time is underestimated by the same
   factor n/n_g; comparisons between designs are unaffected.
6. Knapitsch et al. report a 30–60 % light-yield gain for a different crystal
   (1.2 × 2.6 × 5 mm LSO); the +46 % found here for grease is in that range, but the
   comparison is not like for like.

### Actions usage so far
About 165 runner-minutes since 2026-10-16 (CI 14, compute 151; each job rounded up
to a minute), out of 2,000 free minutes per month for a private repository.

### Next
M4: implement the early-photon objective (derivation 05), check it against these
Monte Carlo early yields, optimise period, fill factor and height, then evaluate the
best designs on fine order-9 tables.

## M2 — angle-resolved RCWA for the reference photonic crystal (done 2026-10-16)

All heavy runs on GitHub Actions; summaries committed under `results/`.

### Done
- Derivation 03 (grating orders, C4v symmetry, lookup table, thin-film check, choice of
  the reference design), with predict exercise, 3 check questions and answers.
- Patterned-layer RCWA (`rcwa.solve_phc`), validated in fast tests: thin-film limit
  against the analytic Airy formula (1e-8), energy conservation (1e-9), open orders
  equal to the grating-equation prediction, C4v symmetry (1e-10).
- Lookup table with C4v reduction, bilinear interpolation, masking of closed orders,
  renormalisation, resumable chunked builds (`lut.py`, `jobs.LutJob`). A table merged
  from chunks equals a direct build (test).
- Remote jobs `benchmark`, `convergence`, `lut`; grids sized from the benchmark
  (docs/decisions.md).

### Numbers produced
Reference design: Si₃N₄ pillars (n = 2.0906 at 420 nm, Luke 2015), a = 0.40 µm,
r = 0.12 µm, h = 0.30 µm, on LYSO (n = 1.81) at 420 nm.

Convergence (`results/convergence-38901900762.json`, figure
`docs/figures/m2_convergence.png`): worst relative change of total transmission over
5 incidences, against order 15.

| Order | Grease (n = 1.46) | Air |
|---|---|---|
| 7 | 0.54 % | 1.7 % |
| 9 | 0.30 % | 0.83 % |
| 11 | 0.18 % | 0.43 % |
| 13 | 0.09 % | 0.19 % |

Real-space grid 128 / 256 / 512 at order 9 changes T by at most 0.07 % (grease) and
0.2 % (air). Energy conserved to 9e-13.

Coarse lookup tables, order 7, θ 2° × φ 5° (`results/lut-38901905525.json`,
`results/lut-38901911122.json`, figures `docs/figures/m2_lut_ref_lyso_*_coarse_M7.png`):
single-pass extraction through the readout face, isotropic emission (derivation 03,
eq. 9). Energy conserved to 3e-11.

| Outside medium | Photonic crystal | of which θ < θc | of which θ > θc | Bare face, same grid | Bare face, exact |
|---|---|---|---|---|---|
| Grease (θc = 53.8°) | 21.10 % | 17.40 % | 3.70 % | 19.34 % | 19.20 % |
| Air (θc = 33.5°) | 8.77 % | 4.55 % | 4.22 % | 7.29 % | 7.17 % |

### Open issues
1. **The photonic crystal costs light inside the escape cone.** With grease it
   transmits 17.40 % from inside the cone where the bare face transmits 19.34 %; with
   air 4.55 % against 7.29 %. The trapped light it adds more than compensates on a
   single pass (+1.8 and +1.5 points). This is derivation 03, 2c, now measured. Whether
   it also helps after many passes, and for early photons, is M3's question.
2. **Grid discretisation near θc.** On the 2° grid the bare face integrates to 19.34 %
   against 19.20 % exact (grease) and 7.29 % against 7.17 % (air): about 0.13 points
   from the kink at θc. The photonic-crystal integrals carry a similar error. Final
   numbers will use the 1° grid.
3. **Air needs higher orders.** Order 7 is good to 0.5 % with grease but only to 1.7 %
   with air (θ = 60°, φ = 0° is the worst case), and the air convergence oscillates at
   θ = 60°, φ = 30°. Final air numbers need order 9 or 11.
4. **Runner hardware varies.** The benchmark ran on an AMD EPYC 9V74 (order 13 in
   73 s); the convergence chunks ran on an EPYC 7763 (order 13 in 48 s). Budgets in
   docs/decisions.md use the slower machine.
5. **Reference geometry is not Knapitsch's.** Still waiting for the published lattice
   parameters (Needs Aziz, item 3).

### Next
M3: Monte Carlo of the pixel with the bare face and with these lookup tables.

## 2026-10-16 — Pre-public checklist

| Item | State |
|---|---|
| 1. History audit | Done. Findings below. |
| 2. Emails to noreply, one rewrite | Done for every branch; `main` force-pushed once. Old commits still reachable on GitHub through PR #1, so not satisfied for publication. |
| 3. MIT licence, README "work in progress", disclosure kept | Done in this PR. Disclosure corrected: agents now draft derivations and log design decisions. |
| 4a. Secret scanning push protection | Not available on a private Free repository (API: "Secret scanning is not available for this repository"). To be enabled right after publication, before any other push. |
| 4b. Default workflow token read-only | Done (`default_workflow_permissions: read`, PR approval by Actions disabled). |
| 4c. No pull_request_target, actions pinned | Done: all actions pinned to full commit SHAs (docs/decisions.md). |
| 5. Make public | **Not done**: blocked by item 2 (see Needs Aziz). |
| 6. Branch protection on main | Not possible before publication on GitHub Free. Rule enforced by AGENTS.md until then. |

**Audit findings (all 9 commits, all branches, plus GitHub's PR ref):**
- No tokens, keys or passwords. Patterns searched: GitHub token prefixes, AWS and
  Google keys, Slack tokens, `sk-` keys, private-key headers, and assignments to
  password, secret, token or api_key. Nothing matched.
- No KAUST or Primalight files, data or code. The only mention is the rule line in
  AGENTS.md ("Never ... commit any files ... originating from KAUST / Primalight Lab").
- Personal information: the Gmail address was the author and/or committer email of 8
  of 9 commits, including GitHub's merge commit of PR #1 (author "Aziz Bek"). Fixed by
  the rewrite in our history; still visible through PR #1 on GitHub (blocker above).
  Your name appears in README (disclosure) and pyproject.toml (author), as intended.
  The decision log names the laptop model (i3-1215U, 8 GB); harmless.
- No local paths or user names in any file; figure PNGs carry only
  "Software: Matplotlib version 3.11.2"; result JSONs carry only architecture, Python
  and library versions, UTC times and commit hashes.

## 2026-10-16 — What ran on the laptop for about 50 minutes

All times local (UTC+5). Heavy work was continuous from 00:14 to 00:45 on 16 Oct, plus
about 8 minutes of benchmarks late on 15 Oct.

| When | What | Parameters | Wall time |
|---|---|---|---|
| 15 Oct ~23:40 | Benchmark probe (scratch script) | placeholder pillar lattice, n = 2.5, a = 0.45, r = 0.15, h = 0.30 µm, LYSO→air, θ = 40°, φ = 20°; Fourier orders 3, 5, 7, 9, 11; complex64 and complex128 | ~2 min |
| 15 Oct ~23:50–23:58 | `scripts/benchmark_rcwa.py`, twice | same geometry; orders 3–11, both precisions | ~2.5 min each |
| 16 Oct 00:14–00:22 | `scripts/convergence.py`, run 1 | reference Si₃N₄ lattice (a = 0.40, r = 0.12, h = 0.30 µm), grease n = 1.5 and air; 5 incidences each; orders 3–13; n_grid 256 | stopped after ~8 min |
| 00:23–00:36 | `scripts/convergence.py`, run 2 | as run 1 with grease n = 1.46 (EJ-550); plus n_grid 128/256/512 at order 9 | 12.5 min, complete |
| 00:36–00:39 | `scripts/build_lut.py` (grease, coarse) | 450 incidences (θ 2° × φ 5°) at order 7 | stopped after ~3 min |
| 00:39–00:45 | `scripts/convergence.py`, run 3 | identical to run 2 | stopped by you |
| alongside | pytest (Monte Carlo tests ~1 min per run, 3 runs) and a 1-min Monte Carlo check | N = 60 000 photons per test | ~4 min |

Why it took so long:
- **High Fourier orders are expensive.** Order 13 means 729 harmonics and an
  eigen-decomposition of a 1458 × 1458 complex matrix per solve: 37–50 s each on this
  laptop, 15–20 s at order 11. One convergence run is about 60 such solves.
- **The same study ran three times.** Run 1 was abandoned when the grease index was
  changed from the brief's 1.5 to the sourced 1.46. Run 3 repeated run 2 only to get a
  clean provenance stamp: the stamp was taken when results were saved, after I had
  edited unrelated files, so run 2 was labelled "dirty". That was my process error;
  the stamp is now taken when the code is loaded.
- **All cores, all the time.** torch used 6 threads with no pauses, and Monte Carlo
  tests ran at the same time.
Nothing heavier than the fast test suite will run on the laptop from now on.

The run-2 convergence results are physically valid but will be regenerated on GitHub
Actions before any number is quoted.

## 2026-10-16 — Compute setup

- `.github/workflows/compute.yml`: manual trigger only (job name, config file, optional
  run id to resume). Plan job → matrix of chunks (at most 6 in parallel, each with a
  270-minute self-imposed deadline and a 300-minute hard limit) → merge job. Every
  chunk checkpoints and uploads its artifact even when it fails, so a later run can
  resume it. Artifacts: npz/csv/png plus JSON with parameters, commit, runner, runtime.
- `scripts/remote_job.py`: the driver (`plan`, `run`, `merge`). First job:
  `benchmark` with `configs/benchmark.json`.
- Laptop: tests use 2 threads (`tests/conftest.py`); `@pytest.mark.slow` tests are
  skipped by default and run in CI.
- Until publication the repository is private, so Actions uses the free private quota
  (2,000 minutes per month on GitHub Free) on 2-vCPU runners. Usage is logged per run.

## M1 — analytic baseline + flat-interface RCWA (done 2026-10-15, PR #1)

### Numbers produced
From `results/m1_escape_cone.json` (`scripts/escape_cone.py`), produced before the
grease index was changed to 1.46 (that change is in the M2 branch):

| Case | n1 | n2 | θc [deg] | η₁ | η₁ with Fresnel |
|---|---|---|---|---|---|
| LYSO → air | 1.81 | 1.0 | 33.54 | 8.32 % | 7.17 % |
| LYSO → n = 1.5 | 1.81 | 1.5 | 55.97 | 22.02 % | 20.79 % |
| BGO → air | 2.15 | 1.0 | 27.72 | 5.74 % | 4.69 % |
| BGO → n = 1.5 | 2.15 | 1.5 | 44.24 | 14.18 % | 12.92 % |
| LYSO (Epic, 1.82) → air | 1.82 | 1.0 | 33.33 | 8.22 % | 7.07 % |

Specular LYSO cuboid, fraction of directions that can ever escape: 49.94 % with six
bare faces into air, 63.64 % with n = 1.5 on the readout face and air elsewhere.

From `results/m1_fresnel_vs_rcwa.json`: torcwa at order [0,0] matches analytic Fresnel
R and T, s and p, to at most 3e-14 over 0–89.5°. Figure:
`docs/figures/m1_fresnel_vs_rcwa.png`.

From `results/m1_rcwa_benchmark.json` (laptop, superseded by the remote benchmark):
order 7 about 4 s, order 9 about 12 s, order 11 about 50 s per solve.

### Open issues
1. The brief's 21.7 % for LYSO → n = 1.5 assumes n_LYSO = 1.82; with 1.81 it is 22.0 %.
2. Angle-grid resolution near θc matters: a 0.5° grid gives η₁ = 5.69 % for BGO → air
   against 5.74 % analytic.
3. Order 3 is badly unconverged on the placeholder lattice (0.123 against 0.076 at
   order 11).
4. Laptop benchmark timings varied by up to about 50 % between runs.
5. The first decision-log entry on complex64 was written before measuring and was
   corrected after.

### Next
Run the RCWA benchmark remotely and size the grids from it, then finish M2 (convergence
and lookup tables on Actions), then M3.
