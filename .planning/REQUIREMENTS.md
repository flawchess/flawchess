# Requirements: FlawChess — v2.3 Bot Play

**Defined:** 2026-07-11
**Core Value:** Position-precise WDL across openings + endgames + time pressure on top of users' actual chess.com / lichess games, with personalized LLM commentary and an auto-generated opening-strengths/weaknesses report.

**Milestone goal:** Let users play clocked games against the FlawChess engine on a new top-level **Bots** page; store every finished game as an analyzable Library game; and build a headless anchor-calibration harness that first measures the engine's real playing strength. Sourced from SEED-091 (five locked design decisions) + the 2026-07-11 milestone-scoping decisions.

## v1 Requirements

Requirements for this milestone. Each maps to a roadmap phase.

### Bot Opponent (BOT)

- [ ] **BOT-01**: The bot chooses its move by blending the play-style slider from sampling the temperature-reshaped Maia root policy at the full-human end to argmax practical score at the full-stockfish end (practical-score-weighted sampling with slider-controlled sharpness in between).
- [ ] **BOT-02**: At the full-human end the bot runs exactly one Maia inference per move (no MCTS pass), so it can reply within ~1–2s on a mid-range phone at the fastest supported time control.
- [ ] **BOT-03**: The bot plays its own configured ELO symmetrically and never adapts to the player's strength (so its strength stays fixed and measurable).
- [ ] **BOT-04**: The bot always returns a legal move, falling back gracefully to a legal move when the sampled policy is empty or degenerate.

### Play Experience (PLAY)

- [ ] **PLAY-01**: Bot play lives on a new top-level **Bots** page (nav sibling of Library · Openings · Endgames), lazy-loaded.
- [ ] **PLAY-02**: User can start a new game from a setup screen choosing ELO, play-style, color, and a lichess-preset time control (blitz 3+0/3+2/5+0/5+3 · rapid 10+0/10+5/15+10 · classical 30+0/30+20; no bullet).
- [ ] **PLAY-03**: User plays on a live board with dual clocks counting down with Fischer increment, moving by drag or click-to-move, turn-gated to legal moves.
- [ ] **PLAY-04**: Clocks stay accurate across tab backgrounding (wall-clock delta model) and pause when the tab is hidden while the bot is thinking, so neither side is unfairly flagged.
- [ ] **PLAY-05**: The bot paces its replies (not instant) with a think-time budget derived from its remaining clock (best-effort; degrades gracefully under time pressure).
- [ ] **PLAY-06**: The game detects all end conditions — checkmate, stalemate, threefold repetition, 50-move, insufficient material — plus flag-on-time.
- [ ] **PLAY-07**: User can resign, and can offer/accept a draw against the bot.
- [ ] **PLAY-08**: User hears move / capture / check / game-end sounds, with a mute control.
- [ ] **PLAY-09**: On game end, a result screen shows the outcome (win/loss/draw + reason) with "Analyze this game" and "New game" actions.
- [ ] **PLAY-10**: Both logged-in users and guests can play bot games and have their finished games saved.

### Game Storage (STORE)

- [ ] **STORE-01**: Every finished bot game is stored as a `platform='flawchess'` `games` row via the shared normalization/persistence path (a new PGN→`NormalizedGame` normalizer feeding the existing downstream) and appears in the Library games tab.
- [ ] **STORE-02**: The stored PGN carries per-move `[%clk]` clock annotations (both colors), so time-management analytics include bot games; the store endpoint rejects a bot PGN missing `[%clk]`.
- [ ] **STORE-03**: The stored game records a save-time converted (lichess-scale, TC-bucket-matched) player rating — NULL only when the user has no imported games — plus the bot's nominal ELO in the opponent-rating column, with the rating source recorded.
- [ ] **STORE-04**: The stored game records the full bot settings (nominal ELO, play-style slider value, TC preset) for later calibration.
- [ ] **STORE-05**: The store endpoint mints/accepts a client-owned game UUID as `platform_game_id` and is idempotent on the unique constraint (a duplicate submit returns success without a second row).
- [ ] **STORE-06**: Stored bot games are analyzable exactly like imported games; guests see a caveat that their bot games are saved but won't be auto-analyzed until they create an account (existing guest eval-exclusion).
- [ ] **STORE-07**: Bot games are excluded from default analytics (Global Stats, endgame-ELO timelines) but included in the Bots and Library Games surfaces, consistent with the existing platform/opponent filter.

### Resume (RESUME)

- [ ] **RESUME-01**: User can leave a bot game mid-play and resume it later via a "Resume game?" prompt, with the clock paused while away (persisted to localStorage every move).
- [ ] **RESUME-02**: Only finished games reach the server; an abandoned (unfinished) game leaves no server trace, and a game already stored is never double-stored on resume.

### Calibration (CAL)

- [ ] **CAL-01**: A headless Node harness plays the bot against known-strength anchors (raw Maia argmax rungs 1100–1900 + Stockfish skill levels) across a coarse (ELO × play-style) grid and emits a strength map as TSV in `reports/data/`.
- [ ] **CAL-02**: The harness reuses the exact same provider-agnostic `selectBotMove` move-selection code the app uses (via the `@/` alias hook), so the measured strength reflects the code users actually play against.
- [ ] **CAL-03**: A feasibility spike confirms Maia ONNX inference runs headlessly in Node at harness-viable throughput (and locks the `onnxruntime-node` version) before the full grid is built.

## v2 Requirements

Deferred to a future milestone. Tracked, not in this roadmap.

### Bot Presets & Progression

- **BOTX-01**: Preset bot character cards (one per 200-ELO step 600–2600 × play-style presets).
- **BOTX-02**: 3-star victory system per bot card (depends on abandonment-as-loss accounting).

### Strength Calibration from Real Play

- **CALX-01**: Post-launch curve fitting (player rating vs result vs bot config) over stored bot games to relabel bots with measured ELO.
- **CALX-02**: Rage-quit / abandonment accounting (e.g. abandoning after move N counts as a loss for star purposes) — needs server-side in-progress tracking.

## Out of Scope

Explicitly excluded from v1. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Premove | Cut from v1 (2026-07-11 decision) — non-trivial board-state handling, low value for a first cut. |
| Takeback | Cut from v1 — complicates clock/PGN accounting and corrupts calibration integrity. |
| Hints / live eval bar during play / opening book for the bot | Training aids that corrupt the game as an honest strength measurement; deliberately stripped. |
| Adaptive difficulty | The bot must play a fixed symmetric ELO; adapting would corrupt calibration. |
| Bullet time controls | Excluded by design so slower devices get client-side compute headroom. |
| Server-side game sessions / websockets | Game runs entirely client-side until finished (locked decision 1); only the finished PGN is POSTed. |
| Rematch button, low-time warnings, bot resignation in dead positions | Polish, deferred to v1.x. |
| User-results ELO curve fitting | Deferred to a later milestone once stored-game volume exists (locked decision 3). |

## Traceability

Which phases cover which requirements. Filled during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| BOT-01 | — | Pending |
| BOT-02 | — | Pending |
| BOT-03 | — | Pending |
| BOT-04 | — | Pending |
| PLAY-01 | — | Pending |
| PLAY-02 | — | Pending |
| PLAY-03 | — | Pending |
| PLAY-04 | — | Pending |
| PLAY-05 | — | Pending |
| PLAY-06 | — | Pending |
| PLAY-07 | — | Pending |
| PLAY-08 | — | Pending |
| PLAY-09 | — | Pending |
| PLAY-10 | — | Pending |
| STORE-01 | — | Pending |
| STORE-02 | — | Pending |
| STORE-03 | — | Pending |
| STORE-04 | — | Pending |
| STORE-05 | — | Pending |
| STORE-06 | — | Pending |
| STORE-07 | — | Pending |
| RESUME-01 | — | Pending |
| RESUME-02 | — | Pending |
| CAL-01 | — | Pending |
| CAL-02 | — | Pending |
| CAL-03 | — | Pending |
