"""First-pass early-photon yield of the pixel (derivation 05, eqs. 1, 1a and 1b).

Below twice the direct transit time, t_dir = n_g Lz / c, a photon can be detected only
on its first readout hit: a photon reflected by the readout must travel at least 2 Lz
more. The yield E(tau) is then an angular integral of the first-pass transmission T of
the readout, with a weight that counts how many emission points reach the readout
within the path budget s_tau = c tau / n_g:
- photons emitted toward the readout travel L in [0, Lz / cos(theta)];
- photons emitted toward the back face travel L in [Lz / cos(theta), 2 Lz / cos(theta)]
  and are reflected once by the back face.
Losses on the way are the side faces (eq. 1a) and the back face, for air-gap mirror
wraps of reflectivity rho; rho = None means lossless mirrors. Side faces must keep |d_z|
(specular reflection), and there is no bulk absorption.
"""

from __future__ import annotations

import math
from collections.abc import Callable

import numpy as np

from phcscint.fresnel import unpolarised_transmittance
from phcscint.timing import C_UM_PER_PS


def wrap_return(n1: float, cos_t: np.ndarray, rho: float, n_gap: float = 1.0) -> np.ndarray:
    """Return probability of a polished face with an air gap and a mirror of reflectivity
    rho, at incidence cosine cos_t (derivation 04): 1 under total internal reflection,
    else R + T^2 rho / (1 - rho R) with R, T the unpolarised Fresnel powers."""
    t = unpolarised_transmittance(n1, n_gap, np.arccos(np.clip(cos_t, 0.0, 1.0)))
    r = 1.0 - t
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(t <= 0.0, 1.0, r + t * t * rho / (1.0 - rho * r))


def side_survival(
    n1: float, d: np.ndarray, path: np.ndarray, rho: float, lx_um: float, ly_um: float
) -> np.ndarray:
    """Probability of surviving the four side faces after a path `path` (1-D), for
    directions d (N, 3), averaged over the uniform start position (derivation 05, 1a):
    along x the photon meets a face floor(D) or floor(D) + 1 times, D = L |d_x| / Lx."""
    out = np.ones((d.shape[0], path.size))
    for axis, width in ((0, lx_um), (1, ly_um)):
        c = np.abs(d[:, axis])
        p = wrap_return(n1, c, rho)[:, None]
        dist = path[None, :] * c[:, None] / width
        k = np.floor(dist)
        f = dist - k
        out *= p**k * (1 - f + f * p)
    return out


def first_pass_yield(
    transmission: Callable[[np.ndarray], np.ndarray],
    n1: float,
    tau_ps: float,
    *,
    lx_um: float,
    ly_um: float,
    lz_um: float,
    rho: float | None = None,
    n_group: float | None = None,
    n_theta: int = 450,
    n_phi: int = 90,
    n_path: int = 400,
) -> float:
    """E(tau), photons detected by tau per emitted photon, for tau < 2 t_dir
    (derivation 05, eq. 1b). transmission(d) is the first-pass transmission for unit
    directions d (N, 3) heading to the readout; it must have the C4v symmetry of the
    lattice, because the integral runs over the wedge 0 <= phi <= 45 deg (times 8).
    Midpoint rules in theta, phi and path length."""
    s = C_UM_PER_PS * tau_ps / (n_group or n1)
    if s >= 2 * lz_um:
        raise ValueError("first_pass_yield needs tau below twice the direct transit time")
    th = (np.arange(n_theta) + 0.5) * (math.pi / 2) / n_theta
    ph = (np.arange(n_phi) + 0.5) * (math.pi / 4) / n_phi
    jac = 8 * (math.pi / 2 / n_theta) * (math.pi / 4 / n_phi) / (4 * math.pi)
    total = 0.0
    for t in th:
        c = math.cos(t)
        d = np.stack([np.sin(t) * np.cos(ph), np.sin(t) * np.sin(ph), np.full(n_phi, c)], 1)
        tr = np.asarray(transmission(d), dtype=float) * math.sin(t) * jac
        l1 = lz_um / c  # forward paths end here, backward paths start here
        l_max = min(s, 2 * l1)
        path = (np.arange(n_path) + 0.5) * l_max / n_path
        if rho is None:
            surv = np.ones((n_phi, n_path))
            back = 1.0
        else:
            surv = side_survival(n1, d, path, rho, lx_um, ly_um)
            back = float(wrap_return(n1, np.array([c]), rho)[0])
        leg = np.where(path <= l1, 1.0, back)  # backward emission: one back-face return
        w = (c / lz_um) * (surv * leg[None, :]).sum(axis=1) * (l_max / n_path)
        total += float(np.sum(tr * w))
    return total
