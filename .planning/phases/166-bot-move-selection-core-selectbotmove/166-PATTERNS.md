# Phase 166: Bot Move Selection Core (`selectBotMove`) - Pattern Map

**Mapped:** 2026-07-11
**Files analyzed:** 4 (2 new source files, 2 new test files)
**Analogs found:** 4 / 4

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|------------------|----------------|
| `frontend/src/lib/engine/selectBotMove.ts` | orchestrator/service (impure, async) | request-response (compose providers → return one move) | `frontend/src/lib/engine/mctsSearch.ts` (impl) + `frontend/src/hooks/useFlawChessEngine.ts` (call-site/`SearchBudget` construction) | exact (role) / role-match (call site) |
| `frontend/src/lib/engine/botSampling.ts` | utility (pure, sync helpers) | transform (weighted sampling / argmax over arrays) | `frontend/src/lib/engine/select.ts` | exact |
| `frontend/src/lib/engine/__tests__/selectBotMove.test.ts` | test | request-response (stubbed deps) | `frontend/src/lib/engine/__tests__/mctsSearch.test.ts` | exact |
| `frontend/src/lib/engine/__tests__/botSampling.test.ts` | test | transform | `frontend/src/lib/engine/__tests__/select.test.ts` | exact |

No analog is a poor/no-match — this phase is pure composition over an already-established sibling-module split in the same directory (`mctsSearch.ts` orchestrator vs. `select.ts`/`treeCommon.ts` pure helpers), so every new file has a direct structural analog one directory-listing away.

## Pattern Assignments

### `frontend/src/lib/engine/selectBotMove.ts` (orchestrator, request-response)

**Analogs:** `frontend/src/lib/engine/guardrail.ts` (type contract), `frontend/src/hooks/useFlawChessEngine.ts` lines 220-233 (real `SearchBudget` construction + `mctsSearch` call site)

**`SearchRunner` contract to match** (`frontend/src/lib/engine/guardrail.ts` lines 13-19):
```typescript
export type SearchRunner = (
  rootFen: string,
  budget: SearchBudget,
  providers: EngineProviders,
  onSnapshot: (snapshot: EngineSnapshot) => void,
  signal: AbortSignal,
) => Promise<EngineSnapshot>;
```
`deps.search` must satisfy this exact shape (positional, `onSnapshot` non-optional — Pitfall 5 in RESEARCH.md: passing `undefined` throws inside `mctsSearch`'s loop).

**Frozen types to import, never redeclare** (`frontend/src/lib/engine/types.ts` lines 26-47, 77-97):
```typescript
export interface EngineProviders {
  policy(fen: string, elo: number, side: Side): Promise<Record<string, number>>;
  grade(fen: string, candidateUcis: string[]): Promise<Map<string, MoveGrade>>;
}
export interface SearchBudget {
  maxNodes: number;
  elo: { w: number; b: number };
  maxPlies: number;
  concurrency: number;
  extraRootMoves?: string[];
  policyTemperature?: number;
}
export interface RankedLine {
  rootMove: string;
  practicalScore: number;   // D-06: root-side-to-move expected score 0-1 — sort order is by rankScore, NOT this
  ...
}
```

**Real call-site pattern to mirror for `SearchBudget` construction** (`frontend/src/hooks/useFlawChessEngine.ts` lines 220-233):
```typescript
const budget: SearchBudget = {
  maxNodes: FLAWCHESS_ENGINE_MAX_NODES,
  maxPlies: FLAWCHESS_ENGINE_MAX_PLIES,
  concurrency: computePoolSize(),
  elo: { w: elo, b: elo },              // symmetric ELO — mirror exactly for BOT-03
  policyTemperature: policyTemperature ?? DEFAULT_POLICY_TEMPERATURE,
};
const providers: EngineProviders = { policy: queue.policy, grade: pool.grade };
void mctsSearch(debouncedFen, budget, providers, handleSnapshot, controller.signal)
```
`selectBotMove` differs deliberately: `policyTemperature` must be OMITTED (D-02 forbids it in the sampling path — do not copy that field from this analog), `onSnapshot` becomes a no-op `() => {}` (this phase never streams), and `budget.elo` is built from `settings.elo` per D-07/BOT-03.

**Core dispatch pattern** — full worked implementation already composed in RESEARCH.md "Pattern 1: Regime dispatch on `blend`" (166-RESEARCH.md lines 177-239). Use verbatim as the base:
- `blend <= 0` → exactly one `deps.policy(fen, settings.elo, side)` call, never `mctsSearch`.
- `blend >= 1` → `(deps.search ?? mctsSearch)(...)` then `argmaxLine`.
- `0 < blend < 1` → same search call, then `tau = TAU_MAX * (1 - blend)`; short-circuit to `argmaxLine` when `tau <= TAU_EPSILON`, else `sampleRankedLines`.
- Every terminal branch is `sampled ?? fallbackMove(fen, deps.rng)`.

**Error handling / fallback boundary:** `selectBotMove` itself has no try/catch — degeneracy is signaled by helpers returning `string | null`, and the ONLY fallback trigger point is the `?? fallbackMove(...)` at each of the three call sites (RESEARCH.md Pattern 2 rationale, Anti-Pattern "Hiding the fallback trigger inside multiple helpers"). Do not add error handling elsewhere in this file.

---

### `frontend/src/lib/engine/botSampling.ts` (utility, transform)

**Analog:** `frontend/src/lib/engine/select.ts` (`truncateAndRenormalize`, lines 44-59)

**Tie-break/sort convention to reuse exactly** (`select.ts` lines 49-50):
```typescript
const sorted = Object.entries(policy).sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1));
```
`select.ts`'s own comment (lines 44-48) explains why: ties must break on ascending UCI string, never Record/Map iteration order, because a real provider's output order is not guaranteed stable across calls. `botSampling.ts`'s `weightedPick` cumulative-distribution walk must sort UCI-ascending FIRST (D-12), then walk — see RESEARCH.md Pattern 2 (lines 241-293) for the full worked `weightedPick`/`samplePolicy`/`sampleRankedLines`/`argmaxLine` implementations, already vetted against this exact convention.

**Renormalization-loop shape to mirror** (`select.ts` lines 51-58) — sum-then-divide-by-total pattern, guarding `total > 0`:
```typescript
const total = kept.reduce((sum, [, p]) => sum + p, 0);
return new Map(kept.map(([uci, p]) => [uci, total > 0 ? p / total : 0]));
```
`botSampling.ts`'s `weightedPick` should use the equivalent `total <= 0 → return null` guard (D-13's degenerate-distribution signal) rather than dividing by zero.

**`mulberry32` and `fallbackMove`:** No existing in-repo analog (RESEARCH.md confirms — "no seeded-RNG or weighted-sample helper exists in the frontend yet"). Use the exact implementations already vetted in RESEARCH.md Pattern 3 (lines 295-313) and Pattern 4 (lines 315-337) verbatim; `fallbackMove`'s chess.js usage mirrors `frontend/src/lib/sanToSquares.ts`'s `sanToUci` and `frontend/src/lib/engine/treeCommon.ts`'s `applyUciMoveFen` for `.lan`-based UCI construction (both already in the codebase as prior art for chess.js move-string extraction, though not literal copy sources for a fresh Chess(fen).moves() call).

---

## Shared Patterns

### Frozen-contract-only imports (no reimplementation)
**Source:** `frontend/src/lib/engine/types.ts`, `guardrail.ts`
**Apply to:** Both `selectBotMove.ts` and `botSampling.ts`
Import `EngineProviders`, `SearchBudget`, `RankedLine`, `EngineSnapshot`, `Side` from `./types`; import `SearchRunner` from `./guardrail`. Never redeclare a structurally-duplicate interface (per `types.ts`'s own header discipline, line 19: "do NOT redeclare a structurally-duplicate interface here").

### UCI-ascending tie-break discipline
**Source:** `frontend/src/lib/engine/select.ts` lines 49-50 (`truncateAndRenormalize`)
**Apply to:** `botSampling.ts`'s `weightedPick`, `argmaxLine`, and `fallbackMove`'s move-index sort
Every place this phase sorts or breaks a tie over UCI-keyed data must use ascending-string comparison, matching this exact established convention — never Map/Record iteration order.

### Null-return-not-throw for degenerate pure helpers
**Source:** Established by D-09/D-13 (new convention for this phase; no prior codebase example needed since it's small and self-contained), but structurally consistent with `treeCommon.ts`'s `applyUciMoveFen` "null-on-illegal" convention referenced in RESEARCH.md's Security Domain section (V5).
**Apply to:** `samplePolicy`, `sampleRankedLines`, `argmaxLine` (return `string | null`); `fallbackMove` is the sole exception — it throws on truly zero legal moves (D-14), never returns null.

### Test file structure (co-located `__tests__/`, one file per source module)
**Source:** `frontend/src/lib/engine/__tests__/select.test.ts` (analog for `botSampling.test.ts`), `frontend/src/lib/engine/__tests__/mctsSearch.test.ts` (analog for `selectBotMove.test.ts`)
**Apply to:** Both new test files
Existing directory already holds one `*.test.ts` per sibling source module (`select.test.ts`, `treeCommon.test.ts`, `mctsSearch.test.ts`, `maiaQueue.test.ts`, `workerPool.test.ts`, `policyTemperature.test.ts`, `fallbackExpectimax.test.ts`, `backup.test.ts`, `findability.test.ts`) — no separate `vitest.config.ts` exists (config co-located in `frontend/vite.config.ts`). Follow this 1:1 naming convention exactly: `selectBotMove.test.ts` stubs `deps.search`/`deps.policy` (mirrors how `mctsSearch.test.ts` presumably stubs `EngineProviders`); `botSampling.test.ts` uses canned `RankedLine[]`/policy-Record fixtures with no async/workers (mirrors `select.test.ts`'s pure-function-on-canned-input style).

## No Analog Found

None. Every file in scope has a strong structural analog in the same directory (`frontend/src/lib/engine/`), since this phase is explicitly "glue" composition over already-shipped primitives (Phases 153-159) rather than new domain logic.

## Metadata

**Analog search scope:** `frontend/src/lib/engine/`, `frontend/src/hooks/useFlawChessEngine.ts`, `frontend/src/lib/sanToSquares.ts`
**Files scanned:** `types.ts`, `guardrail.ts`, `mctsSearch.ts`, `select.ts`, `treeCommon.ts`, `maiaQueue.ts`, `useFlawChessEngine.ts`, `__tests__/` directory listing (10 existing test files)
**Pattern extraction date:** 2026-07-11
