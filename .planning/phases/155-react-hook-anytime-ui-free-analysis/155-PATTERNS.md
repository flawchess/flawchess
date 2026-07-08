# Phase 155: React Hook + Anytime UI (Free Analysis) - Pattern Map

**Mapped:** 2026-07-06
**Files analyzed:** 6 (2 create, 1 create-or-reuse UI primitive, 3 modify)
**Analogs found:** 6 / 6

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `frontend/src/hooks/useFlawChessEngine.ts` | hook | event-driven (worker message stream → throttled React state) | `frontend/src/hooks/useStockfishEngine.ts` | exact (same worker-lifecycle + debounce shape; only the transport differs: pool/queue calls vs raw `postMessage`) |
| `frontend/src/components/analysis/FlawChessEngineLines.tsx` | component | request-response (props in, rendered rows out) | `frontend/src/components/analysis/EngineLines.tsx` | exact (explicit "structural sibling" in UI-SPEC) |
| `frontend/src/lib/expectedScoreToWhitePovCp` (new export, likely added to `frontend/src/lib/liveFlaw.ts`) | utility | transform (pure function) | `frontend/src/lib/liveFlaw.ts`'s `evalToExpectedScore` | exact (algebraic inverse of an existing function in the same file) |
| `frontend/src/components/ui/switch.tsx` | component (ui primitive) | request-response (controlled toggle) | `frontend/src/components/ui/checkbox.tsx` | role-match (both are hand-rolled Radix primitive wrappers with CVA-less `data-checked:`/`data-state=checked` styling; no `switch.tsx` exists yet) |
| `frontend/src/pages/Analysis.tsx` (MODIFY) | component (page) | request-response (composition/orchestration) | itself — existing `engineEnabled`/`EvalBar`/`CardHeader` sections (lines ~1053-1165, ~1503-1552) | exact (same file, extending established precedent) |
| `frontend/src/lib/theme.ts` (MODIFY) | config | n/a (constant export) | itself — `STOCKFISH_ACCENT`/`MAIA_ACCENT` (lines 70, 74) | exact (same file, same convention) |

## Pattern Assignments

### `frontend/src/hooks/useFlawChessEngine.ts` (hook, event-driven)

**Analog:** `frontend/src/hooks/useStockfishEngine.ts` (389 lines, read in full)

**Imports pattern** (lines 17-19):
```typescript
import { useRef, useState, useCallback, useEffect } from 'react';
import { parseInfoLine } from './uciParser';
import type { PvLine } from './uciParser';
```
The new hook swaps `parseInfoLine`/`PvLine` for the frozen contract types:
```typescript
import { useRef, useState, useCallback, useEffect } from 'react';
import { mctsSearch } from '@/lib/engine/mctsSearch';
import { createWorkerPool, computePoolSize } from '@/lib/engine/workerPool';
import { createMaiaQueue } from '@/lib/engine/maiaQueue';
import type { EngineSnapshot, SearchBudget, EngineProviders } from '@/lib/engine/types';
```

**Constants pattern** (lines 21-36) — named constants, no magic numbers, exact convention to copy:
```typescript
const RAPID_STEP_DEBOUNCE_MS = 150; // reuse this exact constant/value for both the FEN debounce AND the new onSnapshot throttle (D-09) — same value, two different mechanisms (see Pitfall 3 in RESEARCH.md)
```
Add two new named constants for the FlawChess Engine's own budget (RESEARCH.md Open Question 3 — flag as tunable):
```typescript
const FLAWCHESS_ENGINE_MAX_NODES = /* placeholder, e.g. 400 */;
const FLAWCHESS_ENGINE_MAX_PLIES = 8; // must stay in the locked [6,10] band (SEED-082)
```

**Worker/provider lifecycle pattern** (lines 235-347, gated on `enabled`):
```typescript
useEffect(() => {
  if (!enabled) return;
  const worker = new Worker(ENGINE_PATH);
  workerRef.current = worker;
  // ... message handlers ...
  return () => {
    worker.postMessage('stop');
    worker.terminate();
    workerRef.current = null;
  };
}, [enabled]); // re-run only if enabled toggles
```
Adapt to the pool/queue pair (both created only while the switch is ON; RESEARCH.md Pattern 1 gives the exact adapted shape — `createWorkerPool()`/`createMaiaQueue()` in refs, terminated on cleanup).

**Adaptive debounce pattern** (lines 145-172) — "settled fires immediately, rapid succession coalesces":
```typescript
const [debouncedFen, setDebouncedFen] = useState<string | null>(null);
useEffect(() => {
  if (fen === null) { setDebouncedFen(null); return; }
  const now = Date.now();
  const sinceLast = now - lastFenChangeAtRef.current;
  lastFenChangeAtRef.current = now;
  if (sinceLast > RAPID_STEP_DEBOUNCE_MS) { setDebouncedFen(fen); return; }
  const timer = setTimeout(() => setDebouncedFen(fen), RAPID_STEP_DEBOUNCE_MS);
  return () => clearTimeout(timer);
}, [fen]);
```
Reuse verbatim for FEN navigation into `mctsSearch`. **Critical addition not in this analog:** on every debounced-FEN change, call BOTH `abortControllerRef.current?.abort()` AND `poolRef.current.stopAll()` before starting the new `mctsSearch` — the analog only has a single Worker with its own `stop`/`stopPendingRef` state machine; the new hook's underlying pool has no signal-forwarding (RESEARCH.md Pitfall 1 — do not skip `stopAll()`).

**Ref-for-latest-value pattern** (lines 85-113): mirror this exactly for `currentFenRef`, plus new refs for `poolRef`/`queueRef`/`abortControllerRef`.

**Return shape pattern** (lines 50-63, 386-389): a plain data interface, no JSX:
```typescript
export interface StockfishEngineState {
  evalCp: number | null;
  evalMate: number | null;
  pvLines: PvLine[];
  depth: number;
  isAnalyzing: boolean;
  isReady: boolean;
}
// ...
return { evalCp, evalMate, pvLines, depth, isAnalyzing, isReady };
```
New hook's analogous return: `{ rankedLines: RankedLine[], nodesEvaluated, budgetExhausted, isSearching, isReady }` (exact shape is the planner's call, but follow this flat-data-only convention — no side effects/handlers in the return object itself).

**NEW mechanism (no direct precedent — write from RESEARCH.md Pattern 3, not from this analog):** the `onSnapshot` throttle. Do NOT copy the FEN debounce shape for this — a debounce here would delay first-paint and violate DISPLAY-01. Use the leaky-bucket throttle in RESEARCH.md Code Examples (commit immediately if `> RAPID_STEP_DEBOUNCE_MS` since last commit, else schedule exactly one trailing commit of the latest snapshot).

**Secondary hook analogs** (read this session at a glance, confirm cadence/shape only — not re-transcribed since `useStockfishEngine.ts` already contains the load-bearing patterns):
- `frontend/src/hooks/useMaiaEngine.ts` — same `RAPID_STEP_DEBOUNCE_MS` constant, ELO-ladder inference call shape (confirms `maiaQueue.policy()` call convention).
- `frontend/src/hooks/useStockfishGradingEngine.ts` — same debounce/worker-lifecycle shape gated on a second independent `enabled` boolean, useful precedent for how one page hosts two independently-toggled engine hooks side by side.

---

### `frontend/src/components/analysis/FlawChessEngineLines.tsx` (component, request-response)

**Analog:** `frontend/src/components/analysis/EngineLines.tsx` (406 lines, read in full)

**Imports pattern** (lines 21-35):
```typescript
import { useState } from 'react';
import { Chess } from 'chess.js';
import { ChevronDown } from 'lucide-react';

import type { PvLine } from '@/hooks/uciParser';
import { moveLabel } from '@/lib/moveNumberLabel';
import { cn } from '@/lib/utils';
import {
  SECOND_BEST_ARROW,
  SECOND_BEST_BADGE_TEXT,
  BEST_MOVE_ARROW,
  MOVE_HIGHLIGHT_GOOD,
} from '@/lib/theme';
import { MiniBoard } from '@/components/board/MiniBoard';
import { Tooltip } from '@/components/ui/tooltip';
```
New component swaps `PvLine` for `RankedLine`, and the theme imports for `STOCKFISH_ACCENT`/`FLAWCHESS_ENGINE_ACCENT`/`FLAWCHESS_ENGINE_HEADLINE_ACCENT` (score-pair coloring, not arrow coloring — D-06).

**Constants pattern** (lines 37-42) — copy the shape, change the values per D-08/D-07:
```typescript
const MAX_LINES = 2;     // → 3 for FlawChessEngineLines (D-08), a LOCAL constant, do not mutate the shared one
const MAX_PLIES = 5;     // → keep 5 (D-07 says mirror this exactly)
const TOOLTIP_BOARD_SIZE = 144; // reuse verbatim
```

**UCI→SAN replay helper** (lines 58-82) — `replayPvLine()`. D-07/RESEARCH.md Code Example 3 says reuse verbatim. Either import it if exported, or (if not exported) duplicate the identical function body into the new file per the UI-SPEC's allowance ("or extract it to a shared module if both components need it — Knip will flag an unused duplicate"). Check export status before duplicating:
```typescript
function replayPvLine(baseFen: string | undefined, uciMoves: string[]): PvStep[] { /* ...verbatim... */ }
```

**Score formatting pattern** (lines 160-175) — `formatScore()`, reuse verbatim per D-06, called twice per line (objective + practical, after converting practicalScore via the new `expectedScoreToWhitePovCp`):
```typescript
function formatScore(evalCp: number | null, evalMate: number | null): string {
  if (evalMate !== null) {
    if (evalMate > 0) return `#+${evalMate}`;
    if (evalMate < 0) return `#-${Math.abs(evalMate)}`;
    return '#0';
  }
  if (evalCp !== null) {
    if (evalCp >= 0) return `+${(evalCp / 100).toFixed(1)}`;
    return (evalCp / 100).toFixed(1);
  }
  return '…';
}
```

**Skeleton pattern** (lines 122-158) — `EngineLinesSkeleton`, reused component per UI-SPEC ("no new skeleton needed"); the new card just needs a taller/3-row variant — either pass a `rows` prop (extend the existing component, minimal signature change) or accept its 2-row default. Reuse `LINES_MIN_HEIGHT`/`LINES_MIN_HEIGHT_COMPACT` sizing convention (lines 104-115) but with a new min-height tuned for 3 rows.

**Row layout pattern** (`PvLineRow`, lines 219-354) — the exact structure to clone: eval badge span (aria-labeled) + flex-1 move-chip container (wrap desktop / no-wrap+scroll compact) + expand chevron pinned right. For the new component, replace the single `BADGE_CLASS` span with a two-segment badge (objective + practical, D-06):
```typescript
// Badge — was: <span className={BADGE_CLASS} style={{ backgroundColor: badgeColor, ... }}>{scoreText}</span>
// New two-number version (D-06):
<span className={BADGE_CLASS} aria-label={`Line ${lineIndex + 1}: objectively ${objectiveText}, practically ${practicalText} for you`}>
  <span style={{ color: STOCKFISH_ACCENT }}>{objectiveText}</span>
  {' / '}
  <span style={{ color: FLAWCHESS_ENGINE_HEADLINE_ACCENT }}>{practicalText}</span>
</span>
```
Move-chip mapping (lines 275-333), `data-testid` convention (`engine-line-${lineIndex}-move-${moveIndex}`) → new component uses `flawchess-line-{n}-move-{m}` per UI-SPEC's naming table; keep the identical `onClick={() => onMoveClick(moves.slice(0, moveIndex + 1))}` semantics (D-10) and the identical hover `Tooltip`+`MiniBoard` preview block (lines 306-330) verbatim.

**Top-level export shape** (lines 362-406) — `EngineLines()`:
```typescript
export function EngineLines({ pvLines, isAnalyzing, startPly = 0, baseFen, flipped = false, onMoveClick, compact = false }: EngineLinesProps) {
  const visibleLines = pvLines.slice(0, MAX_LINES);
  return (
    <div data-testid="analysis-engine-lines" aria-label="Engine lines" aria-live="polite" className={...}>
      {isAnalyzing && pvLines.length === 0 && <EngineLinesSkeleton .../>}
      {visibleLines.map((_, lineIndex) => { const line = visibleLines[lineIndex]; if (!line) return null; return <PvLineRow key={lineIndex} .../>; })}
    </div>
  );
}
```
Same shape for `FlawChessEngineLines`, props renamed to accept `rankedLines: RankedLine[]` instead of `pvLines: PvLine[]`, plus a `rootMover`/`baseFen` prop for the SAN replay + white-POV conversion. `data-testid="analysis-flawchess-card"`/`analysis-flawchess-info"` per UI-SPEC.

**noUncheckedIndexedAccess pattern** (line 388): `const line = visibleLines[lineIndex]; if (!line) return null;` — copy this narrowing exactly; do not use `!` unsafely here.

---

### `expectedScoreToWhitePovCp` (new pure utility, transform)

**Analog:** `frontend/src/lib/liveFlaw.ts`'s `evalToExpectedScore` (lines 36-51, full file read — only 63 lines)

**Forward function to invert** (lines 36-51):
```typescript
export function evalToExpectedScore(
  evalCp: number | null,
  evalMate: number | null,
  mover: MoverColor,
): number {
  const sign = mover === 'white' ? 1 : -1;
  let cp: number;
  if (evalMate != null && evalMate !== 0) {
    cp = evalMate > 0 ? MATE_CP_EQUIVALENT : -MATE_CP_EQUIVALENT;
  } else if (evalCp != null) {
    cp = evalCp;
  } else {
    return 0.5;
  }
  return 1 / (1 + Math.exp(-LICHESS_K * sign * cp));
}
```
Imports to reuse (lines 16-22):
```typescript
import { BLUNDER_DROP, MISTAKE_DROP, INACCURACY_DROP, MATE_CP_EQUIVALENT, LICHESS_K } from '@/generated/flawThresholds';
```
Type to reuse: `MoverColor = 'white' | 'black'` (line 24) and `sideToMoveFromFen()` (lines 26-29) — the new hook/component needs this to derive `rootMover` from the root FEN.

**New inverse function** (add alongside `evalToExpectedScore` in `liveFlaw.ts`, or a new co-located module — planner's call, RESEARCH.md recommends extending `liveFlaw.ts`):
```typescript
export function expectedScoreToWhitePovCp(es: number, rootMover: MoverColor): number {
  const sign = rootMover === 'white' ? 1 : -1;
  if (es <= 0) return -MATE_CP_EQUIVALENT * sign;
  if (es >= 1) return MATE_CP_EQUIVALENT * sign;
  return Math.log(es / (1 - es)) / (LICHESS_K * sign);
}
```
**Must special-case `es<=0`/`es>=1`** (Common Pitfall 2 — naive `Math.log(es/(1-es))` produces `±Infinity`/`NaN` at these exact boundaries, which `RankedLine.practicalScore` can genuinely hit on a forced-mate subtree).

**Test analog:** no direct precedent test file exists for an inverse-sigmoid; write a fresh table test asserting round-trip correctness for both `rootMover` colors and both mate boundaries (see RESEARCH.md Validation Architecture row for DISPLAY-03).

---

### `frontend/src/components/ui/switch.tsx` (new UI primitive)

**Analog:** `frontend/src/components/ui/checkbox.tsx` (31 lines, full file read) — closest existing hand-rolled Radix wrapper; no `switch.tsx` exists yet in this codebase.

**Full pattern to mirror** (checkbox.tsx, entire file):
```typescript
import * as React from "react"
import { Checkbox as CheckboxPrimitive } from "radix-ui"
import { cn } from "@/lib/utils"
import { CheckIcon } from "lucide-react"

function Checkbox({ className, ...props }: React.ComponentProps<typeof CheckboxPrimitive.Root>) {
  return (
    <CheckboxPrimitive.Root
      data-slot="checkbox"
      className={cn(
        "peer relative flex size-4 shrink-0 items-center justify-center rounded-[4px] border border-input transition-colors outline-none ... data-checked:border-primary data-checked:bg-primary data-checked:text-primary-foreground dark:data-checked:bg-primary",
        className
      )}
      {...props}
    >
      <CheckboxPrimitive.Indicator data-slot="checkbox-indicator" className="grid place-content-center text-current transition-none [&>svg]:size-3.5">
        <CheckIcon />
      </CheckboxPrimitive.Indicator>
    </CheckboxPrimitive.Root>
  )
}
export { Checkbox }
```
Adapt: import `{ Switch as SwitchPrimitive } from 'radix-ui'` (confirmed present in RESEARCH.md — `radix-ui@1.4.3`'s bundled export), use `SwitchPrimitive.Root`/`SwitchPrimitive.Thumb` instead of `Checkbox.Root`/`Indicator`, style the checked-state track color per-card via an inline `style` prop (accent color passed by the caller — Stockfish blue / Maia violet / FlawChess brown, per UI-SPEC's "switch on fill color: use each card's own accent" — do NOT hardcode a single accent in the primitive itself, accept it as a prop or `style` override from `Analysis.tsx`). Same `data-slot`/`className` merge convention (`cn(...)`), same unstyled-props passthrough (`{...props}`).

Alternative path (also compliant per UI-SPEC Registry Safety): `npx shadcn add switch` (official registry only, no vetting gate needed) — executor's choice; either satisfies the design contract.

---

### `frontend/src/pages/Analysis.tsx` (MODIFY — 3-toggle refactor + eval-bar precedence)

**Analog:** itself, existing sections.

**Toggle state pattern** (line 299):
```typescript
const [engineEnabled, setEngineEnabled] = useState(true);
```
Add two siblings: `const [maiaEnabled, setMaiaEnabled] = useState(true);` and `const [flawChessEnabled, setFlawChessEnabled] = useState(true);` (all default true per D-02/D-03).

**Card header toggle-button pattern to upgrade → Switch** (lines 1508-1529):
```typescript
<CardHeader size="compact" data-testid="analysis-engine-info" className="font-normal text-muted-foreground">
  <Button variant="ghost" size="icon" className="-ml-1 h-7 w-7 hover:bg-accent"
    onClick={() => setEngineEnabled((v) => !v)} aria-label="Toggle engine" aria-pressed={engineEnabled}
    data-testid="btn-analysis-engine-toggle">
    <Cpu className={`h-4 w-4 ${engineEnabled ? '' : 'text-muted-foreground'}`} />
  </Button>
  <span className="text-sm font-medium" style={{ color: STOCKFISH_ACCENT }}>
    {ENGINE_NAME}{engineEnabled && engine.depth > 0 ? `, Depth ${engine.depth}` : ''}
  </span>
</CardHeader>
```
Replace the `Button`+`Cpu` icon with the new `Switch` component (`data-testid="btn-analysis-engine-toggle"` reused, `aria-label="Toggle Stockfish engine"` per UI-SPEC copy table). Apply the identical `CardHeader` shape to the new FlawChess card (`data-testid="analysis-flawchess-info"`, caption styled `FLAWCHESS_ENGINE_ACCENT`, `"FlawChess Engine"` text) and retrofit the Maia card's own header analogously (per D-03, "all 3 card headers").

**Card body empty-state pattern** (lines 1537-1540) — reuse verbatim for the new card's off-state:
```typescript
<div className="flex h-full items-center px-2 text-sm text-muted-foreground">
  Engine off
</div>
```
→ `"FlawChess Engine off"` per UI-SPEC copy table.

**Card body loading/lines pattern** (lines 1534-1551) — structural template for the new `FlawChessEngineLines` card body:
```typescript
<CardBody className="min-h-[78px] p-2">
  {engineLoading ? (
    <EngineLinesSkeleton testId="analysis-engine-loading" />
  ) : !engineEnabled ? (
    <div className="flex h-full items-center px-2 text-sm text-muted-foreground">Engine off</div>
  ) : (
    <EngineLines pvLines={engine.pvLines} isAnalyzing={engine.isAnalyzing} startPly={currentPly}
      baseFen={position} flipped={boardFlipped} onMoveClick={playUciLine} />
  )}
</CardBody>
```

**Card placement (D-01):** new `Card` goes directly above `MaiaHumanPanel` inside `analysis-human-column` (desktop, ~line 1424-1436) and inside the mobile "Human" tab content (~1264-1281) — both must be updated (mobile-parity rule).

**Eval-bar left-slot precedence pattern to modify** (lines 1067-1075, currently hard-wired to Maia):
```typescript
<EvalBar evalCp={null} evalMate={null} depth={0} whiteFraction={maiaWhiteFraction}
  flipped={boardFlipped} accentColor={MAIA_ACCENT} testId="analysis-maia-eval-bar" />
```
Becomes conditional per D-04/RESEARCH.md Pattern 5:
```typescript
const fcWhiteFraction = topLine
  ? (rootMover === 'white' ? topLine.practicalScore : 1 - topLine.practicalScore)
  : 0.5;
<EvalBar
  evalCp={null} evalMate={null} depth={0}
  whiteFraction={flawChessEnabled ? fcWhiteFraction : maiaWhiteFraction}
  flipped={boardFlipped}
  accentColor={flawChessEnabled ? FLAWCHESS_ENGINE_ACCENT : MAIA_ACCENT}
  testId={flawChessEnabled ? 'analysis-flawchess-eval-bar' : 'analysis-maia-eval-bar'}
/>
```

**Right slot pattern to modify** (lines 1107-1113, currently the standalone Stockfish engine):
```typescript
<EvalBar evalCp={gameOverlay.evalCp} evalMate={gameOverlay.evalMate} depth={gameOverlay.evalDepth}
  flipped={boardFlipped} accentColor={STOCKFISH_ACCENT} />
```
Swap source while FC runs (D-04):
```typescript
<EvalBar
  evalCp={flawChessEnabled ? (topLine?.objectiveEvalCp ?? null) : gameOverlay.evalCp}
  evalMate={flawChessEnabled ? null : gameOverlay.evalMate}
  depth={flawChessEnabled ? 0 : gameOverlay.evalDepth}
  flipped={boardFlipped}
  accentColor={STOCKFISH_ACCENT}
/>
```
(Note: free-analysis mode's right bar source is `engine.evalCp`/`gameOverlay.evalCp` depending on mode — confirm exact existing variable at the boardRow call site before editing; RESEARCH.md's excerpt uses `engine.evalCp` generically, the live file uses `gameOverlay.evalCp` which already falls back to the live engine when not in game mode.)

**Bar-cap pattern** (lines 1129-1156) — `evalBarCap()`/`boardHeaderRow()` — extend the `'Maia' | 'SF'` union to include `'FC'`, add a third `evalBarSlot` call only if a 3rd physical bar existed (it doesn't per D-04 — no third bar), so this becomes a precedence-conditional swap of the LEFT cap's text/color, mirroring the eval-bar swap above:
```typescript
const evalBarCap = (text: 'Maia' | 'SF' | 'FC', color: string) => (
  <span className="whitespace-nowrap text-xs font-medium leading-none" style={{ color }}>{text}</span>
);
// left cap becomes: flawChessEnabled ? evalBarCap('FC', FLAWCHESS_ENGINE_ACCENT) : evalBarCap('Maia', MAIA_ACCENT)
```
Flag per Common Pitfall 4: existing caps use `text-xs` (not the UI-SPEC's stated `text-sm`) — match the pre-existing `text-xs` precedent for visual consistency across all three caps rather than introducing a new size.

**Discretion note wired through this file:** per UI-SPEC Component Inventory §3, the Maia switch continues gating `useMaiaEngine` AND `useStockfishGradingEngine` (both Maia-chart concerns); the Stockfish switch keeps gating `useStockfishEngine` alone; the FlawChess switch gates ONLY the new hook's pool/queue. RESEARCH.md's Open Question 1 recommends `useStockfishEngine`'s effective `enabled` input become `stockfishToggleOn && !flawChessEngineActive` to honor POOL-04's mutual-exclusion contract underneath the independent-looking switch — surface this to the planner as a confirm-before-plan item (see RESEARCH.md Assumptions A2).

---

### `frontend/src/lib/theme.ts` (MODIFY — add 2 tokens)

**Analog:** itself, lines 70/74:
```typescript
export const STOCKFISH_ACCENT = 'oklch(0.58 0.16 255)'; // blue
export const MAIA_ACCENT = 'oklch(0.58 0.20 290)'; // violet
```

**New tokens to add** (verbatim from UI-SPEC, alongside these two, same export style/comment convention):
```typescript
// FlawChess Engine source accent (Phase 155 D-05). Brand brown — third source
// accent alongside STOCKFISH_ACCENT (blue) and MAIA_ACCENT (violet). Tints the
// FlawChessEngineLines card frame + header caption + the "FC" eval-bar fill/cap.
export const FLAWCHESS_ENGINE_ACCENT = 'oklch(0.55 0.09 55)'; // brand brown, matches --brand-brown (#8B5E3C) in oklch

// Subtle gold/bronze highlight reserved for the practical-score headline number
// ONLY (Phase 155 D-05) — never a card-wide glow (fights the ~150ms live-refresh
// churn). Distinct hue from FLAWCHESS_ENGINE_ACCENT (brown, 55) so the "practical"
// number pops against its own brown-accented card without becoming another brown.
export const FLAWCHESS_ENGINE_HEADLINE_ACCENT = 'oklch(0.75 0.14 85)'; // bronze/gold
```

## Shared Patterns

### Worker/provider lifecycle gated by `enabled`
**Source:** `frontend/src/hooks/useStockfishEngine.ts` lines 235-347 (and mirrored in `useMaiaEngine.ts`/`useStockfishGradingEngine.ts`)
**Apply to:** `useFlawChessEngine.ts` — create `WorkerPool`/`MaiaQueue` instances in a `useEffect` gated on the FlawChess switch, terminate on cleanup, re-run only on `[enabled]`.

### Adaptive debounce (settled-vs-rapid)
**Source:** `frontend/src/hooks/useStockfishEngine.ts` lines 145-172
**Apply to:** `useFlawChessEngine.ts`'s FEN-navigation trigger (reuse verbatim, same `RAPID_STEP_DEBOUNCE_MS = 150` constant).

### `formatScore()` pawn-scale formatting
**Source:** `frontend/src/components/analysis/EngineLines.tsx` lines 160-175
**Apply to:** `FlawChessEngineLines.tsx`'s score-pair badge (called twice per line, once per number, per D-06) — reuse verbatim, do not reimplement.

### `noUncheckedIndexedAccess` narrowing before array index use
**Source:** `frontend/src/components/analysis/EngineLines.tsx` line 388 (`const line = visibleLines[lineIndex]; if (!line) return null;`)
**Apply to:** All new array-index access in `FlawChessEngineLines.tsx` and `useFlawChessEngine.ts` (e.g. `rankedLines[0]` for `topLine`).

### `data-testid` naming convention
**Source:** `frontend/src/components/analysis/EngineLines.tsx` (`engine-line-${lineIndex}-move-${moveIndex}`, `engine-line-${lineIndex}-expand`) and `Analysis.tsx` (`btn-analysis-engine-toggle`, `analysis-maia-eval-bar`, `analysis-engine-info`)
**Apply to:** All new interactive elements — `flawchess-line-{n}-move-{m}`, `flawchess-line-{n}-expand`, `btn-analysis-flawchess-toggle`, `analysis-flawchess-card`, `analysis-flawchess-info`, `analysis-flawchess-eval-bar` (exact names specified in UI-SPEC Component Inventory §1).

### Error/empty-state copy pattern
**Source:** `frontend/src/pages/Analysis.tsx` line 1497-1501 (`isGameMode && gameError` block) and line 1538-1540 (`Engine off`)
**Apply to:** New `"FlawChess Engine off"` (off-state) and `"FlawChess Engine unavailable. Something went wrong. Please try again in a moment."` (worker-init failure, CLAUDE.md `isError` copy template) in `FlawChessEngineLines.tsx`/`Analysis.tsx`.

### Sigmoid/threshold constants — single source of truth
**Source:** `frontend/src/generated/flawThresholds.ts` (`LICHESS_K`, `MATE_CP_EQUIVALENT`), already imported by `frontend/src/lib/liveFlaw.ts`
**Apply to:** `expectedScoreToWhitePovCp` — must import from the same generated module, never redefine `K`/mate-cp constants locally (would silently diverge from the backend-mirrored curve).

## No Analog Found

None — every file this phase touches has a strong, directly-cited analog already read in full this session. The one genuinely novel piece of logic (the inverse-sigmoid `expectedScoreToWhitePovCp`) is a straightforward algebraic inversion of an existing function in the same target file (`liveFlaw.ts`), not an unprecedented pattern.

## Metadata

**Analog search scope:** `frontend/src/hooks/`, `frontend/src/components/analysis/`, `frontend/src/components/ui/`, `frontend/src/lib/`, `frontend/src/pages/Analysis.tsx`
**Files read in full this session:** `useStockfishEngine.ts` (389 lines), `EngineLines.tsx` (406 lines), `checkbox.tsx` (31 lines), `liveFlaw.ts` (63 lines), `EvalBar.tsx` (141 lines), plus targeted non-overlapping reads of `Analysis.tsx` (lines 1050-1180, 1495-1564) and `theme.ts` (grep-targeted constant lines)
**Pattern extraction date:** 2026-07-06
