"""Environment smoke tests: the pinned toolchain imports and runs on CPU."""

import importlib

import numpy as np
import torch

import phcscint


def test_version() -> None:
    assert phcscint.__version__ == "0.0.1"


def test_torch_cpu_autograd() -> None:
    x = torch.tensor(1.5, requires_grad=True)
    y = (x**2).sum()
    y.backward()
    assert x.grad is not None
    assert abs(float(x.grad) - 3.0) < 1e-12


def test_torcwa_importable() -> None:
    torcwa = importlib.import_module("torcwa")
    assert hasattr(torcwa, "rcwa")


def test_rng_fixture_is_seeded(rng: np.random.Generator) -> None:
    a = rng.random(3)
    b = np.random.default_rng(20261015).random(3)
    assert np.array_equal(a, b)
