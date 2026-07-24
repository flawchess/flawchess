# Phase 182: Style Levers - Research

**Researched:** 2026-07-21
**Domain:** Pure TypeScript game-engine extension (opening-book weighting, draw/resign policy, Maia-policy reweighting, MCTS score shaping) — no backend, no UI, no new dependencies
**Confidence:** HIGH

## Summary

Phase 182 adds a single new optional field (`style?: BotStyleParams`) to the bot's existing
pure engine surfaces — `selectBotMove.ts`, `botSampling.ts`, `openingBook.ts`,
`botDrawGate.ts`, and `useBotGame.ts` — without touching any of their frozen contracts. Every
seam this phase needs already exists and was purpose-built for it in prior phases:
`openingBook.ts`'s `BookWeightingFn` type (Phase 169.5 D-06) is explicitly "the ONLY thing a
future persona needs to swap"; `botDrawGate.ts`'s `wouldBotAcceptDraw` already threads a
sentinel-bearing `rootPracticalScore`; `RankedLine` (Phase 153, frozen through Phase 161) is a
plain data object that accepts an additive optional field with zero blast radius on existing
consumers; and `selectBotMove`'s two regimes (`blend<=0` raw-policy sample, `blend>0` MCTS
search) map exactly onto STYLE-03 (prior reweighting) and STYLE-04 (score shaping) as the
CONTEXT.md decisions already state.

The one genuinely new piece of code is a **cheap chess.js move-feature classifier** (check,
capture, pawn advance/storm, exchange/trade, retreat) — nothing in the codebase computes this
today; `moveQuality.ts` classifies Stockfish *evaluation* quality (Best/Good/Inaccuracy/…), not
move *features*. This classifier is straightforward: chess.js's `Move` object already exposes
`.captured`, `.flags`, `.piece`, `.color`, `.from`/`.to`, and SAN suffixes (`+`/`#`), so no
board-diffing or FEN parsing beyond what chess.js already does is needed.

The opening-book corpus (`frontend/public/openings.tsv`, 3,641 ECO lines) was verified to
contain strong coverage for style-line curation: Trickster's classic troll openings (Bongcloud
Attack C20, Halloween Gambit C47, Sodium Attack A00, Napoleon Attack, Grob Attack, Barnes
Opening/Hammerschlag) are all present as named ECO lines, distinct from `trollOpenings.ts`'s
own position-key data (which exists for a different purpose — Phase 172's gem-sweep book
markers — and is NOT SAN-prefix-shaped). D-05's re-curation work is therefore real work
(curating fresh SAN prefix lists per style, checked against `openings.tsv`), not just reading
existing data.

**Primary recommendation:** Build `BotStyleParams` as a single new file
(`frontend/src/lib/engine/botStyle.ts`) holding the type, the 4 named bundles (Attacker/
Trickster/Grinder/Wall), and 3 small pure functions (`styleBookWeighting`, `applyStylePriorReweighting`,
`applyStyleScoreShaping`) plus a resign/draw extension in `botDrawGate.ts`. Wire all four into
`useBotGame.ts` at the 4 existing seams the CONTEXT.md canonical refs already identify. Add the
optional `childScoreSpread` field to `RankedLine`/`treeCommon.ts`'s `buildRankedLines`. No new
npm dependencies.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Style-specific opening book selection | Browser / Client (pure engine module) | — | `openingBook.ts` is synchronous, no I/O; the `BookWeightingFn` seam runs entirely in-browser against the already-fetched ECO prefix set |
| Draw contempt / resign policy | Browser / Client (pure engine module) | Browser / Client (React hook orchestration) | `botDrawGate.ts` pure functions decide; `useBotGame.ts` owns the resign-hysteresis counter state and wires the decision into `finalizeGame` |
| Prior reweighting (Human rungs) | Browser / Client (pure engine module) | — | Runs inside `selectBotMove`'s `blend<=0` branch, between `deps.policy()` and `samplePolicy` — no network round-trip, pure synchronous transform of an in-memory `Record<string, number>` |
| Score shaping + variance preference (Light/Deep rungs) | Browser / Client (pure engine module) | — | Runs on `RankedLine[]` already returned by `mctsSearch`/`fallbackExpectimax` — pure array transform before `argmaxLine`/`sampleRankedLines` |
| Move-feature classification (check/capture/pawn-advance/exchange/retreat) | Browser / Client (pure engine module, chess.js) | — | A pure function over a `Chess` instance + a candidate move; no new library, no worker boundary |
| Style bundle data (4 named presets) | Browser / Client (plain exported constants) | — | Data-only module, imported by both the engine (this phase) and Phase 183's persona registry |

No capability in this phase touches the API/Backend or Database tiers — this is explicitly a
frontend-only, engine-layer phase (CONTEXT.md `<domain>`).

## Standard Stack

### Core
No new libraries. This phase extends existing pure TypeScript modules using the already-vendored
`chess.js` (^1.4.0, confirmed in `frontend/package.json`) for move-flag/SAN inspection — the same
dependency `botSampling.ts` and `treeCommon.ts` already import.

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| chess.js | ^1.4.0 [VERIFIED: frontend/package.json] | Move flags (`.captured`, `.flags`, `.piece`), SAN check/mate suffix, legal-move re-derivation | Already the project's sole chess-rules dependency; every existing pure engine module (`botSampling.ts`, `treeCommon.ts`, `openingBook.test.ts`) uses it the same way |

### Supporting
None. Every other piece (softmax sampling, weighted-pick, mulberry32 seeded RNG) is already
implemented in `botSampling.ts` and should be reused, not reimplemented (see Don't Hand-Roll).

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom `Chess` re-play per candidate move for feature classification | `chess.js`'s `.moves({verbose:true})` output directly (already carries `.captured`/`.flags`/`.piece`) | The verbose move list already IS the classification input — no re-play needed; only pawn-storm/exchange/retreat require a tiny bit of extra geometry (rank distance, captured-piece value lookup) on top of the verbose fields |

**Installation:** None — no new packages.

## Package Legitimacy Audit

Not applicable — this phase adds zero new external packages. All work happens inside existing
`frontend/src/lib/engine/` modules using the already-installed `chess.js`.

## Architecture Patterns

### System Architecture Diagram

```
                         ┌─────────────────────────────┐
                         │   BotStyleParams (new data)  │
                         │  botStyle.ts — 4 bundles:    │
                         │  Attacker / Trickster /      │
                         │  Grinder / Wall              │
                         └───────────────┬──────────────┘
                                         │ optional, consumed at 4 seams
           ┌─────────────────────────────┼─────────────────────────────┐
           │                             │                             │
           ▼                             ▼                             ▼
 ┌──────────────────┐        ┌───────────────────────┐      ┌────────────────────┐
 │ openingBook.ts    │        │ selectBotMove.ts       │      │ botDrawGate.ts      │
 │ BookWeightingFn    │        │ (regime dispatch)      │      │ wouldBotAcceptDraw  │
 │ seam (D-06, exists)│        │                        │      │ + NEW: wouldBotResign│
 │                    │        │  blend<=0:              │      │                     │
 │ styleBookWeighting │        │   deps.policy()         │      │ contempt shifts     │
 │ (curated prefix    │        │     ↓                   │      │ 0.5-band accept     │
 │  boost ×20-50)     │        │   applyStylePrior        │      │ threshold           │
 └─────────┬──────────┘        │   Reweighting (NEW)      │      └──────────┬──────────┘
           │                   │     ↓                    │                 │
           │ useBotGame.ts     │   samplePolicy()          │                 │ useBotGame.ts
           │ resolveBookMove() │                           │                 │ resign-hysteresis
           │ book call site    │  blend>0:                 │                 │ counter (NEW state)
           │ (~line 343)       │   deps.search() → lines[]  │                 │
           │                   │     ↓                      │                │
           │                   │   applyStyleScoreShaping   │                │
           │                   │   (NEW; bonus/malus +      │                │
           │                   │    variance via            │                │
           │                   │    childScoreSpread)       │                │
           │                   │     ↓                      │                │
           │                   │   argmaxLine / sampleRanked │               │
           │                   │   Lines (unchanged,         │                │
           │                   │   botSampling.ts)           │               │
           │                   └────────────┬───────────────┘                │
           │                                │                                │
           ▼                                ▼                                ▼
 ┌──────────────────────────────────────────────────────────────────────────────┐
 │                     useBotGame.ts (impure orchestrator)                       │
 │  runBotTurn(): book → selectBotMove → practicalScore refresh → resign check   │
 │  Style params are optional at every call site — undefined ⇒ byte-identical    │
 │  to today's code path (D-03 structural guarantee)                             │
 └──────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
                         ┌───────────────────────────────┐
                         │ mctsSearch.ts / treeCommon.ts   │
                         │ buildRankedLines: ADD optional  │
                         │ childScoreSpread field (D-10) — │
                         │ max−min of root child's OWN     │
                         │ children's `.value`s; additive, │
                         │ analysis-board untouched        │
                         └───────────────────────────────┘
```

### Recommended Project Structure
```
frontend/src/lib/engine/
├── botStyle.ts              # NEW: BotStyleParams type + 4 named bundles + pure helpers
│                             #   (applyStylePriorReweighting, applyStyleScoreShaping,
│                             #   styleBookWeighting, moveFeatures classifier)
├── botStyle.test.ts          # NEW: pure unit tests (mirrors botSampling.test.ts conventions)
├── selectBotMove.ts          # MODIFIED: optional style-aware reweight/shape calls
├── botDrawGate.ts            # MODIFIED: contempt-aware accept gate + new resign function
├── types.ts                  # MODIFIED: RankedLine gains optional childScoreSpread
├── treeCommon.ts             # MODIFIED: buildRankedLines computes childScoreSpread
frontend/src/lib/
├── styleOpeningLines.ts       # NEW (or co-located in botStyle.ts): curated per-style SAN
│                             #   prefix lists (D-05), both colors, checked against openings.tsv
frontend/src/hooks/
├── useBotGame.ts             # MODIFIED: style-aware book call, resign hysteresis counter,
│                             #   contempt-aware draw accept — all gated on settings.style
scripts/
├── style-lever-measurement.mjs  # NEW (D-11): Node script, calibration-harness family
│                                 #   conventions, samples N positions per style, reports
│                                 #   feature-frequency shift vs unstyled baseline
reports/data/
├── style-lever-measurement-<ts>.tsv   # NEW: measurement script output (D-11/D-12 tuning evidence)
```

### Pattern 1: Additive-optional-field extension (do not touch frozen contracts)
**What:** Every locked interface this phase touches (`BotSettings`, `RankedLine`,
`BotGameSettings`) gains a new field that is `undefined` for every existing caller.
**When to use:** Any time a frozen/locked type (marked as such in a prior phase's doc comments)
needs new capability without breaking its contract.
**Example:**
```typescript
// Source: frontend/src/lib/engine/selectBotMove.ts (existing pattern, BotSettings)
export interface BotSettings {
  elo: number;
  blend: number;
  budget: Omit<SearchBudget, 'elo' | 'policyTemperature'>;
  /** NEW (Phase 182, STYLE-05): optional bot-only style params. `undefined` runs the
   * exact current code path — no reweight call, no shaping pass (D-03). */
  style?: BotStyleParams;
}
```

### Pattern 2: The `BookWeightingFn` composition seam (already built for this exact purpose)
**What:** `openingBook.ts`'s `selectBookMove` takes a `weighting: BookWeightingFn` parameter
defaulting to `maiaPolicyWeighting`. A style's weighting function should COMPOSE with the base
one — multiply the base Maia-plausibility weight by a curated-line boost — never replace it
outright (Trickster still needs Maia to tie-break among multiple style lines per D-06).
**When to use:** STYLE-01.
**Example:**
```typescript
// Source: frontend/src/lib/engine/openingBook.ts (existing BookWeightingFn contract)
export function styleBookWeighting(
  styleLinePrefixes: ReadonlySet<string>,
  boostMultiplier: number,
): BookWeightingFn {
  return (candidates, rawPolicy) => {
    const base = maiaPolicyWeighting(candidates, rawPolicy); // reuse, don't reimplement
    const boosted: Record<string, number> = {};
    for (const { uci, san } of candidates) {
      const w = base[uci];
      if (w === undefined) continue;
      // caller passes the joined history+san key; membership test happens
      // one level up (resolveBookMove needs the move-history prefix, not
      // just the candidate's own SAN) — see Pitfall 2 below.
      boosted[uci] = styleLinePrefixes.has(san) ? w * boostMultiplier : w;
    }
    return boosted;
  };
}
```

### Pattern 3: Sentinel-preserving extension of `wouldBotAcceptDraw`
**What:** `rootPracticalScore: number | null`'s `null` sentinel (Phase 169.5, book window) MUST
still refuse a draw for a styled bot — contempt shifts the *threshold*, it never overrides the
"never decide off a number we never computed" rule.
**When to use:** STYLE-02/D-09.
**Example:**
```typescript
// Source: frontend/src/lib/botDrawGate.ts (extend, do not replace)
export function wouldBotAcceptDraw(
  rootPracticalScore: number | null,
  chess: Chess,
  contempt = 0, // NEW optional param, default 0 = today's exact behavior
): boolean {
  if (rootPracticalScore === null) return false; // sentinel discipline preserved
  const drawValue = 0.5 - contempt; // D-09: contempt shifts the accept target, not the band width
  const isNearEqual = Math.abs(rootPracticalScore - drawValue) <= DRAW_ACCEPT_SCORE_BAND;
  if (!isNearEqual) return false;
  return queensAreOff(chess) || chess.moveNumber() >= DRAW_ACCEPT_MIN_FULLMOVE;
}
```

### Pattern 4: chess.js move-feature classification (the one genuinely new piece)
**What:** Cheap, per-candidate-move feature flags derived from chess.js's verbose move object —
no new library, no board re-derivation beyond what `.moves({verbose:true})` already returns.
**When to use:** STYLE-03 (prior reweighting).
**Example:**
```typescript
// Source: chess.js 1.4.0 Move API (captured/flags/piece/color/from/to), verified against
// frontend/src/lib/engine/botSampling.ts's existing chess.js usage pattern
import { Chess, type Move } from 'chess.js';

export interface MoveFeatures {
  isCheck: boolean;      // move.san includes '+' or '#'
  isCapture: boolean;    // move.flags includes 'c' or 'e' (en passant)
  isPawnAdvance: boolean;// move.piece === 'p' && !isCapture
  isPawnStorm: boolean;  // pawn advance into the opponent's half (rank >= 5 for white, <=4 for black)
  isExchange: boolean;   // capture where |value(captured) - value(mover piece)| is small (a "trade")
  isRetreat: boolean;    // non-pawn piece moving toward its own back rank
}

const PIECE_VALUE: Record<string, number> = { p: 1, n: 3, b: 3, r: 5, q: 9, k: 0 };

export function classifyMoveFeatures(move: Move): MoveFeatures {
  const isCapture = move.flags.includes('c') || move.flags.includes('e');
  const isCheck = move.san.includes('+') || move.san.includes('#');
  const isPawnAdvance = move.piece === 'p' && !isCapture;
  const fromRank = Number(move.from[1]);
  const toRank = Number(move.to[1]);
  const isPawnStorm =
    move.piece === 'p' && (move.color === 'w' ? toRank >= 5 : toRank <= 4);
  const capturedValue = move.captured ? (PIECE_VALUE[move.captured] ?? 0) : 0;
  const moverValue = PIECE_VALUE[move.piece] ?? 0;
  const isExchange = isCapture && Math.abs(capturedValue - moverValue) <= 1;
  const isRetreat =
    move.piece !== 'p' &&
    (move.color === 'w' ? toRank < fromRank : toRank > fromRank);
  return { isCheck, isCapture, isPawnAdvance, isPawnStorm, isExchange, isRetreat };
}
```

### Anti-Patterns to Avoid
- **Reimplementing weighted sampling inside `botStyle.ts`:** `botSampling.ts`'s internal
  `weightedPick` already handles unnormalized weights correctly (documented in
  `maiaPolicyWeighting`'s comment — "no renormalization math... a filtered-but-unnormalized
  subset IS the renormalized-over-subset result"). A style's prior-reweight function should
  return unnormalized weights and let `samplePolicy` do the walk — do not add a normalization
  step.
- **Deriving resign/draw state from a fresh per-call computation inside `botDrawGate.ts`:**
  hysteresis (D-08's "N consecutive own turns below threshold") is inherently stateful across
  turns — it must live as a counter in `useBotGame.ts`'s refs (mirroring `hasLeftBookRef`'s
  latch-in-a-ref pattern), NOT inside the pure `botDrawGate.ts` functions, which must stay
  call-and-forget pure predicates over their arguments.
- **Reading `mctsSearch`'s sorted `RankedLine[]` array order as anything but display order:**
  `buildRankedLines` sorts by findability-weighted `rankScore`, never `practicalScore` — this is
  called out three times in the existing code (D-06 in `selectBotMove.ts`, `sampleRankedLines`'s
  doc comment, `argmaxLine`'s doc comment). Score shaping must read/write `practicalScore`
  explicitly per line, never assume `lines[0]` is best.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Weighted proportional sampling over a `Record<string, number>` | A new weighted-random-pick function | `samplePolicy`/`weightedPick` (`botSampling.ts`) | Already handles empty/degenerate/NaN-weight edge cases (D-13) and UCI-ascending deterministic tie-breaks (D-12); a second implementation risks silently diverging on the edge cases |
| Softmax sampling over `RankedLine[]` | A second softmax helper for a style-adjusted score | `sampleRankedLines` (`botSampling.ts`) — feed it style-shaped `practicalScore` values, don't reimplement the softmax | Already numerically stable (max-subtraction trick) and has the `tau<=0` argmax short-circuit; style shaping should only ever transform `RankedLine.practicalScore` inputs, never re-derive its own softmax |
| Seeded randomness for deterministic tests | `Math.random()` or a new PRNG | `mulberry32` (`botSampling.ts`) | Already the project's canonical deterministic-test RNG; reuse gives distribution tests the same reproducibility guarantee every other engine test has |
| ECO-line prefix matching | A custom trie/prefix search | `loadOpeningPrefixSet()` (`lib/openings.ts`) + `getBookCandidates` (`openingBook.ts`) | The prefix set is already built once and cached; `getBookCandidates` already does the exact "is `[...history, candidateSan]` a prefix of some line" test a style-line filter also needs |

**Key insight:** Every "new" capability in this phase is a thin, pure, additive transform
layered on top of primitives the last four phases (153-171) already built and froze for exactly
this purpose. The only load-bearing new logic is the move-feature classifier — everything else
is composition.

## Common Pitfalls

### Pitfall 1: Floor-check-before-weighting order in the book seam
**What goes wrong:** A style's book-weighting function accidentally gets consulted by the
RAW-policy floor check (`BOOK_POLICY_FLOOR`), making the floor un-triggerable for a boosted
style line even when Maia rates it as implausible.
**Why it happens:** `selectBookMove`'s doc comment explicitly warns about this
("the floor is checked against the RAW rawPolicy values... never against weighting's output...
a future persona's weighting may reshape the distribution arbitrarily, so the exit rule must
never depend on its output either way"). A careless refactor moving the floor check after the
`weighting()` call would silently defeat the book's own safety valve for boosted styles
specifically (the case it matters most for).
**How to avoid:** Do not touch `selectBookMove`'s order of operations at all — only pass a new
`weighting` argument through the existing 4-step pipeline; the floor check already reads
`rawPolicy` directly and is untouched by this phase.
**Warning signs:** A style's opening book plays absurd/refuted lines the raw Maia policy rates
near-zero, well past what a human at that ELO would ever consider.

### Pitfall 2: `styleBookWeighting`'s membership test needs the JOINED prefix, not the bare SAN
**What goes wrong:** Curated style lines are naturally stored as full move sequences ("1. e4 e5
2. Ke2" → `"e4 e5 Ke2"`), but `BookWeightingFn`'s signature only receives `candidates`
(`{uci, san}` for THIS ply) and `rawPolicy` — it does NOT receive the move history. A naive
`styleLinePrefixes.has(candidate.san)` check (as sketched in Pattern 2 above) only works for a
line's FIRST move; every subsequent ply needs the full joined prefix to disambiguate (e.g. many
lines share a first move).
**Why it happens:** The existing `BookWeightingFn` type was deliberately kept minimal (just
candidates + rawPolicy) because `maiaPolicyWeighting` doesn't need history. A style's weighting
does.
**How to avoid:** Either (a) curry the move history into the returned closure at
`resolveBookMove`'s call site (the caller already has `moveHistorySan` — pass it when
constructing the per-turn `styleBookWeighting(...)` closure), or (b) store the style's prefix
set keyed by full joined sequences and thread `moveHistorySan` through an extended (but
backward-compatible, since `BookWeightingFn` itself is a type alias, not a frozen export)
closure factory. Do NOT change `BookWeightingFn`'s own signature — `maiaPolicyWeighting`'s
existing 2-arg shape must keep compiling unchanged.
**Warning signs:** A style's book boost applies to the wrong branch of a multi-line family
(e.g. boosting every Sodium Attack sub-variation's first move regardless of what follows).

### Pitfall 3: Resign/draw hysteresis state placement
**What goes wrong:** Consecutive-turns-below-threshold hysteresis (D-08) gets built as module-level
mutable state or accidentally derived fresh each call, either leaking across games (module state)
or never accumulating (fresh-each-call).
**Why it happens:** Every existing per-game counter in `useBotGame.ts` (`hasLeftBookRef`,
`movesSinceLastDeclineRef`, `lastRootPracticalScoreRef`) is a `useRef` reset in `newGame()` —
this is the established pattern, but it's easy to instead reach for a plain module constant
while prototyping the pure `botDrawGate.ts` predicate.
**How to avoid:** Mirror the existing refs exactly: a new `consecutiveLowScoreTurnsRef` (or
similar) in `useBotGame.ts`, reset in `newGame()` alongside the other four latches, incremented/reset
inside `runBotTurn`'s post-move grade callback (same site `lastRootPracticalScoreRef` already
updates).
**Warning signs:** A bot resigns immediately after its FIRST bad move (no hysteresis) or never
resigns at all across a whole game (state not persisted/incremented).

### Pitfall 4: `RankedLine.childScoreSpread` nullability and the concurrency-determinism note
**What goes wrong:** Treating `childScoreSpread` as always present, or assuming its value is
comparable across two `mctsSearch` runs at different `budget.concurrency` values.
**Why it happens:** A root child that was selected but never itself expanded (e.g. a
low-probability move only visited once during a shallow search) has zero or one grandchildren —
spread is undefined for 0 children and trivially 0 for exactly 1. Separately, `mctsSearch.ts`'s
own header states determinism holds "PER concurrency level" only — a style's variance-preference
shaping reading `childScoreSpread` will see different values at c=1 vs c=4 for the SAME position,
which is expected, not a bug to chase.
**How to avoid:** Type `childScoreSpread: number | null`; treat `null` as "no variance signal,
apply no variance bonus" in the score-shaping function. Do not attempt to make variance shaping
concurrency-invariant — `FLAWCHESS_BOT_CONCURRENCY` is pinned to 4 for bot play (`botBudget.ts`),
so in practice the live game always sees the same concurrency; only cross-harness comparisons
(app vs. a differently-configured test) would see this drift, which is already how every other
`RankedLine` field behaves.
**Warning signs:** A "TypeError: undefined is not a number" in the score-shaping function on a
low-visit line, or a variance-preference unit test that flakes when `budget.concurrency` differs
between fixture and production.

### Pitfall 5: `selectBotMove`'s two-regime split means style shaping needs TWO separate hooks, not one
**What goes wrong:** Attempting to write a single `applyStyle(...)` function called once inside
`selectBotMove` that handles both prior reweighting and score shaping, then discovering the two
regimes operate on structurally different data (`Record<string, number>` raw policy vs.
`RankedLine[]`) at different points in the control flow (`blend<=0` early-return vs. after the
`search()` call).
**Why it happens:** STYLE-03 and STYLE-04 read as "the same style, two rungs" in the
requirements, tempting a single unified entry point.
**How to avoid:** Ship two distinct pure functions (`applyStylePriorReweighting` and
`applyStyleScoreShaping`) as the CONTEXT.md canonical refs already imply ("blend≤0 branch:
prior reweighting hooks between deps.policy() and samplePolicy"; "search branch: score shaping
transforms rankedLines before argmax/sampleRankedLines") — both read from the SAME
`BotStyleParams` object but operate on disjoint data shapes and are called from disjoint
branches of `selectBotMove`'s existing `if (blend <= 0) { ... } ... ` structure.
**Warning signs:** A function signature trying to accept `Record<string,number> | RankedLine[]`
as a union parameter, or `selectBotMove`'s currently-clean regime branches growing shared
conditional logic that re-checks `blend` a second time inside a "unified" style helper.

## Code Examples

### Prior reweighting hook point (STYLE-03)
```typescript
// Source: frontend/src/lib/engine/selectBotMove.ts (existing, annotated with the new call site)
if (blend <= 0) {
  const rawPolicy = await deps.policy(fen, settings.elo, side);
  const styledPolicy = settings.style
    ? applyStylePriorReweighting(rawPolicy, fen, settings.style) // NEW, pure, sync
    : rawPolicy; // D-03: undefined style ⇒ byte-identical to today
  const sampled = samplePolicy(styledPolicy, deps.rng);
  return sampled ?? fallbackMove(fen, deps.rng);
}
```

### Score shaping hook point (STYLE-04)
```typescript
// Source: frontend/src/lib/engine/selectBotMove.ts (existing, annotated with the new call site)
const snapshot = await search(fen, budget, deps, () => {}, signal);
const lines: RankedLine[] = settings.style
  ? applyStyleScoreShaping(snapshot.rankedLines, settings.style) // NEW, pure, sync, additive only
  : snapshot.rankedLines;
// argmaxLine / sampleRankedLines below are UNCHANGED — they already read
// practicalScore off whatever RankedLine[] they're given.
```

### Draw contempt threading through `useBotGame.ts`
```typescript
// Source: frontend/src/hooks/useBotGame.ts's existing draw-resolution effect (line ~863),
// extended with the style's contempt knob
const contempt = settings.style?.contempt ?? 0; // D-03: undefined style ⇒ contempt 0 ⇒ unchanged
const accepts = wouldBotAcceptDraw(lastRootPracticalScoreRef.current, chessRef.current, contempt);
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Bot never resigns/offers a draw (Phase 169 D-02/D-03) | Styled bots CAN resign per a hysteresis threshold; draw accept gains a contempt-shifted target (D-07 of this phase, superseding 169's D-02/D-03 for STYLED bots only) | This phase (182) | Unstyled/Custom-mode bots keep the exact old behavior by construction (D-03) |
| Single shared `maiaPolicyWeighting` for all bot book play (Phase 169.5) | Per-style `BookWeightingFn` composed on top of it | This phase (182) | Book behavior for unstyled play is byte-identical (default param unchanged) |

**Deprecated/outdated:** Nothing in this phase deprecates prior work — every change is additive
per D-03's explicit design goal.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Curated per-style opening line boost of ~×20-50 (D-06) is the right order of magnitude to make style lines dominate without breaking the raw-policy floor's safety valve | Architecture Patterns / Pattern 2 | Too low: style identity invisible in the first 10 moves (the "cheapest, most perceptible" lever per SEED-098); too high: numerically it barely matters since `weightedPick` walks a cumulative distribution — an excessive multiplier only matters if a style line's raw Maia weight is already tiny relative to a non-style candidate, in which case ×50 vs ×20 is unlikely to change perceived variety. Low risk. |
| A2 | The move-feature multiplier magnitudes for prior reweighting (per D-12, "~0.02-0.05 in small expected-score units" for score bonuses; feature multipliers for prior reweighting have no equivalent stated range) will land in a "visible but not strength-distorting" zone through iterative hand-tuning against the D-11 measurement script | Architecture Patterns / Don't Hand-Roll | Untuned values could make Attacker play unrecognizably weak/random at Human rungs, or make the shift statistically invisible; mitigated by the measurement script's explicit purpose (iterate until visible without gross distortion) |
| A3 | `childScoreSpread` computed as `max(grandchild.value) - min(grandchild.value)` over a root child's own children (grandchildren of root) is the correct "variance/sharpness" proxy the seed's "wider-spread child" language refers to, rather than e.g. variance across `modalPath` alternatives | Architecture / Pattern in diagram | If the intended signal is something else (e.g. spread of visit-weighted outcomes, not raw value range), the variance-preference lever would reward the wrong lines; low-medium risk, straightforward to redefine at plan/execute time since the field is purely additive |
| A4 | Curated per-style SAN line lists (D-05) can find sufficient coverage in `openings.tsv`'s 3,641-line ECO corpus for all 4 styles, not just Trickster | Summary | Verified for Trickster specifically (Bongcloud/Halloween/Sodium/Napoleon/Grob/Barnes all present as named lines); Attacker (gambits), Grinder (exchange/simplifying lines), and Wall (London/Colle/Stonewall/Caro-Kann systems) were spot-checked and also present (`grep -ic gambit` found 100+ matches; London/Colle/Stonewall system lines confirmed present) but the FULL curated lists per D-05 are execute-time work, not verified exhaustively here |

**If this table is empty:** N/A — see rows above.

## Open Questions (RESOLVED)

1. **Exact `childScoreSpread` semantics (see Assumption A3)**
   - What we know: D-10 says "additive optional child-score-spread field on `RankedLine`,
     reported by `mctsSearch` — a statistic the tree already computes."
   - What's unclear: whether "the tree already computes" means the grandchild-value spread
     (as this research assumes) or some other already-materialized statistic (e.g.
     `rootChildValueExtremes`'s `maxValue - minValue`, which is a ROOT-level statistic across
     all root children, not per-child).
   - Recommendation: the planner should pick ONE precise definition at plan time and document it
     in `types.ts`'s doc comment for the new field, following the project's convention of citing
     the decision that fixes each field's shape (see `types.ts`'s existing header pattern).
   - **RESOLVED (182-01 Task 1):** `childScoreSpread` is fixed as `max(grandchild.value) -
     min(grandchild.value)` over a root child's own children (the per-child grandchild-value
     range, Assumption A3), documented in the `types.ts` doc comment citing D-10.

2. **Resign check dispatch point in `useBotGame.ts`**
   - What we know: D-08 says Light/Deep personas resign when `practicalScore` stays below a
     threshold for N consecutive own turns past a minimum move number; the canonical refs note
     "resign check after each bot search completes."
   - What's unclear: whether the resign check should run inside the same `pool.grade(...).then(...)`
     callback that already updates `lastRootPracticalScoreRef` (best-effort, async, non-blocking),
     or synchronously right after `commitMove` in `runBotTurn` (which would need to wait for that
     grade first, delaying the resign decision by one extra grade round-trip).
   - Recommendation: reuse the existing `pool.grade(...).then(...)` callback site (mirrors D-01's
     "reuse the grading provider it already has" precedent for the draw-accept score) — resign
     decisions naturally lag by the same one grade-call latency the draw-accept score already
     tolerates.
   - **RESOLVED (182-07 Task 2):** the resign check runs inside the existing
     `pool.grade(...).then(...)` callback that already updates `lastRootPracticalScoreRef`, gated
     on `settings.style`; the `consecutiveLowScoreTurnsRef` hysteresis counter is
     incremented/reset there and `wouldBotResign` dispatches `finalizeGame({reason:'resignation'})`.

3. **Style-line prefix membership across BOTH colors at each ply**
   - What we know: D-05 requires curated lines "both colors per style."
   - What's unclear: whether a single style's book-weighting closure needs to know which color
     the bot is playing (a style line curated as "White plays the London" only applies when the
     bot is White) — `openingBook.ts`'s existing `selectBookMove` is color-agnostic (it only
     checks SAN-prefix membership against whatever `legalMoves` the caller passes for the side
     to move).
   - Recommendation: curate the per-style prefix sets as two separate sets (white-side lines,
     black-side lines) mirroring `trollOpenings.ts`'s own `WHITE_TROLL_KEYS`/`BLACK_TROLL_KEYS`
     split, and have `resolveBookMove`'s style-aware call site pick the correct set from
     `chess.turn()`.
   - **RESOLVED (182-03 + 182-04 + 182-07 Task 1):** curated lines are split into white-side and
     black-side sets (182-03 `styleOpeningLines.ts` / `styleLinesFor(style, side)`); the
     `styleBookWeighting` factory (182-04) consumes the side-correct set, and `resolveBookMove`
     (182-07 Task 1) picks the color set from `chess.turn()` at the call site.

## Environment Availability

Skipped — this phase has no external dependencies beyond the already-installed `chess.js`
package and existing project tooling (vitest, TypeScript). No new services, CLIs, or runtimes.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest (existing frontend suite) |
| Config file | `frontend/vite.config.ts` (no dedicated `test:` block — 5s default `testTimeout` applies project-wide per prior memory note) |
| Quick run command | `cd frontend && npx vitest run src/lib/engine/botStyle.test.ts` |
| Full suite command | `cd frontend && npm test -- --run` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| STYLE-01 | Styled bot follows its curated book line over generic book/search | unit | `npx vitest run src/lib/engine/openingBook.test.ts` (extend with style-weighting cases) | ✅ file exists, ❌ style cases — Wave 0 |
| STYLE-02 | Grinder-style bot does not resign/accept-draw where neutral bot would; contempt configurable | unit | `npx vitest run src/lib/botDrawGate.test.ts` (extend) | ✅ file exists, ❌ resign/contempt cases — Wave 0 |
| STYLE-03 | Human-rung move distribution shifts toward style features (measured via seeded distribution test, mirroring `openingBook.test.ts`'s "variety" test pattern) | unit + measurement script | `npx vitest run src/lib/engine/botStyle.test.ts` + `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/style-lever-measurement.mjs` | ❌ both — Wave 0 |
| STYLE-04 | Light/Deep-rung move choice reflects score bonus/malus + variance preference | unit | `npx vitest run src/lib/engine/botStyle.test.ts` + `npx vitest run src/lib/engine/treeCommon.test.ts` (extend for `childScoreSpread`) | ❌ new file, ✅ existing file to extend — Wave 0 |
| STYLE-05 | `botSampling.ts` stays pure; no style param derives from player rating/play; never reuses `policyTemperature` | unit (structural/type-level) + code review | `npx vitest run src/lib/engine/botSampling.test.ts` (unchanged — proves the file wasn't touched) + `tsc -b` (proves `BotSettings.budget`'s `Omit<>` exclusion still compiles) | ✅ existing (regression-only) |

### Sampling Rate
- **Per task commit:** targeted `npx vitest run <changed-test-file>`
- **Per wave merge:** `cd frontend && npm run lint && npm test -- --run`
- **Phase gate:** Full suite green before `/gsd-verify-work`, plus a run of the new
  `style-lever-measurement.mjs` script with its report reviewed in UAT (D-11/D-12).

### Wave 0 Gaps
- [ ] `frontend/src/lib/engine/botStyle.test.ts` — new file, covers STYLE-01/02/03/04 pure helpers
      (`applyStylePriorReweighting`, `applyStyleScoreShaping`, `classifyMoveFeatures`,
      `styleBookWeighting` factory)
- [ ] `frontend/src/lib/engine/openingBook.test.ts` — extend with a styled-weighting composition
      case (proves the floor-check-before-weighting order from Pitfall 1 still holds)
- [ ] `frontend/src/lib/botDrawGate.test.ts` — extend with contempt-shifted accept cases and the
      new resign predicate's hysteresis cases
- [ ] `frontend/src/lib/engine/treeCommon.test.ts` — extend `buildRankedLines` tests for
      `childScoreSpread` (present/null cases)
- [ ] `scripts/style-lever-measurement.mjs` — new Node measurement script (D-11), modeled on
      `scripts/gem-elo-calibration.mjs`'s TSV-emission + `frontend-alias-hook.mjs` import pattern
- [ ] Framework install: none — Vitest and chess.js already present

## Security Domain

`security_enforcement` is not explicitly disabled in `.planning/config.json` (absent = enabled),
but this phase's ASVS surface is minimal — it is a pure client-side game-logic extension with no
new network calls, no new persisted data, no new user input surface in this phase (the setup
screen wiring that would accept user-facing style selection is explicitly Phase 183's job).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | unchanged — no auth surface touched |
| V3 Session Management | no | unchanged |
| V4 Access Control | no | unchanged |
| V5 Input Validation | yes (forward-looking) | `BotStyleParams` numeric fields (multipliers, bonuses, contempt, thresholds) should be finite/range-clamped at the point Phase 183 eventually accepts them from any external source (localStorage, a future settings UI) — mirror `botSetupSettings.ts`'s existing `isNumberInRange` validator pattern (WR-01 there was exactly an unvalidated-range bug that silently corrupted a stored game). This phase ships the params as plain exported constants (trusted, not user input), so no validator is strictly required YET, but the plan should note this as a forward constraint for Phase 183. |
| V6 Cryptography | no | not applicable |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| A future caller threading player-derived data into `BotStyleParams` (defeating BOT-03) | Tampering (of the non-adaptive invariant) | Structural: keep `BotStyleParams` a plain data object with no function fields, sourced only from the 4 exported bundle constants in this phase; Phase 183's registry — not this phase — is the only future call site, and even there the style is chosen by PERSONA slot, never derived from `useUserProfile()`/rating data (mirrors the existing `resolveDefaultBotElo`'s explicit "UI DEFAULT ONLY, never fed into selectBotMove" pattern) |
| A style's numeric knob (contempt, multiplier) reaching `NaN`/`Infinity` and silently degrading move selection | Denial of Service (degenerate distribution) | Reuse `weightedPick`'s existing `Number.isFinite(total)` guard (D-13) — any style-reweighted policy that produces a degenerate total already falls through to `fallbackMove` today; no new guard needed as long as style functions return plain numbers into the SAME `Record<string, number>`/`RankedLine[]` shapes those guards already cover |

## Sources

### Primary (HIGH confidence)
- `frontend/src/lib/engine/selectBotMove.ts`, `botSampling.ts`, `openingBook.ts`,
  `botDrawGate.ts`, `types.ts`, `treeCommon.ts`, `mctsSearch.ts`, `useBotGame.ts`,
  `botBudget.ts`, `playStyle.ts`, `botSetupSettings.ts` — read directly, verified against the
  phase's canonical refs [VERIFIED: local codebase read]
- `frontend/public/openings.tsv` — grepped directly for Trickster's troll-opening coverage
  (Bongcloud/Halloween/Sodium/Napoleon/Grob/Barnes all confirmed present) [VERIFIED: local file
  grep]
- `frontend/src/data/trollOpenings.ts` — read directly, confirms D-05's note that its data is
  position-key-shaped (not SAN-prefix-shaped) [VERIFIED: local codebase read]
- `frontend/package.json` — confirmed `chess.js` `^1.4.0` is the only chess dependency
  [VERIFIED: local file read]
- `.planning/phases/182-style-levers/182-CONTEXT.md` — locked decisions D-01 through D-12,
  canonical refs, code context [user-provided locked decisions]
- `.planning/seeds/SEED-098-bot-personas-playstyle-layer.md` — explore-session locked decisions,
  per-rung lever table, caveats [user-provided locked decisions]

### Secondary (MEDIUM confidence)
- `scripts/gem-elo-calibration.mjs`, `scripts/calibration-harness.mjs` — read for header/
  structure conventions to model the new D-11 measurement script on (not read line-by-line in
  full; header + import pattern confirmed)

### Tertiary (LOW confidence)
None — this research relied entirely on direct codebase inspection; no web search was needed
since every seam is internal, already-documented project code.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies, chess.js version confirmed directly from package.json
- Architecture: HIGH — every integration seam (`BookWeightingFn`, `wouldBotAcceptDraw`,
  `RankedLine`, `selectBotMove`'s regime branches) is pre-existing code read directly, not
  inferred
- Pitfalls: HIGH — every pitfall in this document is traced to an explicit doc-comment warning
  already present in the codebase (e.g. `selectBookMove`'s "order of operations is load-bearing"
  comment, `mctsSearch.ts`'s determinism-scope note) rather than speculated
- Move-feature classifier design: MEDIUM — the chess.js API surface (`.flags`, `.captured`,
  `.piece`) is correct per the installed version's documented behavior, but exact multiplier
  magnitudes and the precise exchange/retreat thresholds are execute-time tuning (D-12), not
  verified against a live chess.js runtime in this research pass

**Research date:** 2026-07-21
**Valid until:** No expiry driver — this is an internal-codebase-only phase with no external
library version risk; re-research only if `selectBotMove.ts`/`openingBook.ts`/`botDrawGate.ts`
change again before this phase executes.
