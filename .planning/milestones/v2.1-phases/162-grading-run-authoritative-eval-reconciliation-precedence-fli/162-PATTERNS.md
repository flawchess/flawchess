# Phase 162: Grading-run-authoritative eval reconciliation — Pattern Map

**Mapped:** 2026-07-10
**Files analyzed:** 6 (all existing — this phase is a precedence-flip/wiring change, no brand-new files expected except possibly one new pure helper)
**Analogs found:** 6 / 6 (every touched file is its own best analog — the mechanism to copy already lives in the file being changed; secondary analogs are the sibling files that share the same shape)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `frontend/src/lib/engineEvalLookup.ts` (`buildEvalLookup` precedence flip) | utility (pure lib) | transform (merge two Maps) | itself (in-place loop reorder) — secondary analog `moveQuality.ts`'s `classifyMoveQuality` argmax loop | exact |
| `frontend/src/lib/engineEvalLookup.ts` (NEW `resolveReconciledBest` helper, if added here per Claude's Discretion) | utility (pure lib) | transform (argmax over a Map) | `moveQuality.ts:78-94` (`classifyMoveQuality`'s internal top-scorer + designated-pin loop) | exact — same argmax+tie-break shape, different key type (UCI vs SAN) |
| `frontend/src/pages/Analysis.tsx` (`unionSans` memo, ~796-800) | component (memo/derived state) | transform (dedup+sort union) | itself — same file's `flawChessDisplayedSans`/`shownSans` memos immediately above (781-789) | exact |
| `frontend/src/pages/Analysis.tsx` (`qualityBySan` pin argument, ~861-882) | component (memo/derived state) | transform | itself — no plumbing change, only the 3rd-arg value passed to `classifyMoveQuality` | exact |
| `frontend/src/pages/Analysis.tsx` (`engineArrows` memo, ~1275-1306; D-07) | component (memo → board overlay) | transform (Map lookup → arrow descriptor) | itself — the FC-arrow branch (1277-1290) already reads from `flawChessEngine.rankedLines`, a reconciled-shaped source; SF branch needs to switch from `engine.pvLines[i]` to a reconciled UCI | role-match |
| `frontend/src/pages/Analysis.tsx` (`FlawChessAgreementVerdict` `stockfishLine` prop, ~1881; D-13) | component (prop wiring) | transform (construct a `PvLine`-shaped object from lookup data) | `reconciledRankedLines` memo (840-851) — the exact pattern of "take a rootMove UCI, resolve it through `evalLookup`, spread into a display object" already exists for the FC side | exact |
| `frontend/src/hooks/useGameOverlay.ts` (`enginePassthrough` eval fields, 178-186 / params 100-102; D-08) | hook (derived overlay state) | transform (passthrough → should read a caller-computed reconciled value) | itself — the hook already has the exact `usePrecomputedEval ? evalPt.X : engineEvalCp` pattern (313-324) for the on-main-line case; the off-main-line passthrough just needs its 3 params (`engineEvalCp`/`engineEvalMate`/`engineDepth`) to be fed the reconciled-best value from the caller instead of raw `engine.evalCp/evalMate/depth` | exact (no hook-internal change — caller-side wiring change in `Analysis.tsx`) |
| `frontend/src/lib/engineEvalLookup.test.ts` (invert precedence assertions + new `resolveReconciledBest` tests) | test | unit | itself | exact |
| `frontend/src/lib/__tests__/moveQuality.test.ts` (mirror-image Best-label case) | test | unit | itself — existing `classifyMoveQuality` describe blocks (designated-pin behavior) | exact |
| `frontend/src/pages/__tests__/Analysis.test.tsx` (extend "Grading run gating" + "Reconciled eval provenance") | test | integration | itself | exact |
| `frontend/src/hooks/__tests__/useGameOverlay.test.ts` (verify/extend `enginePassthrough` coverage) | test | unit | itself | exact |

## Pattern Assignments

### `frontend/src/lib/engineEvalLookup.ts` — `buildEvalLookup` precedence flip (D-01)

**Analog:** itself (`engineEvalLookup.ts:40-60`), read in full above.

**Current (free-run-first) — to invert:**
```typescript
// frontend/src/lib/engineEvalLookup.ts:40-60
export function buildEvalLookup(
  pvLines: PvLine[],
  gradeMapBySan: Map<string, MoveGrade>,
  baseFen: string,
): Map<string, MoveGrade> {
  const lookup = new Map<string, MoveGrade>();

  for (const line of pvLines) {                    // free run inserted FIRST
    const uci = line.moves[0];
    if (uci === undefined || lookup.has(uci)) continue;
    lookup.set(uci, { evalCp: line.evalCp, evalMate: line.evalMate, depth: line.depth });
  }

  for (const [san, grade] of gradeMapBySan) {       // grading run fills GAPS only
    const uci = sanToUci(baseFen, san);
    if (uci === null || lookup.has(uci)) continue;
    lookup.set(uci, grade);
  }

  return lookup;
}
```

**Pattern to apply:** swap loop order only — grading loop first (unconditional insert since the map starts empty), free-run loop second guarded by the SAME `!lookup.has(uci)` idiom so a grading entry is never overwritten. No new logic, no new guard shape — the `!lookup.has()` insertion-order-wins idiom is the load-bearing pattern here and must be preserved verbatim, just reordered. Also rewrite the module docstring (lines 1-23) — it states free-run-first as LOCKED in three places; cite SEED-090/Phase 162 instead.

**Imports pattern** (lines 25-27) — no change needed, already imports `sanToUci`, `PvLine`, `MoveGrade`:
```typescript
import { sanToUci } from '@/lib/sanToSquares';
import type { PvLine } from '@/hooks/uciParser';
import type { MoveGrade } from '@/lib/moveQuality';
```

**Error handling pattern:** none needed — both loops already silently `continue` on unresolvable/duplicate keys (`uci === undefined`, `uci === null`, `lookup.has(uci)`). This is the project's established "skip, never throw" convention for pure transform functions in this file; preserve it exactly when reordering.

---

### `frontend/src/lib/engineEvalLookup.ts` (or `moveQuality.ts`) — NEW `resolveReconciledBest` helper (D-03 argmax, feeds D-07/D-08/D-13)

**Analog:** `frontend/src/lib/moveQuality.ts:73-94` (`classifyMoveQuality`'s internal argmax + designated-pin logic) — this is the closest existing shape in the codebase for "loop a Map, compute expected score via `evalToExpectedScore`, track a running best, optionally honor a designated/tie-break pin."

**Core pattern to copy** (`moveQuality.ts:78-94`):
```typescript
const scores = new Map<string, number>();
let topSan: string | null = null;
let topEs = -Infinity;
for (const [san, grade] of gradeMap) {
  const es = evalToExpectedScore(grade.evalCp, grade.evalMate, mover);
  scores.set(san, es);
  if (es > topEs) {
    topEs = es;
    topSan = san;
  }
}

// Prefer the primary engine's best move as the reference; fall back to this
// pass's own top scorer until it's available/graded.
const useDesignated = designatedBestSan != null && scores.has(designatedBestSan);
const bestSan = useDesignated ? designatedBestSan : topSan;
const bestEs = useDesignated ? scores.get(designatedBestSan)! : topEs;
```

**Adaptation for the new helper (per RESEARCH's suggested signature, `engineEvalLookup.ts` is the natural home — co-located with `buildEvalLookup`, already imports `MoveGrade`):**
```typescript
export function resolveReconciledBest(
  evalLookup: Map<string, MoveGrade>,
  candidateUcis: string[],
  mover: MoverColor,
  tieBreakUci: string | null,
): string | null {
  let bestUci: string | null = null;
  let bestEs = -Infinity;
  for (const uci of candidateUcis) {
    const grade = evalLookup.get(uci);
    if (!grade) continue;
    const es = evalToExpectedScore(grade.evalCp, grade.evalMate, mover);
    if (es > bestEs) {
      bestEs = es;
      bestUci = uci;
    } else if (es === bestEs && uci === tieBreakUci) {
      bestUci = uci;
    }
  }
  return bestUci;
}
```
Note the key difference from `classifyMoveQuality`'s pattern: `resolveReconciledBest` operates on UCI keys (needed for the arrow/verdict, which are UCI-based) and only returns the winning UCI, not a full classification map — `classifyMoveQuality` itself needs NO internal change; only its caller's 3rd-arg value changes (see next section). Reuse `evalToExpectedScore` from `@/lib/liveFlaw` — do not re-derive the sigmoid (Don't Hand-Roll table in RESEARCH.md).

**Imports needed:**
```typescript
import { evalToExpectedScore, type MoverColor } from '@/lib/liveFlaw';
```

---

### `frontend/src/pages/Analysis.tsx` — `unionSans` extension (D-02/D-09)

**Analog:** the same file's `shownSans`/`flawChessDisplayedSans` memos immediately preceding it (lines 763-789) — same "compute a SAN array from an engine source, gate on that source's enabled flag" shape.

**Current union memo** (`Analysis.tsx:796-800`):
```typescript
const unionSans = useMemo(() => {
  const maiaSans = maiaEnabled ? shownSans : [];
  const fcSans = flawChessEnabled ? flawChessDisplayedSans : [];
  return Array.from(new Set([...maiaSans, ...fcSans])).sort();
}, [maiaEnabled, shownSans, flawChessEnabled, flawChessDisplayedSans]);
```

**Pattern to apply:** add a third contributor array gated on the free-run-committed signal (D-09), computed inline per RESEARCH's confirmed no-hook-change signal:
```typescript
const freeRunCommitted = engine.pvLines.length > 0 && !engine.isAnalyzing;
```
then extend the `Set` union with `freeRunCommitted ? [line0San, line1San] : []`, converting `engine.pvLines[0..1].moves[0]` to SAN via the existing `bestSanFromPv(position, uci)` helper already used at line 755. Preserve the existing sort+dedup exactly (`Array.from(new Set([...])).sort()` — D-02 explicitly says "keep the existing sort+dedup").

---

### `frontend/src/pages/Analysis.tsx` — `qualityBySan` pin argument (D-03)

**Analog:** itself, no plumbing change — only the value passed to `classifyMoveQuality`'s 3rd parameter.

**Current** (`Analysis.tsx:869-871`):
```typescript
// Pass the primary engine's bestSan so the chart's "best" agrees with the
// eval bar + engine card (151.1 UAT: reconcile the two Stockfish sources).
const infoBySan = classifyMoveQuality(reconciledGradeMap, sideToMoveFromFen(position), bestSan);
```

**Pattern to apply:** replace `bestSan` with the SAN form of `resolveReconciledBest(evalLookup, Array.from(reconciledGradeMap.keys())... )` — actually per Pitfall 3, the candidate keyspace must be `grading.gradeMap.keys()` (the SAME keyspace `qualityBySan` already iterates at line 863), converted to UCI, not the broader `unionSans`. Convert the winning UCI back to SAN via `bestSanFromPv(position, uci)` (same helper used elsewhere in this file) before passing to `classifyMoveQuality`. Update the comment to cite D-03/Phase 162 instead of "the primary engine's bestSan."

---

### `frontend/src/pages/Analysis.tsx` — `engineArrows` SF branch (D-07)

**Analog:** the FC-arrow branch in the same memo (`Analysis.tsx:1277-1290`), and `reconciledRankedLines` (840-851) for the "resolve a rootMove UCI through the lookup" step.

**Current SF branch** (`Analysis.tsx:1291-1303`):
```typescript
if (engineEnabled) {
  for (let i = 0; i < ARROW_COUNT; i++) {
    const sfSquares = uciToSquares(engine.pvLines[i]?.moves[0] ?? null);
    if (sfSquares) {
      arrows.push({
        startSquare: sfSquares.from,
        endSquare: sfSquares.to,
        color: BEST_MOVE_ARROW,
        width: STOCKFISH_ENGINE_ARROW_WIDTH,
        layerKey: `sf-${i}`,
      });
    }
  }
}
```
Since `ARROW_COUNT = 1` (line 161), this loop only ever runs once (`i=0`) — per RESEARCH Open Question 3, this is a straightforward single-value substitution, not a loop restructure. Swap `engine.pvLines[i]?.moves[0]` for the resolved-reconciled-best UCI (D-12: true global argmax over the full reconciled map, computed via `resolveReconciledBest`). Add `resolveReconciledBest`'s result to this memo's dependency array.

---

### `frontend/src/pages/Analysis.tsx` — `FlawChessAgreementVerdict` `stockfishLine` prop (D-13, Pitfall 1)

**Analog:** `reconciledRankedLines` memo (`Analysis.tsx:840-851`) — the exact "resolve a rootMove UCI through `evalLookup`, spread into a display-shaped object" pattern already used for the FC card side.

**Current (bypasses the lookup — Pitfall 1):**
```typescript
// Analysis.tsx:1881
stockfishLine={engine.pvLines[0] ?? null}
```

**Pattern to apply** — construct a `PvLine`-shaped object from the reconciled-best UCI + its `evalLookup` eval, mirroring `reconciledRankedLines`'s shape-preserving spread:
```typescript
// reconciledRankedLines pattern (840-851) to mirror:
const reconciledRankedLines = useMemo<RankedLine[]>(
  () =>
    flawChessEngine.rankedLines.slice(0, FC_MAX_LINES).map((line) => {
      const resolved = getByUci(evalLookup, line.rootMove);
      return {
        ...line,
        objectiveEvalCp: resolved?.evalCp ?? null,
        objectiveEvalMate: resolved?.evalMate ?? null,
      };
    }),
  [flawChessEngine.rankedLines, evalLookup],
);
```
New memo for the verdict's SF side: resolve `resolveReconciledBest(...)`'s winning UCI through `getByUci(evalLookup, uci)`, then build a minimal `PvLine`-shaped object (`{ multipv: 1, depth, moves: [uci], evalCp, evalMate }`) — matching the `pvLine()` test fixture shape in `engineEvalLookup.test.ts:21-23` for what fields `PvLine` needs. This is a NEW small memo, not a growth of an existing one (project's function-size convention — many small `useMemo` blocks, per RESEARCH's Project Constraints).

---

### `frontend/src/hooks/useGameOverlay.ts` — `enginePassthrough` (D-08, Pitfall 1)

**Analog:** itself — the hook's own on-main-line precomputed-vs-engine pattern (lines 313-324) already establishes the exact shape needed; only the off-main-line passthrough's SOURCE values change (caller-side), not the hook's internal logic.

**Current off-main-line passthrough** (`useGameOverlay.ts:178-186`):
```typescript
const enginePassthrough: GameOverlay = {
  boardArrows: undefined,
  squareMarkers: [],
  lastMoveHighlightColor: undefined,
  evalCp: engineEvalCp,
  evalMate: engineEvalMate,
  evalDepth: engineDepth,
  usingPrecomputed: false,
};
```
`engineEvalCp`/`engineEvalMate`/`engineDepth` are hook PARAMS (`UseGameOverlayParams`, lines 100-102) — the hook itself needs **zero internal changes**. The fix per Pitfall 1's recommendation is entirely at the CALL SITE in `Analysis.tsx`: whatever it currently passes as `engineEvalCp`/`engineEvalMate`/`engineDepth` into `useGameOverlay(...)` must become the reconciled-best-derived eval (the SAME value D-08 computes once for the eval bar/headline), not raw `engine.evalCp`/`engine.evalMate`/`engine.depth`. Grep the current call site (`useGameOverlay({...})` invocation in `Analysis.tsx`) during planning to find the exact param-passing lines to change.

**On-main-line pattern already established** (mirror this shape for the D-08 "refines once" behavior at the caller):
```typescript
// useGameOverlay.ts:313-324
const evalPt = hasPly ? maps.evalByPly.get(k) : undefined;
const usePrecomputedEval =
  evalPt != null && (evalPt.eval_cp != null || evalPt.eval_mate != null);

return {
  ...
  evalCp: usePrecomputedEval ? evalPt.eval_cp : engineEvalCp,
  evalMate: usePrecomputedEval ? evalPt.eval_mate : engineEvalMate,
  evalDepth: usePrecomputedEval ? PRECOMPUTED_EVAL_DEPTH : engineDepth,
  usingPrecomputed: usePrecomputedEval,
};
```

---

## Shared Patterns

### "Skip silently, never throw" for unresolvable SAN/UCI conversions
**Source:** `engineEvalLookup.ts:47-57` (`if (uci === undefined || lookup.has(uci)) continue;` / `if (uci === null || lookup.has(uci)) continue;`)
**Apply to:** `resolveReconciledBest`, the `unionSans` D-09 extension, and the verdict's new `PvLine` construction — any new code converting SAN↔UCI or looking up a possibly-absent Map key must `continue`/return `null`, never throw. This is a hard project convention already enforced by `getBySan`/`getByUci`'s own docstrings ("Never `undefined`... never a throw").

### Argmax-with-tie-break — ONE canonical resolution, threaded everywhere
**Source:** `moveQuality.ts:78-94` (`classifyMoveQuality`'s designated-pin pattern) is the template; RESEARCH's Anti-Patterns section explicitly forbids re-deriving this independently at each display site (arrow, label, bar, verdict).
**Apply to:** every D-07/D-08/D-13 consumer must call the SAME `resolveReconciledBest(...)` result (or a value derived from it), not re-run its own loop over `evalLookup`/`unionSans`. Compute it once as a new `useMemo` in `Analysis.tsx`, thread the resulting UCI (and its resolved SAN via `bestSanFromPv`) as a parameter into `engineArrows`, the verdict's new SF-side memo, the eval-bar/headline value, and `qualityBySan`'s pin argument.

### `evalToExpectedScore` — the ONLY sigmoid implementation
**Source:** `@/lib/liveFlaw.ts`, already imported by `moveQuality.ts:25`.
**Apply to:** `resolveReconciledBest` and any new argmax logic — never re-derive the Lichess-K sigmoid (project's Don't-Hand-Roll rule, RESEARCH.md).

### `sanToUci`/`sanFromUci`/`bestSanFromPv` — the ONLY SAN↔UCI conversions
**Source:** `@/lib/sanToSquares` (`sanToUci`, used by `engineEvalLookup.ts:25`); `Analysis.tsx:313` local helper `bestSanFromPv(baseFen, uci)` for UCI→SAN at a given position.
**Apply to:** the `unionSans` D-09 extension (converting `engine.pvLines[0..1]`'s UCI to SAN) and the verdict's SF-side memo (if it needs a SAN, though the verdict's `PvLine` shape is UCI-based per `moves: [uci]`) — never write a second conversion.

### Small, single-purpose `useMemo` blocks (function-size convention)
**Source:** `Analysis.tsx`'s existing pattern throughout 740-900 — `bestSan`, `shownSans`, `rawProbBySan`, `flawChessDisplayedSans`, `unionSans`, `evalLookup`, `reconciledRankedLines`, `qualityBySan` are each their own small memo with a comment block explaining provenance/phase.
**Apply to:** the new `resolveReconciledBest`-derived value and the verdict's new `stockfishLine` construction — each should be its own new `useMemo`, not folded into an existing one, per CLAUDE.md's nesting/LOC limits and RESEARCH's explicit note that `Analysis.tsx` is already 2321 lines and new logic should follow the "new small memo" pattern, not grow an existing block.

## No Analog Found

None — every file this phase touches already exists with an in-file or same-file analog covering the exact shape needed. No genuinely new module is required; `resolveReconciledBest` is the only new exported function, and its closest analog (`classifyMoveQuality`'s internal loop) is a near-exact structural match.

## Metadata

**Analog search scope:** `frontend/src/lib/`, `frontend/src/pages/Analysis.tsx`, `frontend/src/hooks/useGameOverlay.ts`, `frontend/src/hooks/useStockfishEngine.ts`, `frontend/src/hooks/useStockfishGradingEngine.ts`, and their `__tests__`/co-located test files.
**Files scanned (read in full or targeted sections):** `engineEvalLookup.ts`, `engineEvalLookup.test.ts`, `moveQuality.ts`, `useGameOverlay.ts`, `Analysis.tsx` (lines 740-900, 1270-1325, plus grep of all `bestSan`/`unionSans`/`evalLookup`/`engineArrows`/`stockfishLine` occurrences).
**Pattern extraction date:** 2026-07-10
