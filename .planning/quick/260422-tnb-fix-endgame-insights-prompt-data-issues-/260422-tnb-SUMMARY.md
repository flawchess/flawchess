---
phase: 260422-tnb
plan: 01
completed: 2026-04-22
commits:
  - f6af27e
  - 7343171
files_modified:
  - app/services/insights_service.py
  - app/services/insights_llm.py
  - app/services/insights_prompts/endgame_v1.md
  - tests/services/test_insights_service.py
  - tests/services/test_insights_llm.py
  - tests/test_insights_router.py
---

# 260422-tnb — Fix endgame insights prompt & data issues — Summary

## One-liner

Fixed the endgame insights pipeline so the LLM receives clean, semantically consistent data — bucket-matched metric emission (no 3×3 fan-out), NaN/thin filtering, server-side metadata override, auto-generated zone-threshold appendix, prompt-version bumped to `endgame_v2` for cache invalidation.

## Commits

| # | Hash | Type | Description |
|---|------|------|-------------|
| 1 | `f6af27e` | fix | Data-emission + prompt-assembly fixes (A1-A5, C1-C3) |
| 2 | `7343171` | feat | System prompt v2 rewrite + zone threshold appendix (B1-B6) |

## Changes

### Task 1 (commit f6af27e)

**`app/services/insights_service.py`** — A1 fix
- Added module-level `_BUCKET_TO_METRIC: dict[MaterialBucket, BucketedMetricId]`.
- Imported `BucketedMetricId` from `endgame_zones`.
- Rewrote `_findings_endgame_metrics` so each `MaterialRow` emits exactly ONE finding whose metric matches the row's bucket (conversion → conversion_win_pct, parity → parity_score_pct, recovery → recovery_save_pct). Eliminates the old 3×3 fan-out that produced self-contradictory rows like `parity_score_pct | [bucket=conversion]` and caused the LLM to hallucinate "parity score rates are strong" from conversion-bucket data. Empty-bucket branch collapses from three empty findings to one.
- For a user with 3 non-zero material rows: emits 4 findings (1 endgame_skill + 3 bucket-matched), not 10.

**`app/services/insights_llm.py`** — A2, A3, A4, A5, C1, C2, C3 + B2 scaffolding
- Added `import math` and `from collections import OrderedDict`.
- Added constants: `MIN_BUCKET_N=3`, `_ACTIVITY_GAP_DAYS=90`, `_ALL_TIME_CUTOFF_DAYS=90`, `_SKIPPED_SUBSECTIONS={"time_pressure_vs_performance"}`.
- Bumped `_PROMPT_VERSION = "endgame_v1"` → `"endgame_v2"` (cache invalidation).
- Added `_build_zone_threshold_appendix()` helper at module load. `_SYSTEM_PROMPT` now = raw `endgame_v1.md` content + auto-generated `## Zone thresholds` markdown (sourced from `ZONE_REGISTRY` + `BUCKETED_ZONE_REGISTRY`). Appendix is deterministic and kept out of the md file because threshold changes propagate through `findings_hash` (zones are baked into findings), not prompt_version.
- Rewrote `_assemble_user_prompt`:
  - Drops findings where `subsection_id ∈ _SKIPPED_SUBSECTIONS` (A5: time_pressure_vs_performance).
  - Drops findings with NaN value OR (`sample_size=0 AND sample_quality="thin"`) (A2).
  - Groups findings by `subsection_id` under ONE header, using `OrderedDict` to preserve first-seen order (C1).
  - Parenthesises parent_subsection_id on the header when any member has a parent.
  - Series rendering: filters points with `n < MIN_BUCKET_N` (A4); when an `all_time` series has a `last_3mo` twin for the same `(metric, subsection_id)`, drops `all_time` points within the last 90 days (C2); inserts `# Activity gap: DATE_A → DATE_B` comment lines between retained points more than 90 days apart (C3).
- `generate_insights` now overrides `report.model_used` and `report.prompt_version` via `model_copy(update=...)` AFTER `_run_agent` returns successfully and BEFORE `create_llm_log` — so both the user-facing response AND the persisted log row carry the authoritative server values. Eliminates the fabricated "gpt-4o" seen in Gemini outputs (A3).

**Tests**
- `tests/services/test_insights_service.py` (+168 lines): new `TestFindingsEndgameMetrics` class with 6 tests covering: exactly 4 findings for 3 non-empty rows, no cross-bucket fan-out, empty-bucket emits one empty finding, per-bucket value formulas (conversion = win/100, parity = score, recovery = (win+draw)/100).
- `tests/services/test_insights_llm.py`: 4 new prompt-assembly tests (NaN drop, grouping, sparse series filter, `time_pressure_vs_performance` skip), 1 new metadata-override integration test (seeds a fabricated report, asserts both response and log row show `endgame_v2` + configured model), fixture `_sample_report` bumped to `endgame_v2`, `test_system_prompt_loaded_from_file` updated to assert `startswith(file_contents) + "## Zone thresholds" in _SYSTEM_PROMPT`.
- `tests/test_insights_router.py`: bulk-replaced `"endgame_v1"` → `"endgame_v2"` in seeded fixture rows so router cache-hit/rate-limit tests still match the new prompt_version filter in `get_latest_log_by_hash` / `get_latest_report_for_user`.

### Task 2 (commit 7343171)

**`app/services/insights_prompts/endgame_v1.md`** — full rewrite (file name retained per plan)
- Header updated: "System Prompt v2".
- Top comment documents that file name stays `endgame_v1.md`; `_PROMPT_VERSION` in `insights_llm.py` is the authoritative cache key.
- **B1**: single overview rule — 1-2 short paragraphs totalling ≤150 words. Removed the contradiction between the old line 8 (single paragraph) and old line 27 (1-2 paragraphs).
- **A3**: removed both "echo back" instructions from the output contract. Notes that `model_used` / `prompt_version` placeholders will be server-overridden.
- **B3**: tightened trend-strength guidance — reject trend claims from a single bucket or mostly-n<5 buckets, require sum-of-last-3-4 `n` ≥ 20, honor `# Activity gap` comments by treating adjacent segments independently. Also notes that points with `n<3` are pre-filtered (matches A4).
- **B4**: added TC-weighting caveat to `avg_clock_diff_pct` glossary entry — do not attribute the deficit/surplus to a single time control unless a `time_control` filter is set.
- **B5**: rewrote bucketed-metric glossary entries so each says "Tied to exactly one bucket" (conversion_win_pct → conversion, parity_score_pct → parity, recovery_save_pct → recovery). Removed the misleading "Bucketed like conversion_win_pct" lines that implied the same metric applied to multiple buckets.
- **B6**: added `## Subsection → section_id mapping` section with a table mapping each input subsection to its output section_id, plus a note that `time_pressure_vs_performance` is frontend-only.

## Verification

- `uv run ruff check .` → **All checks passed**
- `uv run ty check app/ tests/` → **All checks passed**
- `uv run pytest tests/services/test_insights_llm.py tests/services/test_insights_service.py tests/services/test_insights_service_series.py tests/test_insights_router.py` → **88 passed** (1.42s)
- `grep -c "echo back" app/services/insights_prompts/endgame_v1.md` → `0` ✓
- `grep -c "Zone thresholds" app/services/insights_llm.py` → `1` ✓
- `grep -c "Subsection → section_id mapping" app/services/insights_prompts/endgame_v1.md` → `1` ✓
- `python -c "from app.services.insights_llm import _SYSTEM_PROMPT; ..."` → len=10519, contains "## Zone thresholds", contains bucketed `conversion_win_pct` bands

## Deviations from plan

**None** — the plan was executed as written. A few notes on local adjustments needed to make tests pass:

1. **Router-test cache pollution**: `TestMetadataOverride` initially used `findings_hash="m" * 64` — the same literal router tests leave behind (they do not teardown users on the `authed_user_with_session` fixture and the tier-1 cache-lookup query does not filter by `user_id`). Switched the test to generate a per-call `uuid.uuid4().hex + uuid.uuid4().hex` hash so the test is hermetic. This is a test-only fix; the service behavior was always correct.
2. **`n=1` substring match**: initial assertion `assert "n=1" not in prompt` matched `(n=10)`. Tightened to `assert "(n=1)" not in prompt` to pinpoint the exact token.
3. **ty-suppress style**: ty does not understand mypy's `# type: ignore[arg-type]` — used `from typing import cast; metric=cast(MetricId, metric)` instead in a test factory helper.
4. **Ripple from prompt_version bump**: updated `tests/test_insights_router.py` fixtures from `endgame_v1` → `endgame_v2` so router cache-hit and stale-fallback tests still observe the seeded rows. Intentional per plan (prompt-version bump is the cache-invalidation mechanism).

## Tests: before and after

- Before: 942-ish passing (pre-existing 8 `test_reclassify.py` failures unrelated to this task — confirmed by stash/pop on clean base).
- After: 1024 passing + same 8 pre-existing failures (out of scope; DB integrity violations from accumulated dev DB state, not touched by this change).

## Known stubs

None. All removed "echo back" instructions were replaced by server-side overrides; all filtered findings (NaN, thin, time_pressure_vs_performance) are documented as intentional rather than stubbed. The placeholder `server-overridden` strings the LLM is now instructed to emit for `model_used` / `prompt_version` are discarded by the server on every call.

## Impact

- **Cache invalidation**: all previously cached endgame reports tier-1 miss on next call (prompt_version `endgame_v1` → `endgame_v2`). Users pay a one-time fresh-miss cost (rate-limited to 3/h per user). Intentional; old reports were generated from the broken prompt.
- **LLM data quality**: user prompt now carries 4 endgame_metrics findings instead of 10 (1 endgame_skill + 3 bucket-matched). NaN rows eliminated. `time_pressure_vs_performance` no longer appears in the prompt (FE chart renders directly). Series drops sparse (n<3) points and flags inactivity gaps.
- **Log auditability**: `llm_logs.response_json.model_used` and `.prompt_version` now always reflect the authoritative server values. Previous rows with fabricated "gpt-4o" strings remain in the DB (read-only history); fresh rows are correct going forward.

## Self-Check: PASSED

- ✓ `f6af27e` visible in `git log --oneline` (task 1)
- ✓ `7343171` visible in `git log --oneline` (task 2)
- ✓ `app/services/insights_service.py` modified — `_BUCKET_TO_METRIC` + dispatch present
- ✓ `app/services/insights_llm.py` modified — `_PROMPT_VERSION="endgame_v2"`, `_build_zone_threshold_appendix`, rewritten `_assemble_user_prompt`, metadata override
- ✓ `app/services/insights_prompts/endgame_v1.md` rewritten — no "echo back", has mapping table
- ✓ Tests: 88 pass across the insights surface
- ✓ Lint + types clean
