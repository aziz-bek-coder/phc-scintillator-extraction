# 05 — A differentiable objective for early photons, and the optimisation

Written by Claude (agent). Code: `src/phcscint/optimize.py`. Scripts:
`scripts/optimize_design.py`, `scripts/compare_designs.py`.

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

Scope of (1): exact for the side models above when absorption over ~20 mm is
negligible. With `lambertian` or `wrapped_lambertian` side faces the sign of d_z can
flip at a side face and (1) is only an approximation; the Monte Carlo evaluates the
real thing. (1) was checked against the M3 Monte Carlo by
`scripts/check_early_yield.py` (results in `results/m4_early_yield_check.json`,
quoted in docs/status.md).

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

## Part 3 — Check

| Quantity | Predicted | Script | Match? |
|---|---|---|---|
| E(100 ps) from (1) vs Monte Carlo, bare face | | | |
| Optimised period vs reference period | | | |
| E(100 ps) and η: bare / reference / optimised | | | |

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
