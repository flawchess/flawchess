# Phase 153: Pure Search Core (Guardrail + Backup + MCTS + Fallback) - Pattern Map

**Mapped:** 2026-07-05
**Files analyzed:** 12 (7 source + 5 test files, all net-new under `frontend/src/lib/engine/`)
**Analogs found:** 12 / 12 (all role-match or exact; no backend/router/component files in this phase)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `frontend/src/lib/engine/types.ts` | model (type-only) | transform | `frontend/src/lib/moveQuality.ts` (lines 28-51) | exact — same "types + constants at top of a pure lib file" shape |
| `frontend/src/lib/engine/guardrail.ts` | utility (interface-only) | request-response | `frontend/src/hooks/useStockfishGradingEngine.ts` (grade contract shape, referenced in RESEARCH) | role-match — defines the callable contract other modules implement |
| `frontend/src/lib/engine/leafScore.ts` | utility (transform wrapper) | transform | `frontend/src/lib/liveFlaw.ts` (whole file, 63 lines) | exact — leafScore.ts is explicitly a "thin wrapper" over `evalToExpectedScore` |
| `frontend/src/lib/engine/backup.ts` | service (pure computation) | transform | `frontend/src/lib/moveQuality.ts` → `selectCandidatesByMass` (lines 129-152) | role-match — same "pure function over Record/array, no I/O" pattern |
| `frontend/src/lib/engine/select.ts` | service (pure computation) | transform | `frontend/src/lib/moveQuality.ts` → `selectCandidatesByMass` (mass-cut loop, lines 138-145) + `frontend/src/lib/maiaEncoding.ts` → `maskAndSoftmax` (lines 234-255, softmax/masking pattern) | role-match — truncation-loop pattern to mirror per D-11 |
| `frontend/src/lib/engine/mctsSearch.ts` | service (orchestrator) | event-driven (async loop + callback) | `frontend/src/hooks/useStockfishGradingEngine.ts` (batched grade orchestration, referenced) | role-match — closest orchestration precedent for a multi-call async loop over providers |
| `frontend/src/lib/engine/fallbackExpectimax.ts` | service (orchestrator, alt strategy) | transform | `frontend/src/lib/engine/mctsSearch.ts` (sibling, same `SearchRunner` contract) | exact — same interface, same backup.ts reuse, this phase's own sibling file |
| `frontend/src/lib/engine/__tests__/backup.test.ts` | test | transform | `frontend/src/lib/__tests__/moveQuality.test.ts` (lines 1-52) | exact — pure-function fixture-test style |
| `frontend/src/lib/engine/__tests__/select.test.ts` | test | transform | `frontend/src/lib/__tests__/moveQuality.test.ts` → `selectCandidatesByMass` describe block | exact |
| `frontend/src/lib/engine/__tests__/leafScore.test.ts` | test | transform | `frontend/src/lib/__tests__/moveQuality.test.ts` (uses `evalToExpectedScore`/`MoverColor` directly, lines 16, 31, 45-51) | exact |
| `frontend/src/lib/engine/__tests__/mctsSearch.test.ts` | test | event-driven | `frontend/src/lib/__tests__/moveQuality.test.ts` (fabricated-input style; no direct async-orchestration analog exists) | role-match |
| `frontend/src/lib/engine/__tests__/fallbackExpectimax.test.ts` | test | request-response | `frontend/src/lib/__tests__/moveQuality.test.ts` (fabricated-input style) | role-match |

## Pattern Assignments

### `frontend/src/lib/engine/leafScore.ts` (utility, transform)

**Analog:** `frontend/src/lib/liveFlaw.ts` (whole file — small, read in full)

**Imports pattern** (lines 15-22):
```typescript
import type { FlawSeverity } from '@/types/library';
import {
  BLUNDER_DROP,
  MISTAKE_DROP,
  INACCURACY_DROP,
  MATE_CP_EQUIVALENT,
  LICHESS_K,
} from '@/generated/flawThresholds';
```
`leafScore.ts` mirrors this shape but imports FROM `liveFlaw.ts` itself rather than the generated constants directly:
```typescript
import { evalToExpectedScore, type MoverColor } from '@/lib/liveFlaw';
import type { MoveGrade } from './types';
```

**Core wrapper pattern** (liveFlaw.ts lines 24-51, the exact function being wrapped):
```typescript
export type MoverColor = 'white' | 'black';

export function sideToMoveFromFen(fen: string): MoverColor {
  return fen.split(' ')[1] === 'b' ? 'black' : 'white';
}

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

**Critical wiring note (Pattern 3 in RESEARCH.md):** `leafScore.ts` must call `evalToExpectedScore(grade.evalCp, grade.evalMate, rootMover)` where `rootMover` is `sideToMoveFromFen(rootFen)` computed ONCE — never the leaf node's own side-to-move. This is the opposite of how `moveQuality.ts`'s `classifyMoveQuality` (line 82) calls it with the CURRENT mover per-candidate — do not copy that call-site convention here, it is correct there (single-ply classification) and wrong for the multi-ply engine core.

**No error handling / no validation needed** — pure function, no I/O, matches liveFlaw.ts's style exactly (no try/catch anywhere in the file).

---

### `frontend/src/lib/engine/select.ts` (service, transform) — truncation loop

**Analog:** `frontend/src/lib/moveQuality.ts` → `selectCandidatesByMass` (lines 129-152)

**Core mass-cut loop pattern to mirror** (lines 138-145):
```typescript
const sorted = Object.entries(rung.moveProbabilities).sort((a, b) => b[1] - a[1]);
const massSet: string[] = [];
let cumulative = 0;
for (const [san, prob] of sorted) {
  if (cumulative >= CUMULATIVE_MASS_THRESHOLD) break;
  massSet.push(san);
  cumulative += prob;
}
```
`select.ts`'s `truncateAndRenormalize` (per RESEARCH.md Pattern 4) uses the identical loop shape with a NEW independent constant `POLICY_MASS_THRESHOLD = 0.9` (D-11 — do not import `CUMULATIVE_MASS_THRESHOLD` or `CANDIDATE_HARD_CAP` from moveQuality.ts) and adds a renormalization step:
```typescript
const total = kept.reduce((sum, [, p]) => sum + p, 0);
return new Map(kept.map(([uci, p]) => [uci, total > 0 ? p / total : 0]));
```

**Constant-naming convention to mirror** (moveQuality.ts lines 47-51):
```typescript
/** Maia cumulative-probability mass cutoff at the selected ELO (D-02). */
export const CUMULATIVE_MASS_THRESHOLD = 0.95;

/** Hard cap on displayed candidate lines after the mass cut (D-06). */
export const CANDIDATE_HARD_CAP = 5;
```
Engine analog: `export const POLICY_MASS_THRESHOLD = 0.9; // D-11: separate from moveQuality.ts's 0.95` — same doc-comment style (one-line JSDoc citing the decision ID).

**Softmax/masking numerical-stability pattern** (maiaEncoding.ts `maskAndSoftmax`, lines 234-255) — reference only if `select.ts` or a fabricated test-provider needs a stable softmax:
```typescript
const max = scores.length > 0 ? Math.max(...scores) : 0;
const exps = scores.map((s) => Math.exp(s - max));
const sum = exps.reduce((a, b) => a + b, 0);
```

---

### `frontend/src/lib/engine/backup.ts` (service, transform) — pure function isolation

**Analog:** `frontend/src/lib/moveQuality.ts` (whole-file style: types/interfaces declared just above the functions that consume them, JSDoc citing decision IDs, no I/O anywhere)

**Interface-then-function pattern to mirror** (moveQuality.ts lines 34-38, adapted per RESEARCH.md Pattern 2):
```typescript
export interface MoveGrade {
  evalCp: number | null;
  evalMate: number | null;
  depth: number;
}
```
`backup.ts` follows the same "small interface directly above the pure function that consumes it" shape:
```typescript
export interface BackupChild {
  prior: number;
  value: number;
}

export function backupExpectation(children: readonly BackupChild[]): number {
  const totalPrior = children.reduce((sum, c) => sum + c.prior, 0);
  if (totalPrior === 0) return 0.5;
  return children.reduce((sum, c) => sum + (c.prior / totalPrior) * c.value, 0);
}

export function backupRootMax(children: readonly BackupChild[]): number {
  return Math.max(...children.map((c) => c.value));
}
```
No error handling needed (pure math over arrays) — matches moveQuality.ts/liveFlaw.ts convention of zero try/catch in pure-transform files. The `noUncheckedIndexedAccess` narrowing pattern to reuse (from `maiaEncoding.ts` line 243, `scores[idx] ?? Number.NEGATIVE_INFINITY`) applies wherever `backup.ts`/`select.ts` index into arrays by computed position.

---

### `frontend/src/lib/engine/__tests__/backup.test.ts`, `select.test.ts`, `leafScore.test.ts` (test, transform)

**Analog:** `frontend/src/lib/__tests__/moveQuality.test.ts` (full file header + describe-block style, lines 1-52 read directly)

**File header / import pattern to mirror** (lines 1-29):
```typescript
/**
 * moveQuality unit tests — pure, deterministic (no engine/worker involved).
 * ...
 */
import { describe, it, expect } from 'vitest';
import { evalToExpectedScore, type MoverColor } from '@/lib/liveFlaw';
import { LICHESS_K } from '@/generated/flawThresholds';
import {
  classifyMoveQuality,
  selectCandidatesByMass,
  CUMULATIVE_MASS_THRESHOLD,
  CANDIDATE_HARD_CAP,
  type MoveGrade,
} from '../moveQuality';
```
Engine test files import the same way, one level deeper: `from '../backup'`, `from '../select'`, `from '../leafScore'`, `from '../types'`.

**Fixture-helper pattern** (lines 33-51) — a small analytic helper to construct exact fixture inputs, documented as NOT a reimplementation of the code under test:
```typescript
/** A tiny straddle offset used to test threshold-boundary semantics without
 *  relying on bit-exact floating-point equality... */
const STRADDLE = 1e-6;

function cpForExpectedScore(es: number): number {
  return -Math.log(1 / es - 1) / LICHESS_K;
}

function gradeForEs(es: number): MoveGrade {
  return { evalCp: cpForExpectedScore(es), evalMate: null, depth: 12 };
}
```
`backup.test.ts`'s SC2 fixture (the 0.6/0.3/0.1-prior worked example from RESEARCH.md) should follow this exact "small pure helper + `describe`/`it` blocks asserting exact values, with an explicit negative-assertion comment" style — see RESEARCH.md's "Backup Rule: Worked Fixture" section for the literal numbers to encode as `expect(...).not.toBe(...)` negative assertions (naive-average and visit-weighted-average must NOT match).

**Assertion style** (lines 56-64):
```typescript
describe('classifyMoveQuality', () => {
  it('returns an empty map for an empty gradeMap', () => {
    const result = classifyMoveQuality(new Map(), WHITE);
    expect(result.size).toBe(0);
  });

  it('classifies a single entry as best', () => {
    const gradeMap = new Map<string, MoveGrade>([['e4', { evalCp: 0, evalMate: null, depth: 10 }]]);
    const result = classifyMoveQuality(gradeMap, WHITE);
    expect(result.get('e4')).toEqual({ quality: 'best', expectedScore: 0.5 });
  });
```

---

### `frontend/src/lib/engine/mctsSearch.ts` / `fallbackExpectimax.ts` (service, orchestrator) and their tests

**Analog:** `frontend/src/hooks/useStockfishGradingEngine.ts` (batched-grade orchestration referenced throughout RESEARCH.md — this is the "per-node primitive the core's grade() contract mirrors", per CONTEXT.md's Established Patterns). No pure-lib file in the codebase does async multi-call orchestration with a callback (`onSnapshot`); this hook is the closest precedent for the *shape* of "batched calls, pv[0]-keyed results, never multipv-rank-keyed" — the actual orchestration loop (select→expand→backup→snapshot) is new construction per RESEARCH.md's Pattern 1/5 pseudocode, not a port of existing code.

**Test analog:** `moveQuality.test.ts`'s fabricated-input style (Map literals as stand-ins for streamed data) is the closest precedent for constructing fabricated `EngineProviders` — no existing test in the codebase fabricates an async provider pair, so `mctsSearch.test.ts`/`fallbackExpectimax.test.ts` are new construction following RESEARCH.md's own "ELO Oracle Fixture" and "Guardrail Swap-in" code examples verbatim (see RESEARCH.md lines 391-441 — those ARE the pattern to copy, already written in the phase's own research doc).

---

## Shared Patterns

### Pure-function, zero-I/O module style
**Source:** `frontend/src/lib/liveFlaw.ts` (whole file) and `frontend/src/lib/moveQuality.ts` (whole file)
**Apply to:** ALL new files in `lib/engine/` except the orchestrators (`mctsSearch.ts`, `fallbackExpectimax.ts`, which are still worker/network-free but have async control flow)
- File-header JSDoc block explaining WHAT and WHY, citing decision IDs (D-01, D-02, etc.) and phase numbers
- No try/catch in pure transform functions — malformed input either throws (chess.js) or degrades gracefully (`?? fallback`, `0.5` neutral defaults)
- Constants declared with `export const NAME = value; // one-line JSDoc citing the decision`
- Types/interfaces declared immediately above the function(s) that consume them

### Reuse-not-reimplement discipline
**Source:** `frontend/src/lib/liveFlaw.ts` → `evalToExpectedScore`/`sideToMoveFromFen`
**Apply to:** `leafScore.ts` (must import, not reimplement, per ENGINE-05 and RESEARCH.md's "Don't Hand-Roll" table)
```typescript
import { evalToExpectedScore, sideToMoveFromFen, type MoverColor } from '@/lib/liveFlaw';
```

### `noUncheckedIndexedAccess`-safe array/Record access
**Source:** `frontend/src/lib/maiaEncoding.ts` lines 152-153, 243, 253, 286-288
**Apply to:** All files in `lib/engine/` that index into arrays/Maps/Records by computed position (child arrays in `backup.ts`/`select.ts`, sorted-entries loops)
```typescript
const rowStr = rows[rowFromTop] ?? '';
// ...
return policy[idx] ?? Number.NEGATIVE_INFINITY;
```

### chess.js usage for legal-move enumeration / UCI parsing
**Source:** `frontend/src/lib/sanToSquares.ts` (whole file) and `frontend/src/lib/maiaEncoding.ts` lines 234-255
**Apply to:** `mctsSearch.ts`/`fallbackExpectimax.ts` (legal-move generation, terminal-position checks via `chess.isGameOver()`) and `select.ts` if UCI parsing is needed
```typescript
export function uciToSquares(uci: string | null): MoveSquares | null {
  if (!uci || uci.length < 4) return null;
  return { from: uci.slice(0, 2), to: uci.slice(2, 4) };
}
```
Note: reuse `uciToSquares` from `sanToSquares.ts` directly if UCI-square parsing is needed anywhere in `lib/engine/` — do not write a second parser (RESEARCH.md "Don't Hand-Roll" table + Pitfall 5).

### Vitest fixture-test style
**Source:** `frontend/src/lib/__tests__/moveQuality.test.ts` (whole file, 367 lines — read lines 1-80 directly)
**Apply to:** All 5 new test files in `lib/engine/__tests__/`
- File-header JSDoc summarizing what behaviors are covered, referencing the plan/phase
- Small analytic helper functions to construct exact fixture inputs (documented as fixture construction, not reimplementation)
- `describe`/`it` blocks, one behavior per `it`, exact-value `expect().toBe()`/`toEqual()` assertions plus explicit negative assertions where a wrong-but-plausible implementation must NOT match

## No Analog Found

None — every file in this phase has at least a role-match analog in `frontend/src/lib/` or its `__tests__/` directory. The orchestrator files (`mctsSearch.ts`, `fallbackExpectimax.ts`) and their tests are the weakest matches (no true async-orchestration-with-callback precedent exists yet in `lib/`), but RESEARCH.md's own "Code Examples" section (Backup Rule Worked Fixture, ELO Oracle Fixture, Root-Relative Frame Fixture, Guardrail Swap-in — lines 353-441) supplies concrete, ready-to-copy code for exactly these files, so the planner should treat that RESEARCH.md section as the primary analog for orchestration/test-fixture code, with `useStockfishGradingEngine.ts` as secondary structural precedent for the batched-call/pv[0]-keying convention.

## Metadata

**Analog search scope:** `frontend/src/lib/`, `frontend/src/lib/__tests__/`, `frontend/src/hooks/` (referenced only, not modified)
**Files scanned:** `liveFlaw.ts`, `moveQuality.ts`, `maiaEncoding.ts`, `sanToSquares.ts`, `moveQuality.test.ts`, directory listing of `frontend/src/lib/__tests__/` (20 existing test files confirming vitest conventions)
**Pattern extraction date:** 2026-07-05
