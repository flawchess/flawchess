---
phase: 57-endgame-elo-timeline-chart
plan: 01
subsystem: api
tags: [endgame, elo, timeline, analytics, sqlalchemy, pydantic, backend]

# Dependency graph
requires:
  - phase: 52-endgames-composed-overview
    provides: /api/endgames/overview composed response pattern (piggyback, not a new endpoint)
  - phase: 53-score-gap-material
    provides: _compute_score_gap_material bucket classification logic (ported here)
  - phase: 54-clock-pressure
    provides: CLOCK_PRESSURE_TIMELINE_WINDOW sibling constant precedent
  - phase: quick-260416-w3q
    provides: _compute_weekly_rolling_series shape reference (ISO-week bucketing + trailing window)
  - phase: quick-260417-o2l
    provides: _compute_score_gap_timeline two-stream merge+sort pattern (closer structural analog)
  - phase: 48-persistence-filter
    provides: user_material_imbalance_after column (4-ply persistence) used by skill bucketing
  - phase: quick-260418-nlh
    provides: frontend endgameSkill() composite being ported to the backend here
provides:
  - EndgameEloTimelinePoint / EndgameEloTimelineCombo / EndgameEloTimelineResponse schemas
  - query_endgame_elo_timeline_rows (repo) returning (bucket_rows, all_rows) tuple
  - ENDGAME_ELO_TIMELINE_WINDOW = 100 constant
  - _endgame_elo_from_skill (pure formula, clamped [0.05, 0.95])
  - _endgame_skill_from_bucket_rows (backend port of frontend endgameSkill, tagged with Phase 56 dedup TODO)
  - _compute_endgame_elo_weekly_series (two-stream weekly rolling helper)
  - get_endgame_elo_timeline orchestrator (user-scoped, partitioned per combo)
  - endgame_elo_timeline field on EndgameOverviewResponse
affects: [57-02 frontend timeline section, 56 endgame-elo-breakdown, future Phase 56 skill-helper dedup]

# Tech tracking
tech-stack:
  added: [math module import (std-lib)]
  patterns:
    - Performance-rating formula with symmetric clamp at ±510 Elo beyond opponent avg
    - Two-stream chronological merge with independent trailing windows (endgame skill + all-games rating)
    - Per-combo partition in Python over shared apply_game_filters result
    - Backend-frontend helper duplication tagged with a Phase 56 dedup TODO

key-files:
  created:
    - tests new classes TestEndgameElo / TestEndgameSkillFromBucketRows / TestEndgameEloTimeline
    - TestEndgameEloTimelineRouter (integration) in tests/test_integration_routers.py
  modified:
    - app/schemas/endgames.py
    - app/repositories/endgame_repository.py
    - app/services/endgame_service.py
    - tests/test_endgame_service.py
    - tests/test_integration_routers.py

key-decisions:
  - "Phase 56 backend endgame_skill() not yet built: inlined _endgame_skill_from_bucket_rows in Phase 57 with TODO for dedup"
  - "Applied symmetric clamp (0.05, 0.95) unconditionally before log10 call — no conditional clamp"
  - "Piggyback on /api/endgames/overview response (no new router endpoint) — consistent with Phase 52 consolidation"
  - "Recency cutoff passed through apply_game_filters but called with None from orchestrator; cutoff_str filters emitted points after the window pre-fills"
  - "Combo ordering: chess.com first, then lichess; within each platform, _TIME_CONTROL_ORDER (bullet->blitz->rapid->classical)"
  - "Drop combos with zero qualifying points (D-10 tier 2) so the frontend never sees empty points: [] payloads"

patterns-established:
  - "Pattern 1: Two-stream weekly rolling helper — merges endgame + all-games events with independent trailing windows, emits one row per ISO week when endgame window >= MIN_GAMES_FOR_TIMELINE"
  - "Pattern 2: Per-combo partition in Python — orchestrator issues one shared apply_game_filters query, partitions rows by (platform, time_control_bucket), calls helper per combo"
  - "Pattern 3: Inline Elo performance-rating formula with clamp — pure function, no exceptions, safe at skill boundaries"

requirements-completed: [ELO-05]

# Metrics
duration: 9min
completed: 2026-04-18
---

# Phase 57 Plan 01: Endgame ELO Timeline — Backend Summary

**Backend pipeline for paired Endgame ELO + Actual ELO weekly rolling series per (platform, time-control) combo, served as a new `endgame_elo_timeline` field on the existing `/api/endgames/overview` response.**

## Performance

- **Duration:** 9 min
- **Started:** 2026-04-18T17:16:07Z
- **Completed:** 2026-04-18T17:24:55Z
- **Tasks:** 4
- **Files modified:** 5

## Accomplishments

- Closed ELO-05 SC-1 (paired lines per combo), SC-2 (filter responsiveness), and SC-3 (cold-start empty combos) at the backend layer.
- Locked the Endgame ELO formula `round(avg_opp + 400 · log10(clamp(skill, 0.05, 0.95) / (1 − clamp(skill))))` in-code with unconditional clamp.
- Ported the frontend `endgameSkill()` composite to the backend with a clearly documented Phase 56 dedup TODO.
- Added 17 new unit tests + 2 integration tests, all green. No regressions in the 829-test suite.

## Task Commits

1. **Task 1: Add Pydantic schemas for Endgame ELO timeline** — `c91084d` (feat)
2. **Task 2: Add repo query for per-combo Elo timeline rows** — `f94b551` (feat)
3. **Task 3: Add service helpers + orchestrator + overview wiring + unit tests** — `d68cbde` (feat)
4. **Task 4: Integration tests for overview endpoint (SC-2 + SC-3)** — `a9f5682` (test)

## Files Created/Modified

- `app/schemas/endgames.py` — `EndgameEloTimelinePoint`, `EndgameEloTimelineCombo`, `EndgameEloTimelineResponse`; one new field on `EndgameOverviewResponse`.
- `app/repositories/endgame_repository.py` — new `query_endgame_elo_timeline_rows` returning `(bucket_rows, all_rows)`, user-scoped at top-level WHERE, routed through `apply_game_filters`, NULL-rating rows excluded.
- `app/services/endgame_service.py` — new constants (`ENDGAME_ELO_TIMELINE_WINDOW = 100`, clamp bounds, `_ENDGAME_ELO_COMBO_ORDER`); helpers `_endgame_elo_from_skill`, `_endgame_skill_from_bucket_rows`, `_compute_endgame_elo_weekly_series`; orchestrator `get_endgame_elo_timeline`; sequential `await` wired into `get_endgame_overview`.
- `tests/test_endgame_service.py` — new classes `TestEndgameElo` (formula clamp boundaries), `TestEndgameSkillFromBucketRows` (bucket classification and mixed-bucket averaging), `TestEndgameEloTimeline` (below-min-games drop, actual-vs-endgame distinctness, cutoff-pre-fill, rolling-window cap); also extended two existing `TestGetEndgameOverview` tests to mock the new orchestrator.
- `tests/test_integration_routers.py` — new `TestEndgameEloTimelineRouter` with two HTTP-level tests for SC-2 (platform filter) and SC-3 (cold-start empty combos).

## Signatures for Plan 02 (frontend) to consume

| Symbol | Location | Shape |
|---|---|---|
| `EndgameEloTimelinePoint` | `app/schemas/endgames.py:332-350` | `{date: str, endgame_elo: int, actual_elo: int, endgame_games_in_window: int}` |
| `EndgameEloTimelineCombo` | `app/schemas/endgames.py:353-369` | `{combo_key: str, platform: Literal["chess.com", "lichess"], time_control: Literal["bullet", "blitz", "rapid", "classical"], points: list[EndgameEloTimelinePoint]}` |
| `EndgameEloTimelineResponse` | `app/schemas/endgames.py:371-384` | `{combos: list[EndgameEloTimelineCombo], timeline_window: int}` |
| `endgame_elo_timeline` | `EndgameOverviewResponse` at `app/schemas/endgames.py:401` | nested `EndgameEloTimelineResponse` |
| `get_endgame_elo_timeline` | `app/services/endgame_service.py` (orchestrator) | async, sequential await on `AsyncSession`, user-scoped |
| `ENDGAME_ELO_TIMELINE_WINDOW` | `app/services/endgame_service.py` (constant = 100) | equals `response.timeline_window` |

Combo ordering is stable: chess.com first, then lichess; within each platform, `bullet -> blitz -> rapid -> classical`. `combo_key` format: `"{platform-with-underscores}_{time_control}"` (e.g. `chess_com_blitz`, `lichess_classical`).

## Decisions Made

- **Phase 56 boundary**: because `.planning/phases/56-*` does not yet exist, `_endgame_skill_from_bucket_rows` lives in `endgame_service.py` with an inline `TODO (Phase 56)` docstring line. When Phase 56 lands and introduces a shared backend `endgame_skill()`, remove this helper and call the shared one.
- **Symmetric clamp**: applied unconditionally (not "only if skill is extreme") so the formula is exception-safe for any caller.
- **Cutoff handling**: the repo function forwards `recency_cutoff` to `apply_game_filters`, but the orchestrator passes `None` — the cutoff filter is re-applied after emission via `cutoff_str >= date` on the per-week dict. This preserves the "windows pre-fill from earlier games" property (Pitfall 2).
- **Combo dropping**: combos with zero qualifying points are omitted from `combos[]` entirely (D-10 tier 2). The frontend never receives `{combo_key, ..., points: []}`.
- **Overview wiring**: chose to mock `get_endgame_elo_timeline` at the orchestrator level in the existing `TestGetEndgameOverview` tests (rather than mocking `query_endgame_elo_timeline_rows`) — mirrors the existing `get_endgame_timeline` mocking pattern and keeps test state minimal.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Existing TestGetEndgameOverview tests broke when new orchestrator was wired in**
- **Found during:** Task 3 (service orchestrator wiring)
- **Issue:** `test_overview_composes_all_five_payloads` and `test_overview_passes_window_to_timeline` patched every repo function that `get_endgame_overview` touched, but the newly added `get_endgame_elo_timeline` call hit the real `query_endgame_elo_timeline_rows` against an `AsyncMock()` session, producing a `TypeError: 'coroutine' object is not iterable`.
- **Fix:** Added `patch("app.services.endgame_service.get_endgame_elo_timeline", new_callable=AsyncMock)` + `return_value = EndgameEloTimelineResponse(combos=[], timeline_window=100)` to both tests. Added a positive assertion on the new sub-payload in the composition test.
- **Files modified:** `tests/test_endgame_service.py`
- **Verification:** Full `uv run pytest tests/test_endgame_service.py` green (189/189).
- **Committed in:** `d68cbde` (part of Task 3 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 bug fix in pre-existing overview tests triggered by wiring the new orchestrator).
**Impact on plan:** Fix was strictly necessary to keep the existing test-suite green under the new wiring. No scope creep — no new assertions beyond mirroring the existing sub-payload pattern.

## Known Stubs

None. The only `TODO` in the Phase 57 additions is an intentional Phase 56 dedup marker on `_endgame_skill_from_bucket_rows` — this is not a stub; it is a functional backend port of the frontend helper, fully unit-tested.

## Threat Flags

No new threat surface beyond the `<threat_model>` register in the plan. All new SQL goes through `apply_game_filters`, every query is user-scoped at the top-level WHERE, and the response contains only aggregated Elo integers + game counts (no PII).

## Issues Encountered

- `Edit` tool produced repeated `READ-BEFORE-EDIT REMINDER` system messages even after the files had been read within the session, but all edits applied successfully. Worked around by using `cat >> file << EOF` for large appends. No file content was lost.
- The existing `TestGetEndgameOverview` tests' coroutine-iteration failure was a straightforward wiring issue, not a logic bug — diagnosed, fixed, and re-run in one iteration.

## Self-Check: PASSED

**Files created/modified verified:**
- `.planning/phases/57-endgame-elo-timeline-chart/57-01-SUMMARY.md` — FOUND (this file, written last)
- `app/schemas/endgames.py` — FOUND (3 new classes + 1 field)
- `app/repositories/endgame_repository.py` — FOUND (query_endgame_elo_timeline_rows)
- `app/services/endgame_service.py` — FOUND (constants + 3 helpers + orchestrator + wiring)
- `tests/test_endgame_service.py` — FOUND (17 new tests, 189 total pass)
- `tests/test_integration_routers.py` — FOUND (2 new integration tests pass)

**Commits verified in `git log`:**
- `c91084d` — feat(57-01): add Endgame ELO timeline Pydantic schemas ✓
- `f94b551` — feat(57-01): add query_endgame_elo_timeline_rows repo function ✓
- `d68cbde` — feat(57-01): add Endgame ELO timeline service helpers + orchestrator ✓
- `a9f5682` — test(57-01): add integration tests for endgame_elo_timeline sub-payload ✓

**Verification commands all green:**
- `uv run ruff check .` — All checks passed
- `uv run ty check app/ tests/` — All checks passed
- `uv run pytest` — 829 passed

## Next Phase Readiness

- **Plan 02 (frontend):** ready to implement. The wire format is stable and tested end-to-end (HTTP status 200 + schema roundtrip in integration tests). Use the `combo_key` string as the `ELO_COMBO_COLORS` lookup key. Combos with no data are absent from the array, so the frontend's cold-start empty-state check is simply `response.combos.length === 0`.
- **Phase 56 (endgame-elo-breakdown):** when this phase builds its own backend `endgame_skill()`, replace `_endgame_skill_from_bucket_rows` usage in Phase 57's `_compute_endgame_elo_weekly_series` and delete the Phase-57 helper. The `Phase 56` TODO docstring flags the exact location.
- **No blockers or concerns** for downstream phases.

---
*Phase: 57-endgame-elo-timeline-chart*
*Completed: 2026-04-18*
