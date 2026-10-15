"""Flat interface: analytic Fresnel vs torcwa zero-order RCWA (derivation 02, 2g).

Produces results/m1_fresnel_vs_rcwa.json and docs/figures/m1_fresnel_vs_rcwa.png.
Run: python scripts/fresnel_vs_rcwa.py
"""

from __future__ import annotations

import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from phcscint import analytic  # noqa: E402
from phcscint.fresnel import brewster_angle, fresnel_power  # noqa: E402
from phcscint.materials import BGO, LYSO, N_AIR, N_GREASE  # noqa: E402
from phcscint.provenance import FIGURES_DIR, git_commit, save_results  # noqa: E402
from phcscint.rcwa import flat_interface_sweep  # noqa: E402

PAIRS = [
    ("LYSO -> air", LYSO.n, N_AIR, LYSO.wavelength_um),
    ("LYSO -> grease", LYSO.n, N_GREASE, LYSO.wavelength_um),
    ("BGO -> air", BGO.n, N_AIR, BGO.wavelength_um),
]
N_THETA = 181  # 0.5 deg steps


def main() -> None:
    print(f"commit {git_commit()}")
    thetas = np.radians(np.linspace(0.0, 89.5, N_THETA))
    summary = []
    fig, axes = plt.subplots(1, len(PAIRS), figsize=(4.2 * len(PAIRS), 3.6), sharey=True)
    for ax, (name, n1, n2, lam) in zip(axes, PAIRS, strict=True):
        Rs, Rp, Ts, Tp = fresnel_power(n1, n2, thetas)
        rc = flat_interface_sweep(n1, n2, lam, thetas, phi=math.radians(20.0))
        dev = {
            "R_s": float(np.max(np.abs(rc["R_s"] - Rs))),
            "R_p": float(np.max(np.abs(rc["R_p"] - Rp))),
            "T_s": float(np.max(np.abs(rc["T_s"] - Ts))),
            "T_p": float(np.max(np.abs(rc["T_p"] - Tp))),
            "cross_pol_max": float(max(np.max(rc[k]) for k in ("R_sp", "R_ps", "T_sp", "T_ps"))),
            "R_plus_T_minus_1_max": float(
                max(
                    np.max(np.abs(rc["R_s"] + rc["T_s"] - 1)),
                    np.max(np.abs(rc["R_p"] + rc["T_p"] - 1)),
                )
            ),
        }
        # geometric escape fraction from RCWA: indicator(T>0) integrated over hemisphere
        w = 0.5 * np.sin(thetas)
        unpol = 0.5 * (rc["T_s"] + rc["T_p"])
        eta_geom_rcwa = float(np.trapezoid((unpol > 0).astype(float) * w, thetas))
        eta_fresnel_rcwa = float(np.trapezoid(unpol * w, thetas))
        eta_1 = analytic.escape_fraction_one_face(n1, n2)
        row = {
            "case": name,
            "n1": n1,
            "n2": n2,
            "wavelength_um": lam,
            "R_normal_incidence": float(Rs[0]),
            "brewster_deg": math.degrees(brewster_angle(n1, n2)),
            "critical_deg": math.degrees(analytic.critical_angle(n1, n2)),
            "max_abs_dev_rcwa_vs_fresnel": dev,
            "eta_1_analytic": eta_1,
            "eta_1_geometric_from_rcwa_grid": eta_geom_rcwa,
            "eta_1_fresnel_weighted_from_rcwa_grid": eta_fresnel_rcwa,
            "n_theta": N_THETA,
        }
        summary.append(row)
        print(
            f"{name:16s} R(0)={Rs[0]:.4f} thetaB={row['brewster_deg']:.2f} "
            f"thetaC={row['critical_deg']:.2f}  max|dev|={max(dev.values()):.2e}  "
            f"eta1={100 * eta_1:.3f}%  eta1(grid,T>0)={100 * eta_geom_rcwa:.3f}%  "
            f"eta1^F(grid)={100 * eta_fresnel_rcwa:.3f}%"
        )
        deg = np.degrees(thetas)
        ax.plot(deg, Rs, "-", lw=2, label="R_s Fresnel")
        ax.plot(deg, Rp, "-", lw=2, label="R_p Fresnel")
        ax.plot(deg, Ts, "-", lw=2, label="T_s Fresnel")
        ax.plot(deg, Tp, "-", lw=2, label="T_p Fresnel")
        ax.plot(
            deg[::6],
            rc["R_s"][::6],
            "o",
            ms=3,
            mfc="none",
            color="k",
            label="torcwa (every 6th pt)",
        )
        ax.plot(deg[::6], rc["R_p"][::6], "o", ms=3, mfc="none", color="k")
        ax.plot(deg[::6], rc["T_s"][::6], "o", ms=3, mfc="none", color="k")
        ax.plot(deg[::6], rc["T_p"][::6], "o", ms=3, mfc="none", color="k")
        ax.axvline(row["critical_deg"], color="grey", ls=":", lw=1)
        ax.set_title(f"{name}  (n1={n1}, n2={n2})", fontsize=10)
        ax.set_xlabel("angle of incidence in scintillator [deg]")
        ax.set_xlim(0, 90)
    axes[0].set_ylabel("power coefficient")
    axes[0].legend(fontsize=7, loc="center left")
    fig.suptitle(
        f"Flat interface: analytic Fresnel vs torcwa order [0,0]   (commit {git_commit()})",
        fontsize=9,
    )
    fig.tight_layout()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    out = FIGURES_DIR / "m1_fresnel_vs_rcwa.png"
    fig.savefig(out, dpi=130)
    print(f"saved {out}")
    path = save_results("m1_fresnel_vs_rcwa", {"azimuth_deg": 20.0, "cases": summary})
    print(f"saved {path}")


if __name__ == "__main__":
    main()
