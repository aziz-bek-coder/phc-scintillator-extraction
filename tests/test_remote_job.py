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
