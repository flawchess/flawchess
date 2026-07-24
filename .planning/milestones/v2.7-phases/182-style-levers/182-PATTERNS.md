# Phase 182: Style Levers - Pattern Map

**Mapped:** 2026-07-21
**Files analyzed:** 9 (5 new, 4 modified)
**Analogs found:** 9 / 9 (all in-repo; the new files extend existing pure-module conventions in the same directory)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `frontend/src/lib/engine/botStyle.ts` (NEW) | service (pure engine module) | transform (data-in/data-out, no I/O) | `frontend/src/lib/engine/openingBook.ts` | exact (same directory, same pure-module doc-header convention, same "seam" pattern) |
| `frontend/src/lib/engine/botStyle.test.ts` (NEW) | test | transform | `frontend/src/lib/engine/botSampling.ts` (its test conventions — not read in full but referenced by RESEARCH.md as the mirror target) | role-match |
| `frontend/src/lib/styleOpeningLines.ts` (NEW, or co-located in botStyle.ts) | config / data (plain exported constants) | batch (static curated data) | `frontend/src/data/trollOpenings.ts` | exact (same "curated Set literals + provenance comment" shape) |
| `frontend/src/lib/engine/selectBotMove.ts` (MODIFIED) | service (pure orchestrator) | request-response (single async resolve) | itself — extend in place, no external analog needed | exact (self) |
| `frontend/src/lib/botDrawGate.ts` (MODIFIED) | service (pure engine module) | transform (predicate over inputs) | itself — extend in place | exact (self) |
| `frontend/src/lib/engine/types.ts` (MODIFIED) | model (type contracts) | — | itself — additive-optional-field extension | exact (self) |
| `frontend/src/lib/engine/treeCommon.ts` (MODIFIED) | service (pure tree primitives) | transform | itself — `buildRankedLines` gains one computed field | exact (self) |
| `frontend/src/hooks/useBotGame.ts` (MODIFIED) | hook (impure orchestrator) | event-driven (game-loop state machine) | itself — extend `resolveBookMove`, the draw-accept effect, `newGame()`'s ref resets | exact (self) |
| `scripts/style-lever-measurement.mjs` (NEW) | utility (Node measurement script) | batch | `scripts/calibration-harness.mjs` | exact (explicitly named as the model in RESEARCH.md; same `@/` alias-hook import pattern, same `reports/data/` TSV output convention) |

## Pattern Assignments

### `frontend/src/lib/engine/botStyle.ts` (NEW — service, transform)

**Analog:** `frontend/src/lib/engine/openingBook.ts` (structure/doc-header) + `frontend/src/lib/botDrawGate.ts` (pure-predicate style) + `frontend/src/lib/engine/botSampling.ts` (pure-helper-catalog style)

**Module doc-header pattern** (`openingBook.ts` lines 1-30):
```typescript
/**
 * openingBook — the pure, synchronous bot opening-book module (Phase 169.5,
 * PLAY-11). ...
 * This module is deliberately pure and synchronous: no React, no providers,
 * no I/O, no `chess.js` import [NOTE: botStyle.ts WILL need chess.js for
 * classifyMoveFeatures — cite that deviation explicitly, mirroring how this
 * file explains its own "why" for each constraint].
 */
```
Every new pure engine module in this codebase opens with: (1) one-paragraph purpose + phase/req-ID citation, (2) an explicit purity statement, (3) forward pointers to the exact call sites that will consume it. `botStyle.ts` should do the same, citing STYLE-01..05 and D-01/D-03.

**The `*Fn` seam-type pattern** (`openingBook.ts` lines 60-72, `BookWeightingFn`):
```typescript
export type BookWeightingFn = (
  candidates: readonly BookCandidate[],
  rawPolicy: Record<string, number>,
) => Record<string, number>;
```
Model `applyStylePriorReweighting` and `applyStyleScoreShaping` as plain named functions (NOT factory-returned closures like `styleBookWeighting`, since D-03's canonical ref shows them called directly with `(rawPolicy, fen, settings.style)` / `(rankedLines, settings.style)` — see selectBotMove.ts excerpts below), each with a doc comment stating input/output shape and the "undefined style ⇒ untouched" contract.

**Named-constant-with-tuning-rationale pattern** (`openingBook.ts` lines 34-52, `BOOK_POLICY_FLOOR`/`BOOK_PLY_CAP`):
```typescript
export const BOOK_POLICY_FLOOR = 0.05;
```
Each constant gets a doc comment stating what it bounds, whether it's `[ASSUMED]`/hand-tuned, and where it's re-tunable. The 4 named style bundles (Attacker/Trickster/Grinder/Wall) and their per-feature multipliers should follow this exact convention — cite D-12 ("Claude hand-tunes magnitudes... iterating against the measurement script").

**Pure-predicate-extension pattern for contempt** (`botDrawGate.ts` lines 42-76, `wouldBotAcceptDraw`): extend with an additional optional `contempt = 0` parameter that shifts a threshold but preserves the `null`-sentinel-refuses-first structure (see RESEARCH.md Pattern 3, already a full worked example — copy verbatim as the shape for any NEW `wouldBotResign` function in the same file).

**Move-feature classifier** — RESEARCH.md's Pattern 4 is a complete, ready-to-use code example (`classifyMoveFeatures`, `MoveFeatures` interface, `PIECE_VALUE` lookup) based directly on chess.js `Move` API fields already used elsewhere in this codebase (`.flags`, `.captured`, `.piece`, `.san`) — copy that pattern into `botStyle.ts` verbatim, adjusting only the exact threshold values per D-12 tuning.

---

### `frontend/src/lib/engine/selectBotMove.ts` (MODIFIED — service, request-response)

**Analog:** self (existing regime-dispatch structure)

**Regime-branch hook points** (lines 113-118 and 131-146, the two branches this phase must extend):
```typescript
if (blend <= 0) {
  // D-03/BOT-02: exactly ONE policy() call, no MCTS.
  const rawPolicy = await deps.policy(fen, settings.elo, side);
  const sampled = samplePolicy(rawPolicy, deps.rng);
  return sampled ?? fallbackMove(fen, deps.rng);
}
...
const snapshot = await search(fen, budget, deps, () => {}, signal);
const lines: RankedLine[] = snapshot.rankedLines;

if (blend >= 1) {
  const best = argmaxLine(lines);
  return best ?? fallbackMove(fen, deps.rng);
}
```
RESEARCH.md's "Code Examples" section already shows the EXACT two insertion points annotated (`applyStylePriorReweighting` between `deps.policy()` and `samplePolicy`; `applyStyleScoreShaping` between `search()` and `argmaxLine`/`sampleRankedLines`) — implement exactly as shown there, guarded by `settings.style ? ... : rawPolicy`/`... : snapshot.rankedLines` (D-03 ternary, same style as the file's own existing `blend` clamp guard at line 111).

**`BotSettings` additive-field pattern** (lines 61-78): add `style?: BotStyleParams;` as a new field, doc-commented the same way `budget: Omit<SearchBudget, 'elo' | 'policyTemperature'>` is — citing the D-03 "undefined runs the exact current code path" contract, exactly as RESEARCH.md's Pattern 1 shows verbatim.

---

### `frontend/src/lib/botDrawGate.ts` (MODIFIED — service, transform)

**Analog:** self

**Extend `wouldBotAcceptDraw`, add `wouldBotResign`** — sentinel-preserving pattern (lines 68-76):
```typescript
export function wouldBotAcceptDraw(rootPracticalScore: number | null, chess: Chess): boolean {
  if (rootPracticalScore === null) return false;
  const isNearEqual = Math.abs(rootPracticalScore - 0.5) <= DRAW_ACCEPT_SCORE_BAND;
  if (!isNearEqual) return false;
  return queensAreOff(chess) || chess.moveNumber() >= DRAW_ACCEPT_MIN_FULLMOVE;
}
```
Add `contempt = 0` param (RESEARCH.md Pattern 3 shows the exact diff: `const drawValue = 0.5 - contempt;` replaces the hardcoded `0.5`). A new `wouldBotResign` predicate should mirror this file's existing style: top-of-file exported tunable constants (mirror `DRAW_ACCEPT_SCORE_BAND`/`DRAW_ACCEPT_MIN_FULLMOVE`), a pure function taking the practicalScore + a style threshold + (per Pitfall 3) a hysteresis COUNT passed in by the caller — the function itself stays stateless; `useBotGame.ts` owns the counter (see below).

**D-02/D-03 doc-header supersession note** (lines 1-14): this file's header explicitly says "the bot never offers a draw and never resigns — no function in this module does either." That sentence must be updated/superseded per D-07 of CONTEXT.md ("this deliberately supersedes Phase 169's D-02/D-03 ... for styled bots only") — follow the existing convention in this codebase of updating a stale doc-header comment in place rather than leaving it contradicted by new code (see how `openingBook.ts`'s header cites its own supersession lineage).

---

### `frontend/src/lib/engine/types.ts` (MODIFIED — model)

**Analog:** self — `RankedLine` additive-field convention (lines 97-118)

```typescript
export interface RankedLine {
  rootMove: string;
  practicalScore: number;
  objectiveEvalCp: number | null;
  objectiveEvalMate: number | null;
  modalPath: string[];
  modalStats: ModalPlyStat[];
  visits: number;
  // ADD: childScoreSpread: number | null;  // Phase 182 D-10 — cite the decision inline,
  //   mirroring every existing field's "D-06:"/"D-08:" doc-comment citation convention.
}
```
Every field in this file cites the decision that fixed its shape (see file header lines 1-14: "Every field cites the decision that fixes its shape"). The new `childScoreSpread` field MUST follow suit — one doc comment line citing D-10, and per RESEARCH.md's Open Question #1, the planner must pick and document ONE precise semantic (grandchild-value spread vs. something else) directly in this comment, not leave it implicit.

---

### `frontend/src/lib/engine/treeCommon.ts` (MODIFIED — service, transform)

**Analog:** self — `buildRankedLines` (lines 214-242)

```typescript
function buildRankedLines<N extends SearchTreeNode<N>>(root: N, rootElo: number): RankedLine[] {
  const pRef = pRefForElo(rootElo);
  const scored: { line: RankedLine; sortRankScore: number }[] = [];
  for (const child of root.children.values()) {
    if (child.uci === null) continue;
    const modal = buildModalPath(child);
    scored.push({
      line: {
        rootMove: child.uci,
        practicalScore: child.value,
        objectiveEvalCp: child.objectiveEvalCp,
        objectiveEvalMate: child.objectiveEvalMate,
        modalPath: modal.path,
        modalStats: modal.stats,
        visits: child.visits,
        // ADD: childScoreSpread: computeChildScoreSpread(child), per D-10/A3
      },
      sortRankScore: rankScore(child.prior, pRef, child.value),
    });
  }
  ...
}
```
`childScoreSpread` computation should be a small new private helper (e.g. `computeChildScoreSpread(node)`) placed near `buildModalPath` (lines 176-204) — same file, same "small pure helper feeding into the line-object literal" shape. Must return `null` (per Pitfall 4) when the root child has 0 or 1 own children, never `0` (0 is a valid "no spread" signal for exactly 1 child in some readings — the planner's chosen semantic in `types.ts`'s doc comment governs this exactly).

---

### `frontend/src/hooks/useBotGame.ts` (MODIFIED — hook, event-driven)

**Analog:** self — three separate existing seams

**1. Book call site** (`resolveBookMove`, lines 316-346): the default-weighting comment at line 343-345 is the exact seam to make style-aware:
```typescript
// Default weighting only (D-06: the BookWeightingFn seam exists for a future
// persona, which this phase deliberately does not build).
return selectBookMove(moveHistorySan, legalMoves, prefixSet, rawPolicy, Math.random);
```
Phase 182 replaces this default-only call with `selectBookMove(..., Math.random, settings.style ? styleBookWeighting(...) : maiaPolicyWeighting)`. `resolveBookMove` needs `settings.style` threaded in as a new parameter (it currently only takes `chess, botElo, policy`).

**2. Ref-latch pattern for new per-game state** (lines 449, 460, 471 — `lastRootPracticalScoreRef`, `hasLeftBookRef`, `movesSinceLastDeclineRef`, all reset in `newGame()` at lines 889-891):
```typescript
const lastRootPracticalScoreRef = useRef<number | null>(null);
...
const hasLeftBookRef = useRef(resume?.hasLeftBook ?? false);
...
const movesSinceLastDeclineRef = useRef(resume?.movesSinceLastDecline ?? DRAW_OFFER_COOLDOWN_MOVES);
```
and in `newGame()`:
```typescript
lastRootPracticalScoreRef.current = null;
hasLeftBookRef.current = false;
```
A new `consecutiveLowScoreTurnsRef` (Pitfall 3's exact recommendation) must follow this SAME pattern: declared alongside the other three refs, reset in `newGame()` alongside `lastRootPracticalScoreRef.current = null;`/`hasLeftBookRef.current = false;`, and incremented/reset in the same `pool.grade(...).then(...)` callback that already updates `lastRootPracticalScoreRef` (per RESEARCH.md Open Question #2's recommendation — reuse this exact callback site, cited around line ~1256).

**3. Draw-accept effect contempt threading** (lines 853-871, the effect calling `wouldBotAcceptDraw`):
```typescript
const accepts = wouldBotAcceptDraw(lastRootPracticalScoreRef.current, chessRef.current);
```
becomes (per RESEARCH.md's worked example):
```typescript
const contempt = settings.style?.contempt ?? 0; // D-03: undefined style ⇒ contempt 0 ⇒ unchanged
const accepts = wouldBotAcceptDraw(lastRootPracticalScoreRef.current, chessRef.current, contempt);
```
A resign check should be added at the SAME `pool.grade(...).then(...)` site that updates `lastRootPracticalScoreRef` (line ~1256), calling the new `wouldBotResign` predicate and invoking `finalizeGame({ reason: 'resignation', winner: ... })` (mirror the existing `resign` callback at lines 836-842) when it returns true.

---

### `scripts/style-lever-measurement.mjs` (NEW — utility, batch)

**Analog:** `scripts/calibration-harness.mjs`

**Header/usage-comment pattern** (lines 1-33):
```javascript
#!/usr/bin/env node
/**
 * calibration-harness.mjs — bot-vs-anchor game loop, pool-backed grid sweep,
 * and durable strength-map TSV emission (Phase 168, Plans 02/03).
 *
 * The bot's ENTIRE move selection is one call to the LIVE `selectBotMove`
 * (`@/lib/engine/selectBotMove`, imported via the `@/` alias hook) with
 * `deps.search` OMITTED so it defaults to the real `mctsSearch`...
 *
 * Usage:
 *   node --import ./scripts/lib/frontend-alias-hook.mjs scripts/calibration-harness.mjs \
 *     [--elo 1100,1500,1900] [--blends 0,0.5,1] ...
 */
```
`style-lever-measurement.mjs` must follow the SAME `@/` alias-hook import convention (`node --import ./scripts/lib/frontend-alias-hook.mjs scripts/style-lever-measurement.mjs`), the same "imports the LIVE production function directly, no reimplementation" principle (import `applyStylePriorReweighting`/`applyStyleScoreShaping`/`classifyMoveFeatures` from `@/lib/engine/botStyle` the same way the harness imports `selectBotMove`), and emit output to `reports/data/` as a TSV, per D-11.

---

## Shared Patterns

### Additive-optional-field extension (governs every locked type touched this phase)
**Source:** RESEARCH.md "Architecture Patterns / Pattern 1", exemplified at `frontend/src/lib/engine/selectBotMove.ts` lines 61-78 (`BotSettings`) and `frontend/src/lib/engine/types.ts` lines 97-118 (`RankedLine`)
**Apply to:** `BotSettings.style?`, `RankedLine.childScoreSpread?`/`| null`, and any new field on `BotGameSettings` in `useBotGame.ts`.
```typescript
/** NEW (Phase 182, STYLE-05): optional bot-only style params. `undefined` runs the
 * exact current code path — no reweight call, no shaping pass (D-03). */
style?: BotStyleParams;
```

### The `Fn`-typed composition seam (never replace, always compose over the base)
**Source:** `frontend/src/lib/engine/openingBook.ts` lines 60-94 (`BookWeightingFn`/`maiaPolicyWeighting`)
**Apply to:** `styleBookWeighting` — must call `maiaPolicyWeighting(candidates, rawPolicy)` internally and multiply, never reimplement the base restriction-to-candidates logic. See RESEARCH.md Pattern 2 for the full worked composition example and Pitfall 2 for the joined-prefix membership-test gotcha that the naive version in Pattern 2 gets wrong.

### Sentinel-preserving extension of pure predicates
**Source:** `frontend/src/lib/botDrawGate.ts` lines 68-76 (`wouldBotAcceptDraw`'s `null` check)
**Apply to:** any new predicate reading `rootPracticalScore: number | null` (the resign predicate in particular) — the `null` check must run FIRST, unconditionally, before any style-threshold logic.

### Ref-latch per-game state (never module-level, never derived fresh)
**Source:** `frontend/src/hooks/useBotGame.ts` lines 449/460/471 (declaration) + 889-891 (`newGame()` reset)
**Apply to:** the new resign hysteresis counter (`consecutiveLowScoreTurnsRef`) — declare beside the other 3 latches, reset in `newGame()`, mutate only inside the existing `pool.grade(...).then(...)` callback.

### Named-constant-with-doc-comment tuning convention
**Source:** `frontend/src/lib/engine/openingBook.ts` lines 34-52 (`BOOK_POLICY_FLOOR`, `BOOK_PLY_CAP`), `frontend/src/lib/botDrawGate.ts` lines 18-25 (`DRAW_OFFER_COOLDOWN_MOVES`, `DRAW_ACCEPT_SCORE_BAND`, `DRAW_ACCEPT_MIN_FULLMOVE`)
**Apply to:** every style-bundle magnitude (book boost multiplier ~×20-50 per D-06, feature multipliers per D-12, score bonuses ~0.02-0.05 per D-12, resign threshold/hysteresis N) — each gets its own `export const NAME = value;` with a doc comment stating what it bounds and citing `[ASSUMED]`/D-12 hand-tuning provenance.

## No Analog Found

None — every file this phase touches either IS an existing file being extended in place, or is a new file in a directory (`lib/engine/`, `scripts/`) whose sibling files already establish the exact structural convention to follow (pure-module doc-header, `*Fn`-typed seam, named-tunable-constant, Node-script-with-`@/`-alias-hook).

## Metadata

**Analog search scope:** `frontend/src/lib/engine/`, `frontend/src/lib/`, `frontend/src/hooks/useBotGame.ts`, `frontend/src/data/trollOpenings.ts`, `scripts/calibration-harness.mjs`
**Files scanned:** 9 read in full (openingBook.ts, botDrawGate.ts, selectBotMove.ts, types.ts, treeCommon.ts, botSampling.ts, trollOpenings.ts header, useBotGame.ts targeted sections, calibration-harness.mjs header)
**Pattern extraction date:** 2026-07-21
