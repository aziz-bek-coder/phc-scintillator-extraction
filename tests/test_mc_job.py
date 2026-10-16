"""The `mc` remote job (src/phcscint/jobs.py): seeded chunks per case, merge with the
analytic oracle. Small photon numbers so it stays fast."""

import json

import numpy as np

from phcscint.fresnel import fresnel_power
from phcscint.jobs import JOBS, Deadline
from phcscint.lut import LUT, LUTConfig, inclusive_grid, midpoint_grid
from phcscint.materials import LYSO, N_GREASE
from phcscint.rcwa import PhCLayer, order_window


def _fresnel_lut(path) -> None:
    """LUT whose only non-zero order is (0, 0) with flat-face Fresnel powers."""
    th_deg = midpoint_grid(0.0, 90.0, 0.25)
    ph_deg = inclusive_grid(0.0, 45.0, 15.0)
    _, _, ts, tp = fresnel_power(LYSO.n, N_GREASE, np.radians(th_deg))
    t00 = 0.5 * (ts + tp)
    orders = order_window(1)
    k = int(np.flatnonzero((orders == [0, 0]).all(axis=1))[0])
    T = np.zeros((len(th_deg), len(ph_deg), len(orders)))
    R = np.zeros_like(T)
    T[:, :, k] = t00[:, None]
    R[:, :, k] = 1 - t00[:, None]
    cfg = LUTConfig(LYSO.n, N_GREASE, 0.42, PhCLayer(0.4, 0.12, 0.3, 2.09), 1, 0, th_deg,
                    ph_deg, 1, label="fresnel")  # fmt: skip
    LUT(cfg, orders, T, R, {"complete": True, "built_at_commits": ["test"]}).save(path)


def test_mc_job_cases_chunks_and_oracle(tmp_path) -> None:
    lut_file = tmp_path / "fresnel.npz"
    _fresnel_lut(lut_file)
    cfg = {
        "description": "test",
        "pixel": {"n1": "LYSO", "wavelength_um": "LYSO-peak"},
        "t_max_ps": 1500.0,
        "n_photons_per_chunk": 6000,
        "chunks_per_case": 2,
        "seed": 7,
        "tau_ps": [100],
        "t_grid_ps": {"stop": 1500, "step": 50},
        "cases": [
            {
                "name": "bare",
                "walls": {"kind": "specular", "reflectivity": 1.0},
                "readout": {"n_out": "grease"},
                "analytic": {"type": "specular_box", "back": "mirror"},
            },
            {
                "name": "fresnel-lut",
                "walls": {"kind": "specular", "reflectivity": 1.0},
                "readout": {"n_out": "grease", "lut": {"path": str(lut_file)}},
                "analytic": {"type": "specular_box", "back": "mirror"},
            },
        ],
    }
    job = JOBS["mc"]
    n = job.n_chunks(cfg)
    assert n == 4
    work = tmp_path / "out"
    for c in range(n):
        d = work / f"mc-chunk-{c}"
        d.mkdir(parents=True)
        assert job.run(cfg, c, n, d, Deadline(60)) is True
        assert job.run(cfg, c, n, d, Deadline(60)) is True  # resume: nothing to redo
    final = tmp_path / "final"
    final.mkdir()
    res = job.merge(cfg, sorted(work.iterdir()), final)
    names = [c["name"] for c in res["cases"]]
    assert names == ["bare", "fresnel-lut"]
    for c in res["cases"]:
        assert c["n_emitted"] == 12000
        assert sum(c["counts"].values()) == 12000
        # 12000 photons: the oracle must hold to a few sigma at every grid point
        assert c["analytic"]["max_abs_z"] < 5
        assert 0 < c["early_yield"]["100"]["value"] < c["efficiency_at_t_max"]
    assert res["cases"][1]["lut"]["lut_label"] == "fresnel"
    # different seeds per chunk: the two parts of a case are not identical
    parts = sorted((work / "mc-chunk-0").glob("*.npz")) + sorted(
        (work / "mc-chunk-1").glob("*.npz")
    )
    with np.load(parts[0]) as a, np.load(parts[1]) as b:
        assert not np.array_equal(a["times_ps"], b["times_ps"])
        assert json.loads(str(a["meta"]))["part"] != json.loads(str(b["meta"]))["part"]
    assert (final / "mc_cdf.png").exists() and (final / "mc_cdf.csv").exists()
