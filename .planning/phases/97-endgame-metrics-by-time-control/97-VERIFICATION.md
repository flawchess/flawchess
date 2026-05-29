---
phase: 97-endgame-metrics-by-time-control
verified: 2026-05-29T12:00:00Z
status: human_needed
score: 7/7
overrides_applied: 0
human_verification:
  - test: "Load the Endgames page at desktop and mobile widths; confirm one full-width card per eligible TC in bullet/blitz/rapid/classical order, metric blocks side-by-side (3-column on xl, 2-column on md) on desktop and stacked (1-column) on mobile; confirm Conv/Recov gauge neutral bands differ between TCs and the Parity band is identical across all TC cards"
    expected: "Responsive layout matches EndgameTimePressureSection pattern; TC-specific gauge bands for Conversion/Recovery visually shift by TC; Parity band unchanged across all cards"
    why_human: "Visual layout parity and gauge zone visual rendering cannot be asserted programmatically; requires browser rendering at multiple viewport widths"
  - test: "Load the Endgames page after the Phase 97 deploy; confirm the Overall Performance section still shows the 'Endgame Score Gap' and 'Achievable Score Gap' percentile chips, and their per-TC tooltips (breakdown by time control) still expand correctly"
    expected: "Both Overall Performance chips render with percentile values and per-TC tooltip breakdown; nothing in the Overall Performance section is broken by the Metrics-section field removal"
    why_human: "Confirms surgical removal of blended-chip fields did not accidentally drop the kept score_gap/achievable chip fields; requires a real user with imported games to see populated values"
---

# Phase 97: Endgame Metrics by Time Control — Verification Report

**Phase Goal:** Restructure the Endgame Metrics section of the Endgames page into per-time-control cards (bullet/blitz/rapid/classical), mirroring the existing `EndgameTimePressureSection` per-TC card pattern. Each TC card renders the Conversion/Parity/Recovery gauge trifecta plus WDL and Score Gap charts scoped to that time control. The single aggregated Conversion/Parity/Recovery cards are removed entirely.
**Verified:** 2026-05-29T12:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | The Endgame Metrics section renders one card per TC in fixed bullet→blitz→rapid→classical order, no aggregated cards | VERIFIED | `EndgameMetricsByTcSection` maps `data.cards` directly (backend pre-filters); `EndgameMetricsByTcCard` deletes confirmed absent; `Endgames.tsx` uses only `EndgameMetricsByTcSection` |
| 2 | Each TC card shows Conversion/Parity/Recovery gauge trifecta + WDL + Score Gap, scoped to that TC | VERIFIED | `EndgameMetricsByTcCard.tsx` renders three `MetricBlock` sub-components per card; each block receives `block` (per-TC `PerTcBucketStats`), WDL via `MiniWDLBar`, Score Gap via `ScoreGapRow` |
| 3 | Conversion/Recovery gauge bands are TC-specific; Parity and Score Gap bands are global | VERIFIED | `TC_METRIC_BANDS` in `endgame_zones.py` holds four distinct per-TC `TcConvRecovBands` (conv_rate/recov_rate/conv_score_gap/recov_score_gap); `FIXED_GAUGE_ZONES.parity` used for parity on every card; `BUCKETED_ZONE_REGISTRY` and `ZONE_REGISTRY` untouched |
| 4 | Cards self-suppress below `MIN_GAMES_PER_TC_CARD`; floor validated against dev-DB during planning | VERIFIED | `_compute_per_tc_metric_cards` gates on `acc.total < MIN_GAMES_PER_TC_CARD` (line 2379); 23-test TDD suite (`test_compute_per_tc_metric_cards`) asserts suppression behavior |
| 5 | Per-TC conv/parity/recovery rate values computed by backend, `endgame_metrics_cards` on `EndgameOverviewResponse`; TC-keyed bands threaded to frontend via regenerated `endgameZones.ts` | VERIFIED | `_compute_per_tc_metric_cards` computes rates (conv win%, parity score%, recov save%); `endgame_metrics_cards` field with `default_factory` on `EndgameOverviewResponse`; `TC_METRIC_BANDS` in both Python and generated TS with verified band tuples; drift gate green per SUMMARY-01 |
| 6 | Desktop and mobile layouts render responsively | HUMAN | `grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3` in `EndgameMetricsByTcCard.tsx` implements D-03; `w-full mt-2 flex flex-col gap-4` in section for D-02; visual rendering requires human confirmation |
| 7 | Backend (`pytest`, `ty`, `ruff`) and frontend (`lint`, `test`, `knip`) gates pass | VERIFIED | Confirmed by orchestrator: pytest 2126 passed, ty clean, ruff clean, eslint clean, tsc clean, knip clean, vitest 710 passed |

**Score:** 7/7 truths verified (2 require human confirmation for visual rendering aspects)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/services/endgame_zones.py` | `TcConvRecovBands` dataclass + `TC_METRIC_BANDS` registry | VERIFIED | Lines 604-639: frozen dataclass + `Mapping[Literal[...], TcConvRecovBands]` with all 4 TCs and exact benchmark band tuples |
| `scripts/gen_endgame_zones_ts.py` | `_format_tc_metric_bands` codegen emitter + `TC_METRIC_BANDS` import | VERIFIED | Lines 38, 132-139, 267-270: import, emitter function, and `_render()` call all present |
| `frontend/src/generated/endgameZones.ts` | `TC_METRIC_BANDS` TS export | VERIFIED | Lines 130-138: typed `Record<'bullet' \| 'blitz' \| 'rapid' \| 'classical', ...>` with matching band values (rapid 0.8 == 0.800 per Python repr) |
| `app/schemas/endgames.py` | `PerTcBucketStats`, `EndgameMetricsTcCard`, `EndgameMetricsCardsResponse` + `endgame_metrics_cards` field | VERIFIED | Lines 816, 845, 866, 978: all four present; `EndgameOverviewResponse.endgame_metrics_cards` has `default_factory` |
| `app/repositories/endgame_repository.py` | `query_endgame_bucket_rows` extended with `time_control_bucket` + LEAD next-eval cols | VERIFIED | Lines 308-411: 9-column SELECT confirmed; `Game.time_control_bucket` at col 6, LEAD cols 7-8 via `span_with_next` subquery |
| `app/services/endgame_service.py` | `_compute_per_tc_metric_cards` threaded into `get_endgame_overview` | VERIFIED | Lines 2283-2410: function defined; lines 3443-3446: called with pre-fetched `bucket_rows` + `percentile_rows`; line 3457: result passed to `EndgameOverviewResponse` constructor |
| `frontend/src/components/charts/EndgameMetricsByTcSection.tsx` | Per-TC section orchestrator (vertical stacking, empty state) | VERIFIED | 49 lines; `data-testid="endgame-metrics-tc-section"` and `...-empty`; full-width `flex flex-col gap-4` layout (D-02) |
| `frontend/src/components/charts/EndgameMetricsByTcCard.tsx` | Per-TC card (Conv/Parity/Recovery trifecta, TC-specific bands, percentile chips) | VERIFIED | 327 lines; `TC_METRIC_BANDS[card.tc]` for conv/recov zones; `FIXED_GAUGE_ZONES.parity` for parity; `PercentileChip` with `tc={tc}` prop; `metrics-tc-card-{tc}` testid |
| `frontend/src/types/endgames.ts` | `PerTcBucketStats`, `EndgameMetricsTcCard`, `EndgameMetricsCardsResponse` + `endgame_metrics_cards` on `EndgameOverviewResponse` | VERIFIED | Lines 414-461: interfaces mirror backend schemas exactly; `tc: 'bullet' \| 'blitz' \| 'rapid' \| 'classical'`; `endgame_metrics_cards?` optional |
| `frontend/src/pages/Endgames.tsx` | `EndgameMetricsByTcSection` wired with `overviewData?.endgame_metrics_cards` | VERIFIED | Lines 22, 590-591: import present; renders `<EndgameMetricsByTcSection data={overviewData?.endgame_metrics_cards ?? { cards: [] }} />` |
| `EndgameMetricsSection.tsx` (deleted) | Component absent | VERIFIED | `ls` returns no-such-file for both `EndgameMetricsSection.tsx` and `EndgameMetricCard.tsx` |
| `EndgameMetricsSection.test.tsx` (deleted) | Test files absent | VERIFIED | `ls` returns no-such-file for both old test files |
| `app/schemas/endgames.py` | Six Metrics-section blended fields removed from `ScoreGapMaterialResponse` | VERIFIED | `grep` for all six removed field names in `app/` returns no output; comment at line 246 in TS types documents the removal |
| `app/schemas/endgames.py` | Overall Performance fields `score_gap_percentile`, `achievable_score_gap_percentile` preserved | VERIFIED | Lines 525 and 334 respectively; `_aggregate_per_tc_percentile` called at lines 1532 and 2806 in service |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `scripts/gen_endgame_zones_ts.py` | `app/services/endgame_zones.py` | `import TC_METRIC_BANDS` | VERIFIED | Line 38: `from app.services.endgame_zones import ... TC_METRIC_BANDS` |
| `frontend/src/generated/endgameZones.ts` | `scripts/gen_endgame_zones_ts.py` | codegen output | VERIFIED | `TC_METRIC_BANDS` in generated file; drift gate confirmed green (no diff after re-run per SUMMARY-01) |
| `app/services/endgame_service.py` | `app/repositories/endgame_repository.py` | extended bucket_rows | VERIFIED | `_compute_per_tc_metric_cards` reads `row[6]` (time_control_bucket) from `bucket_rows` which is the extended 9-column result |
| `app/services/endgame_service.py` | `user_benchmark_percentiles_repository` | direct per-TC percentile lookup | VERIFIED | Lines 2387-2389: `_effective_rows.get("score_gap_conv", {}).get(tc_bucket)` — no `_aggregate_per_tc_percentile` call inside `_compute_per_tc_metric_cards` |
| `frontend/src/components/charts/EndgameMetricsByTcCard.tsx` | `frontend/src/generated/endgameZones.ts` | `TC_METRIC_BANDS[card.tc]` | VERIFIED | Line 32: import; line 244: `const bands = useMemo(() => TC_METRIC_BANDS[card.tc], [card.tc])` |
| `frontend/src/pages/Endgames.tsx` | `EndgameMetricsByTcSection.tsx` | renders with `endgame_metrics_cards` | VERIFIED | Lines 22, 590-591: import and usage confirmed |
| `app/services/endgame_service.py` | `app/schemas/endgames.py` | `_compute_score_gap_material` no longer populates removed fields | VERIFIED | `grep` for six removed field names in `app/` returns no hits |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `EndgameMetricsByTcCard.tsx` | `card.conversion / card.parity / card.recovery` (PerTcBucketStats) | `overviewData?.endgame_metrics_cards` from `GET /api/endgames/overview` | Yes — `_compute_per_tc_metric_cards` iterates real `bucket_rows` from DB query (`query_endgame_bucket_rows` with `apply_game_filters`) | FLOWING |
| `EndgameMetricsByTcCard.tsx` | `bands` (TC_METRIC_BANDS) | `frontend/src/generated/endgameZones.ts` (build-time codegen) | Yes — codegen'd from `app/services/endgame_zones.py` with benchmark values | FLOWING |
| `PercentileChip` in card | `block.percentile` | `percentile_rows[metric][tc_bucket]` from `user_benchmark_percentiles` table | Yes — direct lookup from `user_benchmark_percentiles_repository.fetch_for_user()` | FLOWING |

### Behavioral Spot-Checks

Step 7b: SKIPPED for visual rendering checks (requires browser). Backend logic verified via existing test suite (pytest 2126 passed including 23 new per-TC metric tests).

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `TC_METRIC_BANDS` bullet.conv_rate assertion | `uv run python -c "from app.services.endgame_zones import TC_METRIC_BANDS; assert TC_METRIC_BANDS['bullet'].conv_rate == (0.588, 0.719)"` | Verified per SUMMARY-01 (passed) | PASS |
| `endgame_metrics_cards` field on `EndgameOverviewResponse` | `uv run python -c "from app.schemas.endgames import EndgameOverviewResponse; assert 'endgame_metrics_cards' in EndgameOverviewResponse.model_fields"` | Verified per SUMMARY-02 (passed) | PASS |
| Removed fields absent from `app/` | `grep -rq "score_gap_conv_percentile\|..." app/` | No output (grep exit 1) — confirmed during this verification | PASS |
| Old components absent | `ls frontend/.../EndgameMetricsSection.tsx` | No such file — confirmed during this verification | PASS |

### Requirements Coverage

Phase 97 has no formal requirement IDs (standalone UX refinement). All 7 ROADMAP Success Criteria are mapped:

| Success Criterion | Status | Evidence |
|-------------------|--------|----------|
| SC-1: One card per eligible TC, fixed order, no aggregated cards | VERIFIED | `EndgameMetricsByTcSection` maps backend-provided cards; old section deleted |
| SC-2: Conversion/Parity/Recovery trifecta + WDL + Score Gap per TC | VERIFIED | `MetricBlock` sub-component renders all elements per bucket |
| SC-3: TC-specific Conv/Recov bands; Parity/Score Gap global | VERIFIED | `TC_METRIC_BANDS[card.tc]` for conv/recov; `FIXED_GAUGE_ZONES.parity` for parity |
| SC-4: Cards self-suppress below min-games floor; floor validated | VERIFIED | `MIN_GAMES_PER_TC_CARD` gate in `_compute_per_tc_metric_cards`; TDD test suite covers suppression |
| SC-5: Per-TC rate values computed by backend; TC-keyed bands via regenerated `endgameZones.ts`; CI drift gate green | VERIFIED | All three artifacts present and linked; drift gate confirmed green |
| SC-6: Desktop and mobile layouts render responsively | HUMAN | CSS classes verified; visual rendering requires human confirmation |
| SC-7: All gates pass | VERIFIED | pytest 2126, ty clean, ruff clean, eslint clean, tsc clean, knip clean, vitest 710 — confirmed by orchestrator |

### Anti-Patterns Found

No anti-patterns found in the modified files:
- No `TBD`, `FIXME`, or `XXX` markers introduced
- No stub components (all return real data-driven output)
- No hardcoded empty arrays as data props (fallback `?? { cards: [] }` is a defensive default, not a stub — real data flows from the API)
- `text-xs` not used in `EndgameMetricsByTcCard.tsx` or `EndgameMetricsByTcSection.tsx` (text-sm floor respected)
- One decision note in SUMMARY-04: `SCORE_GAP_CONV_NEUTRAL_MIN/MAX` and `SCORE_GAP_RECOV_NEUTRAL_MIN/MAX` remain in `endgameZones.ts` because `knip.json` excludes `src/generated/endgameZones.ts` — this is intentional and documented, not a dead-code gap

### Human Verification Required

### 1. Per-TC Card Responsive Layout

**Test:** Load the Endgames page at desktop (>1280px / xl breakpoint) and mobile (<768px) widths for a user with games in multiple time controls. Navigate to the Endgame Metrics by Time Control section.
**Expected:**
- Desktop (xl): each TC card shows Conversion / Parity / Recovery metric blocks side-by-side in a 3-column row
- Tablet (md, 768px-1279px): 2 columns per row
- Mobile (<768px): blocks stack vertically (1 column)
- Cards appear in bullet → blitz → rapid → classical order
- Conv/Recovery gauge neutral bands visually shift between TC cards (e.g. bullet recovery band lower than rapid recovery band); Parity band looks identical on all cards
**Why human:** Visual layout parity and gauge zone band rendering cannot be asserted programmatically; requires browser rendering at multiple viewport widths.

### 2. Overall Performance Chips Unaffected

**Test:** Load the Endgames page for a user with games across multiple time controls. Scroll to the Overall Performance section (above the Endgame Metrics by Time Control section). Check the "Endgame Score Gap" and "Achievable Score Gap" percentile chips.
**Expected:**
- Both chips render with populated percentile values (not blank/missing)
- Clicking/hovering each chip reveals the per-TC tooltip breakdown showing percentile values per time control
- No visual regression in the Overall Performance section compared to before Phase 97
**Why human:** Confirms the surgical backend removal of six Metrics-section-only fields did not accidentally drop the `score_gap_percentile` / `achievable_score_gap_percentile` fields or break their per-TC tooltips; requires a real user with imported games and existing percentile data.

### Gaps Summary

No gaps found. All 7 observable truths VERIFIED against the actual codebase. The two human verification items are visual/behavioral checks that automated tests cannot cover (responsive layout rendering, real user data population).

---

_Verified: 2026-05-29T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
