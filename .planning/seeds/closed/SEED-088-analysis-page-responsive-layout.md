---
title: Viewport-locked, fluid responsive layout for the /analysis page
trigger_condition: When next doing frontend/UX work on the analysis page, or when the small-laptop layout cutoff is prioritized
planted_date: 2026-07-09
source: /gsd-explore session 2026-07-09 (Adrian's small-laptop screenshots + live chess.com browser test)
---

# SEED-088: Analysis page responsive layout

On smaller laptop screens the `/analysis` page cuts off content at the bottom (the eval chart
falls off the window's bottom edge). See the two reference screenshots from the explore session:
FlawChess (cut off) vs. chess.com at the same window size (everything fits).

## Root cause (diagnosis)

The cutoff is a **vertical** overflow, not horizontal. The three columns fit width-wise; the
board is 600px tall and pushes the eval chart below the fold.

Current layout (`frontend/src/pages/Analysis.tsx`):
- `Analysis.tsx:1985` — three columns are **fixed pixels** (`lg:w-[360px]` / `lg:w-[628px]` /
  `lg:w-[360px]` ≈ 1412px total) switched by a **single** breakpoint (`lg`=1024px). Below `lg`
  everything stacks (mobile takeover). Nothing between.
- `Analysis.tsx:1984` — `mx-auto w-full max-w-7xl` caps content at 1280px and centers it (the
  "left margin" Adrian flagged). 1412 > 1280, so at `lg` the columns already overflow the cap.
- `ChessBoard.tsx` — board measures its container and caps at `maxWidth={600}`; it **never
  shrinks based on viewport height**.
- `App.tsx:490` — desktop shell is `sm:h-auto sm:block`, i.e. **not viewport-locked**; the page
  scrolls. chess.com/lichess lock to `100dvh` and size the board to the *remaining* height.

## What chess.com does (verified live via Chrome, 2026-07-09)

- Board is **height-bound** on desktop: at 596px viewport height the board was ~490px; at 713px
  it grew to ~560px (same width) — it sizes to available height, not width.
- Nav collapses in stages to reclaim width: full-label sidebar → **icon-only** sidebar (~1100px)
  → hamburger + stacked panel (~800px, the mobile layout).
- Right panel is **fixed-width**; the board column absorbs all the flex. The move list scrolls
  **internally**; the page never scrolls on desktop.
- (Couldn't force extreme-short heights — this display clamps the viewport to ~596–713px.)

Key difference: chess.com has only 2 content regions (board | panel) and **no eval chart under
the board** (just a thin eval bar beside it). FlawChess has 3 columns AND stacks a 120px eval
chart under a height-bound board — that stacked chart is exactly why FlawChess overflows where
chess.com doesn't.

## Design decided in the explore session

Convert the desktop (`lg+`) layout from *scrolling fixed-pixel columns* to *viewport-locked,
fluid* (chess.com/lichess model):

1. **Lock the frame to `100dvh`** on `lg+`, no page scroll. Inner regions scroll instead
   (change `App.tsx:490` shell + the page container).
2. **Board sizes to `min(width budget, remaining height)`** — lift the hard `maxWidth={600}` in
   `ChessBoard.tsx` so it grows on tall screens and shrinks on short ones. Floor at ~420px (the
   "up to 30% reduction" figure).
3. **Reclaim horizontal space** — widen/remove `max-w-7xl` and the center gutter (`Analysis.tsx:1984`)
   so the columns aren't cramped. Natural pivot: turn the flex row at `Analysis.tsx:1985` into a
   CSS grid (`lg:grid-cols-[360px_1fr_360px]`) with a fluid middle.
4. **Relocate the Tags/badges panel out of the middle column.** Today `tagsPanel(true)` renders
   under the eval chart at `Analysis.tsx:2050`. Move it into the **right column, at the bottom**.
   `AnalysisTagsPanel` is one self-contained component (`className` prop, no page coupling) and
   already reflows for a narrow (~350px mobile-tab) width, so it fits the `lg:w-[360px]` right
   column. Keep the `tagsPanel(true)` variant so its hover-highlight into the eval chart still
   works (chart stays visible in the middle column).
   - **Right column order becomes: engine card → moves (variationTree, scrolls) → controls
     (boardControls) → tags.** Controls stay glued directly under the moves (chess.com pattern);
     Tags drop below controls. Code-wise: append `tagsPanel` after `boardControls()` at
     `Analysis.tsx:2127`. Revised middle column = just **board + eval chart**.
5. **Short-screen fallback:** board floors at ~420px, then the **middle column** scrolls
   internally. Reduces (doesn't eliminate) the residual tension from the 120px chart still under
   the board — but makes it rare instead of common (the reported screenshot would now fit).
6. **Mobile (`<lg`) unchanged** — the existing stacked/tab takeover is already good.

## Explicitly out of scope (for now)

- **Top-bar → left-sidebar nav** (would return ~40px of height): raised and *dropped* in the
  session. It touches the global shell (`App.tsx` NavHeader), not just the analysis page.
  Reconsider only if a dedicated global-nav/shell pass happens.

## Open items for the plan phase (not decided)

- Where three columns should start: `lg`=1024px already overflows (360+628+360 > 1024). Likely
  needs a higher three-column threshold and/or an intermediate stage (narrower or icon-collapsed
  side columns), à la chess.com's staged collapse.
- Exact height budget accounting (nav / player-name rows / eval chart / gaps) that feeds the
  board's `min(width, height)` sizing.
