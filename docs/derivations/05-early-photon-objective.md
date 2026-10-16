# 05 — A differentiable objective for early photons, and the optimisation

Written by Claude (agent). Code: `src/phcscint/optimize.py`; remote jobs `optimize` and
`ordercheck` in `src/phcscint/jobs.py` (configs `configs/m4_*.json`). Scripts:
`scripts/check_early_yield.py`, `scripts/make_m4_configs.py`, `scripts/key_figure.py`.

## Part 1 — Predict

1. In the 3 × 3 × 20 mm LYSO bar with mirror-like side faces, can a photon that is
   reflected once by the readout face still be detected within 100 ps of emission?
2. Two readout layers extract the same total fraction of photons on their first hit.
   Layer A extracts mostly photons at θ ≈ 40° (just beyond the grease critical angle),
   layer B mostly at θ ≈ 75°. Which gives more photons in the first 100 ps, and why?
3. Should the period that maximises early photons be larger or smaller than the period
   that maximises total single-pass extraction? Guess, with a one-line reason.

## Part 2 — Derivation

### 2a. Which photons can be early
Let s_τ = c τ / n_g be the path that fits into time τ, and t_dir = n_g Lz / c the
direct-transit time (≈ 121 ps). Side faces of the kinds `specular`, `bare` and
`wrapped_specular` never change the sign of d_z. A photon therefore reverses its
z-motion only at the back face (z = 0) or at the readout (z = Lz). Consequences:
- A photon emitted toward the back face travels at least z + Lz ≥ Lz in z before it
  first reaches the readout: path ≥ Lz, time ≥ t_dir.
- A photon reflected at the readout (any order, any new angle) must reach the back
  face and come back: at least 2 Lz more in z, time ≥ 2 t_dir.
So for τ < t_dir, *only photons emitted toward the readout and transmitted on their
first readout hit* can be detected by τ.

### 2b. The early-photon yield as a single-pass integral
A photon emitted at height z toward the readout with polar angle θ reaches it after
path (Lz − z)/cos θ. With z uniform on [0, Lz], the probability that this path is at
most s_τ is min(1, s_τ cos θ / Lz) (derivation 04, eq. 4 with k = 0). Averaging over
isotropic emission and the first-hit transmission T(θ, φ) of the readout layer,

    E(τ) = (1/4π) ∫_{hemisphere} dΩ T(θ, φ) min(1, s_τ cos θ / Lz),   τ < t_dir.   (1)

For τ = 100 ps, s_τ / Lz = 100 × 299.79 / (1.81 × 20 000) ≈ 0.828, so the weight is
0.828 cos θ: E(100 ps) is a *cosine-weighted* single-pass transmission. Compare the
single-pass extraction (derivation 03, eq. 9), which weights every direction equally:

    η₁ = (1/4π) ∫ dΩ T(θ, φ).                                                     (2)

The cosine weight is the whole difference between optimising for light yield and
optimising for timing: a photon extracted at grazing angle (cos θ small) counts fully
in η₁ but arrives late, because it needed a long path to reach the readout.

Two consequences of (1). First, for every τ < t_dir we have s_τ < Lz, so the minimum
is never 1 and E(τ) = (s_τ / Lz) (1/4π) ∫ dΩ T cos θ: the design that maximises early
photons is the same for every τ below the direct transit time; τ only sets the scale.
Second, the bounds. A readout that transmitted everything (T = 1) would reach
E = s_τ / (4 Lz), which is 0.828 / 4 ≈ 20.7 % at 100 ps. Light from inside the
escape cone can contribute at most (s_τ / Lz) sin²θc / 4 = (s_τ / Lz)(n2/n1)² / 4,
about 13.5 % for grease and 6.3 % for air. The bare face already gets most of that, so
any real gain must come from the trapped band, and there is far more room for an
air-coupled readout than for a grease-coupled one.

Scope of (1). Two things spoil it. First, side faces that can reverse d_z
(`lambertian`, `wrapped_lambertian`): then (1) is only an approximation. Second, losses
on the way to the readout: bulk absorption, and side faces that do not reflect
perfectly. A `bare` or `wrapped_specular` side face loses light only when the photon
hits it inside that face's escape cone, |d_x| > cos θc,s, with θc,s = 33.5° for an air
gap. For the flat readout this never happens to a photon that can be transmitted,
because the readout cone and the side cones are disjoint (cos²θc + cos²θc,s > 1,
derivation 04). A photonic-crystal readout, however, also transmits light with
θ > 90° − θc,s ≈ 56.5°. On its way, that light can lie in a side cone and lose about 5 %
per side bounce (wrap reflectivity 0.95). Then (1) is an upper bound. The exact
first-pass yield replaces the weight by a survival-weighted path integral:

    w(θ, φ) = (cos θ / Lz) ∫_0^{s_τ} S_x(L) S_y(L) dL,                               (1a)

    S_x(L) = P_x^⌊D⌋ (1 − f + f P_x),   D = L |d_x| / Lx,   f = D − ⌊D⌋.

S_x is the probability of surviving the x faces after a path L, averaged over the
uniform start position (the photon hits an x face ⌊D⌋ or ⌊D⌋ + 1 times). P_x is the
return probability of an x face at incidence cosine |d_x|: 1 under total internal
reflection, and R + T²ρ/(1 − ρR) for an air gap and a mirror of reflectivity ρ
(derivation 04). S_y is the same for the y faces. With lossless mirrors, (1a) reduces
to (1). The optimiser uses (1), not (1a). The difference only penalises light with
θ > 56.5°, where the early weight cos θ is already small, so (1) slightly overvalues
designs that transmit grazing light.

Checks:
- (1) against the M3 Monte Carlo for the bare face, where it is exact:
  `scripts/check_early_yield.py`.
- (1) and (1a) against the M4 Monte Carlo with the fine tables, with lossless mirror
  walls and with the nominal wraps: `scripts/m4_table_checks.py`.

The numbers are in docs/status.md.

### 2c. Differentiable evaluation
By C4v symmetry, ∫ dΩ = 8 ∫_0^{π/4} dφ ∫_0^{π/2} sin θ dθ. On the optimisation grid
(midpoints in θ and in φ, which avoids the mirror-symmetric incidences φ = 0 and 45°,
where degenerate eigenvalues make eigenvector gradients ill-conditioned),

    J(p) = (8 / 4π) Σ_i Σ_j T(θ_i, φ_j; p) w_τ(θ_i) sin θ_i Δθ Δφ,                 (3)

with p = (a, f, h): period, area fill factor f = π r² / a², height. Every T is a
torcwa solve, and torcwa propagates gradients through the eigen-decomposition and the
S-matrix, so ∂J/∂p comes from one backward pass.

The pillar permittivity enters through its Fourier coefficients. For a disk of radius
r centred in a square cell of side a (area fraction f),

    ε_G = ε_b δ_{G,0} + (ε_p − ε_b) f · 2 J₁(|G| r) / (|G| r),                      (4)

with the limit f at G = 0 (J₁ the Bessel function of the first kind). (4) is exact and
smooth in r and a, unlike a pixelated disk whose FFT changes in steps as r crosses
pixel edges. The code builds the convolution matrix from (4) directly and checks it
against the real-space FFT path at fine grids. J₁ itself is computed from
J₁(x) = (1/2π) ∫_{−π}^{π} cos(τ − x sin τ) dτ with the trapezoid rule, which for a
periodic integrand converges exponentially; torch's own Bessel function has no
gradient.

Two implementation details matter for the gradient. The calculation runs in units of
the period (frequency a/λ, radius r/a, height h/a), so the period is a smooth input
like the other two. And evanescent transmitted orders are left out of the sum before
torcwa is called: they carry no power, but torcwa's power normalisation takes
sqrt(k_z), whose derivative is infinite at k_z = 0, and a first version returned NaN
gradients because of it. The gradient is tested against finite differences.

### 2d. Parameterisation and bounds
Unconstrained variables x ∈ ℝ³ are mapped by sigmoids to
a ∈ [0.20, 1.00] µm, f ∈ [0.05, 0.60], h ∈ [0.05, 0.80] µm. The upper fill factor
keeps a gap of at least 0.13 a between neighbouring pillars (a fabrication margin);
the period range covers the window of derivation 03, eq. (5) for grease and air.
Optimiser: Adam on x, several starts, the best design re-checked at higher order.

### 2e. Assumptions and their bias
| Assumption | Bias |
|---|---|
| Objective uses the first pass only | Exact for E(τ < t_dir) with non-flipping sides (2a); misses later passes, which matter for η but not for E(100 ps). |
| Coarse angle grid and order during optimisation | Optimum can shift slightly; the final design is re-evaluated on the fine grid at higher order and in the Monte Carlo. |
| Local optimiser | May find a local optimum; several starts reduce, not remove, this risk. |
| Single wavelength | Designs tuned at 420 nm; band-averaged performance is lower (03, 2m). |
| Side-wall losses ignored (uses (1), not (1a)) | Overestimates E for designs that transmit light with θ > 56.5°: by 0.004 points for the grease early optimum and 0.095 for the single-pass optimum (2b, Monte Carlo with the nominal wraps). |

## Part 3 — Check

| Quantity | Predicted | Script | Match? |
|---|---|---|---|
| E(100 ps) from (1) vs Monte Carlo, bare face | | `scripts/check_early_yield.py` | Yes: grease 12.78 % from (1), 12.77 ± 0.03 % Monte Carlo (z = −0.3); air 5.46 % vs 5.49 ± 0.02 % (z = +1.1). |
| E(100 ps) from (1) and (1a) vs Monte Carlo, photonic crystals | | `scripts/m4_table_checks.py` | Yes once side losses are included: lossless mirror walls vs (1), z = −1.0, −0.7, −0.5; nominal wraps vs (1a), z between −0.9 and +1.7. Against (1), the single-pass design with wraps was 3.8σ low (2b). |
| Optimised period vs reference period | | `optimize` runs 38905901930, 38905905490; `scripts/recover_optimize_log.py` | Smaller for early photons: 0.234 µm (grease) and 0.232 µm (air), close to λ/n₁ = 0.232 µm; 0.559 µm for single-pass extraction (grease); reference 0.40 µm. |
| E(100 ps) and η: bare / reference / optimised | | `mc` runs 38936853588, 38953882816; `scripts/key_figure.py` | Grease, by 100 ps: 12.80 / 12.76 / 13.16 % (early optimum) / 12.53 % (single-pass optimum); by 5 ns: 40.4 / 59.2 / 50.7 / 64.6 %. Air, by 100 ps: 5.47 / 5.54 / 5.85 %; by 5 ns: 16.0 / 53.4 / 37.9 %. |

## Part 4 — Check questions

Q1. Why can no photon that starts toward the back face be detected before t_dir, and
which side-wall model would break this statement?

Q2. Derive the weight min(1, s_τ cos θ / Lz) and explain why it becomes cos θ times a
constant for τ = 100 ps in a 20 mm bar.

Q3. Why use the analytic Bessel form (4) for the pillar instead of the pixelated disk
when computing gradients with respect to the radius?

## Part 5 — Answers

A1. It must first travel to z = 0 and back, at least Lz in z, so its path is at least
Lz and its time at least n_g Lz / c = t_dir. A side model that can reverse d_z
(Lambertian contact, or an air-gap diffuse wrap for light in a side cone) breaks it,
because then the photon can turn around without reaching the back face.

A2. Path to the readout is (Lz − z)/cos θ; with z uniform the probability that it is
≤ s_τ is the fraction of z with Lz − z ≤ s_τ cos θ, i.e. min(1, s_τ cos θ / Lz). For
τ = 100 ps, s_τ ≈ 16.6 mm < Lz = 20 mm, so the minimum is never 1 and the weight is
0.828 cos θ.

A3. The FFT of a pixelated disk is piecewise constant in r: it only changes when the
edge crosses a pixel, so its derivative is zero almost everywhere and infinite at the
jumps. A smoothed (sigmoid) edge fixes this but biases the geometry. Equation (4) is
the exact transform of a sharp disk and is analytic in r and a, so automatic
differentiation returns the true derivative of the truncated RCWA model.
