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
