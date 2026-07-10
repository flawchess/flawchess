# Phase 159: FlawChess Engine policy temperature + root-move findability - Pattern Map

**Mapped:** 2026-07-07
**Files analyzed:** 12 (2 new pure modules, 1 new component, 1 new test-adjacent, 6 edits, 2 test extensions implied)
**Analogs found:** 12 / 12 (this phase is a pure extension of an already-shipped, heavily-conventioned engine core — RESEARCH.md already did most of the analog identification; this file adds concrete line-anchored excerpts)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `frontend/src/lib/engine/findability.ts` (NEW) | utility (pure transform) | transform | `frontend/src/lib/engine/select.ts` | exact |
| `frontend/src/lib/engine/policyTemperature.ts` (NEW) | utility (pure transform) | transform | `frontend/src/lib/engine/select.ts` | exact |
| `frontend/src/lib/engine/treeCommon.ts` (EDIT — `buildRankedLines`) | utility (pure ranking) | transform | itself (existing function to modify in place) | exact |
| `frontend/src/lib/engine/types.ts` (EDIT — `SearchBudget`) | model/config (type def) | — | itself | exact |
| `frontend/src/lib/engine/mctsSearch.ts` (EDIT — `dispatchExpansion`) | service (orchestrator) | event-driven (async expansion) | itself (`dispatchExpansion`, lines ~289-304) | exact |
| `frontend/src/lib/engine/fallbackExpectimax.ts` (EDIT — `expandNode`) | service (orchestrator) | event-driven | `mctsSearch.ts`'s `dispatchExpansion` (sibling runner, must mirror) | exact |
| `frontend/src/lib/flawChessVerdict.ts` (EDIT — new gate fn) | service (pure classifier) | transform | itself (existing `computeFlawChessVerdict`-style pure functions) | exact |
| `frontend/src/components/analysis/TemperatureSelector.tsx` (NEW) | component | request-response (controlled input) | `frontend/src/components/analysis/EloSelector.tsx` | exact |
| `frontend/src/components/analysis/FlawChessAgreementVerdict.tsx` (EDIT) | component | request-response | itself (existing verdict-rendering component) | exact |
| `frontend/src/hooks/useFlawChessEngine.ts` (EDIT) | hook | request-response | itself (existing `elo` threading pattern) | exact |
| `frontend/src/pages/Analysis.tsx` (EDIT) | component (page) | request-response | itself (existing `EloSelector` dual mobile/desktop placement, ~1630-1651 and ~1796-1829) | exact |
| `frontend/src/lib/engine/__tests__/findability.test.ts`, `policyTemperature.test.ts` (NEW) | test | transform | `frontend/src/lib/engine/__tests__/select.test.ts` | exact |

No "no analog" files — every file in this phase either edits an existing function in place or has a direct sibling-file precedent already identified by RESEARCH.md.

## Pattern Assignments

### `frontend/src/lib/engine/findability.ts` (NEW utility, transform)

**Analog:** `frontend/src/lib/engine/select.ts`

**Header/module-doc pattern** (`select.ts` lines 1-20, paraphrased convention): every file in `lib/engine/` opens with a doc comment stating (a) what the module does, (b) why it's shaped this way, (c) what alternative was rejected and why. Mirror this for `findability.ts` — lead with D-01's saturating-factor rationale and the explicitly-rejected `P^β·V` alternative.

**Layered-transform discipline** (`select.ts` lines 1-10, the load-bearing convention this phase must extend):
```typescript
// truncateAndRenormalize and rootExplorationPriors are two DISTINCT
// functions layered in sequence, never conflated.
export const POLICY_MASS_THRESHOLD = 0.9;
...
export const ROOT_PRIOR_FLOOR = 0.1;
...
export function truncateAndRenormalize(policy: Record<string, number>): Map<string, number> {
  ...
  if (cumulative >= POLICY_MASS_THRESHOLD) break;
  ...
}
export function rootExplorationPriors(renormalized: Map<string, number>): Map<string, number> {
  const flooredP = Math.max(p, ROOT_PRIOR_FLOOR);
  ...
}
```
`findability.ts` must follow the identical shape: one named exported constant set (`P_REF_ANCHORS`), one pure exported function (`pRefForElo`), one pure exported function (`rankScore`) — each independently unit-testable, never conflated into a single "do everything" function.

**`noUncheckedIndexedAccess` narrowing pattern** — copy from `EloSelector.tsx` lines 30-34 (`const min = ladder[0] ?? value;`) or RESEARCH.md's own worked example for `pRefForElo`'s anchor-array indexing (lines 466-483 of RESEARCH.md) — every array index must be bound to a local and null-checked before use, never asserted with `!`.

---

### `frontend/src/lib/engine/policyTemperature.ts` (NEW utility, transform)

**Analog:** `frontend/src/lib/engine/select.ts` (same layered-transform convention)

**Core pattern** — standard softmax-temperature `p^(1/T)` renormalized, RESEARCH.md's worked example (lines 494-525) is ready to use verbatim:
```typescript
export const DEFAULT_POLICY_TEMPERATURE = 1;

export function applyPolicyTemperature(
  policy: Record<string, number>,
  temperature: number,
): Record<string, number> {
  const exponent = 1 / temperature;
  const reshaped = Object.entries(policy).map(([uci, p]) => [uci, p ** exponent] as const);
  const total = reshaped.reduce((sum, [, p]) => sum + p, 0);
  const result: Record<string, number> = {};
  for (const [uci, p] of reshaped) {
    result[uci] = total > 0 ? p / total : 0;
  }
  return result;
}
```

**Degenerate-guard pattern** — mirror `rankScore`'s `if (pRef <= 0) return value;` guard style (also used in `backup.ts`'s `totalPrior===0` convention) for the `total > 0 ? ... : 0` branch above — this codebase always has an explicit, named guard for zero-division, never a silent `NaN`.

---

### `frontend/src/lib/engine/treeCommon.ts` (`buildRankedLines`, lines 144-161 — EDIT IN PLACE)

**Analog:** itself — the exact function being modified.

**Current implementation (imports/context at top, lines 1-24; function body, lines 144-161)**:
```typescript
import { Chess } from 'chess.js';
import type { MoverColor } from '@/lib/liveFlaw';
import { uciToSquares } from '@/lib/sanToSquares';
import type { EngineSnapshot, RankedLine, Side } from './types';
import { type BackupChild, backupExpectation, backupRootMax } from './backup';

/** Ranked root candidates by practicalScore descending, canonical-UCI tie-break (ENGINE-01/ENGINE-07). */
function buildRankedLines<N extends SearchTreeNode<N>>(root: N): RankedLine[] {
  const lines: RankedLine[] = [];
  for (const child of root.children.values()) {
    if (child.uci === null) continue; // defensive; every root child has a uci
    lines.push({
      rootMove: child.uci,
      practicalScore: child.value,
      objectiveEvalCp: child.objectiveEvalCp,
      modalPath: buildModalPath(child),
      visits: child.visits,
    });
  }
  lines.sort((a, b) => {
    if (b.practicalScore !== a.practicalScore) return b.practicalScore - a.practicalScore;
    return a.rootMove < b.rootMove ? -1 : a.rootMove > b.rootMove ? 1 : 0;
  });
  return lines;
}

export function buildSnapshot<N extends SearchTreeNode<N>>(
  root: N,
  nodesEvaluated: number,
  budgetExhausted: boolean,
): EngineSnapshot {
  return { rankedLines: buildRankedLines(root), nodesEvaluated, budgetExhausted };
}
```

**Required edit shape** (per D-01/D-04, RESEARCH.md Pattern 2, lines 265-302): add a `rootElo: number` parameter, compute `pRef = pRefForElo(rootElo)` once per call (not per child — see Anti-Patterns), compute a **sort-local** `rankScore` field never persisted onto the public `RankedLine`, keep `practicalScore: child.value` byte-identical, keep the canonical-UCI tie-break unchanged. `buildSnapshot` must thread the new `rootElo` param through to `buildRankedLines` and up to its own callers in `mctsSearch.ts`/`fallbackExpectimax.ts`.

**`SearchTreeNode.prior` field already carries `P_you`** (lines 40-60 of `treeCommon.ts`, the interface): `prior: number; // Renormalized Maia prior for this child at its parent (D-02) — root's own value is unused.` — this comment is now stale after Thread B ships (root's prior becomes the exact signal read); update it.

---

### `frontend/src/lib/engine/types.ts` (`SearchBudget` — EDIT, add `policyTemperature?`)

**Analog:** itself, existing field-by-field doc-comment convention (lines 34-45):
```typescript
export interface SearchBudget {
  /** D-09: one node = one expansion event; the unit this budget counts. */
  maxNodes: number;
  /** D-07: color-keyed ELO, never self/opponent-keyed. */
  elo: { w: number; b: number };
  /** Locked 6-10 ply band (SEED-082). */
  maxPlies: number;
  /** D-03: in-flight expansion concurrency, >=1. */
  concurrency: number;
  /** D-04: root-only UCI moves unioned with Maia top-k at the root. */
  extraRootMoves?: string[];
}
```
New field must follow the identical single-line doc-comment-with-decision-ID style: `/** Phase 159 D-06/D-07: reshapes the user's-side policy before truncation; omitted/1 = no-op. */ policyTemperature?: number;`

---

### `frontend/src/lib/engine/mctsSearch.ts` (`dispatchExpansion` — EDIT, lines ~289-304)

**Analog:** itself — the exact insertion point.

**Current implementation:**
```typescript
async function dispatchExpansion(
  leaf: EngineNode,
  path: EngineNode[],
  budget: SearchBudget,
  providers: EngineProviders,
): Promise<DispatchedExpansion> {
  const rawPolicy = await providers.policy(leaf.fen, budget.elo[leaf.side], leaf.side);
  let candidateMap = truncateAndRenormalize(rawPolicy);
  if (leaf.isRoot && budget.extraRootMoves && budget.extraRootMoves.length > 0) {
    const merged = new Map(candidateMap);
    for (const uci of budget.extraRootMoves) {
      if (!merged.has(uci)) merged.set(uci, 0);
    }
    candidateMap = merged;
  }
  ...
}
```
**Required edit** (RESEARCH.md Pattern 1, lines 239-261; Pitfall 1's short-circuit is mandatory): `dispatchExpansion` does not currently have `rootMover` in scope — it must be threaded in as a new parameter (RESEARCH.md flags this explicitly: "unlike `fallbackExpectimax.ts`'s `expandNode`, which already has `rootMover`"). Insert the temperature step between `providers.policy(...)` and `truncateAndRenormalize(rawPolicy)`, short-circuited at `DEFAULT_POLICY_TEMPERATURE`.

---

### `frontend/src/lib/engine/fallbackExpectimax.ts` (`expandNode` — EDIT, lines ~136-193)

**Analog:** `mctsSearch.ts`'s `dispatchExpansion` (sibling runner — MUST mirror exactly, Pitfall 3).

**Current relevant excerpt** (line 166): `const rawPolicy = await providers.policy(node.fen, budget.elo[node.side], node.side);` — `rootMover: MoverColor` is already a parameter of `expandNode` (line 139), so this file's edit is structurally simpler than `mctsSearch.ts`'s (no new param needed). Both edits must land in the same task/commit per Pitfall 3, and both must call the SAME `applyPolicyTemperature`/`sideMatchesMover` helpers — never two independent re-implementations.

---

### `frontend/src/lib/flawChessVerdict.ts` (EDIT — new `computeFindabilityGate` function)

**Analog:** itself — existing pure-classifier convention (header lines 1-18):
```typescript
/**
 * flawChessVerdict — pure, worker-free, chess.js-free classification module for
 * the FlawChess-vs-Stockfish agreement verdict on the `/analysis` page (Phase
 * 157, REVIEW-02). ...
 */
import type { RankedLine } from '@/lib/engine/types';
import type { PvLine } from '@/hooks/uciParser';
import { evalToExpectedScore, type MoverColor } from '@/lib/liveFlaw';
import { BLUNDER_DROP } from '@/generated/flawThresholds';
import { FLAWCHESS_ENGINE_ARROW, BEST_MOVE_ARROW } from '@/lib/theme';
```

**Pattern to copy:** named threshold constant + pure boolean-returning gate function, exact shape RESEARCH.md already worked out (Pattern 3, lines 310-329):
```typescript
export const FINDABILITY_MARGIN = 0.05; // scale reference: BLUNDER_DROP-style constant from flawThresholds.ts

export function computeFindabilityGate(
  pYouFc: number | null,
  pYouSf: number | null,
  fcInPlottedSet: boolean,
): boolean {
  if (pYouFc == null || pYouSf == null) return false;
  return fcInPlottedSet && pYouFc > pYouSf + FINDABILITY_MARGIN;
}
```
**Critical constraint (D-12, structural):** this file must NOT import anything from `lib/engine/` beyond the `RankedLine` type (already imported) — never import `maiaQueue.ts`, `select.ts`, or any temperature-related symbol. `RankedLine` has no `prior` field, so the gate is structurally incapable of reading the temperature-adjusted probability — preserve this by construction, don't add a `prior` passthrough.

---

### `frontend/src/components/analysis/TemperatureSelector.tsx` (NEW)

**Analog:** `frontend/src/components/analysis/EloSelector.tsx` (full file, 67 lines — copy structure almost verbatim)

**Full analog for reference:**
```typescript
import { Slider } from '@/components/ui/slider';
import { MAIA_ELO_LADDER } from '@/lib/maiaEncoding';

export interface EloSelectorProps {
  value: number;
  onChange: (elo: number) => void;
  ladder?: readonly number[];
}

const SINGLE_RUNG_STEP_FALLBACK = 100;

export function EloSelector({
  value,
  onChange,
  ladder = MAIA_ELO_LADDER,
}: EloSelectorProps): React.ReactElement {
  const min = ladder[0] ?? value;
  const max = ladder[ladder.length - 1] ?? value;
  const first = ladder[0];
  const second = ladder[1];
  const step = first !== undefined && second !== undefined ? second - first : SINGLE_RUNG_STEP_FALLBACK;

  const handleValueChange = (values: number[]): void => {
    const next = values[0];
    if (next === undefined) return;
    onChange(next);
  };

  return (
    <div
      data-testid="analysis-elo-selector"
      role="group"
      aria-label="Engine strength (ELO)"
      className="flex items-center gap-3"
    >
      <span className="text-sm text-muted-foreground">ELO</span>
      <Slider
        min={min}
        max={max}
        step={step}
        value={[value]}
        onValueChange={handleValueChange}
        thumbLabels={['Engine strength (ELO)']}
        className="min-w-24"
      />
      <span
        className="text-sm font-medium tabular-nums w-12 text-right"
        data-testid="analysis-elo-selector-value"
      >
        {value}
      </span>
    </div>
  );
}
```

**Required deltas for `TemperatureSelector`:**
- Domain is continuous [0.5, 2.0] log-symmetric (D-08), not a discrete ladder — the underlying `<Slider>` stays linear (min=-1, max=1, small step e.g. 0.01) and the component converts at its boundary via `sliderPositionToTemperature`/`temperatureToSliderPosition` (RESEARCH.md lines 527-546, ready to use).
- `data-testid="analysis-temperature-selector"`, `aria-label` per D-09's plain-language framing ("Play style" / endpoint captions "Sharper"/"More human"), numeric value shown `text-sm font-medium tabular-nums` (copy `EloSelector`'s value-span styling) formatted to one decimal place, no raw "T=" prefix.
- `thumbLabels` prop still required (Radix per-thumb ARIA, same as `EloSelector` line 56).

---

### `frontend/src/hooks/useFlawChessEngine.ts` (EDIT — thread `policyTemperature`)

**Analog:** itself — existing `elo` threading pattern (per RESEARCH.md's diagram, lines 148-154: `elo: { w: elo, b: elo }` passed into `SearchBudget`). Add `policyTemperature` as a same-shape optional pass-through option, defaulting via `?? DEFAULT_POLICY_TEMPERATURE` at the call site, not inside the hook (keep the no-op short-circuit visible at the search-orchestrator layer per Pitfall 1).

---

### `frontend/src/pages/Analysis.tsx` (EDIT — new session state + dual mobile/desktop render)

**Analog:** itself — `useMaiaEloDefault.ts`'s session-only default-with-override pattern (D-08 explicitly mirrors this) for the state hook, and the existing `EloSelector` dual-placement sites (~line 1630-1651 mobile `humanTab`, ~line 1796-1829 desktop human column) for the render.

**Pattern:** `TemperatureSelector` must be rendered in BOTH locations (mobile-parity rule), directly below the existing `EloSelector` render in each, using plain `useState(TEMPERATURE_DEFAULT)` (no async re-derivation needed — simpler than `useMaiaEloDefault`, per RESEARCH.md Sources note) since there's no server-driven default to reconcile, only a constant.

**Raw-probability wiring for the verdict gate** (D-10/D-12, Pitfall 5): `Analysis.tsx` already computes `shownSans`/`maia.perElo` at `selectedElo` for the chart (~line 685-688) — compute the raw-probability-by-SAN map ONCE here and pass it plus `shownSans` down as new props to `FlawChessAgreementVerdict.tsx`. Do NOT let the verdict component call `nearestByElo` independently.

---

### `frontend/src/components/analysis/FlawChessAgreementVerdict.tsx` (EDIT — wire gate, D-11 fallback prose)

**Analog:** itself, existing verdict-prose rendering + `uciToSan` usage (chess.js lives in this component, not in `flawChessVerdict.ts`, per RESEARCH.md Pattern 3 sourcing).

**Pattern:** resolve FC/SF SAN via the existing `uciToSan` call in this file, look up `pYouFc`/`pYouSf` from the props-passed raw-probability map (never re-fetch), call `computeFindabilityGate`, and add exactly one new prose variant (D-11 fallback: "nearly as good / safer follow-ups", no findability claim) alongside the existing tier-based copy — per the popover-copy-minimalism norm (no jargon, no p-values).

---

## Shared Patterns

### Layered pure transforms (the dominant cross-cutting pattern for this entire phase)
**Source:** `frontend/src/lib/engine/select.ts` lines 1-10 (module header) and its `truncateAndRenormalize`/`rootExplorationPriors` pair.
**Apply to:** `findability.ts`, `policyTemperature.ts`, and the edit to `buildRankedLines` in `treeCommon.ts`.
Each derived value is a separate, independently-testable, named pure function — never two concerns folded into one function body. The temperature transform and the findability transform are sequential layers over the same `child.prior` value; no third "combiner" function should be written (RESEARCH.md's central finding).

### No-op short-circuit at default values (determinism guardrail, ENGINE-07)
**Source:** RESEARCH.md Pitfall 1; existing precedent is the codebase's general "guard the identity case explicitly" style seen in `rankScore`'s `if (pRef <= 0) return value;` and `backup.ts`'s `totalPrior===0` guard.
**Apply to:** every call site of `applyPolicyTemperature` (both `mctsSearch.ts` and `fallbackExpectimax.ts`) — must short-circuit at `temperature === DEFAULT_POLICY_TEMPERATURE` rather than routing through the transform, to avoid floating-point drift changing today's default behavior for every existing user/fixture.

### Named constants for every new threshold (project-wide rule, CLAUDE.md "No magic numbers")
**Source:** `frontend/src/lib/engine/select.ts`'s `POLICY_MASS_THRESHOLD`/`ROOT_PRIOR_FLOOR`; `frontend/src/generated/flawThresholds.ts`'s `BLUNDER_DROP`/`INACCURACY_DROP`.
**Apply to:** `P_REF_ANCHORS`, `FINDABILITY_MARGIN`, `TEMPERATURE_MIN`/`MAX`/`DEFAULT`, any root-candidate hard cap constant (Pitfall 6) — all must be named, exported, and documented with a one-line "why this value" comment.

### Doc-comment-with-decision-ID convention
**Source:** every file/interface in `lib/engine/` (e.g. `SearchBudget`'s `/** D-09: ... */`, `SearchTreeNode.prior`'s `/** ... (D-02) ... */`).
**Apply to:** every new field, constant, and function introduced by this phase — reference the specific D-NN decision ID from `159-CONTEXT.md` inline, matching the existing house style exactly.

### Mobile/desktop dual-render parity
**Source:** `Analysis.tsx`'s existing `EloSelector` placement in both `humanTab` (mobile) and the desktop human column.
**Apply to:** `TemperatureSelector` — must render in both locations with identical props/behavior (CLAUDE.md "Always apply changes to mobile too").

## No Analog Found

None — every file in this phase edits an existing function in place or has a direct, already-identified sibling-file precedent (RESEARCH.md performed this mapping exhaustively; this file adds the concrete excerpts).

## Metadata

**Analog search scope:** `frontend/src/lib/engine/`, `frontend/src/lib/flawChessVerdict.ts`, `frontend/src/lib/moveQuality.ts`, `frontend/src/components/analysis/`, `frontend/src/hooks/`, `frontend/src/pages/Analysis.tsx`
**Files scanned:** 12 (all read directly this session or in prior RESEARCH.md session; see RESEARCH.md Sources section for the full list with line ranges)
**Pattern extraction date:** 2026-07-07
