---
phase: 242-openings-stats-insights-rework
plan: 01
subsystem: api
tags: [fastapi, sqlalchemy, openings, stats, wilson, z-test, dev-clock]

requires:
  - phase: 238-239
    provides: 99% verdict system (VERDICT_CI_Z_99) and the dev_now_utc dependency pattern
provides:
  - "repertoire_recency: 200-game / 60-day current-repertoire cutoff (combine_cutoff, is_current, resolve_current_cutoff(s))"
  - "opening_eval.finalize_opening_eval: Openings-only baseline-centred MG-entry eval verdict with 95% and 99% CIs"
  - "score_confidence.score_verdict_fields: score, Wilson p, 99% Wilson CI (shared with the bookmark series in plan 03)"
  - "GET /stats/most-played-openings: deduped, bookmark-twin-free rows, up to 10 current then 10 past per colour, is_current per row, current_cutoff_white/black"
  - "BookmarkPhaseEntryItem baseline-centred eval and eval_ci99 bounds"
affects: [242-02, 242-03, 242-04, 242-05, 242-06, openings-frontend]

actuals:
  tokens: 17800
  tasks: 3
  commits: 3
plan_head_before: dbf39ea4d36e900eca5aff373f4fba45eb36340c
plan_head_after: 59b3edde7ecdb8773a79561bb8acf4e3125d0a57

tech-stack:
  added: []
  patterns:
    - "Neutral recency module shared by stats/insights/openings services (no cross-imports)"
    - "Pure candidate pipeline (build -> dedupe -> drop twins -> split/cap) with async fetch wrappers"
    - "Game-set fingerprint = (total, W/D/L, SUM(DISTINCT game id), last_played_at)"

key-files:
  created:
    - app/services/repertoire_recency.py
    - app/services/opening_eval.py
    - tests/test_repertoire_recency.py
    - tests/services/test_opening_eval.py
  modified:
    - app/repositories/stats_repository.py
    - app/services/stats_service.py
    - app/services/score_confidence.py
    - app/services/eval_confidence.py
    - app/services/opening_insights_constants.py
    - app/routers/stats.py
    - app/schemas/stats.py
    - tests/test_stats_service.py
    - tests/test_stats_repository.py
    - tests/test_stats_router.py
    - tests/test_stats_schemas.py
    - tests/services/test_score_confidence.py
    - tests/services/test_stats_service_phase_entry.py

key-decisions:
  - "Cutoff = min(200th most recent game date of that colour, now_utc - 60 days); None when fewer than 200 games under the active filters"
  - "Baseline centring lives in a new opening_eval module that passes baseline_cp explicitly; the eval_confidence primitive default stays 0 so endgame_service is untouched"
  - "Dedupe fingerprint ignores rows without a position bucket (game_id_sum == 0) so name-only fallback rows are never collapsed"
  - "Twin drop uses all of the user's coloured bookmarks regardless of match_side or sidebar filters; no exclusion parameter (D-16)"
  - "Second cutoff-restricted fetch only nominates openings; WDL/last_played_at/is_current always come from the unrestricted position batch"

patterns-established:
  - "Read module-level limits at call time (never default-argument binding) so tests can monkeypatch them"
  - "Rows from the top-openings query are read by attribute name, never by index"

requirements-completed: [D-00, D-01, D-02, D-03, D-04, D-05, D-06, D-07, D-12, D-13, D-16, D-18]

coverage:
  - id: D1
    description: "Current/past cutoff computed under active filters with the dev clock, returned per colour and as is_current per row"
    requirement: "D-01"
    verification:
      - kind: unit
        ref: "tests/test_repertoire_recency.py"
        status: pass
      - kind: integration
        ref: "tests/test_stats_router.py#test_most_played_openings_passes_dev_clock_now_utc"
        status: pass
    human_judgment: false
  - id: D2
    description: "Most-played rows deduped by game set, bookmark twins dropped, split current/past, capped 10 + 10"
    requirement: "D-06"
    verification:
      - kind: integration
        ref: "tests/test_stats_service.py#TestMostPlayedPipeline"
        status: pass
      - kind: unit
        ref: "tests/test_stats_service.py#TestDedupeIdenticalSets"
        status: pass
    human_judgment: false
  - id: D3
    description: "Cutoff-restricted second fetch fills current rows past openings would push out, counted under the unrestricted filters"
    requirement: "D-05"
    verification:
      - kind: integration
        ref: "tests/test_stats_service.py#test_recent_fallback_fills_current_rows"
        status: pass
    human_judgment: false
  - id: D4
    description: "Baseline-centred eval z-test with 99% CI on most-played rows and bookmark phase-entry items; endgame eval unchanged"
    requirement: "D-13"
    verification:
      - kind: unit
        ref: "tests/services/test_opening_eval.py"
        status: pass
      - kind: integration
        ref: "tests/services/test_stats_service_phase_entry.py#test_most_played_eval_is_centred_on_the_colour_baseline"
        status: pass
      - kind: unit
        ref: "tests/test_endgame_service.py"
        status: pass
    human_judgment: false
  - id: D5
    description: "Score p-value and 99% Wilson CI from one shared helper"
    requirement: "D-18"
    verification:
      - kind: unit
        ref: "tests/services/test_score_confidence.py#TestScoreVerdictFields"
        status: pass
    human_judgment: false

duration: 75min
completed: 2026-10-17
status: complete
---

# Phase 242 Plan 01: Backend for the Openings Stats rework Summary

**Current/past repertoire cutoff (200 games or 60 days), baseline-centred Openings eval verdict with 99% CIs, and a deduped, bookmark-twin-free most-played pipeline (10 current + 10 past per colour, cutoff-restricted second fetch) behind GET /stats/most-played-openings.**

## Performance

- **Duration:** about 75 min
- **Started:** 2026-10-17T15:20:00Z (approx.)
- **Completed:** 2026-10-17T16:35:00Z
- **Tasks:** 3
- **Files modified:** 17 (4 created, 13 modified)

## Accomplishments

- `repertoire_recency.py`: `combine_cutoff` / `is_current` / `resolve_current_cutoff(s)`; the cutoff query (`query_nth_recent_played_at`) goes through `apply_game_filters`, so it respects TC, platform, rated, opponent, recency and gap filters (D-02). The router passes `now_utc` from `dev_now_utc` (D-03); no `datetime.now()` in the service.
- `opening_eval.finalize_opening_eval` tests the MG-entry eval against +25 cp (White) / -25 cp (Black) while `avg_eval_pawns` stays the raw mean; 99% bounds reuse the same standard error. Both the most-played rows and `_bookmark_phase_entry_item` use it. `endgame_service.py` is untouched and its tests pass.
- `score_verdict_fields` gives rows score, two-sided Wilson p, bucket and a 99% Wilson CI; plan 03 reuses it for the bookmark time series.
- Most-played pipeline in `stats_service`: fetch 60 -> position WDL -> dedupe identical game sets (deeper line wins) -> drop same-colour bookmark twins -> cutoff-restricted second fetch when fewer than 10 current rows survive -> split current/past -> cap 10 + 10 -> eval batch on survivors only.
- Full backend suite green (`uv run pytest -n auto`: 5547 passed, 19 skipped); ruff, ty, and the nesting gate are clean.

## Task Commits

1. **Task 1 (tracer): current/past cutoff end-to-end** - `8f889ff48` (feat)
2. **Task 2: baseline-centred eval finalizer, 99% CIs, shared score verdict fields** - `98a55571e` (feat)
3. **Task 3: most-played pipeline (dedupe, twins, fallback, split/cap)** - `59b3edde7` (feat)

**Plan metadata:** committed with this SUMMARY (docs).

## Files Created/Modified

- `app/services/repertoire_recency.py` - cutoff constants and helpers (new)
- `app/services/opening_eval.py` - Openings-only baseline-centred finalizer (new)
- `app/repositories/stats_repository.py` - `query_nth_recent_played_at`; `game_id_sum` on `PositionWDL`; trailing `ply_count` column on the top query
- `app/services/stats_service.py` - the whole pipeline; `MOST_PLAYED_FETCH_LIMIT/CURRENT_LIMIT/PAST_LIMIT`
- `app/services/score_confidence.py` - `ScoreVerdictFields`, `score_verdict_fields`
- `app/schemas/stats.py` - `is_current`, `score*`, `eval_ci99_*`, `current_cutoff_*`
- `app/routers/stats.py` - `NowUtc` alias and `now_utc` parameter
- `app/services/eval_confidence.py`, `app/services/opening_insights_constants.py` - comments/docstrings only (baseline is now the H0 on Openings surfaces)
- Tests: `tests/test_repertoire_recency.py`, `tests/services/test_opening_eval.py` (new); extended service, repository, router, schema, score and phase-entry tests

## Decisions Made

- Dedupe fingerprint skips rows without a position bucket (`game_id_sum == 0`), so name-only fallback rows are never merged.
- The twin drop runs after the dedupe (as planned). Edge case noted: if a bookmark equals the SHALLOWER line of an identical-set pair, the deeper sibling survives and shows next to the bookmark; the plan accepted this ordering and it is cheap to revisit.
- `_merge_recent_nominees` skips the second query when the filter's own `from_date` is already on or after the cutoff day (it would repeat the first query).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] tests/test_stats_schemas.py legacy payload**
- **Found during:** Task 3 full-suite run
- **Issue:** `_LEGACY` payload lacked the now-required `score*` and `is_current` fields, so two schema tests failed validation.
- **Fix:** Added the required fields to the fixture payload and updated the docstring; the tests still assert that the eval fields are optional.
- **Files modified:** `tests/test_stats_schemas.py` (not listed in the plan's `files_modified`)
- **Committed in:** `59b3edde7`

**2. [Rule 1 - Bug] My own cutoff test used wrong day arithmetic**
- **Found during:** Task 1
- **Issue:** The "dense recent games" case seeded 3 games/day over 70 days, putting the 200th game 67 days back (beyond the 60-day floor), so the assertion expecting the floor was wrong.
- **Fix:** Seeded 10 games/day over 25 days (200th game 20 days back).
- **Committed in:** `8f889ff48`

---

**Total deviations:** 2 auto-fixed (1 blocking test fixture, 1 test-authoring bug). **Impact:** none on production code; no scope creep.

## Mutation proof (Task 3, cutoff-restricted second fetch)

With the branch in `_most_played_for_color` temporarily disabled (`if False and cutoff is not None and ...`), `uv run pytest tests/test_stats_service.py -k recent_fallback -x` FAILED (`1 failed, 3 passed`: the white list lacked opening C). Restored, the same command passes (`4 passed`). The test additionally monkeypatches `_needs_recent_fallback` to `False` and asserts C is absent, so the proof is built into the test.

## Issues Encountered

None. The `Bash` sandbox refused a few compound shell commands (reading a `.git/worktrees/...` ledger path), so the plan-commit ledger file was not written; `commits:` above is measured directly with `git rev-list --count dbf39ea4d..HEAD` (3 task commits at write time).

## Known Stubs

None.

## Threat Flags

None. No new endpoint or trust boundary beyond the plan's threat model: the cutoff and bookmark queries are scoped by `user.id` from `current_active_user`; `now_utc` comes only from `dev_now_utc`; the bad-bookmark Sentry capture puts the id in `set_context`, not the message.

## Next Phase Readiness

- Plans 02/03 can import `repertoire_recency`, `opening_eval.finalize_opening_eval` and `score_verdict_fields` as specified in the plan's contracts block.
- `openings_service` and `opening_insights_service` still call `compute_eval_confidence_bucket` with the default 0 baseline until plans 02/03 convert them; the `eval_confidence.py` docstring says so explicitly.
- Frontend TS mirrors (`types/stats.ts`) are not updated here (frontend plans own them).

## Self-Check: PASSED

- Created files exist (`repertoire_recency.py`, `opening_eval.py`, both new test files).
- Task commits `8f889ff48`, `98a55571e`, `59b3edde7` are ancestors of HEAD.
- Plan verification: affected test files pass; `ruff check .`, `ty check app/ tests/ scripts/`, `check_function_size.py app/ --fail-over-depth 4` clean; full `pytest -n auto` green; `endgame_service.py` has no diff against the base commit.

---
*Phase: 242-openings-stats-insights-rework*
*Completed: 2026-10-17*
