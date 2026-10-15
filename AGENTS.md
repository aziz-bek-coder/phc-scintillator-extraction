# Rules for coding agents (Claude and Argon)

Owner: Aziz (`aziz-bek-coder`). Both agents work through Aziz's GitHub account.
Mode since 2026-10-15: agents work autonomously, decide and log decisions in
`docs/decisions.md`, and report in `docs/status.md`. Aziz reviews afterwards.

## Identity
- Each agent commits under its own author name: `Claude (agent)` or `Argon (agent)`
  (`git commit --author="Claude (agent) <noreply@anthropic.com>"`), or adds a
  `Co-authored-by:` trailer. Aziz commits under his own name.
- Branch prefixes: `claude/*`, `argon/*`, `aziz/*`.

## Branching and PRs
- Never commit to or push `main` directly. GitHub branch protection is not available on
  this private Free-plan repo, so this rule is enforced by discipline and by review.
- One topic per branch; one milestone (or one fix) per PR, ideally under 300 changed
  lines of code, always with tests.
- Every PR description states: what changed, which equation or derivation it implements
  (link to `docs/derivations/`), which tests cover it, any number it produces, and open
  doubts. This is the "review summary".
- CI (`pytest` on CPU, `ruff check`) must be green before merge.
- An agent may merge its own PR into `main` only after CI passes and the review summary
  is written. Argon reviews Claude's PRs when available; a review is not a merge gate.
- Rebase on `main` before opening a PR. Never force-push or rewrite history.

## Never, without Aziz's explicit approval (stop and note it in `docs/status.md`)
- Make the repo public.
- Change repo settings or collaborators.
- Force-push or rewrite history.
- Delete files or branches you did not create.
- Do anything that costs money (paid compute, paid APIs, domains, and so on).

## Module ownership (two agents never edit the same file at the same time)
| Path | Owner |
|---|---|
| `src/phcscint/analytic.py`, `fresnel.py`, `materials.py` | Claude |
| `src/phcscint/rcwa.py`, `lut.py` | Claude |
| `src/phcscint/montecarlo.py`, `timing.py` | Claude |
| `src/phcscint/optimize.py` | Claude |
| `scripts/`, `results/`, `docs/figures/`, `tests/` (except `tests/xcheck/`) | Claude |
| `docs/derivations/`, `docs/status.md`, `docs/decisions.md` | Claude writes; Aziz annotates |
| `src/phcscint/xcheck/` (independent re-implementation: escape cone, Fresnel, bare-face MC) | Argon |
| `tests/xcheck/` (tests comparing the two implementations) | Argon |
| Review of every Claude PR | Argon |
| `README.md`, `PLAN.md`, `AGENTS.md` | Aziz (agents propose edits in PRs) |

Argon's cross-checks must not import from the Claude-owned modules they check; they use
only numpy and scipy. Shared fixtures live in `tests/conftest.py` (Claude). If an agent
needs a change in a file it does not own, it opens an issue or notes it in `docs/status.md`.

## Compute constraints (Aziz's laptop: Intel i3-1215U, 8 GB RAM, CPU only)
- Benchmark before sizing: one RCWA solve timed against Fourier order
  (`scripts/benchmark_rcwa.py`); grids are sized from that measurement.
- Use C4v symmetry of the square lattice: for unpolarised light φ runs over 0–45° only.
- Coarse angle grid for optimisation, fine grid for final evaluation.
- Cache lookup tables to disk; long runs must be resumable.
- Keep peak RAM under 4 GB.
- Colab only if a step truly cannot run locally, and log it in `docs/decisions.md`.

## Tests required
- No physics function is merged without a test against an analytic value or a
  conservation law (for example R + T = 1), with the tolerance written in the test.
- Monte Carlo tests fix the RNG seed and compare to an analytic expectation with a
  stated statistical tolerance (state N and the expected standard error).

## Units and sign conventions (stated once, here)
- Lengths in **micrometres (µm)** inside the code; wavelengths in µm; times in **ps**.
  Pixel dimensions in docs may be quoted in mm, but functions take µm.
- Refractive indices are complex, `n + i k` with **k ≥ 0 for loss**, time dependence
  `exp(-iωt)`. torcwa states the same convention (`exp(-jωt)`), so `eps = (n + ik)²`
  can be passed directly.
- Angles: polar angle θ measured from the readout-face normal; +z points out of the
  crystal (from scintillator into the outside medium); azimuth φ from the x lattice axis.
- Angle-resolved quantities are tabulated on the **inside** (scintillator) side:
  (θ_in, φ_in, polarisation) → power fractions into each transmitted and reflected order.
- "Trapped" means `n1 sin θ > n2`, i.e. beyond the critical angle of the flat face.
- Fresnel amplitude coefficients, light going from n1 (angle θ1) to n2 (angle θ2):
  `r_s = (n1 cos θ1 − n2 cos θ2) / (n1 cos θ1 + n2 cos θ2)`,
  `r_p = (n2 cos θ1 − n1 cos θ2) / (n2 cos θ1 + n1 cos θ2)`,
  `t_s = 2 n1 cos θ1 / (n1 cos θ1 + n2 cos θ2)`,
  `t_p = 2 n1 cos θ1 / (n2 cos θ1 + n1 cos θ2)`.
  Born & Wolf / Hecht convention; at normal incidence r_p = −r_s. Beyond the critical
  angle `cos θ2 = +i sqrt((n1/n2)² sin²θ1 − 1)` (decaying evanescent wave).
- Reflectance R = |r|²; transmittance T = Re(n2 cos θ2) / (n1 cos θ1) · |t|².
- Transport time t = n_g L / c with n_g the group index. Assumption: n_g ≈ n at the
  emission peak unless `docs/decisions.md` records otherwise.

## Citations and numbers (honesty rules)
- No number appears in a doc unless a script in `scripts/` produces it (saved under
  `results/` with the git commit hash) or a cited source that Aziz can open contains it.
- Every reference goes in `docs/references.md` with DOI (or arXiv ID, or manufacturer
  URL for datasheets), with the date and method of verification. Never invent or
  guess a citation.
- If a result is surprising or a check fails, record it under "Open issues" in
  `docs/status.md`. Do not tune tolerances to make tests pass.

## Teaching protocol
- For each physics module the implementing agent first writes the derivation in
  `docs/derivations/`: full steps, assumptions, and which way each approximation biases
  the result. The code then follows the derivation.
- Each derivation keeps a "Predict" exercise and ends with 3 check questions; answers
  go in a separate section at the bottom. Aziz works through them later.
- Aziz writes the technical note. Agents review it for correctness and clarity only.

## Never
- Commit secrets, tokens, `.env` files, or anything from `~/.ssh`.
- Commit any files, data, designs or code originating from KAUST / Primalight Lab.
- Commit large binary outputs (over 1 MB); regenerate figures from scripts instead.
