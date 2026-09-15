---
id: SEED-168
status: promoted → Phase 223 (2026-09-15)
planted: 2026-09-15
planted_during: /gsd-explore "bots page welcome avatars + in-game trash-talk" (follow-on to Phase 222's bot-narrated Train onboarding, shipped v2.19)
trigger_when: next Bots window; phase-sized (copy authoring + layout rework on both breakpoints + swing detection); promote as ONE phase, the layout rework and the voice lines share the same bubble slot and should not ship separately
scope: (A) per-persona in-game bot lines in a persistent speech bubble, (B) the mobile bot game screen rebuilt in the chess.com shape (bubble row, clock strip, fixed action bar), (C) desktop gains the bubble in its side column and PlayerBar rows, (D) the Bots roster page's intro card replaced by a welcoming bot bubble
---

# SEED-168: Bots talk during the game, and the game screen makes room for it

## Why

Phase 222 gave the bots a voice on Train (intro stepper, landing greeting, per-outcome
verdicts) and the landing greeting is per-persona, in each bot's own voice. The Bots page
still introduces the same 24 characters with a bland prose card ("These bots are driven
by the FlawChess Engine and play like human players...") and the game itself is silent.
The characters are the product's most shareable asset; let them carry the Bots surface
the way they now carry Train.

## Locked decisions (2026-09-15)

### Voice

- **Per-persona lines, own voice per bot** (owner's call: "that's what makes it fun").
  Same shape as `LANDING_GREETINGS` in `frontend/src/lib/trainBotCopy.ts`: a
  `Record<PersonaId, ...>` so a missing bot is a compile error. One variant per trigger
  is enough; games are short and a repeated line once per game is fine. Budget: roughly
  8-10 lines per bot, ~200-240 authored lines total (comparable to the 24 bios plus
  greetings already written).
- **Tone rule** (inherited from SEED-166 / Phase 222): entertaining, sometimes teasing,
  never mean. The tease must read the same for an 800-rung beginner who just hung a queen
  as for an 1800 player. Self-deprecating lines when the bot's own mistake gets punished
  are what keep the teasing fair.

### The board-truth rule (settles the two giveaway problems)

The bot only talks about what the board already shows, never about what the engine knows.
It speaks **only right after its own move**, and only about swings that have been cashed in.

- **Player blunders:** silence until the bot actually plays the punishing move. Then the
  tease fires and it is earned. If the bot misses the punishment (the 800-1400 rungs run a
  single Maia policy call and often will), nothing fires; consistent with the human-like
  premise, the bot did not see it either.
- **Bot blunders:** silence until the player cashes it in. After the bot's *next* move,
  the self-deprecating line. No giveaway: the piece is already gone. If the player misses
  it, the chance passes silently, as against a human.
- **Threats and attacks** (added 2026-09-15): the bot may comment on a threat the
  *player* made (visible on the board, the player already knows) and on its own check or
  capture (already played). It must never comment on a threat it has set up but not yet
  executed ("something is coming for your king") because that is engine knowledge leaking.
- **Game start** line cannot reference the position: pure voice.

### Trigger set

Cheapest-first, all detectable client-side today:

1. Game start (the bot's first move). May double as the roster welcome line or be separate.
2. First capture in the game (either side).
3. Bot delivers check / makes a capture that realizes a swing (the earned tease).
4. Player's move realized a swing against the bot (self-deprecating, after the bot's next move).
5. Player is attacking / threatening the bot (visible threat on a bot piece after the player's move).
6. Bot draw offer (Phase 183 D-07) moves INTO the bubble with accept/decline; `BotDrawOfferBanner` goes away.
7. Game end: win / loss / draw, one line each.

Swing detection uses the **WDL delta across the ply pair that realized it**, not raw
material. Material alone misfires on Attacker sacrifices (the bot gives a piece on purpose
and would then apologize for it). The Maia worker returns `wdlByElo` on every call for all
24 personas (`frontend/src/lib/engine/maiaWorkerHost.ts`), so the signal exists at every
rung; the Light/Deep rungs additionally have the Stockfish grade `evalCp`, which is more
reliable for sacs. Threshold is a named constant, tuned in UAT.

### Bubble behavior

- The bubble **persists until the player makes a move**, then clears (no timer, no
  animation). Sitting there during the player's think is less distracting than a toast.
- **Fixed two-line height**, never resizes. Every authored line must fit two lines at the
  mobile width; enforce in the copy test like `trainBotCopy.test.ts` enforces the
  greeting invariant.
- Idle state (no active line): the slot shows nothing, or the draw-offer controls when one
  is live.

### Mobile game screen (chess.com shape; the header is already suppressed via `useMarkPlayActive`)

- Top: back arrow left (returns to the roster; the existing resign confirm if the game is
  live), gear right. No logo, no page title.
- Bot row: avatar (56-64px, own size constant like `TRAIN_BOT_AVATAR_CLASS`) with the
  two-line bubble beside it. **No bot name, no playstyle, no ELO** (the roster card did that
  job). No player name either.
- Board.
- Clock strip below the board: white on the left, black on the right, material difference
  beside each clock as `ClockDisplay` shows it today.
- Fixed bottom bar replaces the main nav, via the existing
  `usePublishMobileBoardControls` seam (`frontend/src/lib/mobileBoardControls.ts`, used by
  Train free-move), extended for game actions: **Resign, Back, Forward, Flip**. Removed:
  Reset, Offer draw (user side), sound toggle. This deletes both 48px control rows and the
  `pb-20` nav clearance; roughly 130px back to the board.
- The sound toggle's new home is SEED-167 (amended to cover the bots game).

### Desktop

- Keeps its side column with the avatar; add the two-line bubble above the move list.
- Player rows use `PlayerBar` (`frontend/src/components/board/PlayerBar.tsx`) above and
  below the board exactly as on the analysis board: name and ELO on the left, clock (and
  material) on the right. Names and ELO DO show on desktop; the removal is mobile-only.
- Resign moves with the other controls; user-side draw offer and mute are removed here too.

### Bots roster page

- Replace `HumanLikeOpponentsCard`'s prose sentence (`PersonaGrid.tsx`) with a welcoming
  bot bubble, `TrainBotBubble` size `large`, per-persona `Record<PersonaId, string>` like
  `LANDING_GREETINGS`.
- Two things in that card are load-bearing and must survive: the engine info popover
  (the non-technical "human move prediction, not a weakened engine" explainer, with its
  copy-accuracy constraint that 16 of 24 personas never search) stays as an inline trigger
  in the bubble the way Train does it; the "Your estimated blitz rating ~N" line stays as a
  small row under the bubble (it is the reference users need to pick a rung).
- Guests still see the bubble; only the rating row is gated on `currentStrength`.

## Open questions

- Roster host rotation: the same daily host as Train's `landingHost` (users meet the same
  bot on both pages that day) or its own rotation. Not decided.
- Whether the game-start line and the roster welcome line are one table or two.
- Swing threshold value; whether the 1600/1800 rungs should use `evalCp` instead of WDL.

## Out of scope / decided against

- Per-style or per-temperament shared copy tables (Train's D-06 shape). Decided against
  for this surface: own voice per bot.
- Transient / timed / animated bubbles.
- Lines that reference engine knowledge not yet on the board (see board-truth rule).
- Clock-low or long-think lines: not requested; they would fire during the player's turn,
  which the board-truth rule forbids anyway.
- An in-game mute or settings sheet; see SEED-167.
- Changing the desktop side-column structure beyond adding the bubble.
- Sketch/mockup step before planning (owner declined 2026-09-15).
