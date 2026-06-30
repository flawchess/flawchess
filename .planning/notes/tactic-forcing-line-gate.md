# Forcing-line gate for tactic tagging — design note

**Date:** 2026-06-29
**Context:** `/gsd-explore` session. The tactic tagger looks excellent on the fixture report
(`reports/tactic-tagger/tactic-tagger-2026-06-23.md`: ~0.998 micro-precision, most motifs
1.000) but produces tags that "don't make sense" in real games — especially
clearance / sacrifice / capturing-defender. This note captures the root-cause diagnosis,
the proposed forcing-line gate (modeled on lichess-puzzler's validity criteria), the storage
schema to make threshold tuning cheap, and the user-28 dev-vs-prod experiment. Feeds a
prospective **v1.30 milestone** (see `SEED-070`).

> **AGPL boundary.** lichess-puzzler (`generator/`, `tagger/cook.py`) is AGPL-3.0. This note
> records its *heuristics, constants, and function names* (facts/ideas — not copyrightable),
> described in original prose. Copy **no** source. Reference clone:
> `/home/aimfeld/Projects/Python/lichess-puzzler`. Same boundary as
> `notes/tactic-tagger-cook-alignment.md`.

---

## Root cause: puzzle-distribution detector run on real-game PVs

The detector (`app/services/tactic_detector.py::detect_tactic_motif`) walks a **single stored
refutation PV** (`game_positions.pv`, capped ~12 plies) and tags the **shallowest-firing
motif** (depth-primary dispatch, D-05). It is tuned and validated **entirely on lichess
puzzles** — curated positions where the line *is* forced and the tactic *is* the whole point.

In real games we run the same detector over the engine's best PV in **ordinary positions**,
where the line often isn't forced (several moves near-equal). That mismatch produces all three
user-observed failure modes from one root:

- **Too deep / disconnected** — a clearance/sacrifice fires 4-8 plies past the user's actual
  mistake, describing a tactic they never faced. (`tactic_depth` is the loop index into the
  refutation PV; see `game_flaw.py` `allowed_tactic_depth` / `missed_tactic_depth`.)
- **Wrong label** — the PV continues past the real refutation into normal play, where geometry
  incidentally matches a motif pattern the position doesn't really "contain."
- **Real but trivial** — the tactic is forced and real, but a depth-6 capturing-defender is far
  less instructive than the depth-0 thing the user should have seen.

The fixtures cannot surface this: they have no non-forced tail to walk into.

## The gate: an "only-move" forcing check (lichess-puzzler model)

lichess-puzzler already implements almost exactly the user's "stop the line when the
second-best move's expected score is close to the best" idea, with two refinements we should
adopt. Findings (from `generator/generator.py`, `generator/util.py`, version 50):

1. **Only-move margin (the key constant).** `is_valid_attack` accepts a solver move only if
   `win_chances(best) > win_chances(second) + 0.7`, where `win_chances` is the lila sigmoid
   `2/(1+exp(-0.00368208*cp)) - 1` in **−1..+1** space. The best/second pair comes from a
   `multipv=2` search. A move also passes if there is no legal second move, it's a clean
   mate-in-1, or it's the unique tablebase-winning move.
   - **Translation to our units:** the coefficient `0.00368208` **is** our `LICHESS_K`
     (`app/services/eval_utils.py`), which returns win-probability in **0..1**. Lichess's
     +0.7 in −1..+1 space equals **+0.35 in our 0..1 win-prob space**. So the gate is
     `p(best) − p(second) > 0.35`, reusing `eval_utils` directly. Treat 0.35 as the **starting**
     margin to tune, not gospel.

2. **Solver nodes only (answers the "branch then re-converge" worry).** The uniqueness test
   fires **only at solver nodes** (the refuting/attacking side — our `pov`). At **defender
   nodes there is no uniqueness check** — the engine's single best reply is played and the line
   continues. So a line that branches at a *defender* ply (2-3 equal moves) but re-converges to
   a single forcing continuation is **fine**; only ambiguity on the *tactic-delivering* side
   kills it. This is cleaner than a hard "truncate at first near-equal node" prefix cut.

3. **Bonus rejection filters worth stealing** (each cuts trivial/wrong-label tags):
   - **Already-winning reject:** if the position before the flaw was already > **+300cp**
     (`prev_score > Cp(300)`) — or the winner is already up material — no tactic.
   - **Still-winning floor:** stop extending the line when best-move eval drops below **+200cp**
     (`cook_advantage` stops at `Cp(200)`); don't tag a "tactic" that fizzles.
   - **Length filters:** discard one-movers; require the line to end on a real solver move with
     a genuine second-best. (lichess also strips trailing only-moves and short puzzles by tier.)
   - **Start trigger** (for reference; our flaw detection already does the equivalent): an
     opponent blunder with `score >= Cp(200)` and a win-chance jump `> 0.6`.

**Net rule for our detector:** only credit a motif whose **firing node passes the only-move
gate**, with all **solver nodes leading to it** also passing, plus the already-winning /
still-winning floors. The gate naturally bounds depth — non-forced lines get cut short, so the
deep-disconnected and incidental-tail tags disappear *without* a hand-tuned per-motif depth cap.

**Known risk to measure, not assume away:** "second-best is close" doesn't always mean "not
tactical" — sometimes two moves both win (two ways to grab the piece; fork *or* simpler
capture). A naive gate drops those legitimate tactics. The experiment must track **false
negatives** (good tags killed), not just noise removed. The 0.35 margin trades these off.

## Storage: persist MultiPV so re-tagging is engine-free

The expensive part is the MultiPV=2 engine pass; the gate + motif logic is cheap. **Decouple
them**: store the MultiPV results once, then re-run the tagger with adjusted margins / new rules
/ the filters above as a pure offline re-derivation (`/loop`-tunable) — no engine, no re-backfill
per threshold change.

**What the re-tagger needs per node `i` along the capped line** (beyond what we already store):
- best eval (cp + mate flag) — *best move itself is already `pv[i]`*
- **second-best eval** (cp + mate flag) ← the only genuinely new engine output
- **second-best move UCI** — not needed by the current gate, but cheap and future-proofs rules
  like "is the alternative also winning / also a capture"

We already have: the best-move line (`game_positions.pv`) and the flaw's pre/post eval (for the
already-winning reject and the swing).

**Proposed columns — one JSONB blob per line, on `game_flaws`:**

```
allowed_pv_lines  JSONB   -- refutation line (flaw_ply+1 PV)
missed_pv_lines   JSONB   -- best-move line  (flaw_ply PV)
```

Each an array indexed by ply: `[{"b": <best_cp|null>, "bm": <best_mate|null>,
"s": <second_cp|null>, "sm": <second_mate|null>, "su": "<uci>"}, ...]` (white-perspective cp,
matching the existing `eval_cp` convention; convert at read time).

**Why JSONB over parallel Text columns** (the `pv: Text` idiom): the stated goal is re-running
with *additional rules*. JSONB lets a new rule read a new field added to the blob with **no
migration** and no mate-sentinel parsing. It's genuinely variable-length per-node structured
data read only by the Python re-tagger (never filtered in SQL) — JSONB's sweet spot. Storage is
bounded: it lives on `game_flaws` (blunders/mistakes), **not** the giant `game_positions` table,
and Postgres TOASTs large JSONB out-of-line, so it won't bloat the stats scans that don't select
it. Start **inline**; a `game_flaw_pv_lines` sidecar (FK + the two blobs) is the fallback if we
later want `game_flaws` to stay narrow.

## Experiment: user-28 dev vs prod

User 28 has the same games imported in dev and prod, so it's a ready-made A/B harness.

1. Implement the MultiPV pass + storage + new gated re-tagger in dev.
2. Backfill user 28's flaws in dev with the new pipeline.
3. **Isolate the algorithm from eval noise.** `eval_cp` is non-deterministic across machines
   (memory: `project_eval_nondeterminism`), so a raw dev-vs-prod tag diff conflates the gate
   with eval drift. The clean version: compute the new MultiPV evals **once in dev**, then run
   **both old and new detector logic on that same stored data** and diff *those*. Prod-28 stays
   only as a "what users see today" sanity reference.
4. Measure: tags removed, tags shifted shallower, per motif and per original depth; hand-check
   ~30 to confirm the dropped ones were the nonsense ones; count good tags killed (false neg).

## Open knobs (fold-in — decide during planning, not blockers)

- **Solver-only vs every-node MultiPV.** The current gate only checks solver nodes, so storing
  solver nodes alone **halves** the MultiPV cost. Storing every node future-proofs defender-side
  rules. Recommendation: store **every node** for the user-28 experiment (flexibility); optimize
  to solver-only later if no rule needs defender data.
- **Node/depth budget per MultiPV search.** lichess uses heavy searches (depth-50 / 25M nodes)
  for puzzle-grade certainty. We only need a **trustworthy best-vs-second ordering**, not puzzle
  depth — likely far fewer nodes than 25M. Tune for ordering stability vs cost on the worker
  fleet. (Our current free-PV capture is a 1M-node search; MultiPV=2 is the increment.)
- **Worker infra.** Feasible — remote workers already do whole-game Stockfish analysis, and this
  runs only on flaw positions along ~6-12 plies, a fraction of a full-game pass. Batch sizing /
  scheduling is a phase-level detail.

## Cross-references

- `SEED-070` — the v1.30 milestone this note scopes.
- `reports/tactic-tagger/tactic-tagger-2026-06-23.md` — the "perfect on fixtures" report that
  motivated this (fixtures can't see the non-forced tail).
- `notes/tactic-tagger-cook-alignment.md` — prior AGPL-boundary cook.py alignment work; same
  reference clone, same prose-not-source rule.
- `SEED-039` (tactic-family cause-of-error tags), `SEED-058` (new motifs / lichess coverage),
  `SEED-064` (precision hardening / cook alignment), `SEED-065` (tactic-line explorer) — adjacent
  tactic work this gate interacts with.
- `app/services/tactic_detector.py::detect_tactic_motif`, `app/services/engine.py`
  (`evaluate_nodes_with_pv`, `_pv_to_uci_string`), `app/services/eval_utils.py` (`LICHESS_K`),
  `app/models/game_flaw.py` (`allowed_tactic_*` / `missed_tactic_*`).
