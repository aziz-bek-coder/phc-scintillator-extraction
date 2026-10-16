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
2. **Material constants are PROVISIONAL.** LYSO n = 1.81 at 420 nm, BGO n = 2.15 at
   480 nm (Luxium product pages), grease n = 1.46 (Eljen EJ-550). Please confirm.
3. **References not content-verified** beyond abstracts: Knapitsch 2012 (geometry not
   read; thesis PDF is copy-protected), Carr Delgado 2024.
4. **Argon** has not started. No independent cross-check exists yet.

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
