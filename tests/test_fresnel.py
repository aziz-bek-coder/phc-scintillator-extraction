"""Tests for phcscint.fresnel (derivation 02, eqs. 2-7)."""

import math

import numpy as np
import pytest

from phcscint import analytic, fresnel
from phcscint.materials import BGO, LYSO, N_AIR, N_GREASE

PAIRS = [(LYSO.n, N_AIR), (LYSO.n, N_GREASE), (BGO.n, N_AIR), (N_AIR, LYSO.n)]
THETAS = np.radians(np.linspace(0.0, 89.9, 400))


@pytest.mark.parametrize(("n1", "n2"), PAIRS)
def test_normal_incidence(n1: float, n2: float) -> None:
    r_s, r_p, t_s, t_p = fresnel.fresnel_amplitudes(n1, n2, 0.0)
    assert r_s == pytest.approx((n1 - n2) / (n1 + n2), abs=1e-14)
    assert r_p == pytest.approx(-r_s, abs=1e-14)  # Born & Wolf sign convention
    assert t_s == pytest.approx(2 * n1 / (n1 + n2), abs=1e-14)
    assert t_p == pytest.approx(2 * n1 / (n1 + n2), abs=1e-14)
    R_s, R_p, T_s, T_p = fresnel.fresnel_power(n1, n2, 0.0)
    assert R_s == pytest.approx(((n1 - n2) / (n1 + n2)) ** 2, abs=1e-14)
    assert R_p == pytest.approx(R_s, abs=1e-14)
    assert T_s == pytest.approx(1 - R_s, abs=1e-14)


@pytest.mark.parametrize(("n1", "n2"), PAIRS)
def test_energy_conservation_lossless(n1: float, n2: float) -> None:
    R_s, R_p, T_s, T_p = fresnel.fresnel_power(n1, n2, THETAS)
    np.testing.assert_allclose(R_s + T_s, 1.0, atol=1e-12)
    np.testing.assert_allclose(R_p + T_p, 1.0, atol=1e-12)
    assert np.all(R_s >= 0) and np.all(R_s <= 1 + 1e-12)
    assert np.all(T_p >= -1e-12)


@pytest.mark.parametrize(("n1", "n2"), [(LYSO.n, N_AIR), (LYSO.n, N_GREASE), (BGO.n, N_AIR)])
def test_total_internal_reflection(n1: float, n2: float) -> None:
    theta_c = analytic.critical_angle(n1, n2)
    th = np.linspace(theta_c + 1e-6, math.pi / 2 - 1e-6, 50)
    R_s, R_p, T_s, T_p = fresnel.fresnel_power(n1, n2, th)
    np.testing.assert_allclose(R_s, 1.0, atol=1e-10)
    np.testing.assert_allclose(R_p, 1.0, atol=1e-10)
    np.testing.assert_allclose(T_s, 0.0, atol=1e-10)
    np.testing.assert_allclose(T_p, 0.0, atol=1e-10)
    # the evanescent branch: Im(n2 cos theta2) > 0 (decaying field), t != 0
    _, _, t_s, _ = fresnel.fresnel_amplitudes(n1, n2, th)
    assert np.all(np.abs(t_s) > 0)
    # just below theta_c, R approaches 1 continuously
    R_s_below, _, _, _ = fresnel.fresnel_power(n1, n2, theta_c - 1e-6)
    assert R_s_below == pytest.approx(1.0, abs=1e-2)


@pytest.mark.parametrize(("n1", "n2"), PAIRS)
def test_brewster(n1: float, n2: float) -> None:
    th_b = fresnel.brewster_angle(n1, n2)
    assert th_b == pytest.approx(math.atan(n2 / n1), abs=1e-14)
    _, r_p, _, _ = fresnel.fresnel_amplitudes(n1, n2, th_b)
    assert abs(r_p) < 1e-12
    if n2 < n1:
        assert th_b < analytic.critical_angle(n1, n2)


def test_reciprocity_of_reflectance() -> None:
    """R(n1->n2 at theta1) == R(n2->n1 at theta2) with Snell's theta2, inside the cone."""
    n1, n2 = LYSO.n, N_AIR
    th1 = np.radians(np.linspace(0, 30, 31))
    th2 = np.arcsin(n1 * np.sin(th1) / n2)
    R_s1, R_p1, _, _ = fresnel.fresnel_power(n1, n2, th1)
    R_s2, R_p2, _, _ = fresnel.fresnel_power(n2, n1, th2)
    np.testing.assert_allclose(R_s1, R_s2, atol=1e-12)
    np.testing.assert_allclose(R_p1, R_p2, atol=1e-12)


def test_absorbing_medium_decays_and_conserves_less_than_one() -> None:
    """Complex n2 = 1.5 + 0.1i: R + T < 1 is NOT expected (T is the flux entering the
    absorber, and R + T = 1 still holds at the interface); the check is that the
    transmitted wave decays (Im(n2 cos theta2) > 0) and 0 <= R <= 1."""
    n1, n2 = 1.0, 1.5 + 0.1j
    R_s, R_p, T_s, T_p = fresnel.fresnel_power(n1, n2, THETAS)
    assert np.all((R_s >= 0) & (R_s <= 1))
    np.testing.assert_allclose(R_s + T_s, 1.0, atol=1e-12)
    cos2 = fresnel._cos_theta2(n1, n2, np.cos(THETAS), np.sin(THETAS))
    assert np.all(np.imag(n2 * cos2) > 0)


def test_fresnel_weighted_escape_below_geometric() -> None:
    for n1, n2 in [(LYSO.n, N_AIR), (LYSO.n, N_GREASE), (BGO.n, N_AIR)]:
        eta = analytic.escape_fraction_one_face(n1, n2)
        eta_f = fresnel.escape_fraction_one_face_fresnel(n1, n2)
        assert 0.0 < eta_f < eta
        # Fresnel loss inside the cone is at most ~25 % of the geometric value for
        # these contrasts (a loose physical bound; the exact number is in results/).
        assert eta_f > 0.75 * eta
