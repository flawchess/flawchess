---
phase: 79-position-phase-classifier-and-middlegame-eval
plan: "03"
subsystem: backfill-script
tags:
  - backfill
  - phase-classification
  - middlegame-eval
  - stockfish
  - sentry

dependency_graph:
  requires:
    - "app/services/position_classifier.py (MIDGAME_MAJORS_AND_MINORS_THRESHOLD, MIDGAME_MIXEDNESS_THRESHOLD)"
    - "app/repositories/endgame_repository.py (ENDGAME_PIECE_COUNT_THRESHOLD)"
    - "app/models/game_position.py (phase column added by 79-01)"
    - "scripts/backfill_eval.py (Phase 78 backfill driver — extended)"
  provides:
    - "scripts/backfill_eval.py: PHASE_BACKFILL_CHUNK_SIZE constant"
    - "scripts/backfill_eval.py: phase-column UPDATE pass (PHASE-FILL-01)"
    - "scripts/backfill_eval.py: _build_middlegame_entry_stmt statement builder"
    - "scripts/backfill_eval.py: _evaluate_and_write_rows shared eval helper"
    - "scripts/backfill_eval.py: middlegame entry eval pass (PHASE-FILL-02)"
  affects:
    - "79-04: operator runbook (dev smoke -> benchmark + VAL-01 -> prod)"

tech_stack:
  added:
    - "typing.Sequence for rows parameter (covariant, accepts SQLAlchemy result sequences)"
    - "typing.Literal for eval_kind tag typing"
  patterns:
    - "chunked SQL CASE UPDATE keyed on id range, COMMIT per chunk, WHERE phase IS NULL resume predicate"
    - "f-string constant interpolation into SQL text (single source of truth for thresholds)"
    - "sibling stmt builder parallel to _build_span_entry_stmt (different shape, same output columns)"
    - "shared async eval+write helper parameterised by eval_kind Sentry tag"
    - "Sentry bounded context: no pgn, fen, user_id (T-78-13/T-78-18)"

key_files:
  modified:
    - "scripts/backfill_eval.py"

decisions:
  - "PHASE_BACKFILL_CHUNK_SIZE = 10_000 defensive default per D-79-01 (operator can tune vs EXPLAIN ANALYZE on benchmark)"
  - "Phase pass runs FIRST inside run_backfill (D-79-02: phase -> endgame -> middlegame)"
  - "Sibling _build_middlegame_entry_stmt not UNION ALL (D-79-03: different shapes, simpler logic)"
  - "Shared _evaluate_and_write_rows helper called by both eval passes with parameterised eval_kind tag (D-79-04)"
  - "No new CLI flags; existing --db, --user-id, --dry-run, --limit carry over (D-79-05)"
  - "Sequence[Any] used for rows parameter (list invariance would reject SQLAlchemy result sequences)"
  - "rows parameter uses Sequence[Any] not list[Any] — SQLAlchemy execute().all() returns Sequence[Row[...]]"
  - "# ty: ignore[unresolved-attribute] on result.rowcount — ty sees Result[Any] not CursorResult, but rowcount is valid on DML execute results"

metrics:
  duration: "4 minutes"
  completed: "2026-05-02"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 1
---

# Phase 79 Plan 03: Backfill script extension (phase column + middlegame eval) Summary

Extended `scripts/backfill_eval.py` with a chunked SQL CASE UPDATE phase-column pass and a middlegame entry eval pass sharing a common `_evaluate_and_write_rows` helper, completing the three-pass backfill driver needed for the combined Phase 78+79 operator runbook.

## What Was Built

### Task 1: Phase-column UPDATE pass (PHASE-FILL-01)

**New imports:**
- `ENDGAME_PIECE_COUNT_THRESHOLD` from `app.repositories.endgame_repository`
- `MIDGAME_MAJORS_AND_MINORS_THRESHOLD`, `MIDGAME_MIXEDNESS_THRESHOLD` from `app.services.position_classifier`
- `Any`, `Literal`, `Sequence` from `typing`

**New module-level constant:**
```python
PHASE_BACKFILL_CHUNK_SIZE = 10_000
```

**Phase-column UPDATE pass structure (inserted first in run_backfill):**
```sql
UPDATE game_positions
SET phase = CASE
    WHEN piece_count <= 6  THEN 2
    WHEN (piece_count <= 10
          OR backrank_sparse
          OR mixedness >= 10) THEN 1
    ELSE 0
END
WHERE phase IS NULL
  AND id BETWEEN :lo AND :hi
```
Threshold values (`6`, `10`, `10`) are interpolated from the Python constants via f-string, not hardcoded. Chunked by id range (chunk size 10 000), COMMIT per chunk, `WHERE phase IS NULL` resume predicate.

**Dry-run behavior:** Reports NULL-phase row count without running any UPDATE.

**No-op behavior:** When `hi_total == 0` (no NULL phase rows), logs "Phase-column backfill: zero rows with NULL phase (no-op)" and skips the chunk loop.

### Task 2: Middlegame entry eval pass + shared helper (PHASE-FILL-02)

**`_build_middlegame_entry_stmt` statement builder:**
```python
midgame_min = (
    select(GamePosition.game_id.label("gid"), func.min(GamePosition.ply).label("min_ply"))
    .where(GamePosition.phase == 1)
    .group_by(GamePosition.game_id)
    .subquery("midgame_min")
)
stmt = (
    select(GamePosition.id, GamePosition.game_id, GamePosition.ply, Game.pgn)
    .join(Game, Game.id == GamePosition.game_id)
    .join(midgame_min, (GamePosition.game_id == midgame_min.c.gid)
                       & (GamePosition.ply == midgame_min.c.min_ply))
    .where(GamePosition.eval_cp.is_(None), GamePosition.eval_mate.is_(None), GamePosition.phase == 1)
)
```
Returns the same `(id, game_id, ply, pgn)` shape as `_build_span_entry_stmt`. Supports `--user-id` and `--limit` filters.

**`_evaluate_and_write_rows` shared helper signature:**
```python
async def _evaluate_and_write_rows(
    rows: Sequence[Any],
    session: AsyncSession,
    *,
    db: str,
    eval_kind: Literal["endgame_span_entry", "middlegame_entry"],
) -> tuple[int, int, int]:
```
Returns `(evaluated_count, skipped_no_board, skipped_engine_err)`. Uses `EVAL_BATCH_SIZE` COMMIT-every-N pattern. Sentry context is bounded to `game_position_id`, `game_id`, `ply`, `db_target` (no pgn, fen, user_id per T-78-13/T-78-18).

**Final pass order inside run_backfill:**
1. Phase-column UPDATE pass (PHASE-FILL-01): chunked SQL CASE UPDATE, SQL-bound, no engine
2. Endgame span-entry eval pass (Phase 78): calls `_evaluate_and_write_rows` with `eval_kind="endgame_span_entry"`
3. Middlegame entry eval pass (PHASE-FILL-02): calls `_evaluate_and_write_rows` with `eval_kind="middlegame_entry"`

**Dry-run extension:** Now reports three counts before exiting without starting the engine:
- `--dry-run: would update N rows with NULL phase`
- `--dry-run: would evaluate M endgame span-entry rows`
- `--dry-run: would evaluate K middlegame entry rows`

**Engine lifecycle:** `start_engine()` / `stop_engine()` called once, wrapping both eval passes in a single `try/finally`. VACUUM ANALYZE runs after `stop_engine()`.

## PHASE_BACKFILL_CHUNK_SIZE rationale

Default of 10 000 is the D-79-01 "defensive default" for the chunked UPDATE:
- Prod has ~5M+ rows; a single large UPDATE would hold row locks for minutes
- 10 000 rows per chunk commits frequently, keeping lock contention low
- More overhead (500+ transactions) but each transaction is ~milliseconds
- Operator can tune up (50 000) on benchmark if EXPLAIN ANALYZE shows the overhead dominates

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Sequence[Any] instead of list[Any] for helper rows parameter**

- **Found during:** Task 2 — ty check after initial implementation
- **Issue:** SQLAlchemy `execute().all()` returns `Sequence[Row[...]]`, not `list[Any]`. ty rejected the call sites with `Expected list[Any], found Sequence[Row[...]]`.
- **Fix:** Changed `rows: list[Any]` to `rows: Sequence[Any]` in `_evaluate_and_write_rows` signature; added `Sequence` to the `typing` import.
- **Files modified:** `scripts/backfill_eval.py`

**2. [Rule 1 - Bug] ty: ignore needed for result.rowcount on CursorResult**

- **Found during:** Task 1 — ty check after phase-column UPDATE pass implementation
- **Issue:** ty resolves `execute()` return type as `Result[Any]` which does not expose `rowcount`. SQLAlchemy's DML `execute()` actually returns `CursorResult` which has `rowcount`, but ty's stub doesn't narrow the type.
- **Fix:** Added `# ty: ignore[unresolved-attribute]  # CursorResult from DML execute` comment at the `result.rowcount` call site.
- **Files modified:** `scripts/backfill_eval.py`

**3. [Rule 3 - Structural] Dry-run restructured to report all three counts before returning**

- **Found during:** Task 2 — designing the three-pass dry-run flow
- **Issue:** The original Task 1 dry-run returned early after counting endgame span rows, which would never reach the middlegame count. The plan's acceptance criteria requires all three counts reported in dry-run.
- **Fix:** Both count queries (endgame span + middlegame) are executed unconditionally before the dry-run exit. The engine is only started after the dry-run check confirms real work is needed.
- **Files modified:** `scripts/backfill_eval.py`
- **Commit:** 318aafc

## Known Stubs

None. All implementations are complete and functional.

## Threat Flags

None. This is a local operator script with no new network endpoints, auth paths, or trust boundaries.

## Self-Check: PASSED

- `scripts/backfill_eval.py` -- FOUND and modified
- Commits exist: `7b31d5c` (Task 1), `318aafc` (Task 2)
- `uv run ruff check scripts/backfill_eval.py` exits 0
- `uv run ty check scripts/backfill_eval.py` exits 0
- Acceptance criteria (Task 1): PHASE_BACKFILL_CHUNK_SIZE=1, position_classifier import=1, MIDGAME_MAJORS_AND_MINORS_THRESHOLD=2, MIDGAME_MIXEDNESS_THRESHOLD=2, WHERE phase IS NULL=4, Phase-column backfill=3
- Acceptance criteria (Task 2): _build_middlegame_entry_stmt=1, _evaluate_and_write_rows=1, "middlegame_entry"=2, "endgame_span_entry"=2, set_tag.*eval_kind=1, Middlegame entry eval=2, GamePosition.phase == 1=2, asyncio.gather=0
- Pass order confirmed: phase_update_sql -> _build_span_entry_stmt -> _build_middlegame_entry_stmt in run_backfill
- No new CLI flags in parse_args (still 4 arguments: --db, --user-id, --dry-run, --limit)
