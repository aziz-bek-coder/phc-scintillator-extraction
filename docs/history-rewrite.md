# History rewrite of 2026-10-16

Approved once by Aziz, before publication only: author and committer emails of every
commit were changed to Aziz's GitHub noreply address
(`262705928+aziz-bek-coder@users.noreply.github.com`), for his own commits and for the
agents' commits. Names, dates, trees and messages were not changed. Tool:
`git filter-repo 2.47.0 --mailmap`, mapping `(personal address, removed before publication)` and
`noreply@anthropic.com` (agent author address) to the noreply address. GitHub's own
committer identity on web merges (`GitHub <noreply@github.com>`) was left as is.

Result files written before the rewrite carry the old commit hashes in their
provenance stamps. Use this map to find the same code in the rewritten history.

| Old | New | Commit |
|---|---|---|
| 8f1c7c4 | a3b81c9 | M0: repo skeleton |
| 7023550 | dd7da6a | Normalise line endings to LF |
| c85772f | 741d6b7 | M1: escape cone, Fresnel, flat-interface torcwa check, RCWA benchmark |
| d096fce | 8c941a8 | M1: results, figures, status report |
| 0308772 | aa1c501 | Merge pull request #1 |
| c7ae265 | a0bec4c | M2 (wip): derivation 03, patterned RCWA, LUT module |
| ba0148a | 0ba8197 | M2 (wip): grease index from EJ-550 |
| 59da1f2 | 6ec12e1 | M2: batch LUT sampling, provenance at import |
| f0cc446 | 6b28260 | M3 (wip): Monte Carlo pixel model |

The old commits are still stored by GitHub and reachable through the merged pull
request #1 (`refs/pull/1/head` points to the old `d096fce`). See docs/status.md,
"Publication".


# History rewrite of 2026-10-17: the public repository

Approved by Aziz on 2026-10-17 ("switching commit emails to my GitHub noreply address"
before publication, and the "new repository" option).

Why a new repository:
- GitHub keeps the refs of merged pull requests (`refs/pull/N/head`), and users cannot
  delete them.
- In the old repository those refs still reached commits with Aziz's personal address:
  - the pre-rewrite commits of PR #1;
  - GitHub's merge commits of PRs #2 and #3 (`c7e7621`, `38bcdf6`), on main and inside
    PRs #3–#5.
- An old version of this file also named the address.
- Rewriting `main` could not remove those refs. So the old repository was renamed to
  `aziz-bek-coder/phc-scintillator-extraction-archive` and stays private. This
  repository was created fresh from the rewritten history.

What changed:
- Tool: `git filter-repo a40bce548d2c` on `main`.
- `--mailmap`: the personal address goes to the noreply address, names kept. This
  affects the two GitHub merge commits.
- `--replace-text`: the address replaced inside file contents. Only this file
  contained it.
- Trees, dates and messages are otherwise unchanged. The final tree differs from the
  archive's only in this file.

What did not change:
- Remote runs. Every run ID quoted in `results/` and `docs/` before 2026-10-17 is a
  workflow run of the archive repository.
- Commit hashes inside result files are hashes of the archive history. The map below
  translates them.
- The quoted numbers are all in the committed summaries (`results/*.json`). The run
  artifacts (tables, CSVs) stay in the archive until their 30-day retention ends.

Commits older than the first affected one kept their hashes and are not listed.

| Archive commit | Public commit | Subject |
|---|---|---|
| b5b417f | 5ecb44e | Infra: MIT licence, WIP README, pinned actions, remote compute workflow, laptop test limits |
| c7e7621 | 7e0c5df | Merge pull request #2 from aziz-bek-coder/claude/infra-compute |
| 7e4de75 | 76b5eaa | M2 (wip): derivation 03, patterned RCWA solve, thin-film formula, LUT module, convergence script |
| 1c30b2b | e130ddb | M2 (wip): grease index from Eljen EJ-550 (1.46); M2 tests; LUT build script |
| c64729b | ae197a9 | M2: batch LUT sampling, provenance captured at import, LUT records build commits |
| 108612d | 6397c67 | M2 (wip): build_lut can stop at a deadline and checkpoint (for remote chunks) |
| 50d3984 | 45c2740 | M4 (wip): draft derivation 05, early-photon objective (not yet checked against code) |
| 49189f4 | c6c2f43 | M2: remote convergence and lut jobs; grids sized from the remote benchmark |
| 0060901 | f0e7d1b | M3 (wip): Monte Carlo pixel model, analytic timing oracle, derivation 04, tests |
| 40c7f22 | b928c47 | M3: mc remote job (seeded chunks per case, analytic oracle in merge), validation and wall-model configs |
| 1fd662b | 9651fc0 | M3: reference PhC vs bare config (uses coarse LUT runs 38901905525 and 38901911122) |
| efcdef2 | 04b120e | M2: results from remote runs (convergence, coarse LUTs), status, decisions |
| 38bcdf6 | 8b8a96c | Merge pull request #3 from aziz-bek-coder/claude/m2-reference-phc |
| 585a10a | 51a8801 | Merge branch 'main' into claude/m3-mc |
| 7d480c6 | f731611 | M3: remote Monte Carlo results (validation, wall models, reference PhC), status, decisions |
| 39c3f4e | e0f891c | Merge branch 'main' into claude/m4-optimisation |
| 2b50905 | 1b48b8e | M4: differentiable early-photon objective, optimiser, optimize remote job, configs |
| e107a3b | acd3084 | M4: eq. (1) vs Monte Carlo check (all /z/ <= 1.2) |
| dbbacf7 | a972a44 | M4: skip backward at incidences with no propagating transmitted order |
| 2bf04bf | c96b29b | M4: fine lookup-table configs for the final designs, config and figure scripts |
| 5a4a6bb | af2e979 | M4: ordercheck job, integrated objectives of final designs vs Fourier order |
| c477633 | 14c06af | Derivation 05: name the jobs and scripts that exist |
| 003f408 | ecd85cc | M4: fine-table checks (angle-grid bound, eq. (1) vs Monte Carlo); readable MC case names |
| 6cc272f | bc3a866 | M4: angular transmission figure script; in-cone vs trapped split of the table checks |
| 04f0aae | dd35ed2 | M4: Monte Carlo comparison config, grease (bare, reference, two optimised designs) |
| decc222 | 5554743 | M4: Monte Carlo check of eq. (1) with ideal mirror walls (fine grease tables) |
| 8875fcd | c871c6b | M4: recover an optimisation start from the job logs when its checkpoint was lost |
| 61166d1 | 60a4329 | M4: log recovery also summarises the finished starts of a run |
| 14f9f18 | 33b7838 | M4: air early design recovered from the job logs; its fine table and the order check |
| 3e10fb0 | 90fb8bb | M4: table checks integrate the Monte Carlo lookup model, with side-wall losses (eq. 1a) |
| c0be7cb | f7c0bcb | M4: fix the memory leak that shut down the air runner; derivation 05 scope of eq. (1) |
| 3624ec4 | 34f9e10 | M4: key figure shows gains relative to the bare face (early-time curves, early vs total light) |
| e300ef2 | 4b83810 | M4: grease run summaries (optimisation, fine tables, Monte Carlo), table checks, scripts README |
| 05f08b3 | 0fd742f | M4: Monte Carlo comparison config, air (bare, reference, early-photon optimum) |
| 1e6fc51 | 7dbc822 | M4: table checks also report the near-normal transmission |
| 195a6bd | fb05699 | M4: status, key figure, angular transmission and order-check figures, PLAN ticks |
| 3ea5d54 | 89a23cc | M4: air optimisation completed with the leak fix (run 38950528275) |
