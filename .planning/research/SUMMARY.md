# Project Research Summary

**Project:** FlawChess — v2.3 Bot Play
**Domain:** Client-side clocked bot-play + synthetic-game storage + headless calibration harness, layered onto an existing React 19 / FastAPI / PostgreSQL chess-analysis PWA
**Researched:** 2026-07-11
**Confidence:** HIGH

## Executive Summary

v2.3 adds a "play against the computer" surface on top of an app whose hard parts already ship in prod: the FlawChess practical-play engine (`mctsSearch` + Maia-3 ONNX policy + Stockfish.wasm grading), the `/analysis` ELO and play-style sliders, the Library games corpus, and the import→normalization→Zobrist→flaw pipeline. The play UI itself is well-trodden table-stakes (lichess "Play with the computer", chess.com "Play Bots"): a setup screen (strength / color / time control), a live clocked board, resign/draw/flag, game-end detection, a result screen, and move sounds. The genuinely differentiated part is that **every finished bot game is stored as a first-class analyzable Library game** (`platform='flawchess'`), feeding the same WDL / endgame / time-management analytics as imported games, and that a **headless Node calibration harness** produces the engine's first real (ELO × play-style) strength map.

The recommended build is deliberately thin on new dependencies. The clock, move sounds, and `[%clk]` PGN annotations add **zero** new runtime packages: the clock is a ~80-line hand-rolled deadline-based hook, sounds are a small Web Audio wrapper over CC0 assets, and `chess.js@1.4.0` (already installed) emits `[%clk]` via `setComment()`. The only net-new packages are **dev-only** harness tooling — `onnxruntime-node` and `tsx`. Architecturally, the milestone is cheap because of one load-bearing decision already baked into the codebase: **provider injection**. `selectBotMove` (new, pure) and `mctsSearch` (existing) take an `EngineProviders` seam, so the identical move-selection logic runs unchanged in the browser (Workers) and in the Node harness (direct sessions) — the harness therefore measures the exact code users play against. The backend is a one-endpoint touch (`POST /bot-games`) reusing the import persistence path; no websockets, no server game session.

The risks are concentrated and well-understood. The clock **must** be a `Date.now()`-delta model (never `setInterval` decrement) and must treat the Page Visibility API as first-class game state, or backgrounded tabs will self-flag the bot or bleed the human's clock. Move selection **must** sample (not argmax) at the human end and run exactly one Maia inference there (no MCTS), or the bot plays hundreds of Elo above nominal and every game is identical — corrupting both playability and calibration. The "reuse the existing normalization path" instruction is a trap: there is **no** PGN→game normalizer today (only chess.com/lichess JSON normalizers with a narrow `Platform` Literal), so a new `normalize_flawchess_game(pgn, …)` is required. And `[%clk]` emission is load-bearing, not cosmetic — omit it and every bot game is silently invisible to time-management stats, permanently (clocks can't be recovered post-hoc).

## Key Findings

### Recommended Stack

The stack story is "consume what ships, add almost nothing." All four net-new concerns (chess clock, move sounds, calibration harness, `[%clk]` emission) resolve without new runtime dependencies except the dev-only harness. Versions were verified via `npm view` and behaviors (chess.js `[%clk]`, engine-module browser-independence, headless Stockfish) confirmed by direct Node execution against the repo's own `node_modules` — hence HIGH confidence. See `STACK.md`.

**Core technologies:**
- **Hand-rolled `useGameClock`** (deadline-based) — accurate clock — no maintained React chess-clock lib gets the accuracy model right; ~80 lines of `Date.now()`-delta math is the correct pattern and is background-tab-safe.
- **Hand-rolled `useMoveSounds`** (Web Audio, preloaded buffers) — move/capture/check/end cues — platform-native, no per-play latency, overlapping plays; source **CC0** assets (freesound.org / synthetic), NOT lichess's non-CC0 files. Precache via the existing `vite-plugin-pwa` Workbox config.
- **`chess.js@1.4.0` `setComment('[%clk h:mm:ss]')`** (already installed) — per-move clock annotation — verified to emit the exact lichess/PGN convention; python-chess already parses it on ingest. No PGN-writer lib.
- **`onnxruntime-node@1.27.0`** (**devDependency**) — Maia inference in the Node harness — pin to *exactly* match the browser's `onnxruntime-web@1.27.0` (identical opset/kernels → zero model-compat risk); native CPU EP, no browser globals. Must NOT ship in the browser bundle.
- **`tsx@4.23.0`** (**devDependency**) — run harness TS unbundled — esbuild loader, `@/` alias-aware, no jsdom/build step.
- **Reused as-is (do NOT replace/re-benchmark):** `mctsSearch` / `useFlawChessEngine`, Maia worker + `onnxruntime-web@1.27.0`, vendored `stockfish-18-lite-single.{js,wasm}`, `policyTemperature`, the import normalization downstream, `react-chessboard`.

> **Version reconciliation (confirm at plan time):** STACK recommends `onnxruntime-node@1.27.0` to match the pinned `onnxruntime-web@1.27.0` opset exactly. PITFALLS loosely referenced `~1.20.1` "per project memory" — but that `1.20.1` figure is the unrelated **Python** `onnxruntime` package from a different Maia repro, not the Node package. Prefer **1.27.0** (version-match rationale); flag as a plan-time confirm.

### Expected Features

The play UI is table-stakes; the storage-as-first-class-game and the calibration harness are the differentiators. v1 IN/OUT boundaries are locked in SEED-091: draw offers + move sounds IN; premove + takeback OUT. FlawChess deliberately **strips the training aids** (no hints/takeback/live-eval) precisely to keep the game an honest, calibration-grade strength measurement. See `FEATURES.md`.

**Must have (table stakes):**
- Setup screen — reused ELO + play-style sliders, color choice, TC presets (**bullet excluded** by design for compute headroom).
- Live clocked board driving the engine client-side; dual clocks + Fischer increment + flag-on-time (background-tab-safe).
- Whose-move indication + turn-gated legal input (drag + click); bot "thinking" affordance + human-like pacing.
- Full game-end detection (mate/stalemate/threefold/50-move/insufficient/resign/flag/draw-agreed); result screen with "Analyze this game" + "New game".
- Resign + draw offers; move sounds (with mute).
- PGN capture with `[%clk]`; store finished game → `games` row (`platform='flawchess'`); localStorage resume (clock paused while away).

**Should have (competitive / this-app differentiators):**
- Finished bot games become first-class analyzable Library games (WDL / mistake tags / endgame + time analytics) — nothing on lichess/chess.com folds bot games into a personal analytics corpus.
- Practical-play engine as opponent (Maia-conditioned, human-like at chosen ELO, symmetric — never adapts).
- Save-time converted player rating on every stored game (calibration substrate, not a thrown-away NULL).
- Headless anchor-calibration harness — first real (ELO × play-style) strength map + reusable engine bench.

**Defer (v1.x / v2+):**
- Rematch button, bot resignation/draw-offers in dead positions, phone-perf tuning, low-time warnings (v1.x).
- Preset bot character cards, 3-star victory system, user-results ELO relabeling, rage-quit accounting (v2+ — several need server-side in-progress tracking that v1's client-side design avoids).
- **CUT entirely:** takeback, premove, hints, live eval during play, opening book for the bot, adaptive difficulty, server-enforced clock/websockets (each corrupts calibration or adds server complexity the design rejects).

### Architecture Approach

The NEW bot surface plugs into EXISTING architecture through the frozen `EngineProviders` seam. The single most important structural constraint: `selectBotMove` must be a **pure, provider-agnostic** function in `lib/engine/` (no React, no `new Worker()`, no DOM) so the Node harness can import it through the `@/` alias hook without dragging in browser dependencies. The browser and harness differ only in how they *build* providers. Backend stays a one-endpoint touch reusing the import persistence path; bot settings live in a side-table, not new columns on the hot `games` table. See `ARCHITECTURE.md`.

**Major components:**
1. **`selectBotMove.ts`** (NEW, pure) — maps `(fen, {elo, styleSlider}, providers, budget)` → chosen UCI; owns the sample↔argmax blend across two regimes.
2. **`useBotGame.ts`** (NEW hook) — game loop: chess.js move tree, dual clocks + increment, side-to-move, pacing, flag/terminal detection, localStorage snapshot each move; holds one persistent pool+queue.
3. **`BotsPage` + subcomponents** (NEW) — setup screen (reuse `EloSelector` + style slider + color + TC preset), live board, resume prompt, POST on finish; lazy-loaded route, nav sibling to Library/Openings/Endgames.
4. **`routers/bot_games.py` + `bot_game_service.py`** (NEW) — thin router → build `NormalizedGame`, derive converted player rating, persist via shared path.
5. **`persist_normalized_games()`** (extracted from `import_service._flush_batch`) + **`bot_game_settings`** side-table + **`normalize_flawchess_game`** (NEW) — the reuse boundary.
6. **`scripts/bot-calibration.mjs`** (NEW) — clone of the proven `gem-elo-calibration.mjs`; Node providers (onnxruntime-web wasm session + spawned Stockfish `.cjs`) over the (ELO × slider × anchor) grid → TSV.

> **Store-on-finish reconciliation (compatible, not a contradiction):** ARCHITECTURE says "reuse `_flush_batch` / extract `persist_normalized_games`"; PITFALLS clarifies there is no PGN front-door. The reconciliation: a NEW `normalize_flawchess_game(pgn, …)` builds a `NormalizedGame`, which then feeds the SAME reusable downstream (`find_opening` + position hashing + `_flush_batch`/`persist_normalized_games`). The `Platform` Literal must be **widened** to include `"flawchess"`, but `games.platform` is `String(20)` with no CHECK constraint, so **no column migration** is needed.

### Critical Pitfalls

Top items from `PITFALLS.md` (14 total, each mapped to a phase and verification):

1. **Timer drift + backgrounded-tab throttle (Pitfalls 1–2)** — never subtract per `setInterval` tick; store absolute deadlines and derive display from `Date.now()` deltas (interval repaints only). Make the Page Visibility API first-class: on hide, pause the clock and don't bill away-time; on show, recompute against the wall clock. Otherwise the bot self-flags while hidden or the human returns already flagged.
2. **Argmax at the human end (Pitfalls 3–5)** — argmax over Maia-predicted human moves plays hundreds of Elo above nominal and makes every game identical. Sample the temperature-reshaped Maia policy at the human end; argmax only at the Stockfish extreme. Fixed sampler order: `policy()` → drop illegal (via `applyUciMoveFen`) → apply temperature → renormalize → sample; fall back to a legal move on empty policy.
3. **Full MCTS at the human end (Pitfall 4)** — run exactly ONE Maia inference at full-human (no tree); engage `mctsSearch` only as the Stockfish weight rises. Branch on the slider *before* the compute path, or blitz on a mid-range phone can't answer in 1–2 s.
4. **The "reuse normalization" trap + missing `[%clk]` (Pitfalls 6–7)** — no PGN→game path exists; write `normalize_flawchess_game` and widen the `Platform` Literal. Emit `{[%clk h:mm:ss]}` after every move (both colors) using true post-move remaining time — load-bearing for time-management analytics, unrecoverable if omitted. Add a store-endpoint validation gate that rejects a bot PGN missing `[%clk]`.
5. **Synthetic id collisions + NULL player rating (Pitfalls 8–9)** — mint `crypto.randomUUID()` at game *start*, persist it in localStorage (survives resume), send as `platform_game_id`; make the store endpoint idempotent on unique-constraint conflict (return 200). Derive a lichess-scale, TC-bucket-matched player rating at save via the existing `useMaiaEloDefault` machinery; NULL only when the user has zero imported games. Record `rating_source` for the ±100–150 caveat.
6. **Node-ONNX feasibility + unanchored self-play (Pitfalls 13–14)** — de-risk Maia-in-Node with a spike *first* (measure per-inference latency + games/hour); note the gem harness already proves this path works. Always fit strength against external anchors (raw-Maia 1100–1900 argmax rungs + Stockfish skill levels), never pure self-play; sample grid cells evenly.

## Implications for Roadmap

Research points to **six phases in three dependency waves**, closely mirroring the `ARCHITECTURE.md` build order. The keystone is `selectBotMove` (Phase 1): everything on the play side and the harness depends on it. The backend store path (Phase 2) is fully independent of engine work and parallelizable. The harness (Phase 3) and clocked board (Phase 4) both depend only on Phase 1 and can run in parallel.

### Phase 1: Move selection core (`selectBotMove`)
**Rationale:** Pure, provider-agnostic, depends only on existing engine primitives; foundational to both the app and the harness. Building it wrong (argmax / MCTS-everywhere) is the single highest-impact failure.
**Delivers:** `selectBotMove.ts` (two-regime sample↔argmax blend) + unit tests with injectable RNG for determinism.
**Addresses:** practical-play engine as opponent; play-style slider semantics.
**Avoids:** Pitfalls 3, 4, 5, 10 (argmax, full-MCTS-at-human-end, botched blend, adaptive strength).

### Phase 2: Backend store-on-finish
**Rationale:** Independent of all engine work; parallelizable with Phase 1. Settles the schema/id/rating contracts everything else persists through.
**Delivers:** `normalize_flawchess_game`, widened `Platform` Literal (no column migration), `bot_game_settings` model+migration, extracted `persist_normalized_games`, `bot_game_service`, thin `routers/bot_games.py`, Pydantic schemas, idempotent + PGN-validating + server-sanity-checked endpoint.
**Uses:** existing import persistence path, `user_rating_anchors` / `chesscom_to_lichess` rating conversion.
**Avoids:** Pitfalls 6, 7 (validation gate), 8, 9 (server-derived id + rating).

### Phase 3: Calibration harness (spike-gated)
**Rationale:** Committed deliverable, architecturally independent of the play UI (depends only on Phase 1). Gate on a Maia-in-Node feasibility spike as the first task — though the shipped `gem-elo-calibration.mjs` already answers the open question YES.
**Delivers:** `scripts/bot-calibration.mjs` reusing the `@/` alias hook + proven Node providers; first (ELO × play-style) strength map streamed to `reports/data/`.
**Uses:** `onnxruntime-node@1.27.0` (or onnxruntime-web wasm, per the harness's existing recipe), vendored Stockfish `.cjs`, `tsx`.
**Avoids:** Pitfalls 13 (spike first), 14 (external anchors, even grid sampling).

### Phase 4: Clocked board + game loop (`useBotGame`)
**Rationale:** Depends on Phase 1. The heart of the play experience and the home of the highest-risk clock/visibility work.
**Delivers:** `useBotGame` (dual clocks + increment, pacing, flag + terminal detection, resign, draw offers, move sounds), `useGameClock`, `useMoveSounds`, `botGamePgn` `[%clk]` emission.
**Uses:** hand-rolled clock/sound hooks, chess.js, `chess.js setComment`.
**Avoids:** Pitfalls 1, 2 (Date.now()-delta clock + Page Visibility), 7 (client emission).

### Phase 5: localStorage resume
**Rationale:** Depends on Phase 4; enhances the board with tab-close forgiveness.
**Delivers:** `botGamePersistence.ts` — persist paused-clock snapshot every move; "Resume game?" gate; clear only after a confirmed 2xx.
**Avoids:** Pitfall 12 (paused-remaining persistence, no terminal-state resume, no double-store).

### Phase 6: Bots page + nav wiring
**Rationale:** Depends on Phases 4, 5, 2 — the integration layer.
**Delivers:** setup screen (reused sliders/color/TC), live board wiring, resume prompt, POST-on-finish, lazy `/bots/*` route + nav sibling, guest analyzed-coverage caveat.
**Avoids:** Pitfall 11 (guest eval-exclusion UX), analytics-contamination posture (bot games excluded from defaults, opted into Bots + Library Games).

### Phase Ordering Rationale
- **Waves:** A = {1, 2}, B = {3, 4}, C = {5, 6} — matches `ARCHITECTURE.md`'s dependency graph exactly.
- **`selectBotMove` first** because both the play loop and the harness import it; getting the two-regime blend right up front prevents calibration-corrupting rework.
- **Backend parallel to engine** because store-on-finish shares no code with move selection and unblocks persistence early.
- **Harness parallel to the board** because it's non-browser and independent; spiking it early de-risks the one open feasibility item without blocking the UI.
- **Clock/visibility risk is concentrated in Phase 4**, so it gets a dedicated phase with explicit wall-clock and hide-tab verification rather than being smeared across the UI work.

### Research Flags

Phases likely needing deeper research/spike during planning:
- **Phase 1:** the exact slider → (temperature, sharpness, regime thresholds) curve is itself a calibration target with a genuine discontinuity at `HUMAN_ONLY_THRESHOLD`; resolve the mapping at plan time and have the harness sweep *through* the boundary. Watch the `policyTemperature` polarity (T<1 = human end) — inverting it was a prior bug.
- **Phase 3:** gate on a Maia-in-Node feasibility spike (latency + games/hour) as the first task; also confirm the `onnxruntime-node@1.27.0` vs `~1.20.1` version question (prefer 1.27.0 to match the browser opset).

Phases with standard patterns (skip research-phase):
- **Phase 2:** well-understood extend-the-import-path work against named files; the only design choices (id/rated/opponent-type/rating) are already recommended in `ARCHITECTURE.md`.
- **Phase 5:** localStorage snapshot/restore is a solved pattern; the pitfalls are enumerated.
- **Phase 6:** page/nav/route wiring reuses existing `Analysis` lazy-route + slider components.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Versions verified via `npm view`; chess.js `[%clk]`, engine browser-independence, and headless Stockfish confirmed by direct Node execution against the repo's own install. Only soft spot: sound-asset licensing (verify each CC0 file at plan time). |
| Features | HIGH | Well-trodden lichess/chess.com UX; scope tightly locked in SEED-091's 5 decisions + PROJECT.md. IN/OUT boundaries explicit. |
| Architecture | HIGH | Every integration point named against real source; the `EngineProviders` seam and the `gem-elo-calibration.mjs` harness pattern are proven in prod. Store-schema choices are open-by-design but come with clear recommendations. |
| Pitfalls | HIGH | Grounded in the actual codebase (`mctsSearch.ts`, `normalization.py`, `eval_queue_service.py`, `useMaiaEngine.ts`) plus well-established browser-platform behavior. |

**Overall confidence:** HIGH

### Gaps to Address

- **`onnxruntime-node` version (1.27.0 vs ~1.20.1):** cross-file discrepancy resolved in favor of 1.27.0 (matches the pinned browser `onnxruntime-web` opset; the 1.20.1 figure was the unrelated Python package). Confirm at Phase 3 plan time with a one-inference smoke test.
- **Slider → (temperature, sharpness, thresholds) mapping:** a genuine design decision AND a calibration target, with a distribution discontinuity at the human/search regime boundary. Resolve at Phase 1 plan time; validate with a harness sweep through the seam.
- **Store-on-finish schema knobs:** `platform_game_id` source (→ server `uuid4`), `rated` (→ False), opponent-type (→ `is_computer_game=True`), bot-ELO/player-rating columns — all have recommendations in `ARCHITECTURE.md` but must be locked at Phase 2 plan time.
- **Maia-in-Node harness speed:** the one open feasibility item; de-risk with a spike as the first Phase 3 task (fallback: Playwright headless-browser harness driving the real worker).
- **Sound-asset licensing:** confirm each audio file is genuinely CC0 before committing; do NOT copy lichess assets.

## Sources

### Primary (HIGH confidence)
- `STACK.md` — verified package versions (`npm view`), direct Node execution of `chess.js` `[%clk]` emission and vendored Stockfish, source inspection confirming engine math is browser-global-free.
- `FEATURES.md` — lichess "Play with the computer" + chess.com "Play Bots" UX; SEED-091 locked scope + PROJECT.md milestone.
- `ARCHITECTURE.md` — live-source integration points (`useFlawChessEngine`, `mctsSearch`, `maiaQueue`, `import_service._flush_batch`, `normalization.py`, `user_rating_anchors`, `gem-elo-calibration.mjs`); SEED-091 + CLAUDE.md constraints.
- `PITFALLS.md` — codebase-grounded failure modes (`mctsSearch.ts` determinism/WR-04/WR-07, `normalization.py` Platform Literal, `eval_queue_service.py` guest exclusion, `useMaiaEngine.ts`); CLAUDE.md critical constraints; well-established browser platform behavior (Page Visibility, timer clamping, Worker throttling).

### Secondary (MEDIUM confidence)
- Project memory: `project_headless_stockfish_wasm_verification` (Stockfish-WASM-in-Node verified), `project_flawchess_engine_prior_art`, `project_frontend_beta_gating_source`.
- Sound-asset licensing guidance (freesound.org CC0 vs lichess non-CC0) — verify per-file at plan time.

### Tertiary (LOW confidence)
- The `onnxruntime==1.20.1` memory note — refers to the Python package for a different Maia repro; superseded here by the STACK `onnxruntime-node@1.27.0` recommendation.

---
*Research completed: 2026-07-11*
*Ready for roadmap: yes*
