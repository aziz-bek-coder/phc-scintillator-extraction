"""Angle-resolved lookup table (LUT) of diffraction-order powers (owner: Claude).

Implements docs/derivations/03-grating-orders-and-lut.md, sections 2h to 2j:
- C4v symmetry: the table covers phi in [0, 45] deg; any other azimuth is mapped into
  that wedge by one of the 8 operations of C4v, and order indices are mapped back.
- Disk cache with resumable builds: a partial file is checkpointed while building and
  completed points are skipped on restart.
- Bilinear interpolation in (theta, phi), then the propagating set is recomputed at the
  exact incidence and the powers are renormalised (2i).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from phcscint.provenance import REPO_ROOT
from phcscint.rcwa import PhCLayer, order_window, propagating_mask, solve_phc

DATA_DIR = REPO_ROOT / "data" / "lut"

# The 8 operations of C4v as integer 2x2 matrices acting on in-plane vectors and on
# order indices (m, n) alike.
C4V: tuple[np.ndarray, ...] = tuple(
    np.array(q, dtype=int)
    for q in (
        [[1, 0], [0, 1]],  # identity
        [[0, -1], [1, 0]],  # rotation +90
        [[-1, 0], [0, -1]],  # rotation 180
        [[0, 1], [-1, 0]],  # rotation 270
        [[1, 0], [0, -1]],  # mirror y -> -y
        [[-1, 0], [0, 1]],  # mirror x -> -x
        [[0, 1], [1, 0]],  # mirror in the diagonal x = y
        [[0, -1], [-1, 0]],  # mirror in the anti-diagonal x = -y
    )
)


def reduce_to_wedge(u: np.ndarray, tol: float = 1e-12) -> tuple[np.ndarray, np.ndarray]:
    """Return (Q, v) with v = Q^T u lying in the wedge 0 <= phi <= 45 deg (Q orthogonal,
    so Q^T = Q^-1). For u = 0 returns the identity."""
    u = np.asarray(u, dtype=float)
    if np.hypot(u[0], u[1]) < tol:
        return C4V[0], u.copy()
    for q in C4V:
        v = q.T @ u
        if v[1] >= -tol and v[0] >= v[1] - tol:
            return q, v
    raise RuntimeError("no C4v operation maps u into the wedge (should not happen)")


@dataclass(frozen=True)
class LUTConfig:
    """Everything that determines the table contents. Its hash names the cache file."""

    n1: float
    n2: float
    wavelength_um: float
    layer: PhCLayer
    order: int
    n_grid: int
    theta_deg: tuple[float, ...]
    phi_deg: tuple[float, ...]
    window: int
    edge_sharpness: float = 1000.0
    label: str = ""

    def key(self) -> str:
        d = asdict(self)
        d.pop("label")
        blob = json.dumps(d, sort_keys=True).encode()
        return hashlib.sha1(blob).hexdigest()[:12]

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)

    @staticmethod
    def from_json(s: str) -> LUTConfig:
        d = json.loads(s)
        d["layer"] = PhCLayer(**d["layer"])
        d["theta_deg"] = tuple(d["theta_deg"])
        d["phi_deg"] = tuple(d["phi_deg"])
        return LUTConfig(**d)


def window_for(n1: float, wavelength_um: float, period_um: float) -> int:
    """Smallest order window that holds every order able to propagate in the crystal
    for any incidence: K >= ceil(2 n1 / g), g = lambda / a (derivation 03, 2i)."""
    g = wavelength_um / period_um
    return int(math.ceil(2 * n1 / g))


def midpoint_grid(lo: float, hi: float, step: float) -> tuple[float, ...]:
    n = int(round((hi - lo) / step))
    return tuple(float(lo + (i + 0.5) * step) for i in range(n))


def inclusive_grid(lo: float, hi: float, step: float) -> tuple[float, ...]:
    n = int(round((hi - lo) / step))
    return tuple(float(lo + i * step) for i in range(n + 1))


@dataclass
class LUT:
    config: LUTConfig
    orders: np.ndarray  # (K, 2)
    T: np.ndarray  # (n_theta, n_phi, K)
    R: np.ndarray  # (n_theta, n_phi, K)
    meta: dict = field(default_factory=dict)

    @property
    def theta(self) -> np.ndarray:
        return np.radians(np.array(self.config.theta_deg))

    @property
    def phi(self) -> np.ndarray:
        return np.radians(np.array(self.config.phi_deg))

    @property
    def g(self) -> float:
        return self.config.wavelength_um / self.config.layer.period_um

    # ---------------------------------------------------------------- persistence
    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp.npz")
        np.savez_compressed(
            tmp,
            config=self.config.to_json(),
            orders=self.orders,
            T=self.T,
            R=self.R,
            meta=json.dumps(self.meta),
        )
        os.replace(tmp, path)

    @staticmethod
    def load(path: Path) -> LUT:
        with np.load(path, allow_pickle=False) as z:
            return LUT(
                config=LUTConfig.from_json(str(z["config"])),
                orders=z["orders"],
                T=z["T"],
                R=z["R"],
                meta=json.loads(str(z["meta"])),
            )

    # ---------------------------------------------------------------- lookup
    def _bilinear(self, theta: float, phi: float) -> tuple[np.ndarray, np.ndarray]:
        th, ph = self.theta, self.phi

        def bracket(x, grid):
            if len(grid) == 1 or x <= grid[0]:
                return 0, 0, 0.0
            if x >= grid[-1]:
                return len(grid) - 1, len(grid) - 1, 0.0
            j = int(np.searchsorted(grid, x)) - 1
            w = (x - grid[j]) / (grid[j + 1] - grid[j])
            return j, j + 1, float(w)

        i0, i1, wt = bracket(theta, th)
        j0, j1, wp = bracket(phi, ph)

        def mix(a):
            return (
                (1 - wt) * (1 - wp) * a[i0, j0]
                + (1 - wt) * wp * a[i0, j1]
                + wt * (1 - wp) * a[i1, j0]
                + wt * wp * a[i1, j1]
            )

        return mix(self.T), mix(self.R)

    def lookup(self, theta: float, phi: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Order powers for incidence (theta, phi) in radians, any phi.

        Returns (orders, T, R) in the actual (unreduced) frame. Only orders that
        propagate at this exact incidence are kept, and powers are renormalised so
        that sum(T) + sum(R) = 1 (derivation 03, 2i)."""
        n1 = self.config.n1
        u = n1 * math.sin(theta) * np.array([math.cos(phi), math.sin(phi)])
        q, v = reduce_to_wedge(u)
        phi_w = math.atan2(v[1], v[0]) if np.hypot(*v) > 0 else 0.0
        t_w, r_w = self._bilinear(theta, phi_w)
        orders = self.orders @ q.T  # actual order = Q (m', n')
        open_t = propagating_mask(orders, u, self.g, self.config.n2)
        open_r = propagating_mask(orders, u, self.g, n1)
        t = np.where(open_t, t_w, 0.0)
        r = np.where(open_r, r_w, 0.0)
        s = t.sum() + r.sum()
        if s <= 0:
            raise RuntimeError("no open channel after masking (should not happen)")
        return orders, t / s, r / s

    # ---------------------------------------------------------------- integrals
    def single_pass_extraction(self, theta_split_deg: float | None = None) -> dict[str, float]:
        """Eq. (9) of derivation 03 by midpoint rule in theta (the theta grid must be a
        midpoint grid) and trapezoid rule in phi over [0, 45] deg, times 8 by C4v.
        If theta_split_deg is given, also returns the parts below and above it."""
        th, ph = self.theta, self.phi
        dth = th[1] - th[0]
        t_tot = self.T.sum(axis=-1)  # (n_theta, n_phi)
        phi_int = np.trapezoid(t_tot, ph, axis=1)  # integral over [0, pi/4]
        per_theta = 8 * phi_int * np.sin(th) * dth / (4 * math.pi)
        out = {"eta_single_pass": float(per_theta.sum())}
        if theta_split_deg is not None:
            below = np.degrees(th) < theta_split_deg
            out["in_cone_part"] = float(per_theta[below].sum())
            out["trapped_part"] = float(per_theta[~below].sum())
        return out


def build_lut(
    config: LUTConfig,
    *,
    cache_dir: Path = DATA_DIR,
    checkpoint_seconds: float = 60.0,
    max_points: int | None = None,
    progress: Callable[[str], None] | None = print,
) -> tuple[LUT, Path]:
    """Build (or load from cache) the LUT for config. Resumable: completed points are
    checkpointed to <key>.partial.npz and skipped on restart. If max_points is given,
    stop after that many new points and return the partial table (for tests)."""
    name = (config.label + "_" if config.label else "") + config.key()
    final = cache_dir / f"{name}.npz"
    partial = cache_dir / f"{name}.partial.npz"
    if final.exists():
        return LUT.load(final), final

    orders = order_window(config.window)
    n_t, n_p, n_o = len(config.theta_deg), len(config.phi_deg), len(orders)
    t_arr = np.zeros((n_t, n_p, n_o))
    r_arr = np.zeros((n_t, n_p, n_o))
    done = np.zeros((n_t, n_p), dtype=bool)
    if partial.exists():
        with np.load(partial, allow_pickle=False) as z:
            if str(z["config"]) == config.to_json():
                t_arr, r_arr, done = z["T"], z["R"], z["done"].astype(bool)
    seconds = 0.0

    def checkpoint() -> None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        tmp = partial.with_suffix(".tmp.npz")
        np.savez_compressed(tmp, config=config.to_json(), T=t_arr, R=r_arr, done=done)
        os.replace(tmp, partial)

    last = time.perf_counter()
    new = 0
    for i, th in enumerate(config.theta_deg):
        for j, ph in enumerate(config.phi_deg):
            if done[i, j]:
                continue
            t0 = time.perf_counter()
            op = solve_phc(
                config.n1,
                config.n2,
                config.wavelength_um,
                config.layer,
                math.radians(th),
                math.radians(ph),
                order=config.order,
                n_grid=config.n_grid,
                edge_sharpness=config.edge_sharpness,
                report_window=config.window,
            )
            seconds += time.perf_counter() - t0
            t_arr[i, j], r_arr[i, j] = op.T, op.R
            done[i, j] = True
            new += 1
            if time.perf_counter() - last > checkpoint_seconds:
                checkpoint()
                last = time.perf_counter()
                if progress:
                    progress(f"  {int(done.sum())}/{done.size} points ({name})")
            if max_points is not None and new >= max_points:
                checkpoint()
                return LUT(config, orders, t_arr, r_arr, {"complete": False}), partial

    energy_err = float(np.max(np.abs(t_arr.sum(-1) + r_arr.sum(-1) - 1.0)))
    lut = LUT(
        config,
        orders,
        t_arr,
        r_arr,
        {"complete": True, "max_energy_error": energy_err, "solve_seconds_this_run": seconds},
    )
    lut.save(final)
    if partial.exists():
        partial.unlink()
    return lut, final
