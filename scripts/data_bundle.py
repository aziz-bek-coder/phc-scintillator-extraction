"""Pack or fetch the merged outputs of the remote runs (light; no physics).

Every number and figure in the docs comes from a remote run. Run artifacts expire after
30 days, and runs before 2026-10-17 belong to the private archive repository, so the
merged outputs of every quoted run (summary.json, tables, CSVs, figures) are published
as one zip file attached to a GitHub release of this repository. results/runs.json lists
the runs: job, run ID, repository, milestone and config.

  pack:  python scripts/data_bundle.py pack --out <zip>
         Zips results/<job>/<run>/ for every listed run (merged outputs only, not chunk
         checkpoints) from the local downloads.
  fetch: python scripts/data_bundle.py fetch --tag <release-tag>
         Downloads the release asset and unpacks it into results/ (no GitHub login
         needed for this public repository); skips runs already present.
"""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "results"
PUBLIC = "aziz-bek-coder/phc-scintillator-extraction"
ASSET = "phcscint-run-outputs.zip"


def runs() -> list[dict]:
    return json.loads((RESULTS / "runs.json").read_text(encoding="utf-8"))["runs"]


def cmd_pack(args) -> None:
    out = Path(args.out)
    n = 0
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for r in runs():
            d = RESULTS / r["job"] / str(r["run"])
            files = [p for p in d.iterdir() if p.is_file()] if d.exists() else []
            if not any(p.name == "summary.json" for p in files):
                raise SystemExit(f"missing merged outputs for {r['job']} {r['run']}: {d}")
            for p in sorted(files):
                z.write(p, f"{r['job']}/{r['run']}/{p.name}")
                n += 1
        z.write(RESULTS / "runs.json", "runs.json")
    print(f"packed {n} files from {len(runs())} runs into {out} ({out.stat().st_size} bytes)")


def cmd_fetch(args) -> None:
    missing = [
        r for r in runs() if not (RESULTS / r["job"] / str(r["run"]) / "summary.json").exists()
    ]
    if not missing:
        print("all run outputs present")
        return
    url = f"https://github.com/{PUBLIC}/releases/download/{args.tag}/{ASSET}"
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / ASSET
        with urllib.request.urlopen(url) as resp, path.open("wb") as f:  # noqa: S310
            shutil.copyfileobj(resp, f)
        with zipfile.ZipFile(path) as z:
            for r in missing:
                prefix = f"{r['job']}/{r['run']}/"
                for name in z.namelist():
                    if name.startswith(prefix):
                        z.extract(name, RESULTS)
    print(f"fetched {len(missing)} runs from release {args.tag}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pack")
    p.add_argument("--out", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("--tag", required=True)
    args = ap.parse_args()
    {"pack": cmd_pack, "fetch": cmd_fetch}[args.cmd](args)


if __name__ == "__main__":
    main()
