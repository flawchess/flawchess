# Phase 170: localStorage Resume - Research

**Researched:** 2026-07-13
**Domain:** Client-side game-state persistence (localStorage), React hook resume seams, PGN/chess.js round-tripping, TanStack mutation queue draining
**Confidence:** HIGH (every claim below is either empirically verified against the real chess.js install, read directly from the shipped source, or confirmed against the actual passing test suite — no speculative library knowledge was needed for this phase)

## Summary

Phase 170 is almost entirely a *grounding* exercise, not a technology-selection one — CONTEXT.md's 14 decisions already fix the shape. This research resolves the two things the planner cannot get from CONTEXT.md alone: (1) the D-08 open question on snapshot format, settled empirically below, and (2) the exact ref/effect surface of `useBotGame.ts` that the D-10 resume seam must touch, including one structural gap CONTEXT.md's D-03 prewarm mechanism did not fully account for (the provider bring-up effect and the bot-turn-trigger effect are currently coupled to the same unconditional mount, which breaks "no clock runs while booting" for a resumed bot-turn position unless the hook gains a `live` gate).

The single most consequential finding: **CONTEXT.md's D-14 `tc_preset` trap is backwards.** The shipped Phase 167 code and its passing test suite prove `tc_preset` must be the **base-seconds** string (`"180+2"`, identical to `toBackendTcStr`'s output) — not a lichess minutes-display preset. Sending a "5+3"-style string would silently misclassify the game's TC bucket (used for rating-anchor lookup) and get rejected or misparsed by `normalize_flawchess_game`. See the dedicated section below; this must be corrected before planning, not carried forward as written in CONTEXT.md.

**Primary recommendation:** Persist `chess.pgn()` directly as the snapshot's move+clock field (verified lossless round-trip via `loadPgn()`), seed `useBotGame`'s refs from an optional `resume` argument exactly as D-10 specifies, add a `live` gate so the hook can mount early (for D-03 prewarm) without starting the bot-turn/clock effects until the user confirms, and reuse `toBackendTcStr` verbatim for `StoreBotGameRequest.tc_preset` (not a new "display preset" derivation).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Snapshot persistence (serialize/restore/version) | Browser / Client | — | Pure localStorage module, no server involvement (REQUIREMENTS Non-Goals: no server-side game sessions) |
| Resume seam into game loop | Browser / Client | — | `useBotGame` hook, in-memory only |
| Resume-gate UI | Browser / Client | — | New React component on `/bots` |
| Pending-store queue + drain | Browser / Client | API / Backend | Client owns the queue; backend is the already-shipped idempotent `POST /bots/games` sink |
| Store-once idempotency | API / Backend | Browser / Client | Server enforces via `uq_games_user_platform_game_id` (Phase 167, already shipped); client's job is only to mint a stable `gameUuid` and never lose the queue entry before a confirmed 2xx |
| TC bucket / rating derivation | API / Backend | — | `store_bot_game_service.py` — untouched by this phase, but the request's `tc_preset` field must match its expectations exactly (see the D-14 correction) |

## Standard Stack

No new dependencies. Everything needed is already in `frontend/package.json`.

### Core (already present)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| chess.js | 1.4.0 (pinned; `^1.4.0` in package.json, confirmed via `node -e "require('chess.js/package.json').version"`) | PGN parse/serialize, move replay | Already the project's only chess-rules library; verified below to round-trip `[%clk]` comments losslessly |
| @tanstack/react-query | ^5.100.14 | `useStoreBotGame` mutation + queue-drain retry policy | Already the project's only mutation layer; global Sentry capture already wired |
| @sentry/react | ^10.55.0 | Capture-once on snapshot write/parse failure, 422 drop | Already used identically elsewhere in `useBotGame.ts` (`Sentry.captureException(err, { tags: { source: 'bot-game' } })`) |

No `Package Legitimacy Audit` section is needed — this phase installs zero external packages.

## `chess.js` PGN Round-Trip — D-08 Resolved (VERIFIED empirically)

CONTEXT.md D-08 made SAN+clk-array the default and allowed `chess.pgn()`/`loadPgn()` **only if research confirms a lossless round-trip**. This was tested directly against the installed `chess.js@1.4.0` (not assumed from training data or docs).

**Method:** `annotateClock`'s exact production code (`chess.setComment('[%clk h:mm:ss]')`, copied verbatim from `frontend/src/lib/botGamePgn.ts:60-62`) was used to build games with moves by both colors, then `chess.pgn()` was compared byte-for-byte against `new Chess().loadPgn(pgn1).pgn()`. Four scenarios were run:

| Scenario | Byte-identical? | `history()` match? | Comments (`getComments()`) match? |
|---|---|---|---|
| 10-ply opening, decisive result set (`Result`/`Termination`/`TimeControl` headers) | **YES** | YES | YES (10/10) |
| 32-ply full game with draw result | **YES** | YES (no line-wrap observed even at 865 chars) | YES |
| Checkmate ending (`Qh4#`, mate symbol) | **YES** | YES | YES |
| Custom starting FEN + promotion (`a8=Q+`) | **YES** | — | YES |
| **Mid-game snapshot with NO Result set yet** (the actual every-move write shape — chess.js defaults the header to `Result "*"`) | **YES** | YES, `fen`/`turn()` both match | YES |

`[VERIFIED: local chess.js@1.4.0 install]` — **chess.js 1.4.0 round-trips `{[%clk ...]}` comments through `pgn() → loadPgn() → pgn()` losslessly, byte-identical, including headers, check/mate symbols, castling, promotion, and a mid-game (unterminated, `Result "*"`) snapshot.** Comments are internally keyed by full FEN (including move-count fields), which cannot collide within one game since the fullmove number strictly increases.

**Verdict for the planner:** the D-08 precondition is satisfied. **Use `chess.pgn()` as the snapshot's move/clock field, restore via `new Chess(); chess.loadPgn(snapshot.pgn)`.** This is simpler than SAN+clk-array (one string field, no parallel-array index-alignment bug class, `restore(...).history()` comes for free for 169.5's `resolveBookMove` requirement) and is now a *verified*, not an *assumed*, choice. Reasons to still prefer SAN+clk-array do not apply here (no length/index desync possible with a single string).

Property test for the acceptance gate (D-08's own name for it): `restore(snapshot(game)).pgn() === game.pgn()`. With the PGN-format snapshot this is almost tautological by construction (`snapshot = game.pgn()`, `restore = loadPgn(snapshot)`), which is exactly what makes it a strong revert-detector: if a future edit swaps `loadPgn` for a lossy hand-rolled replay, or drops the mid-game `Result "*"` default, this test fails immediately. Confirm this in a real vitest file (see Validation Architecture below), not just in the throwaway script used for this research.

**Payload size** (D-06's "a few KB" claim, confirmed): a 60-ply game snapshot (full `BotGameSettings`, 60 SAN moves + clocks, all D-09 fields) serializes to **~1.1 KB** as SAN+clk-array or **~1.7 KB** as a PGN string (JSON-measured, `JSON.stringify(...).length`). Either format is comfortably inside typical `localStorage` per-key/per-origin limits (5-10 MB depending on browser) — no chunking or compression needed.

## Standard Stack — Snapshot Payload (D-09, PGN variant)

```typescript
interface BotGameSnapshot {
  version: 1;
  gameUuid: string;             // crypto.randomUUID(), minted at game start (D-11)
  settings: BotGameSettings;    // botElo, blend, baseSeconds, incrementSeconds, userColor
  pgn: string;                  // chess.pgn() at snapshot time — VERIFIED lossless (see above)
  whiteClockMs: number;         // BASE value, D-01/D-02 fold already applied at write time
  blackClockMs: number;
  movesSinceLastDecline: number;
  hasLeftBook: boolean;         // 169.5 D-03 one-way latch — MUST persist, cannot be re-derived
  hasFiredLowTime: boolean;
  savedAt: number;              // Date.now() at write, for D-06's "2 days ago" age display
}
```

`activeColor` is deliberately omitted (derive from `new Chess().loadPgn(pgn).turn()`, or equivalently `moveHistory.length` parity after restore) — do not store a second copy of a derivable fact, per D-09. `lastRootPracticalScore` is deliberately omitted per D-09's fail-closed sentinel argument (a fresh `null` on resume is correct, not a gap).

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────┐   mount    ┌──────────────────────┐
│  Bots.tsx   │───────────>│ readSnapshot()         │  lib/botGameSnapshot.ts
│  route load │            │ (localStorage.getItem, │  pure, try/catch, version-gated
└─────────────┘            │  JSON.parse, validate)  │
       │                   └──────────┬─────────────┘
       │                              │
       │                    snapshot found?
       │                    ┌─────────┴─────────┐
       │                   YES                  NO
       │                    │                    │
       │        ┌───────────▼───────────┐        │
       │        │ mount useBotGame(      │        │ mount useBotGame(settings)
       │        │   settings, resume,    │        │ (today's D-14 stub — live=true,
       │        │   live=false)           │        │  auto-starts immediately)
       │        │ — bring-up effect fires │        └───────────┬────────────┘
       │        │   NOW: pool.warm(),     │                    │
       │        │   queue.warm(), ECO     │                    │
       │        │   prefix fetch          │                    │
       │        │ — clock-tick/bot-turn   │                    │
       │        │   effects SKIPPED       │                    │
       │        │   (live===false)        │                    │
       │        └───────────┬────────────┘                    │
       │                    │                                  │
       │        render "Resume game?" gate                     │
       │        (age, TC, bot ELO, move count)                 │
       │                    │                                  │
       │         ┌──────────┴──────────┐                       │
       │        Resume               Discard (confirm first)   │
       │         │                     │                        │
       │  confirmLive() ─┐    clearSnapshot() + newGame()       │
       │  turnStartedAtRef│    (falls through to D-14 stub)     │
       │  set NOW, tick/  │                                     │
       │  bot-turn effects│                                     │
       │  start           │                                     │
       └──────────────────┴──────────────────┬──────────────────┘
                                              │
                                   live game loop (useBotGame,
                                   unchanged from Phase 169)
                                              │
                            every commitMove() ──> writeSnapshot()
                            visibilitychange/pagehide (hidden) ──>
                              writeSnapshot() with D-01/D-02 fold
                                              │
                                        finalizeGame()
                                              │
                              enqueue to flawchess_bot_pending_store
                              (separate key, D-12) + clearSnapshot()
                                              │
                              Bots.tsx mount (NEXT visit) ──> drainQueue()
                              ──> POST /bots/games ──> remove entry on
                                  confirmed 2xx (created:true or false)
```

### Recommended Project Structure
```
frontend/src/
├── lib/
│   ├── botGameSnapshot.ts       # NEW: serialize/parse/validate/version/fold (D-09)
│   ├── botPendingStore.ts       # NEW: queue enqueue/dequeue/list (D-12), separate key
│   └── chessClock.ts            # ADD: a small pure fold helper (see Clock Fold below)
├── hooks/
│   └── useBotGame.ts            # MODIFY: add `resume?`, `live` gate (D-10)
├── api/
│   └── client.ts                # ADD: botsApi.storeGame
├── hooks/
│   └── useStoreBotGame.ts       # NEW: TanStack mutation wrapping botsApi.storeGame
└── components/bots/
    └── ResumeGate.tsx           # NEW: D-04 gate component
```

### Pattern 1: Resume seam via optional lazy-init argument (D-10)
**What:** `useBotGame(settings: BotGameSettings, resume?: BotGameSnapshot): UseBotGameState`
**When to use:** Always — this IS the seam; Phase 171 will call it identically with no `resume`.
**Example:**
```typescript
// frontend/src/hooks/useBotGame.ts — illustrative, not literal diff
export function useBotGame(
  settings: BotGameSettings,
  resume?: BotGameSnapshot,
): UseBotGameState {
  const chessRef = useRef<Chess>(initChess(settings, resume)); // loadPgn(resume.pgn) or new Chess()
  const clockBaseRef = useRef(resume
    ? { white: resume.whiteClockMs, black: resume.blackClockMs }
    : freshClockBase(settings.baseSeconds));
  const hasLeftBookRef = useRef(resume?.hasLeftBook ?? false);       // MUST seed — see gap below
  const hasFiredLowTimeRef = useRef(resume?.hasFiredLowTime ?? false); // MUST seed — see gap below
  const [moveHistory, setMoveHistory] = useState<string[]>(() =>
    resume ? new Chess().loadPgn(resume.pgn).history() : []);
  const [viewedPly, setViewedPly] = useState(() => moveHistory.length); // live on resume, not 0
  const [activeColor, setActiveColor] = useState<MoverColor>(() =>
    resume ? (moveHistory.length % 2 === 0 ? 'white' : 'black') : 'white');
  const [whiteClockMs, setWhiteClockMs] = useState(resume?.whiteClockMs ?? settings.baseSeconds * 1000);
  const [blackClockMs, setBlackClockMs] = useState(resume?.blackClockMs ?? settings.baseSeconds * 1000);
  const [movesSinceLastDecline, setMovesSinceLastDecline] = useState(
    resume?.movesSinceLastDecline ?? DRAW_OFFER_COOLDOWN_MOVES);
  // ... viewedPlyRef/liveGamePlyRef must ALSO be seeded to match (they're refs, not just state)
}
```
**Source:** verified against `frontend/src/hooks/useBotGame.ts:267-361` (the exact refs/state block).

### Pattern 2: `live` gate for D-03's "anchor after live" (NEW — not in CONTEXT.md, discovered here)
**What:** A boolean that starts `true` for a fresh game (`!resume`) and `false` for a resumed game until the caller confirms.
**When to use:** Gates exactly three things in `useBotGame.ts`: the turn-anchor mount effect (674-686), the clock-tick effect (694-737), and the bot-turn-trigger effect (977-981). The provider bring-up effect (761-786, `pool.warm()`/`queue.warm()`/ECO fetch) must stay **unconditional** — that is what satisfies D-03 mechanism 1.
**Why this is required, not optional:** see "The D-03 Prewarm Gap" below — without it, a resumed snapshot where it is the bot's turn starts a real `selectBotMove` search (and clock anchor) the instant `useBotGame` mounts, i.e. while the "Resume game?" gate is still on screen and before the user has agreed to anything.

### Anti-Patterns to Avoid
- **Reusing the `visibilitychange` effect's empty `[]` dependency array for the new hide-time snapshot write.** The existing effect (`useBotGame.ts:741-757`) intentionally has `[]` deps because it only touches refs (`pausedAtRef`, `turnStartedAtRef`). The moment the hide handler also needs to *read* `activeColor`, `moveHistory`, `clockBaseRef`, `hasLeftBookRef`, etc. to build a snapshot, a `[]`-deps closure will silently read **stale values frozen at first mount** — this is exactly the "half-invariant" bug shape from Phase 169's gap closures (a rule enforced in one place, bypassed via a stale closure in another, invisible to tsc/eslint/knip). Either (a) give the hide-time write its own effect with a correct dependency array (mirroring the clock-tick effect's `[activeColor, outcome, ...]` shape), or (b) read through refs that are kept fresh via a sync effect (the way `liveGamePlyRef`/`viewedPlyRef` are already mirrored at `useBotGame.ts:285-290, 376-378`). Do not bolt new stateful reads onto the existing `[]`-deps handler.
- **Mutating `clockBaseRef.current` directly during the D-01 fold.** The fold must produce a value written into the *snapshot payload* only. If it mutates the live ref, the next real `commitMove()` will double-subtract the same elapsed time (once via the fold, once via its own `chargeableElapsedMs()` read). Compute a folded *copy* for serialization; leave `clockBaseRef.current` untouched.
- **Building a second SAN→UCI or SAN→FEN replay path for the snapshot restore.** `resolveBookMove` (`useBotGame.ts:233-263`) already requires `chess.history()` to be non-empty and derived from real pushed moves, not a `new Chess(fen)` board. `loadPgn()` satisfies this for free; do not add a parallel "replay SAN list" helper that produces a *different* Chess instance shape than the one 169.5 depends on.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PGN move+clock serialization | A custom SAN+clk-array replay/annotate loop | `chess.pgn()` / `loadPgn()` | Verified lossless above; chess.js already owns this format, and `annotateClock`/`finalizeBotPgn` already depend on chess.js's own comment store — a second serialization format for the same data is a second bug surface |
| "Is a snapshot stale/expired" | A TTL constant + auto-drop | D-06's explicit no-TTL, age-display-only design | Locked decision; do not add expiry logic the planner wasn't asked for |
| Draw-cooldown / clock-fold math | New elapsed-time helpers | `chargeableElapsedMs()` (`useBotGame.ts:414-416`) / `computeChargeableElapsedMs` (`chessClock.ts:172-177`) | Phase 169 CR-01 made "one pause-aware elapsed source" a structural invariant; a second reader reintroduces exactly the bug class Plan 10 closed |
| Retry/backoff for the pending-store drain | Hand-rolled retry loop | TanStack Query's mutation `retry`/`retryDelay` options | The project has zero hand-rolled HTTP retry code anywhere; `queryClient.ts`'s `defaultOptions.queries.retry: 1` is the existing precedent for retry-via-config, not retry-via-loop |

**Key insight:** almost everything this phase needs already exists in the codebase in a form built for exactly this reuse (`useBotGame`'s own header comment names Phase 170 as "the snapshot consumer" — this was designed for). The risk is not missing library knowledge, it is silently duplicating an invariant that already lives in one place.

## The D-03 Prewarm Gap (structural finding — read before planning the resume-gate mount timing)

D-03 mechanism 1 requires `pool.warm()`/`queue.warm()`/ECO-fetch to start "the moment a resumable snapshot is found... while the gate is on screen." But `WorkerPool`/`MaiaQueue` are constructed **entirely inside `useBotGame`'s own mount effect** (`useBotGame.ts:761-786`) and torn down on unmount (`780-785`) — there is no external handle to them. This means:

- If `Bots.tsx` defers calling `useBotGame(settings, resume)` until AFTER the user clicks "Resume" (the naive reading of D-04's "do not auto-start any game until the user chooses"), the provider bring-up effect cannot fire until then either — defeating D-03 mechanism 1 entirely. Prewarming a *separate, throwaway* `WorkerPool`/`MaiaQueue` instance from `Bots.tsx` during the gate does **not** help: a brand-new `Worker()`/ONNX session spawned later by `useBotGame`'s own effect pays the full spawn/compile cost again regardless of what a different, discarded instance did earlier.
- The correct reading (consistent with D-03's own "same trick as 169.5's warm-during-the-book-window" comparison — 169.5 warmed an *already-mounted* game's engines during its book window, it did not warm before mount) is: **mount `useBotGame(settings, resume)` immediately once a snapshot is detected**, rendering the gate as an overlay/replacement UI on top of (or instead of) the board, so the hook's own real bring-up effect starts warming immediately. What must NOT start immediately is the clock and the bot's move search — hence Pattern 2's `live` gate.
- Without the `live` gate specifically, there is a second, sharper bug: the bot-turn-trigger effect (`useBotGame.ts:977-981`) is unconditional on mount — `if (activeColor === settings.userColor) return; runBotTurnRef.current?.(BOT_SEARCH_BUDGET);`. For a resumed snapshot where it is the bot's turn, this fires the instant the hook mounts (i.e., the instant the gate renders), starting a real search and committing the bot's think-deadline anchor before the user has agreed to resume at all. This directly violates D-03 mechanism 2 ("No clock runs while the page is booting") and RESUME-01's "no away-time billed" framing, and it also means a user who clicks "Discard" on the gate could return to find the bot has already searched and potentially even applied a move+clock-debit inside a game that is about to be thrown away (harmless since the whole snapshot is discarded, but the search itself was wasted work and, if the bot's clock happened to be low, could flag it mid-boot for no reason).

**Plan implication:** `useBotGame` needs a third seam beyond `resume?`: a way to say "mounted, providers warming, but not live yet." The simplest shape consistent with D-10's "ONE hook, ONE game loop": an optional third param or a returned `confirmLive()` callback that flips an internal `live` ref/state from `false` (only when `resume` is present and not yet confirmed) to `true`, gating the three effects named in Pattern 2. A fresh game (no `resume`) keeps `live` implicitly `true` from mount, matching today's unconditional behavior exactly — zero behavior change on the non-resume path.

## The D-14 `tc_preset` Correction (contradicts CONTEXT.md — verified against shipped tests)

CONTEXT.md's D-14 states: *"the PGN's `[TimeControl]` header uses `toBackendTcStr` = base-seconds (`"300+3"`), while Phase 167 D-16 stores `tc_preset` as the lichess display preset (`"5+3"`)... derive the preset separately."*

This is **not what the shipped, currently-passing code does.** Evidence, read directly from source:

1. `app/services/store_bot_game_service.py:76`: `tc_bucket, _ = parse_time_control(request.tc_preset)`. `parse_time_control`'s own docstring (`app/services/normalization.py:58-75`) requires a base-**seconds** string (`'180+2' -> ('blitz', 260)`) — feeding it a minutes-display string like `"3+2"` would compute `estimated = 3 + 2*40 = 83` and misclassify a 3-minute blitz game as **bullet**.
2. `app/services/store_bot_game_service.py:91-99` passes the *same* `request.tc_preset` value as the `tc_str` positional argument to `normalize_flawchess_game`, whose docstring (`app/services/normalization.py:572-575`) is explicit: *"same base_seconds+increment_seconds format... e.g. '180+2' — NOT a minutes-based display label."*
3. The shipped, currently-passing test suite proves this empirically:
   - `tests/services/test_store_bot_game_service.py:32`: `_TC_STR = "180+2"  # parse_time_control("180+2") -> ("blitz", 260)`
   - `tests/routers/test_bots.py:77`: `_TEST_TC_PRESET = "180+2"`
   - `tests/repositories/test_bot_game_settings_repository.py:51,73,96,111`: literal `tc_preset="3+2"` / `"5+0"` values stored and read back verbatim — these happen to *also* look like display strings, but `"5+0"`/`"3+2"` interpreted as base-seconds are nonsensically short games (5s, 3s base), so these particular repository-level tests do not by themselves prove the format; the **service-level and router-level tests are the ones that exercise `parse_time_control` and settle the question**, and they use `"180+2"`.

The `BotGameSettings` model's inline comment (`app/models/bot_game_settings.py:34`, *"lichess TC preset string, e.g. '3+2'"*) is the likely source of CONTEXT.md's D-14 framing, but it is misleading/stale relative to the tested behavior — a documentation artifact, not the executable contract.

**Correction for the planner:** `StoreBotGameRequest.tc_preset` must be populated with **`toBackendTcStr(settings.baseSeconds, settings.incrementSeconds)`** — the exact same string already used for the PGN's `[TimeControl]` header (`botGamePgn.ts:112-114`). Do **not** build a separate "lichess display preset" derivation function for this field. This also means Phase 171's setup-screen TC *labels* ("5+3" shown to the user) are a pure UI-layer concern — internally they still resolve to `baseSeconds`/`incrementSeconds`, and the wire value sent to the backend is always the seconds format. Flag this correction explicitly when presenting the plan (it reverses a locked CONTEXT.md decision on the basis of source ground-truth, which the discuss-phase user should be made aware of even though it does not require re-opening discussion — it is a factual correction, not a design choice).

## Clock Fold (D-01/D-02) — exact call sites

The fold must reuse `chargeableElapsedMs()` (`useBotGame.ts:414-416`, wrapping `computeChargeableElapsedMs` in `chessClock.ts:172-177`) — this is the ONE pause-aware elapsed-time source Phase 169 CR-01 made structural. Do not add a second reader.

**Where the fold happens (proposed, matching D-01/D-02 exactly):**
```typescript
// New pure helper, chessClock.ts (co-located with hasFlaggedOnDebit — same
// "commit-time math" family, same file per the module's own stated purpose)
export function foldElapsedIntoClockBase(remainingMs: number, elapsedMs: number): number {
  return Math.max(0, remainingMs - elapsedMs);
}
```
```typescript
// useBotGame.ts — inside the write-on-hide handler (a NEW effect, per the
// Anti-Patterns note above — NOT bolted onto the existing []-deps visibilitychange effect)
function buildHideTimeSnapshot(): BotGameSnapshot {
  const userIsActive = activeColor === settings.userColor; // D-02: fold ONLY on the user's turn
  const elapsed = userIsActive ? chargeableElapsedMs() : 0;
  const foldedWhite = activeColor === 'white' && userIsActive
    ? foldElapsedIntoClockBase(clockBaseRef.current.white, elapsed)
    : clockBaseRef.current.white;
  const foldedBlack = activeColor === 'black' && userIsActive
    ? foldElapsedIntoClockBase(clockBaseRef.current.black, elapsed)
    : clockBaseRef.current.black;
  return buildSnapshot({ ...otherFields, whiteClockMs: foldedWhite, blackClockMs: foldedBlack });
}
```
D-02's "bot's clock is snapshotted as of its last commit" falls out naturally: when `!userIsActive` (bot's turn), `elapsed` is forced to `0`, so the fold is a no-op and the bot's clock base is written as-is — no separate branch needed beyond the `userIsActive` guard.

**Every-move write** (the D-01 primary write path) is simpler: it happens *inside* `commitMove()` right after the clock bases are updated (`useBotGame.ts:484-488`), where `clockBaseRef.current[mover]` already reflects the post-move, post-increment value for the mover — no fold needed there at all, since the value being written IS already the settled base. Only the *hide-time* write (mid-turn, before a move commits) needs the fold, because it captures a clock that is still ticking.

## Reliable Leave Detection — `pagehide` + `visibilitychange` (2026 guidance, confirmed)

`[CITED: developer.chrome.com/docs/web-platform/page-lifecycle-api, developer.mozilla.org/en-US/docs/Web/API/Window/pagehide_event]` — current (2026) guidance, cross-checked across MDN, Chrome DevRel, and independent engineering blogs:

- **`document.visibilitychange` (state `'hidden'`) is the primary, most-reliable signal** across desktop and mobile — "the only event your application can count on" for session-save logic. `useBotGame` already listens to this (`useBotGame.ts:741-757`) for pause bookkeeping; the snapshot write should hang off the **same event type**, in a **separate, correctly-scoped effect** (see Anti-Patterns above).
- **`pagehide` should be registered as an additional fallback**, specifically for hard-navigation/back-forward-cache scenarios that don't always fire `visibilitychange` first on some browsers. Register it alongside, not instead of, `visibilitychange`.
- **Do NOT use `beforeunload`/`unload`.** Both are unreliable on mobile Safari (iOS explicitly does not guarantee synchronous handler execution before teardown) and the mere presence of an `unload`/`beforeunload` listener **disables the back/forward cache (bfcache)** for the page in Chromium and Firefox — a real performance regression for a PWA, not just a theoretical concern.
- This directly confirms CONTEXT.md D-01's "accepted gap" framing is correct as written: neither `visibilitychange` nor `pagehide` is a 100%-guaranteed hook (browser kill, iOS tab purge under memory pressure, crash), and no combination of DOM events closes that gap — a heartbeat/polling write is the only way to fully close it, and D-01 already explicitly rejects that tradeoff. No changes to that decision are warranted by this research; it is confirmed, not merely assumed.
- **Do not double-register.** `useBotGame.ts:741-757`'s existing `visibilitychange` listener already exists for pause bookkeeping. Adding the snapshot write should either extend that SAME listener body (if a correctly-scoped ref-mirror is used to keep it fresh) or add a second listener in a separate, properly-dependent effect — but must not silently duplicate `document.addEventListener('visibilitychange', ...)` registration in a way that makes the pause-bookkeeping and snapshot-write ordering non-deterministic relative to each other. Snapshot-write should read `pausedAtRef`/`turnStartedAtRef` AFTER the pause-bookkeeping handler has run for the same event (i.e., call `chargeableElapsedMs()` from inside/after the existing handler, not from a second listener that might run before or after it depending on registration order — DOM listener execution order for the same event type IS registration order, so this is controllable but must be deliberate).

## localStorage Failure Modes (D-09's guard requirement)

Two existing patterns to follow, both read directly from source:

- **`frontend/src/lib/welcomeDismissal.ts:8`**: `if (typeof localStorage === 'undefined') return false;` — the SSR/prerender guard (the project's vite-prerender-plugin renders some pages at build time with no `localStorage`).
- **`frontend/src/hooks/useUserFlag.ts:24-30, 43-55`**: wraps every `localStorage.getItem`/`setItem` call in `try { ... } catch { return <safe default>; }` — this is the pattern for `QuotaExceededError` / Safari private-mode `setItem` throws (private-mode Safari historically throws on `setItem` even though `localStorage` itself is `typeof` defined).

**What D-09 requires on top of these two established patterns:**
1. The `typeof localStorage === 'undefined'` guard (welcomeDismissal.ts pattern) — same as always.
2. A try/catch around every write AND every read/parse (useUserFlag.ts pattern) — but unlike `useUserFlag`'s boolean flag, this module also needs to catch `JSON.parse` failures (a corrupted/truncated value) and schema-validation failures (a `version` mismatch, or a value written by a future/older schema), not just the storage-API throw itself. Both should degrade to "no resumable snapshot" (the D-04 gate silently shows nothing) rather than propagating.
3. **Capture once, not on every access.** Since `readSnapshot()` runs on every `/bots` mount, a persistently-corrupted value would otherwise spam Sentry on every visit. Recommend clearing the bad key immediately on first detected corruption (so subsequent reads see "no snapshot" cleanly) and capturing exactly once at that clear point — mirrors the general Sentry rule ("skip trivial/expected exceptions... capture on last attempt only" pattern from CLAUDE.md, adapted here to "capture on first detection, then the corruption is gone").
4. **Version gate is a hard drop, not a migration.** D-06 explicitly says "a schema-version bump invalidates it" (silent drop) — no migration function needed for v1; this simplifies the guard to `if (parsed.version !== CURRENT_SNAPSHOT_VERSION) return null`.

## Frontend Store Client + Drain (D-13/D-14)

**`botsApi.storeGame`** — follows `frontend/src/api/client.ts`'s exact existing shape (grouped object export per resource, `apiClient.post<Response>(url, body).then(r => r.data)`):
```typescript
// frontend/src/api/client.ts — new section, same file (no new api module file —
// every other resource lives inline in this one file, e.g. feedbackApi at line 223)
export const botsApi = {
  storeGame: (data: StoreBotGameRequest) =>
    apiClient.post<StoreBotGameResponse>('/bots/games', data).then(r => r.data),
};
```
`StoreBotGameRequest`/`StoreBotGameResponse` TS types must mirror `app/schemas/bots.py` exactly: `{ game_uuid: string; pgn: string; user_color: 'white' | 'black'; bot_elo: number; play_style_blend: number; tc_preset: string }` → `{ game_id: number; created: boolean }`.

**`useStoreBotGame`** — a plain TanStack `useMutation` wrapping `botsApi.storeGame`. Per CLAUDE.md and `queryClient.ts:13-19`'s global `MutationCache.onError`, **do not** add a component-level `Sentry.captureException` around this mutation's error path — the global handler already tags `source: 'tanstack-mutation'` and captures every mutation failure automatically.

**D-13 retry policy — per-status differentiation.** TanStack's built-in `retry` option only sees the error, not semantic distinctions like "422 vs 5xx vs 401" out of the box unless you supply a function. Recommended shape (a `retry` predicate, standard TanStack pattern, not a new invention):
```typescript
useMutation({
  mutationFn: botsApi.storeGame,
  retry: (failureCount, error) => {
    if (!axios.isAxiosError(error)) return failureCount < MAX_STORE_RETRIES;
    const status = error.response?.status;
    if (status === 422) return false;      // client bug — never retry, drop the entry (D-13)
    if (status === 401) return true;       // keep trying — retry once authenticated
    return failureCount < MAX_STORE_RETRIES; // network/5xx — bounded retry
  },
});
```
The 422-drop and 401-keep semantics from D-13 must ultimately be enforced by the **queue drain logic** (whether to remove the entry from `flawchess_bot_pending_store` after the mutation settles), not solely by the mutation's internal retry — `retry` only governs in-flight retries of a single `mutate()` call, not "should this queue entry survive to the next page visit." The drain loop's own `onError`/`onSuccess` handling must inspect the resolved/rejected outcome and decide entry removal independently: 2xx (both `created: true/false`) → remove; 422 → capture + remove; 401 or network/5xx → keep for next visit.

## Common Pitfalls

### Pitfall 1: Seeding `useState`/`useRef` from `resume` only partially
**What goes wrong:** D-10 says "lazily initialize the existing refs/state from it," but `useBotGame` has **11 distinct state/ref values that all default from either `settings` or a hardcoded fresh-game constant** (enumerated in Pattern 1's example and the list below). Missing even one silently resets that piece of game state on every resume — exactly Phase 169's "half-invariant" failure shape (invisible to tsc/eslint/knip/tests unless a test specifically asserts the value survives a resume).
**The full list, verified line-by-line against `useBotGame.ts`:**
| Ref/state | Line | Today's default | Resume seed needed |
|---|---|---|---|
| `chessRef` | 270 | `new Chess()` | `loadPgn(resume.pgn)` |
| `clockBaseRef` | 271-273 | `freshClockBase(settings.baseSeconds)` | `{ white: resume.whiteClockMs, black: resume.blackClockMs }` |
| `viewedPlyRef` | 285 | `0` | live ply (`moveHistory.length` post-restore) |
| `liveGamePlyRef` | 290 | `0` | self-corrects via existing sync effect (376-378) once `moveHistory` state is seeded — no direct seed needed, but verify the effect runs before first use |
| `hasLeftBookRef` | 341 | `false` | **`resume.hasLeftBook`** — D-09 explicitly requires this; missing it silently re-enters the book mid-game |
| `hasFiredLowTimeRef` | 343 | `false` | **`resume.hasFiredLowTime`** — D-09 explicitly requires this |
| `lastRootPracticalScoreRef` | 332 | `null` | **intentionally NOT seeded** (D-09) — leave `null` |
| `moveHistory` state | 349 | `[]` | `loadPgn(resume.pgn).history()` |
| `viewedPly` state | 350 | `0` | live ply, matching `viewedPlyRef` |
| `activeColor` state | 351 | `'white'` | derived from `moveHistory.length` parity (D-09: do not store this separately) |
| `whiteClockMs`/`blackClockMs` state | 352-353 | `settings.baseSeconds * 1000` | `resume.whiteClockMs`/`resume.blackClockMs` |
| `movesSinceLastDecline` state | 360 | `DRAW_OFFER_COOLDOWN_MOVES` | **`resume.movesSinceLastDecline`** — D-09 explicitly requires this |
| `outcomeRef`/`outcome` state | 297, 354 | `null` | correctly stays `null` — a resumed snapshot is by construction never a finished game (finished games go to the pending-store queue, not this snapshot) |
| `turnStartedAtRef`/`pausedAtRef` | 279-280 | set to `Date.now()` on mount (674-686) | **NOT seeded from resume** — always "now," gated instead by the `live` flag (Pattern 2) so the anchor is only meaningful once the user has confirmed |
**How to avoid:** write the round-trip/resume test enumerated in Validation Architecture below BEFORE wiring the seam, and assert on every one of the 8 bolded/flagged fields individually, not just "the position looks right."
**Warning signs:** a resumed game where the draw-offer button is immediately clickable (missing `movesSinceLastDecline` seed), or the bot re-enters book after leaving it pre-resume (missing `hasLeftBookRef` seed) — both are silent, only visible via manual play-through, not via any type error.

### Pitfall 2: The D-03 prewarm gap (see dedicated section above)
Already covered in full above — repeated here as a pitfall entry because it is easy to miss during planning if the planner reads D-03 literally as "call warm() from the gate component" without noticing `WorkerPool`/`MaiaQueue` have no life outside `useBotGame`'s own effect.

### Pitfall 3: Stale closures in the hide-time snapshot write
Already covered in Anti-Patterns above. Repeated here because it is the single most likely source of a passing-tsc, passing-lint, silently-wrong resume (the exact shape CLAUDE.md's `feedback_mutation_test_gap_closures` memory warns about — a duplicated/bypassed invariant invisible to static tooling).

### Pitfall 4: Treating `tc_preset` as needing a new derivation function
Already covered in the dedicated D-14 Correction section above. Repeated here because CONTEXT.md explicitly locked the opposite (wrong) framing, so a planner working from CONTEXT.md alone without this research would build unnecessary code and likely introduce a genuine TC-bucket misclassification bug.

### Pitfall 5: Writing the snapshot from inside `commitMove` unconditionally, including for the FIRST move of a brand-new (non-resumed) game
**What goes wrong:** D-01 says "written on every move" — but a fresh game with no `resume` prop has no reason to ever write a snapshot until the user actually plays. This is a non-issue for correctness (writing a "resumable" 1-move snapshot for a brand-new game the user is still actively playing is fine and IS the desired behavior — RESUME-01 wants exactly this), but the planner should confirm `writeSnapshot()` inside `commitMove` fires regardless of whether the CURRENT hook instance itself was resumed or fresh — it must not be conditioned on `resume !== undefined`. The gate is not "was this game resumed" but "is there an in-progress game right now."

## Code Examples

### Verified round-trip test (chess.js 1.4.0, from this research's throwaway script)
```typescript
// Source: empirically verified in this research session against the real
// installed chess.js@1.4.0 — see the chess.js Round-Trip section above for
// the full scenario matrix (10-ply, 32-ply, checkmate, promotion, mid-game).
import { Chess } from 'chess.js';

const chess = new Chess();
chess.move('e4');
chess.setComment('[%clk 0:04:57]'); // annotateClock's exact production call shape
const pgn1 = chess.pgn();

const restored = new Chess();
restored.loadPgn(pgn1);
const pgn2 = restored.pgn();

pgn1 === pgn2;                                    // true — byte-identical
restored.history().length === chess.history().length; // true
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `beforeunload`/`unload` for save-on-close | `visibilitychange` (+ `pagehide` fallback) | Long-standing (pre-2020) mobile-Safari guidance, still current in 2026 sources | Confirms D-01's design; no action needed beyond registering both events correctly |

No other "old vs new" shifts apply — this phase's entire technology surface (chess.js, TanStack Query, localStorage) is already the project's existing, current stack.

**Deprecated/outdated:** none relevant to this phase.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `MAX_STORE_RETRIES` / bounded-retry count for the D-13 drain is left as a Claude's-discretion tuning constant (CONTEXT.md explicitly reserves "the queue cap" and similar as discretion) | Frontend Store Client + Drain | Low — a wrong constant just changes how many app-visits a transient outage survives before the queue entry is dropped-on-422-only-anyway; no correctness risk since 422 is the only unconditional drop |
| A2 | The `live` gate (Pattern 2) is proposed here as the mechanism to satisfy D-03 without contradicting D-04, but CONTEXT.md does not name this mechanism explicitly — it is this research's synthesis of D-03 + D-04 + the actual `useBotGame.ts` effect structure, not a verbatim quote from any locked decision | The D-03 Prewarm Gap | Medium — if the planner instead chooses to lift `WorkerPool`/`MaiaQueue` construction out of the hook entirely (the alternative option named in that section), the resulting task breakdown would differ meaningfully in shape (bigger refactor, touches the hook's public surface) while still satisfying the same locked decisions. Worth a one-line confirmation with the user or an explicit planner note, not a full re-discuss. |

## Open Questions

1. **Exact `live`-gate API shape (prop vs returned callback vs internal auto-detection).**
   - What we know: the hook needs SOME way to defer the turn-anchor/clock-tick/bot-turn effects until after gate confirmation, while keeping the provider bring-up effect unconditional.
   - What's unclear: whether this should be a third `useBotGame` parameter, a returned `confirmLive()` function in `UseBotGameState`, or an internal state machine keyed off a `resume.confirmed` flag mutated by the caller. CONTEXT.md's "Claude's Discretion (remaining)" section covers "the gate component's file placement and visual composition" but not this specific hook-API question.
   - Recommendation: a returned `confirmLive(): void` callback in `UseBotGameState`, defaulting `live` internal state to `resume === undefined` at mount — keeps the hook's constructor signature unchanged (`(settings, resume?)`, matching D-10 literally) and gives `Bots.tsx` an explicit, discoverable action to call on the gate's "Resume" button handler.

2. **Whether the resume-gate's "Discard" flow needs to also drain/inspect the pending-store queue before falling through to a fresh game.**
   - What we know: D-07 says discard clears the in-progress snapshot only; D-12 says the pending-store queue is a wholly separate key that only `finalizeGame` writes to.
   - What's unclear: nothing structurally — the two are independent by design — but the planner should confirm the discard path does not accidentally touch `flawchess_bot_pending_store`.
   - Recommendation: no code changes needed; call this out as a one-line negative-space verification item in the plan's checkpoint list ("Discard does not touch the pending-store queue").

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest ^4.1.7 (`frontend/vitest` via `npm test` / `npm run test:watch`) |
| Config file | `frontend/vite.config.ts` (Vitest config is typically colocated with Vite config in this project's setup — confirm exact location at plan time; not read in this research pass) |
| Quick run command | `npm test -- src/lib/__tests__/botGameSnapshot.test.ts` (new file) or `-t "<token>"` filter, matching `useBotGame.test.ts`'s own documented `-t` filter-token convention |
| Full suite command | `npm test -- --run` |

Existing sibling test files to mirror directly: `frontend/src/lib/__tests__/chessClock.test.ts`, `frontend/src/lib/__tests__/botGamePgn.test.ts`, `frontend/src/hooks/__tests__/useBotGame.test.ts` (mocks `selectBotMove`/`createDeadlineSearch`/provider factories via `vi.mock`, drives time with `vi.useFakeTimers({ now: 0 })`, uses `renderHook`/`act` from `@testing-library/react`, `@vitest-environment jsdom` pragma at file top).

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RESUME-01 | Round-trip: `restore(snapshot(game)).pgn() === game.pgn()` for a game with moves by both colors | unit | `npm test -- src/lib/__tests__/botGameSnapshot.test.ts -t "round-trip"` | ❌ Wave 0 |
| RESUME-01 | `hasLeftBook`/`hasFiredLowTime`/`movesSinceLastDecline` all survive a resume — REVERT each seed individually and confirm the specific test fails (mutation-test gap-closure discipline per project memory, not a grep) | unit | `npm test -- src/hooks/__tests__/useBotGame.test.ts -t "resume-seed"` | ❌ Wave 0 (extends existing file) |
| RESUME-01 | D-01/D-02 clock fold: hide during user's turn folds elapsed think time into the snapshot base; hide during bot's turn does NOT (snapshot base == last-commit value, unfolded) | unit | `npm test -- src/lib/__tests__/chessClock.test.ts -t "fold"` | ❌ Wave 0 (extends existing file) |
| RESUME-01 | `live` gate: a resumed snapshot where it is the bot's turn does NOT trigger `runBotTurnRef` until `confirmLive()` is called (mock `selectBotMove`, assert zero calls pre-confirm, one call post-confirm) | unit | `npm test -- src/hooks/__tests__/useBotGame.test.ts -t "prewarm-gate"` | ❌ Wave 0 (extends existing file) |
| RESUME-02 | An unfinished game's snapshot never appears in `flawchess_bot_pending_store` — only `finalizeGame` ever enqueues | unit | `npm test -- src/lib/__tests__/botPendingStore.test.ts -t "store-once"` | ❌ Wave 0 |
| RESUME-02 | Drain: 2xx (both `created:true/false`) removes the queue entry; 422 removes + captures; 401/5xx keeps the entry | unit | `npm test -- src/hooks/__tests__/useStoreBotGame.test.ts -t "drain"` | ❌ Wave 0 |
| RESUME-02 | Resumed-then-finished game's `gameUuid` is stable from mint through store (never re-minted on resume) | unit | `npm test -- src/hooks/__tests__/useBotGame.test.ts -t "stable-uuid"` | ❌ Wave 0 (extends existing file) |

### Sampling Rate
- **Per task commit:** `npm test -- <touched test file> -t "<relevant token>"`
- **Per wave merge:** `npm test -- --run` (frontend full suite) — this phase has no backend changes, so `uv run pytest` is not gated by this phase's own work, but the pre-merge gate still runs it per CLAUDE.md's standing rule.
- **Phase gate:** `npm run lint && npm test -- --run` green, plus `npx tsc -b` (per project memory `feedback_frontend_run_tsc_build` — `npm run build`/lint/test do NOT type-check property access; run the build explicitly since this phase touches `useBotGame`'s exported `UseBotGameState` shape).

### Wave 0 Gaps
- [ ] `frontend/src/lib/botGameSnapshot.ts` + `frontend/src/lib/__tests__/botGameSnapshot.test.ts` — new module, new test file
- [ ] `frontend/src/lib/botPendingStore.ts` + `frontend/src/lib/__tests__/botPendingStore.test.ts` — new module, new test file
- [ ] `frontend/src/hooks/useStoreBotGame.ts` + `frontend/src/hooks/__tests__/useStoreBotGame.test.ts` — new hook, new test file
- [ ] Extend `frontend/src/hooks/__tests__/useBotGame.test.ts` with resume-seed, prewarm-gate, and stable-uuid test groups (existing file, existing mocking conventions apply unchanged)
- [ ] Extend `frontend/src/lib/__tests__/chessClock.test.ts` with the new `foldElapsedIntoClockBase` helper's tests

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Store endpoint already gated by `current_active_user` (Phase 167, unchanged this phase) |
| V3 Session Management | No | No new session surface |
| V4 Access Control | No | Server already derives `user_id` from the JWT, never trusts client input (Phase 167, verified in `app/routers/bots.py:29-30` docstring) |
| V5 Input Validation | Yes | `StoreBotGameRequest`'s existing Pydantic bounds (`MAX_BOT_PGN_LENGTH`, ELO/blend ranges, `_MAX_TC_PRESET_LENGTH`) already gate the server side; this phase's only new *client-side* input-validation surface is the localStorage snapshot's own JSON.parse + version + shape checks (a client reading its own prior write, low risk, but a corrupted/tampered localStorage value — e.g. a browser extension or a user editing devtools — must not crash the app; the try/catch + version-gate design already covers this) |
| V6 Cryptography | No | No crypto surface; `crypto.randomUUID()` is used for uniqueness (D-11), not for a security boundary |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| A malformed/tampered localStorage snapshot value crashes the resume-gate render | Denial of Service (client-only, single-user) | Try/catch + schema/version validation on every read, degrading to "no snapshot" (already specified in D-09 and this research's localStorage Failure Modes section) |
| A user re-submits an already-stored `gameUuid` (duplicate tab, replayed request) | Tampering (self only, not cross-user) | Already fully mitigated server-side by Phase 167's `uq_games_user_platform_game_id` idempotency constraint — this phase's `gameUuid` stability (D-11) is what makes the mitigation reachable, not a new mitigation itself |
| `MAX_BOT_PGN_LENGTH` (100,000 chars) DoS via an oversized client-crafted PGN | Denial of Service | Already enforced server-side (Phase 167, unchanged); this phase's snapshot payload (≤~2 KB per the size estimate above) is far below this bound in normal operation, so no new client-side length cap is needed for the resume snapshot itself |

## Sources

### Primary (HIGH confidence — empirically verified in this session)
- `frontend/package.json` — chess.js version pin (`^1.4.0`), installed version confirmed via `node -e` (`1.4.0`)
- Local `node_modules/chess.js@1.4.0` — direct execution of `pgn()`/`loadPgn()`/`setComment()`/`getComments()` across 5 scenarios (10-ply, 32-ply, checkmate, promotion+custom-FEN, mid-game unterminated)
- `frontend/src/hooks/useBotGame.ts` (full file, 1005 lines) — every ref/state/effect referenced above cited by exact line number
- `frontend/src/lib/chessClock.ts` (full file) — `computeChargeableElapsedMs`, `hasFlaggedOnDebit`, `applyIncrementMs` semantics
- `frontend/src/lib/botGamePgn.ts` (full file) — `annotateClock`, `finalizeBotPgn`, `toBackendTcStr` exact signatures
- `frontend/src/lib/engine/openingBook.ts` (full file) — `resolveBookMove`'s `chess.history()` requirement, confirming the PGN-restore approach satisfies it
- `frontend/src/pages/Bots.tsx` (full file) — confirmed the D-14 stub auto-starts unconditionally on mount, no gate today
- `frontend/src/lib/welcomeDismissal.ts`, `frontend/src/hooks/useUserFlag.ts` — localStorage guard/try-catch precedent
- `frontend/src/lib/botDrawGate.ts` — `DRAW_OFFER_COOLDOWN_MOVES`, `canOfferDraw`, `wouldBotAcceptDraw` sentinel semantics
- `app/schemas/bots.py`, `app/routers/bots.py`, `app/services/store_bot_game_service.py`, `app/models/bot_game_settings.py`, `app/services/normalization.py` (relevant sections) — the D-14 `tc_preset` correction
- `tests/services/test_store_bot_game_service.py`, `tests/routers/test_bots.py`, `tests/repositories/test_bot_game_settings_repository.py` — the executable ground truth for `tc_preset`'s real format
- `frontend/src/hooks/__tests__/useBotGame.test.ts` (header + mocks section) — test conventions to mirror

### Secondary (MEDIUM confidence)
- [Page Lifecycle API | Chrome for Developers](https://developer.chrome.com/docs/web-platform/page-lifecycle-api) — `visibilitychange` as the primary reliable signal
- [Window: pagehide event | MDN](https://developer.mozilla.org/en-US/docs/Web/API/Window/pagehide_event) — `pagehide` fallback behavior
- [Document: visibilitychange event | MDN](https://developer.mozilla.org/en-US/docs/Web/API/Document/visibilitychange_event)
- [window.onbeforeunload Not Working on Mobile Safari for iOS? — w3tutorials.net](https://www.w3tutorials.net/blog/is-there-any-way-to-use-window-onbeforeunload-on-mobile-safari-for-ios-devices/) — mobile Safari unreliability of `beforeunload`
- [Time to unload your unload events | rumvision](https://www.rumvision.com/blog/time-to-unload-your-unload-events/) — bfcache impact of `unload`/`beforeunload` listeners

### Tertiary (LOW confidence)
- None — every claim in this document is either empirically verified against the real codebase/dependency in this session, or cited to an official/authoritative source above. No claims are marked `[ASSUMED]` in the body text (the two Assumptions Log entries are discretion-scope tuning notes, not unverified factual claims).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies; every library already in production use in this exact domain
- Architecture (resume seam, live gate, clock fold): HIGH — every ref/effect cited by exact line number from the real, current `useBotGame.ts`; the `live`-gate mechanism is a synthesis (see Assumption A2) but is derived directly from the hook's actual effect structure, not speculation
- D-08 snapshot format: HIGH — empirically verified via direct execution against the installed chess.js version, not training-data recall
- D-14 tc_preset correction: HIGH — verified against the actual shipped, currently-passing test suite (three independent test files), not a single ambiguous doc comment
- Pitfalls: HIGH — every pitfall traces to a specific, cited line range in the real source, mirroring the exact "half-invariant" failure shape documented in this project's own retained memory from Phase 169

**Research date:** 2026-07-13
**Valid until:** Effectively indefinite for the chess.js round-trip finding (pinned dependency version, empirically tested, will not change until a chess.js upgrade). 30 days for the `useBotGame.ts` line-number references (will drift as Phase 170 itself edits the file — treat line numbers as of-this-commit references, re-verify if significant unrelated changes land on `useBotGame.ts` before this phase is planned).

## RESEARCH COMPLETE
