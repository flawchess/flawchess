# Phase 235: Train Grading Anchored to the Server Answer Key (SEED-192) - Context

**Gathered:** 2026-10-07
**Status:** Ready for planning

<domain>
## Phase Boundary

A Train reveal never contradicts itself. The server's stored best move (the "key") becomes the single
source of truth for which move is the solution on every source (SR flaw items, red herrings, sharp
filler). The phone grades the played move against that key with its own engine on both sides
(two after-move searches, same budget). On sharp puzzles a rare disagreement path re-checks with a
longer search, gives the benefit of the doubt when the disagreement survives, and records every
re-check queryably so answer-key quality can be judged from real prod solves.

Not in this phase (ROADMAP step 4, owner 2026-10-07): sharp-classification hardening, extra server
search budget, or a deeper server re-check queue. The recorded re-checks are the measurement.

### Prod sizing (60 days to 2026-10-07, prod `drill_solves`, SR items joined to `game_positions.best_move`)

| SR puzzle type | Solves | Played the key | Off-key move graded good |
|---|---|---|---|
| sharp | 1,428 | 934 (65%) | 2 (0.14%) |
| soft | 2,371 | 749 | 693 (29%) |

Herring 1,068 and sharp-filler 711 solves (no SQL-joinable key). Puzzle type inferred from
`guess` x `correct_guess`. Takeaways: the user-28 case was a PLAYED-KEY solve (the contradiction was
the arrow source, not the grade, and is likely frequent); the disagreement path is ~1 in 700 sharp
solves; a type-blind pre-POST trigger would fire on ~29% of soft solves.

</domain>

<decisions>
## Implementation Decisions

### Locked upstream (ROADMAP Phase 235 + SEED-192, owner 2026-10-07; do not re-open)
- **D-01:** Grade against the server key with the client engine on both sides: played == key ->
  GOOD with no search; otherwise compare the client's after-move search of the played move with its
  after-move search of the key, same budget. Replaces the mixed-horizon root (`esBefore`) vs
  after-move (`esAfter`) drop in `gradeMoveInner`. Never mix server and client evals in one drop.
  Applies to all sources (soft and herring included), not only sharp.
- **D-02:** Server-graded runner-up: on a sharp SR item, played == `su` is graded server-side from
  the blob's `b`/`s` evals (extend `_override_for_key_move`, empty on sharp puzzles today). No client
  search decides it.
- **D-03:** Raising the client movetime globally is rejected (Qh4/b3 swap between depth 19 and 22,
  device- and hash-dependent per SEED-130).
- **D-04:** No sharp-classification hardening or extra server search budget in this phase; a high
  confirmed-disagreement rate becomes a follow-up seed.

### Key delivery (supersedes P-01 / POOL-10)
- **D-05:** `TrainPuzzle` (pre-attempt) carries the server key move (UCI) AND `puzzle_type`. Owner
  2026-10-07: cheating is not a concern (anyone can run Stockfish in another tab, and `move_quality`
  for off-key moves is already client-asserted). `puzzle_type` is sent because it changes UX: it
  lets the D-10 re-check run before the POST on sharp puzzles only. The guess UI must still never
  DISPLAY the puzzle type or the key before the attempt. Rewrite the `TrainPuzzle` docstring (and
  the `PuzzleRevealResponse` / `SolveRequest` docstrings that cite P-01) to record the new rule and
  why. `source` stays as it is unless the planner finds the client needs it.
  — **Reversibility:** costly — a published API contract change; the frontend grading path is
  rebuilt around the pre-attempt key, so reverting means reinstating mount best-move search and the
  old grading path.
- **D-06:** Key per source: SR item = `game_positions.best_move` at the flaw ply (the existing deep
  answer key); herring = the top entry of the server-certified `herring_pool.ladder`; sharp filler =
  the solution move from `app/data/sharp_filler_puzzles.csv`.
- **D-07:** No key available (~0.4% of SR items have no `game_positions.best_move`): send `null` and
  fall back to today's behavior (client mount best names the solution, today's grading path). No
  pool change.
- **D-08:** Mount search moves from "find the best move at the root" to "evaluate the position after
  the key" during think time, so the wait after the move is unchanged (one after-move search of the
  played move, or none when played == key).

### Reveal (amends 190.1-03 D-01/D-05)
- **D-09:** The server picks every move shown (key arrow and solution card, soft `su`, herring
  ladder "also fine" moves); the phone supplies every number. The solution line = key + the phone's
  after-key PV and eval. Other displayed lines stay clamped to the key line's eval
  (`clampLineEvalToBest`, now capped by the key line) EXCEPT in a confirmed disagreement (D-15).
  190.1-03's rule that no server number is displayed still holds; only the solution MOVE now comes
  from the server.

### Disagreement re-check
- **D-10 Trigger:** `puzzle_type == sharp` (SR sharp AND sharp filler), played != key, played !=
  `su` (D-02 owns that), and the phone's 1.5s grade vs the key is **good** (owner picked "good
  only"; an inaccuracy reading is not re-checked).
- **D-11 Budget:** re-run BOTH after-move searches (key and played) at 3s each, sequentially (~6s).
  The re-check's verdict replaces the 1.5s grade whatever it says. `TRAIN_GRADING_TIMEOUT_MS`
  (8000) must be raised for this path (new named constants).
- **D-12 Wait UX:** while the re-check runs, "Checking your move…" switches to an explicit message
  along the lines of "Taking a closer look…".
- **D-13 Outcomes:** re-check still rates the played move good -> **confirmed** disagreement:
  benefit of the doubt, `move_quality = good`. Otherwise -> **resolved**: the re-check's tier is
  recorded as usual.

### Confirmed disagreement: guess, copy, numbers
- **D-14 Guess (amends P-02):** after a confirmed disagreement the position is treated as ambiguous:
  EITHER guess ("critical" or "several") earns the guess point (`correct_guess = true`). The server
  computes this, accepting the client's disagreement claim after sanity checks (puzzle is sharp,
  played != key and != `su`, claimed tier good). The weekly leaderboard (Phase 230) picks this up
  automatically through `correct_guess`. Owner rationale: crediting the move while marking a
  "several" guess wrong would contradict itself on one screen.
  — **Reversibility:** costly — changes recorded `correct_guess` values (and leaderboard points)
  for affected solves; reverting does not restore past rows.
- **D-15 Copy (owner sign-off on a new branch in LOCKED `guessFeedbackProse`):** one line for both
  guesses: **"Qh4 is the engine's first choice, but your move holds up too."** (Qh4 = key SAN).
  It replaces every "only one move works" branch on this path. The existing six strings stay verbatim.
- **D-16 Numbers:** in a confirmed disagreement the reveal shows the phone's honest evals (no clamp),
  so the played line may read above the key's.

### Disagreement record
- **D-17:** Record EVERY re-check (outcome `confirmed` and `resolved`), not only confirmed ones, so
  a review can separate phone noise (resolved) from a likely bad answer key (confirmed), per source.
- **D-18:** Storage: a new nullable JSONB column `drill_solves.recheck` (name at planner's
  discretion), NULL when no re-check ran. It travels as its own Pydantic-validated `SolveRequest`
  field (`extra="forbid"`, capped/typed values, a `v` version key), separate from `telemetry`,
  because it feeds grading and Phase 233 D-05 forbids telemetry as a grading input. Omit the column
  from the write when absent so it stays SQL NULL (memory
  `project_asyncpg_jsonb_null_vs_sql_null`).
  — **Reversibility:** costly — Alembic migration adding a column; dropping it later loses the
  collected re-check data.

### Added at plan time (owner 2026-10-07, from research open questions)
- **D-19:** `TrainPuzzle` also carries the sharp runner-up UCI (`su`), filled only for sharp SR
  items (null otherwise). Reason: at 1.5s the phone can rate `su` above the key (user-28: d1d5 vs
  Qh4), so without it playing `su` would trigger a needless ~6s re-check that D-02 then overrides.
  The D-10 trigger excludes `su` client-side. Same no-display rule as D-05.
- **D-20:** Re-check timeout or engine error: keep the 1.5s grade, send no re-check record, no
  disagreement credit.
- Research recommendations adopted: no server override for `played == key` on sharp/filler (out of
  scope); the D-15 line lives in `guessFeedbackProse` (reveal guess card), as D-15 says.

### Claude's Discretion
- Exact field names (`TrainPuzzle` key/type fields, the re-check column and its keys). Suggested
  payload: outcome, key and played ES at 1.5s and at 3s, depth reached per search, `v: 1`.
- Exact wait-message copy (D-12) within the "Taking a closer look…" intent.
- The new timeout and re-check movetime constants and where they live.
- Server sanity-check details for D-14, and how a re-check claim on a non-sharp puzzle is handled
  (ignore it rather than fail the solve, matching the telemetry drop-invalid pattern).
- Whether the solve POST should carry the 1.5s client ES values even without a re-check (not required).
- How the stale-bundle case degrades (old client ignores the new `TrainPuzzle` fields and grades the
  old way; the server must still accept its solve).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase source
- `.planning/seeds/SEED-192-train-grading-anchored-to-server-answer-key.md` — the user-28 case,
  depth table, proposed direction, breadcrumbs with line numbers.
- `.planning/ROADMAP.md` § "Phase 235" — locked scope (steps 1-4, coverage, rejected options).

### Decisions this phase amends
- `app/schemas/train.py` `TrainPuzzle` docstring — P-01 / POOL-10 (superseded by D-05).
- `app/schemas/train.py` `PuzzleRevealResponse` docstring — 190.1-03 D-01/D-05 (amended by D-09).
- `app/schemas/train.py` `SolveRequest` / `SolveResponse` docstrings — P-02, Phase 211 D-03/D-04/D-07
  (amended by D-02, D-14).
- `frontend/src/lib/trainGuessLabels.ts` `guessFeedbackProse` — LOCKED copy (new branch D-15).
- `.planning/phases/233-train-puzzle-timing-telemetry/233-CONTEXT.md` — D-01 (JSONB pattern), D-05
  (telemetry never a grading input; reason for D-18's separate column).
- `.planning/phases/230-weekly-train-leaderboards/230-CONTEXT.md` — D-01 scoring from
  `correct_guess` + `move_quality` (affected by D-14).

### Code anchors (from SEED-192 breadcrumbs)
- `app/services/train_pool.py` — `SHARP_GAP_ES`, `classify_puzzle_type`, `vetted_moves_from_pv_node`.
- `app/repositories/train_repository.py` — `_classify_and_certify_solve`, `_override_for_key_move`,
  `_compute_correct_guess`, `record_solve`.
- `app/routers/train.py:105` — `TrainPuzzle` construction.
- `app/services/sharp_filler.py`, `app/data/sharp_filler_puzzles.csv` — filler key (D-06).
- `app/models/herring_pool.py` — `ladder` (herring key, D-06).
- `app/models/drill_solve.py` — `DrillSolve` (new column D-18), `DrillSource`/`DrillGuess`/`DrillMoveQuality`.
- `frontend/src/hooks/useTrainGradingEngine.ts` — movetime/timeout constants, `startGrading`,
  `gradeMoveInner`, `clampLineEvalToBest`.
- `frontend/src/components/train/TrainSolveScreen.tsx` — grade -> solve POST, "Checking your move…".
- `frontend/src/components/train/TrainReveal.tsx`, `frontend/src/lib/trainArrows.ts` — best/solution arrow.
- `frontend/scripts/measure-train-movetime.mjs` — headless SF18 WASM harness (repro of the user-28 FEN).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_override_for_key_move` + `VettedMove`: the server already overrides the client tier for a played
  key move on soft/herring puzzles; D-02 extends the same mechanism to sharp `su`.
- `clampLineEvalToBest`: existing display clamp; re-point its cap to the key line and bypass it on
  the confirmed-disagreement path (D-16).
- Phase 233 telemetry plumbing (`SolveTelemetry`, drop-invalid wrap validator, JSONB omit-when-absent
  write): the template for the D-18 re-check field and column.
- `evalToExpectedScore` / `classifyLiveSeverity` (`frontend/src/lib/liveFlaw.ts`) with
  `INACCURACY_DROP` / `MISTAKE_DROP` from `generated/flawThresholds.ts`.

### Established Patterns
- Mount search is width 1 (Phase 211 D-05); alternatives come from the server's vetted list, never
  the client engine. The phone evaluates moves, it no longer proposes them.
- `graded_es_before/after` in `SolveResponse` exist so the board badge re-classifies from the same
  numbers as the recorded score: keep display and recorded verdict from one source.
- Single-threaded lite WASM engine: searches are sequential, never parallel.

### Integration Points
- `TrainPuzzle` payload (router) -> `useTrainGradingEngine.startGrading` (after-key search during think).
- `SolveRequest` new re-check field -> `record_solve` -> `correct_guess` / `move_quality` overrides.
- `guessFeedbackProse` and the verdict bubble read `correct_guess` + a disagreement signal.

</code_context>

<specifics>
## Specific Ideas

- Reference case: prod user 28, game 1715828 ply 52, FEN `1r2r1k1/pq3pPp/4p3/3bP1P1/4pQ2/N7/1PP2P2/2KR3R w`,
  key Qh4 (f4h4), phone pick b3, server `su` d1d5. After this phase the arrow must name Qh4.
- Bubble line (D-15): "Qh4 is the engine's first choice, but your move holds up too."

</specifics>

<deferred>
## Deferred Ideas

- A user who guessed "several" and played the key on a mis-classified sharp puzzle (the user-28
  case) still gets "wrong call"; the re-check never runs when played == key. This is answer-key
  quality (ROADMAP step 4): watch the confirmed rate, then a follow-up seed for deeper sharp
  verification before pool entry or a larger runner-up budget.
- A server-side deep re-check queue for puzzles with confirmed disagreements (SEED-192 step 3),
  possibly flipping the stored puzzle type.
- Re-checking a phone "inaccuracy" reading on sharp puzzles (owner chose "good only" for now).

</deferred>

---

*Phase: 235-train-grading-server-answer-key*
*Context gathered: 2026-10-07*
