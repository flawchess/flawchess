---
phase: 108-flaws-subtab-game-flaws-materialization-per-flaw-endpoint-cr
plan: "05"
subsystem: backend
tags: [library, game_flaws, endpoint, IDOR, pagination, D-05, D-07, D-08, SEED-038]
dependency_graph:
  requires:
    - phase: 108-03
      provides: "build_flaw_filter_clauses — shared predicate builder (OR within / AND across families)"
    - phase: 108-04
      provides: "library_repository: inverse encoding maps (_SEVERITY_INT_TO_TAG, _TEMPO_INT_TO_TAG, _PHASE_INT_TO_TAG)"
  provides:
    - "app/schemas/library.py: FlawListItem + LibraryFlawsResponse"
    - "app/repositories/library_repository.py: query_flaws + _reconstruct_tags"
    - "app/services/library_service.py: get_library_flaws"
    - "app/routers/library.py: GET /library/flaws + FlawTagFilter"
    - "tests/test_library_router.py: 13-test suite (ordering, pagination, filter, IDOR, rejection)"
  affects:
    - "Plans 108-06..08 — frontend can now query GET /library/flaws for the Flaws subtab"
tech_stack:
  added: []
  patterns:
    - "query_flaws: SELECT GameFlaw JOIN Game, user-scoped, shared build_flaw_filter_clauses, played_at DESC + ply ASC"
    - "_reconstruct_tags: typed boolean/int columns → FlawTag list in canonical order (phase tags excluded)"
    - "FlawTagFilter Literal: 7 non-phase tags only; FastAPI 422-rejects phase tags at HTTP boundary"
    - "get_library_flaws: defaults severity to M+B when empty; Sentry capture on exception"
    - "flaws_test_state: module-scoped async fixture committing via test_engine (ASGI client visibility)"
key_files:
  created: []
  modified:
    - app/schemas/library.py
    - app/repositories/library_repository.py
    - app/services/library_service.py
    - app/routers/library.py
    - tests/test_library_router.py
key-decisions:
  - "MIN-threshold severity semantics preserved from build_flaw_filter_clauses (consistent with Games EXISTS); ?severity=mistake means severity >= 1 (mistake + blunder)"
  - "game-metadata filter applied via game_id IN (SELECT id FROM games WHERE ...) subquery approach — avoids applying apply_game_filters to a GameFlaw-based select"
  - "FlawTagFilter excludes phase tags at HTTP boundary (FastAPI 422) so build_flaw_filter_clauses never receives them"
  - "Tags reconstructed from typed columns in canonical order: miss, lucky-escape, while-ahead, result-changing, tempo (phase tags excluded)"
requirements-completed: [D-05, D-07, D-08, D-03]
duration: 10min
completed: "2026-06-06"
tasks_completed: 3
tasks_total: 3
files_created: 0
files_modified: 5
---

# Phase 108 Plan 05: Per-Flaw List Endpoint (GET /library/flaws) Summary

**FlawListItem schema + LibraryFlawsResponse + query_flaws repository (shared predicate, recent-first, paginated, user-scoped) + GET /library/flaws route + 13-test suite proving ordering, pagination, filtering, IDOR isolation, and phase-tag rejection**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-06-06T16:36:33Z
- **Completed:** 2026-06-06T16:47:13Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- Added `FlawListItem(BaseModel)` to `app/schemas/library.py` — full miniboard display payload: `game_id`, `ply`, `fen`, `move_san`, `severity` (FlawSeverity), `tags` (list[FlawTag]), `es_before`, `es_after`, plus game metadata (`user_result` Literal["win","draw","loss"], `played_at`, `time_control_bucket`, `platform`, `platform_url`, `white_username`, `black_username`, `user_color`). No `*_hash` fields (CLAUDE.md V5).
- Added `LibraryFlawsResponse(BaseModel)` — mirrors `LibraryGamesResponse` pagination shape (`flaws / matched_count / offset / limit`).
- Added `_reconstruct_tags(flaw: GameFlaw) -> list[FlawTag]` — reads typed boolean (`is_miss`, `is_lucky_escape`, `is_while_ahead`, `is_result_changing`) and integer (`tempo`) columns in deterministic canonical order; phase tags excluded (display-only per UI-SPEC).
- Added `query_flaws()` to `library_repository.py` — `SELECT GameFlaw, Game JOIN games WHERE user_id == user_id AND *build_flaw_filter_clauses(severity, tags)`, game-metadata filters applied via `game_id IN (filtered_game_ids)` subquery, ordered `played_at DESC NULLS LAST, ply ASC` (D-07), paginated; returns `(list[FlawListItem], matched_count)`.
- Added `get_library_flaws()` to `library_service.py` — defaults severity to `["mistake","blunder"]` when empty (D-08); Sentry capture on exception; thin delegation to `query_flaws`.
- Added `FlawTagFilter = Literal[7 non-phase tags]` to `app/routers/library.py` — phase tags excluded so FastAPI rejects them with 422 (T-108-11).
- Added `GET /library/flaws` route — `current_active_user` dep (IDOR-safe), relative path, `SeverityFilter` + `FlawTagFilter` Query params, `offset ge=0`, `limit ge=1 le=100` default 20 (D-08/T-108-12); thin HTTP layer.
- Extended `tests/test_library_router.py` with 13 new tests in `TestGetLibraryFlaws`:
  - `test_returns_401_without_auth` — baseline auth requirement
  - `test_returns_200_with_auth` — structure check (flaws/matched_count/offset/limit)
  - `test_default_limit_is_20` — D-08 page size
  - `test_ordering_recent_first_then_ply_asc` — 3-game fixture asserts exact (game_id, ply) order (D-07)
  - `test_pagination_offset_returns_next_rows` — no overlap, consistent matched_count
  - `test_severity_filter_blunder_only` — ?severity=blunder returns only blunders
  - `test_severity_filter_mistake_returns_mb` — MIN-threshold: ?severity=mistake matches M+B
  - `test_tag_filter_result_changing` — ?tag=result-changing returns only is_result_changing rows
  - `test_flaw_list_item_fields` — all required fields present; no `*_hash` leakage
  - `test_idor_user_a_cannot_see_user_b_flaws` — IDOR gate: user B's game_b1 flaw never appears for user A (T-108-10)
  - `test_phase_tag_in_query_rejected_422` — opening/middlegame/endgame in ?tag= → 422 (T-108-11)
  - `test_invalid_severity_rejected_422` — inaccuracy/unknown in ?severity= → 422 (T-108-11)
  - `test_limit_bounds_enforced` — limit=0/101/-1 → 422 (T-108-12)
  - `test_tags_reconstructed_in_flaw_item` — 'miss' and 'low-clock' appear in tags list

## Task Commits

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | FlawListItem + LibraryFlawsResponse schemas + query_flaws repository | f8c6bf9e | app/schemas/library.py, app/repositories/library_repository.py |
| 2 | get_library_flaws service + GET /library/flaws route | 366bab9d | app/services/library_service.py, app/routers/library.py |
| 3 | Endpoint pagination + filter + IDOR test | b2415b66 | tests/test_library_router.py |

## Files Created/Modified

- `app/schemas/library.py` — added `FlawListItem` + `LibraryFlawsResponse` (with updated module docstring)
- `app/repositories/library_repository.py` — added `FlawListItem` + `derive_user_result` imports; added `_reconstruct_tags()` helper; added `query_flaws()` paginated SELECT function
- `app/services/library_service.py` — added `LibraryFlawsResponse` import; added `_DEFAULT_SEVERITY` constant; added `get_library_flaws()` service function
- `app/routers/library.py` — updated module docstring; added `LibraryFlawsResponse` import; added `FlawTagFilter` Literal; added `GET /library/flaws` route
- `tests/test_library_router.py` — added imports (`datetime`, `async_sessionmaker`); added seeding helpers (`_register_and_login`, `_seed_game_committed`, `_seed_flaw_committed`); added `flaws_test_state` module-scoped fixture; added `TestGetLibraryFlaws` with 13 tests

## Decisions Made

- MIN-threshold severity semantics preserved from `build_flaw_filter_clauses` — `?severity=mistake` means `severity >= 1` (matches mistakes AND blunders), consistent with the shared predicate design (SEED-038). The test documents this explicitly. Users wanting only mistakes would not normally filter by severity alone on the Flaws endpoint.
- Game-metadata filter in `query_flaws` applied via `GameFlaw.game_id.in_(game_filter_stmt)` subquery (not by adding game-filter columns to the SELECT) — this avoids SQLAlchemy join ambiguity when applying `apply_game_filters` to a `Select[tuple[GameFlaw, Game]]` statement.
- Phase tags excluded at both HTTP layer (FlawTagFilter Literal) and predicate layer (build_flaw_filter_clauses produces no clause for phase tags) — defense in depth for T-108-11.

## Deviations from Plan

**1. [Rule 1 - Bug] Fixed test: ?severity=mistake uses MIN-threshold (returns all M+B)**

- **Found during:** Task 3 — first test run
- **Issue:** Initial test asserted `?severity=mistake` returns only 2 mistake rows. Actual behavior: `build_flaw_filter_clauses(["mistake"], [])` computes threshold=1 → `GameFlaw.severity >= 1` → returns mistakes AND blunders (5 rows). This is correct MIN-threshold semantics, not a bug in the code.
- **Fix:** Rewrote `test_severity_filter_mistake_only` → `test_severity_filter_mistake_returns_mb` to assert the correct MIN-threshold semantics and document the design decision.
- **Files modified:** `tests/test_library_router.py`
- **Commit:** b2415b66

---

**Total deviations:** 1 test correction (no code bug — test expectation was misaligned with the shared predicate semantics).

## Known Stubs

None — all outputs are fully functional. The endpoint returns real data from `game_flaws`, uses the shared predicate builder, and is fully tested.

## Threat Flags

No new network endpoints beyond the documented `GET /library/flaws`. All T-108-10/11/12 mitigations implemented and verified:

| Flag | File | Description |
|------|------|-------------|
| (none — T-108-10 mitigated) | app/routers/library.py | user_id from `current_active_user` only; `query_flaws` WHERE includes `GameFlaw.user_id == user_id`; verified by IDOR test |
| (none — T-108-11 mitigated) | app/routers/library.py | FlawTagFilter excludes phase tags (FastAPI 422); severity/tag values flow through parameterized SQLAlchemy build_flaw_filter_clauses |
| (none — T-108-12 mitigated) | app/routers/library.py | limit ge=1 le=100, offset ge=0; verified by test_limit_bounds_enforced |

## Verification

```
uv run pytest tests/test_library_router.py -k flaws -x   → 13 passed (+ 7 existing = 20 total)
uv run pytest -n auto -x                                  → 2402 passed, 10 skipped
uv run ty check app/ tests/                               → All checks passed!
```

## Self-Check: PASSED
