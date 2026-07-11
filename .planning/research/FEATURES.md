# Feature Research

**Domain:** "Play against a bot / computer" for a chess web app (FlawChess v2.3 Bot Play)
**Researched:** 2026-07-11
**Confidence:** HIGH (well-trodden UX on lichess/chess.com; scope tightly locked in SEED-091 + PROJECT.md)

> Scope note: this is a **subsequent milestone** adding clocked bot-play to an existing analysis app. The engine (`useFlawChessEngine` / `mctsSearch` + Maia inference), the `/analysis` board with ELO + play-style sliders, the Library games surface, and the import normalization path already exist. Research here is about the **play-a-game feature set** layered on top, not about the engine or analysis. v1 IN/OUT boundaries are locked: draw offers + move sounds IN; premove + takeback OUT.

---

## How lichess & chess.com actually do "play the computer"

Grounding for the categorization below:

- **lichess "Play with the computer"** — a setup dialog: pick Stockfish **level 1–8** (mapped to a rough Elo, ~400 up to full strength), **side** (white / black / random), and a **time control** (including "unlimited"/correspondence). The game is a normal board with clocks (if a real TC is chosen), resign, and an offer-draw affordance. Crucially, **the computer game is not a rated server game with a hard enforced running clock** the way human games are — it lives largely client-side and you can leave and come back. At game end you get the result and an "analysis board" link.
- **chess.com "Play Bots"** — a richer setup: bot **character cards** (avatar + nominal rating), difficulty, side, and options. In-game it exposes analyze / hint / takeback (some behind membership). At game-over a result modal with **Rematch / New Bot / Review (analyze)**. Coach modes are typically untimed; timed modes exist.
- **Common to both:** the "vs computer" experience is deliberately lower-stakes than rated human play — no anti-cheat, forgiving abandonment, take-backs/hints as training aids.

FlawChess's twist: the "bot" is the **FlawChess practical-play engine** (Maia-conditioned, ELO-sliderable, symmetric — never adapts to the player), and every finished game is **stored as a real analyzable Library game** feeding the same WDL / endgame / time-management analytics as imported games. That storage-as-first-class-game is the differentiator; the play UI itself is table-stakes. FlawChess deliberately **strips the training aids** (no hints/takeback/eval) precisely because the point is an honest, calibration-grade measurement of the engine's strength.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Missing any of these makes the bot mode feel broken or unfinished.

| Feature | Why Expected | Complexity | Notes / Dependencies |
|---------|--------------|------------|----------------------|
| **Setup: strength (ELO slider)** | Every "play computer" flow leads with difficulty | LOW | Reuse the existing `/analysis` ELO slider verbatim → engine `budget.elo`. |
| **Setup: color choice (white / black / random)** | Universal on lichess & chess.com | LOW | Trivial state; "random" picks a side on Play. Sets who moves first + board orientation. |
| **Setup: time-control presets** | Clocked play needs a TC; presets are the norm | LOW | Locked list: blitz 3+0/3+2/5+0/5+3 · rapid 10+0/10+5/15+10 · classical 30+0/30+20. **Bullet excluded by design** (client compute headroom). Preset → `{base_seconds, increment_seconds}`; also drives the saved game's TC bucket + player-rating conversion. |
| **Setup: play-style knob** | Already a first-class engine control here | LOW | Reuse the human↔stockfish play-style slider. Blends sample↔argmax move selection (locked decision #2). Novel vs lichess/chess.com but table-stakes *for this app*. |
| **Play → live clocked board** | The core action | MEDIUM | react-chessboard + chess.js loop with the engine driving bot moves. Client-side only. |
| **Two clocks counting down with increment** | Defines "clocked game" | MEDIUM | Fischer increment: decrement mover's clock while thinking, add increment after the move. Needs wall-clock-delta timing (not naive `setInterval` accumulation, which drifts and dies in backgrounded tabs). |
| **Whose-move indication** | Users must know if it's their turn | LOW | Active-clock highlight + input gating (can't move on bot's turn). |
| **Legal-move enforcement + click & drag input** | A board allowing illegal moves is broken | LOW | chess.js validation; both drag-drop and click-to-click required project-wide (mobile). Reuse board input from `/analysis`. |
| **Bot "thinking" affordance** | Instant replies feel robotic / broken | LOW–MEDIUM | Subtle indicator on the bot's side/clock. Pairs with pacing (below). |
| **Human-like think-time pacing (not instant)** | Instant moves feel wrong AND never burn the bot's clock | MEDIUM | Pace bot delay from its remaining clock; also caps the search budget. Best-effort per seed (perf tuning is polish, not a blocker). Must keep 3+0 playable on mid-range phones (~1–2s/move) and degrade gracefully. |
| **Move sounds** | Standard on both platforms; **confirmed IN** | LOW | Move / capture / check / game-end sounds + mute toggle. Respect browser autoplay (first interaction unlocks audio). Frontend-only. |
| **Resign** | Table-stakes everywhere | LOW | Ends game as a loss for the resigner → game-end. |
| **Flagging (loss on time)** | A clock that can't expire isn't a clock | MEDIUM | Clock hits 0 → loss on time, with the standard "opponent has insufficient mating material → draw" exception. Must fire even after a backgrounded tab (reconcile on focus via wall-clock delta). |
| **Full game-end detection** | Games must end correctly | MEDIUM | Mate, stalemate, threefold repetition, fifty-move, insufficient material — all from chess.js. Plus resign, flag, draw-agreed. |
| **End-of-game result screen** | Users expect a clear result + next actions | LOW–MEDIUM | Result (win/loss/draw) + reason (checkmate / resignation / time / stalemate / agreement / repetition / 50-move / insufficient material), **"Analyze this game"** (deep-link into existing analysis/Library), **"New game"**. |
| **Draw offers** | **Confirmed IN**; standard clocked-game control | MEDIUM | Human offers → bot accept/decline policy (simple: accept when its practical eval is ~level/losing, else decline). Threefold/50-move remain automatic, distinct from agreed draws. Bot-initiated offers optional (keep simple). |
| **PGN capture with per-move clock (`[%clk]`)** | Without it, time-management analytics silently exclude bot games (locked decision #1) | MEDIUM | Emit standard PGN with `[%clk H:MM:SS]` after each move — exactly the lichess/chess.com format the existing normalization + clock parser expects. Load-bearing, not cosmetic. |
| **Persist finished game to server** | The whole point: bot games become analyzable Library games | MEDIUM | POST finished PGN → `games` row, `platform='flawchess'`, via existing normalization. Depends on synthetic `platform_game_id`, `rated` + opponent-type values, player-rating conversion. |
| **localStorage resume (clock paused while away)** | Users close tabs mid-game; losing a casual bot game feels punishing | MEDIUM | Persist game state (FEN/PGN + clocks + config) every move. On return: "Resume game?". Clock **paused while away** (matches lichess computer games). Only finished games reach the server; rage-quits leave no trace in v1. |
| **Board orientation follows chosen color** | Playing black should flip the board | LOW | Reuse board flip from `/analysis`. |

### Differentiators (Competitive Advantage)

Where FlawChess's bot mode is more than a generic "play the computer."

| Feature | Value Proposition | Complexity | Notes / Dependencies |
|---------|-------------------|------------|----------------------|
| **Finished games become first-class analyzable Library games** | Play → immediately get WDL / mistake tags / endgame + time analytics on your bot games, same as imports | MEDIUM | Enabled by `platform='flawchess'` + normalization reuse. Nothing on lichess/chess.com folds bot games into a personal analytics corpus this way. Guest caveat: eval pipeline excludes guests, so a guest bot game shows in Library but won't auto-analyze until promotion. |
| **Practical-play engine as opponent (Maia-conditioned, ELO + play-style)** | The bot plays *human-like* lines at a chosen rating, not a nerfed Stockfish playing alien moves | MEDIUM | Reuses v2.0 engine + v1.32 Maia infra. Sample↔argmax blend from the play-style slider (locked decision #2). Symmetric — bot plays its own ELO, never adapts (adapting corrupts calibration). |
| **`[%clk]`-annotated PGN → time-management analytics on synthetic games** | Bot games contribute to clock-advantage / flag-rate / time-pressure stats | MEDIUM | Direct consequence of clock capture + the platform filter. Real-import timelines stay clean by construction (opt-in/out via platform filter). |
| **Save-time converted player rating on every game** | Every game is a calibration data point (player Elo vs result vs bot config), not a thrown-away NULL | MEDIUM | Reuse `useMaiaEloDefault` conversion. Store player rating (lichess-scale, TC-bucket-matched; chess.com converted fallback; NULL only when no imported games) + bot nominal ELO in opponent-rating column + full bot settings (ELO/slider/TC). Substrate for deferred user-results curve fitting. |
| **Headless anchor-calibration harness (engine test bench)** | First real (ELO × play-style) strength map for the engine; a reusable bench | HIGH | Node harness: bot vs known-strength anchors (raw Maia 1100–1900 argmax; Stockfish skill levels) over a coarse grid. Stockfish-WASM-in-Node verified; **open feasibility item: Maia ONNX headless in Node at harness-viable speed.** Committed in-milestone; independent of the play UI. |

### Anti-Features (Commonly Requested, Often Problematic — AVOID in v1)

Documenting to prevent scope creep. Several are *especially* wrong here because they corrupt the calibration signal or add server/state complexity the "client-side until done" architecture deliberately avoids.

| Feature | Why Requested | Why Problematic (here) | Alternative |
|---------|---------------|------------------------|-------------|
| **Takeback / undo move** | Common training aid on chess.com bot mode | **Already cut.** Corrupts the game as a strength measurement; recorded result no longer reflects real play. Adds fiddly clock-rewind state. | Play it out; analyze afterward in the Library. |
| **Premove** | Speeds up blitz on human platforms | **Already cut.** Real value only vs a live server clock racing an opponent; here the clock pauses on the bot's turn anyway. Adds input-queue + validation complexity. | Move on your turn; bot pacing keeps the game flowing. |
| **Hints / best-move suggestions** | "Help me not blunder" | Destroys calibration (result no longer reflects the player's true strength) and turns a game into a tutor. That engine already lives on `/analysis`. | Point users to `/analysis` for training; keep bot play honest. |
| **Live engine eval / win-bar during play** | Chess.com/lichess show an eval bar in some modes | Same calibration problem + a crutch that changes how people play + extra on-device Stockfish compute during a timed game. | Full eval graph is available *after* the game via Library analysis. |
| **Opening book / forced book moves for the bot** | "Bot plays weird openings" | Maia's policy already produces human-like openings at the chosen ELO; a bolted-on book breaks the "plays its own strength, symmetric" property and the calibration. | Trust the Maia policy — it's the point. |
| **In-game chat / bot trash-talk / personas** | chess.com character bots are fun | Pure scope creep; no calibration or analytics value; copy/asset/state work. | Deferred — see "preset bot cards" in future extensions. |
| **Rematch that re-runs identical config** | chess.com has a Rematch button | Minor, but "New game" already returns to setup with settings retained; a dedicated rematch button is redundant in v1 (not harmful, just not needed). | "New game" preserves last settings; add explicit Rematch later if wanted. |
| **Rage-quit / abandonment counts as a loss** | Fair for a competitive ladder | Requires server-side tracking of in-progress games — directly contradicts "client-side until done, only finished games reach the server." Tied to the future star/victory system. | v1: rage-quits leave no trace. Revisit with the deferred 3-star system. |
| **Server-enforced running clock / websockets / live sessions** | "Real" online-game fidelity | Massive infra for zero benefit; it's single-player-vs-local-engine. Clock pausing while away is correct/expected for computer games. | Client-side clock + localStorage resume + one store-on-finish endpoint. |
| **Adaptive difficulty (bot matches your level)** | Feels friendlier | **Corrupts calibration** — no fixed strength to measure. Explicitly rejected (locked decision #5). | Fixed symmetric ELO the user chooses. |
| **Rated ladder / bot Elo affecting a user rating** | Gamification | No rating system exists for bot play; premature. Recorded player rating is a save-time *estimate* (±100–150), unfit for precise per-game claims. | Store settings + estimate for later batch curve-fitting; no live rating. |
| **Preset bot character cards (per-ELO × playstyle)** | Nice browsing UX | Explicitly a future extension in the seed; the ELO + play-style sliders cover v1. | Ship sliders now; add cards post-launch. |

---

## Feature Dependencies

```
Setup screen (ELO + play-style sliders, color, TC preset)
    └──requires──> existing /analysis sliders + budget.elo plumbing
    └──feeds────> Live clocked board

Live clocked board
    ├──requires──> FlawChess engine (useFlawChessEngine / mctsSearch) + Maia inference
    ├──requires──> clock loop (increment, flag detection, background-tab reconcile)
    ├──requires──> chess.js (legal moves + all draw/mate detection)
    └──enables───> Bot think-time pacing ──caps──> engine search budget

Game-end detection (mate/stalemate/threefold/50-move/insufficient/resign/flag/draw)
    └──requires──> Live clocked board
    └──produces──> Result screen (win/loss/draw + reason)
                       ├──links──> "Analyze this game" (existing analysis/Library)
                       └──triggers──> PGN capture

PGN capture (with [%clk] per-move clocks)
    └──requires──> clock loop recording per-move elapsed time
    └──feeds────> Store-finished-game endpoint

Store-finished-game endpoint
    ├──requires──> synthetic platform_game_id + rated/opponent-type values
    ├──requires──> save-time player-rating conversion (useMaiaEloDefault machinery)
    ├──reuses────> existing import normalization path
    └──produces──> games row (platform='flawchess') ──> Library games tab + all analytics

localStorage resume ──enhances──> Live clocked board (survives tab close; clock paused)

Anchor-calibration harness (Node)
    ├──requires──> Stockfish WASM in Node (verified) + Maia ONNX in Node (OPEN feasibility)
    └──independent of──> the play UI (parallelizable)
```

### Dependency Notes

- **Store endpoint requires a synthetic game id + rated/opponent-type decisions.** The `(user, platform, platform_game_id)` unique key needs a generated id for `platform='flawchess'`, and `rated` + opponent-type columns need values chosen (flagged as plan-time items in the seed). Blocks nothing else but must be settled before persistence works.
- **PGN `[%clk]` capture is load-bearing for analytics, not cosmetic.** Missing clock comments → the existing time-management path silently drops the game. The clock loop must record per-move elapsed time from move 1, so clock implementation and PGN capture are coupled — plan them together.
- **Think-time pacing both improves feel AND caps the search budget.** Same knob (remaining-clock-derived); design as one mechanism, not two.
- **Flag detection and localStorage resume both hinge on wall-clock reconciliation.** Backgrounded tabs throttle timers; both must recompute elapsed time from a stored wall-clock timestamp on focus/resume, not from accumulated interval ticks.
- **The calibration harness is architecturally independent** of the play UI and can be built in parallel; its only shared risk is the Maia-ONNX-in-Node feasibility.

---

## MVP Definition

### Launch With (v1)

- [ ] **Setup screen** — reused ELO + play-style sliders, color choice, TC presets (bullet excluded) — the entry point.
- [ ] **Live clocked board** driving the FlawChess engine client-side — the core loop.
- [ ] **Dual clocks + increment + flag-on-time** (background-tab-safe) — makes it a clocked game.
- [ ] **Whose-move indication + turn-gated legal input** (drag + click) — basic playability.
- [ ] **Bot thinking affordance + human-like pacing** (best-effort) — non-robotic feel.
- [ ] **Move sounds** (with mute) — confirmed IN.
- [ ] **Resign + draw offers** (confirmed IN) — clocked-game controls.
- [ ] **Full game-end detection** (mate/stalemate/threefold/50-move/insufficient/resign/flag/draw) — correct endings.
- [ ] **Result screen** — win/loss/draw + reason, "Analyze this game", "New game".
- [ ] **PGN capture with `[%clk]`** — required for analytics inclusion.
- [ ] **Store finished game** endpoint → `games` row (`platform='flawchess'`) with bot settings + converted player rating — the strategic payoff.
- [ ] **localStorage resume** (clock paused while away) — casual-play forgiveness.
- [ ] **Anchor-calibration harness** — first strength map + engine bench (committed in-milestone; parallel track).

### Add After Validation (v1.x)

- [ ] **Rematch button** (re-run identical config) — if users ask; low cost.
- [ ] **Bot resignation / bot draw offers in dead positions** — polish once accept/decline heuristics prove out.
- [ ] **Phone-perf tuning** for the search budget under 3+0 — promote from best-effort if devices struggle.
- [ ] **Low-time clock warning / haptics** — sensory polish.

### Future Consideration (v2+)

- [ ] **Preset bot character cards** (per-ELO × playstyle) — browsing UX once sliders validate.
- [ ] **3-star victory system** — depends on abandonment-as-loss revisit (needs server-side in-progress tracking).
- [ ] **User-results strength calibration → relabel bots with measured ELO** — deferred; needs data volume.
- [ ] **Rage-quit accounting** — only once a rating/ladder exists to make it matter.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Setup screen (reused sliders + color + TC) | HIGH | LOW | P1 |
| Live clocked board + engine loop | HIGH | MEDIUM | P1 |
| Clocks + increment + flag detection | HIGH | MEDIUM | P1 |
| Game-end detection (all conditions) | HIGH | MEDIUM | P1 |
| Result screen (+ Analyze / New game) | HIGH | LOW | P1 |
| PGN `[%clk]` capture + store endpoint | HIGH | MEDIUM | P1 |
| localStorage resume | MEDIUM | MEDIUM | P1 |
| Bot pacing + thinking affordance | MEDIUM | MEDIUM | P1 (best-effort) |
| Draw offers | MEDIUM | MEDIUM | P1 (confirmed IN) |
| Move sounds | MEDIUM | LOW | P1 (confirmed IN) |
| Save-time player-rating conversion on stored game | HIGH (calibration) | MEDIUM | P1 |
| Anchor-calibration harness | HIGH (project goal) | HIGH | P1 (parallel track) |
| Rematch button | LOW | LOW | P2 |
| Preset bot cards | MEDIUM | MEDIUM | P3 |
| 3-star / rage-quit accounting | LOW (now) | HIGH | P3 |
| Takeback / hints / live eval / premove | (negative) | — | **CUT** |

**Priority key:** P1 must-have for launch · P2 add when possible · P3 future.

## Competitor Feature Analysis

| Feature | lichess "Play with computer" | chess.com "Play Bots" | FlawChess Bot Play (v1) |
|---------|------------------------------|-----------------------|-------------------------|
| Strength selection | 8 Stockfish levels | Bot cards + difficulty slider | Continuous ELO slider (Maia-conditioned) + play-style slider |
| Opponent nature | Nerfed Stockfish (alien at low levels) | Nerfed Stockfish / personas | Human-like practical-play engine at chosen ELO, symmetric |
| Time control | Presets incl. unlimited | Presets / untimed coach modes | lichess presets, **bullet excluded**, no untimed |
| Takeback / hints | Available | Available (some paywalled) | **Deliberately absent** (honest calibration) |
| Live eval during play | Optional | Optional | **Absent** (crutch + compute cost) |
| Resign / draw | Yes / offer-draw | Yes | Yes / draw offers (IN) |
| Move sounds | Yes | Yes | Yes (IN) |
| Abandonment | Forgiving (client-side) | Forgiving | localStorage resume, clock paused, no server trace until finished |
| Game stored & analyzable | Analysis-board link, not a personal corpus | Review link | **First-class Library game** feeding WDL/endgame/time analytics |
| Per-move clocks in PGN | Yes (`[%clk]`) | Yes | Yes (`[%clk]`) — required for analytics |
| Rematch | Start new | Rematch button | "New game" retains settings (Rematch = P2) |

## Sources

- lichess "Play with the computer" — Stockfish levels 1–8, side/TC selection, forgiving computer-game abandonment: [How strong are the stockfish levels? (lichess feedback)](https://lichess.org/forum/lichess-feedback/how-strong-are-the-stockfish-levels), [Abort or resign in a computer game? (lichess)](https://lichess.org/forum/general-chess-discussion/abort-or-resign-in-a-computer-game), [Play with the computer from a position (lichess)](https://lichess.org/forum/general-chess-discussion/is-there-a-way-to-play-the-computer-with-a-specific-fen-position-and-at-a-specific-level)
- chess.com "Play Bots" — bot cards, in-game analyze/takeback, game-over Rematch/New/Review: [Play Chess Online Against the Computer (chess.com)](https://www.chess.com/play/computer), [How to resign a computer match (chess.com forum)](https://www.chess.com/forum/view/help-support/how-to-resign-a-computer-match)
- Internal: `.planning/seeds/SEED-091-flawchess-bot-play-milestone.md` (v1 scope + 5 locked decisions + plan-time flags), `.planning/PROJECT.md` "Current Milestone: v2.3 Bot Play"

---
*Feature research for: chess "play against a bot" experience (FlawChess v2.3)*
*Researched: 2026-07-11*
