---
phase: quick-260429-gmj
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/board/MiniBoard.tsx
  - frontend/src/components/board/LazyMiniBoard.tsx
  - frontend/src/components/insights/OpeningFindingCard.tsx
  - frontend/src/components/insights/OpeningFindingCard.test.tsx
  - frontend/src/lib/sanToSquares.ts
  - frontend/src/lib/sanToSquares.test.ts
autonomous: true
requirements: []
must_haves:
  truths:
    - "Each Insights finding card mini-board renders a fine arrow from the candidate move's from-square to its to-square"
    - "The arrow color matches the card's score-derived border color (DARK_RED / LIGHT_RED / DARK_GREEN / LIGHT_GREEN)"
    - "The arrow is visually thinner than the main MoveExplorer board arrows (fine, not heavy)"
    - "No color hex strings are introduced inline in components — colors come from arrowColor.ts/theme.ts only"
    - "Mobile and desktop card layouts both render the arrow (no parity gap)"
    - "Arrow rendering does not break for unreliable findings (n_games < 10 or confidence === 'low'); it inherits the same UNRELIABLE_OPACITY fade as the rest of the card"
  artifacts:
    - path: "frontend/src/lib/sanToSquares.ts"
      provides: "Pure helper: (fen, san) -> { from, to } | null using chess.js"
    - path: "frontend/src/components/board/MiniBoard.tsx"
      provides: "Optional arrows prop with absolutely-positioned SVG overlay"
  key_links:
    - from: "OpeningFindingCard.tsx"
      to: "sanToSquares.ts"
      via: "sanToSquares(finding.entry_fen, finding.candidate_move_san)"
      pattern: "sanToSquares\\("
    - from: "OpeningFindingCard.tsx"
      to: "MiniBoard arrows prop"
      via: "LazyMiniBoard arrows={[{ from, to, color: borderLeftColor }]}"
      pattern: "arrows=\\{"
---

<objective>
Draw a fine, score-colored arrow on each Insights finding card's mini chessboard, from the "from" square to the "to" square of the candidate (after-) move.

Purpose: Make findings instantly readable at a glance — the user sees both the position AND which move scored well/poorly, without having to read the SAN text or click through to the Move Explorer.

Output: Updated MiniBoard with optional arrow overlay; OpeningFindingCard wires score-colored arrows for each finding; unit tests cover SAN→squares conversion and arrow rendering.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@./CLAUDE.md
@frontend/src/components/insights/OpeningFindingCard.tsx
@frontend/src/components/insights/OpeningFindingCard.test.tsx
@frontend/src/components/board/MiniBoard.tsx
@frontend/src/components/board/LazyMiniBoard.tsx
@frontend/src/components/board/ChessBoard.tsx
@frontend/src/lib/arrowColor.ts
@frontend/src/lib/openingInsights.ts
@frontend/src/types/insights.ts
@frontend/src/lib/theme.ts

<interfaces>
<!-- Existing primitives the executor must reuse — do NOT reinvent these. -->

From frontend/src/lib/arrowColor.ts:
```typescript
export const DARK_RED   = '#9B1C1C';
export const LIGHT_RED  = '#E07070';
export const DARK_GREEN = '#1E6B1E';
export const LIGHT_GREEN = '#6BBF59';
export const GREY       = '#B0B0B0';
```

From frontend/src/lib/openingInsights.ts:
```typescript
// Already used by OpeningFindingCard — returns the same hex the arrow should adopt.
export function getSeverityBorderColor(
  classification: OpeningInsightFinding['classification'],
  severity:       OpeningInsightFinding['severity'],
): string;
```

From frontend/src/types/insights.ts (OpeningInsightFinding fields used):
```typescript
entry_fen:           string;   // position BEFORE candidate move
candidate_move_san:  string;   // SAN like "Be2", "Nxd4", "O-O"
classification, severity, color, ...
```

From chess.js (already a dep, used in useChessGame.ts and zobrist.ts):
```typescript
import { Chess } from 'chess.js';
const chess = new Chess(fen);
const move  = chess.move(san);   // throws on illegal; returns { from, to, ... }
// move.from / move.to are square strings like "e2" / "e4"
```

From frontend/src/components/board/ChessBoard.tsx (reference only — its ArrowOverlay
draws an SVG of normalized width 0..1 mapped to MIN_SHAFT_WIDTH..MAX_SHAFT_WIDTH;
the MiniBoard variant should use a fixed thin shaft width, not the normalized scale).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: SAN→squares helper + MiniBoard arrow overlay</name>
  <files>
    frontend/src/lib/sanToSquares.ts,
    frontend/src/lib/sanToSquares.test.ts,
    frontend/src/components/board/MiniBoard.tsx,
    frontend/src/components/board/LazyMiniBoard.tsx
  </files>
  <behavior>
    sanToSquares (frontend/src/lib/sanToSquares.test.ts):
    - Test 1: returns { from: 'e2', to: 'e4' } for ('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1', 'e4')
    - Test 2: returns { from: 'b1', to: 'c3' } for ('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1', 'Nc3')
    - Test 3: handles castling — 'O-O' on a kingside-castle-legal FEN returns { from: 'e1', to: 'g1' } for white (or e8/g8 for black FEN)
    - Test 4: returns null on illegal/unparseable SAN (e.g. 'xx99' or a move illegal in the given FEN)
    - Test 5: does NOT mutate or throw the caller — illegal SAN never produces an unhandled exception (chess.js v1.x throws on .move; helper must catch)

    MiniBoard arrows (smoke-tested via OpeningFindingCard tests in Task 2 — no separate MiniBoard test file added unless the executor finds it valuable):
    - When `arrows` prop is undefined or empty: renders identically to today (no overlay element).
    - When `arrows={[{ from: 'e2', to: 'e4', color: '#9B1C1C' }]}`: renders an absolutely-positioned SVG overlay sibling to the Chessboard with one <path> whose `fill` equals the supplied color.
    - Arrows respect the `flipped` prop (re-uses the same coord-flip math as ChessBoard.tsx).
    - Shaft width is FIXED and visually fine (recommend: shaft = 0.07 * sqSize, head = 0.22 * sqSize, head length = head * 0.7) — distinct from ChessBoard's normalized 0..1 scale. Extract these as named constants at top of file (no magic numbers).
  </behavior>
  <action>
    Create `frontend/src/lib/sanToSquares.ts`:
    - Export `interface MoveSquares { from: string; to: string }`.
    - Export `function sanToSquares(fen: string, san: string): MoveSquares | null` that constructs a `new Chess(fen)`, calls `.move(san)` inside try/catch, and returns `{ from: result.from, to: result.to }` on success or `null` on failure (illegal SAN, malformed FEN, etc.). chess.js v1.x throws on illegal moves — the helper must swallow and return null so the card can fall back to no arrow.
    - Add JSDoc explaining: "FEN is the position BEFORE the move (= finding.entry_fen); san is the candidate move SAN."

    Create `frontend/src/lib/sanToSquares.test.ts` (vitest, jsdom not required — pure logic) covering the 5 cases listed in <behavior>.

    Modify `frontend/src/components/board/MiniBoard.tsx`:
    - Add new optional prop `arrows?: ReadonlyArray<{ from: string; to: string; color: string }>` to MiniBoardProps.
    - When `arrows` is non-empty, render an absolutely-positioned `<svg>` sibling layered over the Chessboard. The wrapper div must become `position: relative` and explicitly sized (it already is via `style={{ width: size, height: size }}`).
    - Implement a small internal `MiniArrowOverlay` that mirrors ChessBoard.tsx's `squareToCoords` + `buildArrowPath` math but with FIXED FINE proportions:
      `const MINI_SHAFT_WIDTH = 0.07; const MINI_HEAD_WIDTH = 0.22; const MINI_HEAD_LENGTH_RATIO = 0.7; const MINI_ARROW_OPACITY = 0.85; const MINI_TIP_OVERSHOOT = 0.10;`
      (extract constants at module top — no magic numbers per CLAUDE.md "No magic numbers").
    - SVG must include `pointerEvents: 'none'` (the parent already has `pointer-events-none`, but be explicit on the overlay too).
    - Skip degenerate same-square arrows (defensive: `if (a.from === a.to) return null` inside the map, matching ChessBoard.tsx).
    - Pass `arrows` straight through; do not sort/filter (mini cards always pass exactly one arrow).
    - The `<svg>` element gets `data-testid="mini-board-arrow-overlay"` so OpeningFindingCard tests can assert presence/absence.
    - Keep the existing `useMemo` on `options` for Chessboard untouched — only the new SVG should depend on `arrows`/`flipped`/`size`.

    Modify `frontend/src/components/board/LazyMiniBoard.tsx`:
    - Add same optional `arrows` prop and forward it into `<MiniBoard>`.
    - No other changes.

    Reuse, don't reimplement: copy/move the `squareToCoords` + `buildArrowPath` helpers from ChessBoard.tsx into a new shared module `frontend/src/components/board/arrowGeometry.ts` and import from BOTH files. This avoids duplicated SVG path math and is the cleanest factoring per CLAUDE.md "Shared Query Filters" precedent (single implementation rule).

    Note on knip: the new `arrowGeometry.ts` exports must be imported by both MiniBoard.tsx AND ChessBoard.tsx, otherwise knip will flag dead exports and CI will fail.
  </action>
  <verify>
    <automated>cd frontend &amp;&amp; npx vitest run src/lib/sanToSquares.test.ts</automated>
  </verify>
  <done>
    - sanToSquares.test.ts passes all 5 cases.
    - MiniBoard accepts arrows prop without breaking existing call sites (LazyMiniBoard call sites in GameCard, PositionBookmarkCard, etc. continue to work without passing arrows).
    - arrowGeometry.ts exists and is imported by both MiniBoard.tsx and ChessBoard.tsx (verified via `grep -l "from.*arrowGeometry" frontend/src/components/board/`).
    - No new color hex strings in MiniBoard.tsx — all colors come via the arrows prop.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Wire score-colored arrow into OpeningFindingCard + tests + type/lint verification</name>
  <files>
    frontend/src/components/insights/OpeningFindingCard.tsx,
    frontend/src/components/insights/OpeningFindingCard.test.tsx
  </files>
  <behavior>
    OpeningFindingCard.test.tsx adds these cases (the existing react-chessboard mock + IntersectionObserver stub already cover MiniBoard rendering):
    - Test A (mobile + desktop both): renders an `<svg data-testid="mini-board-arrow-overlay">` element inside the card when candidate_move_san is parseable from entry_fen. (Use `getAllByTestId` since both layouts mount.)
    - Test B: the rendered <path> child of the overlay has `fill` equal to `getSeverityBorderColor(classification, severity)` — concretely:
        * weakness/major → DARK_RED
        * weakness/minor → LIGHT_RED
        * strength/major → DARK_GREEN
        * strength/minor → LIGHT_GREEN
      Loop over all 4 (classification, severity) combos.
    - Test C: when `candidate_move_san` is illegal in `entry_fen` (e.g. set candidate_move_san = 'Zz9' on a normal FEN), the card still renders without throwing and the arrow overlay is NOT present (`queryAllByTestId('mini-board-arrow-overlay').length === 0`).
    - Test D: arrow renders for both color sides — when finding.color === 'black' the board is flipped; the overlay still mounts. (Don't assert exact path coordinates — too brittle. Just assert the overlay element exists.)
  </behavior>
  <action>
    Modify `frontend/src/components/insights/OpeningFindingCard.tsx`:
    - Import `sanToSquares` from `@/lib/sanToSquares`.
    - At the top of the component (after `borderLeftColor` is computed, before `headerLine`):
      ```ts
      const moveSquares = sanToSquares(finding.entry_fen, finding.candidate_move_san);
      const arrows = moveSquares
        ? [{ from: moveSquares.from, to: moveSquares.to, color: borderLeftColor }] as const
        : undefined;
      ```
    - Pass `arrows={arrows}` to BOTH `<LazyMiniBoard ... />` instances (mobile branch at the `sm:hidden` block AND desktop branch at the `hidden sm:flex` block) — per CLAUDE.md "Always apply changes to mobile too".
    - No other markup changes — the troll watermark, layout, prose, links, opacity logic are untouched.

    Modify `frontend/src/components/insights/OpeningFindingCard.test.tsx`:
    - The existing `vi.mock('react-chessboard', ...)` stub returns null, which means MiniBoard's `<Chessboard>` does not render real DOM — but the MiniBoard's own SVG arrow overlay sibling DOES render (it's a plain React element, not part of Chessboard). Confirm this by inspection; no test plumbing change needed.
    - Note re LazyMiniBoard: it gates rendering on IntersectionObserver firing. The existing MockIntersectionObserver stubs `observe`/`disconnect`/`unobserve` but never fires the callback, meaning `visible` stays `false` and MiniBoard never mounts. There are two viable fixes — pick whichever is cleaner:
        Option (a) — preferred: replace the stub with one whose `observe` immediately invokes the callback with `[{ isIntersecting: true }]`, e.g.:
          ```ts
          class MockIntersectionObserver {
            constructor(private cb: IntersectionObserverCallback) {}
            observe = (el: Element) => {
              this.cb([{ isIntersecting: true, target: el } as IntersectionObserverEntry], this as unknown as IntersectionObserver);
            };
            disconnect = vi.fn();
            unobserve = vi.fn();
          }
          ```
        Option (b): mock `@/components/board/LazyMiniBoard` to a passthrough that renders MiniBoard directly.
      Option (a) is preferred because it exercises real component code paths.
    - Add the four test cases A/B/C/D from <behavior>. Reuse `makeFinding()`. Keep tests in a new `describe('Quick task 260429-gmj — score-colored after-move arrow', () => { ... })` block at the bottom of the file.
    - For Test B, use the same `hexToRgb` helper already defined at the bottom of the test file. Note: SVG `fill` attribute may or may not be normalized to rgb() in jsdom — check both forms (`fill === DARK_RED || fill === hexToRgb(DARK_RED)`) to be robust, OR query the rendered SVG path's `getAttribute('fill')` which preserves the literal hex.

    Verification commands run as part of <verify> below:
    - `cd frontend && npx tsc --noEmit` (zero errors required)
    - `cd frontend && npm run lint` (zero errors required)
    - `cd frontend && npx vitest run src/components/insights/OpeningFindingCard.test.tsx src/lib/sanToSquares.test.ts` (all green)
    - `cd frontend && npm run knip` (no new dead exports — arrowGeometry.ts must be imported by both consumers)
  </action>
  <verify>
    <automated>cd frontend &amp;&amp; npx tsc --noEmit &amp;&amp; npm run lint &amp;&amp; npx vitest run src/components/insights/OpeningFindingCard.test.tsx src/lib/sanToSquares.test.ts &amp;&amp; npm run knip</automated>
  </verify>
  <done>
    - OpeningFindingCard renders the score-colored arrow on its mini board for both mobile and desktop branches.
    - All 4 (classification, severity) combos produce the matching DARK_RED/LIGHT_RED/DARK_GREEN/LIGHT_GREEN arrow color.
    - Illegal/unparseable SAN gracefully degrades to no arrow (no crash).
    - tsc, lint, vitest (existing + new tests), and knip all pass with zero errors.
    - No new color hex literals or magic-number coordinates introduced in OpeningFindingCard.tsx.
  </done>
</task>

</tasks>

<verification>
- Visual sanity check (manual, post-merge): on /openings, scroll the Insights findings; each card's mini board shows a fine arrow from the candidate move's source to target square, colored to match the card's left border.
- Automated gates (CI parity): tsc, lint, vitest, knip all green from Task 2's verify step.
- Mobile parity: Test A in OpeningFindingCard.test.tsx asserts the overlay renders in BOTH the `sm:hidden` and `hidden sm:flex` branches (use `getAllByTestId`).
</verification>

<success_criteria>
- Each Insights finding card mini board renders a fine arrow from the candidate move's from-square to its to-square.
- Arrow color exactly equals `getSeverityBorderColor(classification, severity)` — same source as the card's left-border tint.
- Arrow is visibly thinner than MoveExplorer board arrows (fixed shaft = 0.07 of square size vs. MoveExplorer's normalized 0.06–0.26 scale, typically rendered in the upper half of that range).
- chess.js illegal-move exceptions never propagate to the React render path.
- No new color hex strings or magic numbers introduced — all colors via arrowColor.ts re-export, all geometry constants named at module top.
- Mobile and desktop branches both updated.
- `cd frontend && npx tsc --noEmit && npm run lint && npx vitest run && npm run knip` is green.
</success_criteria>

<output>
After completion, no SUMMARY required (this is a /gsd:quick task). The user will commit and ship directly per CLAUDE.md "When working on the main branch (e.g. with /gsd:quick), don't commit the changes unless the user explicitly asks for it."
</output>
