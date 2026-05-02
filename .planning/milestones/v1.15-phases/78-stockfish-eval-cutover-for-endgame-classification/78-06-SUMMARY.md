---
phase: 78
plan: "06"
subsystem: cutover
tags: [cutover, operator, smoke, backfill, dev-only, deferred]
---

# Plan 78-06 SUMMARY — Cutover Execution (slimmed: dev-DB smoke only)

## Scope reduction (decided 2026-05-02)

The original plan sequenced a full operator cutover: dev smoke → benchmark backfill (~2 h) → VAL-01 ≥99% agreement gate → prod backfill via tunnel → merge → deploy → VAL-02 live UI smoke.

A new requirement landed mid-phase: extend the eval scheme to also cover **middlegame** entry positions, using the lichess Divider classifier (`piece_count` + `backrank_sparse` + `mixedness` — all already on `game_positions`). Doing it as a follow-up phase (79) lets the combined endgame + middlegame backfill run as a single benchmark + prod pass instead of paying the operational cost twice.

**Phase 78 ships code only.** Operational steps are deferred:

| Original step | Status |
|---------------|--------|
| Round 1 — Dev DB smoke (`--user-id 28`) | ✅ Done — see results below |
| Round 2 — Benchmark DB full backfill | ⏸ Deferred to post-phase-79 (combined run) |
| Round 3 — Prod DB backfill via tunnel | ⏸ Deferred to post-phase-79 (combined run) |
| VAL-01 ≥99% agreement vs Stockfish | ⏸ Deferred — runs after combined backfill |
| Merge to main + `bin/deploy.sh` | ⏸ Deferred — bundle deploy with phase 79 so prod doesn't run with eval-classification on a no-eval DB |
| VAL-02 live UI smoke | ⏸ Deferred — after deploy |

The phase branch stays unmerged. Production keeps using the material-imbalance + 4-ply persistence proxy until phase 79 ships and the combined backfill populates both endgame and middlegame eval entries.

## Round 1 results (dev DB, user_id=28)

User 28 = aimfeld80@gmail.com. 5062 games, 336 618 positions, 110 261 endgame positions before backfill (35 667 already eval-populated from lichess `%eval` PGN annotations).

Local Stockfish: pinned sf_17 AVX2 binary (same SHA as Dockerfile: `6c9aaaf4...341cdde`), installed at `~/.local/stockfish/sf` and exported via `STOCKFISH_PATH`.

```
$ uv run python scripts/backfill_eval.py --db dev --user-id 28 --dry-run
[2026-05-02 13:32:28] Starting backfill: db=dev user_id=28 dry_run=True limit=None
[2026-05-02 13:32:29] Found 3758 span-entry rows with NULL eval (db=dev, user_id=28, limit=None)
[2026-05-02 13:32:29] --dry-run: exiting without starting engine or writing
[2026-05-02 13:32:29] Done.

$ uv run python scripts/backfill_eval.py --db dev --user-id 28
[2026-05-02 13:32:52] Committed 200/3758 rows (evaluated=200, skipped_no_board=0, skipped_engine_err=0)
... (37 commit batches at 100 rows each) ...
[2026-05-02 13:34:48] Final commit. Total evaluated=3758, skipped_no_board=0, skipped_engine_err=0
[2026-05-02 13:34:48] Running VACUUM ANALYZE game_positions...
[2026-05-02 13:34:50] VACUUM ANALYZE complete.
[2026-05-02 13:34:50] Done.
real    2m05s

$ uv run python scripts/backfill_eval.py --db dev --user-id 28
[2026-05-02 13:35:00] Starting backfill: db=dev user_id=28 dry_run=False limit=None
[2026-05-02 13:35:01] Found 0 span-entry rows with NULL eval (db=dev, user_id=28, limit=None)
[2026-05-02 13:35:01] Nothing to do.
[2026-05-02 13:35:01] Done.
real    2s
```

| Metric | Value |
|--------|-------|
| Rows evaluated | 3758 / 3758 |
| `skipped_no_board` (PGN replay failures) | 0 |
| `skipped_engine_err` (engine returned `(None, None)`) | 0 |
| Total wall time | 2 m 05 s |
| Per-eval latency (depth 15) | ~33 ms |
| VACUUM ANALYZE | succeeded |
| Idempotency re-run (no work expected) | exits in ~2 s, no engine spawned |

## Final state for user 28

```sql
WITH span_min AS (
  SELECT user_id AS uid, game_id AS gid, endgame_class AS ec, MIN(ply) AS min_ply
  FROM game_positions
  WHERE endgame_class IS NOT NULL
  GROUP BY user_id, game_id, endgame_class
  HAVING COUNT(ply) >= 6   -- ENDGAME_PLY_THRESHOLD
)
SELECT COUNT(*) AS total, COUNT(eval_cp) + COUNT(eval_mate) AS populated_evals
FROM game_positions gp
JOIN span_min sm USING (uid, gid, ec)  -- pseudocode; real query joins on the four columns
WHERE gp.user_id = 28 AND gp.ply = sm.min_ply;
```

Result: **4231 qualifying span entries, 4231 populated (100% coverage), 0 NULL.**

(The other ~106 000 endgame positions for user 28 are not span entries — they're follow-on plies inside ongoing endgame spans, which the new eval-based classification reads through `array_agg(eval_cp ORDER BY ply)[1]` against the span-entry row only.)

## Outcome

- ✅ Backfill script end-to-end correct against real chess.com PGN data (zero `skipped_no_board` over 3758 PGN replays at varying ply depths)
- ✅ Engine wrapper (Plan 78-02) handled 3758 sequential UCI evaluations without process restart, leak, or hang
- ✅ COMMIT-every-100 cadence works (37 batches)
- ✅ Idempotency holds (row-level WHERE on `eval_cp IS NULL AND eval_mate IS NULL` per Plan 78-03 Decision D-10)
- ✅ VACUUM ANALYZE executes cleanly post-backfill
- ✅ FILL-04 lichess preservation: pre-existing 35 667 lichess `%eval` rows untouched (script filters them out before engine call)

## What ships in phase 78

Code-complete for endgame classification cutover:
- `Dockerfile` + CI runner ship pinned sf_17 AVX2 (Plans 78-01)
- `app/services/engine.py` async UCI wrapper, lifespan-bound (Plan 78-02)
- `scripts/backfill_eval.py` standalone CLI (Plan 78-03)
- `app/services/import_service.py` evals span entries on import (Plan 78-04)
- `app/repositories/endgame_repository.py` + `app/services/endgame_service.py` read `eval_cp`/`eval_mate` instead of material-imbalance proxy (Plan 78-05)
- Alembic migration `c92af8282d1a` reshapes `ix_gp_user_endgame_game` INCLUDE columns

## What's gated until phase 79

- Apply migration `c92af8282d1a` on benchmark + prod DBs
- Run `scripts/backfill_eval.py --db benchmark` (full ~1.5M positions, ~2 h on 8 cores at depth 15)
- Re-run `/conv-recov-validation` skill — assert ≥99% agreement vs Stockfish on the populated subset (VAL-01)
- Run `scripts/backfill_eval.py --db prod` via `bin/prod_db_tunnel.sh` localhost:15432
- Merge phase-78 + phase-79 to main, deploy via `bin/deploy.sh`
- VAL-02 live UI smoke check on 3-5 representative users
