# Phase 161: Analysis page viewport-locked responsive layout - Pattern Map

**Mapped:** 2026-07-09
**Files analyzed:** 4 (all modified, no new files)
**Analogs found:** 4 / 4 (self-analogs — this phase extends existing patterns in the same files rather than copying from a different subsystem)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `frontend/src/pages/Analysis.tsx` (desktop 3-column block, lines 1982-2134) | component (page, layout) | request-response (renders from query state) | `Analysis.tsx`'s own mobile-tree above (lines ~1780-1980, already `100dvh`/`min-h-0`/`flex-1` locked) + `VariationTree.tsx` internal scroll region | exact — same file, same page, mobile branch already implements the target pattern |
| `frontend/src/components/board/ChessBoard.tsx` (lines 251-277, 337-340) | component (sizing/measurement) | event-driven (ResizeObserver callback → state → re-render) | itself — extend the existing width-only `updateWidth`/`ResizeObserver` effect | exact — same function, add a second observed target |
| `frontend/src/App.tsx` (lines 484-500, `isAnalysisRoute` shell) | provider/shell (layout container) | request-response (route-level layout) | itself — the shell already has a working `100dvh`-locked base state (today gated to `<640px` via `sm:h-auto sm:block`) | exact — polarity inversion of the same block, not a new pattern |
| `frontend/src/index.css` (Tailwind v4 CSS-first config) | config | n/a (declarative CSS config) | `@custom-variant dark (&:is(.dark *));` at line 7 (existing `@custom-variant` precedent) + `@theme inline { ... }` at line 94 (existing `@theme` block to extend, though no `--breakpoint-*` token exists yet) | role-match — precedent for the *mechanism* (`@custom-variant`), no prior `--breakpoint-*` token to copy verbatim |

## Pattern Assignments

### `frontend/src/pages/Analysis.tsx` (component, request-response layout)

**Analog:** the file's own mobile/tab-takeover branch (renders when `isMobile === true`, roughly lines 1780-1980) already achieves the "viewport-locked frame + internally-scrolling middle" contract this phase adds to the desktop branch. Also `VariationTree.tsx` for the scrolling-child pattern.

**Current desktop grid-row anchor (lines 1982-1985)** — copy the container wiring, remap breakpoint token, convert `flex-row` → `grid`:
```tsx
// Analysis.tsx:1982-1985 (current)
return (
  <div data-testid="analysis-page" className="flex min-h-0 flex-1 flex-col bg-background">
    <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-2 pb-20 md:py-6 md:pb-6 md:px-6">
      <div className="flex flex-col lg:flex-row lg:items-stretch gap-4">
```
Target shape (per RESEARCH.md Pattern 2/3): `max-w-7xl` removed/widened at the `<main>`; add `<newbp>:min-h-0 <newbp>:flex <newbp>:flex-col <newbp>:h-full` to `<main>`; grid row becomes `flex flex-col <newbp>:grid <newbp>:grid-cols-[360px_1fr_360px] <newbp>:min-h-0 <newbp>:h-full gap-4` (replacing `lg:flex-row lg:items-stretch`).

**Column-top alignment spacer (copy verbatim, do not alter) — lines 1999-2003 and 2063-2067:**
```tsx
{isGameMode && gameData && (
  <div aria-hidden="true" className="hidden lg:block lg:invisible lg:-mb-2">
    {playerBar(boardFlipped ? 'white' : 'black')}
  </div>
)}
```
Both occurrences remap `lg:` → the new breakpoint token but must otherwise stay byte-identical — per RESEARCH.md Pitfall 3, this trick depends on each column staying an independent `flex flex-col` item (1-D grid only), not on row-based grid track sizing.

**Board column (line 2025) → fluid grid cell:**
```tsx
// current: <div className="flex flex-col gap-2 w-full lg:w-[628px] shrink-0">
```
becomes the middle `1fr` grid track — drop the fixed `lg:w-[628px]`, add `<newbp>:min-h-0 <newbp>:h-full` (this is the D-09 scroll target once the board hits its 420px floor).

**Right column (line 2056) → fixed 360px grid cell, tags relocation (D-04):**
```tsx
// current: <div className="flex w-full lg:w-[360px] shrink-0 flex-col gap-4 min-w-0">
  ...
  {variationTree('responsive')}          // line 2124
  {boardControls()}                       // line 2127
</div>                                    // line 2128
```
Append `{tagsPanel(true)}` immediately after `{boardControls()}` (after line 2127, before the closing `</div>` at 2128) — remove it from its current home in the board column at line 2050. Keep `withHighlight=true` (the `true` argument) unchanged so the eval-chart hover wiring is preserved. Add `<newbp>:min-h-0 <newbp>:h-full` to this column div so `VariationTree`'s own internal scroll (already `min-h-0 flex-1 overflow-y-auto`) actually has a bounded ancestor to constrain against.

**Eval bar row — leave untouched (Pitfall 4):** `boardRow`'s internal `flex flex-row items-stretch gap-2` (around line 1447-1497) and `evalBarSlot`'s `w-5 shrink-0` (line ~1529) are nested *inside* the middle grid column's own flex-row; the D-03 grid conversion applies only at the outer row (line 1985), not here.

**Board's `maxWidth` prop (line ~1481, referenced in CONTEXT D-02):** change the hard `maxWidth={600}` pass-through to still pass `600` as the ceiling constant (`BOARD_MAX_WIDTH`), but the component itself now also needs a `heightRef`/height-bounding prop — see ChessBoard.tsx assignment below.

---

### `frontend/src/components/board/ChessBoard.tsx` (component, event-driven sizing)

**Analog:** itself — the existing width-only measurement effect (lines 262-277) is the pattern to extend, not replace.

**Current pattern (lines 251-277, read in full this session):**
```tsx
export function ChessBoard({ position, onPieceDrop, flipped = false, lastMove, lastMoveColor, arrows = [], squareMarkers = [], id, maxWidth = 400 }: ChessBoardProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  // Start at 0 so we don't mount react-chessboard until the container has measured.
  // Mounting with a non-zero width inside a display:none parent ... causes react-chessboard's
  // passive effect to throw "Square width not found" when it measures squares at 0.
  const [boardWidth, setBoardWidth] = useState(0);
  ...
  useEffect(() => {
    const updateWidth = () => {
      if (containerRef.current) {
        const containerWidth = containerRef.current.clientWidth;
        // On mobile, use full container width; on desktop cap at maxWidth (400 default).
        setBoardWidth(Math.min(containerWidth, maxWidth));
      }
    };
    updateWidth();
    const observer = new ResizeObserver(updateWidth);
    if (containerRef.current) {
      observer.observe(containerRef.current);
    }
    return () => observer.disconnect();
  }, [maxWidth]);
```

**Extension target (per RESEARCH.md Pattern 1, D-02/D-08):** add a second optional ref (e.g. `heightRef`) observed by the *same* `ResizeObserver` instance (do not create a second observer — "one code path, one set of edge cases" per RESEARCH's Don't-Hand-Roll table), and clamp with named constants instead of the bare `600`:
```tsx
const BOARD_MIN_WIDTH = 420; // D-08 floor
const BOARD_MAX_WIDTH = 600; // D-08 ceiling — board never grows past today's size
// ...
const heightBudget = heightRef?.current?.clientHeight ?? Infinity;
const next = Math.min(containerWidth, maxWidth, heightBudget);
setBoardWidth(Math.max(BOARD_MIN_WIDTH, Math.min(next, BOARD_MAX_WIDTH)));
```

**Guard to preserve verbatim (line 253-257's mount-at-zero comment, and the `boardWidth > 0` render gate at ~line 407):** treat `heightBudget` the same as `containerWidth` — both must be `> 0` before rendering `<Chessboard>`. Do not add a second, height-specific guard (RESEARCH.md Pitfall 1).

**Numeric-only constraint (lines 337-340) — why CSS `clamp()` alone cannot work, cite when justifying the JS-measurement approach in the plan:**
```tsx
const boardStyle = useMemo<React.CSSProperties>(
  () => ({ width: boardWidth, height: boardWidth, borderRadius: '0.5rem' }),
  [boardWidth],
);
```
`ArrowOverlay` also does `sqSize = boardWidth / 8` arithmetic and sets SVG `width`/`height` attributes directly from the numeric state (lines ~147, 163-164) — this is a hard constraint against a CSS-only sizing approach.

---

### `frontend/src/App.tsx` (shell/provider, request-response layout)

**Analog:** itself — the `isAnalysisRoute` branch already has a correct `100dvh`/`min-h-0` chain, just gated the wrong direction relative to this phase's needs.

**Current pattern (lines 484-500, read in full this session):**
```tsx
if (isAnalysisRoute) {
  return (
    <>
      {/* Full-height flex chain on mobile so the page's tab content can fill the
          space between the board and the in-flow board-controls footer. `sm:h-auto
          sm:block` reverts to normal block flow on desktop (layout unchanged). */}
      <div className="flex flex-col h-[100dvh] sm:h-auto sm:block">
        <NavHeader />
        <AnalysisMobileHeader />
        <main className="flex-1 min-h-0 flex flex-col sm:block sm:flex-none">
          <Outlet />
        </main>
      </div>
      <InstallPromptBanner />
      <FeedbackButton />
    </>
  );
}
```

**Required inversion (RESEARCH.md Pattern 2, D-01/D-09 — the single highest-risk mechanical mistake per the research's Anti-Patterns section):** do NOT literal-rename `sm:` → the new breakpoint token; the base/unprefixed classes must become the **unlocked** state (today's post-`sm:` behavior) and the new breakpoint variant must **add** the lock:
```tsx
// Target polarity (illustrative, planner finalizes exact token name/value):
<div className="h-auto block <newbp>:flex <newbp>:flex-col <newbp>:h-[100dvh]">
  <NavHeader />
  <AnalysisMobileHeader />
  <main className="block flex-none <newbp>:flex-1 <newbp>:min-h-0 <newbp>:flex <newbp>:flex-col">
    <Outlet />
  </main>
</div>
```
The D-09 short-screen fallback (`short:` custom variant, ~560px max-height) only needs to be applied at this shell level (`h-[100dvh]` release) — not repeated down the `min-h-0` chain, per RESEARCH.md's Pattern 4 "Interaction with the min-h-0 chain" note.

---

### `frontend/src/index.css` (config, declarative)

**Analog:** existing `@custom-variant dark (&:is(.dark *));` at line 7 — the only precedent for a custom variant in this codebase; there is no prior `--breakpoint-*` token in the `@theme inline { ... }` block starting at line 94 (confirmed — this phase introduces the first one).

**New breakpoint token (D-07), added inside `@theme` — either the existing `@theme inline { ... }` block at line 94 or a sibling plain `@theme { ... }` block (Tailwind v4 supports both; a plain `@theme` block is simpler for a bare breakpoint that doesn't reference a CSS custom property):**
```css
@theme {
  --breakpoint-desk3col: 1200px; /* exact px is Claude's discretion, target ~1200 (D-07) */
}
```
Usage: `desk3col:grid-cols-[360px_1fr_360px]` replacing all 6 `lg:` occurrences in `Analysis.tsx`'s desktop-column block (lines 1985, 1993, 2000, 2025, 2056, 2064 — grep-verified in RESEARCH.md this session). Do not touch `lg:` elsewhere in the codebase (`Openings.tsx`, `Endgames.tsx`, etc.) — out of scope.

**New height-based custom variant (D-09), following the `@custom-variant dark` precedent at line 7:**
```css
@custom-variant short (&:is(@media (max-height: 559.98px)));
```
Fallback if the named-variant syntax doesn't compile against the installed `^4.3.0` pin (RESEARCH.md Assumption A4, MEDIUM confidence): inline arbitrary form `[@media(max-height:559.98px)]:h-auto` applied directly at `App.tsx:490`.

## Shared Patterns

### `min-h-0` propagation chain (applies to `App.tsx`, `Analysis.tsx` — 7 links total)
**Source:** RESEARCH.md Architecture Pattern 2, verified against live code this session at each cited line.
**Apply to:** every flex/grid ancestor between the `100dvh`-locked shell and the two children that need to scroll internally (middle board+chart column, right column's `VariationTree`).
**Rule:** `min-h-0` is not inherited — each of the 7 links below needs it set explicitly (do not assume it "flows down" once set on the grid row):
1. `App.tsx:493` `<main>` (needs `<newbp>:min-h-0`, currently escaped by `sm:block sm:flex-none`)
2. `Analysis.tsx:1983` `analysis-page` div — ✓ already `flex min-h-0 flex-1 flex-col`
3. `Analysis.tsx:1984` inner `<main>` — missing `min-h-0` today, must add
4. `Analysis.tsx:1985` grid row div — add `min-h-0 h-full` at the new breakpoint
5. Board column (`Analysis.tsx:2025`) — add `min-h-0 h-full`
6. Right column (`Analysis.tsx:2056`) — add `min-h-0 h-full` (unblocks `VariationTree`'s own internal scroll, already present at `VariationTree.tsx:683,883,930,939`)
7. Human column (`Analysis.tsx:1993`) — same treatment; flagged as an Open Question in RESEARCH.md whether `MaiaHumanPanel`/`flawChessCard` content needs its own `overflow-y-auto` — planner should verify during implementation.

### `VariationTree.tsx` self-scrolling child (no changes needed — reference only)
**Source:** `frontend/src/components/analysis/VariationTree.tsx` lines 683, 883, 930/939 (grep-verified).
```
line 683: className="min-h-0 flex-1 overflow-y-auto thin-scrollbar"   (mobile/responsive strip)
line 883: className="absolute inset-0 overflow-y-auto thin-scrollbar" (desktop vertical list)
line 930/939: outer wrapper "flex min-h-0 flex-1 flex-col" / "sm:flex sm:flex-col"
```
**Apply to:** this is the model any *other* self-scrolling column child in this phase should mirror if the Human column (Open Question above) turns out to need one — no edits needed to `VariationTree.tsx` itself, only to its ancestor chain (item 6 above).

### Tailwind v4 CSS-first config precedent
**Source:** `frontend/src/index.css:7` (`@custom-variant dark`), `:94` (`@theme inline`).
**Apply to:** the new `--breakpoint-desk3col` token and `short` custom variant — same declarative mechanism, no JS `matchMedia` listener needed (contrast with `useIsMobile()` below, which is a different, untouched mechanism).

## No Analog Found

None — all 4 files are modified-in-place extensions of an already-established pattern in the same file. No wholly new file/component is introduced by this phase.

## Explicitly Out of Scope (do not treat as a file to pattern-match)

| Reference | Why excluded |
|-----------|--------------|
| `useIsMobile()` / `MOBILE_BREAKPOINT_PX = 640` (`Analysis.tsx:108-151`) | Separate JS `matchMedia` mechanism governing the mobile-tab-takeover JSX-tree swap, independent of this phase's CSS grid breakpoint (RESEARCH.md Pitfall 2 + CONTEXT.md explicit exclusion) |
| `lg:` usage in `Openings.tsx`, `Endgames.tsx` | Phase is `/analysis`-scoped only; do not remap `lg:` elsewhere even though the token exists globally once declared |

## Metadata

**Analog search scope:** `frontend/src/pages/Analysis.tsx`, `frontend/src/components/board/ChessBoard.tsx`, `frontend/src/App.tsx`, `frontend/src/index.css`, `frontend/src/components/analysis/VariationTree.tsx` (reference only, not modified)
**Files scanned:** 5 (all read in full or targeted-range this session; no new Grep/Glob needed — RESEARCH.md already grep-verified exact line numbers for every `lg:` occurrence and every `min-h-0`/`overflow-y-auto` site)
**Pattern extraction date:** 2026-07-09
