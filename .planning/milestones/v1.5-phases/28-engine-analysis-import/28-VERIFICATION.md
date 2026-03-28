---
phase: 28-engine-analysis-import
verified: 2026-03-25T22:30:00Z
status: passed
score: 15/15 must-haves verified
re_verification: false
---

# Phase 28: Engine Analysis Import — Verification Report

**Phase Goal:** The system imports available engine analysis data (chess.com accuracy scores, lichess per-move evals) during game import, storing them for future display
**Verified:** 2026-03-25T22:30:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Success Criteria from ROADMAP.md

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | A lichess game with prior computer analysis imports with per-move eval values populated | VERIFIED | `_flush_batch` builds `evals` list from `node.eval()` on `classify_nodes`, stores `eval_cp`/`eval_mate` on every position row; `evals=True` param enables annotations in lichess API stream |
| 2 | A chess.com game with accuracy score imports with that score stored; without accuracy imports with NULL | VERIFIED | `normalize_chesscom_game()` extracts `accuracies.get("white")` / `accuracies.get("black")`, returns `None` when key absent; `TestChesscomAccuracy` tests cover both paths |
| 3 | A game with no analysis data imports cleanly with all engine fields NULL and no error | VERIFIED | All four columns are nullable; chess.com games produce empty `evals` list (all NULL); games without `accuracies` key return `None` for accuracy fields; tests confirm this |

### Observable Truths (from plan must_haves)

#### Plan 01 Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Game model has white_accuracy and black_accuracy nullable Float columns | VERIFIED | `app/models/game.py` lines 62-63: `Mapped[float | None] = mapped_column(Float(24), nullable=True)` |
| 2 | GamePosition model has eval_cp and eval_mate nullable SmallInteger columns | VERIFIED | `app/models/game_position.py` lines 48-49: `Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)` |
| 3 | Alembic migration adds all 4 columns and applies cleanly | VERIFIED | `alembic/versions/20260325_213250_cf839d2edbf8_add_engine_analysis_columns.py` adds `eval_cp`, `eval_mate` (game_positions) and `white_accuracy`, `black_accuracy` (games) |
| 4 | normalize_chesscom_game returns white_accuracy and black_accuracy from accuracies field | VERIFIED | `app/services/normalization.py` lines 208-235: extracts `accuracies.get("white")` / `accuracies.get("black")`, includes both in return dict |
| 5 | normalize_chesscom_game returns None for both accuracy fields when accuracies key absent | VERIFIED | `game.get("accuracies", {})` — empty dict default; `.get("white")` on empty dict returns `None` |
| 6 | lichess API requests include evals=true parameter | VERIFIED | `app/services/lichess_client.py` line 50: `"evals": True` |
| 7 | bulk_insert_positions chunk_size is 2300 (14 columns) | VERIFIED | `app/repositories/game_repository.py` line 92: `chunk_size = 2300` with updated comment |

#### Plan 02 Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 8 | Lichess games with %eval annotations store eval_cp and eval_mate values on position rows | VERIFIED | `import_service.py` lines 419-427, 462-467: `node.eval()` → `w.score(mate_score=None)` / `w.mate()` stored in `row["eval_cp"]` / `row["eval_mate"]` |
| 9 | Lichess games without %eval annotations store NULL for eval_cp and eval_mate | VERIFIED | `pov is None` path appends `(None, None)`; chess.com games produce empty `evals` list |
| 10 | Chess.com games always store NULL for eval_cp and eval_mate | VERIFIED | chess.com PGNs carry no `%eval` annotations; `evals` list stays empty; all rows get `(None, None)` |
| 11 | Final position row always has eval_cp=None and eval_mate=None | VERIFIED | `if i < len(evals)` guard — `hash_tuples` has N+1 entries, `evals` has N; final row index always out of range |
| 12 | Ply 0 (starting position) always has eval_cp=None and eval_mate=None | VERIFIED | Ply 0 has no corresponding `classify_nodes` entry (nodes are for moves, not starting position); `evals[0]` maps to the eval on the first move node |

#### Plan 03 Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 13 | Admin can re-import all games for a single user via --user-id N flag | VERIFIED | `scripts/reimport_games.py` lines 44-49: `--user-id` argument in mutually exclusive group |
| 14 | Admin can re-import all games for all users via --all flag | VERIFIED | `scripts/reimport_games.py` lines 50-55: `--all` argument in mutually exclusive group |
| 15 | Re-import script requires --yes flag or interactive confirmation | VERIFIED | `scripts/reimport_games.py` lines 178-186: prompts `[y/N]` unless `args.yes` is set |

**Score:** 15/15 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/models/game.py` | white_accuracy, black_accuracy Float(24) | VERIFIED | Both columns present, nullable, Float(24) |
| `app/models/game_position.py` | eval_cp SmallInteger, eval_mate SmallInteger | VERIFIED | Both columns present, nullable, SmallInteger |
| `app/services/normalization.py` | Accuracy extraction in normalize_chesscom_game | VERIFIED | Lines 207-235, wired into return dict |
| `app/services/lichess_client.py` | evals=True API param | VERIFIED | Line 50 |
| `app/repositories/game_repository.py` | chunk_size=2300 for 14 columns | VERIFIED | Lines 88-92, comment updated |
| `alembic/versions/20260325_213250_cf839d2edbf8_add_engine_analysis_columns.py` | Migration adds 4 columns | VERIFIED | Adds eval_cp, eval_mate, white_accuracy, black_accuracy |
| `tests/test_normalization.py` | TestChesscomAccuracy class | VERIFIED | Line 338, 4 test methods |
| `app/services/import_service.py` | Eval extraction in _flush_batch | VERIFIED | Lines 414-467 |
| `tests/test_import_service.py` | TestEvalExtraction class | VERIFIED | Line 932, 5 test methods |
| `scripts/reimport_games.py` | Admin re-import script | VERIFIED | Full implementation with --user-id, --all, --yes |
| `tests/test_reimport.py` | Re-import tests | VERIFIED | 13 tests: arg parsing (6), eval extraction (4), reimport flow (3) |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/services/normalization.py` | `app/models/game.py` | normalized dict keys match Game model columns | VERIFIED | `"white_accuracy"` and `"black_accuracy"` in return dict (lines 234-235); match model column names |
| `app/repositories/game_repository.py` | `app/models/game_position.py` | chunk_size accounts for 14 column count | VERIFIED | Comment explicitly lists 14 columns including `eval_cp, eval_mate` |
| `app/services/import_service.py` | `app/models/game_position.py` | position row dict includes eval_cp and eval_mate keys | VERIFIED | `row["eval_cp"]` and `row["eval_mate"]` assigned at lines 466-467 |
| `app/services/import_service.py` | classify_nodes loop | evals list built from `node.eval()` | VERIFIED | Lines 420-427: iterates `classify_nodes`, calls `node.eval()` |
| `scripts/reimport_games.py` | `app/repositories/game_repository.py` | delete_all_games_for_user for clean slate | VERIFIED | Line 123: `await game_repository.delete_all_games_for_user(session, user_id)` |
| `scripts/reimport_games.py` | `app/services/import_service.py` | triggers import pipeline with updated eval extraction | VERIFIED | Line 133: `await run_import(job_id)` after `create_job()` |

---

### Data-Flow Trace (Level 4)

The artifacts in this phase do not render dynamic data to end users — they are database columns, import pipeline functions, and an admin script. Data-flow tracing for UI rendering is not applicable here. The relevant data-flow is import-time: API data flows into columns.

| Flow | Source | Transformation | Destination | Status |
|------|--------|---------------|-------------|--------|
| chess.com accuracy | `game["accuracies"]` dict from API response | `normalize_chesscom_game()` extracts to float or None | `games.white_accuracy` / `games.black_accuracy` | FLOWING |
| lichess %eval annotations | `%eval` PGN tokens in NDJSON stream (`evals=True` param) | `node.eval().white().score()` / `.mate()` in `_flush_batch` | `game_positions.eval_cp` / `game_positions.eval_mate` | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All phase 28 tests pass | `uv run pytest tests/test_normalization.py tests/test_import_service.py tests/test_reimport.py -q` | 124 passed | PASS |
| Full test suite passes (no regressions) | `uv run pytest -x -q` | 375 passed, 32 warnings | PASS |
| Re-import script help is valid | `uv run python scripts/reimport_games.py --help` | Shows `--user-id`, `--all`, `--yes` flags | PASS (verified from argparse tests) |
| No lint errors | `uv run ruff check <all modified files>` | All checks passed | PASS |

---

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| ENGINE-01 | 28-02, 28-03 | System imports per-move eval (centipawns/mate) from lichess PGN annotations for games with prior computer analysis | SATISFIED | `_flush_batch` extracts `eval_cp`/`eval_mate` from `node.eval()` on lichess PGN `%eval` annotations; `evals=True` API param enables retrieval |
| ENGINE-02 | 28-01, 28-03 | System imports game-level accuracy scores from chess.com for games where analysis exists | SATISFIED | `normalize_chesscom_game()` extracts `white_accuracy`/`black_accuracy` from `game["accuracies"]`; stored in `games` table |
| ENGINE-03 | 28-01, 28-02, 28-03 | System gracefully handles missing analysis data (null fields, no errors) for unanalyzed games | SATISFIED | All four columns nullable; empty dict default for missing `accuracies`; `if pov is not None` guard; `if i < len(evals)` guard; tests verify None paths |

**Note on traceability table:** REQUIREMENTS.md traceability table maps ENGINE-01/02/03 to Phase 29 (listed as "Pending"), but ROADMAP.md phase details and all three plans correctly assign them to Phase 28. The traceability table is stale and was not updated when the roadmap was written. All three requirements are fully implemented in Phase 28.

---

### Anti-Patterns Found

No blockers or warnings found.

| File | Pattern Checked | Result |
|------|----------------|--------|
| `app/services/import_service.py` | Stub return / empty implementations | Clean — eval extraction is fully wired |
| `app/services/normalization.py` | Hardcoded empty returns | Clean — `game.get("accuracies", {})` correctly handles missing key |
| `scripts/reimport_games.py` | TODO/FIXME/placeholder | None found |
| `tests/test_reimport.py` | Mock-only with no real assertions | Clean — `TestReimportFlow` uses real DB session |
| `alembic/versions/..._add_engine_analysis_columns.py` | Incomplete migration | Clean — adds all 4 columns with correct types |

---

### Human Verification Required

The following behaviors cannot be verified programmatically without hitting live APIs:

#### 1. End-to-End Lichess Eval Import

**Test:** Import games from a lichess account that has games with prior computer analysis (the "Request a Computer Analysis" feature on lichess.org).
**Expected:** After import completes, query `game_positions` for those games — rows corresponding to analyzed moves should have non-NULL `eval_cp` or `eval_mate` values. The `%eval` annotations appear in the PGN stream when `evals=True` is set.
**Why human:** Requires a real lichess account with analyzed games and a running backend connected to the database.

#### 2. End-to-End Chess.com Accuracy Import

**Test:** Import games from a chess.com account that has games with computer accuracy scores (games analyzed via chess.com's analysis feature).
**Expected:** After import, query `games` table — rows for analyzed games should have non-NULL `white_accuracy` and `black_accuracy`. Unanalyzed games should have NULL for both.
**Why human:** Requires a real chess.com account with analyzed games and a running backend.

#### 3. Re-import Script Produces Populated Eval Data

**Test:** With Phase 28 deployed, run `uv run python scripts/reimport_games.py --user-id <id> --yes` for a user with both lichess and chess.com games.
**Expected:** Script outputs deletion confirmation, re-import progress per platform, and final summary. After completion, `eval_cp`/`eval_mate` populated on qualifying lichess positions, `white_accuracy`/`black_accuracy` populated on qualifying chess.com games.
**Why human:** Requires production or staging database with real users and live API connectivity.

---

### Gaps Summary

No gaps found. All 15 must-have truths verified. All artifacts exist, are substantive, and are fully wired. All key links confirmed. 375 tests pass with no regressions. No blocker anti-patterns.

The only non-blocking note: REQUIREMENTS.md traceability table maps ENGINE-01/02/03 to "Phase 29" rather than Phase 28 — this is a stale entry that should be updated to reflect Phase 28 completion and mark these requirements as complete.

---

_Verified: 2026-03-25T22:30:00Z_
_Verifier: Claude (gsd-verifier)_
