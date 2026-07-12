---
title: Bot move pacing — confidence-based early stopping + one shared per-move budget knob
trigger_condition: Engine (mctsSearch) change with calibration downstream — NOT a small "calibration-adjacent" harness tweak. Sits BEHIND the SEED-091 clock-model decision and depends on [[SEED-095]] (deterministic grades) as a prerequisite. Fold into the SEED-091 bot-play milestone at plan time, after the clock/fixed-strength fork is settled.
planted_date: 2026-07-12
source: /gsd-explore session 2026-07-12 (Adrian — per-move UX concern surfaced while reviewing calibration-harness.mjs)
---

# SEED-096: Bot move pacing — confidence-based early stopping

Per-move UX for real players is the real concern behind "why does a bot move take up to 90s".
Today the FlawChess engine's per-move cost is a fixed node/ply budget (`FLAWCHESS_ENGINE_MAX_NODES=400`,
`FLAWCHESS_ENGINE_MAX_PLIES=8` in `useFlawChessEngine.ts`, mirrored by the calibration harness via
D-11). Time is emergent: at the full-Stockfish-grading end a single `mctsSearch` move can legitimately
take minutes. That's the strongest-desktop config the app actually ships, so the slowness is real, not
a harness artifact. See [[SEED-091-flawchess-bot-play-milestone]] (this is the "Bot think-time pacing"
default that seed flagged for plan time) and [[project_flawchess_engine_prior_art]].

## Locked direction (explore 2026-07-12)

1. **Decouple strength from think-time.** Think-time changes are *pacing*, not strength. One search
   budget → one calibrated ELO per config. Keeps Phase 168's calibration meaningful (a "1500" bot must
   stay 1500 regardless of how the move is paced).

2. **Mechanism: confidence-based (soft) early stopping — NOT a wall-clock cap.** Keep expanding MCTS
   nodes only while the decision is unsettled (top candidate's grade close to the runner-up, or the
   best move still changing as nodes are added); stop once the best move is stable with a clear margin.
   - Openings / obvious positions settle in ~1s → feel instant (the likely real pain today: waiting
     several seconds for an obvious recapture).
   - Genuinely complex positions run toward the full budget → naturally longer. ~15s is a *target*, not
     a wall. Near-strength-preserving *with tuned thresholds* (NOT "by construction" — MCTS's best move
     can still flip after apparent stability when a deeper line reveals a refutation, so the stop margin
     is a tunable trade, see point 5); small, mostly-in-simple-positions strength cost.
   - **Only as deterministic as the grades it thresholds on — [[SEED-095]] is a prerequisite.** The stop
     condition is a function of the grades, not the wall clock (good — that keeps it off the machine-
     dependent path in point 3). But it inherits whatever determinism `grade()` has, and Phase 168 proved
     the harness's Stockfish grades are NOT reliably deterministic under load ([[SEED-095]]: movetime-
     bounded search + shared hash). Early stopping is *more* sensitive to grade noise than a fixed budget —
     the STOP POINT depends on grade margins, so a small grade wobble flips the node count, which can flip
     the move. So it does not automatically preserve D-09; it can amplify the existing flakiness. Fix
     [[SEED-095]] BEFORE mirroring any stop condition into the harness, or the sweep stops being
     byte-identical-reproducible.

3. **If a hard per-move ceiling is still needed, bound it with a smaller MAX_NODES, never a wall-clock
   timer.** A wall-clock cap is machine-dependent (fires based on CPU speed / pool contention, not the
   seed) → breaks D-09 determinism and makes the measured ELO depend on which box ran the sweep. A
   node-budget cap is deterministic and reproducible.

4. **The per-move budget is ONE shared product knob (app == harness).** Whatever value ships in
   `useFlawChessEngine.ts` is what the harness must measure (D-11). Never lower the harness budget just
   to speed up the sweep while the app stays at 400 — that calibrates a bot that does not exist. Pick
   the number that makes real-player moves acceptably fast, set it in the app, and the harness inherits it.

   **Two distinct levers — don't conflate them:**
   - *Soft early-stopping* mainly helps the AVERAGE/easy positions (openings, obvious recaptures settle
     in ~1s) → this is the **per-move UX** win. Its sweep-wall-clock benefit is modest, because the
     positions that dominate sweep cost are exactly the COMPLEX ones that DON'T early-stop (they run to
     the full budget anyway).
   - *A smaller `MAX_NODES`* is a UNIFORM cut across every position → this is the **sweep wall-clock** win
     (the real lever for a long calibration run), at a uniform strength cost that then gets re-measured.

   They address different problems; pick per goal rather than assuming one change fixes both.

5. **Measure before choosing thresholds.** ~~The spike run already logs per-move `moveMs` per blend~~
   — CORRECTED 2026-07-12: that spike data never existed (168-03 deliberately never launched the
   operator grid run; only two single-move probes were on record). A bounded measurement run was done
   instead — see "Measured 2026-07-12" below. Note per SEED-091 decision #2: the full-human slider
   end uses no MCTS at all (one Maia inference, near-instant, confirmed ~0.09s/move) — so the pacing
   problem bites in the ENTIRE `blend > 0` range (see finding 1 below: not just "middle-to-Stockfish").

## Measured 2026-07-12 (bounded moveMs run — raw data in `temp/bot-run/`)

Setup: working-tree harness (with SEED-097 `--resume`), 4 Stockfish procs on a 16-core box,
`MAX_NODES=400`, bot vs maia1500. Run aborted early as too slow; the partial data already settles
the key questions.

1. **The "90s worst-case" is the FLOOR, not the tail.** blend=1 bot moves (13 samples, ELO 1100):
   min 96s, median 109s, mean 111s, max 146s. There is NO fast tail of easy positions today — a
   fixed node budget doesn't adapt to position simplicity, so every `blend > 0` move pays the full
   400 expansions (~0.28s/expansion measured). "Openings settle in ~1s" is a claim about the
   future WITH early stopping, not a property of the current engine. blend=0 measured ~0.09s/move.
2. **Mid-slider costs the same as full-Stockfish.** Per `selectBotMove`, any `blend > 0` runs the
   identical 400-node search — only `blend <= 0` skips it. (168-03-SUMMARY's "much faster
   blend=0/0.5 cells" is wrong for 0.5; only blend=0 is fast.)
3. **Consequence: 400 nodes cannot ship for bot play, so do NOT run the long calibration at 400.**
   It would calibrate a bot that will never exist. Settle the budget first. Rough sizing for a
   ~15s move target: ~50 nodes at the measured per-expansion cost — validate, don't trust.
4. **Sweep cost reality**: one `blend > 0` game ≈ 1.5–2.5h at 4 procs (~40+ bot moves × ~110s).
   The harness's printed "10.92h full grid" projection extrapolates from whatever cells ran first
   (here a blend=0 game) — wildly optimistic for any grid with `blend > 0` cells; the default grid
   is a multi-month run. Consistent with 168-02's 59-day projection.
5. **Harness fragility (fold into [[SEED-095]] scope):** one grading reply arriving later than the
   fixed 5s watchdog (`movetime 2500` + `SLACK_MS 2500`, `calibration-providers.mjs`) under load
   kills the whole sweep with a fatal `Stockfish response timeout`; `--resume` recovers only at
   cell granularity (a mid-game crash loses the in-flight game, ~1h at blend=1). Any real sweep
   needs watchdog headroom or retry-in-place, plus an operational `--resume` retry loop.

## Evaluation notes (session 2026-07-12) — add to scope at plan time

- **Concurrency is a hole in the "app == harness" principle (point 4).** The app sets
  `budget.concurrency = computePoolSize()` (device-dependent); the harness uses the Stockfish pool
  size. `mctsSearch` is deterministic only PER concurrency level and legitimately builds different
  trees at different levels. Early stopping deepens this: the stop point is evaluated on
  concurrency-dependent tree state, so effective strength becomes systematically device-dependent.
  Mitigation: evaluate the stop condition in canonical apply order, and validate tuned thresholds
  at 2–3 concurrency levels (or pin the bot's concurrency).
- **Early stopping shifts the mid-slider SAMPLING distribution, not just the argmax.** At
  `0 < blend < 1`, `selectBotMove` softmax-samples over `practicalScore`; stopping earlier changes
  the whole score vector feeding that softmax. Strength shifts at EVERY blend — the
  "near-strength-preserving" intuition is weakest in the middle of the slider.
- **No zero-cost stop rule exists here.** The visit-futility trick (stop when the most-visited move
  can't change with the remaining budget) only guarantees strength-neutrality for visit-based final
  selection; FlawChess selects by `practicalScore` (value), so any margin-based stop is genuinely
  lossy and must be tuned + re-measured (confirms point 2's "NOT by construction").

## For Phase 168 specifically

- Do **not** enforce per-game time pressure (a simulated clock) in the calibration harness — calibration
  measures fixed strength, not clock management.
- A per-move cost bound is acceptable **only** as a reduced `MAX_NODES` (deterministic) that also ships,
  or via soft early-stopping — not a wall-clock cutoff.

## Deferred / uncertain (do NOT commit to v1 here)

- **Time-control sensitivity of think-time.** Under fixed strength, TC can only move a *cosmetic pacing
  envelope* (min reveal delay / soft target), never the search budget — otherwise strength drifts by TC
  and you need per-TC calibration. Whether this is worth building is open.
- **Bot clock / clock-derived budget.** SEED-091 currently assumes a clocked bot whose "search budget
  degrades gracefully under the clock" (strength drops under time pressure) — the *opposite* of the
  fixed-strength decision above. This tension (fixed strength vs. a real blitz clock on a mid-range
  phone, where a full search can't return in 1–2s) is the thing to settle when the clocked-game
  milestone is actually planned. Left unresolved on purpose.

## Suggested shape

NOT a small "calibration-adjacent 168.1" tweak — soft early-stopping lives in `mctsSearch` (Phase 166
app-engine core, which Phase 168 deliberately never touched), so this is a change to the SHIPPED product's
move selection, with re-calibration as a downstream consequence. Scope and sequence it accordingly.

Sequencing (upstream → downstream — do NOT start at step 3):
1. **Settle the clock / fixed-strength fork first** (the deferred question below). It decides whether
   there even is "one fixed ELO per config" to preserve — pacing is downstream of this, not beside it.
   Building early-stop thresholds or a retuned `MAX_NODES` before this risks calibrating for a strength
   model the clock decision overturns.
2. **Fix [[SEED-095]] (deterministic grades)** — prerequisite for mirroring any stop condition into the
   harness without breaking D-09.
3. Then: implement soft early-stopping in `mctsSearch` and/or retune `MAX_NODES` (the moveMs
   measurement is DONE — see "Measured 2026-07-12"; ~110s/move at 400 nodes means the budget must
   drop a lot, ballpark ~50 nodes for a ~15s target), mirror the shared budget into the harness's
   D-11 constants, re-run a bounded sweep. The TC/clock questions stay with
   [[SEED-091-flawchess-bot-play-milestone]].
