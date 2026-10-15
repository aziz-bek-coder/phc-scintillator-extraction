"""Shared fixtures (owner: Claude). Keep this file small; module-specific fixtures
belong next to their tests."""

import numpy as np
import pytest


@pytest.fixture
def rng() -> np.random.Generator:
    """Seeded generator so Monte Carlo tests are reproducible."""
    return np.random.default_rng(20261015)
