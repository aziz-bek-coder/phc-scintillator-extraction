"""Time one patterned RCWA solve against Fourier order on this CPU (AGENTS.md,
compute constraints). The geometry is a placeholder square lattice of TiO2-like
pillars (n = 2.5, period 0.45 um, radius 0.15 um, height 0.30 um) on LYSO into air at
theta = 40 deg, phi = 20 deg. It is NOT the reference design; it only sizes the grids.

Produces results/m1_rcwa_benchmark.json and docs/figures/m1_rcwa_benchmark.png.
Run: python scripts/benchmark_rcwa.py [--orders 3 5 7 9 11] [--dtypes c128]
"""

from __future__ import annotations

import argparse
import math
import os
import time

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import torch  # noqa: E402
import torcwa  # noqa: E402

from phcscint.materials import LYSO, N_AIR  # noqa: E402
from phcscint.provenance import FIGURES_DIR, git_commit, save_results  # noqa: E402

DTYPES = {"c64": torch.complex64, "c128": torch.complex128}


def _rss_gb() -> float:
    try:
        import psutil  # type: ignore

        return psutil.Process(os.getpid()).memory_info().rss / 1e9
    except ImportError:
        return float("nan")


def one_solve(order: int, dtype: torch.dtype, *, n_grid: int = 256) -> tuple[float, float]:
    period, radius, height, n_pillar = 0.45, 0.15, 0.30, 2.5
    sim = torcwa.rcwa(
        freq=1.0 / LYSO.wavelength_um,
        order=[order, order],
        L=[period, period],
        dtype=dtype,
        device=torch.device("cpu"),
    )
    sim.add_input_layer(eps=LYSO.n**2)
    sim.add_output_layer(eps=N_AIR**2)
    sim.set_incident_angle(inc_ang=math.radians(40.0), azi_ang=math.radians(20.0))
    x = torch.linspace(-period / 2, period / 2, n_grid, dtype=torch.float64)
    X, Y = torch.meshgrid(x, x, indexing="ij")
    pillar = (X**2 + Y**2) < radius**2
    eps = torch.where(
        pillar, torch.tensor(n_pillar**2, dtype=dtype), torch.tensor(N_AIR**2, dtype=dtype)
    )
    t0 = time.perf_counter()
    sim.add_layer(thickness=height, eps=eps)
    sim.solve_global_smatrix()
    t_total = 0.0
    for i in range(-order, order + 1):
        for j in range(-order, order + 1):
            s = sim.S_parameters(
                orders=[i, j], direction="forward", port="transmission", polarization="ss"
            )
            t_total += abs(complex(s.reshape(-1)[0].item())) ** 2
    return time.perf_counter() - t0, t_total


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--orders", type=int, nargs="+", default=[3, 5, 7, 9, 11])
    ap.add_argument("--dtypes", nargs="+", default=["c128"], choices=list(DTYPES))
    args = ap.parse_args()
    print(f"commit {git_commit()}  torch threads={torch.get_num_threads()}")
    rows = []
    for key in args.dtypes:
        for order in args.orders:
            dt, t_tot = one_solve(order, DTYPES[key])
            rows.append(
                {
                    "dtype": key,
                    "order": order,
                    "n_harmonics": (2 * order + 1) ** 2,
                    "seconds": dt,
                    "T_ss_total_order00_in": t_tot,
                    "rss_gb_after": _rss_gb(),
                }
            )
            print(
                f"{key:5s} order={order:2d} N={(2 * order + 1) ** 2:4d} t={dt:7.2f}s "
                f"T_ss(all orders)={t_tot:.5f} rss={_rss_gb():.2f} GB"
            )
    fig, ax = plt.subplots(figsize=(4.5, 3.4))
    for key in args.dtypes:
        sub = [r for r in rows if r["dtype"] == key]
        ax.plot([r["n_harmonics"] for r in sub], [r["seconds"] for r in sub], "o-", label=key)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Fourier harmonics (2M+1)^2")
    ax.set_ylabel("seconds per solve (CPU)")
    ax.set_title(
        f"torcwa solve time, placeholder pillar lattice (commit {git_commit()})", fontsize=8
    )
    ax.legend()
    ax.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES_DIR / "m1_rcwa_benchmark.png", dpi=130)
    path = save_results(
        "m1_rcwa_benchmark",
        {
            "geometry": "square lattice, n_pillar=2.5, period 0.45 um, r 0.15 um, h 0.30 um, "
            "LYSO->air, theta 40 deg, phi 20 deg, 256x256 eps grid",
            "torch_threads": torch.get_num_threads(),
            "rows": rows,
        },
    )
    print(f"saved {path}")


if __name__ == "__main__":
    main()
