---
id: SEED-170
status: open
planted: 2026-09-27
planted_during: FlawChess engine code review (session 2026-09-27); behavior-neutral findings shipped separately as a /gsd-quick
trigger_when: next engine milestone, or any time bot-move latency or analysis-board suggestion quality is the priority
scope: three search-behavior changes in frontend/src/lib/engine (root-child comparability before early stop, round-underfill in selectPath, findability fallback term) plus an optional non-root candidate cap, gated by a before/after measurement including a persona-calibration spot check
---

# SEED-170: Engine search fixes: root comparability, round underfill, findability fallback

All three changes alter what the search returns, which is why they are a phase and not a quick
task. The bot budget (50 nodes, concurrency 4) was calibrated against today's tree shapes in
Phase 199, so every item below needs the measurement gate at the end.

## 1. Root children are compared at different evaluation stages (conceptual, affects bot play)

**Where:** `mctsSearch.ts` `stopRuleSatisfied` (~246), `treeCommon.ts` `recomputeValue` (~238,
root = `backupRootMax`).

**Mechanism.** An unexpanded root child's `value` is `sigmoid(Stockfish grade)`: both sides
perfect from there. Its first expansion replaces that with a Maia-weighted average over the
opponent's replies, each graded by Stockfish. The average of opponent replies is always >= the
opponent's best reply (for the root player), so a first expansion raises the value by roughly
the opponent's expected error at that ELO. The root then takes a plain max over children that
have and have not received that boost.

Consequences:
- The early-stop clear-winner check (`FLAWCHESS_BOT_STOP_RULE`: minNodes 8, margin 0.05,
  stability 3) frequently compares an expanded top child against unexpanded runners-up. With up
  to 15 root candidates (`ROOT_CANDIDATE_HARD_CAP`) and a stop possible after 8 nodes, several
  root children are still unexpanded when it fires. The bias favors whichever high-prior move got
  searched first, i.e. it quietly re-introduces "most likely human move" preference.
- The deadline cut (`deadlineSearch.ts`, floor `BOT_MIN_SEARCH_NODES` = 8) has the same exposure.
- Deeper in the tree the effect alternates by parity (opponent-node expansion raises, own-node
  expansion lowers). Not in `docs/flawchess-engine-explained-2026-07-06.md`; document it.

**Proposed fix (smallest version).** In `stopRuleSatisfied`, only allow the clear-winner branch
when every root child whose value is within `marginThreshold` of the top (or simply every root
child) has `visits >= 1`. Flatness branch unchanged. Consider the same guard as a precondition
for the deadline cut. Do NOT add value corrections or blend terms; the visit guard is enough to
make the compared estimates like-for-like at depth one.

Open question for discuss-phase: guard all root children (simple, costs up to ~15 of 50 bot nodes
before any early stop) vs only the within-margin ones (cheaper, slightly more code).

## 2. Round underfill: `selectPath` gives up instead of backtracking (perf bug, confirmed)

**Where:** `mctsSearch.ts` `selectPath` (`if (candidates.length === 0) return null;` ~313) and the
fill loop (`if (path === null) break;` ~516).

**Mechanism.** Within one dispatch round only the leaf is marked `isPending`. Root PUCT sees the
same visit counts all round, so later walks re-descend the same root child. If any node on that
walk has no child left that is neither pending nor closed, `selectPath` returns null and the
fill loop stops, even though other root subtrees have plenty of expandable leaves. Nodes with one
or two candidates after the 0.9-mass cut (recaptures, forced replies) are exactly this case.

**Evidence** (throwaway vitest harness, real `mctsSearch`, 50 nodes, concurrency 4, grade calls
counted per event-loop tick, flat root policy, non-root policy shape varied):

| Non-root policy | Rounds | Grades per round |
|---|---|---|
| flat | 14 | 1,4,4,...,4,1 |
| two candidates (55/37%) | 21 | 1,4,4,4,4, then 2 |
| one candidate (92%) | 38 | 1,4,4,4,4, then 1 |

Effective concurrency collapses to 1-2 of 4 once the favored subtree narrows. Up to 2-3x wall
clock at the bot budget; also affects the 400-node analysis search.

Phase 198's `apply-order-design.md` (§5, ~156) treated "`selectPath` returns null while
`inFlight < c`" as the saturated-tree case. It is not saturated here; it is a premature give-up.
This fix is independent of the rejected continuous-dispatch rewrite (Phase 198 / SEED-130): the
round structure and canonical apply order stay exactly as they are.

**Proposed fix.** When the walk reaches a non-root node with zero selectable children, mark that
node blocked for the rest of the round (reuse `isPending` or a separate `isBlocked` flag), push it
onto a per-round list, and restart the walk from the root. Clear the flags after the round's
`Promise.all` resolves. If the root itself has no selectable child, return null as today.
Termination: each restart blocks one more node, bounded by tree size. Output stays deterministic
per concurrency level (module header's determinism scope is unchanged). Add a unit test that
asserts round sizes with a peaked fake policy (the harness above, made permanent).

## 3. Findability ranking treats "didn't find the move" as a loss (conceptual, analysis UI only)

**Where:** `findability.ts` `rankScore`, consumed by `treeCommon.ts` `buildRankedLines` (sort only;
`practicalScore` is untouched, and bot sampling reads `practicalScore`, so bot play is unaffected).

**Mechanism.** `rankScore = min(1, P/Pref) * V` implicitly scores the "player fails to find the
move" branch as 0. The penalty therefore scales with how good the position is: at V ~ 0.95 a
hard-to-find winning move drops to ~0.475 and ranks below a 0.6 move that gives away most of the
win, while in a lost position the same findability barely moves anything in absolute terms.

**Proposed fix.** `rankScore = f * V + (1 - f) * V_fallback`, with `f = min(1, P/Pref)` as today.
Candidate for `V_fallback`: the root player's own prior-weighted expectation over root children,
`sum(prior_i * value_i)` (what they score if they just play like a human at their rating). It is
computed once per `buildRankedLines` call from data already on the root. `f = 1` still gives
exactly `V`, so the saturation property (a findable move is never boosted above its own V) holds.

Must re-check the three D-03 regression cases in `findability.test.ts` (incl. the 600-ELO case) and
decide whether `P_REF_ANCHORS` need retuning, since the effective penalty gets milder.

## 4. Optional: cap candidates below the root

`truncateAndRenormalize` has no count cap; only the root gets `ROOT_CANDIDATE_HARD_CAP = 15`.
`applyPolicyTemperature` also reshapes non-root nodes where the root player moves, so at T up to
2.0 a deep node can need 20+ moves to reach 0.9 mass. Each extra candidate adds a MultiPV line to
that node's grade (cost roughly linear in k), while a 2%-prior tail move barely changes the
expectation. A cap of ~6-8 is a one-constant change but it changes bot strength, so it is only
worth doing inside this phase's measurement, not separately.

## Measurement gate (write the accept rule first, per project precedent)

Follow the Phase 195/197/198 pattern: commit an accept rule under `reports/<dir>/accept-rule.md`
before any measurement, never edit it after data exists (override docs only).

- **Throughput:** `scripts/engine-grading-depth-ab.mjs` at both budgets (bot 50/c4, analysis 400/c4),
  before vs after item 2. Report wall clock and grade CPU; expected large win on peaked positions.
- **Move quality:** `fixtures/engine/maia-blindness.tsv` (12 positions, Stockfish d20 ground truth,
  §4b 0.05 margin), see `reports/grading-ladder/override-2026-07-31.md` for the procedure. Must
  not regress.
- **Stop rule behavior:** `scripts/engine-dispatch-stop-rule.mjs`: nodes-at-stop distribution
  before/after item 1 (item 1 will raise it; check it stays inside the bot think deadline).
- **Calibration spot check:** `reports/bot-parity-199/runbook.md` +
  `bin/run_persona_calibration_sweep.sh` on a small cell subset. Goal is "does the persona curve
  shift enough to need a refit", not a full 24-persona recalibration (see memory note on the
  August full recalibration: no shift, not promoted).
- **Analysis ordering (item 3):** qualitative check on a handful of winning positions where a
  hard-to-find move currently ranks below a much worse findable one.

Items 1+2 (+4) change bot trees, item 3 does not; they can be measured in one pass but the report
should attribute any calibration shift to 1/2/4 separately if it appears.

## Explicitly out of scope

- Repetition / game-history awareness (tree nodes and Stockfish `position fen` carry no history,
  so a winning bot can repeat into threefold). Reviewed and deferred by the user on 2026-09-27.
- Continuous dispatch / removing the `Promise.all` straggler wait (Phase 198, rejected; SEED-130).
- Cross-FEN Maia batching in `maiaQueue.ts` (worker changes; revisit with WebGPU policy).
- Grade-cache set-mixing redesign (`workerPool.ts` write-merge); the quick task only fixes the
  misleading comment.

## Related

- SEED-130 (browser grade nondeterminism), Phase 198 continuous-dispatch report, Phase 199 bot
  parity/calibration, `reports/grading-ladder/override-2026-07-31.md`.
