# Phase 161: Analysis page viewport-locked responsive layout - Research

**Researched:** 2026-07-09
**Domain:** Responsive CSS layout (Tailwind v4 grid/flex), height-aware component sizing (React + react-chessboard)
**Confidence:** HIGH

## Summary

This phase is a pure frontend layout refactor of `Analysis.tsx` / `ChessBoard.tsx` / `App.tsx` — no
new dependencies, no backend surface, no schema changes. All design decisions are locked in
`161-CONTEXT.md` (D-01…D-09); this research resolves the mechanical "how" for each, grounded in the
actual current code (all line numbers below verified in this session against the live files, not
copied from CONTEXT.md).

The single biggest de-risking finding: **the board cannot become height-aware via pure CSS.**
`ChessBoard.tsx`'s `ArrowOverlay` does `boardWidth / 8` arithmetic and sets SVG `width`/`height`
attributes directly from the numeric `boardWidth` React state — there is no way to hand it a CSS
`clamp()` string. The board's `ResizeObserver`-based measurement (already the established pattern
for width) must be extended to also read a **CSS-flexbox-resolved height budget**, not a
hand-computed `calc()` of magic-number pixel constants. Concretely: give the board's wrapper element
`flex-1 min-h-0` inside a height-locked flex column, and let the *browser's flex layout* compute the
remaining height after the header row / footer row / eval chart's `h-[120px]` take their share —
then have `ChessBoard`'s effect read that wrapper's `clientHeight` via a **second** `ResizeObserver`
target (or the same one, now observing an ancestor). This avoids hard-coding NavHeader/PlayerBar/gap
pixel heights (all of which are typography- and content-dependent, e.g. the mobile `text-sm` bump in
`index.css:313-317` — a `calc()` approach would silently drift out of sync with that).

Second major finding: there are **two independent breakpoint mechanisms** already in `Analysis.tsx`,
and only one of them is this phase's concern. `useIsMobile()` (`Analysis.tsx:139-151`) is a **JS
`matchMedia` hook at `640px`** that swaps between two entirely different JSX subtrees (true
mobile-tab-takeover UI vs. the desktop 3-column tree). Independently, inside the **desktop tree**,
Tailwind's `lg:` classes (`1024px`) currently decide 3-column-vs-stacked. D-07's "raise the threshold
to ~1200" only touches the second mechanism (the `lg:` → new custom-breakpoint swap inside the
desktop tree). It does **not** touch `MOBILE_BREAKPOINT_PX = 640` in `useIsMobile()`. Do not conflate
the two — CONTEXT.md's "existing mobile stack" refers to the desktop tree's own stacked fallback
(`flex flex-col` without the breakpoint prefix), which today already renders for 640–1023px and will,
after this phase, render for 640–(new threshold)px. This is intentional and already covered by D-06/
D-07 — flagging only so the planner doesn't accidentally also touch `useIsMobile()`.

Third finding: the mobile-first CSS polarity must **invert**, not just get a token rename. Today
`App.tsx:490` is base-locked (`h-[100dvh] flex flex-col`) with `sm:h-auto sm:block` **removing** the
lock at 640px+. Since D-05 requires everything below the new ~1200px threshold to behave like today's
unlocked/scrolling layout, the base (unprefixed) classes must become the **unlocked** state and the
new custom breakpoint variant must **add** the lock — the opposite direction from today's `sm:`
override. A literal find-replace of `sm:` → the new breakpoint token would preserve the wrong polarity
and lock the page at exactly the wrong widths.

**Primary recommendation:** Add one Tailwind v4 custom breakpoint token (`--breakpoint-<name>` in
`index.css`'s `@theme`, e.g. `desk3col: 1200px`) for D-07, remap all 6 existing `lg:` occurrences in
`Analysis.tsx`'s desktop-column block to it, invert the shell's lock/unlock base-vs-override polarity
in `App.tsx:490`/`493`, add `min-h-0` down through `Analysis.tsx:1984` (main) → `1985` (grid row) →
each column div, and extend `ChessBoard`'s existing `ResizeObserver` pattern with a
flexbox-resolved height read rather than a magic-number `calc()`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Viewport-lock / scroll containment | Browser / Client (CSS) | — | Pure CSS flexbox `min-h-0`/`overflow` chain, no server involvement |
| Board width/height sizing | Browser / Client (React component) | — | `ChessBoard.tsx` owns its own `ResizeObserver`-driven sizing; purely client-side |
| 3-column ↔ stacked breakpoint | Browser / Client (CSS + one JS hook) | — | Tailwind custom breakpoint (CSS) for the grid; separate pre-existing JS `matchMedia` hook for the mobile-tree swap (untouched by this phase) |
| Tags panel relocation | Browser / Client (JSX reorder) | — | `AnalysisTagsPanel` is self-contained; this is pure JSX reordering, no new data flow |

All capabilities in this phase live entirely in the browser/client tier — there is no
frontend-server, API, CDN, or database dimension to this work.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SEED-088 | Convert `/analysis` desktop layout from scrolling fixed-pixel columns to a `100dvh`-locked, fluid, height-aware layout so content stops cutting off on small laptop screens (per `161-CONTEXT.md` D-01…D-09) | All 6 findings below (height-aware board, min-h-0 chain, height-budget accounting, custom breakpoint, short-screen fallback, grid-conversion gotchas) directly implement the locked design |

</phase_requirements>

## Standard Stack

No new libraries are introduced by this phase. Existing stack, versions confirmed from
`frontend/package.json` this session:

| Library | Version | Purpose | Relevance to this phase |
|---------|---------|---------|--------------------------|
| tailwindcss | ^4.3.0 [VERIFIED: frontend/package.json] | Utility CSS, CSS-first `@theme` config | Custom breakpoint token (D-07), arbitrary/custom variants (D-09) |
| react-chessboard | ^5.10.0 [VERIFIED: frontend/package.json] | Board rendering | Consumes only a numeric px `width`/`height` via `boardStyle` — confirms JS-measured (not CSS-only) sizing is required |
| react | (project pin, unrelated to this phase) | — | `useEffect`/`ResizeObserver` pattern already established in `ChessBoard.tsx` |

**Installation:** none — no `npm install` needed for this phase.

## Package Legitimacy Audit

Not applicable — this phase adds no new npm packages. No legitimacy check was run since there is
nothing to check.

## Architecture Patterns

### System Architecture Diagram

```
Browser viewport (100dvh)
        │
        ▼
App.tsx shell  ── <div className="flex flex-col h-[100dvh] ...">  (D-01: lock spans ALL breakpoints
        │                                                           now; today only <640px)
        ├── NavHeader (fixed natural height, ~45px, "hidden sm:block")
        │
        ▼
main (flex-1 min-h-0)  ── App.tsx:493, remove "sm:block sm:flex-none" escape
        │
        ▼
Outlet → Analysis.tsx desktop return (isMobile === false branch, line 1982)
        │
        ▼
analysis-page div (flex min-h-0 flex-1 flex-col)  ── ALREADY has min-h-0 (mobile-inherited)
        │
        ▼
inner <main> (Analysis.tsx:1984)  ── MISSING min-h-0 today; must add
        │
        ▼
grid row (Analysis.tsx:1985)  ── flex flex-col lg:flex-row  →  grid <newbp>:grid-cols-[360px_1fr_360px]
        │            needs min-h-0 + h-full at the new breakpoint so columns can stretch/scroll
        │
   ┌────┼───────────────────────┬─────────────────────────┐
   ▼    ▼                       ▼                         ▼
Human   Board column            Right column
column  (flex-col, min-h-0)     (flex-col, min-h-0)
(1993)  ├─ boardHeaderRow (nat) ├─ engine card (nat height, Card)
        ├─ boardRow (flex-1?)  ├─ variationTree('responsive')  ← ALREADY has its own
        │    ChessBoard reads      internal min-h-0 flex-1 overflow-y-auto
        │    available height      (VariationTree.tsx:683/883/930/939) — just needs the
        │    from this wrapper     ANCESTOR chain to actually bound its height
        ├─ boardFooterRow (nat) ├─ boardControls() (nat height)
        ├─ evalChart h-[120px]  └─ tagsPanel(true) ← RELOCATED HERE (D-04), was in
        └─ (tagsPanel REMOVED       board column, now appended after boardControls()
            from here, D-04)
```

A reader tracing the primary use case (page load → board fits on screen without cutoff): viewport
height flows down through the `100dvh` lock, through `min-h-0` at every flex level (the chain breaks
today at `Analysis.tsx:1984`'s inner `<main>`), into the grid row, into the board column, where the
board's own wrapper div resolves to a concrete pixel height via flex distribution — which
`ChessBoard`'s `ResizeObserver` then reads to size the board itself.

### Recommended structural changes (not a new folder layout — this is a same-file refactor)

No new files. Changes concentrated in 3 existing files:
```
frontend/src/
├── App.tsx                        # shell lock/unlock polarity inversion (D-01/D-09 seam)
├── index.css                      # new @theme --breakpoint-<name> (D-07) + optional
│                                   #   @custom-variant for the short-screen fallback (D-09)
├── pages/Analysis.tsx              # grid conversion (D-03), tags relocation (D-04),
│                                   #   min-h-0 chain, remap lg: → new breakpoint token
└── components/board/ChessBoard.tsx # extend ResizeObserver to read height, drop hard
                                     #   maxWidth={600} ceiling logic in favor of clamp(420,·,600)
```

### Pattern 1: Height-aware board sizing via flexbox-resolved measurement (D-02/D-08)

**What:** Instead of computing `heightBudget` as `100dvh - navHeight - playerBarHeight - evalChartHeight
- gaps` (a `calc()`/JS arithmetic of magic-number pixel constants — explicitly the CLAUDE.md "No magic
numbers" rule this would violate), give the board's own wrapper a CSS-resolved height via `flex-1
min-h-0` inside an already-bounded flex column, and read `clientHeight` off that wrapper.

**When to use:** Whenever a sized-by-content element must fit "whatever space is left" in a flex
layout where the other siblings' heights are either fixed (`h-[120px]` eval chart) or natural
(header/footer text rows) — exactly this phase's case.

**Example (illustrative signature — planner formalizes exact prop/effect wiring):**
```tsx
// ChessBoard.tsx — extend the existing effect (currently only reads containerWidth)
useEffect(() => {
  const updateSize = () => {
    if (!containerRef.current) return;
    const containerWidth = containerRef.current.clientWidth;
    // heightRef points at a wrapper the caller sizes via flex-1 min-h-0 (Analysis.tsx
    // gives the board row this treatment); when unset (e.g. Openings mini-board caller),
    // heightBudget is Infinity so the size is width-driven exactly as it is today.
    const heightBudget = heightRef?.current?.clientHeight ?? Infinity;
    const next = Math.min(containerWidth, maxWidth, heightBudget);
    setBoardWidth(Math.max(BOARD_MIN_WIDTH, Math.min(next, BOARD_MAX_WIDTH)));
  };
  updateSize();
  const observer = new ResizeObserver(updateSize);
  if (containerRef.current) observer.observe(containerRef.current);
  if (heightRef?.current) observer.observe(heightRef.current);
  return () => observer.disconnect();
}, [maxWidth, heightRef]);
```
`BOARD_MIN_WIDTH = 420` / `BOARD_MAX_WIDTH = 600` are the D-08 floor/ceiling — named constants, not
literals, per CLAUDE.md.

**Why this beats the alternatives:**
- *Pure CSS `min()`/`clamp()` on the container* — rejected: `ArrowOverlay` needs a JS number for SVG
  `width`/`height` and `sqSize = boardWidth / 8` arithmetic (`ChessBoard.tsx:147,163-164`); a CSS-only
  size can't be read back into JS without... a `ResizeObserver` anyway, so CSS-only buys nothing.
- *Hand-computed `calc()` height budget* — rejected: requires hard-coding NavHeader (~45px, itself not
  a fixed value — it wraps to 2 rows on some `navItems` configs since it has no `flex-wrap: nowrap`
  guard), `PlayerBar` height (`text-sm`, which is `1rem`/`16px` on mobile per `index.css:315` vs. the
  Tailwind default `0.875rem` — this project overrides `.text-sm` below `640px` only, but the analysis
  desktop tree also renders `PlayerBar` at `text-sm` above 640px, so the value differs by breakpoint),
  and `gap-4`/`gap-2` spacing constants. Any of these drifting (a future UI tweak bumping `PlayerBar`
  padding, e.g.) silently breaks the `calc()` without a build-time signal. The flex measurement
  approach has zero such magic numbers — the browser computes them.
- *JS measurement of the locked frame's total height, then subtract concrete estimates* — same
  fragility as `calc()`, just moved from CSS to JS; rejected for the same reason.

### Pattern 2: `100dvh` lock inversion + `min-h-0` propagation chain (D-01/D-09)

**What:** The base (mobile-first, unprefixed) classes at `App.tsx:490` become the **unlocked**
state (matches today's post-`sm:` desktop behavior, i.e. what should still show below the new
threshold); the new custom breakpoint variant **adds** the lock, instead of removing it.

**Concretely (illustrative — planner picks exact variant name/values):**
```tsx
// App.tsx:490 — polarity inverted from today's "locked-by-default, sm: unlocks"
// to "unlocked-by-default (mobile+tablet, matches today's scroll behavior below the
// new threshold), <newbp>: locks (this phase's new desktop behavior)."
<div className="h-auto block <newbp>:flex <newbp>:flex-col <newbp>:h-[100dvh]">
```
```tsx
// App.tsx:493 — main must stay flex-1 min-h-0 unconditionally ABOVE the new breakpoint;
// below it, block/flex-none (today's sm: escape) so mobile/tablet scrolling is untouched.
<main className="block flex-none <newbp>:flex-1 <newbp>:min-h-0 <newbp>:flex <newbp>:flex-col">
```

**`min-h-0` chain — every element below that must shrink below its content size** (add where
missing; ✓ = already present as of this research session):
1. `App.tsx:493` `<main>` — add `<newbp>:min-h-0` (currently unconditional `min-h-0` but escaped by
   `sm:block sm:flex-none` — needs the same inversion as above)
2. `Analysis.tsx:1983` `analysis-page` div — ✓ already `flex min-h-0 flex-1 flex-col`
3. `Analysis.tsx:1984` inner `<main>` — **missing `min-h-0` today** — must add
   `<newbp>:min-h-0 <newbp>:flex <newbp>:flex-col <newbp>:h-full` (it's currently a plain block
   `<main>` with no flex properties at all; on desktop it needs to become a flex column that fills
   the parent so children can distribute the constrained height)
4. `Analysis.tsx:1985` grid row div — add `<newbp>:min-h-0 <newbp>:h-full` alongside the new
   `<newbp>:grid-cols-[360px_1fr_360px]` (replacing `flex flex-col lg:flex-row lg:items-stretch`)
5. Board column div (`Analysis.tsx:2025`) — add `<newbp>:min-h-0 <newbp>:h-full`; this is the column
   whose internal middle section (board + eval chart) is the D-09 scroll target when the board hits
   its 420px floor
6. Right column div (`Analysis.tsx:2056`) — add `<newbp>:min-h-0 <newbp>:h-full` — `VariationTree`'s
   own internal `min-h-0 flex-1 overflow-y-auto` (confirmed present at `VariationTree.tsx:683,883,930,
   939`) is a no-op until this ancestor actually has a bounded height to constrain it to; today the
   column's height comes from `lg:items-stretch` matching the tallest sibling (the board column,
   itself content-driven) — under the new locked/grid layout the row's height comes from the frame,
   not from content, so this needs to be explicit.
7. Human column div (`Analysis.tsx:1993`) — same treatment as the right column (no internally-scrolling
   content today, but should not overflow the grid row's bounded height either — verify `MaiaHumanPanel`
   content doesn't need its own scroll region; out of research scope to inspect further, flag as an
   **Open Question**).

**Anti-pattern to avoid:** applying `min-h-0` only to the grid row and assuming it "flows down" —
`min-h-0` is not inherited; every flex/grid item in the chain that needs to shrink below its content
height must set it explicitly on itself.

### Pattern 3: Tailwind v4 custom breakpoint (D-07)

**What:** Tailwind v4 uses CSS-first configuration. A new named breakpoint is declared as a
`--breakpoint-*` theme variable inside `@theme` in `index.css`, generating a new variant usable
anywhere in the codebase [CITED: tailwindcss.com/docs/theme, tailwindcss.com/docs/responsive-design].

```css
/* frontend/src/index.css, inside the existing @theme inline { ... } block or a sibling @theme block */
@theme {
  --breakpoint-desk3col: 1200px; /* exact px is Claude's discretion per CONTEXT.md, target ~1200 */
}
```
Usage: `desk3col:grid-cols-[360px_1fr_360px]` (replacing every `lg:` in the block spanning
`Analysis.tsx:1985-2128`). **Confirmed scope: exactly 6 occurrences of `lg:`** in `Analysis.tsx`
(grep-verified this session) — lines 1985, 1993, 2000, 2025, 2056, 2064. All 6 are inside the
desktop-column block and must remap; no other `lg:` usage in the file needs touching.

**Alternative (one-off, no config change):** Tailwind v4 also supports arbitrary breakpoint variants
inline: `min-[1200px]:grid-cols-[...]` [CITED: tailwindcss.com/docs/responsive-design]. **Recommend
the named `@theme` token over the arbitrary inline form** — it's used in 6 places across one file
today but is conceptually a single semantic threshold ("desktop 3-column layout is viable"); a named
token documents that intent once and avoids 6 repeated magic numbers, and if the planner's exact px
choice needs revision later (Claude's discretion note in CONTEXT.md acknowledges the exact figure is
still open) it's a one-line change instead of 6.

**`lg:` remapping is NOT a blanket rename** — do not touch `lg:` occurrences elsewhere in the
codebase (e.g. `Openings.tsx`, `Endgames.tsx` sidebars) — this phase is `/analysis`-scoped only per
the CONTEXT.md domain boundary.

### Pattern 4: Short-screen page-scroll fallback (D-09)

**What:** Below ~560px viewport height, release the `100dvh` lock entirely (whole page scrolls,
not just the middle column). Two independent axes are now in play: the **width** breakpoint (D-07,
~1200px, decides 3-col vs. stacked) and a **height** breakpoint (D-09, ~560px, decides
locked-with-inner-scroll vs. fully-unlocked-page-scroll). These are orthogonal — a wide-but-short
window (e.g. an ultrawide monitor with a short browser window) hits the height fallback regardless of
the width breakpoint.

**Mechanism — Tailwind v4 custom variant for a height media feature** [CITED:
tailwindcss.com/docs/adding-custom-styles, confirmed via web search this session against the
`@custom-variant` directive]:
```css
/* index.css */
@custom-variant short (&:is(@media (max-height: 559.98px)));
```
Or the one-off arbitrary form directly in the className: `[@media(max-height:559.98px)]:h-auto`.
**Recommend the named `@custom-variant`** for the same reason as Pattern 3 — it's a semantic
threshold applied at more than one class in the shell (`App.tsx:490` needs it to release `h-[100dvh]`,
and potentially the board-column's internal scroll region needs its `overflow-y-auto` suppressed so
the *whole page* scrolls instead of double-nested scroll regions competing).

**Interaction with the min-h-0 chain (Pattern 2):** when the height fallback triggers, the
`<newbp>:h-full`/`<newbp>:min-h-0` classes down the chain should NOT be undone — releasing `100dvh`
on the shell alone is enough to let the whole page's natural content height take over, because CSS
flexbox children with `min-h-0` don't force their own height, they only ALLOW shrinking; once the
ancestor's height itself becomes `auto` (content-driven) instead of `100dvh`, the whole chain's
resolved heights become content-sized again and the middle column's own internal `overflow-y-auto`
becomes moot (nothing to scroll internally — the outer page scrolls instead). This means the `short:`
variant only needs to be applied at the **shell level** (`App.tsx:490`/`493`), not repeated at every
level of the chain — a useful simplification for the planner's task breakdown.

### Anti-Patterns to Avoid
- **Renaming `sm:` to the new breakpoint token 1:1 without inverting which side has the lock** — see
  Summary; this is the single highest-risk mechanical mistake in this phase.
- **Computing `heightBudget` as a `calc()` of hard-coded pixel constants** — violates CLAUDE.md's
  "No magic numbers" rule and drifts silently when any sibling's height changes (font-size media
  queries, a future `PlayerBar` padding tweak, etc.). Use the flexbox-resolved measurement (Pattern 1)
  instead.
- **Forgetting `min-h-0` at any single link in the chain** — the visible symptom is identical to the
  original bug (content pushes past the viewport) even though the top-level shell is `100dvh`-locked,
  which will read as "the fix didn't work" during UAT. Verify all 6 chain links in Pattern 2.
- **Changing `MOBILE_BREAKPOINT_PX` (640, `Analysis.tsx:108`) or `useIsMobile()`** — out of scope;
  this hook governs an entirely separate JSX-tree swap, not the 3-column grid threshold.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Height-based responsive breakpoint | A JS `window.innerHeight` listener + React state for the ~560px fallback | Tailwind v4 `@custom-variant` with a `max-height` media feature (Pattern 4) | Declarative, no extra re-render on every resize event, consistent with how the width breakpoint is already handled via CSS |
| Board height availability | A second bespoke height-tracking hook duplicating `ChessBoard`'s existing `ResizeObserver` logic | Extend the same effect/observer already in `ChessBoard.tsx:262-277` to also observe a height-bounding element | One code path, one set of edge cases (the existing 0-width-before-mount guard already documented at `ChessBoard.tsx:253-257` needs the analogous 0-height guard, not a second one) |

**Key insight:** every piece of "don't hand-roll" guidance here is really "extend the existing
pattern, don't add a parallel one" — this phase has almost no genuinely new mechanism, it's
recombining patterns already proven elsewhere in this codebase (width `ResizeObserver`, Tailwind
custom breakpoints aren't used yet in this repo but are first-class in the installed v4).

## Common Pitfalls

### Pitfall 1: react-chessboard mount-at-zero-size crash recurs for height too
**What goes wrong:** `ChessBoard.tsx:253-257`'s comment documents that mounting `react-chessboard`
with a non-zero width inside a `display:none` parent throws "Square width not found." The same class
of bug applies to height: if the new height-observing wrapper resolves to `0` during initial paint
(e.g., before the flex layout has settled, or briefly during a breakpoint transition), `boardWidth`
could compute to `0` via `Math.min(..., 0)`.
**Why it happens:** `ResizeObserver` fires asynchronously after layout; the first synchronous
`updateSize()` call at effect-mount time may run before the flex ancestor has been assigned its
final height by the browser's layout pass, especially across a `<newbp>:` breakpoint crossing.
**How to avoid:** Keep the existing `boardWidth > 0` gate (`ChessBoard.tsx:407`) as the single guard
— do not special-case a "height not ready yet" state separately; treat `heightBudget` the same as
`containerWidth` (both must be `> 0` before rendering `<Chessboard>`).
**Warning signs:** Board flashes/disappears momentarily when resizing the window across the new
breakpoint threshold; Sentry error "Square width not found" reappearing (previously fixed per the
comment at `ChessBoard.tsx:253`).

### Pitfall 2: Two independent breakpoint systems create a confusing "why is this still stacked" bug
**What goes wrong:** A developer testing at, say, 900px width sees a stacked layout and assumes the
new D-07 threshold (~1200px) is misconfigured, when actually `useIsMobile()`'s separate 640px hook
already puts them in a different code branch than expected — or vice versa, someone "fixes" the
apparent bug by lowering `MOBILE_BREAKPOINT_PX`, silently changing the true mobile-tab-takeover
threshold as an unintended side effect.
**Why it happens:** `useIsMobile()` (JS `matchMedia`, swaps entire JSX subtree) and the Tailwind
`lg:`/new-custom-breakpoint (CSS, swaps grid layout within the desktop subtree) are both "mobile
detection" in spirit but serve different purposes and have different thresholds (640 vs. ~1024→1200).
**How to avoid:** Document (in the plan or inline comment) that these are two separate mechanisms and
this phase only touches the CSS one. Verify behavior at three distinct width bands during UAT: <640px
(true mobile tree), 640–(new threshold) (desktop tree, stacked fallback), ≥(new threshold) (desktop
tree, 3-column grid).
**Warning signs:** Layout looks "half mobile, half desktop" (e.g., `AnalysisMobileHeader` visible
alongside desktop-tree-only elements) — that combination is impossible given the current code
structure, so if seen, something was miswired.

### Pitfall 3: Column-top alignment spacers silently misalign under CSS Grid
**What goes wrong:** The invisible spacer pattern (`Analysis.tsx:2000-2003`, `2063-2067`:
`hidden lg:block lg:invisible lg:-mb-2` wrapping a duplicate `playerBar()` call) exists to make the
Human/Board/Engine column tops visually align despite the board column's extra `boardHeaderRow` (with
source caps) sitting above the actual board. This relies on the spacer rendering at **exactly the same
height** as the real `boardHeaderRow`'s player-bar row in the middle column. Under flexbox
`items-stretch` today, all three columns are independent flex items with independently-computed
natural heights: the spacer's height is driven purely by its own content (an invisible `PlayerBar`),
which is identical in both places, so this already works by construction, not by row-based grid
alignment. **Converting the row to CSS Grid does not break this** as long as each column remains an
independent grid item stacking its own children in a `flex flex-col` (i.e., grid only governs the
3-column widths; vertical alignment within each column stays flexbox) — but if the grid conversion is
done naively with `display: grid` on `Analysis.tsx:1985` governing BOTH rows and columns (a full 2D
grid with named rows), the spacer trick would need re-verification since grid track sizing (not
flexbox natural-height stacking) would then govern each row's height.
**How to avoid:** Keep the grid as **1-dimensional** — `grid-cols-[360px_1fr_360px]` for column
widths only, with each column `<div>` remaining `flex flex-col` internally exactly as today. Do not
introduce `grid-template-rows` / `grid-row` placement — nothing in the locked decisions calls for it,
and it would be the one part of this refactor genuinely novel enough to risk misalignment.
**Warning signs:** Human/Engine card tops no longer align with the board top after the grid
conversion — a purely visual regression, easy to catch in the same UAT pass as the breakpoint checks.

### Pitfall 4: `evalBarSlot`'s `w-5` flanking columns are unaffected by the grid conversion, but easy to second-guess
**What goes wrong:** `evalBarSlot` (`Analysis.tsx:1529-1531`, `w-5 shrink-0`) and the `EvalBar`
components in `boardRow` (`Analysis.tsx:1447-1497`, bare `w-5` via `EvalBar.tsx:117`) are nested
**inside** the middle grid column, in a flex-row of their own (`boardRow`'s
`flex flex-row items-stretch gap-2`) — they are not part of the 3-column grid at all. A developer
reviewing the CONTEXT.md's "board width budget = `1fr` minus two `w-5` bars + `gap-2`" note might
mistakenly try to express the eval bars as additional grid columns.
**How to avoid:** Leave `boardRow`'s internal flex-row untouched; the D-03 grid conversion applies
only at `Analysis.tsx:1985` (the 3-column row), not at `Analysis.tsx:1434`'s eval-bar-flanking row.
The middle grid column's available width for `ChessBoard`'s `containerWidth` measurement is
implicitly `1fr` (the grid track) minus the two `w-5` (20px each, Tailwind default spacing scale
[ASSUMED]) bars and the `gap-2` (8px [ASSUMED]) — but this arithmetic happens for free via the
existing flex-row layout and `ChessBoard`'s own `containerRef.clientWidth` read; no new width
calculation is needed here, only the height addition from Pattern 1.
**Warning signs:** None expected if the grid conversion stays scoped to line 1985 only — this pitfall
is more "don't overthink it" than "watch for a bug."

## Code Examples

### Verified: current numeric width-measurement pattern (unchanged, to be extended)
```tsx
// Source: frontend/src/components/board/ChessBoard.tsx:262-277 (read in full this session)
useEffect(() => {
  const updateWidth = () => {
    if (containerRef.current) {
      const containerWidth = containerRef.current.clientWidth;
      setBoardWidth(Math.min(containerWidth, maxWidth));
    }
  };
  updateWidth();
  const observer = new ResizeObserver(updateWidth);
  if (containerRef.current) observer.observe(containerRef.current);
  return () => observer.disconnect();
}, [maxWidth]);
```

### Verified: react-chessboard v5 consumes a plain numeric px style, not a CSS expression
```tsx
// Source: frontend/src/components/board/ChessBoard.tsx:337-340
const boardStyle = useMemo<React.CSSProperties>(
  () => ({ width: boardWidth, height: boardWidth, borderRadius: '0.5rem' }),
  [boardWidth],
);
// ... passed into options.boardStyle, consumed by <Chessboard options={options} /> (v5.10.0)
```
This confirms the width/height must be resolved to a number in JS before reaching the board —
supporting the Pattern 1 recommendation over a CSS-only approach.

### Verified: `VariationTree` already implements the internal-scroll half of the D-09 contract
```
// Source: frontend/src/components/analysis/VariationTree.tsx (grep-verified this session)
// line 683: className="min-h-0 flex-1 overflow-y-auto thin-scrollbar"   (mobile/responsive strip)
// line 883: className="absolute inset-0 overflow-y-auto thin-scrollbar" (desktop vertical list)
// line 930/939: outer wrapper "flex min-h-0 flex-1 flex-col" / "sm:flex sm:flex-col"
```
No changes needed inside `VariationTree.tsx` itself — it already assumes a height-bounded ancestor
and will "just work" once `Analysis.tsx`'s right-column ancestor chain (Pattern 2, item 6) actually
constrains its height.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `App.tsx:490` locked-by-default, `sm:` (640px) unlocks | Unlocked-by-default, new custom breakpoint (~1200px) locks | This phase | Inverts the CSS cascade direction for the shell — see Pitfall/Pattern 2 |
| `lg:` (1024px, Tailwind default) decides 3-col vs. stacked in `Analysis.tsx` | New named custom breakpoint (~1200px) decides it | This phase | 6 occurrences remapped; no other `lg:` in the file touched |
| Board hard-capped at `maxWidth={600}`, width-only sizing | `clamp(420, min(width, height), 600)`, height-aware | This phase | `ChessBoard.tsx`'s effect gains a second observed target |
| Tags panel under the eval chart (middle column) | Tags panel at bottom of right column | This phase (D-04) | Pure JSX relocation, `AnalysisTagsPanel` itself untouched |

**Deprecated/outdated:** none — this is a first-time introduction of a height-aware layout for this
page, not a replacement of a previously-deprecated pattern.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Tailwind v4 default spacing scale: `w-5` = 20px, `gap-2` = 8px, `gap-4` = 16px | Pitfall 4 / Architecture Diagram | Low — these are Tailwind's well-known default `--spacing` multiplier (`0.25rem` unit) values, not verified via a live tool call this session; if wrong, only affects the precision of the illustrative width-budget arithmetic, not the mechanism itself (the browser computes real values regardless) |
| A2 | NavHeader resolves to ~44-45px tall (its tallest child is the `h-11 w-11` logo image, no header-level padding) | Height-budget discussion (Summary) | Low — this figure is only used to explain *why* a `calc()` approach is fragile, not fed into any implementation; the recommended Pattern 1 approach doesn't depend on this number at all |
| A3 | Tailwind v4's `@theme { --breakpoint-name: value }` generates a `name:` variant usable identically to built-in breakpoints (e.g. `lg:`) | Pattern 3 | Medium — sourced from WebSearch against tailwindcss.com docs, not Context7-verified against this exact installed version (^4.3.0); if the exact variant-naming behavior differs slightly, the planner should confirm against `tailwindcss.com/docs/theme` before finalizing the token name |
| A4 | Tailwind v4's `@custom-variant` directive supports a `max-height`/`min-height` media-feature wrapped in `&:is(@media (...))` syntax as shown in Pattern 4 | Pattern 4 | Medium — same sourcing caveat as A3; the arbitrary inline form (`[@media(max-height:560px)]:`) is the safer fallback if the named `@custom-variant` syntax doesn't compile as written |

## Open Questions

1. **Does the Human column (`Analysis.tsx:1993`, `MaiaHumanPanel` + FlawChess card) need its own
   internal scroll region under the locked layout, or does it fit naturally within the grid row's
   height on typical small-laptop screens?**
   - What we know: `VariationTree` (right column) already has internal scroll built in; the Human
     column's content (`flawChessCard`, `MaiaHumanPanel`) was not read in full this session — its
     content height at a 420px board-floor scenario is unverified.
   - What's unclear: whether this column could overflow the grid row's bounded height on a very short
     screen, independent of the D-09 board/chart overflow the phase already addresses.
   - Recommendation: the planner should read `MaiaHumanPanel.tsx` and the FlawChess card component
     during planning (not deferred to execution) and decide whether it also needs
     `min-h-0 overflow-y-auto` treatment, or whether its content is short enough to be a non-issue.

2. **Exact custom breakpoint token name and both threshold pixel values** — explicitly left as
   "Claude's Discretion" in `161-CONTEXT.md`; this research does not recommend specific numbers beyond
   the CONTEXT.md-stated targets (~1200px width, ~560px height). The planner should pick concrete
   values (e.g. via the seed's own math: `360 + 420 + 50 + 360 = 1190`, rounding up slightly for
   safety margin) and name the tokens descriptively (e.g. `desk3col`, `short`).

## Environment Availability

Skipped — this phase has no external tool/service/runtime dependencies beyond the existing frontend
toolchain (Vite, Vitest, Tailwind, already installed and in daily use for this repo).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest ^4.1.7 + @testing-library/react ^16.3.2 [VERIFIED: frontend/package.json] |
| Config file | `frontend/vite.config.ts` (no separate `vitest.config.*` found) |
| Quick run command | `cd frontend && npx vitest run src/pages/__tests__/Analysis.test.tsx` |
| Full suite command | `cd frontend && npm test -- --run` |

### Critical constraint: jsdom cannot exercise this phase's core behavior
`Analysis.test.tsx` (confirmed this session, lines 150-170) stubs both `window.matchMedia` (always
`matches: false`) and `ResizeObserver` (`observe()`/`disconnect()` are no-ops — the callback is never
invoked). jsdom also does not perform real CSS layout, so `clientWidth`/`clientHeight` are always `0`
unless a test manually mocks them. This means:
- **No Vitest/RTL test can verify actual responsive breakpoint switching, the `100dvh` lock, or the
  board's height-aware sizing** — these require a real browser layout engine.
- Automated tests in this phase are necessarily limited to **structural assertions**: correct
  Tailwind classes present on the right elements, `AnalysisTagsPanel` rendering in the right-column
  JSX position (not the middle column), and that existing non-layout behavior (engine card, move
  list, tags panel content) is unaffected by the JSX reorder.
- **Real responsive behavior verification is HUMAN-UAT / manual-browser-only** for this phase — there
  is no Playwright/Cypress/e2e framework in this repo (confirmed absent from `package.json`). The
  existing repo convention for this class of check is the Chrome DevTools/Claude-in-Chrome live
  resize test the SEED-088 explore session itself used (documented in `SEED-088.md`'s "verified live
  via Chrome" section) — the planner should specify concrete viewport sizes to check manually: 1280×800
  and 1366×768 (small-laptop cases from the bug report), a short window (~560-600px tall) to exercise
  D-09's fallback, and a tall window (~900px+) to confirm the board still caps at 600px (D-08).

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SEED-088 | `AnalysisTagsPanel` renders after `boardControls()` in the right column, not in the middle column | unit/structural (RTL query order) | `npx vitest run src/pages/__tests__/Analysis.test.tsx` | ✅ existing file, extend with a new assertion |
| SEED-088 | Grid/flex classes present at the new breakpoint token on the 3 column divs | unit/structural (className assertion) | `npx vitest run src/pages/__tests__/Analysis.test.tsx` | ✅ existing file |
| SEED-088 | Board sizes within `[420, 600]` px given a mocked height/width | unit (mock `clientWidth`/`clientHeight` + fire `ResizeObserver` callback manually, since the test stub currently no-ops it) | new test in a `ChessBoard.test.tsx` (none exists today) | ❌ Wave 0 — no `ChessBoard.test.tsx` file exists; the stub `ResizeObserverStub` in `Analysis.test.tsx` also needs a variant that actually *invokes* its callback for this assertion to be meaningful |
| SEED-088 | `100dvh` lock, real breakpoint switching, short-screen fallback | manual/HUMAN-UAT only | — (no automated path; see constraint above) | N/A |

### Sampling Rate
- **Per task commit:** `cd frontend && npx vitest run src/pages/__tests__/Analysis.test.tsx` (fast,
  targeted)
- **Per wave merge:** `cd frontend && npm run lint && npm test -- --run` (full frontend suite, per
  CLAUDE.md pre-merge gate)
- **Phase gate:** full frontend suite green + a manual multi-viewport-size UAT pass (see above) before
  `/gsd-verify-work`

### Wave 0 Gaps
- [ ] A `ResizeObserverStub` variant that actually invokes its callback (the current stub in
  `Analysis.test.tsx:164-170` is a pure no-op) — needed if any unit test wants to assert board-size
  behavior in response to a simulated resize.
- [ ] Optionally, a new `frontend/src/components/board/__tests__/ChessBoard.test.tsx` if the planner
  wants isolated unit coverage of the `clamp(420, min(w,h), 600)` sizing logic separate from the full
  `Analysis.tsx` integration test (recommended — this is the one piece of genuinely new *logic* in the
  phase, versus everything else being CSS/JSX structural changes).
- [ ] No test-framework install needed — Vitest/RTL already fully configured.

## Security Domain

No `security_enforcement` key is set in `.planning/config.json` (absent = enabled per policy), so
this section is included for completeness, though this phase has no meaningful security surface.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | No | Phase touches only already-authenticated page layout; no auth logic changed |
| V3 Session Management | No | No session/token handling in scope |
| V4 Access Control | No | No route/permission changes |
| V5 Input Validation | No | No new user input surfaces introduced (pure layout/CSS) |
| V6 Cryptography | No | Not applicable |

### Known Threat Patterns for this stack
None applicable — this is a CSS/layout-only refactor of an existing authenticated page with no new
data flows, no new endpoints, and no changes to how user input is processed or rendered. The only
component whose rendering position changes (`AnalysisTagsPanel`) is not modified internally, so its
existing (pre-audited) behavior is unaffected.

## Sources

### Primary (HIGH confidence)
- `frontend/src/components/board/ChessBoard.tsx` (full file read this session) — board sizing,
  `ResizeObserver` pattern, `ArrowOverlay` numeric-width dependency, react-chessboard v5 `boardStyle`
  consumption
- `frontend/src/App.tsx:101-273,460-519` (read this session) — `NavHeader`, `AnalysisMobileHeader`,
  the `isAnalysisRoute` shell, current `100dvh`/`sm:` escape
- `frontend/src/pages/Analysis.tsx` (multiple targeted reads this session: 108-151, 1400-1660,
  1970-2135) — `useIsMobile()`/`MOBILE_BREAKPOINT_PX`, board row, header/footer rows, eval bar slots,
  the desktop 3-column JSX, `tagsPanel`/`boardControls`/`variationTree` factories
- `frontend/src/components/analysis/VariationTree.tsx` (grep-verified this session, lines
  54-66,166-171,683,762,810,842,878-939) — existing internal scroll/min-h-0 pattern
- `frontend/src/components/analysis/EvalBar.tsx:95-136` (read this session) — no explicit height
  class, confirms stretch-based height matching with the board
- `frontend/src/components/board/PlayerBar.tsx` (full file read this session) — no fixed height,
  `text-sm` single-line row
- `frontend/src/index.css` (full file read this session) — no existing custom `@theme` breakpoints
  or `@custom-variant` declarations; confirms this phase introduces the first one; the mobile
  `text-sm` font-size override at lines 313-317 (relevant to why height-budget `calc()` would be
  fragile)
- `frontend/package.json` (grep-verified) — `tailwindcss: ^4.3.0`, `react-chessboard: ^5.10.0`,
  `vitest: ^4.1.7`, no Playwright/Cypress/Puppeteer present
- `frontend/src/pages/__tests__/Analysis.test.tsx:140-178` (read this session) — `matchMedia` and
  `ResizeObserver` jsdom stubs, confirming the Validation Architecture constraint

### Secondary (MEDIUM confidence)
- [Theme variables - Tailwind CSS docs](https://tailwindcss.com/docs/theme) — `--breakpoint-*` custom
  breakpoint mechanism
- [Responsive design - Tailwind CSS docs](https://tailwindcss.com/docs/responsive-design) — arbitrary
  `min-[value]:`/`max-[value]:` breakpoint variants
- [Adding custom styles - Tailwind CSS docs](https://tailwindcss.com/docs/adding-custom-styles) —
  `@custom-variant` directive for arbitrary media-feature variants (e.g. `min-height`)
- WebSearch cross-check on GitHub Tailwind Labs discussions (#15113, #15744, #15721) confirming the
  `@custom-variant`/arbitrary-variant syntax for non-width media features, consistent with the docs
  above

## Metadata

**Confidence breakdown:**
- Standard stack / architecture: HIGH — every recommendation is grounded in code actually read this
  session (file:line citations throughout), not inferred from CONTEXT.md's summaries
- Height-aware board mechanism (Pattern 1): HIGH — the "pure CSS won't work" conclusion follows
  directly from `ArrowOverlay`'s numeric SVG arithmetic, a hard constraint, not a judgment call
- Tailwind v4 custom-breakpoint/custom-variant syntax (Patterns 3/4): MEDIUM — confirmed via
  WebSearch against official docs, not Context7-verified against the exact `^4.3.0` pin; flagged in
  Assumptions Log (A3/A4) as needing a quick doc-check during planning if the exact directive syntax
  doesn't compile as written
- Pitfalls: HIGH — all four pitfalls trace to specific code read this session (mount-at-zero-size
  comment, the two-breakpoint-mechanism split, the spacer alignment trick, the eval-bar flex-row
  nesting)

**Research date:** 2026-07-09
**Valid until:** 30 days (stable frontend stack, no fast-moving external dependency)
