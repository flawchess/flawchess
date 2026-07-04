---
phase: 149-retire-prune
plan: 04
subsystem: backend
tags: [zobrist, chesscom-to-lichess, eval-jobs, eval-queue, dead-code-removal]

# Dependency graph
requires:
  - phase: 149-01
    provides: Phase 149 requirements/scope for PRUNE-01..06 dead-weight retirement
provides:
  - Caller-less hashes_for_game wrapper removed from zobrist.py (process_game_pgn is now the sole PGN-walk implementation)
  - Dead Table-3 (LICHESS_BLITZ_INTRA_TC) lookup surface removed from chesscom_to_lichess.py; Tables 1/2 and canonical_slice_sql.py's import path untouched
  - Caller-less Game.needs_engine_full_evals hybrid property + inplace expression removed; ix_games partial index and raw predicates kept
  - Unused TIER_AUTO_WINDOW constant removed; eval_jobs.tier column and tier-agnostic claim SQL kept
affects: [150-consolidate-write-path]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - app/services/zobrist.py
    - app/services/chesscom_to_lichess.py
    - app/models/game.py
    - app/models/eval_jobs.py
    - app/services/eval_queue_service.py
    - app/services/eval_drain.py
    - app/services/import_service.py
    - tests/test_zobrist.py
    - tests/test_seed_openings.py
    - tests/services/test_chesscom_to_lichess.py
    - tests/test_import_service.py

key-decisions:
  - "hashes_for_game deleted outright (not deprecated) — zero production callers confirmed via repo-wide grep before deletion"
  - "Only Table 3 (LICHESS_BLITZ_INTRA_TC) + its 2 lookup functions deleted from chesscom_to_lichess.py; Tables 1/2 and their lookups stay because canonical_slice_sql.py imports them live"
  - "needs_engine_full_evals hybrid property deleted but the DB partial index (ix_games_needs_engine_full_evals) and raw full_evals_completed_at IS NULL predicates are untouched — comments that named the deleted property were rewritten to reference the raw predicate instead, per CLAUDE.md's 'no comment naming a deleted symbol' convention"
  - "TIER_AUTO_WINDOW constant deleted; eval_jobs.tier column and the tier-agnostic ORDER BY tier ASC claim SQL kept exactly as-is (RESEARCH Pitfall 2: no deletable tier-2 code branch ever existed, only the unused constant + speculative docstring narrative)"

patterns-established: []

requirements-completed: [PRUNE-02]

coverage:
  - id: D1
    description: "hashes_for_game removed; seed-opening hash-equivalence assertion rewritten to use process_game_pgn and still passes"
    requirement: "PRUNE-02"
    verification:
      - kind: unit
        ref: "tests/test_zobrist.py, tests/test_seed_openings.py::TestPgnToFenPlyHashes::test_hashes_match_import_pipeline"
        status: pass
    human_judgment: false
  - id: D2
    description: "Dead Table-3 lookup surface removed from chesscom_to_lichess.py; live Tables 1/2 conversion path (canonical_slice_sql.py) still resolves and passes"
    requirement: "PRUNE-02"
    verification:
      - kind: unit
        ref: "tests/services/test_chesscom_to_lichess.py"
        status: pass
      - kind: integration
        ref: "tests/test_import_service.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "Caller-less Game.needs_engine_full_evals hybrid property removed with zero live-query impact"
    requirement: "PRUNE-02"
    verification:
      - kind: unit
        ref: "uv run ty check app/ tests/ (zero errors)"
        status: pass
      - kind: integration
        ref: "uv run pytest -n auto -x (full suite)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Unused TIER_AUTO_WINDOW constant removed; eval_jobs.tier column and tier-agnostic claim SQL preserved"
    requirement: "PRUNE-02"
    verification:
      - kind: integration
        ref: "uv run pytest -n auto -x (full suite, includes eval_queue_service tests)"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-04
status: complete
---

# Phase 149 Plan 04: Retire & Prune — Dead Weight Removal Summary

**Removed four genuinely-dead code items (hashes_for_game, Table-3 chesscom_to_lichess lookups, needs_engine_full_evals hybrid, TIER_AUTO_WINDOW constant) with zero live-path behavior change; full backend suite green (3158 passed).**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-07-04
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments
- Deleted the caller-less `hashes_for_game` wrapper from `zobrist.py` (superseded by `process_game_pgn`), removed its 17 dedicated tests + the now-redundant equivalence test, and rewrote `test_seed_openings.py`'s hash-equivalence assertion to prove the same invariant via `process_game_pgn` directly.
- Removed only the dead Table-3 (`LICHESS_BLITZ_INTRA_TC`) lookup surface from `chesscom_to_lichess.py` — confirmed Tables 1/2 and `canonical_slice_sql.py`'s live rating-conversion import path are untouched and still resolve.
- Removed the caller-less `Game.needs_engine_full_evals` hybrid property and its inplace expression from `game.py`, while keeping the `ix_games_needs_engine_full_evals` partial index and the raw `full_evals_completed_at IS NULL AND lichess_evals_at IS NULL` predicate used directly by live queries.
- Removed the unused `TIER_AUTO_WINDOW` constant from `eval_jobs.py` and trimmed the speculative "future per-user mode" narrative from its docstring and `eval_queue_service.py`'s module docstring, while keeping the `eval_jobs.tier` DB column and its tier-agnostic `ORDER BY tier ASC` claim SQL exactly as-is (RESEARCH Pitfall 2 confirmed there was never a deletable `if tier == 2` branch).

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove hashes_for_game and rewrite the seed-opening equivalence test** - `a350b81e` (refactor)
2. **Task 2: Trim dead Table-3 lookups, needs_engine_full_evals, and TIER_AUTO_WINDOW** - `60bf73aa` (refactor)

_Note: no test-first (TDD) tasks in this plan — pure deletion/refactor work._

## Files Created/Modified
- `app/services/zobrist.py` - Deleted `hashes_for_game`
- `tests/test_zobrist.py` - Deleted 17 `hashes_for_game`-specific tests + 1 equivalence test; removed the import
- `tests/test_seed_openings.py` - Rewrote the hash-equivalence assertion to call `process_game_pgn` directly
- `app/services/chesscom_to_lichess.py` - Deleted `LICHESS_BLITZ_INTRA_TC`, `_LICHESS_BLITZ_KEYS`, `LichessIntraTC`, `lookup_uscf_from_lichess_blitz`, `lookup_fide_from_lichess_blitz`; trimmed module docstring; updated a docstring example in `_interp_int_column` that named the deleted table
- `tests/services/test_chesscom_to_lichess.py` - Deleted Table-3-only tests/imports; updated module docstring
- `app/models/game.py` - Deleted `needs_engine_full_evals` hybrid property + `_needs_engine_full_evals_expression`; updated the adjacent index comment to reference the raw predicate
- `app/models/eval_jobs.py` - Deleted `TIER_AUTO_WINDOW`; trimmed tier-2 narrative in the module comment and class docstring
- `app/services/eval_queue_service.py` - Trimmed the tier-2 "future mode" narrative in the module docstring; updated two comments that named the deleted `Game.needs_engine_full_evals` property to reference the raw predicate
- `app/services/eval_drain.py` - Updated a comment naming the deleted property to reference the raw predicate
- `app/services/import_service.py` - Updated a docstring naming the deleted property to reference the raw predicate
- `tests/test_import_service.py` - Updated a test-class docstring naming the deleted property

## Decisions Made
- `hashes_for_game` deleted outright (zero production callers confirmed via repo-wide grep of `app/` and `scripts/` before deletion).
- Only Table 3 of `chesscom_to_lichess.py` deleted; Tables 1/2 (`CHESSCOM_INTRA_TC`, `CHESSCOM_BLITZ_TO_LICHESS`) and their consumers (`convert_chesscom_to_lichess`, `composed_chesscom_to_lichess_grid`, `canonical_slice_sql.py`) are load-bearing and untouched.
- `needs_engine_full_evals` hybrid property deleted, but the backing partial index and raw predicate are database-level artifacts independent of the Python property — kept per the plan's explicit prohibition.
- `TIER_AUTO_WINDOW` deleted per RESEARCH Pitfall 2's recommendation (option (a): minimal deletion of the dead constant + narrative trim), since it satisfies the letter of PRUNE-02/R12 with near-zero risk (zero callers) while Phase 150 will touch `eval_queue_service.py` again anyway.

## Deviations from Plan

None — plan executed exactly as written. All four deletion targets were confirmed zero-caller before removal via grep, matching RESEARCH's pre-verified line numbers and scope corrections.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 149 Plan 05 (or whatever plan handles PRUNE-01/03/04/05/06) is unaffected by this plan's scope — no shared files touched beyond `eval_jobs.py`/`eval_queue_service.py`, which Phase 150 (Consolidate Write Path) will revisit for the broader write-path unification.
- Full backend suite green (3158 passed, 18 skipped); `uv run ty check app/ tests/` zero errors; `uv run ruff format`/`check` clean.
- No blockers.

---
*Phase: 149-retire-prune*
*Completed: 2026-07-04*

## Self-Check: PASSED

All modified files confirmed present on disk; both task commits (`a350b81e`, `60bf73aa`) confirmed in git log.
