"""Differentiable early-photon objective and gradient-based design (owner: Claude).

Implements docs/derivations/05-early-photon-objective.md.

The pillar layer enters RCWA through the exact Fourier coefficients of a disk
(derivation 05, eq. 4), with J1 evaluated by the periodic trapezoid rule
J1(x) = (1/2pi) int_{-pi}^{pi} cos(tau - x sin tau) dtau, which is exact to round-off
for the arguments used here and differentiable with torch autograd. Everything runs in
normalised units: the length unit is the lattice period a, the frequency is a / lambda,
the radius is r / a and the height h / a. That makes the period differentiable too.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np
import torch
import torcwa

CPU = torch.device("cpu")
C_UM_PER_PS = 299.792458
_N_TAU = 160  # trapezoid points for J1; exact to ~1e-15 for x <= 80 (tested)


# ---------------------------------------------------------------- Fourier coefficients


def bessel_j1(x: torch.Tensor) -> torch.Tensor:
    """J1(x) by the periodic trapezoid rule; differentiable, any tensor shape."""
    tau = torch.arange(_N_TAU, dtype=torch.float64) * (2 * math.pi / _N_TAU) - math.pi
    return torch.cos(tau - x.unsqueeze(-1) * torch.sin(tau)).mean(dim=-1)


def disk_convolution_matrix(
    order: int, rho: torch.Tensor, eps_pillar: float, eps_background: float
) -> torch.Tensor:
    """Toeplitz permittivity matrix of a disk of radius rho * a centred in a square cell
    of side a, for Fourier orders |m|, |n| <= order in torcwa's m-major ordering.

    eps_(dm, dn) = eps_b delta + (eps_p - eps_b) f 2 J1(|G| r) / (|G| r) (-1)^(dm + dn),
    with f = pi rho^2 and |G| r = 2 pi rho sqrt(dm^2 + dn^2). The sign factor places the
    disk at the cell centre (a/2, a/2), as phcscint.rcwa.pillar_permittivity does, so
    the two paths can be compared directly."""
    r = torch.arange(-order, order + 1)
    mm, nn = torch.meshgrid(r, r, indexing="ij")
    m = mm.reshape(-1)
    n = nn.reshape(-1)
    dm = (m[:, None] - m[None, :]).to(torch.float64)
    dn = (n[:, None] - n[None, :]).to(torch.float64)
    q = torch.sqrt(dm**2 + dn**2)
    x = 2 * math.pi * rho * q
    zero = q == 0
    x_safe = torch.where(zero, torch.ones_like(x), x)
    airy = torch.where(zero, torch.ones_like(x), 2 * bessel_j1(x_safe) / x_safe)
    f = math.pi * rho**2
    sign = torch.where(((dm + dn) % 2) == 0, 1.0, -1.0).to(torch.float64)
    eps = (eps_pillar - eps_background) * f * airy * sign
    eps = eps + eps_background * torch.eye(m.numel(), dtype=torch.float64)
    return eps.to(torch.complex128)


class AnalyticLayerRCWA(torcwa.rcwa):
    """torcwa.rcwa that also accepts a precomputed permittivity convolution matrix."""

    def add_layer_conv(self, thickness, eps_conv: torch.Tensor) -> None:
        self.eps_conv.append(eps_conv)
        self.mu_conv.append(torch.eye(self.order_N, dtype=self._dtype, device=self._device))
        self.layer_N += 1
        self.thickness.append(thickness)
        self._eigen_decomposition()
        self._solve_layer_smatrix()


# ------------------------------------------------------------- design and transmission


@dataclass(frozen=True)
class Bounds:
    period_um: tuple[float, float] = (0.20, 1.00)
    fill: tuple[float, float] = (0.05, 0.60)
    height_um: tuple[float, float] = (0.05, 0.80)


def to_physical(x: torch.Tensor, bounds: Bounds) -> tuple[torch.Tensor, ...]:
    """Unconstrained x (3,) -> (period, fill factor, height) inside the bounds."""
    s = torch.sigmoid(x)
    lo = torch.tensor(
        [bounds.period_um[0], bounds.fill[0], bounds.height_um[0]], dtype=torch.float64
    )
    hi = torch.tensor(
        [bounds.period_um[1], bounds.fill[1], bounds.height_um[1]], dtype=torch.float64
    )
    p = lo + (hi - lo) * s
    return p[0], p[1], p[2]


def to_unconstrained(period: float, fill: float, height: float, bounds: Bounds) -> torch.Tensor:
    def logit(v: float, lo: float, hi: float) -> float:
        t = (v - lo) / (hi - lo)
        t = min(max(t, 1e-9), 1 - 1e-9)
        return math.log(t / (1 - t))

    return torch.tensor(
        [
            logit(period, *bounds.period_um),
            logit(fill, *bounds.fill),
            logit(height, *bounds.height_um),
        ],
        dtype=torch.float64,
    )


def transmission(
    n1: float,
    n2: float,
    wavelength_um: float,
    n_pillar: float,
    period_um: torch.Tensor | float,
    fill: torch.Tensor | float,
    height_um: torch.Tensor | float,
    theta: float,
    phi: float,
    *,
    order: int = 5,
) -> torch.Tensor:
    """Unpolarised total transmission into the outside medium (sum over orders, average
    over input polarisation), differentiable in period, fill factor and height."""
    a = torch.as_tensor(period_um, dtype=torch.float64)
    f = torch.as_tensor(fill, dtype=torch.float64)
    h = torch.as_tensor(height_um, dtype=torch.float64)
    rho = torch.sqrt(f / math.pi)
    sim = AnalyticLayerRCWA(
        freq=a / wavelength_um,
        order=[order, order],
        L=[1.0, 1.0],
        dtype=torch.complex128,
        device=CPU,
    )
    sim.add_input_layer(eps=n1**2)
    sim.add_output_layer(eps=n2**2)
    sim.set_incident_angle(inc_ang=float(theta), azi_ang=float(phi), angle_layer="input")
    sim.add_layer_conv(h / a, disk_convolution_matrix(order, rho, n_pillar**2, n2**2))
    sim.solve_global_smatrix()
    # Only orders that propagate in the outside medium (derivation 03, eq. 3). Evanescent
    # orders carry no power, and asking torcwa for them puts sqrt(kz = 0) into the
    # power normalisation, whose derivative is infinite (0 * inf = NaN in backward).
    r = np.arange(-order, order + 1)
    mm, nn = np.meshgrid(r, r, indexing="ij")
    orders = np.stack([mm.ravel(), nn.ravel()], axis=1)
    g = wavelength_um / float(a.detach())
    u = n1 * math.sin(theta) * np.array([math.cos(phi), math.sin(phi)])
    umn = np.hypot(u[0] + g * orders[:, 0], u[1] + g * orders[:, 1])
    orders = orders[umn < n2 * (1 - 1e-9)]
    total = torch.zeros((), dtype=torch.float64)
    if orders.size == 0:
        return total
    for pol in ("ss", "ps", "sp", "pp"):
        s = sim.S_parameters(
            orders=torch.tensor(orders.copy(), dtype=torch.int64),
            direction="forward",
            port="transmission",
            polarization=pol,
            power_norm=True,
        )
        total = total + torch.sum(s.real**2 + s.imag**2)
    return 0.5 * total


# ----------------------------------------------------------------------------- objective


def early_weight(tau_ps: float, lz_um: float, n_group: float) -> Callable[[float], float]:
    """Derivation 05, eq. (1): probability that a photon emitted toward the readout at
    polar angle theta reaches it within tau, min(1, s_tau cos(theta) / Lz)."""
    s = C_UM_PER_PS * tau_ps / n_group
    return lambda theta: min(1.0, s * math.cos(theta) / lz_um)


@dataclass(frozen=True)
class AngleGrid:
    """Midpoints in theta over [0, 90] deg and in phi over the C4v wedge [0, 45] deg
    (midpoints avoid the mirror-symmetric planes phi = 0 and 45 deg)."""

    n_theta: int = 18
    n_phi: int = 4

    def points(self) -> list[tuple[float, float, float]]:
        """(theta, phi, solid-angle weight / 4 pi) for the hemisphere, using C4v."""
        dth = (math.pi / 2) / self.n_theta
        dph = (math.pi / 4) / self.n_phi
        pts = []
        for i in range(self.n_theta):
            th = (i + 0.5) * dth
            for j in range(self.n_phi):
                ph = (j + 0.5) * dph
                pts.append((th, ph, 8 * math.sin(th) * dth * dph / (4 * math.pi)))
        return pts


def objective(
    weight: Callable[[float], float],
    n1: float,
    n2: float,
    wavelength_um: float,
    n_pillar: float,
    period_um,
    fill,
    height_um,
    grid: AngleGrid,
    *,
    order: int = 5,
    backward: bool = False,
) -> float:
    """J = sum over the grid of w(theta) T(theta, phi) dOmega / (4 pi) (derivation 05,
    eq. 3). With backward=True the gradient is accumulated into the .grad of whichever
    inputs require it, one incidence at a time, so memory stays bounded."""
    total = 0.0
    for th, ph, dw in grid.points():
        w = weight(th) * dw
        if w == 0.0:
            continue
        t = transmission(
            n1, n2, wavelength_um, n_pillar, period_um, fill, height_um, th, ph, order=order
        )
        term = w * t
        if backward:
            term.backward()
        total += float(term.detach())
    return total


def bare_objective(
    weight: Callable[[float], float], n1: float, n2: float, grid: AngleGrid
) -> float:
    """Same quadrature with the flat-face Fresnel transmission, for comparison."""
    from phcscint.fresnel import unpolarised_transmittance

    return sum(
        weight(th) * dw * float(unpolarised_transmittance(n1, n2, th))
        for th, _, dw in grid.points()
    )


def adam_step(
    x: torch.Tensor, grad: torch.Tensor, state: dict, lr: float, maximise: bool = True
) -> torch.Tensor:
    """One Adam update on the unconstrained variables (plain tensors, no autograd)."""
    b1, b2, eps = 0.9, 0.999, 1e-8
    g = -grad if maximise else grad
    state["t"] = state.get("t", 0) + 1
    state["m"] = b1 * state.get("m", torch.zeros_like(x)) + (1 - b1) * g
    state["v"] = b2 * state.get("v", torch.zeros_like(x)) + (1 - b2) * g * g
    m_hat = state["m"] / (1 - b1 ** state["t"])
    v_hat = state["v"] / (1 - b2 ** state["t"])
    return x - lr * m_hat / (torch.sqrt(v_hat) + eps)


def evaluate_with_gradient(
    x: torch.Tensor,
    bounds: Bounds,
    weight: Callable[[float], float],
    n1: float,
    n2: float,
    wavelength_um: float,
    n_pillar: float,
    grid: AngleGrid,
    order: int,
) -> tuple[float, torch.Tensor, tuple[float, float, float]]:
    """Objective, its gradient with respect to the unconstrained x, and the physical
    parameters (period, fill, height)."""
    xg = x.detach().clone().requires_grad_(True)
    a, f, h = to_physical(xg, bounds)
    # accumulate d J / d (a, f, h) per incidence, then chain to x
    a_l = a.detach().clone().requires_grad_(True)
    f_l = f.detach().clone().requires_grad_(True)
    h_l = h.detach().clone().requires_grad_(True)
    j = objective(
        weight, n1, n2, wavelength_um, n_pillar, a_l, f_l, h_l, grid, order=order, backward=True
    )
    g_phys = torch.stack([a_l.grad, f_l.grad, h_l.grad])
    torch.autograd.backward(torch.stack([a, f, h]), g_phys)
    return j, xg.grad.detach().clone(), (float(a.detach()), float(f.detach()), float(h.detach()))


def optimise(
    start: Sequence[float],
    bounds: Bounds,
    weight: Callable[[float], float],
    n1: float,
    n2: float,
    wavelength_um: float,
    n_pillar: float,
    grid: AngleGrid,
    *,
    order: int = 5,
    steps: int = 40,
    lr: float = 0.15,
    history: list | None = None,
    on_step: Callable[[list], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> list[dict]:
    """Adam ascent from start = (period, fill, height). Resumes from history if given:
    the last entry's x and Adam state are restored. Returns the full history."""
    history = list(history or [])
    if history:
        last = history[-1]
        x = torch.tensor(last["x_next"], dtype=torch.float64)
        state = {
            "t": last["adam_t"],
            "m": torch.tensor(last["adam_m"], dtype=torch.float64),
            "v": torch.tensor(last["adam_v"], dtype=torch.float64),
        }
    else:
        x = to_unconstrained(*start, bounds)
        state = {}
    while len(history) < steps:
        if should_stop is not None and should_stop():
            break
        j, g, (a, f, h) = evaluate_with_gradient(
            x, bounds, weight, n1, n2, wavelength_um, n_pillar, grid, order
        )
        x_next = adam_step(x, g, state, lr)
        history.append(
            {
                "step": len(history),
                "period_um": a,
                "fill": f,
                "height_um": h,
                "radius_um": a * math.sqrt(f / math.pi),
                "objective": j,
                "grad_x": g.tolist(),
                "x": x.tolist(),
                "x_next": x_next.tolist(),
                "adam_t": state["t"],
                "adam_m": state["m"].tolist(),
                "adam_v": state["v"].tolist(),
            }
        )
        x = x_next
        if on_step is not None:
            on_step(history)
    return history
