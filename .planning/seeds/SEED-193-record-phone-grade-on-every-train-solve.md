---
id: SEED-193
status: planted
planted: 2026-10-08
planted_during: ad-hoc Train grading investigation (prod user 28, quick tasks 261008-ob1 / 261008-opg; no phase in flight, milestone v2.21 after Phase 235)
trigger_when: next Train phase, any further change to Train grading, or before re-running the grade audit in temp/grade-audit/
scope: small-medium (Part 1: migration + payload field + server write; Part 2: puzzle payload + client fast path, gated on a prod frequency check)
---

# SEED-193: Record the phone's grade on every Train solve, and skip the wait on server-graded moves

## Why This Matters

We cannot measure how well phones grade Train moves from the data we store.
`drill_solves.move_quality` is the EFFECTIVE tier after the server override
(`_resolve_grade` path 1 replaces the client tier for server-graded moves: the
sharp runner-up `su`, soft vetted moves, the herring good band), and the
phone's own tier is discarded (`train_repository.py` ~3337). The phone's
expected scores and search depths are stored only when a disagreement
re-check ran (`drill_solves.recheck`, zero rows in prod as of 2026-10-08).

So the only way to audit grading today is to re-run Stockfish over sampled
positions, and even then we cannot tell WHY a grade was wrong: misread key vs
misread played move, or a slow device reaching too little depth.

### Evidence that it matters (2026-10-08 audit)

Re-graded 240 distinct prod solves (last 30 days, SR + herring, 40 per stored
tier) at depth 18 with `temp/grade-audit/audit.py`; 55 server-graded rows had
to be reconstructed and excluded by hand from `missed_pv_lines` / herring
ladders. Of 185 phone-graded rows:

| Stored tier | Agrees with d18 | Should be good | Should be inaccuracy | Should be wrong |
|---|---|---|---|---|
| good | 65-87% | – | 13-35% | 0% |
| inaccuracy | 58-60% | 13-18% | – | 23-29% |
| wrong | 92-95% | 0-2% | 3-6% | – |

28 of 44 disagreements sit within 0.015 ES of a tier boundary (noise), 16 are
real misreads. Quick 261008-ob1 extended the 3 s re-check to every off-key
"inaccuracy" grade; whether that, and Phase 235's key anchoring, actually
improved accuracy is unmeasurable without this seed.

## Proposed Direction

- On every keyed solve the client already holds the 1.5 s pair (key ES,
  played ES, both depths) and its own tier before the POST. Send them as a
  `phone_grade` record mirroring `SolveRecheck`'s shape (`v`, `tier`,
  `key_es`, `played_es`, `key_depth`, `played_depth`), alongside `recheck`.
- Store it in a new nullable JSONB column on `drill_solves` (same pattern as
  `recheck` / `telemetry`; omit the column rather than writing JSON `null`,
  see the asyncpg JSONB-null gotcha), validated with `extra="forbid"`.
- Keep `move_quality` as the effective tier; the new record is the phone's
  pre-override reading, so the override rate falls out of a column compare.
- What the phone actually grades: when the played move IS the key, the phone
  runs no after-move search (`useTrainGradingEngine.ts` ~669, GOOD by
  definition), so there is no played reading to record (send the tier only,
  or omit the record). Every other move, including server-graded ones (sharp
  runner-up, soft vetted moves, herring good band), IS graded by the phone's
  1.5 s search: the phone knows only `key_move_uci` / `runner_up_uci` before
  the solve (vetted moves arrive in `SolveResponse`), and the runner-up only
  skips the re-check, not the grading. Those discarded phone grades on
  server-graded moves are the best accuracy signal available, since the
  server's deep tier for the same move is the ground truth, free of charge.
- Optional: an engine/device hint (wasm build, threads, nodes reached) only
  if cheap; `telemetry.client` already gives mobile vs desktop.
- Afterwards, rewrite `temp/grade-audit/` as a query + depth-18 spot check
  instead of the current reconstruct-and-exclude workflow.

## Part 2: instant verdict for server-graded moves

Today the phone runs its 1.5 s after-move search on every non-key move,
including moves the server grades itself and whose phone tier `_resolve_grade`
then discards. The user waits ~1.5 s ("Checking your move…") for a grade that
is thrown away. The search is NOT pure waste: it supplies the "Your move"
reveal card's line and eval (`GradeResult.playedLine`), and the server's
`VettedMove` wire shape carries only UCI + tier, no PV or eval
(`app/schemas/train.py` ~423).

Direction:

- Send the server-graded moves (soft vetted, herring good band, sharp
  runner-up) with their tiers in the puzzle payload, read only after the move
  like `key_move_uci` / `runner_up_uci` today (Phase 235 D-05). The key is
  already on the wire, so this exposes nothing new.
- When the played move is in that set, show the verdict immediately from the
  server tier and POST without waiting.
- Keep the after-move search running in the background to fill the "Your
  move" card, and record its tier/ES/depth per Part 1: on exactly these moves
  the server's deep tier is the ground truth, so Part 1 gets its best accuracy
  signal without any extra wait.
- Before planning, measure how often a played move is a non-key server-graded
  move in prod (my stratified audit sample had ~23% such rows, which is NOT a
  population rate). If it is rare, Part 2 may not be worth its complexity.

## Breadcrumbs

- `app/schemas/train.py` `SolveRecheck` (~259): shape and validator precedent.
- `app/models/drill_solve.py` `recheck` (~205) / `telemetry`: JSONB column precedent.
- `app/repositories/train_repository.py` `_resolve_grade` (~2840), `record_solve`
  claim_values (~3337-3361): where the client tier is consumed and discarded.
- `frontend/src/components/train/TrainSolveScreen.tsx` `gradeAndSolve` (~1120):
  the grade is in hand before `solvePuzzle`; `frontend/src/lib/trainRecheck.ts`
  `buildRecheckPayload`: payload builder to mirror.
- `frontend/src/hooks/trainGradingSupport.ts` `LastPlayedSearch` / `GradingAnchor`:
  where the 1.5 s ES and depths live.
- Audit tooling: `temp/grade-audit/` (`audit.py`, `report.py`, `sample.txt`,
  `server_graded.txt`), gitignored.

## Notes

- Not a grading change: no new engine search, no wait time, no scoring effect.
- Re-run the audit on post-Phase-235 solves about two weeks after 2026-10-08
  regardless; this seed makes the next one a query instead of a Stockfish run.
