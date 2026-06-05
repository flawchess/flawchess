---
phase: 106-games-surface-backend-mistake-filter-per-game-counts-stats-a
plan: 03
subsystem: backend
tags: [library, mistake-stats, analyzed-denominator, rolling-window-trend, kernel-recall, tag-distribution]
requires:
  - "library_repository._filtered_games_base / apply_game_filters(mistake_severity, user_id) (106-01/02)"
  - "mistakes_service.count_game_severities + SeverityCounts + EVAL_COVERAGE_MIN (105/106-01)"
  - "mistakes_service.classify_game_mistakes + FlawRecord/FlawTag/TempoTag (Phase 105)"
  - "mistakes_repository.fetch_game_positions_ordered (Phase 105)"
  - "openings_service.get_time_series machinery: ROLLING_WINDOW_SIZE / MIN_GAMES_FOR_TIMELINE (rolling-window precedent)"
provides:
  - "library_repository.count_filtered_and_analyzed(...) -> (total_n, analyzed_n) (>=90% coverage denominator)"
  - "library_repository.analyzed_game_ids(...) -> list[int] (chronological analyzed filtered ids)"
  - "library_repository._filtered_games_base (shared SELECT Game.id filter base)"
  - "schemas.library.MistakeStatsResponse + SeverityRates/TagDistribution/MistakeTrendPoint"
  - "library_service.get_mistake_stats(...) + _load_analyzed_flaws/_compute_rates/_compute_tag_distribution/_compute_trend"
  - "GET /api/library/mistake-stats (current_active_user gated)"
affects:
  - "LIBG-03 frontend Games-subtab stats panel (consumes this endpoint)"
tech-stack:
  added: []
  patterns:
    - "Per-game coverage aggregate in SQL: SUM(CASE WHEN eval non-null THEN 1 ELSE 0 END)::float / COUNT(*) >= EVAL_COVERAGE_MIN, GROUP BY game_id, HAVING"
    - "Analyzed denominator intersected with the bounded filtered game-id set -> PK-backed nested loop (criterion-1 EXPLAIN: ~11ms, no new index)"
    - "Rolling-GAME-window trend adapted from get_time_series: trailing window, per-date dedupe, min-games gate; point.date = window last-game date (label only)"
    - "Per-game kernel re-call SEQUENTIAL on one AsyncSession (D1 pragmatic path; never asyncio.gather)"
    - "Pipeline-orchestrator split (load -> aggregate -> rates -> tags -> trend) to stay shallow"
key-files:
  created: []
  modified:
    - app/repositories/library_repository.py
    - app/services/library_service.py
    - app/schemas/library.py
    - app/routers/library.py
    - tests/test_library_repository.py
    - tests/services/test_library_service.py
decisions:
  - "D1 (locked) honored: SQL handles ONLY the EXISTS filter + per-severity counts (via count_game_severities) + the >=90% analyzed denominator; tag distribution + rates come from re-calling the kernel over the analyzed filtered set. No severity-math fork."
  - "D3 (locked) honored: trend is a trailing rolling-GAME window (ROLLING_WINDOW_SIZE games, MIN_GAMES_FOR_TIMELINE gate), NOT calendar buckets. MistakeTrendPoint.date is the window's last-game date — a label, never a bucket boundary (W5)."
  - "W2: per-100-moves denominator is the count of USER-mover plies (parity == game.user_color) across the analyzed set — computed in _count_user_moves, summed in get_mistake_stats — not severity events nor both colors' plies."
  - "W3: result_changing_rate = result-changing M+B flaws / total M+B flaws (both from the FlawRecord set). Inaccuracies never enter the distribution; the I count comes only from count_game_severities."
  - "Criterion 1 (index decision): no new (game_id, ply) index — the realistic service query intersects the coverage aggregate with the bounded filtered game-id set, which the (game_id, user_id, ply) PK serves via a nested loop (~11ms on dev DB). The isolated whole-user aggregate is slow but is not the service's access pattern."
  - "Phase-histogram + tempo split are derived from FlawRecord tags (each flaw carries exactly one phase-* and one tempo tag), consistent with the M+B tagged set; phase int 1->middlegame, 2->endgame per _phase_tag."
metrics:
  duration_minutes: 26
  completed: "2026-06-05"
  tasks: 2
  files_created: 0
  files_modified: 6
---

# Phase 106 Plan 03: Games-surface Backend — Mistake-Stats Aggregate Summary

`GET /api/library/mistake-stats`: the Games-subtab stats-panel aggregate over the filtered analyzed-only set. Per-severity counts (B/M/I) and rates normalized two ways (per analyzed game AND per 100 USER-moves), the full tag distribution (tempo split, result-changing rate, phase histogram), a rolling-GAME-window trend, and the explicit `% analyzed` (>=90%-per-ply-coverage) denominator with the analyzed-game N — so the panel never implies clean games where evals are merely absent. Built on the D1 pragmatic path: SQL owns the EXISTS filter + the coverage denominator; the Phase 105 kernel is re-called per analyzed game for counts + tags.

## What was built

### Task 1 — analyzed denominator + analyzed-set loader (`library_repository`)
- `count_filtered_and_analyzed(...) -> (total_n, analyzed_n)`: `total_n` = filtered game count; `analyzed_n` = filtered games whose per-game coverage aggregate (`SUM(CASE WHEN eval_cp OR eval_mate non-null THEN 1 ELSE 0 END)::float / COUNT(*)`, `GROUP BY game_id`, `HAVING ratio >= EVAL_COVERAGE_MIN`) clears the gate. `EVAL_COVERAGE_MIN` is the imported kernel constant (no 0.90 literal). User-scoped; early `(0, 0)` when the filtered set is empty.
- `analyzed_game_ids(...) -> list[int]`: the analyzed filtered game-ids ordered `played_at ASC` (chronological, for the trend re-call), same filter + analyzed gate, user-scoped.
- `_filtered_games_base(...)`: extracted shared `SELECT Game.id` filter base so `query_filtered_games` (06-02), `count_filtered_and_analyzed`, and `analyzed_game_ids` agree on what "the filtered set" means.
- `_analyzed_game_ids_subquery(user_id)`: the reusable coverage-aggregate subquery.

### Task 2 — `get_mistake_stats` service + schemas + router
- Schemas (`app/schemas/library.py`): `SeverityRates` (`per_game` / `per_100_moves` dicts keyed by FlawSeverity), `TagDistribution` (`tempo` dict, `result_changing_rate`, `phase_histogram`), `MistakeTrendPoint` (`date` = window last-game date, `rate`, `game_count`, `window_size`), `MistakeStatsResponse` (`per_severity_counts`, `rates`, `tag_distribution`, `trend`, `analyzed_pct`, `analyzed_n`, `total_n`).
- `get_mistake_stats(...)`: computes the denominator + chronological ids (SQL), re-calls the kernel per analyzed game (SEQUENTIAL on one AsyncSession), then assembles via stage helpers:
  - `_load_analyzed_flaws`: per-game `count_game_severities` + `classify_game_mistakes` + `_count_user_moves` (W2 user-mover ply count) + the game's `played_at`, collected into `_GameFlaws`.
  - `_aggregate_counts`: sums all three tiers (the I count is genuinely from `count_game_severities`, never the M+B set).
  - `_compute_rates`: `per_game = count / analyzed_n`; `per_100_moves = count / total_user_moves * 100` (W2). Both guard div-by-zero.
  - `_compute_tag_distribution`: tempo split, `result_changing_rate = result-changing M+B / total M+B` (W3, guarded), phase histogram (phase int 1->middlegame / 2->endgame).
  - `_compute_trend`: trailing rolling-GAME window (`ROLLING_WINDOW_SIZE`, `MIN_GAMES_FOR_TIMELINE` gate, per-date dedupe), each point dated by its window's last game (W5).
  - empty analyzed set (`analyzed_n == 0`) -> `_empty_stats(total_n)`: zeros + empty trend, `analyzed_pct 0.0`, never raises. Sentry-wrapped around the SQL + re-call block.
- Router (`app/routers/library.py`): thin `@router.get("/mistake-stats")` mirroring the `/games` param list (severity forwarded as `mistake_severity`), `from_date>to_date -> 422`, `current_active_user` gated. Mounted at `/api/library/mistake-stats`.

## Deviations from Plan

### Auto-fixed / additive (Rule 3)

**1. [Rule 3 - Blocking] `session.get(Game, ...)` keyed on single-column PK, not a composite**
- **Found during:** Task 2.
- **Issue:** The plan sketch implied a `(game_id, user_id)` lookup, but `Game`'s PK is the single `id` column (only `game_positions` has the 3-tuple PK).
- **Fix:** `session.get(Game, game_id)` plus an explicit `game.user_id != user_id` ownership re-assert (T-106-03AC) before reading any game state.
- **Files modified:** app/services/library_service.py
- **Commit:** 9b7fbb9a

No architectural changes (Rule 4). No new packages. No DB column/table/migration/backfill — on-the-fly only.

## Verification

- `uv run pytest tests/test_library_repository.py tests/services/test_library_service.py` -> 22 passed (9 repo + 13 service).
- `uv run pytest tests/test_library_repository.py -k analyzed_denominator -x` -> 2 passed (total_n=2/analyzed_n=1 for analyzed+chesscom; user-scoped).
- `uv run pytest tests/services/test_library_service.py -k stats -x` -> 4 passed: definite `per_100_moves` blunder == 20.0 (1 blunder / 5 user moves), `result_changing_rate` == 0.5 (1 result-changing of 2 M+B flaws), trend point date == window last-game date, empty analyzed set -> zeros.
- `uv run pytest -n auto -x` -> **2319 passed, 10 skipped** (the pre-merge gate; 2 fewer skips than 106-02 because the `analyzed_denominator` / `stats` placeholders are now implemented).
- `uv run ruff format app/ tests/`, `uv run ruff check app/ tests/ --fix`, `uv run ty check app/ tests/` -> all clean.
- Route registration: `app.routes` exposes `/api/library/mistake-stats`.

### Criterion 1 — index decision (EXPLAIN ANALYZE on dev DB)
The coverage aggregate `GROUP BY game_id ... HAVING` was run two ways on the dev DB:
- **Whole-user (not the service path):** parallel seq scan on `game_positions` filtered by `user_id`, ~1.7s — slow, but this is NOT how the service queries.
- **Service path (intersected with the bounded filtered game-id set):** nested loop keyed on `game_id` using the `(game_id, user_id, ply)` PK btree, **~11ms** for a 50-game filtered set.

**Decision: no new `(game_id, ply)` index.** The PK already serves the `game_id`-leading per-game scan once the aggregate is intersected with the filtered set, exactly as RESEARCH §"SQL: the EXISTS mistake filter" (criterion 1) anticipated. (No VERIFICATION.md exists for this phase; the EXPLAIN result is documented here, the canonical plan output.)

## Known Stubs
None. All previously-skipped 106-03 placeholders (`TestAnalyzedDenominator` in the repo test, `TestMistakeStats` in the service test) are now implemented with real assertions.

## Threat Flags
None. All new surface is covered by the plan's threat register: route gated by `current_active_user`; `count_filtered_and_analyzed` / `analyzed_game_ids` / the per-game `session.get(Game)` + `fetch_game_positions_ordered` all filter or re-assert `user_id` (T-106-03AC); `from_date>to_date -> 422` + severity Literal at the boundary (T-106-03V); the O(analyzed games) kernel re-call cost is the accepted T-106-03DOS (A4, v1).

## Acceptance Criteria
- [x] `count_filtered_and_analyzed` + `analyzed_game_ids` present; `EVAL_COVERAGE_MIN` imported (no 0.90 literal); analyzed+chesscom seed -> total_n=2/analyzed_n=1; user-scoped.
- [x] `MistakeStatsResponse` with `analyzed_pct` / `analyzed_n` / `total_n`; per-severity rates per game AND per 100 user-moves; `tag_distribution` (tempo + result_changing_rate + phase_histogram); `trend` list.
- [x] Inaccuracy count from `count_game_severities`, never the M+B FlawRecord tags.
- [x] Definite `per_100_moves` = severity_count / total_user_moves * 100 (W2); definite `result_changing_rate` = result-changing M+B / total M+B (W3); trend point dated by its window's last game (W5).
- [x] No `asyncio.gather` on the session; empty analyzed set -> zeros without raising.
- [x] `GET /api/library/mistake-stats` mounted under /api, gated, severity constrained to mistake/blunder, from_date>to_date -> 422.
- [x] ruff/ty clean; targeted + full suite green.

## Self-Check: PASSED
- FOUND: app/repositories/library_repository.py (def count_filtered_and_analyzed, def analyzed_game_ids)
- FOUND: app/services/library_service.py (def get_mistake_stats)
- FOUND: app/schemas/library.py (class MistakeStatsResponse)
- FOUND: app/routers/library.py ("/mistake-stats" -> /api/library/mistake-stats)
- FOUND commit f67855e6 (feat 106-03 analyzed denominator + loader)
- FOUND commit 9b7fbb9a (feat 106-03 get_mistake_stats service + router)
