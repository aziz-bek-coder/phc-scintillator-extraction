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


# --------------------------------------------------------------------------------------
# M2: patterned photonic-crystal layer (docs/derivations/03-grating-orders-and-lut.md)
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class PhCLayer:
    """Square lattice of circular pillars of index n_pillar and height height_um on the
    readout face; the space between pillars is filled by the outside medium.
    Lengths in micrometres."""

    period_um: float
    radius_um: float
    height_um: float
    n_pillar: float

    @property
    def fill_factor(self) -> float:
        return float(np.pi * self.radius_um**2 / self.period_um**2)


def order_window(k: int) -> np.ndarray:
    """All integer orders (m, n) with |m|, |n| <= k, shape ((2k+1)^2, 2), m-major."""
    r = np.arange(-k, k + 1)
    mm, nn = np.meshgrid(r, r, indexing="ij")
    return np.stack([mm.ravel(), nn.ravel()], axis=1)


def pillar_permittivity(
    layer: PhCLayer,
    n_out: float,
    *,
    n_grid: int = 256,
    edge_sharpness: float = 1000.0,
    radius: torch.Tensor | float | None = None,
    dtype: torch.dtype = torch.complex128,
) -> torch.Tensor:
    """Real-space permittivity on an n_grid x n_grid cell-centred grid, C4v-symmetric
    about the pillar centre (derivation 03, 2h). Uses torcwa's sigmoid-edged circle;
    the edge width is about radius / edge_sharpness. radius may be a tensor that
    requires grad (M4); otherwise layer.radius_um is used."""
    geo = torcwa.geometry(
        Lx=layer.period_um,
        Ly=layer.period_um,
        nx=n_grid,
        ny=n_grid,
        edge_sharpness=edge_sharpness,
        dtype=torch.float64,
        device=CPU,
    )
    r = layer.radius_um if radius is None else radius
    c = layer.period_um / 2
    occ = geo.circle(R=r, Cx=c, Cy=c)  # 1 inside the pillar, 0 outside
    eps = n_out**2 + (layer.n_pillar**2 - n_out**2) * occ
    return eps.to(dtype)


def _new_sim(n1, n2, wavelength_um, period_um, order, theta, phi, dtype):
    sim = torcwa.rcwa(
        freq=1.0 / wavelength_um,
        order=[order, order],
        L=[period_um, period_um],
        dtype=dtype,
        device=CPU,
    )
    sim.add_input_layer(eps=n1**2)
    sim.add_output_layer(eps=n2**2)
    sim.set_incident_angle(inc_ang=float(theta), azi_ang=float(phi), angle_layer="input")
    return sim


def _unpolarised_order_powers(sim, orders: np.ndarray, port: str) -> np.ndarray:
    """Eq. (7) of derivation 03: one half of the sum over input and output polarisation
    of |S|^2, per order. Orders outside the solver's truncation window are 0."""
    out = np.zeros(len(orders))
    m_max = sim.order[0]
    inside = (np.abs(orders[:, 0]) <= m_max) & (np.abs(orders[:, 1]) <= m_max)
    if not inside.any():
        return out
    sel = orders[inside]
    acc = np.zeros(len(sel))
    for pol in ("ss", "ps", "sp", "pp"):
        # a fresh tensor for each call, because torcwa clamps the order array in place
        s = sim.S_parameters(
            orders=torch.tensor(sel.copy(), dtype=torch.int64),
            direction="forward",
            port=port,
            polarization=pol,
            power_norm=True,
        )
        acc += np.abs(s.detach().numpy().reshape(-1)) ** 2
    out[inside] = 0.5 * acc
    return out


@dataclass
class OrderPowers:
    """Unpolarised power fractions per diffraction order for one incidence."""

    orders: np.ndarray  # (K, 2) integer orders
    T: np.ndarray  # (K,) transmitted into the outside medium
    R: np.ndarray  # (K,) reflected back into the scintillator

    @property
    def total(self) -> float:
        return float(self.T.sum() + self.R.sum())


def solve_phc(
    n1: float,
    n2: float,
    wavelength_um: float,
    layer: PhCLayer,
    theta: float,
    phi: float,
    *,
    order: int = 7,
    n_grid: int = 256,
    edge_sharpness: float = 1000.0,
    report_window: int | None = None,
    dtype: torch.dtype = torch.complex128,
) -> OrderPowers:
    """RCWA of the pillar layer between the scintillator n1 (input) and the outside
    medium n2 (output) at polar angle theta and azimuth phi (radians, in the
    scintillator). Returns unpolarised order powers on the window
    |m|, |n| <= report_window (default: the solver truncation window)."""
    sim = _new_sim(n1, n2, wavelength_um, layer.period_um, order, theta, phi, dtype)
    eps = pillar_permittivity(layer, n2, n_grid=n_grid, edge_sharpness=edge_sharpness, dtype=dtype)
    sim.add_layer(thickness=layer.height_um, eps=eps)
    sim.solve_global_smatrix()
    orders = order_window(order if report_window is None else report_window)
    return OrderPowers(
        orders=orders,
        T=_unpolarised_order_powers(sim, orders, "transmission"),
        R=_unpolarised_order_powers(sim, orders, "reflection"),
    )


def solve_uniform_film_general_path(
    n1: float,
    n_film: float,
    n2: float,
    wavelength_um: float,
    thickness_um: float,
    theta: float,
    phi: float = 0.0,
    *,
    order: int = 2,
    n_grid: int = 32,
    period_um: float = 0.4,
    dtype: torch.dtype = torch.complex128,
) -> OrderPowers:
    """Homogeneous film passed to torcwa as a 2D eps array, which forces the general
    Fourier eigen-solver path. Validates that path against the analytic thin-film
    formula (derivation 03, 2k)."""
    sim = _new_sim(n1, n2, wavelength_um, period_um, order, theta, phi, dtype)
    eps = torch.full((n_grid, n_grid), n_film**2, dtype=dtype)
    sim.add_layer(thickness=thickness_um, eps=eps)
    sim.solve_global_smatrix()
    orders = order_window(order)
    return OrderPowers(
        orders=orders,
        T=_unpolarised_order_powers(sim, orders, "transmission"),
        R=_unpolarised_order_powers(sim, orders, "reflection"),
    )


def propagating_mask(orders: np.ndarray, u: np.ndarray, g: float, n_medium: float) -> np.ndarray:
    """Grating equation (derivation 03, eq. 3): True where |u + g (m, n)| < n_medium.
    u is the normalised in-plane wavevector n1 sin(theta) (cos phi, sin phi)."""
    umn = np.asarray(u, dtype=float)[None, :] + g * np.asarray(orders, dtype=float)
    return np.hypot(umn[:, 0], umn[:, 1]) < n_medium
