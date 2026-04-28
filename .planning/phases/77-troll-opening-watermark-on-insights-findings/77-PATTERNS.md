# Phase 77: Troll-opening watermark on Insights findings - Pattern Map

**Mapped:** 2026-04-28
**Files analyzed:** 8 (4 new, 4 modified)
**Analogs found:** 7 / 8 (one — `frontend/scripts/curate_troll_openings.ts` — has no in-repo analog because no TS/JS curation script exists yet; closest reference is the Python `scripts/gen_endgame_zones_ts.py`)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `frontend/src/lib/trollOpenings.ts` (NEW) | utility | transform (pure string → boolean) | `frontend/src/lib/openingInsights.ts` | exact (same role: small typed pure-function utility module imported by insights consumers) |
| `frontend/src/lib/trollOpenings.test.ts` (NEW) | test | transform | `frontend/src/lib/openingInsights.test.ts` and `frontend/src/lib/zobrist.test.ts` | exact (sibling `.test.ts` next to a pure-function lib file) |
| `frontend/src/data/trollOpenings.ts` (NEW) | static data module | static lookup (`Set<string>` literals) | `frontend/src/generated/endgameZones.ts` | role-match (codegen-emitted typed data module) |
| `frontend/scripts/curate_troll_openings.ts` (NEW) | build-time script | file-I/O + transform | `scripts/gen_endgame_zones_ts.py` | partial (different language, same role: read source → emit TS data file) |
| `frontend/src/assets/troll-face.svg` (NEW, moved from `temp/Troll-Face.svg`) | static asset | n/a | `frontend/src/assets/react.svg` | role-match (only other SVG in `assets/`; first **imported** SVG since `react.svg` is unused) |
| `frontend/src/components/insights/OpeningFindingCard.tsx` (MODIFY) | component | request-response (props → JSX) | itself (read-only, structural insertion) | exact (existing file; modify in place) |
| `frontend/src/components/insights/OpeningFindingCard.test.tsx` (MODIFY) | test | event-driven | itself (extend) | exact (existing file; extend with new `describe` block) |
| `frontend/src/components/move-explorer/MoveExplorer.tsx` (MODIFY) | component | request-response | itself (read-only, structural insertion in `MoveRow`) | exact (existing file; modify in place) |
| `frontend/src/components/move-explorer/__tests__/MoveExplorer.test.tsx` (MODIFY) | test | event-driven | itself (extend) | exact |

## Pattern Assignments

### `frontend/src/lib/trollOpenings.ts` (NEW — utility, pure-string transform)

**Analog:** `frontend/src/lib/openingInsights.ts` (76 lines; same shape: a couple of small exported pure functions, typed parameters, no side effects, imported by insights surfaces).

**Imports pattern** — copy the shape of `openingInsights.ts:1-2`:
```typescript
import { DARK_RED, LIGHT_RED, DARK_GREEN, LIGHT_GREEN } from '@/lib/arrowColor';
import type { OpeningInsightFinding } from '@/types/insights';
```
For Phase 77 this becomes:
```typescript
import type { Color } from '@/types/api';
import { WHITE_TROLL_KEYS, BLACK_TROLL_KEYS } from '@/data/trollOpenings';
```
- `Color` lives at `frontend/src/types/api.ts:39` (`export type Color = 'white' | 'black';`). Use it explicitly per CLAUDE.md "Type safety — never use bare `str` for fields with a fixed set of values".
- `@/...` path alias is the project convention (used in every consumer).

**Core pattern (small typed pure helpers)** — copy the shape of `openingInsights.ts:48-56` and `:67-75`:
```typescript
export function getSeverityBorderColor(
  classification: OpeningInsightFinding['classification'],
  severity: OpeningInsightFinding['severity'],
): string {
  if (classification === 'weakness') {
    return severity === 'major' ? DARK_RED : LIGHT_RED;
  }
  return severity === 'major' ? DARK_GREEN : LIGHT_GREEN;
}

export function formatCandidateMove(
  entrySanSequence: string[],
  candidateMoveSan: string,
): string {
  const plyIndex = entrySanSequence.length;
  const isWhitePly = plyIndex % 2 === 0;
  const moveNumber = Math.floor(plyIndex / 2) + 1;
  return isWhitePly ? `${moveNumber}.${candidateMoveSan}` : `${moveNumber}...${candidateMoveSan}`;
}
```

Phase 77 must replicate: explicit return type (`string`/`boolean`), JSDoc above the export, no `any`, no class wrapping.

**Index-access narrowing pattern** — copy from `frontend/src/lib/zobrist.ts:830-836` (the project's canonical example of `noUncheckedIndexedAccess` discipline):
```typescript
function squareToIndex(square: Square): number {
  const file = square.charCodeAt(0) - 97; // 'a' = 0, 'h' = 7
  // safe: square is always a 2-char chess square string like "e4"
  const rank = parseInt(square[1]!) - 1;   // '1' = 0, '8' = 7
  return rank * 8 + file;
}
```
Phase 77 will need the same `// safe: ...` non-null comments where it does `placement.split(' ', 1)[0]!` (always present after split) and where the rank-walker indexes `parseInt(ch, 10)` results.

**What to copy:** module style, JSDoc, explicit `Color` typing, named non-null assertions with `// safe:` comments, no default export.
**What to change:** the actual functions (`deriveUserSideKey`, `isTrollPosition`); pull the algorithm verbatim from RESEARCH.md Pattern 1.

---

### `frontend/src/lib/trollOpenings.test.ts` (NEW — vitest unit tests for the pure helpers)

**Analog:** `frontend/src/lib/openingInsights.test.ts` (golden-input → expected-output style; sibling `.test.ts` next to the implementation; 67 lines).

**Imports + describe shape** — copy verbatim from `openingInsights.test.ts:1-8`:
```typescript
import { describe, it, expect } from 'vitest';
import {
  formatCandidateMove,
  getSeverityBorderColor,
} from './openingInsights';
import * as openingInsights from './openingInsights';
import { DARK_RED, LIGHT_RED, DARK_GREEN, LIGHT_GREEN } from './arrowColor';
```
Note the relative `./` import (NOT `@/lib/...`) for tests sitting next to their target. Keep that convention.

**Golden-input table style** — copy from `openingInsights.test.ts:9-35`:
```typescript
describe('formatCandidateMove', () => {
  it('renders a white candidate after a long entry sequence with the move-number prefix only', () => {
    expect(
      formatCandidateMove(['e4', 'c5', 'Nf3', 'd6', 'd4', 'cxd4'], 'Nxd4'),
    ).toBe('4.Nxd4');
  });

  it('renders a white candidate after exactly 2 entry plys', () => {
    expect(formatCandidateMove(['e4', 'c5'], 'Nf3')).toBe('2.Nf3');
  });
  // ...
});
```
One-line `it()` with `expect(...).toBe(...)` — keep tests narrow, one assertion per test, no shared mutation.

**Set-membership testing pattern** — when the test needs to verify `isTrollPosition` returns `true` for a curated key but the curated `Set` may not include the test fixture, use `vi.mock` to stub the data module. Copy the pattern from `OpeningFindingCard.test.tsx:14-21`:
```typescript
vi.mock('react-chessboard', () => ({
  Chessboard: vi.fn(() => null),
}));

vi.mock('@/components/ui/tooltip', () => ({
  Tooltip: ({ children }: { children: React.ReactNode }) => children,
}));
```
Phase 77 equivalent:
```typescript
vi.mock('@/data/trollOpenings', () => ({
  WHITE_TROLL_KEYS: new Set(['8/8/8/8/8/8/PPPPKPPP/RNBQ1BNR']),
  BLACK_TROLL_KEYS: new Set([]),
}));
```
This isolates the unit tests from the curation pipeline (the curated data file may be empty until step 2 of execution surfaces candidates to the user).

**Test file naming convention** — sibling `<name>.test.ts` next to `<name>.ts`. Verified against `frontend/src/lib/`:
- `arrowColor.ts` + `arrowColor.test.ts`
- `impersonation.ts` + `impersonation.test.ts`
- `openingInsights.ts` + `openingInsights.test.ts`
- `pgn.ts` + `pgn.test.ts`
- `utils.ts` + `utils.test.ts`
- `zobrist.ts` + `zobrist.test.ts`

So `trollOpenings.ts` + `trollOpenings.test.ts` is exactly right (NOT `__tests__/trollOpenings.test.ts`).

---

### `frontend/src/data/trollOpenings.ts` (NEW — static `ReadonlySet<string>` data module)

**Analog:** `frontend/src/generated/endgameZones.ts` — the only existing codegen-emitted typed data module in the FE.

**Header comment pattern** — copy from `frontend/src/generated/endgameZones.ts` (top three lines, emitted by `scripts/gen_endgame_zones_ts.py:70-72`):
```typescript
// AUTO-GENERATED — do not edit by hand.
// Source: app/services/endgame_zones.py
// Regenerate with: uv run python scripts/gen_endgame_zones_ts.py
```
Phase 77 variant (note the human-pruning step is part of the regeneration recipe):
```typescript
// Curated troll-opening positions, keyed by user-side-only FEN piece-placement.
// Source: lichess.org/study/cEDAMVBB.pgn (hand-pruned to strict Bongcloud-tier per Phase 77 D-01).
// Regenerate with: npx tsx frontend/scripts/curate_troll_openings.ts
//   then hand-prune the candidate list before pasting into the Set literals below.
```

**`ReadonlySet<string>` literal exports** — no exact in-repo analog (`endgameZones.ts` exports records, not Sets). Use the shape from RESEARCH.md "Output Data Module" verbatim:
```typescript
export const WHITE_TROLL_KEYS: ReadonlySet<string> = new Set([
  // Bongcloud Attack — after 1.e4 e5 2.Ke2
  '8/8/8/8/4P3/8/PPPPKPPP/RNBQ1BNR',
  // ...entries hand-pruned during curation...
]);

export const BLACK_TROLL_KEYS: ReadonlySet<string> = new Set([
  // ...entries hand-pruned during curation...
]);
```

**What to copy:** the AUTO-GENERATED-style header, explicit `ReadonlySet<string>` annotation (so consumers can't `.add(...)`), and the convention of emitting comments above each entry that name the opening + move sequence (mirrors the inline comments style used throughout `theme.ts` lines 16-24).
**What to change:** the actual entries, populated only AFTER the human review step per D-01 / D-09.

---

### `frontend/scripts/curate_troll_openings.ts` (NEW — Node/TS curation script, run via `npx tsx`)

**Analog:** `scripts/gen_endgame_zones_ts.py` is the only build-time codegen script in the repo, but it's Python. There is NO in-repo TS/Node script analog. The directory `frontend/scripts/` does not yet exist.

**Header docstring pattern** — copy the spirit of `scripts/gen_endgame_zones_ts.py:1-17`:
```python
"""Generate frontend/src/generated/endgameZones.ts from the Python zone registry.

Python (app/services/endgame_zones.py) is the authoritative source per Phase 63
D-01. This script emits a TypeScript mirror consumed by EndgameScoreGapSection,
EndgameClockPressureSection, and EndgamePerformanceSection. CI runs
`git diff --exit-code` on the generated file to block drift.

Usage (local dev):
    uv run python scripts/gen_endgame_zones_ts.py

Usage (CI drift check):
    uv run python scripts/gen_endgame_zones_ts.py
    git diff --exit-code frontend/src/generated/endgameZones.ts
"""
```
Phase 77 TS variant (top-of-file comment block):
```typescript
/**
 * Curate troll-opening positions from Lichess study cEDAMVBB.
 *
 * Reads the multi-chapter PGN, walks each chapter via chess.js, derives the
 * user-side-only FEN key per ply, and prints a candidate list to stdout for
 * human review per Phase 77 D-01.
 *
 * Run:
 *   npx tsx frontend/scripts/curate_troll_openings.ts > /tmp/troll-candidates.txt
 *
 * After review, hand-paste the pruned keys into frontend/src/data/trollOpenings.ts.
 * The script does NOT auto-write the data file (per D-09 — human review is mandatory).
 */
```

**Algorithm + emission shape** — RESEARCH.md "Curation Script Skeleton" gives the full skeleton; copy it verbatim. Key patterns to replicate from in-repo code:

1. **chess.js usage** — copy the pattern from `frontend/src/components/move-explorer/MoveExplorer.tsx:69-71`:
   ```typescript
   const moveMap = useMemo(() => {
     const chess = new Chess(position);
     const legalMoves = chess.moves({ verbose: true });
     return new Map(legalMoves.map(m => [m.san, { from: m.from, to: m.to }]));
   }, [position]);
   ```
   For curation script: `const chess = new Chess(); chess.loadPgn(chapterText);` then iterate `chess.history({ verbose: true })`.

2. **Index-access narrowing in script** — same `// safe:` comment pattern as `zobrist.ts:830-836`. RESEARCH.md Pitfall 7 calls out the specific case: `position.split(' ')[1]` returns `string | undefined`; narrow before use.

3. **No `package.json` script entry** — RESEARCH.md anti-pattern: "Embedding the curation step as a `package.json` script". Run via `npx tsx` ad-hoc.

**What to copy:** docstring style (purpose + usage), chess.js construction pattern, narrowing discipline, JSDoc on every helper.
**What to change:** language (TS not Python), entry point (no `__main__` block; just bare `await main()` with `.catch`), output (stdout, not file write).

**Note:** Because `frontend/scripts/` does not exist, the planner should add a one-line action: `mkdir -p frontend/scripts/`. The committed script does not need a `.gitkeep` since it itself is the only file in the directory.

---

### `frontend/src/assets/troll-face.svg` (NEW — moved from `temp/Troll-Face.svg`)

**Analog:** `frontend/src/assets/react.svg` is the only other file in `frontend/src/assets/`. It is NOT imported anywhere in `frontend/src` (verified via `grep -rn "import.*\.svg"` — zero matches).

This is therefore the **first SVG asset import** in the project. There is no in-repo precedent. RESEARCH.md "Standard Stack" verifies via `frontend/vite.config.ts` that no `vite-plugin-svgr` is installed → Vite's default behavior applies: `import url from '@/assets/troll-face.svg'` returns a URL string suitable for `<img src={url} />`.

**Asset import pattern (from RESEARCH.md Pattern 3)** — to be used at the consumer site (`OpeningFindingCard.tsx`, `MoveExplorer.tsx`):
```typescript
import trollFaceUrl from '@/assets/troll-face.svg';
// ...
<img src={trollFaceUrl} alt="" aria-hidden="true" ... />
```

**File-move action shape** — single git operation in the executor:
- `git mv temp/Troll-Face.svg frontend/src/assets/troll-face.svg` (kebab-case rename per CLAUDE.md "kebab-case per repo convention" + D-11).

**What to copy:** none (no analog).
**What to change:** filename casing (PascalCase → kebab-case); location (`temp/` → `frontend/src/assets/`).

---

### `frontend/src/components/insights/OpeningFindingCard.tsx` (MODIFY — add bottom-right watermark)

**Analog:** itself. The existing card root is at `OpeningFindingCard.tsx:131-168`. Insertion point is inside that root `<div>`, after the desktop branch closes (i.e., as a sibling to both mobile and desktop branches).

**Existing `cardStyle` + outer-`<div>` pattern** (`OpeningFindingCard.tsx:49-55`, `:131-136`):
```typescript
// D-11: Apply UNRELIABLE_OPACITY when n_games < 10 OR confidence is low.
const isUnreliable =
  finding.n_games < MIN_GAMES_FOR_RELIABLE_STATS || finding.confidence === 'low';
const cardStyle: React.CSSProperties = {
  borderLeftColor,
  ...(isUnreliable ? { opacity: UNRELIABLE_OPACITY } : {}),
};

// ...

return (
  <div
    data-testid={`opening-finding-card-${idx}`}
    className="block border-l-4 charcoal-texture border border-border/20 rounded px-4 py-3"
    style={cardStyle}
  >
    {/* Mobile: header full-width on top, board + prose/links row below */}
    <div className="flex flex-col gap-2 sm:hidden">
      ...
    </div>

    {/* Desktop: board left, header + prose + links stacked right */}
    <div className="hidden sm:flex gap-3 items-center">
      ...
    </div>
  </div>
);
```

**Watermark insertion point** — inside the outer `<div>` (so it inherits the `UNRELIABLE_OPACITY` multiplication per RESEARCH.md Pitfall 4 — accepted), as a third child after the mobile and desktop branches. Must add `relative` to the outer div's className (currently absent — verified at line 134, no `relative` token).

**JSX shape to insert** (copy from RESEARCH.md Pattern 3):
```tsx
{showTroll && (
  <img
    src={trollFaceUrl}
    alt=""
    aria-hidden="true"
    data-testid={`opening-finding-card-${idx}-troll-watermark`}
    className="absolute bottom-2 right-2 h-16 w-16 sm:h-20 sm:w-20 pointer-events-none select-none"
    style={{ opacity: TROLL_WATERMARK_OPACITY }}
  />
)}
```

**`data-testid` + `aria-hidden` pattern** — copy from the existing `lucide-react` icon usage in this same file at `:111`:
```tsx
<ArrowRightLeft className="h-3.5 w-3.5" />
```
The lucide icon is rendered without `aria-label` because the surrounding `<button>` has `aria-label`. For a decorative `<img>` that is not inside an interactive element, the `alt=""` + `aria-hidden="true"` combination is the screen-reader-quieting idiom (per CLAUDE.md "ARIA labels on icon-only buttons" — applies to interactive icons; decorative ones use `alt=""`).

**Theme constant import addition** — copy the pattern from `OpeningFindingCard.tsx:9`:
```typescript
import { MIN_GAMES_FOR_RELIABLE_STATS, UNRELIABLE_OPACITY } from '@/lib/theme';
```
Phase 77 extends this line to add `TROLL_WATERMARK_OPACITY` (the new constant must be added in `theme.ts` adjacent to `UNRELIABLE_OPACITY` at lines 76-77 — the existing precedent).

**`isTrollPosition` call site** — add a new derived constant alongside `isUnreliable` (line 50-51):
```typescript
const showTroll = isTrollPosition(finding.entry_fen, finding.color);
```
Place it inline (not in `useMemo` — RESEARCH.md anti-pattern).

**What to copy:** the `relative` + `absolute` + `pointer-events-none` Tailwind idiom (no in-file precedent — first introduction); the existing `data-testid` template `opening-finding-card-${idx}-...` (lines 90, 94, 108, 120, 133); the existing theme-constant import line.
**What to change:** add `relative` to the outer card's className (line 134); add the `<img>` sibling as the last child of the outer `<div>`; add the `showTroll` derived constant near `isUnreliable`.

---

### `frontend/src/components/insights/OpeningFindingCard.test.tsx` (MODIFY — extend with watermark assertions)

**Analog:** itself; 322 lines. Has a clear "Phase 76" sub-`describe` block at line 267 to extend.

**Extension shape** — copy the structure of the existing Phase 76 sub-describe at `OpeningFindingCard.test.tsx:267-308`:
```typescript
describe('Phase 76 — Confidence indicator + mute', () => {
  it('renders Confidence: <level> line with the right data-testid', () => {
    const finding = makeFinding({ confidence: 'medium' });
    renderCard({ finding, idx: 3 });
    const lines = screen.getAllByTestId('opening-finding-card-3-confidence');
    expect(lines.length).toBeGreaterThanOrEqual(1);
    expect(lines[0]!.textContent).toMatch(/Confidence:\s*medium/);
  });
  // ...
});
```

Phase 77 adds a `describe('Phase 77 — Troll-opening watermark', () => { ... })` block.

**`vi.mock` of the data module** — same pattern as the existing tooltip mock at `:19-21`:
```typescript
vi.mock('@/components/ui/tooltip', () => ({
  Tooltip: ({ children }: { children: React.ReactNode }) => children,
}));
```
Phase 77 adds (top-of-file, before any imports of `OpeningFindingCard`):
```typescript
vi.mock('@/data/trollOpenings', () => ({
  WHITE_TROLL_KEYS: new Set([
    // matches makeFinding({ entry_fen: '...', color: 'white' }) when used in tests
    '<key derived from the test fixture FEN>',
  ]),
  BLACK_TROLL_KEYS: new Set([]),
}));
```

**Asserting the watermark presence/absence** — copy the duplicate-render assertion idiom from `:177-179`:
```typescript
const movesBtns = screen.getAllByTestId('opening-finding-card-6-moves');
fireEvent.click(movesBtns[0]!);
```
Note: because the card has both mobile and desktop branches, `data-testid="opening-finding-card-${idx}-troll-watermark"` will only appear ONCE (the watermark is a single element on the outer wrapper, not duplicated in each branch). So Phase 77 tests use `getByTestId` (singular) — different from the existing Moves/Games duplicate pattern.

**Tests to add (one per D- decision):**
- D-04: `pointer-events-none` class is present.
- D-05: watermark renders for both `classification: 'weakness'` and `classification: 'strength'`.
- Default-off path: a non-troll FEN does NOT render the watermark.
- Click-pass-through: with watermark present, the Moves button still fires `onFindingClick` (regression for D-04).

**What to copy:** `describe` block heading style with phase number; `vi.mock` placement at top of file; `screen.getByTestId` / `getAllByTestId` patterns; `makeFinding({ ...overrides })` factory pattern at `:28-50`.
**What to change:** add the new `describe` block at the bottom of the existing `describe('OpeningFindingCard', () => {...})` outer block; add the `vi.mock('@/data/trollOpenings', ...)` at file top.

---

### `frontend/src/components/move-explorer/MoveExplorer.tsx` (MODIFY — add inline icon to MoveRow)

**Analog:** itself. Insertion point is **NOT** `frontend/src/components/board/MoveList.tsx` (CONTEXT.md `<code_context>` mistakenly references that — the move list inside the Move Explorer is the `MoveRow` function-component at `MoveExplorer.tsx:224-334`, NOT the separate `MoveList.tsx` component used elsewhere).

**Existing `MoveRow` SAN cell** (`MoveExplorer.tsx:303-305`):
```tsx
<td className="py-1 text-sm text-foreground font-normal truncate">
  {entry.move_san}
</td>
```

**Existing inline icon-next-to-data idiom in this same file** (`MoveExplorer.tsx:307-316`) — exactly the analog pattern for "small icon next to SAN":
```tsx
<td className="py-1 text-right tabular-nums">
  <span className="inline-flex items-center justify-end gap-0.5">
    {entry.transposition_count > entry.game_count && (
      <TranspositionInfo
        moveSan={entry.move_san}
        transpositionCount={entry.transposition_count}
        gameCount={entry.game_count}
      />
    )}
    {entry.game_count}
  </span>
</td>
```
Phase 77 will use the same `<span className="inline-flex items-center gap-1">` wrapper around `{entry.move_san}` + the conditional icon. Use `gap-1` (slightly more breathing room than the `gap-0.5` used by the games-cell, since the icon is larger than the lucide arrow).

**Side-just-moved derivation** (per RESEARCH.md Pattern 2 + Pitfall 7) — derive in the parent `MoveExplorer` once, pass to each `MoveRow` as a prop. Insert the derivation alongside the existing `moveMap` `useMemo` at `:68-72`:
```typescript
const moveMap = useMemo(() => {
  const chess = new Chess(position);
  const legalMoves = chess.moves({ verbose: true });
  return new Map(legalMoves.map(m => [m.san, { from: m.from, to: m.to }]));
}, [position]);
```
Phase 77 adds (also as `useMemo` to keep the same render-perf shape):
```typescript
const sideJustMoved: Color = useMemo(() => {
  const tokens = position.split(' ');
  const sideToken = tokens[1];
  if (sideToken !== 'w' && sideToken !== 'b') {
    throw new Error(`MoveExplorer: position must be a full FEN with side-to-move, got: ${position}`);
  }
  return sideToken === 'w' ? 'white' : 'black';
}, [position]);
```

**`MoveRow` prop addition** — copy the prop-passing pattern from `MoveExplorer.tsx:202-213`:
```tsx
<MoveRow
  key={entry.move_san}
  entry={entry}
  selectedMove={selectedMove}
  onRowClick={handleRowClick}
  onRowKeyDown={handleRowKeyDown}
  onMoveHover={onMoveHover}
  highlightColor={isHighlighted ? highlightedMove.color : null}
  highlightPulse={isHighlighted ? highlightedMove.pulse : false}
  rowRef={isHighlighted ? highlightedRowRef : undefined}
/>
```
Phase 77 adds one more line: `sideJustMoved={sideJustMoved}`.

**`MoveRow` signature update** — copy the inline-typed-props pattern from `:224-236`:
```tsx
function MoveRow({ entry, selectedMove, onRowClick, onRowKeyDown, onMoveHover, highlightColor, highlightPulse, rowRef }: {
  entry: NextMoveEntry;
  selectedMove: string | null;
  onRowClick: (entry: NextMoveEntry) => void;
  onRowKeyDown: (e: React.KeyboardEvent, entry: NextMoveEntry) => void;
  onMoveHover?: (moveSan: string | null) => void;
  highlightColor: string | null;
  highlightPulse: boolean;
  rowRef?: React.Ref<HTMLTableRowElement>;
}) {
```
Phase 77 adds `sideJustMoved: Color;` to the type and `sideJustMoved` to the destructuring.

**Inline icon JSX** — combine `MoveExplorer.tsx:303-305` (current SAN cell) + RESEARCH.md Pattern 4:
```tsx
<td className="py-1 text-sm text-foreground font-normal truncate">
  <span className="inline-flex items-center gap-1">
    <span>{entry.move_san}</span>
    {showTroll && (
      <img
        src={trollFaceUrl}
        alt=""
        aria-hidden="true"
        data-testid={`move-list-row-${entry.move_san}-troll-icon`}
        className="hidden sm:inline-block h-3.5 w-3.5"
      />
    )}
  </span>
</td>
```
- `hidden sm:inline-block` enforces D-07 (desktop-only).
- `h-3.5 w-3.5` matches the lucide icon size used for `ArrowRightLeft` at `:362` (`className="inline h-4 w-4 mr-1"`) and the existing 3.5 size used by lucide icons in `OpeningFindingCard.tsx:111` (`className="h-3.5 w-3.5"`).

**`isTrollPosition` call site** — add the derived constant inside `MoveRow` near `:240-245` where similar derived values live:
```typescript
const showTroll = isTrollPosition(entry.result_fen, sideJustMoved);
```

**What to copy:** the `inline-flex items-center gap-N` wrapper idiom (already used inside this same file at `:307`); the conditional rendering pattern `{cond && <Component .../>}` (used six times in this file); the prop-typing inline-object pattern at `:224-236`.
**What to change:** wrap `{entry.move_san}` in a `<span>` inside a new `inline-flex` wrapper; add the conditional `<img>` with the `hidden sm:inline-block` D-07 gate; add a new `sideJustMoved: Color` prop to `MoveRow`; derive `sideJustMoved` once in the parent and pass it down.

---

### `frontend/src/components/move-explorer/__tests__/MoveExplorer.test.tsx` (MODIFY — extend with icon assertions)

**Analog:** itself; 297 lines, with two existing top-level `describe` blocks: `'MoveExplorer — highlightedMove prop'` and `'Phase 76 — Conf column + mute extension'`. Pattern: each phase gets its own top-level `describe`.

**Existing `vi.mock` shape** (`MoveExplorer.test.tsx:7-9`):
```typescript
vi.mock('@/components/ui/tooltip', () => ({
  Tooltip: ({ children }: { children: React.ReactNode }) => children,
}));
```
Phase 77 adds at the top of the file:
```typescript
vi.mock('@/data/trollOpenings', () => ({
  WHITE_TROLL_KEYS: new Set(['<key derived from the test fixture board FEN>']),
  BLACK_TROLL_KEYS: new Set([]),
}));
```

**`makeEntry` factory + position fixtures** — already exist at `MoveExplorer.test.tsx:27-45` and `:23-25`:
```typescript
const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
const AFTER_E4_FEN = 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1';

function makeEntry(overrides: Partial<NextMoveEntry> & Pick<NextMoveEntry, 'move_san'>): NextMoveEntry {
  return {
    move_san: overrides.move_san,
    game_count: 100,
    // ...
    result_fen: '',
    // ...
    ...overrides,
  };
}
```
Phase 77 tests pass `result_fen` overrides (the existing default is empty string — an invalid FEN, but harmless because the existing tests don't exercise the troll-matcher path). Phase 77 tests must override `result_fen: '<board fen that derives to a key in WHITE_TROLL_KEYS>'`.

**Phase 76 `describe` shape to mirror** — `MoveExplorer.test.tsx:190-296`:
```typescript
describe('Phase 76 — Conf column + mute extension', () => {
  it('renders the Conf header cell with data-testid="move-explorer-th-conf"', () => {
    render(
      <MoveExplorer
        moves={[makeEntry({ move_san: 'e4' })]}
        isLoading={false}
        isError={false}
        position={START_FEN}
        onMoveClick={() => {}}
      />,
    );
    const th = screen.getByTestId('move-explorer-th-conf');
    expect(th.textContent?.trim()).toBe('Conf');
  });
  // ...
});
```
Phase 77 adds `describe('Phase 77 — Troll-opening inline icon', () => { ... })`.

**Tests to add (mapped to D- decisions):**
- D-06 positive: `result_fen` matching the mocked `WHITE_TROLL_KEYS` set produces an `<img>` with the right `data-testid`.
- D-06 negative: `result_fen` not in the set produces no icon.
- D-07: the icon's class string contains `hidden` and `sm:inline-block` (jsdom default viewport is desktop-width; assert via `className` contains, not via visibility).
- D-10: when `position` is `START_FEN` (white-to-move), `sideJustMoved` is `white` and `WHITE_TROLL_KEYS` is consulted; flipping to a black-to-move position consults `BLACK_TROLL_KEYS`. Validate via the mock asymmetry (white set populated, black set empty).
- Pitfall 7 defensive: when `position` is a board-only FEN (no side-to-move token), the component throws (use `expect(() => render(...)).toThrow(...)`).

**What to copy:** `vi.mock` placement (top of file, before component import); `START_FEN` / `AFTER_E4_FEN` constants; `makeEntry({ move_san: 'e4', result_fen: '...' })` factory pattern; one-`it` one-assertion style.
**What to change:** add a new top-level `describe('Phase 77 — Troll-opening inline icon', ...)`; add the `@/data/trollOpenings` mock; pass `result_fen` overrides on entries used in the new tests.

---

## Shared Patterns

### Theme constant for opacity
**Source:** `frontend/src/lib/theme.ts:76-77`
**Apply to:** `OpeningFindingCard.tsx` watermark `style.opacity`
```typescript
// Opacity applied to stats/charts with unreliable data (below MIN_GAMES_FOR_RELIABLE_STATS)
export const UNRELIABLE_OPACITY = 0.5;
```
Phase 77 adds (adjacent to the above):
```typescript
// Opacity applied to the troll-opening watermark on OpeningFindingCard.
// Locked at 0.30 per Phase 77 D-02. NOTE: when the parent card has UNRELIABLE_OPACITY
// applied (n_games < 10 or confidence === 'low'), the watermark renders at 0.15 due to
// CSS opacity multiplication — accepted per Phase 77 RESEARCH.md Pitfall 4.
export const TROLL_WATERMARK_OPACITY = 0.30;
```
This is also the canonical project pattern per CLAUDE.md "Theme constants in theme.ts — all theme-relevant color constants ... must be defined in `frontend/src/lib/theme.ts`".

### Decorative `<img>` (alt="" + aria-hidden) idiom
**Source:** No in-repo analog (first decorative-image pattern in the project — verified by `grep -rn "import.*\.svg"` returning zero matches).
**Apply to:** both watermark and inline icon
```tsx
<img
  src={trollFaceUrl}
  alt=""              // empty alt = decorative; screen readers skip
  aria-hidden="true"  // belt-and-suspenders for older AT
  data-testid="..."   // for snapshot / DOM tests
  className="..."
/>
```
Pattern derives from CLAUDE.md "ARIA labels on icon-only buttons" (interactive icons get aria-label; decorative ones use alt="" + aria-hidden).

### Path alias `@/...`
**Source:** every TS/TSX file in `frontend/src/` (universal convention). E.g. `OpeningFindingCard.tsx:2-10`:
```typescript
import { LazyMiniBoard } from '@/components/board/LazyMiniBoard';
import { Tooltip } from '@/components/ui/tooltip';
import { ... } from '@/lib/openingInsights';
import { MIN_GAMES_FOR_RELIABLE_STATS, UNRELIABLE_OPACITY } from '@/lib/theme';
import type { OpeningInsightFinding } from '@/types/insights';
```
**Apply to:** all new imports — use `@/data/trollOpenings`, `@/lib/trollOpenings`, `@/assets/troll-face.svg`, `@/types/api` (NOT relative paths), except inside test files where `./<sibling>` is the convention for the file-under-test.

### `data-testid` template
**Source:** `OpeningFindingCard.tsx:90, 94, 108, 120, 133` and `MoveExplorer.tsx:285, 350` — the project's universal `${component}-${id}-${element}` template.
**Apply to:** the two new decorative elements
- `data-testid="opening-finding-card-${idx}-troll-watermark"` (matches the `opening-finding-card-${idx}-...` family already on this card)
- `data-testid="move-list-row-${entry.move_san}-troll-icon"` (per CONTEXT.md `<code_context>` line 98; note that the existing row testid is `move-explorer-row-${move_san}` — both are valid; CONTEXT.md explicitly prescribes the `move-list-row-` form for this new icon to differentiate)

### `noUncheckedIndexedAccess` narrowing
**Source:** `frontend/src/lib/zobrist.ts:830-836, 894-895, 920-940` — the project's canonical example, with `// safe: ...` comments on every `!` non-null assertion.
**Apply to:** the new `trollOpenings.ts` utility (`fen.split(' ', 1)[0]!` after the length check) and the curation script (every `placement.split('/')[i]` and `tokens[1]` access).

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `frontend/scripts/curate_troll_openings.ts` | build-time codegen script (Node/TS) | file-I/O + transform | The repo has no existing TS/Node build-time script. The closest precedent is `scripts/gen_endgame_zones_ts.py` (Python). Use RESEARCH.md "Curation Script Skeleton" as the primary template; copy docstring+usage convention from the Python script. |

The SVG asset move (`temp/Troll-Face.svg` → `frontend/src/assets/troll-face.svg`) has no functional analog (`react.svg` exists in `assets/` but is not imported anywhere). This is acceptable — the asset-import pattern is documented in RESEARCH.md "Standard Stack" as Vite default behavior, and `<img src={trollFaceUrl} />` is a one-line pattern that needs no codebase precedent.

## Metadata

**Analog search scope:**
- `frontend/src/lib/` (16 files — read `openingInsights.ts`, `openingInsights.test.ts`, `theme.ts`, `zobrist.ts`, `zobrist.test.ts`, `pgn.ts`)
- `frontend/src/components/insights/` (5 files — read `OpeningFindingCard.tsx`, `OpeningFindingCard.test.tsx`)
- `frontend/src/components/move-explorer/` (read `MoveExplorer.tsx`, `__tests__/MoveExplorer.test.tsx`)
- `frontend/src/types/api.ts` (Color type at line 39)
- `frontend/src/assets/` (1 file: `react.svg`, unused)
- `frontend/src/generated/` (1 file: `endgameZones.ts` — codegen analog)
- `frontend/src/data/` — NOT YET EXISTING (will be created)
- `frontend/scripts/` — NOT YET EXISTING (will be created)
- `scripts/gen_endgame_zones_ts.py` (Python codegen analog for the curation script)
- `temp/Troll-Face.svg` — confirmed source asset present

**Verified non-existence:**
- `frontend/scripts/` directory does NOT exist (`ls` returns "No such file or directory").
- `frontend/src/data/` directory does NOT exist.
- Zero `import .*\.svg` matches across `frontend/src/` (so this is the first imported SVG).
- No `vite-plugin-svgr` in `package.json` (RESEARCH.md verified).

**Files scanned:** ~14 source files read line-by-line; ~6 grep scopes for cross-cutting patterns.
**Pattern extraction date:** 2026-04-28
