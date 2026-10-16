# 04 — Monte Carlo of one scintillator pixel: transport, walls, readout, timing

Written by Claude (agent) 2026-10-16. Code: `src/phcscint/montecarlo.py` (ray tracer),
`src/phcscint/timing.py` (analytic expectations used as test oracles and figures of
merit). Script: `scripts/run_pixel_mc.py`.

## Part 1 — Predict

Pixel: LYSO, 3 × 3 × 20 mm, readout on one 3 × 3 mm face, coupled with grease
(n = 1.46). Emission uniform in the volume, isotropic. No bulk absorption.

1. All five other faces are perfect mirrors. What fraction of photons is *eventually*
   detected? (A number, from derivation 01.)
2. In the same box, what is the shortest possible transport time for a photon emitted
   at the far end? Which photons arrive first?
3. Replace the side mirrors by a diffuse reflector (Teflon-like) separated from the
   polished crystal by a thin air gap. Does the eventually detected fraction go up,
   down, or stay the same?
4. Replace them instead by a diffuse reflector *in optical contact* with the crystal
   (paint on a ground surface). What happens to the detected fraction, and to the
   number of photons arriving in the first 100 ps?

## Part 2 — Derivation

### 2a. Geometry and coordinates
Box [0, Lx] × [0, Ly] × [0, Lz], Lx = Ly = 3000 µm, Lz = 20 000 µm. The readout face
is z = Lz with outward normal +z (AGENTS.md: +z points out of the crystal through
the readout). The opposite face z = 0 is the *back face*; x = 0, Lx and y = 0, Ly
are the *side faces*. Faces are numbered 0: −x, 1: +x, 2: −y, 3: +y, 4: back (−z),
5: readout (+z).

### 2b. Emission and transport
Emission points are uniform in the volume; directions are isotropic, i.e. w = cos θ
is uniform on [−1, 1] and the azimuth uniform on [0, 2π). (Uniform depth is an
assumption, see 2j.) Between interactions a photon moves in a straight line. From
position p and unit direction d the distance to the plane x_a = c is (c − p_a)/d_a,
taken only if positive; the next interaction is at the smallest of the three
candidate distances (one per axis). The path length L is accumulated.

Bulk absorption with absorption length ℓ: the survival probability after path L is
exp(−L/ℓ). Equivalent and cheaper: draw an absorption budget L_abs ~ Exponential(ℓ)
once per photon at emission; the photon is absorbed if its path reaches L_abs. Both
give P(survive L) = exp(−L/ℓ).

### 2c. Transport time
The photon's energy travels at the group velocity c/n_g, so

    t = n_g L / c,    c = 299.792458 µm/ps.                                         (1)

Assumption: n_g = n (phase index at the emission peak) because no dispersion formula
for LYSO could be verified (docs/decisions.md). For normal dispersion n_g > n, so (1)
*underestimates* every time by the same factor n/n_g. Because the factor is common to
every photon and every design, it rescales the time axis and does not change any
comparison between designs. Time spent inside the sub-micron PhC layer and in the
grease is neglected.

Scale: the direct transit along the bar takes t_dir = n Lz / c = 1.81 × 20 000 /
299.79 ≈ 121 ps.

### 2d. Wall models (faces 0 to 4)
All use the unpolarised Fresnel coefficients of derivation 02 at the crystal side.
Let θ be the angle of incidence on the face, R_F(θ) and T_F(θ) = 1 − R_F the
crystal → air Fresnel power coefficients, and ρ a reflector reflectivity.

1. `specular` (ideal mirror in contact): reflect specularly with probability ρ, else
   lost at the wall.
2. `bare` (polished face, nothing around it, air outside): reflect specularly with
   probability R_F, else the photon leaves the crystal (lost).
3. `wrapped_specular` (polished face, thin air gap, specular reflector such as a
   multilayer mirror film): with probability R_F specular reflection at the crystal;
   otherwise the photon crosses the gap, is reflected by the mirror with probability
   ρ, and meets the crystal again *at the same angle*, where it re-enters with
   probability T_F (reciprocity: same T_F from either side at matched angles) or is
   sent back to the mirror. Summing the geometric series of gap round trips, the
   probability of returning into the crystal is

       P_ret = R_F + T_F² ρ / (1 − ρ R_F),                                        (2)

   always in the specular direction. Under total internal reflection P_ret = 1.
4. `wrapped_lambertian` (polished face, thin air gap, diffuse reflector such as PTFE
   tape): with probability R_F specular reflection; otherwise the photon reaches the
   reflector, is absorbed with probability 1 − ρ, or re-emitted into the gap with a
   cosine (Lambertian) distribution, cos θ_a = sqrt(U), U uniform. It then meets the
   crystal at θ_a from the air side, enters with probability T_F^{air→crystal}(θ_a),
   else goes back to the reflector and the process repeats. An entering photon is
   refracted: sin θ_1 = sin θ_a / n1, with a uniform random azimuth.
5. `lambertian` (diffuse reflector in optical contact, e.g. paint on a ground
   surface): with probability ρ the photon is re-emitted into the crystal with a
   cosine distribution about the inward normal over the *full* hemisphere; else lost.

Key property of model 4: refraction from air into the crystal can only produce
angles with sin θ_1 ≤ 1/n1, i.e. *inside that face's own escape cone*. Light
recycled by an air-gap wrap on a side face therefore comes back with
|d_side| > cos θc,air, and for LYSO with grease readout the side cones and the
readout cone are disjoint (derivation 01, A2, here with n = 1.46:
cos²θc,grease + cos²θc,air = 0.349 + 0.695 = 1.044 > 1). Such light can never reach
the readout cone. Only model 5 (or a PhC on the readout) moves light between cones.
This is a testable prediction (2h).

The cones stop being disjoint when cos²θc,r + cos²θc,air < 1, i.e. when
n_r² > n1² − 1: for LYSO, a readout medium with n_r > sqrt(1.81² − 1) ≈ 1.509.

### 2e. Readout models (face 5)
- `bare`: crystal → outside medium n2 Fresnel; transmitted photons are detected at
  the moment they cross the face, reflected ones are reflected specularly.
- `lut`: the photonic-crystal lookup table of derivation 03. For direction
  d = (d_x, d_y, d_z), d_z > 0: θ = arccos d_z, φ = atan2(d_y, d_x), and the normalised
  in-plane wavevector is u = n1 (d_x, d_y). The table gives the powers T_mn, R_mn of
  the open orders (after the C4v mapping, interpolation and renormalisation, 03 §2i).
  One channel is drawn with probability equal to its power. A transmitted channel
  means detection. A reflected order (m, n) gives the new direction

      d' = ( u_mn / n1 ,  −sqrt(1 − |u_mn|² / n1²) ),   u_mn = u + g (m, n),        (3)

  which is a unit vector heading back into the crystal (d'_z < 0), and is a real
  direction because reflected orders are kept only if |u_mn| < n1. For (m, n) = (0, 0),
  (3) is the specular reflection.

"Detected" means "entered the outside medium". The photodetector is idealised: every
photon entering the grease is counted. This overestimates detection and, importantly
for this project, ignores that a real photodetector window reflects more light at
oblique angles. A PhC sends light out through diffracted orders at angles different
from the bare face, so the comparison between designs inherits this idealisation.

### 2f. Analytic expectation: specular box, any readout reflectance, mirror sides
Side faces are mirrors (ρ = 1). Specular reflections from side faces change only
d_x, d_y signs, so w = d_z keeps its magnitude (derivation 01, 2e), and the distance
travelled along z between readout hits is 2 Lz. Hence the path length depends only
on the start height z and on |w|: side reflections do not add z-progress, and the
path length is (z-distance travelled) / |w|.

Let T_r(|w|) and R_r = 1 − T_r be the readout coefficients and R_b(|w|) the
back-face reflectance (1 for a mirror). Write s = c t / n_g for the path length that
fits into time t.

- w > 0 (toward the readout): the k-th readout hit (k = 0, 1, …) happens after path
  L_k = [(Lz − z) + 2k Lz] / w, and the photon is detected there with probability
  a_k = T_r (R_r R_b)^k.
- w < 0: it first goes to the back face, so L_k = [z + Lz + 2k Lz] / |w| and
  a_k = R_b T_r (R_r R_b)^k.

z is uniform on [0, Lz]. The condition L_k ≤ s is linear in z, and the fraction of z
values that satisfy it is, in both cases,

    P_z(k) = clip( |w| s / Lz − o_k , 0, 1 ),   o_k = 2k (w > 0),  2k + 1 (w < 0).   (4)

(For w > 0: Lz − z + 2k Lz ≤ w s ⟺ z ≥ (2k + 1) Lz − w s, and the length of that
interval inside [0, Lz] divided by Lz is (4). Same steps for w < 0.)

The detected-time CDF per *emitted* photon is then

    F(t) = ½ ∫_{−1}^{1} dw  Σ_k a_k(|w|) P_z(k; |w|, s(t)),                          (5)

and its long-time limit is

    F(∞) = ½ ∫_{−1}^{1} dw  T_r / (1 − R_r R_b) · (1 if w > 0, R_b if w < 0).        (6)

With a mirror back face (R_b = 1) every photon with T_r > 0 is eventually detected,
and (6) gives F(∞) = 1 − cos θc = 2 η₁: the answer to Predict 1. For LYSO → grease
(n = 1.46), (6) gives 40.9 %, and the Monte Carlo detects 40.8 % by 2 ns
[`results/mc-38902476498.json`, case "mirror walls"].

With absorption, multiply each term in (5) by exp(−L_k / ℓ) inside the z-average.
`timing.py` evaluates (5) and (6) by quadrature in w and z; these are the test
oracles for the Monte Carlo.

### 2g. Analytic expectation: lossless Lambertian walls
With `lambertian` walls of ρ = 1 on all five faces and no absorption, the only sink
is the readout, and every photon is eventually detected: F(∞) = 1. The time to get
there is long (many diffuse bounces); only the bookkeeping limit is tested.

### 2h. Prediction for the air-gap diffuse wrap
By 2d, `wrapped_lambertian` side faces with ρ = 1, a mirror back face and a bare grease
readout give *exactly* the same detected-time distribution as mirror side faces: the
photons that can reach the readout cone are never in a side cone (TIR, specular), and
the photons in a side cone never reach the readout cone. The Monte Carlo must
reproduce (5) for this configuration too. This is a sharp test of the wrap code and
of the claim itself.

### 2i. Figures of merit
For N emitted photons:
- extraction efficiency η(t_max) = N_det(t < t_max) / N, with t_max the simulation
  cut-off (photons still bouncing at t_max are reported separately);
- the detected-time CDF per emitted photon F(t) = N_det(t' < t) / N (plotted on one
  axis for all designs, so both yield and timing are visible);
- the early-photon yield E(τ) = F(τ) for τ = 50, 100 and 200 ps (headline τ = 100 ps,
  roughly the direct transit time 2c).
Statistical uncertainty of each fraction p: sqrt(p (1 − p) / N).

Why E(τ) and not η: for timing, the photodetector's time stamp is driven by the first
few detected photons, so the yield in the first ~100 ps matters, not the total. This
model includes only photon transport. Scintillation rise and decay (tens of ns for
LYSO) and the photodetector's single-photon time resolution are outside it; they
would convolve the transport-time distribution and are stated as limitations.

### 2j. Assumptions and their bias
| Assumption | Bias |
|---|---|
| Emission uniform in depth | Real 511 keV interactions are exponentially distributed from the entrance face; depth-of-interaction effects are averaged differently. Affects absolute times, not the ranking of readout designs. |
| n_g = n | Underestimates all times by n/n_g; common factor (2c). |
| Ideal photodetector at the readout | Overestimates detection; ignores angle-dependent window reflection (2e). |
| Light unpolarised at every interaction | Derivation 03 §2g. |
| Air gaps of zero thickness | No lateral displacement or time in the gap; negligible for micrometre gaps. |
| Reflectivities ρ independent of angle and wavelength | Simplification; real films vary with angle. |
| Ray optics in the bulk (incoherent) | Valid: crystal dimensions are ~10⁴ wavelengths and scintillation is broadband. |
| Monochromatic at the emission peak | As in derivation 03. |

## Part 3 — Check against the script

| Quantity | Predicted | Script | Match? |
|---|---|---|---|
| F(∞), mirror box, bare grease readout | | | |
| Earliest arrival from the far end | | | |
| Air-gap diffuse sides vs mirror sides | | | |
| E(100 ps), Lambertian contact vs mirror | | | |

## Part 4 — Check questions

Q1. Why does the analytic CDF (5) need only the start height z and |w|, and not
x, y or how many times the photon hits the side faces?

Q2. Show that an air-gap diffuse wrap on the side faces cannot feed light into the
readout cone for LYSO with n_r = 1.46 grease, and find the readout index above which
it can.

Q3. Give a configuration change that increases η(t_max) but decreases E(100 ps),
and explain the mechanism.

## Part 5 — Answers

A1. Side mirrors flip d_x or d_y and leave |w| unchanged, so the photon's progress
along z per unit path is always |w|. Reaching the readout requires a fixed z-distance
(Lz − z, or z + Lz via the back face, plus 2Lz per extra round trip), so the path is
that distance divided by |w|, independent of the lateral motion. The side hits change
where on the readout face the photon arrives, which does not matter for a uniform face.

A2. Re-entry from the air gap gives sin θ_side ≤ 1/n1, i.e. |d_side| ≥ cos θc,air =
sqrt(1 − 1/n1²). The readout cone needs |w| > cos θc,r = sqrt(1 − n_r²/n1²). Both at
once require d_side² + w² > (1 − 1/n1²) + (1 − n_r²/n1²), which exceeds 1 unless
n_r² > n1² − 1. For n1 = 1.81: n_r > 1.509. With n_r = 1.46 the sum is 1.044, so it is
impossible.

A3. Replacing mirror side faces by `lambertian` (contact) walls. η rises (in the
lossless limit to 1) because diffuse re-emission eventually puts every photon into the
readout cone. But in a 3 × 3 × 20 mm bar most photons heading for the readout inside
its cone hit a side face first (lateral travel 20 mm × tan θ is larger than 3 mm for
most θ in the cone), and a diffuse wall sends about half of them backward. They then
arrive late. So the early yield E(100 ps) can drop while η rises. The Monte Carlo
checks this: lossless contact-diffuse sides raise the fraction detected by 2 ns from
40.8 % to 79.0 % but lower E(100 ps) from 12.76 % to 10.93 % [`results/mc-38902476498.json`].
