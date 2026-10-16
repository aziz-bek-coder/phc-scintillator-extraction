"""Key figure for the technical note (light: plotting only).

Reads the merged Monte Carlo results of the M4 comparison runs (downloaded with gh into
results/mc/<run-id>/ if missing) and draws, per outside medium:
  left:  detected photons per emitted photon vs transport time, early part;
  right: early yield E(100 ps) and the fraction detected by 5 ns, with 1-sigma bars.
Writes docs/figures/key_figure.png and results/key_figure.json (the plotted numbers).
Run: python scripts/key_figure.py --run grease:<mc-run-id> --run air:<mc-run-id>
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from phcscint.provenance import FIGURES_DIR, REPO_ROOT, git_commit, save_results  # noqa: E402


def fetch(run: str):
    dest = REPO_ROOT / "results" / "mc" / run
    if not (dest / "summary.json").exists():
        subprocess.run(
            ["gh", "run", "download", run, "-n", "mc-result", "-D", str(dest)], check=True
        )
    summary = json.loads((dest / "summary.json").read_text())
    with (dest / "mc_cdf.csv").open(encoding="utf-8") as f:
        rows = list(csv.reader(f))
    names = rows[0][1:]
    data = np.array([[float(x) for x in r] for r in rows[1:]])
    return summary, data[:, 0], {n: data[:, i + 1] for i, n in enumerate(names)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", nargs="+", required=True, help="medium:mc-run-id")
    args = ap.parse_args()
    panels = [r.split(":", 1) for r in args.run]
    fig, axes = plt.subplots(len(panels), 2, figsize=(11, 3.6 * len(panels)), squeeze=False)
    plotted = {}
    for row, (medium, run) in enumerate(panels):
        summary, t, curves = fetch(run)
        t_dir = summary["pixel"]["direct_transit_ps"]
        ax = axes[row, 0]
        for name, y in curves.items():
            ax.plot(t, 100 * y, lw=1.6, label=name)
        ax.axvline(t_dir, color="grey", ls=":", lw=1)
        ax.set_xlim(0, 3 * t_dir)
        ax.set_xlabel("transport time [ps]")
        ax.set_ylabel("detected / emitted [%]")
        ax.set_title(f"LYSO → {medium}: early arrivals (dotted: direct transit)", fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=7)
        ax = axes[row, 1]
        cases = summary["cases"]
        x = np.arange(len(cases))
        e100 = [100 * c["early_yield"]["100"]["value"] for c in cases]
        e100s = [100 * c["early_yield"]["100"]["sigma"] for c in cases]
        tot = [100 * c["efficiency_at_t_max"] for c in cases]
        tots = [100 * c["efficiency_sigma"] for c in cases]
        ax.bar(x - 0.2, e100, 0.4, yerr=e100s, capsize=3, label="detected by 100 ps")
        ax.bar(x + 0.2, tot, 0.4, yerr=tots, capsize=3, label="detected by 5 ns")
        ax.set_xticks(x, [c["name"] for c in cases], rotation=15, fontsize=7)
        ax.set_ylabel("detected / emitted [%]")
        ax.set_title(f"LYSO → {medium}: early vs total light", fontsize=9)
        ax.grid(True, axis="y", alpha=0.3)
        ax.legend(fontsize=7)
        plotted[medium] = {
            "mc_run": run,
            "mc_merged_at_commit": summary["merged_at_commit"],
            "cases": [
                {
                    "name": c["name"],
                    "E100": c["early_yield"]["100"],
                    "E50": c["early_yield"]["50"],
                    "E200": c["early_yield"]["200"],
                    "detected_by_t_max": c["efficiency_at_t_max"],
                    "sigma": c["efficiency_sigma"],
                    "lut": c.get("lut"),
                }
                for c in cases
            ],
        }
    fig.suptitle(f"Photonic-crystal readout layer: early vs total light (commit {git_commit()})",
                 fontsize=9)  # fmt: skip
    fig.tight_layout()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    out = FIGURES_DIR / "key_figure.png"
    fig.savefig(out, dpi=150)
    print(f"saved {out}")
    print(save_results("key_figure", {"panels": plotted}))


if __name__ == "__main__":
    main()
