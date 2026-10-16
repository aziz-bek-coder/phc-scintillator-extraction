"""Write the M4 follow-up configs from finished remote runs (light; no physics).

  luts:  python scripts/make_m4_configs.py luts [--opt <medium>:<kind>:<summary.json> ...]
                                               [--ref <medium> ...]
         One fine lookup-table config per design (best design of each optimisation run,
         plus the reference design once per medium of --opt and --ref):
         configs/m4_lut_<label>.json.
  mc:    python scripts/make_m4_configs.py mc --medium grease --lut <label>:<run-id> ...
         One Monte Carlo config comparing the bare face with every listed table:
         configs/m4_mc_<medium>.json.

Fine grid (docs/decisions.md): theta 1 deg midpoints x phi 5 deg, order 9, 4 chunks.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REFERENCE = {"period_um": 0.40, "radius_um": 0.12, "height_um": 0.30}
FINE = {"order": 9, "n_grid": 256, "theta_step_deg": 1.0, "phi_step_deg": 5.0}


def lut_config(label: str, medium: str, layer: dict, note: str) -> dict:
    return {
        "description": f"M4 fine lookup table ({note}): theta 1 deg x phi 5 deg, order 9.",
        "lut": {
            "n1": "LYSO",
            "n2": medium,
            "wavelength_um": "LYSO-peak",
            "layer": {**layer, "n_pillar": "Si3N4-Luke2015"},
            **FINE,
            "window": "auto",
            "edge_sharpness": 1000.0,
            "label": label,
        },
        "chunks": 4,
    }


def cmd_luts(args) -> None:
    media = set(args.ref)
    for spec in args.opt:
        medium, kind, path = spec.split(":", 2)
        s = json.loads(Path(path).read_text())
        b = s["best"]
        layer = {
            "period_um": round(b["period_um"], 5),
            "radius_um": round(b["period_um"] * math.sqrt(b["fill"] / math.pi), 5),
            "height_um": round(b["height_um"], 5),
        }
        label = f"opt_{kind}_lyso_{medium}_fine_M9"
        note = f"best {kind} design for {medium}, optimisation run in {path}"
        out = REPO / "configs" / f"m4_lut_{label}.json"
        out.write_text(json.dumps(lut_config(label, medium, layer, note), indent=2) + "\n")
        print(out.relative_to(REPO), layer)
        media.add(medium)
    for medium in sorted(media):
        label = f"ref_lyso_{medium}_fine_M9"
        out = REPO / "configs" / f"m4_lut_{label}.json"
        out.write_text(
            json.dumps(lut_config(label, medium, REFERENCE, "Knapitsch-style reference"), indent=2)
            + "\n"
        )
        print(out.relative_to(REPO), REFERENCE)


def cmd_mc(args) -> None:
    walls = {"kind": "wrapped_specular", "reflectivity": 0.95}
    cases = [{"name": f"bare readout, {args.medium}", "walls": walls,
              "readout": {"n_out": args.medium}}]  # fmt: skip
    for spec in args.lut:
        label, run = spec.split(":", 1)
        summary = REPO / "results" / "lut" / run / "summary.json"
        fname = json.loads(summary.read_text())["lut_file"]
        cases.append(
            {
                "name": label,
                "walls": walls,
                "readout": {
                    "n_out": args.medium,
                    "lut": {"run_id": int(run), "artifact": "lut-result", "file": fname},
                },
            }
        )
    cfg = {
        "description": f"M4 comparison, LYSO 3x3x20 mm -> {args.medium}: bare face vs fine "
        "lookup tables (order 9); all five other faces polished + air gap + mirror film, "
        "ASSUMED reflectivity 0.95.",
        "pixel": {
            "n1": "LYSO",
            "wavelength_um": "LYSO-peak",
            "lx_um": 3000,
            "ly_um": 3000,
            "lz_um": 20000,
        },  # fmt: skip
        "t_max_ps": 5000,
        "n_photons_per_chunk": 500000,
        "chunks_per_case": 2,
        "seed": args.seed,
        "tau_ps": [50, 100, 200],
        "t_grid_ps": {"stop": 5000, "step": 10},
        "cases": cases,
    }
    out = REPO / "configs" / f"m4_mc_{args.medium}.json"
    out.write_text(json.dumps(cfg, indent=2) + "\n")
    print(out.relative_to(REPO), [c["name"] for c in cases])


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("luts")
    a.add_argument("--opt", nargs="+", default=[], help="medium:kind:path/to/summary.json")
    a.add_argument("--ref", nargs="+", default=[], help="extra media for the reference design")
    b = sub.add_parser("mc")
    b.add_argument("--medium", required=True)
    b.add_argument("--lut", nargs="+", required=True, help="label:lut-run-id")
    b.add_argument("--seed", type=int, default=20261019)
    args = ap.parse_args()
    {"luts": cmd_luts, "mc": cmd_mc}[args.cmd](args)


if __name__ == "__main__":
    main()
