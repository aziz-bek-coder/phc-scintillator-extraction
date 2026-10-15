"""torcwa zero-order flat interface vs analytic Fresnel (derivation 02, 2g).

Tolerance 1e-6 in complex128: any larger deviation is a convention error, since one
Fourier harmonic is exact for a homogeneous structure.
"""

import math

import numpy as np
import pytest
import torch

from phcscint import analytic, fresnel
from phcscint.materials import BGO, LYSO, N_AIR, N_GREASE
from phcscint.rcwa import flat_interface

TOL = 1e-6
PAIRS = [
    (LYSO.n, N_AIR, LYSO.wavelength_um),
    (LYSO.n, N_GREASE, LYSO.wavelength_um),
    (BGO.n, N_AIR, BGO.wavelength_um),
]
THETAS_DEG = [0.0, 10.0, 25.0, 30.0, 33.0, 36.0, 45.0, 60.0, 80.0, 89.0]


@pytest.mark.parametrize(("n1", "n2", "lam"), PAIRS)
@pytest.mark.parametrize("theta_deg", THETAS_DEG)
@pytest.mark.parametrize("phi_deg", [0.0, 37.0])
def test_flat_interface_matches_fresnel(n1, n2, lam, theta_deg, phi_deg) -> None:
    th = math.radians(theta_deg)
    R_s, R_p, T_s, T_p = fresnel.fresnel_power(n1, n2, th)
    res = flat_interface(n1, n2, lam, th, math.radians(phi_deg))
    assert res.R_s == pytest.approx(float(R_s), abs=TOL)
    assert res.R_p == pytest.approx(float(R_p), abs=TOL)
    assert res.T_s == pytest.approx(float(T_s), abs=TOL)
    assert res.T_p == pytest.approx(float(T_p), abs=TOL)
    # energy conservation and no cross-polarisation for an isotropic flat interface
    assert res.R_s + res.T_s == pytest.approx(1.0, abs=TOL)
    assert res.R_p + res.T_p == pytest.approx(1.0, abs=TOL)
    assert max(res.R_sp, res.R_ps, res.T_sp, res.T_ps) < TOL


def test_beyond_critical_angle_is_total_reflection() -> None:
    n1, n2, lam = LYSO.n, N_AIR, LYSO.wavelength_um
    theta_c = analytic.critical_angle(n1, n2)
    for th in (theta_c + 0.01, theta_c + 0.3, 1.5):
        res = flat_interface(n1, n2, lam, th)
        assert res.R_s == pytest.approx(1.0, abs=TOL)
        assert res.R_p == pytest.approx(1.0, abs=TOL)
        assert res.T_s == pytest.approx(0.0, abs=TOL)
        assert res.T_p == pytest.approx(0.0, abs=TOL)


def test_complex64_is_only_approximately_right() -> None:
    """Documents why validation runs use complex128: single precision deviated by about
    2e-5 from Fresnel in the M1 check. The assertion is loose on purpose."""
    th = math.radians(25.0)
    R_s, _, _, _ = fresnel.fresnel_power(LYSO.n, N_AIR, th)
    res = flat_interface(LYSO.n, N_AIR, LYSO.wavelength_um, th, dtype=torch.complex64)
    assert res.R_s == pytest.approx(float(R_s), abs=1e-3)


def test_geometric_escape_fraction_from_rcwa_grid() -> None:
    """Integrate indicator(T > 0) over the hemisphere on a 0.25-degree grid: must
    reproduce eta_1 to within the grid resolution (one step of sin theta d theta / 2
    at theta_c is about 1.5e-3 for LYSO->air)."""
    n1, n2, lam = LYSO.n, N_AIR, LYSO.wavelength_um
    thetas = np.radians(np.arange(0.0, 90.0, 0.25))
    t_unpol = np.array(
        [0.5 * (r.T_s + r.T_p) for r in (flat_interface(n1, n2, lam, float(t)) for t in thetas)]
    )
    eta_grid = float(np.trapezoid((t_unpol > 0).astype(float) * 0.5 * np.sin(thetas), thetas))
    assert eta_grid == pytest.approx(analytic.escape_fraction_one_face(n1, n2), abs=2e-3)
