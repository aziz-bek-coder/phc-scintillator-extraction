"""Driver for heavy computations on GitHub Actions (.github/workflows/compute.yml).

Subcommands
  plan  --job J --config C
      Print 'matrix=<json>' for $GITHUB_OUTPUT. Imports nothing heavy.
  run   --job J --config C --chunk I --n-chunks N --out DIR [--resume DIR] [--deadline-min M]
      Run one chunk into DIR/<J>-chunk-<I>/, checkpointing as it goes, and write
      chunk.json (parameters, git commit, runtime, complete flag). If --resume holds a
      checkpoint for this chunk, finished work is skipped. A chunk that reaches its
      deadline stops cleanly with complete = false, so its artifact can be resumed.
  merge --job J --config C --in DIR --out DIR
      Combine every chunk directory found under --in into DIR/: summary.json plus
      job-specific csv/png/npz files.

Jobs are registered in JOBS. Each job implements n_chunks, run and merge; heavy
imports (torch, torcwa, matplotlib) happen inside those methods only.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
JOB_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,40}$")


# ----------------------------------------------------------------------------- utils


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds")


def _git_commit() -> str:
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "--short=12", "HEAD"],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--", "src", "scripts", "configs", "pyproject.toml"],
            cwd=REPO,
            capture_output=True,
            text=True,
        ).stdout.strip()
        return sha + ("-dirty" if dirty else "")
    except Exception:  # noqa: BLE001 - provenance must never crash a job
        return (os.environ.get("GITHUB_SHA") or "unknown")[:12]


COMMIT_AT_START = _git_commit()  # the code this process loaded


def runner_info() -> dict[str, Any]:
    info: dict[str, Any] = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "cpu_count": os.cpu_count(),
        "omp_num_threads": os.environ.get("OMP_NUM_THREADS"),
        "github_sha": os.environ.get("GITHUB_SHA"),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_ref_name": os.environ.get("GITHUB_REF_NAME"),
        "runner_name": os.environ.get("RUNNER_NAME"),
    }
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.exists():
        for line in cpuinfo.read_text(errors="ignore").splitlines():
            if line.lower().startswith("model name"):
                info["cpu_model"] = line.split(":", 1)[1].strip()
                break
    return info


def set_threads() -> int:
    """torch intra-op threads = min(OMP_NUM_THREADS, cpu count)."""
    import torch

    want = int(os.environ.get("OMP_NUM_THREADS", "4"))
    n = max(1, min(want, os.cpu_count() or want))
    torch.set_num_threads(n)
    return n


def peak_rss_mb() -> float:
    try:
        import resource  # Linux / macOS

        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    except ImportError:
        try:
            import psutil

            return psutil.Process().memory_info().rss / 1e6
        except ImportError:
            return float("nan")


class Deadline:
    def __init__(self, minutes: float) -> None:
        self.t0 = time.monotonic()
        self.limit = minutes * 60.0

    def expired(self) -> bool:
        return time.monotonic() - self.t0 >= self.limit


def write_json(path: Path, obj: Any) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def load_config(path: str) -> dict[str, Any]:
    p = (REPO / path).resolve()
    if REPO / "configs" not in p.parents:
        raise SystemExit(f"config must live under configs/: {path}")
    return json.loads(p.read_text(encoding="utf-8"))


# ----------------------------------------------------------------------------- jobs


class Job:
    name = ""

    def n_chunks(self, cfg: dict[str, Any]) -> int:
        return 1

    def run(
        self, cfg: dict[str, Any], chunk: int, n_chunks: int, workdir: Path, deadline: Deadline
    ) -> bool:
        raise NotImplementedError

    def merge(self, cfg: dict[str, Any], chunk_dirs: list[Path], out: Path) -> dict[str, Any]:
        raise NotImplementedError


class Benchmark(Job):
    """Time per RCWA solve against Fourier order, and the cost of one backward pass.

    Measures what the pipeline does per incidence: build the pillar permittivity,
    eigen-decompose the layer (add_layer), assemble the global S-matrix, then extract
    unpolarised powers of all orders in the reporting window, vectorised (4
    polarisation pairs x 2 ports), as phcscint.rcwa.solve_phc does."""

    name = "benchmark"

    def n_chunks(self, cfg: dict[str, Any]) -> int:
        return 1  # timings must come from one machine to be comparable

    @staticmethod
    def _sim(torch, torcwa, g, order, th, ph):
        sim = torcwa.rcwa(
            freq=1.0 / g["wavelength_um"],
            order=[order, order],
            L=[g["period_um"], g["period_um"]],
            dtype=torch.complex128,
            device=torch.device("cpu"),
        )
        sim.add_input_layer(eps=g["n1"] ** 2)
        sim.add_output_layer(eps=g["n2"] ** 2)
        sim.set_incident_angle(inc_ang=th, azi_ang=ph)
        return sim

    @staticmethod
    def _eps(torch, torcwa, g, n_grid, radius, edge):
        geo = torcwa.geometry(
            Lx=g["period_um"],
            Ly=g["period_um"],
            nx=n_grid,
            ny=n_grid,
            edge_sharpness=edge,
            dtype=torch.float64,
            device=torch.device("cpu"),
        )
        c = g["period_um"] / 2
        occ = geo.circle(R=radius, Cx=c, Cy=c)
        eps = g["n2"] ** 2 + (g["n_pillar"] ** 2 - g["n2"] ** 2) * occ
        return eps.to(torch.complex128)

    @staticmethod
    def _window(k: int):
        import numpy as np

        r = np.arange(-k, k + 1)
        mm, nn = np.meshgrid(r, r, indexing="ij")
        return np.stack([mm.ravel(), nn.ravel()], axis=1)

    def _forward(self, torch, torcwa, cfg, order, th, ph) -> dict[str, float]:
        import numpy as np

        g = cfg["geometry"]
        t0 = time.perf_counter()
        sim = self._sim(torch, torcwa, g, order, th, ph)
        eps = self._eps(torch, torcwa, g, cfg["n_grid"], g["radius_um"], 1000.0)
        t1 = time.perf_counter()
        sim.add_layer(thickness=g["height_um"], eps=eps)
        t2 = time.perf_counter()
        sim.solve_global_smatrix()
        t3 = time.perf_counter()
        orders = self._window(min(order, cfg["report_window"]))
        power = {"transmission": 0.0, "reflection": 0.0}
        for port in power:
            for pol in ("ss", "ps", "sp", "pp"):
                s = sim.S_parameters(
                    orders=torch.tensor(orders.copy(), dtype=torch.int64),
                    direction="forward",
                    port=port,
                    polarization=pol,
                    power_norm=True,
                )
                power[port] += 0.5 * float(np.sum(np.abs(s.detach().numpy()) ** 2))
        t4 = time.perf_counter()
        return {
            "seconds_total": t4 - t0,
            "seconds_setup": t1 - t0,
            "seconds_layer_eig": t2 - t1,
            "seconds_smatrix": t3 - t2,
            "seconds_extract": t4 - t3,
            "T_total": power["transmission"],
            "energy_sum": power["transmission"] + power["reflection"],
        }

    def _gradient(self, torch, torcwa, cfg, order, th, ph) -> dict[str, float]:
        g = cfg["geometry"]
        r = torch.tensor(g["radius_um"], dtype=torch.float64, requires_grad=True)
        h = torch.tensor(g["height_um"], dtype=torch.float64, requires_grad=True)
        t0 = time.perf_counter()
        sim = self._sim(torch, torcwa, g, order, th, ph)
        eps = self._eps(torch, torcwa, g, cfg["n_grid"], r, cfg["grad_edge_sharpness"])
        sim.add_layer(thickness=h, eps=eps)
        sim.solve_global_smatrix()
        orders = self._window(min(order, cfg["report_window"]))
        s = sim.S_parameters(
            orders=torch.tensor(orders.copy(), dtype=torch.int64),
            direction="forward",
            port="transmission",
            polarization="ss",
            power_norm=True,
        )
        t_ss = torch.sum(torch.abs(s) ** 2)
        t1 = time.perf_counter()
        t_ss.backward()
        t2 = time.perf_counter()
        return {
            "seconds_forward": t1 - t0,
            "seconds_backward": t2 - t1,
            "T_ss": float(t_ss.detach()),
            "dT_dr": float(r.grad),
            "dT_dh": float(h.grad),
        }

    def run(self, cfg, chunk, n_chunks, workdir, deadline) -> bool:
        import torch
        import torcwa

        n_threads = set_threads()
        rows_path = workdir / "rows.json"
        rows = json.loads(rows_path.read_text()) if rows_path.exists() else []
        done = {(r["kind"], r["order"], r["repeat"]) for r in rows}
        th, ph = (math.radians(x) for x in cfg["incidence_deg"])
        plan = [("forward", o, k) for o in cfg["orders"] for k in range(cfg["repeats"])]
        plan += [
            ("gradient", o, k)
            for o in cfg.get("grad_orders", [])
            for k in range(cfg.get("grad_repeats", 1))
        ]
        for kind, order, rep in plan:
            if (kind, order, rep) in done:
                continue
            if deadline.expired():
                return False
            fn = self._forward if kind == "forward" else self._gradient
            row = fn(torch, torcwa, cfg, order, th, ph)
            row.update(
                kind=kind,
                order=order,
                repeat=rep,
                n_harmonics=(2 * order + 1) ** 2,
                torch_threads=n_threads,
                peak_rss_mb=peak_rss_mb(),
            )
            rows.append(row)
            write_json(rows_path, rows)
            print(json.dumps(row), flush=True)
        return True

    def merge(self, cfg, chunk_dirs, out) -> dict[str, Any]:
        import csv

        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np

        rows = []
        for d in chunk_dirs:
            p = d / "rows.json"
            if p.exists():
                rows += json.loads(p.read_text())
        fwd = [r for r in rows if r["kind"] == "forward"]
        grad = [r for r in rows if r["kind"] == "gradient"]
        if not fwd:
            return {"forward": [], "gradient": [], "budgets": {}}
        table = []
        for order in sorted({r["order"] for r in fwd}):
            sub = [r for r in fwd if r["order"] == order]
            tot = np.array([r["seconds_total"] for r in sub])
            table.append(
                {
                    "order": order,
                    "n_harmonics": (2 * order + 1) ** 2,
                    "repeats": len(sub),
                    "median_s": float(np.median(tot)),
                    "min_s": float(tot.min()),
                    "max_s": float(tot.max()),
                    "median_layer_eig_s": float(np.median([r["seconds_layer_eig"] for r in sub])),
                    "median_smatrix_s": float(np.median([r["seconds_smatrix"] for r in sub])),
                    "median_extract_s": float(np.median([r["seconds_extract"] for r in sub])),
                    "max_energy_error": float(max(abs(r["energy_sum"] - 1) for r in sub)),
                    "T_total": float(np.median([r["T_total"] for r in sub])),
                    "peak_rss_mb": float(max(r["peak_rss_mb"] for r in sub)),
                }
            )
        gtable = []
        for order in sorted({r["order"] for r in grad}):
            sub = [r for r in grad if r["order"] == order]
            gtable.append(
                {
                    "order": order,
                    "median_forward_s": float(np.median([r["seconds_forward"] for r in sub])),
                    "median_backward_s": float(np.median([r["seconds_backward"] for r in sub])),
                    "dT_dr": sub[-1]["dT_dr"],
                    "dT_dh": sub[-1]["dT_dh"],
                }
            )
        fit = None
        big = [t for t in table if t["order"] >= cfg.get("fit_min_order", 7)]
        if len(big) >= 2:
            x = np.log([t["n_harmonics"] for t in big])
            y = np.log([t["median_s"] for t in big])
            fit = float(np.polyfit(x, y, 1)[0])
        by_order = {t["order"]: t["median_s"] for t in table}
        budgets = {}
        for name, grid in cfg.get("planned_grids", {}).items():
            n_solves = grid["n_theta"] * grid["n_phi"]
            for order in grid["orders"]:
                if order in by_order:
                    budgets[f"{name}_M{order}"] = {
                        "solves": n_solves,
                        "hours_one_runner": n_solves * by_order[order] / 3600.0,
                    }
        for name, step in cfg.get("planned_gradient_steps", {}).items():
            gt = {t["order"]: t for t in gtable}
            if step["order"] in gt:
                t = gt[step["order"]]
                per = t["median_forward_s"] + t["median_backward_s"]
                budgets[name] = {
                    "incidences_per_step": step["incidences"],
                    "minutes_per_step_one_runner": step["incidences"] * per / 60.0,
                }

        with (out / "benchmark.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(table[0].keys()))
            w.writeheader()
            w.writerows(table)
        fig, ax = plt.subplots(figsize=(5.2, 3.8))
        nh = [t["n_harmonics"] for t in table]
        med = [t["median_s"] for t in table]
        lo = [t["median_s"] - t["min_s"] for t in table]
        hi = [t["max_s"] - t["median_s"] for t in table]
        ax.errorbar(
            nh, med, yerr=[lo, hi], fmt="o-", capsize=3, label="forward solve + extraction"
        )
        if gtable:
            gn = [(2 * t["order"] + 1) ** 2 for t in gtable]
            ax.plot(gn, [t["median_backward_s"] for t in gtable], "s--", label="backward pass")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("Fourier harmonics (2M+1)²")
        ax.set_ylabel("seconds (median of repeats)")
        title = f"torcwa on {runner_info().get('cpu_model', 'runner')}"
        ax.set_title(title[:70], fontsize=8)
        ax.grid(True, which="both", alpha=0.3)
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(out / "benchmark.png", dpi=130)
        return {
            "forward": table,
            "gradient": gtable,
            "fit_exponent_time_vs_harmonics": fit,
            "budgets": budgets,
        }


JOBS: dict[str, Job] = {j.name: j for j in (Benchmark(),)}


# ----------------------------------------------------------------------------- commands


def cmd_plan(args: argparse.Namespace) -> None:
    if not JOB_RE.match(args.job) or args.job not in JOBS:
        raise SystemExit(f"unknown job {args.job!r}; known: {sorted(JOBS)}")
    cfg = load_config(args.config)
    n = JOBS[args.job].n_chunks(cfg)
    matrix = {"include": [{"chunk": i, "n_chunks": n} for i in range(n)]}
    print("matrix=" + json.dumps(matrix, separators=(",", ":")))


def _restore(resume: str | None, workdir: Path) -> None:
    if not resume:
        return
    base = Path(resume)
    for src in (base / workdir.name, base):
        if src.is_dir() and any(src.iterdir()):
            for f in src.iterdir():
                if f.is_file() and not (workdir / f.name).exists():
                    shutil.copy2(f, workdir / f.name)
            print(f"resumed from {src}", flush=True)
            return


def cmd_run(args: argparse.Namespace) -> None:
    job = JOBS[args.job]
    cfg = load_config(args.config)
    workdir = Path(args.out) / f"{args.job}-chunk-{args.chunk}"
    workdir.mkdir(parents=True, exist_ok=True)
    _restore(args.resume, workdir)
    meta_path = workdir / "chunk.json"
    segments = json.loads(meta_path.read_text())["segments"] if meta_path.exists() else []
    seg = {"git_commit": COMMIT_AT_START, "started_utc": utc_now(), "runner": runner_info()}
    t0 = time.perf_counter()
    complete = job.run(cfg, args.chunk, args.n_chunks, workdir, Deadline(args.deadline_min))
    seg.update(ended_utc=utc_now(), seconds=time.perf_counter() - t0, complete=complete)
    segments.append(seg)
    write_json(
        meta_path,
        {
            "job": args.job,
            "config_path": args.config,
            "config": cfg,
            "chunk": args.chunk,
            "n_chunks": args.n_chunks,
            "complete": complete,
            "segments": segments,
        },
    )
    print(f"chunk {args.chunk}/{args.n_chunks} complete={complete}", flush=True)


def cmd_merge(args: argparse.Namespace) -> None:
    job = JOBS[args.job]
    cfg = load_config(args.config)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    metas = sorted(Path(args.inp).rglob("chunk.json"))
    chunk_dirs = [m.parent for m in metas]
    chunks = [json.loads(m.read_text()) for m in metas]
    n_expected = chunks[0]["n_chunks"] if chunks else 0
    complete = bool(chunks) and len(chunks) == n_expected and all(c["complete"] for c in chunks)
    extras = job.merge(cfg, chunk_dirs, out) if chunks else {}
    summary = {
        "job": args.job,
        "config_path": args.config,
        "config": cfg,
        "merged_at_commit": COMMIT_AT_START,
        "merged_utc": utc_now(),
        "complete": complete,
        "chunks": [
            {
                "chunk": c["chunk"],
                "complete": c["complete"],
                "segments": c["segments"],
                "seconds": sum(s["seconds"] for s in c["segments"]),
            }
            for c in chunks
        ],
        "total_runner_seconds": sum(sum(s["seconds"] for s in c["segments"]) for c in chunks),
        **extras,
    }
    write_json(out / "summary.json", summary)
    print(json.dumps({k: summary[k] for k in ("job", "complete", "total_runner_seconds")}))
    if not complete:
        sys.exit("merge: some chunks are missing or incomplete; resume with resume_run_id")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--job", required=True)
    p.add_argument("--config", required=True)
    r = sub.add_parser("run")
    r.add_argument("--job", required=True, choices=sorted(JOBS))
    r.add_argument("--config", required=True)
    r.add_argument("--chunk", type=int, required=True)
    r.add_argument("--n-chunks", type=int, required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--resume", default=None)
    r.add_argument("--deadline-min", type=float, default=270.0)
    m = sub.add_parser("merge")
    m.add_argument("--job", required=True, choices=sorted(JOBS))
    m.add_argument("--config", required=True)
    m.add_argument("--in", dest="inp", required=True)
    m.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    {"plan": cmd_plan, "run": cmd_run, "merge": cmd_merge}[args.cmd](args)


if __name__ == "__main__":
    main()
