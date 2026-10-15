"""Fourier-order and grid convergence for the reference photonic crystal (M2).

Reference design (derivation 03, 2l): Si3N4 pillars, square lattice, a = 0.40 um,
r = 0.12 um, h = 0.30 um, on LYSO at 420 nm, outside medium grease (1.5) and air.
For a set of incidences, computes total T and the largest single transmitted order vs
Fourier order M, plus a real-space grid check at fixed M.

Produces results/m2_convergence.json and docs/figures/m2_convergence.png.
Run: python scripts/convergence.py [--orders 3 5 7 9 11 13]
"""

from __future__ import annotations

import argparse
import math
import time

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from phcscint.materials import LYSO, N_AIR, N_GREASE, n_si3n4_luke  # noqa: E402
from phcscint.provenance import FIGURES_DIR, git_commit, save_results  # noqa: E402
from phcscint.rcwa import PhCLayer, solve_phc  # noqa: E402

REFERENCE = PhCLayer(
    period_um=0.40, radius_um=0.12, height_um=0.30, n_pillar=n_si3n4_luke(LYSO.wavelength_um)
)
INCIDENCES_DEG = [(20.0, 0.0), (45.0, 0.0), (60.0, 0.0), (60.0, 30.0), (75.0, 20.0)]
MEDIA = [("grease", N_GREASE), ("air", N_AIR)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--orders", type=int, nargs="+", default=[3, 5, 7, 9, 11, 13])
    ap.add_argument("--grid-order", type=int, default=9)
    ap.add_argument("--grids", type=int, nargs="+", default=[128, 256, 512])
    args = ap.parse_args()
    print(f"commit {git_commit()}  reference {REFERENCE}  ff={REFERENCE.fill_factor:.3f}")
    rows = []
    for mname, n2 in MEDIA:
        for th, ph in INCIDENCES_DEG:
            for m in args.orders:
                t0 = time.perf_counter()
                op = solve_phc(
                    LYSO.n,
                    n2,
                    LYSO.wavelength_um,
                    REFERENCE,
                    math.radians(th),
                    math.radians(ph),
                    order=m,
                    n_grid=256,
                )
                dt = time.perf_counter() - t0
                rows.append(
                    {
                        "medium": mname,
                        "theta_deg": th,
                        "phi_deg": ph,
                        "order": m,
                        "n_grid": 256,
                        "T_total": float(op.T.sum()),
                        "T_max_order": float(op.T.max()),
                        "energy_error": abs(op.total - 1),
                        "seconds": dt,
                    }
                )
                print(
                    f"{mname:6s} th={th:4.0f} ph={ph:4.0f} M={m:2d} T={op.T.sum():.5f} "
                    f"Tmax={op.T.max():.5f} |1-sum|={abs(op.total - 1):.1e} t={dt:6.1f}s",
                    flush=True,
                )
    grid_rows = []
    for mname, n2 in MEDIA:
        th, ph = 60.0, 30.0
        for ng in args.grids:
            op = solve_phc(
                LYSO.n,
                n2,
                LYSO.wavelength_um,
                REFERENCE,
                math.radians(th),
                math.radians(ph),
                order=args.grid_order,
                n_grid=ng,
            )
            grid_rows.append(
                {
                    "medium": mname,
                    "theta_deg": th,
                    "phi_deg": ph,
                    "order": args.grid_order,
                    "n_grid": ng,
                    "T_total": float(op.T.sum()),
                }
            )
            print(f"grid {mname:6s} M={args.grid_order} n_grid={ng:4d} T={op.T.sum():.5f}")

    # relative change of T_total against the highest order, per incidence
    m_top = max(args.orders)
    summary = []
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6), sharey=True)
    for ax, (mname, _) in zip(axes, MEDIA, strict=True):
        for th, ph in INCIDENCES_DEG:
            sub = [
                r
                for r in rows
                if r["medium"] == mname and r["theta_deg"] == th and r["phi_deg"] == ph
            ]
            ref = next(r["T_total"] for r in sub if r["order"] == m_top)
            ms = [r["order"] for r in sub]
            rel = [abs(r["T_total"] - ref) / max(ref, 1e-12) for r in sub]
            for r, e in zip(sub, rel, strict=True):
                summary.append(
                    {
                        **{k: r[k] for k in ("medium", "theta_deg", "phi_deg", "order")},
                        "rel_change_vs_top": e,
                    }
                )
            ax.semilogy(
                ms[:-1], np.maximum(rel[:-1], 1e-8), "o-", label=f"θ={th:.0f}°, φ={ph:.0f}°"
            )
        ax.axhline(0.01, color="grey", ls=":", lw=1)
        ax.set_title(f"LYSO → {mname}", fontsize=10)
        ax.set_xlabel("Fourier order M  (harmonics (2M+1)²)")
        ax.grid(True, which="both", alpha=0.3)
    axes[0].set_ylabel(f"|T(M) − T(M={m_top})| / T(M={m_top})")
    axes[0].legend(fontsize=7)
    fig.suptitle(
        f"Reference Si3N4 PhC (a=0.40, r=0.12, h=0.30 µm): convergence of total T "
        f"(commit {git_commit()})",
        fontsize=9,
    )
    fig.tight_layout()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES_DIR / "m2_convergence.png", dpi=130)
    path = save_results(
        "m2_convergence",
        {
            "reference_layer": {
                "period_um": REFERENCE.period_um,
                "radius_um": REFERENCE.radius_um,
                "height_um": REFERENCE.height_um,
                "n_pillar": REFERENCE.n_pillar,
                "fill_factor": REFERENCE.fill_factor,
            },
            "wavelength_um": LYSO.wavelength_um,
            "n1": LYSO.n,
            "rows": rows,
            "relative_change": summary,
            "grid_check": grid_rows,
        },
    )
    print(f"saved {path}")


if __name__ == "__main__":
    main()
