---
phase: 161-analysis-page-viewport-locked-responsive-layout-seed-088
reviewed: 2026-07-09T18:18:55Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - frontend/src/App.tsx
  - frontend/src/components/board/ChessBoard.tsx
  - frontend/src/components/board/__tests__/boardSize.test.ts
  - frontend/src/components/board/boardSize.ts
  - frontend/src/index.css
  - frontend/src/pages/Analysis.tsx
  - frontend/src/pages/__tests__/Analysis.test.tsx
findings:
  critical: 1
  warning: 3
  info: 1
  total: 5
status: issues_found
---

# Phase 161: Code Review Report

**Reviewed:** 2026-07-09T18:18:55Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Phase 161 was scoped as a client-side layout refactor of the `/analysis` page:
a new `computeBoardSize` helper, a `heightRef` prop on `ChessBoard` for
height-aware sizing, a viewport lock (`h-[100dvh]`) with two custom Tailwind
breakpoints (`desk3col`, `short`), and a 3-column grid on the analysis page.

The analysis-page-specific desktop layout logic is sound: the `min-h-0` flex
chain, the `sm:max-desk3col` unlock band (with a well-documented reason for
avoiding the `sm:` cascade-order trap), and the height budget flowing through
`flex-1` decoupling all hold up.

However, the sizing helper introduced a **cross-page regression**. The new
`BOARD_MIN_WIDTH` floor is applied unconditionally inside `computeBoardSize`,
so every `ChessBoard` caller that does *not* pass `heightRef` (the Openings
explorer board, the Openings games board, and the mobile analysis board) now
renders at a hard 420px regardless of container width or `maxWidth`. This
overflows the Openings desktop board's fixed 400px container and overflows the
board container on any phone narrower than 420px. The helper's own docstring
claims these callers behave "exactly as it was before this prop existed" — that
invariant is false. The unit tests miss the case entirely.

## Critical Issues

### CR-01: `BOARD_MIN_WIDTH` floor applied unconditionally overflows narrow containers and regresses every width-driven board

**File:** `frontend/src/components/board/boardSize.ts:26-29`

**Issue:**
`computeBoardSize` returns
`Math.max(BOARD_MIN_WIDTH, Math.min(widthBudget, heightBudget, maxWidth, BOARD_MAX_WIDTH))`.
The `Math.max(420, …)` floor is the *last* operation, so it can produce a size
larger than both the container width (`widthBudget`) and the caller's
`maxWidth`. Whenever `min(widthBudget, heightBudget, maxWidth, 600)` is below
420, the result is a hard **420** — the board is sized wider than the space it
sits in.

Concrete, provable regressions (all callers that do NOT pass `heightRef`, so
`heightBudget = Infinity`):

- **Openings desktop explorer board** (`Openings.tsx:924`) — sits inside a
  fixed `w-[400px]` container (`openingsBoardLayout.ts:18`), default
  `maxWidth = 400`. Before: `min(400, 400) = 400`. After:
  `max(420, min(400, ∞, 400, 600)) = max(420, 400) = 420`. The board overflows
  its own container by 20px.
- **Openings games board** (`Openings.tsx:1060`) — full-width `flex-1` container.
  On a 390px phone: `max(420, min(~380, ∞, 400, 600)) = 420`, overflowing the
  viewport (only masked, not fixed, by `body { overflow-x: hidden }` in
  `index.css:171` — the right file rank/edge is clipped).
- **Mobile analysis board** — the shared `boardRow` passes `heightRef`, but
  below `desk3col` its wrapper is natural-height, so `heightBudget` collapses to
  the board's own row height and the floor still pins it to 420 on sub-420px
  phones. Before phase 161 it was `min(containerWidth, 600)` and fit.

The docstring at `boardSize.ts:16-25` and the `ChessBoard.tsx:274-278` comment
both assert non-`heightRef` callers stay "width-driven exactly as it was
before" — the unconditional floor breaks that contract. The floor's true intent
(from the seed) is to resist the *height* budget on short viewports, not the
width/maxWidth budget.

**Fix:** clamp the floor so it can never exceed the width or `maxWidth` budget —
apply the floor only against the height dimension:

```ts
export function computeBoardSize(widthBudget: number, heightBudget: number, maxWidth: number): number {
  if (widthBudget <= 0 || heightBudget <= 0) return 0;
  // Floor fights only the HEIGHT budget (accept vertical scroll on a short
  // viewport); it must never make the board wider than its container or maxWidth.
  return Math.min(widthBudget, maxWidth, BOARD_MAX_WIDTH, Math.max(BOARD_MIN_WIDTH, heightBudget));
}
```

Verification against the intended cases:
- Openings mobile: `min(360, 400, 600, max(420, ∞)) = 360` ✓ (fits)
- Openings desktop: `min(400, 400, 600, ∞) = 400` ✓ (cap respected)
- Analysis short viewport: `min(600, 600, 600, max(420, 300)) = 420` ✓ (floors, scrolls)
- Analysis normal: `min(600, 600, 600, max(420, 480)) = 480` ✓ (height-driven)

## Warnings

### WR-01: Unit tests never exercise the regression case (width below the floor with unconstrained height)

**File:** `frontend/src/components/board/__tests__/boardSize.test.ts:4-29`

**Issue:** The suite covers width-driven (`500, ∞`), ceiling (`900, ∞`),
height-driven (`600, 480`), floor-via-height (`600, 300`), and the two
zero-guards. It never tests `computeBoardSize(width < 420, Infinity, maxWidth)`
— the exact shape of every non-`heightRef` caller (Openings, mobile). That gap
let CR-01 ship green. A test like
`expect(computeBoardSize(360, Infinity, 400)).toBe(360)` would have failed and
caught the overflow.

**Fix:** Add regression tests asserting the board never exceeds `widthBudget` or
`maxWidth`, e.g. `computeBoardSize(360, Infinity, 400) === 360` and
`computeBoardSize(300, Infinity, 600) === 300`. (These will fail against the
current implementation and pass against the CR-01 fix — add them alongside it.)

### WR-02: Right (side-panel) column omits `overflow-y-auto` that both sibling columns have; relocated tags panel can clip

**File:** `frontend/src/pages/Analysis.tsx:2068` (and D-04 relocation at 2141-2145)

**Issue:** Under the locked `desk3col` grid, the human column
(`Analysis.tsx:2004`) and the board column (`Analysis.tsx:2042`) both carry
`desk3col:overflow-y-auto`. The side-panel column carries only
`desk3col:min-h-0 desk3col:h-full` — no internal scroll. It now stacks engine
card + `VariationTree` (`flex-1`, scrolls internally) + `boardControls` +
the newly relocated `tagsPanel` (D-04). The `flex-1` tree absorbs slack, so in
the common case this fits, but on a viewport in the 560–~700px-tall locked band
in game mode with a tall tags panel, the fixed-height engine card + controls +
tags panel can exceed the column and the bottom content (the relocated tags
panel) clips with no way to scroll to it. The `short:` unlock only triggers
below 560px, leaving a gap.

**Fix:** Add `desk3col:overflow-y-auto` to the side-panel column for parity with
its siblings, or cap the tags panel with its own `min-h-0`/scroll so it can
never push `boardControls` off-column.

### WR-03: `heightRef` points at the board's own ancestor, making the height budget self-referential below `desk3col`

**File:** `frontend/src/pages/Analysis.tsx:1439` (`boardHeightRef` on `boardRow`), consumed at `ChessBoard.tsx:278`

**Issue:** `boardHeightRef` is attached to `boardRow`, which *wraps* the
`ChessBoard`. On desktop this is safe because `desk3col:flex-1` fixes the
wrapper's height independently of its child. But below `desk3col` the wrapper is
natural-height — its `clientHeight` is driven by the board it contains — so
`heightRef.current.clientHeight` feeds the board its own height back as the
"available" budget. It converges (and after the CR-01 fix converges harmlessly
because width becomes the binding constraint), but a `ResizeObserver` observing
an ancestor whose size is child-driven is the classic shape that emits
"ResizeObserver loop completed with undelivered notifications". The correctness
here rests entirely on the `flex-1` decoupling holding; it's fragile and
undocumented as a load-bearing assumption.

**Fix:** Point `heightRef` at a container whose height is *independent* of the
board (e.g. the board column itself, or an explicit height-defining wrapper),
or document at the ref site that the budget is only meaningful in the `flex-1`
(desk3col) layout and is a no-op elsewhere.

## Info

### IN-01: `maxWidth={600}` at the analysis call site duplicates `BOARD_MAX_WIDTH`

**File:** `frontend/src/pages/Analysis.tsx:1488` and `frontend/src/components/board/boardSize.ts:14`

**Issue:** The analysis board passes a literal `maxWidth={600}` while
`BOARD_MAX_WIDTH = 600` already caps the same dimension inside
`computeBoardSize`. The two 600s are independent literals that can silently
drift; per the project's no-magic-numbers rule the call site should reference a
named constant.

**Fix:** Import and pass `BOARD_MAX_WIDTH` (or a shared analysis-board constant)
instead of the bare `600`, so the ceiling has a single source of truth.

---

_Reviewed: 2026-07-09T18:18:55Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
