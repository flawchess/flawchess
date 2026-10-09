---
id: SEED-192
status: closed. Resolved by Phase 235 (release #402). Closed at the v2.24 milestone close 2026-10-09.
promoted_to: Phase 235
promoted: 2026-10-07
planted: 2026-10-07
planted_during: ad-hoc prod analysis of a contradictory Train reveal (user 28, no phase; current phase 234)
trigger_when: next Train phase, or any change to Train grading / puzzle classification; plan as its own GSD phase
scope: medium (one phase: steps 1-3; step 4 is monitoring via the step-3 disagreement flag, hardening only as a follow-up)
---

# SEED-192: Train grading anchored to the server answer key (sharp-puzzle server/client mismatch)

## Why This Matters

A Train reveal can contradict itself because three DIFFERENT engine readings
feed one screen. Reported 2026-10-07 by the owner (prod user 28):

- The reveal said there is **only one good move, b3** (star arrow on b3).
- The board put a **green checkmark on the user's move Qh4** and awarded +2 move points.
- The bubble said "Wrong call, but the right move".

A user reads that as "the app says only b3 works, and also that my different
move is fine". It erodes trust in the core Train verdict (the guess is 1 of 3
points and the whole "only one vs several" framing).

### The case (prod, game 1715828, ply 52, user 28, session 1318 position 2)

FEN `1r2r1k1/pq3pPp/4p3/3bP1P1/4pQ2/N7/1PP2P2/2KR3R w` (white to move). In the
game the user blundered Rxh7?? (+4 -> 0, `game_flaws.severity` blunder,
`is_squandered`). Stored solve: `guess = SEVERAL`, `correct_guess = false`,
`played_move = f4h4`, `move_quality = GOOD`.

| Reveal element | Source | What it said |
|---|---|---|
| "Only one good move" verdict (guess graded wrong) | Server: `missed_pv_lines[0]` from the worker's MultiPV-2 search at `_NODES_BUDGET = 1_000_000` | best `b = +401`, runner-up `su = d1d5`, `s = +129`. ES gap 0.814 - 0.617 = **0.197** >= `SHARP_GAP_ES` (0.10) -> sharp. `game_positions.best_move = f4h4` (**Qh4**) |
| b3 as "the" solution (star / best arrow) | Client: phone mount search, `TRAIN_GRADING_MOVETIME_MS = 1500`, width 1 | b3 ~+2.2 (reproduced headless with the vendored SF18 lite WASM: depth 19, b3 on 3/3 fresh-hash runs) |
| Green check + 2 move points on Qh4 | Client: after-move search on Qh4, 1500ms | ~+1.9; drop vs b3's +2.2 < `INACCURACY_DROP` (0.05) -> good |

So the "only one" verdict is the SERVER's (whose one move is Qh4), but the
solution arrow is the PHONE's best move (b3). For sharp puzzles the server
serves no vetted list (`vetted_moves_from_pv_node` returns `[]` by
construction), so the client has nothing but its own search to name the move.
The key-move override in `record_solve` therefore never fires either, and the
client's tier stands.

### Deeper truth: the puzzle is probably not even sharp

Same SF18 lite WASM, MultiPV, fresh hash (`ucinewgame`) per depth:

| Depth | Qh4 | b3 | d1d5 | Top |
|---|---|---|---|---|
| 10 | (not top 2) | +71 | | Rxh7 +72 |
| 14 | **+101** | 0 | | Qh4 |
| 18 | **+272** | +160 | +133 | Qh4 |
| 22 | **+431** | +264 | +133 | Qh4 |
| 26 | **+511** | +412 | +136 | Qh4 |
| 30 | **+527** | +437 | +209 | Qh4 |

At depth 30 the Qh4 vs b3 ES gap is 0.874 - 0.833 = **0.041**: under
`INACCURACY_DROP` (b3 is a GOOD move) and well under `SHARP_GAP_ES`. The
position is really "several good moves", so the user's call was arguably right.
The server's 1M-node MultiPV-2 under-read b3 so badly it ranked d1d5 second.
Two independent defects, then:

1. **Presentation/grading mismatch (always fixable):** the verdict and the
   solution/grade come from different engines.
2. **Answer-key quality (root cause here):** the sharp classification rests on
   a 1M-node runner-up eval that can be far off.

## Proposed Direction (discussed with owner 2026-10-07)

Owner agreed the server's 1M-node answer is more trustworthy than a phone's
1.5s search and wants the server/client mismatch reduced.

**Rejected: just raise the client budget globally.** Qh4/b3 swap between
depth 19 and 22 and settle only around 26-30. Doubling phone movetime buys ~1-2
plies, costs every puzzle a longer "Checking your move...", and remains device-
and hash-dependent (SEED-130: the browser never clears its TT).

### 1. The server's move is the solution

- The reveal's best/solution arrow and "only one move works" copy name the
  server's key (`game_positions.best_move` at the flaw ply for SR items; the
  equivalent stored best for herring and sharp-filler sources), never the
  client's mount-search pick.
- **Design constraint (LOCKED P-01 / POOL-10):** `TrainPuzzle`'s docstring
  forbids any answer key in the PRE-attempt payload. Options for the phase to
  decide:
  - (a) Deliver the key in `SolveResponse` only (keeps P-01). The client grades
    as today, then reconciles once the response lands (see 2-3). Adds a
    possible second search after the POST on the disagreement path only.
  - (b) Relax P-01 for the best UCI only, arguing the client engine already
    computes a best move at mount, so devtools cheating is no easier. Weigh the
    weekly leaderboard (Phase 230) before choosing this.
  Recommendation going in: (a), unless the latency on the disagreement path
  turns out to hurt.

### 2. Grade the played move against the server's move, client engine on both sides

- Played == server key -> GOOD with no search (exact match).
- Otherwise compare the client's after-move search of the played move against
  the client's after-move search of the SERVER key, same budget. Two after-move
  searches are apples to apples; today's root-search `esBefore` vs after-move
  `esAfter` mixes horizons (`gradeMoveInner`).
- Never mix server and client evals in one drop (server +401 vs phone +190 for
  the same Qh4 would manufacture fake mistakes).
- **Server-graded runner-up (refinement, 2026-10-07):** for SR items the blob
  also stores the second-best move (`su`, with eval `s`). On a sharp puzzle
  `su` is a mistake by construction, so a played move == `su` can be graded
  server-side from the server's own `b`/`s` evals with no client search,
  keeping verdict and grade consistent. This is a small extension of the
  existing key-move override (`_override_for_key_move`), which today is empty
  on sharp puzzles. It does NOT cover moves the server never evaluated (b3
  here), so 2-3 are still needed for every other move.
- **Runner-up as a contradiction signal:** a sharp verdict claims no non-key
  move beats `su`. If the client rates the played move clearly above `su`
  (client engine on both sides, after-move searches), the server's ranking is
  demonstrably wrong (here b3 beats d1d5 at every depth >= 18). Candidate
  extra trigger for step 3.
- Herring puzzles already have a server-certified ladder; sharp-filler puzzles
  (lichess CC0) have only the solution move, but lichess verifies uniqueness
  deeply, so they are low risk.
- Under option 1(a) the after-key search can only start once the key is known;
  under 1(b) it can run during the think phase like today's mount search.

### 3. Adaptive extension only on disagreement

Trigger: sharp puzzle, played != server key, and the client says the played
move is within the good band of the key.
- Re-run both after-move searches with a longer budget (e.g. 3-4s each). Rare,
  so the UX cost is bounded. Needs a measurement of how rare.
- Still disagreeing -> benefit of the doubt: grade the move good, and change
  the copy so it does not claim "only one move works" (e.g. "The engine's first
  choice was Qh4, but your move holds up too"). Copy is LOCKED wording in
  `guessFeedbackProse`, so new branches need owner sign-off.
- Record the disagreement (a `drill_solves` flag or telemetry key) and queue
  the puzzle for a deeper server re-check (see 4).
- `correct_guess` stays server-owned (P-02). Open question for discuss: should
  a confirmed disagreement retroactively flip the guess verdict or the puzzle's
  type after the re-check?

### 4. Watch the step-3 disagreement rate; harden only if it is high

Owner decision 2026-10-07: no separate measurement or classification
hardening in this phase. The server's BEST move is strong (depth 30 agrees on
Qh4); the weak point is only the runner-up eval behind the sharp verdict, and
one case does not establish a rate.

- The step-3 disagreement flag is the measurement, for free, from real prod
  solves. Make sure it is queryable (which puzzle, played move, both client
  evals) so a later review can count it per source.
- Low rate -> server classification stays as is.
- High rate -> a follow-up seed/phase for deeper verification of sharp
  puzzles before pool entry (worker fleet has headroom, see
  project_remote_workers_cover_pool) or a larger runner-up search budget.
- The offline deep-search sample (re-search node 0 of N sharp puzzles at
  depth ~28 and count flips) stays available as a fallback if the prod signal
  is ambiguous.

## Breadcrumbs

- `app/services/train_pool.py:77`: `SHARP_GAP_ES = MISTAKE_DROP`
- `app/services/train_pool.py:262`: `classify_puzzle_type` (node-0 best vs second ES gap)
- `app/services/train_pool.py:~350`: `vetted_moves_from_pv_node` (sharp -> `[]`, so no key-move override)
- `app/services/train_pool.py:504`: `dead_band_admissible` (`[INACCURACY_DROP, BLUNDER_DROP)` exclusion)
- `app/services/train_pool.py:762`: `pool_entry_stmt`
- `app/repositories/train_repository.py:2441`: `_classify_and_certify_solve`
- `app/repositories/train_repository.py:2550`: `_override_for_key_move`
- `app/repositories/train_repository.py:2564`: `_compute_correct_guess`
- `app/repositories/train_repository.py:2924`: `record_solve` (client tier kept for off-key moves, D-04)
- `app/schemas/train.py:33`: `TrainPuzzle` (P-01: no answer key pre-attempt)
- `app/schemas/train.py:355`: `SolveResponse.vetted_moves`
- `app/services/engine.py:104`: `_NODES_BUDGET = 1_000_000`; `:650` `evaluate_nodes_multipv2`
- `frontend/src/hooks/useTrainGradingEngine.ts:78-109`: movetime / node cap / timeout constants
- `frontend/src/hooks/useTrainGradingEngine.ts:613`: `startGrading` (mount search)
- `frontend/src/hooks/useTrainGradingEngine.ts:662`: `gradeMoveInner` (root vs after-move comparison)
- `frontend/src/components/train/TrainSolveScreen.tsx:~1071, ~1289`: grade -> solve POST; `playedMoveQuality`
- `frontend/src/components/train/TrainReveal.tsx:~279`: best arrow from `gradeResult.bestLine.moves[0]`
- `frontend/src/lib/trainArrows.ts:~394`: best/played/fine arrow markers
- `frontend/src/lib/trainGuessLabels.ts:73`: `guessFeedbackProse` (LOCKED copy)
- `frontend/scripts/measure-train-movetime.mjs`: headless SF18 WASM harness (reuse for the measurement)
- Related seeds: SEED-130 (browser grade nondeterminism, uncleared hash), SEED-150 (second search cost)

## Notes

- Reproduction: run the SF18 lite WASM headless via `frontend/scripts/` (the
  `stockfish` npm package, `initEngine('lite-single')`) on the FEN above with
  `go movetime 1500 nodes 2000000` vs `go depth 30` + MultiPV 3.
- Herring puzzles are soft by construction (server-certified ladder), and
  sharp-filler puzzles (`DrillSource.SHARP_FILLER`) carry their own answer key.
  The phase must cover all three sources.
