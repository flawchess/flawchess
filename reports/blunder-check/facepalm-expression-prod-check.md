# R2 expression readers on prod: plans, parity (Phase 254 release R2)

Date: 2026-11-15 (UTC). Plan 254-10 Task 3.

## Precondition

`copy_line_material.py --db prod --status` from the prod-run worktree before the merge:
`copy_pending_rows=0 copied_rows=2169544`. Plan 06 recorded a passing parity after the copy.

## Query plans before and after (read-only, prod)

`EXPLAIN (ANALYZE, BUFFERS)` on the statements the four readers send, captured with literal binds from the R1 code
(prod-run worktree at `697ec5fbd`, stored column) and from the R2 branch (expression). Three rounds on one read-only
connection; execution time in ms. Round 1 hit a cold cache on the R1 library queries.

Inputs: user 28; drill pickers with `require_facepalm`, limit 20; foreign band 1400 to 1700, sample 2.0%; loader over
user 28's 20 newest fully evaluated games; `query_flaws` with severity blunder and `min_facepalm_pct=70`.

| Statement | R1 round 1 | R1 round 2 | R1 round 3 | R2 round 1 | R2 round 2 | R2 round 3 |
|---|---|---|---|---|---|---|
| `pick_own_game_ids` | 74.3 | 41.5 | 43.8 | 53.9 | 45.7 | 50.0 |
| `pick_foreign_game_ids` | 75.2 | 33.1 | 47.2 | 45.1 | 57.3 | 41.7 |
| `load_blunder_flaws` | 0.96 | 0.19 | 0.36 | 0.39 | 0.55 | 0.28 |
| `query_flaws` count | 675.9 | 68.9 | 60.7 | 71.7 | 68.4 | 61.4 |
| `query_flaws` page | 824.1 | 63.6 | 62.5 | 54.1 | 55.9 | 52.8 |

No expression plan is more than twice as slow as its stored-column counterpart, and none is near 1 s. No expression
index is needed.

## Release

- R2 squash commit on main: `5d9075796` (tree identical to the gated branch tip `840bd35c6`).
- Release PR #479, CI green, squash-merged to production as `9c22730c6`.
- Deployed through `bin/deploy.sh`, finished 2026-11-15T01:13Z, server SHA verified as `9c22730c`. Site HTTP 200,
  backend container up, no error lines in the backend log tail.
- Forward-port pushed to main as `4d0a3f586`.
- The release contained only R2 (plans 08, 18, 09, the changelog) and Phase 254 docs.

## Strict parity on live data (from the main checkout, deployed code)

`stored_scored=1850930 expression_scored=1850930 both_scored=1850930 max_abs_diff=1.003345291294977e-07 cut_side_mismatches=0`

Exit 0. PASS: the difference is below 1e-6, the scored counts are equal, and there is no cut-side mismatch. This is
the strict check for the D-02 drop gate; after the refit the stored column is stale by design.

## Sentry

Checked 2026-11-15T01:16Z: no issue first seen in the previous 3 hours in the `flawchess` organization (this covers
the R1 deploy at 23:38Z and the first minutes of R2). A second check one hour after the R2 deploy is recorded in the
plan summary.
