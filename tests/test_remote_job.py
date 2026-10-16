"""The remote-job driver (scripts/remote_job.py): plan output, checkpoint/resume,
merge. Uses configs/smoke_benchmark.json (Fourier orders 1-2) so it stays fast."""

import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("remote_job", REPO / "scripts" / "remote_job.py")
remote_job = importlib.util.module_from_spec(spec)
spec.loader.exec_module(remote_job)

SMOKE = "configs/smoke_benchmark.json"


def test_plan_prints_github_output_line(capsys) -> None:
    remote_job.main(["plan", "--job", "benchmark", "--config", SMOKE])
    line = capsys.readouterr().out.strip()
    assert line.startswith("matrix=")
    matrix = json.loads(line.removeprefix("matrix="))
    assert matrix == {"include": [{"chunk": 0, "n_chunks": 1}]}


def test_plan_rejects_unknown_job_and_outside_config() -> None:
    with pytest.raises(SystemExit):
        remote_job.main(["plan", "--job", "rm -rf", "--config", SMOKE])
    with pytest.raises(SystemExit):
        remote_job.main(["plan", "--job", "benchmark", "--config", "pyproject.toml"])


def test_run_resume_and_merge(tmp_path) -> None:
    out1 = tmp_path / "out1"
    args = ["run", "--job", "benchmark", "--config", SMOKE, "--chunk", "0", "--n-chunks", "1"]
    # deadline 0: stops before doing any work, but leaves a valid incomplete chunk
    remote_job.main([*args, "--out", str(out1), "--deadline-min", "0"])
    meta = json.loads((out1 / "benchmark-chunk-0" / "chunk.json").read_text())
    assert meta["complete"] is False
    # resume from that checkpoint and finish
    out2 = tmp_path / "out2"
    remote_job.main([*args, "--out", str(out2), "--resume", str(out1)])
    meta = json.loads((out2 / "benchmark-chunk-0" / "chunk.json").read_text())
    assert meta["complete"] is True
    assert len(meta["segments"]) == 2  # the interrupted segment and the resumed one
    rows = json.loads((out2 / "benchmark-chunk-0" / "rows.json").read_text())
    assert {(r["kind"], r["order"]) for r in rows} == {
        ("forward", 1),
        ("forward", 2),
        ("gradient", 1),
    }
    for r in rows:
        if r["kind"] == "forward":
            assert r["energy_sum"] == pytest.approx(1.0, abs=1e-9)
        else:
            assert r["dT_dr"] != 0.0 and r["dT_dh"] != 0.0
    final = tmp_path / "final"
    remote_job.main(
        ["merge", "--job", "benchmark", "--config", SMOKE, "--in", str(out2), "--out", str(final)]
    )
    summary = json.loads((final / "summary.json").read_text())
    assert summary["complete"] is True
    assert [t["order"] for t in summary["forward"]] == [1, 2]
    assert summary["budgets"]["coarse_lut_M1"]["solves"] == 450
    assert (final / "benchmark.csv").exists() and (final / "benchmark.png").exists()


def test_merge_flags_incomplete(tmp_path) -> None:
    out = tmp_path / "out"
    remote_job.main(
        [
            "run",
            "--job",
            "benchmark",
            "--config",
            SMOKE,
            "--chunk",
            "0",
            "--n-chunks",
            "1",
            "--out",
            str(out),
            "--deadline-min",
            "0",
        ]
    )
    with pytest.raises(SystemExit):
        remote_job.main(
            [
                "merge",
                "--job",
                "benchmark",
                "--config",
                SMOKE,
                "--in",
                str(out),
                "--out",
                str(tmp_path / "final"),
            ]
        )


# ---------------------------------------------------------------- M2 jobs


def _run_all_chunks(job: str, config: str, out, n: int) -> None:
    for c in range(n):
        remote_job.main(
            ["run", "--job", job, "--config", config, "--chunk", str(c), "--n-chunks", str(n),
             "--out", str(out)]
        )  # fmt: skip


def test_material_names_resolve_to_materials_module() -> None:
    from phcscint.jobs import resolve_index, resolve_wavelength
    from phcscint.materials import LYSO, N_GREASE, n_si3n4_luke

    lam = resolve_wavelength("LYSO-peak")
    assert lam == LYSO.wavelength_um
    assert resolve_index("LYSO", lam) == LYSO.n
    assert resolve_index("grease", lam) == N_GREASE
    assert resolve_index("Si3N4-Luke2015", lam) == n_si3n4_luke(lam)
    assert resolve_index(1.7, lam) == 1.7
    with pytest.raises(ValueError):
        resolve_index("unobtainium", lam)


def test_convergence_job_assigns_every_item_once_and_merges(tmp_path) -> None:
    from phcscint.jobs import JOBS

    cfg = json.loads((REPO / "configs" / "smoke_convergence.json").read_text())
    pairs = JOBS["convergence"].assignment(cfg, 2)
    assert len(pairs) == 3 + 2  # three orders plus two grid-check items
    assert {owner for _, owner in pairs} == {0, 1}
    out = tmp_path / "out"
    _run_all_chunks("convergence", "configs/smoke_convergence.json", out, 2)
    final = tmp_path / "final"
    remote_job.main(["merge", "--job", "convergence", "--config", "configs/smoke_convergence.json",
                     "--in", str(out), "--out", str(final)])  # fmt: skip
    s = json.loads((final / "summary.json").read_text())
    assert s["complete"] is True
    assert len(s["rows"]) == 5
    assert s["max_energy_error"] < 1e-9
    assert {r["order"] for r in s["relative_change"]} == {1, 2, 3}
    assert "grease" in s["recommended_order"]
    assert (final / "convergence.png").exists() and (final / "convergence.csv").exists()


def test_lut_job_chunks_merge_to_the_same_table_as_a_direct_build(tmp_path) -> None:
    from phcscint.jobs import JOBS
    from phcscint.lut import LUT, build_lut

    out = tmp_path / "out"
    _run_all_chunks("lut", "configs/smoke_lut.json", out, 2)
    final = tmp_path / "final"
    remote_job.main(["merge", "--job", "lut", "--config", "configs/smoke_lut.json",
                     "--in", str(out), "--out", str(final)])  # fmt: skip
    s = json.loads((final / "summary.json").read_text())
    assert s["complete"] is True and s["lut_complete"] is True
    assert s["max_energy_error"] < 1e-9
    assert 0 < s["eta_single_pass_phc"] < 0.5
    merged = LUT.load(final / s["lut_file"])
    cfg = json.loads((REPO / "configs" / "smoke_lut.json").read_text())
    full = JOBS["lut"].full_config(cfg)
    assert merged.config == full
    direct, _ = build_lut(full, cache_dir=tmp_path / "direct", progress=None)
    import numpy as np

    np.testing.assert_allclose(merged.T, direct.T, atol=1e-13)
    np.testing.assert_allclose(merged.R, direct.R, atol=1e-13)


def test_optimize_job_runs_resumes_and_merges(tmp_path) -> None:
    out = tmp_path / "out"
    base = ["run", "--job", "optimize", "--config", "configs/smoke_optimize.json"]
    remote_job.main([*base, "--chunk", "0", "--n-chunks", "2", "--out", str(out),
                     "--deadline-min", "0"])  # fmt: skip
    meta = json.loads((out / "optimize-chunk-0" / "chunk.json").read_text())
    assert meta["complete"] is False
    _run_all_chunks("optimize", "configs/smoke_optimize.json", out, 2)
    final = tmp_path / "final"
    remote_job.main(["merge", "--job", "optimize", "--config", "configs/smoke_optimize.json",
                     "--in", str(out), "--out", str(final)])  # fmt: skip
    s = json.loads((final / "summary.json").read_text())
    assert s["complete"] is True
    assert [st["steps"] for st in s["starts"]] == [2, 2]
    assert s["best"]["objective"] >= max(st["initial_objective"] for st in s["starts"])
    assert s["recheck"]["order"] == 2
    assert (final / "optimize.png").exists()


# ---------------------------------------------------------------- M4 jobs


def test_ordercheck_job_integrates_both_objectives(tmp_path) -> None:
    from phcscint.jobs import JOBS

    cfg = json.loads((REPO / "configs" / "smoke_ordercheck.json").read_text())
    pairs = JOBS["ordercheck"].assignment(cfg, 2)
    assert len(pairs) == 2 * 2  # two orders x two incidences, one design
    assert {owner for _, owner in pairs} == {0, 1}
    out = tmp_path / "out"
    _run_all_chunks("ordercheck", "configs/smoke_ordercheck.json", out, 2)
    final = tmp_path / "final"
    remote_job.main(["merge", "--job", "ordercheck", "--config", "configs/smoke_ordercheck.json",
                     "--in", str(out), "--out", str(final)])  # fmt: skip
    s = json.loads((final / "summary.json").read_text())
    assert s["complete"] is True and s["max_energy_error"] < 1e-9
    (d,) = s["designs"]
    assert set(d["by_order"]) == {"1", "2"} and set(d["rel_change_vs_top"]) == {"1"}
    for v in d["by_order"].values():
        assert 0 < v["early"] < v["single_pass"] < 0.5
    assert (final / "ordercheck.png").exists() and (final / "ordercheck.csv").exists()


def test_ordercheck_with_invisible_pillars_reproduces_the_bare_face(tmp_path, monkeypatch) -> None:
    """Pillars with the index of the outside medium: every order must give the flat-face
    (Fresnel) value of both integrals, which checks the solve-to-integral bookkeeping."""
    from phcscint.jobs import JOBS, Deadline, OrderCheck

    lut = json.loads((REPO / "configs" / "smoke_lut.json").read_text())["lut"]
    layer = {**lut["layer"], "n_pillar": "grease"}
    invisible = {"config": "(test)", **lut, "label": "invisible", "layer": layer}
    monkeypatch.setattr(OrderCheck, "_designs", staticmethod(lambda cfg: [invisible]))
    cfg = json.loads((REPO / "configs" / "smoke_ordercheck.json").read_text())
    job = JOBS["ordercheck"]
    assert job.run(cfg, 0, 1, tmp_path, Deadline(60)) is True
    (d,) = job.merge(cfg, [tmp_path], tmp_path)["designs"]
    for v in d["by_order"].values():
        for k in ("early", "single_pass"):
            assert v[k] == pytest.approx(d["bare_same_grid"][k], rel=1e-10)
