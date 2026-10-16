"""Checks of the M4 fine lookup tables (light: about a minute, reads downloaded tables).

For each table:
1. Node quadrature: the single-pass extraction (derivation 03, eq. 9) and the early-photon
   yield E(100 ps) from eq. (1) of derivation 05, on the table grid (theta 1 deg x phi
   5 deg) and on grids subsampled 3x in theta or in phi. The change on subsampling is
   taken as a bound on the angle-grid error (decision of 2026-10-16), without the
   Richardson factor: the integrands have square-root edges (critical angle, Rayleigh
   anomalies) whose position relative to the grid makes the error irregular. The same
   bound is applied to the flat face, whose exact value is known, to test it.
2. Lookup model: the same integrals over what the Monte Carlo actually samples (bilinear
   interpolation, masking of closed orders, renormalisation; lut.channel_powers_batch)
   on a fine deterministic grid, without and with the side-wall losses of eq. (1a)
   (air-gap mirror wraps of reflectivity rho). The difference to the node quadrature
   measures the error of the lookup model itself.
With --mc, each Monte Carlo early yield E(100 ps) is compared with the lookup model that
matches its walls: eq. (1) for lossless mirror walls, eq. (1a) for wrapped_specular walls.

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
from phcscint.timing import C_UM_PER_PS

TAU_PS = 100.0
PIXEL_UM = (3000.0, 3000.0, 20000.0)  # lx, ly, lz of the M4 Monte Carlo pixel
RHO_NOMINAL = 0.95  # wrap reflectivity of the nominal wall model (assumed, decisions.md)
N_THETA, N_PHI, N_PATH = 450, 90, 200  # lookup-model grid over the wedge, path points


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


def side_survival(n1: float, d: np.ndarray, path: np.ndarray, rho: float) -> np.ndarray:
    """Eq. (1a) of derivation 05: survival after path length `path` for direction d,
    averaged over the start position, with air-gap mirror wraps on the four sides."""
    out = np.ones((d.shape[0], path.size))
    for axis, width in ((0, PIXEL_UM[0]), (1, PIXEL_UM[1])):
        c = np.abs(d[:, axis])
        r = 1.0 - unpolarised_transmittance(n1, 1.0, np.arccos(np.clip(c, 0.0, 1.0)))
        p = np.where(r >= 1.0, 1.0, r + (1 - r) ** 2 * rho / (1 - rho * r))[:, None]
        dist = path[None, :] * c[:, None] / width
        k = np.floor(dist)
        out *= p**k * (1 - (dist - k) + (dist - k) * p)
    return out


def lookup_model(lut: LUT, rho: float | None) -> dict[str, float]:
    """Eq. (1) and the single pass over the Monte Carlo's lookup model, on a midpoint
    grid of N_THETA x N_PHI directions in the C4v wedge; with rho also eq. (1a)."""
    n1 = lut.config.n1
    s_tau = C_UM_PER_PS * TAU_PS / n1
    lz = PIXEL_UM[2]
    th = (np.arange(N_THETA) + 0.5) * (math.pi / 2) / N_THETA
    ph = (np.arange(N_PHI) + 0.5) * (math.pi / 4) / N_PHI
    jac = 8 * (th[1] - th[0]) * (ph[1] - ph[0]) / (4 * math.pi)
    path = (np.arange(N_PATH) + 0.5) * s_tau / N_PATH
    out = {"E100": 0.0, "eta1": 0.0, "E100_side_loss": 0.0}
    for t in th:
        d = np.stack(
            [np.sin(t) * np.cos(ph), np.sin(t) * np.sin(ph), np.full(N_PHI, np.cos(t))], 1
        )
        _, tr, _, _ = lut.channel_powers_batch(d)
        tr = tr.sum(axis=1) * math.sin(t) * jac
        out["eta1"] += float(tr.sum())
        out["E100"] += float(tr.sum()) * s_tau * math.cos(t) / lz
        if rho is not None:
            surv = side_survival(n1, d, path, rho).mean(axis=1) * s_tau
            out["E100_side_loss"] += float(np.sum(tr * surv)) * math.cos(t) / lz
    if rho is None:
        out.pop("E100_side_loss")
    return out


def check_table(label: str, run: str) -> tuple[dict, LUT]:
    d = fetch("lut", run, "lut-result")
    s = json.loads((d / "summary.json").read_text())
    lut = LUT.load(d / s["lut_file"])
    c = lut.config
    assert len(c.theta_deg) % 3 == 0 and (len(c.phi_deg) - 1) % 3 == 0, "grid not 3x-subsampled"
    weight = early_weight(TAU_PS, PIXEL_UM[2], c.n1)
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
    model = lookup_model(lut, RHO_NOMINAL)
    table = {
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
        "lookup_model": model | {"rho_side_loss": RHO_NOMINAL},
        "lookup_model_minus_nodes": {k: model[k] - q["full"][k] for k in ("E100", "eta1")},
    }
    return table, lut


def compare_mc(run: str, tables: dict[str, dict], luts: dict[str, LUT]) -> list[dict]:
    s = json.loads((fetch("mc", run, "mc-result") / "summary.json").read_text())
    px = s["config"]["pixel"]
    assert (px["lx_um"], px["ly_um"], px["lz_um"]) == PIXEL_UM, "pixel differs from PIXEL_UM"
    rows = []
    for case in s["cases"]:
        label = (case.get("lut") or {}).get("lut_label")
        if label not in tables or "100" not in case["early_yield"]:
            continue
        walls = case["walls"]
        kind, rho = walls["kind"], float(walls.get("reflectivity", 1.0))
        if kind == "specular" and rho == 1.0:
            model, which = tables[label]["lookup_model"]["E100"], "eq. (1)"
        elif kind == "wrapped_specular":
            m = tables[label]["lookup_model"]
            if rho != m["rho_side_loss"]:
                m = lookup_model(luts[label], rho)
            model, which = m["E100_side_loss"], f"eq. (1a), rho {rho:g}"
        else:
            continue
        mc = case["early_yield"]["100"]
        rows.append({"mc_run": run, "case": case["name"], "label": label, "walls": walls,
                     "mc_E100": mc["value"], "mc_sigma": mc["sigma"], "model": which,
                     "model_E100": model, "z": (mc["value"] - model) / mc["sigma"]})  # fmt: skip
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lut", nargs="+", required=True, help="label:lut-run-id")
    ap.add_argument("--mc", nargs="*", default=[], help="mc-run-id")
    args = ap.parse_args()
    print(f"commit {git_commit()}")
    tables, luts = {}, {}
    for spec in args.lut:
        label, run = spec.split(":", 1)
        tables[label], luts[label] = check_table(label, run)
        t = tables[label]
        f, e, fl, m = t["phc"]["full"], t["phc"]["grid_error_bound"], t["flat"], t["lookup_model"]
        print(
            f"{label:36s} nodes: eta1 {100 * f['eta1']:.3f} +- {100 * e['eta1']:.3f}, E100 "
            f"{100 * f['E100']:.3f} +- {100 * e['E100']:.3f} | lookup model: eta1 "
            f"{100 * m['eta1']:.3f}, E100 {100 * m['E100']:.3f}, with side loss "
            f"{100 * m['E100_side_loss']:.3f} | flat E100 {100 * fl['exact']['E100']:.3f} "
            f"(grid error {100 * fl['true_error']['E100']:+.4f}, bound "
            f"{100 * fl['bound']['E100']:.4f}) | energy {t['max_energy_error']:.1e}"
        )
    mc_rows = [r for run in args.mc for r in compare_mc(run, tables, luts)]
    for r in mc_rows:
        print(
            f"MC {r['mc_run']} {r['case']:40s} {100 * r['mc_E100']:.3f} +- "
            f"{100 * r['mc_sigma']:.3f} vs {r['model']} {100 * r['model_E100']:.3f}: "
            f"z = {r['z']:+.2f}"
        )
    path = save_results("m4_table_checks", {
        "what": "M4 fine tables: single pass and E(100 ps) by node quadrature (with angle-grid "
                "bounds) and over the Monte Carlo lookup model (with and without side-wall "
                "losses, derivation 05 eq. 1a); Monte Carlo E(100 ps) against the matching model",
        "tau_ps": TAU_PS, "pixel_um": PIXEL_UM,
        "lookup_model_grid": {"n_theta": N_THETA, "n_phi": N_PHI, "n_path": N_PATH},
        "tables": list(tables.values()), "mc_vs_model": mc_rows,
    })  # fmt: skip
    print(f"saved {path}")


if __name__ == "__main__":
    main()
