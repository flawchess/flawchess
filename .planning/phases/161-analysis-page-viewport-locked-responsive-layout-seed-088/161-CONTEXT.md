# Phase 161: Analysis page viewport-locked responsive layout - Context

**Gathered:** 2026-07-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Convert the `/analysis` **desktop (`lg+`) layout** from *scrolling fixed-pixel columns* to a
**`100dvh`-locked, fluid** layout (chess.com/lichess model) so content stops cutting off at the
bottom on small laptop screens. The frame locks to viewport height (no page scroll), inner regions
scroll instead, the board sizes to the available height/width budget, horizontal space is reclaimed
(fixed-pixel flex row → CSS grid with a fluid middle), and the Tags/badges panel moves out of the
middle column into the bottom of the right column.

**Mobile (`<lg`) is explicitly unchanged** — the existing stacked/tab takeover is already good.

</domain>

<decisions>
## Implementation Decisions

### Locked by SEED-088 (design decided in the explore session — carry forward, do NOT re-litigate)
- **D-01:** Lock the desktop frame to `100dvh`, no page scroll; inner regions scroll instead.
  Touches the shell at `App.tsx:490` (`sm:h-auto sm:block` is currently NOT viewport-locked) and
  the page container at `Analysis.tsx:1983-1984`.
- **D-02:** Board sizes to `min(width budget, remaining height)` — lift the hard `maxWidth={600}`
  passed at `Analysis.tsx:1481` and the `Math.min(containerWidth, maxWidth)` logic in
  `ChessBoard.tsx` (see `updateWidth` / `ResizeObserver`, ~line 265) so the board responds to
  height, not just container width.
- **D-03:** Flex row → CSS grid `lg:grid-cols-[360px_1fr_360px]` (fixed side columns, fluid middle);
  widen/remove `max-w-7xl` and the center gutter at `Analysis.tsx:1984`. Grid row is
  `Analysis.tsx:1985`.
- **D-04:** Relocate the Tags/badges panel from the middle column (`tagsPanel(true)` at
  `Analysis.tsx:2050`) to the **bottom of the right column**. Right-column order becomes:
  **engine card → moves (variationTree, scrolls) → controls (boardControls) → tags** — append
  `tagsPanel(true)` after `boardControls()` at `Analysis.tsx:2127`. Keep the `withHighlight=true`
  variant so its hover-highlight into the eval chart still works (chart stays in the middle column).
  Revised middle column = **board + eval chart only**.
- **D-05:** Mobile (`<lg`) layout untouched.

### Breakpoint / staged-collapse strategy (open item #1 in the seed — DECIDED)
- **D-06:** **Raise the 3-column threshold, hard stack below it.** No intermediate staged-collapse
  stage (rejected chess.com's icon-collapse and the fluid-side-columns option). Above the threshold:
  full `[360][fluid board][360]`. Below it: fall straight to the existing mobile stack.
- **D-07:** **Set the threshold as low as viable (~1200px), NOT ~1300.** Because the middle board is
  now fluid, the 3-column layout stays viable down to roughly `360 + (~420 board floor + ~50 eval
  bars) + 360 ≈ 1190px`. Setting the threshold near that minimum keeps small laptops (1280 / 1366)
  in the **fixed desktop 3-column layout** — which is the whole point of this phase. **A threshold
  that pushes the reported small laptop into the mobile stack would be worse than the bug being
  fixed.** Intent is locked: small laptops stay desktop; the board shrinks fluidly to fit narrower
  widths. Exact px is a planning detail but must sit at/below ~1200 and below any typical small-laptop
  width. `lg` = 1024px is NOT a safe threshold (360+628+360 overflows it); the new threshold is a
  custom value (~1200) above `lg`.

### Board size ceiling (DECIDED)
- **D-08:** **Cap the board at 600px** — it only *shrinks* on short screens (floor ~420px), never
  grows past today's size. Sizing model: `clamp(420, min(widthBudget, heightBudget), 600)`. Rejected
  letting the board grow past 600 on tall/large screens (chess.com behavior) — avoids the board
  dominating large monitors and preserves current visual weight.

### Short-screen fallback (open item — DECIDED, refines the seed)
- **D-09:** **Page-scroll safety valve below a minimum usable height (~560px).** Not a strict lock at
  all heights. Behavior:
  - height **≥ ~560px**: `100dvh`-locked; once the board hits its ~420 floor, the **middle column**
    (board + eval chart) scrolls internally, page frame stays locked.
  - height **< ~560px**: **release the `100dvh` lock and let the whole page scroll** normally.
  This is a deliberate refinement of the seed's "always locked, middle column scrolls" — it adds a
  forgiving fallback for extreme-short windows at the cost of two behavior modes. Exact min-height px
  is a planning detail (~560 is the working figure).

### Claude's Discretion
- Exact breakpoint px for D-07 (target ~1200, must keep 1280/1366 laptops in desktop).
- Exact min-height px for the D-09 page-scroll fallback (~560 working figure).
- Height-budget accounting: how nav / player-name rows / eval chart / gaps are subtracted to compute
  the board's `heightBudget` (seed's open item #2). Planner derives this from measured/known heights.
- Mechanism for making ChessBoard height-aware (measure available height via the locked frame vs. a
  CSS `min()`/`clamp()` approach vs. JS measurement) — implementation choice for research/planning.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase origin / design decisions
- `.planning/phases/161-analysis-page-viewport-locked-responsive-layout-seed-088/SEED-088.md` — the
  explore-session diagnosis + the locked design (steps 1-6) + the two open items this discussion
  resolved. **The root-cause analysis and the chess.com live-test findings live here — read first.**

### Code touched by this phase
- `frontend/src/pages/Analysis.tsx` — desktop 3-column layout. Key lines: `1983-1985` (page
  container `max-w-7xl` + flex row → grid), `1481` (`maxWidth={600}` board cap), `2024-2051` (board
  column: board + eval chart + tags to relocate), `2050` (`tagsPanel(true)` current home), `2056-2128`
  (right column: engine card → variationTree → boardControls, append tags after `2127`).
- `frontend/src/components/board/ChessBoard.tsx` — board sizing. `~251` (`maxWidth = 400` default,
  `600` passed from Analysis), `~265` (`Math.min(containerWidth, maxWidth)` in `updateWidth`,
  `ResizeObserver`). Must become height-aware.
- `frontend/src/App.tsx:484-500` — analysis-route shell. `490`: `flex flex-col h-[100dvh] sm:h-auto
  sm:block` — the `sm:h-auto sm:block` is why desktop is NOT viewport-locked today. This is the
  frame-lock seam for D-01/D-09.

### No external specs
- No ADRs/PRDs for this phase — requirements fully captured in the decisions above + SEED-088.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AnalysisTagsPanel` (rendered via `tagsPanel(true)`): self-contained (`className` prop, no page
  coupling), already reflows for a narrow ~350px mobile-tab width → fits the `lg:w-[360px]` right
  column as-is (D-04). Keep the `withHighlight=true` variant for the eval-chart hover wiring.
- `ChessBoard`'s `ResizeObserver` + `boardWidth` state already exists — extend it to also account for
  available height rather than replacing it.
- The `100dvh` flex chain is already wired for mobile in `App.tsx:490` (`flex flex-col h-[100dvh]`);
  the desktop change is removing the `sm:h-auto sm:block` escape and extending the min-h-0/flex chain
  down to the analysis page container.

### Established Patterns
- Column-top alignment uses invisible spacer divs mirroring the player bar (`lg:invisible lg:-mb-2`
  at `Analysis.tsx:2000-2003` and `2063-2067`) — the grid conversion must preserve these so the
  Human / board / engine card tops stay aligned.
- Eval bars are `w-5` flanking slots (`Analysis.tsx:1434`, `evalBarSlot` at `1529`); the board's
  width budget in the middle column is `1fr` minus two `w-5` bars + `gap-2`.

### Integration Points
- Board column currently `lg:w-[628px]` (`Analysis.tsx:2025`) becomes the fluid `1fr` grid cell.
- Right column `lg:w-[360px]` (`Analysis.tsx:2056`) receives the relocated tags at its bottom.
- Frame lock spans `App.tsx` shell → `Analysis.tsx` `data-testid="analysis-page"` container
  (`1983`) → `main` (`1984`); all three need the min-h-0 / overflow chain for inner scrolling.

</code_context>

<specifics>
## Specific Ideas

- Reference model is **chess.com / lichess**: height-bound board that grows/shrinks with available
  height, fixed-width side panel absorbing no flex, internally-scrolling move list, page never scrolls
  on desktop. FlawChess differs by having 3 columns + a 120px eval chart stacked under the board —
  that stacked chart is exactly why FlawChess overflows where chess.com doesn't, so the fix centers on
  the middle column's height budget.
- Two reference screenshots from the explore session (FlawChess cut off vs. chess.com fitting at the
  same window size) motivated this phase.

</specifics>

<deferred>
## Deferred Ideas

- **Top-bar → left-sidebar nav** (would reclaim ~40px of height): raised and dropped in the explore
  session. It touches the global shell (`App.tsx` NavHeader), not just the analysis page. Reconsider
  only if a dedicated global-nav/shell pass happens — its own phase, not this one.
- **Intermediate staged-collapse stage** (chess.com-style icon-collapsed side columns between full
  3-column and mobile): considered and rejected for this phase (D-06). Could revisit if the simple
  hard-stack threshold proves too coarse in practice.

</deferred>

---

*Phase: 161-analysis-page-viewport-locked-responsive-layout-seed-088*
*Context gathered: 2026-07-09*
