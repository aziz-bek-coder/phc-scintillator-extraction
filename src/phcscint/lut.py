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

from phcscint.provenance import REPO_ROOT, git_commit
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

    # ---------------------------------------------------------------- batch sampling
    def _bilinear_batch(self, theta: np.ndarray, phi: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Vectorised version of _bilinear: returns (T, R) of shape (N, K)."""

        def bracket(x: np.ndarray, grid: np.ndarray):
            if len(grid) == 1:
                z = np.zeros(x.size, dtype=int)
                return z, z, np.zeros(x.size)
            xc = np.clip(x, grid[0], grid[-1])
            j = np.clip(np.searchsorted(grid, xc) - 1, 0, len(grid) - 2)
            w = (xc - grid[j]) / (grid[j + 1] - grid[j])
            return j, j + 1, w

        i0, i1, wt = bracket(theta, self.theta)
        j0, j1, wp = bracket(phi, self.phi)
        wt = wt[:, None]
        wp = wp[:, None]

        def mix(a: np.ndarray) -> np.ndarray:
            return (
                (1 - wt) * (1 - wp) * a[i0, j0]
                + (1 - wt) * wp * a[i0, j1]
                + wt * (1 - wp) * a[i1, j0]
                + wt * wp * a[i1, j1]
            )

        return mix(self.T), mix(self.R)

    def channel_powers_batch(
        self, d: np.ndarray, tol: float = 1e-12
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """For unit directions d (N, 3) with d_z > 0 hitting the PhC from inside, return
        (orders (N, K, 2), T (N, K), R (N, K), u_mn (N, K, 2)) in the actual frame, after
        C4v mapping, bilinear interpolation, masking of closed orders and
        renormalisation (derivation 03, 2h-2i)."""
        n1, n2, g = self.config.n1, self.config.n2, self.g
        u = n1 * d[:, :2]
        qs = np.stack(C4V)  # (8, 2, 2)
        v = np.einsum("qji,nj->nqi", qs, u)  # Q^T u for every Q
        ok = (v[..., 1] >= -tol) & (v[..., 0] >= v[..., 1] - tol)
        qi = np.argmax(ok, axis=1)
        vw = v[np.arange(len(u)), qi]
        phi_w = np.where(np.hypot(vw[:, 0], vw[:, 1]) > 0, np.arctan2(vw[:, 1], vw[:, 0]), 0.0)
        theta = np.arccos(np.clip(d[:, 2], -1.0, 1.0))
        t_w, r_w = self._bilinear_batch(theta, phi_w)
        orders = np.einsum("nij,kj->nki", qs[qi], self.orders)  # actual order = Q o'
        umn = u[:, None, :] + g * orders
        mag = np.hypot(umn[..., 0], umn[..., 1])
        t = np.where(mag < n2, t_w, 0.0)
        r = np.where(mag < n1, r_w, 0.0)
        tot = t.sum(1) + r.sum(1)
        if np.any(tot <= 0):
            raise RuntimeError("no open channel after masking (should not happen)")
        return orders, t / tot[:, None], r / tot[:, None], umn

    def sample_batch(
        self, d: np.ndarray, rng: np.random.Generator
    ) -> tuple[np.ndarray, np.ndarray]:
        """Draw one channel per photon (derivation 04, 2e). Returns (transmitted (N,),
        new_d (N, 3)); new_d is the reflected direction, eq. (3) of derivation 04, and
        is meaningless for transmitted photons."""
        n = d.shape[0]
        _, t, r, umn = self.channel_powers_batch(d)
        k = t.shape[1]
        cum = np.cumsum(np.concatenate([t, r], axis=1), axis=1)
        x = rng.random(n)[:, None] * cum[:, -1:]
        ch = np.minimum((cum < x).sum(axis=1), 2 * k - 1)
        transmitted = ch < k
        new_d = np.zeros((n, 3))
        refl = ~transmitted
        if refl.any():
            um = umn[np.flatnonzero(refl), ch[refl] - k]  # (n_refl, 2)
            n1 = self.config.n1
            new_d[refl, 0] = um[:, 0] / n1
            new_d[refl, 1] = um[:, 1] / n1
            new_d[refl, 2] = -np.sqrt(np.clip(1.0 - (um[:, 0] ** 2 + um[:, 1] ** 2) / n1**2, 0, 1))
        return transmitted, new_d

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

    def weighted_single_pass(self, weight) -> float:
        """Eq. (9) of derivation 03 with an angular weight w(theta) inside the integral,
        e.g. derivation 05, eq. (1): the early-photon yield from the first pass."""
        th, ph = self.theta, self.phi
        dth = th[1] - th[0]
        phi_int = np.trapezoid(self.T.sum(axis=-1), ph, axis=1)
        w = np.array([weight(float(t)) for t in th])
        return float(np.sum(8 * phi_int * w * np.sin(th) * dth / (4 * math.pi)))


def build_lut(
    config: LUTConfig,
    *,
    cache_dir: Path = DATA_DIR,
    checkpoint_seconds: float = 60.0,
    max_points: int | None = None,
    progress: Callable[[str], None] | None = print,
    should_stop: Callable[[], bool] | None = None,
) -> tuple[LUT, Path]:
    """Build (or load from cache) the LUT for config. Resumable: completed points are
    checkpointed to <key>.partial.npz and skipped on restart. If max_points is given,
    stop after that many new points and return the partial table (for tests). If
    should_stop() becomes true (a remote job's deadline), checkpoint and return the
    partial table; meta["complete"] is False in both cases."""
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
    # every commit whose code computed some of the points (more than one only if a
    # build was interrupted and resumed after a commit)
    commits: list[str] = []
    if partial.exists():
        with np.load(partial, allow_pickle=False) as z:
            if str(z["config"]) == config.to_json():
                t_arr, r_arr, done = z["T"], z["R"], z["done"].astype(bool)
                if "commits" in z.files:
                    commits = json.loads(str(z["commits"]))
                else:
                    commits = ["not recorded"]
    if git_commit() not in commits:
        commits.append(git_commit())
    seconds = 0.0

    def checkpoint() -> None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        tmp = partial.with_suffix(".tmp.npz")
        np.savez_compressed(
            tmp,
            config=config.to_json(),
            T=t_arr,
            R=r_arr,
            done=done,
            commits=json.dumps(commits),
        )
        os.replace(tmp, partial)

    last = time.perf_counter()
    new = 0
    for i, th in enumerate(config.theta_deg):
        for j, ph in enumerate(config.phi_deg):
            if done[i, j]:
                continue
            if should_stop is not None and should_stop():
                checkpoint()
                return LUT(config, orders, t_arr, r_arr, {"complete": False}), partial
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
        {
            "complete": True,
            "max_energy_error": energy_err,
            "solve_seconds_this_run": seconds,
            "built_at_commits": commits,
        },
    )
    lut.save(final)
    if partial.exists():
        partial.unlink()
    return lut, final
