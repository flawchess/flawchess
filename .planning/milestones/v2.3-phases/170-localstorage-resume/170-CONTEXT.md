# Phase 170: localStorage Resume - Context

**Gathered:** 2026-07-13
**Status:** Ready for planning

<domain>
## Phase Boundary

A bot game **survives leaving the page**, and every finished bot game reaches the
server **exactly once**.

Two halves, both client-side:

1. **Resume (RESUME-01)** — the in-progress game (moves, clocks, settings, book
   latch) is snapshotted to localStorage on every move and on tab-hide/unload.
   Returning to `/bots` offers a "Resume game?" gate that restores the position
   and clocks with **no away-time billed**.
2. **Store-once (RESUME-02)** — a finished game is enqueued locally and POSTed to
   the already-shipped Phase 167 `POST /bots/games`; the local record clears only
   after a **confirmed** store. An abandoned (unfinished) game is never POSTed at
   all, and a resumed-then-finished game can never be stored twice.

**In scope:** the snapshot module (serialize / restore / version / validate), the
resume seam into `useBotGame`, the pause-aware clock-fold rules, the resume-gate
UI component on `/bots`, the frontend store client (`botsApi.storeGame` +
mutation), the pending-store queue and its drain-on-mount, and tests.

**Out of scope (Phase 171):** the Bots **setup screen** (ELO / blend / color / TC
pickers), the **nav entry**, the guest not-auto-analyzed caveat UI, and the
Library deep-link from the result surface. 170 leaves the existing D-14 stub
auto-start in place for the "no snapshot" branch; 171 replaces exactly that
branch with the setup screen.

**170 / 171 boundary — resolved (see D-10).** The ROADMAP gives both phases a
claim on the store call (170 SC2/SC3 vs 171 SC3/SC4). 170's SCs are unverifiable
without a client store path, so **170 owns the store plumbing** (api client,
mutation, uuid, pending queue, once-only semantics) and **171 owns the surfaces**
that sit on top of it. Phase 171's SC3/SC4 will already be largely satisfied by
170's plumbing; 171 verifies them through the real page.

</domain>

<decisions>
## Implementation Decisions

### Clock fairness on leave / resume (discussed)

- **D-01 — Bill think time, refund away time.** The snapshot is written on every
  move **and** on tab-hide / `pagehide`, and the hide-time write **folds the
  active side's in-turn `chargeableElapsedMs()` into its clock base** before
  serializing. So a user who thinks 40s and then closes the tab resumes with
  those 40s **spent**, and with 0s of away-time billed. A snapshot-on-moves-only
  design was rejected: it silently refunds the current turn's think time on every
  refresh, which is a free "undo my clock".
  - **Accepted gap:** `pagehide` / `visibilitychange` are not guaranteed (browser
    kill, crash, iOS tab purge). Those fall back to the last **move** snapshot and
    forgive the in-turn think time. That is an acceptable, honest degradation — do
    NOT add a polling heartbeat to close it (a throttled ~1s clock write was
    explicitly considered and rejected as not worth a timer running all game).

- **D-02 — The bot's interrupted think is REFUNDED, not billed.** The in-turn
  elapsed fold in D-01 applies **only when the USER is the active side**. If the
  page is left during the bot's turn, the bot's clock is snapshotted as of its
  **last commit** and its turn restarts cleanly on resume. Rationale: the search
  dies with the Web Workers, so we would be billing for work we throw away — and
  Phase 169 already establishes exactly this rule (a resign / new-game / unmount
  cancel discards a bot turn with no debit). No user exploit exists: refunding the
  *bot's* clock only ever helps the bot.

- **D-03 — Nobody pays for the engine cold-start.** On resume the `WorkerPool` /
  `MaiaQueue` / Maia ONNX session must respawn (~1–2s); a bot with 5s left must
  not flag on a worker spawn. Two mechanisms, both required:
  1. **Prewarm on snapshot detection** — start `pool.warm()` / `queue.warm()` (and
     the ECO prefix-set fetch) the moment a resumable snapshot is found, i.e.
     while the "Resume game?" gate is on screen, before the user commits. Same
     trick as 169.5's warm-during-the-book-window.
  2. **Anchor after live** — the clock's `turnStartedAtRef` is set only once the
     resumed board is live (and, on a bot turn, the engines are warm). No clock
     runs while the page is booting.
  - **⚠ MECHANISM CORRECTED 2026-07-13 by RESEARCH (source-verified).** The intent
    above is unchanged, but mechanism 1 as written is not reachable:
    `createWorkerPool()` / `createMaiaQueue()` are constructed *inside*
    `useBotGame`'s own mount effect (`useBotGame.ts:761-765`), so `Bots.tsx`
    cannot call `pool.warm()` before the hook mounts without creating a second,
    throwaway pool. Correct shape: **mount the hook immediately on snapshot
    detection** (its real bring-up effect already calls `pool.warm()` /
    `queue.warm()` at `useBotGame.ts:774-775`) and add a **`live` gate** so the
    turn-anchor, clock-tick, and bot-turn-trigger effects do not fire until the
    user confirms Resume. Without that gate, a snapshot restored on the *bot's*
    turn starts searching — and billing the clock — the instant the resume gate
    renders. This makes mechanism 2 ("anchor after live") explicit rather than
    implicit.

### Resume gate UX + slot policy (discussed)

- **D-04 — 170 ships a real resume-gate component, not just headless logic.** On
  `/bots` load: snapshot present → render the gate ("Resume game?" with the game's
  identity — e.g. *Blitz 5+3 vs bot 1500 · 14 moves · 2 days ago* — and
  **Resume** / **Discard**), and **do not auto-start any game until the user
  chooses**. No snapshot → today's D-14 stub auto-start (which 171 replaces with
  the setup screen). This makes SC1 verifiable inside 170, and 171 keeps the
  component.

- **D-05 — Discard confirms first.** Discard is irreversible (an abandoned game
  leaves no server trace anywhere — SC2), so it opens a small confirmation
  ("This game will be lost — unfinished games are never saved") before clearing
  the snapshot and falling through to the fresh-game path. Mirrors the existing
  resign-confirm pattern in `GameControls`. Rejected: an immediate one-tap drop
  sitting next to "Resume" on mobile. Also rejected (and requires a REQUIREMENTS
  change, not a phase decision): treating abandonment as an auto-resigned loss —
  that directly contradicts RESUME-02 / SC2.

- **D-06 — A snapshot never expires; show its age instead.** It lives until the
  user resumes-and-finishes it, discards it, or a schema-version bump invalidates
  it. The gate shows the game's age ("2 days ago") so a stale game is obvious and
  the **user** decides. No TTL constant — the snapshot is a few KB and a silent
  auto-drop destroys a game the user may still want.

- **D-07 — Single in-progress slot.** One localStorage key holds at most one
  in-progress bot game. Multiple resumable games would need a game-list UI that
  belongs to 171's setup screen at the earliest. Starting a new game while a
  snapshot exists goes through the D-05 discard confirmation. (Note this is
  independent of the pending-store queue, which is a separate key — D-12.)

### Snapshot shape + resume seam (Claude's discretion — grounded calls)

- **D-08 — Persist the move stack, NOT a FEN, as the source of truth.**
  **⚠ RESOLVED 2026-07-13 by RESEARCH — the concrete form is `chess.pgn()`.**
  This bullet originally mandated a SAN move list plus a parallel per-ply
  `[%clk]` array, with an explicit escape hatch: *"the planner may instead
  persist `chess.pgn()` and restore via `loadPgn()` if and only if research
  confirms chess.js 1.x round-trips `{[%clk ...]}` comments through `loadPgn`
  losslessly."* Research **confirmed exactly that** against the installed
  chess.js 1.4.0: `pgn()` → `loadPgn()` → `pgn()` is byte-identical across 5
  scenarios, including the mid-game unterminated shape written on every move.
  **So the snapshot persists `chess.pgn()` and restores via `loadPgn()`** —
  simpler, and it carries the `[%clk]` comments for free. The reasoning below
  still explains *why a FEN is disqualified*, which is unchanged and remains
  binding. The round-trip property test below remains the acceptance gate.
  - Two hard reasons a FEN (or a bare SAN list) is wrong — both still apply, and
    both are satisfied by the `chess.pgn()` / `loadPgn()` form:
  - **A FEN loses the move stack**, which kills threefold-repetition detection,
    the PGN export, and — critically — 169.5's `resolveBookMove`, which
    **explicitly requires a board with pushed moves** (`chess.history()`); a
    `new Chess(fen)` board silently matches the wrong ECO prefixes.
  - **A bare SAN list loses every `[%clk]` comment.** `annotateClock` writes the
    clock into chess.js's per-position **comment store** (`chess.setComment`),
    and `finalizeBotPgn` emits them via `chess.pgn()`. Replaying SAN on a fresh
    board drops them all — so a resumed game's PGN would carry clocks only for
    post-resume plies, and a game resumed and immediately ended (resign) could
    lose a color's clock entirely and be **rejected 422** by the Phase 167
    `[%clk]` presence gate. The clk array is exactly the
    `remainingAfterIncrement` value `commitMove` already computes per ply.
  - **Verification hook (make this a real test, not a grep):** a round-trip
    property — `restore(snapshot(game)).pgn() === game.pgn()` for a game with
    moves by both colors. Reverting the PGN restore MUST fail this test.
  - *(The escape hatch this bullet originally offered — "persist `chess.pgn()`
    if and only if research confirms the `loadPgn` round-trip" — has been taken;
    see the RESOLVED note at the top of D-08.)*

- **D-09 — Snapshot payload.** Versioned JSON under one key. Contents:
  `version` (bump ⇒ silently drop the snapshot), `gameUuid` (D-11), `settings`
  (the whole `BotGameSettings` — needed for the store POST after a resume),
  `pgn: string` (the `chess.pgn()` form — see D-08's RESOLVED note; this replaces
  the `sanMoves` + `clkMs` pair this bullet originally listed, and carries the
  `[%clk]` comments losslessly), `whiteClockMs` / `blackClockMs`
  (the **base** values, with the D-01/D-02 fold applied), `movesSinceLastDecline`
  (else a refresh resets the draw-offer cooldown and it can be spammed),
  `hasLeftBook` (**must** persist — 169.5 D-03 makes leaving book a one-way latch
  that **cannot** be re-derived from move history; a fresh latch would silently
  re-enter the book mid-game), `hasFiredLowTime`, and `savedAt` (for D-06's age).
  Deliberately **not** persisted: `activeColor` (derive from `sanMoves.length`
  parity — do not store a second copy of a derivable fact) and
  `lastRootPracticalScore` (its `null` sentinel is fail-closed: the bot simply
  refuses draws until its next searched move re-populates it).
  - Persistence lives in a pure `lib/botGameSnapshot.ts` (serialize / parse /
    validate / version) that the hook calls; guard `typeof localStorage ===
    'undefined'` (the `lib/welcomeDismissal.ts` pattern) and try/catch writes
    (QuotaExceeded / Safari private mode) — degrade to no-resume, capture once.

- **D-10 — Resume seam: ONE hook, ONE game loop.** Add an optional
  `resume?: BotGameSnapshot` argument to `useBotGame(settings, resume?)` and
  lazily initialize the existing refs/state from it (`chessRef` via SAN replay,
  `clockBaseRef`, the latches). Do **not** fork a second restore path or a parallel
  hook — a duplicated invariant is exactly the failure shape Phase 169's gap
  closures kept hitting. `newGame()` additionally clears the snapshot.

### Store-once lifecycle (Claude's discretion — grounded calls)

- **D-11 — Mint `gameUuid` at game START** (`crypto.randomUUID()`), persisted in
  the snapshot, so it is **stable across a resume**. Phase 167 keys idempotency on
  `platform_game_id = game_uuid` (its `uq_games_user_platform_game_id`
  constraint), so a stable uuid makes a double-store structurally impossible even
  across a lost response or a second tab.

- **D-12 — The pending-store queue is a SEPARATE localStorage key.**
  It must not share the in-progress snapshot's key.
  On game end, `finalizeGame`'s PGN + settings + uuid are
  **enqueued** to `flawchess_bot_pending_store` (an array, capped) and the
  in-progress key is cleared. If they shared one key, a failed store followed by
  the user starting a new game would **silently overwrite and lose the finished
  game forever**. Enqueue-on-finish is also what makes SC2 structural: the POST
  can only ever be fed from a queue that only `finalizeGame` writes to, so an
  abandoned game has no path to the server.

- **D-13 — Drain the queue on `/bots` mount, before the gate renders.** Each entry
  POSTs to `/bots/games`; the entry is removed **only** on a confirmed 2xx (both
  `created: true` and `created: false` count — a `false` means the server already
  has it, which is exactly the success we want). Failure handling:
  - **network / 5xx** → keep the entry, retry on the next visit (bounded in-session
    retries via the mutation's retry config). A pending entry blocks nothing.
  - **422** (invalid PGN — a client bug) → capture to Sentry and **drop** the
    entry; retrying can never succeed and would pin a permanent pending record.
  - **401** (logged out / expired guest token) → keep the entry, retry once
    authenticated. Do not drop.

- **D-14 — Frontend store client.** Add `botsApi.storeGame` to
  `frontend/src/api/client.ts` + a `useStoreBotGame` TanStack mutation (the global
  `MutationCache.onError` in `lib/queryClient.ts` already captures to Sentry — do
  not add a duplicate `captureException`). Request body per the shipped
  `StoreBotGameRequest`: `{ game_uuid, pgn, user_color, bot_elo, play_style_blend,
  tc_preset }`.

  - **⚠ CORRECTED 2026-07-13 by RESEARCH (source-verified) — the original D-14
    text below was inverted.** `tc_preset` MUST be
    `toBackendTcStr(baseSeconds, incrementSeconds)` — base-**seconds**, e.g.
    `"300+3"` — i.e. the **same string** as the PGN's `[TimeControl]` header.
    It is NOT the lichess display preset. Despite the column's name, the server
    feeds it straight into `parse_time_control()`
    (`app/services/store_bot_game_service.py:76`), which reads base-seconds, and
    then into `games.time_control_str` via `normalize_flawchess_game`. Sending
    `"5+3"` would parse as base=5s → estimated 5 + 3*40 = 125s → **bullet**,
    silently mis-bucketing the game, picking the wrong rating anchor, and writing
    a `time_control_str` in a format no imported game uses. The shipped tests are
    unambiguous: `tests/services/test_store_bot_game_service.py:32`
    (`_TC_STR = "180+2"  # parse_time_control("180+2") -> ("blitz", 260)`),
    `tests/routers/test_bots.py:77` (`_TEST_TC_PRESET = "180+2"`).
    **So: reuse `toBackendTcStr` for `tc_preset`. There is no separate derivation.**
  - *Original (WRONG, kept for the record):* "Watch the `tc_preset` trap: the PGN's
    `[TimeControl]` header uses `toBackendTcStr` = base-seconds (`"300+3"`), while
    Phase 167 D-16 stores `tc_preset` as the lichess display preset (`"5+3"`).
    These are different strings — derive the preset separately."

*(D-08's and D-03's 2026-07-13 research corrections are recorded inline on those
bullets above, not as separate decisions.)*

### Claude's Discretion (remaining)

- Exact localStorage key names, the snapshot module's function names, the queue
  cap, the gate component's file placement and visual composition (it must follow
  the existing Bots component conventions + the `data-testid` rules), and whether
  the pending-store drain surfaces any UI at all in 170 (it may be silent; 171
  owns the user-facing result/Library surfaces).
- Whether the resume gate is a full-page state or a dialog over the board.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase / milestone scope
- `.planning/ROADMAP.md` §"Phase 170: localStorage Resume" — the goal + SC1–SC3
  this phase is verified against. Also read §"Phase 171" to respect the D-10
  boundary (setup screen / nav / guest caveat are NOT this phase).
- `.planning/REQUIREMENTS.md` — RESUME-01, RESUME-02 (locked) + the "Non-Goals"
  table (no server-side game sessions, no websockets).
- `.planning/seeds/SEED-091-flawchess-bot-play-milestone.md` — the milestone's
  locked design decisions (store-on-finish via the existing normalization path).

### The game loop this phase snapshots (Phase 169 / 169.5)
- `frontend/src/hooks/useBotGame.ts` — the hook to add the resume seam to (D-10).
  Read its header comment in full: the honest-clock model (D-15/D-16), the
  pause-aware `chargeableElapsedMs` / `resetTurnAnchor` helpers (D-20/CR-01 — the
  machinery D-01/D-02 build on), the `outcomeRef` finalize latch, and the
  `hasLeftBookRef` one-way latch (D-09 must persist it).
- `frontend/src/lib/chessClock.ts` — `computeChargeableElapsedMs`,
  `shiftAnchorForPause`, `applyIncrementMs`, `hasFlaggedOnDebit`. The clock is
  honest and can flag either side; a resume must not resurrect a never-flag clamp.
- `frontend/src/lib/botGamePgn.ts` — `annotateClock` (writes `[%clk]` into
  chess.js's **comment store**, the D-08 trap), `finalizeBotPgn`, `toBackendTcStr`
  (base-SECONDS, not the display preset — the D-14 trap).
- `frontend/src/lib/engine/openingBook.ts` + `.planning/phases/169.5-bot-opening-book/169.5-CONTEXT.md`
  §D-03 — the one-way leave-book latch, and why `resolveBookMove` needs a board
  with pushed SAN moves (not a FEN-loaded board).
- `.planning/phases/169-clocked-board-game-loop-usebotgame/169-CONTEXT.md` — the
  full clock/pacing decision set (esp. the "Decision Amendments" section) this
  phase must not contradict.
- `frontend/src/pages/Bots.tsx` — the D-14 stub the resume gate must gate
  (it auto-starts a game on route load today).

### The store endpoint this phase calls (Phase 167 — already shipped)
- `app/routers/bots.py` — `POST /bots/games` (200 on success, 422 on invalid PGN
  / missing `[%clk]`).
- `app/schemas/bots.py` — `StoreBotGameRequest` / `StoreBotGameResponse`
  (`{game_id, created}`), the UUID canonicalization validator, the field bounds.
- `app/services/store_bot_game_service.py` — the idempotent store path.
- `.planning/phases/167-backend-store-on-finish/167-CONTEXT.md` §D-11 / §D-14 /
  §D-15 / §D-16 — client-minted uuid idempotency, the server-derives-everything
  rule, the `[%clk]` gate, and the `tc_preset` column semantics.

### Frontend conventions
- `frontend/src/lib/welcomeDismissal.ts`, `frontend/src/hooks/useUserFlag.ts` —
  the existing localStorage patterns (SSR guard, no schema, no versioning — this
  phase needs more, but follow their shape).
- `frontend/src/api/client.ts` + `frontend/src/lib/queryClient.ts` — where the
  store client goes; the global `QueryCache`/`MutationCache` Sentry capture (do
  not duplicate it in components).
- `CLAUDE.md` §Frontend — `data-testid` on every interactive element, `text-sm`
  floor, `brand-outline` for secondary buttons, mobile parity.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `useBotGame` already exposes a fully serializable state surface and its own
  docstring names Phase 170 as the snapshot consumer — but there is **no**
  init-from-snapshot seam today; every ref/state initializes from `settings` at
  mount. D-10 adds the seam.
- `chargeableElapsedMs()` / `pausedAtRef` / `resetTurnAnchor()` (useBotGame) —
  the hidden-tab pause machinery. A leave/resume is the same problem at a longer
  timescale; D-01/D-02's fold reuses `chargeableElapsedMs()` verbatim rather than
  inventing a second elapsed-time reader (Phase 169 CR-01 made "one pause-aware
  elapsed source" a structural invariant — do not add a second one).
- `pool.warm()` / `queue.warm()` (169.5) — already exist and are idempotent; D-03
  calls them from the resume gate.
- `finalizeBotPgn` / `annotateClock` (botGamePgn.ts) — the PGN the store POST
  sends; `useBotGame` already sets `pgn` state on game end (D-12 enqueues it).
- Phase 167's `POST /bots/games` is shipped, idempotent, and has **no frontend
  call site yet** — this phase writes the first one.

### Established Patterns
- localStorage access is guarded (`typeof localStorage === 'undefined'`) and
  wrapped in tiny pure modules (`welcomeDismissal.ts`) — no existing versioned/
  structured snapshot pattern to copy, so D-09 introduces one.
- TanStack mutations get Sentry capture for free via the global `MutationCache`
  (CLAUDE.md) — the store call must NOT add its own `captureException`.
- Phase 169's hard-won lesson (recorded in the project memory): a "half-invariant"
  — a rule enforced in one place but duplicated/bypassed in another — is invisible
  to tsc/eslint/knip/tests. Every invariant this phase adds (clk restore, book
  latch, store-once) needs a test that FAILS when the mechanism is reverted.

### Integration Points
- `Bots.tsx` route load → snapshot detection → (prewarm + resume gate) → either
  `useBotGame(settings, snapshot)` or `useBotGame(settings)`.
- `useBotGame.commitMove` → snapshot write (every move). `visibilitychange` /
  `pagehide` → snapshot write with the D-01 fold. `finalizeGame` → enqueue to the
  pending-store queue + clear the in-progress key.
- `Bots.tsx` mount → drain the pending-store queue → `POST /bots/games` → clear
  each entry on a confirmed 2xx.
- Phase 171 consumes: the resume gate component, the store mutation, and the
  `useBotGame(settings, resume?)` signature.

</code_context>

<specifics>
## Specific Ideas

- The gate's game identity line should read like a lichess resume card:
  *"Blitz 5+3 vs FlawChess Bot (1500) · 14 moves · 2 days ago"* — enough for the
  user to recognize the game without restoring it (D-04/D-06).
- The `restore(snapshot(game)).pgn() === game.pgn()` round-trip property test is
  the acceptance gate for D-08. Reverting the clk-array restore must turn it red.

</specifics>

<deferred>
## Deferred Ideas

- **Multiple resumable games / a resumable-games list** — needs a game-list UI;
  earliest home is Phase 171's setup screen, more likely a later milestone
  (D-07).
- **A clock heartbeat that survives a hard browser kill** — explicitly rejected in
  D-01; the last-move fallback forgives the in-turn think time in that rare case.
  Revisit only if it ever matters competitively.
- **Surfacing "your finished game failed to save, retrying"** to the user — 170
  drains silently; the user-facing result/Library surfaces belong to Phase 171.

</deferred>

---

*Phase: 170-localstorage-resume*
*Context gathered: 2026-07-13*
