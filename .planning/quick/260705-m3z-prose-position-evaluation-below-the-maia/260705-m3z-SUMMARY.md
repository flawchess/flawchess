---
phase: quick-260705-m3z
plan: 01
subsystem: frontend-analysis
tags: [maia, analysis, prose, verdict, board-arrow, popover]
dependency-graph:
  requires: [positionVerdict.ts consumes moveQuality.ts's exported nearestByElo; MaiaMoveQualityBar's existing onHoverMovesChange/qualityHoverArrows mechanism (quick 260705-kfg)]
  provides: [positionVerdict.ts (computePositionVerdict, formatVerdictEval, joinMoveNames); prose resting-state verdict in MaiaMoveQualityBar]
  affects: [frontend/src/pages/Analysis.tsx (unchanged, reads the same onHoverMovesChange prop); frontend/src/components/analysis/MaiaHumanPanel.tsx (unchanged, unmodified call sites)]
tech-stack:
  added: []
  patterns: [pure classification module (badMass thresholds) mirroring moveQuality.ts's bucketing style; controlled Radix Popover for a hover+tap tooltip, reusing PercentileChip's convention rather than the touch-suppressing Tooltip primitive]
key-files:
  created:
    - frontend/src/lib/positionVerdict.ts
    - frontend/src/lib/positionVerdict.test.ts
  modified:
    - frontend/src/components/analysis/MaiaMoveQualityBar.tsx
    - frontend/src/components/analysis/__tests__/MaiaMoveQualityBar.test.tsx
    - frontend/src/lib/moveQuality.ts
decisions:
  - "Copy templates (safe / tricky / highly difficult sentences) were authored directly in this session — the referenced '/gsd-explore spec' was not persisted to a file in .planning/, so the exact wording is a new decision, not a verbatim transcription. Documented here for review."
  - "computePositionVerdict takes the perElo/selectedElo/shownSans/qualityBySan shape (mirrors bucketMovesByQuality) rather than a pre-derived array, keeping MaiaMoveQualityBar's wiring thin (no extra derivation step)."
  - "qualityBySan's value type is a locally-defined VerdictMoveGrade ({quality, evalCp, evalMate}) rather than importing MoveQualityEval from a component file, avoiding a lib->component dependency; MoveQualityEval is structurally identical so no cast is needed at the call site."
  - "'good' named-move list in the safe tier includes both 'best' and 'good' Stockfish-graded qualities (bucketMovesByQuality already folds them into one visual bucket); only tricky/difficult distinguishes an explicit 'escape' role for the 'best' move."
  - "Segment hover and prose-span hover are unified into a single hoveredArrowMoves useMemo (segment takes priority) instead of two independent effects, avoiding an effect-ordering race that could otherwise clobber a live segment arrow with a stale prose-hover cleanup."
metrics:
  duration: 25min
  completed: 2026-07-05
status: complete
---

# Phase quick-260705-m3z Plan 01: Prose position evaluation below the Maia move-quality bar Summary

Replaced the static "Hover a segment to list its moves..." resting-state help
text below the Maia move-quality bar with a computed prose verdict (safe /
tricky / highly difficult) at the selected ELO, driven by the summed Maia
probability mass of Stockfish-graded mistakes + blunders, with interactive
per-move spans that draw a severity-colored board arrow and a Maia%+eval
tooltip on hover or tap.

## What was built

**`frontend/src/lib/positionVerdict.ts`** (new, pure, no React) — exports:
- `SAFE_MAX_BAD_MASS` (0.20), `TRICKY_MAX_BAD_MASS` (0.50), `NAMED_MOVE_MIN_MASS` (0.08) — named thresholds, no magic numbers.
- `computePositionVerdict(perElo, selectedElo, shownSans, qualityBySan)` — returns `{ tier, moves }` or `null` (nothing to narrate yet: Maia not ready, or none of the shown moves are graded). `tier` is `'safe' | 'tricky' | 'difficult'` from `badMass` (mistake+blunder Maia mass only — inaccuracies excluded). Named moves are floor-filtered at `NAMED_MOVE_MIN_MASS`, except the single `'best'`-graded escape move in tricky/difficult, which is always named even below the floor.
- `formatVerdictEval(evalCp, evalMate)` — white-POV eval text, `"+1.2"`/`"-0.8"` for centipawns, `"M3"`/`"-M2"` for mate (deliberately different from `MovesByRatingChart`'s own `"#3"`/`"#-3"` chart-tooltip notation, which is untouched).
- `joinMoveNames(names, conjunction)` — list grammar: 1 → `"A"`; 2 → `"A and B"`; 3+ → `"A, B and C"` / `"A, B, C or D"` (no comma before the final conjunction).

**`frontend/src/lib/moveQuality.ts`** — exported the previously-private `nearestByElo` helper so `positionVerdict.ts` reuses the exact same ELO-ladder-nearest-rung lookup instead of re-deriving it.

**`frontend/src/lib/positionVerdict.test.ts`** (new, 27 tests) — verdict-tier boundaries at exactly/just-below/just-above 0.20 and 0.50; floor filtering at exactly/just-below 0.08; safe tier with zero good moves above the floor (empty move list, no crash); escape-move-always-present in both tricky and difficult at very low Maia %; graceful omission when no `'best'`-graded move exists; `joinMoveNames` for 1/2/3/4 items with both `"and"`/`"or"`; `formatVerdictEval` for cp+/mate+/-/ungraded.

**`frontend/src/components/analysis/MaiaMoveQualityBar.tsx`** — the resting-state slot (`data-testid="maia-quality-hovered-list"`) now renders, in priority order:
1. The hovered bar segment's move list (unchanged — bar-segment hover still fully overrides the slot exactly as before).
2. Otherwise, the prose verdict (`data-testid="maia-position-verdict"`) when `computePositionVerdict` has something to narrate.
3. Otherwise, the original static help text (unchanged fallback when nothing is graded yet).

Each named move renders as a `ProseMoveSpan` (`<button data-testid="maia-prose-move-{san}">`) colored per its role (bad = severity color; good/escape text = light green; escape arrow = dark green `MOVE_QUALITY_BEST`). A single hover (desktop) or tap (mobile, via the same `onMouseEnter`/`onClick`-toggle/`onFocus`/`onBlur` pattern already used by the bar segments) fires both:
- A board arrow, via the existing `onHoverMovesChange` prop (Analysis.tsx's `qualityHoverArrows` derives from/to squares from the current position — no new prop threading).
- A `Popover` tooltip (`data-testid="maia-prose-move-tooltip-{san}"`) showing `"{maiaPct}% at this rating · {evalText}"`, using Radix `Popover` (not the touch-suppressing `Tooltip` primitive) in a controlled open-state mode so it works on both mouse hover and touch tap.

Segment-hover state (`activeKey`) and prose-span-hover state (`activeProseSan`) are unified into one `hoveredArrowMoves` `useMemo` (segment takes priority) feeding a single `useEffect` that calls `onHoverMovesChange` — this avoids a two-effect ordering race that could otherwise let a prose-hover cleanup clobber a live segment arrow. Each hover source also proactively clears the other's state so the resting slot never renders both at once.

## Deviations from Plan

**1. [Rule 2 — missing test coverage for a changed contract] Updated the existing hover test's idle-state assertion + added a new fallback test**
- **Found during:** Task 2 verification (`npm test`)
- **Issue:** `MaiaMoveQualityBar.test.tsx`'s pre-existing hover test asserted the idle slot showed `/Hover a segment/` — but its fixture grades all four shown moves, so the new resting state correctly now shows the prose verdict instead (the intended behavior change of this task).
- **Fix:** Changed that assertion to check for `data-testid="maia-position-verdict"`; added a new test asserting the static help text still renders when `qualityBySan` is empty (nothing graded yet).
- **Files modified:** `frontend/src/components/analysis/__tests__/MaiaMoveQualityBar.test.tsx`
- **Commit:** `b31a1f45`

No other deviations — the pure module (Task 1) and the component wiring (Task 2) were implemented per the plan's `<action>` blocks.

## Verification

- `cd frontend && npm run lint` — clean (0 errors; 3 pre-existing warnings on generated `coverage/` files, unrelated).
- `cd frontend && npm test -- --run` — 1395 tests passed (117 files), including the 27 new `positionVerdict.test.ts` cases.
- `cd frontend && npm run build` — `tsc -b && vite build` succeeded, zero type errors.
- `cd frontend && npm run knip` — clean, no output (no dead exports / unused deps).
- Manual read-verification: `Analysis.tsx`'s desktop (`MaiaHumanPanel` at ~line 1384) and mobile (`humanTab` at ~line 1216) call sites are unchanged — both still pass `selectedElo`, `qualityBySan`, and `onHoverMovesChange={setHoveredQualityMoves}` into `MaiaHumanPanel`, which forwards them into `MaiaMoveQualityBar` unmodified.

## Self-Check: PASSED

- `frontend/src/lib/positionVerdict.ts` — FOUND
- `frontend/src/lib/positionVerdict.test.ts` — FOUND
- `frontend/src/components/analysis/MaiaMoveQualityBar.tsx` — FOUND (modified)
- Commit `402e4c80` (Task 1) — FOUND in `git log`
- Commit `b31a1f45` (Task 2) — FOUND in `git log`
