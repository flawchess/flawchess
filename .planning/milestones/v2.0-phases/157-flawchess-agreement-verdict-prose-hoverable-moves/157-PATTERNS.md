# Phase 157: FlawChess Agreement Verdict - Pattern Map

**Mapped:** 2026-07-07
**Files analyzed:** 5 (2 new lib files, 2 new component files, 1 modified page)
**Analogs found:** 5 / 5 (all exact — this phase is a reuse-and-mirror exercise per RESEARCH.md)

This PATTERNS.md builds on RESEARCH.md's already-detailed analog map (Patterns 1-3, Code Examples, Don't-Hand-Roll table) — it does not re-derive that analysis. It adds concrete, line-anchored excerpts for the planner to copy from, and resolves the extraction-vs-duplication question RESEARCH.md flagged as open.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `frontend/src/lib/flawChessVerdict.ts` | utility (pure classifier) | transform | `frontend/src/lib/positionVerdict.ts` | exact |
| `frontend/src/lib/flawChessVerdict.test.ts` | test | transform | `frontend/src/lib/positionVerdict.test.ts` | exact |
| `frontend/src/components/analysis/FlawChessAgreementVerdict.tsx` | component | request-response (hover/click UI over pre-fetched engine data) | `frontend/src/components/analysis/MaiaMoveQualityBar.tsx` | exact (interaction shell); role-match (bar chrome doesn't apply, only the prose+span sub-pattern does) |
| `frontend/src/components/analysis/__tests__/FlawChessAgreementVerdict.test.tsx` | test | request-response | `frontend/src/components/analysis/__tests__/MaiaMoveQualityBar.test.tsx` (prose-span tests, lines 143-200) | exact |
| `frontend/src/pages/Analysis.tsx` (modify) | component (page, wiring only) | request-response | itself — mirror the existing `<MaiaHumanPanel onHoverMovesChange=.../>` call site (L1540-1543) as the wiring template | exact |

## Pattern Assignments

### `frontend/src/lib/flawChessVerdict.ts` (utility, transform)

**Analog:** `frontend/src/lib/positionVerdict.ts` (full file, 188 lines — read in full, small file)

**Module doc-comment convention** (lines 1-21): every pure verdict module opens with a comment describing the tier thresholds, the naming/ordering rule for the `moves` array, and which existing module it reuses instead of re-deriving. Mirror this shape, but the content is D-01–D-11, not the Maia badMass logic:

```typescript
// Source: frontend/src/lib/positionVerdict.ts:1-21 — doc-comment shape to mirror
/**
 * positionVerdict — pure, worker-free prose position-evaluation module ...
 * Classifies "how hard is this position ..." from the summed Maia probability
 * mass of Stockfish-graded mistakes + blunders ...
 *   - safe (badMass < SAFE_MAX_BAD_MASS): ...
 *   - tricky / difficult (badMass >= SAFE_MAX_BAD_MASS): ...
 * Reuses moveQuality.ts's nearestByElo rung lookup ... rather than re-deriving it.
 */
```

**Imports pattern** (lines 23-25) — pull constants from generated/shared modules, never restate a threshold literal:

```typescript
import { nearestByElo, type MoveQuality } from '@/lib/moveQuality';
import type { MoveCurvePoint } from '@/hooks/useMaiaEngine';
import { MOVE_QUALITY_BEST, MOVE_QUALITY_BLUNDER, MOVE_QUALITY_GOOD, MOVE_QUALITY_MISTAKE } from '@/lib/theme';
```
For `flawChessVerdict.ts`, the equivalent imports (per RESEARCH.md's Code Examples section and Don't-Hand-Roll table) are:
```typescript
import type { RankedLine } from '@/lib/engine/types';
import type { PvLine } from '@/hooks/uciParser';
import { evalToExpectedScore, type MoverColor } from '@/lib/liveFlaw';
import { BLUNDER_DROP } from '@/generated/flawThresholds'; // 0.15, win% units — D-05's named constant
import { FLAWCHESS_ENGINE_ARROW, BEST_MOVE_ARROW } from '@/lib/theme';
```

**Types + named constants** (lines 27-68) — export a tier union, a "verdict move" shape, and named thresholds with a one-line comment on each boundary:

```typescript
// Source: frontend/src/lib/positionVerdict.ts:30-42, 63-68
export type VerdictTier = 'safe' | 'tricky' | 'difficult';

export interface VerdictMove {
  san: string;
  maiaPct: number;
  role: 'good' | 'bad' | 'escape';
  textColor: string;
  arrowColor: string;
  evalCp: number | null;
  evalMate: number | null;
}

/** badMass strictly below this -> 'safe'. */
export const SAFE_MAX_BAD_MASS = 0.2;
```
Do NOT reuse `VerdictTier`/`VerdictMove` directly (RESEARCH.md Pattern 1 explicitly rules this out — `role: 'good'|'bad'|'escape'` and `maiaPct` don't map onto FC-vs-SF agreement). Declare a new, analogous `FlawChessVerdictTier = 'aligned' | 'safe' | 'sharp'` and `FlawChessVerdictMove` per RESEARCH.md lines 186-200 (`role: 'flawchess' | 'stockfish'`, `evalCp`/`evalMate` white-POV, `textColor`/`arrowColor` from the two theme constants).

**Eval formatter** (lines 72-84) — exported, unit-testable, `—` fallback for null, exact string contract to mirror or reuse directly (RESEARCH.md Open Question 1 recommends `formatScore` from `EngineLines.tsx:179` instead for cross-badge consistency — planner's call, either format function already exists, do not write a third):

```typescript
export function formatVerdictEval(evalCp: number | null, evalMate: number | null): string {
  if (evalMate !== null) return evalMate > 0 ? `M${evalMate}` : `-M${Math.abs(evalMate)}`;
  if (evalCp !== null) {
    const pawns = evalCp / 100;
    return pawns >= 0 ? `+${pawns.toFixed(1)}` : pawns.toFixed(1);
  }
  return '—';
}
```

**Null-gate / "nothing to narrate yet" contract** (lines 154-163) — the top-level compute function returns `null` (not a bogus tier) when inputs aren't ready; the caller falls back to static help text. This is the exact shape D-06 requires:

```typescript
// Source: frontend/src/lib/positionVerdict.ts:154-163
export function computePositionVerdict(
  perElo: MoveCurvePoint[],
  selectedElo: number,
  shownSans: string[],
  qualityBySan: Map<string, VerdictMoveGrade>,
): PositionVerdictResult | null {
  const rung = nearestByElo(perElo, selectedElo);
  const ranked = rankMoves(rung, shownSans, qualityBySan);
  const totalMass = ranked.reduce((sum, m) => sum + m.probability, 0);
  if (ranked.length === 0 || totalMass <= 0) return null;
  ...
```
Mirror this exact early-return contract for `flawChessVerdict.ts`'s top-level function (name it e.g. `computeFlawChessVerdict`): return `null` when `flawChessLine === null`, `stockfishLine === null`, `flawChessLine.objectiveEvalCp === null`, or both `stockfishLine.evalCp`/`evalMate` are null (D-06). The Analysis.tsx caller (per D-02/D-03) additionally gates the whole render on `engineEnabled === true` BEFORE calling this function — don't fold that gate into the pure module (it's a UI/rendering concern, not a classification concern; `positionVerdict.ts` has no such gate itself, all gating is done by its caller in `MaiaMoveQualityBar.tsx`).

**Tier-split composition using the existing sigmoid** (RESEARCH.md Code Examples section, verbatim — copy this, don't re-derive the sigmoid math):

```typescript
// Source: 157-RESEARCH.md "Computing the win%-drop tier (D-05)" — composes
// existing exports, invents nothing new
function computeDrop(
  fcEvalCp: number | null,
  sfEvalCp: number | null,
  sfEvalMate: number | null,
  mover: MoverColor,
): number | null {
  if (fcEvalCp === null || (sfEvalCp === null && sfEvalMate === null)) return null; // D-06 gate
  const fcWinPct = evalToExpectedScore(fcEvalCp, null, mover);       // FC has no mate field (Pitfall 4)
  const sfWinPct = evalToExpectedScore(sfEvalCp, sfEvalMate, mover);
  return sfWinPct - fcWinPct; // D-06: always >= 0 by construction
}

const tier: FlawChessVerdictTier =
  drop === 0 /* same move, D-04 aligned check is separate/prior */
    ? 'aligned'
    : drop < BLUNDER_DROP
      ? 'safe'
      : 'sharp';
```
Note D-04's `aligned` check is a UCI move-string equality check (`flawChessLine.rootMove === stockfishLine.moves[0]`), done BEFORE the drop computation — not derived from `drop === 0` (two different UCI moves can coincidentally have `drop === 0` in a very flat position; D-04 is explicit about string equality being the aligned criterion).

---

### `frontend/src/lib/flawChessVerdict.test.ts` (test)

**Analog:** `frontend/src/lib/positionVerdict.test.ts` — read this file directly before writing tests; it establishes the fixture style (`rung`-like helper objects, `Map` construction for per-move grades) and one-behavior-per-`it` granularity. Cover: D-04 (aligned), D-05 (safe vs sharp boundary at exactly `BLUNDER_DROP`), D-06 (null-gate on either side's missing eval), Pitfall 4 (FC side never reads/writes a mate field).

---

### `frontend/src/components/analysis/FlawChessAgreementVerdict.tsx` (component, request-response)

**Analog:** `frontend/src/components/analysis/MaiaMoveQualityBar.tsx` (468 lines, already read in full — reuse the prose+span sub-pattern, NOT the stacked-bar chrome which doesn't apply here).

**Imports pattern** (lines 33-49) — Radix popover primitives + the pure verdict module + theme constants, same shape the new component needs:

```typescript
import { useEffect, useMemo, useRef, useState } from 'react';
import { Popover, PopoverAnchor, PopoverContent } from '@/components/ui/popover';
import { computePositionVerdict, formatVerdictEval, type PositionVerdictResult, type VerdictMove } from '@/lib/positionVerdict';
```
New file's equivalent:
```typescript
import { useEffect, useMemo, useRef, useState } from 'react';
import { Popover, PopoverAnchor, PopoverContent } from '@/components/ui/popover';
import { computeFlawChessVerdict, formatVerdictEval /* or formatScore, per Open Q1 */ } from '@/lib/flawChessVerdict';
import type { RankedLine } from '@/lib/engine/types';
import type { PvLine } from '@/hooks/uciParser';
import type { HoveredQualityMove } from '@/components/analysis/MaiaMoveQualityBar'; // re-export point, see below
```
`HoveredQualityMove` (the `{san, color}` shape `onHoverMovesChange` emits) is currently declared and exported from `MaiaMoveQualityBar.tsx:52-55` — import it from there rather than redeclaring a structurally-identical interface, OR (cleaner, planner's call) lift it to a shared location (e.g. `@/lib/engine/types.ts` or a small shared UI-types module) since it's no longer Maia-specific once a second consumer exists. Either is acceptable; do not duplicate the interface.

**`ProseMoveSpan` interaction shell — extraction vs duplication (RESEARCH.md's flagged open decision, resolved here with both excerpts):**

Full contract, verbatim (`MaiaMoveQualityBar.tsx:145-207`):
```typescript
function ProseMoveSpan({
  move, isOpen, onOpenDelayed, onOpenNow, onClose, onPlay,
}: {
  move: VerdictMove; isOpen: boolean;
  onOpenDelayed: () => void; onOpenNow: () => void; onClose: () => void; onPlay?: () => void;
}): React.ReactElement {
  const evalText = formatVerdictEval(move.evalCp, move.evalMate);
  const ariaLabel = `${move.san}, ${move.maiaPct}% at this rating, evaluated ${evalText}. Click to play it.`;
  const wasOpenAtPress = useRef(false); // synchronous press-time snapshot, NOT React state
  return (
    <Popover open={isOpen} onOpenChange={(next) => (next ? undefined : onClose())}>
      <PopoverAnchor asChild>
        <button
          type="button"
          className="font-semibold underline decoration-dotted underline-offset-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          style={{ color: move.textColor }}
          aria-label={ariaLabel}
          data-testid={`maia-prose-move-${move.san}`}
          onMouseEnter={onOpenDelayed}
          onMouseLeave={onClose}
          onFocus={onOpenNow}
          onBlur={onClose}
          onPointerDown={() => { wasOpenAtPress.current = isOpen; }}
          onClick={() => {
            if (wasOpenAtPress.current) { if (onPlay) onPlay(); else onClose(); }
            else { onOpenNow(); }
          }}
        >
          {move.san}
        </button>
      </PopoverAnchor>
      <PopoverContent side="top" onMouseEnter={onOpenNow} onMouseLeave={onClose}
        className="w-auto max-w-xs rounded-md border-0 bg-foreground px-3 py-1.5 text-xs text-background"
        data-testid={`maia-prose-move-tooltip-${move.san}`}
      >
        {`${move.maiaPct}% at this rating · ${evalText}`}  {/* <-- Maia-hardcoded, does NOT fit D-10 */}
      </PopoverContent>
    </Popover>
  );
}
```

**Recommendation (per RESEARCH.md's own "extraction is the recommended default"): extract the shell.** Concretely:
1. Add a new export to `MaiaMoveQualityBar.tsx` (or a new small shared file, e.g. `frontend/src/components/analysis/ProseSpan.tsx` — planner's call, but a shared file avoids re-touching a shipped component's export surface) — a content-parameterized version:
   ```typescript
   export function ProseSpan({
     label, textColor, ariaLabel, testId, isOpen,
     onOpenDelayed, onOpenNow, onClose, onPlay, children,
   }: {
     label: string; textColor: string; ariaLabel: string; testId: string; isOpen: boolean;
     onOpenDelayed: () => void; onOpenNow: () => void; onClose: () => void; onPlay?: () => void;
     children: React.ReactNode; // popover body — content-agnostic per RESEARCH.md's guidance
   }): React.ReactElement { /* identical button/Popover/ref wiring as above, parameterized */ }
   ```
2. `MaiaMoveQualityBar.tsx`'s own `ProseMoveSpan` becomes a thin wrapper calling `ProseSpan` with its Maia-specific `children` (`{move.maiaPct}% at this rating · {evalText}`) — its existing 3 tests (`MaiaMoveQualityBar.test.tsx:143-200`) must keep passing unchanged (same `data-testid`s, same aria-label, same behavior) since this is a refactor of a shipped, tested file.
3. The new `FlawChessAgreementVerdict.tsx` calls the same `ProseSpan` with the D-10 two-line popover body (`FlawChess: … (practical)` / `Stockfish: … (objective)`, omitting the FlawChess line when the SF pick wasn't also FC-ranked).

If the planner instead chooses to duplicate (lower-risk, zero touch to `MaiaMoveQualityBar.tsx`): copy the ~60-line shell verbatim into `FlawChessAgreementVerdict.tsx` with FlawChess-appropriate prop/type names and the D-10 popover content. Either choice is acceptable per CONTEXT.md's explicit "planner's discretion" framing — this PATTERNS.md surfaces both so the planner doesn't have to re-derive the tradeoff RESEARCH.md already did.

**Parent-side state ownership** (`MaiaMoveQualityBar.tsx:272-277, 355-367`) — one `activeSan: string | null`, one hover-timer ref, three handler factories; mirror directly (this phase has at most 2 spans open at once — FC pick and SF pick — never more, so no bar-segment-equivalent complexity):

```typescript
const [activeProseSan, setActiveProseSan] = useState<string | null>(null);
const proseHoverTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
const PROSE_POPOVER_OPEN_DELAY_MS = 100; // matches InfoPopover / MaiaMoveQualityBar precedent — reuse the same constant/value, don't invent a different delay

const openProseNow = (san: string): void => { clearProseTimer(); setActiveProseSan(san); };
const openProseDelayed = (san: string): void => {
  clearProseTimer();
  proseHoverTimer.current = setTimeout(() => openProseNow(san), PROSE_POPOVER_OPEN_DELAY_MS);
};
const closeProse = (): void => { clearProseTimer(); setActiveProseSan(null); };
```

**Hover-lift effect** (`MaiaMoveQualityBar.tsx:299-318`) — derive the `HoveredQualityMove[] | null` for the hovered span and lift it via `useEffect`, clearing on unmount:

```typescript
const hoveredArrowMoves = useMemo<HoveredQualityMove[] | null>(() => {
  if (activeProseSan === null) return null;
  const move = /* find in this component's [fcMove, sfMove] array by san */;
  return move ? [{ san: move.san, color: move.arrowColor }] : null;
}, [activeProseSan, /* ...deps */]);

useEffect(() => {
  if (!onHoverMovesChange) return;
  onHoverMovesChange(hoveredArrowMoves);
  return () => onHoverMovesChange(null);
}, [hoveredArrowMoves, onHoverMovesChange]);
```
D-09 note: unlike Maia's bar (which can show a whole bucket's worth of moves), this component isolates exactly ONE arrow at a time (the single hovered pick) — `hoveredArrowMoves` will only ever be a 0- or 1-element array, in the pick's own tier color (`FLAWCHESS_ENGINE_ARROW` or `BEST_MOVE_ARROW`, not a severity color).

**Sentence-assembly pattern** (`MaiaMoveQualityBar.tsx:215-261`, `renderVerdictSentence`) — a plain function (not a hook) taking the verdict result + a `renderMove` callback, returning `React.ReactNode`, switching on tier to interpolate 1-2 named-move spans into one of the D-07 prose templates. Mirror this shape exactly for the three D-07 templates (aligned/safe/sharp), substituting the interpolated moves per template. `interleaveWithConjunction`/`joinMoveNames` are NOT needed here (RESEARCH.md explicitly notes this — each template names exactly 1 or 2 fixed moves, never a variable-length list).

**Fixed-height resting slot / no-Stockfish fallback** (`MaiaMoveQualityBar.tsx:442-464`, D-03's analog):

```jsx
<div className="min-h-[1.5rem] text-sm" data-testid="maia-quality-hovered-list">
  {/* ... */ verdict ? (
    <span data-testid="maia-position-verdict">{renderVerdictSentence(...)}</span>
  ) : (
    <span className="text-muted-foreground">
      Hover a segment to list its moves and highlight them on the board.
    </span>
  )}
</div>
```
For `FlawChessAgreementVerdict.tsx`: same `min-h-[...]` wrapper; render the tier prose when `computeFlawChessVerdict(...)` is non-null AND `engineEnabled === true`; render the muted `Turn on Stockfish to compare picks.` line (D-03) when `engineEnabled === false`; the loading/null-verdict case (D-06, mid-search) falls back to the SAME muted line per D-06's "no layout jump" requirement (or a near-identical resting message — planner's copy call).

---

### `frontend/src/components/analysis/__tests__/FlawChessAgreementVerdict.test.tsx` (test)

**Analog:** `frontend/src/components/analysis/__tests__/MaiaMoveQualityBar.test.tsx`, lines 143-200 (prose-span tests only — ignore the bar-segment tests earlier in that file, they don't apply):

```typescript
// Source: MaiaMoveQualityBar.test.tsx:143-161 — hover/focus opens popover with content
it('opens a prose move popover on hover/focus, showing ... (quick 260705-m3z)', () => {
  render(<MaiaMoveQualityBar ... />);
  const move = screen.getByTestId('maia-prose-move-g4');
  expect(screen.queryByTestId('maia-prose-move-tooltip-g4')).toBeNull();
  fireEvent.focus(move);
  expect(screen.getByTestId('maia-prose-move-tooltip-g4').textContent).toMatch(/11%/);
  fireEvent.blur(move);
  expect(screen.queryByTestId('maia-prose-move-tooltip-g4')).toBeNull();
});

// Source: MaiaMoveQualityBar.test.tsx:163-181 — open-at-press plays
it('plays a prose move as a free move when clicked while its popover is open (quick 260705-mth)', () => {
  const onPlayMove = vi.fn();
  render(<MaiaMoveQualityBar ... onPlayMove={onPlayMove} />);
  const move = screen.getByTestId('maia-prose-move-g4');
  fireEvent.focus(move);          // open it first
  fireEvent.pointerDown(move);    // press begins while open
  fireEvent.click(move);
  expect(onPlayMove).toHaveBeenCalledWith('g4');
});

// Source: MaiaMoveQualityBar.test.tsx:183-200 — closed-at-press only reveals
it('the first interaction reveals a prose move without playing it (quick 260705-mth)', () => {
  const onPlayMove = vi.fn();
  render(<MaiaMoveQualityBar ... onPlayMove={onPlayMove} />);
  const move = screen.getByTestId('maia-prose-move-g4');
  fireEvent.pointerDown(move);  // press begins closed
  fireEvent.click(move);
  expect(onPlayMove).not.toHaveBeenCalled();
  expect(screen.getByTestId('maia-prose-move-tooltip-g4')).toBeTruthy();
});
```
Mirror all three `fireEvent` patterns verbatim with the new component's `data-testid`s. Per RESEARCH.md's Wave-0-gaps note: this file needs NO `matchMedia`/`ResizeObserver` stubs (unlike `FlawChessEngineLines.test.tsx`, which needs them for its `Tooltip`+`MiniBoard` hover preview) — `MaiaMoveQualityBar.test.tsx`'s simpler setup is the correct template. Additional new-behavior tests to add (no analog exists yet, write fresh): D-02/D-03 (muted prompt when `engineEnabled=false`), D-10's per-pick popover content (two-line vs one-line omission when the Stockfish pick wasn't FC-ranked).

---

### `frontend/src/pages/Analysis.tsx` (modify)

**Analog:** the existing `<MaiaHumanPanel .../>` call site is the wiring template — no new plumbing needed, only a new call using already-existing state/handlers.

**Existing state/handlers to reuse (already declared, do not redeclare):**
```typescript
// Line 411 — already the exact HoveredQualityMove[] | null shape qualityHoverArrows consumes
const [hoveredQualityMoves, setHoveredQualityMoves] = useState<HoveredQualityMove[] | null>(null);

// Lines 513-520 — already resolves a SAN to from/to and calls makeMove; reuse directly
const playProseMove = (san: string): void => {
  try {
    const move = new Chess(position).move(san);
    if (move) makeMove(move.from, move.to);
  } catch {
    // SAN no longer legal (position changed under the prose) — ignore.
  }
};

// Lines 240-254 — module-private UCI->SAN helper; export it (or keep conversion
// call-site-local) — needed to convert flawChessEngine.rankedLines[0].rootMove
// and engine.pvLines[0].moves[0] (both UCI, D-08) into SANs before constructing
// verdict-move objects or calling onHoverMovesChange (Pitfall 2)
function bestSanFromPv(baseFen: string, uci: string | null): string | null { ... }
```

**Existing arrow-precedence chain (already wins in the right order, no change needed):**
```typescript
// Lines 1139-1142 — qualityHoverArrows already takes precedence over engineArrows;
// the new component's hover callback feeding setHoveredQualityMoves gets this for free
const baseArrows: BoardArrow[] | undefined =
  qualityHoverArrows ??
  pvSidelineArrows ??
  (engineArrows.length > 0 ? engineArrows : undefined);
```

**Insertion point** (inside `flawChessCard`, lines 1496-1513) — add the new component as a sibling directly below `FlawChessEngineLines`, inside the same `CardBody`, NOT folded into `FlawChessEngineLines`'s own props (per the "body-only sibling" boundary documented in `FlawChessEngineLines.tsx:19-20`):

```jsx
// Source: frontend/src/pages/Analysis.tsx:1504-1511 (existing) — insert the new
// component as a sibling right after this, still inside the same CardBody (else branch)
<FlawChessEngineLines
  rankedLines={flawChessEngine.rankedLines}
  isSearching={flawChessEngine.isSearching}
  baseFen={position}
  startPly={currentPly}
  flipped={boardFlipped}
  onMoveClick={playUciLine}
/>
{/* NEW */}
<FlawChessAgreementVerdict
  flawChessLine={flawChessEngine.rankedLines[0] ?? null}
  stockfishLine={engine.pvLines[0] ?? null}
  flawChessRankedLines={flawChessEngine.rankedLines}  // for D-10's "was SF pick also FC-ranked" check
  engineEnabled={engineEnabled}
  baseFen={position}
  onHoverMovesChange={setHoveredQualityMoves}
  onPlayMove={playProseMove}
/>
```

**Wiring precedent to copy verbatim** (the `MaiaHumanPanel` call site, lines 1533-1543 mobile / 1712-1723 desktop — same JSX rendered from the SAME `flawChessCard`/panel variable in both surfaces, satisfying SC4/REVIEW-01 parity by construction with zero extra work):
```jsx
// Source: frontend/src/pages/Analysis.tsx:1533-1543
<MaiaHumanPanel
  selectedElo={selectedElo}
  perElo={maia.perElo}
  playedSan={playedSan}
  bestSan={bestSan}
  shownSans={shownSans}
  qualityBySan={qualityBySan}
  engineTopLines={engineTopLines}
  onHoverMovesChange={setHoveredQualityMoves}
  onPlayMove={playProseMove}
/>
```
Because `flawChessCard` (line 1476) is a single JSX variable rendered at both line 1532 (mobile `humanTab`) and line 1712 (desktop human column), the new component only needs to be added ONCE inside that variable's definition — it automatically appears on both surfaces, which is exactly what SC4/REVIEW-01 (game-review parity) requires. Do NOT duplicate the insertion at both render sites.

## Shared Patterns

### Hover-intent + click-to-play interaction shell
**Source:** `frontend/src/components/analysis/MaiaMoveQualityBar.tsx:145-207` (`ProseMoveSpan`)
**Apply to:** `FlawChessAgreementVerdict.tsx` — either via extraction into a shared `ProseSpan` (recommended) or duplication (acceptable fallback). See full extraction proposal above.

### Pure verdict-classification module shape
**Source:** `frontend/src/lib/positionVerdict.ts` (full file)
**Apply to:** `flawChessVerdict.ts` — tier union + named constants (import `BLUNDER_DROP` rather than restate) + verdict-move interface + `null`-gate contract + exported eval formatter.

### Board-arrow hover-isolation via lifted state
**Source:** `frontend/src/pages/Analysis.tsx:1049-1067` (`qualityHoverArrows`), `:1139-1142` (precedence chain)
**Apply to:** `FlawChessAgreementVerdict.tsx`'s hover callback — already-existing plumbing, zero changes needed to this memo; the new component just becomes a second caller of `setHoveredQualityMoves`.

### Win% sigmoid + inverse
**Source:** `frontend/src/lib/liveFlaw.ts:24, 46, 53` (`MoverColor`, `expectedScoreToWhitePovCp`, `evalToExpectedScore`)
**Apply to:** `flawChessVerdict.ts`'s drop computation (D-05). Do not hand-roll a second sigmoid (explicit Don't-Hand-Roll entry in RESEARCH.md).

### Free-move click handler
**Source:** `frontend/src/pages/Analysis.tsx:513-520` (`playProseMove`)
**Apply to:** wired as-is into the new component's `onPlayMove` prop; no changes to this function.

## No Analog Found

None — every file in scope has an exact analog (this phase is explicitly a reuse-and-mirror exercise per RESEARCH.md's own framing).

## Metadata

**Analog search scope:** `frontend/src/lib/`, `frontend/src/components/analysis/`, `frontend/src/pages/Analysis.tsx`, `frontend/src/lib/engine/types.ts`, `frontend/src/generated/flawThresholds.ts` (all directly read this session; RESEARCH.md's own Sources list also covers `frontend/src/hooks/uciParser.ts`, `frontend/src/lib/theme.ts`, `frontend/src/components/ui/popover.tsx`, `frontend/src/lib/positionVerdict.test.ts`, `frontend/src/components/analysis/__tests__/FlawChessEngineLines.test.tsx`).
**Files scanned:** 8 read directly this session (`positionVerdict.ts`, `MaiaMoveQualityBar.tsx`, `engine/types.ts`, `Analysis.tsx` targeted ranges, `MaiaMoveQualityBar.test.tsx` targeted range) + grep-located line numbers in `liveFlaw.ts`, `flawThresholds.ts`, `EngineLines.tsx`, `FlawChessEngineLines.tsx`.
**Pattern extraction date:** 2026-07-07
