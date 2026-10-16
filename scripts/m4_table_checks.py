"""Checks of the M4 fine lookup tables (light: seconds, reads downloaded tables).

For each table: the single-pass extraction (derivation 03, eq. 9) and the early-photon
yield E(100 ps) from eq. (1) of derivation 05, on the full grid (theta 1 deg x phi 5 deg)
and on grids subsampled 3x in theta or in phi. The change on subsampling is taken as a
bound on the angle-grid error of the full grid (decision of 2026-10-16), without the
Richardson factor: the integrands have square-root edges (critical angle, Rayleigh
anomalies) whose position relative to the grid makes the error irregular. The same
bound is applied to the flat face, whose exact value is known, to test it.
With --mc, the Monte Carlo E(100 ps) of each table is compared with eq. (1).

Run: python scripts/m4_table_checks.py --lut <label>:<lut-run-id> ... [--mc <mc-run-id> ...]
Tables and Monte Carlo results are downloaded with gh into results/<job>/<run-id>/.
Writes results/m4_table_checks.json.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import math
import subprocess
from pathlib import Path

import numpy as np

from phcscint.fresnel import unpolarised_transmittance
from phcscint.lut import LUT
from phcscint.optimize import early_weight
from phcscint.provenance import REPO_ROOT, git_commit, save_results

TAU_PS = 100.0
LZ_UM = 20000.0


def fetch(job: str, run: str, artifact: str) -> Path:
    dest = REPO_ROOT / "results" / job / run
    if not (dest / "summary.json").exists():
        subprocess.run(["gh", "run", "download", run, "-n", artifact, "-D", str(dest)], check=True)
    return dest


def subsample(lut: LUT, ti: slice, pi: slice) -> LUT:
    cfg = dataclasses.replace(
        lut.config,
        theta_deg=tuple(np.array(lut.config.theta_deg)[ti]),
        phi_deg=tuple(np.array(lut.config.phi_deg)[pi]),
    )
    return LUT(config=cfg, orders=lut.orders, T=lut.T[ti][:, pi], R=lut.R[ti][:, pi])


def quantities(lut: LUT, weight, theta_c_deg: float) -> dict[str, float]:
    """Single pass and E(100 ps), with the parts from inside the flat-face escape cone."""
    sp = lut.single_pass_extraction(theta_split_deg=theta_c_deg)

    def in_cone(theta: float) -> float:
        return weight(theta) if math.degrees(theta) < theta_c_deg else 0.0

    return {
        "eta1": sp["eta_single_pass"],
        "eta1_in_cone": sp["in_cone_part"],
        "E100": lut.weighted_single_pass(weight),
        "E100_in_cone": lut.weighted_single_pass(in_cone),
    }


def bare(n1: float, n2: float, weight, theta: np.ndarray) -> dict[str, float]:
    """Flat face on a midpoint theta grid (phi-independent)."""
    t = unpolarised_transmittance(n1, n2, theta)
    w = np.array([weight(float(x)) for x in theta])
    dth = theta[1] - theta[0]
    return {
        "eta1": float(np.sum(t * np.sin(theta)) * dth / 2),
        "E100": float(np.sum(t * w * np.sin(theta)) * dth / 2),
    }


def bound(full: dict, coarse_theta: dict, coarse_phi: dict) -> dict[str, float]:
    return {k: abs(full[k] - coarse_theta[k]) + abs(full[k] - coarse_phi[k]) for k in full}


def check_table(label: str, run: str) -> dict:
    d = fetch("lut", run, "lut-result")
    s = json.loads((d / "summary.json").read_text())
    lut = LUT.load(d / s["lut_file"])
    c = lut.config
    assert len(c.theta_deg) % 3 == 0 and (len(c.phi_deg) - 1) % 3 == 0, "grid not 3x-subsampled"
    weight = early_weight(TAU_PS, LZ_UM, c.n1)
    theta_c = math.degrees(math.asin(c.n2 / c.n1))
    sub_t = subsample(lut, slice(1, None, 3), slice(None))  # 3x coarser theta midpoints
    sub_p = subsample(lut, slice(None), slice(None, None, 3))  # 3x coarser phi, same ends
    q = {"full": quantities(lut, weight, theta_c), "theta_3x": quantities(sub_t, weight, theta_c),
         "phi_3x": quantities(sub_p, weight, theta_c)}  # fmt: skip
    q["grid_error_bound"] = bound(q["full"], q["theta_3x"], q["phi_3x"])
    # the same estimator on the flat face, whose exact value is known
    fine = (np.arange(400_000) + 0.5) * (math.pi / 2) / 400_000
    b_full, b_3 = bare(c.n1, c.n2, weight, lut.theta), bare(c.n1, c.n2, weight, sub_t.theta)
    b_exact = bare(c.n1, c.n2, weight, fine)
    flat = {
        "exact": b_exact,
        "grid": b_full,
        "true_error": {k: b_full[k] - b_exact[k] for k in b_exact},
        "bound": {k: abs(b_full[k] - b_3[k]) for k in b_exact},
    }
    tot = lut.T.sum(axis=-1) + lut.R.sum(axis=-1)
    return {
        "label": label,
        "lut_run": run,
        "lut_file": s["lut_file"],
        "built_at_commits": lut.meta.get("built_at_commits"),
        "n1": c.n1,
        "n2": c.n2,
        "layer": dataclasses.asdict(c.layer),
        "order": c.order,
        "theta_c_deg": theta_c,
        "max_energy_error": float(np.max(np.abs(tot - 1))),
        "phc": q,
        "flat": flat,
        "gain_vs_flat": {k: q["full"][k] / b_exact[k] for k in b_exact},
        "change_vs_flat_points": {
            "E100_in_cone": q["full"]["E100_in_cone"] - b_exact["E100"],
            "E100_trapped": q["full"]["E100"] - q["full"]["E100_in_cone"],
            "eta1_in_cone": q["full"]["eta1_in_cone"] - b_exact["eta1"],
            "eta1_trapped": q["full"]["eta1"] - q["full"]["eta1_in_cone"],
        },
    }


def compare_mc(run: str, tables: dict[str, dict]) -> list[dict]:
    s = json.loads((fetch("mc", run, "mc-result") / "summary.json").read_text())
    rows = []
    for case in s["cases"]:
        t = tables.get((case.get("lut") or {}).get("lut_label"))
        if t is None:
            continue
        mc = case["early_yield"]["100"]
        eq1 = t["phc"]["full"]["E100"]
        grid = t["phc"]["grid_error_bound"]["E100"]
        rows.append({"mc_run": run, "label": t["label"], "mc_E100": mc["value"],
                     "mc_sigma": mc["sigma"], "eq1_fine_grid": eq1, "grid_error_bound": grid,
                     "z_stat_only": (mc["value"] - eq1) / mc["sigma"]})  # fmt: skip
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lut", nargs="+", required=True, help="label:lut-run-id")
    ap.add_argument("--mc", nargs="*", default=[], help="mc-run-id")
    args = ap.parse_args()
    print(f"commit {git_commit()}")
    tables = {}
    for spec in args.lut:
        label, run = spec.split(":", 1)
        t = check_table(label, run)
        tables[label] = t
        f, e, fl = t["phc"]["full"], t["phc"]["grid_error_bound"], t["flat"]
        print(
            f"{label:38s} eta1 {100 * f['eta1']:.3f} +- {100 * e['eta1']:.3f} %  "
            f"E100 {100 * f['E100']:.3f} +- {100 * e['E100']:.3f} %  "
            f"(flat E100 exact {100 * fl['exact']['E100']:.3f} %, grid error "
            f"{100 * fl['true_error']['E100']:+.4f}, bound "
            f"{100 * fl['bound']['E100']:.4f})  energy {t['max_energy_error']:.1e}"
        )
    mc_rows = [r for run in args.mc for r in compare_mc(run, tables)]
    for r in mc_rows:
        print(
            f"MC {r['label']:38s} {100 * r['mc_E100']:.3f} +- {100 * r['mc_sigma']:.3f} % vs "
            f"eq. (1) {100 * r['eq1_fine_grid']:.3f} %: z = {r['z_stat_only']:+.2f}"
        )
    path = save_results("m4_table_checks", {
        "what": "M4 fine tables: single-pass and E(100 ps) with angle-grid error estimates; "
                "Monte Carlo E(100 ps) vs derivation 05 eq. (1)",
        "tau_ps": TAU_PS, "lz_um": LZ_UM,
        "tables": list(tables.values()), "mc_vs_eq1": mc_rows,
    })  # fmt: skip
    print(f"saved {path}")


if __name__ == "__main__":
    main()
