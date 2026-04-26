---
phase: 69
plan: 02
subsystem: ingestion
tags: [migration, schema, normalization, lichess, eval, benchmark]
requires:
  - "Alembic chain head 2af113f4790f (drop_llm_logs_flags)"
provides:
  - "games.eval_depth (SmallInteger nullable)"
  - "games.eval_source_version (String(50) nullable)"
  - "NormalizedGame.eval_depth + NormalizedGame.eval_source_version Pydantic fields"
  - "normalize_lichess_game tags eval_source_version='lichess-pgn'"
  - "tests/test_benchmark_ingest.py — Wave 0 test scaffold for Plans 04-06"
  - "Centipawn convention documented (signed-from-white-POV cp via python-chess)"
affects:
  - app/models/game.py
  - app/schemas/normalization.py
  - app/services/normalization.py
  - alembic/versions/
  - tests/test_benchmark_ingest.py
tech-stack:
  added: []
  patterns:
    - "TDD RED -> GREEN cycle for schema additions"
    - "Pydantic field defaults (None) absorb the chess.com NULL behavior — no chess.com normalizer change needed"
key-files:
  created:
    - tests/test_benchmark_ingest.py
    - alembic/versions/20260425_203423_b11018499e4f_add_eval_depth_eval_source_version_to_.py
  modified:
    - app/models/game.py
    - app/schemas/normalization.py
    - app/services/normalization.py
decisions:
  - "Stripped autogenerate drift (REAL->Float on *_accuracy/clock_seconds, llm_logs index DESC ordering) from migration; that pre-existing ORM/DB drift is tracked as deferred tech debt from v1.11."
  - "Adjusted plan's test code to call normalize_*_game with the actual signature (positional username + user_id=) instead of the plan's incorrect target_username= kwarg."
metrics:
  duration_min: 4
  tasks_completed: 3
  tasks_total: 3
  files_changed: 5
  completed: 2026-04-25
---

# Phase 69 Plan 02: eval columns + benchmark test scaffold Summary

JWT-style schema migration adding `eval_depth` (SmallInteger nullable) and `eval_source_version` (String(50) nullable) to the canonical `games` table, wired through SQLAlchemy ORM, Pydantic `NormalizedGame`, and `normalize_lichess_game` so every Lichess import unconditionally tags `eval_source_version='lichess-pgn'`. Bootstraps `tests/test_benchmark_ingest.py` as the Wave 0 unit test file; the centipawn convention (signed-from-white-POV cp via python-chess) is documented and verified.

## What Shipped

### Migration

`alembic/versions/20260425_203423_b11018499e4f_add_eval_depth_eval_source_version_to_.py`

- `down_revision = "2af113f4790f"`
- `upgrade()`: two `op.add_column` calls (eval_depth SmallInteger nullable, eval_source_version String(50) nullable)
- `downgrade()`: drops in reverse order
- Docstring documents the centipawn convention and the rationale for `eval_depth` being NULL for current Lichess imports
- Applied to dev DB; downgrade->upgrade roundtrip verified

### ORM and Schema

- `Game.eval_depth: Mapped[int | None]` (SmallInteger nullable)
- `Game.eval_source_version: Mapped[str | None]` (String(50) nullable)
- `NormalizedGame.eval_depth: int | None = None`
- `NormalizedGame.eval_source_version: str | None = None`

### Normalizer

- `normalize_lichess_game()` adds `eval_depth=None, eval_source_version="lichess-pgn"` to every constructed `NormalizedGame` (unconditional, regardless of `[%eval]` annotation presence in the PGN)
- `normalize_chesscom_game()` unchanged; Pydantic field defaults give NULL for both columns

### Tests (Wave 0 scaffold)

`tests/test_benchmark_ingest.py`:
- `test_centipawn_convention_signed_from_white` (passed immediately — verifies python-chess `[%eval 2.35] -> 235`, `[%eval -0.50] -> -50`, `[%eval #4] -> mate(4)`)
- `test_eval_columns_lichess_sets_constant` (RED -> GREEN once Task 02-02 shipped)
- `test_eval_columns_chesscom_leaves_null` (RED -> GREEN once Task 02-02 shipped)

All three tests pass.

## Verification

- `uv run pytest tests/test_benchmark_ingest.py -v` — 3 passed
- `uv run pytest tests/test_normalization.py` — 102 passed (no regressions)
- `uv run ty check app/ tests/` — All checks passed
- `uv run ruff check .` — All checks passed
- `uv run alembic upgrade head` against dev DB — clean
- `uv run alembic downgrade -1 && uv run alembic upgrade head` against dev DB — clean roundtrip
- `\d games` confirms both columns present with `smallint` and `character varying(50)` types, both nullable

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Plan's test snippet used wrong function signature**
- **Found during:** Task 02-01 (RED) — wrote tests
- **Issue:** Plan's test code called `normalize_lichess_game(game, target_username="alice")` and `normalize_chesscom_game(game, target_username="alice")`. Actual signatures are `normalize_lichess_game(game: dict, username: str, user_id: int)` and `normalize_chesscom_game(game: dict, username: str, user_id: int)` (verified in `app/services/normalization.py` and existing `tests/test_normalization.py`).
- **Fix:** Changed test calls to match actual signature: `normalize_lichess_game(game, "alice", user_id=1)` and `normalize_chesscom_game(game, "alice", user_id=1)`.
- **Files modified:** `tests/test_benchmark_ingest.py`
- **Commit:** 8898fc5

**2. [Rule 2 — Threat T-69-04] Stripped autogenerate drift from migration**
- **Found during:** Task 02-03 Step 1 — autogenerate output
- **Issue:** Autogenerate detected three pre-existing drifts in addition to the wanted column adds:
  - `REAL() -> Float(precision=24)` on `game_positions.clock_seconds`, `games.white_accuracy`, `games.black_accuracy`
  - `ix_llm_logs_*_created_at` index ordering (`created_at DESC` -> `created_at`)
  These are listed in `STATE.md` Deferred Items as v1.11-close tech debt; they belong in a separate cleanup migration, not this Phase 69 INGEST-06 migration. Per the plan's Step 1 instruction to "STOP and surface unexpected diff", I stripped them and kept only the two `op.add_column` calls. This satisfies threat T-69-04 (Tampering: scope-creep in autogenerate diff).
- **Fix:** Hand-rewrote the migration file with only the two `add_column` ops in `upgrade()` and the matching `drop_column`s in `downgrade()`.
- **Files modified:** `alembic/versions/20260425_203423_b11018499e4f_add_eval_depth_eval_source_version_to_.py`
- **Commit:** 46158d2

### Skipped Steps (Plan 01 Dependency)

**Task 02-03 Step 4 + Step 5 (benchmark DB application + roundtrip)** — Plan 01 has not yet shipped on this Wave 1 base (`docker-compose.benchmark.yml` and `bin/benchmark_db.sh` do not exist). The plan's `<action>` block explicitly states "ASSUMES Plan 01 has shipped and `bin/benchmark_db.sh start` was run". Plan 01 will pick up the migration automatically the first time `bin/benchmark_db.sh start` runs `alembic upgrade head`, which is the expected lifecycle (per the plan: "the same migration ran against both databases — INFRA-02 verified" is satisfied by the canonical Alembic chain, not by this plan needing to apply it manually). Recorded for the orchestrator's wave merge: dev-DB-only verification was performed; INFRA-02 uniformity is asserted by the canonical chain itself.

## Commits

| Task | Type     | Hash    | Message                                                                       |
| ---- | -------- | ------- | ----------------------------------------------------------------------------- |
| 02-01 | test    | 8898fc5 | test(69-02): add failing tests for eval columns + centipawn convention        |
| 02-02 | feat    | 2eb895b | feat(69-02): add eval_depth + eval_source_version through ORM, schema, normalization |
| 02-03 | feat    | 46158d2 | feat(69-02): add Alembic migration for eval_depth + eval_source_version       |

## Self-Check: PASSED

- FOUND: tests/test_benchmark_ingest.py
- FOUND: alembic/versions/20260425_203423_b11018499e4f_add_eval_depth_eval_source_version_to_.py
- FOUND: app/models/game.py contains `eval_depth: Mapped[int | None]`
- FOUND: app/schemas/normalization.py contains `eval_source_version: str | None = None`
- FOUND: app/services/normalization.py contains `eval_source_version="lichess-pgn"`
- FOUND: commit 8898fc5 (test RED)
- FOUND: commit 2eb895b (feat GREEN)
- FOUND: commit 46158d2 (migration)

## TDD Gate Compliance

- RED gate: 8898fc5 `test(69-02): add failing tests...`
- GREEN gate: 2eb895b `feat(69-02): add eval_depth + eval_source_version...`
- REFACTOR: not needed (the two adds are minimal)

Plan-level type was `auto` (not `tdd`), but Task 02-01 had `tdd="true"` and the RED/GREEN sequence is preserved in the commit history.
