"""Analytic baseline: escape cone and trapping (owner: Claude).

PHYSICS GATE: the bodies of these functions are intentionally left as
``NotImplementedError`` until Aziz has written
docs/derivations/01-escape-cone-and-trapping.md (AGENTS.md, Teaching protocol).
The signatures and docstrings fix the interface so tests and the cross-check
package (src/phcscint/xcheck, owner Argon) can be written now.

Conventions: see AGENTS.md. theta is the polar angle from the readout-face normal.
"""

from __future__ import annotations

import numpy as np

_GATE_MSG = (
    "physics gate: write docs/derivations/01-escape-cone-and-trapping.md first "
    "(AGENTS.md, Teaching protocol)"
)


def critical_angle(n1: float, n2: float) -> float:
    """Critical angle (radians) for light going from index n1 into n2 < n1.

    theta_c = arcsin(n2 / n1). Raises ValueError if n2 >= n1 (no total internal
    reflection; every direction escapes).
    """
    raise NotImplementedError(_GATE_MSG)


def escape_fraction_one_face(n1: float, n2: float) -> float:
    """Fraction of isotropically emitted photons that hit ONE flat face inside its
    escape cone: eta_1 = (1 - cos theta_c) / 2.

    Assumptions (to be stated in the derivation): no Fresnel loss inside the cone,
    no bulk absorption, single pass, point source. Returns a value in [0, 0.5].
    """
    raise NotImplementedError(_GATE_MSG)


def is_trapped(direction: np.ndarray, n1: float, n2: float) -> np.ndarray:
    """Boolean mask: True where a unit direction vector (..., 3) lies outside the
    escape cone of a z-face, i.e. n1 * sin(theta) > n2 with cos(theta) = |d_z|.
    """
    raise NotImplementedError(_GATE_MSG)


def reflect_specular(direction: np.ndarray, face_normal_axis: int) -> np.ndarray:
    """Specular reflection of unit direction vectors (..., 3) from a face whose
    normal is along axis 0 (x), 1 (y) or 2 (z): flips the sign of that component.

    This is the operation behind "trapped rays stay trapped": |d_z| is conserved.
    """
    raise NotImplementedError(_GATE_MSG)
