---
phase: 106-games-surface-backend-mistake-filter-per-game-counts-stats-a
plan: 02
subsystem: backend
tags: [library, games-archive, mistake-filter, kernel-recall, chip-curation, pagination]
requires:
  - "library_repository.mistake_exists_subquery + apply_game_filters(mistake_severity, user_id) (106-01)"
  - "mistakes_service.count_game_severities + SeverityCounts (106-01)"
  - "mistakes_service.classify_game_mistakes + FlawRecord/FlawTag/GameNotAnalyzed (Phase 105)"
  - "mistakes_repository.fetch_game_positions_ordered (Phase 105)"
  - "endgame_repository.query_endgame_games (paginated-archive template)"
provides:
  - "schemas.library.GameMistakeCard + LibraryGamesResponse"
  - "library_repository.query_filtered_games(...) (paginated mistake-EXISTS archive)"
  - "library_service.get_library_games(...) (kernel re-call + chip curation)"
  - "library_service._curate_chips(flaws) (phase-* excluded, deduped, ordered)"
  - "GET /api/library/games (current_active_user gated)"
affects:
  - "106-03 (stats panel + analyzed denominator reuses query_filtered_games / kernel seam)"
  - "LIBG-01 frontend Games subtab card list (consumes this endpoint)"
tech-stack:
  added: []
  patterns:
    - "Paginated archive copied from endgame_repository (base subquery -> func.count -> order_by played_at desc nulls_last -> offset/limit)"
    - "Per-game Phase 105 kernel re-call, SEQUENTIAL on one AsyncSession (never asyncio.gather)"
    - "TypedDict union discrimination on the 'reason' key; ty narrows the else-branch automatically"
    - "FastAPI Query Literal constraint (mistake/blunder) for HTTP-boundary validation"
key-files:
  created:
    - app/schemas/library.py
    - app/services/library_service.py
    - app/routers/library.py
  modified:
    - app/repositories/library_repository.py
    - app/main.py
    - tests/test_library_repository.py
    - tests/services/test_library_service.py
decisions:
  - "D1 (locked) honored: counts + chips come from RE-CALLING the kernel per game (count_game_severities for B/M/I, classify_game_mistakes for the chip tag set) — no severity-math fork in the service."
  - "Severity Query param constrained to Literal['mistake','blunder'] at the route (T-106-02V) — inaccuracies are count-only, never a filter; invalid values rejected with 422 before the service."
  - "Chip ordering is an explicit _CHIP_ORDER tuple (the FlawTag subset minus phase-*), giving deterministic output independent of FlawRecord iteration order."
metrics:
  duration_minutes: 18
  completed: "2026-06-05"
  tasks: 2
  files_created: 3
  files_modified: 4
---

# Phase 106 Plan 02: Games-surface Backend — Games Archive Endpoint Summary

`GET /api/library/games`: a paginated, boolean-mistake-severity-filterable game archive (mirroring the endgame-archive shape) where each card carries its per-game B/M/I severity counts plus a curated/deduped tag-chip set — built by re-calling the Phase 105 kernel per game on the returned page only — and chess.com / unanalyzed-lichess games surface an explicit `no_engine_analysis` card state, never a false 0/0/0.

## What was built

### Task 1 — schemas + paginated mistake-EXISTS archive query
- `app/schemas/library.py` (NEW): `GameMistakeCard` mirrors `GameRecord`'s display fields (game_id, user_result, played_at, time_control_bucket, platform, platform_url, white/black username+rating, opening_name/eco, user_color, move_count, termination, time_control_str, result_fen) and adds `severity_counts: SeverityCounts | None`, `chips: list[FlawTag]`, `analysis_state: Literal["analyzed","no_engine_analysis"]`. No `*_hash` field (T-106-02HASH / V5). `LibraryGamesResponse` carries `games / matched_count / offset / limit`.
- `library_repository.query_filtered_games(session, user_id, *, time_control, platform, rated, opponent_type, from_date, to_date, mistake_severity, offset, limit, opponent_gap_min, opponent_gap_max) -> tuple[list[Game], int]`: copies the `query_endgame_games` archive shape but drops the endgame-span subquery — base select is `select(Game).where(Game.user_id == user_id)`, then `apply_game_filters(..., mistake_severity=..., user_id=...)`. `func.count()` over `base.subquery()` for `matched_count`; early `([], 0)` on zero; `order_by(played_at desc nulls_last).offset().limit()` for the page. The `user_id` is threaded into both the base WHERE and the EXISTS scope (T-106-02AC).
- Module-level `from app.repositories.query_utils import apply_game_filters` is safe: `query_utils` only lazy-imports `library_repository` inside the function body, so there is no top-level cycle.

### Task 2 — get_library_games service + router + /api mount
- `library_service.get_library_games(...)`: loads the filtered page via `query_filtered_games`, then per game (SEQUENTIALLY on the same `AsyncSession` — never `asyncio.gather`, CLAUDE.md §Critical Constraints) calls `fetch_game_positions_ordered` + `count_game_severities` + `classify_game_mistakes`. The per-game N+1 loop is capped by the route's `limit le 100` (RESEARCH Pitfall 4). The whole orchestration is wrapped in a single `try/except` that calls `sentry_sdk.set_context` + `capture_exception` before re-raising.
- `_build_card(...)`: discriminates `GameNotAnalyzed` on the `"reason"` key (ty narrows the else-branch automatically — no cast needed). Unanalyzed -> `severity_counts=None`, `chips=[]`, `analysis_state="no_engine_analysis"` (never 0/0/0). Analyzed -> counts from `count_game_severities`, chips from `_curate_chips`, `analysis_state="analyzed"`.
- `_curate_chips(flaws: list[FlawRecord]) -> list[FlawTag]`: collects tags across all FlawRecords, drops any `phase-*` tag, emits one chip per remaining type in the explicit `_CHIP_ORDER` tuple (deterministic). FlawRecords are already M+B-only so inaccuracy-level tags never appear.
- `app/routers/library.py` (NEW): `APIRouter(prefix="/library", tags=["library"])`, thin `@router.get("/games", response_model=LibraryGamesResponse)`. `severity: list[Literal["mistake","blunder"]] | None = Query(default=None)` forwarded as `mistake_severity`; `offset ge 0`, `limit ge 1 le 100`; `from_date>to_date -> 422`; `current_active_user` dependency.
- `app/main.py`: `from app.routers.library import router as library_router` + `app.include_router(library_router, prefix="/api")` after `admin_router`. Verified the route registers at `/api/library/games`.

## Deviations from Plan

### Auto-fixed / additive

**1. [Rule 3 - Blocking] `_curate_chips` re-typed from `list[dict]` to `list[FlawRecord]`**
- **Found during:** Task 2 (ty gate).
- **Issue:** The plan's sketch passed loosely-typed dicts; ty rejected `dict.get`/iteration on `object` values and the test's `list[dict[str, list[str]]]` argument.
- **Fix:** Typed `_curate_chips(flaws: list[FlawRecord])` and indexed `flaw["tags"]` directly (FlawRecord guarantees `tags: list[FlawTag]`). The test builds proper `FlawRecord`s via a `_make_flaw` helper. No `# ty: ignore` needed anywhere.
- **Files modified:** app/services/library_service.py, tests/services/test_library_service.py
- **Commit:** 7a987250

No architectural changes (Rule 4). No new packages. No DB column/table/migration/backfill — on-the-fly only.

## Verification
- `uv run pytest tests/test_library_repository.py tests/services/test_library_service.py` -> 16 passed, 2 skipped (the 2 skips are the 106-03 `analyzed_denominator` / `stats` placeholders).
- `uv run pytest tests/services/test_library_service.py -k "chips or no_engine_analysis" -x` -> 5 passed.
- `uv run pytest tests/test_library_repository.py -k "query_filtered_games"` (class match) -> passes (severity filter narrows, pagination/matched_count, empty -> ([],0)).
- `uv run pytest -n auto -x` -> 2313 passed, 12 skipped (no regressions; the pre-merge gate).
- `uv run ruff check app/ tests/`, `uv run ruff format --check app/ tests/`, `uv run ty check app/ tests/` -> all clean.
- Route registration: `app.routes` exposes `/api/library/games`.

## Known Stubs
None. The remaining skipped test classes (`TestAnalyzedDenominator` in the repo test, `TestMistakeStats` in the service test) are intentional 106-03 placeholders with explicit skip reasons, not stubbed runtime behavior.

## Threat Flags
None. All new surface is covered by the plan's threat register: route gated by `current_active_user`; `query_filtered_games` + `fetch_game_positions_ordered` both filter `user_id`; Query bounds + severity Literal + from/to 422 guard at the boundary; card exposes FEN/usernames only (no hashes).

## Acceptance Criteria
- [x] `GameMistakeCard` + `LibraryGamesResponse` in `app/schemas/library.py`; no hash field.
- [x] `query_filtered_games` mirrors the endgame archive shape, mistake-EXISTS filtered, user-scoped, returns Game objects + matched_count.
- [x] `get_library_games` re-calls the kernel per game (sequential, no gather); GameNotAnalyzed -> no_engine_analysis/None/[]; analyzed -> counts + curated chips.
- [x] `_curate_chips` drops phase-*, dedupes one-per-type, deterministic order.
- [x] `GET /api/library/games` mounted under /api, gated by current_active_user, severity constrained to mistake/blunder, from_date>to_date -> 422.
- [x] ruff/ty clean; targeted + full suite green.

## Self-Check: PASSED
- FOUND: app/schemas/library.py (class LibraryGamesResponse, class GameMistakeCard)
- FOUND: app/services/library_service.py (def get_library_games, def _curate_chips)
- FOUND: app/routers/library.py (prefix="/library", "/games")
- FOUND: library_repository.query_filtered_games
- FOUND: app/main.py (library_router mounted under /api -> /api/library/games)
- FOUND commit df459329 (feat 106-02 schemas + archive query)
- FOUND commit 7a987250 (feat 106-02 service + router + mount)
