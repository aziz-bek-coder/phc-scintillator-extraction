"""Helpers so every number a script produces carries its provenance (AGENTS.md)."""

from __future__ import annotations

import datetime as _dt
import json
import platform
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "results"
FIGURES_DIR = REPO_ROOT / "docs" / "figures"


def _compute_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        # "dirty" only if code that produces numbers differs from the commit; regenerated
        # outputs under results/ and docs/figures/ do not count.
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--", "src", "scripts", "pyproject.toml"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        ).stdout.strip()
        return out.stdout.strip() + ("-dirty" if dirty else "")
    except Exception:  # noqa: BLE001 - provenance must never crash a script
        return "unknown"


# Captured once, when the package is imported, i.e. when the code that will produce
# the numbers is loaded. Editing files later in the same session does not change the
# code already running, so the stamp must not be recomputed at save time.
_COMMIT_AT_IMPORT = _compute_commit()
_STARTED_UTC = _dt.datetime.now(_dt.UTC).isoformat(timespec="seconds")


def git_commit() -> str:
    """Commit (with '-dirty' if src/, scripts/ or pyproject.toml had uncommitted
    changes) of the code loaded by this process."""
    return _COMMIT_AT_IMPORT


def stamp() -> dict[str, Any]:
    return {
        "git_commit": git_commit(),
        "started_utc": _STARTED_UTC,
        "utc": _dt.datetime.now(_dt.UTC).isoformat(timespec="seconds"),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "torch": torch.__version__,
        "machine": platform.machine(),
    }


def save_results(name: str, payload: dict[str, Any]) -> Path:
    """Write results/<name>.json with a provenance stamp; returns the path."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / f"{name}.json"
    data = {"provenance": stamp(), **payload}
    path.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return path
