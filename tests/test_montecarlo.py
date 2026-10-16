"""Monte Carlo validation (derivation 04). Every test compares to an analytic
expectation with a stated statistical tolerance (AGENTS.md)."""

import math

import numpy as np
import pytest

from phcscint import montecarlo as mc
from phcscint.fresnel import fresnel_power
from phcscint.lut import LUT, LUTConfig, inclusive_grid, midpoint_grid
from phcscint.materials import LYSO, N_AIR, N_GREASE
from phcscint.rcwa import PhCLayer, order_window
from phcscint.timing import (
    binomial_sigma,
    fresnel_R,
    fresnel_T,
    mirror,
    specular_box_cdf,
)

PIXEL = mc.Pixel(n1=LYSO.n, wavelength_um=LYSO.wavelength_um)
T_GRID = np.array([40.0, 80.0, 121.0, 200.0, 400.0, 800.0, 1500.0])
N = 60_000
T_MAX = 1500.0


def _assert_matches(res: mc.MCResult, expected: np.ndarray, extra: float = 5e-4) -> None:
    """4 sigma binomial (N = 60000: sigma <= 2e-3) plus 5e-4 for the oracle quadrature
    and, in the LUT test, bilinear interpolation of the Fresnel table near theta_c."""
    got = res.cdf(T_GRID)
    tol = 4 * binomial_sigma(expected, res.n_emitted) + extra
    assert np.all(np.abs(got - expected) <= tol), (got, expected, tol)


@pytest.mark.parametrize(
    "side", [mc.Wall("lambertian", 1.0), mc.Wall("specular", 0.95)], ids=["lambertian", "rho95"]
)
@pytest.mark.slow
def test_negative_control_wrong_walls_fail_the_oracle(side, rng) -> None:
    """The oracle comparison must have power: wall models that do change |w| or lose
    light at the sides must deviate by far more than the tolerance (measured in the M3
    session: |z| up to ~140 for lambertian, ~55 for rho = 0.95)."""
    res = mc.run(
        PIXEL,
        (side,) * 4 + (mc.Wall("specular", 1.0),),
        mc.Readout(N_GREASE),
        N,
        rng,
        t_max_ps=T_MAX,
    )
    expected = specular_box_cdf(
        T_GRID, n_group=PIXEL.ng, lz_um=PIXEL.lz_um, readout_T=fresnel_T(LYSO.n, N_GREASE)
    )
    z = np.abs(res.cdf(T_GRID) - expected) / binomial_sigma(expected, N)
    assert z.max() > 20


def test_isotropic_directions(rng) -> None:
    d = mc._isotropic(200_000, rng)
    np.testing.assert_allclose(np.linalg.norm(d, axis=1), 1.0, atol=1e-12)
    # <w> = 0 and <w^2> = 1/3 for isotropic directions; sigma ~ 1.3e-3 and 6.7e-4
    assert abs(d[:, 2].mean()) < 5e-3
    assert abs((d[:, 2] ** 2).mean() - 1 / 3) < 3e-3


def test_lambertian_emission_cosine_law(rng) -> None:
    n = 200_000
    axis = np.full(n, 0)
    inward = np.full(n, -1.0)
    d = mc._direction_about_axis(np.sqrt(rng.random(n)), axis, inward, rng)
    np.testing.assert_allclose(np.linalg.norm(d, axis=1), 1.0, atol=1e-12)
    assert np.all(d[:, 0] <= 0)
    # cosine law: <cos theta> = 2/3, sigma = sqrt(1/18 / n) ~ 5e-4
    assert abs(np.abs(d[:, 0]).mean() - 2 / 3) < 3e-3


def test_wrapped_specular_return_probability(rng) -> None:
    """Eq. (2) of derivation 04 at an angle inside the side cone."""
    n = 200_000
    cos_t = math.cos(math.radians(20.0))
    d = np.tile([math.sqrt(1 - cos_t**2), 0.0, cos_t], (n, 1))[:, [2, 1, 0]]  # along x
    wall = mc.Wall("wrapped_specular", reflectivity=0.9)
    surv, _, _ = mc._wall_interaction(wall, LYSO.n, d, np.zeros(n, int), np.ones(n), rng)
    r_s, r_p, _, _ = fresnel_power(LYSO.n, 1.0, math.radians(20.0))
    r = 0.5 * (r_s + r_p)
    t = 1 - r
    p = r + t * t * 0.9 / (1 - 0.9 * r)
    assert abs(surv.mean() - p) < 4 * math.sqrt(p * (1 - p) / n)


SIDE_MODELS = [
    mc.Wall("specular", 1.0),
    mc.Wall("bare"),
    mc.Wall("wrapped_specular", 0.9),
    mc.Wall("wrapped_lambertian", 0.9),
]


@pytest.mark.parametrize("side", SIDE_MODELS, ids=lambda w: f"{w.kind}-{w.reflectivity}")
@pytest.mark.parametrize("back", ["mirror", "bare"])
@pytest.mark.slow
def test_specular_box_matches_analytic(side, back, rng) -> None:
    """Derivation 04, eq. (5) and 2h: for LYSO with grease readout, every side model
    with air outside (or a perfect mirror) gives the same detected-time CDF, because
    readout-cone photons are totally reflected at the sides."""
    back_wall = mc.Wall("specular", 1.0) if back == "mirror" else mc.Wall("bare")
    res = mc.run(
        PIXEL,
        (side,) * 4 + (back_wall,),
        mc.Readout(N_GREASE),
        N,
        rng,
        t_max_ps=T_MAX,
    )
    expected = specular_box_cdf(
        T_GRID,
        n_group=PIXEL.ng,
        lz_um=PIXEL.lz_um,
        readout_T=fresnel_T(LYSO.n, N_GREASE),
        back_R=mirror if back == "mirror" else fresnel_R(LYSO.n, N_AIR),
    )
    _assert_matches(res, expected)


@pytest.mark.slow
def test_readout_into_air_matches_analytic(rng) -> None:
    res = mc.run(PIXEL, mc.Wall("bare"), mc.Readout(N_AIR), N, rng, t_max_ps=T_MAX)
    expected = specular_box_cdf(
        T_GRID,
        n_group=PIXEL.ng,
        lz_um=PIXEL.lz_um,
        readout_T=fresnel_T(LYSO.n, N_AIR),
        back_R=fresnel_R(LYSO.n, N_AIR),
    )
    _assert_matches(res, expected)


@pytest.mark.slow
def test_absorption_matches_analytic(rng) -> None:
    pix = mc.Pixel(n1=LYSO.n, wavelength_um=0.42, abs_length_um=50_000.0)
    res = mc.run(pix, mc.Wall("specular", 1.0), mc.Readout(N_GREASE), N, rng, t_max_ps=T_MAX)
    expected = specular_box_cdf(
        T_GRID,
        n_group=pix.ng,
        lz_um=pix.lz_um,
        readout_T=fresnel_T(LYSO.n, N_GREASE),
        abs_length_um=50_000.0,
    )
    _assert_matches(res, expected)
    assert res.counts["absorbed_bulk"] > 0


def test_analytic_long_time_limit_is_two_eta() -> None:
    """Eq. (6) with mirror back face equals 1 - cos(theta_c) = 2 eta_1."""
    f_inf = specular_box_cdf(
        math.inf, n_group=1.81, lz_um=20_000.0, readout_T=fresnel_T(LYSO.n, N_GREASE)
    )[0]
    cos_c = math.sqrt(1 - (N_GREASE / LYSO.n) ** 2)
    assert f_inf == pytest.approx(1 - cos_c, abs=1e-4)
    # the finite-time CDF approaches it from below
    f_late = specular_box_cdf(
        1e6, n_group=1.81, lz_um=20_000.0, readout_T=fresnel_T(LYSO.n, N_GREASE)
    )[0]
    assert f_late <= f_inf + 1e-9
    assert f_late == pytest.approx(f_inf, abs=2e-3)


@pytest.mark.slow
def test_lambertian_lossless_detects_everything(rng) -> None:
    """Derivation 04, 2g: lossless diffuse walls, the readout is the only sink."""
    res = mc.run(
        PIXEL, mc.Wall("lambertian", 1.0), mc.Readout(N_GREASE), 4000, rng, t_max_ps=40_000.0
    )
    assert res.counts["lost_wall"] == 0
    assert res.counts["escaped_wall"] == 0
    assert res.counts["absorbed_bulk"] == 0
    assert res.counts["detected"] + res.counts["capped"] == 4000
    assert res.efficiency > 0.97


def test_bookkeeping_with_losses(rng) -> None:
    pix = mc.Pixel(n1=LYSO.n, wavelength_um=0.42, abs_length_um=200_000.0)
    walls = (
        mc.Wall("bare"),
        mc.Wall("lambertian", 0.9),
        mc.Wall("wrapped_specular", 0.95),
        mc.Wall("wrapped_lambertian", 0.95),
        mc.Wall("specular", 0.98),
    )
    res = mc.run(pix, walls, mc.Readout(N_GREASE), 20_000, rng, t_max_ps=3000.0)
    assert sum(res.counts.values()) == 20_000
    assert np.all(res.times_ps <= 3000.0)
    assert np.all(res.times_ps >= 0.0)
    assert np.all(res.readout_hits >= 1)


# ---------------------------------------------------------------- LUT readout


def _fresnel_lut() -> LUT:
    """Synthetic LUT whose only non-zero order is (0, 0) with the flat-face Fresnel
    powers: the LUT readout path must then reproduce the bare readout."""
    th_deg = midpoint_grid(0.0, 90.0, 0.25)
    ph_deg = inclusive_grid(0.0, 45.0, 15.0)
    th = np.radians(th_deg)
    _, _, ts, tp = fresnel_power(LYSO.n, N_GREASE, th)
    t00 = 0.5 * (ts + tp)
    orders = order_window(1)
    k00 = int(np.flatnonzero((orders == [0, 0]).all(axis=1))[0])
    T = np.zeros((len(th_deg), len(ph_deg), len(orders)))
    R = np.zeros_like(T)
    T[:, :, k00] = t00[:, None]
    R[:, :, k00] = 1 - t00[:, None]
    layer = PhCLayer(0.4, 0.12, 0.3, 2.09)
    cfg = LUTConfig(LYSO.n, N_GREASE, 0.42, layer, 1, 0, th_deg, ph_deg, 1)
    return LUT(cfg, orders, T, R)


@pytest.mark.slow
def test_lut_readout_reproduces_bare_readout(rng) -> None:
    res = mc.run(
        PIXEL,
        mc.Wall("specular", 1.0),
        mc.Readout(N_GREASE, _fresnel_lut()),
        N,
        rng,
        t_max_ps=T_MAX,
    )
    expected = specular_box_cdf(
        T_GRID, n_group=PIXEL.ng, lz_um=PIXEL.lz_um, readout_T=fresnel_T(LYSO.n, N_GREASE)
    )
    _assert_matches(res, expected)


def test_specular_box_smoke_fast(rng) -> None:
    """Fast version of the oracle test for laptops: N = 6000, so sigma <= 6.5e-3 and the
    4-sigma tolerance only catches gross errors. The full-statistics versions are
    marked slow and run in CI."""
    n = 6000
    res = mc.run(PIXEL, mc.Wall("specular", 1.0), mc.Readout(N_GREASE), n, rng, t_max_ps=T_MAX)
    expected = specular_box_cdf(
        T_GRID, n_group=PIXEL.ng, lz_um=PIXEL.lz_um, readout_T=fresnel_T(LYSO.n, N_GREASE)
    )
    tol = 4 * binomial_sigma(expected, n) + 5e-4
    assert np.all(np.abs(res.cdf(T_GRID) - expected) <= tol)
