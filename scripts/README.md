# scripts/

Every number or figure quoted in the docs is produced by code in this repository and
saved with the git commit that produced it.

Light scripts (run on a laptop in seconds; results in `results/m1_*.json`):
- `escape_cone.py` (M1): η₁ for LYSO→air, LYSO→grease, BGO→air.
- `fresnel_vs_rcwa.py` (M1): flat interface, analytic Fresnel vs torcwa, R + T check.
- `benchmark_rcwa.py` (M1, laptop era): kept so `results/m1_rcwa_benchmark.json` stays
  reproducible; superseded by the remote `benchmark` job.

Heavy work runs on GitHub Actions through `remote_job.py` (jobs in
`src/phcscint/jobs.py`, configs in `configs/`):

| Job | Config | Produces |
|---|---|---|
| `benchmark` | `configs/benchmark.json` | time per RCWA solve vs Fourier order, backward-pass cost, grid budgets |
| `convergence` | `configs/m2_convergence.json` | Fourier-order and grid convergence of the reference photonic crystal |
| `lut` | `configs/m2_lut_ref_*_coarse_M7.json` | angle-resolved lookup tables (npz) with single-pass extraction |

```bash
gh workflow run compute.yml --ref <branch> -f job=<job> -f config=<config>
gh run watch <run-id>
gh run download <run-id> -D results/<job>/<run-id>/
```

The small `summary.json` of a run is copied to `results/<job>-<run-id>.json` and its
figure to `docs/figures/` when the numbers are quoted in the docs.
