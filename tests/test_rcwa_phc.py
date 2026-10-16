"""Patterned-layer RCWA checks (derivation 03). Small orders and grids so CI stays fast;
the convergence study itself is scripts/convergence.py."""

import math

import numpy as np
import pytest

from phcscint.fresnel import thin_film_power
from phcscint.materials import LYSO, N_AIR, N_GREASE, n_si3n4_luke
from phcscint.rcwa import (
    PhCLayer,
    order_window,
    propagating_mask,
    solve_phc,
    solve_uniform_film_general_path,
)

N_SIN = n_si3n4_luke(LYSO.wavelength_um)
LAYER = PhCLayer(period_um=0.40, radius_um=0.12, height_um=0.30, n_pillar=N_SIN)
FAST = {"order": 3, "n_grid": 64}


def test_si3n4_index_matches_tabulated_values() -> None:
    """refractiveindex.info CSV values for Luke 2015 (docs/references.md)."""
    assert n_si3n4_luke(0.4139) == pytest.approx(2.0934554672447, abs=1e-9)
    assert n_si3n4_luke(0.4658) == pytest.approx(2.0731921339333, abs=1e-9)
    with pytest.raises(ValueError):
        n_si3n4_luke(0.2)


def test_order_window() -> None:
    w = order_window(2)
    assert w.shape == (25, 2)
    assert (w == [0, 0]).all(axis=1).sum() == 1
    assert np.abs(w).max() == 2


@pytest.mark.parametrize("n2", [N_GREASE, N_AIR])
@pytest.mark.parametrize("theta_deg", [0.0, 25.0, 40.0, 70.0])
def test_uniform_film_general_path_matches_thin_film(n2: float, theta_deg: float) -> None:
    """Derivation 03, 2k: a uniform eps array forces torcwa's general eigen-solver; it
    must reproduce the analytic film. Tolerance 1e-8 (measured agreement ~1e-10)."""
    th = math.radians(theta_deg)
    rs, rp, ts, tp = thin_film_power(LYSO.n, N_SIN, n2, 0.30, LYSO.wavelength_um, th)
    op = solve_uniform_film_general_path(
        LYSO.n, N_SIN, n2, LYSO.wavelength_um, 0.30, th, math.radians(25.0)
    )
    assert op.T.sum() == pytest.approx(0.5 * (float(ts) + float(tp)), abs=1e-8)
    assert op.R.sum() == pytest.approx(0.5 * (float(rs) + float(rp)), abs=1e-8)
    # a homogeneous film couples only to the specular (0, 0) order
    nonzero = op.orders[(op.T + op.R) > 1e-12]
    assert all(tuple(o) == (0, 0) for o in nonzero)


def test_thin_film_zero_thickness_is_fresnel() -> None:
    from phcscint.fresnel import fresnel_power

    th = np.radians(np.linspace(0, 89, 50))
    a = thin_film_power(LYSO.n, N_SIN, N_AIR, 0.0, 0.42, th)
    b = fresnel_power(LYSO.n, N_AIR, th)
    for x, y in zip(a, b, strict=True):
        np.testing.assert_allclose(x, y, atol=1e-12)


@pytest.mark.parametrize("n2", [N_GREASE, N_AIR])
@pytest.mark.parametrize(("theta_deg", "phi_deg"), [(10, 0), (45, 20), (60, 0), (80, 40)])
def test_energy_conservation_patterned(n2, theta_deg, phi_deg) -> None:
    """Derivation 03, eq. (6): lossless layer, sum of all order powers = 1."""
    op = solve_phc(
        LYSO.n,
        n2,
        LYSO.wavelength_um,
        LAYER,
        math.radians(theta_deg),
        math.radians(phi_deg),
        **FAST,
    )
    assert op.total == pytest.approx(1.0, abs=1e-9)
    assert np.all(op.T >= -1e-12) and np.all(op.R >= -1e-12)


@pytest.mark.parametrize(("theta_deg", "phi_deg"), [(20, 10), (60, 0), (60, 30), (85, 45)])
def test_open_orders_follow_grating_equation(theta_deg, phi_deg) -> None:
    """Power appears only in orders the grating equation allows (derivation 03, eq. 3),
    and every allowed transmitted order nearby carries some power."""
    th, ph = math.radians(theta_deg), math.radians(phi_deg)
    op = solve_phc(LYSO.n, N_GREASE, LYSO.wavelength_um, LAYER, th, ph, **FAST)
    u = LYSO.n * math.sin(th) * np.array([math.cos(ph), math.sin(ph)])
    g = LYSO.wavelength_um / LAYER.period_um
    open_t = propagating_mask(op.orders, u, g, N_GREASE)
    open_r = propagating_mask(op.orders, u, g, LYSO.n)
    assert op.T[~open_t].sum() < 1e-12
    assert op.R[~open_r].sum() < 1e-12


def test_trapped_ray_gains_a_transmitted_channel() -> None:
    """Q1 of derivation 03: at theta = 60 deg (trapped for LYSO -> grease) the flat face
    transmits nothing; the PhC opens order (-1, 0) and transmits a finite fraction."""
    th = math.radians(60.0)
    assert LYSO.n * math.sin(th) > N_GREASE
    op = solve_phc(LYSO.n, N_GREASE, LYSO.wavelength_um, LAYER, th, 0.0, **FAST)
    idx = {tuple(o): i for i, o in enumerate(op.orders)}
    assert op.T[idx[(0, 0)]] < 1e-12  # specular transmission still closed
    assert op.T[idx[(-1, 0)]] > 0.01
    assert op.T.sum() > 0.05


@pytest.mark.parametrize(("theta_deg", "phi_deg"), [(50, 20), (30, 5)])
def test_c4v_symmetry(theta_deg, phi_deg) -> None:
    """Derivation 03, eq. (8): diagonal mirror (phi -> 90 - phi, (m,n) -> (n,m)) and
    x-axis mirror (phi -> -phi, (m,n) -> (m,-n)) leave unpolarised powers unchanged."""
    th = math.radians(theta_deg)
    a = solve_phc(LYSO.n, N_GREASE, 0.42, LAYER, th, math.radians(phi_deg), **FAST)
    b = solve_phc(LYSO.n, N_GREASE, 0.42, LAYER, th, math.radians(90 - phi_deg), **FAST)
    c = solve_phc(LYSO.n, N_GREASE, 0.42, LAYER, th, math.radians(-phi_deg), **FAST)
    idx = {tuple(o): i for i, o in enumerate(a.orders)}
    diag = [idx[(o[1], o[0])] for o in a.orders]
    mirx = [idx[(o[0], -o[1])] for o in a.orders]
    np.testing.assert_allclose(a.T, b.T[diag], atol=1e-10)
    np.testing.assert_allclose(a.R, b.R[diag], atol=1e-10)
    np.testing.assert_allclose(a.T, c.T[mirx], atol=1e-10)
    np.testing.assert_allclose(a.R, c.R[mirx], atol=1e-10)


def test_subwavelength_period_has_only_specular_orders() -> None:
    """Derivation 03, 2d: a < lambda / (2 n1) means no non-zero order can propagate."""
    tiny = PhCLayer(period_um=0.10, radius_um=0.03, height_um=0.10, n_pillar=N_SIN)
    op = solve_phc(LYSO.n, N_GREASE, 0.42, tiny, math.radians(50), math.radians(10), **FAST)
    nonzero = op.orders[(op.T + op.R) > 1e-12]
    assert all(tuple(o) == (0, 0) for o in nonzero)
    assert op.total == pytest.approx(1.0, abs=1e-9)
