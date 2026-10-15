"""Analytic Fresnel coefficients for a single flat interface (owner: Claude).

Implements docs/derivations/02-fresnel-and-flat-rcwa.md, equations (2)-(6).
Conventions (AGENTS.md): Born & Wolf sign for r_p, exp(-i omega t), complex index
n + i k with k >= 0 for loss. theta is the angle of incidence in medium 1 (radians).
All functions are vectorised over theta.
"""

from __future__ import annotations

import math

import numpy as np

_Array = np.ndarray


def _cos_theta2(n1: complex, n2: complex, cos1: _Array, sin1: _Array) -> _Array:
    """cos theta_2 from Snell's law, with the branch of the square root chosen so that
    Im(n2 cos theta_2) >= 0, i.e. the transmitted wave decays into medium 2 (eq. 6).
    For real indices beyond the critical angle this gives +i sqrt(...)."""
    sin2 = (n1 / n2) * sin1
    cos2 = np.sqrt(1.0 - sin2 * sin2 + 0j)
    # enforce decaying evanescent / absorbed wave: Im(n2 cos2) >= 0
    flip = np.imag(n2 * cos2) < 0
    cos2 = np.where(flip, -cos2, cos2)
    return cos2


def fresnel_amplitudes(
    n1: complex, n2: complex, theta: float | _Array
) -> tuple[_Array, _Array, _Array, _Array]:
    """Amplitude coefficients (r_s, r_p, t_s, t_p) for light going from n1 into n2 at
    angle theta (radians, measured from the normal in medium 1). Complex arrays."""
    th = np.asarray(theta, dtype=float)
    cos1 = np.cos(th)
    sin1 = np.sin(th)
    cos2 = _cos_theta2(n1, n2, cos1, sin1)
    a, b = n1 * cos1, n2 * cos2
    r_s = (a - b) / (a + b)
    t_s = 2 * a / (a + b)
    c, d = n2 * cos1, n1 * cos2
    r_p = (c - d) / (c + d)
    t_p = 2 * a / (c + d)
    return r_s, r_p, t_s, t_p


def fresnel_power(
    n1: complex, n2: complex, theta: float | _Array
) -> tuple[_Array, _Array, _Array, _Array]:
    """Power coefficients (R_s, R_p, T_s, T_p), eqs. (4)-(5):
    R = |r|^2, T = Re(n2 cos theta_2) / Re(n1 cos theta_1) * |t|^2.
    For lossless media R + T = 1 for each polarisation; beyond the critical angle
    T = 0 and R = 1."""
    th = np.asarray(theta, dtype=float)
    cos1 = np.cos(th)
    sin1 = np.sin(th)
    cos2 = _cos_theta2(n1, n2, cos1, sin1)
    r_s, r_p, t_s, t_p = fresnel_amplitudes(n1, n2, th)
    flux_ratio = np.real(n2 * cos2) / np.real(n1 * cos1)
    r_s2 = np.abs(r_s) ** 2
    r_p2 = np.abs(r_p) ** 2
    t_s2 = flux_ratio * np.abs(t_s) ** 2
    t_p2 = flux_ratio * np.abs(t_p) ** 2
    return r_s2, r_p2, t_s2, t_p2


def brewster_angle(n1: float, n2: float) -> float:
    """Brewster angle tan theta_B = n2 / n1 (radians), eq. in 2e."""
    return math.atan2(n2, n1)


def unpolarised_transmittance(n1: complex, n2: complex, theta: float | _Array) -> _Array:
    """(T_s + T_p) / 2 for unpolarised light."""
    _, _, t_s, t_p = fresnel_power(n1, n2, theta)
    return 0.5 * (t_s + t_p)


def escape_fraction_one_face_fresnel(n1: float, n2: float, n_theta: int = 20001) -> float:
    """Single-pass escape fraction through one face including Fresnel transmission,
    eq. (7): integral over the hemisphere of (T_s + T_p)/2 * (1/2) sin theta dtheta.
    Trapezoidal rule on n_theta points over [0, pi/2]; T is exactly 0 beyond the
    critical angle so the integrand is continuous there (it goes to 0 at theta_c)."""
    th = np.linspace(0.0, math.pi / 2, n_theta)
    integrand = unpolarised_transmittance(n1, n2, th) * 0.5 * np.sin(th)
    return float(np.trapezoid(integrand, th))


def thin_film_power(
    n1: float,
    n_film: complex,
    n2: complex,
    thickness_um: float,
    wavelength_um: float,
    theta: float | _Array,
) -> tuple[_Array, _Array, _Array, _Array]:
    """(R_s, R_p, T_s, T_p) of one homogeneous film between a lossless incident medium
    n1 and exit medium n2, characteristic-matrix method (derivation 03, eq. 10).
    Convention exp(-i omega t): decaying waves have Im(n cos theta) >= 0."""
    th = np.asarray(theta, dtype=float)
    cos1 = np.cos(th) + 0j
    sin1 = np.sin(th)
    cos_f = _cos_theta2(n1, n_film, np.cos(th), sin1)
    cos_2 = _cos_theta2(n1, n2, np.cos(th), sin1)
    k0 = 2 * np.pi / wavelength_um
    delta = k0 * n_film * thickness_um * cos_f
    out = []
    for pol in ("s", "p"):
        if pol == "s":
            e1, ef, e2 = n1 * cos1, n_film * cos_f, n2 * cos_2
        else:
            e1, ef, e2 = n1 / cos1, n_film / cos_f, n2 / cos_2
        b = np.cos(delta) - 1j * np.sin(delta) / ef * e2
        c = -1j * ef * np.sin(delta) + np.cos(delta) * e2
        r = (e1 * b - c) / (e1 * b + c)
        t = 4 * np.real(e1) * np.real(e2) / np.abs(e1 * b + c) ** 2
        out.append((np.abs(r) ** 2, t))
    (r_s, t_s), (r_p, t_p) = out
    return r_s, r_p, t_s, t_p
