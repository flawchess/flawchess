---
phase: 99-percentile-badges-for-conversion-parity-and-recovery
plan: "04"
subsystem: frontend
tags:
  - percentile
  - endgame
  - chip
  - wave-2b
  - typescript

dependency_graph:
  requires:
    - phase: 99-02
      provides: rate_percentile field names locked
    - phase: 99-03
      provides: backend PerTcBucketStats rate_percentile trio + API serialization
  provides:
    - frontend/src/types/endgames.ts (PerTcBucketStats rate field trio — TS interface)
    - frontend/src/components/charts/EndgameMetricsByTcCard.tsx (title-line rate chip in MetricBlock)
  affects:
    - Plan 05 (CDF regen + backfill — once cohort rows exist, rate chips will render in prod)

tech-stack:
  added: []
  patterns:
    - "D-01 coexistence: rate chip on title line, gap chip on ΔES bullet — both coexist, neither replaced"
    - "D-03 tooltip-only differentiation: same PercentileChip flavor, distinct metricLabel"
    - "Single MetricBlock renderer covers desktop + mobile — no markup duplication"
    - "Pitfall 6 fix: w-full on h4 so ml-auto pushes chip to right edge"

key-files:
  created: []
  modified:
    - frontend/src/types/endgames.ts
    - frontend/src/components/charts/EndgameMetricsByTcCard.tsx

key-decisions:
  - "PercentileChip testId on the chip trigger (data-testid from testId prop) — wrapping span has no testId to avoid duplicate test IDs"
  - "rate_percentile? fields are optional (?) to match backend Pydantic None defaults and avoid breaking existing fixtures"
  - "metricLabel mapping: conversion->'Conversion Rate', parity->'Parity Rate', recovery->'Recovery Rate' — sole tooltip differentiator (D-08)"
  - "PercentileChip.tsx not modified — existing conversion/parity/recovery flavors reused exactly (Pitfall 8)"

requirements-completed: []

duration: ~5min
completed: "2026-05-30"
---

# Phase 99 Plan 04: Wave 2B Frontend Chip Wiring Summary

**Wave 2B frontend: PerTcBucketStats TS type extended with the rate field trio; MetricBlock renders a title-line right-aligned rate PercentileChip gated on percentile+anchor; Wave-0 tests green; PercentileChip and gap chip untouched.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-30T23:20:00Z
- **Completed:** 2026-05-30T23:24:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Extended `PerTcBucketStats` TypeScript interface with three optional fields: `rate_percentile?: number | null`, `rate_percentile_n_games?: number | null`, `rate_percentile_value?: number | null`. Fields are distinct from `percentile*` (D-01 coexistence). Typed `number | null`, optional `?:` for backward compatibility with existing fixtures.
- Added `w-full` to the MetricBlock `h4` className (Pitfall 6 fix — `inline-flex` without `w-full` shrinks to content; `ml-auto` requires the container to fill the row).
- Added title-line rate `PercentileChip` inside the `h4` after `InfoPopover`, right-aligned via `ml-auto inline-flex` span. Gated on `block.rate_percentile != null && anchorRating != null` (SC-1: below-floor or no-anchor → silent suppression).
- Chip uses existing `'conversion'` / `'parity'` / `'recovery'` flavors (Pitfall 8: no flavor extension) with `metricLabel='Conversion Rate'` / `'Parity Rate'` / `'Recovery Rate'` — the sole tooltip differentiator (D-03/D-08).
- Existing ΔES-gap chip on the `ScoreGapRow chipSlot` is completely untouched (D-01).
- MetricBlock is a single component definition (confirmed by `grep -c "function MetricBlock\|const MetricBlock"` = 1). The three `<MetricBlock>` calls at lines 404–439 (conversion, parity, recovery) are invocations, not separate definitions. This single renderer covers both desktop (flex-row at lg+) and mobile (flex-col below lg) via responsive CSS — no duplicated markup.
- Wave-0 frontend tests: 25 passed (previously 5 RED + 20 GREEN — all 25 now GREEN).

## Task Commits

1. **Task 1: PerTcBucketStats TS rate field trio** - `9e7f135d` (feat)
2. **Task 2: Title-line rate chip in MetricBlock** - `101e88a3` (feat)

## Files Created/Modified

- `frontend/src/types/endgames.ts` — `rate_percentile`, `rate_percentile_n_games`, `rate_percentile_value` added to `PerTcBucketStats` interface with comment
- `frontend/src/components/charts/EndgameMetricsByTcCard.tsx` — `w-full` added to `h4`; rate chip slot added inside `h4`

## Key Contract Values (for Plan 05 + downstream)

**MetricBlock rate chip testId pattern:**
```
${testId}-rate-percentile-chip
→ e.g. "metrics-tc-blitz-conversion-rate-percentile-chip"
```

**Chip render gate:**
```tsx
{block.rate_percentile != null && anchorRating != null && (
  <span className="ml-auto inline-flex">
    <PercentileChip testId={`${testId}-rate-percentile-chip`} ... />
  </span>
)}
```

**metricLabel mapping:**
- conversion → 'Conversion Rate'
- parity → 'Parity Rate'
- recovery → 'Recovery Rate'

## Single-Renderer Fact (Desktop + Mobile)

`MetricBlock` is defined exactly once. The `EndgameMetricsByTcCard` body uses `flex-col lg:flex-row` responsive CSS but one `<MetricBlock>` call per bucket — no mobile-only branch. Adding the chip to `MetricBlock` automatically covers both desktop and mobile surfaces. Confirmed by:
- `grep -c "function MetricBlock\|const MetricBlock" EndgameMetricsByTcCard.tsx` → 1
- Lines 404–439 show three `<MetricBlock>` call-sites, not separate definitions

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — the chip renders real backend data (`rate_percentile` from `PerTcBucketStats` threaded by `endgame_service.py`). Until Plan 05 runs the CDF regen + backfill, `rate_percentile` will be `null` for all users and chips will suppress silently. This is correct behavior per SC-1 (below-floor → no chip), not a stub.

## Threat Flags

No new security-relevant surface introduced. Rate percentile values flow from the authenticated API response (scoped by `fetch_for_user` in Plan 03) and are rendered by React (auto-escaping). No `dangerouslySetInnerHTML`. T-99-IDOR mitigated server-side per Plan 03 as documented in the threat model.

## Self-Check

**Files verified:**
- `frontend/src/types/endgames.ts` — `grep -c "rate_percentile"` = 4 (3 fields + comment); contains `rate_percentile?: number | null`
- `frontend/src/components/charts/EndgameMetricsByTcCard.tsx` — contains `w-full` on h4; contains `rate-percentile-chip`; contains `Conversion Rate`, `Parity Rate`, `Recovery Rate` (3 occurrences); single MetricBlock definition
- `frontend/src/components/charts/PercentileChip.tsx` — `git diff --stat` shows no change

**Commits verified:**
- `9e7f135d` — Task 1 commit
- `101e88a3` — Task 2 commit

**Test suite:** 25 passed (2 test files), 0 failed
**lint:** clean
**knip:** clean
**tsc --noEmit:** clean

## Self-Check: PASSED

---
*Phase: 99-percentile-badges-for-conversion-parity-and-recovery*
*Completed: 2026-05-30*
