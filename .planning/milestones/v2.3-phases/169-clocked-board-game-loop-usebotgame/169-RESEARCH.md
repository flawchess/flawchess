# Phase 169: Clocked Board + Game Loop (`useBotGame`) - Research

**Researched:** 2026-07-12
**Domain:** React game-loop hook orchestration (chess clocks, chess.js end-condition detection, client-only audio, PGN annotation) on top of a frozen engine core (Phases 153-168.5)
**Confidence:** HIGH (engine seam, chess.js API, PGN backend contract, existing board component all directly verified in-repo) / MEDIUM (clock/audio architecture patterns — no in-repo precedent, drawn from well-established React/PWA idioms) / LOW→CORRECTED (D-08's sound-set license premise — see Pitfall 1, now HIGH after direct verification)

## Summary

This phase builds one new orchestrating hook (`useBotGame`) plus five categories of net-new UI (dual clocks, sound, result screen, move list, resign/draw controls) around code that is **entirely frozen and must not be modified**: `selectBotMove` (Phase 166), `botBudget.ts` constants (Phase 168.5), and `ChessBoard.tsx` (existing). The hook's job is pure orchestration — chess.js already owns every rules question (legality, end conditions, PGN/comment serialization), `selectBotMove` already owns move selection, and `ChessBoard.tsx` already owns board rendering/input. Nothing here should reimplement chess rules or search.

The most consequential finding is a **license correction to locked decision D-08**: lichess's "standard" sound set (the one D-08 names) is explicitly listed as a **non-free exception** in lila's own `COPYING.md`, not AGPLv3+. Four *other* lila sound directories (`futuristic`, `nes`, `piano`, `sfx`) are genuinely AGPLv3+ (compatible with FlawChess's own AGPL-3.0), and critically **share the exact same filename convention** (`Move.mp3`, `Capture.mp3`, `Check.mp3`, `Checkmate.mp3`, `Draw.mp3`, `Victory.mp3`, `Defeat.mp3`, `LowTime.mp3`, `GenericNotify.mp3`, `Confirmation.mp3`, `Error.mp3` — both `.mp3`/`.ogg`). This means the D-08 vendoring plan is executable almost unchanged, just pointed at a different (still lichess-sourced, still license-compatible) subdirectory: this needs a one-line correction, not a redesign, but it must be surfaced before planning locks it in silently.

Everything else needed to plan this phase well is already in the repo: `selectBotMove`'s `AbortSignal` cancellation contract, `useFlawChessEngine.ts`'s provider-lifecycle pattern to mirror, chess.js's `isCheckmate`/`isStalemate`/`isThreefoldRepetition`/`isDrawByFiftyMoves`/`isInsufficientMaterial`/`isDraw` end-condition surface, chess.js's `setComment`/`pgn()` pair for `[%clk]` emission, the backend's exact `[Termination "..."]` header vocabulary and `tc_str` format (`"180+2"`, base+increment **seconds**, NOT a minutes display label), and `buildAnalysisLineUrl` for the D-12 deep link. No new npm dependencies are required.

**Primary recommendation:** Build `useBotGame` as a single stateful hook wrapping a `chess.js` `Chess` instance + a wall-clock-delta dual-clock reducer + a thin sound-effect module, calling `selectBotMove` directly (harness-style, not through `useFlawChessEngine`) with an `AbortController` per bot turn; drive the D-05 pacing reconciliation (real-time tick vs. synthetic debit) as two independent numbers reconciled only at move-reveal time, never fighting each other mid-think.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Chess rules / legality / end conditions | Browser (client) | — | chess.js is the single source of truth; locked decision 1 (167-CONTEXT/STATE) — game runs entirely client-side until finished |
| Bot move selection | Browser (client) | — | `selectBotMove` (Phase 166) — frozen, provider-agnostic, already client-side |
| Dual clocks (Fischer increment, wall-clock delta) | Browser (client) | — | No server round-trip per move; clock state is pure client timing math |
| Bot pacing (reveal delay, synthetic debit) | Browser (client) | — | UX-only theater layered on top of the search result (168.5 D-04b: harness has none) |
| Sound effects | Browser (client) | — | `HTMLAudioElement`, no server involvement |
| Result screen / move list / resign-draw UI | Browser (client) | — | Presentational React components |
| PGN generation with `[%clk]` | Browser (client) | — | chess.js `setComment`/`pgn()` — the finished PGN is *produced* here; POSTing it is Phase 171 |
| PGN validation (`[%clk]` gate, `[Termination]` vocabulary, tc_str parsing) | API / Backend | — | Already shipped (Phase 167, `normalize_flawchess_game`) — this phase must produce PGN the backend's frozen validator accepts, but does not call it |
| Store-on-finish POST | API / Backend | — | Explicitly out of scope (Phase 171) |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| chess.js | 1.4.0 (installed) [VERIFIED: node_modules] | Rules engine, end-condition detection, PGN/comment (`[%clk]`) serialization | Already the project's sole chess-logic dependency (CLAUDE.md); `1.4.0`'s public API confirmed via `node_modules/chess.js/dist/types/chess.d.ts` — no upgrade needed |
| react-chessboard | 5.10.0 (installed) [VERIFIED: node_modules] | Board rendering, drag + click-to-move | Already wrapped by `ChessBoard.tsx`; reuse as-is |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `HTMLAudioElement` (browser built-in, no package) | n/a | Move/capture/check/game-end/low-time/notify sounds | Six short one-shot clips with no mixing/spatial requirements — `new Audio(url); audio.play()` is sufficient; no Web Audio API graph needed |
| Page Visibility API (browser built-in, no package) | n/a | Pause clock ticking while tab hidden during bot's turn (SC2) | `document.visibilityState` + `visibilitychange` listener — standard, no polyfill needed for any evergreen browser FlawChess targets |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Native `HTMLAudioElement` | `howler.js` | Howler adds sprite-sheet batching and better mobile-autoplay handling, but is a new dependency for six independent short clips with no overlap/spatial needs — not justified here. Revisit only if autoplay-unlock friction proves real on iOS Safari (see Pitfall 4). |
| Direct `selectBotMove` call per turn | `useFlawChessEngine` hook | `useFlawChessEngine` is built for the *analysis* board's anytime-refining UI (throttled `onSnapshot`, device-adaptive pool sizing) — bot play wants a single resolved move, pinned concurrency (168.5 D-09), and no intermediate snapshot commits. `useBotGame` should call `selectBotMove` + `createWorkerPool()`/`createMaiaQueue()` directly, harness-style, not route through the analysis hook. |
| `setInterval`-driven clock display | `requestAnimationFrame` | `setInterval` at ~100ms is standard for chess clocks (lichess itself does this) and is what the D-07 tenths-precision display needs; `requestAnimationFrame` is unnecessary tick-rate precision for a text display and burns more CPU on a backgrounded/inactive tab (though visibility-paused anyway per SC2). |

**Installation:** None — no new packages required for this phase.

**Version verification:**
```bash
$ cat frontend/node_modules/chess.js/package.json | grep '"version"'
"version": "1.4.0"
$ cat frontend/node_modules/react-chessboard/package.json | grep '"version"'
"version": "5.10.0"
```
Both match `frontend/package.json`'s declared ranges (`^1.4.0`, `^5.10.0`) — installed, current, no drift.

## Package Legitimacy Audit

**No new external packages are introduced by this phase.** All required capabilities (chess rules, board rendering, audio playback, tab-visibility detection, localStorage) are covered by already-installed dependencies or browser built-ins. This section is intentionally empty per the "skip if no new packages" allowance — flagged explicitly rather than omitted, since a package-heavy prior phase (154, ONNX) might make "core+supporting" tables look install-shaped when they are not.

## Architecture Patterns

### System Architecture Diagram

```
User input (drag/click on ChessBoard)
        │
        ▼
useBotGame.attemptMove(from, to, promotion?)
        │
        ├─ chess.js legality check (turn-gated: only if side-to-move === user's color)
        │       │
        │       ├─ illegal/wrong-turn → return false (board snaps back)
        │       │
        │       └─ legal → chess.move(); commit SAN + clock delta + [%clk] comment
        │                       │
        │                       ▼
        │              check end conditions (chess.js is*() methods)
        │                       │
        │            ┌──────────┴──────────┐
        │            │                     │
        │       game over              game continues
        │            │                     │
        │            ▼                     ▼
        │      → Result screen      Fischer increment applied to
        │        (SC3/D-11)          the mover's clock; switch side to bot
        │                                   │
        │                                   ▼
        │                     ┌─────────────────────────────┐
        │                     │  Bot turn orchestration       │
        │                     │  (AbortController per turn)   │
        │                     │                                │
        │                     │  1. start real-time clock tick │
        │                     │     (setInterval, Date.now()   │
        │                     │     delta) — bot clock visibly │
        │                     │     counts down (D-05)         │
        │                     │  2. fire selectBotMove(fen,    │
        │                     │     settings, deps, signal)    │
        │                     │     — search runs fixed budget │
        │                     │     from botBudget.ts (168.5)  │
        │                     │  3. Promise.all([search,       │
        │                     │     randomized reveal delay])  │
        │                     │     — D-03 floor for fast moves│
        │                     │  4. on resolve: stop real-time │
        │                     │     tick; debit = max(real     │
        │                     │     elapsed, synthetic         │
        │                     │     fraction-of-remaining)      │
        │                     │     clamped to never-flag floor │
        │                     │     (D-05)                      │
        │                     └─────────────────────────────┘
        │                                   │
        │                                   ▼
        │                     chess.move(botUci); commit SAN +
        │                     clock delta + [%clk] comment
        │                                   │
        │                                   ▼
        │                     check end conditions → loop back
        │                     to "user's turn" or → Result screen
        │
        ▼
Resign / Draw-offer / Draw-accept controls (side-effect into the
same end-condition path — see D-01..D-04 gates in Common Pitfalls)
        │
        ▼
On game end: chess.pgn() with per-ply setComment([%clk ...]) →
serializable PGN string handed to caller (Phase 171 POSTs it later;
this phase does NOT call the store endpoint)
```

### Recommended Project Structure
```
frontend/src/
├── hooks/
│   └── useBotGame.ts              # the game-loop hook — new
├── lib/
│   ├── chessClock.ts              # pure clock math (wall-clock delta, Fischer increment, low-time threshold) — new, unit-testable in isolation
│   └── sounds.ts                  # small standalone sound-effect module (D-08) — new, reusable by future surfaces
├── components/
│   └── bots/                      # new directory (Phase 169 UI only; Phase 171 adds setup/nav)
│       ├── ClockDisplay.tsx       # dual clock UI (D-06/D-07 pulsing-dot + tenths display)
│       ├── GameResultDialog.tsx   # D-11 dismissible modal
│       ├── GameResultStrip.tsx    # D-11 persistent inline strip
│       ├── MoveListPanel.tsx      # D-13 SAN move list + view-only scroll-back
│       └── GameControls.tsx       # resign/draw-offer/mute buttons
├── public/sound/                  # vendored AGPLv3+ lila sound set (see Pitfall 1) — new
└── pages/
    └── Bots.tsx                   # D-14 minimal stub route (lazy-loaded, unlinked from nav)
```

### Pattern 1: Provider bring-up mirrors `useFlawChessEngine.ts`, not its search-driving effect
**What:** Create `WorkerPool`/`MaiaQueue` once per game (mount), terminate on unmount, exactly like `useFlawChessEngine`'s provider-lifecycle effect. But do NOT copy its debounced-FEN → `mctsSearch` effect chain — that's built for continuous re-search on every analysis-board navigation. Bot play calls `selectBotMove` exactly once per bot turn, imperatively (inside an async function triggered by "it's the bot's turn now"), not via a `useEffect` keyed on `fen`.
**When to use:** Every bot-turn dispatch.
**Example:**
```typescript
// Source: frontend/src/hooks/useFlawChessEngine.ts (Pattern 1, adapted)
useEffect(() => {
  const pool = createWorkerPool();
  const queue = createMaiaQueue();
  poolRef.current = pool;
  queueRef.current = queue;
  return () => {
    pool.terminate();
    queue.terminate();
  };
}, []); // once per game, not re-run per FEN
```

### Pattern 2: `selectBotMove` call with per-turn `AbortController`
**What:** Every bot turn gets a fresh `AbortController`; `signal.abort()` is called on resign, "New game", route navigation, and (defensively) on unmount — mirroring `useFlawChessEngine`'s abort-on-disable guard.
**When to use:** Bot turn start/teardown.
**Example:**
```typescript
// Source: frontend/src/lib/engine/selectBotMove.ts signature (Phase 166, frozen)
const controller = new AbortController();
abortRef.current = controller;
const uci = await selectBotMove(
  fen,
  { elo: settings.botElo, blend: settings.blend, budget: {
      maxNodes: FLAWCHESS_BOT_MAX_NODES,
      maxPlies: FLAWCHESS_BOT_MAX_PLIES,
      concurrency: FLAWCHESS_BOT_CONCURRENCY,
      stopRule: FLAWCHESS_BOT_STOP_RULE,
    } },
  { policy: queue.policy, grade: pool.grade, rng: Math.random },
  controller.signal,
);
```
`selectBotMove`'s `budget.elo` is built internally as `{w: elo, b: elo}` (BOT-03) — the caller never supplies asymmetric ELO.

### Pattern 3: Reveal-delay + search run concurrently, clock reconciled once at resolve
**What:** D-03's reveal-delay floor and the search itself should run in parallel via `Promise.all`, not sequentially (a sequential `await search(); await delay();` would double-count elapsed time in the D-05 real-elapsed reconciliation).
**When to use:** Bot turn dispatch.
**Example:**
```typescript
const revealDelayMs = REVEAL_DELAY_MIN_MS + rng() * (REVEAL_DELAY_MAX_MS - REVEAL_DELAY_MIN_MS);
const turnStartedAt = Date.now();
const [uci] = await Promise.all([
  selectBotMove(fen, settings, deps, controller.signal),
  new Promise((resolve) => setTimeout(resolve, revealDelayMs)),
]);
const realElapsedMs = Date.now() - turnStartedAt;
const syntheticMs = computeSyntheticDebit(botClockRemainingMs, incrementMs); // named-constant divisor, D-02/168.5
const debitMs = Math.max(realElapsedMs, syntheticMs);
const clampedDebitMs = Math.min(debitMs, botClockRemainingMs - NEVER_FLAG_FLOOR_MS); // D-05 clamp
```

### Pattern 4: Wall-clock delta ticking, not `setInterval` cadence trust
**What:** Never accumulate elapsed time by counting `setInterval` firings (`count * intervalMs`) — background tab throttling means intervals can be delayed or coalesced by the browser for minutes. Always recompute `Date.now() - turnStartedAt` (or `- lastResumedAt` after a pause) on every tick and on `visibilitychange`.
**When to use:** Both the display tick and the eventual debit computation.
**Example (established idiom, not in-repo — CITED from MDN Page Visibility API):**
```typescript
// Source: MDN Page Visibility API guide (https://developer.mozilla.org/en-US/docs/Web/API/Page_Visibility_API)
useEffect(() => {
  const handleVisibility = () => {
    if (document.visibilityState === 'hidden') {
      pausedAtRef.current = Date.now();
    } else if (pausedAtRef.current !== null) {
      const pausedForMs = Date.now() - pausedAtRef.current;
      turnStartedAtRef.current += pausedForMs; // shift the anchor, not the elapsed total
      pausedAtRef.current = null;
    }
  };
  document.addEventListener('visibilitychange', handleVisibility);
  return () => document.removeEventListener('visibilitychange', handleVisibility);
}, []);
```

### Pattern 5: `[%clk]` PGN emission via chess.js `setComment`
**What:** chess.js associates comments with the FEN reached *after* a move via `setComment(text)` called immediately after `chess.move(...)`; `chess.pgn()` automatically wraps them in `{...}` in the exported PGN. This is exactly the lichess `{[%clk h:mm:ss]}` convention the backend's `node.clock()` parser (python-chess) expects.
**When to use:** After every move (both user and bot), for both colors (SC5/STORE-02).
**Example:**
```typescript
// Source: frontend/node_modules/chess.js/dist/types/chess.d.ts (setComment/pgn, verified)
chess.move({ from, to, promotion });
chess.setComment(`[%clk ${formatClockHms(remainingMsAfterIncrement)}]`);
// later: const pgnText = chess.pgn(); // comments auto-embedded per move
```
`formatClockHms` must produce lichess's `h:mm:ss` form (e.g. `0:04:57`), matching what `app/services/normalization.py`'s `node.clock()` (python-chess) parses — confirm exact format expectations against a real lichess-exported PGN sample if available, but `h:mm:ss` is the documented lichess convention.

### Pattern 6: `[Termination "..."]` header — closed vocabulary, backend-enforced
**What:** The backend's `_FLAWCHESS_TERMINATION_HEADER_MAP` recognizes exactly six literal strings: `"checkmate"`, `"resignation"`, `"timeout"`, `"draw"`, `"abandoned"`, `"unknown"` (verified `app/services/normalization.py:505-511`). Any other string falls back to board-derived termination server-side (not an error, but loses fidelity — e.g. a resign wouldn't be distinguishable from a generic draw/unknown if mislabeled).
**When to use:** `chess.setHeader('Termination', ...)` when finalizing the PGN, before Phase 171 POSTs it.
**Example:**
```typescript
// Source: app/services/normalization.py:505-511 (verified, backend contract)
chess.setHeader('Termination', outcome.reason); // 'checkmate' | 'resignation' | 'timeout' | 'draw' | 'abandoned' | 'unknown'
chess.setHeader('Result', outcome.pgnResult);   // '1-0' | '0-1' | '1/2-1/2'
```
Both `checkmate` (SC3 auto-detect) and `resignation` (D-04) map cleanly; `stalemate`/`threefold`/`fifty-move`/`insufficient-material` should all set `Termination: 'draw'` (the backend has no finer-grained draw-reason header) — client-side UI can still show the specific reason in the result dialog text, just not in the PGN header.

### Pattern 7: TC string format is base+increment **seconds**, not a display label
**What:** `parse_time_control`/`parse_base_and_increment` (backend, already shipped) expect `"180+2"` (180 base seconds + 2 increment seconds), NOT `"3+2"` (a lichess-style minutes+seconds display label). REQUIREMENTS.md's PLAY-02 presets are written in the minutes+seconds display convention (`3+2`, `5+3`, `10+5`, `30+20`) — `useBotGame`'s settings/PGN-building code must convert: `tc_str = `${minutes * 60}+${incrementSeconds}``.
**When to use:** D-14's hardcoded settings stub — whatever TC preset is hardcoded must be stored internally in the base-seconds format, not the display label, or the PGN's implicit TC bookkeeping (base clock initialization, increment application) will silently use the wrong numbers.
**Example:**
```typescript
// Source: app/services/normalization.py:572-575 docstring (verified) +
// STATE.md "[Phase 167]: tc_str is fed directly into parse_time_control in the
// existing seconds-based format; flagged for Phase 169/171 if the wire
// tc_preset value is ever a minutes-based label" (already flagged by Phase 167)
const PRESET_5_3 = { baseSeconds: 5 * 60, incrementSeconds: 3 }; // "5+3" preset
const tcStrForBackend = `${PRESET_5_3.baseSeconds}+${PRESET_5_3.incrementSeconds}`; // "300+3"
```

### Anti-Patterns to Avoid
- **Re-deriving chess rules by hand:** every end condition (SC3) has a direct chess.js method — `isCheckmate()`, `isStalemate()`, `isThreefoldRepetition()`, `isDrawByFiftyMoves()`, `isInsufficientMaterial()`, `isDraw()` (which is the OR of the draw sub-conditions), `isGameOver()` (OR of all of the above). Flag-on-time is the *only* end condition this phase must implement itself (it's a clock concept, not a board-state concept chess.js can see).
- **Threading the analysis board's `policyTemperature` into bot play:** `BotSettings.budget` structurally excludes `policyTemperature` (Phase 166 D-02, `Omit<SearchBudget, 'elo' | 'policyTemperature'>`) — this is enforced by TypeScript, not just convention; don't work around the `Omit` with an `as` cast.
- **Sequential `await search(); await delay();`:** double-counts real elapsed time against the D-05 `max(real, synthetic)` reconciliation — must be `Promise.all`.
- **Trusting `setInterval` tick counts for elapsed time:** background-tab throttling breaks this; always `Date.now() - anchor`.
- **A single shared `AbortController` across turns:** Phase 166 established the per-turn-fresh-controller pattern via `useFlawChessEngine`'s abort-before-new-search idiom; reusing one controller across the whole game means a `resign` mid-game can't distinguish "abort THIS think" from "the controller is already spent from a prior think."

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Threefold repetition / 50-move / insufficient material detection | A custom position-history tracker | `chess.isThreefoldRepetition()` / `chess.isDrawByFiftyMoves()` / `chess.isInsufficientMaterial()` | chess.js already tracks full position history internally (needed for its own `isDraw()`); a parallel Zobrist-based tracker (even though FlawChess already has Zobrist hashing server-side) would be a second, divergent source of truth for a client-only concern |
| PGN `[%clk]` / `[Termination]` emission | Manual string-templating of the PGN text | `chess.setComment()` + `chess.setHeader()` + `chess.pgn()` | chess.js already handles move-numbering, check/checkmate suffix (`+`/`#`), and comment placement correctly; hand-templating risks a subtly malformed PGN the backend's `chess.pgn.read_game()` (python-chess) parser rejects |
| Bot move selection / search | Anything | `selectBotMove` (frozen, Phase 166) | Explicitly out of scope — this phase CONSUMES it |
| Sound mixing / preloading | A custom `AudioContext` graph | `new Audio(url)` per clip, preloaded via `<link rel="preload">` or an eager `new Audio()` at module load | Six independent, non-overlapping, non-spatial one-shot clips is exactly `HTMLAudioElement`'s designed use case; Web Audio API buffers add real complexity (decode, node graph, resume-on-gesture) for zero benefit here |

**Key insight:** Every "hard" problem this phase touches (rules, search, board rendering) is already solved by frozen code one layer down. The genuinely new work is thin orchestration (the hook itself) and UI (clocks, sounds, result screen) — the risk is in *reconciliation logic* (D-05's max(real, synthetic) clock math, D-01's draw-accept gate) which has no library to lean on and must be built carefully with named constants per CLAUDE.md.

## Common Pitfalls

### Pitfall 1: D-08's sound-set license premise is wrong — "standard" is non-free
**What goes wrong:** Locked decision D-08 says "vendor the standard lichess sound set... FlawChess is AGPL-3.0 like lila — license-compatible." Direct verification of lila's `COPYING.md` shows the **"standard"** sound directory is explicitly listed under **"Exceptions (non-free)"** — it is NOT covered by lila's AGPLv3+ license grant.
**Why it happens:** lila (the whole webapp) is AGPL-3.0, but individual asset directories carry separate, narrower licenses documented in `COPYING.md`; "the code is AGPL" does not imply "every vendored asset is AGPL."
**How to avoid:** Vendor a **different** lila sound directory instead: `public/sound/sfx` or `public/sound/piano` (both explicitly AGPLv3+, credited to "Enigmahack" in `COPYING.md`) — these use the **identical filename convention** as "standard" (`Move.mp3`, `Capture.mp3`, `Check.mp3`, `Checkmate.mp3`, `Draw.mp3`, `Victory.mp3`, `Defeat.mp3`, `LowTime.mp3`, `GenericNotify.mp3`, `Confirmation.mp3`, `Error.mp3`, both `.mp3`/`.ogg`), so the D-08/D-09 sound-event mapping carries over unchanged — only the vendored subdirectory and the attribution line change. `LowTime.mp3` and `GenericNotify.mp3` map directly onto D-09's two extra sound events. Mirror the existing `README.md` "## Engine Binaries (GPLv3 License Note)" precedent with a new "## Sound Assets" section crediting Enigmahack + AGPLv3+.
**Warning signs:** Any plan or PR description that says "vendored the standard lichess sound set" without a corrected directory name — flag at plan-review time.

### Pitfall 2: react-chessboard 5.x has NO built-in promotion dialog
**What goes wrong:** Assuming `Chessboard`'s `options`/`onPieceDrop` surface exposes a promotion-piece picker prop (many chess UI libraries do). `frontend/node_modules/react-chessboard/dist/types.d.ts` has no `promotion`-related type at all.
**Why it happens:** react-chessboard 5.x deliberately delegates promotion entirely to the consumer's `onPieceDrop` callback logic.
**How to avoid:** The existing in-repo precedent (`useAnalysisBoard.ts:208`, `:509`) always auto-promotes to queen (`promotion: 'q'`) with a comment noting chess.js "ignores [the promotion param] for non-promotion moves." CONTEXT.md's "Claude's Discretion" note says "follow the existing analysis-board promotion pattern" — that pattern IS auto-queen, no dialog. If a genuine underpromotion picker is wanted, it is new UI work (a small square-anchored popover choosing among Q/R/B/N) with no precedent to copy; recommend the planner explicitly decide auto-queen-only vs. a new picker component rather than assuming a picker "already exists to follow."
**Warning signs:** A plan task referencing an existing promotion-picker component — there isn't one.

### Pitfall 3: `selectBotMove`'s search can legitimately take up to ~15s (168.5 measurement)
**What goes wrong:** Building the bot-turn UI (D-06's "thinking" indicator, the real-time clock tick) around an assumption that bot moves resolve in ~1-2s. 168.5's real measurement: median ~5.4s, **worst-case ~12.7s** for contested `blend > 0` positions (the two-sided stop rule intentionally lets genuinely contested positions run to the ~50-node budget).
**Why it happens:** `blend <= 0` (full-human, BOT-02) resolves in ~0.09-2s (single Maia inference, no search) — easy to anchor intuition on the fast case and under-build for the slow one.
**How to avoid:** D-06's pulsing "thinking" indicator and D-05's real-time-ticking bot clock are both explicitly designed for this — make sure `useBotGame`'s `isBotThinking` boolean is derived from the actual in-flight `selectBotMove` promise, not a fixed-duration animation, so a 12s think genuinely shows 12s of ticking + pulsing, not a premature "done" flicker.
**Warning signs:** A reveal-delay implementation that races search against a *fixed* short timeout and reveals whichever finishes "first" incorrectly — the reveal delay (D-03) is a *floor*, not a race; `Promise.all` (not `Promise.race`), per Pattern 3.

### Pitfall 4: iOS Safari autoplay-unlock gate on `HTMLAudioElement`
**What goes wrong:** `audio.play()` called from a non-user-gesture context (e.g. inside a `setTimeout` after the bot's async think resolves) can be silently blocked on iOS Safari / mobile Chrome until the page has received at least one user interaction.
**Why it happens:** Browser autoplay policies require a user gesture to "unlock" audio playback per page load; a bot-initiated move-sound (the bot playing a capture) is not itself a user gesture.
**How to avoid:** The very first user interaction on the page (e.g. the user's own first move, or a "Start game" tap) should call `.play()`/`.pause()` on each `Audio` instance once (silently, at ~0 volume or immediately paused) to unlock playback for the rest of the session — a well-known, standard workaround. Given FlawChess is mobile-first PWA (CLAUDE.md), this is not optional polish; verify audibility on a real iOS device during UAT, not just desktop Chrome dev tools.
**Warning signs:** Sounds work in desktop dev testing but silently don't fire on a real phone for the bot's *first* move sound specifically (later ones may work once unlocked by an intervening user click).

### Pitfall 5: Draw-throttle (D-04) and draw-accept gate (D-01) are independent state, not one flag
**What goes wrong:** Collapsing "can the user offer a draw right now" (D-04's post-decline cooldown, counted in the user's own moves) and "will the bot accept THIS offer" (D-01's eval+endgame gate) into a single boolean — they have different lifecycles (one persists across the whole game as a cooldown counter, the other is evaluated fresh at each user offer).
**Why it happens:** Both gate the same UI button, tempting a single `canOfferDraw` boolean.
**How to avoid:** Model as two separate pieces of state: (a) `movesSinceLastDecline: number` compared against a named `DRAW_OFFER_COOLDOWN_MOVES` constant (~5 per D-04) that gates whether the *button* is even clickable, and (b) a pure `wouldBotAcceptDraw(currentEval, moveNumber, materialState): boolean` function evaluated only when the user actually clicks it — this keeps D-01's threshold constants independently testable from D-04's cooldown counter.
**Warning signs:** A single `drawState` enum trying to represent both "throttled" and "would decline" — these can be simultaneously true/false in any combination and conflating them makes the throttle un-testable in isolation.

### Pitfall 6: `useFlawChessEngine.ts`'s constants must NOT be retuned in place for bot play
**What goes wrong:** `FLAWCHESS_ENGINE_MAX_NODES`/`FLAWCHESS_ENGINE_MAX_PLIES` (lines 39/45 of `useFlawChessEngine.ts`) are the **analysis board's** budget — a completely separate, already-carefully-tuned profile from `botBudget.ts`'s `FLAWCHESS_BOT_*` constants. Editing either file to "harmonize" them, or importing the wrong constant set into `useBotGame`, silently changes the analysis board's behavior (a regression outside this phase's scope) or ships a bot at the wrong strength (breaking 168.5's calibration).
**Why it happens:** Both live in adjacent files with similar names; `useFlawChessEngine.ts` even re-exports the `FLAWCHESS_BOT_*` constants (for convenience), which can make it look like the "engine hook" is the canonical import site for bot-play constants when it's just a pass-through.
**How to avoid:** `useBotGame` should import `FLAWCHESS_BOT_MAX_NODES`/`_MAX_PLIES`/`_CONCURRENCY`/`_STOP_RULE` directly from `@/lib/engine/botBudget` (the dependency-light, harness-shared module), not from `useFlawChessEngine.ts`'s re-export, per that module's own header comment ("single definition shared by the app and the calibration harness").
**Warning signs:** A diff touching `useFlawChessEngine.ts`'s `FLAWCHESS_ENGINE_MAX_NODES`/`_MAX_PLIES` constants during this phase — should not happen; this phase's only touch point in that file is reading the re-exported bot constants, or better, bypassing it entirely.

## Code Examples

### Full end-condition check (SC3)
```typescript
// Source: frontend/node_modules/chess.js/dist/types/chess.d.ts (verified method surface)
function detectEndCondition(chess: Chess): GameEndResult | null {
  if (chess.isCheckmate()) {
    // side to move is checkmated => the OTHER side won
    return { reason: 'checkmate', winner: chess.turn() === 'w' ? 'black' : 'white' };
  }
  if (chess.isStalemate()) return { reason: 'draw', drawReason: 'stalemate' };
  if (chess.isThreefoldRepetition()) return { reason: 'draw', drawReason: 'threefold' };
  if (chess.isDrawByFiftyMoves()) return { reason: 'draw', drawReason: 'fifty-move' };
  if (chess.isInsufficientMaterial()) return { reason: 'draw', drawReason: 'insufficient-material' };
  return null; // game continues (flag-on-time is checked separately, clock-driven)
}
```

### Deep-linking "Analyze this game" (D-12)
```typescript
// Source: frontend/src/lib/analysisUrl.ts:39 (verified, existing helper — reuse directly)
import { buildAnalysisLineUrl } from '@/lib/analysisUrl';
const analysisUrl = buildAnalysisLineUrl(sanMoveHistory); // navigate(analysisUrl) on "Analyze this game" click
```
Works client-side immediately for guests (no `game_id` needed) per D-12 — Phase 171 later upgrades the CTA to `buildGameAnalysisUrl(storedGameId)` once the POST succeeds.

### Mute toggle persistence (D-10) — new small hook, not `useUserFlag`
`useUserFlag` (`frontend/src/hooks/useUserFlag.ts`) is a **one-shot, per-user-email-scoped, set-only-to-true** flag (used for "has seen X" nav dots) — its semantics (no unset, no false-state persistence, email-scoped) don't fit a toggleable, guest-usable, default-true mute preference. Recommend a small dedicated hook following the same `useSyncExternalStore` shape but with real toggle semantics and a flat (non-email-scoped) key, since guests without an account still need mute to persist:
```typescript
// New pattern, modeled on useUserFlag.ts's useSyncExternalStore shape but toggleable
const MUTE_KEY = 'flawchess_bot_sound_muted';
// getSnapshot: localStorage.getItem(MUTE_KEY) === '1' (default false/unmuted per D-10)
// setMuted(muted): localStorage.setItem(MUTE_KEY, muted ? '1' : '0'); notify listeners
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| N/A — this is the first clocked-game feature in FlawChess | Wall-clock-delta dual clocks + fixed-budget bot search + synthetic clock debit | Locked 168.5 (2026-07-12) | Establishes the pacing contract this phase must implement verbatim (SC1) |

**Deprecated/outdated:** None — no prior bot-play or clock code exists to deprecate; this is greenfield within the frozen-engine constraint.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `formatClockHms` must exactly match lichess's `h:mm:ss` `[%clk]` convention (not `hh:mm:ss` or a fractional-seconds variant) for python-chess's `node.clock()` parser to accept it | Pattern 5 | If the format mismatches, `node.clock()` returns `None` for that ply, and enough missing clocks could trip STORE-02's per-color presence gate, causing the backend to reject the whole game's PGN (a Phase 171-visible failure, but rooted in this phase's PGN-writer) — verify against a captured real lichess PGN sample or a direct python-chess round-trip test during planning/execution, not left to production discovery |
| A2 | `sfx`/`piano` (the recommended AGPLv3+ substitute sets) contain sounds that are *stylistically* acceptable substitutes for "standard" (i.e., still read as normal move/capture/check sounds, not overtly retro/piano-themed in a way that feels off-brand) | Pitfall 1 | If the `piano`/`sfx`/`nes`/`futuristic` sets all sound wrong for FlawChess's tone, D-08 may need a genuinely different sourcing decision (a CC0 sound pack, or a paid license) — this needs a quick manual listen-through before locking the plan, flagged as an Open Question below |

## Open Questions

1. **Which AGPLv3+-compatible lila sound directory to vendor (`sfx` vs. `piano` vs. `futuristic` vs. `nes`)?**
   - What we know: all four are AGPLv3+ (Enigmahack), share the "standard" set's filename convention exactly.
   - What's unclear: which one *sounds* like a normal chess move/capture/check sound vs. an overtly retro/8-bit (`nes`) or synth (`futuristic`) or piano-note (`piano`) theme that might feel tonally off for FlawChess. `sfx` (generic "sound effects") is the most likely fit by name alone.
   - Recommendation: planner/discussion should have a human listen to the four candidate `Move.mp3`/`Capture.mp3` pairs (download from `github.com/lichess-org/lila/tree/master/public/sound/{sfx,piano,futuristic,nes}`) before locking which directory to vendor — a 2-minute check, not a research blocker.

2. **Exact `[%clk]` timestamp format python-chess expects on the parse side.**
   - What we know: lichess convention is `{[%clk h:mm:ss]}`; the backend's presence gate only checks `node.clock() is not None`, not the specific value.
   - What's unclear: whether python-chess's `Board`/`GameNode.clock()` parser is strict about the `h:mm:ss` format (vs. accepting `hh:mm:ss` or fractional seconds) — this determines exactly how `formatClockHms` must zero-pad/format.
   - Recommendation: a quick executor-time check (`python -c "import chess.pgn; ..."` against a hand-built `{[%clk 0:04:57]}` comment) resolves this in minutes; not worth a research-phase spike.

## Environment Availability

No external service/tool dependencies beyond what's already installed (chess.js, react-chessboard — both verified present and current). Browser APIs used (Page Visibility, `HTMLAudioElement`) are universally available in evergreen browsers with no polyfill. Skipping the full audit table — nothing to probe.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest ^4.1.7 + @testing-library/react ^16.3.2 (installed, project standard) |
| Config file | `frontend/vite.config.ts` (vitest config colocated, project convention) |
| Quick run command | `cd frontend && npx vitest run src/hooks/__tests__/useBotGame.test.ts` |
| Full suite command | `cd frontend && npm test -- --run` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PLAY-03 | Turn-gated legal moves via drag/click; illegal/off-turn moves rejected | unit | `npx vitest run src/hooks/__tests__/useBotGame.test.ts -t "turn-gate"` | ❌ Wave 0 |
| PLAY-03 | Fischer increment applied correctly after each move | unit | `npx vitest run src/lib/__tests__/chessClock.test.ts` | ❌ Wave 0 |
| PLAY-04 | Wall-clock delta model stays accurate across simulated `visibilitychange` pause during bot's turn | unit (fake timers + manual `document.visibilityState` stub) | `npx vitest run src/lib/__tests__/chessClock.test.ts -t "visibility"` | ❌ Wave 0 |
| PLAY-05 | Bot pacing: real-time tick during think; final debit = max(real, synthetic), clamped never-flag | unit (mocked `selectBotMove` resolving after a controlled fake-timer delay) | `npx vitest run src/hooks/__tests__/useBotGame.test.ts -t "pacing"` | ❌ Wave 0 |
| PLAY-06 | Every end condition detected (checkmate/stalemate/threefold/50-move/insufficient-material/flag) | unit (fixed FEN fixtures per condition, mirroring `useAnalysisBoard.test.ts`'s fixture style) | `npx vitest run src/hooks/__tests__/useBotGame.test.ts -t "end-conditions"` | ❌ Wave 0 |
| PLAY-07 | Resign confirmation gate; draw offer/accept/decline + D-04 throttle | unit | `npx vitest run src/hooks/__tests__/useBotGame.test.ts -t "resign-draw"` | ❌ Wave 0 |
| PLAY-08 | Mute toggle persists to localStorage; sounds fire on move/capture/check/game-end | unit (mock `HTMLAudioElement`/`Audio` global, assert `.play()` called with right asset) | `npx vitest run src/lib/__tests__/sounds.test.ts` | ❌ Wave 0 |
| PLAY-09 | Result screen shows correct outcome+reason; PGN carries `[%clk]` for both colors + correct `[Termination]` | unit + one integration-style test asserting the full generated PGN string against a scripted short game | `npx vitest run src/hooks/__tests__/useBotGame.test.ts -t "pgn-export"` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** targeted `npx vitest run <file>` for the file(s) touched.
- **Per wave merge:** `cd frontend && npm test -- --run` (full frontend suite).
- **Phase gate:** Full suite green (`npm run lint && npm test -- --run`, plus `npx tsc -b` per CLAUDE.md's "frontend has no separate type-check in lint/test" note) before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `src/hooks/__tests__/useBotGame.test.ts` — the new hook's own tests; no existing file to extend.
- [ ] `src/lib/__tests__/chessClock.test.ts` — pure clock-math unit tests (wall-clock delta, Fischer increment, low-time threshold, visibility pause) — extracting clock math into `lib/chessClock.ts` (rather than inlining it in the hook) makes this file test-in-isolation-able without mounting React at all.
- [ ] `src/lib/__tests__/sounds.test.ts` — sound-module tests (mute persistence, correct asset dispatched per event).
- [ ] Fake-timer convention: no existing hook test in this repo currently drives a live `setInterval`-based ticking clock under `vi.useFakeTimers()` — `useFlawChessEngine.test.ts`/`useStockfishEngine.test.ts` use fake timers only for *debounce/throttle* windows, not a continuously-ticking display. `useBotGame.test.ts` will be the first to combine `vi.useFakeTimers({ now: 0 })` with `vi.advanceTimersByTime(...)` in a loop to simulate real clock countdown — no new gap in tooling (Vitest supports this natively), just a genuinely new usage pattern worth flagging so the planner doesn't underestimate this test file's complexity.
- Framework install: none needed (Vitest already configured).

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | This phase is entirely client-side, no auth surface touched (guest and logged-in users both play identically per D-14's stub; real guest/auth wiring is Phase 171's PLAY-10) |
| V3 Session Management | no | No session state created/read by this phase |
| V4 Access Control | no | No server endpoint called |
| V5 Input Validation | yes (deferred to backend) | The PGN this phase produces is validated server-side by `normalize_flawchess_game`'s already-shipped `[%clk]`-presence gate, `Result`/`Termination` vocabulary check, and length bound (`MAX_BOT_PGN_LENGTH`) — this phase's job is to produce PGN that passes that validation, not to duplicate the validation client-side. No new server input surface is added by Phase 169 itself. |
| V6 Cryptography | no | Not applicable — no secrets, no crypto operations |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| A malicious/buggy client fabricating an implausible finished-game PGN (e.g. claiming victory after 2 moves, or a clock that never moved) | Tampering | Already mitigated server-side by Phase 167's `[%clk]` presence gate + `Result`/`Termination` vocabulary check + the `[Termination]`→board-state cross-check fallback; this phase should not attempt client-side "fairness" enforcement beyond producing an honest game — the backend is the trust boundary, and Phase 167 already treats client PGN as untrusted input (D-13: `user_id` server-derived from JWT, never client-supplied) |
| Denial-of-wallet via runaway client-side search (a user leaving many tabs open, each running an unbounded `mctsSearch`) | Denial of Service | Already bounded by `botBudget.ts`'s fixed `FLAWCHESS_BOT_MAX_NODES`/`_MAX_PLIES`/pinned concurrency (168.5) — this is entirely client-CPU-bound with no server cost, so "DoS" here only affects the user's own device, not FlawChess infrastructure; no new mitigation needed in this phase |

## Sources

### Primary (HIGH confidence)
- `frontend/node_modules/chess.js/dist/types/chess.d.ts` — full public API surface (verified: `isCheckmate`/`isStalemate`/`isThreefoldRepetition`/`isDrawByFiftyMoves`/`isInsufficientMaterial`/`isDraw`/`isGameOver`, `setComment`/`getComments`/`pgn`/`setHeader`/`removeHeader`/`getHeaders`, `move`)
- `frontend/node_modules/react-chessboard/dist/types.d.ts` — confirmed no promotion-dialog type exists
- `app/services/normalization.py` (lines 498-660) — `normalize_flawchess_game`, `_FLAWCHESS_TERMINATION_HEADER_MAP`, `_VALID_GAME_RESULTS`, `_clock_presence_by_color`, `parse_time_control`/`parse_base_and_increment` signatures and formats
- `frontend/src/lib/engine/selectBotMove.ts`, `botBudget.ts`, `types.ts` (Phase 166/168.5 frozen contracts)
- `frontend/src/hooks/useFlawChessEngine.ts` — provider-lifecycle pattern to mirror
- `frontend/src/components/board/ChessBoard.tsx` — existing board wrapper, its `onPieceDrop`/`onSquareClick` contract
- `frontend/src/lib/analysisUrl.ts` — `buildAnalysisLineUrl` (D-12's deep link)
- `frontend/src/hooks/useUserFlag.ts` — existing localStorage-boolean pattern (used as a *contrast* reference, not a direct fit)
- `.planning/phases/168.5-.../168.5-CONTEXT.md` — the locked pacing model (D-01..D-18) this phase implements
- `.planning/REQUIREMENTS.md`, `.planning/STATE.md` — requirement text, prior-phase decisions (esp. the Phase 167 tc_str/minutes-label flag)

### Secondary (MEDIUM confidence)
- `github.com/lichess-org/lila/blob/master/COPYING.md` (fetched via WebFetch, cross-checked twice) — sound-directory license table: `futuristic`/`nes`/`piano`/`sfx` = AGPLv3+ (Enigmahack); `lisp` = CC BY-NC-SA 4.0; **"the other sounds in public/sound" (including "standard") = non-free exception**
- `github.com/lichess-org/lila/tree/master/public/sound/standard` and `.../sfx` (fetched via WebFetch) — confirmed identical filename convention across both directories
- MDN Page Visibility API guide — `visibilitychange`/`document.visibilityState` pattern for pausing the clock tick (well-established web platform API, not project-specific)

### Tertiary (LOW confidence)
- None — every claim above was either verified directly against repo code/installed packages, or cross-checked against lila's own `COPYING.md` via two independent WebFetch calls.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all versions verified against installed `node_modules`.
- Architecture: HIGH for the engine/board/backend seams (all read directly from source); MEDIUM for the clock/sound module design (no in-repo precedent, but drawn from well-established, uncontroversial web-platform idioms with no viable alternative approach).
- Pitfalls: HIGH for the license correction (Pitfall 1, directly verified against lila's own license file) and the promotion-dialog gap (Pitfall 2, directly verified against the installed package's types); MEDIUM for the pacing/draw-gate pitfalls (reasoned from the locked 168.5 decisions, not yet executed).

**Research date:** 2026-07-12
**Valid until:** 30 days (stable frozen-engine dependencies; the one time-sensitive external fact — lila's sound-directory licensing — was verified directly against the current `COPYING.md`, low churn risk)
