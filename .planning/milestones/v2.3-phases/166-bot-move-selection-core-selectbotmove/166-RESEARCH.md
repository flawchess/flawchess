# Phase 166: Bot Move Selection Core (`selectBotMove`) - Research

**Researched:** 2026-07-11
**Domain:** Pure TypeScript orchestration over an already-shipped MCTS/Maia/Stockfish engine core (v2.0 FlawChess Engine); no new libraries, no new I/O.
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** The bot play-style slider is a blend parameter `b ∈ [0,1]`, NOT the analysis-board policy-temperature slider. `b=0` = Human end, `b=1` = Stockfish end. Sibling knob to the analysis Human↔Stockfish framing, not the same transform.
- **D-02:** `applyPolicyTemperature` is NOT used in `selectBotMove`. In a raw-sampling path there is no Stockfish to rescue anything, so temperature's polarity inverts vs. the analysis ranking pipeline — using it for sampling gives a non-monotonic (U-shaped) strength curve. Raw Maia (T=1) is the human end.
- **D-03:** Regime split — `b=0` → no MCTS, exactly one `policy()` call, sample raw Maia root policy (SC2). `b ∈ (0,1]` → run `mctsSearch`, choose from its `RankedLine[]`. A mild style discontinuity at `b=0⁺` is accepted by design.
- **D-04:** Practical-score sampling is a softmax over `RankedLine.practicalScore` (0-1, root-side-to-move expected score): `P(moveᵢ) ∝ exp(practicalScoreᵢ / τ(b))`. Uses raw `practicalScore`, NOT the findability-weighted `rankScore` — the root candidate set is already Maia-gated, so human-likeness dials in via `τ` only.
- **D-05:** `τ(b) = TAU_MAX · (1 − b)`, linear/monotone decreasing, `TAU_MAX = 0.10` (named constant, harness-refinable). A 0.10 expected-score gap favors the best move ~2.7x at the soft edge.
- **D-06:** `b=1` → pure deterministic argmax over `practicalScore` (UCI-ascending tie-break), per SC1. `mctsSearch`'s `RankedLine[]` is sorted by findability-weighted `rankScore`, NOT `practicalScore` — `argmaxLine` must scan explicitly, never trust array order. Short-circuit to argmax when `τ ≤ ε` to avoid divide-by-zero.
- **D-07:** Signature `selectBotMove(fen, settings, deps, signal?): Promise<string>`. `settings = { elo, blend, budget }`; `elo` → `budget.elo = { w: elo, b: elo }` (symmetric, SC3). `budget` (`maxNodes`/`maxPlies`/`concurrency`) passed IN by the caller (Phase 169 derives it from the clock). `deps = { policy, grade, rng, search? }`. `signal?: AbortSignal` passed through to `mctsSearch`, defaults to a never-aborting signal; `selectBotMove` supplies a no-op `onSnapshot` internally.
- **D-08:** `deps.search` defaults to `mctsSearch` imported directly, optional/injectable so unit tests can stub it and the Phase 168 harness can supply Node providers while using the SAME default `mctsSearch`.
- **D-09:** Split into an impure orchestrator (`selectBotMove`) and pure, sync, separately-exported helpers: `samplePolicy(policy, rng)`, `sampleRankedLines(lines, tau, rng)`, `argmaxLine(lines)`, `fallbackMove(fen, rng)`. Helpers unit-test on canned inputs — no workers, no async, no real search.
- **D-10:** RNG injected as `deps.rng: () => number` in `[0,1)`. `selectBotMove` only ever calls `rng()`. Live app passes a `Math.random`-backed rng; tests/harness pass a seeded PRNG.
- **D-11:** Seeded PRNG = a tiny inlined `mulberry32(seed)` (~5 lines, no dependency), exported for tests/harness. Fixed seed → deterministic selection (SC4).
- **D-12:** Weighted sampling = cumulative-distribution walk over candidates sorted UCI-ascending (same tie-break convention as `select.ts`/`truncateAndRenormalize`), so a given `rng()` draw always yields the same move regardless of Map/Record iteration order.
- **D-13:** Fallback (SC5) = uniform-random legal move. When the sampled distribution is empty/degenerate (`policy()` returns `{}`, all-zero weights, or MCTS yields no `RankedLine[]`): generate legal moves from the FEN via chess.js, sort UCI-ascending, pick uniformly via `rng()`. Covers both `b=0` and `b>0` regimes.
- **D-14:** A terminal position (no legal moves at all) is a caller precondition bug — `selectBotMove` throws a clear error there. SC5's "legal fallback" governs a degenerate *policy*, not a checkmate/stalemate position with zero legal moves.

### Claude's Discretion

- Exact names/paths of the new module(s) under `frontend/src/lib/engine/` (or a new `bot/` subdir), the `ε` threshold value for the argmax short-circuit, and the chess.js move-generation call shape.
- The precise `τ(b)` curve constant (`TAU_MAX = 0.10`) is the locked default but is explicitly harness-refinable in Phase 168 without a signature change.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope. User-results strength curve fitting remains explicitly out of this milestone (SEED-091 decision #3); the Phase 168 anchor harness is engine-vs-anchor self-play and needs no user data.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BOT-01 | Bot blends the play-style slider from raw-Maia sampling (full-human) to argmax practical score (full-stockfish), practical-score-weighted sampling with slider-controlled sharpness in between. | D-01–D-06 fully specify the regime split, softmax formula, and τ curve; see Architecture Patterns § Pattern 1/2 and Code Examples for the exact implementation shape. |
| BOT-02 | Full-human end issues exactly one Maia inference per move (no MCTS), replies within ~1-2s on a mid-range phone at the fastest TC. | D-03's `b=0` branch calls `deps.policy()` exactly once, never `mctsSearch`; verified against `maiaQueue.ts`'s single-inference-per-`policy()`-call contract (one ONNX forward pass per queued FIFO batch). |
| BOT-03 | Bot plays its own configured ELO symmetrically, never adapts to player strength. | D-07's `budget.elo = { w: elo, b: elo }` construction is the single point of proof; `mctsSearch`'s per-node `policy()` call already keys ELO off `budget.elo[leaf.side]`, so symmetric input structurally guarantees symmetric behavior (see Common Pitfalls § Pitfall 3). |
| BOT-04 | Bot always returns a legal move; falls back gracefully on empty/degenerate policy. | D-13/D-14 define the exact fallback semantics and the terminal-position precondition boundary; see Code Examples § fallbackMove and Common Pitfalls § Pitfall 4. |
</phase_requirements>

## Summary

This phase adds no new runtime dependencies, no new I/O, and no new UI — it is a pure orchestration layer over engine primitives that Phases 153-159 already shipped and froze (`mctsSearch`, `EngineProviders`, `SearchBudget`, `RankedLine`, `truncateAndRenormalize`/`select.ts`'s UCI-ascending tie-break convention). The entire research surface is: (1) correctly reading the frozen contracts so `selectBotMove` composes them without reimplementing anything, (2) getting three small numerically-sensitive helpers right — softmax-over-`practicalScore` sampling, a canonical mulberry32 PRNG, and a UCI-ascending cumulative-distribution walk — and (3) respecting the CONTEXT.md decisions verbatim, since D-01 through D-14 already resolve every design question a "从 scratch" research pass would normally have to answer (blend curve shape, tie-breaks, fallback triggers, terminal-position handling).

The one area needing genuine engineering care beyond the locked decisions is **plumbing discipline**: `RankedLine[]` from `mctsSearch` is sorted by `rankScore` (findability-weighted), not `practicalScore`, and every consumer in this phase (`argmaxLine`, `sampleRankedLines`) must explicitly scan for `practicalScore` rather than trusting array order — this exact confusion is called out three times independently in the existing codebase (`treeCommon.ts`'s `buildRankedLines` docstring, `select.ts`'s D-06 comment, and CONTEXT.md D-06), which signals it is a genuine, easy-to-reintroduce bug class rather than a one-off caution.

**Primary recommendation:** Build `selectBotMove` as a thin async orchestrator in a new `frontend/src/lib/engine/selectBotMove.ts` (co-located with its sibling primitives) that calls exactly one of `deps.policy()` (b=0) or `deps.search ?? mctsSearch` (b>0), then delegates to synchronous, separately-exported, unit-testable helpers for every decision (`samplePolicy`, `sampleRankedLines`, `argmaxLine`, `fallbackMove`, `mulberry32`) — mirroring the `mctsSearch.ts`/`select.ts`/`treeCommon.ts` split already established in this codebase (impure orchestrator + pure helper modules).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Move selection (blend regime, sampling, argmax, fallback) | Browser / Client (pure lib, no framework) | — | `selectBotMove` is a plain TS module under `frontend/src/lib/engine/`, imported by both the browser bot-game loop (Phase 169, React) and a headless Node harness (Phase 168) — it cannot depend on React or DOM, only on injected async providers (D-07/D-08). |
| Maia policy inference | Browser / Client (Web Worker) in-app; Node ONNX runtime in harness | — | `deps.policy` is injected; the app supplies `maiaQueue.ts`'s worker-backed provider, the Phase 168 harness supplies a Node onnxruntime provider. `selectBotMove` never imports either directly (provider-agnostic per phase goal). |
| Stockfish practical grading | Browser / Client (Web Worker pool) in-app; Node UCI process in harness | — | Same injection pattern via `deps.grade`; `selectBotMove` never imports `workerPool.ts` directly. |
| RNG / determinism | Browser / Client (pure function) | — | `deps.rng` is injected; live app uses `Math.random`, tests/harness use the exported `mulberry32` seeded PRNG (D-10/D-11). No server-side randomness is involved. |
| Legal-move fallback generation | Browser / Client (chess.js, already a frontend dependency) | — | `fallbackMove` uses chess.js's `Chess(fen).moves({ verbose: true })` — pure, synchronous, no network. |

## Standard Stack

### Core

No new libraries. This phase is 100% composition over already-installed, already-frozen internal modules.

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| chess.js | ^1.4.0 (already installed) | Legal move enumeration for the D-13 fallback (`Chess(fen).moves({ verbose: true })` → `.lan` gives the UCI string directly) | Already the project's sole chess-rules library; `treeCommon.ts`'s `applyUciMoveFen`/`terminalValue` and `sanToSquares.ts`'s `sanToUci` already establish the exact usage pattern this phase reuses (`${move.from}${move.to}${move.promotion ?? ''}`, or the equivalent `.lan` field — [VERIFIED: `node_modules/chess.js/dist/types/chess.d.ts` — `Move.lan: string` confirmed present in the installed version]). |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| (none) | — | — | — |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Inlined `mulberry32` (D-11, locked) | `seedrandom` npm package | Rejected by CONTEXT.md D-11 explicitly — mulberry32 is ~5 lines, adding a dependency for this is unjustified; also keeps the harness (Node) and app (browser) byte-identical without a package resolution difference between environments. |
| chess.js legal-move enumeration for fallback | Writing a hand-rolled legal-move generator | Never — chess.js is already the project's chess-rules source of truth (CLAUDE.md); hand-rolling move legality is exactly the kind of deceptively-complex problem CLAUDE.md's "Don't Hand-Roll" spirit and this project's existing conventions forbid. |

**Installation:**
```bash
# No new packages — this phase adds zero dependencies to package.json.
```

**Version verification:** chess.js is already pinned at `^1.4.0` in `frontend/package.json` [VERIFIED: `frontend/package.json` grep] and its installed `.d.ts` confirms the `Move.lan` field this phase's fallback helper needs. No version bump required.

## Package Legitimacy Audit

**Not applicable — this phase installs zero external packages.** No `npm install` runs as part of this phase; the only dependency touched (chess.js) is pre-existing and already vetted by prior phases (Phase 153+). Nothing to run through `gsd-tools query package-legitimacy check`.

## Architecture Patterns

### System Architecture Diagram

```
                         ┌─────────────────────────────────────────┐
                         │        selectBotMove(fen, settings,      │
                         │        deps, signal?)  [impure orchestr.] │
                         └───────────────┬───────────────────────┘
                                         │
                         settings.blend (b) read once
                                         │
                    ┌────────────────────┴────────────────────┐
                    │                                          │
              b === 0                                   b ∈ (0, 1]
                    │                                          │
                    ▼                                          ▼
       ┌─────────────────────────┐          ┌──────────────────────────────────┐
       │ ONE deps.policy(fen,     │          │ (deps.search ?? mctsSearch)(      │
       │ elo, side) call          │          │   fen, budget, {policy, grade},   │
       │ (D-03/BOT-02)             │          │   noopOnSnapshot, signal)         │
       └────────────┬─────────────┘          └────────────────┬──────────────────┘
                    │                                          │
                    ▼                                          ▼
       ┌─────────────────────────┐          ┌──────────────────────────────────┐
       │ samplePolicy(policy, rng) │          │ snapshot.rankedLines (RankedLine[])│
       │  [pure helper]            │          │  sorted by rankScore (NOT         │
       │  UCI-ascending cum-dist   │          │  practicalScore — Pitfall 1)      │
       │  walk (D-12)              │          └────────────────┬──────────────────┘
       └────────────┬─────────────┘                            │
                    │                              τ = TAU_MAX·(1−b) (D-05)
                    │                                          │
                    │                        τ ≤ ε? ───────────┼─────────── no
                    │                          │yes             │
                    │                          ▼                ▼
                    │              ┌───────────────────┐  ┌─────────────────────────┐
                    │              │ argmaxLine(lines)  │  │ sampleRankedLines(lines, │
                    │              │  [pure helper]      │  │ tau, rng) [pure helper]  │
                    │              │  scans practicalScore│  │ softmax over            │
                    │              │  explicitly (D-06)   │  │ practicalScore, UCI-     │
                    │              └──────────┬──────────┘  │ ascending cum-dist walk  │
                    │                         │              │ (D-04/D-12)              │
                    │                         │              └────────────┬─────────────┘
                    │                         │                           │
                    └─────────────┬───────────┴───────────────────────────┘
                                  │
                       distribution empty/degenerate? (D-13)
                                  │
                        yes ──────┴────── no
                         │                 │
                         ▼                 ▼
            ┌─────────────────────┐   return sampled/argmax UCI move
            │ fallbackMove(fen, rng)│
            │  [pure helper]         │
            │  chess.js legal moves, │
            │  UCI-ascending, pick   │
            │  uniformly via rng()   │
            │  (D-13) — OR throw if  │
            │  zero legal moves      │
            │  exist at all (D-14,   │
            │  caller precondition)  │
            └─────────────────────┘
```

### Recommended Project Structure

```
frontend/src/lib/engine/
├── selectBotMove.ts        # impure orchestrator (D-07/D-08/D-09) + type exports for settings/deps
├── botSampling.ts          # pure helpers: samplePolicy, sampleRankedLines, argmaxLine, fallbackMove, mulberry32
├── __tests__/
│   ├── selectBotMove.test.ts   # orchestrator regime-selection + injection tests (stub deps.search/policy)
│   └── botSampling.test.ts     # pure helper unit tests (canned RankedLine[]/policy fixtures, no workers/async)
```

Two files, not one, because the orchestrator (`selectBotMove.ts`) needs `mctsSearch`/`maiaQueue`/`workerPool` type imports (`EngineProviders`, `SearchBudget`, `RankedLine`) and is inherently async, while the helpers (`botSampling.ts`) are pure/sync and should be importable by the Phase 168 Node harness and unit tests without pulling in any async orchestration machinery — this mirrors the existing `mctsSearch.ts` (orchestrator) vs. `select.ts`/`treeCommon.ts` (pure helpers) split already established in this same directory. A `bot/` subdirectory is unnecessary churn for two files; keeping them flat in `engine/` alongside their sibling primitives (`mctsSearch.ts`, `select.ts`, `treeCommon.ts`) matches existing layout.

### Pattern 1: Regime dispatch on `blend` (D-03)

**What:** `selectBotMove` reads `settings.blend` exactly once and branches into one of two mutually exclusive paths — no MCTS at `b=0`, always MCTS at `b∈(0,1]`.
**When to use:** This IS the phase's central control-flow decision (BOT-01/BOT-02).
**Example:**
```typescript
// Source: composed from CONTEXT.md D-03/D-07/D-08 + frontend/src/lib/engine/guardrail.ts (SearchRunner shape)
import type { EngineProviders, SearchBudget, RankedLine } from './types';
import type { SearchRunner } from './guardrail';
import { mctsSearch } from './mctsSearch';
import { samplePolicy, sampleRankedLines, argmaxLine, fallbackMove } from './botSampling';

const TAU_MAX = 0.10; // D-05
const TAU_EPSILON = 1e-9; // Claude's discretion — short-circuit threshold for divide-by-zero guard

export interface BotSettings {
  elo: number;
  /** b ∈ [0,1]: 0 = full-human (raw Maia sample), 1 = full-stockfish (argmax practicalScore). */
  blend: number;
  budget: Omit<SearchBudget, 'elo'>; // caller (Phase 169) derives maxNodes/maxPlies/concurrency from the clock
}

export interface BotMoveDeps extends EngineProviders {
  rng: () => number; // [0,1) — D-10
  search?: SearchRunner; // defaults to mctsSearch — D-08
}

const NEVER_ABORT_SIGNAL = new AbortController().signal; // never aborts — D-07 default

export async function selectBotMove(
  fen: string,
  settings: BotSettings,
  deps: BotMoveDeps,
  signal: AbortSignal = NEVER_ABORT_SIGNAL,
): Promise<string> {
  const side = fen.split(' ')[1] === 'b' ? 'b' : 'w';

  if (settings.blend <= 0) {
    // D-03: b=0 -> exactly ONE policy() call, no MCTS (BOT-02).
    const rawPolicy = await deps.policy(fen, settings.elo, side);
    const sampled = samplePolicy(rawPolicy, deps.rng);
    return sampled ?? fallbackMove(fen, deps.rng);
  }

  const search = deps.search ?? mctsSearch;
  const budget: SearchBudget = { ...settings.budget, elo: { w: settings.elo, b: settings.elo } }; // D-07/BOT-03
  const snapshot = await search(fen, budget, deps, () => {}, signal); // no-op onSnapshot — selectBotMove never streams
  const lines: RankedLine[] = snapshot.rankedLines;

  if (settings.blend >= 1) {
    const best = argmaxLine(lines); // D-06 — deterministic argmax, never trusts array order
    return best ?? fallbackMove(fen, deps.rng);
  }

  const tau = TAU_MAX * (1 - settings.blend); // D-05
  if (tau <= TAU_EPSILON) {
    const best = argmaxLine(lines);
    return best ?? fallbackMove(fen, deps.rng);
  }
  const sampled = sampleRankedLines(lines, tau, deps.rng); // D-04/D-12
  return sampled ?? fallbackMove(fen, deps.rng);
}
```

### Pattern 2: Pure helpers return `null` on degenerate input, never throw (D-13)

**What:** Every sampling/argmax helper returns `string | null` — `null` signals "distribution was empty/degenerate", which the orchestrator interprets uniformly as "fall back" (D-13). This keeps the fallback trigger condition in exactly ONE place (the orchestrator's `?? fallbackMove(...)`), rather than duplicated inside each helper.
**When to use:** All four sampling/selection helpers (`samplePolicy`, `sampleRankedLines`, `argmaxLine`).
**Example:**
```typescript
// Source: composed from CONTEXT.md D-04/D-06/D-12/D-13 + frontend/src/lib/engine/select.ts's
// UCI-ascending tie-break convention (truncateAndRenormalize)

/** Cumulative-distribution walk over UCI-ascending-sorted (uci, weight) pairs (D-12). */
function weightedPick(entries: [string, number][], rng: () => number): string | null {
  const sorted = [...entries].sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0));
  const total = sorted.reduce((sum, [, w]) => sum + w, 0);
  if (total <= 0) return null; // degenerate: all-zero or empty (D-13 trigger)
  const draw = rng() * total;
  let cumulative = 0;
  for (const [uci, w] of sorted) {
    cumulative += w;
    if (draw < cumulative) return uci;
  }
  return sorted[sorted.length - 1]?.[0] ?? null; // floating-point edge case: draw === total exactly
}

export function samplePolicy(policy: Record<string, number>, rng: () => number): string | null {
  return weightedPick(Object.entries(policy), rng);
}

export function sampleRankedLines(
  lines: readonly RankedLine[],
  tau: number,
  rng: () => number,
): string | null {
  if (lines.length === 0) return null;
  // D-04: softmax over practicalScore, NOT rankScore.
  const weighted: [string, number][] = lines.map((l) => [l.rootMove, Math.exp(l.practicalScore / tau)]);
  return weightedPick(weighted, rng);
}

export function argmaxLine(lines: readonly RankedLine[]): string | null {
  if (lines.length === 0) return null;
  // D-06: mctsSearch's RankedLine[] is sorted by rankScore, NOT practicalScore —
  // must scan explicitly, never trust lines[0].
  let best: RankedLine | null = null;
  for (const line of lines) {
    const isBetter =
      best === null ||
      line.practicalScore > best.practicalScore ||
      (line.practicalScore === best.practicalScore && line.rootMove < best.rootMove);
    if (isBetter) best = line;
  }
  return best?.rootMove ?? null;
}
```

### Pattern 3: `mulberry32` — the locked seeded PRNG (D-11)

**What:** A ~5-line, dependency-free, deterministic 32-bit PRNG. Public-domain-equivalent, one of the most widely used tiny JS PRNGs for exactly this use case (game/simulation determinism) [CITED: https://gist.github.com/tommyettinger/46a874533244883189143505d203312c — canonical reference gist; also documented at https://github.com/bryc/code/blob/master/jshash/PRNGs.md].
**When to use:** Tests and the Phase 168 harness inject this; the live app injects a thin `() => Math.random()` wrapper instead (D-10 — a played game needs no reproducibility).
**Example:**
```typescript
// Source: canonical public-domain mulberry32 implementation
// [CITED: https://gist.github.com/tommyettinger/46a874533244883189143505d203312c]
export function mulberry32(seed: number): () => number {
  let a = seed;
  return function (): number {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
```

### Pattern 4: Legal-move fallback via chess.js `.lan` (D-13)

**What:** Uniform-random legal move, generated fresh from the FEN — never derived from a stale candidate set.
**When to use:** Whenever `samplePolicy`/`sampleRankedLines`/`argmaxLine` return `null`.
**Example:**
```typescript
// Source: pattern established by frontend/src/lib/sanToSquares.ts's sanToUci
// and frontend/src/lib/engine/treeCommon.ts's applyUciMoveFen (chess.js v1.4 Move.lan)
import { Chess } from 'chess.js';

export function fallbackMove(fen: string, rng: () => number): string {
  const chess = new Chess(fen);
  const moves = chess.moves({ verbose: true }); // Move[] — .lan is UCI (from+to+promotion)
  if (moves.length === 0) {
    // D-14: a terminal position (checkmate/stalemate) reaching this helper is a
    // caller precondition bug — the game loop must detect end states BEFORE
    // calling selectBotMove. Throw with a clear message, never silently return "".
    throw new Error(`fallbackMove: no legal moves for fen "${fen}" (terminal position reached selectBotMove)`);
  }
  const ucis = moves.map((m) => m.lan).sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
  const idx = Math.min(Math.floor(rng() * ucis.length), ucis.length - 1); // clamp against rng()===1 edge case
  return ucis[idx] as string;
}
```

### Anti-Patterns to Avoid

- **Reading `rankedLines[0]` as "the best move":** `mctsSearch`'s `RankedLine[]` is sorted by findability-weighted `rankScore` (`treeCommon.ts`'s `buildRankedLines`), not `practicalScore`. At `b=1` this would silently make the bot weaker than SC1 specifies (D-06). Every consumer in this phase must scan `practicalScore` explicitly.
- **Routing `b=0` through `mctsSearch` with a 1-node budget "for consistency":** this would violate BOT-02 (exactly one Maia inference) — `mctsSearch` always calls `policy()` at least once per expansion PLUS the root truncation/hard-cap machinery is unnecessary overhead for a single inference; D-03 requires the direct `deps.policy()` call.
- **Using `applyPolicyTemperature` anywhere in this phase:** D-02 explicitly forbids it — it's an analysis-ranking-pipeline transform whose polarity inverts under raw sampling (no Stockfish rescue), which would produce a non-monotonic strength curve and break Phase 168 calibration.
- **Letting `deps.rng()` return exactly `1`:** `Math.random()` never returns 1, but a test-injected fake could. The cumulative-walk and fallback index calculations above defensively clamp (`Math.min(..., length-1)`, the `?? sorted[last]` fallback) — do not assume `rng()` is strictly `< 1` in practice even though the contract says `[0,1)`.
- **Hiding the fallback trigger inside multiple helpers:** keep the "was this distribution degenerate?" decision in exactly one place (each helper returning `null`, the orchestrator's single `?? fallbackMove(...)` at each of the three call sites) — three independent degenerate-detection implementations is how the D-13 fallback silently diverges between the `b=0` and `b>0` paths over time.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Legal move generation / legality checking | A custom chess-rules engine or move validator | `chess.js` `Chess(fen).moves({ verbose: true })` | Already the project's sole source of chess-rules truth (CLAUDE.md); `applyUciMoveFen`/`terminalValue` in `treeCommon.ts` and `sanToUci` in `sanToSquares.ts` already establish the exact usage pattern this phase's `fallbackMove` reuses. |
| Maia move-probability inference | A custom neural-net client / ONNX wrapper | `deps.policy` (injected — app wires `maiaQueue.ts`, harness wires a Node ONNX provider per Phase 168) | Already shipped in Phase 154; `selectBotMove` must stay provider-agnostic per the phase goal, never importing `maiaQueue` directly. |
| Stockfish practical grading | A custom WASM Stockfish wrapper | `deps.grade` (injected — app wires `workerPool.ts`) | Same reasoning; `mctsSearch` already consumes this via `EngineProviders.grade`, `selectBotMove` inherits it unchanged when `b>0`. |
| PUCT tree search / node expansion | A second, bot-specific search implementation | `mctsSearch` (imported as the default `deps.search`) | Phase 153-159 already built, hardened, and froze this (`guardrail.ts`'s `SearchRunner` contract); reimplementing search logic in this phase would violate the phase's own stated goal ("reuses the already-shipped v2.0 engine primitives... does not modify them"). |

**Key insight:** This entire phase is a "glue" layer by design (CONTEXT.md `<domain>`: "does NOT own... the harness itself"). Every non-trivial piece of logic it might be tempted to reimplement (chess rules, neural-net inference, tree search) already exists elsewhere in the codebase, frozen and tested. The only genuinely new code is ~4 small pure functions (`samplePolicy`, `sampleRankedLines`, `argmaxLine`, `fallbackMove`) plus `mulberry32` — everything else is composition.

## Common Pitfalls

### Pitfall 1: Trusting `RankedLine[]` array order

**What goes wrong:** `argmaxLine`/`sampleRankedLines` iterate `lines[0]` or otherwise assume sort order matches `practicalScore` descending.
**Why it happens:** `mctsSearch`'s output IS sorted, just not by the field this phase needs — it's sorted by `rankScore` (Phase 159's findability-weighted metric, `treeCommon.ts`'s `buildRankedLines`). Reading `lines[0].rootMove` looks correct in casual testing (the two orderings often agree for a decisively-best move) and only diverges on positions where a highly-findable-but-suboptimal move outranks the true best-practical-score move.
**How to avoid:** Every consumer explicitly scans for `max(practicalScore)`, exactly as `argmaxLine` in Pattern 2 does. Add a unit test fixture where `rankScore` order and `practicalScore` order deliberately disagree (three lines, the 2nd-ranked-by-`rankScore` has the highest `practicalScore`) to make this structural, not just documented.
**Warning signs:** A `b=1` bot that plays a "reasonable but not best" move in a fixture where the true best move is heavily discounted by findability (e.g. an engine-only move Maia never proposes at the configured ELO, injected via `extraRootMoves`).

### Pitfall 2: Softmax overflow/underflow at extreme `practicalScore` or tiny `tau`

**What goes wrong:** `Math.exp(practicalScore / tau)` can overflow to `Infinity` when `tau` is very small (near the `b→1` end, before the `τ≤ε` short-circuit fires) and a line's `practicalScore` is close to 1. `Infinity / Infinity` propagates `NaN` through the cumulative-walk weighting.
**Why it happens:** `practicalScore` ranges 0-1, so `practicalScore/tau` at `tau=0.01` (a `b` very close to 1) can reach 100, and `Math.exp(100) ≈ 2.7e43` — not yet `Infinity` in float64, but if `tau` drifts even smaller (a future tuning pass, or a caller-supplied budget with `b` extremely close to 1 without hitting the epsilon threshold) this becomes a real risk.
**How to avoid:** Either (a) subtract the max `practicalScore` before exponentiating (the standard "softmax stability" trick: `exp((score - maxScore) / tau)`), which keeps every exponent `≤ 0` and never overflows, or (b) keep `TAU_EPSILON` generous enough that this never triggers in practice (the D-05 curve only reaches `tau→0` exactly at `b=1`, which the `b>=1` branch already routes to `argmaxLine` directly, bypassing softmax entirely — verify the plan's exact `ε` choice is large enough that no floating-point path between `b=0.99` and `b=1.0` produces overflow). Recommend implementing (a) regardless, since it's free and removes the entire failure class.
**Warning signs:** A unit test at `b=0.999` (or similar near-1 non-exactly-1 value) producing `NaN`/`undefined` instead of a valid UCI move.

### Pitfall 3: Symmetric ELO — do not thread a player-ELO input anywhere

**What goes wrong:** A future caller (Phase 169) might be tempted to pass the player's own rating into `selectBotMove` "for realism," silently violating BOT-03.
**Why it happens:** The signature (`fen, settings, deps, signal?`) has no player-ELO field at all — `settings.elo` is unambiguously the bot's own ELO (D-07). This is a structural guarantee, not a runtime check, PROVIDED the signature is never extended with a second ELO field. The pitfall is at the call-site/future-phase level, not inside this phase's own code.
**How to avoid:** Document in the module's header comment (mirroring `mctsSearch.ts`'s own header discipline) that `settings.elo` is the bot's ONLY strength input and the signature intentionally has no slot for player rating — this phase's job is to make BOT-03 impossible to violate by construction, and a code reviewer checking Phase 169's `useBotGame` call site should verify no such second ELO ever gets threaded in.
**Warning signs:** A `selectBotMove` call site in Phase 169 that reads `player.rating` anywhere near the `settings` object construction.

### Pitfall 4: Terminal position vs. degenerate policy — two different "no moves" cases

**What goes wrong:** Conflating D-13 (degenerate policy → fallback to a legal move) with D-14 (genuinely zero legal moves → throw) — e.g. calling `fallbackMove` on a checkmated position and having it silently swallow the "should never happen" case instead of surfacing a clear caller bug.
**Why it happens:** Both cases manifest as "the normal path produced nothing," so it's tempting to handle them identically. But D-14 is explicit: a terminal position reaching `selectBotMove` at all is a caller precondition violation (the game loop must detect checkmate/stalemate BEFORE calling), NOT something this phase should paper over.
**How to avoid:** `fallbackMove` itself is the single place this distinction is enforced (Pattern 4's code example: `moves.length === 0` throws, never returns a fallback). Every other helper's "empty/degenerate" (`{}` policy, all-zero weights, empty `RankedLine[]`) case is DIFFERENT from "chess.js says there are literally zero legal moves" — the former still has legal moves available (chess.js will find them), just no meaningful policy/search signal to choose among them.
**Warning signs:** A unit test asserting `selectBotMove` on a checkmate FEN returns some move instead of throwing.

### Pitfall 5: Forgetting the no-op `onSnapshot` still needs to be a valid function reference

**What goes wrong:** `mctsSearch`'s `SearchRunner` signature requires a 4th positional `onSnapshot` callback (not optional in `guardrail.ts`'s type) — passing `undefined` here throws inside `mctsSearch`'s loop (`onSnapshot(buildSnapshot(...))` is called unconditionally after every completed backup).
**Why it happens:** D-07 states "`selectBotMove` supplies a no-op `onSnapshot` internally — the bot never streams intermediate snapshots" — easy to overlook if focused only on the `deps`/`signal` plumbing.
**How to avoid:** Always pass `() => {}` explicitly at the `search(...)` call site (Pattern 1's example does this).
**Warning signs:** A `TypeError: onSnapshot is not a function` surfacing only when `b>0` (never when `b=0`, since that path never calls `mctsSearch`).

## Code Examples

Verified patterns from this codebase's own frozen contracts (no external library APIs beyond chess.js, already covered above):

### Constructing a `SearchBudget` from `BotSettings` (mirrors `useFlawChessEngine.ts`'s established call-site pattern)
```typescript
// Source: frontend/src/hooks/useFlawChessEngine.ts lines 221-233 (existing, real call site)
const budget: SearchBudget = {
  maxNodes: settings.budget.maxNodes,
  maxPlies: settings.budget.maxPlies,
  concurrency: settings.budget.concurrency,
  elo: { w: settings.elo, b: settings.elo }, // symmetric — BOT-03
  // policyTemperature intentionally omitted/defaulted — D-02 forbids using it here at all;
  // mctsSearch's own DEFAULT_POLICY_TEMPERATURE short-circuit makes omission a true no-op.
};
```

### A never-aborting default `AbortSignal` (D-07)
```typescript
// Source: standard Web platform API composition — no existing codebase precedent
// (grep confirmed no prior "never-aborting signal" utility exists; this phase introduces it)
const NEVER_ABORT_SIGNAL = new AbortController().signal;
// AbortSignal has no public "never aborts" constant; constructing a controller whose
// abort() is simply never called is the standard idiom.
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| N/A — this is new code in an active milestone, not a migration of existing behavior. | — | — | — |

**Deprecated/outdated:** None applicable.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | mulberry32's specific bit-manipulation implementation shown in Pattern 3 is the canonical, widely-used one and produces a well-distributed `[0,1)` output stream for the seed range this phase needs (small integer seeds from tests/harness CLI args). | Architecture Patterns § Pattern 3 | Low — mulberry32 is one of the most widely cited/used tiny JS PRNGs (multiple independent sources agree on this exact bit sequence); even a minor implementation variance would only affect the SPECIFIC sequence of test-fixture "expected" values, not correctness of the sampling algorithm itself. The planner/executor should still run the actual chosen implementation through a distribution sanity check in a unit test (e.g. sampling 10,000 draws from a known 2-move 50/50 policy and asserting the split lands near 50/50) rather than trusting the algorithm blindly. |
| A2 | `chess.js` v1.4's `Move.lan` field is stable across the `^1.4.0` semver range currently pinned in `package.json` and will not be removed/renamed in a patch bump. | Standard Stack, Code Examples § fallbackMove | Low — verified directly against the currently-installed `node_modules/chess.js/dist/types/chess.d.ts`, and this project already relies on chess.js's from/to/promotion fields elsewhere (`sanToUci`) as a stable public API; a breaking rename would already break existing shipped code, not just this phase. |

## Open Questions (RESOLVED)

> Both questions are resolved in `166-01-PLAN.md`: Task 1 mandates the max-subtraction softmax stability trick; Task 2 co-locates `BotSettings`/`BotMoveDeps` in `selectBotMove.ts` per the recommendations below.

1. **Should `sampleRankedLines`'s softmax subtract the max score before exponentiating (Pitfall 2's stability fix), or is the `TAU_EPSILON` short-circuit alone sufficient?**
   - What we know: D-06 already short-circuits to argmax when `τ ≤ ε`, which bounds how small `tau` can get before this phase's own softmax path is even reached.
   - What's unclear: CONTEXT.md leaves the exact `ε` value to Claude's discretion (the planner/executor), and no specific numeric floor was chosen during discussion.
   - Recommendation: Implement the max-subtraction stability trick regardless (it's free, a few extra lines, and eliminates an entire class of `NaN`-producing edge cases) rather than relying solely on tuning `ε` correctly. Do this in the initial implementation, not as a follow-up fix.

2. **Where exactly should `BotSettings`/`BotMoveDeps` types live if Phase 169 (game loop) and Phase 168 (harness) both need to import them independently of `selectBotMove` itself?**
   - What we know: D-07 fixes the shape of `settings`/`deps`; both downstream phases (168, 169) explicitly depend on Phase 166 and will import from wherever this phase lands them.
   - What's unclear: whether they should be co-located in `selectBotMove.ts` (simplest, and this phase controls the file) or split into `types.ts` (the existing frozen-contract file) alongside `EngineProviders`/`SearchBudget`.
   - Recommendation: Co-locate in `selectBotMove.ts` and export directly — `types.ts`'s own header states it is "the frozen public contract of the Phase 153 pure search core," and `BotSettings`/`BotMoveDeps` are a Phase 166-owned contract layered ON TOP of that core, not a modification to it. Keeping them in a separate file avoids ambiguity about whether editing `types.ts` in this phase is "modifying the frozen core" (the phase description explicitly says it does not).

## Environment Availability

Skipped — this phase has no external tool/service/runtime dependencies beyond what the existing frontend toolchain (Vite, vitest, TypeScript, chess.js) already provides and CI already verifies. No new CLI, database, or network dependency is introduced.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Vitest ^4.1.7 (existing, project-standard) |
| Config file | `frontend/vite.config.ts` (vitest config is co-located per this repo's existing convention — verified: no separate `vitest.config.ts` exists; `frontend/src/lib/engine/__tests__/*.test.ts` is the established pattern for this exact directory) |
| Quick run command | `cd frontend && npx vitest run src/lib/engine/__tests__/selectBotMove.test.ts src/lib/engine/__tests__/botSampling.test.ts` |
| Full suite command | `cd frontend && npm test -- --run` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BOT-01 | `b=0` samples raw Maia; `b=1` argmax practicalScore; `b∈(0,1)` softmax-samples with `τ(b)` sharpness | unit | `npx vitest run src/lib/engine/__tests__/selectBotMove.test.ts -t "blend"` | ❌ Wave 0 |
| BOT-02 | `b=0` path calls `deps.policy` exactly once, never `deps.search`/`mctsSearch` | unit | `npx vitest run src/lib/engine/__tests__/selectBotMove.test.ts -t "single Maia inference"` | ❌ Wave 0 |
| BOT-03 | `budget.elo = {w: elo, b: elo}` regardless of any other input; no player-strength parameter exists in the signature at all | unit | `npx vitest run src/lib/engine/__tests__/selectBotMove.test.ts -t "symmetric ELO"` | ❌ Wave 0 |
| BOT-04 | Empty/degenerate policy or `RankedLine[]` falls back to a uniform-random legal move; a position with zero legal moves throws | unit | `npx vitest run src/lib/engine/__tests__/botSampling.test.ts -t "fallback"` | ❌ Wave 0 |
| SC4 (determinism) | Same `mulberry32` seed + same inputs → same returned UCI move, repeatably | unit | `npx vitest run src/lib/engine/__tests__/botSampling.test.ts -t "determinism"` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `cd frontend && npx vitest run src/lib/engine/__tests__/selectBotMove.test.ts src/lib/engine/__tests__/botSampling.test.ts`
- **Per wave merge:** `cd frontend && npm test -- --run` (full frontend suite)
- **Phase gate:** Full suite green before `/gsd-verify-work`; also run `npx tsc -b` (per `feedback_frontend_run_tsc_build` memory — `npm test`/`npm run lint` do not type-check property access across the new `BotSettings`/`BotMoveDeps` types).

### Wave 0 Gaps

- [ ] `frontend/src/lib/engine/__tests__/selectBotMove.test.ts` — new file, covers BOT-01/BOT-02/BOT-03 + SC1-SC3/SC5 orchestration-level behavior with stubbed `deps.search`/`deps.policy`/`deps.grade`/`deps.rng` (per D-08's explicit "unit tests can pass a stub returning canned `RankedLine[]`").
- [ ] `frontend/src/lib/engine/__tests__/botSampling.test.ts` — new file, covers the four pure helpers + `mulberry32` in isolation on canned fixtures (per D-09 — "no workers, no async, no real search").
- [ ] Framework install: none — Vitest is already configured project-wide; no new test infra needed.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | This phase has no auth surface — it's a pure client-side move-selection function with no user identity involved. |
| V3 Session Management | No | No session state is created, read, or mutated. |
| V4 Access Control | No | No resource access decisions are made here. |
| V5 Input Validation | Yes (narrow) | `fen` is trusted (supplied by the caller's own game-loop state, not raw user/network input at this layer); the real input-hygiene concern is `policy()`/`grade()` provider output (UCI candidate strings) potentially being malformed or referring to illegal moves after crossing a Worker/Node-process boundary — already handled by the EXISTING `treeCommon.ts` `applyUciMoveFen` null-on-illegal convention (WR-07), which this phase's helpers should mirror: `fallbackMove`'s chess.js `.moves({verbose:true})` call is itself the source of truth (never trusts an externally-supplied UCI string as "legal" without chess.js re-validating it). |
| V6 Cryptography | No | `deps.rng`/`mulberry32` are explicitly NOT cryptographic (game-fairness/determinism only, not security-sensitive randomness — no secrets, no tokens, no session IDs are derived from this RNG). Do not conflate this with a security-relevant RNG requirement; `Math.random()` is an intentional, correct choice for the live-app path per D-10. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malformed/illegal UCI candidate from a Worker/Node-process boundary (provider output corruption, race, or protocol hiccup) | Tampering (unintentional, not adversarial — same class already documented as WR-07 in `treeCommon.ts`) | `fallbackMove` and any helper touching provider-supplied UCI strings must go through chess.js's own move validation (`.move()`/`.moves()`), never trust a string as legal without re-deriving it from the current FEN — exactly the existing `applyUciMoveFen` pattern this phase should mirror, not reinvent. |
| Denial of "reply" (an infinite/hung Promise if a provider or `mctsSearch` never resolves) | Denial of Service (client-side, not server) | Already addressed structurally: `deps.search` defaults to the frozen `mctsSearch`, which already respects `signal.aborted`; `selectBotMove`'s own optional `signal` parameter (default: never-aborting) lets Phase 169 wire a real cancellation path (resign/flag/navigation) without this phase needing to build its own timeout logic. |

This phase has no server-side attack surface, no persisted data, no auth boundary, and no network calls of its own (all I/O is behind injected `deps`) — the ASVS review here is intentionally light because the phase genuinely has almost nothing security-relevant to it beyond "don't trust externally-sourced move strings without re-validating them," which the codebase already has a established pattern for.

## Sources

### Primary (HIGH confidence)
- `frontend/src/lib/engine/types.ts` — frozen `EngineProviders`/`SearchBudget`/`RankedLine`/`EngineSnapshot` contracts this phase composes.
- `frontend/src/lib/engine/mctsSearch.ts` — the `SearchRunner` this phase invokes for `b>0`; confirms `onSnapshot` is a required positional param and `signal.aborted` is checked between rounds.
- `frontend/src/lib/engine/guardrail.ts` — the exact `SearchRunner` function type signature.
- `frontend/src/lib/engine/select.ts` — the UCI-ascending tie-break convention (`truncateAndRenormalize`) this phase's `weightedPick`/`argmaxLine` mirror.
- `frontend/src/lib/engine/treeCommon.ts` — `buildRankedLines`'s docstring, independently confirming the `rankScore` vs. `practicalScore` sort-order distinction (D-06's core caution).
- `frontend/src/lib/engine/maiaQueue.ts` — confirms `policy()` issues exactly one ONNX inference per queued FIFO batch (BOT-02's single-Maia-call guarantee at the provider level).
- `frontend/src/lib/sanToSquares.ts` — the established `sanToUci`/`uciToSquares` pattern this phase's `fallbackMove` mirrors for chess.js UCI construction.
- `frontend/src/hooks/useFlawChessEngine.ts` — real call-site precedent for constructing a `SearchBudget` with symmetric `elo: {w, b}` from a single on-page value.
- `frontend/node_modules/chess.js/dist/types/chess.d.ts` — confirms `Move.lan: string` exists on the installed `^1.4.0` chess.js version [VERIFIED: direct file read].
- `frontend/package.json` — confirms `chess.js` pinned at `^1.4.0`, `vitest` at `^4.1.7`, no new dependency needed [VERIFIED: direct grep].

### Secondary (MEDIUM confidence)
- `.planning/phases/166-bot-move-selection-core-selectbotmove/166-CONTEXT.md` — the locked decisions (D-01–D-14) that resolve essentially every design question in this research; treated as authoritative per the tool_strategy's user-constraint precedence.
- `.planning/REQUIREMENTS.md` / `.planning/ROADMAP.md` — BOT-01..04 requirement text and SC1-SC5 success criteria.

### Tertiary (LOW confidence)
- mulberry32 canonical implementation — [CITED: https://gist.github.com/tommyettinger/46a874533244883189143505d203312c] and [CITED: https://github.com/bryc/code/blob/master/jshash/PRNGs.md] — WebSearch-sourced, cross-referenced across two independent well-known sources agreeing on the identical bit sequence; flagged in the Assumptions Log (A1) since it was not verified via a project-internal source (this phase introduces the first use of this algorithm in the codebase).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies; the one library touched (chess.js) is verified directly against the installed `.d.ts`.
- Architecture: HIGH — every pattern is a direct composition of already-shipped, already-frozen internal contracts (`types.ts`, `guardrail.ts`, `select.ts`, `treeCommon.ts`) plus CONTEXT.md's locked decisions; no external unknowns.
- Pitfalls: HIGH — four of five pitfalls are drawn directly from explicit warnings already present in the existing codebase (`treeCommon.ts`, `select.ts`, CONTEXT.md D-06/D-07/D-14); only Pitfall 2 (softmax numerical stability) is this researcher's own addition, flagged as a standard, well-known numerical-computing concern rather than a codebase-specific finding.

**Research date:** 2026-07-11
**Valid until:** 30 days (stable internal contracts; no fast-moving external dependency in this phase)
