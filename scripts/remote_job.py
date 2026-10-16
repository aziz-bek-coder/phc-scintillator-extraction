"""Driver for heavy computations on GitHub Actions (.github/workflows/compute.yml).

Subcommands
  plan  --job J --config C
      Print 'matrix=<json>' for $GITHUB_OUTPUT. Imports nothing heavy, so the plan step
      needs no package installation.
  run   --job J --config C --chunk I --n-chunks N --out DIR [--resume DIR] [--deadline-min M]
      Run one chunk into DIR/<J>-chunk-<I>/, checkpointing as it goes, and write
      chunk.json (parameters, git commit, runtime, complete flag). If --resume holds a
      checkpoint for this chunk, finished work is skipped. A chunk that reaches its
      deadline stops cleanly with complete = false, so its artifact can be resumed.
  merge --job J --config C --in DIR --out DIR
      Combine every chunk directory found under --in into DIR/: summary.json plus
      job-specific csv/png/npz files.

The jobs themselves live in src/phcscint/jobs.py (JOBS).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))  # plan step runs without installing the package

from phcscint.jobs import JOBS, Deadline, runner_info, write_json  # noqa: E402

JOB_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,40}$")


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


def load_config(path: str) -> dict[str, Any]:
    p = (REPO / path).resolve()
    if REPO / "configs" not in p.parents:
        raise SystemExit(f"config must live under configs/: {path}")
    return json.loads(p.read_text(encoding="utf-8"))


def cmd_plan(args: argparse.Namespace) -> None:
    if not JOB_RE.match(args.job) or args.job not in JOBS:
        raise SystemExit(f"unknown job {args.job!r}; known: {sorted(JOBS)}")
    cfg = load_config(args.config)
    n = JOBS[args.job].n_chunks(cfg)
    if n > 6:
        print(f"note: {n} chunks; at most 6 run in parallel", file=sys.stderr)
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
