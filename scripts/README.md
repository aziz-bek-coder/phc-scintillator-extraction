# scripts/

Every number or figure quoted in the docs is produced here. Each script prints the
values it produces together with the git commit hash, and saves figures to
`docs/figures/`. Planned:

- `escape_cone.py` (M1) — η₁ for LYSO→air, LYSO→grease, BGO→air.
- `fresnel_vs_rcwa.py` (M1) — flat interface: analytic Fresnel vs torcwa, R + T check.
- `convergence.py` (M2) — Fourier-order convergence plot for the reference PhC.
- `build_lut.py` (M2) — angle-resolved lookup table for the Monte Carlo.
- `run_pixel_mc.py` (M3) — extraction efficiency and transport-time CDF.
- `optimize.py` (M4) — gradient-based design.
- `key_figure.py` (M5) — bare vs reference vs optimised, LYSO.
