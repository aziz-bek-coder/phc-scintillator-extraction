# Hand derivations

Written by Aziz before the corresponding physics module is implemented (AGENTS.md,
"Teaching protocol"). Each file has three parts:

1. **Predict** (written before any code runs): the setup, the result I expect, and why.
2. **Derivation**: the full derivation, with every assumption named.
3. **Check** (filled in after the module exists): the number the repo script produces,
   whether it matched the prediction, and what I learned if it did not.

Index:
- `01-escape-cone-and-trapping.md` — escape fraction through one face; why trapped
  rays stay trapped in an ideal cuboid (gates `phcscint.analytic`).
- `02-fresnel-and-flat-rcwa.md` — (M1) Fresnel coefficients, R + T = 1, what a
  zero-order RCWA of a flat interface must reproduce.
- `03-grating-orders.md` — (M2) k∥ + G, which orders propagate, trapped-mode escape.
- `04-monte-carlo-expectations.md` — (M3) bare-face expectation per wall model,
  transport time from path length.
- `05-objective.md` — (M4) the differentiable early-arrival objective.
