---
title: FlawChess bot play — clocked games against the engine, stored and analyzable (milestone-sized)
trigger_condition: Next /gsd-new-milestone selection; surfaces as a candidate milestone
planted_date: 2026-07-10
source: /gsd-explore session 2026-07-10 (Adrian's proposal + four locked design decisions)
---

# SEED-091: FlawChess bot play milestone

Let the user play clocked games against a bot powered by the FlawChess engine
(Maia+Stockfish practical-play MCTS, `useFlawChessEngine` / `mctsSearch`). Fun, challenging,
engaging — and the only ELO calibration that means anything, since the engine's real playing
strength is currently unknown (the ELO slider conditions Maia's move candidates, not Stockfish
strength, and the human↔stockfish temperature slider's strength impact is unmeasured).

## v1 scope (as proposed)

- Setup screen: ELO slider + human↔stockfish playstyle slider (reuse the analysis-board
  sliders), color choice, and a time control from the lichess presets:
  blitz 3+0, 3+2, 5+0, 5+3 · rapid 10+0, 10+5, 15+10 · classical 30+0, 30+20.
- Play button starts the game on a live board with clocks.
- Every finished bot game is stored as a `games` row and appears in the library games tab.
- Bot games are analyzable exactly like imported chess.com/lichess games.

## Locked design decisions (explore session 2026-07-10)

1. **Game lives client-side until done.** The game runs entirely in the browser (the engine
   already does). On game end, POST the finished PGN — **with `[%clk]` clock annotations**, or
   time-management stats silently exclude bot games — to a small endpoint that stores it as a
   `games` row with `platform='flawchess'`, reusing the existing normalization path. No server
   game sessions, no websockets. The platform value gives analytics inclusion/exclusion for
   free via the existing platform filter, and endgame-ELO timelines (per platform+TC) stay
   uncontaminated by construction.

2. **Move selection: the human↔stockfish slider blends sample↔argmax.** Full-human = sample
   from the temperature-reshaped Maia root policy (mistakes included; strength ≈ Maia at that
   ELO; **no MCTS needed — one Maia inference per move**, cheap enough for blitz on phones).
   Full-stockfish = argmax practical score from the search. Between = interpolate (e.g.
   practical-score-weighted sampling with slider-controlled sharpness). Both sliders keep
   their analysis-board semantics; compute cost scales with the strength setting. Rationale:
   argmax-practical is "a human who never actually makes the mistakes Maia predicts" — far
   stronger than nominal ELO and deterministic (same game every time, exploitable).
   ELO-faithfulness comes from sampling.

3. **Calibration: anchor harness in-milestone + log settings; user-results fitting deferred.**
   - Headless Node harness playing the bot against known-strength anchors (raw Maia
     1100–1900 argmax with published lichess-rating behavior; Stockfish skill levels) across
     a coarse (ELO × slider) grid → first strength map, and the engine test bench Adrian
     wants. Stockfish WASM in Node is already verified
     ([[project_headless_stockfish_wasm_verification]]); **open question: does Maia ONNX
     inference run headlessly in Node at harness-viable speed?** Pure self-play ELO without
     external anchors is unreliable — don't bother.
   - Store the bot's full settings (nominal ELO, slider value, TC) on every stored game.
   - Post-launch curve fitting (player rating vs result vs bot config) is a later milestone,
     once data volume exists.

4. **Abandonment: localStorage resume, clock paused while away.** Game state persists to
   localStorage every move; on return the user gets "Resume game?". Only finished games
   (mate/resign/flag/draw/stalemate) reach the server. Rage-quits leave no trace in v1 —
   revisit when stars arrive (e.g. abandoning after move N counts as a loss for star
   purposes).

5. **Player/bot ELO handling.**
   - The bot plays **its own ELO, symmetric** (engine's existing shared per-side
     `budget.elo`); it never adapts to player strength — adapting would also corrupt
     calibration (no fixed strength to measure).
   - **Record the player's ELO at save time, converted, not "unknown"** — every game saved
     with a NULL player rating is a calibration data point thrown away. Derive a
     lichess-scale rating matched to the bot game's TC bucket: user's lichess rating for that
     bucket if they have recent games there, else chess.com converted (the
     `useMaiaEloDefault` machinery already solves this for the slider default). NULL only
     when the user has no imported games at all.
   - Store the bot's nominal ELO in the opponent rating column ("vs FlawChess Bot (1400)").
   - Caveat to carry into any strength claims: the recorded player rating is a save-time
     *estimate*; conversion error ±100–150 per user is expected — fine for curve fitting
     across many games, not for claiming a precise bot ELO from ten games.

## Defaults flagged during the session (settle at plan time)

- **Bot think-time pacing**: instant replies feel robotic and never burn the bot's clock;
  pace the bot's move delay from its remaining time (also the search budget ceiling).
- **Clock pressure vs browser compute**: on 3+0 the bot must move in ~1–2s on the user's
  device including mid-range phones; search budget must degrade gracefully under the clock.
  Backgrounded-tab throttling while the bot is "thinking" is a real edge case.

  **Resolved 2026-07-12 (Phase 168.5):** the clock/fixed-strength fork is DECIDED as fixed
  strength + synthetic bot clock (D-01) — one global search budget maps to one calibrated ELO
  per config; the bot's search never reads the clock, and neither the pacing above nor the
  clock-pressure degradation described here happens. Instead: the displayed bot clock is
  debited a fraction-of-remaining synthetic think time (D-02), so the bot cannot flag; a small
  TC-independent randomized reveal delay floors near-instant moves so replies don't feel
  robotic (D-03); and this pacing theater is UX-only, entirely absent from the calibration
  harness (D-04b). See `.planning/phases/168.5-bot-move-pacing-search-budget-seed-096/168.5-CONTEXT.md`
  (D-01, D-02, D-03, D-04b) for the full decision record; Phase 169 SC1 is amended to match.
- **Play-UI scope control**: game-end detection (mate/stalemate/repetition/50-move/
  insufficient material), resign, flagging are required; premove, draw offers, sounds are
  candidates to cut from v1.
- Schema details: `rated` flag, opponent-type value, unique-key generation
  (user+platform+platform_game_id needs a generated game id for `platform='flawchess'`).
- Whether v1 ships beta-gated (`beta_enabled` via `useUserProfile().data`) and whether
  guests can play (guest games can't be stored).

## Future extensions (explicitly out of v1)

- Preset bot cards: one per ELO level (200-ELO steps, 600–2600) × playstyle presets
  (temperature 0.5 / 1 / 2).
- 3-star victory system per bot card (depends on the abandonment=loss revisit above).
- User-results strength calibration → relabel bots with measured ELO.
