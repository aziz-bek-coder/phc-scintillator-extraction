# Design-decision log

Newest at the bottom. Each entry: date, decision, one-line reason.

## 2026-10-15 — Package name `phcscint`, `src/` layout
Short importable name; `src/` layout so tests run against the installed package, not
the working directory.

## 2026-10-15 — CPU-only toolchain, torch 2.14.1 (CPU wheel), torcwa 0.1.4.2
Aziz's machine: Intel i3-1215U, 8 GB RAM, integrated graphics, no CUDA. torcwa runs on
CPU through PyTorch. Rules out any design that needs a GPU to reproduce.

## 2026-10-15 — Units: µm inside the code, ps for time
Matches torcwa (lengths in the same unit as wavelength) and keeps timing numbers
readable (transport across 20 mm of LYSO is of order 100 ps).

## 2026-10-15 — Sign conventions written once in AGENTS.md
Both agents and all tests refer to AGENTS.md rather than restating conventions.

## 2026-10-15 — Initial commit lands on `main`
There is no other way to create the branch. All later work goes through PR branches.

## 2026-10-15 — Autonomous mode (Aziz's decision)
Agents decide, log here, and continue; Aziz reviews later. Repo created private; no
branch protection (not available on GitHub Free private repos), rule kept in AGENTS.md.
Argon works through Aziz's account with its own git author name.

## 2026-10-15 — Physics gate lifted (Aziz's decision)
Claude writes each derivation itself before the code, keeps predict exercises, adds 3
check questions with answers at the bottom of each derivation. xfail gate converted to
normal tests.

## 2026-10-15 — Milestone dates revised (Aziz's decision)
M3 by 6 Dec, M4 by 20 Dec, pause 21 Dec to 3 Jan, M5 4 to 12 Jan 2027.

## 2026-10-15 — Material constants from Luxium Solutions product pages
One manufacturer per material, as Aziz asked. Luxium (formerly Saint-Gobain Crystals,
the LYSO and BGO supplier most often cited in Crystal Clear papers) states the index
"@ emission max": LYSO n = 1.81 at 420 nm, BGO n = 2.15 at 480 nm. The brief's LYSO
value 1.82 is what Epic Crystal lists; the two vendors differ in the second decimal.
We use 1.81 and keep both values PROVISIONAL until Aziz confirms. Effect on η₁ is
about 0.1 percentage point (see `results/m1_escape_cone.json`).

## 2026-10-15 — Claude commits as author `Claude (agent)` plus Co-authored-by trailer
Satisfies Aziz's rule (own author name) and the Claude Code attribution rule at once.

## 2026-10-15 — Flat-interface RCWA check uses zero Fourier order and one zero-thickness layer
With order [0,0] and homogeneous input/output media, torcwa's S-matrix is exactly the
Fresnel interface, so the check is "does torcwa's s/p decomposition and power
normalisation agree with Born & Wolf", not a convergence test. A zero-thickness
homogeneous layer of the scintillator material is added because torcwa's global
S-matrix path assumes at least one internal layer (the zero-layer path also worked in
a probe, but is not the documented usage).

## 2026-10-15 — complex128 everywhere
Two benchmark runs on the same commit disagreed: in the first, complex64 was 20-30 %
faster; in the second (the one saved in `results/m1_rcwa_benchmark.json`) it was slower
at orders 5-9. Laptop timings vary by up to about 50 % between runs (thermal state,
background load), so complex64 has no demonstrated speed advantage here. Its accuracy
cost is measured: flat-interface deviation from Fresnel about 2e-5 for complex64 vs
about 3e-14 for complex128. Decision: complex128 for everything.

## 2026-10-15 — Fourier-order plan for M2 from the benchmark
Per solve, complex128, 6 threads, placeholder pillar lattice, range over two runs:
order 7 about 4 s, order 9 about 12 s, order 11 about 32-50 s; peak RSS under 1 GB.
Total transmitted s-power changed by 0.8 % from order 7 to 9 and 0.3 % from 9 to 11;
order 3 is 60 % off, so it is never used. Plan: order 7 for optimisation sweeps, order
9 for final evaluation, order 11 only for spot checks, all to be confirmed by the M2
convergence study on the actual reference geometry. A coarse grid of about 300 angles
at order 7 costs about 20 min; a fine grid of about 1700 angles at order 9 about 6 h,
so the fine-grid run must be resumable.

## 2026-10-15 — Small numeric outputs are committed under `results/` as JSON
So that every number quoted in docs has a file with the commit hash that produced it.
Large arrays (lookup tables) stay in `data/` (git-ignored) and are regenerated.

## 2026-10-16 — Grease index 1.46 (Eljen EJ-550) instead of the brief's 1.5
Numbers must come from a source; 1.5 had none. EJ-550 lists 1.46 and Luxium BC-631
lists 1.465. The brief's 1.5 is kept as `N_GREASE_BRIEF` only to reproduce the brief's
21.7 % check. A first convergence run with 1.5 was stopped and redone with 1.46.

## 2026-10-16 — Pillar material Si3N4 (Luke 2015), not TiO2
Knapitsch et al. used silicon nitride (paper abstract). Two independent Si3N4 sources
agree to 1.4 % at 420 nm (Luke 2.091, Philipp 2.062), while TiO2 thin-film records
disagree by 0.3 in n (2.29 vs 2.62) and one shows absorption at 420 nm. TiO2 can be
revisited in M4 as a higher-contrast option once a deposition-matched source exists.

## 2026-10-16 — Reference design is "Knapitsch-style", not a replica
The Knapitsch geometry is not in the abstracts, and the thesis PDF is copy-protected,
so it was not text-extracted. Reference: square lattice of Si3N4 pillars, a = 0.40 µm,
r = 0.12 µm (fill factor 0.28), h = 0.30 µm. Period chosen from the grating equation
so that order (−1, 0) maps the middle of the trapped band into the escape cone
(derivation 03, 2l); radius and height are typical single-etch values, not optimised.
Replace with the published geometry if Aziz reads it from the thesis.

## 2026-10-16 — Pillars sit directly on LYSO and are surrounded by the outside medium
No residual Si3N4 layer under the pillars. Simplest structure that M4 can optimise
with three parameters (period, radius, height).

## 2026-10-16 — Light is treated as unpolarised at every interaction
LUT stores the unpolarised order powers, eq. (7) of derivation 03. Bias discussed in
derivation 03, 2g. Tracking polarisation is a possible extension, not planned.

## 2026-10-16 — LUT grids and storage
θ on a midpoint grid (no solve at exactly 90°, where the input kz vanishes), φ on an
inclusive grid over the C4v wedge [0°, 45°]. Coarse: 2° × 5° (450 solves). Fine: 1° ×
2.5° (1710 solves). Stored order window |m|, |n| ≤ ceil(2 n1 / g) = 4 for the
reference (81 orders), which holds every order that can propagate in LYSO. Cached in
`data/lut/` (git-ignored) under a hash of the full configuration; builds checkpoint
every 60 s and resume.

## 2026-10-16 — The M1 benchmark overstated solve times
`scripts/benchmark_rcwa.py` timed the solve plus a Python loop calling `S_parameters`
once per order (529 calls at order 11). With vectorised extraction (`rcwa.solve_phc`)
the extraction step costs about 7 ms (remote benchmark below). The laptop numbers are
superseded by `results/benchmark-38798175139.json`.

## 2026-10-16 — Heavy computation moves to GitHub Actions (Aziz's decision)
The laptop overheated during about 50 minutes of RCWA runs (docs/status.md). Laptop:
edit code, fast tests with 2 threads, plotting downloaded results. Everything else runs
through `.github/workflows/compute.yml`.

## 2026-10-16 — Licence MIT (Aziz's decision)
`LICENSE` added; README marked "work in progress".

## 2026-10-16 — One history rewrite to the noreply address (approved by Aziz)
All author and committer emails now use `262705928+aziz-bek-coder@users.noreply.github.com`,
including the agents' commits. Old-to-new commit map in `docs/history-rewrite.md`, so
provenance stamps written before the rewrite stay traceable. A local bundle of the old
history was kept outside the repository and is not pushed anywhere.

## 2026-10-16 — Publication deferred until PR #1's ref is gone
GitHub keeps `refs/pull/1/head` at the old commit `d096fce`, and the API still returns
the Gmail address for `d096fce`, `8f1c7c4` and the old merge commit `0308772`.
Publishing now would expose it. Options for Aziz are in docs/status.md. Meanwhile the
private repository's free Actions quota is used, on 2-vCPU runners.

## 2026-10-16 — Actions pinned to full commit SHAs
Tags can be moved; SHAs cannot. Pinned (latest releases on 2026-10-16):
actions/checkout 3d3c42e5aac5ba805825da76410c181273ba90b1 (v7.0.1),
actions/setup-python 5fda3b95a4ea91299a34e894583c3862153e4b97 (v7.0.0),
actions/upload-artifact cf430e030ddbb5b0abf93d22962f4752f3646cd9 (v7.0.2),
actions/download-artifact 9000827ccba6bdab643e8b6fd33ac0654aef8333 (v8.0.2).
Checkout runs with `persist-credentials: false`; workflow inputs reach shell steps only
through environment variables, never by direct expression interpolation.

## 2026-10-16 — Workflow permissions
Repository default token is read-only. `ci.yml` asks for `contents: read`;
`compute.yml` asks for `contents: read` and `actions: read` (needed to download an
earlier run's artifacts when resuming). No workflow uses `pull_request_target` or a
schedule.

## 2026-10-16 — CI triggers: pull requests and pushes to main only
Previously every branch push ran CI and the pull request ran it again. Halves CI minutes.
CI runs the full suite including `@pytest.mark.slow` tests.

## 2026-10-16 — Remote job design (`scripts/remote_job.py`)
`plan` turns a config into a matrix of chunks; `run` executes one chunk with a
checkpoint file and a 270-minute self-imposed deadline (hard limit 300 minutes) and
writes `chunk.json` (config, commit, runner CPU, runtime per segment, complete flag);
`merge` combines chunks into `summary.json` plus csv/png/npz. A chunk that hits its
deadline exits cleanly and its artifact is uploaded, so `resume_run_id` can continue it.
At most 6 chunks run in parallel. Configs live in `configs/` and nowhere else.

## 2026-10-16 — Results layout
Downloaded artifacts go to `results/<job>/<run-id>/` and are git-ignored. Small summary
JSONs at the top level of `results/` and final figures in `docs/figures/` are committed.

## 2026-10-16 — Laptop test settings
`tests/conftest.py` sets OMP_NUM_THREADS = 2 (unless already set) before importing
torch and calls `torch.set_num_threads`. `pytest` skips `@pytest.mark.slow` by default
(`-m 'not slow'` in pyproject); CI overrides with `-m "slow or not slow"`.

## 2026-10-16 — Repository requires SHA-pinned actions
Enabled the Actions setting `sha_pinning_required` (checklist item 4, "pin third-party
actions"), so a workflow that references an action by tag fails instead of running.

## 2026-10-16 — Grids sized from the remote benchmark (run 38798175139)
Runner: GitHub-hosted, 2 vCPU AMD EPYC 9V74 (private-repository runner), torch on 2
threads. Reference pillar lattice, θ = 60°, φ = 30°, complex128, n_grid 256, median of
3 repeats (spread under 1 %); numbers in `results/benchmark-38798175139.json`, figure
`docs/figures/benchmark_rcwa_remote.png`.

| Order M | Harmonics | Forward solve | Backward pass |
|---|---|---|---|
| 5 | 121 | 0.44 s | 0.29 s |
| 7 | 225 | 2.45 s | 1.76 s |
| 9 | 361 | 9.5 s | 7.2 s |
| 11 | 529 | 28.6 s | not measured |
| 13 | 729 | 73 s | not measured |

Time grows as (harmonics)^2.89 for M ≥ 7; extraction of all order powers costs 7 ms;
peak memory 1.7 GB at M = 13; energy conserved to 4e-13. Choices, per runner:
- Convergence study: orders 3–15 at 10 incidences plus a grid check, about 47
  runner-minutes, 4 chunks. Order 15 is added so that order 13 has an error estimate.
- Coarse LUT, order 7 (2° × 5°, 450 solves): 18 runner-minutes, 2 chunks. For M3
  development and M4 screening.
- Fine LUT, order 9 (1° × 2.5°, 1710 solves): 4.5 runner-hours, 4 chunks of about
  70 minutes. For the final evaluation of each design.
- Order 11 on the fine grid would take 13.6 runner-hours: not planned; order-11 spot
  checks only.
- M4 gradient steps at order 5 with 72 incidences: 0.9 runner-minutes per step, so 4
  starts × 50 steps ≈ 3 runner-hours in 4 chunks; candidates re-checked at order 7
  (about 5 minutes per evaluation) before the fine-grid Monte Carlo.
Orders used for final numbers are confirmed by the remote convergence study. Public
4-vCPU runners should be faster; rerun the benchmark after publication.

## 2026-10-16 — Job code in `src/phcscint/jobs.py`; laptop-made M2 results removed
The benchmark, convergence and lut jobs live in the package (standard-library imports at
module level, so the plan step needs no installation); `scripts/remote_job.py` is the
command line. `scripts/convergence.py` and `scripts/build_lut.py` were removed because
their logic moved into the jobs, and the laptop-made `results/m2_convergence.json` and
its figure were removed: those numbers will come from the remote convergence job.
Configs name materials ("LYSO", "grease", "Si3N4-Luke2015") instead of copying numbers.

## 2026-10-16 — Fourier orders for final numbers, from the convergence study
Convergence run 38901900762 (results/convergence-38901900762.json), worst case over 5
incidences against order 15: grease 0.54 % at order 7, 0.30 % at 9, 0.18 % at 11; air
1.7 % at 7, 0.83 % at 9, 0.43 % at 11. Decision: order 7 coarse tables for development
and screening; order 9 fine tables for final grease numbers (target ≤ 0.3 %); order 11
for any final air number (≤ 0.5 %). The real-space grid stays at 256 × 256 (doubling
it changes T by ≤ 0.2 %).

## 2026-10-16 — Branches cited by remote runs are merged, not rebased
Every remote result records the commit that produced it. Rebasing a branch after its
commits were used by a run would orphan those hashes. Such branches are merged into
main with a merge commit (and main is merged into them when needed), never rebased.
This overrides the "rebase before opening a PR" rule in AGENTS.md for those branches.

## 2026-10-16 — Runner hardware varies between jobs
GitHub's 2-vCPU runners came with different CPUs: AMD EPYC 9V74 (benchmark, order 13 in
73 s) and EPYC 7763 (convergence, order 13 in 48 s). Budgets use the slower machine;
timings in result files are informative only, never a result.

## 2026-10-16 — Monte Carlo conventions (M3)
- Seeds: chunk part p of case c uses `SeedSequence([seed, c, p])`; every part is an
  independent, reproducible stream.
- Time cut-off 5 ns for efficiency numbers ("detected by 5 ns"); validation runs use
  2 ns because the closed form holds at any time.
- Nominal wall model for design comparisons: all five non-readout faces polished, thin
  air gap, specular mirror film. It is the common choice for timing pixels and the one
  under which early photons are insensitive to the wrap (they see only total internal
  reflection at the sides).
- Wall reflectivity 0.95 is an assumption: no citable value was found for mirror films
  or diffuse wraps (searched 2026-10-16; publisher pages paywalled, 3M site timed out).
  Early-photon yields do not depend on it; totals by 5 ns do.
- No bulk absorption in design comparisons until a LYSO absorption length is cited.

## 2026-10-16 — Pull requests are merged by fast-forward, never by a GitHub merge commit
`gh pr merge` lets GitHub author the merge commit with the account's primary email,
which put the Gmail address on the merge commits of PRs #2 and #3. Asking for the
noreply address (`gh pr merge --author-email ...`) was rejected by GitHub ("Invalid
email address"), apparently because the account's email privacy setting is off. So
merges are fast-forwards of the CI-green PR branch after merging `main` into it (agent
author, noreply email); GitHub marks the PR merged (PR #4 was merged this way). No
commit hashes change, so result provenance stays valid.

## 2026-10-16 — M4 final tables: order 9 on θ 1° × φ 5°; integrated order check instead of order 11
- The fine tables for the final M4 comparison use order 9 on θ 1° (midpoints) × φ 5°
  (inclusive): 900 solves, about 2.4 runner-hours each in 4 chunks. The M2 sizing was
  1° × 2.5° (1710 solves, 4.5 h). Five final tables (reference and optimised designs,
  grease and air) on that grid would need about 22 runner-hours, more than the private
  repository's remaining monthly Actions minutes (about 590 of 2000 used by 16 October,
  estimated from job durations). The angle-grid error is estimated by subsampling the
  tables (φ 5° → 15°, θ 1° → 3°) and is reported with the results.
- Air numbers stay at order 9, not 11 as decided in M2: an order-11 fine table would
  take about 7 runner-hours. The M2 criterion was the worst single incidence; the
  quantities reported are integrals over angle, which converge faster (the order-7
  rechecks of the grease optimisation runs moved the integrated objectives by at most
  1.2e-4, relative, against 0.54 % at the worst incidence). Instead, an order check
  evaluates both integrated objectives of every final design at orders 7, 9 and 11 on a
  9 × 2 angle grid, and its size is quoted next to the numbers.

## 2026-10-17 — Published as a fresh repository; old one kept as a private archive
GitHub keeps the refs of merged pull requests, and users cannot delete them. In the
old repository they reached commits carrying Aziz's personal address, so making it
public would have exposed the address, whatever was done to `main`.

Aziz chose the "new repository" option (2026-10-17):
- rename the old repository to `phc-scintillator-extraction-archive` (private);
- publish the rewritten history (docs/history-rewrite.md) under the original name.

Remote runs before this date stay in the archive. Their numbers are in
`results/*.json`; hashes are mapped in docs/history-rewrite.md.

Branch protection on `main` requires a pull request and the `test` check, with no
approvals and no admin enforcement. Admin enforcement is off so that the owner account
can keep merging by fast-forward after green CI. Merges done by GitHub would author a
commit with the account's primary email until "Keep my email addresses private" is
enabled.

## Open
- Group index of LYSO at 420 nm: no dispersion source found (docs/references.md);
  M3 uses n_g = n and states the bias.
- Wavelength at which Epic Crystal quotes n = 1.82 for LYSO is not stated on its page.
- Knapitsch geometry from the thesis, to replace the Knapitsch-style reference.
- Publication: waiting on Aziz (docs/status.md).
