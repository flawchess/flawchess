---
slug: endgame-score-gap-wrong-color
status: resolved
trigger: "In 'Endgame vs Non-Endgame Score over Time' chart, the shaded gap between the two lines is sometimes marked green when it should be red."
created: 2026-04-24
updated: 2026-04-24
---

# Debug Session: endgame-score-gap-wrong-color (resolved)

## Root Cause

`colorFor(0)` returned green (`diff >= 0`), and the crossover detector used
`dA * dB < 0`. When the very first weekly bucket rounded to
`endgame === non_endgame` (diff=0), the initial `currentColor` was green and
`0 * (any negative) = 0` failed the strict `< 0` test, so every subsequent
negative-diff segment stayed green. Observed by the user on the all-time
view; the 1-year filter started from a firmly negative first bucket and
rendered red correctly, which pointed the diagnosis at the zero-start edge.

## Fix

`frontend/src/components/charts/EndgamePerformanceSection.tsx`

1. Initialize `currentColor` from the first NON-ZERO diff (walk the data
   array; fall back to `SCORE_TIMELINE_FILL_ABOVE` in the degenerate
   all-zero case where the band has zero thickness everywhere).
2. Change the sign-flip detector from `dA * dB < 0` to
   `colorFor(dA) !== colorFor(dB)`. When either endpoint is zero, the
   linear interpolation formula `t = dA / (dA - dB)` naturally lands at
   `t = 0` or `t = 1`, producing a coincident flip-stop at the segment
   boundary — visually an instant switch at the point where diff == 0.

Kept `type="monotone"` on the band `<Area>` and both `<Line>`s — the prior
fix that switched to `type="linear"` degraded the visual and was reverted.

## Tests

`frontend/src/components/charts/__tests__/EndgamePerformanceSection.test.tsx`

Added `ZERO_START_NEGATIVE_FIXTURE` + regression test asserting the last
gradient stop is `SCORE_TIMELINE_FILL_BELOW` when the first bucket rounds to
diff=0 and subsequent buckets are negative.

## Verification

- `cd frontend && npm test` — 106/106 pass (10/10 in EndgamePerformanceSection)
- `npx tsc --noEmit` — clean
- `npm run lint` — clean (3 pre-existing coverage-file warnings unrelated)

## Files Changed

- frontend/src/components/charts/EndgamePerformanceSection.tsx
- frontend/src/components/charts/__tests__/EndgamePerformanceSection.test.tsx
