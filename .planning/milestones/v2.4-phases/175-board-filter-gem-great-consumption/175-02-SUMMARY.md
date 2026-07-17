---
phase: 175-board-filter-gem-great-consumption
plan: 02
subsystem: api
tags: [pydantic, sqlalchemy, fastapi, gem-great, maia]

# Dependency graph
requires:
  - phase: 174-backend-maia-inference-best-move-storage-spike-gated
    provides: game_best_moves table + classify_best_move/GEM_MAIA_MAX_PROB/GREAT_MAIA_MAX_PROB constants
  - phase: 175-board-filter-gem-great-consumption
    provides: "175-01: best_move_tier_sql SQL twin + has_gem/has_great filter (FILT-01), establishing the classify_best_move-is-authoritative convention this plan mirrors on the board read path"
provides:
  - "EvalPoint.best_move_tier / EvalPoint.maia_prob — pre-classified gem/great fields on the eval-chart payload"
  - "fetch_page_best_moves(session, game_ids) -> dict[int, dict[int, GameBestMove]] — batched, no user_id scoping (IDOR-safe via caller scoping)"
  - "_build_eval_series(best_moves_by_ply=) — classifies stored rows via classify_best_move, threaded through _build_card/get_library_game/get_library_games"
affects: [175-03, 175-04, 175-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Batched per-page repository fetch mirroring fetch_page_eval_positions's shape (dict[int, dict[int, Row]], one query, .in_(game_ids), no user_id column)"
    - "Row-presence-is-not-a-marker: classify_best_move is always called on the raw floats, never inferred from row presence (Pitfall 3)"

key-files:
  created: []
  modified:
    - app/schemas/library.py
    - app/repositories/library_repository.py
    - app/services/library_service.py
    - tests/services/test_library_service.py
    - tests/test_library_router.py

key-decisions:
  - "Test method names for both the -k eval_series service tests and the router round-trip test were given an explicit eval_series substring prefix so the plan's own -k eval_series verify selector actually picks them up — same lesson 175-01 already documented for pytest -k's literal substring match against node ids."
  - "fetch_page_best_moves is scoped to analyzed_game_ids in get_library_games (mirroring page_positions' scoping) since unanalyzed games have no eval_series to attach a tier to; get_library_game always fetches for the single already-IDOR-checked game_id."

patterns-established:
  - "TDD-mutation self-check: after GREEN, temporarily replaced the `if tier != \"neither\"` guard with `if True` and reran the Pitfall-3 test — it failed with a Pydantic ValidationError (EvalPoint.best_move_tier rejects the literal \"neither\"), proving the guard is load-bearing rather than decorative, before reverting."

requirements-completed: [BOARD-01]

coverage:
  - id: D1
    description: "EvalPoint gains best_move_tier (Literal['gem','great']|None) and maia_prob (float|None); populated only from classify_best_move's output, never inferred from row presence (Pitfall 3), and maia_prob only alongside a non-null tier (Pitfall 5)"
    requirement: "BOARD-01"
    verification:
      - kind: unit
        ref: "tests/services/test_library_service.py::TestBestMoveTierAssembly (6 tests: gem, great, narrow-margin-null, neither-row-null-maia_prob, no-row-null, backward-compat default)"
        status: pass
      - kind: integration
        ref: "tests/test_library_router.py::TestEvalPointBestMoveTierRoundTrip::test_eval_series_gem_tier_and_maia_prob_serialize_no_hash_leak"
        status: pass
    human_judgment: false
  - id: D2
    description: "fetch_page_best_moves batch-loads game_best_moves rows in one query per page, grouped by (game_id, ply), threaded through get_library_game/get_library_games at the same call sites as fetch_page_eval_positions (no N+1, no unscoped game_ids)"
    requirement: "BOARD-01"
    verification:
      - kind: unit
        ref: "uv run ty check app/schemas/library.py app/repositories/library_repository.py (clean) + grep confirms async def fetch_page_best_moves exists exactly once"
        status: pass
      - kind: integration
        ref: "tests/test_library_router.py::TestEvalPointBestMoveTierRoundTrip (real ASGI client against real Postgres, exercising the full get_library_game batch-fetch path)"
        status: pass
    human_judgment: false

# Metrics
duration: 25min
completed: 2026-07-16
status: complete
---

# Phase 175 Plan 02: EvalPoint Gem/Great Backend Read Path Summary

**EvalPoint gains a pre-classified `best_move_tier`/`maia_prob` computed server-side from batched `game_best_moves` rows via the authoritative `classify_best_move` — the board never does its own cp/margin math for an analyzed game's stored mainline.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-07-16T20:33:19Z (approx, session start per STATE.md)
- **Completed:** 2026-07-16T20:58:59Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- `EvalPoint.best_move_tier: Literal["gem","great"] | None` and `EvalPoint.maia_prob: float | None` added to `app/schemas/library.py` — null when no candidate row exists OR the row classifies "neither" (D-03).
- `fetch_page_best_moves(session, game_ids) -> dict[int, dict[int, GameBestMove]]` added to `library_repository.py`, cloning `fetch_page_eval_positions`'s exact batching shape: one query, `.in_(game_ids)`, grouped `{gid: {ply: row}}`. Docstring codifies the no-user_id/IDOR-safe-by-caller contract (mirrors T-175-04's mitigation from Plan 01).
- `_build_eval_series` gained a `best_moves_by_ply` parameter: for each position, looks up the stored row (if any) and calls `classify_best_move(maia_prob, best_cp, best_mate, second_cp, second_mate, mover_color_for_ply(ply))` — **always** on the raw floats, never inferring the tier from row presence (Pitfall 3). When the tier is not `"neither"`, sets both `best_move_tier` and `maia_prob`; otherwise both stay null (Pitfall 5).
- `_build_card` threads `best_moves_by_ply` into `_build_eval_series`; both `get_library_game` and `get_library_games` batch-fetch `fetch_page_best_moves` at the same call sites they already call `fetch_page_eval_positions` (single-game: the already-IDOR-checked `[game_id]`; list: `analyzed_game_ids`, mirroring `page_positions`' scoping since unanalyzed games have no eval_series to attach a tier to).
- Verified the `if tier != "neither"` guard is load-bearing (not decorative) by temporarily replacing it with `if True` and confirming the Pitfall-3 narrow-margin test fails (Pydantic rejects the literal `"neither"` on `best_move_tier`), then reverting.

## Task Commits

Each task was committed atomically:

1. **Task 1: EvalPoint schema fields + batched game_best_moves fetch** - `d047d7f1` (feat)
2. **Task 2a: RED — failing tests for gem/great tier assembly** - `46671159` (test)
2. **Task 2b: GREEN — classify tier from stored rows in eval_series** - `b4245722` (feat)

## Files Created/Modified
- `app/schemas/library.py` - `EvalPoint.best_move_tier` / `EvalPoint.maia_prob`
- `app/repositories/library_repository.py` - `fetch_page_best_moves` batched fetch
- `app/services/library_service.py` - `_build_eval_series`/`_build_card` classification assembly, `get_library_game`/`get_library_games` call-site threading
- `tests/services/test_library_service.py` - `TestBestMoveTierAssembly` (6 pure in-memory unit tests, no DB)
- `tests/test_library_router.py` - `TestEvalPointBestMoveTierRoundTrip` (HTTP round-trip + no-hash-leak integration test)

## Decisions Made
- Renamed the new test methods (service unit tests + router round-trip test) with an explicit `eval_series` substring so the plan's own `-k eval_series` verify selector actually matches them — `pytest -k` does a literal substring match against node ids, and neither `TestBestMoveTierAssembly` nor `TestEvalPointBestMoveTierRoundTrip` contains that substring on their own (same lesson 175-01 already recorded).
- `fetch_page_best_moves` in `get_library_games` is scoped to `analyzed_game_ids` (not the full page), matching `page_positions`'s existing scoping — an unanalyzed game has no `eval_series` to attach a tier to, so fetching its best-move rows would be wasted work.

## Deviations from Plan

None - plan executed exactly as written. Test-naming adjustment (adding the `eval_series` substring) is a test-authoring detail to satisfy the plan's own verify command, not a behavior or scope change.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- BOARD-01 backend is fully delivered: `GET /api/library/games/{id}` and `GET /api/library/games` both return `eval_series[].best_move_tier`/`maia_prob` pre-classified server-side, with row-absence deterministically null (no live engine call needed for an analyzed game's mainline — the structural basis for BOARD-02's no-sweep-delay guarantee) and no N+1/IDOR exposure.
- The board frontend consumption of `best_move_tier`/`maia_prob` (retiring `useGemSweep.ts` or demoting it to a free-play fallback) and the Library filter UI toggles (consuming Plan 01's `has_gem`/`has_great` query params) remain for subsequent 175-series plans.

---
*Phase: 175-board-filter-gem-great-consumption*
*Completed: 2026-07-16*

## Self-Check: PASSED

All 5 modified source/test files confirmed present on disk; all 4 commits
(`d047d7f1`, `46671159`, `b4245722`, `6ab0612a`) confirmed in git history.
