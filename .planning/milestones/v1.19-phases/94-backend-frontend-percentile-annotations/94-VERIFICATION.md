---
phase: 94-backend-frontend-percentile-annotations
verified: 2026-05-23T11:25:00Z
status: passed
score: 14/14 must-haves verified
overrides_applied: 0
---

# Phase 94: Backend & Frontend Percentile Annotations — Verification Report

**Phase Goal:** Surface percentile annotations end-to-end on the 4 chipped ΔES rows. Backend interpolates user metric value against `GLOBAL_PERCENTILE_CDF`, emits a nullable `{metric}_percentile` field gated by `PVALUE_RELIABILITY_MIN_N`. Frontend renders a compact "top X%" chip with desktop+mobile parity, theme-driven colors, and metric-aware popover copy (skill-isolating vs improvement-focus). Recovery ΔES + raw % gauges get NO chip.

**Verified:** 2026-05-23T11:25:00Z
**Status:** passed
**Re-verification:** No (initial verification)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | 4 nullable `*_percentile` fields present on endgame Pydantic schemas | ✓ VERIFIED | `app/schemas/endgames.py` lines 260, 447, 470, 485 declare all 4 as `float \| None = None` |
| 2 | 4 gated `interpolate_percentile` calls at 2 compute sites | ✓ VERIFIED | `app/services/endgame_service.py` lines 1369-1394 (site B, 3 calls) + line 2344-2347 (site A, 1 call); `grep -cE 'interpolate_percentile\("(score_gap\|achievable_score_gap\|section2_score_gap_conv\|section2_score_gap_parity)"'` returns 4 |
| 3 | `PVALUE_RELIABILITY_MIN_N` reliability-N gate is wired | ✓ VERIFIED | Defined at `endgame_service.py:206`; reused at lines 1371, 1387, 1392, 2346 (one gate per metric, dual-N for score_gap) |
| 4 | Recovery is structurally excluded (no `section2_score_gap_recov_percentile` field anywhere in production code) | ✓ VERIFIED | `grep -c section2_score_gap_recov_percentile` returns 0 in `app/schemas/`, `app/services/`, `frontend/src/types/`; only test files assert exclusion |
| 5 | 4 nullable percentile fields mirrored in TS types; recovery excluded | ✓ VERIFIED | `frontend/src/types/endgames.ts` lines 118, 211, 229, 239 declare `number \| null`; no recovery field |
| 6 | `PercentileChip` standalone component exists | ✓ VERIFIED | `frontend/src/components/charts/PercentileChip.tsx` (181 lines); exports `PercentileChip` + `PercentileChipFlavor` |
| 7 | Chip uses theme.ts constants (no hard-coded band colors) | ✓ VERIFIED | Line 24 imports `ZONE_DANGER`, `GAUGE_NEUTRAL`, `ZONE_SUCCESS` from `@/lib/theme`; only `CHIP_TEXT_COLOR` (oklch 0.98 0 0, near-white text) is local with documented justification |
| 8 | Flavor routing — `skill-isolating` + `improvement-focus` | ✓ VERIFIED | Type at line 41; `PercentileChipPopoverBody` lines 71-86 routes the 2 copy branches; flavor routed at the 4 call sites |
| 9 | Banded color (red <25 / blue 25..75 / green >75) | ✓ VERIFIED | `deriveBandColor` lines 54-58 dispatches on `PERCENTILE_BAND_LOW=25` / `_HIGH=75` |
| 10 | Flame tier dispatch (top 10% / 5% / 1%, highest tier only) | ✓ VERIFIED | `deriveFlameCount` lines 60-65 cascades `if TIER_3 return 3; TIER_2 return 2; TIER_1 return 1`; test asserts exactly 3 flames at p=99 (not 6 cumulative) |
| 11 | Chips render on exactly 4 sites with correct flavor routing | ✓ VERIFIED | `EndgameOverallPerformanceSection.tsx` lines 183-192 (Achievable, skill-isolating) + 233-242 (Endgame Score Gap, skill-isolating); `EndgameMetricCard.tsx` lines 231-240 with `flavor={bucket === 'conversion' ? 'improvement-focus' : 'skill-isolating'}`; recovery blocked by `bucket !== 'recovery'` guard |
| 12 | Recovery card + per-type cards + raw gauges + Time Pressure MUST NOT render a chip | ✓ VERIFIED | `grep -rln PercentileChip frontend/src/components/` returns only the 4 expected files; `EndgameMetricCard` defensive `bucket !== 'recovery'`; `EndgameMetricsSection.tsx:148` passes `scoreGapPercentile={null}` to recovery card explicitly |
| 13 | Mobile parity at 375px via CSS Grid (chip below bullet on mobile, inline right on desktop) | ✓ VERIFIED | `EndgameOverallScoreGapRow.tsx` lines 132-164 — `<div className="grid grid-cols-[1fr_auto] ...">`, chip span at lines 145-149 uses `row-start-3 col-span-2 justify-self-start sm:row-start-1 sm:col-start-2 sm:justify-self-end` |
| 14 | Tests cover field presence + gate semantics + chip presence/absence + flavor routing + flame dispatch | ✓ VERIFIED | Backend: 13 percentile-tagged tests pass (`tests/schemas/test_endgames_schema.py::TestPercentileFieldsPresent` 2/2 + `tests/test_endgame_service.py::TestPercentileGates` 11/11). Frontend: 91 tests pass across `PercentileChip`, `EndgameOverallPerformanceSection`, `EndgameMetricCard`, `EndgameTypeCard`, `EndgameOverallScoreGapRow` |

**Score:** 14/14 truths verified.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/schemas/endgames.py` | 4 new nullable `*_percentile` fields | ✓ VERIFIED | lines 260, 447, 470, 485; each with docstring documenting [0,100] range + gate semantics |
| `app/services/endgame_service.py` | 4 gated `interpolate_percentile` calls at 2 sites | ✓ VERIFIED | import at line 74; sites at 1369 (score_gap dual-N), 1385 (conv), 1390 (parity), 2344 (achievable); response constructors at 1406/1413/1419/2370 |
| `frontend/src/types/endgames.ts` | 4 nullable percentile fields | ✓ VERIFIED | lines 118 (achievable), 211 (score_gap), 229 (conv), 239 (parity); each with JSDoc gate clause |
| `frontend/src/components/charts/PercentileChip.tsx` | Banded color pill + flame stack + Radix popover + flavor routing | ✓ VERIFIED | 181 LOC; all named constants extracted; popover shell mirrors MetricStatPopover |
| `frontend/src/components/charts/__tests__/PercentileChip.test.tsx` | Unit tests for label, color, flames, flavor, accessibility | ✓ VERIFIED | 15 tests across 5 behavior groups; all green |
| `frontend/src/components/charts/EndgameOverallScoreGapRow.tsx` | `chipSlot?: ReactNode` prop + CSS Grid mobile layout | ✓ VERIFIED | prop at line 61; CSS Grid render branch at 132-164 |
| `frontend/src/components/charts/EndgameOverallPerformanceSection.tsx` | 2 chip insertions (Endgame + Achievable Score Gap, skill-isolating) | ✓ VERIFIED | lines 183-192, 233-242 |
| `frontend/src/components/charts/EndgameMetricCard.tsx` | `scoreGapPercentile` prop + chip with `bucket !== 'recovery'` guard | ✓ VERIFIED | prop at line 79; conditional at line 231-240; flavor routed by bucket |
| `frontend/src/components/charts/EndgameMetricsSection.tsx` | Per-bucket scoreGapPercentile routing (conv/parity/recovery=null) | ✓ VERIFIED | lines 113 (conv), 129 (parity), 148 (`={null}` for recovery) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `endgame_service.py` | `global_percentile_cdf.py` | `interpolate_percentile` import | ✓ WIRED | Line 74 |
| `PercentileChip.tsx` | `lib/theme.ts` | `ZONE_DANGER/GAUGE_NEUTRAL/ZONE_SUCCESS` import | ✓ WIRED | Line 24 |
| `PercentileChip.tsx` | radix-ui Popover | `PopoverPrimitive.Root/Trigger/Portal/Content` | ✓ WIRED | Line 20 + JSX lines 129-178 |
| `PercentileChip.tsx` | lucide-react | `Flame` icon | ✓ WIRED | Line 21 + render at line 147 |
| `EndgameOverallPerformanceSection.tsx` | `PercentileChip.tsx` | import + 2 conditional sites | ✓ WIRED | import line 44; 2 sites verified |
| `EndgameMetricCard.tsx` | `PercentileChip.tsx` | import + 1 bucket-gated site | ✓ WIRED | import line 41; 1 site (covers conv + parity via flavor switch, recovery guarded) |
| `EndgameMetricsSection.tsx` | `EndgameMetricCard.tsx` | per-bucket `scoreGapPercentile` prop | ✓ WIRED | Lines 113, 129, 148 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `PercentileChip` | `percentile` prop | Backend `*_percentile` fields → `interpolate_percentile(metric, value)` against Phase 93 `GLOBAL_PERCENTILE_CDF` | Yes — service calls helper at 4 gated sites; helper returns [0,100] float or None | ✓ FLOWING |
| `EndgameOverallPerformanceSection` chips | `data.achievable_score_gap_percentile`, `scoreGap.score_gap_percentile` | API response via TanStack Query; gated by `!= null` | Yes — backend emits per-request; nulls gracefully suppress chip | ✓ FLOWING |
| `EndgameMetricCard` chips | `scoreGapPercentile` prop | `EndgameMetricsSection` passes `data.section2_score_gap_{conv,parity}_percentile` | Yes — per-bucket routing verified | ✓ FLOWING |
| `EndgameMetricCard` recovery chip | `null` (explicit) | `EndgameMetricsSection:148` passes `={null}` | N/A — defensive structural exclusion | ✓ DISCONNECTED (intended) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Backend percentile-tagged tests pass | `uv run pytest tests/schemas/test_endgames_schema.py tests/test_endgame_service.py -k percentile` | 13 passed, 310 deselected, 0 failed | ✓ PASS |
| Frontend chart tests pass | `cd frontend && npm test -- --run PercentileChip EndgameOverallPerformanceSection EndgameMetricCard EndgameTypeCard EndgameOverallScoreGapRow` | 91 passed across 5 files in 1.25s | ✓ PASS |
| TypeScript compile clean | `cd frontend && npx tsc --noEmit` | exit 0, no output | ✓ PASS |
| Module exports | `grep` confirms `PercentileChip` + `PercentileChipFlavor` exported and imported in 2 consumer files | OK | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| PCTL-02 | 94-01 | Backend emits nullable `{metric}_percentile` gated by per-metric N | ✓ SATISFIED | 4 fields present, 4 gated interpolate calls, N=10 floor reused |
| PCTL-03 | 94-02, 94-03 | Chipped row renders "top X%" with honest rounding | ✓ SATISFIED | `formatTopXPercent` floors at `Math.max(1, Math.round(100-pct))`; integer percent only |
| PCTL-04 | 94-02, 94-03 | Metric-aware popover framing (skill-isolating vs improvement-focus) | ✓ SATISFIED | 2 copy bodies + flavor prop routing; Conversion → improvement-focus, others → skill-isolating |
| PCTL-05 | 94-02, 94-03 | Desktop + mobile parity, theme-driven colors | ✓ SATISFIED | CSS Grid mobile layout in `EndgameOverallScoreGapRow`; theme constants imported from `theme.ts` |
| PCTL-06 | 94-01, 94-03 | Reliability gate — no chip below N floor; defensive guards | ✓ SATISFIED | Gate at PVALUE_RELIABILITY_MIN_N=10 (dual-N for score_gap); callers gate `!= null`; recovery defensively excluded at 2 layers (call-site `null` + component `bucket !== 'recovery'`) |

All 5 requirement IDs from PLAN frontmatter accounted for and traceable to shipped code. No orphans.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `PercentileChip.tsx` | 14-16 | Stale comment "Wired into rows by Plan 94-03 — until then this export is intentionally unused" | ℹ️ Info | REVIEW IN-04 carry-forward — Wave 3 has shipped; comment is now misleading historical context. Cosmetic only. |
| `app/services/endgame_service.py` | 2325 | Comment "REVIEW IN-01 carry-forward" | ℹ️ Info | Pre-existing review note tracking a separate issue; not a phase 94 regression |

No TODO/FIXME/TBD/XXX debt markers introduced in Phase 94 code. No console.log stubs. No hard-coded empty returns. No unintentional placeholder values.

### Code-Review Fixes Verified

| ID | Fix | Status | Evidence |
|----|-----|--------|----------|
| WR-01 | `PercentileChip` useEffect cleanup clears hoverTimeout on unmount; `handleMouseEnter` clears before set | ✓ APPLIED | `PercentileChip.tsx` lines 100-107 (useEffect cleanup) + line 112 (`if (hoverTimeout.current) clearTimeout(...)` before setting new timer) |
| WR-02 | Dead `conv_n is not None` / `parity_n is not None` clauses removed | ✓ APPLIED | `endgame_service.py` lines 1385-1394 only contain load-bearing `mean is not None` guards; explanatory comment at lines 1382-1384 documents that `n` is `int`, not `int \| None` |

### Human Verification Required (Recurring UAT for Future Regression)

The Phase 94-03 Task 3 HUMAN-UAT was approved interactively by the user during execution, with 4 iteration commits documented in 94-03-SUMMARY.md. These items remain valid recurring UAT items for any future regression check that touches `EndgameOverallScoreGapRow`, `EndgameOverallPerformanceSection`, `EndgameMetricCard`, `EndgameMetricsSection`, or `PercentileChip` styling/layout:

1. **Visual checks (desktop ≥1280px):** chip renders right-aligned on Endgame Score Gap + Achievable Score Gap rows; chip on Section 2 Conversion + Parity cards; NO chip on Recovery card, per-type cards (Rook/Minor/Pawn/Queen/Mixed), raw % gauges, timelines, or Time Pressure section.
2. **Color band + flame tier sanity:** red <p25, blue p25..p75, green >p75; 1 flame at p≥90, 2 at p≥95, 3 at p≥99 (highest tier only).
3. **Popover companion read:** skill-isolating + improvement-focus copy reads as deliberate companions, not contradictions.
4. **Mobile parity at 375px:** chips render with same color bands and flame tiers; chip wraps to its own row below the bullet chart, left-aligned (CSS Grid `row-start-3`).
5. **Null fallback:** users below the N floor render no chip, row is pixel-identical to pre-Phase-94 state.
6. **Accessibility smoke:** chip is keyboard-focusable, Enter/Space opens popover, screen reader announces via `aria-label`.

**Status: not blocking phase close.** These items were already approved during execution. They are documented here for any future regression suite (UI/UX checks are recurring by nature).

### Gaps Summary

No gaps found. All 14 must-haves verified against the codebase; all 5 PCTL requirements satisfied; both code-review warnings (WR-01, WR-02) addressed; full test suites green; data flows end-to-end from backend percentile fields through the wire to the 4 chip render sites; defensive recovery exclusion enforced at 4 layers (backend schema absence, backend service no-emit, frontend type absence, parent component `null` pass, child component `bucket !== 'recovery'` guard).

Phase 94 ships the goal as specified.

---

_Verified: 2026-05-23T11:25:00Z_
_Verifier: Claude (gsd-verifier)_
