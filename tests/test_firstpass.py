"""First-pass early yield (derivation 05, eqs. 1, 1a, 1b) against closed forms. Fast."""

import math

import numpy as np
import pytest

from phcscint.firstpass import first_pass_yield, wrap_return
from phcscint.fresnel import unpolarised_transmittance
from phcscint.materials import LYSO, N_GREASE
from phcscint.timing import C_UM_PER_PS, mirror, specular_box_cdf

PIXEL = {"lx_um": 3000.0, "ly_um": 3000.0, "lz_um": 20000.0}


def fresnel(d: np.ndarray) -> np.ndarray:
    return unpolarised_transmittance(LYSO.n, N_GREASE, np.arccos(np.clip(d[:, 2], 0, 1)))


def test_wrap_return_at_normal_incidence_and_under_total_reflection() -> None:
    r0 = ((LYSO.n - 1) / (LYSO.n + 1)) ** 2
    expect = r0 + (1 - r0) ** 2 * 0.95 / (1 - 0.95 * r0)
    assert wrap_return(LYSO.n, np.array([1.0]), 0.95)[0] == pytest.approx(expect, rel=1e-12)
    assert wrap_return(LYSO.n, np.array([0.5]), 0.95)[0] == 1.0  # 60 deg > 33.5 deg


@pytest.mark.parametrize("tau", [50.0, 150.0, 230.0])
def test_lossless_flat_face_matches_the_specular_box_closed_form(tau) -> None:
    """Below 2 t_dir (241.6 ps) only first readout hits count, and with lossless mirrors
    eq. (1b) must equal derivation 04, eq. (5)."""
    got = first_pass_yield(fresnel, LYSO.n, tau, **PIXEL, n_theta=3000, n_phi=1, n_path=2000)
    exp = specular_box_cdf(
        np.array([tau]),
        n_group=LYSO.n,
        lz_um=PIXEL["lz_um"],
        readout_T=lambda w: unpolarised_transmittance(LYSO.n, N_GREASE, np.arccos(w)),
        back_R=mirror,
    )[0]
    assert got == pytest.approx(exp, rel=2e-4)


def test_below_direct_transit_it_is_the_cos_weighted_single_pass() -> None:
    """For tau < t_dir, eq. (1b) without losses is eq. (1): (s/Lz) <T cos(theta)>."""
    tau = 100.0
    s = C_UM_PER_PS * tau / LYSO.n
    th = (np.arange(200_000) + 0.5) * (math.pi / 2) / 200_000
    t = unpolarised_transmittance(LYSO.n, N_GREASE, th)
    eq1 = (
        float(np.sum(t * (s / PIXEL["lz_um"]) * np.cos(th) * np.sin(th))) * (math.pi / 2) / 2e5 / 2
    )
    got = first_pass_yield(fresnel, LYSO.n, tau, **PIXEL, n_theta=4000, n_phi=1, n_path=10)
    assert got == pytest.approx(eq1, rel=5e-5)


def test_side_losses_spare_the_flat_face_but_not_grazing_light() -> None:
    """Flat face with grease: the transmitted directions never lie in a side escape cone
    (derivation 04), so the wraps cost nothing before t_dir. Light transmitted at grazing
    angles does lose some."""
    kw = {**PIXEL, "n_theta": 300, "n_phi": 6, "n_path": 300}
    lossless = first_pass_yield(fresnel, LYSO.n, 100.0, **kw)
    wraps = first_pass_yield(fresnel, LYSO.n, 100.0, rho=0.95, **kw)
    assert wraps == pytest.approx(lossless, rel=1e-12)

    def everything(d: np.ndarray) -> np.ndarray:
        return np.ones(d.shape[0])

    full = first_pass_yield(everything, LYSO.n, 100.0, **kw)
    lossy = first_pass_yield(everything, LYSO.n, 100.0, rho=0.95, **kw)
    assert 0.9 * full < lossy < full


def test_rejects_tau_beyond_two_transits() -> None:
    with pytest.raises(ValueError):
        first_pass_yield(fresnel, LYSO.n, 250.0, **PIXEL)
