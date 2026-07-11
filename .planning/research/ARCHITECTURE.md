# Architecture Research

**Domain:** Client-side clocked bot-play integrated into an existing chess-analysis PWA (FlawChess v2.3)
**Researched:** 2026-07-11
**Confidence:** HIGH (engine + harness reuse verified against live source; store path verified against normalization + Game model; some schema choices are open by design)

> Scope: how the NEW bot-play surface plugs into the EXISTING architecture. Every integration point below is named against real files. "NEW" vs "MODIFIED" is called out explicitly. The single load-bearing decision that makes the whole milestone cheap is **provider injection**: the search core (`mctsSearch`) and the Maia policy worker already accept an `EngineProviders` seam, so the same move-selection logic runs unchanged in the browser (Workers) and in a headless Node harness (direct sessions).

---

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                        BROWSER (Bots page — NEW)                       │
├──────────────────────────────────────────────────────────────────────┤
│  BotsPage (NEW)  ── setup screen (reuse EloSelector + style slider +   │
│    │                 color + lichess TC preset) → live clocked board   │
│    ▼                                                                   │
│  useBotGame (NEW hook) ── chess.js move tree · dual clocks · side ·    │
│    │      result · pacing · flag detection · localStorage persist      │
│    ▼                                                                   │
│  selectBotMove(fen, settings, providers) (NEW pure module) ───────────┐│
│    │  human end  → policy() → applyPolicyTemperature → sample (NO MCTS)││
│    │  mid/SF end → mctsSearch() → practicalScore weighted-sample/argmax││
│    ▼                                                                   ││
│  EngineProviders  { policy, grade }   ← injected                       ││
│    │            (browser: createMaiaQueue + createWorkerPool)          ││
├────┼──────────────────────────────────────────────────────────────────┤│
│  createMaiaQueue() [EXISTING]      createWorkerPool() [EXISTING]        ││
│  Maia-3 ONNX Worker                Stockfish.wasm pool                  ││
├──────────────────────────────────────────────────────────────────────┤│
│  localStorage  "flawchess:botgame:active" (NEW, isolated from ?fen=)   ││
└───────────────────────────────┬───────────────────────────────────────┘│
              POST /bot-games    │  (finished PGN with [%clk] + settings)  │
                                 ▼                                         │
┌──────────────────────────────────────────────────────────────────────┐ │
│                     BACKEND (one small endpoint — NEW)                 │ │
├──────────────────────────────────────────────────────────────────────┤ │
│  routers/bot_games.py (NEW)  → services/bot_game_service.py (NEW)      │ │
│     │  build NormalizedGame(platform='flawchess', gen id, rated=False) │ │
│     │  derive converted player rating (user_rating_anchors) [EXISTING] │ │
│     ▼                                                                  │ │
│  persist_normalized_games()  ← extracted from import_service._flush_   │ │
│     │   batch [EXISTING logic]: bulk-insert + process_game_pgn Zobrist │ │
│     │   positions + classify_game_flaws                                │ │
│     ▼                                                                  │ │
│  games (platform='flawchess') + game_positions + bot_game_settings(NEW)│ │
└──────────────────────────────────────────────────────────────────────┘ │
                                                                           │
┌──────────────────────────────────────────────────────────────────────┐ │
│          HEADLESS NODE HARNESS (calibration — NEW, non-browser)        │◄┘
├──────────────────────────────────────────────────────────────────────┤
│  scripts/bot-calibration.mjs (NEW)                                     │
│    imports selectBotMove + mctsSearch + encoding from LIVE src via     │
│    scripts/lib/frontend-alias-hook.mjs [EXISTING @/ resolve hook]      │
│    builds NODE EngineProviders: onnxruntime-web session (policy) +     │
│    spawned Stockfish WASM .cjs over UCI (grade) — same recipe as       │
│    scripts/gem-elo-calibration.mjs [EXISTING, proven]                  │
│    plays bot × anchor over (ELO × slider) grid → TSV in reports/data/  │
└──────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | New / Modified / Existing |
|-----------|----------------|---------------------------|
| `selectBotMove.ts` | Pure move picker: maps `(fen, {elo, styleSlider}, providers)` → chosen UCI. Owns the sample↔argmax blend. **No React, no Worker, no DOM.** | **NEW** |
| `useBotGame.ts` | Game-loop hook: chess.js move tree, dual clocks + increment, side-to-move, result/termination, bot think-time pacing, flag detection, localStorage snapshot each move. Holds one persistent `pool`+`queue`. | **NEW** |
| `BotsPage.tsx` + setup/board subcomponents | Nav-sibling page: setup screen (reuse `EloSelector`, style slider, color, TC preset) then live board; "Resume game?" gate; POST on finish. | **NEW** |
| `createMaiaQueue()` (`lib/engine/maiaQueue.ts`) | `policy(fen, elo, side) → UCI-keyed prob map`. The human-end path calls this **once per move**. | EXISTING, reused unchanged |
| `mctsSearch` (`lib/engine/mctsSearch.ts`) | Full practical-play search → `rankedLines[]` sorted by `practicalScore`. Mid/Stockfish-end path only. | EXISTING, reused unchanged |
| `applyPolicyTemperature`, `truncateAndRenormalize` | Reshape/trim the raw Maia policy before sampling. | EXISTING, reused |
| `useMaiaEloDefault` + `chesscom_to_lichess`/`user_rating_anchors` | Save-time converted, TC-bucket-matched player rating. | EXISTING, reused |
| `routers/bot_games.py` / `bot_game_service.py` | Accept finished PGN+settings, build `NormalizedGame`, persist via shared path. | **NEW** |
| `import_service._flush_batch` | Bulk insert + Zobrist positions + flaw classification. | EXISTING → **extract** a shared `persist_normalized_games()` |
| `bot_game_settings` table + model/migration | Authoritative record of `(nominal_elo, style_slider, tc_preset, player_rating, rating_source)` per stored bot game. | **NEW** |
| `scripts/bot-calibration.mjs` | Headless bot×anchor grid → TSV. | **NEW** (clone of `gem-elo-calibration.mjs` structure) |

---

## Recommended Project Structure

```
frontend/src/
├── lib/engine/
│   ├── selectBotMove.ts        # NEW — pure blend picker (shared browser+Node)
│   ├── botMoveSelection.test.ts# NEW — sampling/argmax/determinism unit tests
│   ├── mctsSearch.ts           # EXISTING — reused via EngineProviders seam
│   ├── maiaQueue.ts            # EXISTING — policy() provider
│   ├── workerPool.ts           # EXISTING — grade() provider
│   └── policyTemperature.ts    # EXISTING — applyPolicyTemperature
├── hooks/
│   ├── useBotGame.ts           # NEW — game loop, clocks, pacing, persist
│   └── useMaiaEloDefault.ts    # EXISTING — converted-rating default
├── lib/
│   ├── botGamePersistence.ts   # NEW — localStorage snapshot schema + load/save
│   └── botGamePgn.ts           # NEW — chess.js history → PGN WITH [%clk] comments
├── pages/
│   └── Bots.tsx                # NEW — lazy-loaded page (like Analysis.tsx)
└── components/bots/            # NEW — BotSetup, BotBoard, BotClock, ResumePrompt

app/
├── routers/bot_games.py        # NEW — POST /bot-games (thin)
├── services/bot_game_service.py# NEW — NormalizedGame build + persist + rating
├── services/import_service.py  # MODIFIED — expose persist_normalized_games()
├── schemas/bot_games.py        # NEW — request/response Pydantic models
├── schemas/normalization.py    # MODIFIED — Platform Literal += "flawchess"
├── models/bot_game_settings.py # NEW — FK(game_id) settings side-table
└── alembic/versions/xxxx_bot_game_settings.py  # NEW migration

scripts/
├── bot-calibration.mjs         # NEW — reuses frontend-alias-hook + Node providers
└── lib/frontend-alias-hook.mjs # EXISTING — @/ resolve hook (zero-drift code share)

reports/data/                   # EXISTING — calibration TSV output dir
```

### Structure Rationale

- **`selectBotMove.ts` lives in `lib/engine/` beside `mctsSearch.ts`, not in `hooks/`.** It must be a *pure* provider-agnostic function so the Node harness can import it through the `@/` alias hook without dragging in React or `new Worker()`. This is the single most important structural constraint of the milestone.
- **`useBotGame` owns lifecycle, not selection.** It mirrors `useFlawChessEngine`'s provider-lifecycle pattern (create `pool`+`queue` once while mounted, terminate on cleanup) but drives a stateful game rather than a single-position search.
- **Backend stays a one-endpoint touch.** No websockets, no server game session. The router is thin (CLAUDE.md router convention); all logic is in `bot_game_service`; persistence reuses the existing import path.
- **Bot settings in a side table, not new `games` columns.** Keeps the hot, ~300k-row `games` table free of mostly-NULL bot columns (DB design rule: lookup table + FK when the value carries metadata).

---

## Architectural Patterns

### Pattern 1: Provider-injected move selection (the code-sharing keystone)

**What:** `selectBotMove` takes the search primitives as arguments, exactly as `mctsSearch` already takes `EngineProviders`. The browser and the Node harness differ only in how they *build* providers.

**When to use:** every bot move, both environments.

**Trade-offs:** one extra parameter object vs. total elimination of duplicated selection logic and a browser-only dependency in the harness. Strongly worth it.

```typescript
// frontend/src/lib/engine/selectBotMove.ts  (NEW — sketch)
export interface BotMoveSettings {
  elo: number;
  styleSlider: number; // 0 = full human (sample), 1 = full stockfish (argmax)
}
export interface BotMoveProviders {
  policy: EngineProviders['policy'];          // Maia (human-end, one inference)
  runSearch: (fen: string, budget: SearchBudget) => Promise<EngineSnapshot>; // = mctsSearch bound to full providers
  random?: () => number;                      // injectable RNG → deterministic harness/tests
}

export async function selectBotMove(
  fen: string, settings: BotMoveSettings, providers: BotMoveProviders,
  searchBudget: SearchBudget,                 // clock-derived ceiling (Pattern 3)
): Promise<string /* uci */> {
  const side = fen.split(' ')[1] as 'w' | 'b';
  const rng = providers.random ?? Math.random;

  if (settings.styleSlider <= HUMAN_ONLY_THRESHOLD) {
    // Human end — NO MCTS: one Maia inference, temperature reshape, sample.
    const raw = await providers.policy(fen, settings.elo, side);
    const temp = sliderToTemperature(settings.styleSlider);
    const shaped = temp === DEFAULT_POLICY_TEMPERATURE ? raw : applyPolicyTemperature(raw, temp);
    return sampleFromDistribution(truncateAndRenormalize(shaped), rng);
  }
  // Mid / Stockfish end — practical scores require the search.
  const snap = await providers.runSearch(fen, searchBudget);
  if (settings.styleSlider >= STOCKFISH_ARGMAX_THRESHOLD) {
    return snap.rankedLines[0].rootMove;                      // deterministic argmax
  }
  return sampleByPracticalScore(snap.rankedLines, sliderToSharpness(settings.styleSlider), rng);
}
```

### Pattern 2: Two selection regimes, one slider (flag for plan)

**What:** the play-style slider has *different* meaning in bot play than on `/analysis`. On `/analysis` it maps to `policyTemperature` feeding a full MCTS. In bot play it maps to **both** a temperature (human-end sampling sharpness) **and** the sample→argmax transition.

**When to use:** interpreting the reused slider widget on the setup screen.

**Trade-offs:** reusing the widget is free UX consistency, but the mapping is a genuine design decision with a discontinuity at the regime boundary (`HUMAN_ONLY_THRESHOLD`): below it there is no MCTS and moves are Maia-policy samples; above it moves are practical-score samples. The two distributions are not continuous across the seam. Recommend the calibration harness sweep *through* the boundary so the strength curve exposes any cliff. Resolve the exact slider→(temperature, sharpness, thresholds) curve at plan time; it is itself a calibration target.

> Note on `policyTemperature` polarity (from `policyTemperature.ts`): T<1 is the *Human* end (sharpen toward the single most-human move); T>1 is the *Stockfish* end (flatten so rare-but-strong moves surface). Do not re-invert this when mapping the slider — the inverted assumption was a prior bug.

### Pattern 3: Clock-derived search budget + human-like pacing

**What:** the bot's remaining clock drives (a) a *think-time budget* (wall-clock delay before the move appears) and (b) the *search ceiling* (`SearchBudget.maxNodes` / grade movetime). Both scale down under time pressure so a 3+0 game stays responsive on a mid-range phone.

```typescript
const thinkMs = clamp(remainingMs / THINK_DIVISOR, MIN_THINK_MS, MAX_THINK_MS); // e.g. /30
const budget: SearchBudget = {
  maxNodes: nodesForThinkTime(thinkMs),   // fewer nodes when short on time
  maxPlies: FLAWCHESS_ENGINE_MAX_PLIES, concurrency: computePoolSize(),
  elo: { w: elo, b: elo }, policyTemperature: sliderToTemperature(slider),
};
// Human end is ~instant (one inference) → still enforce a minimum pacing delay
// so replies aren't robotic and the bot actually spends clock.
```

**Trade-offs:** best-effort only (SEED: perf tuning is polish, not a blocker). Backgrounded-tab `setTimeout`/rAF throttling while the bot "thinks" is a real edge case — detect via `document.visibilityState` and treat clock consistently. Flagging is checked in the clock tick loop: when the side-to-move clock crosses 0, the game ends by timeout attributed to that side.

### Pattern 4: Persist-every-move, restore-paused (localStorage resume)

**What:** after each applied move, serialize a compact snapshot to `localStorage["flawchess:botgame:active"]`; on Bots-page mount, if a snapshot exists show "Resume game?" and restore with **clocks paused** until the user resumes.

```typescript
interface BotGameSnapshot {
  schemaVersion: 1;
  settings: { elo: number; styleSlider: number; tcPreset: string; userColor: 'white'|'black' };
  sanMoves: string[];        // replay via chess.js — source of truth for the board
  clocksMs: { white: number; black: number };
  sideToMove: 'white'|'black';
  startedAt: string; lastMoveAt: string;   // wall-clock, for "time away" handling
}
```

**Trade-offs:** localStorage is the *only* store for an in-progress game (SEED: rage-quits leave no server trace in v1). It is strictly isolated from `/analysis`, which keeps ephemeral position state in the `?fen=` URL param (`lib/analysisUrl.ts`) and no localStorage. The two surfaces share no state. On finish (mate/resign/flag/draw/stalemate) the key is **removed** after a successful POST.

---

## Data Flow

### Bot move (per turn)

```
useBotGame (bot's turn)
   → derive clock budget (Pattern 3)
   → selectBotMove(fen, settings, providers, budget)
        human end:  queue.policy() ──1 Maia inference──► sample           (NO MCTS)
        mid/SF end: mctsSearch(pool.grade + queue.policy) ► rankedLines ► sample/argmax
   → chess.js.move(uci) · add increment · flip side · persist snapshot
   → render board + clocks
```

### Game finish → server

```
useBotGame detects terminal (mate/stalemate/3-fold/50-move/insufficient/resign/flag/draw)
   → botGamePgn.ts: chess.js history → PGN with [%clk h:mm:ss] per move  (REQUIRED — else time-mgmt stats silently exclude bot games)
   → POST /bot-games { pgn, result, termination, userColor, botSettings }
       router (thin) → bot_game_service:
          build NormalizedGame(platform='flawchess', platform_game_id=<generated>,
             rated=False, is_computer_game=True,
             {user_color}_rating = converted player rating (user_rating_anchors),
             {bot_color}_rating  = bot nominal ELO,
             {bot_color}_username = "FlawChess Bot ({elo})")
          persist_normalized_games(session, [game], user_id)   # EXISTING logic:
             process_game_pgn → Zobrist white/black/full hashes → game_positions
             classify_game_flaws (guest games excluded by eval pipeline as today)
          insert bot_game_settings(game_id, nominal_elo, style_slider, tc_preset,
             player_rating, rating_source)
          commit
   → remove localStorage key
Game now appears in Library games tab, analyzable like any imported game.
```

### Calibration (offline)

```
scripts/bot-calibration.mjs  (node --import ...frontend-alias-hook.mjs)
   → import { selectBotMove, mctsSearch, encodeBoard, maskAndSoftmax, ... } from '@/...'
   → build NODE providers:
        policy = onnxruntime-web session (maia3_simplified.onnx, wasm, 1 thread)
        grade  = spawned Stockfish .cjs over UCI (MultiPV)     ← both proven in gem harness
   → for each (elo × slider) cell, for each anchor (raw-Maia argmax rungs, SF skill levels):
        play bot vs anchor to termination via repeated selectBotMove
   → stream rows to reports/data/bot-calibration-<ts>.tsv
```

---

## Store-on-finish schema decisions (RESOLVE-AT-PLAN, with recommendation)

| Question | Options | Recommendation |
|----------|---------|----------------|
| **`platform` value** | new literal `"flawchess"` | Add `"flawchess"` to `Platform` Literal in `schemas/normalization.py`. **No DB migration for the column** — `games.platform` is `String(20)` with no CHECK constraint (verified in migrations + model). Analytics inclusion/exclusion comes free via the existing platform filter. |
| **`platform_game_id` (unique-key component)** | client UUID · server UUID · content hash | **Server-generated `uuid4().hex`** in `bot_game_service`. Satisfies the `(user_id, platform, platform_game_id)` unique constraint, avoids trusting/colliding on client-supplied ids. Client may send its own idempotency key, but the stored id is server-owned. |
| **`rated` flag** | True · False | **`False`.** Bot games are not rated ladder games. They still show in the Library games tab (not rated-gated) and still feed calibration via the stored settings + converted rating. |
| **opponent-type value** | reuse `is_computer_game` | **`is_computer_game=True`.** It *is* a computer opponent; the existing `opponent_type` filter and the Global-Stats default-exclude-bots behavior then work with zero new plumbing. |
| **Bot nominal ELO storage** | opponent rating column | **`{bot_color}_rating = nominal ELO`** (SEED-locked) + duplicated into the settings side-table as the authoritative calibration field. Display: `"vs FlawChess Bot (1400)"` via `{bot_color}_username`. |
| **Converted player rating** | user rating column | **`{user_color}_rating` = converted, TC-bucket-matched, lichess-scale rating** from `user_rating_anchors_repository.fetch_anchors_for_user` (blended median) / `chesscom_to_lichess`; NULL only when the user has no imported games. Record `rating_source` (`lichess_native`/`chesscom_converted`/`none`) in the side-table for the ±100–150 caveat. |
| **Full bot settings (nominal_elo, style_slider, tc_preset)** | new `games` columns · JSONB on `games` · **separate table** | **Separate `bot_game_settings` table**: `game_id` PK + FK→`games(id, user_id)` `ON DELETE CASCADE`, `bot_nominal_elo SMALLINT`, `style_slider REAL`, `tc_preset TEXT` (+ CHECK of the preset set), `player_rating SMALLINT NULL`, `player_rating_source TEXT`. Matches DB design rules (FK mandatory, no NULL pollution of the hot table, metadata-carrying value → lookup table). |

**Reuse boundary for persistence:** extract the body of `import_service._flush_batch` into a public `persist_normalized_games(session, games, user_id) -> int` (or call `_flush_batch` directly). It already does single-parse `process_game_pgn` → Zobrist positions → `classify_game_flaws`, and it deliberately does **not** commit (caller owns the transaction), which suits the bot service wrapping insert-game + insert-settings in one transaction.

---

## Build Order (dependencies first)

1. **`selectBotMove.ts` + unit tests** — pure, depends only on existing engine primitives. Foundational; shared by app and harness. Injectable RNG for determinism.
2. **Backend store-on-finish** (parallelizable with 1): `Platform` literal widen · `bot_game_settings` model+migration · extract `persist_normalized_games` · `bot_game_service` (rating conversion reuse) · thin `routers/bot_games.py` · Pydantic schemas. Independent of any engine work.
3. **`scripts/bot-calibration.mjs`** — depends on (1); reuses `frontend-alias-hook.mjs` + the gem harness's Maia-ONNX-in-Node and Stockfish-WASM-in-Node recipes. **De-risks the SEED "Maia headless in Node at harness-viable speed" open question — already answered YES by the shipped `gem-elo-calibration.mjs`.** Produces the first strength map and doubles as the engine test bench.
4. **`useBotGame` hook** — depends on (1): game loop, dual clocks + increment, pacing, flag detection, terminal detection (mate/stalemate/3-fold/50-move/insufficient), resign, draw offer, move sounds, `botGamePgn` `[%clk]` emission.
5. **localStorage resume** (`botGamePersistence.ts`) — depends on (4).
6. **Bots page + nav wiring** — depends on (4), (5), (2): setup screen (reuse `EloSelector`/style slider/color/TC preset), live board, resume prompt, POST on finish, `App.tsx` route (`/bots/*`, lazy like `Analysis`) + nav sibling in the Library·Openings·Endgames set.

Waves: **A** = {1, 2}; **B** = {3, 4}; **C** = {5, 6}.

---

## Anti-Patterns

### Anti-Pattern 1: Running MCTS at the human end
**What people do:** route every bot move through `mctsSearch` and vary only the temperature.
**Why it's wrong:** the human end needs exactly one Maia inference; a 400-node search per move is 100–1000× the compute and blows the 3+0 phone budget. It also makes the human end *stronger* than nominal ELO (argmax-practical never makes Maia's predicted mistakes) — corrupting calibration.
**Do this instead:** the two-regime `selectBotMove` (Pattern 1) — policy-sample below `HUMAN_ONLY_THRESHOLD`, search only above it.

### Anti-Pattern 2: `new Worker()` inside `selectBotMove`
**What people do:** build the Maia queue / Stockfish pool inside the selection function.
**Why it's wrong:** it makes the function browser-only and un-importable by the Node harness → duplicated selection logic → drift (the exact failure mode the gem harness's `@/`-import discipline was built to prevent).
**Do this instead:** inject `EngineProviders`; build them in `useBotGame` (Workers) and in the harness (direct ONNX + spawned Stockfish).

### Anti-Pattern 3: Adaptive bot strength
**What people do:** nudge bot ELO toward the player to keep games close.
**Why it's wrong:** there is then no fixed strength to measure — calibration is meaningless (SEED-locked: bot plays its own symmetric ELO, never adapts).
**Do this instead:** `budget.elo = { w: elo, b: elo }` fixed for the whole game.

### Anti-Pattern 4: Omitting `[%clk]` from the stored PGN
**What people do:** store the bare SAN PGN.
**Why it's wrong:** the Time-Management analytics parse `[%clk]`; without it, bot games are silently excluded from every clock-based stat (SEED-locked requirement).
**Do this instead:** `botGamePgn.ts` writes `{ [%clk h:mm:ss] }` after each move; python-chess `process_game_pgn` already reads it.

### Anti-Pattern 5: Bot-game state in the URL / shared with `/analysis`
**What people do:** reuse the `?fen=` analysis URL param for the live bot board.
**Why it's wrong:** the bot game is a stateful multi-move session with clocks; the `?fen=` param is ephemeral single-position analysis state. Mixing them breaks resume and pollutes analysis deep-links.
**Do this instead:** bot state lives only in the dedicated localStorage key; `/analysis` stays URL-driven and untouched.

---

## Integration Points

### Internal boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `useBotGame` ↔ `selectBotMove` | direct async call with injected providers | providers built once per mounted game (mirror `useFlawChessEngine` lifecycle) |
| `selectBotMove` ↔ `mctsSearch` / `createMaiaQueue` | `EngineProviders` seam (existing frozen contract) | zero change to the engine core |
| Browser ↔ backend | one `POST /bot-games` (REST) | no websockets, no server session |
| `bot_game_service` ↔ import pipeline | `persist_normalized_games()` (extracted from `_flush_batch`) | shared Zobrist + flaw classification; no SQL in the service (CLAUDE.md layering) |
| Harness ↔ frontend source | `@/` alias resolve hook + Node TS type-stripping | `scripts/lib/frontend-alias-hook.mjs`; gem-parity-style tripwire if a non-erasable TS edit lands |
| Bot game ↔ eval pipeline | `platform='flawchess'` games flow through the existing tiered eval queue | guest bot games stored but not auto-analyzed until promotion (existing guest exclusion — no new work) |

### External runtimes (already vendored)

| Runtime | Integration pattern | Notes |
|---------|---------------------|-------|
| Maia-3 ONNX | browser: Web Worker (`createMaiaQueue`); Node: `onnxruntime-web` wasm session, 1 thread | Node headless inference **verified working** in `gem-elo-calibration.mjs` (`createMaiaSession`/`maiaProbsForPosition`) |
| Stockfish.wasm | browser: `createWorkerPool`; Node: copy glue to `.cjs`, spawn, drive over UCI | Node recipe verified (`project_headless_stockfish_wasm_verification`); illegal `searchmoves` silently dropped, MultiPV keyed by `pv[0]` |

---

## Scaling Considerations

| Scale | Adjustments |
|-------|-------------|
| Any user count | Game is 100% client-side; server sees only a small POST per finished game. No new sustained backend load. |
| Store endpoint | Reuses the import persistence path (bulk insert + COPY positions); one game ≈ one small batch. Negligible vs. multi-hundred-game imports. |
| Calibration | Offline, single-box, hours-long sweep; unrelated to prod. Emit durable per-row TSV (stream-append, crash-safe — copy the gem harness's incremental writer). |

### Scaling Priorities

1. **First bottleneck is on-device compute**, not the server — the bot's move in blitz (3+0) on a mid-range phone. Mitigations are all client-side: human-end single-inference path, clock-scaled `maxNodes`, bullet excluded by design.
2. **Second: harness wall-clock** for a full (ELO × slider × anchor) grid. Keep games short-capped, reuse one ONNX session + one Stockfish process across positions (as the gem harness does), stream output.

---

## Sources

- Live source (HIGH): `frontend/src/hooks/useFlawChessEngine.ts`, `lib/engine/mctsSearch.ts`, `lib/engine/maiaQueue.ts`, `lib/engine/types.ts`, `lib/engine/policyTemperature.ts`, `hooks/useMaiaEloDefault.ts`, `scripts/gem-elo-calibration.mjs`, `scripts/lib/frontend-alias-hook.mjs`, `app/services/normalization.py`, `app/services/import_service.py` (`_flush_batch`), `app/models/game.py`, `app/schemas/normalization.py`, `app/services/chesscom_to_lichess.py`, `app/repositories/user_rating_anchors_repository.py`, `frontend/src/App.tsx`
- Design decisions (HIGH): `.planning/seeds/SEED-091` (5 locked decisions), `.planning/PROJECT.md` "Current Milestone: v2.3 Bot Play"
- Constraints (HIGH): `CLAUDE.md` (router convention, DB design rules, TC bucketing, PGN parsing, type-safety)
- Memory (MEDIUM): `project_headless_stockfish_wasm_verification`, `project_flawchess_engine_prior_art`

---
*Architecture research for: client-side clocked bot-play integration (FlawChess v2.3)*
*Researched: 2026-07-11*
