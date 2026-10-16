"""Analytic transport-time expectations and figures of merit (owner: Claude).

Implements docs/derivations/04-monte-carlo-pixel.md, sections 2c, 2f and 2i.
Times in ps, lengths in micrometres.
"""

from __future__ import annotations

import math
from collections.abc import Callable

import numpy as np

from phcscint.fresnel import fresnel_power

C_UM_PER_PS = 299.792458

# A function of |w| = cos(theta) returning an unpolarised power coefficient.
AngularCoefficient = Callable[[np.ndarray], np.ndarray]


def fresnel_T(n1: float, n2: float) -> AngularCoefficient:
    """Unpolarised Fresnel transmittance n1 -> n2 as a function of cos(theta)."""

    def f(cos_t: np.ndarray) -> np.ndarray:
        th = np.arccos(np.clip(cos_t, 0.0, 1.0))
        _, _, ts, tp = fresnel_power(n1, n2, th)
        return 0.5 * (ts + tp)

    return f


def fresnel_R(n1: float, n2: float) -> AngularCoefficient:
    """Unpolarised Fresnel reflectance n1 -> n2 as a function of cos(theta)."""
    t = fresnel_T(n1, n2)
    return lambda cos_t: 1.0 - t(cos_t)


def mirror(cos_t: np.ndarray) -> np.ndarray:
    return np.ones_like(np.asarray(cos_t, dtype=float))


def direct_transit_ps(lz_um: float, n_group: float) -> float:
    """Time to travel the bar length along its axis, eq. (1) of derivation 04."""
    return n_group * lz_um / C_UM_PER_PS


def specular_box_cdf(
    t_ps: np.ndarray | float,
    *,
    n_group: float,
    lz_um: float,
    readout_T: AngularCoefficient,
    back_R: AngularCoefficient = mirror,
    abs_length_um: float = math.inf,
    n_w: int = 20000,
) -> np.ndarray:
    """Detected-time CDF per emitted photon for a box whose side faces keep |w|
    (derivation 04, eqs. 4-5, with absorption as in 2f). Pass t = inf for eq. (6).

    The z-distance travelled before the k-th readout hit is uniform on
    [o_k Lz, (o_k + 1) Lz] with o_k = 2k (w > 0) or 2k + 1 (w < 0); the path is that
    distance divided by |w|. Midpoint rule in |w| with n_w points."""
    t = np.atleast_1d(np.asarray(t_ps, dtype=float))
    if np.isinf(t).any() and np.isfinite(t).any():
        raise ValueError("evaluate t = inf separately from finite times")
    s = np.where(np.isinf(t), np.inf, t * C_UM_PER_PS / n_group)  # path budget per t
    w = (np.arange(n_w) + 0.5) / n_w  # |w| midpoints on (0, 1)
    dw = 1.0 / n_w
    tr = readout_T(w)
    rr = 1.0 - tr
    rb = back_R(w)
    q = rr * rb  # survival factor per round trip
    lz = lz_um
    out = np.zeros_like(t)
    finite_s = s[np.isfinite(s)]
    s_max = finite_s.max() if finite_s.size else math.inf
    if math.isfinite(s_max):
        k_max = int(math.ceil(s_max / (2 * lz))) + 1
    else:
        # enough terms that q^k is negligible for every |w| with T > 0, or, without
        # absorption, use the closed-form sum below
        k_max = None

    def term(o: int) -> np.ndarray:
        """E_z[ exp(-L/l) 1(L <= s) ] for distance window [o Lz, (o+1) Lz]; shape (n_w, n_t)."""
        lo = o * lz
        hi = (o + 1) * lz
        dmax = np.clip(w[:, None] * s[None, :], lo, hi)  # upper limit of D
        if math.isinf(abs_length_um):
            return (dmax - lo) / lz
        a = w[:, None] * abs_length_um
        return (a / lz) * (np.exp(-lo / a) - np.exp(-dmax / a))

    if k_max is None and math.isinf(abs_length_um):
        # t = inf, no absorption: eq. (6) in closed form
        with np.errstate(divide="ignore", invalid="ignore"):
            geo = np.where(tr > 0, tr / (1.0 - q), 0.0)
        val = 0.5 * np.sum(geo * (1.0 + rb)) * dw
        return np.full_like(t, val)
    if k_max is None:
        k_max = 400  # absorption makes the series converge; 400 round trips = 16 m
    for k in range(k_max + 1):
        qk = q**k
        if not np.any(qk * tr > 1e-15):
            break
        a_plus = tr * qk  # w > 0
        a_minus = rb * tr * qk  # w < 0
        out += 0.5 * dw * (a_plus @ term(2 * k) + a_minus @ term(2 * k + 1))
    return out


def cdf_from_times(times_ps: np.ndarray, n_emitted: int, t_grid: np.ndarray) -> np.ndarray:
    """F(t) = N_det(t' <= t) / N_emitted (derivation 04, 2i)."""
    ts = np.sort(np.asarray(times_ps, dtype=float))
    return np.searchsorted(ts, np.asarray(t_grid, dtype=float), side="right") / n_emitted


def binomial_sigma(p: np.ndarray | float, n: int) -> np.ndarray:
    p = np.asarray(p, dtype=float)
    return np.sqrt(np.clip(p * (1 - p), 0, None) / n)
