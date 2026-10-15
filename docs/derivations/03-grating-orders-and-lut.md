# 03 — Diffraction orders, the photonic-crystal readout layer, and the lookup table

Written by Claude (agent) 2026-10-16. Code: `src/phcscint/rcwa.py` (patterned solve),
`src/phcscint/lut.py` (lookup table, symmetry), `src/phcscint/fresnel.py`
(thin-film check). Scripts: `scripts/convergence.py`, `scripts/build_lut.py`.

## Part 1 — Predict

1. A ray in LYSO (n1 = 1.81) hits a square-lattice photonic crystal (PhC) with period
   a = 0.40 µm at θ = 60°, φ = 0, λ = 0.42 µm. Grease outside (n2 = 1.5). Which
   transmitted orders (m, n) can carry power out? Which reflected orders exist?
2. Without the PhC this ray is trapped. With the PhC, is it *guaranteed* to escape on
   this pass? On some later pass?
3. If the period is made very small (a = 0.10 µm), what happens to the diffracted
   orders, and what does the layer act like?
4. A ray *inside* the flat-face escape cone hits the PhC. Can the PhC make it *less*
   likely to escape? Give the mechanism.

## Part 2 — Derivation

### 2a. In-plane momentum and the grating equation
The incident plane wave in the scintillator has wavevector of magnitude n1 k0,
k0 = 2π/λ. Its component parallel to the readout face is

    k∥ = n1 k0 sin θ (cos φ, sin φ).                                            (1)

A structure periodic in x and y with period a (square lattice) has reciprocal lattice
vectors G_mn = (2π/a)(m, n), m, n integers. Bloch's theorem (equivalently: the field
scattered by a periodic structure must itself be quasi-periodic with the same Bloch
phase) means the outgoing waves on either side carry only the in-plane wavevectors

    k∥,mn = k∥ + G_mn.                                                           (2)

Normalising by k0, with u = n1 sin θ (cos φ, sin φ) and g = λ/a,

    u_mn = u + g (m, n).                                                         (3)

In a medium of index n_j the order is a propagating plane wave if |u_mn| < n_j and
evanescent otherwise; its polar angle there is sin θ_mn = |u_mn| / n_j and its z
component of direction is cos θ_mn = sqrt(1 − |u_mn|²/n_j²). Transmitted orders use
n_j = n2 (outside), reflected orders use n_j = n1 (back into the crystal).

For the flat face only (m, n) = (0, 0) exists, |u| is conserved, and we recover
derivation 01: transmission requires |u| < n2, i.e. n1 sin θ < n2.

### 2b. Answer to the trapping question
A trapped ray has n2 < |u| ≤ n1. It can leave through transmitted order (m, n) if
|u + g(m, n)| < n2. For the order (−1, 0) at φ = 0 this is

    |u| − n2 < g < |u| + n2,                                                     (4)

so a single period can serve the whole trapped band n2 < |u| ≤ n1 only if
n1 − n2 < g < 2 n2, i.e.

    λ / (2 n2) < a < λ / (n1 − n2).                                              (5)

For LYSO → grease at 420 nm: 0.14 µm < a < 1.35 µm. For LYSO → air: 0.21 µm < a <
0.52 µm. This is the reason the period must be comparable to the wavelength.

Whether the ray actually escapes is a question of *power*: the grating equation
says which channels are open, the RCWA says how much power goes into each. Power not
transmitted goes into reflected orders (lossless layer). Each reflected order has its
own |u_mn| and so a new direction in the crystal: diffraction breaks the |w|
conservation of derivation 01, which is how the PhC acts on *later* passes too.

### 2c. The other side of the coin
For a ray inside the flat-face cone (|u| < n2) the same orders open: order (−1, 0)
can send it to |u − g| > n2 in reflection, i.e. into a trapped direction. The
transmitted (0, 0) order also has a different strength than the bare Fresnel
coefficient. So a PhC can reduce extraction for rays that would have escaped. The net
effect has to be computed; it is not guaranteed to be positive. This is why the
figure of merit integrates over all angles, not only trapped ones.

### 2d. Very small and very large periods
If g > n1 + n1 (a < λ/(2 n1) ≈ 0.12 µm for LYSO), no order other than (0, 0) can
propagate in either medium for any incidence: the layer is sub-wavelength and acts
like a homogeneous film with an effective index between n_pillar and n2 (effective
medium). It can still act as an anti-reflection coating but it cannot rescue trapped
light. If a ≫ λ, very many orders propagate with small angular steps; the layer acts
more like a rough surface (scattering), and the RCWA needs many Fourier orders.

### 2e. What RCWA computes, and what truncation means
Inside the patterned layer (thickness h, z-invariant) the permittivity ε(x, y) is
expanded in a Fourier series with coefficients ε_pq. Fields are expanded in the same
Bloch harmonics (2). Maxwell's equations become, for each layer, a matrix eigenproblem
of size 2N with N = (2M + 1)² harmonics for orders |m|, |n| ≤ M. Its eigenvectors
are the layer's modes and the eigenvalues their kz. The layers are joined by
continuity of tangential E and H, which gives a scattering matrix (S-matrix) from
input to output harmonics. Truncation at order M is the only approximation for a
lossless z-invariant layer: the result converges as M → ∞, slowly for high-contrast
sharp edges (Gibbs phenomenon in ε_pq). torcwa uses the inverse of the ε Toeplitz
matrix where Maxwell's equations need 1/ε (the "inverse rule"), which is known to
converge reasonably for this TE/TM mix but not optimally (the Li factorisation rules
are not implemented in torcwa 0.1.4.2). We therefore *measure* convergence instead of
assuming it: `scripts/convergence.py`.

The permittivity is sampled on an n_grid × n_grid real-space grid before the FFT.
That is a second discretisation (staircase edge of the circle); it is checked by
doubling n_grid.

### 2f. Power and energy conservation
With power normalisation, |S_mn|² is the fraction of incident power carried by
order (m, n) (ratio of normal Poynting flux, as in derivation 02 eq. 5, now per
order). For lossless media

    Σ_mn T_mn + Σ_mn R_mn = 1,                                                   (6)

which must hold for every incidence and both polarisations, at every truncation.
It is a test, not a convergence criterion: a badly truncated solve can conserve
energy and still be wrong.

### 2g. Unpolarised light and the depolarisation assumption
Scintillation light is unpolarised. For each incidence the solver gives 2 × 2
polarisation blocks (s, p in; s, p out) for each order. The unpolarised power into
order (m, n) is

    P_mn = ½ ( |S_ss|² + |S_ps|² + |S_sp|² + |S_pp|² )_mn,                         (7)

i.e. sum over output polarisation, average over input polarisation.

Assumption: the Monte Carlo (M3) treats light as unpolarised at *every* interaction.
After one reflection off the PhC the light is partially polarised, so this is an
approximation. Its bias direction is not fixed: it overestimates extraction where the
reflected light is preferentially in the polarisation that transmits worse on the
next hit, and underestimates it otherwise. Specular side walls with TIR preserve s and
p power separately, so the error is largest for the bare-wall case. It is the standard
approximation in scintillator ray tracing; tracking polarisation would need the full
2 × 2 data and is noted as a possible extension.

### 2h. C4v symmetry and the fundamental domain
A circular pillar on a square lattice is invariant under the 8 operations of the
group C4v: rotations by 0, 90, 180, 270° and mirrors in the x axis, y axis and the two
diagonals. Each is a 2 × 2 orthogonal integer matrix Q acting on in-plane vectors,
and it maps the reciprocal lattice onto itself: Q G_mn = G_{Q(m,n)}. If the structure
is invariant under Q then, for unpolarised light,

    P_{Q(m,n)}(Q u) = P_{(m,n)}(u),                                              (8)

for both transmission and reflection. (Polarisation states map into each other under
Q, s to s and p to p up to sign, so the unpolarised sum (7) is invariant.) Every
in-plane direction φ can be mapped into the wedge 0 ≤ φ ≤ 45° by one of the 8
operations. The lookup table therefore only needs φ ∈ [0°, 45°], and for any other
φ we find Q with Q⁻¹u in the wedge, look up P_{(m',n')}(Q⁻¹u), and assign that power
to order (m, n) = Q (m', n'). Test: compute φ and 90° − φ directly and check (8).

The discretised ε grid is exactly C4v-symmetric if the grid is symmetric about the
pillar centre (even n_grid, cell-centred samples), and the square truncation
|m|, |n| ≤ M is C4v-invariant, so (8) holds to round-off in the solver too.

### 2i. Lookup table and interpolation
Table axes: θ (polar angle in the crystal) and φ ∈ [0°, 45°]. Entries: P^T_mn and
P^R_mn on a fixed order window |m|, |n| ≤ K, with K large enough to hold every
order that can propagate in the crystal: K ≥ ceil(2 n1 / g). In the Monte Carlo the
table is interpolated bilinearly in (θ, φ). The set of propagating orders changes
abruptly at Rayleigh anomalies (|u_mn| = n_j), so interpolation can assign power to an
order that is evanescent at the exact incidence. The Monte Carlo therefore recomputes
the propagating set from (3) at the exact (θ, φ), drops the others, and renormalises
the remaining powers to sum to 1. Bias: near anomalies power is redistributed among
open channels in proportion to the interpolated values; the error shrinks with grid
step, which is why the final evaluation uses a finer grid.

### 2j. Single-pass extraction from the table
The single-pass extraction through the readout face, averaged over isotropic emission
toward the face, is

    η₁^PhC = (1/4π) ∫ dφ ∫₀^{π/2} sin θ dθ Σ_mn P^T_mn(θ, φ),                       (9)

the PhC version of derivation 02 eq. (7). By C4v, ∫₀^{2π} dφ = 8 ∫₀^{π/4} dφ. Split
into an in-cone part (θ < θc) and a trapped part (θ > θc): the trapped part is the
new light the PhC adds on the first pass; the in-cone part may go down (2c).

### 2k. Thin-film limit (validation)
If the pillar index equals the outside index, or the fill factor is 1, the layer is
a homogeneous film. Then only (0, 0) exists and the answer is the Airy thin-film
formula. With the characteristic-matrix method, for a film of index n_f and thickness
h between n1 and n2, for each polarisation define the tilted admittances
η_j = n_j cos θ_j (s) or n_j / cos θ_j (p), δ = k0 n_f h cos θ_f, and

    [B; C] = [[cos δ, −i sin δ / η_f], [−i η_f sin δ, cos δ]] [1; η_2],
    r = (η_1 B − C) / (η_1 B + C),   T = 4 η_1 Re(η_2) / |η_1 B + C|².           (10)

(Macleod, *Thin-Film Optical Filters*, ch. 2; sign of the off-diagonal terms for
exp(−iωt) chosen so that a decaying evanescent wave has Im η_2 ≥ 0.) The RCWA with a
*uniform* ε grid (which forces torcwa through the general Fourier path, not the
homogeneous shortcut) must reproduce (10). This validates the general eigen-solver
path, the S-matrix assembly and the per-order power normalisation on a case with an
analytic answer.

### 2l. Choice of the reference ("literature-style") design
Knapitsch et al. (2012) used a silicon-nitride photonic-crystal slab on the outcoupling
face of LSO (abstract of doi:10.1109/TNS.2012.2184556); their lattice parameters are
not in the abstract and have not been read from the paper yet (docs/status.md). The
reference design here is therefore *Knapitsch-style*, not a replica:
Si₃N₄ pillars (n from Luke et al. 2015, ≈ 2.09 at 420 nm), square lattice, chosen from
(4)–(5) so that the (−1, 0) order maps the middle of the trapped band into the
centre of the escape cone. For LYSO → grease, the trapped band is
1.5 < |u| < 1.81; g ≈ 1.05 (a = 0.40 µm) sends it to 0.45 < |u − g| < 0.76, well inside
the grease cone (and inside the air cone too). Radius 0.12 µm (area fill factor
π r²/a² ≈ 0.28) and height 0.30 µm are typical values for a single-etch nitride
layer, not optimised. M4 optimises a, r and h.

### 2m. Assumptions and their bias
| Assumption | Bias |
|---|---|
| Infinite periodic layer | Real face is 3 × 3 mm, i.e. ~7500 periods: negligible edge effects. |
| Perfect pillars (vertical walls, exact radius) | Fabrication rounding and sidewall angle usually weaken diffraction: likely overestimates PhC gain. |
| Monochromatic λ = emission peak | The emission band is ~100 nm wide; diffraction angles shift with λ, so a design tuned at one λ is less efficient on average: overestimates gain. |
| Unpolarised at every hit (2g) | Sign not fixed; noted. |
| Fourier truncation at order M | Measured by the convergence study; reported as an uncertainty on T. |
| Lossless Si₃N₄ (k = 0, Luke record has no k) | Slight overestimate of T if the real film absorbs at 420 nm. |

## Part 3 — Check against the scripts

| Quantity | Predicted | Script | Match? |
|---|---|---|---|
| Open transmitted orders at θ = 60°, φ = 0 (Q1) | | | |
| Order M at which total T changes < 1 % | | | |
| η₁^PhC vs η₁^F (bare), LYSO → grease | | | |
| In-cone part with PhC vs bare | | | |

## Part 4 — Check questions

Q1. Why does the PhC need a period comparable to λ? Use (5) to give the window for
BGO → air at 480 nm.

Q2. Equation (6) holds for the truncated solve at every M. Why can the result still be
wrong, and what test catches it?

Q3. The table stores φ only from 0 to 45°. A photon arrives at φ = 120°. Describe step
by step how its transmitted-order powers and directions are obtained.

## Part 5 — Answers

A1. Only orders with |u + g(m,n)| < n2 can carry trapped light out; the window (5)
follows from requiring order (−1, 0) to be open for the whole trapped band. For BGO
(n1 = 2.15) into air (n2 = 1) at 0.48 µm: λ/(2 n2) = 0.24 µm < a < λ/(n1 − n2) =
0.48/1.15 ≈ 0.42 µm. Smaller periods make every first order evanescent (2d); larger
ones leave part of the trapped band without an open channel through (−1, 0), although
higher orders may then help.

A2. Energy conservation is a property of the S-matrix of *any* lossless truncated
system: it checks the bookkeeping (power normalisation, evanescent orders), not
whether the truncated fields represent the true fields. A solve at M = 1 conserves
energy and is still far from converged. The convergence study (vary M and n_grid until
the quantities of interest stop changing) catches truncation error.

A3. u = n1 sin θ (cos 120°, sin 120°). Find the C4v operation Q such that
u' = Q⁻¹ u has azimuth in [0°, 45°]: rotating by −90° gives azimuth 30°, so
Q = rotation by +90°. Look up P_{(m',n')}(θ, 30°) by bilinear interpolation. Assign
each power to order (m, n) = Q(m', n') = (−n', m'). Then compute u_mn = u + g(m, n)
for every order, drop those with |u_mn| ≥ n2 (transmitted) or ≥ n1 (reflected),
renormalise, and pick an outgoing order with probability equal to its power. Its
direction follows from u_mn: in-plane part u_mn / n_j, z part ± sqrt(1 − |u_mn|²/n_j²).
