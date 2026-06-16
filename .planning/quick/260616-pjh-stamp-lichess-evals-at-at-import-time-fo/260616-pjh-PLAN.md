---
phase: quick-260616-pjh
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/services/import_service.py
  - tests/test_import_service.py
  - CHANGELOG.md
autonomous: true
requirements: [QUICK-260616-pjh]
must_haves:
  truths:
    - "A freshly imported lichess game WITH lichess analysis (white_blunders set) gets lichess_evals_at populated at import time."
    - "A lichess game WITHOUT analysis (white_blunders NULL) keeps lichess_evals_at NULL."
    - "A chess.com game keeps lichess_evals_at NULL regardless of white_blunders."
    - "The stamp lands in the same batch transaction as the position inserts (atomic)."
    - "The stamp is idempotent — re-running over already-stamped games is a no-op."
  artifacts:
    - path: "app/services/import_service.py"
      provides: "Import-time lichess_evals_at stamp stage in _flush_batch"
      contains: "lichess_evals_at"
    - path: "tests/test_import_service.py"
      provides: "DB-backed regression test for the import-time stamp"
      contains: "lichess_evals_at"
  key_links:
    - from: "app/services/import_service.py::_flush_batch"
      to: "games.lichess_evals_at"
      via: "Table-level bulk UPDATE scoped to batch new_game_ids"
      pattern: "lichess_evals_at"
---

<objective>
Stamp `games.lichess_evals_at = NOW()` at import time for newly-imported lichess
games that arrived WITH lichess computer analysis (`white_blunders IS NOT NULL`).

Purpose: `lichess_evals_at` is currently only ever set by the one-time Phase 117
migration backfill. No live import path stamps it, so after a user delete+reimport,
lichess-analyzed games come back with `lichess_evals_at = NULL`, match
`needs_engine_full_evals`, and get wastefully re-analyzed by the Stockfish drain
(confirmed on prod: 5,152 of user 95's lichess games in this state). It also flips
`has_engine_full_evals` FALSE and corrupts the lichess-vs-engine provenance split.

Output: a new bulk-UPDATE stage in `_flush_batch` (adjacent to Stage 5c) plus a
DB-backed regression test, and a CHANGELOG bullet.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@.planning/notes/eval-completion-columns.md
@app/services/import_service.py
@tests/test_import_service.py

# Canonical condition this fix mirrors (one-time backfill, do NOT re-run it):
# alembic/versions/20260613_120000_phase_117_queue_pv.py lines 156-161:
#   UPDATE games SET lichess_evals_at = COALESCE(imported_at, NOW())
#   WHERE white_blunders IS NOT NULL AND lichess_evals_at IS NULL
#
# Fix site facts already confirmed by the planner:
# - The new stamp goes in `_flush_batch(session, batch, user_id)` (import_service.py
#   ~line 692), immediately AFTER the Stage 5c "covered" UPDATE (~lines 794-817) and
#   BEFORE the `return len(rows_result.new_game_ids)` at ~line 820.
# - Stage 5c pattern to mirror: Table-level `update(Game.__table__)` with a
#   `bindparam("b_id")` WHERE, `datetime.now(timezone.utc)` value, executemany over
#   the scoped game ids. (NOT ORM `update(Game)` — that raises "bulk synchronize ..."
#   on a real session; see test_orm_level_update_with_executemany_raises ~line 2920.)
# - `datetime`, `timezone`, `bindparam`, `update`, `Game` are already imported in
#   import_service.py (Stage 5/5c uses all of them).
# - Test harness to mirror: TestFlushBatchStage5RealDb (~line 2816) and its
#   `_seed_user_and_games` helper + the `db_session` rollback-scoped fixture +
#   `tests/conftest.ensure_test_user`.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Stamp lichess_evals_at in _flush_batch</name>
  <files>app/services/import_service.py</files>
  <action>
In `_flush_batch`, add a new bulk-UPDATE stage immediately after the Stage 5c
covered-games block (after the `_classify_and_insert_flaws(session, covered_ids)`
call, before `return len(rows_result.new_game_ids)`). Name it "Stage 5d" in a
comment that explains WHY (bug fix: provenance column was only ever set by the
Phase 117 backfill; reference quick 260616-pjh).

Implement as a single Table-level bulk UPDATE on `Game.__table__` mirroring the
Stage 5c pattern, scoped to the batch via `rows_result.new_game_ids`. The WHERE
clause must match exactly:
  id == bindparam("b_id")
  AND platform == 'lichess'
  AND white_blunders IS NOT NULL
  AND lichess_evals_at IS NULL
Set `.values(lichess_evals_at=now_ts)` where `now_ts = datetime.now(timezone.utc)`.
Execute with executemany params `[{"b_id": gid} for gid in rows_result.new_game_ids]`.

Notes:
- Use the constant column predicates (`platform == 'lichess'`, `white_blunders
  IS NOT NULL`, `lichess_evals_at IS NULL`) directly in the `.where(...)` chain on
  `Game.__table__.c.*`, combined with the `id == bindparam("b_id")` predicate — so
  a single invariant prepared statement is reused for the whole executemany (same
  compile-cache discipline as Stage 5: no per-batch SQL text variance).
- Guard with `if rows_result.new_game_ids:` so an empty batch issues no statement.
- Apply to ALL qualifying new games in the batch (keyed on platform +
  white_blunders), NOT only `covered_ids` — a lichess-analyzed game may still have
  pending entry plies and not be "covered".
- The `platform = 'lichess'` guard is intentional future-proofing: once engine-filled
  oracle counts blur the white_blunders signal, gating on platform keeps this
  import-time stamp correct (the freshly-imported game has not been engine-analyzed,
  so white_blunders can only be lichess-sourced).
- The `lichess_evals_at IS NULL` guard keeps it idempotent on any re-run.
- Do NOT add a `synchronize_session` kwarg or use the ORM `update(Game)` form — the
  Table-level form is required (see test_orm_level_update_with_executemany_raises).
- Caller still owns the commit (WR-05) — do NOT commit inside `_flush_batch`.
  </action>
  <verify>
    <automated>uv run ruff check app/services/import_service.py && uv run ty check app/services/import_service.py && uv run python -c "import ast; ast.parse(open('app/services/import_service.py').read())"</automated>
  </verify>
  <done>
Stage 5d bulk UPDATE present in `_flush_batch`, scoped to `rows_result.new_game_ids`,
WHERE platform='lichess' AND white_blunders IS NOT NULL AND lichess_evals_at IS NULL,
Table-level (Game.__table__) with bindparam("b_id") executemany, value
datetime.now(timezone.utc). ruff + ty clean. chess.com path and lichess-without-analysis
path are untouched (no stamp applied to them by construction of the WHERE clause).
  </done>
</task>

<task type="auto">
  <name>Task 2: DB-backed regression test for the import-time stamp</name>
  <files>tests/test_import_service.py</files>
  <action>
Add a new test class (e.g. `TestImportStampLichessEvalsAt`) near
`TestFlushBatchStage5RealDb`, using the rollback-scoped `db_session` fixture and
`tests/conftest.ensure_test_user`. Reuse the existing seeding style from
`_seed_user_and_games` (insert real `Game` rows directly).

Seed FOUR games under one test user, varying platform + white_blunders:
  (a) platform="lichess", white_blunders=3  (analyzed)        -> expect stamped
  (b) platform="lichess", white_blunders=None (not analyzed)  -> expect NULL
  (c) platform="chess.com", white_blunders=2 (defensive)      -> expect NULL
  (d) platform="lichess", white_blunders=0  (analyzed, zero blunders) -> expect stamped
All seeded with lichess_evals_at=None initially.

Drive the SAME UPDATE logic the production stage runs. Prefer to exercise the real
code path rather than re-deriving the SQL in the test:
  - If Task 1 extracted the stamp into a small helper (e.g.
    `_stamp_lichess_evals_at(session, new_game_ids)`), import and call it with the
    seeded ids, then `await db_session.flush()`.
  - Otherwise, replicate the exact Stage 5d statement inline in the test (same
    Table-level update + WHERE + bindparam executemany) so the test pins the
    behavior contract. (If you inline it, the assertions below still fully gate
    correctness.)

Then SELECT lichess_evals_at for all four games and assert:
  - (a) IS NOT NULL  and (d) IS NOT NULL
  - (b) IS NULL  and (c) IS NULL

Add a second test asserting idempotency: run the stamp twice over (a); capture the
first lichess_evals_at value, run again, assert the value is UNCHANGED (the
`lichess_evals_at IS NULL` guard prevents a re-stamp). Use a distinct user_id to
avoid cross-test contention.

Use distinct hardcoded user_ids in the 95xx range (consistent with existing tests:
9501, 9502) to avoid collisions — e.g. 9510 and 9511. Mark async tests with
`@pytest.mark.asyncio` per the module convention. Do NOT use SQLite or a real
import HTTP fetch — seed Game rows directly.
  </action>
  <verify>
    <automated>uv run pytest tests/test_import_service.py -k "StampLichessEvalsAt" -p no:cacheprovider -q</automated>
  </verify>
  <done>
New test class present and passing. Assertions cover: lichess+analyzed (incl.
white_blunders=0) stamped; lichess-without-analysis NULL; chess.com NULL; idempotent
re-run leaves the value unchanged. Tests use db_session + ensure_test_user, no SQLite.
  </done>
</task>

<task type="auto">
  <name>Task 3: CHANGELOG bullet + full local gate</name>
  <files>CHANGELOG.md</files>
  <action>
Add one bullet under `## [Unreleased]` in the `### Fixed` subsection (create the
subsection if absent, in the conventional order). Terse, user-facing tone:

  - Stop re-running Stockfish analysis on re-imported lichess games that already
    carry lichess computer analysis. Imports now record the lichess-analysis
    provenance (`lichess_evals_at`) at import time, so a delete+reimport no longer
    flags thousands of already-analyzed games for wasteful re-evaluation
    (quick 260616-pjh).

Then run the FULL local gate per CLAUDE.md and resolve any output before marking
done:
  - uv run ruff format app/ tests/
  - uv run ruff check app/ tests/ --fix
  - uv run ty check app/ tests/
  - uv run pytest -n auto -x

If ruff format/check modifies files, that is fine — they are part of this task's
output. The suite must be green.
  </action>
  <verify>
    <automated>uv run ruff format --check app/ tests/ && uv run ruff check app/ tests/ && uv run ty check app/ tests/ && uv run pytest -n auto -x -q</automated>
  </verify>
  <done>
CHANGELOG.md has the Fixed bullet referencing quick 260616-pjh. ruff format --check
clean, ruff check clean, ty check zero errors, full backend suite green under -n auto.
  </done>
</task>

</tasks>

<verification>
- `_flush_batch` issues a Table-level bulk UPDATE setting lichess_evals_at for
  lichess-analyzed new games in the batch, in the same transaction as position inserts.
- The WHERE clause restricts to platform='lichess' AND white_blunders IS NOT NULL
  AND lichess_evals_at IS NULL, so chess.com and unanalyzed lichess games are untouched.
- New DB-backed tests prove the three provenance outcomes + idempotency.
- ruff format/check, ty, and the full backend suite (`uv run pytest -n auto`) pass.
</verification>

<success_criteria>
- Re-imported lichess games that arrived with lichess analysis get lichess_evals_at
  set at import time (no longer NULL), so they no longer match needs_engine_full_evals.
- chess.com games and lichess games without analysis are behaviorally unchanged.
- No Alembic migration (column already exists; live-path write only).
- All CLAUDE.md gates green.
</success_criteria>

<output>
Create `.planning/quick/260616-pjh-stamp-lichess-evals-at-at-import-time-fo/260616-pjh-SUMMARY.md` when done.
</output>
