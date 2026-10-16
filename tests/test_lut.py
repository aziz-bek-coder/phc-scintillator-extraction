"""Lookup-table tests (derivation 03, 2h to 2j): C4v reduction, caching/resume,
lookup consistency with direct solves, and the single-pass integral."""

import math

import numpy as np
import pytest

from phcscint.fresnel import escape_fraction_one_face_fresnel, fresnel_power
from phcscint.lut import (
    C4V,
    LUT,
    LUTConfig,
    build_lut,
    inclusive_grid,
    midpoint_grid,
    reduce_to_wedge,
    window_for,
)
from phcscint.materials import LYSO, N_GREASE, n_si3n4_luke
from phcscint.rcwa import PhCLayer, order_window, solve_phc

N_SIN = n_si3n4_luke(LYSO.wavelength_um)
LAYER = PhCLayer(period_um=0.40, radius_um=0.12, height_um=0.30, n_pillar=N_SIN)


def test_c4v_is_a_group_of_orthogonal_integer_matrices() -> None:
    keys = {q.tobytes() for q in C4V}
    assert len(keys) == 8
    for a in C4V:
        np.testing.assert_array_equal(a @ a.T, np.eye(2, dtype=int))
        for b in C4V:
            assert (a @ b).tobytes() in keys  # closure


@pytest.mark.parametrize("phi_deg", np.arange(-180, 181, 7.5))
def test_reduce_to_wedge(phi_deg: float) -> None:
    u = 1.3 * np.array([math.cos(math.radians(phi_deg)), math.sin(math.radians(phi_deg))])
    q, v = reduce_to_wedge(u)
    np.testing.assert_allclose(q @ v, u, atol=1e-12)
    ang = math.degrees(math.atan2(v[1], v[0]))
    assert -1e-9 <= ang <= 45 + 1e-9


def test_window_for_reference() -> None:
    # g = 0.42/0.40 = 1.05, 2 n1 / g = 3.45 -> 4
    assert window_for(LYSO.n, 0.42, 0.40) == 4


def _tiny_config(label: str) -> LUTConfig:
    return LUTConfig(
        n1=LYSO.n,
        n2=N_GREASE,
        wavelength_um=LYSO.wavelength_um,
        layer=LAYER,
        order=3,
        n_grid=48,
        theta_deg=midpoint_grid(0.0, 90.0, 30.0),  # 15, 45, 75
        phi_deg=inclusive_grid(0.0, 45.0, 22.5),  # 0, 22.5, 45
        window=3,
        label=label,
    )


def test_build_is_resumable_and_cached(tmp_path) -> None:
    cfg = _tiny_config("resume")
    part, ppath = build_lut(cfg, cache_dir=tmp_path, max_points=4, progress=None)
    assert ppath.name.endswith(".partial.npz") and ppath.exists()
    assert not part.meta["complete"]
    full, fpath = build_lut(cfg, cache_dir=tmp_path, progress=None)
    assert fpath.exists() and not ppath.exists()
    assert full.meta["complete"]
    assert full.meta["max_energy_error"] < 1e-9
    # resumed result equals a fresh build
    fresh, _ = build_lut(_tiny_config("fresh"), cache_dir=tmp_path / "x", progress=None)
    np.testing.assert_allclose(full.T, fresh.T, atol=1e-13)
    np.testing.assert_allclose(full.R, fresh.R, atol=1e-13)
    # cached load returns identical arrays and config
    again, _ = build_lut(cfg, cache_dir=tmp_path, progress=None)
    np.testing.assert_array_equal(again.T, full.T)
    assert again.config == cfg
    loaded = LUT.load(fpath)
    assert loaded.config.layer == LAYER


def test_lookup_matches_direct_solve_on_grid_points_any_azimuth(tmp_path) -> None:
    """At a grid point (theta=45, phi=22.5 in the wedge), the lookup for an equivalent
    azimuth outside the wedge (phi = 22.5 + 90 + 45 = 157.5 deg, i.e. mirror images)
    must reproduce a direct solve at that azimuth."""
    cfg = _tiny_config("lookup")
    lut, _ = build_lut(cfg, cache_dir=tmp_path, progress=None)
    for phi_deg in (22.5, 67.5, 112.5, 157.5, -22.5, 202.5):
        th, ph = math.radians(45.0), math.radians(phi_deg)
        orders, t, r = lut.lookup(th, ph)
        direct = solve_phc(
            LYSO.n,
            N_GREASE,
            LYSO.wavelength_um,
            LAYER,
            th,
            ph,
            order=3,
            n_grid=48,
            report_window=3,
        )
        d_idx = {tuple(o): i for i, o in enumerate(direct.orders)}
        perm = [d_idx[tuple(o)] for o in orders]
        np.testing.assert_allclose(t, direct.T[perm], atol=1e-9)
        np.testing.assert_allclose(r, direct.R[perm], atol=1e-9)
        assert t.sum() + r.sum() == pytest.approx(1.0, abs=1e-12)


def test_lookup_off_grid_is_normalised_and_only_open_orders(tmp_path) -> None:
    lut, _ = build_lut(_tiny_config("offgrid"), cache_dir=tmp_path, progress=None)
    rng = np.random.default_rng(1)
    g = lut.g
    for _ in range(50):
        th = rng.uniform(0, math.pi / 2)
        ph = rng.uniform(-math.pi, math.pi)
        orders, t, r = lut.lookup(th, ph)
        assert t.sum() + r.sum() == pytest.approx(1.0, abs=1e-12)
        u = LYSO.n * math.sin(th) * np.array([math.cos(ph), math.sin(ph)])
        umn = np.hypot(*(u[None, :] + g * orders).T)
        assert np.all(t[umn >= N_GREASE] == 0)
        assert np.all(r[umn >= LYSO.n] == 0)


def test_single_pass_integral_reproduces_bare_fresnel() -> None:
    """Feed the integrator a 'LUT' filled with the analytic flat-face Fresnel T in the
    (0,0) order: it must return eta_1^F of derivation 02 to the quadrature accuracy of
    a 1-degree midpoint grid (the integrand has a kink at theta_c)."""
    th_deg = midpoint_grid(0.0, 90.0, 1.0)
    ph_deg = inclusive_grid(0.0, 45.0, 5.0)
    th = np.radians(th_deg)
    _, _, ts, tp = fresnel_power(LYSO.n, N_GREASE, th)
    t_unpol = 0.5 * (ts + tp)
    orders = np.array([[0, 0]])
    T = np.broadcast_to(t_unpol[:, None, None], (len(th_deg), len(ph_deg), 1)).copy()
    cfg = LUTConfig(LYSO.n, N_GREASE, 0.42, LAYER, 0, 0, th_deg, ph_deg, 0)
    lut = LUT(cfg, orders, T, 1 - T)
    eta = lut.single_pass_extraction()["eta_single_pass"]
    assert eta == pytest.approx(escape_fraction_one_face_fresnel(LYSO.n, N_GREASE), abs=1e-3)


# ---------------------------------------------------------------- batch sampling


def _first_order_lut() -> LUT:
    """All power reflected into table order (-1, 0) everywhere."""
    th_deg = midpoint_grid(0.0, 90.0, 10.0)
    ph_deg = inclusive_grid(0.0, 45.0, 45.0)
    orders = order_window(1)
    k = int(np.flatnonzero((orders == [-1, 0]).all(axis=1))[0])
    T = np.zeros((len(th_deg), len(ph_deg), len(orders)))
    R = np.zeros_like(T)
    R[:, :, k] = 1.0
    layer = PhCLayer(0.40, 0.12, 0.30, 2.09)
    cfg = LUTConfig(LYSO.n, N_GREASE, 0.42, layer, 1, 0, th_deg, ph_deg, 1)
    return LUT(cfg, orders, T, R)


@pytest.mark.parametrize("phi_deg", [0.0, 90.0, 180.0, 270.0])
def test_reflected_order_direction(phi_deg, rng) -> None:
    """Eq. (3) of derivation 04: the reflected order (m, n) leaves with in-plane
    wavevector u + g (m, n). For the synthetic table the order is Q(-1, 0), i.e. it
    always points against the incident in-plane direction."""
    lut = _first_order_lut()
    g = 0.42 / 0.40
    sin_t = 1.2 / LYSO.n  # |u| = 1.2: trapped for grease, and |u - g| = 0.15 is open
    ph = math.radians(phi_deg)
    d = np.array([[sin_t * math.cos(ph), sin_t * math.sin(ph), math.sqrt(1 - sin_t**2)]])
    trans, new_d = lut.sample_batch(d, rng)
    assert not trans[0]
    u_new = LYSO.n * new_d[0, :2]
    expected = (1.2 - g) * np.array([math.cos(ph), math.sin(ph)])
    np.testing.assert_allclose(u_new, expected, atol=1e-12)
    assert new_d[0, 2] < 0
    assert np.linalg.norm(new_d[0]) == pytest.approx(1.0, abs=1e-12)


def test_batch_lookup_equals_single_lookup(tmp_path) -> None:
    layer = PhCLayer(0.40, 0.12, 0.30, n_si3n4_luke(0.42))
    cfg = LUTConfig(
        LYSO.n,
        N_GREASE,
        0.42,
        layer,
        3,
        48,
        midpoint_grid(0.0, 90.0, 30.0),
        inclusive_grid(0.0, 45.0, 22.5),
        3,
    )
    lut, _ = build_lut(cfg, cache_dir=tmp_path, progress=None)
    rng = np.random.default_rng(3)
    d = rng.normal(size=(300, 3))
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    d[:, 2] = np.abs(d[:, 2])
    orders_b, t_b, r_b, _ = lut.channel_powers_batch(d)
    for i in range(len(d)):
        th = math.acos(d[i, 2])
        ph = math.atan2(d[i, 1], d[i, 0])
        orders_s, t_s, r_s = lut.lookup(th, ph)
        np.testing.assert_array_equal(orders_b[i], orders_s)
        np.testing.assert_allclose(t_b[i], t_s, atol=1e-12)
        np.testing.assert_allclose(r_b[i], r_s, atol=1e-12)
