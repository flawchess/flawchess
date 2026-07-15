# Pitfalls Research

**Domain:** Client-side clocked bot-play + synthetic-game storage + headless calibration harness, added to an existing React 19 / FastAPI / PostgreSQL chess-analysis app (FlawChess v2.3 "Bot Play")
**Researched:** 2026-07-11
**Confidence:** HIGH (grounded in the actual codebase: `mctsSearch.ts`, `normalization.py`, `query_utils.py`, `eval_queue_service.py`, `useMaiaEngine.ts`, `SEED-091`)

This file is scoped to mistakes specific to bolting clocked bot-play onto THIS app. Generic web-dev advice is omitted. Every pitfall names a warning sign, an app-specific prevention, and the owning stage. Stage names are logical (the roadmap isn't written yet): **Setup/Engine-wiring**, **Clocked-board/Lifecycle**, **Resume**, **Store-endpoint/Normalization**, **Calibration-harness**, **Perf-polish**.

---

## Critical Pitfalls

### Pitfall 1: Timer drift from `setInterval` as the clock source of truth

**What goes wrong:**
The chess clock is decremented by a fixed amount every `setInterval(…, 100)` tick. `setInterval` does not fire on a precise schedule — it drifts under main-thread contention (Maia/Stockfish inference, React re-renders, GC), and browsers coalesce/clamp it. After a 5-minute blitz game the displayed clock can be off by seconds, unacceptable when flagging decides the stored, calibrated-on result.

**Why it happens:**
`setInterval` is the obvious first reach. Its callback frequency is a hint, not a guarantee; accumulated per-tick subtraction compounds every missed/late fire.

**How to avoid:**
Never subtract a fixed delta per tick. Store an absolute `turnStartedAt = Date.now()` (or `performance.now()`) plus `msRemainingAtTurnStart` when each side's turn begins; on every render compute `displayed = msRemainingAtTurnStart - (Date.now() - turnStartedAt)`. The interval drives *repaint only*, never the value. On move commit, snapshot true remaining time once and add the increment. This mirrors the discipline `mctsSearch.ts` already enforces ("no `Date.now()`/`performance.now()` anywhere in this file" — timing lives outside the search).

**Warning signs:**
Clock and wall-clock diverge on a running game; two clocks that don't sum to (start − elapsed); flags firing at displayed time ≠ 0.

**Phase to address:** Clocked-board/Lifecycle (build the clock as a `Date.now()`-delta model from day one; retrofitting is painful).

---

### Pitfall 2: Backgrounded/inactive-tab throttling — clock keeps real time but bot compute stalls (the seed's flagged edge case)

**What goes wrong:**
When the tab is hidden or the phone screen locks, browsers clamp timers (≥1000 ms, often frozen on mobile) AND throttle/suspend Web Workers — which is exactly what the Maia ONNX worker and Stockfish WASM worker are. If the bot is "thinking" when the tab backgrounds, its move computation stalls. Meanwhile a correct `Date.now()`-delta clock keeps elapsing, so the **bot can flag itself while backgrounded**, or the human returns to a game that silently timed out. Naively pausing compute but not the clock bleeds the human's clock while they're away instead.

**Why it happens:**
Timers and workers are throttled by different, platform-dependent rules; developers test only on a focused desktop tab where neither throttle triggers.

**How to avoid:**
Make the Page Visibility API a first-class game state. On `visibilitychange → hidden`: pause the clock (record the instant) and defer/mark any in-flight bot search as "must not count toward flag." On `→ visible`: resume from the recorded pause instant, do NOT bill away-time to either player (SEED-091 decision 4 commits to "clock paused while away"). "Tab hidden while bot is thinking" = freeze; on return resume or recompute the search. This must work within a single live session, distinct from localStorage Resume.

**Warning signs:**
Refocusing shows a flagged/decided game; bot moves land seconds after refocus; mobile users report the bot never moving after screen-lock.

**Phase to address:** Clocked-board/Lifecycle (visibility-driven pause is core, not polish; Perf-polish only tunes the search-budget side).

---

### Pitfall 3: Argmax-practical is deterministic → same game every time, and stronger than the nominal ELO

**What goes wrong:**
`mctsSearch` is documented as **deterministic per concurrency level** (bit-identical repeated runs). If the bot always plays the argmax practical move, every game at a given (ELO, color, opening) is *identical* — trivially exploitable, boring, and useless for calibration (no distribution to fit). Worse, "argmax over Maia-predicted human moves" is a player who *never makes the mistakes Maia predicts*, so it plays far above nominal ELO (SEED-091 decision 2). Shipping argmax at the human end silently mis-rates the bot by hundreds of Elo.

**Why it happens:**
The engine's analysis surface returns one best practical move; reusing it verbatim for play is the path of least resistance.

**How to avoid:**
ELO-faithfulness comes from **sampling**, not argmax. Full-human: draw from the temperature-reshaped Maia root policy (Pitfall 5). Full-stockfish: argmax the practical score. Between: practical-score-weighted sampling with slider-controlled sharpness (`policyTemperature`), collapsing to argmax only at the extreme. Seed the RNG per move from game state if you want *replay* determinism, but never make the *policy* a point mass except at the stockfish extreme. Test that a full-human position yields a move *distribution* over many samples, not one move.

**Warning signs:**
Two games with identical settings/opening play move-for-move; a "1200" bot beating 1500s consistently; near-zero result variance in self-play.

**Phase to address:** Setup/Engine-wiring (the move-selection function is the heart of the milestone).

---

### Pitfall 4: Running a full MCTS at the full-human end when one Maia inference is required

**What goes wrong:**
The natural implementation calls `mctsSearch` for every move regardless of slider. At full-human that runs the whole tree (many `policy()` + batched `grade()` expansions) just to then sample — wasting a second+ per move on a phone, blowing the blitz budget, and defeating SEED-091 decision 2 ("**no MCTS needed — one Maia inference per move**").

**Why it happens:**
A single `search(fen, budget)` entry point is convenient; the slider becomes just a budget parameter instead of a fork in the algorithm.

**How to avoid:**
Branch on the slider *before* choosing the compute path. Full-human (and a band near it) = one `providers.policy(fen, elo, side)` → `applyPolicyTemperature` → sample. Engage `mctsSearch` only as the stockfish weight rises and search actually changes the move. Reuse `applyPolicyTemperature` / `truncateAndRenormalize` from `mctsSearch.ts` so play-side reshaping matches analysis semantics. Budget-scale `maxNodes` with the slider so the human end is genuinely cheap.

**Warning signs:**
Flat per-move latency across the slider; profiler shows Stockfish `grade()` calls at full-human; blitz on a mid phone can't answer in 1–2 s.

**Phase to address:** Setup/Engine-wiring.

---

### Pitfall 5: Botched sample↔argmax blend — reshape side, illegal/degenerate handling, temperature direction

**What goes wrong:**
Several subtle traps in the sampler:
- **Reshape on the wrong side.** `mctsSearch` reshapes only when `sideMatchesMover(leaf.side, rootMover)` and short-circuits at the default temperature. For play the bot only moves on its own side; copying the analysis reshape naively can reshape opponent replies or skip reshaping at the default temperature, giving a different distribution than the sampler expects.
- **Illegal candidates.** Maia can emit a UCI illegal in the actual position; `mctsSearch` drops these via `applyUciMoveFen(...) === null` (WR-07). A sampler that plays a raw sampled UCI will occasionally attempt an illegal move → crash/forfeit. Filter to legal moves *before* renormalizing.
- **Degenerate empty policy** (WR-04): `mctsSearch` closes such a node as a dead end. A sampler must fall back to a legal move (e.g. uniform over `chess.js` legal moves) rather than throw or pass.
- **Temperature direction.** High temperature should *flatten* toward weaker/varied play; low should sharpen to the mode. Inverting makes the "weak" bot play sharper than the "strong" one.

**Why it happens:**
The sample path is new code lacking the guardrails baked into `mctsSearch`; the reshape/legality/renormalize order is easy to get wrong.

**How to avoid:**
Fixed order: `policy()` → drop illegal (via `applyUciMoveFen`/chess.js) → apply temperature → renormalize → sample. Reuse `applyPolicyTemperature` and `truncateAndRenormalize` verbatim. Unit-test: illegal-UCI injection dropped; empty policy falls back to a legal move; temperature monotonicity (higher T → higher entropy → more distinct moves).

**Warning signs:**
Rare "illegal move" crashes; bot passes/hangs; higher-temperature bots play better; NaN priors after renormalizing an all-illegal set.

**Phase to address:** Setup/Engine-wiring.

---

### Pitfall 6: The "reuse the existing normalization path" trap — there is no PGN→game normalizer

**What goes wrong:**
SEED-091 says "reuse the existing normalization path," which reads as "hand it a PGN and get a `games` row." But `app/services/normalization.py` has only `normalize_chesscom_game(game: dict, …)` and `normalize_lichess_game(game: dict, …)` — both parse **raw platform JSON**, not PGN, and both hard-return `platform="chess.com"`/`"lichess"`. `Platform` is `Literal["chess.com", "lichess"]`. There is no `platform="flawchess"` path and no PGN→`NormalizedGame` function. A literal reuse won't compile.

**Why it happens:**
"Normalization" sounds format-agnostic; the shared downstream (position hashing, `find_opening`, `_flush_batch`) *is* reusable, but the front door isn't.

**How to avoid:**
Add `normalize_flawchess_game(pgn, user_id, bot_settings, player_rating, …) -> NormalizedGame` that:
- Widens the `Platform` Literal to include `"flawchess"` (and update the `game.platform` column comment / any CHECK per the DB rules; the column is `String(20)`).
- Parses the PGN with python-chess (per CLAUDE.md: per-game try/except, `board.board_fen()` for positions, Standard-only), extracts the client-set result/termination, reuses `find_opening(pgn)` for opening tagging, maps client end-reasons to the `Termination` Literal.
- Feeds the same `NormalizedGame` into the *existing* position-hashing + `_flush_batch` path (that part IS the safe reuse).

**Warning signs:**
Type errors on `platform="flawchess"`; passing a PGN string into `normalize_chesscom_game`; positions not hashed because you bypassed `_flush_batch`.

**Phase to address:** Store-endpoint/Normalization.

---

### Pitfall 7: Forgetting `[%clk]` annotations — time-management stats silently exclude every bot game

**What goes wrong:**
FlawChess Time Management analytics (clock advantage/deficit at endgame entry, flag rates, time-pressure-vs-performance) read per-move clocks from `[%clk H:MM:SS]` PGN comments. A bare PGN stores fine and shows in the Library, but is **silently invisible** to every time-management stat (SEED-091 decision 1 warns of this). No error, no empty state — just missing data found months later.

**Why it happens:**
`chess.js` `.pgn()` does not emit `[%clk]`; the clock lives in React state, not the move objects. Easy to omit because everything else works.

**How to avoid:**
The client must write `{[%clk H:MM:SS]}` after every move using the true post-move remaining time (the snapshot Pitfall 1 takes on commit). Add a store-endpoint validation that flags a bot PGN missing `[%clk]`, and a normalization test asserting the flawchess path populates the clock columns. Match the format the existing v1.1 clock-import path already parses.

**Warning signs:**
Bot games absent from Time Management charts but present in the Games tab; clock columns NULL for `platform='flawchess'` rows; `[%clk` grep on the stored PGN returns nothing.

**Phase to address:** Store-endpoint/Normalization (validation gate) + Clocked-board/Lifecycle (client emission).

---

### Pitfall 8: Synthetic `platform_game_id` / unique-key collisions

**What goes wrong:**
`games` enforces uniqueness on `(user_id, platform, platform_game_id)`. Real platforms supply that id; a synthetic `flawchess` game has none. A weak id (timestamp, counter) collides on fast games or double-submit → the second POST 500s on the unique constraint, or silently overwrites. Guests replaying across devices can collide too.

**Why it happens:**
The id is an afterthought; "current timestamp" feels unique enough until it isn't.

**How to avoid:**
Mint `crypto.randomUUID()` client-side at *game start*, persist it in the localStorage game state (so a resumed-then-finished game keeps one id), send it as `platform_game_id`. Make the store endpoint idempotent: on unique-constraint conflict for the same `(user, platform, id)`, treat as already-stored and return 200. This also makes Resume safe (Pitfall 12) — one game, one id, one row.

**Warning signs:**
500s under fast play; duplicate rows for one game; a resumed game creating a second row.

**Phase to address:** Store-endpoint/Normalization (id contract) + Clocked-board (id minted at start).

---

### Pitfall 9: NULL player rating throws away the calibration data point

**What goes wrong:**
Storing the human's rating as NULL "because it's a bot game" discards exactly the signal calibration needs (SEED-091 decision 5: "every game saved with a NULL player rating is a calibration data point thrown away"). The bot's nominal ELO is known; without a paired player rating there's nothing to fit result-vs-strength against.

**Why it happens:**
There's no opponent rating on a casual bot game by default; the human never entered one.

**How to avoid:**
At save time derive a lichess-scale, TC-bucket-matched player rating using the **existing** `useMaiaEloDefault` machinery (it already solves this for the slider default): user's lichess rating for that TC bucket if recent games exist, else converted chess.com. Store it in the human's side rating column, bot nominal ELO in the opponent side. NULL only when the user has zero imported games. Persist the bot's full settings (nominal ELO, slider, TC) on the row for the later curve-fit milestone. Carry the ±100–150 conversion-error caveat into any strength claim — fine for fitting across many games, not for a precise ELO from ten.

**Warning signs:**
`platform='flawchess'` rows with NULL player rating despite imported games; missing bot-settings columns; calibration query returning mostly NULLs.

**Phase to address:** Store-endpoint/Normalization + Setup/Engine-wiring (compute where the slider default already does).

---

### Pitfall 10: The bot adapting to the player corrupts calibration

**What goes wrong:**
A tempting "fun" feature — easing off when the human is losing, ramping up when winning — destroys the one property calibration requires: a **fixed, symmetric strength to measure** (SEED-091 decision 5). If effective strength depends on game state, there's no single ELO to fit and stored games become uninterpretable.

**Why it happens:**
Adaptive difficulty is a common "good UX" instinct; the engine's per-side `budget.elo` makes it easy to nudge.

**How to avoid:**
The bot plays its configured ELO on **both** sides, symmetric, constant for the whole game. No in-game adaptation. Encode as an invariant: `budget.elo[bot_side]` set once at game start from the setup screen, never mutated. Easier bots = a *new bot card at lower ELO*, not runtime adaptation.

**Warning signs:**
Any code reading the current score/result to adjust `budget`; players reporting the bot "goes easy"; self-play variance correlating with position eval.

**Phase to address:** Setup/Engine-wiring.

---

### Pitfall 11: Guest bot games look "broken" because the eval pipeline excludes guests

**What goes wrong:**
Guests are first-class `User` rows and can play + save bot games (SEED-091: no beta gate). But `eval_queue_service.py` excludes guests from **automatic** analysis (`WHERE u.is_guest = false` for bulk; `AND (u.is_guest = false OR ej.tier = 1)` on claim). So a stored guest bot game shows in the Library but never auto-analyzes → the eval-based surfaces (mistake dots, expected-score chart, "% analyzed" coverage badge) stay empty. A guest sees a perpetually "unanalyzed" game and thinks it's broken.

**Why it happens:**
The exclusion is intentional (guests don't get free bulk Stockfish), but bot-play makes guests *create analyzable content* for the first time, surfacing the gap in a new place.

**How to avoid:**
Set expectations in UI: for guests show the coverage/"% analyzed" caveat and a "promote your account to analyze this game" affordance (reuse the existing guest-banner/promotion pattern) rather than a bare empty chart. Note the nuance: guests CAN still trigger a **tier-1 explicit** analysis (`OR ej.tier = 1`), so an on-demand "Analyze this game" button may work for a guest even though bulk drain skips them — decide which behavior you want and match the copy. Do NOT "fix" this by removing the guest exclusion (that opens unbounded guest Stockfish load and reverts QUEUE-08).

**Warning signs:**
Guest Library shows bot games at 0% analyzed with no explanation; "my bot game won't analyze" reports; a proposal to drop `is_guest = false` from the drain.

**Phase to address:** Store-endpoint/Normalization (behavior) + a small UI caveat in Clocked-board/Library surfacing.

---

### Pitfall 12: localStorage resume corrupting the clock or double-storing

**What goes wrong:**
Two failure modes around SEED-091 decision 4:
- **Clock bleed across the gap.** If the persisted state stores a live `Date.now()` anchor, the *away* elapsed time is billed on resume → the human returns already flagged. The clock must persist as *paused remaining ms*, not a running anchor.
- **Double-store / ghost rows.** A finished, POSTed game whose localStorage entry wasn't cleared offers "Resume game?" on a finished game, or a re-finish re-POSTs. With a fresh id this creates duplicate rows.

**Why it happens:**
Serializing "current" clock state is easier than serializing "paused" state; clearing localStorage on successful store is easy to miss.

**How to avoid:**
Persist the *paused* clock model (remaining ms per side, whose move, no running anchor) every move. On resume the clock stays paused until the human's first move. Clear the localStorage game only after a confirmed 2xx from the store endpoint (the idempotent id from Pitfall 8 makes an accidental re-POST harmless). Never offer resume for a terminal-result state.

**Warning signs:**
Resumed games start with time already burned; "Resume game?" on a finished game; duplicate `flawchess` rows after a resume.

**Phase to address:** Resume.

---

### Pitfall 13: Maia ONNX won't run headlessly in Node at harness-viable speed (the open feasibility item)

**What goes wrong:**
The browser Maia path uses **onnxruntime-web** (`webgpu`/`wasm` EP) loaded via `importScripts()` in a classic Worker (`useMaiaEngine.ts`). That path doesn't exist in Node — no DOM worker, no webgpu, different `.wasm` loading. The harness needs **onnxruntime-node** (native): a different package, different EPs, different numerics. If nobody validates this early, the calibration harness (a committed deliverable) can stall late. SEED-091 flags this as the open question; project memory notes "Maia repro needs onnxruntime==1.20.1".

**Why it happens:**
"It runs in the browser, Node is just JS" hides that the runtime, EP, and model-loading are entirely different in Node.

**How to avoid:**
De-risk with a **feasibility spike first** (before committing harness scope): load the Maia ONNX model under `onnxruntime-node`, run one inference, measure per-inference latency and games/hour. Pin `onnxruntime-node` to a version compatible with the model opset (memory: 1.20.1). Reuse the framework-agnostic encoding (`maskAndSoftmax`, `maiaEncoding.ts`); only session creation/run differs. Stockfish-WASM-in-Node is already verified (project memory), so the anchor side is lower risk. If Node inference is too slow, fall back to a headless-browser harness (Playwright) driving the real worker — decide that fork *before* building the grid runner.

**Warning signs:**
Spike shows seconds-per-inference in Node; `onnxruntime-node` version incompatible with the model; numerics diverge enough from the browser that anchor results don't transfer.

**Phase to address:** Calibration-harness (gate on a spike; make it the first task).

---

### Pitfall 14: Pure self-play ELO with no external anchor

**What goes wrong:**
Estimating strength by playing the bot against itself yields a *self-consistent but unanchored* number — it says nothing about lichess/chess.com Elo. SEED-091 is explicit: "pure self-play ELO without external anchors is unreliable — don't bother."

**Why it happens:**
Self-play is the easiest harness (no external opponents to wire).

**How to avoid:**
Always play against **known-strength anchors**: raw Maia 1100–1900 in argmax mode (published lichess-rating behavior) and Stockfish skill levels. Fit the bot's Elo relative to those anchors across the coarse (ELO × slider) grid. Self-play is fine only as a plumbing smoke test, never the strength number. Beware strata-sampling bias — cover the grid cells evenly (each ELO × slider cell gets enough anchored games), or the map is confident where you happened to sample and blank elsewhere.

**Warning signs:**
A "measured ELO" produced with no anchor opponent in the loop; strength numbers untied to any external scale; a grid where some cells have 100 games and others 2.

**Phase to address:** Calibration-harness.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Call `mctsSearch` for every move regardless of slider | One code path | Wastes phone compute at the human end (Pitfall 4); flat latency; misses blitz budget | Never — branch on the slider |
| `setInterval`-decrement clock | Trivial to write | Drift; flag at wrong time; corrupt stored result (Pitfall 1) | Never — use `Date.now()` deltas |
| Bare PGN without `[%clk]` | Simpler client serialization | Time-management stats silently drop every bot game (Pitfall 7) | Never — clocks are a headline feature |
| NULL player rating on save | Skip the conversion call | Every game a lost calibration point (Pitfall 9) | Only when the user has zero imported games |
| Timestamp-based `platform_game_id` | No UUID plumbing | Collisions / duplicate rows / non-idempotent store (Pitfall 8) | Never — `crypto.randomUUID()` at game start |
| Self-play strength number | No anchors to wire | Unanchored, meaningless ELO (Pitfall 14) | Only as a plumbing smoke test |
| Defer the Node-ONNX check to harness build | Faster to "start" the harness | Late discovery blocks a committed deliverable (Pitfall 13) | Never — spike first |
| Remove `is_guest` exclusion to "fix" guest analysis | Guest bot games auto-analyze | Unbounded guest Stockfish load; reverts QUEUE-08 | Never — UI caveat + tier-1 explicit |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Existing import/normalization pipeline | Assuming a PGN→game path exists; passing PGN to `normalize_chesscom_game` | New `normalize_flawchess_game(pgn,…)` → `NormalizedGame`; widen `Platform` Literal to `"flawchess"`; reuse only the downstream hashing/`_flush_batch` (Pitfall 6) |
| `mctsSearch` / `useFlawChessEngine` | Reusing analysis argmax verbatim for play (deterministic, too strong) | Sample the reshaped Maia policy at the human end; argmax only at the stockfish extreme (Pitfalls 3–5) |
| `applyPolicyTemperature` / `truncateAndRenormalize` | Re-implementing reshape/renormalize in the sampler | Import the exact primitives; drop illegal UCIs before renormalizing |
| Maia inference in Node | Expecting the browser onnxruntime-web + Worker path to work | `onnxruntime-node` (pin ~1.20.1); reuse `maiaEncoding`/`maskAndSoftmax`; spike before committing (Pitfall 13) |
| Game filters (`apply_game_filters`) | Bot games leaking into opening/endgame/global analytics | `is_computer_game=True` + `platform='flawchess'`; verify the default posture excludes bots (opponent_type='human' and/or native-platform default) while Bots page + Library Games explicitly include them |
| Eval queue (`eval_queue_service`) | Expecting guest bot games to auto-analyze | Guests excluded from bulk (`is_guest=false`); tier-1 explicit allowed (`OR ej.tier=1`); set UI expectations (Pitfall 11) |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Full MCTS at full-human on a phone | 1+ s/move, blitz budget blown | One Maia inference at the human end (Pitfall 4) | Mid-range phones on blitz (3+0) |
| Fixed search budget under clock pressure | Bot flags itself; UI jank | Scale `maxNodes` from remaining clock; degrade gracefully; bullet excluded by design for headroom | Low remaining time on slow devices |
| Worker throttling in background tab | Bot never moves after screen-lock; flags | Page Visibility pause of clock + search (Pitfall 2) | Any mobile screen-lock / tab switch |
| Main-thread contention (inference + React + clock) | `setInterval` drift, dropped frames | Clock as a `Date.now()` delta (repaint-only interval); inference in workers | Every game once inference runs |
| Harness games/hour too low | Grid takes days | Measure Node inference latency in the spike; cap grid coarseness; parallelize anchor matches | Fine grid × slow Node ONNX |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Trusting the client-submitted result/rating blindly | A crafted POST stores fabricated wins / inflated ratings, poisoning calibration and stats | Server-side sanity-check the PGN (replay with python-chess; claimed result must match the terminal position/termination); derive/clamp the player rating server-side; keep bot games `is_computer_game=True` so they can't masquerade as rated human games |
| Unbounded store endpoint | Spam rows / storage abuse (esp. guests) | Rate-limit the store endpoint per user (reuse existing guest IP rate-limit patterns); idempotent on `platform_game_id` |
| Exposing internal hashes in the store response | Violates the app invariant (API returns FEN, never Zobrist) | Return FEN/game metadata only, per CLAUDE.md |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Instant bot replies | Feels robotic; never burns the bot's clock; unrealistic | Pace move delay from the bot's remaining clock (SEED-091 flagged default) |
| Guest bot game shows 0% analyzed, no explanation | User thinks the feature is broken | Coverage caveat + promote-to-analyze affordance (Pitfall 11) |
| Bot games contaminating "real" rating/analytics views | Endgame-ELO timeline / opening stats skewed by practice games | Default analytics exclude bots; Bots page + Library Games opt them in (the "uncontaminated by construction" design) |
| Missing draw-offer / resign / flag affordances | Game feels unfinished | Ship game-end detection + resign + flag + draw offers + move sounds (v1 IN); premove/takeback explicitly OUT |
| Clock reads non-zero at the moment of a flag | Confusing/incorrect result | Flag off the `Date.now()`-delta model, not the last painted value (Pitfall 1) |

## "Looks Done But Isn't" Checklist

- [ ] **Move selection:** Full-human position yields a *distribution* over many samples, not one repeated move (Pitfall 3); illegal-UCI injection dropped, empty policy falls back to a legal move (Pitfall 5).
- [ ] **Clock:** Correct after a 5-min game vs wall clock; pauses on `visibilitychange`; flags at displayed 0 (Pitfalls 1–2).
- [ ] **Backgrounded bot:** Hide the tab while the bot is thinking — no self-flag, resumes on return (Pitfall 2).
- [ ] **`[%clk]`:** Stored PGN has per-move clock comments; flawchess normalization populates clock columns; game appears in Time Management stats (Pitfall 7).
- [ ] **Storage:** `platform="flawchess"` compiles (Literal widened); positions hashed via `_flush_batch`; unique `platform_game_id` per game; store endpoint idempotent (Pitfalls 6, 8).
- [ ] **Player rating:** Non-NULL when the user has imported games; bot nominal ELO in opponent column; bot settings persisted (Pitfall 9).
- [ ] **Analytics posture:** Bot games excluded from opening/endgame/global defaults, included in Bots + Library Games (contamination check).
- [ ] **Guest:** Guest can play + save; Library shows an honest analyzed-coverage caveat, not a bare empty chart (Pitfall 11).
- [ ] **Resume:** Clock persists as *paused remaining*, not a running anchor; localStorage cleared only after 2xx store; no resume for terminal states (Pitfall 12).
- [ ] **Harness:** Maia runs under `onnxruntime-node` at measured games/hour; results anchored to raw-Maia/Stockfish, never pure self-play; grid cells evenly sampled (Pitfalls 13–14).

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| `[%clk]` omitted (games already stored) | MEDIUM | Clocks aren't recoverable post-hoc (they only existed client-side); fix emission going forward; affected rows stay excluded from time stats permanently. This is why the client-side gate matters most. |
| Deterministic argmax shipped | LOW | Swap the move-selection function to the sampler; no data migration (past games are just repetitive, not corrupt) |
| NULL player ratings stored | MEDIUM | Backfill is lossy (no save-time snapshot); best-effort re-derive from the user's rating history at `played_at`; prevention (compute at save) is far cheaper |
| `platform_game_id` collisions / dupes | MEDIUM | Enforce the unique constraint + idempotency; dedupe existing dupes by `(user, platform, id)` keeping the completest row |
| Node-ONNX infeasible | HIGH (late) / LOW (if spiked early) | Pivot to Playwright headless-browser harness driving the real worker; cheap only if discovered in the spike |
| Guest exclusion "fixed" by dropping the filter | MEDIUM | Revert; re-instate `is_guest=false` + tier-1 carve-out and use UI copy instead |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| 1 Timer drift | Clocked-board/Lifecycle | 5-min game clock matches wall clock within ~50 ms |
| 2 Background throttle / hidden-while-thinking | Clocked-board/Lifecycle | Hide-tab test: no self-flag, resumes on focus |
| 3 Deterministic argmax | Setup/Engine-wiring | Sampled-move distribution test at full-human |
| 4 Full MCTS at human end | Setup/Engine-wiring | Profiler: one `policy()`, no `grade()` at full-human; blitz <2 s on mid phone |
| 5 Sample/argmax blend correctness | Setup/Engine-wiring | Illegal-UCI drop + empty-fallback + temperature-monotonicity tests |
| 6 No PGN normalizer | Store-endpoint/Normalization | `normalize_flawchess_game` unit test → valid `NormalizedGame`; positions hashed |
| 7 Missing `[%clk]` | Store-endpoint/Normalization + Clocked-board | Stored PGN has `[%clk]`; game appears in Time Management |
| 8 Synthetic id collisions | Store-endpoint/Normalization | Double-submit returns 200, one row; UUID per game |
| 9 NULL player rating | Store-endpoint + Setup/Engine-wiring | Row rating non-NULL when user has games; bot settings present |
| 10 Bot adaptation | Setup/Engine-wiring | No code path reads score to mutate `budget.elo`; symmetric |
| 11 Guest eval exclusion | Store-endpoint + Library UI | Guest game shows analyzed-coverage caveat, not empty chart |
| 12 Resume clock/dupe | Resume | Resume starts paused; localStorage cleared post-2xx; no terminal-state resume |
| 13 Node ONNX feasibility | Calibration-harness (spike first) | Spike measures inference latency + games/hour under `onnxruntime-node` |
| 14 Unanchored / biased self-play | Calibration-harness | Strength fit references raw-Maia/Stockfish anchors; grid cells evenly sampled |

## Sources

- SEED-091 (`.planning/seeds/SEED-091-flawchess-bot-play-milestone.md`) — locked decisions + "Defaults flagged during the session" (HIGH: the author's own risk enumeration)
- `.planning/PROJECT.md` "Current Milestone: v2.3 Bot Play" (HIGH)
- Codebase (HIGH): `frontend/src/lib/engine/mctsSearch.ts` (determinism per concurrency, WR-04/WR-07 illegal/degenerate handling, temperature reshape gating), `app/services/normalization.py` + `app/schemas/normalization.py` (platform Literal, no PGN path, `NormalizedGame`), `app/repositories/query_utils.py` (opponent_type/platform filters), `app/services/eval_queue_service.py` (guest exclusion + tier-1 carve-out), `frontend/src/hooks/useMaiaEngine.ts` (onnxruntime-web webgpu/wasm + Worker path)
- CLAUDE.md Critical Constraints (HIGH): `[%clk]`/clock handling, `board.board_fen()`, Standard-only, API never exposes hashes, DB FK/unique/enum rules
- Project memory (MEDIUM): `project_headless_stockfish_wasm_verification` (Stockfish-WASM-in-Node verified), Maia repro needs `onnxruntime==1.20.1`; `project_frontend_beta_gating_source` (guest/profile gating)
- Browser platform behavior (HIGH, well-established): Page Visibility API, background timer clamping, Web Worker throttling on hidden/mobile tabs

---
*Pitfalls research for: client-side clocked bot-play + synthetic-game storage + headless calibration harness (FlawChess v2.3)*
*Researched: 2026-07-11*
