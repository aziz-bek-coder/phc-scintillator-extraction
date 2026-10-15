"""Tests for phcscint.analytic (derivation 01).

Expected values are test oracles computed from eta_1 = (1 - cos theta_c)/2 with the
PROVISIONAL indices in phcscint.materials. Citable numbers come from
scripts/escape_cone.py.
"""

import math

import numpy as np
import pytest

from phcscint import analytic
from phcscint.materials import BGO, LYSO, LYSO_N_EPIC, N_AIR, N_GREASE, N_GREASE_BRIEF

PAIRS = [(LYSO.n, N_AIR), (LYSO.n, N_GREASE), (LYSO.n, N_GREASE_BRIEF), (BGO.n, N_AIR)]


def _eta_oracle(n1: float, n2: float) -> float:
    return 0.5 * (1.0 - math.sqrt(1.0 - (n2 / n1) ** 2))


@pytest.mark.parametrize(("n1", "n2"), PAIRS)
def test_critical_angle_matches_snell(n1: float, n2: float) -> None:
    assert analytic.critical_angle(n1, n2) == pytest.approx(math.asin(n2 / n1), abs=1e-12)


def test_critical_angle_rejects_no_tir() -> None:
    with pytest.raises(ValueError):
        analytic.critical_angle(1.5, 1.82)
    with pytest.raises(ValueError):
        analytic.critical_angle(1.5, 1.5)


@pytest.mark.parametrize(("n1", "n2"), PAIRS)
def test_escape_fraction_one_face(n1: float, n2: float) -> None:
    assert analytic.escape_fraction_one_face(n1, n2) == pytest.approx(
        _eta_oracle(n1, n2), abs=1e-12
    )


def test_escape_fraction_brief_values() -> None:
    """The project brief quotes LYSO->air ~8.2 %, LYSO->n=1.5 ~21.7 %, BGO->air ~5.7 %,
    computed with n_LYSO = 1.82 (the Epic Crystal value) and n2 = 1.5. Reproduce them at
    those indices to 0.1 percentage point. The code's production values (Luxium 1.81,
    EJ-550 grease 1.46) give different numbers; see results/m1_escape_cone.json."""
    assert analytic.escape_fraction_one_face(LYSO_N_EPIC, N_AIR) == pytest.approx(0.082, abs=0.001)
    assert analytic.escape_fraction_one_face(LYSO_N_EPIC, N_GREASE_BRIEF) == pytest.approx(
        0.217, abs=0.001
    )
    assert analytic.escape_fraction_one_face(BGO.n, N_AIR) == pytest.approx(0.057, abs=0.001)
    # and the sensitivity to the vendor spread in n_LYSO is below 0.4 percentage points
    for n2 in (N_AIR, N_GREASE, N_GREASE_BRIEF):
        d = analytic.escape_fraction_one_face(LYSO.n, n2) - analytic.escape_fraction_one_face(
            LYSO_N_EPIC, n2
        )
        assert abs(d) < 0.004


def test_escape_fraction_limits() -> None:
    # n2 -> n1: cone opens to the hemisphere, half the photons hit this face.
    assert analytic.escape_fraction_one_face(1.82, 1.82 - 1e-9) == pytest.approx(0.5, abs=1e-4)
    # n2 -> 0: cone closes; small-contrast expansion eta ~ (n2/n1)^2 / 4.
    assert analytic.escape_fraction_one_face(1.82, 1e-3) == pytest.approx(
        (1e-3 / 1.82) ** 2 / 4, rel=1e-5
    )


def test_specular_reflection_conserves_abs_components(rng: np.random.Generator) -> None:
    d = rng.normal(size=(1000, 3))
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    for axis in range(3):
        r = analytic.reflect_specular(d, axis)
        np.testing.assert_allclose(np.abs(r), np.abs(d), atol=1e-15)
        np.testing.assert_allclose(r[:, axis], -d[:, axis], atol=1e-15)
        assert r is not d


def test_trapped_mask_is_invariant_under_reflections(rng: np.random.Generator) -> None:
    """'Trapped rays stay trapped' (derivation 01, 2e), as a test."""
    d = rng.normal(size=(2000, 3))
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    trapped0 = analytic.is_trapped(d, LYSO.n, N_AIR)
    assert 0.5 < trapped0.mean() < 0.95
    for axis in (0, 1, 2, 0, 1):
        d = analytic.reflect_specular(d, axis)
        np.testing.assert_array_equal(analytic.is_trapped(d, LYSO.n, N_AIR), trapped0)


def test_trapped_fraction_matches_escape_cone(rng: np.random.Generator) -> None:
    """Isotropic directions: fraction NOT trapped w.r.t. the z faces is 2 eta_1 (both
    z faces). N = 200000, 4 sigma binomial tolerance."""
    n = 200_000
    d = rng.normal(size=(n, 3))
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    frac_free = 1.0 - analytic.is_trapped(d, LYSO.n, N_AIR).mean()
    expected = 2.0 * _eta_oracle(LYSO.n, N_AIR)
    sigma = math.sqrt(expected * (1 - expected) / n)
    assert abs(frac_free - expected) < 4 * sigma


def test_cones_overlap_threshold() -> None:
    assert not analytic.cones_overlap(LYSO.n, N_AIR)  # n2/n1 = 0.55 < 0.707
    assert analytic.cones_overlap(LYSO.n, N_GREASE)  # 1.46 / 1.81 = 0.81 > 0.707
    assert not analytic.cones_overlap(1.0, 1 / math.sqrt(2) - 1e-9)
    assert analytic.cones_overlap(1.0, 1 / math.sqrt(2) + 1e-9)


def test_escapable_fraction_cuboid_six_faces_air(rng: np.random.Generator) -> None:
    """Disjoint cones: closed form 6 eta_1 equals a direct Monte Carlo count of
    directions inside at least one cone (N = 400000, 4 sigma)."""
    expected = analytic.escapable_fraction_cuboid(LYSO.n)
    assert expected == pytest.approx(6 * _eta_oracle(LYSO.n, N_AIR), abs=1e-12)
    n = 400_000
    d = rng.normal(size=(n, 3))
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    cos_c = math.cos(analytic.critical_angle(LYSO.n, N_AIR))
    in_any = (np.abs(d) > cos_c).any(axis=1).mean()
    sigma = math.sqrt(expected * (1 - expected) / n)
    assert abs(in_any - expected) < 4 * sigma


def test_escapable_fraction_cuboid_mixed_faces(rng: np.random.Generator) -> None:
    """Grease on +z, air on the other five (derivation 01, A2): cones just miss
    overlapping, so the sum is still exact."""
    faces = (N_AIR,) * 5 + (N_GREASE,)
    expected = analytic.escapable_fraction_cuboid(LYSO.n, faces)
    assert expected == pytest.approx(
        5 * _eta_oracle(LYSO.n, N_AIR) + _eta_oracle(LYSO.n, N_GREASE), abs=1e-12
    )
    n = 400_000
    d = rng.normal(size=(n, 3))
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    cos_air = math.cos(analytic.critical_angle(LYSO.n, N_AIR))
    cos_gr = math.cos(analytic.critical_angle(LYSO.n, N_GREASE))
    in_any = (
        (np.abs(d[:, 0]) > cos_air)
        | (np.abs(d[:, 1]) > cos_air)
        | (-d[:, 2] > cos_air)
        | (d[:, 2] > cos_gr)
    ).mean()
    sigma = math.sqrt(expected * (1 - expected) / n)
    assert abs(in_any - expected) < 4 * sigma


def test_escapable_fraction_cuboid_rejects_overlap() -> None:
    with pytest.raises(ValueError):
        analytic.escapable_fraction_cuboid(LYSO.n, (N_GREASE,) * 6)
