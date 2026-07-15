# Phase 169: Clocked Board + Game Loop (`useBotGame`) - Context

**Gathered:** 2026-07-12
**Status:** Ready for planning

<domain>
## Phase Boundary

The user plays a full clocked game against the bot on a live client-side board:
a `useBotGame` game-loop hook plus the surrounding UI — dual Fischer-increment
clocks (wall-clock `Date.now()`-delta model, pause while the tab is hidden
during the bot's turn), bot pacing per the locked 168.5 model (fixed shipped
search budget, randomized reveal delay, synthetic clock debit, bot never
flags), every end condition (checkmate, stalemate, threefold repetition,
50-move, insufficient material, user flag-on-time), resign + draw offer/accept,
move sounds with a mute control, a result screen with "Analyze this game" /
"New game", and per-move `[%clk]` PGN annotations for both colors.

Ships on the real lazy-loaded `/bots` route, unlinked from the nav, behind a
minimal hardcoded-settings start stub. Does NOT own: the setup screen, nav
entry, or guest flow (Phase 171); localStorage persistence/resume (Phase 170);
store-on-finish POST wiring (Phase 171 calls the Phase 167 endpoint); any
change to search strength or budget (168.5 shipped `botBudget.ts` — consume it
as-is).

</domain>

<decisions>
## Implementation Decisions

### Bot draw/resign etiquette
- **D-01: Draw-offer acceptance = eval + endgame gate.** The bot accepts the
  user's draw offer only when BOTH hold: its evaluation of the current position
  is near-equal (expected score ~0.5 within a named threshold — reuse the
  grading provider it already has, or the last search's root practicalScore)
  AND the game is past an endgame/material gate (e.g. queens off or a move-
  number threshold; exact gate is a named constant). Early lifeless positions
  get declined — play continues.
- **D-02: The bot never offers a draw itself.** It only responds to user
  offers. Automatic draw rules (threefold, 50-move, insufficient material)
  already end truly dead games.
- **D-03: The bot never resigns.** It plays to mate — beginners get conversion
  practice; zero resign logic.
- **D-04: Guard rails — confirm resign, throttle draw offers.** Resign requires
  one confirmation step (two-tap or confirm dialog; misclicks are fatal). After
  a declined draw offer the user must wait a few of their own moves (named
  constant, ~5) before offering again. Lichess-like.

### Pacing & clock display
- **D-05: Bot clock ticks in real time during its think; final debit = max(real elapsed, synthetic scheduled), clamped never-flag.** While search +
  reveal delay run, the bot's displayed clock counts down in real time (never
  looks frozen). On move reveal the total debit applied is the LARGER of real
  elapsed time and the 168.5 D-02 fraction-of-remaining synthetic amount — no
  visible upward snap, at most an extra drop. Because "the bot never flags" is
  locked (168.5 D-02), the final debit is clamped so the bot's clock never
  reaches zero (clamp floor = named constant).
- **D-06: Subtle "bot is thinking" indicator** — a small pulsing dot / animated
  ellipsis next to the bot's name or clock while it thinks, on top of the
  ticking clock. Reassures during a 10s+ contested-position think.
- **D-07: Lichess-style low-time display.** Under a threshold (~10s, named
  constant): the clock shows tenths (0:09.4) and the active clock turns
  red/urgent.

### Sounds (net-new — no audio infra exists)
- **D-08: Vendor the standard lichess sound set** (move, capture, check,
  game-end). FlawChess is AGPL-3.0 like lila — license-compatible; include
  attribution.
- **D-09: Two extra sound events beyond the required four.** A low-time
  warning that fires once when the USER's clock first crosses the low-time
  threshold (pairs with D-07's red clock), and a notification blip when the
  bot declines a draw offer.
- **D-10: Sounds default ON; mute toggle persisted to localStorage.** Boolean
  mute only — no volume slider. Toggle lives on the game screen.

### Result screen & phase surface
- **D-11: Dismissible result dialog + persistent inline strip.** On game end a
  compact modal shows outcome + reason ("You won — checkmate") with Analyze /
  New game actions; dismissing it reveals the final position, and an inline
  result strip keeps the actions reachable. Lichess-like.
- **D-12: "Analyze this game" deep-links to `/analysis` with the move sequence NOW.** Uses
  the existing `line` param (precedence game_id > fen > line). Works
  client-side immediately, works for guests. Phase 171 upgrades the CTA to the
  stored `game_id` after the POST succeeds.
- **D-13: Move list + view-only scroll-back during play.** A linear SAN move
  list next to the board; clicking / arrow keys step back through earlier
  positions VIEW-ONLY (board input disabled off the live position; snaps back
  to live when a new move is played).
- **D-14: Ships on the final `/bots` route, lazy-loaded, unlinked from nav,**
  with a minimal hardcoded-settings "Start game" stub (fixed ELO/blend/TC or a
  bare debug picker — Claude's discretion). Phase 171 replaces the stub with
  the real setup screen and adds the nav entry. Enables full in-browser UAT of
  this phase.

### Decision Amendments — 2026-07-13, post-verification gap closure (SUPERSEDING)

Verification (`169-VERIFICATION.md`) failed SC1 and SC2. Rather than restore the
never-flag invariant, the user reversed it: **the bot is now allowed to lose on
time.** These amendments supersede D-05 and the 168.5 D-02/D-04 "never flags"
lock. Where this section conflicts with D-05, the 168.5 decision records, PLAY-05,
or ROADMAP SC1, **this section wins** — those documents are to be amended as part
of the closure work, not treated as constraints on it.

- **D-15 (supersedes D-05): The bot's clock is honest — real elapsed time, no synthetic debit, no never-flag clamp.**
  The fraction-of-remaining synthetic
  model (`computeSyntheticDebitMs`) and the never-flag clamp
  (`reconcileBotDebitMs` / `NEVER_FLAG_FLOOR_MS`) are deleted, not guarded. They
  produced a clock that mathematically converges to a ~6s equilibrium at the
  shipped 5+3 preset (`r = 0.95r + 300 → r* = 6000ms`) and parks there for the
  whole game, which is both a UX oddity and the root cause of the SC1 failure.
  The bot is debited exactly the wall-clock time its turn actually consumed
  (search + reveal delay), plus the Fischer increment on commit — the same rule
  the user's clock obeys.

- **D-16: The bot manages its clock via a per-move think deadline; the search is cut at the deadline and plays its best move so far.**
  An honest clock with a
  *fixed* search budget is degenerate — at 5+3 with a ~5.4s median search and a
  3s increment the bot bleeds ~2.4s/move net and any user can win every game by
  shuffling pieces for ~125 moves. So the bot must speed up when low. A deadline
  is derived from its remaining time (`computeThinkDeadlineMs(remainingMs,
  incrementMs)`, engine-style `remaining/MOVES_TO_GO + increment × share`,
  clamped to a named [min, max] band) and enforced by aborting the search when it
  expires.

  **Key enabler (verified, 2026-07-13):** `mctsSearch` treats abort as a graceful
  stop, not an error — its loop condition is `while (nodesEvaluated <
  budget.maxNodes && !signal.aborted && !earlyStop)` and it falls through to
  `return buildSnapshot(...)` (mctsSearch.ts:456 → 535). A deadline abort
  therefore returns the best line found so far. **No change to the frozen Phase
  166/168.5 engine core is required**, and `botBudget.ts`'s node budget stays
  exactly as calibrated.

- **D-17: Two distinct abort reasons.** Today `useBotGame` treats every
  `signal.aborted` as "discard the turn" (useBotGame.ts:509, 515). That is now
  wrong for a deadline cut. A **deadline** abort must *use* the returned snapshot
  and commit the move; a **cancel** abort (new game, unmount, bot flagged) must
  still discard. Distinguish them explicitly — do not infer intent from
  `signal.aborted` alone.

- **D-18: A minimum-node floor gates the deadline.** A deadline that fires before
  the tree has expanded any root children would hand `selectBotMove` a degenerate
  snapshot. The deadline may not cut below a named minimum-node floor (reuse or
  align with `FLAWCHESS_BOT_STOP_RULE.minNodes = 8`); if the bot is so low on
  time that the floor overruns its remaining clock, it **flags** — that is the
  intended behavior now, not a bug to clamp away.

- **D-19: The bot's calibrated ELO holds only at the full node budget — accepted, and must be stated in-code.**
  `botBudget.ts` is the single definition shared
  with the calibration harness, and the 168.5 ELO mapping was measured at the
  full 50-node budget. Under D-16 a time-troubled bot is deadline-cut to fewer
  nodes and plays materially weaker than its advertised ELO. This is accepted as
  desirable (humans get worse in time trouble) but it means the shipped ELO label
  is accurate only when the bot is not low on clock. Document this explicitly in
  `botBudget.ts` / `chessClock.ts` so a future reader does not "fix" the
  divergence, and so the harness numbers are not mistaken for whole-game truth.

- **D-20 (gap 2, unchanged by the above — a plain bug): the hidden-tab pause must reach the bot's committed debit.**
  `runBotTurn` snapshots `turnStartedAtRef`
  into a dispatch-time local (useBotGame.ts:489) and computes the debit from it
  (line 519), bypassing the visibility-pause anchor shift that the live ref
  receives. Read the **live** ref at resolution time, and re-baseline
  `pausedAtRef` when `commitMove`/`newGame` reset the anchor mid-hide (WR-02) so
  a move committed while hidden cannot produce a future-dated anchor on resume.
  With D-15/D-16 making the bot flaggable this is no longer cosmetic: charging
  the bot for hidden-tab time makes "background the tab during the bot's think"
  a reliable way to farm timeout wins.

**Documents to amend as part of closure** (they currently assert the reversed
invariant and will otherwise re-fail verification on their own text): ROADMAP SC1,
`REQUIREMENTS.md` PLAY-05, the 168.5 D-02/D-04/D-05 decision records, and the
`chessClock.ts` / `botBudget.ts` module docstrings.

### Claude's Discretion
- The D-16 deadline parameters (`MOVES_TO_GO` divisor, increment share, the
  [min, max] clamp band) and the D-18 minimum-node floor — named constants, tuned
  by feel so a 5+3 game paces plausibly and time trouble is reachable but not
  routine.
- The exact reveal-delay range (168.5 locked the ~0.5–1.5s ballpark). Note the
  reveal delay is part of the bot's honest debit under D-15 and must not be
  allowed to push a low-clock bot over its own deadline gratuitously.
- Exact D-01 thresholds (near-equal eval band, endgame gate definition) and
  the D-04 draw-throttle count.
- Audio implementation approach (HTMLAudioElement vs Web Audio buffers),
  preloading, and asset format.
- Interim start-stub shape on `/bots` (hardcoded constants vs bare debug
  picker), component/file layout, promotion-picker UX (follow the existing
  analysis-board promotion pattern), board orientation defaults.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope & locked pacing model (READ FIRST)
- `.planning/ROADMAP.md` §"Phase 169" — goal + SC1–SC5 (SC1 is the 168.5-
  amended pacing contract this phase implements verbatim).
- `.planning/phases/168.5-bot-move-pacing-search-budget-seed-096/168.5-CONTEXT.md`
  — D-01..D-04b: the locked fixed-strength + synthetic-debit + reveal-delay
  model; D-04b (pacing theater is UX-only, harness has none) must stay true.
- `.planning/REQUIREMENTS.md` — PLAY-03..PLAY-09. NOTE: PLAY-05's original
  "budget derived from remaining clock" wording is superseded by the amended
  ROADMAP SC1 (fixed budget + reveal delay + synthetic debit, per 168.5 D-04).
- `.planning/seeds/SEED-091-flawchess-bot-play-milestone.md` — milestone frame
  and the five locked design decisions.

### Engine surface this phase CONSUMES (do not modify)
- `frontend/src/lib/engine/botBudget.ts` — the shipped bot budget profile
  (`FLAWCHESS_BOT_MAX_NODES 50`, `_MAX_PLIES 8`, `_CONCURRENCY 4`,
  `FLAWCHESS_BOT_STOP_RULE`); single definition shared with the harness;
  `useFlawChessEngine.ts` re-exports for app callers.
- `frontend/src/lib/engine/selectBotMove.ts` — the move-selection entry:
  `selectBotMove(fen, settings, deps, signal)`; AbortSignal cancels the think
  on resign / new game / navigation (166 D-07).
- `.planning/phases/166-bot-move-selection-core-selectbotmove/166-CONTEXT.md`
  — D-07..D-14: signature, deps injection (policy/grade/rng), fallback and
  determinism rules; live app passes a `Math.random`-backed rng.
- `frontend/src/hooks/useFlawChessEngine.ts` — reference wiring of providers
  (`createMaiaQueue()`/`createWorkerPool()`) + `SearchBudget`; `useBotGame`
  mirrors this provider bring-up.
- `frontend/src/lib/engine/types.ts` — `SearchBudget`, `BotStopRule`,
  `EngineProviders` contracts.

### UI/board assets this phase builds on
- `frontend/src/components/board/ChessBoard.tsx` — the existing interactive
  react-chessboard 5.x wrapper (drag + click-to-move, `data-testid`
  conventions per CLAUDE.md Browser Automation Rules).
- `frontend/src/hooks/useAnalysisBoard.ts` — chess.js game-state patterns
  (promotion handling ~line 508, legal-move gating) to mirror, not reuse
  wholesale (analysis branching is out of scope here).
- `frontend/src/pages/Analysis.tsx` — deep-link param handling
  (game_id > fen > line) that D-12's Analyze CTA targets.

### Downstream consumers (design for, don't build)
- Phase 170 (localStorage resume) will snapshot/restore `useBotGame` state +
  paused clocks — keep game state serializable.
- Phase 171 (Bots page/setup/store) replaces the D-14 stub and POSTs the
  finished PGN to the Phase 167 endpoint — the PGN with both-color `[%clk]`
  (SC5) must satisfy STORE-02's rejection rule
  (`app/services/` normalize_flawchess_game).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ChessBoard.tsx` (components/board) — interactive board with drag +
  click-to-move already required by CLAUDE.md automation rules; turn-gating
  and view-only mode (D-13) are the new requirements on top.
- `botBudget.ts` — locked budget constants; `useBotGame` builds its
  `SearchBudget` from these + `FLAWCHESS_BOT_STOP_RULE`, elo `{w,b}` symmetric.
- chess.js (already a dependency) provides all end-condition detection:
  `isCheckmate`, `isStalemate`, `isThreefoldRepetition`, `isInsufficientMaterial`,
  `isDraw` / 50-move — flag-on-time is the only loop-owned end condition.
- `useFlawChessEngine.ts` — provider bring-up (Maia queue, worker pool) and
  budget wiring to copy for the bot path; note bot play pins concurrency
  (168.5 D-09), it does NOT use device-adaptive `computePoolSize()`.

### Established Patterns
- No audio infrastructure exists anywhere in the frontend — the sound module
  (D-08..D-10) is net-new; keep it a small standalone util (e.g.
  `lib/sounds.ts`) other surfaces could reuse later.
- No clock component exists — dual-clock UI is net-new; wall-clock delta
  model per SC2 (never trust `setInterval` cadence; recompute from
  `Date.now()` on each tick; `visibilitychange` for hidden-tab pause during
  the bot's turn).
- Theme constants live in `frontend/src/lib/theme.ts` — low-time red/urgent
  styling (D-07) must come from there, not hard-coded colors.
- Minimum font size `text-sm`; every interactive element needs `data-testid`
  (`board-btn-*`, `btn-*` conventions).
- PGN `[%clk]` emission: lichess convention `{[%clk h:mm:ss]}` per move, both
  colors — STORE-02 (Phase 167, already shipped) rejects bot PGNs without it,
  so match what `normalize_flawchess_game` parses.

### Integration Points
- `useBotGame(settings)` is the seam Phase 170 (serialize state + clocks) and
  Phase 171 (setup screen supplies `settings`; on-finish PGN → POST) both
  consume — design its state shape and callbacks as the stable contract.
- `selectBotMove`'s AbortSignal is the cancellation path for resign, new game,
  and route navigation — the loop must abort in-flight thinks, not orphan them.
- D-12 Analyze CTA → `/analysis` `line` param (existing precedence
  game_id > fen > line).

</code_context>

<specifics>
## Specific Ideas

- Lichess is the explicit UX reference throughout: low-time tenths + red clock,
  familiar sound set, dismissible result dialog over the final position,
  view-only scroll-back during play, resign confirmation + draw throttle.
- The bot's clock must never look frozen during a long think — real-time
  ticking with the max(real, synthetic) reconciliation (D-05) was chosen
  specifically over freeze-and-deduct for this reason.
- The low-time warning sound fires ONCE at the threshold crossing for the
  user's clock only (D-09) — not a repeating tick.

</specifics>

<deferred>
## Deferred Ideas

- **Premove** — not in requirements (PLAY-03 is drag/click turn-gated); a new
  capability if ever wanted, its own phase/seed.
- **Bot proactively offering draws / resigning lost positions** — considered
  and rejected (D-02/D-03); revisit only if bots feel disrespectful of user
  time in long lost endings.
- **Volume slider / per-event sound settings** — D-10 ships boolean mute only.
- **TC-scaled cosmetic pacing envelope** — stays deferred per SEED-096 /
  168.5.

### Reviewed Todos (not folded)
- *Bitboard storage for partial-position queries* (score 0.2) — spurious
  keyword match, unrelated to the game loop; already reviewed and left in the
  backlog during 168.5.

</deferred>

---

*Phase: 169-clocked-board-game-loop-usebotgame*
*Context gathered: 2026-07-12*
