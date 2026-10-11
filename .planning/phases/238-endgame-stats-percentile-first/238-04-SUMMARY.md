---
phase: 238-endgame-stats-percentile-first
plan: 04
subsystem: api
tags: [fastapi, pydantic-ai, llm-insights, prompt, ranked-sample, cache-key, filter-free]

requires:
  - phase: 238-01
    provides: build_ranked_stats / fetch_ranked_inputs / RankedTcStats ranked payload
  - phase: 238-02
    provides: per-TC timelines, pressure quintile curve and Endgame Type rows on RankedTcStats
provides:
  - "Filter-free POST /api/insights/endgame and GET /api/insights/endgame/cached (no filter params, no 400 filters_not_supported, one report per user)"
  - "Insights cache key (user_id, prompt_version, model) with constant INSIGHTS_CACHE_OPPONENT_STRENGTH 'any'; prompt endgame_v48"
  - "compute_findings(session, user_id): one fetch_ranked_inputs, all_time and last_3mo (since=now-90d) built from the same inputs"
  - "Per-TC Overall, Score-timeline, Metrics, ELO and Type findings; EndgameTabFindings.ranked_tcs; per-TC-only percentile records"
  - "System prompt v48 and a deliberately regenerated golden user prompt"
affects: [238-07, 238-09]

plan_head_before: 1052c3a407318eea73f850cfb3c9f88414549099
plan_head_after: 04452aff26625ec5975f528dc047aac2b898d164
actuals:
  tokens: 29000
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Pure build_findings(all_time, last_3mo, as_of) split from the async compute_findings so tests build findings from synthetic RankedTcStats without a DB"
    - "Constant cache-key dimension (INSIGHTS_CACHE_OPPONENT_STRENGTH) keeps the llm_logs JSON shape, so no migration"
    - "Finding-id bridge table _PCTL_KEYS maps every ranked CdfMetricId to its finding metric id(s) (recovery_score_gap <-> score_gap_recov, *_rate <-> conversion_win_pct ...)"

key-files:
  created:
    - tests/services/ranked_payload_fixtures.py
  modified:
    - app/routers/insights.py
    - app/services/insights_llm.py
    - app/services/insights_service.py
    - app/schemas/insights.py
    - app/schemas/llm_log.py
    - app/prompts/endgame_insights.md
    - tests/test_insights_router.py
    - tests/test_insights_llm_thinking.py
    - tests/test_insights_schema.py
    - tests/services/test_insights_service.py
    - tests/services/test_insights_service_series.py
    - tests/services/test_insights_llm.py
    - tests/services/golden/insights_user_prompt.txt
    - tests/prompts/test_endgame_insights_prompt.py
    - tests/routers/test_insights_openings.py

key-decisions:
  - "last_3mo findings carry no peer percentiles: build_ranked_stats(since=...) drops persisted percentiles, and per_tc_metric_percentiles is built from the all_time payload only (the stored rank belongs to the full ranked sample)"
  - "score_gap finding keeps sample_size = endgame + non-endgame games (existing quality bands) while its value comes from metrics['score_gap']; achievable and the Metrics findings use the metric's own n"
  - "A TC absent from a window (no ranked games in the last 90 days) emits no findings for that window; the renderer's existing 'last_3mo: no data' line covers it"
  - "Metrics, time-pressure table and Type findings keep the MIN_GAMES_PER_TC_CARD (20) gate, now applied to the TC's ranked endgame game count"
  - "The score_timeline score_gap finding falls back to the series mean only when the ranked score_gap has no value (one side empty)"

patterns-established:
  - "Ranked payload is the only data source of insights_service: no app.repositories import, no filtered overview"

requirements-completed: [D-04, D-00b, D-00i, D-01]

coverage:
  - id: D1
    description: "Router takes no filters: any query string behaves like none, no 400 path, cache lookup keyed on the constant opponent_strength 'any'"
    requirement: "D-04"
    verification:
      - kind: integration
        ref: "tests/test_insights_router.py#TestFilterFree"
        status: pass
      - kind: integration
        ref: "tests/test_insights_router.py#TestCachedEndpoint"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every narrated all_time finding equals the ranked per-TC value; last_3mo is the ranked subset of the last 90 days; percentile records exist exactly for ranked metrics and are all per TC"
    requirement: "D-00b"
    verification:
      - kind: unit
        ref: "tests/services/test_insights_service.py#TestRankedPayloadAlignment"
        status: pass
    human_judgment: false
  - id: D3
    description: "Cross-user cache isolation (T-238-10): another user's matching row is a cache miss; removing the user_id predicate fails the test"
    requirement: "D-04"
    verification:
      - kind: integration
        ref: "tests/services/test_insights_llm.py#TestStructuralCacheInvalidation::test_other_users_log_not_returned"
        status: pass
    human_judgment: false
  - id: D4
    description: "User prompt has no filter or scoping block; overall_wdl is one table per ranked TC; time-pressure tables and aggregates read the ranked payload; golden regenerated deliberately and deterministic"
    requirement: "D-04"
    verification:
      - kind: unit
        ref: "tests/services/test_insights_llm.py#TestGoldenUserPrompt"
        status: pass
      - kind: unit
        ref: "tests/services/test_insights_llm.py#TestTimePressureScoreGapChartBlock"
        status: pass
    human_judgment: false
  - id: D5
    description: "System prompt v48: no scoping caveat, per-TC granularity rule, ranked-sample window anchoring, overall narrated per time control; banned-vocabulary and peer-rank phrasing rules unchanged"
    requirement: "D-04"
    verification:
      - kind: unit
        ref: "tests/prompts/test_endgame_insights_prompt.py"
        status: pass
    human_judgment: true
    rationale: "Whether the narration reads well on real per-TC data needs the live smoke generate planned for 238-09; no automated test judges prose quality"

duration: 85min
completed: 2026-10-11
status: complete
---

# Phase 238 Plan 04: Filter-free insights over the ranked sample Summary

**Shelly's endgame insights now take no filters, key the cache on `(user_id, prompt_version, model)` plus a constant, and narrate the same per-TC ranked values the Stats tab shows, with prompt `endgame_v48` and a deliberately regenerated golden.**

## Performance

- **Duration:** about 85 min
- **Tasks:** 3 (1 tracer, 1 TDD, 1 auto) plus one Rule 1 test fix
- **Files:** 16 touched (1 created, 15 modified)

## Accomplishments

- **Router (D-04):** `POST /insights/endgame` and `GET /insights/endgame/cached` declare only the session and auth dependencies. `_validate_full_history_filters`, the custom opponent-gap 400 and every `Query(...)` are gone; FastAPI ignores undeclared query strings, so the unchanged frontend (which still sends filters until 238-07) keeps working and receives the one per-user report. The 502 mapping is unchanged.
- **Cache key:** `INSIGHTS_CACHE_OPPONENT_STRENGTH: Literal["any"]` is defined in `insights_llm` and used by the lookup, the cached GET and the `LlmLogFilterContext` write, so the JSON shape and the DB are untouched (no migration). `_PROMPT_VERSION = "endgame_v48"` invalidates every v47 row.
- **Findings from the ranked payload:** `compute_findings(session, user_id)` awaits `fetch_ranked_inputs` once, then `build_ranked_stats(inputs)` (all_time) and `build_ranked_stats(inputs, since=now-90d)` (last_3mo). Overall (`endgame_start_vs_end`, `score_gap`), `score_timeline`, `endgame_metrics_<tc>`, `endgame_elo_timeline` and `endgame_type_<tc>` findings are built per TC with `dimension={"time_control": tc}` from `RankedTcStats` (value and n from `metrics`, scores from the overall WDL, entry metrics from `entry_flow`). The module no longer imports `get_endgame_overview`, `EndgameOverviewResponse` or any repository.
- **Percentiles:** `per_tc_metric_percentiles` carries a `"{metric}:{tc}"` record (value x100, `n_games = n`, TC anchor) exactly for metrics whose status is `ranked`, including the recovery bridge key; the page-level weighted records and `_lookup_pctl_record`'s page-level branch are gone.
- **Prompt assembly:** `_format_filters_for_prompt` deleted; `overall_wdl` renders one table per ranked TC; the time-pressure quintile tables and the three aggregates read `ranked_tcs[i].time_pressure` and the TC's ranked metrics (a line is omitted when neither a percentile nor a value exists); `Total games in scope` sums `ranked_games`.
- **Schema:** `EndgameTabFindings` loses `filters`, `time_pressure_chart`, `overall_performance`, `type_categories`, `metric_percentiles` and `time_pressure_cards`, gains `ranked_tcs`; `FilterContext` is deleted. The Shelly report shape (`EndgameInsightsReport`) is unchanged (D-00i).
- **System prompt v48:** Scoping caveat bullet and the Opponent strength scoping section removed; the granularity rule says every `pctl=` token is per TC (the weighted page-level sentence is gone); window anchoring describes the ranked sample ("the page's headline numbers", no gauges); overall subsections are narrated per time control, never averaged. Banned-vocabulary, peer-rank phrasing and disclosure rules are untouched; no "typical" band sentence was edited, so `reports/benchmark/benchmarks-latest.md` was not consulted.

## Task Commits

1. **Task 1 (tracer): filter-free insights path with ranked per-TC Overall findings** - `748550ef4` (feat)
2. **Task 2: ranked per-TC findings, chart blocks, regenerated golden** - `733c46126` (feat)
3. **Task 3: system prompt v48 and prompt/schema tests** - `ed6dcfb92` (feat)
4. **Rule 1 fix: endgame insights no longer 400 on from_date** - `04452aff2` (test)

## Verification

- Tracer gate (Task 1): `<verify>` (`tests/test_insights_router.py`, `tests/test_insights_llm_thinking.py`, `ty check app/`) re-run green before expanding; the human-verify mode is `end-of-phase` with automated-only verify, so no checkpoint.
- Task 2 verify: `tests/services/test_insights_service.py`, `..._series.py`, `test_insights_llm.py` green (235 passed); `-k other_users_log_not_returned` reports `1 passed`.
- Task 3 verify and the plan verification set: 358 passed across router, service, series, llm, prompt, schema, thinking, `test_llm_log_cascade.py`, `test_llm_log_repository.py`, `test_no_conversion_elo_string.py`.
- Gate: `ruff format --check app/ tests/ scripts/ analysis/` clean, `ruff check .` clean, `ty check app/ tests/ scripts/` and `ty check analysis/` zero errors, `check_function_size.py app/ --fail-over-depth 4` no breaches, full `uv run pytest -n auto`: **5543 passed, 19 skipped** (10.5 min wall, the box was loaded by sibling work).
- Acceptance greps: `_validate_full_history_filters` 0 in the router, `Query(` 0, `get_endgame_overview|EndgameOverviewResponse` 0 in `insights_service.py` and `insights_llm.py`, `metric_percentiles["score_gap"]` 0, no `FilterContext` outside `LlmLogFilterContext`, `Scoping caveat` and `Opponent strength scoping` 0 in the prompt, `_PROMPT_VERSION = "endgame_v48"` present.

### T-238-10 mutation check (recorded as required)

`test_other_users_log_not_returned` (ported mechanically to `generate_insights(fresh_test_user.id, session)`, name, seeded second-user row and `assert r.status == "fresh"` unchanged). With `LlmLog.user_id == user_id` in `get_latest_successful_log_for_user` temporarily replaced by `LlmLog.user_id == LlmLog.user_id`, the test **failed** (`AssertionError: assert 'cache_hit' == 'fresh'`); after restoring the predicate it **passed** and `git diff --quiet app/repositories/llm_log_repository.py` exits 0.

### Golden regeneration (Pitfall 7, deliberate)

`tests/services/golden/insights_user_prompt.txt` was regenerated from `_build_golden_findings()` (now on a ranked blitz fixture, `quintiles=[]` so only the overall/series sections are pinned) after confirming two consecutive builds are byte-identical. The diff is exactly the `overall_wdl` block (`### Chart: overall_wdl (blitz, all_time)` and its caption) and nothing else; `Total games in scope: 940` is unchanged. The test docstring carries the line "Regenerated deliberately in Phase 238 (D-04): ranked-sample population, per-TC overall findings, no filter block." The assembler was not edited to match the old golden.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `tests/routers/test_insights_openings.py` pinned the retired 400 gate**
- **Found during:** full-suite run after Task 3
- **Issue:** `test_insights_blocked_when_from_date_set` asserted `POST /insights/endgame?from_date=...` returns 400 "Clear Custom date range filter". That gate is removed by D-04 by design.
- **Fix:** replaced it with `test_endgame_insights_no_longer_gated_by_from_date` (stubs `generate_insights`, asserts 200 and one call); the module docstring reference to the deleted function was reworded.
- **Files modified:** `tests/routers/test_insights_openings.py` (not in the plan's file list)
- **Commit:** `04452aff2`

### Execution notes (no scope impact)

- **New test helper module** `tests/services/ranked_payload_fixtures.py`: a `make_ranked_tc` / `make_metric` factory for synthetic `RankedTcStats`. The plan listed no home for fixtures; three test files share it (same situation as 238-03's `rankedFixtures.ts`).
- **`build_findings(all_time, last_3mo, *, as_of)`** was split out of `compute_findings` as a public pure function so the findings can be built and tested without a DB; `compute_findings` stays the sole entry point used by `insights_llm`.
- **Task 1 transitional state** kept `time_pressure_cards` on the schema (None) until Task 2 removed it, exactly as the plan described; the golden/service tests were red only between Task 1 and Task 2 commits.
- **Placeholder findings** for an empty `endgame_elo_timeline` are still emitted (NaN, thin), as before; the renderer's A2 filter drops them.

**Total deviations:** 1 auto-fixed (Rule 1), 4 execution notes. **Impact:** none on the contract.

## TDD Gate Compliance (Task 2)

`workflow.tdd_mode` is not enabled in this repo and I wrote Task 2's tests together with the implementation instead of committing a RED commit first, so **there is no `test(238-04)` RED commit**. This is an advisory TDD-order violation. Compensating evidence, in the repo's preferred revert style: with the Task 2 app changes reverted to the Task 1 commit, the four behavior tests were run again. `test_findings_values_equal_ranked_payload` failed on `assert 12 == (2 * ((4 + 2) + 6))` (only the Overall findings existed) and `test_elo_and_score_timeline_from_ranked_series` failed on `assert [] == [('chess.com', 'blitz'), ('lichess', 'rapid')]`. `test_last_3mo_uses_ranked_subset` and `test_pctl_records_only_for_ranked_status` already passed against the Task 1 code because Task 1 delivered the two-window build and the per-TC percentile records; they remain as regression pins. The patch was re-applied and everything is green.

## Authentication Gates

None.

## Issues Encountered

- **Transient frontend state (accepted by the plan):** until 238-07, the frontend hooks still send the page filters as query params and key their react-query cache per filter state. The filter-free router ignores them and returns the one per-user report. Router tests pin this (12 legacy query strings x POST and GET).
- The first full-suite attempt stopped on the `test_insights_openings.py` failure above; the rerun passed. The full suite took 635 s because other executors share the machine; not a test problem.

## Known Stubs

None. Every `EndgameTabFindings` field is populated from the ranked payload.

## Threat Flags

None. The only surface touched is the existing authenticated insights router (T-238-10..13): `user_id` still comes only from `current_active_user`, the cached-report lookup keeps `LlmLog.user_id == user_id` as its first key (mutation-checked), the rate limiter and structural cache are untouched, and no user free text enters the prompt.

## Next Phase Readiness

Ready for 238-07 (frontend hooks drop the filter plumbing and key the insights cache per user) and 238-09 (live smoke generate on real per-TC data to judge the v48 narration, since no automated test can).

## Self-Check: PASSED

- Created file exists: `tests/services/ranked_payload_fixtures.py`
- Commits `748550ef4`, `733c46126`, `ed6dcfb92`, `04452aff2` are ancestors of HEAD
- Acceptance greps and the plan verification set re-run after the last code commit (see Verification)
