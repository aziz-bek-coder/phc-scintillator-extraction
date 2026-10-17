"""Robustness check 2 (M5): the early-photon optimisation from three new starts (light).

Compares the M4 runs with the M5 restarts, on the objective the optimiser itself uses:
derivation 05, eq. (1), at Fourier order 5 on the 18 x 4 optimisation grid. For every
start it gives the best objective, its gain over the bare face on the same grid, and the
design it reached. It also counts how many starts end above the bare face and how many
reach the M4 optimum (within 1 % of its gain).

Inputs: results/optimize-<run>.json (committed run summaries).
Run: python scripts/m5_restart_check.py
Writes results/m5_restart_check.json.
"""

from __future__ import annotations

import json

from phcscint.provenance import REPO_ROOT, git_commit, save_results

RUNS = {
    "grease": {"m4": ["38905901930"], "m5": "39018671447"},
    "air": {"m4": ["38950528275"], "m5": "39018677264"},
}


def starts(run: str) -> tuple[list[dict], float]:
    s = json.loads((REPO_ROOT / "results" / f"optimize-{run}.json").read_text())
    if s["objective_kind"] != "early":
        raise SystemExit(f"{run}: not an early-photon run")
    bare = s["bare_objective_same_grid"]
    out = []
    for st in s["starts"]:
        out.append(
            {
                "run": run,
                "chunk": st["chunk"],
                "start": st["start"],
                "steps": st["steps"],
                "best_objective": st["best_objective"],
                "gain_over_bare": st["best_objective"] / bare - 1,
                "final": st["final"],
            }
        )
    return out, bare


def main() -> None:
    print(f"commit {git_commit()}")
    media = {}
    for medium, r in RUNS.items():
        m4 = [x for run in r["m4"] for x in starts(run)[0]]
        m5, bare = starts(r["m5"])
        best_m4 = max(m4, key=lambda x: x["best_objective"])
        best_m5 = max(m5, key=lambda x: x["best_objective"])
        reach = [x for x in m5 if x["gain_over_bare"] >= 0.99 * best_m4["gain_over_bare"]]
        media[medium] = {
            "bare_objective_same_grid": bare,
            "m4_starts": m4,
            "m5_starts": m5,
            "m4_best": best_m4,
            "m5_best": best_m5,
            "m5_starts_above_bare": sum(x["gain_over_bare"] > 0 for x in m5),
            "m5_starts_reaching_m4_best": len(reach),
        }
        print(f"{medium}: bare {100 * bare:.3f} %, M4 best {100 * best_m4['best_objective']:.3f} %"
              f" (gain {100 * best_m4['gain_over_bare']:+.2f} %)")  # fmt: skip
        for x in m5:
            f = x["final"]
            print(
                f"  restart {x['chunk']} from {x['start']}: best "
                f"{100 * x['best_objective']:.3f} % (gain {100 * x['gain_over_bare']:+.2f} %),"
                f" ends at a={f['period_um']:.3f} f={f['fill']:.3f} h={f['height_um']:.3f}"
            )
    what = (
        "early-photon optimisation from three new Latin-hypercube starts (M5) vs the M4 "
        "starts, objective of derivation 05 eq. (1), order 5, 18 x 4 grid"
    )
    print(f"saved {save_results('m5_restart_check', {'what': what, 'media': media})}")


if __name__ == "__main__":
    main()
