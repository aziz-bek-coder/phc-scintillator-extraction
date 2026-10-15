"""torcwa wrappers (owner: Claude).

M1: flat-interface solve used to validate conventions against Fresnel
(docs/derivations/02-fresnel-and-flat-rcwa.md, 2g). M2 adds the patterned layer.

Conventions (AGENTS.md): the input layer is the scintillator (light travels from the
crystal outward, +z), the output layer is the outside medium; the incidence angle is
defined in the input layer; eps = n**2 with torcwa's exp(-j omega t) convention.
Lengths in micrometres.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
import torcwa

CPU = torch.device("cpu")


@dataclass(frozen=True)
class FlatResult:
    """Power coefficients from a zero-order RCWA of a flat interface."""

    R_s: float
    R_p: float
    T_s: float
    T_p: float
    R_sp: float  # cross-polarised terms; must be ~0 for an isotropic flat interface
    R_ps: float
    T_sp: float
    T_ps: float


def _power(sim: torcwa.rcwa, port: str, pol: str) -> float:
    s = sim.S_parameters(
        orders=[0, 0], direction="forward", port=port, polarization=pol, power_norm=True
    )
    return float(abs(complex(s.reshape(-1)[0].item())) ** 2)


def flat_interface(
    n1: float,
    n2: float,
    wavelength_um: float,
    theta: float,
    phi: float = 0.0,
    *,
    dtype: torch.dtype = torch.complex128,
    period_um: float = 1.0,
) -> FlatResult:
    """Zero-order torcwa solve of a flat n1 -> n2 interface at polar angle theta and
    azimuth phi (radians, defined in medium n1). The lattice period is arbitrary
    for a homogeneous structure and only sets the (unused) reciprocal vector.

    One zero-thickness homogeneous layer of medium n1 is inserted so the global
    S-matrix assembly follows torcwa's documented path (docs/decisions.md).
    """
    sim = torcwa.rcwa(
        freq=1.0 / wavelength_um, order=[0, 0], L=[period_um, period_um], dtype=dtype, device=CPU
    )
    sim.add_input_layer(eps=n1**2)
    sim.add_output_layer(eps=n2**2)
    sim.set_incident_angle(inc_ang=float(theta), azi_ang=float(phi), angle_layer="input")
    sim.add_layer(thickness=0.0, eps=n1**2)
    sim.solve_global_smatrix()
    return FlatResult(
        R_s=_power(sim, "reflection", "ss"),
        R_p=_power(sim, "reflection", "pp"),
        T_s=_power(sim, "transmission", "ss"),
        T_p=_power(sim, "transmission", "pp"),
        R_sp=_power(sim, "reflection", "sp"),
        R_ps=_power(sim, "reflection", "ps"),
        T_sp=_power(sim, "transmission", "sp"),
        T_ps=_power(sim, "transmission", "ps"),
    )


def flat_interface_sweep(
    n1: float,
    n2: float,
    wavelength_um: float,
    thetas: np.ndarray,
    phi: float = 0.0,
    *,
    dtype: torch.dtype = torch.complex128,
) -> dict[str, np.ndarray]:
    """Vectorised-by-loop sweep over polar angles; returns arrays keyed like FlatResult."""
    rows = [flat_interface(n1, n2, wavelength_um, float(t), phi, dtype=dtype) for t in thetas]
    keys = ("R_s", "R_p", "T_s", "T_p", "R_sp", "R_ps", "T_sp", "T_ps")
    return {k: np.array([getattr(r, k) for r in rows]) for k in keys}
