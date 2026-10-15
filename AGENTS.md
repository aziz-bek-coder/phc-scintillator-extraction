# Rules for coding agents (Claude and Argon)

Owner and sole reviewer/merger: Aziz (`aziz-bek-coder`). Agents never merge.

## Branching and PRs
- Never commit to or push `main`. One branch prefix per agent: `claude/<topic>` and
  `argon/<topic>`. One topic per branch.
- Small PRs: one module or one fix, ideally under 300 changed lines, always with tests.
- Every PR description states: what changed, which equation or derivation it implements
  (link to `docs/derivations/`), how it was tested, and any number it produces.
- CI (`pytest` on CPU, `ruff check`) must be green before review is requested.
- Rebase on `main` before opening a PR; never force-push a branch someone else has reviewed.

## Module ownership (two agents never edit the same file at the same time)
| Path | Owner |
|---|---|
| `src/phcscint/analytic.py`, `fresnel.py`, `materials.py` | Claude |
| `src/phcscint/rcwa.py`, `lut.py` | Claude |
| `src/phcscint/montecarlo.py`, `timing.py` | Claude |
| `src/phcscint/optimize.py` | Claude |
| `scripts/`, `docs/figures/`, `tests/` (except `tests/xcheck/`) | Claude |
| `src/phcscint/xcheck/` (independent re-implementation: escape cone, Fresnel, bare-face MC) | Argon |
| `tests/xcheck/` (tests comparing the two implementations) | Argon |
| Review of every Claude PR | Argon |
| `README.md`, `PLAN.md`, `AGENTS.md`, `docs/decisions.md`, `docs/derivations/` | Aziz (agents propose edits in PRs) |

Argon's cross-checks must not import from the Claude-owned modules they check; they use
only numpy and scipy. Shared fixtures live in `tests/conftest.py` (Claude). If an agent
needs a change in a file it does not own, it opens an issue or asks Aziz.

## Tests required
- No physics function is merged without a test against an analytic value or a
  conservation law (for example R + T = 1), with the tolerance written in the test.
- Monte Carlo tests fix the RNG seed and compare to an analytic expectation with a
  stated statistical tolerance (state N and the expected standard error).
- A test may be `xfail(strict=True)` only while the corresponding derivation in
  `docs/derivations/` is not yet written.

## Units and sign conventions (stated once, here)
- Lengths in **micrometres (µm)** inside the code; wavelengths in µm; times in **ps**.
  Pixel dimensions in docs may be quoted in mm, but functions take µm.
- Refractive indices are complex, `n + i k` with **k ≥ 0 for loss** (time dependence
  `exp(-iωt)`). Check that torcwa uses the same convention before adding a material.
- Angles: polar angle θ measured from the readout-face normal; +z points out of the
  crystal (from scintillator into the outside medium); azimuth φ from the x lattice axis.
- Angle-resolved quantities are tabulated on the **inside** (scintillator) side:
  (θ_in, φ_in, polarisation) → power fractions into each transmitted and reflected order.
- "Trapped" means `n1 sin θ > n2`, i.e. beyond the critical angle of the flat face.
- Fresnel amplitude coefficients, light going from n1 (angle θ1) to n2 (angle θ2):
  `r_s = (n1 cos θ1 − n2 cos θ2) / (n1 cos θ1 + n2 cos θ2)`,
  `r_p = (n2 cos θ1 − n1 cos θ2) / (n2 cos θ1 + n1 cos θ2)`.
  This is the Born & Wolf / Hecht convention; at normal incidence r_p = −r_s.
- Reflectance R = |r|²; transmittance T = Re(n2 cos θ2) / Re(n1 cos θ1) · |t|².
- Transport time t = n_g L / c with n_g the group index. Assumption: n_g ≈ n at the
  emission peak unless `docs/decisions.md` records otherwise.

## Citations and numbers (honesty rules)
- No number appears in a doc unless a script in `scripts/` produces it or a cited
  paper or datasheet that Aziz can open contains it. Scripts print the number and the
  git commit hash.
- Every reference goes in `docs/references.md` with DOI (or arXiv ID), verified on the
  publisher's page or arXiv, with the date verified. Never invent or guess a citation.
- If a result is surprising or a check fails, say so in the PR. Do not tune tolerances
  to make tests pass.

## Teaching protocol
- Before each physics module Aziz writes the derivation in `docs/derivations/`. Agents
  may build scaffolding, tests and tooling before that, but not the physics core.
- After each module the implementing agent explains the code in terms of the equations
  and asks Aziz three understanding-check questions.
- Aziz writes the technical note. Agents review it for correctness and clarity only.

## Never
- Commit secrets, tokens, `.env` files, or anything from `~/.ssh`.
- Commit any files, data, designs or code originating from KAUST / Primalight Lab.
- Commit large binary outputs (over 1 MB); regenerate figures from scripts instead.
