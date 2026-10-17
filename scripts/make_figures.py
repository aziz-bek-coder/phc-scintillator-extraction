"""Regenerate every figure in docs/figures with one command (light: about a minute).

  python scripts/make_figures.py [--tag <release-tag>] [--laptop-benchmark]

1. Makes sure the merged outputs of every quoted remote run are in results/<job>/<run>/,
   fetching the release asset with scripts/data_bundle.py if any run is missing.
2. Copies the figures drawn by the remote jobs themselves to docs/figures/ under their
   documented names.
3. Runs the light figure scripts: M1 Fresnel vs RCWA, the M4 angular transmission and
   the key figure. These stamp the current commit into the figure.
The laptop-era RCWA benchmark (m1_rcwa_benchmark.png) is rerun only with
--laptop-benchmark: it times the machine it runs on and is superseded by the remote
benchmark.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RELEASE_TAG = "results-2026-10-17"

# docs/figures/<name> <- results/<job>/<run>/<file>, drawn by the remote job's merge step
REMOTE_FIGURES = {
    "benchmark_rcwa_remote.png": ("benchmark", 38798175139, "benchmark.png"),
    "m2_convergence.png": ("convergence", 38901900762, "convergence.png"),
    "m2_lut_ref_lyso_grease_coarse_M7.png": ("lut", 38901905525, "ref_lyso_grease_coarse_M7.png"),
    "m2_lut_ref_lyso_air_coarse_M7.png": ("lut", 38901911122, "ref_lyso_air_coarse_M7.png"),
    "m3_validation_cdf.png": ("mc", 38902476498, "mc_cdf.png"),
    "m3_wall_models_cdf.png": ("mc", 38902480681, "mc_cdf.png"),
    "m3_reference_cdf.png": ("mc", 38903357645, "mc_cdf.png"),
    "m4_opt_grease_early.png": ("optimize", 38905901930, "optimize.png"),
    "m4_opt_grease_single_pass.png": ("optimize", 38905905490, "optimize.png"),
    "m4_opt_air_early.png": ("optimize", 38950528275, "optimize.png"),
    "m4_ordercheck.png": ("ordercheck", 38949360857, "ordercheck.png"),
}

LIGHT_SCRIPTS = [
    ["scripts/fresnel_vs_rcwa.py"],
    [
        "scripts/plot_angular_transmission.py",
        "--lut",
        "grease:reference PhC:38931698470",
        "grease:optimised, early photons:38931708295",
        "grease:optimised, single pass:38931717766",
        "air:reference PhC:38931726855",
        "air:optimised, early photons:38949348290",
    ],
    ["scripts/key_figure.py", "--run", "grease:38936853588", "air:38953882816"],
]


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run([sys.executable, *cmd], cwd=REPO, check=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default=RELEASE_TAG, help="release holding the run outputs")
    ap.add_argument("--laptop-benchmark", action="store_true")
    args = ap.parse_args()
    run(["scripts/data_bundle.py", "fetch", "--tag", args.tag])
    figures = REPO / "docs" / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    for name, (job, run_id, file) in REMOTE_FIGURES.items():
        shutil.copyfile(REPO / "results" / job / str(run_id) / file, figures / name)
        print(f"copied {job} {run_id} -> docs/figures/{name}")
    for cmd in LIGHT_SCRIPTS:
        run(cmd)
    if args.laptop_benchmark:
        run(["scripts/benchmark_rcwa.py"])
    print("all figures regenerated; review `git status` and `git diff --stat docs/figures`")


if __name__ == "__main__":
    main()
