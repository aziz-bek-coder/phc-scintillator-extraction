"""Tests for phcscint.analytic.

All tests are xfail(strict=True) with reason "physics gate" until Aziz writes
docs/derivations/01-escape-cone-and-trapping.md and the stubs are implemented. Once
implemented, remove the marker: strict xfail turns an unexpected pass into a failure,
so CI will remind us.

Expected values below come from eta_1 = (1 - cos theta_c)/2 with the PROVISIONAL
indices in phcscint.materials. They are test oracles, not citable results; the
citable numbers are produced by scripts/escape_cone.py.
"""

import math

import numpy as np
import pytest

from phcscint import analytic
from phcscint.materials import BGO, LYSO, N_AIR, N_GREASE

GATE = pytest.mark.xfail(
    strict=True,
    raises=NotImplementedError,
    reason="physics gate: docs/derivations/01-escape-cone-and-trapping.md not yet written",
)


def _eta_oracle(n1: float, n2: float) -> float:
    return 0.5 * (1.0 - math.sqrt(1.0 - (n2 / n1) ** 2))


@GATE
@pytest.mark.parametrize(
    ("n1", "n2"),
    [(LYSO.n, N_AIR), (LYSO.n, N_GREASE), (BGO.n, N_AIR)],
)
def test_critical_angle_matches_snell(n1: float, n2: float) -> None:
    assert analytic.critical_angle(n1, n2) == pytest.approx(math.asin(n2 / n1), abs=1e-12)


@GATE
def test_critical_angle_rejects_no_tir() -> None:
    with pytest.raises(ValueError):
        analytic.critical_angle(1.5, 1.82)


@GATE
@pytest.mark.parametrize(
    ("n1", "n2"),
    [(LYSO.n, N_AIR), (LYSO.n, N_GREASE), (BGO.n, N_AIR)],
)
def test_escape_fraction_one_face(n1: float, n2: float) -> None:
    assert analytic.escape_fraction_one_face(n1, n2) == pytest.approx(
        _eta_oracle(n1, n2), abs=1e-12
    )


@GATE
def test_escape_fraction_limits() -> None:
    # n2 -> n1: cone opens to the hemisphere, half the photons hit this face.
    assert analytic.escape_fraction_one_face(1.82, 1.82 - 1e-9) == pytest.approx(0.5, abs=1e-4)
    # n2 -> 0: cone closes.
    assert analytic.escape_fraction_one_face(1.82, 1e-6) == pytest.approx(0.0, abs=1e-6)


@GATE
def test_specular_reflection_conserves_abs_components(rng: np.random.Generator) -> None:
    d = rng.normal(size=(1000, 3))
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    for axis in range(3):
        r = analytic.reflect_specular(d, axis)
        np.testing.assert_allclose(np.abs(r), np.abs(d), atol=1e-15)
        np.testing.assert_allclose(r[:, axis], -d[:, axis], atol=1e-15)


@GATE
def test_trapped_mask_is_invariant_under_reflections(rng: np.random.Generator) -> None:
    """The 'trapped rays stay trapped' statement, as a test."""
    d = rng.normal(size=(2000, 3))
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    trapped0 = analytic.is_trapped(d, LYSO.n, N_AIR)
    for axis in (0, 1, 2, 0, 1):
        d = analytic.reflect_specular(d, axis)
        np.testing.assert_array_equal(analytic.is_trapped(d, LYSO.n, N_AIR), trapped0)


@GATE
def test_trapped_fraction_matches_escape_cone(rng: np.random.Generator) -> None:
    """Isotropic directions: fraction NOT trapped w.r.t. the +z face should be
    2 * eta_1 (both z faces), within Monte Carlo error."""
    n = 200_000
    d = rng.normal(size=(n, 3))
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    frac_free = 1.0 - analytic.is_trapped(d, LYSO.n, N_AIR).mean()
    expected = 2.0 * _eta_oracle(LYSO.n, N_AIR)
    sigma = math.sqrt(expected * (1 - expected) / n)
    assert abs(frac_free - expected) < 4 * sigma
