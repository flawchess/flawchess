# Phase 172: Background Gem Sweep on Analysis - Research

**Researched:** 2026-07-14
**Domain:** Client-side chess-engine scheduling (Stockfish WASM + Maia ONNX Web Workers) inside an already worker-dense React page; one additive backend field
**Confidence:** HIGH (all findings verified by reading the actual shipped code — no external library research needed; this phase touches only code already in the repo)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D1 — A gem is a property of the game, not of the view.** Pin gem classification to each **mover's own** Lichess-blitz-normalized rating-at-game-time (the rung Phase 164 already seeds via `deriveRawDefault` / the `*_lichess_blitz` fields). The Elo slider drives only the live exploration overlay, **not** the gem badges. This is a behavior change from shipped code — today `gemC1` resolves the rung via `nearestByElo` against the slider (`Analysis.tsx:1445`), so gems shift when the slider moves. Pinning is also what makes a background sweep cacheable at all. Both movers matter — each ply is classified against the player who made it.
- **D2 — Analysis move list only. No persistence, no backend gem store.** Gems never appear on Library cards or in stats. Consequence: no Maia in Python. Maia exists only as ONNX in the browser (`useMaiaEngine.ts`), and C1 is the sole reason gems are a frontend feature.
- **D3 — Sweep analyzed games only, but trigger on analysis *becoming* ready.** No backend evals ⇒ no free prefilter ⇒ no sweep. Unanalyzed games keep today's lazy behavior and surface the existing one-click Analyze pill. Amended 2026-07-14: "analyzed" is not a one-shot check at mount — a bot game opened while its tier-1 analysis runs in the background must be swept the moment the evals arrive. The sweep keys off analysis readiness as a **transition**, not a mount-time boolean.
- **D4 — Prefilter: `played === best_move` AND out of opening book.** Both free. C2 implies the played move lost ~zero expected score, so most plies are eliminated with data the page already fetches and ignores: `EvalPoint.best_move`. Strict equality (not an es-loss band) fails safe. Mirrors the backend's `_hint_flaw_plies` (`scripts/remote_eval_worker.py:226`). Three tiers: (1) Free — `played === best_move` AND out of book, zero engine work; (2) Cheap — Maia forward pass on survivors' parent positions for C1; (3) Expensive — Stockfish parent grade (MultiPV over `selectCandidatesByMass`) on the handful that clear C1.
- **D5 — Cascade + contention.** Reuse the existing isolated gem-grading worker and the `gemByNode` sticky cache (`Analysis.tsx:1484-1521`). The sweep MUST yield to the position the user is actually looking at — never starve the live free-run/grading engines for the current node. The page must not feel slower than it does today. This is the phase's main failure mode.
- **D6 — `opening_ply_count`, computed on-read. No column, no migration, no backfill.** `opening_lookup.py` builds a SAN trie (`_TRIE`, line 89) as a module-level singleton, walks to the deepest match, and throws the depth away. The game-detail payload already ships `moves: list[str]`, so the depth is computed when the game is opened and returned as an additive field. `find_opening` takes a PGN and normalizes to SAN internally, so the detail path wants a `find_opening_from_moves(moves)` variant; the loop tracks `last_result` but not its depth, so it needs an index carried alongside. This supersedes SEED-092's D-02 ("no opening-ply guard").
- **D7 — Raise `GEM_MAIA_MAX_PROB` from 0.10 to 0.20** (`gemMove.ts:25`). "Hard to find" becomes "fewer than 1 in 5 rating-peers would play it." Measured against the Phase 165 calibration TSV, the raise multiplies gem frequency by 1.35x at Maia-600, rising to ~1.8x at 2200-2600, and *narrows* the Elo skew (3.8x → 2.9x). Caveat: the TSV's sample is enriched (21.8% C2-pass rate) — only ratios transfer, not absolute frequencies.
- **D8 — Opening-book markers, precedence `severity > gem > book`.** Today the rule is severity > gem (`VariationTree.tsx:59-69`, `resolveMarkerIcon`). Book slots in at the bottom: severity overrides the book icon (a book move can still be an inaccuracy). Gem-vs-book never actually arises (D4 skips book plies before classification) but the chain is stated in full. Applies on every surface where gems already render: `VariationTree` marker AND the board corner marker (`boardMarkers.tsx`).

### Claude's Discretion

- The scheduler's concrete shape (idle-callback vs. explicit priority queue vs. abortable batches), as long as D5's yield-to-cursor invariant holds and is provable.
- How the sweep's progress is (or is not) surfaced in the UI — no spinner was specified.
- Test strategy and where the seams are cut, subject to the project's normal gates.
- The exact name/signature of the `find_opening_from_moves` variant.

### Deferred Ideas (OUT OF SCOPE)

- Sweeping user variations (mainline only this phase).
- Persisting gems / surfacing them outside `/analysis` (D2 — explicitly rejected, not merely deferred).
- Measuring real-game gem frequency before shipping (explicit call: judge it in UAT).
- A persisted `games.opening_ply_count` column — revisit only if book depth is ever needed in a SQL filter or aggregate.
</user_constraints>

<phase_requirements>
## Phase Requirements

No `REQUIREMENTS.md` IDs apply — this phase is SEED-106 direct (D1-D8 locked 2026-07-14, not milestone requirements). The 7 ROADMAP success criteria stand in as the requirement set; each maps to the research below.

| # | Success Criterion | Research Support |
|---|--------------------|-------------------|
| 1 | Background sweep, free→cheap→expensive cascade | Architecture Patterns §"The cascade, concretely"; `EvalPoint.best_move` is UCI, played move is SAN — needs `sanToUci` conversion (Pitfall) |
| 2 | Sweep yields to the live cursor, page doesn't feel slower | Architecture Patterns §"D5 — the scheduler / contention model" (the phase's real work) |
| 3 | Gem rung pinned to mover's own rating | Architecture Patterns §"D1 — the rung pin"; reuse/export `deriveRawDefault` |
| 4 | Unanalyzed games stay lazy | Architecture Patterns §"D3 — the readiness transition"; `evalChartReady`/`live:true` polling already ships this signal |
| 5 | `GEM_MAIA_MAX_PROB` 0.10 → 0.20 | One-line constant change (`gemMove.ts:25`) + one hardcoded test literal (`gemMove.test.ts:59`) |
| 6 | `opening_ply_count` computed on-read, book markers, `severity > gem > book` | Architecture Patterns §"D6 — the backend field", §"D8 — markers" |
| 7 | Bot game swept the moment tier-1 evals land while board is open | Architecture Patterns §"D3", confirmed via quick 260714-rj5's `live: true` poll + `evalChartReady` transition |
</phase_requirements>

## Summary

This phase has almost no unknown-technology risk — everything it touches is already shipped, in-repo code (Stockfish WASM workers, a Maia ONNX worker, a React Query poll, a Python trie). The entire research burden is architectural: **the page already runs up to ~5-8 concurrent Worker threads** (primary Stockfish free-run, a shared grading Stockfish worker, an intermittent per-node gem-grading Stockfish worker, a 2-4-slot Stockfish MCTS pool when the FlawChess card is on, and a Maia ONNX worker), and neither the Stockfish grading hook nor the Maia hook has any concept of request priority or preemption. Layering a sweep on top without an explicit scheduling discipline is guaranteed to either (a) starve the live position behind background work, or (b) oversubscribe the device's CPU cores and make the whole tab feel laggy — exactly the failure mode D5 names as the phase's real work.

The good news: the codebase already contains every primitive the sweep needs, just not wired together. `workerPool.ts` ships an abortable, already-prioritized multi-worker Stockfish pool (`priority`/`depth` fields exist and are unit-tested, just always `0` today because "no caller exists yet" — literally built for exactly this). `useFlawChessEngine.ts` demonstrates the established abort pattern (`AbortController` + `pool.stopAll()`, and explicit acceptance that "an in-flight ONNX inference cannot be interrupted... a stale policy() resolution is unused and harmless"). `deriveRawDefault` in `useMaiaEloDefault.ts` already computes exactly the per-mover, per-ply rating D1 needs — it just needs to be exported and called with each ply's own mover color instead of the reactive `selectedElo`/slider default. `opening_lookup.py`'s trie walk just needs its already-tracked `last_result` variable to also carry the matching depth.

**Primary recommendation:** Do NOT literally share the live `gemGrading`/`grading`/`maia` hook instances with the sweep — their single-in-flight-request, auto-reconverge-to-current-position design means feeding them a background FEN injects real latency into the live path the moment the user navigates mid-sweep-request. Instead, give the sweep its own dedicated, low-priority Stockfish and Maia worker instance(s), gated to non-mobile devices, paced via an idle-callback-driven scheduler (one candidate in flight at a time, checked against the current cursor before and after each step), and prove the "never starves the live position" invariant with a test that starts a live gem-grading request mid-sweep and asserts it resolves without waiting on the sweep's queue — per the project's own mutation-test-gap-closure discipline (a "the sweep exists" test proves nothing; only a "the live request still wins" test proves the invariant).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Free prefilter (played === best_move, out-of-book) | Browser / Client (main thread, pure JS) | — | Pure data already on the fetched `EvalPoint`/`opening_ply_count`; no engine work, so no Worker involvement at all |
| Cheap tier (Maia forward pass) | Browser / Client (dedicated Web Worker) | — | ONNX inference is CPU/GPU-bound; must run off the main thread; needs a worker instance separate from the live Maia hook |
| Expensive tier (Stockfish parent grade) | Browser / Client (dedicated Web Worker) | — | WASM search is CPU-bound single-threaded-per-worker; needs a worker instance separate from `engine`/`grading`/`gemGrading` |
| Sweep scheduler / yield-to-cursor arbitration | Browser / Client (main thread, plain JS/React state) | — | Pure scheduling logic — should be a testable, worker-free module (mirrors `gemMove.ts`'s existing precedent) |
| Gem rung pin (D1) | Browser / Client (derived from already-fetched `GameFlawCard` fields) | — | `white_rating_lichess_blitz`/`black_rating_lichess_blitz` already ship on the game-detail payload; no new fetch |
| `opening_ply_count` | API / Backend (computed on-read in `library_service.py`) | — | Needs the SAN trie, which is a Python module-level singleton; recomputing client-side would require shipping the trie to the browser (explicitly rejected, D6) |
| Book/gem/severity marker precedence | Browser / Client (`VariationTree.tsx`, `boardMarkers.tsx` call sites) | — | Pure display logic, no data fetch |

## Standard Stack

No new libraries. Every primitive is already vendored/shipped:

| Component | Where | Purpose | Why reuse (not new) |
|-----------|-------|---------|----------------------|
| Stockfish WASM (`stockfish-18-lite-single.js`) | `public/engine/`, loaded via classic `new Worker()` | Expensive tier's parent grade | Same binary as `engine`/`grading`/`gemGrading`/`workerPool` — one more `new Worker(ENGINE_PATH)` call is the established pattern for "a fully isolated instance" (see `useStockfishGradingEngine.ts` header comment) |
| Maia ONNX (`maia-worker.js`, onnxruntime-web) | `public/maia/`, loaded via classic `new Worker()` | Cheap tier's forward pass | Same worker script as the live `useMaiaEngine` instance; a second `new Worker('/maia/maia-worker.js')` instance is the only way to avoid blocking the live curve (see Pitfall 1 below) |
| `workerPool.ts`'s `QueuedGradeRequest.priority`/`depth` fields | `frontend/src/lib/engine/workerPool.ts:65-73, 127-171` | Already-built, already-unit-tested priority queue | POOL-02's own header comment says the ordering logic is "correct and tested in isolation but currently unreachable" through the frozen 2-arg `grade()` contract — this phase is a candidate second caller, IF the plan chooses this route over a dedicated single-worker sweep engine (see discretion note below) |
| `AbortController`/`AbortSignal` | Native browser API | Cancel an in-flight low-priority sweep request when the cursor moves | Already the established pattern in `useFlawChessEngine.ts:229-291` and `workerPool.ts:404-431` — do not invent a new cancellation primitive |
| `deriveRawDefault` (private, `useMaiaEloDefault.ts:104-119`) | Frontend lib | Per-mover, rating-at-game-time lookup with normalized/raw fallback | Already implements exactly D1's fallback chain; currently unexported (hook-internal) — export it (or extract to a shared pure function) rather than reimplementing the `*_lichess_blitz ?? raw` chain a second time |

**No installation step** — nothing to add to `package.json` or `pyproject.toml`.

## Package Legitimacy Audit

Not applicable — this phase installs zero external packages (D2/scope: "no new backend dependency," no new frontend dependency either). Skipped per the protocol's own applicability gate.

## Architecture Patterns

### The current worker census (read this before designing the sweep)

Confirmed by reading `Analysis.tsx` end to end. On `/analysis` in game mode with the Maia panel, Stockfish panel, and FlawChess Engine panel all enabled (a realistic, not a worst-case, user state), the page can already be running:

| Instance | Hook / module | Line | Gate | Purpose |
|----------|---------------|------|------|---------|
| `engine` | `useStockfishEngine` | `Analysis.tsx:557` | always-on in game/free-play mode | Primary free-run — live eval bar, board arrow |
| `grading` | `useStockfishGradingEngine` | `Analysis.tsx:906` | `maiaEnabled \|\| flawChessEnabled` | Current-position candidate grading for the Moves-by-Rating chart / FlawChess card's reconciled evals |
| `gemGrading` | `useStockfishGradingEngine` (SECOND instance) | `Analysis.tsx:1476` | `gradingEnabled && needParentGemGrade` | Live per-node C2 confirmation, intermittent (only when the CURRENT node's arrival move passes C1) |
| FlawChess pool | `createWorkerPool()` via `useFlawChessEngine` | `useFlawChessEngine.ts` | FlawChess card enabled | 2-4 Stockfish workers (`computePoolSize()`) for the MCTS search |
| `maia` | `useMaiaEngine` | `Analysis.tsx` (single call) | Maia panel enabled | Live Maia curve for the current position (chart, WDL bar, C1 lookups) |

That is already up to **1 (engine) + 1 (grading) + 0-1 (gemGrading, bursty) + 2-4 (FlawChess pool) + 1 (Maia) ≈ 5-8 concurrent Worker threads** on a desktop before this phase adds anything. `computePoolSize()`'s own `DESKTOP_HEADROOM_CORES = 2` comment ("cores reserved for the main thread + Maia worker") only budgets for ONE Maia worker and does not account for `engine`/`grading`/`gemGrading` running concurrently — i.e. the page can already be oversubscribed on a 4-core-effective device today, independent of this phase. This is existing behavior, not a regression to fix here, but it sets the ceiling for how much MORE headroom a sweep can safely claim: **effectively none**, unless the sweep's own footprint is kept deliberately small and throttled.

### D5 — the scheduler / contention model (the phase's real work)

**Key finding 1 — neither existing engine hook has priority or preemption.**

- `useStockfishGradingEngine.ts` (the pattern both `grading` and `gemGrading` use) is a *single-FEN* state machine: `fen`/`candidateSans` are hook props, there is exactly one Worker, and `prepareSearch` (line 213) either sends a fresh `go` or, if a search is already `thinking`, sends `stop` and re-issues once the stale `bestmove` arrives (lines 217-224). There is no queue and no priority field — feeding this hook a background sweep FEN while it is ALSO the vehicle for a live gem-grading request would force one to literally interrupt the other's in-flight WASM search every time either side's `fen` prop changes. **Do not drive the sweep through the SAME hook instance used for `gemGrading` or `grading`.**
- `useMaiaEngine.ts`'s `analyze()` (line 168) is even more restrictive: "Keep a single inference in flight... posting a second `analyze` only queues it behind the first... Drop the request here" (lines 180-187) — a second `analyze()` call while one is running is silently DROPPED, not queued, and the result handler auto-reconverges to whatever FEN is `currentFenRef.current` once the in-flight inference completes (lines 269-276). If the sweep drives the SAME `useMaiaEngine` instance the live chart uses, a sweep-issued inference for an ancestor position would occupy the ONLY in-flight slot, and the live position's own inference would be **dropped and only re-issued after the sweep's inference finishes** — injecting the sweep's full inference latency onto the live path. This is the single most concrete way D5 could be violated by accident.
- `workerPool.ts`'s `dispatchNext()` (line 238) only assigns pending requests to **idle** slots — it never preempts an in-flight low-priority slot to make room for a newly-arrived high-priority one. Even with `priority` wired up, if all N pool slots are busy with sweep work when a live high-priority request arrives, the live request queues behind whatever finishes first. Priority alone (without an explicit stop-in-flight-slot escalation) does not fully satisfy "never starve the live position" under saturation — only helps for requests still in the pending array.

**Key finding 2 — the codebase already has an established, deliberate answer for "can't cancel a running inference": tolerate a stale result.** `useFlawChessEngine.ts:224-225` states plainly: "maiaQueue has no stopAll (an in-flight ONNX inference cannot be interrupted) — a stale policy() resolution is unused and harmless." This is the precedent to follow for the sweep's Maia tier: it is fine to let an in-flight background Maia inference run to completion even after the cursor moves, as long as (a) the live position's OWN inference is never blocked behind it (requires a separate worker instance, per Key finding 1), and (b) the stale result is simply written to the sweep's own cache/dropped, never forced onto the live display.

**Recommended shape (Claude's Discretion per CONTEXT.md, but concretely scoped by the above):**

1. **Dedicated sweep workers, never shared.** Spin up a THIRD `useStockfishGradingEngine`-shaped Stockfish worker instance and a SECOND Maia worker instance, used exclusively by the sweep. This trades "one more Worker thread" for "the live path is structurally never blocked" — given the existing worker census above, the added CPU cost must be bounded by throttling (next point), not by sharing.
2. **Throttle via idle-yield, one candidate at a time.** Use `requestIdleCallback` (with a `setTimeout(cb, 1)` fallback — `requestIdleCallback` is not implemented in all Safari versions; feature-detect, don't assume) to schedule each sweep step only when the browser is idle. Before dispatching each candidate, re-check the current cursor/live-request state; if the live gem-grading path (`needParentGemGrade`) is currently active, skip this tick entirely rather than racing it.
3. **Reduce the sweep's Stockfish movetime cap.** The live `gemGrading` uses `GRADING_MOVETIME_SAFETY_CAP_MS = 4000` (`useStockfishGradingEngine.ts:52`) because it must resolve promptly for the position the user is looking at. The sweep has no such deadline — background candidates can use a materially smaller cap (e.g. matching the free-run's `MOVETIME_MS` order of magnitude) to reduce how long the sweep pegs a CPU core per candidate, trading a small amount of grading depth for much lower per-candidate wall-clock cost. Cite this explicitly as a deliberate DIFFERENT constant from `GRADING_MOVETIME_SAFETY_CAP_MS`, not a reuse.
4. **Gate the sweep off entirely on mobile / coarse-pointer devices**, mirroring `workerPool.ts`'s own `computePoolSize()`/`MOBILE_CORE_THRESHOLD`/coarse-pointer heuristic (`workerPool.ts:182-195`) — a 2-core phone already runs the existing MOBILE_POOL_SIZE=2 FlawChess pool plus the live Stockfish/Maia workers; a background sweep is a poor trade against battery/thermal/frame-drop risk there, and the lazy per-node resolution already works.
5. **Pause on tab-hidden**, mirroring the visibilitychange handlers already in both `useStockfishGradingEngine.ts:431-454` and `useMaiaEngine.ts:309-325` — a backgrounded tab should not burn CPU sweeping.
6. **AbortController per in-flight sweep Stockfish request**, mirroring `useFlawChessEngine.ts`'s pattern — the moment the cursor changes, abort any in-flight LOW-priority Stockfish search (Stockfish, unlike Maia's ONNX call, CAN be `stop`ped mid-search — `workerPool.ts`'s abort path already demonstrates this). The Maia tier cannot be aborted mid-inference (tolerate per Key finding 2 above); the Stockfish tier can and should be.
7. **Extract the scheduling/prefilter logic as a pure, worker-free module** (mirroring `gemMove.ts`'s own stated rationale — "pure, worker-free... detection"), e.g. `frontend/src/lib/gemSweep.ts`, exposing: (a) a pure function computing the free-prefilter survivor list from `EvalPoint[]` + `moves` + `openingPlyCount`, and (b) a pure "what's the next candidate to dispatch, given the current cursor and already-resolved set" scheduler-decision function. This keeps the yield-to-cursor invariant unit-testable without mocking React hooks or Workers (see Validation Architecture).

**Open discretion point:** whether to build the sweep's dedicated Stockfish worker as a fourth bespoke `useStockfishGradingEngine`-style hook, or to finally wire up `workerPool.ts`'s already-built `priority`/`depth` fields (tagging sweep requests with a low, fixed priority and the live gem-grading path — if migrated onto the pool — with a high one). The pool route is architecturally cleaner (POOL-02 was LITERALLY built for "background work that yields to something more urgent") but is a bigger refactor (the live `gemGrading` hook would need to move onto the pool's UCI-keyed, promise-based `grade()` API instead of its own SAN-keyed streaming state machine, losing the progressive `info`-line refinement `gemGrading` doesn't currently need anyway). Recommend the smaller, structurally-isolated option (a dedicated worker, item 1 above) for THIS phase, and leave the pool-based unification as a natural follow-up once there are two real callers wanting priority (this phase's sweep, and Phase 155's still-unbuilt MCTS priority caller).

### D1 — the rung pin

`gemC1` (`Analysis.tsx:1445-1454`) and the C2-confirmation effect (`Analysis.tsx:1501`) both call `nearestByElo(parentCurve ?? [], selectedElo)` — `selectedElo` is the reactive ELO-slider state (`useMaiaEloDefault`'s `selectedElo`, user-overridable). This is the exact behavior D1 changes: the rung must instead be **each node's own mover's** rating-at-game-time, computed once and never re-derived when the slider moves.

The data and the fallback chain already exist, verbatim, in `useMaiaEloDefault.ts`'s **private, unexported** `deriveRawDefault` function (lines 104-119):

```typescript
function deriveRawDefault(
  isGameMode: boolean,
  gameData: MaiaEloGameData | undefined,
  profile: MaiaEloProfile | undefined,
  sideToMove: MoverColor | undefined,
): number | null {
  if (isGameMode) {
    if (gameData == null) return null;
    const moverColor = sideToMove ?? gameData.user_color;
    if (moverColor === 'white') {
      return gameData.white_rating_lichess_blitz ?? gameData.white_rating;
    }
    return gameData.black_rating_lichess_blitz ?? gameData.black_rating;
  }
  return profile?.lichess_blitz_equivalent_rating ?? FREE_PLAY_DEFAULT_ELO;
}
```

This is available for **both** players (the `moverColor` branch), for bot games (confirmed server-side: `library_service.py:561-589` passes a `flawchess`-platform game's raw `white_rating`/`black_rating` through unchanged as `*_lichess_blitz` — "a stored flawchess rating is ALREADY lichess-blitz-equivalent by construction of anchor_rating"), and degrades to `null` for guest/no-imported-games users where both the normalized and raw ratings are `NULL` — in which case the existing `useMaiaEloDefault` wrapper falls back to `FREE_PLAY_DEFAULT_ELO = 1500` only via its `?? FREE_PLAY_DEFAULT_ELO` at the OUTER call site, not inside `deriveRawDefault` itself.

**Concrete plan-time task:** export `deriveRawDefault` (or extract it to a shared pure-function module both `useMaiaEloDefault.ts` and the sweep can import) rather than re-deriving the `*_lichess_blitz ?? raw` fallback chain a second time in the sweep. For each mainline node, the pinned rung is:

```typescript
const mover = sideToMoveFromFen(parentFen); // already used at Analysis.tsx:1495 for byOpponent
const pinnedElo = clampToLadderBounds(
  deriveRawDefault(isGameMode, gameData, profile, mover) ?? FREE_PLAY_DEFAULT_ELO,
);
```

`clampToLadderBounds` is also currently private to `useMaiaEloDefault.ts` (lines 94-98) — export or extract alongside `deriveRawDefault`. Both `sideToMoveFromFen` (already imported in `Analysis.tsx`) and `clampToLadderBounds`/`deriveRawDefault` are small, pure, and trivially unit-testable in isolation — this is the natural seam for proving "a slider nudge never changes the pinned rung" (Validation Architecture).

**Both movers matter, already confirmed working today for the BYOPPONENT framing:** `Analysis.tsx:1509-1512` already computes `mover = sideToMoveFromFen(parentFen)` and `byOpponent = isGameMode && gameData?.user_color != null && mover !== gameData.user_color` — the machinery for "classify against whoever actually moved" already exists in the live path; D1 just needs the RUNG lookup to use the same `mover` variable instead of the shared `selectedElo`.

### D3 — the readiness transition

Confirmed via quick 260714-rj5 (`c9e94ea2`, shipped the same day this phase was scoped): `useLibraryGame(gameId, { live: true })` is now called **unconditionally** in game mode (`Analysis.tsx:597-600`), not just for bot games. `useLibraryGame`'s `live` option wires `refetchInterval` to a pure function `libraryGamePollInterval(data, elapsedMs)` (`useLibrary.ts:42-49`): it returns `LIBRARY_GAMES_POLL_INTERVAL_MS` (3000ms, `useEvalCoverage.ts:15`) while `analysis_state === 'no_engine_analysis'` and the elapsed time is under `LIBRARY_GAME_POLL_TIMEOUT_MS` (10 minutes, `useLibrary.ts:32`), and `false` (no more polling) once the card is analyzed or the backstop trips.

`evalChartReady` (`Analysis.tsx:2214`, per the rj5 plan's own interface notes) is: `isGameMode && gameId != null && gameData?.eval_series != null && gameData.flaw_markers != null && gameData.phase_transitions != null && gameData.moves != null`. This is **exactly** the transition D3's amendment needs: a `useEffect` keyed on `evalChartReady` (or more precisely on `gameData?.eval_series != null`) flipping `false → true` is the correct, already-shipped signal to (re)start the sweep — no new polling/query machinery is needed, the TanStack Query poll from quick 260714-rj5 already delivers this transition for exactly the case the amendment calls out (a bot game opened while its tier-1 analysis is still running).

**Concrete implementation note:** do not gate the sweep-start effect on mount (`useEffect(() => {...}, [])`) — gate it on the VALUE of `evalChartReady` (or `gameData?.eval_series`) changing, with a ref tracking "already swept this game_id" so a later poll-driven re-render (e.g. flaw markers updating) does not re-trigger a full re-sweep. Suggested shape:

```typescript
const sweptGameIdRef = useRef<number | null>(null);
useEffect(() => {
  if (!evalChartReady || gameId == null || sweptGameIdRef.current === gameId) return;
  sweptGameIdRef.current = gameId;
  // start sweep
}, [evalChartReady, gameId]);
```

Games that are `analysis_state === 'no_engine_analysis'` with no active job at all (`active_eval_status === null`) never reach `evalChartReady`, and the poll never even starts (`libraryGamePollInterval` only fires while there IS a card — the existing Analyze-pill path is untouched, satisfying success criterion 4 for free).

### D6 — the backend field

`app/services/opening_lookup.py`'s trie walk (`find_opening`, lines 99-120):

```python
def find_opening(pgn: str | None) -> tuple[str | None, str | None]:
    moves = _normalize_pgn_to_san_sequence(pgn)
    if not moves:
        return None, None
    node = _TRIE
    last_result: tuple[str, str] | None = None
    for move in moves:
        if move not in node.children:
            break
        node = node.children[move]
        if node.result is not None:
            last_result = node.result
    if last_result is None:
        return None, None
    return last_result
```

The needed new function is additive and small — track the matching index alongside `last_result`, and skip `_normalize_pgn_to_san_sequence` entirely since the game-detail payload's `moves: list[str]` is already tokenized SAN (confirmed: `openings.tsv` and `game_positions.move_san` both use `python-chess`/`chess.js`-standard SAN including `O-O` castling notation — verified no format mismatch):

```python
def find_opening_ply_count(moves: list[str]) -> int:
    """1-based ply depth of the deepest known-opening match, or 0 if none."""
    node = _TRIE
    last_depth = 0
    for i, move in enumerate(moves):
        if move not in node.children:
            break
        node = node.children[move]
        if node.result is not None:
            last_depth = i + 1
    return last_depth
```

Existing callers of `find_opening` (`app/services/normalization.py:301,446,662`, `app/routers/position_bookmarks.py:115`) are untouched — this is a new, parallel function, not a signature change.

**Insertion point:** `app/services/library_service.py`'s `_build_card` (lines 373-621) is the single function that constructs `GameFlawCard` for BOTH `get_library_game` (single-game, used by `/analysis?game_id=`) and `get_library_games` (list). `moves_data` is set in both the unanalyzed branch (line 439-441, only when positions were fetched — single-game path per quick 260714-rj5) and the analyzed branch (line 541). Compute `opening_ply_count` once, right before the `GameFlawCard(...)` constructor call (~line 591), from whichever `moves_data` resulted:

```python
opening_ply_count = find_opening_ply_count(moves_data) if moves_data else 0
```

**Note for the planner:** because `_build_card` is shared, this computes (cheaply — a few dozen dict lookups against an already-loaded module-level trie) for every card that carries `moves_data`, including every row of a paginated Library list where the game is analyzed (list-mode already populates `moves_data` for analyzed games, unrelated to the rj5 change). This is negligible cost (tens of microseconds per game) but is a real scope question: either accept it uniformly (simplest — the field is cheap and harmless even where unused) or gate it to the single-game path only (matches the "when the game is opened" framing more literally, avoids a payload field on list-mode cards that no list-mode surface reads). Recommend accepting it uniformly; flag the alternative for planner discretion.

Add `opening_ply_count: int = 0` to `GameFlawCard` in `app/schemas/library.py` (near `moves: list[str] | None = None`, line 129) and to `frontend/src/types/library.ts`'s `GameFlawCard`-equivalent type (near the `moves` field, line ~92).

**Existing tests:** `tests/test_opening_lookup.py` has a `TestFindOpening` class (lines 72+) covering Italian/Sicilian/Queen's Gambit/King's Pawn/empty/None cases against `find_opening(pgn)` — a parallel `TestFindOpeningPlyCount` (or similar) exercising `find_opening_ply_count(moves)` against the SAME canonical openings, plus a mid-line-divergence case (moves that start in book and leave it) and an all-book case, is the natural Wave-0 gap.

### D8 — markers

Two SEPARATE code paths implement precedence differently today, confirmed by reading both:

1. **`VariationTree.tsx`'s `resolveMarkerIcon`** (lines 59-69) implements REAL precedence logic, because its input (`FlawMarkerEntry`, a merged map — `Analysis.tsx:moveListMarkers`) can legitimately carry BOTH a `severity` and a `gem` field on the same node (163-REVIEW WR-05: "a BACKEND severity... and the live WASM gem can legitimately disagree"):

```typescript
function resolveMarkerIcon(flaw: FlawMarkerEntry | undefined): {
  show: boolean; Icon: typeof BlunderIcon; isGem: boolean;
} {
  if (flaw != null && (flaw.severity === 'blunder' || flaw.severity === 'mistake')) {
    return { show: true, Icon: flaw.severity === 'blunder' ? BlunderIcon : MistakeIcon, isGem: false };
  }
  if (flaw?.gem) return { show: true, Icon: GemIcon, isGem: true };
  return { show: false, Icon: MistakeIcon, isGem: false };
}
```

  D8's book slot is a third, lowest clause: add `isBook: boolean` to the return type and `flaw?.book` as a new optional field on `FlawMarkerEntry` (mirroring `gem?`/`gemMaiaProbability?` etc., `VariationTree.tsx:140-169`), checked only after both the severity and gem branches fall through.

2. **`boardMarkers.tsx`'s `SquareMarkerBadge`** (lines 96-157) does NOT implement precedence internally — its `SquareMarker` type takes `severity?`/`gem?` as mutually-exclusive-by-construction fields (the doc comment says so explicitly: "No runtime assertion enforces the exclusivity — callers only ever set one or the other by construction"), and the actual precedence decision is made at the CALL SITE in `Analysis.tsx`'s `boardSquareMarkers` memo (lines 2046-2064): the gem marker is only appended `if (... !base.some((m) => m.square === lastMove.to && m.severity != null))`. D8's book marker needs the SAME pattern: a THIRD append, gated on the square having neither an existing severity NOR gem marker, e.g.:

```typescript
if (
  isBookPly && // current node's ply index < opening_ply_count
  lastMove != null &&
  !base.some((m) => m.square === lastMove.to && (m.severity != null || m.gem === true))
) {
  return [...withGem, { square: lastMove.to, book: true }];
}
```

  Add `book?: boolean` to `SquareMarker` (`boardMarkers.tsx:24-33`) and a rendering branch in `SquareMarkerBadge` (parallel to the existing `if (marker.gem) {...}` block, `boardMarkers.tsx:116-131`).

**Ply-index math:** mainline nodes have no explicit `ply` field on `MoveNode` — the ply number of `mainLine[i]` is `i + 1` (0-based array index). A node is "in book" when its index in `mainLine` is `< opening_ply_count`. `gameData.eval_series[i]`/`gameData.moves[i]` already align to this same ply indexing (per existing doc comments in `library.ts`), so no new alignment logic is needed.

**Icon/color:** `BookOpen` (lucide-react) is already used elsewhere in the codebase for the "opening" concept (`Import.tsx`, `GameCard.tsx`, `LibraryGameCard.tsx`, `EndgameInsightsBlock.tsx`) — reuse it for consistency rather than introducing a new icon. Per `theme.ts`'s existing hue allocation (blunder/mistake ~25/55, inaccuracy ~95, Maia violet 290, Stockfish blue 255, FlawChess gold 80, WDL green 145), a book marker should claim a genuinely unused, LOW-emphasis hue — a muted cool grey-blue (e.g. `oklch(0.55 0.06 230)`-ish) reads as "quiet reassurance," distinct from every existing warning/accent color, consistent with CLAUDE.md's "no hardcoded semantic colors — theme.ts only" rule. Mirror `gemGlyph.ts`'s "one record, two consumers" pattern with a new `bookGlyph.ts` (or extend an existing shared glyph module) so `VariationTree`'s icon and `boardMarkers`'s SVG circle can never drift.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Per-mover rating-at-game-time lookup with normalized/raw fallback | A second `*_lichess_blitz ?? raw` chain in the sweep module | Export/extract `deriveRawDefault`/`clampToLadderBounds` from `useMaiaEloDefault.ts` | Single source of truth for the fallback rule; a second implementation WILL drift the moment Phase 164's normalization edge cases change |
| SAN → UCI conversion for the free prefilter | A bespoke move-notation converter | `sanToUci(fen, san)` (`frontend/src/lib/sanToSquares.ts:63`) — already used by `useStockfishGradingEngine.ts` | `EvalPoint.best_move` is UCI; `moves`/played SAN is SAN — the comparison is a silent no-op (never matches) unless this conversion happens; already-battle-tested helper exists |
| Cancellable background engine work | A custom promise-cancellation scheme | `AbortController`/`AbortSignal`, mirroring `useFlawChessEngine.ts:229-291` and `workerPool.ts:404-431` | Already the project's established idiom for exactly this |
| Idle-time scheduling | A hand-rolled setInterval poll loop for "is the browser idle" | `requestIdleCallback` (feature-detected, `setTimeout` fallback) | Standard browser primitive; a poll loop would itself compete for CPU with the very engines it's trying to yield to |
| Opening-book depth | Shipping `openings.tsv`/the trie to the frontend | Backend `find_opening_ply_count`, additive field on the existing payload | D6 explicitly rejected this (bundle cost in a mobile-first PWA to answer one boolean per ply) |

**Key insight:** every "don't hand-roll" item above is not a generic library recommendation — it's "don't re-implement a function that already exists three call-sites away in this exact codebase." The entire phase is glue code between existing, well-tested primitives.

## Common Pitfalls

### Pitfall 1: Feeding a sweep FEN through the SAME hook instance the live position uses
**What goes wrong:** The live gem badge for the CURRENT node stalls or shows stale data while a background sweep candidate is mid-search/mid-inference.
**Why it happens:** `useStockfishGradingEngine` and `useMaiaEngine` are both single-FEN, single-in-flight-request hooks by design (see Architecture Patterns §D5 Key finding 1) — they have no queue, no priority, and (for Maia) silently drop a second concurrent request rather than servicing both.
**How to avoid:** Dedicated worker instance(s) for the sweep, never the same hook call used for `gemGrading`/`grading`/the live `maia` curve.
**Warning signs:** A test that starts a live gem-grading request WHILE a sweep candidate is in flight and asserts the live request still resolves promptly — if this test can't be written without mocking away the contention entirely, the implementation shares state it shouldn't.

### Pitfall 2: Comparing SAN to UCI in the free prefilter
**What goes wrong:** `played === best_move` never matches (or matches only by accident on 1-character pawn pushes), silently defeating the entire "free" tier and pushing every ply into the expensive Maia/Stockfish tiers.
**Why it happens:** `gameData.moves[i]` is SAN (`"Nf3"`); `EvalPoint.best_move` is UCI (`"g1f3"`) — confirmed by the type comments in `frontend/src/types/library.ts:92,106`.
**How to avoid:** Convert the played SAN to UCI via `sanToUci(parentFen, playedSan)` before comparing to `best_move`, exactly as `useStockfishGradingEngine.ts` already does for its own candidate-set construction.
**Warning signs:** The sweep resolving suspiciously slowly / issuing far more Maia calls than the seed's own cost model ("a few Stockfish passes per game, not eighty") implies — a red flag that the free prefilter isn't actually filtering anything.

### Pitfall 3: `requestIdleCallback` is not universally available
**What goes wrong:** The sweep throws or silently never runs on browsers without `requestIdleCallback` (older Safari).
**Why it happens:** It is not part of every browser's baseline (unlike `requestAnimationFrame`).
**How to avoid:** Feature-detect (`typeof window.requestIdleCallback === 'function'`) and fall back to `setTimeout(cb, 1)` (or a small fixed delay) — this pattern is not yet used anywhere in the codebase, so there is no existing precedent to copy; document the fallback explicitly rather than assuming universal support.
**Warning signs:** The sweep works in local Chrome dev testing but a code-reviewer/CI browser-matrix flags it, or a Safari UAT session shows book/gem badges never filling in ahead of the cursor.

### Pitfall 4: `LIVE_EVAL_CACHE_MAX = 256` is a per-Map FIFO, shared with live free-variation exploration
**What goes wrong:** A sweep-resolved gem at move 8 is silently evicted (FIFO, not LRU) by the time the user has explored enough free variations to push 256 more entries through `maiaCurveByFen`/`gemByNode`, and the badge disappears on scroll-back.
**Why it happens:** `engineEvalByFen`, `maiaCurveByFen`, `liveFlawByNode`, and `gemByNode` (`Analysis.tsx:120,1302,1335,1406,1521`) are FOUR separate `Map`s, each independently capped at the SAME `LIVE_EVAL_CACHE_MAX` constant, evicting oldest-inserted-first. A background sweep populating dozens of `maiaCurveByFen` entries up front (to run C1 for every free-prefilter survivor) consumes a meaningful fraction of that budget before the user has even started navigating; subsequent free-variation exploration can then evict early sweep results.
**How to avoid:** Since the sweep is explicitly MAINLINE-ONLY (D2/scope) with a known, bounded length (`mainLine.length`, realistically well under a few hundred plies), give the sweep its OWN cache map(s) sized to the mainline (no eviction needed at all, since the size is bounded and known upfront) rather than writing into the shared, FIFO-256-capped, free-variation-scoped `maiaCurveByFen`/`gemByNode`. If reusing `gemByNode` for display simplicity, at minimum decouple its cap from the other three maps' shared constant and size it generously against `mainLine.length`.
**Warning signs:** A long-game (200+ ply) manual UAT pass where an early-game gem badge (visible right after the sweep completes) is gone by the time the user has explored several sidelines and scrolled back.

### Pitfall 5: Gating the sweep-start effect on mount instead of on the readiness *transition*
**What goes wrong:** A bot game opened while its tier-1 analysis is still running never gets swept, even after the poll delivers the completed evals (violates ROADMAP success criterion 7 / D3's amendment).
**Why it happens:** A naive `useEffect(() => { startSweep(); }, [])` (mount-only) fires once while `gameData.eval_series` is still `null`, sees nothing to sweep, and never re-checks.
**How to avoid:** Gate the sweep-start effect on `evalChartReady` (or `gameData?.eval_series != null`) as a dependency, with a per-`gameId` "already swept" ref so the poll's later re-renders (once analyzed) don't re-trigger, but the FIRST transition into `evalChartReady === true` does.
**Warning signs:** Manual UAT step "open a just-finished bot game, wait for the pill to flip to the eval chart, confirm gem/book badges then fill in ahead of the cursor" fails specifically for bot games opened via the Quick 260714-rj5 live-polling path, while working fine for already-analyzed imported games opened normally.

### Pitfall 6: The hardcoded `GEM_MAIA_MAX_PROB === 0.1` test
**What goes wrong:** `gemMove.test.ts:58-59` (`it('D-07: GEM_MAIA_MAX_PROB is exactly 0.1', ...)`) fails the moment the constant is bumped to 0.20, for a reason that has nothing to do with a real regression.
**Why it happens:** The test pins the literal value, and D7 changes that literal by design.
**How to avoid:** Update this test's literal (and its description) to `0.2` as part of the same commit that changes `gemMove.ts:25` — this is an expected, deliberate test update, not a Rule-1 bug.
**Warning signs:** None needed — this WILL fail immediately on `npm test`, which is the point (the test IS the pin).

## Code Examples

### The free prefilter (D4, tier 1)

```typescript
// Illustrative shape — not a literal file. Pure, worker-free (mirrors gemMove.ts's
// own stated rationale for testability without mocking React/Workers).
import { sanToUci } from '@/lib/sanToSquares';
import type { EvalPoint } from '@/types/library';

interface SweepCandidate {
  plyIndex: number; // 0-based index into mainLine/moves/eval_series
  parentFen: string;
  playedSan: string;
}

function selectSweepCandidates(
  moves: string[],
  evalSeries: EvalPoint[],
  openingPlyCount: number,
  fenAtPly: (i: number) => string, // parent FEN before moves[i]
): SweepCandidate[] {
  const survivors: SweepCandidate[] = [];
  for (let i = 0; i < moves.length; i++) {
    if (i < openingPlyCount) continue; // D6/D8: book plies never enter the cascade
    const point = evalSeries[i];
    const playedSan = moves[i];
    if (point?.best_move == null || playedSan === undefined) continue;
    const parentFen = fenAtPly(i);
    const playedUci = sanToUci(parentFen, playedSan);
    if (playedUci === null || playedUci !== point.best_move) continue; // D4: strict equality, fails safe
    survivors.push({ plyIndex: i, parentFen, playedSan });
  }
  return survivors;
}
```

### The abort-on-navigation pattern (mirrors `useFlawChessEngine.ts:214-291`)

```typescript
// Illustrative — the established project idiom for "abort stale background work
// the instant the thing driving it changes," applied to a sweep-dedicated worker.
useEffect(() => {
  sweepAbortRef.current?.abort();
  const controller = new AbortController();
  sweepAbortRef.current = controller;
  // ... schedule the next idle-time sweep step, checking controller.signal.aborted
  // before dispatching and before committing a result.
  return () => controller.abort();
}, [currentNodeId]); // re-arm whenever the cursor moves
```

## State of the Art

| Old Approach | Current Approach (this phase) | When Changed | Impact |
|--------------|-------------------------------|---------------|--------|
| Gem rung follows the reactive ELO slider (`nearestByElo(parentCurve, selectedElo)`) | Gem rung pinned per-node to the mover's own rating-at-game-time (`deriveRawDefault(..., mover)`) | This phase (D1) | Gems stop shifting when the slider moves; makes background sweep results cacheable/stable |
| Gems resolve lazily, exactly at the position the user is standing on | Gems resolve ahead of the cursor via a background sweep | This phase (D4/D5) | Badges visible before the user reaches the move, not after |
| No opening-book awareness in the gem/marker system (SEED-092 D-02: explicitly "no opening-ply guard") | `opening_ply_count` gates the sweep AND renders book markers (D6/D8) | This phase — explicitly supersedes SEED-092 D-02 | Memorized theory moves no longer eligible for gem badges; book plies get their own marker |
| `GEM_MAIA_MAX_PROB = 0.10` ("hard to find" = top-10%-rarest) | `GEM_MAIA_MAX_PROB = 0.20` ("hard to find" = top-20%-rarest) | This phase (D7) | More gems overall, disproportionately for strong players (2600-rung C1 pass rate on C2-qualifying positions was only 2.9% before the raise) |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | A muted grey-blue hue is the right visual choice for the book marker (no locked design decision exists for this) | Architecture Patterns §D8 | Low — purely cosmetic, easy to adjust in review; CLAUDE.md's theme.ts-only rule is the hard constraint, the specific hue is a suggestion |
| A2 | The recommended sweep architecture (dedicated worker instances, idle-callback throttling, reduced movetime cap) is the right shape versus migrating onto `workerPool.ts`'s priority queue | Architecture Patterns §D5 | Medium — this is explicitly flagged as Claude's Discretion in CONTEXT.md; the research presents both options and argues for the smaller one, but the planner/executor should treat this as a real design choice, not a locked fact |
| A3 | A realistic upper bound on mainline length for cache-sizing purposes is "a few hundred plies" | Common Pitfalls §4 | Low — this number comes from CONTEXT.md's own risk section ("~200 plies at worst"), not independently verified against the actual `games.ply_count` distribution in production; if real games run meaningfully longer, the dedicated sweep cache should size generously rather than hard-coding a number |
| A4 | How many Maia inferences the sweep will actually issue per typical real game after the free prefilter is unmeasured (explicitly deferred to UAT per CONTEXT.md's Deferred Ideas) | Architecture Patterns §D5 | Medium — if the free-prefilter survivor count turns out much larger than expected for club-level play, the sweep's total wall-clock time and CPU footprint could be larger than the "a few passes per game" framing assumes; this is explicitly out of scope to measure before shipping, per the locked decision, but the scheduler design should degrade gracefully (throttled, abortable) regardless of the actual count rather than assuming it will always be small |

**If this table is empty:** N/A — see entries above.

## Open Questions

1. **Should `opening_ply_count` be computed for every card in `_build_card`, or gated to the single-game path only?**
   - What we know: `_build_card` is shared by `get_library_game` (single) and `get_library_games` (list); computing it unconditionally is cheap (a few dozen dict lookups) but runs for every analyzed game in a paginated list, where nothing currently reads it.
   - What's unclear: whether the planner considers "cheap and simple, computed everywhere" or "gated to the single-game path, matching the on-read framing literally" the better default.
   - Recommendation: compute unconditionally (simpler code, negligible cost); revisit only if a future profiling pass shows list-endpoint latency regressing.

2. **Dedicated sweep worker vs. `workerPool.ts` priority-queue migration (see Architecture Patterns §D5's discretion note).**
   - What we know: both are architecturally valid; the pool route is the "more correct" long-term shape (POOL-02 was built for this) but is a larger refactor touching the live `gemGrading` hook's own design.
   - What's unclear: whether the phase's time-box favors the smaller, isolated change.
   - Recommendation: dedicated worker for this phase; leave the pool migration as a natural follow-up once Phase 155's MCTS priority caller (if ever built) creates a second real consumer of the same mechanism.

3. **Real-game Maia-C1-survivor rate is unmeasured (by design, per CONTEXT.md's explicit deferral).**
   - What we know: the Phase 165 calibration TSV's 21.8% C2-pass rate is from an enriched sample and does not transfer to absolute frequency.
   - What's unclear: whether a typical ~60-90 ply real game produces 5 sweep candidates or 50 after the free prefilter.
   - Recommendation: build the scheduler to degrade gracefully regardless (throttled, abortable, one-at-a-time) rather than sizing anything against an assumed candidate count; treat the UAT pass on a handful of real games as the actual measurement.

## Environment Availability

Not applicable — no new external tool/service/runtime dependencies. Everything (Stockfish WASM binary, Maia ONNX model + onnxruntime-web, the SAN trie/TSV) is already vendored and present in the repo.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Backend framework | pytest (existing `tests/test_opening_lookup.py`, `tests/services/test_library_service.py`) |
| Frontend framework | Vitest (existing `frontend/src/lib/__tests__/gemMove.test.ts`, `frontend/src/pages/__tests__/Analysis.test.tsx` — 1243 lines, already mocks `useStockfishGradingEngine`/`useMaiaEngine`/`useStockfishEngine` module-wide) |
| Config file | `pyproject.toml` (pytest), `frontend/vite.config.ts`/`vitest` config (existing, unchanged) |
| Quick run command | `uv run pytest tests/test_opening_lookup.py tests/services/test_library_service.py -x -q`; `cd frontend && npm test -- --run src/lib/__tests__/gemMove.test.ts src/pages/__tests__/Analysis.test.tsx` |
| Full suite command | `uv run pytest -n auto`; `cd frontend && npm test -- --run` |

### Phase Requirements → Test Map

| Success Criterion | Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|---|
| 1 (cascade) | Free prefilter correctly converts SAN→UCI and compares against `best_move`; out-of-book plies excluded | unit | `npm test -- --run src/lib/__tests__/gemSweep.test.ts` | ❌ Wave 0 (new pure module) |
| 2 (yield-to-cursor) | A live gem-grading request started while a sweep candidate is mid-flight resolves without waiting on the sweep's queue/worker | unit (the load-bearing one — see Pitfall 1) | `npm test -- --run src/lib/__tests__/gemSweep.test.ts` (or a dedicated scheduler test file) | ❌ Wave 0 |
| 3 (rung pin) | Changing `selectedElo` (the slider) does NOT change which nodes classify as gems; changing `sideToMove`/mover DOES change the rung used | unit | `npm test -- --run src/hooks/__tests__/useMaiaEloDefault.test.ts` (extend) | Existing file, new cases |
| 4 (unanalyzed stays lazy) | A card with `analysis_state === 'no_engine_analysis'` and `active_eval_status === null` never triggers a sweep-start effect | unit | `npm test -- --run src/pages/__tests__/Analysis.test.tsx` | Existing file, new cases |
| 5 (threshold raise) | `GEM_MAIA_MAX_PROB === 0.2`; a probability of 0.15 that failed before now passes C1 | unit | `npm test -- --run src/lib/__tests__/gemMove.test.ts` | Existing file, literal update required (Pitfall 6) |
| 6 (`opening_ply_count` + markers) | `find_opening_ply_count` returns correct depth for exact/partial/no book match; `resolveMarkerIcon`/`SquareMarkerBadge` apply `severity > gem > book` | unit | `uv run pytest tests/test_opening_lookup.py -x -q`; `npm test -- --run src/components/analysis/__tests__/VariationTree.test.tsx src/components/board/__tests__/boardMarkers.test.tsx` | opening_lookup: existing file, new cases; VariationTree/boardMarkers: existing test files, new cases |
| 7 (bot-game mid-analysis sweep trigger) | Sweep-start effect fires on the `evalChartReady` FALSE→TRUE transition, not only at mount | unit | `npm test -- --run src/pages/__tests__/Analysis.test.tsx` | Existing file, new case (mirrors the rj5 "flips from unanalyzed to analyzed" test already in this file) |

### Sampling Rate

- **Per task commit:** the relevant unit test file(s) from the table above, plus `uv run ty check app/ tests/` / `npx tsc -b --noEmit` for the touched language.
- **Per wave merge:** `uv run pytest -n auto -x`; `cd frontend && npm run lint && npm run knip && npx tsc -b --noEmit && npm test -- --run`.
- **Phase gate:** full pre-merge gate (CLAUDE.md) green before `/gsd-verify-work`, PLUS a manual UAT pass on a real, already-analyzed game and a real bot game opened mid-tier-1-analysis, watching gem/book badges fill in ahead of the cursor without perceptible lag on the current position.

### Wave 0 Gaps

- [ ] `frontend/src/lib/__tests__/gemSweep.test.ts` (or equivalent) — covers the free-prefilter purity (success criterion 1) and, critically, the yield-to-cursor invariant (success criterion 2) via a REVERT-and-fail-red test per the project's own mutation-test-gap-closure discipline: start a live gem-grading request, THEN start a sweep candidate, assert the live request's result lands without measurable delay attributable to the sweep. A test that only asserts "the sweep resolves gems" does NOT prove this invariant — it must specifically exercise contention.
- [ ] `tests/test_opening_lookup.py::TestFindOpeningPlyCount` (or similar) — new test class for `find_opening_ply_count`, covering exact match, partial match (game leaves book), no match, and the empty-moves-list edge case.
- [ ] `frontend/src/hooks/__tests__/useMaiaEloDefault.test.ts` — extend with a case proving `selectedElo`/slider changes do not affect a pinned-per-node rung once `deriveRawDefault`/`clampToLadderBounds` are exported and called with a fixed `sideToMove` per node (this is the D1 behavior-change regression test).
- [ ] `frontend/src/components/analysis/__tests__/VariationTree.test.tsx` — extend `resolveMarkerIcon` coverage with a `book`-only case and a `severity + book` case (severity wins).
- [ ] `frontend/src/components/board/__tests__/boardMarkers.test.tsx` — extend with a `book` marker render case.

**Note on the "half-invariant" risk (per project memory on mutation-test gap closures):** D5's yield-to-cursor requirement is exactly the shape of invariant that tsc/eslint/knip/existing-tests are structurally blind to — a sweep that technically "runs in the background" but happens to share a worker/hook instance with the live path will pass every type check and every test that doesn't specifically construct contention. The Wave 0 gap above must be written as a genuine contention test (start both, assert ordering/latency), not a "does the sweep exist" smoke test. If in doubt, prove it the way the project's own memory prescribes: implement the sweep sharing a worker with the live path first, confirm the contention test FAILS, then implement the dedicated-worker fix and confirm it turns green.

## Security Domain

`security_enforcement` is not explicitly disabled in `.planning/config.json` (absent under `workflow`), so this section is included per protocol, scoped honestly to what's actually applicable — this phase has almost no new attack surface.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---|---|---|
| V2 Authentication | No | No auth surface touched |
| V3 Session Management | No | No session surface touched |
| V4 Access Control | No | `opening_ply_count` is derived from data (`moves`) already gated by the SAME ownership check `get_library_game`/`get_library_games` already enforce (`game.user_id != user_id` → `None`, per the T-RJ5-01 threat register precedent) — no new IDOR surface |
| V5 Input Validation | Marginal | `moves: list[str]` is already a validated Pydantic field on the existing payload; `find_opening_ply_count` only ever reads from this already-typed list, never from raw user input — no new validation surface |
| V6 Cryptography | No | Not touched |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---|---|---|
| Client-side CPU/battery exhaustion (a runaway sweep pegging cores indefinitely) | Denial of Service (against the USER's own device, not the server) | Not a server-side threat, but a real UX/reliability risk — mitigated by the throttling/mobile-gating/tab-hidden-pause discipline in Architecture Patterns §D5. Worth a STRIDE-adjacent note even though it's client-not-server: an unbounded sweep is effectively a self-inflicted DoS on the user's own browser tab. |
| None new on the backend | — | `opening_ply_count`'s computation touches no new trust boundary — it reads the same already-fetched, already-scoped `moves` list every other field on `GameFlawCard` already reads from |

## Sources

### Primary (HIGH confidence — verified by reading the shipped source)
- `frontend/src/pages/Analysis.tsx` (2857 lines) — full gem-resolution block (1414-1539), board marker construction (2046-2064), `evalChartReady`/`useLibraryGame` wiring (594-600, 2206-2226), worker-instantiation call sites (557, 906, 1476)
- `frontend/src/hooks/useStockfishGradingEngine.ts` (459 lines) — single-FEN state machine, no priority/preemption
- `frontend/src/hooks/useMaiaEngine.ts` (347 lines) — single-in-flight-request drop behavior, no priority/preemption
- `frontend/src/lib/engine/workerPool.ts` (485 lines) — abortable priority queue, `priority`/`depth` fields unused today
- `frontend/src/hooks/useFlawChessEngine.ts` — established `AbortController` + "stale ONNX result is harmless" pattern
- `frontend/src/hooks/useMaiaEloDefault.ts` (159 lines) — `deriveRawDefault`/`clampToLadderBounds`, the D1 data source
- `frontend/src/lib/gemMove.ts` (92 lines) — `GEM_MAIA_MAX_PROB`, `classifyGem`, `summarizeForGem`
- `frontend/src/lib/gemGlyph.ts`, `frontend/src/lib/theme.ts` — existing color-token pattern for markers
- `frontend/src/components/analysis/VariationTree.tsx` (lines 1-170) — `resolveMarkerIcon`, `FlawMarkerEntry`
- `frontend/src/components/board/boardMarkers.tsx` (184 lines) — `SquareMarker`, `SquareMarkerBadge`
- `frontend/src/types/library.ts` — `EvalPoint` (SAN vs UCI distinction), `GameFlawCard`-equivalent fields
- `app/services/opening_lookup.py` (121 lines) — trie structure, `find_opening`
- `app/services/library_service.py` (`_build_card` 373-621, rating-normalization block 548-589) — payload construction, flawchess-passthrough guard
- `app/services/chesscom_to_lichess.py` (`normalize_to_lichess_blitz`) — confirms bot-game ratings are already lichess-blitz-scale
- `app/schemas/library.py` (`GameFlawCard`) — additive-field insertion point
- `tests/test_opening_lookup.py`, `frontend/src/lib/__tests__/gemMove.test.ts` — existing test shapes/hardcoded literals
- `.planning/quick/260714-rj5-.../260714-rj5-SUMMARY.md` + `260714-rj5-PLAN.md` — the live-updating analysis board (D3's readiness-transition mechanism)

### Secondary (MEDIUM confidence)
- CONTEXT.md / SEED-106 itself — the locked decisions, treated as authoritative per the untrusted-input-boundary rule for user-approved decisions

### Tertiary (LOW confidence — flagged in Assumptions Log)
- The suggested book-marker hue (a cosmetic suggestion, not verified against any design review)
- The dedicated-worker-vs-pool-migration recommendation (a documented discretion call, not a locked fact)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries, every primitive read directly from the shipped source
- Architecture (worker contention model): HIGH — verified by reading all five existing worker-instantiation sites plus the two hooks' full implementations; MEDIUM on the specific recommended shape (dedicated-worker-vs-pool), which is explicitly Claude's Discretion per CONTEXT.md
- Rung pin (D1): HIGH — `deriveRawDefault` read in full, bot-game passthrough confirmed server-side
- Backend field (D6): HIGH — `opening_lookup.py` and `library_service.py` read in full, SAN-format compatibility spot-checked
- Markers (D8): HIGH — both `resolveMarkerIcon` and `SquareMarkerBadge`/`boardSquareMarkers` construction read and precedence mechanisms confirmed to differ (real logic vs. construction-time exclusivity)
- Pitfalls: HIGH — all five pitfalls are traced to specific, cited lines of already-shipped code, not speculative

**Research date:** 2026-07-14
**Valid until:** 30 days (stable, in-repo code; the only external-ish dependency, the Phase 165 calibration TSV's ratio-transfer caveat, does not decay on any particular schedule)
