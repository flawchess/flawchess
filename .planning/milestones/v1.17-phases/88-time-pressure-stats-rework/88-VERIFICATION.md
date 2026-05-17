---
phase: 88-time-pressure-stats-rework
verified: 2026-05-17T00:00:00Z
status: gaps_found
must_haves_verified: 5
must_haves_total: 6
requirement_ids_covered:
  - POLISH-01 (partially — neutral band ships, gating decision deferred to Phase 89)
  - POLISH-03 (partially — data-testid coverage present, full sweep is Phase 89 scope)
gaps:
  - truth: "CR-01: query_cohort_clock_rows runs unfiltered global cohort on every overview request (no apply_game_filters call; no LIMIT/pagination; contradicts CONTEXT D-05 filter-responsive mirror-bucket doctrine; OOM risk at production scale)"
    status: failed
    reason: "endgame_repository.py:878-943 builds an unfiltered, global-population query aggregating ply_array + clock_array for every user except the requester. No time_control/platform/rated/opponent_type filter, no LIMIT, no cache. Contradicts CONTEXT D-05 ('Filter-responsive. Matches Phases 85-87 exactly so the page-wide frame stays consistent.') The docstring explicitly states the opposite of D-05 ('the cohort represents the broader population, not a mirror of the user's own filters'). At production DB scale this is the exact pattern that triggered the Phase 41.1 OOM (FLAWCHESS-3Q). A user filtering to classical-only games will see their delta computed against a cohort dominated by bullet/blitz players."
    artifacts:
      - path: "app/repositories/endgame_repository.py"
        issue: "Lines 878-943: query_cohort_clock_rows has no apply_game_filters call; fetches ALL games for ALL users (minus requester) into Python memory on every /api/endgames/overview request"
      - path: "app/services/endgame_service.py"
        issue: "Line 2415: cohort_rows = await query_cohort_clock_rows(session, exclude_user_id=user_id) — no filter args passed"
    missing:
      - "Either: wire apply_game_filters with user's (time_control, platform, rated, opponent_type) into query_cohort_clock_rows, matching Phases 85-87 mirror-bucket pattern (restores D-05 correctness + removes OOM risk)"
      - "Or: precompute cohort (TC, quintile) -> mean_score at benchmark-calibration time and ship as a constant alongside PRESSURE_BIN_SCORE_NEUTRAL_ZONES (removes live query entirely)"
      - "Or at minimum: add request-scoped cache + MIN_COHORT_GAMES_PER_BIN gate (mitigates availability risk without re-locking the doctrine question — see REVIEW.md CR-01 option (c))"
human_verification:
  - test: "Render the Endgames page with different sidebar filter combinations (e.g. bullet-only, classical-only, rated-only) and check that the Time Pressure card grid appears, shows the correct TC cards, and that score deltas vary as expected across filter changes"
    expected: "4-col (xl) / 2-col (lg) / 1-col (base) card grid renders; TC cards without enough games are hidden; Clock Gap and Score-Delta bullets appear with CI whiskers; sparse quintile bins show dash + 'no games'; low-n bins are dimmed at UNRELIABLE_OPACITY with n=X chip"
    why_human: "Visual rendering, responsive layout, opacity dimming, and interactive filter-response cannot be verified by grep"
  - test: "Verify that a TC card hides entirely when total games for that TC < 20 (MIN_GAMES_PER_TC_CARD), and reappears after importing more games for that TC"
    expected: "Card absent below threshold, present above it"
    why_human: "Requires controlled game-count manipulation or a test account with a known game distribution"
  - test: "Click a MetricStatPopover info button on both a Clock Gap row and a Score-Delta row; verify popover content is correct and popovers are reachable on mobile (375px)"
    expected: "Popover opens with expected copy; tappable on mobile; dismisses correctly"
    why_human: "Interactive UI behavior and mobile tap-target sizing require browser testing"
---

# Phase 88: Time Pressure Stats Rework Verification Report

**Phase Goal:** Replace the legacy time-pressure (line chart) + clock-pressure (clock stats) sections in the Endgames page with a card-grid of 4 per-TC cards — each card showing 1 Clock Gap bullet + 5 Score-Delta bullets per pressure quintile — backed by benchmark-calibrated neutral zones.

**Verified:** 2026-05-17
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Legacy `EndgameClockPressureSection.tsx` deleted; `EndgameTimePressureSection.tsx` is the NEW card-grid orchestrator (not the legacy line chart) | VERIFIED | `ls frontend/src/components/charts/` confirms no `EndgameClockPressureSection.tsx`. `EndgameTimePressureSection.tsx` renders a `grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-4` of `EndgameTimePressureCard` instances. Commit `5706ed09` "delete EndgameClockPressureSection, full suite green". |
| 2 | `data.time_pressure_chart` and `data.clock_pressure` references are gone from Endgames.tsx; replaced by `time_pressure_cards` | VERIFIED | `grep "clock_pressure\|time_pressure_chart" frontend/src/pages/Endgames.tsx` returns nothing. Page correctly reads `overviewData?.time_pressure_cards` (line 284). |
| 3 | `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` has 20 calibrated delta-IQR entries (asymmetric bands, each edge capped at ±0.06); `clock_gap_pct` ZoneSpec uses calibrated (-0.065, +0.047) | VERIFIED | `endgame_zones.py` contains exactly 20 `PressureBinBand` instances. Values are delta-IQR centered near zero (e.g. bullet/Q1: `(-0.0481, 0.0524)`) after the defect-and-fix loop that reverted the incorrect absolute-score-IQR calibration (commits `4f6ebb4b` revert, `af8e246d` recalibration). `clock_gap_pct` ZoneSpec is `(-0.065, 0.047)`. Codegen regenerated (`f12e145d`). |
| 4 | `compute_score_delta_vs_reference` exists in score_confidence.py with documented signature and boundary tests | VERIFIED | Function at line 339 in `app/services/score_confidence.py` with full docstring. Returns `(delta, p_value, ci_low, ci_high)`. N-gates match contract: n=0 → all None, n=1 → CI None, n<10 → p None, n≥10 → all populated. 11 boundary tests in `TestComputeScoreDeltaVsReference` per 88-01-SUMMARY. Wired in `endgame_service.py` line 1565. |
| 5 | Frontend card component renders 1 Clock Gap bullet + 5 Score-Delta bullets per TC with correct sparse handling, triple-gate coloring, and `data-testid` coverage | VERIFIED | `EndgameTimePressureCard.tsx` implements `ClockGapRow`, `QuintileRow`, `EmptyBinRow` sub-components. Sparse handling: `card.total < MIN_GAMES_PER_TC_CARD` → `return null`; `bin.n === 0` → `EmptyBinRow` with dash/no-games; `0 < bin.n < MIN_GAMES_PER_PRESSURE_BIN` → `isDimmed` with `UNRELIABLE_OPACITY`. Triple-gate: `n >= MIN_GAMES_PER_PRESSURE_BIN && isConfident(level) && isInColoredZone`. `data-testid` present on card, bullets, values, info buttons. |
| 6 | Cohort lookup is filter-responsive, uses mirror-bucket per D-05 (same rating × TC × color × opponent-type as user), not a global unfiltered population query | FAILED | `query_cohort_clock_rows` applies no `apply_game_filters` call. The docstring explicitly states "the cohort represents the broader population, not a mirror of the user's own filters." This contradicts CONTEXT D-05 (locked: "Filter-responsive. Matches Phases 85-87 exactly") and creates a production OOM risk. A user filtering to classical games sees their delta compared to an unfiltered global cohort. See CR-01 in REVIEW.md. |

**Score:** 5/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/services/score_confidence.py` | `compute_score_delta_vs_reference` function | VERIFIED | Lines 339-388. Private `_wilson_score_test_vs_ref` helper at lines 124-141. Both correct and well-tested. |
| `app/services/endgame_zones.py` | 20 calibrated `PressureBinBand` entries + `clock_gap_pct` ZoneSpec | VERIFIED | 20 instances confirmed. Delta-IQR semantics correct after recalibration. `clock_gap_pct` at `(-0.065, 0.047)`. |
| `frontend/src/generated/endgameZones.ts` | Regenerated TS constants matching calibrated Python values | VERIFIED | 20 `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` entries (delta-IQR). `CLOCK_GAP_NEUTRAL_MIN=-0.065`, `CLOCK_GAP_NEUTRAL_MAX=0.047`. Codegen drift-gate clean post-recalibration. |
| `frontend/src/lib/pressureBulletConfig.ts` | Domain constants + `clampDeltaCi` + `pressureDeltaZoneColor` | VERIFIED | File exists. `PRESSURE_DELTA_CENTER=0`, `PRESSURE_DELTA_DOMAIN=0.20`, `CLOCK_GAP_DOMAIN=0.30`, both helpers implemented. |
| `frontend/src/components/charts/EndgameTimePressureCard.tsx` | 6-bullet per-TC card with sparse handling | VERIFIED | 297 lines. Three sub-components (`ClockGapRow`, `QuintileRow`, `EmptyBinRow`). All three sparse-handling branches implemented. Triple-gate font coloring present. |
| `frontend/src/components/charts/EndgameTimePressureSection.tsx` | Card-grid orchestrator (replaces legacy line chart) | VERIFIED | Renders `grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-4`. Maps `data.cards` to `EndgameTimePressureCard`. Empty-state message when `data.cards.length === 0`. |
| `frontend/src/types/endgames.ts` | New TS types: `PressureQuintileBullet`, `ClockGapBullet`, `TimePressureTcCard`, `TimePressureCardsResponse` | VERIFIED | All four interfaces defined at lines 225-255. `EndgameOverviewResponse.time_pressure_cards: TimePressureCardsResponse` wired at line 264. Legacy `ClockStatsRow` / `ClockPressureTimelinePoint` types confirmed removed (comment at line 222). |
| `app/schemas/endgames.py` | New Pydantic schemas matching TS types; `EndgameOverviewResponse.time_pressure_cards` present | VERIFIED | `PressureQuintileBullet`, `ClockGapBullet`, `TimePressureTcCard`, `TimePressureCardsResponse` at lines 615-682. `EndgameOverviewResponse.time_pressure_cards: TimePressureCardsResponse` at line 698. |
| `app/repositories/endgame_repository.py` | `query_cohort_clock_rows` function | VERIFIED (exists) / FAILED (doctrine) | Function exists at lines 878-943. However: no `apply_game_filters` call — global unfiltered cohort contradicting D-05. See CR-01. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `endgame_zones.py PRESSURE_BIN_SCORE_NEUTRAL_ZONES` | `endgameZones.ts PRESSURE_BIN_SCORE_NEUTRAL_ZONES` | `scripts/gen_endgame_zones_ts.py` | WIRED | Codegen confirmed drift-clean after recalibration commits `af8e246d` + `f12e145d`. |
| `endgameZones.ts` | `EndgameTimePressureCard.tsx` | import at line 23 | WIRED | Card imports `PRESSURE_BIN_SCORE_NEUTRAL_ZONES`, `CLOCK_GAP_NEUTRAL_MIN`, `CLOCK_GAP_NEUTRAL_MAX`. |
| `score_confidence.compute_score_delta_vs_reference` | `endgame_service._build_quintile_bullets` | import at line 76 | WIRED | Function called at line 1565 with `(w, d, los, n, cohort_score)`. |
| `endgame_service._compute_time_pressure_cards` | `EndgameOverviewResponse.time_pressure_cards` | `compute_endgame_overview` at line 2417 | WIRED | `time_pressure_cards = _compute_time_pressure_cards(clock_rows, cohort_lookup)` returned in overview. |
| `Endgames.tsx` | `EndgameTimePressureSection` | import at line 28 | WIRED | `showTimePressureCards && timePressureCardsData` guard renders the section at line 530-538. |
| `query_cohort_clock_rows` | `apply_game_filters` (user's filter args) | should be inside `query_cohort_clock_rows` | NOT WIRED | CR-01: no filter parameters passed through. Global cohort instead of mirror-bucket. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| `EndgameTimePressureCard` | `card.quintiles[q].delta` | `_build_quintile_bullets` → `compute_score_delta_vs_reference` → `query_clock_stats_rows` | Yes — real user clock/WDL rows from DB | FLOWING (user side) |
| `EndgameTimePressureCard` | `bin.cohort_score` | `_compute_cohort_lookup` → `query_cohort_clock_rows` | Yes — real DB data, but globally unfiltered | HOLLOW (cohort = unfiltered global, not mirror-bucket) |
| `EndgameTimePressureCard` | `card.clock_gap.mean_diff_pct` | `_build_clock_gap` → `compute_paired_difference_test` → `query_clock_stats_rows` | Yes — real user clock diffs | FLOWING |

### Behavioral Spot-Checks

Step 7b skipped — no runnable API server available for spot-check. The backend is not started in this verification context.

### Probe Execution

No `scripts/*/tests/probe-*.sh` files declared in PLAN.md or found in the repo for this phase.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| POLISH-01 | 88-ROADMAP | Per-bucket neutral band decision resolved | PARTIALLY SATISFIED | `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` ships calibrated bands. Full gating-decision sweep is Phase 89 scope per ROADMAP line 379. |
| POLISH-02 | 88-ROADMAP | Gauge significance gating decision | DEFERRED to Phase 89 | Phase 89 owns this per ROADMAP. |
| POLISH-03 | 88-ROADMAP | data-testid + ARIA + semantic HTML | PARTIALLY SATISFIED | `data-testid` coverage on card, bullets, values, info buttons is present. Full sweep across all v1.17 surfaces is Phase 89 scope. |
| POLISH-04 | 88-ROADMAP | Mobile parity at 375px | DEFERRED to Phase 89 | Phase 89 owns the 375px sweep per ROADMAP line 384. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|---------|--------|
| `frontend/src/generated/endgameZones.ts` | 91, 102 | "PLACEHOLDER" in comments on calibrated values | WARNING | Comments claim values are placeholders; they are calibrated. Misleads next reader. IN-02 in REVIEW.md. |
| `frontend/src/components/charts/EndgameTimePressureSection.tsx` | 22 | `aria-labelledby="time-pressure-heading"` with no matching `id="time-pressure-heading"` in codebase | WARNING | Broken ARIA reference. The `<h2>Time Pressure</h2>` in `Endgames.tsx:532` lacks `id="time-pressure-heading"`. Screen readers announce the section with no accessible name. WR-02 in REVIEW.md. |
| `frontend/src/components/charts/EndgameTimePressureCard.tsx` | 140 | `PRESSURE_BIN_SCORE_NEUTRAL_ZONES[tc][bin.quintile_index as 0 \| 1 \| 2 \| 3 \| 4]!` — unsafe cast + non-null assertion, bypassing `noUncheckedIndexedAccess` | WARNING | CLAUDE.md forbids using `!` to suppress `noUncheckedIndexedAccess` errors. Runtime TypeError if backend emits `quintile_index >= 5`. WR-03 in REVIEW.md. |
| `app/services/endgame_service.py` | 1254, 1269, 1270, 1291 | Dead constants: `MIN_GAMES_FOR_CLOCK_STATS`, `NUM_BUCKETS`, `BUCKET_WIDTH_PCT`, `CLOCK_PRESSURE_TIMELINE_WINDOW` — unreferenced after legacy deletion | INFO | Not causing errors, but misleads readers. IN-01 in REVIEW.md. |
| `app/services/endgame_service.py` | 1263 | `MIN_GAMES_PER_PRESSURE_BIN = 5` declared but never used in backend — frontend duplicates it as a magic literal | WARNING | Frontend re-declares the same constant independently with no shared source of truth. Drift risk on future calibration retunes. WR-04 + WR-05 in REVIEW.md. |
| `app/services/insights_service.py` | 963, 977 | `_finding_clock_diff_timeline` and `_finding_time_pressure_vs_performance` return hard-coded empty findings with no sentinel distinguishing "deprecated" from "no data" | WARNING | LLM prompt assembler silently receives empty findings for these subsections on every call. No downstream consumer can distinguish "feature deprecated" from "user has no data". WR-06 in REVIEW.md. |
| `scripts/gen_endgame_zones_ts.py` | 212, 220 | Generator template emits "PLACEHOLDER" comment strings on calibrated values | INFO | Source of the IN-02 misleading comments in the generated file. Fix template, regenerate. |

### Human Verification Required

**1. Visual rendering of the 4-TC card grid at multiple breakpoints**

**Test:** Load the Endgames page in a browser at xl (≥1280px), lg (≥1024px), and base (<1024px) widths. Apply various sidebar filter combinations (all TCs, bullet-only, classical-only).
**Expected:** At xl, up to 4 TC cards render side-by-side; at lg, 2-column; below lg, 1-column. TC cards with <20 games are hidden. Remaining cards show 6 bullet rows each (1 Clock Gap + 5 quintile rows). Section disappears entirely when all TC cards are hidden.
**Why human:** Responsive Tailwind layout, grid reflow, and conditional card visibility are not verifiable by grep.

**2. Sparse-bin rendering: dim + n=X chip vs dash/no-games**

**Test:** Find or construct a test scenario where at least one quintile bin has 0 < n < 5 (dimmed) and another has n = 0 (dash). Verify the two states render distinctly.
**Expected:** n=0 bin shows axis label + em-dash + "no games"; 0 < n < 5 bin shows dimmed bullet at `UNRELIABLE_OPACITY` with `n=X` chip; n >= 5 bin renders at full opacity.
**Why human:** UNRELIABLE_OPACITY dimming and inline n-chip display require visual inspection.

**3. Triple-gate font coloring fires correctly**

**Test:** With enough games (n >= 5), verify that a score-delta bullet only shows colored text (green/red) when all three conditions are true: n >= MIN_GAMES_PER_PRESSURE_BIN AND p < 0.05 AND delta outside neutral band.
**Expected:** Bullets inside the neutral band or with p >= 0.05 show muted text. Bullets outside the band with confident p show ZONE_SUCCESS (green) or ZONE_DANGER (red).
**Why human:** Requires a real user with enough games in specific quintile bins to trigger the color gate.

**4. InfoPopovers: content and mobile accessibility**

**Test:** Tap each MetricStatPopover on a Clock Gap row and a Score-Delta row on a 375px-wide screen.
**Expected:** Popover opens with correct explanation text; popover is reachable without horizontal scroll; dismisses on tap-outside or close button.
**Why human:** Interactive popover behavior and 44px tap-target sizing on mobile require browser testing.

### Gaps Summary

**One blocking gap:**

**CR-01 (BLOCKER candidate):** `query_cohort_clock_rows` fetches an unfiltered global cohort on every endgame-overview request. This is a dual defect:

1. **Correctness:** CONTEXT D-05 requires filter-responsive mirror-bucket matching Phases 85-87. The implementation ships the opposite — a global cross-user aggregate with no TC/platform/rated/opponent-type filter. A user filtering to classical games compares against a cohort dominated by bullet/blitz players, producing systematically misleading deltas.

2. **OOM/availability risk:** Loading every endgame game in the DB as per-game `ply_array` + `clock_array` Python arrays on every overview request replicates the exact failure mode documented in CLAUDE.md's "Production Server" section (Phase 41.1 OOM, FLAWCHESS-3Q). No caching layer, no LIMIT, no pagination.

The fix options are documented in REVIEW.md CR-01. The phase history notes acknowledge this is a follow-up rather than blocking in the reviewer's judgement, but the correctness impact (wrong cohort reference = wrong delta color signals for every user with TC filters active) is user-visible. The call is the developer's.

**Six non-blocking issues (Warnings/Info from REVIEW.md):**

- WR-01: `_compute_cohort_lookup` admits any bin with `n >= 1` — no `MIN_COHORT_GAMES_PER_BIN` gate — can produce spurious "sure-signal" p-values against meaningless single-game cohort references.
- WR-02: Broken `aria-labelledby="time-pressure-heading"` in `EndgameTimePressureSection.tsx` — no matching `id` exists.
- WR-03: Unsafe `!` non-null assertion on `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` index in `EndgameTimePressureCard.tsx:140` — CLAUDE.md `noUncheckedIndexedAccess` violation.
- WR-04/WR-05: `MIN_GAMES_PER_TC_CARD` and `MIN_GAMES_PER_PRESSURE_BIN` duplicated between backend and frontend with no shared source of truth; backend constant unreferenced.
- WR-06: `_finding_clock_diff_timeline` and `_finding_time_pressure_vs_performance` return permanent empty findings with no sentinel distinguishing "deprecated" from "no user data" — silent LLM prompt degradation.
- IN-01/IN-02: Dead constants and stale "PLACEHOLDER" comments in generated TS and codegen template.

---

**Recommendation:** The phase delivers its primary UI goal (legacy sections replaced, 4-TC card grid with 6 bullets each, delta-IQR calibration correct after the defect-and-fix loop). The blocking question for the developer is whether CR-01's cohort doctrine deviation is acceptable to ship, or whether the filter-responsive fix must land before release. The OOM risk on the current implementation is real but latent — it depends on production DB size and request concurrency. The correctness impact (wrong cohort reference when filters are active) is present for all users who use TC or other sidebar filters.

---

_Verified: 2026-05-17_
_Verifier: Claude (gsd-verifier)_
