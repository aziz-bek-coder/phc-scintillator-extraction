"""Tests for phcscint.optimize (derivation 05). Small orders and grids: fast."""

import math

import numpy as np
import pytest
import scipy.special as sp
import torch

from phcscint import optimize as opt
from phcscint.fresnel import unpolarised_transmittance
from phcscint.materials import LYSO, N_AIR, N_GREASE, n_si3n4_luke
from phcscint.rcwa import PhCLayer, pillar_permittivity, solve_phc

N_SIN = n_si3n4_luke(LYSO.wavelength_um)
LAM = LYSO.wavelength_um


def test_bessel_j1_matches_scipy_and_its_derivative() -> None:
    x = torch.linspace(0.0, 80.0, 801, dtype=torch.float64, requires_grad=True)
    j = opt.bessel_j1(x)
    np.testing.assert_allclose(j.detach().numpy(), sp.j1(x.detach().numpy()), atol=1e-13)
    j.sum().backward()
    xd = x.detach().numpy()
    np.testing.assert_allclose(x.grad.numpy(), 0.5 * (sp.j0(xd) - sp.jv(2, xd)), atol=1e-12)


def test_disk_matrix_matches_fft_of_a_fine_pixel_disk() -> None:
    """The analytic coefficients are the limit of the pixelated FFT path: the
    difference shrinks as the real-space grid is refined."""
    order, period, radius = 3, 0.40, 0.12
    rho = torch.tensor(radius / period, dtype=torch.float64)
    analytic = opt.disk_convolution_matrix(order, rho, N_SIN**2, N_GREASE**2)
    layer = PhCLayer(period, radius, 0.3, N_SIN)
    errs = []
    for n_grid in (128, 1024):
        eps = pillar_permittivity(layer, N_GREASE, n_grid=n_grid)
        sim = opt.AnalyticLayerRCWA(freq=1 / LAM, order=[order, order], L=[period, period],
                                    dtype=torch.complex128, device=opt.CPU)  # fmt: skip
        fft_conv = sim._material_conv(eps)
        errs.append(float(torch.max(torch.abs(fft_conv - analytic))))
    assert errs[1] < errs[0] / 4  # pixel staircase error falls with the grid
    assert errs[1] < 5e-3


def test_invisible_pillars_give_fresnel() -> None:
    """Pillars with the outside index: the layer is invisible, T = Fresnel n1 -> n2 for
    any period, fill factor and height (checks the normalised units end to end)."""
    for theta in (0.2, 0.7, 1.2):
        t = opt.transmission(LYSO.n, N_GREASE, LAM, N_GREASE, 0.37, 0.3, 0.25, theta, 0.3,
                             order=2)  # fmt: skip
        assert float(t) == pytest.approx(
            float(unpolarised_transmittance(LYSO.n, N_GREASE, theta)), abs=1e-9
        )


@pytest.mark.parametrize("n2", [N_GREASE, N_AIR])
def test_analytic_layer_agrees_with_fft_layer(n2) -> None:
    """Same structure through both permittivity paths (order 3): agreement to the
    pixel-staircase error of the n_grid = 512 FFT path."""
    layer = PhCLayer(0.40, 0.12, 0.30, N_SIN)
    for th, ph in ((math.radians(30), math.radians(10)), (math.radians(60), math.radians(30))):
        fft = solve_phc(LYSO.n, n2, LAM, layer, th, ph, order=3, n_grid=512)
        ana = opt.transmission(LYSO.n, n2, LAM, N_SIN, 0.40, layer.fill_factor, 0.30, th, ph,
                               order=3)  # fmt: skip
        assert float(ana) == pytest.approx(float(fft.T.sum()), abs=3e-3)


def test_gradient_matches_finite_differences() -> None:
    grid = opt.AngleGrid(n_theta=2, n_phi=1)
    w = opt.early_weight(100.0, 20000.0, LYSO.n)
    p = [0.40, 0.28, 0.30]

    def j_of(q):
        return opt.objective(w, LYSO.n, N_GREASE, LAM, N_SIN, *q, grid, order=2)

    a, f, h = (torch.tensor(v, dtype=torch.float64, requires_grad=True) for v in p)
    opt.objective(w, LYSO.n, N_GREASE, LAM, N_SIN, a, f, h, grid, order=2, backward=True)
    auto = [float(a.grad), float(f.grad), float(h.grad)]
    for k in range(3):
        step = 1e-5
        hi = list(p)
        lo = list(p)
        hi[k] += step
        lo[k] -= step
        fd = (j_of(hi) - j_of(lo)) / (2 * step)
        assert auto[k] == pytest.approx(fd, rel=1e-4, abs=1e-8)


def test_parameter_mapping_round_trip_and_bounds() -> None:
    b = opt.Bounds()
    x = opt.to_unconstrained(0.4, 0.28, 0.3, b)
    a, f, h = opt.to_physical(x, b)
    assert (float(a), float(f), float(h)) == pytest.approx((0.4, 0.28, 0.3), abs=1e-12)
    a, f, h = opt.to_physical(torch.tensor([50.0, -50.0, 50.0], dtype=torch.float64), b)
    assert float(a) <= b.period_um[1] and float(f) >= b.fill[0] and float(h) <= b.height_um[1]


def test_bare_objective_with_unit_weight_is_the_single_pass_fresnel() -> None:
    from phcscint.fresnel import escape_fraction_one_face_fresnel

    grid = opt.AngleGrid(n_theta=360, n_phi=1)
    j = opt.bare_objective(lambda th: 1.0, LYSO.n, N_GREASE, grid)
    assert j == pytest.approx(escape_fraction_one_face_fresnel(LYSO.n, N_GREASE), abs=1e-3)


def test_optimise_resumes_exactly() -> None:
    grid = opt.AngleGrid(n_theta=2, n_phi=1)
    w = opt.early_weight(100.0, 20000.0, LYSO.n)
    args = (opt.Bounds(), w, LYSO.n, N_GREASE, LAM, N_SIN, grid)
    full = opt.optimise((0.4, 0.28, 0.3), *args, order=1, steps=3, lr=0.2)
    part = opt.optimise((0.4, 0.28, 0.3), *args, order=1, steps=2, lr=0.2)
    resumed = opt.optimise((0.4, 0.28, 0.3), *args, order=1, steps=3, lr=0.2, history=part)
    assert [s["objective"] for s in resumed] == pytest.approx([s["objective"] for s in full])
    assert resumed[-1]["x_next"] == pytest.approx(full[-1]["x_next"])


class _Points:
    """Duck-typed angle grid with explicit (theta, phi, weight) points."""

    def __init__(self, pts: list[tuple[float, float, float]]) -> None:
        self.pts = pts

    def points(self) -> list[tuple[float, float, float]]:
        return self.pts


def test_closed_incidences_give_zero_and_keep_the_gradient_finite() -> None:
    """Air outside, a = 0.2 um: at theta 45 deg, phi 22.5 deg no transmitted order
    propagates (|u + g(m, n)| > 1 for every m, n), so T = 0 and has no autograd graph.
    The first M4 air run (38905911733, start 1) stopped on such an incidence."""
    closed = (math.radians(45.0), math.radians(22.5))
    open_ = (math.radians(20.0), math.radians(22.5))
    t = opt.transmission(LYSO.n, N_AIR, LAM, N_SIN, 0.2, 0.3, 0.2, *closed, order=2)
    assert float(t) == 0.0 and not t.requires_grad

    def unit(theta: float) -> float:
        return 1.0

    bounds = opt.Bounds(period_um=(0.1, 0.3))
    x = opt.to_unconstrained(0.2, 0.3, 0.2, bounds)
    args = (x, bounds, unit, LYSO.n, N_AIR, LAM, N_SIN)
    j_both, g_both, _ = opt.evaluate_with_gradient(
        *args, _Points([(*closed, 0.5), (*open_, 0.5)]), order=2
    )
    j_open, g_open, _ = opt.evaluate_with_gradient(*args, _Points([(*open_, 0.5)]), order=2)
    assert j_open > 0 and j_both == j_open
    torch.testing.assert_close(g_both, g_open, rtol=0, atol=0)
    assert torch.all(torch.isfinite(g_open)) and torch.count_nonzero(g_open) > 0
    j_closed, g_closed, _ = opt.evaluate_with_gradient(*args, _Points([(*closed, 1.0)]), order=2)
    assert j_closed == 0.0 and torch.count_nonzero(g_closed) == 0


def test_closed_incidence_builds_no_solver(monkeypatch) -> None:
    """At a closed incidence T = 0 is returned before the RCWA is built. The unused
    autograd graph of a built solver is never freed by a backward pass and kept about
    20 MB per call, which filled the runner's memory in the M4 air runs."""

    def boom(*args, **kwargs):
        raise AssertionError("solver built for a closed incidence")

    monkeypatch.setattr(opt, "AnalyticLayerRCWA", boom)
    a = torch.tensor(0.2, dtype=torch.float64, requires_grad=True)
    t = opt.transmission(LYSO.n, N_AIR, LAM, N_SIN, a, 0.3, 0.2, math.radians(45.0),
                         math.radians(22.5), order=2)  # fmt: skip
    assert float(t) == 0.0
