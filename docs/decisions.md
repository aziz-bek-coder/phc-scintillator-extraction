# Design-decision log

Newest at the bottom. Each entry: date, decision, why, what it rules out.

## 2026-10-15 — Package name `phcscint`, `src/` layout
Short importable name; `src/` layout so tests run against the installed package, not
the working directory.

## 2026-10-15 — CPU-only toolchain, torch 2.14.1 (CPU wheel), torcwa 0.1.4.2
Aziz's machine: Intel i3-1215U, 8 GB RAM, integrated graphics, no CUDA. torcwa runs on
CPU through PyTorch; GPU is optional. Consequence: keep Fourier-order counts and
angle grids modest, cache RCWA lookup tables to disk, and let CI run everything on CPU.
Rules out any design that needs a GPU to reproduce.

## 2026-10-15 — Units: µm inside the code, ps for time
Chosen to match torcwa (lengths in the same unit as wavelength) and to keep timing
numbers readable (transport times across a 20 mm crystal are tens to hundreds of ps).

## 2026-10-15 — Sign conventions written once in AGENTS.md
Both agents and all tests refer to AGENTS.md rather than restating conventions.

## 2026-10-15 — Teaching gate on physics modules
The escape-cone and Fresnel functions are stubs (`NotImplementedError`) with
`xfail(strict=True)` tests until Aziz writes
`docs/derivations/01-escape-cone-and-trapping.md`. This keeps the "derive before
implement" rule mechanical rather than a matter of discipline.

## 2026-10-15 — Initial commit lands on `main`
There is no other way to create the branch. All later work goes through
`claude/*` and `argon/*` branches and PRs.

## Open
- Licence for the public release (~10 Jan 2027): MIT or Apache-2.0. Decide by M5.
- Wall model to validate first in M3: specular is the only one with a closed-form
  expectation (trapped rays stay trapped), so start there.
- Group index of LYSO at 420 nm: needs a dispersion source before M3.
