# scripts/

Every number or figure quoted in the docs is produced by code in this repository and
saved with the git commit that produced it.

Light scripts (run on a laptop in seconds; results in `results/m1_*.json`):
- `escape_cone.py` (M1): η₁ for LYSO→air, LYSO→grease, BGO→air.
- `fresnel_vs_rcwa.py` (M1): flat interface, analytic Fresnel vs torcwa, R + T check.
- `benchmark_rcwa.py` (M1, laptop era): kept so `results/m1_rcwa_benchmark.json` stays
  reproducible; superseded by the remote `benchmark` job.

Light scripts that read downloaded remote results (seconds; M4):
- `check_early_yield.py`: derivation 05, eq. (1), against the M3 Monte Carlo.
- `make_m4_configs.py`: writes the fine-table and Monte Carlo configs from finished runs.
- `recover_optimize_log.py`: rebuilds an optimisation start from the job log when its
  checkpoint was lost.
- `m4_table_checks.py`: fine-table integrals, angle-grid bounds, lookup-model integrals
  with and without side-wall losses (eq. 1a), and the Monte Carlo against them.
- `plot_angular_transmission.py`, `key_figure.py`: the M4 figures.

Heavy work runs on GitHub Actions through `remote_job.py` (jobs in
`src/phcscint/jobs.py`, configs in `configs/`):

| Job | Config | Produces |
|---|---|---|
| `benchmark` | `configs/benchmark.json` | time per RCWA solve vs Fourier order, backward-pass cost, grid budgets |
| `convergence` | `configs/m2_convergence.json` | Fourier-order and grid convergence of the reference photonic crystal |
| `lut` | `configs/m2_lut_*.json`, `configs/m4_lut_*.json` | angle-resolved lookup tables (npz) with single-pass extraction |
| `mc` | `configs/m3_*.json`, `configs/m4_mc_*.json` | Monte Carlo of the pixel: efficiency, time CDF, early yields, analytic oracle |
| `optimize` | `configs/m4_opt_*.json` | Adam ascent of the early-photon or single-pass objective from several starts |
| `ordercheck` | `configs/m4_ordercheck.json` | integrated objectives of the final designs vs Fourier order |

```bash
gh workflow run compute.yml --ref <branch> -f job=<job> -f config=<config>
gh run watch <run-id>
gh run download <run-id> -D results/<job>/<run-id>/
```

The small `summary.json` of a run is copied to `results/<job>-<run-id>.json` and its
figure to `docs/figures/` when the numbers are quoted in the docs.
