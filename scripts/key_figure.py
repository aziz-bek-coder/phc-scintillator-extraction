"""Key figure for the technical note (light: plotting only).

Reads the merged Monte Carlo results of the M4 comparison runs (downloaded with gh into
results/mc/<run-id>/ if missing) and draws, per outside medium:
  left:  photons detected by time t relative to the bare face, F(t) / F_bare(t) - 1,
         with 1-sigma bands (binomial, independent samples), for the first 600 ps;
         the vertical range is set by t < 2 t_dir, so later, larger gains leave the frame;
  right: gain in photons detected by 100 ps against gain in photons detected by 5 ns,
         one point per readout, with 1-sigma error bars.
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

BARE = "bare readout"


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


def ratio(f: np.ndarray, n: float, fb: np.ndarray, nb: float) -> tuple[np.ndarray, np.ndarray]:
    """F / F_bare - 1 and its 1-sigma error for independent binomial samples."""
    with np.errstate(divide="ignore", invalid="ignore"):
        r = f / fb
        rel = np.sqrt(f * (1 - f) / n) / f
        relb = np.sqrt(fb * (1 - fb) / nb) / fb
        return r - 1, r * np.hypot(rel, relb)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", nargs="+", required=True, help="medium:mc-run-id")
    args = ap.parse_args()
    panels = [r.split(":", 1) for r in args.run]
    fig, axes = plt.subplots(len(panels), 2, figsize=(11, 3.9 * len(panels)), squeeze=False)
    plotted = {}
    for row, (medium, run) in enumerate(panels):
        summary, t, curves = fetch(run)
        cases = {c["name"]: c for c in summary["cases"]}
        t_dir = summary["pixel"]["direct_transit_ps"]
        b = cases[BARE]
        ax = axes[row, 0]
        sel = (t >= 10) & (t <= 600)
        early = (t >= 10) & (t <= 2 * t_dir)
        lo, hi = -1.0, 1.0
        for name, y in curves.items():
            if name == BARE:
                continue
            g, s = ratio(y, cases[name]["n_emitted"], curves[BARE], b["n_emitted"])
            line = ax.plot(t[sel], 100 * g[sel], lw=1.6, label=name)[0]
            lo = min(lo, float(np.min(100 * (g - s)[early])))
            hi = max(hi, float(np.max(100 * (g + s)[early])))
            ax.fill_between(t[sel], 100 * (g - s)[sel], 100 * (g + s)[sel],
                            color=line.get_color(), alpha=0.25, lw=0)  # fmt: skip
        ax.axhline(0, color="k", lw=0.8)
        for k in (1, 2):
            ax.axvline(k * t_dir, color="grey", ls=":", lw=1)
        ax.set_xlim(0, 600)
        ax.set_ylim(lo - 1.5, hi + 2.5)
        ax.set_xlabel("transport time t [ps]  (dotted: one and two direct transits)")
        ax.set_ylabel("detected by t, relative to bare [%]")
        ax.set_title(f"LYSO → {medium}: photons detected by t, vs the bare face", fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=7, loc="upper left")
        ax = axes[row, 1]
        out = []
        for name, c in cases.items():
            if name == BARE:
                continue
            e, eb = c["early_yield"]["100"], b["early_yield"]["100"]
            ge, se = ratio(np.array(e["value"]), c["n_emitted"], np.array(eb["value"]),
                           b["n_emitted"])  # fmt: skip
            gt, st = ratio(np.array(c["efficiency_at_t_max"]), c["n_emitted"],
                           np.array(b["efficiency_at_t_max"]), b["n_emitted"])  # fmt: skip
            ax.errorbar(100 * gt, 100 * ge, xerr=100 * st, yerr=100 * se, fmt="o", ms=6,
                        capsize=3, label=name)  # fmt: skip
            ax.annotate(name, (100 * gt, 100 * ge), textcoords="offset points",
                        xytext=(6, 6), fontsize=7)  # fmt: skip
            out.append({"name": name, "lut": c.get("lut"),
                        "gain_E100": float(ge), "sigma_gain_E100": float(se),
                        "gain_5ns": float(gt), "sigma_gain_5ns": float(st),
                        "E100": e, "detected_by_5ns": c["efficiency_at_t_max"],
                        "sigma_5ns": c["efficiency_sigma"]})  # fmt: skip
        ax.axhline(0, color="k", lw=0.8)
        ax.axvline(0, color="k", lw=0.8)
        ax.set_xlabel("photons detected by 5 ns, relative to bare [%]")
        ax.set_ylabel("photons detected by 100 ps, relative to bare [%]")
        ax.set_title(f"LYSO → {medium}: early light vs total light", fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.margins(x=0.25, y=0.3)
        plotted[medium] = {
            "mc_run": run,
            "mc_merged_at_commit": summary["merged_at_commit"],
            "bare": {"E100": b["early_yield"]["100"], "detected_by_5ns":
                     b["efficiency_at_t_max"], "sigma_5ns": b["efficiency_sigma"]},
            "designs": out,
        }  # fmt: skip
    fig.suptitle(f"Photonic-crystal readout of a 3 × 3 × 20 mm LYSO pixel, Monte Carlo "
                 f"(commit {git_commit()})", fontsize=9)  # fmt: skip
    fig.tight_layout()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    out_png = FIGURES_DIR / "key_figure.png"
    fig.savefig(out_png, dpi=150)
    print(f"saved {out_png}")
    print(save_results("key_figure", {"panels": plotted}))


if __name__ == "__main__":
    main()
