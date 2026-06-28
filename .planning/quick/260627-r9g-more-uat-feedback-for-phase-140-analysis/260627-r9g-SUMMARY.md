---
quick_id: 260627-r9g
title: Phase 140 analysis-board UAT polish round 4
status: complete
date: 2026-06-27
---

# Quick Task 260627-r9g — Phase 140 analysis-board UAT polish (round 4)

Six frontend tweaks to the `/analysis` game board, plus mirroring the three
board-level changes onto the games-card hover MiniBoard (follow-up request).
Frontend only. No backend, schema, or new deps.

## What changed

1. **Move list max-height −25px.** `VariationTree` desktop list `max-h-[480px]` →
   `max-h-[455px]`.

2. **Zebra rows + sideline band.** Subtle `bg-foreground/[0.03]` stripe on odd
   desktop move-list rows. The injected `variation-pv-section` (and its nested
   sub-PV) inherits the fork row's zebra band so the whole sideline reads as one
   block. Mobile (horizontal chip list) has no rows — n/a.

3. **Engine info → fixed-height charcoal Card.** The engine area is now a `<Card>`:
   the info line (toggle + `SF 18, Depth d`) is the `<CardHeader>`; a fixed-height
   `<CardBody>` holds the lines. The "Analyzing…" and "Loading engine…" text are
   replaced by a shared `EngineLinesSkeleton` (animate-pulse bars). "Engine off"
   stays text.

4. **Severity arrows → corner glyphs.** The red/orange/yellow flaw arrow is gone;
   the played move now shows a Blunder (`??`) / Mistake (`?`) / Inaccuracy (`!?`)
   glyph in the target square's top-right corner. The inaccuracy glyph is new
   (`!?` on a yellow dot), added to the shared `SEVERITY_GLYPH` map.

5. **Severity-colored last-move overlay.** The played-move square overlay is now
   red (blunder) / orange (mistake) / yellow (inaccuracy, unchanged) / green
   (clean move) on the main line. `ChessBoard`/`MiniBoard` gained a `lastMoveColor`
   prop defaulting to the legacy yellow, so Openings/TrainSketch are untouched.

6. **Depth labels → top-left, smaller.** Arrow depth numbers moved from the
   top-right to the top-left corner and shrink via a max-px cap (smaller on the
   large desktop board, unchanged on the smaller mini/mobile boards).

**MiniBoard parity (follow-up):** items 4, 5, 6 also applied to the games-card
hover MiniBoard via shared `boardMarkers` primitives (`DepthLabel`,
`SquareMarkerGroup`) so both boards render identical marks.

## Key files

- `lib/severityGlyph.ts` (new) — `SEVERITY_GLYPH` map (symbol/color/fontSize), incl. `!?` inaccuracy
- `components/board/boardMarkers.tsx` (new) — shared `DepthLabel` (top-left) + `SquareMarkerGroup` SVG primitives
- `lib/theme.ts` — `MOVE_HIGHLIGHT_BLUNDER/MISTAKE/GOOD` overlay colors
- `hooks/useGameOverlay.ts` — drop flaw arrow; return `squareMarkers` + `lastMoveHighlightColor`
- `components/board/ChessBoard.tsx` — `squareMarkers` + `lastMoveColor` props; consume shared markers
- `components/board/MiniBoard.tsx` + `LazyMiniBoard.tsx` — same props plumbed through
- `components/results/LibraryGameCard.tsx` — flaw arrow → square marker + severity last-move color
- `pages/Analysis.tsx` — Card-wrapped engine area, skeleton loaders, wire markers/lastMoveColor
- `components/analysis/EngineLines.tsx` — `EngineLinesSkeleton`, replace Analyzing text
- `components/analysis/VariationTree.tsx` — max-h −25px, zebra rows + sideline band

## Verification

- `npx tsc -b` — clean
- `npm run lint` / `npx eslint src` — clean
- `npm run knip` — clean (no dead exports)
- `npm test -- --run` — 1203 passed (103 files). Updated 2 assertions
  (EngineLines "Analyzing…" text and Analysis "Loading engine…" text are now
  skeletons).

## Follow-up tweaks (round 4b)

- **Bigger, corner-overlapping severity badge on small boards.** `boardMarkers`
  now scales the glyph radius (0.18 of a square on large boards, 0.30 on mini
  boards <40px/square) and pulls the badge onto the square's top-right corner so it
  straddles/overlaps it instead of sitting fully inside.
- **Eval chart: chart hover/drag no longer moves the slider.** Hovering (desktop)
  or dragging over the chart (mobile) is now a transient preview that drives the
  board + tooltip but holds the slider thumb still. A `previewingRef` gates the
  `syncPly` echo, and the mobile chart-touch scrub previews via `hoverPly`
  (reverting on touch-end) instead of committing `sliderPly`. The slider is the
  commit input; move-list navigation still syncs the thumb.
- **Inaccuracy glyph flipped** `!?` → `?!` (standard dubious-move NAG).

## Notes / deviations

- Inaccuracy glyph is `?!` (the standard dubious-move NAG) after the round-4b flip.
- The standalone `InaccuracyIcon` React component was not added — the move list
  intentionally omits inaccuracy (D-03), so the glyph lives only in `SEVERITY_GLYPH`
  / the board markers (avoids a dead export).
- On the small games-card MiniBoard the glyph reads mostly as a colored badge;
  the `??`/`?`/`!?` text is legible on the large analysis board.
