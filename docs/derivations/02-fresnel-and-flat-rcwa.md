# 02 — Fresnel coefficients and the flat-interface RCWA check

Written by Claude (agent) 2026-10-15. Code: `src/phcscint/fresnel.py`,
`src/phcscint/rcwa.py`; numbers and figure: `scripts/fresnel_vs_rcwa.py` →
`results/m1_fresnel_vs_rcwa.json`, `docs/figures/m1_fresnel_vs_rcwa.png`.

## Part 1 — Predict

1. At normal incidence LYSO→air, what fraction of the power is reflected? Give the
   formula and the number to one digit.
2. Is there an angle where p-polarised light is fully transmitted? For LYSO→air, is it
   below or above the critical angle?
3. Just beyond the critical angle, R = 1. Does the transmitted field vanish there? If
   not, why is T = 0 anyway?
4. A zero-order RCWA (one Fourier harmonic) of a flat interface: should it agree with
   Fresnel to machine precision, or only approximately? Why?

## Part 2 — Derivation

### 2a. Setup and conventions
Plane wave in medium 1 (index n1) incident at angle θ1 on the plane z = 0; medium 2
(index n2) for z > 0. Time dependence exp(−iωt), k0 = 2π/λ, wavevector in medium j
has magnitude nj k0. Tangential wavevector is conserved across the interface
(translation invariance along the plane):

    k∥ = n1 k0 sin θ1 = n2 k0 sin θ2,      kz,j = nj k0 cos θj.             (1)

s-polarisation (TE): E perpendicular to the plane of incidence. p-polarisation (TM):
E in the plane of incidence. Amplitude coefficients are defined on E for s and on E
for p with the Born & Wolf sign convention (AGENTS.md).

### 2b. Boundary conditions → Fresnel amplitudes
Tangential E and tangential H are continuous at z = 0 (no surface currents, μ = 1).

s: E = ŷ E, H ∝ k × E / (ω μ0). Continuity of E_y and H_x gives
    1 + r_s = t_s,      n1 cos θ1 (1 − r_s) = n2 cos θ2 t_s,
    r_s = (n1 cos θ1 − n2 cos θ2) / (n1 cos θ1 + n2 cos θ2),
    t_s = 2 n1 cos θ1 / (n1 cos θ1 + n2 cos θ2).                                (2)

p: H = ŷ H. Continuity of H_y and E_x gives
    r_p = (n2 cos θ1 − n1 cos θ2) / (n2 cos θ1 + n1 cos θ2),
    t_p = 2 n1 cos θ1 / (n2 cos θ1 + n1 cos θ2).                                (3)

Check: at θ1 = 0, r_s = (n1 − n2)/(n1 + n2) and r_p = (n2 − n1)/(n1 + n2) = −r_s.
The sign difference is the convention for the direction of the p-field, not physics;
|r|² is the same.

### 2c. Power coefficients
Reflectance is the ratio of normal Poynting-flux components, which for the reflected
wave in the same medium is

    R = |r|².                                                                   (4)

For transmission the flux is (nj cos θj)|E|² up to a common constant, so

    T = Re(n2 cos θ2) / (n1 cos θ1) · |t|².                                     (5)

Energy conservation for lossless media: R + T = 1 for each polarisation, which
follows from (2)–(5) by direct algebra, and is what the tests assert.

### 2d. Beyond the critical angle
For sin θ1 > n2/n1, cos θ2 = sqrt(1 − (n1/n2)² sin²θ1) is imaginary. With exp(−iωt)
the transmitted field goes like exp(i kz,2 z) and must decay into z > 0, so
Im kz,2 > 0, i.e.

    cos θ2 = + i sqrt((n1/n2)² sin²θ1 − 1).                                     (6)

Then n2 cos θ2 is purely imaginary, (2) and (3) have |r| = 1 (numerator and
denominator are complex conjugates), and T = Re(n2 cos θ2)·…/… = 0 while t ≠ 0: the
evanescent field carries no normal power flux. R = 1 exactly, phase of r varies.

### 2e. Brewster angle
r_p = 0 when n2 cos θ1 = n1 cos θ2. With Snell this gives tan θB = n2/n1. For
LYSO→air θB = arctan(1/1.81) ≈ 29°, below θc ≈ 34°. Inside the escape cone
p-polarised light therefore has a transmission window up to 100 %, while s-polarised
reflection rises monotonically. For unpolarised scintillation light the relevant
quantity is (T_s + T_p)/2.

### 2f. Flux-weighted escape with Fresnel loss
The geometric escape fraction (derivation 01) assumed T = 1 inside the cone. With
Fresnel transmission the single-pass fraction through one face is

    η₁^F = ∫₀^{θc} ½ [T_s(θ) + T_p(θ)] · ½ sin θ dθ,                            (7)

where ½ sin θ dθ is the isotropic probability of a polar angle in [θ, θ + dθ] on one
hemisphere (the azimuth integral already done). η₁^F < η₁; the script reports both.
This is a *single-pass* number; the reflected part comes back with the same |w| and
escapes on a later pass in the ideal lossless specular bar, so η₁^F is the quantity
that matters for the *first* arrival, not for the total.

### 2g. What the zero-order RCWA of a flat interface must reproduce
RCWA expands the fields in each layer in Fourier harmonics of the lattice. For a
homogeneous structure every Fourier coefficient except the zeroth vanishes, so the
truncated problem with order [0, 0] is exact: a single plane wave per medium and
polarisation, connected by the same boundary conditions as in 2b. torcwa solves this
in an (x, y)-polarisation basis and converts to s/p inside `S_parameters`; with
`power_norm=True` the returned |S|² are power fractions normalised by the kz ratio,
which is equation (5). Therefore

    |S_ss|²_T = T_s,  |S_pp|²_T = T_p,  |S_ss|²_R = R_s,  |S_pp|²_R = R_p,        (8)

with cross terms S_sp = S_ps = 0 for an isotropic flat interface at any azimuth, and
beyond θc the transmitted orders are evanescent and torcwa returns 0 for them. Any
disagreement is a convention error (sign, normalisation, angle layer), not a
truncation error. The tolerance in the test is set at 1e-6 for complex128; the
measured maximum deviation is in `results/m1_fresnel_vs_rcwa.json`.

### 2h. Assumptions and bias
| Assumption | Bias |
|---|---|
| Lossless media (real n) | Real scintillators have negligible absorption at the emission peak over one interface; no bias for the interface, bias for long paths (M3). |
| μ = 1 | Exact for these dielectrics at optical frequencies. |
| Infinite plane interface | Fine while the face is thousands of wavelengths across; edge diffraction ignored. |
| Monochromatic at the emission peak | Dispersion of n over the emission band (LYSO roughly 380–480 nm) changes θc by a small amount; checked later if a dispersion source is cited. |

## Part 3 — Check against the script

| Quantity | Predicted | Script | Match? |
|---|---|---|---|
| R at normal incidence, LYSO→air | | | |
| Brewster angle, LYSO→air | | | |
| max |RCWA − Fresnel| over all angles | | | |
| η₁^F / η₁ for LYSO→air | | | |

## Part 4 — Check questions

Q1. Why is the transmittance T = Re(n2 cos θ2)/(n1 cos θ1) |t|² and not simply |t|²?
What would go wrong with energy conservation if you used |t|²?

Q2. Beyond the critical angle |r| = 1 but r is complex with a phase that depends on
angle and polarisation. Name one physical consequence of that phase.

Q3. The flat-interface RCWA check passes at 1e-6. What does this validate, and what
does it *not* validate, about the RCWA that will be used for the patterned layer in M2?

## Part 5 — Answers

A1. Power flow across the interface is the normal component of the Poynting vector,
proportional to nj cos θj |E|² in medium j. Equal electric-field amplitude on the two
sides does not mean equal power: the wave in the denser medium (or at a steeper angle)
carries more flux per unit field. Using |t|² gives R + |t|² ≠ 1; for example at normal
incidence LYSO→air, |t_s|² = (2·1.81/2.81)² ≈ 1.66, obviously not a transmitted
fraction.

A2. The Goos–Hänchen shift (lateral displacement of a totally reflected beam), and the
fact that the s and p phases differ, which turns linear into elliptical polarisation
on TIR (the Fresnel rhomb). For the Monte Carlo, which tracks power, the phase is
irrelevant; for the RCWA lookup table the phases are discarded once |S|² is formed.

A3. It validates torcwa's conventions as used here: the s/p decomposition, the
kz-ratio power normalisation, the treatment of evanescent transmitted orders, the
angle definition in the input layer, and that eps = n² is the right input. It does
not validate Fourier-truncation convergence for a structured layer (one harmonic is
exact for a flat interface), the correctness of the permittivity convolution matrix,
or the Li factorisation rules for high-contrast pillars. Those need the M2
convergence study and a comparison with an independent published result.
