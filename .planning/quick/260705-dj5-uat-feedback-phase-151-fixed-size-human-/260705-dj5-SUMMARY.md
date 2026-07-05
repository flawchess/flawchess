---
status: complete
---

# Quick Task 260705-dj5 — Summary

Phase 151 Maia UAT: fixed-size Human Move Probability card, wider chart with
right-side move labels, and horizontal grid lines.

## What changed

All in `frontend/src/components/analysis/MovesByRatingChart.tsx`:

- **Fixed-size loading (T1):** The `perElo.length === 0` branch now renders a
  fixed-height (`h-64`, shared `CHART_HEIGHT_CLASS` constant) pulsing skeleton
  (`animate-pulse rounded-md bg-muted/30`, `aria-busy`) instead of a short text
  line, so the card no longer jumps when Maia results arrive — same no-jump
  pattern as the engine (Stockfish) card. The "Waiting for Maia analysis…" text is
  kept as `sr-only` for screen readers (and the existing `aria-label`).
- **Wider plot + move labels (T2):** `YAxis width={36}` tightens the left gutter and
  `margin.right = 40` reserves room on the right; a per-line `LabelList` with a
  `content` render (`endOfLineLabel`) draws each shown move's SAN at its last ELO
  rung, in the line's own color — an on-chart legend matching the desktop
  reference image.
- **Horizontal grid lines (T3):** `<CartesianGrid vertical={false} />`, themed via the
  ChartContainer's existing `#ccc` → `stroke-border/50` override (same as ScoreChart).

Test update: the empty-state test now asserts the `moves-by-rating-chart-skeleton`
testid (and still checks the sr-only "Waiting" text).

## Verification

- `npx tsc -b` — clean.
- `npm run lint` — clean (only pre-existing `coverage/` warnings).
- `npm run knip` — clean (new `CartesianGrid` / `LabelList` imports both used).
- Vitest: `MovesByRatingChart` 7/7, `MaiaHumanPanel` 3/3.

## Note

jsdom does not lay out the SVG, so the unit tests do not assert the rendered
positions of the end-of-line labels or the exact plot width. A quick visual UAT in
the running app is recommended to confirm label placement and the left/right margin
balance look right against the reference image.

## Commit

`026e2edb` feat(151): fixed-size Maia card, wider chart with move labels + grid (UAT 260705-dj5)
