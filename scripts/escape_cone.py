"""Escape-cone fractions for the project's material pairs (derivation 01).

Produces results/m1_escape_cone.json and prints a table with the commit hash.
Run: python scripts/escape_cone.py
"""

from __future__ import annotations

import math

from phcscint import analytic
from phcscint.fresnel import escape_fraction_one_face_fresnel
from phcscint.materials import BGO, LYSO, LYSO_N_EPIC, N_AIR, N_GREASE
from phcscint.provenance import git_commit, save_results

CASES = [
    ("LYSO -> air", LYSO.n, N_AIR),
    ("LYSO -> grease", LYSO.n, N_GREASE),
    ("BGO -> air", BGO.n, N_AIR),
    ("BGO -> grease", BGO.n, N_GREASE),
    ("LYSO(n=1.82, Epic) -> air", LYSO_N_EPIC, N_AIR),
]


def main() -> None:
    rows = []
    print(f"commit {git_commit()}")
    print(
        f"{'case':28s} {'n1':>5s} {'n2':>4s} {'theta_c[deg]':>12s} {'eta_1':>8s} {'eta_1^F':>8s}"
    )
    for name, n1, n2 in CASES:
        theta_c = analytic.critical_angle(n1, n2)
        eta = analytic.escape_fraction_one_face(n1, n2)
        eta_f = escape_fraction_one_face_fresnel(n1, n2)
        rows.append(
            {
                "case": name,
                "n1": n1,
                "n2": n2,
                "theta_c_deg": math.degrees(theta_c),
                "eta_1": eta,
                "eta_1_fresnel": eta_f,
                "cones_overlap_same_n2": analytic.cones_overlap(n1, n2),
            }
        )
        print(
            f"{name:28s} {n1:5.2f} {n2:4.2f} {math.degrees(theta_c):12.3f} "
            f"{100 * eta:7.3f}% {100 * eta_f:7.3f}%"
        )
    six = analytic.escapable_fraction_cuboid(LYSO.n)
    print(f"LYSO, six bare faces into air, specular: escapable fraction = {100 * six:.3f}%")
    mixed = analytic.escapable_fraction_cuboid(LYSO.n, (N_AIR,) * 5 + (N_GREASE,))
    print(f"LYSO, grease on +z, air elsewhere, specular: escapable fraction = {100 * mixed:.3f}%")
    path = save_results(
        "m1_escape_cone",
        {
            "definition": "eta_1 = (1 - cos theta_c)/2; eta_1_fresnel = eq. (7) of derivation 02",
            "cases": rows,
            "lyso_six_faces_air_specular": six,
            "lyso_grease_readout_air_sides_specular": mixed,
        },
    )
    print(f"saved {path}")


if __name__ == "__main__":
    main()
