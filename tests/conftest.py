"""Shared fixtures (owner: Claude). Keep this file small; module-specific fixtures
belong next to their tests.

Thread limits (AGENTS.md, compute rules): on a laptop the tests use 2 threads. CI sets
OMP_NUM_THREADS itself. The environment variable must be set before torch is imported,
which is why it is done at the top of this file.
"""

import os

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", os.environ["OMP_NUM_THREADS"])

import numpy as np  # noqa: E402
import pytest  # noqa: E402
import torch  # noqa: E402

torch.set_num_threads(int(os.environ["OMP_NUM_THREADS"]))


@pytest.fixture
def rng() -> np.random.Generator:
    """Seeded generator so Monte Carlo tests are reproducible."""
    return np.random.default_rng(20261015)
