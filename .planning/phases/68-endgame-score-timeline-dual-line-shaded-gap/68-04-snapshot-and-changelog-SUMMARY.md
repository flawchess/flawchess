---
phase: 68-endgame-score-timeline-dual-line-shaded-gap
plan: 04
subsystem: insights
tags:
  - insights
  - endgame
  - tests
  - changelog
requires:
  - Plan 01 (backend rename + two-finding emitter)
  - Plan 02 (frontend dual-line chart)
  - Plan 03 (prompt simplification + v12 → v13 bump)
provides:
  - End-to-end integration test spanning compute_findings → _assemble_user_prompt on a realistic fixture
  - CHANGELOG.md ## [Unreleased] → ### Changed bullet for Phase 68
affects:
  - v1.11 milestone close-out (CHANGELOG bullet ready for version-renaming at milestone boundary)
tech-stack:
  added: []
  patterns:
    - Cross-plan integration smoke test pattern — reach for a module-private helper (_assemble_user_prompt) to avoid spinning up the full generate_insights agent machinery
key-files:
  created: []
  modified:
    - tests/services/test_insights_service_series.py
    - tests/test_insights_router.py
    - CHANGELOG.md
decisions:
  - Realigned the PLAN.md-stated assertion shape (`[summary score_timeline]` per-window counts) with the emitter's actual format. The plan text was imprecise — the emitter never emits a literal `[summary score_timeline]` block. Actual shape emitted: ONE `### Subsection: score_timeline` header (spans both windows with `all_time:` + `last_3mo:` lines inline inside each summary block), TWO `[summary score_gap | part=<endgame|non_endgame>]` blocks, TWO `[series score_gap, all_time, weekly, part=...]` blocks (C5 dedupes last_3mo series when all_time series exists for the same `(metric, subsection)` pair). The test documents this reconciliation inline so future readers see both the PLAN wording and the real contract.
  - Chose to reach for the private `_assemble_user_prompt(findings)` helper rather than driving the full `generate_insights` pipeline. The integration guard is the rendered prompt body, not the agent round-trip — reaching for the helper keeps the test pure, avoids pulling in pydantic-ai `Agent` + `TestModel` wiring, and mirrors how every other `TestPromptAssembly` test in `tests/services/test_insights_llm.py` already uses the same private helper.
metrics:
  duration: ~35m
  completed: 2026-04-24
---

# Phase 68 Plan 04: Snapshot and Changelog Summary

**One-liner:** End-to-end integration test proving the three upstream plans compose correctly at the rendered-prompt layer, plus the `[Unreleased]` CHANGELOG bullet and three stale `endgame_v12` test-literal fixes that Plan 03 missed.

## What Changed

### 1. New end-to-end integration test (Task 1)

Added `TestScoreTimelineIntegration.test_score_timeline_end_to_end_payload` in `tests/services/test_insights_service_series.py`. The test:

1. Reuses the existing `_make_minimal_response()` fixture (13 weekly points with mixed endgame-vs-non-endgame score patterns).
2. Calls `compute_findings(FilterContext(), session=AsyncMock(), user_id=1)` with `get_endgame_overview` patched to return the fixture.
3. Passes the resulting `EndgameTabFindings` into the module-private `_assemble_user_prompt` helper.
4. Asserts on the rendered prompt string directly.

**Finding-level assertions** (Plan 01 contract):
- Exactly 2 `score_timeline` findings per window.
- Order: `{"part": "endgame"}` first, then `{"part": "non_endgame"}`.

**Prompt-level assertions** (Plan 01 emitter + Plan 03 prompt text):
- Exactly 1 `### Subsection: score_timeline` header (both windows render inline under one header, not duplicated per-window).
- Exactly 1 `[summary score_gap | part=endgame]` block + exactly 1 `[summary score_gap | part=non_endgame]` block.
- Both per-part all_time series blocks present with `weekly` granularity:
  - `[series score_gap, all_time, weekly, part=endgame]`
  - `[series score_gap, all_time, weekly, part=non_endgame]`
- No `monthly` granularity for score_timeline (Plan 01 W7 guard).
- No `score_gap_timeline` anywhere (Plan 01 rename complete).
- No `Framing rule` substring (Plan 03 deletion complete).
- The bare `[summary score_gap]` aggregate still emits under `### Subsection: overall` (Plan 01 explicit preservation of the authoritative aggregate).

**`[summary score_timeline]` count assertion (PLAN B4 option c):** the PLAN text asked for a count of `[summary score_timeline]` blocks at 2-per-window. The emitter format is actually `[summary <metric> | <dim>]` where `<metric> = score_gap` — it never literally emits `[summary score_timeline]`. The test instead asserts the realised B4-option-c shape: two per-part summary blocks under one subsection header. A comment in the test reconciles the plan wording with the emitter reality so future readers are not confused.

### 2. Stale `endgame_v12` literal fix (Rule 1 auto-fix)

Plan 03 bumped `_PROMPT_VERSION` from `endgame_v12` to `endgame_v13` and claimed "all nine existing `endgame_v12` string literals across the test suite were also bumped". Three occurrences in `tests/test_insights_router.py` were missed:

- Line 53: `_sample_report` default `prompt_version`.
- Line 252: cache-hit fixture seed.
- Line 387: tier-2 fallback fixture seed.

Result: `tests/test_insights_router.py::TestHappyPath::test_cache_hit_returns_200` failed because the cache lookup filters by `prompt_version=endgame_v13` and the seeded row had `endgame_v12`, making the cache miss instead of hit. **Auto-fixed as Rule 1 (bug)** since this directly blocked the full test suite from passing.

### 3. CHANGELOG bullet (Task 2)

Appended under `## [Unreleased]` → `### Changed` in `CHANGELOG.md`:

> - Phase 68: Endgame tab now shows a dual-line "Endgame vs Non-Endgame Score over Time" chart (both absolute Score series, with a shaded band between them, green when endgame leads, red when it trails) in place of the old single-line "Score Gap over Time" chart. The backend subsection was renamed from `score_gap_timeline` to `score_timeline` and now emits two `[series score_gap, part=endgame|non_endgame]` blocks under two per-part `[summary score_gap]` blocks per window. Prompt bumped to `endgame_v13`, dropping the now-redundant `score_gap` framing rule (the two-line chart makes gap composition self-evident). The info popover drops the "Score Gap is a comparison, not an absolute measure" caveat.

No em-dashes used (per CLAUDE.md style rule). Mentions every required element: dual-line chart, prompt bump to `endgame_v13`, old Score Gap chart removed.

## Deviations from Plan

**Rule 1 — Auto-fixed bug: stale `endgame_v12` literals in `tests/test_insights_router.py`.**

- **Found during:** Task 1 full-suite pytest run.
- **Issue:** `tests/test_insights_router.py::TestHappyPath::test_cache_hit_returns_200` failed with `assert 'fresh' == 'cache_hit'`. Root cause: the test seeds a `LlmLog` row with `prompt_version="endgame_v12"` but the production code now computes the cache key with `endgame_v13` (Plan 03 bump). Cache lookup missed.
- **Fix:** Bumped three `endgame_v12` → `endgame_v13` literals in the router test file. Plan 03's SUMMARY explicitly claimed to have done this across all nine sites, but overlooked this file.
- **Files modified:** `tests/test_insights_router.py`.
- **Commit:** `8b6e5bd` (bundled with Task 1 since it's a one-file blocking fix).

**Rule 3 — Plan wording vs emitter reality: `[summary score_timeline]` count assertion.**

- **Found during:** Task 1 initial TDD run (RED).
- **Issue:** PLAN.md §objective asked for `rendered.count("[summary score_timeline]")` = 2/window. The emitter format is `[summary <metric> | <dim>]` where `<metric> = score_gap` — there is no literal `[summary score_timeline]` string anywhere in the emitted prompt body. Plan 01's SUMMARY example output confirms this (`[summary score_gap | part=endgame]` + `[summary score_gap | part=non_endgame]`).
- **Fix:** Kept the spirit of the assertion (two per-part summary blocks under one `### Subsection: score_timeline` header, both windows rendered inline) while matching the real emitter format. The test has an inline comment reconciling the PLAN wording with the emitter's contract.

**Pre-existing out-of-scope failure:** `tests/test_reclassify.py::TestBackfillGame::test_backfill_updates_null_material_count_to_nonnull` fails with a foreign-key `IntegrityError` on the test fixture (games row inserted before user row commits). Confirmed pre-existing on the Phase 68 wave-3 base commit `71b583e` by running the test against a fresh checkout. Plan 01 SUMMARY already used `--ignore=tests/test_reclassify.py` in its verification runs for the same reason. Logged to `.planning/phases/68-endgame-score-timeline-dual-line-shaded-gap/deferred-items.md`.

## Follow-ups

- **Milestone close:** CHANGELOG bullet is ready. At v1.11 milestone close, rename `## [Unreleased]` → `## [v1.11] <title> — <date>` and create the git tag + GitHub release per CLAUDE.md §Per-milestone instructions.
- **Phase 69+ (opt-in):** rename the backend helper `_compute_score_gap_timeline` → `_compute_score_timeline` + its docstring reference in `_series_granularity` to close the remaining three incidental `score_gap_timeline` references in `app/services/{endgame_service,insights_llm}.py`. These never reach the LLM, so the cleanup is cosmetic.

## Verification

- `uv run pytest tests/services/test_insights_service.py tests/services/test_insights_service_series.py tests/services/test_insights_llm.py -x` — **106 passed**.
- `uv run pytest --ignore=tests/test_reclassify.py -x` — **1057 passed**.
- `uv run ruff check app/ tests/` — clean.
- `uv run ty check app/ tests/` — clean.
- `cd frontend && npm test -- --run` — **106 passed** (9 files).
- `cd frontend && npm run lint` — clean.
- `cd frontend && npm run build` — clean (1849.49 KiB PWA precache, 11 entries).
- `cd frontend && npm run knip` — clean.
- `grep -rn "score_gap_timeline" app/ tests/ frontend/src/` — only the documented incidental references remain (`_compute_score_gap_timeline` helper name + its Plan-01 carve-out docstring + `_PROMPT_VERSION` v13 change comment + one test-fixture local variable name + one forbidden-substring literal inside my new test). **Zero occurrences in `frontend/src/`.** Zero in the prompt file itself.
- `grep -n "Phase 68" CHANGELOG.md` — 1 match.
- `grep -n "endgame_v13" CHANGELOG.md` — 1 match.
- PCRE em-dash check on the Phase 68 line: zero matches.

## Self-Check: PASSED

- `8b6e5bd` (Task 1 commit) — FOUND in `git log --oneline`.
- `b57104d` (Task 2 commit) — FOUND in `git log --oneline`.
- `tests/services/test_insights_service_series.py` — FOUND, `TestScoreTimelineIntegration` class + `test_score_timeline_end_to_end_payload` method present.
- `tests/test_insights_router.py` — FOUND, three `endgame_v12` literals bumped to `endgame_v13`.
- `CHANGELOG.md` — FOUND, Phase 68 bullet present under `## [Unreleased]` → `### Changed` at line 28.
- `.planning/phases/68-endgame-score-timeline-dual-line-shaded-gap/deferred-items.md` — FOUND.
