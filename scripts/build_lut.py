"""Build (or load from cache) the angle-resolved LUT for the reference photonic crystal
and report its single-pass extraction against the bare face (derivation 03, 2j).

Grids (docs/decisions.md): coarse = theta 2 deg midpoints x phi 5 deg (0..45);
fine = theta 1 deg midpoints x phi 2.5 deg. Resumable: re-run the same command after an
interruption and finished points are skipped.

Produces data/lut/<label>_<hash>.npz (git-ignored), results/m2_lut_<label>.json and
docs/figures/m2_lut_<label>.png.
Run: python scripts/build_lut.py --medium grease --grid coarse --order 7
"""

from __future__ import annotations

import argparse
import math
import time

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from phcscint import analytic  # noqa: E402
from phcscint.fresnel import escape_fraction_one_face_fresnel, fresnel_power  # noqa: E402
from phcscint.lut import LUTConfig, build_lut, inclusive_grid, midpoint_grid, window_for  # noqa: E402
from phcscint.materials import LYSO, N_AIR, N_GREASE, n_si3n4_luke  # noqa: E402
from phcscint.provenance import FIGURES_DIR, git_commit, save_results  # noqa: E402
from phcscint.rcwa import PhCLayer  # noqa: E402

REFERENCE = PhCLayer(
    period_um=0.40, radius_um=0.12, height_um=0.30, n_pillar=n_si3n4_luke(LYSO.wavelength_um)
)
GRIDS = {
    "coarse": (midpoint_grid(0.0, 90.0, 2.0), inclusive_grid(0.0, 45.0, 5.0)),
    "fine": (midpoint_grid(0.0, 90.0, 1.0), inclusive_grid(0.0, 45.0, 2.5)),
}
MEDIA = {"grease": N_GREASE, "air": N_AIR}


def reference_config(medium: str, grid: str, order: int, n_grid: int = 256) -> LUTConfig:
    n2 = MEDIA[medium]
    th, ph = GRIDS[grid]
    return LUTConfig(
        n1=LYSO.n,
        n2=n2,
        wavelength_um=LYSO.wavelength_um,
        layer=REFERENCE,
        order=order,
        n_grid=n_grid,
        theta_deg=th,
        phi_deg=ph,
        window=window_for(LYSO.n, LYSO.wavelength_um, REFERENCE.period_um),
        label=f"ref_lyso_{medium}_{grid}_M{order}",
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--medium", choices=list(MEDIA), default="grease")
    ap.add_argument("--grid", choices=list(GRIDS), default="coarse")
    ap.add_argument("--order", type=int, default=7)
    args = ap.parse_args()
    cfg = reference_config(args.medium, args.grid, args.order)
    assert cfg.order >= cfg.window, "solver truncation must cover the reporting window"
    print(f"commit {git_commit()}  {cfg.label}  points={len(cfg.theta_deg) * len(cfg.phi_deg)}")
    t0 = time.perf_counter()
    lut, path = build_lut(cfg)
    wall = time.perf_counter() - t0
    n2 = cfg.n2
    theta_c = math.degrees(analytic.critical_angle(LYSO.n, n2))
    phc = lut.single_pass_extraction(theta_split_deg=theta_c)

    # bare face on the same quadrature (Fresnel in the (0,0) order), and exactly
    th = lut.theta
    _, _, ts, tp = fresnel_power(LYSO.n, n2, th)
    bare_t = 0.5 * (ts + tp)
    dth = th[1] - th[0]
    bare_grid = float(np.sum(bare_t * np.sin(th) * dth) / 2)
    bare_exact = escape_fraction_one_face_fresnel(LYSO.n, n2)

    t_phi_mean = np.trapezoid(lut.T.sum(-1), lut.phi, axis=1) / (lut.phi[-1] - lut.phi[0])
    print(f"LUT {path.name}: max energy error {lut.meta.get('max_energy_error'):.1e}")
    print(
        f"single pass: PhC {100 * phc['eta_single_pass']:.3f}% "
        f"(in-cone cells {100 * phc['in_cone_part']:.3f}%, trapped cells "
        f"{100 * phc['trapped_part']:.3f}%) | bare Fresnel {100 * bare_grid:.3f}% on this grid, "
        f"{100 * bare_exact:.3f}% exact"
    )

    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    im = axes[0].imshow(
        lut.T.sum(-1).T,
        origin="lower",
        aspect="auto",
        extent=[0, 90, cfg.phi_deg[0], cfg.phi_deg[-1]],
        vmin=0,
        vmax=1,
        cmap="viridis",
    )
    axes[0].axvline(theta_c, color="w", ls="--", lw=1)
    axes[0].set_xlabel("θ in LYSO [deg]")
    axes[0].set_ylabel("φ [deg] (C4v wedge)")
    axes[0].set_title(f"total transmission, reference PhC → {args.medium}", fontsize=9)
    fig.colorbar(im, ax=axes[0])
    deg = np.degrees(th)
    axes[1].plot(deg, t_phi_mean, "-", label="reference PhC (mean over φ)")
    axes[1].plot(deg, bare_t, "--", label="bare face (Fresnel)")
    axes[1].axvline(theta_c, color="grey", ls=":", lw=1)
    axes[1].set_xlabel("θ in LYSO [deg]")
    axes[1].set_ylabel("transmitted fraction, unpolarised")
    axes[1].set_ylim(0, 1)
    axes[1].legend(fontsize=8)
    axes[1].set_title(f"single-pass transmission vs angle (M={cfg.order})", fontsize=9)
    fig.suptitle(f"{cfg.label}   (commit {git_commit()})", fontsize=8)
    fig.tight_layout()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES_DIR / f"m2_lut_{cfg.label}.png", dpi=130)

    out = save_results(
        f"m2_lut_{cfg.label}",
        {
            "config": cfg.to_json(),
            "lut_file": path.name,
            "max_energy_error": lut.meta.get("max_energy_error"),
            "wall_seconds_this_run": wall,
            "theta_c_deg": theta_c,
            "eta_single_pass_phc": phc["eta_single_pass"],
            "phc_in_cone_cells": phc["in_cone_part"],
            "phc_trapped_cells": phc["trapped_part"],
            "eta_single_pass_bare_same_grid": bare_grid,
            "eta_single_pass_bare_exact": bare_exact,
            "note": "cells are classified by their centre; the cell containing theta_c "
            "counts as in-cone",
        },
    )
    print(f"saved {out}")


if __name__ == "__main__":
    main()
