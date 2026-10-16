"""Recover the trajectory of one optimisation start from the GitHub job logs (light).

Used when a runner died before the chunk checkpoint was uploaded: the optimize job prints
one line per Adam step ("start k step n: J=... a=... f=... h=..."), so the evaluated
designs survive in the log even when history.json is lost. The objective is printed to
6 decimals and the parameters to 4, which is what the recovered design carries.
If several runs are given (resumed attempts of the same start), their step lines must
agree; the longest is kept.

Run: python scripts/recover_optimize_log.py --config configs/<opt>.json --chunk <k>
         --run <run-id> [<run-id> ...] --out <name>
Writes results/<name>.json (steps, best step, bare objective on the same grid).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess

from phcscint.jobs import Optimize
from phcscint.provenance import REPO_ROOT, git_commit, save_results

LINE = re.compile(r"start (\d+) step (\d+): J=([-+0-9.eE]+) a=([0-9.]+) f=([0-9.]+) h=([0-9.]+)")


def step_lines(run: str, chunk: int) -> list[dict]:
    view = subprocess.run(["gh", "run", "view", run, "--json", "jobs"], capture_output=True,
                          text=True, check=True)  # fmt: skip
    job = next(
        j for j in json.loads(view.stdout)["jobs"] if j["name"].startswith(f"run ({chunk},")
    )
    log = subprocess.run(
        ["gh", "run", "view", "--job", str(job["databaseId"]), "--log"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout
    steps = []
    for m in LINE.finditer(log):
        if int(m.group(1)) != chunk:
            continue
        steps.append({"step": int(m.group(2)), "objective": float(m.group(3)),
                      "period_um": float(m.group(4)), "fill": float(m.group(5)),
                      "height_um": float(m.group(6))})  # fmt: skip
    return steps


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--chunk", type=int, required=True)
    ap.add_argument("--run", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    print(f"commit {git_commit()}")
    cfg = json.loads((REPO_ROOT / args.config).read_text(encoding="utf-8"))
    opt, lam, n1, n2, n_p, bounds, weight, grid = Optimize._setup(cfg)
    per_run = {run: step_lines(run, args.chunk) for run in args.run}
    longest = max(per_run.values(), key=len)
    agree = all(s == longest[: len(s)] for s in per_run.values())
    best = max(longest, key=lambda s: s["objective"])
    best = best | {"radius_um": best["period_um"] * (best["fill"] / 3.141592653589793) ** 0.5}
    for run, s in per_run.items():
        print(f"run {run}: {len(s)} step lines")
    print(
        f"agree: {agree}; best step {best['step']}: J = {100 * best['objective']:.4f} %, "
        f"a = {best['period_um']} um, f = {best['fill']}, h = {best['height_um']} um"
    )
    path = save_results(args.out, {
        "what": f"start {args.chunk} of {args.config}, recovered from the job logs",
        "config_path": args.config, "chunk": args.chunk, "start": cfg["starts"][args.chunk],
        "runs": {run: len(s) for run, s in per_run.items()}, "runs_agree": agree,
        "steps_planned": cfg["steps"], "steps": longest, "best": best,
        "precision": "objective 6 decimals, parameters 4 decimals (as printed by the job)",
        "bare_objective_same_grid": opt.bare_objective(weight, n1, n2, grid),
    })  # fmt: skip
    print(f"saved {path}")


if __name__ == "__main__":
    main()
