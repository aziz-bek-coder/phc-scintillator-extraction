"""Monte Carlo ray model of one scintillator pixel (owner: Claude).

Implements docs/derivations/04-monte-carlo-pixel.md. Lengths in micrometres, times
in ps. Faces: 0 -x, 1 +x, 2 -y, 3 +y, 4 back (z = 0), 5 readout (z = Lz, normal +z).
Vectorised over photons with numpy; a batch is traced until every photon is detected,
absorbed, lost or past the time cut-off.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np

from phcscint.fresnel import fresnel_power
from phcscint.lut import LUT
from phcscint.timing import C_UM_PER_PS, cdf_from_times

WALL_KINDS = ("specular", "bare", "wrapped_specular", "wrapped_lambertian", "lambertian")
FACE_NAMES = ("-x", "+x", "-y", "+y", "back", "readout")


@dataclass(frozen=True)
class Pixel:
    n1: float
    wavelength_um: float
    lx_um: float = 3000.0
    ly_um: float = 3000.0
    lz_um: float = 20000.0
    n_group: float | None = None  # None: use n1 (derivation 04, 2c)
    abs_length_um: float = math.inf

    @property
    def ng(self) -> float:
        return self.n1 if self.n_group is None else self.n_group

    @property
    def size(self) -> np.ndarray:
        return np.array([self.lx_um, self.ly_um, self.lz_um])


@dataclass(frozen=True)
class Wall:
    """Wall model of derivation 04, 2d. n_outside is the medium beyond a bare face or
    in the air gap of a wrap."""

    kind: str
    reflectivity: float = 1.0
    n_outside: float = 1.0

    def __post_init__(self) -> None:
        if self.kind not in WALL_KINDS:
            raise ValueError(f"unknown wall kind {self.kind!r}; choose from {WALL_KINDS}")
        if not 0.0 <= self.reflectivity <= 1.0:
            raise ValueError("reflectivity must be in [0, 1]")


@dataclass(frozen=True)
class Readout:
    """Readout face: bare Fresnel into n_out, or a photonic-crystal LUT (derivation 04,
    2e). For a LUT, n_out must equal the LUT's outside index."""

    n_out: float
    lut: LUT | None = None

    def __post_init__(self) -> None:
        if self.lut is not None and abs(self.lut.config.n2 - self.n_out) > 1e-12:
            raise ValueError("readout n_out differs from the LUT's outside medium")


@dataclass
class MCResult:
    n_emitted: int
    times_ps: np.ndarray  # detection times of detected photons
    readout_hits: np.ndarray  # number of readout interactions up to and incl. detection
    counts: dict[str, int]
    t_max_ps: float
    meta: dict = field(default_factory=dict)

    @property
    def efficiency(self) -> float:
        return self.counts["detected"] / self.n_emitted

    def cdf(self, t_grid: np.ndarray) -> np.ndarray:
        return cdf_from_times(self.times_ps, self.n_emitted, t_grid)

    def early_yield(self, tau_ps: float) -> float:
        return float(np.count_nonzero(self.times_ps <= tau_ps) / self.n_emitted)

    def first_pass_fraction(self) -> float:
        """Fraction of emitted photons detected at their first readout hit."""
        return float(np.count_nonzero(self.readout_hits == 1) / self.n_emitted)


# ------------------------------------------------------------------ helpers


def _unpol_R(n1: float, n2: float, cos_t: np.ndarray) -> np.ndarray:
    th = np.arccos(np.clip(cos_t, 0.0, 1.0))
    r_s, r_p, _, _ = fresnel_power(n1, n2, th)
    return 0.5 * (r_s + r_p)


def _unpol_T(n1: float, n2: float, cos_t: np.ndarray) -> np.ndarray:
    th = np.arccos(np.clip(cos_t, 0.0, 1.0))
    _, _, t_s, t_p = fresnel_power(n1, n2, th)
    return 0.5 * (t_s + t_p)


def _isotropic(n: int, rng: np.random.Generator) -> np.ndarray:
    w = rng.uniform(-1.0, 1.0, n)
    phi = rng.uniform(0.0, 2 * math.pi, n)
    s = np.sqrt(1.0 - w * w)
    return np.stack([s * np.cos(phi), s * np.sin(phi), w], axis=1)


def _direction_about_axis(
    cos_t: np.ndarray, axis: np.ndarray, inward_sign: np.ndarray, rng: np.random.Generator
) -> np.ndarray:
    """Unit vectors with component inward_sign * cos_t along `axis` (per photon) and a
    uniformly random azimuth around it."""
    n = cos_t.size
    sin_t = np.sqrt(np.clip(1.0 - cos_t * cos_t, 0.0, None))
    psi = rng.uniform(0.0, 2 * math.pi, n)
    d = np.empty((n, 3))
    a1 = (axis + 1) % 3
    a2 = (axis + 2) % 3
    rows = np.arange(n)
    d[rows, axis] = inward_sign * cos_t
    d[rows, a1] = sin_t * np.cos(psi)
    d[rows, a2] = sin_t * np.sin(psi)
    return d


# ------------------------------------------------------------------ interactions


def _wall_interaction(
    wall: Wall,
    n1: float,
    d: np.ndarray,
    axis: np.ndarray,
    outward_sign: np.ndarray,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Apply one wall model to photons hitting faces with normal `axis`.

    Returns (survive, new_d, escaped): survive marks photons back in the crystal with
    direction new_d; escaped marks photons that left through a bare face (the rest of
    the non-survivors were absorbed at the wall/reflector)."""
    n = d.shape[0]
    rows = np.arange(n)
    cos_t = np.abs(d[rows, axis])
    spec = d.copy()
    spec[rows, axis] *= -1.0
    u = rng.random(n)
    escaped = np.zeros(n, dtype=bool)
    rho = wall.reflectivity
    inward = -outward_sign

    if wall.kind == "specular":
        survive = u < rho
        return survive, spec, escaped

    if wall.kind == "lambertian":
        survive = u < rho
        new_d = _direction_about_axis(np.sqrt(rng.random(n)), axis, inward, rng)
        return survive, new_d, escaped

    r_f = _unpol_R(n1, wall.n_outside, cos_t)
    if wall.kind == "bare":
        survive = u < r_f
        escaped = ~survive
        return survive, spec, escaped

    if wall.kind == "wrapped_specular":
        t_f = 1.0 - r_f
        with np.errstate(divide="ignore", invalid="ignore"):
            p_ret = np.where(r_f >= 1.0, 1.0, r_f + t_f * t_f * rho / (1.0 - rho * r_f))
        survive = u < p_ret
        return survive, spec, escaped

    # wrapped_lambertian
    new_d = spec.copy()
    survive = u < r_f  # specular reflection at the polished crystal face
    pending = np.flatnonzero(~survive)  # photons now in the gap, heading to the reflector
    n_air_in = wall.n_outside
    guard = 0
    while pending.size:
        guard += 1
        if guard > 10_000:
            raise RuntimeError("wrapped_lambertian loop did not terminate")
        refl = rng.random(pending.size) < rho
        pending = pending[refl]  # the others are absorbed by the reflector
        if not pending.size:
            break
        cos_a = np.sqrt(rng.random(pending.size))  # Lambertian emission into the gap
        t_in = _unpol_T(n_air_in, n1, cos_a)  # gap -> crystal
        enter = rng.random(pending.size) < t_in
        ent = pending[enter]
        if ent.size:
            sin_a = np.sqrt(1.0 - cos_a[enter] ** 2)
            sin_1 = sin_a * n_air_in / n1
            cos_1 = np.sqrt(1.0 - sin_1 * sin_1)
            new_d[ent] = _direction_about_axis(cos_1, axis[ent], inward[ent], rng)
            survive[ent] = True
        pending = pending[~enter]  # reflected at the crystal back to the reflector
    return survive, new_d, escaped


def _readout_interaction(
    readout: Readout, n1: float, d: np.ndarray, rng: np.random.Generator
) -> tuple[np.ndarray, np.ndarray]:
    """Returns (detected, new_d) for photons hitting the readout face (d_z > 0)."""
    if readout.lut is None:
        t = _unpol_T(n1, readout.n_out, d[:, 2])
        detected = rng.random(d.shape[0]) < t
        new_d = d.copy()
        new_d[:, 2] *= -1.0
        return detected, new_d
    return readout.lut.sample_batch(d, rng)


# ------------------------------------------------------------------ driver


def run(
    pixel: Pixel,
    walls: Wall | Sequence[Wall],
    readout: Readout,
    n_photons: int,
    rng: np.random.Generator,
    *,
    t_max_ps: float = 5000.0,
    batch: int = 200_000,
) -> MCResult:
    """Trace n_photons emitted uniformly in the volume with isotropic directions.

    walls: one Wall for all five non-readout faces, or a sequence of five for faces
    0..4 (-x, +x, -y, +y, back)."""
    if isinstance(walls, Wall):
        walls = (walls,) * 5
    walls = tuple(walls)
    if len(walls) != 5:
        raise ValueError("need one wall model or five (faces -x, +x, -y, +y, back)")
    if readout.lut is not None and abs(readout.lut.config.n1 - pixel.n1) > 1e-12:
        raise ValueError("LUT was built for a different scintillator index")

    size = pixel.size
    path_cap = t_max_ps * C_UM_PER_PS / pixel.ng
    counts = {"detected": 0, "absorbed_bulk": 0, "lost_wall": 0, "escaped_wall": 0, "capped": 0}
    times_all: list[np.ndarray] = []
    hits_all: list[np.ndarray] = []
    steps = 0

    remaining = n_photons
    while remaining > 0:
        n = min(batch, remaining)
        remaining -= n
        pos = rng.random((n, 3)) * size
        d = _isotropic(n, rng)
        path = np.zeros(n)
        budget = (
            rng.exponential(pixel.abs_length_um, n)
            if math.isfinite(pixel.abs_length_um)
            else np.full(n, np.inf)
        )
        hits = np.zeros(n, dtype=np.int64)
        alive = np.arange(n)

        while alive.size:
            steps += alive.size
            p = pos[alive]
            dd = d[alive]
            with np.errstate(divide="ignore", invalid="ignore"):
                t_hi = (size[None, :] - p) / dd
                t_lo = -p / dd
            tt = np.where(dd > 0, t_hi, np.where(dd < 0, t_lo, np.inf))
            ax = np.argmin(tt, axis=1)
            step = np.maximum(tt[np.arange(alive.size), ax], 0.0)
            new_path = path[alive] + step

            absorbed = new_path >= budget[alive]
            capped = ~absorbed & (new_path > path_cap)
            counts["absorbed_bulk"] += int(absorbed.sum())
            counts["capped"] += int(capped.sum())
            go = ~(absorbed | capped)
            idx = alive[go]
            ax = ax[go]
            pos[idx] += step[go, None] * d[idx]
            path[idx] = new_path[go]
            outward = np.where(d[idx, ax] > 0, 1.0, -1.0)
            pos[idx, ax] = np.where(outward > 0, size[ax], 0.0)  # snap onto the face
            face = 2 * ax + (outward > 0)

            survivors = []
            # readout face
            sel = face == 5
            if sel.any():
                ids = idx[sel]
                hits[ids] += 1
                det, new_d = _readout_interaction(readout, pixel.n1, d[ids], rng)
                counts["detected"] += int(det.sum())
                times_all.append(path[ids[det]] * pixel.ng / C_UM_PER_PS)
                hits_all.append(hits[ids[det]])
                back = ~det
                d[ids[back]] = new_d[back]
                survivors.append(ids[back])
            # other faces
            for f in range(5):
                sel = face == f
                if not sel.any():
                    continue
                ids = idx[sel]
                surv, new_d, esc = _wall_interaction(
                    walls[f], pixel.n1, d[ids], ax[sel], outward[sel], rng
                )
                counts["escaped_wall"] += int(esc.sum())
                counts["lost_wall"] += int((~surv & ~esc).sum())
                d[ids[surv]] = new_d[surv]
                survivors.append(ids[surv])
            alive = np.concatenate(survivors) if survivors else np.empty(0, dtype=int)

    times = np.concatenate(times_all) if times_all else np.empty(0)
    rh = np.concatenate(hits_all) if hits_all else np.empty(0, dtype=np.int64)
    total = sum(counts.values())
    if total != n_photons:
        raise RuntimeError(f"photon bookkeeping failed: {total} != {n_photons}")
    return MCResult(
        n_emitted=n_photons,
        times_ps=times,
        readout_hits=rh,
        counts=counts,
        t_max_ps=t_max_ps,
        meta={"photon_steps": steps},
    )
