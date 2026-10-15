"""Analytic baseline: escape cone and trapping (owner: Claude).

Implements docs/derivations/01-escape-cone-and-trapping.md. Equation numbers below
refer to that file. Conventions: AGENTS.md. theta is the polar angle from the
readout-face normal; direction vectors are (u, v, w) with w along the bar axis.
"""

from __future__ import annotations

import math

import numpy as np


def critical_angle(n1: float, n2: float) -> float:
    """Critical angle (radians) for light going from index n1 into n2 < n1, eq. (1):
    sin theta_c = n2 / n1. Raises ValueError if n2 >= n1 (no total internal
    reflection) or if either index is non-positive."""
    if n1 <= 0 or n2 <= 0:
        raise ValueError("refractive indices must be positive")
    if n2 >= n1:
        raise ValueError(f"no total internal reflection for n2={n2} >= n1={n1}")
    return math.asin(n2 / n1)


def escape_fraction_one_face(n1: float, n2: float) -> float:
    """Fraction of isotropically emitted photons whose direction lies inside the escape
    cone of ONE flat face, eq. (4): eta_1 = (1 - sqrt(1 - (n2/n1)^2)) / 2.

    Assumptions (derivation 01, 2d): no Fresnel loss inside the cone, no absorption,
    single pass, isotropic point source. Returns a value in [0, 0.5].
    """
    theta_c = critical_angle(n1, n2)
    return 0.5 * (1.0 - math.cos(theta_c))


def is_trapped(direction: np.ndarray, n1: float, n2: float) -> np.ndarray:
    """Boolean mask, True where a unit direction vector (..., 3) lies outside the escape
    cone of a z-face: |w| < cos theta_c, equivalently n1 sin theta > n2 (derivation 01,
    2e). The boundary |w| == cos theta_c counts as not trapped."""
    d = np.asarray(direction, dtype=float)
    cos_theta_c = math.cos(critical_angle(n1, n2))
    return np.abs(d[..., 2]) < cos_theta_c


def reflect_specular(direction: np.ndarray, face_normal_axis: int) -> np.ndarray:
    """Specular reflection of unit direction vectors (..., 3) from a face whose normal
    is along axis 0 (x), 1 (y) or 2 (z): flips the sign of that component, eq. (5).
    Returns a new array; the input is not modified."""
    if face_normal_axis not in (0, 1, 2):
        raise ValueError("face_normal_axis must be 0, 1 or 2")
    out = np.array(direction, dtype=float, copy=True)
    out[..., face_normal_axis] *= -1.0
    return out


def cones_overlap(n1: float, n2: float) -> bool:
    """True if the escape cones of two perpendicular faces with the same outside index
    n2 overlap, i.e. theta_c > 45 deg, i.e. n2/n1 > 1/sqrt(2) (derivation 01, 2f)."""
    return critical_angle(n1, n2) > math.pi / 4


def escapable_fraction_cuboid(n1: float, n2_faces: tuple[float, ...] | None = None) -> float:
    """Total fraction of isotropic directions lying in the escape cone of at least one
    face of a cuboid with specular lossless walls (derivation 01, 2e-2f).

    n2_faces: outside index for the six faces in the order (-x, +x, -y, +y, -z, +z);
    None means all faces into air (n2 = 1). Faces with n2 >= n1 count as fully open
    (eta_1 = 0.5 for that face). If any pair of cones can overlap the sum would be
    wrong, so this function raises ValueError in that case; use the Monte Carlo (M3)
    for overlapping cones.
    """
    if n2_faces is None:
        n2_faces = (1.0,) * 6
    if len(n2_faces) != 6:
        raise ValueError("n2_faces must have six entries")
    cos_c = []
    for n2 in n2_faces:
        if n2 >= n1:
            cos_c.append(0.0)
        else:
            cos_c.append(math.cos(critical_angle(n1, n2)))
    # Overlap between the cones of faces with normals along different axes requires
    # cos_c(a)^2 + cos_c(b)^2 < 1 for some pair of perpendicular faces (derivation 01,
    # 2f). Opposite faces (same axis) never overlap because |w| cannot exceed 1 twice.
    axes = {0: (0, 1), 1: (2, 3), 2: (4, 5)}
    for a in range(3):
        for b in range(a + 1, 3):
            for ia in axes[a]:
                for ib in axes[b]:
                    if cos_c[ia] ** 2 + cos_c[ib] ** 2 < 1.0:
                        raise ValueError(
                            "escape cones overlap; closed-form sum is invalid "
                            f"(faces {ia} and {ib})"
                        )
    return sum(0.5 * (1.0 - c) for c in cos_c)
