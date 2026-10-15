# 01 — Escape cone and trapping in an ideal cuboid

Written by Claude (agent) 2026-10-15 under the lifted physics gate. Aziz: work through
Part 1 before reading Part 2, then answer the check questions in Part 4 before reading
Part 5. Code that follows this derivation: `src/phcscint/analytic.py`;
numbers: `scripts/escape_cone.py` → `results/m1_escape_cone.json`.

## Part 1 — Predict (answer before reading on)

Setup: a point source inside a scintillator of index n1 emits isotropically. One face
is flat and in contact with a medium of index n2 < n1. Ignore Fresnel reflection inside
the cone (every ray inside the escape cone is transmitted) and ignore absorption.

1. What fraction of the emitted photons hits *this one face* inside the escape cone,
   as a function of n1 and n2? Guess the number for LYSO→air before computing it.
2. Will LYSO→grease (n2 = 1.5) give a *larger* or *smaller* fraction than LYSO→air, and
   roughly by what factor?
3. A long bar (3×3×20 mm) with perfectly specular, lossless, bare walls. A photon is
   emitted outside the escape cone of the readout face. Can it ever reach the
   photodetector? Yes or no, and the one-line reason.
4. All six faces bare into air: is the total first-pass escape simply 6 × η₁? Why or
   why not? Does the answer depend on n2/n1?

## Part 2 — Derivation

### 2a. Critical angle
Snell's law at the flat face, n1 sin θ1 = n2 sin θ2. The transmitted ray leaves at
grazing exit, θ2 = π/2, when

    sin θc = n2 / n1.                                                        (1)

For θ1 > θc there is no real θ2: total internal reflection (TIR). With n2 < n1, θc is
real and smaller than π/2.

### 2b. Solid angle of the escape cone
Directions are points on the unit sphere. A cone of half-angle θc around the face
normal has solid angle

    Ω(θc) = ∫₀^{2π} dφ ∫₀^{θc} sin θ dθ = 2π (1 − cos θc).                   (2)

### 2c. Escape fraction through one face
Isotropic emission means the probability density over directions is 1/(4π) per
steradian. The fraction of photons whose direction lies inside the cone of this one
face is

    η₁ = Ω(θc) / (4π) = (1 − cos θc) / 2.                                    (3)

With (1), cos θc = sqrt(1 − sin²θc) = sqrt(1 − (n2/n1)²), so

    η₁(n1, n2) = ½ [ 1 − sqrt(1 − (n2/n1)²) ].                               (4)

Limits as sanity checks: n2 → n1 gives θc → π/2 and η₁ → ½ (the whole hemisphere
facing the face escapes, which is half of all directions). n2 → 0 gives η₁ → 0.
Small-angle expansion for n2 ≪ n1: η₁ ≈ (n2/n1)²/4, so the fraction falls
quadratically with the index contrast.

η₁ depends only on the ratio n2/n1 and on nothing else: not on crystal size, not on
where the photon was emitted, not on wavelength except through n1(λ) and n2(λ).

### 2d. Assumptions and the direction of their bias
| Assumption | Effect on the true single-pass escape |
|---|---|
| No Fresnel reflection inside the cone | Overestimates: Fresnel R rises from ((n1−n2)/(n1+n2))² at normal incidence (LYSO→air: about 8 %) to 1 at θc, so the flux-weighted transmission inside the cone is below 1. `scripts/fresnel_vs_rcwa.py` computes the Fresnel-weighted value for comparison. |
| No bulk absorption | Overestimates, by a factor exp(−L/ℓ_abs) averaged over path lengths; negligible for 20 mm of LYSO (ℓ_abs is metres), relevant with many wall bounces. |
| Point source, isotropic | No bias for the angular fraction: every emission point sees the same cone. |
| Single pass only | Underestimates the *eventual* detected light when other faces are reflective: light returned by wrapping gets further chances. This is the quantity the Monte Carlo (M3) computes. |

### 2e. Trapped rays stay trapped in an ideal cuboid
Let the ray direction be the unit vector d = (u, v, w) = (sin θ cos φ, sin θ sin φ,
cos θ), with z along the bar axis toward the readout face. The cuboid's faces are
perpendicular to x, y or z. A specular reflection from a face with normal along
axis a reverses only the component of d along that axis:

    x-face: (u, v, w) → (−u, v, w)
    y-face: (u, v, w) → (u, −v, w)
    z-face: (u, v, w) → (u, v, −w).                                          (5)

Consequence: |u|, |v| and |w| are each separately conserved under any sequence of
specular reflections. The angle to the z-face normal, cos θ = |w|, never changes.

The escape cone of a z-face is the set |w| > cos θc (equivalently n1 sin θ < n2, the
definition of "not trapped" in AGENTS.md). Since |w| is invariant, a ray that starts
with |w| < cos θc never enters the z-face escape cone: it is trapped with respect to
the readout face forever, however many times it bounces. The same statement holds for
the x-faces with |u| and the y-faces with |v|. So the set of rays that can ever
escape through any face is fixed at the moment of emission.

Fresnel reflection does not change this. A ray inside the cone that is partially
reflected comes back with the same |w| and meets the face again inside the cone, so
with lossless walls and no absorption it escapes eventually through a z-face
(if it is not also inside a side-face cone). Fresnel only delays escape; it does not
alter the trapped set.

### 2f. Do the six cones overlap?
A direction can be in the +z cone and the +x cone simultaneously only if
|w| > cos θc and |u| > cos θc with u² + w² ≤ 1, i.e. only if 2 cos²θc < 1, i.e.
θc > 45°, i.e. n2/n1 > 1/√2 ≈ 0.707. For LYSO→air, n2/n1 = 0.552: the cones are
disjoint, the six escape sets are disjoint, and the total escapable fraction with six
bare faces is exactly 6 η₁. For LYSO→grease on a face, n2/n1 = 0.829 > 0.707: that
cone overlaps with neighbouring cones of the same n2, and the union is smaller than
the sum. Mixed cases (grease on the readout face, air on the sides) are checked in
question 2 of Part 4. The Monte Carlo of M3 must reproduce these numbers for the
specular wall model.

### 2g. What breaks the argument
- Rough or Lambertian walls re-randomise the direction at each hit; |w| is no longer
  conserved and every photon eventually finds a cone (if not absorbed first).
- Absorption removes photons on long paths, which affects trapped rays most.
- A periodic layer on the readout face adds a reciprocal-lattice vector to the in-plane
  wavevector: k∥ → k∥ + G. That changes |w| for both transmitted and reflected
  diffraction orders, so it can move a trapped ray into the escape cone (transmitted
  order) or change the |w| it carries on its next pass (reflected order). This is the
  whole mechanism the project exploits.

### 2h. Connection to timing
Because a flat face cannot change |w|, the readout face cannot change *which* photons
arrive, only *when* each in-cone photon's partial reflections return it. The arrival
time of the extracted light is set by geometry and emission direction alone. A
photonic-crystal layer changes the set of extracted photons and their paths, which is
why it can change the early part of the arrival-time distribution.

## Part 3 — Check against the script (fill after running `scripts/escape_cone.py`)

| Case | Predicted (Part 1) | Script result | Match? |
|---|---|---|---|
| LYSO (n1 = 1.81) → air | | | |
| LYSO → n2 = 1.5 | | | |
| BGO (n1 = 2.15) → air | | | |

What surprised me:

## Part 4 — Check questions (answer before reading Part 5)

Q1. Why does η₁ depend only on n2/n1 and not on the size of the crystal or on where
the photon is emitted? What assumption would have to fail for size to matter?

Q2. LYSO bar with grease (n2 = 1.5) on the readout face and air on the other five.
Can a direction lie in the readout cone and in an air side cone at the same time?
Show it with the two cosines.

Q3. Replace the specular walls by Lambertian ones (direction re-randomised at every
wall hit, no absorption). Which statement in 2e fails, what happens to the
extraction efficiency, and what happens to the arrival-time distribution?

## Part 5 — Answers

A1. The escape condition is purely angular (|w| > cos θc) and the emission is
isotropic, so every emission point sees the same fraction of directions inside the
cone; no length enters equation (4). Size enters only through absorption (path length
to the face) or through non-specular walls, where the number of bounces before escape
matters.

A2. Readout cone: |w| > cos θc,grease = sqrt(1 − (1.5/1.81)²) ≈ 0.560. Side cone:
|u| > cos θc,air = sqrt(1 − (1/1.81)²) ≈ 0.834. Both at once needs u² + w² > 0.560² +
0.834² ≈ 0.313 + 0.695 = 1.008 > 1, impossible for a unit vector. So no: the sets are
disjoint, just barely. The total escapable fraction is η₁(grease) + 5 η₁(air) with no
overlap correction. (The numbers come from `results/m1_escape_cone.json`; the
inequality is the point.)

A3. Equation (5) fails: a Lambertian hit replaces d by a new direction drawn from a
cosine distribution about the wall normal, so |w| is not conserved. Every photon
eventually samples a direction inside some cone, so without absorption the extraction
efficiency through the six faces tends to 1 (through the readout face alone, to the
fraction set by the competition between faces). The arrival-time distribution acquires
a long tail: photons escape after a random number of wall hits, each adding path
length. Fast timing wants the opposite: many photons on the first pass.
