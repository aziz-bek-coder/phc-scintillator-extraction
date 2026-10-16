"""Where the light leaves the crystal: first-pass transmission vs polar angle for the M4
fine tables (light: plotting only, reads downloaded tables).

Per outside medium, two panels:
  left:  T(theta), averaged over phi, for the flat face (Fresnel) and every table;
  right: its contribution to E(100 ps), T(theta) w(theta) sin(theta) / 2 per radian
         (derivation 05, eq. 1), whose area is the early-photon yield.
Run: python scripts/plot_angular_transmission.py --lut <medium>:<label>:<lut-run-id> ...
Writes docs/figures/m4_angular_transmission.png.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from phcscint.fresnel import unpolarised_transmittance  # noqa: E402
from phcscint.lut import LUT  # noqa: E402
from phcscint.optimize import early_weight  # noqa: E402
from phcscint.provenance import FIGURES_DIR, REPO_ROOT, git_commit  # noqa: E402

TAU_PS, LZ_UM = 100.0, 20000.0


def load(run: str) -> LUT:
    dest = REPO_ROOT / "results" / "lut" / run
    if not (dest / "summary.json").exists():
        subprocess.run(
            ["gh", "run", "download", run, "-n", "lut-result", "-D", str(dest)], check=True
        )
    return LUT.load(dest / json.loads((dest / "summary.json").read_text())["lut_file"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lut", nargs="+", required=True, help="medium:label:lut-run-id")
    args = ap.parse_args()
    specs = [s.split(":", 2) for s in args.lut]
    media = list(dict.fromkeys(m for m, _, _ in specs))
    fig, axes = plt.subplots(len(media), 2, figsize=(11, 3.6 * len(media)), squeeze=False)
    for row, medium in enumerate(media):
        luts = [(label, load(run)) for m, label, run in specs if m == medium]
        n1, n2 = luts[0][1].config.n1, luts[0][1].config.n2
        weight = early_weight(TAU_PS, LZ_UM, n1)
        th = np.radians(np.linspace(0.05, 89.95, 1800))
        w = np.array([weight(float(t)) for t in th])
        flat = unpolarised_transmittance(n1, n2, th)
        ax_t, ax_e = axes[row]
        ax_t.plot(np.degrees(th), flat, "k--", lw=1.2, label="flat face")
        ax_e.plot(np.degrees(th), flat * w * np.sin(th) / 2, "k--", lw=1.2, label="flat face")
        for label, lut in luts:
            # phi average over the wedge by the trapezoid rule (C4v)
            t_phi = np.trapezoid(lut.T.sum(axis=-1), lut.phi, axis=1) / (math.pi / 4)
            wl = np.array([weight(float(t)) for t in lut.theta])
            ax_t.plot(np.degrees(lut.theta), t_phi, lw=1.4, label=label)
            ax_e.plot(np.degrees(lut.theta), t_phi * wl * np.sin(lut.theta) / 2, lw=1.4,
                      label=label)  # fmt: skip
        theta_c = math.degrees(math.asin(n2 / n1))
        for ax in (ax_t, ax_e):
            ax.axvline(theta_c, color="grey", ls=":", lw=1)
            ax.set_xlabel("polar angle in the crystal θ [deg]  (dotted: critical angle)")
            ax.set_xlim(0, 90)
            ax.grid(True, alpha=0.3)
        ax_t.set_ylabel("first-pass transmission T")
        ax_t.set_title(f"LYSO → {medium}: transmission, averaged over φ", fontsize=9)
        ax_e.set_ylabel("dE(100 ps)/dθ [1/rad]")
        ax_e.set_title(f"LYSO → {medium}: contribution to the 100 ps yield (eq. 1)", fontsize=9)
        ax_t.legend(fontsize=7)
    fig.suptitle(f"M4 fine tables (order 9, θ 1° × φ 5°), commit {git_commit()}", fontsize=9)
    fig.tight_layout()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    out = FIGURES_DIR / "m4_angular_transmission.png"
    fig.savefig(out, dpi=150)
    print(f"saved {out}")


if __name__ == "__main__":
    main()
