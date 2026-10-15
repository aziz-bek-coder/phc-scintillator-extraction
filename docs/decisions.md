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

## Open
- Licence for the public release: MIT or Apache-2.0. Decide by M5.
- Group index of LYSO at 420 nm: needs a dispersion source before M3.
- Wavelength at which Epic Crystal quotes n = 1.82 for LYSO is not stated on its page.
