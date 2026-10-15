# 01 — Escape cone and trapping in an ideal cuboid

Author: Aziz. Status: **predict exercise issued 2026-10-15, derivation not yet written.**
`phcscint.analytic` stays a stub until Part 2 is filled in.

## Part 1 — Predict (write this before deriving anything)

Setup: a point source inside a scintillator of index n1 emits isotropically. One face
is flat and in contact with a medium of index n2 < n1. Ignore Fresnel reflection
inside the cone (treat every ray inside the escape cone as fully transmitted) and
ignore absorption.

Answer in one or two sentences each, with a number where asked:

1. What fraction of the emitted photons hits *this one face* inside the escape cone,
   as a function of n1 and n2? Guess the number for LYSO→air before computing it.
2. Will LYSO→grease (n2 = 1.5) give a *larger* or *smaller* fraction than LYSO→air, and
   roughly by what factor?
3. If the crystal is a long rectangular bar (3×3×20 mm) with perfectly specular,
   lossless, bare walls, and a photon is emitted outside the escape cone of the
   readout face, can it ever reach the photodetector? Yes or no, and the one-line
   reason.
4. Six faces, all bare, all into air: what total fraction escapes somewhere on the
   first pass? Is it simply 6 × η₁? Why or why not?

## Part 2 — Derivation (the physics gate)

Fill in, by hand, in your own words. Suggested structure:

### 2a. Escape-cone fraction through one face
- Define the critical angle θc from Snell's law at grazing exit.
- Write the solid angle of a cone of half-angle θc.
- Isotropic emission: probability per unit solid angle is 1/(4π). Integrate over the cone.
- Show that η₁ = (1 − cos θc)/2 and that cos θc = sqrt(1 − (n2/n1)²).
- State the two approximations made (no Fresnel loss inside the cone, no absorption)
  and which direction each one pushes the true answer.

### 2b. Trapped rays stay trapped in an ideal cuboid
- Write the ray direction as unit vector (u, v, w) = (sin θ cos φ, sin θ sin φ, cos θ)
  with z along the bar axis toward the readout face.
- State what a specular reflection from a face perpendicular to x does to (u, v, w).
  Same for y and z faces.
- Show that |w| is unchanged by every reflection, so the angle to the readout-face
  normal is conserved: a ray with |w| < cos θc never enters the escape cone of the
  z faces.
- Say what happens to the *side* faces: the ray is also tested against their escape
  cones, with |u| and |v| conserved. Conclude: the set of rays that can ever escape
  is fixed at emission.
- One sentence on what breaks this: roughness, Lambertian wrapping, absorption,
  and a periodic layer that adds k∥ → k∥ + G.

### 2c. Connect to the project
- Why does conserved |w| mean a flat readout face cannot help timing either?
- In one sentence: what must the photonic-crystal layer change for a trapped ray?

## Part 3 — Check (fill after `scripts/escape_cone.py` exists)

| Case | Predicted (Part 1) | Script result | Match? |
|---|---|---|---|
| LYSO (n1 = 1.82) → air | | | |
| LYSO → n2 = 1.5 | | | |
| BGO (n1 = 2.15) → air | | | |

What surprised me:
