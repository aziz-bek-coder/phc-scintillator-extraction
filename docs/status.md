# Status

Updated by the agents at the end of each milestone. Newest milestone first.
Every number below comes from a file in `results/` (named next to it), produced by
the script named there, at the commit recorded inside that file.

## Needs Aziz (approval or confirmation)
- **Material constants are PROVISIONAL.** LYSO n = 1.81 at 420 nm and BGO n = 2.15 at
  480 nm, from the Luxium Solutions product pages (`docs/references.md`). Please open
  both pages and confirm, or pick another datasheet.
- **References not content-verified.** Knapitsch 2012 and Carr Delgado 2024: DOIs and
  metadata checked, but nobody has read the cited claims on the papers yet. Nothing
  from them is quoted in the repo.
- **Argon** has not started. No cross-check of `analytic.py` or `fresnel.py` exists yet.
- Nothing has hit the "never without approval" list so far.

## M1 — analytic baseline + flat-interface RCWA (done 2026-10-15)

### Done
- Derivations 01 (escape cone, trapping) and 02 (Fresnel, flat-interface RCWA), each
  with a predict exercise, three check questions and answers at the bottom.
- `analytic.py`: critical angle, η₁, trapped mask, specular reflection, cone-overlap
  test, closed-form escapable fraction of a specular cuboid.
- `fresnel.py`: r and t for s and p, power coefficients, total internal reflection
  branch, Brewster angle, Fresnel-weighted single-pass escape.
- `rcwa.py`: zero-order torcwa solve of a flat interface.
- The physics-gate xfails are now normal tests: 102 tests pass locally.
- RCWA benchmark against Fourier order; grid plan logged in `docs/decisions.md`.

### Numbers produced
From `results/m1_escape_cone.json` (`scripts/escape_cone.py`):

| Case | n1 | n2 | θc [deg] | η₁ | η₁ with Fresnel |
|---|---|---|---|---|---|
| LYSO → air | 1.81 | 1.0 | 33.54 | 8.32 % | 7.17 % |
| LYSO → grease | 1.81 | 1.5 | 55.97 | 22.02 % | 20.79 % |
| BGO → air | 2.15 | 1.0 | 27.72 | 5.74 % | 4.69 % |
| BGO → grease | 2.15 | 1.5 | 44.24 | 14.18 % | 12.92 % |
| LYSO (Epic, 1.82) → air | 1.82 | 1.0 | 33.33 | 8.22 % | 7.07 % |

Specular LYSO cuboid, fraction of directions that can ever escape: 49.94 % with six
bare faces into air, 63.64 % with grease on the readout face and air elsewhere.

From `results/m1_fresnel_vs_rcwa.json` (`scripts/fresnel_vs_rcwa.py`): torcwa at order
[0,0] matches analytic Fresnel R and T, s and p, to at most 3e-14 over 0–89.5° for
LYSO→air, LYSO→grease and BGO→air. Cross-polarised terms are zero. Figure:
`docs/figures/m1_fresnel_vs_rcwa.png`.

From `results/m1_rcwa_benchmark.json` (`scripts/benchmark_rcwa.py`), placeholder
pillar lattice, complex128: order 7 about 4 s, order 9 about 12 s, order 11 about 50 s
per solve; peak RSS under 1 GB.

### Validation checklist (brief, "Validation before optimisation")
- [x] Flat interface reproduces Fresnel s and p: `tests/test_rcwa_flat.py`, tolerance 1e-6.
- [x] R + T = 1 for lossless materials: same tests, and `tests/test_fresnel.py` at 1e-12.
- [ ] Convergence in Fourier orders with plot: M2 (benchmark only so far).
- [x] Unpatterned face matches the escape-cone estimate: brief's 8.2 / 21.7 / 5.7 %
      reproduced to 0.1 point at n_LYSO = 1.82 (`test_escape_fraction_brief_values`).
- [ ] Bare-face Monte Carlo vs analytic: M3.

### Open issues
1. **The brief's 21.7 % for LYSO → grease assumes n = 1.82.** With Luxium's 1.81 it is
   22.0 %. The vendor spread in n moves η₁ by up to 0.3 percentage points. Not a bug;
   it means the second decimal of n matters for grease coupling.
2. **Angle-grid resolution near θc matters.** Integrating the RCWA result on a 0.5°
   grid gives η₁ = 5.69 % for BGO → air against 5.74 % analytic. The difference is the
   step at the critical angle. The M2 lookup table needs a finer step near θc or
   integration that knows where θc is.
3. **Order 3 is badly unconverged** on the placeholder lattice: transmitted power 0.123
   against 0.076 at order 11. Never use order 3, not even for quick sweeps.
4. **Benchmark timings vary by up to about 50 %** between runs on this laptop. The grid
   sizes in `docs/decisions.md` use the slower run.
5. The first version of `docs/decisions.md` stated a complex64 conclusion before it
   was measured. It was corrected in the same PR after measurement.

### Next
M2: derivation 03 (k∥ + G, which orders propagate), reference photonic crystal on LYSO,
Fourier-order convergence study with a plot, C4v-reduced angle sweep, cached and
resumable lookup table.
