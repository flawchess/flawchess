# Phase 223: Bot Voice & Immersive Bot Game Layout (SEED-168 + SEED-167) - Context

**Gathered:** 2026-09-15
**Status:** Ready for planning

<domain>
## Phase Boundary

The 24 Bots personas get a voice during the game and on the roster, and the game screen is
rebuilt so the voice has room:

1. **In-game bot lines**, own voice per bot, in a persistent two-line speech bubble beside
   the avatar. Lines fire only right after the bot's own move and only about what the
   board already shows (the board-truth rule); the bubble stays until the player moves.
   Triggers: game start, first capture, the bot's own check/capture that realized a big
   swing (earned tease), a big swing against the bot (split by capture: punished mistake
   vs. nice move), a visible player threat on a bot piece, the bot's draw offer (with
   accept/decline inside the bubble), and win/loss/draw.
2. **Mobile game screen** in the chess.com shape: back arrow + gear on top, avatar + bubble
   row (no bot name, style, ELO or player name), board, clock strip below the board (white
   left, black right, material beside each clock), and a fixed bottom bar replacing the
   main nav with exactly Resign / Back / Forward / Flip. Reset, user-side Offer draw and
   the sound toggle are removed. `BotDrawOfferBanner` is retired.
3. **Desktop** keeps its side column with the avatar and gains the bubble above the move
   list; the player rows become `PlayerBar` above and below the board (name + ELO left,
   clock + material right). Resign moves with the remaining controls; user-side draw
   offer and mute are removed here too.
4. **Roster page**: the "Human-like Opponents" prose card is replaced by a welcoming bot
   bubble (`TrainBotBubble`, size `large`, per-persona line) that keeps the engine info
   popover inline and the "Your estimated blitz rating" row beneath it; guests see the
   bubble without the rating row.
5. **SEED-167 folded in**: one "board sounds" switch on a settings surface, because after
   (2) and (3) no in-game mute control remains anywhere.

Out of scope (ROADMAP): per-style/per-temperament shared copy tables; timed, animated or
transient bubbles; clock-low or long-think lines; an in-game mute or settings sheet;
changing the desktop side-column structure beyond the bubble; a sketch step.

</domain>

<decisions>
## Implementation Decisions

### Swing signal & thresholds (discussed)
- **D-01:** The swing signal is the **existing post-bot-move Stockfish grade**. After every
  non-book bot move `useBotGameEngineDispatch.ts` already runs `pool.grade(fen, [uci])`
  and stores a bot-POV expected score (0-1) in `lastRootPracticalScoreRef` for the
  resign/draw gates. The realized swing is the **delta between consecutive post-bot-move
  scores** (i.e. over one move pair: player move + bot reply). No Maia WDL plumbing
  (`selectBotMove` returns only a UCI string and stays that way); no extra engine calls.
  Consequence accepted: no swing lines during the opening-book window (nothing is graded
  there) and none when a grade fails (best-effort, as today).
- **D-02:** Threshold is **large only, ~0.20 expected-score points** over the move pair
  (roughly a clean piece), a named constant (`BOT_LINE_SWING_THRESHOLD` or similar),
  tuned in UAT. Lines should fire a couple of times per game at most; every one must be
  obviously visible on the board.
- **D-03:** Swing in the bot's favor ≥ threshold → the **earned tease** line, regardless of
  whether the bot found the strongest punishment ("delta is delta"). No multi-candidate
  grading to check optimality.
- **D-04:** Swing against the bot ≥ threshold is **split by capture**: if the player's move
  in that pair captured material → the "you punished my mistake" line (self-deprecating);
  otherwise → the "nice move" compliment. Known imprecision accepted (a sacrifice in reply
  is also a capture).
- **D-05:** The **player-threat** line is detected with pure chess.js after the player's
  move: a bot piece is attacked and either undefended or attacked by a lower-value piece
  (hanging / under-defended). No engine involvement, so it can never announce something
  the board does not show. It fires after the bot's reply like every other line.

### Board-truth rule (from SEED-168, locked)
- **D-06:** A line is shown **only right after the bot's own move** and only about swings
  already cashed in on the board. Never on the player's turn, never about a player blunder
  the bot did not punish, never about the bot's own mistake before the player cashed it
  in, never about a threat the bot has prepared but not executed. The game-start line is
  pure voice (it cannot reference the position).
- **D-07:** The bubble **persists until the player's next committed move**, then clears.
  No timers, no animation. Fixed two-line height on both breakpoints; a copy test rejects
  any line that overflows two lines at the 375px bubble width (the `trainBotCopy.test.ts`
  invariant pattern).

### Copy (locked)
- **D-08:** Own voice per bot: every line table is `Record<PersonaId, string>` (or a
  per-trigger record of them) so a missing persona is a compile error, mirroring
  `LANDING_GREETINGS` in `frontend/src/lib/trainBotCopy.ts`. One variant per trigger;
  repeating a line once per game is fine. Tone: entertaining, sometimes teasing, never
  mean; the tease must read the same to an 800-rung beginner as to an 1800 player; no
  em-dashes; the `HumanLikeOpponentsCard` accuracy rule holds (16 of 24 personas never
  search, so no line may claim the bot "calculated" or "saw it coming").
  — **Reversibility:** costly — ~200+ authored lines across 24 personas; changing the
  table shape touches every entry.
- **D-09:** Copy authored in the plan is a **starting point**: messages, tone and the
  board-truth constraints are locked; the executor may tighten wording within them.

### Layout (locked from SEED-168; details are Claude's discretion below)
- **D-10:** Mobile: header already suppressed via `useMarkPlayActive`; the bottom nav is
  replaced through the existing `usePublishMobileBoardControls` seam
  (`frontend/src/lib/mobileBoardControls.ts`), extended with a Resign action and without
  Reset. Exactly four actions: Resign, Back, Forward, Flip. Resign keeps its confirm
  dialog.
- **D-11:** Mobile shows no bot name/style/ELO and no player name; desktop shows both
  players via `PlayerBar` (name + ELO left, clock + material right). Bot ELO on desktop is
  the persona's `calibratedLabel`; the user's is `profile.current_strength.rating`
  (rounded, tilde-prefixed like the roster row) or omitted when null (guests).
- **D-12:** The bot's draw offer (Phase 183 D-07, `botDrawOffer`) renders inside the bubble
  with Accept / Decline buttons; `BotDrawOfferBanner` is deleted. The user-side Offer draw
  button and its cooldown UI are removed; `offerDraw` stays in the hook for now (dead
  wiring may be pruned if trivially safe).
- **D-13:** Roster page: the welcome bubble replaces the sentence in
  `HumanLikeOpponentsCard`; the `InfoPopover` engine explainer stays as an inline trigger
  at the end of the bubble copy (Train landing pattern); the estimated-rating row keeps its
  own `InfoPopover` and its `currentStrength !== null` gate.

### Claude's Discretion
The three undiscussed gray areas. Recommendations below are the defaults the planner
should take unless the user edits this file.

- **Trigger priority & pacing.** One line per bot move, priority order: game end >
  draw offer > swing (either direction) > player threat > first capture > game start.
  First capture and game start fire once per game; swing/threat lines can repeat but with
  a minimum spacing of 3 bot moves between any two non-terminal lines so the bot is not
  chatty at low rungs. Game-end line: show it in the bubble AND keep `GameResultDialog`;
  the dialog already waits on `celebrationHold`, so the line is visible during the hold
  and stays behind the dialog afterwards (no new timing logic).
- **Sound switch home & the gear.** No settings page exists. Recommended home: a
  "Board sounds" switch in the **mobile More drawer** (`MobileMoreDrawer`, under the
  account header) and the **desktop header's account area** (next to Logout), both bound
  to the existing `useMuted`/`setMuted` in `frontend/src/lib/sounds.ts`. No new route.
  The top-right gear on the mobile game screen is therefore **dropped** (an icon with no
  sheet behind it is worse than no icon); the top bar holds only the back arrow. If the
  user prefers a gear, it should open the More drawer, not a new sheet.
- **Roster host & greeting tables.** Recommended: the roster host is Train's
  `landingHost` rotation (same bot greets on /train and /bots that day; reuse
  `LANDING_ROTATION_EPOCH` and the day index, but never the Train-specific
  `introSeenAt`/`sessionDate` gates: fall back to a plain day-index rotation with no Tank
  pin on the roster). Two separate tables: `ROSTER_GREETINGS` (welcome, may mention
  "pick an opponent") and `GAME_START_LINES` (in-game hello), since the surfaces read
  differently.
- Back arrow on mobile: navigates to the roster; a live game stays in the existing
  pending store (`botPendingStore.ts`) and `ResumeGate` handles the return, no new
  resign-on-leave logic unless research finds the pending store does not cover it.
- Avatar size constants, bubble tail/border (reuse `TRAIN_BUBBLE_BORDER`), clock strip
  layout, PlayerBar clock source (`whiteClockMs`/`blackClockMs` in seconds), test
  strategy for the trigger resolver (pure module with fabricated score sequences).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and locked design
- `.planning/seeds/SEED-168-bot-voice-and-immersive-bot-game-layout.md` — the full
  locked design: voice, board-truth rule, trigger set, bubble behavior, mobile/desktop
  layouts, roster bubble, open questions (now resolved above).
- `.planning/seeds/SEED-167-train-sound-toggle-rehoming.md` — why the mute toggle needs a
  settings-surface home and why it must ship with this phase.
- `.planning/ROADMAP.md` §"Phase 223" — goal (A–E), success criteria 1–7, out-of-scope
  list, cross-cutting constraints.

### Precedent (Phase 222, the Train bot bubble)
- `.planning/milestones/v2.19-phases/222-train-bot-narrated-onboarding-and-verdicts/222-CONTEXT.md`
  — D-06 (per-outcome copy on Train; this phase is the explicit per-persona exception),
  D-07 (one persistent chat-row slot, no layout jump), D-21 tone rules, temperament
  mapping.
- `frontend/src/lib/trainBotCopy.ts` — `LANDING_GREETINGS` (the per-persona table shape
  to mirror), `landingHost` (daily rotation), `HILDA_ID`/`TANK_ID`.

### Frontend rules
- `frontend/CLAUDE.md` — testids on every interactive element, `text-sm` floor, Button
  variants, no Umami for DB-known facts, complexity gate 15 for new code.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/components/train/TrainBotBubble.tsx` — the shared avatar + bubble row
  (sizes `default`/`large`, `state`, `nudgeNonce`, children for buttons). Use it for the
  roster welcome as-is; the in-game bubble needs a fixed two-line height and a compact
  mobile variant, so either a size/variant prop or a sibling `BotGameBubble` that shares
  its tokens (`TRAIN_BUBBLE_BORDER` in `frontend/src/lib/theme.ts`).
- `frontend/src/hooks/useBotGameEngineDispatch.ts` ~L455-505 — the post-bot-move
  `pool.grade()` continuation with `lastRootPracticalScoreRef`, `evalToExpectedScore`,
  the resign/draw-offer updates and the `controller.signal.aborted` staleness guard. The
  swing detector hooks in here (or consumes the score via a new field on
  `UseBotGameState`), never with a second grade call.
- `frontend/src/hooks/useBotGame.ts` `UseBotGameState` — `moveHistory`, `lastMove`,
  `liveGamePly`, `botDrawOffer`/`acceptBotDraw`/`declineBotDraw`, `outcome`, `resign`,
  `viewPly`/`returnToLive`: everything the bubble state machine and the bottom bar need.
- `frontend/src/lib/mobileBoardControls.ts` — `usePublishMobileBoardControls` +
  `MobileBoardControls` (Back/Forward/Reset/Flip today); `App.tsx` `MobileBottomBar`
  swaps the nav when a payload is published. Extend the payload with an optional
  `onResign` and make Reset optional.
- `frontend/src/lib/playActive.ts` `useMarkPlayActive` — already suppresses the mobile
  header for the bot game.
- `frontend/src/components/board/PlayerBar.tsx` — name/rating/clock/material row from
  the analysis board (`clockSeconds`, `fen`, `rightSlotContent`).
- `frontend/src/components/bots/ClockDisplay.tsx` — current avatar + name + material +
  clock row; its `MaterialDisplay` usage moves to the clock strip / PlayerBar.
- `frontend/src/components/bots/GameControls.tsx` — Resign confirm dialog (keep), Offer
  draw + mute (remove).
- `frontend/src/components/bots/PersonaGrid.tsx` `HumanLikeOpponentsCard` — the card to
  replace; keep its `InfoPopover` content and the rating row verbatim.
- `frontend/src/lib/sounds.ts` — `useMuted`/`setMuted`/`MUTE_KEY` (flat localStorage
  preference); the settings switch binds to these.
- `frontend/src/lib/personas/personaRegistry.ts` — `PERSONA_REGISTRY`, `PersonaId`,
  `calibratedLabel`, `temperament`; `personaAvatars.ts` for art.
- chess.js (`Chess`) for the first-capture flag (`move.captured`), the threat check
  (`attackers`/`isAttacked`-style probes after the player's move) and piece values.

### Established Patterns
- Copy and state live in pure `lib/` modules (`trainBotCopy.ts`, `trainBubbleState.ts`):
  the trigger resolver is a pure function of (previous score, new score, move pair facts,
  game phase) → line key, unit-tested with fabricated sequences. `Bots.tsx` (819 lines),
  `useBotGame.ts` (816) and `useBotGameEngineDispatch.ts` (557) are already large: add
  new modules, not branches.
- Layout in `Bots.tsx` is two pure render helpers (`renderMobileLayout`,
  `renderDesktopLayout`) fed pre-built elements; the rework replaces those helpers.
- `pb-20 sm:pb-4` bottom-nav clearance on the page root goes away on mobile once the bar
  is the page's own.
- Every interactive element carries a `data-testid`; existing ones (`clock-bot`,
  `clock-user`, `bots-intro-card`, `bots-player-rating`) have tests that will need
  updating when the elements move.

### Integration Points
- `Bots.tsx` game view (both render helpers, the draw-offer banner slot, the controls
  row), `PersonaGrid.tsx` intro card, `App.tsx` `MobileBottomBar` + `MobileMoreDrawer` +
  desktop header account area (sound switch), `mobileBoardControls.ts` payload shape,
  `useBotGameEngineDispatch.ts` grade continuation (swing signal out), `trainBotCopy.ts`
  or a new `botGameCopy.ts` (tables), `CHANGELOG.md` `[Unreleased]`.

</code_context>

<specifics>
## Specific Ideas

- The chess.com bot screen is the visual reference for mobile: back arrow top-left,
  avatar with a wide speech bubble directly above the board, clocks under the board,
  a move strip, then a four-item labelled action bar (Options / Resign / Hint / Undo
  there; Resign / Back / Forward / Flip here). Not a pixel spec; adapt to the app's
  tokens.
- Example lines from the exploration: earned tease "That knight was hanging for a whole
  move, you know."; bot-loses "Well. I'd like that one back."
- The existing Train landing bubble (Fury: "Show me a weakness and I'll tear into it.
  Today's weaknesses come from your own games.") is the register for the roster welcome.

</specifics>

<deferred>
## Deferred Ideas

- A real `/settings` page (account, sounds, Train schedule in one place). This phase puts
  the sound switch in the existing account surfaces; a settings page is its own phase if
  more preferences accumulate.
- Maia-WDL-flavoured lines ("a human at your level misses that"): rejected for this phase
  in favour of the existing Stockfish signal; revisit only if the lines feel generic.

### Reviewed Todos (not folded)
- "WR-01 — pt-33 is not a valid Tailwind class on the Score Y-axis label" (matched on
  "frontend" only; Train score chart, unrelated).
- "172-deferred-review-findings", "variation-tree-nested-button", "bitboard storage":
  keyword matches only, unrelated.

</deferred>

---

*Phase: 223-bot-voice-immersive-bot-game-layout-seed-168-seed-167*
*Context gathered: 2026-09-15*
