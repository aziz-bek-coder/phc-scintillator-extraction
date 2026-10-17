"""Write the M5 robustness configs (light; no physics).

restarts: python scripts/make_m5_configs.py restarts [--seed 20261017] [--steps 40]
          Three new starting designs for the early-photon optimisation, drawn by Latin
          hypercube sampling over the same bounds, with the M4 settings otherwise:
          configs/m5_opt_<medium>_early_restarts.json for grease and air. The same
          three starts are used for both media. Distances to the M4 starts are printed
          (in units of the bound widths) to show that the new starts are different.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.stats import qmc

REPO = Path(__file__).resolve().parents[1]
KEYS = ("period_um", "fill", "height_um")


def write(path: Path, obj: dict) -> None:
    path.write_bytes((json.dumps(obj, indent=2) + "\n").encode("utf-8"))  # LF on every OS


def cmd_restarts(args) -> None:
    for medium in ("grease", "air"):
        base = json.loads((REPO / "configs" / f"m4_opt_{medium}_early.json").read_text())
        lo = np.array([base["bounds"][k][0] for k in KEYS])
        hi = np.array([base["bounds"][k][1] for k in KEYS])
        u = qmc.LatinHypercube(d=3, seed=args.seed).random(3)
        starts = np.round(lo + (hi - lo) * u, 3)
        old = np.array(base["starts"])
        for s in starts:
            dist = np.min(np.linalg.norm((old - s) / (hi - lo), axis=1))
            print(f"{medium}: start {s.tolist()}, nearest M4 start at {dist:.2f} bound widths")
        cfg = {
            **base,
            "description": f"M5 robustness: the early-photon optimisation of M4 "
            f"(configs/m4_opt_{medium}_early.json) rerun from three new starts, Latin "
            f"hypercube over the same bounds (seed {args.seed}), {args.steps} Adam steps.",
            "steps": args.steps,
            "starts": starts.tolist(),
        }
        out = REPO / "configs" / f"m5_opt_{medium}_early_restarts.json"
        write(out, cfg)
        print(out.relative_to(REPO))


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("restarts")
    r.add_argument("--seed", type=int, default=20261017)
    r.add_argument("--steps", type=int, default=40)
    args = ap.parse_args()
    {"restarts": cmd_restarts}[args.cmd](args)


if __name__ == "__main__":
    main()
