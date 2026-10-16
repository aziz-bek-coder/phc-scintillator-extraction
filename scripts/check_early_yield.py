"""Check derivation 05, eq. (1): the early-photon yield E(tau < t_dir) equals the
cos-weighted single-pass transmission, against the M3 Monte Carlo (light: seconds).

Inputs (downloaded with gh into results/<job>/<run-id>/ if missing):
  lut run 38901905525 (grease), 38901911122 (air): coarse order-7 lookup tables
  mc run 38903357645: bare face vs reference photonic crystal, 1e6 photons per case
Writes results/m4_early_yield_check.json.
Run: python scripts/check_early_yield.py
"""

from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

import numpy as np

from phcscint.fresnel import unpolarised_transmittance
from phcscint.lut import LUT
from phcscint.materials import LYSO, N_AIR, N_GREASE
from phcscint.optimize import early_weight
from phcscint.provenance import REPO_ROOT, git_commit, save_results

LZ_UM = 20000.0
CASES = [
    ("grease", N_GREASE, "38901905525", "ref_lyso_grease_coarse_M7_c1b20c8410b4.npz",
     "bare readout, grease", "reference PhC, grease"),
    ("air", N_AIR, "38901911122", "ref_lyso_air_coarse_M7_4db1fc0f59a7.npz",
     "bare readout, air", "reference PhC, air"),
]  # fmt: skip
MC_RUN = "38903357645"


def fetch(job: str, run: str, artifact: str) -> Path:
    dest = REPO_ROOT / "results" / job / run
    if not dest.exists() or not any(dest.rglob("*")):
        subprocess.run(["gh", "run", "download", run, "-n", artifact, "-D", str(dest)], check=True)
    return dest


def bare_exact(n2: float, weight) -> float:
    """Eq. (1) for the flat face by a fine midpoint rule; for tau < t_dir the weight is
    (s_tau / Lz) cos(theta), and weight(0) = s_tau / Lz."""
    th = (np.arange(200_000) + 0.5) * (math.pi / 2) / 200_000
    s = weight(0.0)
    return float(
        np.sum(unpolarised_transmittance(LYSO.n, n2, th) * s * np.cos(th) * np.sin(th))
        * (math.pi / 2 / 200_000)
        / 2
    )


def bare_on_grid(n2: float, weight, theta: np.ndarray) -> float:
    w = np.array([weight(float(t)) for t in theta])
    tf = unpolarised_transmittance(LYSO.n, n2, theta)
    return float(np.sum(tf * w * np.sin(theta)) * (theta[1] - theta[0]) / 2)


def main() -> None:
    print(f"commit {git_commit()}")
    mc_dir = fetch("mc", MC_RUN, "mc-result")
    mc = {c["name"]: c for c in json.loads((mc_dir / "summary.json").read_text())["cases"]}
    rows = []
    for tau in (50.0, 100.0):
        weight = early_weight(tau, LZ_UM, LYSO.n)
        assert weight(0.0) < 1.0, "tau must be below the direct transit time"
        for med, n2, run, fname, bare_name, phc_name in CASES:
            lut = LUT.load(fetch("lut", run, "lut-result") / fname)
            exact = bare_exact(n2, weight)
            grid = bare_on_grid(n2, weight, lut.theta)
            phc_grid = lut.weighted_single_pass(weight)
            key = f"{tau:g}"
            row = {
                "tau_ps": tau,
                "medium": med,
                "bare_eq1_exact": exact,
                "bare_eq1_coarse_grid": grid,
                "grid_error_estimate": grid - exact,
                "phc_eq1_coarse_grid": phc_grid,
                "phc_eq1_grid_corrected": phc_grid - (grid - exact),
                "bare_mc": mc[bare_name]["early_yield"][key]["value"],
                "bare_mc_sigma": mc[bare_name]["early_yield"][key]["sigma"],
                "phc_mc": mc[phc_name]["early_yield"][key]["value"],
                "phc_mc_sigma": mc[phc_name]["early_yield"][key]["sigma"],
                "upper_bound_T1": weight(0.0) / 4,
                "in_cone_bound": weight(0.0) * (n2 / LYSO.n) ** 2 / 4,
            }
            row["bare_z"] = (row["bare_mc"] - exact) / row["bare_mc_sigma"]
            row["phc_z_corrected"] = (row["phc_mc"] - row["phc_eq1_grid_corrected"]) / row[
                "phc_mc_sigma"
            ]
            rows.append(row)
            pct = {k: 100 * v for k, v in row.items() if isinstance(v, float)}
            print(
                f"tau={tau:4.0f} {med:6s} bare: eq1 {pct['bare_eq1_exact']:.3f}% "
                f"MC {pct['bare_mc']:.3f}+-{pct['bare_mc_sigma']:.3f} z={row['bare_z']:+.1f} | "
                f"PhC: eq1 {pct['phc_eq1_grid_corrected']:.3f}% (grid-corrected) "
                f"MC {pct['phc_mc']:.3f}+-{pct['phc_mc_sigma']:.3f} "
                f"z={row['phc_z_corrected']:+.1f}"
            )
    path = save_results(
        "m4_early_yield_check",
        {
            "what": "derivation 05 eq. (1) vs Monte Carlo early yields (tau < t_dir)",
            "inputs": {"lut_runs": [c[2] for c in CASES], "mc_run": MC_RUN},
            "note": "phc_eq1_grid_corrected subtracts the bare-face grid error on the same "
            "coarse theta grid; it is an estimate of the fine-grid value",
            "rows": rows,
        },
    )
    print(f"saved {path}")


if __name__ == "__main__":
    main()
