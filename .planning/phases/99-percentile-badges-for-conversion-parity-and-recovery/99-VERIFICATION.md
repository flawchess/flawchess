---
phase: 99-percentile-badges-for-conversion-parity-and-recovery
verified: 2026-05-31T00:45:00Z
status: human_needed
score: 5/5
overrides_applied: 0
human_verification:
  - test: "Open the endgame metrics cards for a dev user who has bullet/blitz/rapid data. Confirm each per-TC Conversion, Parity, and Recovery card shows the title-line rate chip (right-aligned, distinct from the ΔES-gap chip on the ScoreGapRow). Confirm classical may suppress when data is thin."
    expected: "Each per-TC card with a qualifying user shows two chips: the existing gap chip near the ΔES score-gap bullet, and a new title-line rate chip. The chips' aria-labels reference different metric nouns (e.g. 'Conversion Rate percentile' vs 'Conversion Score Gap percentile'). Classical rate chips may be absent."
    why_human: "Visual layout correctness, chip coexistence at render time, and title-line right-alignment cannot be verified without a running browser. Automated tests cover render/suppress logic but not pixel layout."
  - test: "On a narrow mobile viewport (< 1024px), confirm the rate chips still render on the per-TC cards and that the ΔES-gap chips are not displaced."
    expected: "Desktop and mobile render the same chip state. MetricBlock is a single shared renderer — no duplicate markup — so both viewports are covered. Rate chip position on the h4 title line should remain right-aligned."
    why_human: "Mobile responsive layout cannot be verified by automated tests. The single-renderer fact is code-confirmed but visual alignment needs a viewport check."
---

# Phase 99: Percentile Badges for Conversion, Parity, and Recovery — Verification Report

**Phase Goal:** Add peer-relative percentile chips (the v1.19 `PercentileChip` primitive) to the per-TC Conversion, Parity, and Recovery rate cards from Phase 97. Requires new per-(metric, TC) cohort CDF materialization in `user_benchmark_percentiles`. 3 rate families × 4 TCs computed via the pooled-per-user methodology in `canonical_slice_sql.py` parameterised by TC, cohort-matched on the per-(user, TC) rating anchor, surfaced with the 4-bullet disclosure tooltip.

**Verified:** 2026-05-31T00:45:00Z
**Status:** human_needed (5/5 automated criteria verified; 2 human UAT items for visual layout)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Each per-TC card renders a rate chip on Conversion/Parity/Recovery, gated on per-(metric, TC) inclusion floor | VERIFIED | `EndgameMetricsByTcCard.tsx` line 165: `block.rate_percentile != null && anchorRating != null` gate; 25/25 frontend tests pass including render + suppress-on-null-percentile + suppress-on-null-anchor |
| 2 | 12 new metrics in ENUM + computed via shared canonical_slice_sql.py builder — CDF/lookup drift impossible | VERIFIED | `benchmark_metric_enum` SAEnum has 23 values (8 + 12 TC-suffixed + 3 bare); 2 Alembic migrations; `_ = source` idiom in all 3 builders; `test_canonical_slice_sql.py` source-parity tests GREEN (313 backend tests pass) |
| 3 | Cohort CDFs generated into global_percentile_cdf.py under the per-(metric, ELO anchor, TC) sliding-window protocol; regen report archived | VERIFIED | `COHORT_PERCENTILE_CDF` keys: conversion_rate (111 anchors), parity_rate (96 anchors), recovery_rate (105 anchors); report at `reports/percentile/cohort-percentile-cdf-latest.md` (116,220 bytes, 2026-05-30 23:40); archived prior report at `reports/archive/cohort-percentile-cdf-latest-2026-05-30-phase-94.4.md` |
| 4 | Chips cohort-matched on per-(user, TC) rating anchor; carry 4-bullet disclosure tooltip with first two bullets TC-scoped | VERIFIED | `PercentileChip` receives `tc={tc}`, `anchorRating={anchorRating}`, `metricLabel={'Conversion Rate'/'Parity Rate'/'Recovery Rate'}`; `PercentileChip.tsx` bullet 1 template: "Your recent {metricLabel} is {phrasing} of ~{anchorRating}-rated players in {tc}"; frontend aria-label tests assert TC + rate noun present |
| 5 | Backfill populates 12 new metrics on dev DB; prod backfill deferred per D-11 (tracked in todos) | VERIFIED | Dev DB has 27 conversion_rate rows, 27 parity_rate rows, 26 recovery_rate rows (MCP-verified per 99-05-SUMMARY); classical = 0 (expected floor suppression, D-05); prod backfill tracked at `.planning/todos/pending/2026-05-31-phase-99-prod-backfill-rate-percentiles.md` |

**Score:** 5/5 truths verified

### parity_rate|classical Suppression (Expected by Design)

`COHORT_PERCENTILE_CDF` has 0 non-suppressed anchors for `parity_rate|classical` (147 benchmark users qualify but max in-window = 49 < 100-user MIN floor). This is correct CDF suppression per D-05, not a defect. Chips suppress silently when the CDF cell is empty — verified by SC-1 gate logic.

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/services/canonical_slice_sql.py` | 3 rate builders + MINIMUM_RATE_BUCKET_SPANS | VERIFIED | `grep -c def per_user_cte_*_rate_tc` = 3; `MINIMUM_RATE_BUCKET_SPANS` count = 7 (def + 3 HAVING + doc refs); `_ = source` idiom present in all 3; no `lead()` in new builders |
| `alembic/versions/20260530_extend_benchmark_metric_for_rate_percentiles.py` | ADD VALUE × 12 TC-suffixed values | VERIFIED | Migration revision `3981239fd391`, `down_revision=c70f5d94b243`; loop pattern with 12 `_rate_` entries |
| `alembic/versions/20260530_220134_52c928794fe7_add_rate_family_names_to_benchmark_metric.py` | ADD VALUE × 3 bare family names | VERIFIED | Revision `52c928794fe7`, `down_revision=3981239fd391`; adds `conversion_rate`, `parity_rate`, `recovery_rate` bare names (Rule 1 fix found during backfill) |
| `app/models/user_benchmark_percentile.py` | SAEnum with 23 values (8 + 12 + 3) | VERIFIED | Lines 81-98 confirm all 12 TC-suffixed + 3 bare family names; module docstring updated for Phase 99 |
| `app/services/global_percentile_cdf.py` | CdfMetricId with 3 rate families; COHORT_PERCENTILE_CDF with 12 rate cells | VERIFIED | `CdfMetricId` lines 112-114: `conversion_rate`, `parity_rate`, `recovery_rate`; `COHORT_PERCENTILE_CDF` keys confirmed via Python import; all non-classical families non-empty |
| `app/schemas/endgames.py` | rate_percentile field trio on PerTcBucketStats, distinct from percentile | VERIFIED | Lines 868-870: `rate_percentile`, `rate_percentile_n_games`, `rate_percentile_value` all `float/int | None = None`; distinct from `percentile*` fields (D-01) |
| `app/services/endgame_service.py` | rate row lookups + _build_per_tc_bucket_stats rate param | VERIFIED | Lines 2677-2700: `conv_rate_row`, `parity_rate_row`, `recov_rate_row` looked up via `_effective_rows.get()`; all 3 passed to `_build_per_tc_bucket_stats`; return threads `rate_percentile*` fields |
| `app/services/user_benchmark_percentiles_service.py` | STAGE_B_METRIC_FAMILIES extended to 10; dispatch arms | VERIFIED | `STAGE_B_METRIC_FAMILIES` is 10-tuple (confirmed by `test_stage_b_metric_families_is_10_tuple`); imports + 3 dispatch arms to rate builders with `source="single_user"` |
| `scripts/gen_global_percentile_cdf.py` | IN_SCOPE_METRICS extended; regen dispatch arms | VERIFIED | `IN_SCOPE_METRICS` confirmed via `python -c ... assert {'conversion_rate',...} <= set(IN_SCOPE_METRICS)`; 3 dispatch arms with `source="benchmark"`; `_METRIC_DISPLAY` has 3 new entries |
| `frontend/src/types/endgames.ts` | rate_percentile field trio in PerTcBucketStats TS interface | VERIFIED | Lines 442-444: `rate_percentile?: number | null`, `rate_percentile_n_games?: number | null`, `rate_percentile_value?: number | null`; optional for backward compat |
| `frontend/src/components/charts/EndgameMetricsByTcCard.tsx` | Title-line rate chip in MetricBlock; w-full fix; single renderer | VERIFIED | Lines 165-190: chip wired with `block.rate_percentile != null && anchorRating != null` gate, `ml-auto inline-flex` span, `testId={...rate-percentile-chip}`, `metricLabel` mapping; `w-full` on h4 (line 150); `grep -c 'function MetricBlock\|const MetricBlock'` = 1 |
| `tests/models/test_user_benchmark_percentile.py` | ENUM membership assertions for 12 new rate metrics | VERIFIED | File exists; contains `conversion_rate_bullet`; parametrized test over all 12 new ENUM names; GREEN (313 backend tests pass) |
| `tests/services/test_canonical_slice_sql.py` | Source-parity + floor tests; 3 occurrences | VERIFIED | `grep -c source_parity` = 3; all Wave-0 tests GREEN after Wave-1 symbols landed |
| `tests/services/test_endgame_service.py` | rate_percentile field coexistence tests | VERIFIED | `TestPerTcBucketStatsRatePercentileFields` class with 4 tests; all GREEN |
| `tests/services/test_user_benchmark_percentiles_service.py` | STAGE_B_METRIC_FAMILIES is_10_tuple test | VERIFIED | Test renamed + updated; GREEN |
| `tests/integration/test_benchmark_metric_enum.py` | EXPECTED_ENUM_LABELS updated to 23 | VERIFIED | 23 labels in alphabetical order; GREEN (Postgres ENUM introspection) |
| `frontend/src/components/charts/EndgameMetricsByTcCard.test.tsx` | Rate chip render/suppress/tooltip/coexistence tests | VERIFIED | 25/25 tests pass (previously 5 RED Wave-0 + 20 GREEN; all 25 now GREEN) |
| `tests/scripts/fixtures/global_percentile_cdf/` | 12 new SQL golden fixtures | VERIFIED | All 12 files exist: `{conversion_rate,parity_rate,recovery_rate}__{bullet,blitz,rapid,classical}.sql` |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `EndgameMetricsByTcCard.tsx` | `PercentileChip.tsx` | Second `PercentileChip` instance on title line | WIRED | Line 167: `<PercentileChip` with `rate-percentile-chip` testId; `flavor`, `tc`, `anchorRating`, `metricLabel` all passed; PercentileChip.tsx unchanged (Pitfall 8) |
| `MetricBlock h4` | `block.rate_percentile` | Null-and-anchor gate | WIRED | `block.rate_percentile != null && anchorRating != null` gate at line 165 |
| `endgame_service.py` | `user_benchmark_percentiles_repository.py` | `_effective_rows.get('conversion_rate', {}).get(tc_bucket)` | WIRED | Lines 2677-2679 confirmed; same `fetch_for_user [metric][tc]` nested dict path used by gap rows |
| `user_benchmark_percentiles_service.py` | `canonical_slice_sql.py` | Import + dispatch of 3 rate builders with `source="single_user"` | WIRED | Lines 109-111 import; lines 202-207 dispatch arms |
| `gen_global_percentile_cdf.py` | `canonical_slice_sql.py` | Import + dispatch of 3 rate builders with `source="benchmark"` | WIRED | Lines 100-101 import; lines 319-324 dispatch arms |
| `global_percentile_cdf.py CdfMetricId` | `user_benchmark_percentile.py SAEnum` | 3 rate family names present in both (ty enforces) | WIRED | CdfMetricId has 11 families; SAEnum has 23 values; `uv run ty check app/ tests/` passes |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `EndgameMetricsByTcCard.tsx MetricBlock` | `block.rate_percentile` | `PerTcBucketStats.rate_percentile` threaded by `endgame_service.py` from `_effective_rows.get("conversion_rate", {}).get(tc_bucket)` | Yes — `user_benchmark_percentiles` table with 27/27/26 dev rows (Postgres-verified); null until backfill (chip suppresses) | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Backend rate builder tests green | `uv run pytest tests/services/test_canonical_slice_sql.py tests/models/test_user_benchmark_percentile.py tests/services/test_endgame_service.py tests/services/test_user_benchmark_percentiles_service.py tests/integration/test_benchmark_metric_enum.py -q` | 313 passed | PASS |
| Frontend chip tests green | `cd frontend && npm test -- --run EndgameMetricsByTcCard` | 25 passed (2 test files) | PASS |
| Full backend suite green | `uv run pytest -x -q` | 2191 passed, 16 skipped, 3 warnings | PASS |
| Full frontend suite green | `cd frontend && npm test -- --run` | 742 passed (63 test files) | PASS |
| Type check clean | `uv run ty check app/ tests/` | All checks passed | PASS |
| Frontend lint + knip clean | `cd frontend && npm run lint && npm run knip` | No errors | PASS |
| COHORT_PERCENTILE_CDF has rate families | Python import check | conversion_rate (111), parity_rate (96), recovery_rate (105) non-suppressed anchors | PASS |

---

### Probe Execution

No probes defined for this phase (manual-only SC-3 regen was performed during Plan 05 execution; evidence is the archived regen report).

---

### Requirements Coverage

Phase 99 is standalone (no REQ-IDs). Coverage driven by SC-1..SC-5.

| SC | Description | Status | Evidence |
|----|-------------|--------|---------|
| SC-1 | Per-TC card renders chip, gated on inclusion floor | VERIFIED | Rate chip gate in `EndgameMetricsByTcCard.tsx`; frontend suppress tests GREEN |
| SC-2 | 12 new ENUM metrics + shared canonical_slice_sql.py builder — drift impossible | VERIFIED | SAEnum 23 values; 2 migrations; source-parity tests GREEN; dispatch in both service + regen script |
| SC-3 | Cohort CDFs regenerated into global_percentile_cdf.py; regen report archived | VERIFIED | 12 new cells in COHORT_PERCENTILE_CDF; report at reports/percentile/; archived copy present |
| SC-4 | Chips cohort-matched on per-(user, TC) anchor; 4-bullet tooltip with TC-scoped bullet 1 | VERIFIED | metricLabel + tc props passed to PercentileChip; aria-label tests assert TC + rate noun |
| SC-5 | Dev backfill done; prod backfill deferred per D-11 (tracked) | VERIFIED | 27/27/26 dev rows confirmed; todo file tracking prod backfill at deploy |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app/services/user_benchmark_percentiles_service.py` | 10, 467 | Stale docstring count: "(7-tuple)" should be "(10-tuple)" (REVIEW WR-01, IN-04) | Warning | Misleading to future readers; does not affect behavior |
| `app/services/canonical_slice_sql.py` | 1029-1040 | Recovery builder bucket CASE uses flat structure vs nested form in sibling builders (REVIEW WR-02) | Warning | Logically equivalent; structural divergence is a maintainability trap without documentation |
| `app/models/user_benchmark_percentile.py` | 12 | Docstring says "11 new values" where 3 × 4 = 12 (REVIEW IN-01) | Info | Transcription error in comment; correct value is 12 |
| `tests/integration/test_benchmark_metric_enum.py` | 114 | Stale function name `test_benchmark_metric_enum_has_exactly_four_labels` (REVIEW IN-02) | Info | Misleading test name; test body is correct |

No TBD/FIXME/XXX debt markers found in any modified file. The 2 warnings and 2 info items are documentation-quality issues from the code review, none blocking phase goal achievement.

---

### Human Verification Required

#### 1. Desktop Rate Chip Visual Rendering

**Test:** Run `bin/run_local.sh`, log in as a dev user (one with bullet/blitz/rapid endgame data — check that 27 rows exist for `conversion_rate` in dev DB). Navigate to Endgame Metrics. Open a per-TC card (e.g. blitz). Confirm the Conversion, Parity, and Recovery title lines each show a rate chip right-aligned on the h4 line, distinct from the ΔES-gap chip on the ScoreGapRow bullet below.

**Expected:** Title line shows chip (e.g. "p72 blitz") right-aligned; the ΔES-gap chip further down the card is unchanged. Both chips' tooltips open with distinct bullet 1 copy ("Your recent Conversion Rate X% is in the 72nd percentile of ~1400-rated players in blitz" vs "Your recent Conversion Score Gap is…"). Classical may show no rate chip if the user has < 30 classical endgame spans.

**Why human:** Visual layout correctness and chip positioning cannot be verified by automated tests. The chip gate and data wiring are automated-tested, but the `ml-auto inline-flex` right-alignment and two-chip coexistence in the actual rendered DOM require a browser.

#### 2. Mobile Rate Chip Parity

**Test:** Same as above but with browser devtools viewport set to mobile width (< 1024px). Confirm rate chips render on the mobile layout of the per-TC cards. Confirm the existing ΔES-gap chips are not displaced.

**Expected:** MetricBlock is a single shared renderer — the chip renders on both layouts. The `flex-col lg:flex-row` CSS means cards stack vertically on mobile, but the chip inside MetricBlock's `h4` is layout-independent.

**Why human:** Mobile responsive layout requires visual inspection. The single-renderer fact is verified in code (`grep -c 'function MetricBlock\|const MetricBlock'` = 1) but the visual result on small screens needs a viewport check.

---

### Gaps Summary

No gaps. All 5 success criteria are verified in the codebase. The 2 human verification items are for visual layout confirmation only — the underlying logic, data, and behavior are all automated-tested and GREEN.

**Notable findings from code review (non-blocking):**

The code review (99-REVIEW.md) found 2 warnings (stale docstring counts, recovery builder CASE structure divergence) and 2 info items (comment typo, stale test function name). None affect behavior. These are cleanup candidates for a follow-up or the next phase touching these files.

---

_Verified: 2026-05-31T00:45:00Z_
_Verifier: Claude (gsd-verifier)_
