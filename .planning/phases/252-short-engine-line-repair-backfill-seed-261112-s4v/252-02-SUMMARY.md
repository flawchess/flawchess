---
phase: 252-short-engine-line-repair-backfill-seed-261112-s4v
plan: 02
subsystem: tier-4-flaw-blob-lane
tags: [postgres, jsonb, coalesce, fastapi, tier-4-backfill, per-line-null]

requires:
  - phase: 252-01
    provides: line repair script that NULLs/rewrites stored pvs (consumer of this lane)
provides:
  - per-line NULL semantics for the tier-4 flaw-blob lane (D-03)
  - fill-NULL-only blob writer (_batch_fill_null_flaw_pv_lines) and OR stamp probe
  - shared submit core eval_apply.apply_flaw_blob_results with a typed FlawBlobApplyOutcome (D-12 hook for plan 03)
  - stamp_flaw_blob_sentinels for the two /flaw-blob-lease 204 branches
affects: [252-03, 252-04, 252-07, 252-08]

actuals:
  tokens: 17600
  tasks: 2
  commits: 2
plan_head_before: 143c5db5f68a7af4b63007a8021be9e8d0a8c824
plan_head_after: a4bd5eecc621450b8a4720b87b7f5e3a3fbbcd7f

tech-stack:
  added: []
  patterns:
    - "fill-NULL-only writes via COALESCE(existing, new) so every tier-4 write site is safe for single-line re-walks"
    - "submit core returns a typed outcome (status, blobs_written, foreign_token); the router maps it to HTTP and keeps heartbeat + Maia re-score"

key-files:
  created: []
  modified:
    - app/services/eval_apply.py
    - app/routers/eval_remote.py
    - tests/test_eval_worker_endpoints.py
    - tests/services/test_eval_apply.py
    - tests/services/test_eval_queue.py

key-decisions:
  - "The two blob writers share one VALUES/CAST builder (_flaw_pv_values_clause); _batch_update_flaw_pv_lines keeps overwrite semantics for _diff_upsert_flaw_rows, tier 4 uses only the COALESCE writer"
  - "Tag updates are grouped by column set (both lines: 8 columns, one line: 4 columns) and written with one bulk_update_tactic_tags call per group, so no executemany mixes key sets"
  - "stamp_flaw_blob_sentinels takes the per-game advisory lock (the old inline branches did not), serialising the sentinel write against the submit path"
  - "The nothing_pending path keeps the old behaviour: stamp refresh only, no heartbeat upsert (the in_tx_hook runs only on the applied path)"

requirements-completed: [D-03, D-06]

coverage:
  - id: C1
    description: "A flaw with only its missed (or only its allowed) line NULL is leased for that line alone, written fill-NULL-only, and only that line's four tactic columns are re-derived; the other line and its tags stay byte-identical"
    requirement: "D-03"
    verification:
      - kind: integration
        ref: "tests/test_eval_worker_endpoints.py#TestFlawBlobSingleNullLine"
        status: pass
    human_judgment: false
  - id: C2
    description: "Sentinel (all-sentinel and over-cap) branches never clobber a non-NULL line; games.blobs_completed_at stays NULL while any line of any flaw is NULL and is stamped once both are filled"
    requirement: "D-03"
    verification:
      - kind: integration
        ref: "tests/test_eval_worker_endpoints.py#TestFlawBlobSingleNullLine"
        status: pass
      - kind: integration
        ref: "tests/services/test_eval_apply.py#TestRefreshBlobsCompletedPerLine"
        status: pass
    human_judgment: false
  - id: C3
    description: "A token for a non-NULL line is rejected with 422 and nothing is written; a second identical submit writes nothing; both-NULL flaws behave as before"
    requirement: "D-03"
    verification:
      - kind: integration
        ref: "tests/test_eval_worker_endpoints.py#TestFlawBlobSingleNullLine"
        status: pass
    human_judgment: false
  - id: C4
    description: "The tier-4 per-line path never writes eval_cp, eval_mate or game_best_moves"
    requirement: "D-06"
    verification:
      - kind: integration
        ref: "tests/test_eval_worker_endpoints.py#TestFlawBlobSingleNullLine::test_missed_only_null_line_end_to_end"
        status: pass
    human_judgment: false
  - id: C5
    description: "Fill-NULL-only writer keeps a non-NULL column and writes a JSON array (never JSON null) into a SQL NULL one"
    requirement: "D-03"
    verification:
      - kind: integration
        ref: "tests/services/test_eval_apply.py#TestFillNullOnlyWriter"
        status: pass
    human_judgment: false

duration: 40min
completed: 2026-11-12
status: complete
---

# Phase 252 Plan 02: Per-line NULLs in the tier-4 flaw-blob lane Summary

**The tier-4 lane now leases, sentinels, writes and retags only the NULL line of a flaw: every blob write is `COALESCE(existing, new)`, the stamp probe checks either line, and the submit core lives in `eval_apply.apply_flaw_blob_results` so plan 03's drain tick shares it.**

## Performance

- **Duration:** ~40 min
- **Tasks:** 2 (tracer, edge cases)
- **Files modified:** 5 (no model or migration change)

## Accomplishments

- `_null_blob_lines_by_ply` is the single per-line NULL definition (SQL NULL only, JSON null documented as invisible); `_build_flaw_blob_lease_positions` leases and sentinels only NULL lines (missed node 0 = flaw ply, allowed = flaw ply + 1) and loads pv only for the needed node-0 plies.
- `_batch_fill_null_flaw_pv_lines` (COALESCE per column) is the only blob writer of the tier-4 lane (submit, all-sentinel and over-cap branches); `_batch_update_flaw_pv_lines` is untouched in behaviour for `_diff_upsert_flaw_rows`.
- `_refresh_blobs_completed` probes `allowed_pv_lines IS NULL OR missed_pv_lines IS NULL`, with a D-03 comment at the probe.
- `apply_flaw_blob_results(game_id, evals, *, in_tx_hook=None) -> FlawBlobApplyOutcome` holds the former `_apply_flaw_blob_submit` body (read phase, idempotency gate, re-derived lease and 422-equivalent `foreign_token`, FLAWCHESS-8D in-lock survivor filter, stamp refresh, commit). The router wrapper maps statuses to 404/422, upserts the heartbeat via the hook in the same transaction and runs the Maia re-score.
- `stamp_flaw_blob_sentinels(game_id, plies | None)` backs both 204 branches of `/flaw-blob-lease` (advisory lock, fill-NULL-only sentinel, stamp refresh; `None` = every NULL-line ply for the over-cap case).

## Task Commits

1. **Task 1: Tracer, a single NULL missed line leased, submitted and written alone** - `8c974a8a8` (feat)
2. **Task 2: Sentinel and over-cap branches, stamp invariant and per-line edge cases** - `a4bd5eecc` (feat)

## Mutation proof (Task 2 step 4)

Each guard was reverted, the relevant tests run, then restored (final tree green, 42 passed):

| Reverted guard | Tests that failed |
|---|---|
| OR probe back to `allowed_pv_lines IS NULL` | `TestRefreshBlobsCompletedPerLine::test_missed_only_null_keeps_game_pending_until_filled`, `::test_stamp_clears_again_when_a_line_is_re_nulled` |
| COALESCE writer back to overwrite | `TestFlawBlobSingleNullLine` missed-only e2e, allowed-only e2e, all-sentinel and over-cap tests, plus `TestFillNullOnlyWriter::test_keeps_non_null_line_and_fills_null_line` |

The over-cap test is killed by the writer mutation (the kept allowed line is clobbered with `[]`), not by the probe mutation: in that test every NULL line is sentineled, so the stamp ends non-NULL either way. The stamp invariant is proven by the service-level probe tests.

## Verification run

- `uv run pytest tests/test_eval_worker_endpoints.py tests/services/test_eval_apply.py -n auto -q -k "blob or fill_null or refresh_blobs or FillNull or PerLine or SingleNull"`: 42 passed.
- Wider run `uv run pytest -n auto tests/ -q -k "eval or blob or flaw or drain or tier4 or maia"`: 1345 passed, 8 skipped.
- `uv run ty check app/ tests/ scripts/`: all checks passed. `uv run ruff check .` and `ruff format` clean.
- `uv run python scripts/check_function_size.py app/ --fail-over-depth 4`: OK, no breaches.
- `git diff --name-only $(git merge-base HEAD main) -- app/models alembic/versions`: empty (no migration, claim SQL and `ix_games_blob_backfill_pending` untouched).
- Acceptance greps: `COALESCE(game_flaws` x3, `missed_pv_lines IS NULL` x1, `stamp_flaw_blob_sentinels(` x2 in the router, `_batch_update_flaw_pv_lines(` x0 in the router.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] FLAWCHESS-8D no-resurrect test patched the router binding the submit no longer uses**
- **Found during:** Task 1 (`TestFlawBlobSubmitEndpoint::test_blob_submit_no_resurrect` failed)
- **Issue:** The test simulates a concurrent `rederive` DELETE by monkeypatching `eval_remote._build_flaw_blob_lease_positions` and expects the submit's re-derive call to hit it. After the core moved to eval_apply the submit resolves that call through `eval_apply`'s module binding, so the delete never ran and the assertion failed.
- **Fix:** the test now patches (and delegates to) `app.services.eval_apply._build_flaw_blob_lease_positions`; assertions unchanged. The /flaw-blob-lease endpoint still uses the router binding, which other tests patch unchanged.
- **Files modified:** `tests/test_eval_worker_endpoints.py`
- **Commit:** `8c974a8a8`

**2. [Rule 1 - Bug] Two tier-4 queue tests modelled "blobbed" as allowed-only**
- **Found during:** Task 1 wider run (`tests/services/test_eval_queue.py::TestTier4BlobBackfill::test_tier4_blobbed_game_excluded`, `::test_tier4_returns_none_empty_queue`)
- **Issue:** both set only `allowed_pv_lines` and expected `_refresh_blobs_completed` to stamp the game. Under D-03 a game with a NULL `missed_pv_lines` is correctly still pending, so the stamp stayed NULL and the claim re-picked the game.
- **Fix:** `_insert_game_flaw` gained a `missed_pv_lines` kwarg; both tests now fill both lines (the intent "all blobs written" is unchanged).
- **Files modified:** `tests/services/test_eval_queue.py` (not in the plan's `files_modified`)
- **Commit:** `8c974a8a8`

### Plan-form deviations (intent met)

- Task 1 already swapped the router's two sentinel branches to the fill-NULL writer (with an inline OR predicate on the over-cap plies) so the commit was never a regression window; Task 2 then replaced both branches with `stamp_flaw_blob_sentinels`.
- `stamp_flaw_blob_sentinels` takes the per-game advisory lock, which the old inline branches did not; this is stricter, not looser.

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug), both test-side. **Impact:** none on production behaviour beyond the plan.

## Known Stubs

None.

## Threat Flags

None. T-252-04 mitigated (kept-line token rejected with 422, every write COALESCE, covered by `test_token_for_kept_line_rejected_422` and the over-cap/all-sentinel tests); T-252-05 mitigated (OR probe, `stamp_flaw_blob_sentinels` backstop, `jsonb_typeof` test proves no JSON null).

## Next Phase Readiness

Plan 03 can call `apply_flaw_blob_results` from the server-pool blob-only tick (D-12) without an `in_tx_hook`; the Maia re-score (`score_game_flaws_after_apply`) stays with the caller because `maia_flaw_scoring` imports `eval_apply`.

## Self-Check: PASSED

- Files: `app/services/eval_apply.py`, `app/routers/eval_remote.py`, `tests/test_eval_worker_endpoints.py`, `tests/services/test_eval_apply.py`, `tests/services/test_eval_queue.py` modified and present.
- Commits `8c974a8a8` and `a4bd5eecc` are ancestors of HEAD; `git rev-list --count 143c5db5f..HEAD` = 2.
