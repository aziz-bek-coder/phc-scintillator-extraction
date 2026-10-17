"""Robustness check 1 (M5): the early-photon gain at the 50, 100 and 200 ps thresholds.

For every readout of the M4 Monte Carlo comparisons:
- the gain over the bare face in photons detected by tau, F(tau) / F_bare(tau) - 1, with
  its 1-sigma error (binomial, independent samples);
- the same quantity from the first-pass model, derivation 05, eq. (1b), with the
  nominal wraps (air gap + mirror, rho 0.95, on the four sides and the back face),
  integrated over each lookup table exactly as the Monte Carlo samples it;
- z = (Monte Carlo - model) / sigma for each yield.
All three thresholds lie below twice the direct transit time (241.6 ps), where only
first readout hits count, so eq. (1b) applies to each. Light: about a minute.

Inputs: Monte Carlo summaries results/mc-<run>.json (committed), and the lookup tables
in results/lut/<run>/ (downloaded with gh from the archive repository if missing).
Run: python scripts/m5_threshold_check.py
Writes results/m5_threshold_check.json.
"""

from __future__ import annotations

import json
import math
import subprocess
from collections.abc import Callable

import numpy as np

from phcscint.firstpass import first_pass_yield
from phcscint.fresnel import unpolarised_transmittance
from phcscint.jobs import resolve_index, resolve_wavelength
from phcscint.lut import LUT
from phcscint.provenance import REPO_ROOT, git_commit, save_results

MC_RUNS = {"grease": "38936853588", "air": "38953882816"}
ARCHIVE = "aziz-bek-coder/phc-scintillator-extraction-archive"
TAUS = ("50", "100", "200")
BARE = "bare readout"
NOMINAL_WALLS = {"kind": "wrapped_specular", "reflectivity": 0.95}


def load_table(info: dict) -> LUT:
    run = str(info["run_id"])
    dest = REPO_ROOT / "results" / "lut" / run
    path = dest / info["lut_file"]
    if not path.exists():
        cmd = ["gh", "run", "download", run, "-R", ARCHIVE, "-n", "lut-result", "-D", str(dest)]
        subprocess.run(cmd, check=True)
    return LUT.load(path)


def readout(case: dict, n1: float) -> Callable[[np.ndarray], np.ndarray]:
    """First-pass transmission T(d) of the case's readout: lookup table or flat face."""
    if case.get("lut"):
        lut = load_table(case["lut"])
        return lambda d: lut.channel_powers_batch(d)[1].sum(axis=1)
    n2 = resolve_index(case["readout"]["n_out"], resolve_wavelength("LYSO-peak"))
    return lambda d: unpolarised_transmittance(n1, n2, np.arccos(np.clip(d[:, 2], 0.0, 1.0)))


def gain(f: float, n: float, fb: float, nb: float) -> tuple[float, float]:
    """F / F_bare - 1 and its 1-sigma error for independent binomial samples."""
    r = f / fb
    rel = math.hypot(math.sqrt(f * (1 - f) / n) / f, math.sqrt(fb * (1 - fb) / nb) / fb)
    return r - 1, r * rel


def check_medium(run: str) -> dict:
    s = json.loads((REPO_ROOT / "results" / f"mc-{run}.json").read_text())
    px = s["pixel"]
    lx, ly, lz = px["size_um"]
    cases = {c["name"]: c for c in s["cases"]}
    model = {}
    for name, c in cases.items():
        assert c["walls"] == NOMINAL_WALLS, f"{name}: model assumes the nominal walls"
        t = readout(c, px["n1"])
        model[name] = {
            tau: first_pass_yield(
                t,
                px["n1"],
                float(tau),
                lx_um=lx,
                ly_um=ly,
                lz_um=lz,
                rho=0.95,
                n_group=px["n_group"],
            )  # fmt: skip
            for tau in TAUS
        }
    bare = cases[BARE]
    rows = []
    for name, c in cases.items():
        for tau in TAUS:
            e = c["early_yield"][tau]
            m = model[name][tau]
            row = {"case": name, "tau_ps": int(tau), "mc": e["value"], "sigma": e["sigma"]}
            row |= {"model": m, "z": (e["value"] - m) / e["sigma"]}
            if name != BARE:
                eb = bare["early_yield"][tau]["value"]
                g, sg = gain(e["value"], c["n_emitted"], eb, bare["n_emitted"])
                row |= {"gain_mc": g, "sigma_gain": sg, "gain_model": m / model[BARE][tau] - 1}
            rows.append(row)
    return {"mc_run": run, "mc_merged_at_commit": s["merged_at_commit"], "rows": rows}


def main() -> None:
    print(f"commit {git_commit()}")
    media = {medium: check_medium(run) for medium, run in MC_RUNS.items()}
    for medium, res in media.items():
        for r in res["rows"]:
            line = (
                f"{medium:6s} {r['case']:26s} {r['tau_ps']:3d} ps: MC {100 * r['mc']:.3f} "
                f"+- {100 * r['sigma']:.3f} %, model {100 * r['model']:.3f} % (z {r['z']:+.2f})"
            )
            if "gain_mc" in r:
                line += (
                    f" | gain MC {100 * r['gain_mc']:+.2f} +- {100 * r['sigma_gain']:.2f} %, "
                    f"model {100 * r['gain_model']:+.2f} %"
                )
            print(line)
    what = (
        "early-photon gain over the bare face at 50, 100 and 200 ps: Monte Carlo vs the "
        "first-pass model, derivation 05 eq. (1b), nominal wraps rho 0.95"
    )
    print(f"saved {save_results('m5_threshold_check', {'what': what, 'media': media})}")


if __name__ == "__main__":
    main()
