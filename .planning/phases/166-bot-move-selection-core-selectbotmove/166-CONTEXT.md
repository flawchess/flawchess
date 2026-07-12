# Phase 166: Bot Move Selection Core (`selectBotMove`) - Context

**Gathered:** 2026-07-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a single **pure, provider-agnostic `selectBotMove`** function (plus its
pure sub-helpers) that, given a position and (ELO, play-style) settings, returns
a legal UCI move at the bot's configured strength. Both the play loop (Phase
169) and the calibration harness (Phase 168) import and run this function
**unchanged** via the `@/` alias.

This phase is move *selection* only. It does NOT own: the game loop, clocks,
think-time pacing, or the clock→budget derivation (Phase 169 supplies `budget`);
persistence (Phase 167); or the harness itself (Phase 168). It reuses the
already-shipped v2.0 engine primitives (`mctsSearch`, `maiaQueue.policy`,
`workerPool.grade`) — it does not modify them.

</domain>

<decisions>
## Implementation Decisions

### Play-style slider → selection mode (Area 1)
- **D-01:** The bot play-style slider is a **blend parameter `b ∈ [0,1]`**, NOT
  the analysis-board policy-temperature slider. `b=0` = Human end, `b=1` =
  Stockfish end. It keeps the analysis board's Human↔Stockfish *framing* but is
  a sibling knob, not the same transform.
- **D-02:** **`applyPolicyTemperature` (the analysis temperature transform) is
  NOT used in `selectBotMove`.** Reason (worked through in discussion): the
  transform's "Stockfish end = stronger" polarity is an artifact of the analysis
  *ranking* pipeline, where the reshaped policy is only a prior and Stockfish
  grading + findability rescue the surfaced strong move. In a raw-*sampling*
  path there is no Stockfish to rescue anything, so the polarity inverts —
  flattening (T>1) just samples rare human moves, which skew toward blunders, so
  it makes the bot *noisier and weaker*, not more engine-like. Using temperature
  for sampling would give a non-monotonic (U-shaped) strength curve that breaks
  Phase 168 calibration. Raw Maia (T=1) is the canonical ELO-faithful human, so
  the human end simply samples raw Maia.
- **D-03:** Regime split:
  - **`b = 0`** → **no MCTS**: exactly one `policy()` call, sample the raw Maia
    root policy (satisfies SC2 — one inference at full-human).
  - **`b ∈ (0,1]`** → run `mctsSearch`, then choose from its `RankedLine[]`
    (see D-04/D-05).
  - A mild *style* discontinuity at `b=0⁺` (Maia-human distribution → practical-
    score distribution) is accepted by design: the leftmost stop is explicitly
    "pure human," everything to its right has engine influence.

### Blend sharpness curve (Area 2)
- **D-04:** Practical-score sampling is a **softmax over `RankedLine.practicalScore`**
  (0–1, root-side-to-move expected score): `P(moveᵢ) ∝ exp(practicalScoreᵢ / τ(b))`.
  Sampling weights deliberately use raw `practicalScore`, NOT the findability-
  weighted `rankScore` (which discounts moves humans at the ELO rarely find):
  the root candidate set is already Maia-gated (`truncateAndRenormalize` + the
  root hard cap), so engine-only moves Maia never proposes cannot appear as
  candidates, and human-likeness dials in via `τ`, not findability discounting.
- **D-05:** **`τ(b) = TAU_MAX · (1 − b)`**, linear and monotone decreasing, with
  **`TAU_MAX = 0.10`** (named constant; harness-refinable but a complete default
  now). A 0.10 expected-score gap favors the best move ~2.7× at the soft edge,
  so 2nd/3rd moves keep real probability; the distribution sharpens toward the
  center.
- **D-06:** **`b = 1` → pure deterministic argmax over `practicalScore`**
  (UCI-ascending tie-break) per SC1. CAUTION: `mctsSearch`'s `RankedLine[]` is
  sorted by findability-weighted `rankScore` (`treeCommon.ts` `buildRankedLines`),
  NOT by `practicalScore` — `argmaxLine` must scan for the max `practicalScore`
  explicitly and never trust array order (`rankedLines[0]` is the most human-
  findable move, which would make the `b=1` bot weaker than SC1 specifies).
  Since `τ→0` there, short-circuit to argmax when `τ ≤ ε` to avoid
  divide-by-zero.

### API surface & harness reuse (Area 3)
- **D-07:** Signature `selectBotMove(fen, settings, deps, signal?): Promise<string>`.
  - `settings = { elo, blend, budget }`. `elo` → `budget.elo = { w: elo, b: elo }`
    (symmetric, SC3 — the bot never adapts to the player). `budget` carries
    `maxNodes / maxPlies / concurrency`, passed IN by the caller (Phase 169
    derives them from the clock; this phase only accepts them).
  - `deps = { policy, grade, rng, search? }`.
  - `signal?: AbortSignal` — optional, passed through to `mctsSearch` (whose
    signature requires one) so Phase 169 can cancel the bot's think on resign,
    flag, new game, or navigation; defaults to a never-aborting signal.
    `selectBotMove` supplies a no-op `onSnapshot` internally — the bot never
    streams intermediate snapshots.
- **D-08:** **`deps.search` defaults to `mctsSearch`** imported directly (it is
  already pure — takes injected providers). It is *optional/injectable* so unit
  tests can pass a stub returning canned `RankedLine[]`. The Phase 168 harness
  supplies Node-side `policy`/`grade` providers + a seeded rng and uses the real
  `mctsSearch` — identical to the app. (Chosen over "fully injected/required"
  precisely so the harness cannot accidentally diverge from the app's search.)
- **D-09:** Split into an **impure orchestrator** (`selectBotMove` — regime
  choice + one `policy()` or one `mctsSearch()`) and **pure, sync, separately-
  exported helpers** holding all the interesting logic: `samplePolicy(policy,
  rng)`, `sampleRankedLines(lines, tau, rng)`, `argmaxLine(lines)`,
  `fallbackMove(fen, rng)`. Helpers unit-test on canned inputs — no workers, no
  async, no real search.

### Fallback & determinism (Area 4)
- **D-10:** **RNG is injected as `deps.rng: () => number`** in `[0,1)`.
  `selectBotMove` only ever calls `rng()`. Live app passes a `Math.random`-backed
  rng (a played game needs no reproducibility); tests + harness pass a seeded
  PRNG.
- **D-11:** **Seeded PRNG = a tiny inlined `mulberry32(seed)`** (~5 lines, no
  dependency), exported for tests/harness. Fixed seed → deterministic selection
  (SC4).
- **D-12:** **Weighted sampling = cumulative-distribution walk over candidates
  sorted UCI-ascending** (same tie-break convention as `select.ts` /
  `truncateAndRenormalize`), so a given `rng()` draw always yields the same move
  regardless of Map/Record iteration order.
- **D-13:** **Fallback (SC5) = uniform-random legal move.** When the sampled
  distribution is empty/degenerate (`policy()` returns `{}`, all-zero weights, or
  MCTS yields no `RankedLine[]`): generate legal moves from the FEN via chess.js,
  sort UCI-ascending, and pick one uniformly via `rng()`. This covers both the
  `b=0` and `b>0` regimes.
- **D-14:** A **terminal position (no legal moves at all)** is a caller/
  precondition bug (the game loop must detect end states before calling), so
  `selectBotMove` **throws a clear error** there. SC5's "return a legal move
  rather than throwing/passing" governs a *degenerate policy*, not a checkmate/
  stalemate position where no legal move exists to return.

### Claude's Discretion
- Exact names/paths of the new module(s) under `frontend/src/lib/engine/` (or a
  new `bot/` subdir), the `ε` threshold value for the argmax short-circuit, and
  the chess.js move-generation call shape — implementation detail for the
  planner.
- The precise `τ(b)` curve constant (`TAU_MAX = 0.10`) is the locked default but
  is explicitly harness-refinable in Phase 168 without a signature change.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase / milestone scope
- `.planning/ROADMAP.md` §"Phase 166" — goal + the 5 success criteria this phase
  is verified against (SC1–SC5).
- `.planning/REQUIREMENTS.md` — BOT-01 (sample↔argmax blend), BOT-02 (one Maia
  inference at full-human), BOT-03 (symmetric, non-adaptive ELO), BOT-04
  (graceful legal fallback).
- `.planning/seeds/SEED-091-flawchess-bot-play-milestone.md` — the five locked
  design decisions; note that decision #2's "temperature-reshaped" wording is
  superseded here by D-01/D-02 (temperature not used in sampling; see rationale).

### Engine primitives this phase reuses unchanged
- `frontend/src/lib/engine/types.ts` — the frozen contract: `EngineProviders`
  (`policy`/`grade`), `SearchBudget` (`maxNodes`/`elo{w,b}`/`maxPlies`/
  `concurrency`), `RankedLine` (`rootMove`, `practicalScore` 0–1), `EngineSnapshot`.
- `frontend/src/lib/engine/mctsSearch.ts` — the pure search `selectBotMove`
  invokes for `b>0`; signature `mctsSearch(fen, budget, providers, onSnapshot, signal)`.
- `frontend/src/lib/engine/maiaQueue.ts` — `MaiaQueue.policy(fen, elo, side)`,
  the single Maia inference used by the `b=0` path (real `EngineProviders.policy`).
- `frontend/src/lib/engine/workerPool.ts` — `pool.grade` provider + `computePoolSize()`.
- `frontend/src/lib/engine/select.ts` — the UCI-ascending tie-break convention
  D-12 mirrors; `truncateAndRenormalize` semantics for reference.
- `frontend/src/hooks/useFlawChessEngine.ts` — reference call site showing how the
  app wires providers + `SearchBudget` (`maxNodes=400`, `maxPlies=8`,
  `elo={w,b}`) into `mctsSearch`; Phase 169's `useBotGame` will mirror this.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `mctsSearch` (already pure, provider-injected): call directly for `b>0`.
  NOTE: its `RankedLine[]` is sorted by findability-weighted `rankScore`
  (`treeCommon.ts` `buildRankedLines`), NOT by `practicalScore` — both argmax
  and the softmax sampler must read `practicalScore` off each line and ignore
  array order (see D-06).
- `maiaQueue.policy` / `workerPool.grade`: the real `EngineProviders` the app
  injects; `selectBotMove` receives them as `deps`, never imports them, keeping
  it provider-agnostic for the Node harness.
- `select.ts` tie-break pattern (`b[1]-a[1] || (a[0]<b[0]?-1:1)`): reuse the same
  UCI-ascending discipline for sampling determinism (D-12).

### Established Patterns
- Engine core speaks **UCI everywhere** and side-to-move is the FEN `'w'/'b'`
  literal (D-08 in `types.ts`) — `selectBotMove` returns a UCI string; derive
  `side` from the FEN.
- No seeded-RNG or weighted-sample helper exists in the frontend yet — this phase
  introduces both (`mulberry32`, cumulative-walk sampler) as small pure utilities.
- `SearchBudget.elo` is color-keyed `{w,b}`; symmetric bot ELO = both set to the
  one configured value (matches how `useFlawChessEngine` shares one on-page ELO).

### Integration Points
- `deps` boundary is the reuse seam: app supplies `createMaiaQueue()`/
  `createWorkerPool()` providers + `Math.random` rng; harness supplies Node
  ONNX/WASM providers + seeded rng; both use the same default `mctsSearch`.

</code_context>

<specifics>
## Specific Ideas

- The Human↔Stockfish slider framing is kept for user familiarity, but under the
  hood it is a blend `b`, decoupled from the analysis temperature transform (D-01).
- `b=1` is intentionally pure/deterministic argmax even though that makes the
  strongest setting "the same game every time" — SC1 defines it that way, and
  ELO-faithful variety comes from lower `b` / the ELO setting, not from softening
  the top end.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (User-results strength curve fitting
remains explicitly out of this milestone per SEED-091 decision #3; the Phase 168
anchor harness is engine-vs-anchor self-play and needs no user data.)

</deferred>

---

*Phase: 166-bot-move-selection-core-selectbotmove*
*Context gathered: 2026-07-11*
