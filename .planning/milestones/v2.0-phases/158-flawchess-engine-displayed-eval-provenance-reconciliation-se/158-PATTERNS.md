# Phase 158: FlawChess Engine displayed-eval provenance reconciliation - Pattern Map

**Mapped:** 2026-07-07
**Files analyzed:** 4 (1 new, 3 modified) + test-file touch-ups
**Analogs found:** 4 / 4

This phase is a pure frontend (React + TypeScript) display-logic change. No backend, no new packages. RESEARCH.md already did an exhaustive file:line data-flow trace and named the exact target files, so this pattern map focuses on **which existing files to copy structure/conventions from**, with concrete excerpts.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `frontend/src/lib/engineEvalLookup.ts` (NEW) | utility (pure lib module) | transform (map merge/precedence) | `frontend/src/lib/flawChessVerdict.ts` + `frontend/src/lib/moveQuality.ts` | exact (same "pure, worker-free, chess.js-free-ish classification/transform module" role) |
| `frontend/src/lib/engineEvalLookup.test.ts` (NEW) | test | unit | `frontend/src/lib/__tests__/moveQuality.test.ts` | exact |
| `frontend/src/hooks/useStockfishGradingEngine.ts` (MODIFIED — candidate union, depth/movetime constants, gating) | hook | streaming (Web Worker UCI) | itself (edit in place) — constant/config changes only | n/a (modification, not new file) |
| `frontend/src/pages/Analysis.tsx` (MODIFIED — new `evalLookup` memo + reconciled `RankedLine[]`/`qualityBySan`/verdict inputs) | component (orchestration) | request-response / derived-state | itself (edit in place) — existing `qualityBySan`/`engineTopLines`/`shownSans` memos at lines 660-740 are the direct template for the new `evalLookup` memo | n/a (modification, not new file) |
| `frontend/src/hooks/__tests__/useStockfishGradingEngine.test.ts` (MODIFIED — updated depth/movetime/gating assertions) | test | unit | itself (edit in place) | n/a |
| `frontend/src/pages/__tests__/Analysis.test.tsx` (MODIFIED — gating + reconciled-wiring assertions) | test | integration | itself (edit in place) | n/a |

Note: `FlawChessEngineLines.tsx`, `flawChessVerdict.ts`, `FlawChessAgreementVerdict.tsx`, `moveQuality.ts`, `MovesByRatingChart.tsx`, `MaiaMoveQualityBar.tsx`, `positionVerdict.ts` are **explicitly NOT modified** (RESEARCH.md: "no signature change... stays green untouched") — reconciliation happens entirely upstream of them, inside the new `evalLookup` memo and the reconciled values `Analysis.tsx` now feeds in. Do not touch these files' internals.

## Pattern Assignments

### `frontend/src/lib/engineEvalLookup.ts` (utility, transform)

**Analog:** `frontend/src/lib/flawChessVerdict.ts` (structure/docstring convention) + `frontend/src/lib/moveQuality.ts` (`MoveGrade` type reuse)

**Docstring/header convention** (`flawChessVerdict.ts` lines 1-19):
```typescript
/**
 * flawChessVerdict — pure, worker-free, chess.js-free classification module for
 * the FlawChess-vs-Stockfish agreement verdict on the `/analysis` page (Phase
 * 157, REVIEW-02). Compares FlawChess's practical #1 pick
 * (`flawChessEngine.rankedLines[0]`) against Stockfish's objective #1 pick
 * (`engine.pvLines[0]`) and classifies the pair into one of three tiers:
 *   ...
 * Reuses evalToExpectedScore's Lichess winning-chances sigmoid (@/lib/liveFlaw) rather
 * than re-deriving it, and BLUNDER_DROP (@/generated/flawThresholds) as the
 * sharp/safe threshold rather than a fresh hand-picked constant.
 */

import type { RankedLine } from '@/lib/engine/types';
import type { PvLine } from '@/hooks/uciParser';
import { evalToExpectedScore, type MoverColor } from '@/lib/liveFlaw';
import { BLUNDER_DROP } from '@/generated/flawThresholds';
```
Copy this header shape for `engineEvalLookup.ts`: state the phase (158), what problem it solves, which existing helper it reuses (`sanToUci` from `@/lib/sanToSquares`) rather than re-deriving, and explicitly call out what it does NOT do (no tier math, no sigmoid — see RESEARCH's "Don't Hand-Roll" table).

**Imports pattern** — reuse existing exports, do not reimplement:
```typescript
import { sanToUci } from '@/lib/sanToSquares';       // sanToSquares.ts:63 — export function sanToUci(fen: string, san: string): string | null
import type { PvLine } from '@/hooks/uciParser';
import type { MoveGrade } from '@/lib/moveQuality';  // moveQuality.ts:33-37 — { evalCp: number | null; evalMate: number | null; depth: number }
```

**Core transform pattern** (map-merge with precedence) — modeled on `classifyMoveQuality`'s existing style of iterating an input map and building a new output map (`moveQuality.ts` classify loop) combined with the null-propagation convention already used throughout `flawChessVerdict.ts` ("Returns `null` whenever either side's objective eval hasn't arrived yet — never a bogus value from a partial snapshot"):
```typescript
export function buildEvalLookup(
  pvLines: PvLine[],
  gradeMapBySan: Map<string, MoveGrade>,
  baseFen: string,
): Map<string, MoveGrade> {
  const lookup = new Map<string, MoveGrade>();
  // Free run wins (precedence: free run first, grading run second — CONTEXT.md LOCKED).
  for (const line of pvLines) {
    const uci = line.moves[0];
    if (uci !== undefined && !lookup.has(uci)) {
      lookup.set(uci, { evalCp: line.evalCp, evalMate: line.evalMate, depth: line.depth });
    }
  }
  for (const [san, grade] of gradeMapBySan) {
    const uci = sanToUci(baseFen, san);
    if (uci !== null && !lookup.has(uci)) lookup.set(uci, grade);
  }
  return lookup;
}

export function getBySan(lookup: Map<string, MoveGrade>, baseFen: string, san: string): MoveGrade | null {
  const uci = sanToUci(baseFen, san);
  return uci === null ? null : (lookup.get(uci) ?? null);
}
```

**Error handling pattern:** None needed beyond what `sanToUci` already provides — it swallows chess.js exceptions internally and returns `null` (see `sanToSquares.ts` docstring lines 8-16: "chess.js v1.x throws on illegal moves and on malformed FENs. We swallow everything and return `null` so callers can simply fall back... without try/catch boilerplate"). `engineEvalLookup.ts` should NOT add its own try/catch around `sanToUci` calls — follow the same "caller doesn't need to guard" convention.

**Do NOT** re-derive white-POV sign normalization or sigmoid/expected-score math here (RESEARCH.md "Don't Hand-Roll" table) — both `pvLines` and `gradeMapBySan` are already white-POV-normalized by their source hooks before this module ever sees them.

---

### `frontend/src/lib/engineEvalLookup.test.ts` (test, unit)

**Analog:** `frontend/src/lib/__tests__/moveQuality.test.ts`

**Header/structure convention** (`moveQuality.test.ts` lines 1-13):
```typescript
/**
 * moveQuality unit tests — pure, deterministic (no engine/worker involved).
 *
 * Covers every <behavior> bullet from 151.1-02-PLAN.md Task 1:
 * - classifyMoveQuality: empty map, single entry, and the 5-bucket boundary
 *   behavior ...
 */

import { describe, it, expect } from 'vitest';
import { evalToExpectedScore, type MoverColor } from '@/lib/liveFlaw';
import { LICHESS_K } from '@/generated/flawThresholds';
import type { MoveCurvePoint } from '@/hooks/useMaiaEngine';
import {
  classifyMoveQuality,
  selectCandidatesByMass,
  ...
} from '../moveQuality';
```
For `engineEvalLookup.test.ts`, reference the 158-PLAN.md task instead, import from `../engineEvalLookup`, and hand-build `PvLine[]`/`Map<string, MoveGrade>` fixtures the same way `flawChessVerdict.test.ts` hand-builds `RankedLine`/`PvLine` fixtures (no jsdom, no worker mocking needed — pure function tests). Cover, per RESEARCH.md's Phase Requirements → Test Map: (1) UCI present in both sources resolves to free-run value, (2) UCI present only in `gradeMap` resolves via `sanToUci` conversion, (3) UCI in neither resolves to `null`/`null` (no third pool-grade parameter exists — structural exclusion).

---

### `frontend/src/hooks/useStockfishGradingEngine.ts` (hook, streaming — MODIFIED)

**Analog:** itself; the sibling `frontend/src/hooks/useStockfishEngine.ts` is the pattern source for the movetime-only-cap convention if `GRADING_TARGET_DEPTH` is dropped.

**Constants block to edit** (current, lines ~36-40):
```typescript
/** Grading search depth target — conservative start per RESEARCH Open Question 1. */
const GRADING_TARGET_DEPTH = 14;
```
Per CONTEXT.md's Open Measurement requirement, these constants must be re-derived from the headless Node WASM measurement (see RESEARCH.md "Open Measurement" section) before editing — do not guess new numbers. If the measurement recommends dropping the depth cap in favor of a pure movetime/nodes cap, mirror `useStockfishEngine.ts`'s own convention (no `depth` clause in its `go` command — confirmed by RESEARCH.md Pitfall 3).

**Candidate-set union pattern** — extend the existing `candidatesKey`-stable-primitive-dependency convention already in the hook (`useStockfishGradingEngine.ts:178` per RESEARCH.md) rather than passing a raw array; build the union `[...shownSans, ...flawChessDisplayedMoves].sort()` at the `Analysis.tsx` call site (RESEARCH.md Pitfall 4) so the existing debounce short-circuit absorbs no-op re-triggers.

**Gating pattern** — current code pairs `fen`/`enabled` on the same condition (`Analysis.tsx:719-721` today: both conditioned on `maiaEnabled`). Replicate that pairing exactly with the OR'd condition (RESEARCH.md Pitfall 5):
```typescript
const gradingEnabled = maiaEnabled || flawChessEnabled;
const grading = useStockfishGradingEngine({
  fen: gradingEnabled ? position : null,
  candidateSans: unionSans,
  enabled: gradingEnabled,
});
```

---

### `frontend/src/pages/Analysis.tsx` (component, orchestration — MODIFIED)

**Analog:** itself — the existing `bestSan` / `engineTopLines` / `shownSans` / `grading` / `qualityBySan` memo chain (lines 660-740) is the direct structural template for the new `evalLookup` memo and its downstream reconciled values.

**Existing memo-chain pattern to extend** (`Analysis.tsx` lines 668-740, verbatim as read):
```typescript
const bestSan = useMemo(() => { ... }, [position, engineEnabled, engine.pvLines, flawChessEnabled, flawChessEngine.rankedLines]);

const engineTopLines = useMemo<EngineLine[]>(() => { ... }, [position, engineEnabled, engine.pvLines, flawChessEnabled, flawChessEngine.rankedLines]);

const shownSans = useMemo(
  () => selectCandidatesByMass(maia.perElo, selectedElo, playedSan, bestSan),
  [maia.perElo, selectedElo, playedSan, bestSan],
);

const grading = useStockfishGradingEngine({
  fen: maiaEnabled ? position : null,
  candidateSans: shownSans,
  enabled: maiaEnabled,
});

const qualityBySan = useMemo<Map<string, MoveQualityEval>>(() => {
  const infoBySan = classifyMoveQuality(grading.gradeMap, sideToMoveFromFen(position), bestSan);
  const merged = new Map<string, MoveQualityEval>();
  for (const [san, info] of infoBySan) {
    const grade = grading.gradeMap.get(san);
    merged.set(san, {
      quality: info.quality,
      evalCp: grade?.evalCp ?? null,
      evalMate: grade?.evalMate ?? null,
    });
  }
  return merged;
}, [grading.gradeMap, position, bestSan]);
```
**New memo to insert** in this same chain, right after `grading` is available and before `qualityBySan` reads it:
```typescript
const evalLookup = useMemo(
  () => buildEvalLookup(engine.pvLines, grading.gradeMap, position),
  [engine.pvLines, grading.gradeMap, position],
);
```
Then rewrite `qualityBySan` to source from `evalLookup` (via `getBySan`) instead of `grading.gradeMap` directly, and add a new `reconciledRankedLines` memo (mapping `flawChessEngine.rankedLines.slice(0, MAX_LINES_DISPLAYED)` to new objects with `objectiveEvalCp` replaced by the lookup result — Pattern 2 in RESEARCH.md, never mutate the original `RankedLine` objects since `RankedLine` is a frozen Phase 153 type). Thread `reconciledRankedLines` everywhere `flawChessEngine.rankedLines` is currently passed to `FlawChessEngineLines`, `flawChessVerdict.ts`'s `flawChessLine` arg, and `FlawChessAgreementVerdict`'s `flawChessRankedLines` prop (verdict's `stockfishLine` prop stays `engine.pvLines[0]`, per existing D-01 convention at `Analysis.tsx:1524` — RESEARCH.md confirms this is unchanged, both sides just resolve through the same `evalLookup`).

**Naming convention:** camelCase memo names matching the existing sibling set (`bestSan`, `shownSans`, `qualityBySan`, `engineTopLines`) — use `evalLookup`, `reconciledRankedLines`.

---

## Shared Patterns

### Pure-lib-module docstring convention
**Source:** `frontend/src/lib/flawChessVerdict.ts` lines 1-19, `frontend/src/lib/moveQuality.ts` lines 1-22
**Apply to:** `engineEvalLookup.ts`
Every pure lib module in this codebase opens with a docstring stating: (1) what phase/plan introduced it, (2) what it does NOT do and which existing helper it reuses instead of re-deriving (sigmoid math, sign normalization, chess.js parsing), (3) any load-bearing caveat inherited from a prior phase's spike (e.g. Pitfall 2's "multipv is an eval rank, not a stable move identity" — already documented near-verbatim in `useStockfishGradingEngine.ts` lines 17-20 and must be repeated in `engineEvalLookup.ts` since it consumes that same grade map).

### Never fall back to the MCTS pool grade
**Source:** RESEARCH.md Anti-Patterns section + CONTEXT.md LOCKED decision
**Apply to:** `engineEvalLookup.ts`, `Analysis.tsx`'s reconciled memos
Structurally enforced by `buildEvalLookup`'s signature taking only `(pvLines, gradeMapBySan, baseFen)` — no pool-grade parameter exists at all, so there is no code path that could accidentally read `objectiveEvalCp` from `flawChessEngine.rankedLines` directly for display. An unresolved lookup entry must render as the existing `formatScore(null, null) → '…'` placeholder (`EngineLines.tsx:179-193`), not a stale/fallback number.

### `RankedLine` is frozen — build parallel objects, never mutate or extend
**Source:** `frontend/src/lib/engine/types.ts` (Phase 153 freeze comment, cited in RESEARCH.md Pitfall 6)
**Apply to:** `Analysis.tsx`'s `reconciledRankedLines` memo
```typescript
// Pattern: new array of RankedLine-shaped objects, only objectiveEvalCp swapped.
const reconciledRankedLines = flawChessEngine.rankedLines.slice(0, MAX_LINES_DISPLAYED).map((line) => ({
  ...line,
  objectiveEvalCp: getByUci(evalLookup, line.rootMove) ?? null,
}));
```

### Test fixture convention: hand-built shapes, no mocking of pure functions
**Source:** `frontend/src/lib/flawChessVerdict.test.ts`, `frontend/src/lib/__tests__/moveQuality.test.ts`, `frontend/src/components/analysis/__tests__/FlawChessAgreementVerdict.test.tsx`
**Apply to:** `engineEvalLookup.test.ts`
All pure-lib tests in this codebase hand-construct `RankedLine`/`PvLine`/`Map<string, MoveGrade>` fixtures directly (no factory library, no worker/engine mocking) since these are pure functions. Follow this exactly for `engineEvalLookup.test.ts`.

## No Analog Found

None — every file in scope has a direct structural analog already in the codebase (this phase deliberately reuses existing shapes/contracts per CONTEXT.md's "Claude's Discretion... pick the seam that keeps functions small").

## Metadata

**Analog search scope:** `frontend/src/lib/`, `frontend/src/hooks/`, `frontend/src/pages/Analysis.tsx`, associated `__tests__/` directories — all files RESEARCH.md already identified as touchpoints via direct code reads on 2026-07-07.
**Files scanned:** `flawChessVerdict.ts`, `moveQuality.ts`, `sanToSquares.ts`, `useStockfishGradingEngine.ts`, `Analysis.tsx` (lines 660-745), `moveQuality.test.ts`.
**Pattern extraction date:** 2026-07-07
