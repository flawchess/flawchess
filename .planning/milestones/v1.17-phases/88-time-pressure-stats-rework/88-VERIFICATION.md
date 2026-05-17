---
phase: 88-time-pressure-stats-rework
verified: 2026-05-17T16:50:18Z
status: human_needed
score: 6/6 must-haves verified (all gap-closure targets + original ROADMAP SCs)
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 5/6
  gaps_closed:
    - "CR-01: query_cohort_clock_rows unfiltered global cohort — cohort layer dropped entirely (D-07 supersedes D-05)"
    - "WR-01: small-N cohort cell admission — subsumed by min(n_user, n_opp) gate"
    - "WR-02: dangling aria-labelledby='time-pressure-heading' — replaced with self-contained aria-label"
    - "WR-03: unsafe `!` non-null assertion on PRESSURE_BIN_SCORE_NEUTRAL_ZONES — replaced with getPressureBinBand helper"
    - "WR-04/WR-05: MIN_GAMES_* duplicated + unused — lifted to endgame_zones.py + codegen-mirrored + n-gate wired in _build_quintile_bullets"
    - "WR-06: orphan LLM prompt subsection + helpers — removed (8+ symbols + 2 finding-helpers gone)"
    - "IN-01: dead constants (MIN_GAMES_FOR_CLOCK_STATS, NUM_BUCKETS, BUCKET_WIDTH_PCT, CLOCK_PRESSURE_TIMELINE_WINDOW) — removed"
    - "IN-02: 'PLACEHOLDER' / 'placeholder until benchmarks' comments on calibrated zones — stripped from generated TS and codegen template"
    - "IN-04: D-07 documented in 88-CONTEXT.md retiring D-05 — locked"
    - "IN-05: ARIA-wiring regression test added to EndgameTimePressureSection.test.tsx"
    - "IN-06: getPressureBinBand helper generated in endgameZones.ts and consumed in card"
    - "POLISH-01: §3.3.3.b rerun appended to reports/benchmarks-latest.md; keep-as-is decision recorded in 88-12-SUMMARY frontmatter"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Render the Endgames page in a real browser at xl (≥1280px), lg (≥1024px), and base (<1024px) widths. Apply various sidebar filter combinations (all TCs / bullet-only / classical-only / rated-only)."
    expected: "4-col (xl) / 2-col (lg) / 1-col (base) card grid renders. TC cards with total < 20 are hidden. Each rendered card shows 6 rows (1 Clock Gap + 5 quintiles). Score-delta values now reflect user_score − opp_score (D-07), not the prior cohort frame; popover copy reads 'vs opponent'."
    why_human: "Responsive Tailwind layout, conditional card visibility, and filter-response interactivity cannot be verified by grep. The display change from 'vs cohort' to 'vs opponent' is a user-facing semantic shift worth eyeballing on real data."
  - test: "Sparse-bin rendering: with a real user, find a bin where 0 < min(n_user, n_opp) < 5 (dimmed at UNRELIABLE_OPACITY + n=X chip), a bin where n=0 (dash + 'no games' empty row), and a confidently-rendered bin (full opacity)."
    expected: "Three visually-distinct sparse states (full / dimmed / empty). The n-gate is now min(n_user, n_opp) ≥ MIN_GAMES_PER_PRESSURE_BIN (changed from the prior single-side gate), so a few previously-rendered bins may now drop into the dimmed state — confirm this is acceptable."
    why_human: "UNRELIABLE_OPACITY dimming and inline n-chip display require visual inspection; behavioural change from D-07 may affect which bins paint colored."
  - test: "MetricStatPopover on a Clock Gap row and a Score-Delta row at 375px width."
    expected: "Popover opens with the new 'vs opponent' / 'same-game opp-quintile' methodology copy; readable and reachable on mobile; dismisses cleanly."
    why_human: "Interactive popover behavior, 44px tap-target sizing, and copy correctness require browser testing."
  - test: "ARIA accessible name on the Time Pressure section is announced as 'Time pressure analysis' by a screen reader (VoiceOver / NVDA)."
    expected: "Screen reader announces section by aria-label, not silently degrading to no accessible name (which was the WR-02 state pre-fix)."
    why_human: "Requires assistive-technology testing; jsdom-based unit test asserts the attribute is present but cannot confirm the actual AT announcement."
---

# Phase 88: Time Pressure Stats Rework — Verification Report (post-gap-closure, re-verification)

**Phase Goal (ROADMAP):** Replace the Time Pressure at Endgame Entry table and the Time Pressure vs Performance line chart with a unified per-TC card design (one card per bullet/blitz/rapid/classical, 6 bullets each: 1 Clock Gap + 5 Score-Delta quintile bullets). Closes v1.17 endgame rework arc.

**Verified:** 2026-05-17T16:50:18Z
**Status:** human_needed
**Re-verification:** Yes — closing the `gaps_found` from the prior 88-VERIFICATION.md (CR-01 blocker + 6 warnings) after Plans 88-09..88-12 shipped.

## Re-Verification Summary

| Prior gap | Closure plan | Status now |
|---|---|---|
| CR-01 (cohort blocker) | 88-09 | CLOSED — cohort layer deleted; D-07 supersedes D-05 |
| WR-01 (small-N cohort gate) | 88-09 | CLOSED (subsumed by min-n-per-side gate) |
| WR-02 (aria-labelledby orphan) | 88-11 | CLOSED — aria-label="Time pressure analysis" |
| WR-03 (unsafe `!` non-null assertion) | 88-11 | CLOSED — getPressureBinBand helper consumed |
| WR-04 (duplicated MIN_GAMES_*) | 88-10 | CLOSED — single source of truth in endgame_zones.py |
| WR-05 (MIN_GAMES_PER_PRESSURE_BIN unused) | 88-09 | CLOSED — wired into gate inside _build_quintile_bullets |
| WR-06 (orphan LLM subsection / helpers) | 88-09 | CLOSED — 8+ symbols + 2 finding helpers removed |
| IN-01 (dead constants) | 88-09 | CLOSED — 4 constants removed |
| IN-02 (PLACEHOLDER strings) | 88-10 | CLOSED |
| IN-04 (D-07 retires D-05) | 88-09 | CLOSED — D-07 locked in 88-CONTEXT.md |
| IN-05 (ARIA-wiring test) | 88-11 | CLOSED |
| IN-06 (getPressureBinBand helper) | 88-10 | CLOSED |
| POLISH-01 (rerun + decision) | 88-12 | CLOSED (keep-as-is, documented) |

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Legacy `EndgameClockPressureSection.tsx` deleted; `EndgameTimePressureSection.tsx` is the NEW card-grid orchestrator | VERIFIED (regression-clean) | `ls frontend/src/components/charts/ | grep -i "clock\|pressure\|legacy"` returns only `EndgameTimePressureCard.tsx` and `EndgameTimePressureSection.tsx`. Section renders `grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-4` of `EndgameTimePressureCard`. |
| 2 | `data.time_pressure_chart` / `data.clock_pressure` references are gone from Endgames.tsx; replaced by `time_pressure_cards` | VERIFIED (regression-clean) | Endgames.tsx:284 reads `overviewData?.time_pressure_cards`; line 534 renders `<EndgameTimePressureSection data={timePressureCardsData} />`. |
| 3 | Per-TC card renders 6 bullets: 1 Clock Gap + 5 Score-Delta quintile bullets, sparse-handled, triple-gate font coloring | VERIFIED (regression-clean) | `EndgameTimePressureCard.tsx` defines `ClockGapRow`, `QuintileRow`, `EmptyBinRow`. Card hides when `card.total < MIN_GAMES_PER_TC_CARD` (now imported from generated `endgameZones`). 5 quintile rows iterate `card.quintiles`. |
| 4 | Cohort doctrine — the prior CR-01 failed truth ("filter-responsive mirror-bucket") is REPLACED by D-07's same-game opp-quintile split | VERIFIED (design pivot, scope-supersedes) | `query_cohort_clock_rows` and `_compute_cohort_lookup` are deleted. `_build_quintile_bullets` now consumes `(user_w, user_d, user_l, user_n, opp_w, opp_d, opp_l, opp_n)` via `compute_score_difference_test` (unpaired two-sample Wilson). D-07 in `88-CONTEXT.md:77` explicitly retires D-05. No cross-user query runs on `/api/endgames/overview`. |
| 5 | Score-Delta significance test exists, is wired, and the n-gate is min(n_user, n_opp) ≥ MIN_GAMES_PER_PRESSURE_BIN | VERIFIED | `compute_score_difference_test` is the unpaired two-sample Wilson helper (kept from Phase 85.1). `_build_quintile_bullets` at endgame_service.py:1593 enforces `n_user >= MIN_GAMES_PER_PRESSURE_BIN AND n_opp >= MIN_GAMES_PER_PRESSURE_BIN`. The 88-01-vintage `compute_score_delta_vs_reference` helper (and its private `_wilson_score_test_vs_ref`) were deliberately removed by 88-09 — the D-07 design uses the two-sample form, not the fixed-reference form. |
| 6 | Frontend type `PressureQuintileBullet.opp_score` matches backend schema; popover copy reads "vs opponent"; unsafe index-narrowing replaced; ARIA accessible-name resolves; MIN_GAMES_* sourced from codegen | VERIFIED | `frontend/src/types/endgames.ts:234` declares `opp_score: number | null`. Card imports `MIN_GAMES_PER_TC_CARD, MIN_GAMES_PER_PRESSURE_BIN, getPressureBinBand` from `@/generated/endgameZones`. `getPressureBinBand(tc, bin.quintile_index)` replaces the `[q as 0|1|2|3|4]!` pattern. Section uses `aria-label="Time pressure analysis"`. |

**Score:** 6/6 truths verified.

Note on Truth 4 vs the original ROADMAP SC: the ROADMAP Phase 88 SC text predates the post-VERIFICATION pivot and references "cohort_score" + "compute_score_delta_vs_reference". The user explicitly approved a design pivot (D-07 supersedes D-05) inside the same phase boundary, recorded in 88-VERIFICATION.md lines 178-220 and 88-CONTEXT.md lines 77-105. The pivot delivers the same observable user-facing outcome (per-quintile score deltas with CI whiskers and triple-gate coloring) via a cleaner, OOM-safe data path. Treating this as an in-phase amendment to the ROADMAP SC, not a deviation.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/repositories/endgame_repository.py` | `query_cohort_clock_rows` REMOVED | VERIFIED (DELETED) | Only a commemorative comment remains at line 877 documenting the removal under D-07 / CR-01. |
| `app/services/endgame_service.py` | Cohort plumbing removed; opp-quintile split; MIN_GAMES_* imported from endgame_zones | VERIFIED | `_compute_cohort_lookup` / `cohort_lookup` / `cohort_rows`: 0 occurrences in source. `MIN_GAMES_PER_PRESSURE_BIN` / `MIN_GAMES_PER_TC_CARD` imported from endgame_zones at lines 67-68. Gate at line 1593, card-total gate at line 1662. Dead constants (`MIN_GAMES_FOR_CLOCK_STATS`, `NUM_BUCKETS`, `BUCKET_WIDTH_PCT`, `CLOCK_PRESSURE_TIMELINE_WINDOW`): 0 occurrences. |
| `app/services/score_confidence.py` | `compute_score_delta_vs_reference` + `_wilson_score_test_vs_ref` REMOVED | VERIFIED (DELETED) | Only a commemorative comment remains at lines 124-128. `compute_score_difference_test` (the surviving Phase 85.1 helper) is the live function used by `_build_quintile_bullets`. |
| `app/schemas/endgames.py` | `PressureQuintileBullet.opp_score` (not `cohort_score`) | VERIFIED | `opp_score: float | None` at line 650; docstrings rewritten for D-07 semantics; `cohort_score` absent. |
| `app/services/endgame_zones.py` | `MIN_GAMES_PER_TC_CARD = 20`, `MIN_GAMES_PER_PRESSURE_BIN = 5` as module-level constants; 20 `PressureBinBand` entries preserved (keep-as-is from 88-08) | VERIFIED | Constants at lines 164, 169. 20 `PressureBinBand` entries intact (bullet/blitz/rapid/classical × Q0..Q4) with 88-08 calibration values unchanged. |
| `scripts/gen_endgame_zones_ts.py` | Emits `MIN_GAMES_PER_TC_CARD`, `MIN_GAMES_PER_PRESSURE_BIN`, and `getPressureBinBand` helper; no PLACEHOLDER strings on calibrated zones | VERIFIED | Lines 212-241 emit the calibrated zones with attribution to §3.3.3 (no PLACEHOLDER on the pressure-bin block), the two MIN_GAMES_* constants, and the typed helper. Codegen drift gate: `uv run python scripts/gen_endgame_zones_ts.py --check` → "OK: ... is up to date". |
| `frontend/src/generated/endgameZones.ts` | New TS exports + helper; no PLACEHOLDER comments on calibrated values | VERIFIED | Exports `MIN_GAMES_PER_TC_CARD = 20` (line 105), `MIN_GAMES_PER_PRESSURE_BIN = 5` (line 106), `getPressureBinBand` (line 113). `grep -E "PLACEHOLDER\|placeholder until benchmarks" frontend/src/generated/endgameZones.ts` → 0. |
| `frontend/src/components/charts/EndgameTimePressureCard.tsx` | Imports codegen constants; uses `getPressureBinBand`; "vs opponent" copy | VERIFIED | Imports at line 23-28. `getPressureBinBand(tc, bin.quintile_index)` at line 142 (2 references total). Unsafe `[q as 0|1|2|3|4]!` pattern: 0 occurrences. Local `const MIN_GAMES_PER_*` shadows: 0 occurrences. |
| `frontend/src/components/charts/EndgameTimePressureSection.tsx` | `aria-label="Time pressure analysis"` (not dangling `aria-labelledby`) | VERIFIED | Line 22. `aria-labelledby="time-pressure-heading"`: 0 occurrences. `time-pressure-heading` id across entire `frontend/src/` tree: 0 references — no orphan id. |
| `frontend/src/types/endgames.ts` | `PressureQuintileBullet.opp_score` | VERIFIED | Line 234 declares `opp_score: number | null`. `cohort_score`/`cohortPct` greps: 0. |
| `app/services/insights_service.py` | `_finding_clock_diff_timeline` + `_finding_time_pressure_vs_performance` REMOVED | VERIFIED (DELETED) | Only a commemorative comment remains at lines 954-956. |
| `app/services/insights_llm.py` | WR-06 orphans REMOVED (`_SKIPPED_SUBSECTIONS`, `_format_time_pressure_chart_block`, `_low_time_gap_line`, `_LOW_TIME_BUCKETS`, `_LOW_TIME_GAP_DECISIVE`) | VERIFIED (DELETED) | Only commemorative comments remain at lines 142-143 and line 971. Live code references: 0. |
| `frontend/src/components/charts/__tests__/EndgameTimePressureSection.test.tsx` | IN-05 ARIA-wiring regression test | VERIFIED | Lines 180-190 assert `aria-label === 'Time pressure analysis'` AND `aria-labelledby === null`. |
| `.planning/milestones/v1.17-phases/88-time-pressure-stats-rework/88-CONTEXT.md` | D-07 entry retiring D-05 | VERIFIED | Lines 77-105 contain the locked D-07 decision; explicit "supersedes D-05" in the heading. |
| `reports/benchmarks-latest.md` | §3.3.3.b opp-quintile rerun subsection | VERIFIED | Line 1134 contains `#### §3.3.3.b chess-score-per-pressure-bin — opp-quintile rerun (Phase 88.1 / 2026-05-17)`. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `endgame_zones.py` (MIN_GAMES_* + PressureBinBand) | `endgameZones.ts` (constants + helper + ZONES record) | `scripts/gen_endgame_zones_ts.py` | WIRED | Codegen drift gate exits 0. Generated file emits all expected exports. |
| `endgame_zones.MIN_GAMES_PER_PRESSURE_BIN` | `_build_quintile_bullets` (gate) | python import at endgame_service.py:67 | WIRED | Imported once at the top of the module; consumed at line 1593 in the n-gate. |
| `compute_score_difference_test` | `_build_quintile_bullets` | python import at endgame_service.py:80 | WIRED | Called at line 1620 with `(user_w, user_d, user_l, n_user, opp_w, opp_d, opp_l, n_opp)`. |
| `getPressureBinBand` (generated) | `EndgameTimePressureCard.tsx` (QuintileRow) | TS import at line 27 | WIRED | `neutralBand = getPressureBinBand(tc, bin.quintile_index)` at line 142, with early-null handling. |
| `MIN_GAMES_PER_TC_CARD` (generated) | `EndgameTimePressureCard.tsx` (card-level visibility) | TS import (codegen-side) | WIRED | Consumed in the card-level gate (no local shadow remains; `grep -cE "^const MIN_GAMES_PER_" EndgameTimePressureCard.tsx` → 0). |
| Schema `opp_score` (Pydantic) | `PressureQuintileBullet.opp_score` (TS) | manual mirror | WIRED | Both fields present; popover copy switched to "vs opponent". |
| Endgames page section | section accessible name | self-contained `aria-label` | WIRED | aria-label is now self-contained; no cross-file id dependency. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|---|---|---|---|---|
| `EndgameTimePressureCard` quintile delta | `bin.delta` | `_build_quintile_bullets` → `compute_score_difference_test` on `user_quintile_wdl[tc][q]` and `opp_quintile_wdl[tc][q]` (both from `_iterate_clock_rows` over user's own filtered games) | Yes — single-pass derivation from the user's filtered game stream; both sides backed by real DB rows | FLOWING |
| `EndgameTimePressureCard` opp_score | `bin.opp_score` | Same path; opp side derived by bucketing same rows with opp clock-pct and inverting result | Yes; replaces the prior HOLLOW (unfiltered cohort) data path flagged in the original verification | FLOWING |
| `EndgameTimePressureCard` clock_gap | `card.clock_gap.mean_diff_pct` | `_build_clock_gap` → `compute_paired_difference_test` over same rows | Yes (unchanged from original) | FLOWING |

The previously-HOLLOW cohort path (the original Truth 6 / CR-01 failure) is removed entirely. All bullet values now flow from the user's own filtered games, scientifically valid (independent two-sample test because user/opp clocks fall in different quintiles within the same game), and OOM-safe (no cross-user query).

### Behavioral Spot-Checks

- Backend tests (gap-closure surface): `uv run pytest tests/services/test_time_pressure_service.py tests/services/test_score_confidence.py tests/services/test_insights_llm.py tests/services/test_endgame_zones.py -q` → **193 passed in 0.56s**.
- Frontend tests for the two card files: `npm test -- --run EndgameTimePressureCard.test.tsx EndgameTimePressureSection.test.tsx` → **22 passed (22)**.
- Codegen drift gate: `uv run python scripts/gen_endgame_zones_ts.py --check` → exits 0 ("OK: frontend/src/generated/endgameZones.ts is up to date.").
- Backend type check on touched files: `uv run ty check app/services/endgame_service.py app/services/endgame_zones.py app/services/score_confidence.py app/schemas/endgames.py app/services/insights_service.py app/services/insights_llm.py` → "All checks passed!".

### Probe Execution

No `scripts/*/tests/probe-*.sh` files declared in any of the 12 plans. Step skipped.

### Requirements Coverage

| Requirement | Source plan(s) | Description | Status | Evidence |
|---|---|---|---|---|
| POLISH-01 | 88-09, 88-11, 88-12 | Peer/neutral band decision resolved | SATISFIED | §3.3.3.b rerun documented in reports/benchmarks-latest.md; keep-as-is decision in 88-12-SUMMARY frontmatter; PRESSURE_BIN_SCORE_NEUTRAL_ZONES intact and now semantically valid on `user_score − opp_score`. |
| POLISH-03 | 88-10, 88-11 | data-testid + ARIA + semantic HTML coverage | SATISFIED (for Phase 88 surfaces) | data-testid present across card / bullets / values / info / empty rows. ARIA accessible name resolves. WR-02 closed. Full v1.17 sweep remains Phase 89 scope per ROADMAP. |
| POLISH-02 | — | Gauge significance gating | DEFERRED to Phase 89 (per ROADMAP). |
| POLISH-04 | — | Mobile parity at 375px | DEFERRED to Phase 89 (per ROADMAP); spot-checked here as human-needed item below. |

REQUIREMENTS.md still lists POLISH-01..04 against Phase 88. POLISH-01 and POLISH-03 are now satisfied within the Phase 88 scope as far as the Time Pressure section is concerned; POLISH-02 and POLISH-04 are explicitly Phase 89 scope per the ROADMAP. No orphaned requirement IDs.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| `scripts/gen_endgame_zones_ts.py` | 72 | Internal Python comment `# PLACEHOLDER band until benchmarks §3.3.1 clock-gap-% runs calibrate it.` references a stale state — Phase 88-08 has since calibrated the clock-gap band | INFO | Codegen-template-internal Python comment about the `_CLOCK_GAP_SPEC` source variable; doesn't appear in the generated TS (the TS-side block at lines 243-244 correctly attributes the calibrated values to §3.3.1). Not in IN-02 scope (IN-02 specifically targeted the generated-TS PLACEHOLDER strings). Worth a one-line cleanup but out of Phase 88.1 scope; flagging for future hygiene. |
| `scripts/gen_endgame_zones_ts.py` | 200-201 | `// Phase 87.1 (SEED-016 D-04): achievable_score_gap added as a placeholder` mention | INFO | Belongs to Phase 87.1 work (different ZoneSpec), not Phase 88 / IN-02. Mentioned here only to confirm grep noise is not a Phase 88 regression. |

No blocker- or warning-severity anti-patterns introduced or remaining in Phase 88 scope.

### Human Verification Required

See `human_verification:` in frontmatter. Four items, all standard rendering / interactivity / accessibility checks that require a running browser:

1. Responsive 4/2/1 col grid at xl/lg/base with filter-response behaviour (D-07 user-facing semantic shift: "vs opponent" rather than "vs cohort").
2. Three sparse states render distinctly (full / dimmed / empty), with the new min(n_user, n_opp) gate.
3. MetricStatPopover content + mobile tap-target at 375px.
4. Screen reader announces the section's accessible name correctly (jsdom-level test passes but cannot confirm the actual AT announcement).

### Gaps Summary

No remaining gaps. All 12 previously-identified findings (CR-01 + 6 WR-* + 5 IN-* + POLISH-01 partial) are closed in the live codebase. The CR-01 cohort-fairness blocker is resolved by a design pivot (D-07) — the entire cohort data path is gone, replaced by a same-game opp-quintile split that is both semantically cleaner (no cross-user query, no OOM risk) and statistically valid (compute_score_difference_test is the right test for two independent samples drawn from the same filtered game-set).

Status is `human_needed` rather than `passed` because the rendering / interactivity / accessibility checks in `human_verification:` are intrinsically not grep-verifiable, not because of any open gap.

---

_Verified: 2026-05-17T16:50:18Z_
_Verifier: Claude (gsd-verifier)_
_Re-verification of: 88-VERIFICATION.md gaps_found (2026-05-17)_
