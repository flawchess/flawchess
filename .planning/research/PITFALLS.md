# Pitfalls Research

**Domain:** MultiPV=2 eval pass + JSONB storage + forcing-line tactic gate (v1.30)
**Researched:** 2026-06-29
**Confidence:** HIGH

Sources: project memory files, `app/services/engine.py` QUEUE-07 accounting comment,
`app/services/eval_utils.py` sigmoid constant, `.planning/notes/tactic-forcing-line-gate.md`
(design note), `.planning/PROJECT.md` v1.30 milestone context, and CLAUDE.md prod config.

---

## Critical Pitfalls

### Pitfall 1: MultiPV=2 ordering unreliable at the 1M-node budget

**What goes wrong:**
The 0.35 margin is calibrated for lichess-puzzler's depth-50 / ~25M-node searches, where
best-vs-second ordering is close to certain. At 1M nodes with `multipv=2`, each line gets
roughly half the effective search depth of a single-PV run at the same budget. For positions
where the margin is close to 0.35 (neither clearly forced nor clearly branching), the ordering
is noisy: the gate will randomly fire or pass on the same position depending on TT state and
machine speed, producing flaky tags across re-runs and between dev and prod.

**Why it happens:**
The node budget (`_NODES_BUDGET = 1_000_000`) was set for Lichess fishnet parity on
single-PV eval quality. MultiPV=2 at the same budget doesn't halve quality evenly — Stockfish
reuses most of the search tree — but depth per line drops from roughly 22 to roughly 18-20 at
this budget, and the margin between two near-equal moves is exactly what depth-sensitive search
is meant to resolve.

**How to avoid:**
In Phase 142, after wiring the MultiPV pass, sample 200-500 flaw positions from the dev corpus
and plot the distribution of `p(best) - p(second)`. If the distribution is bimodal (most
positions far from 0.35, few near it), 1M nodes is probably fine for ordering. If there is a
fat distribution of margins near the threshold, increase the budget to 1.5-2M nodes before
committing. Document the chosen budget with the same rationale as `_NODES_BUDGET`. The
reliability check is cheap to do in Phase 142 and eliminates the risk before backfill.

**Warning signs:**
Running the re-tagger twice on the same stored MultiPV evals produces different tag sets (if
deterministic re-tagger logic is confirmed, this means the eval capture code is re-running the
engine rather than reading stored blobs). Alternatively: the margin histogram shows >10% of
positions within ±0.05 of the 0.35 threshold.

**Phase to address:** Phase 142 (MultiPV eval pass — includes budget calibration before commit)

---

### Pitfall 2: RSS regression from MultiPV=2 pushing into the 4g OOM zone

**What goes wrong:**
The QUEUE-07 accounting (engine.py comment) shows 6 workers = ~1,586 MB Stockfish RSS,
leaving ~0.76 GB headroom in the 4g container when FastAPI/Uvicorn (~0.3 GB) is included.
If the MultiPV budget is raised significantly above 1M nodes to get reliable ordering, the
effective per-worker working set grows. Hash table size is fixed at 32 MB per worker, but
longer searches fill it more densely and keep more NNUE network paths hot, modestly increasing
RSS from the kernel's demand-paged perspective. Crucially, if a separate `EnginePool` is
created for the MultiPV backfill with different sizing than the module-level pool, two pools
can co-exist and exceed the container limit.

**Why it happens:**
The OOM history (CLAUDE.md and memory files) traces to import memory pressure, not Stockfish.
The temptation is to assume Stockfish is safe and be aggressive with a larger MultiPV pool for
the backfill. But the Phase 145 backfill will run concurrently with normal prod operations, and
a separate N-worker pool layered on top of the existing 6-worker pool could push RSS above 4g.

**How to avoid:**
Reuse the module-level pool for the MultiPV pass. For the backfill script (Phase 145), use
`STOCKFISH_POOL_SIZE` workers, not a pool sized independently. If the backfill needs speed,
document the RSS arithmetic before raising pool size: 7 workers at ~368 MB = ~2.58 GB
Stockfish + 0.3 GB FastAPI = ~2.88 GB fits the 4g limit; 8 workers = ~3.24 GB, which is the
Phase 116 ceiling. Do not exceed the Phase 116 pool-size gate (8 workers) without a fresh RSS
measurement.

**Warning signs:**
Container RSS crossing 3.5 GB in a 4g container. `docker stats` on prod backend showing
sustained memory near the limit during a backfill run. A sudden backend container restart
(OOM-kill) during Phase 145 backfill while the regular eval drain is also active.

**Phase to address:** Phase 142 (wiring decision: reuse module pool vs. separate pool);
Phase 145 (backfill run — must not create a second independent EnginePool during prod hours)

---

### Pitfall 3: A/B validation conflating gate effect with eval_cp non-determinism

**What goes wrong:**
The natural-seeming validation is: run the old tagger on prod's stored `eval_cp` /
`tactic_motif` columns and run the new gated tagger on dev's newly stored MultiPV evals, then
diff the tag sets. This conflates two independent signals: (a) the gate filtering noise and
(b) eval drift between dev and prod machines (documented in `project_eval_nondeterminism`:
TT cross-position contamination + wall-clock timeout differences + different NNUE scheduling
on different hosts). The diff will show tag changes that are pure eval drift, not gate effect,
and the false-negative count will be inflated or deflated by accident.

**Why it happens:**
The eval non-determinism is a known fact but an easy trap when "user-28 has the same games in
dev and prod" seems to imply a clean comparison. The games are the same; the stored evals are
not identical.

**How to avoid:**
Implement the A/B exactly as the design note specifies: compute the MultiPV evals ONCE in dev,
store them to `allowed_pv_lines` / `missed_pv_lines` in dev's `game_flaws`, then run BOTH old
tagger logic AND new gated tagger logic against that SAME stored MultiPV data. The old-tagger
re-run must read from the same stored `eval_cp` already in dev's DB — it must NOT call
`engine.evaluate_nodes`. Prod-28 is a "what users see today" sanity reference only, not an A/B
control. The Phase 144 test code must make this isolation explicit.

**Warning signs:**
The A/B diff shows tag differences on positions where both old and new logic would agree if
given identical inputs (e.g., depth-12 forced mates that would never be gated). If the
no-gate replay on dev produces different tags from prod even without the gate applied, the
comparison methodology is wrong — the eval source is leaking.

**Phase to address:** Phase 144 (validation) — the methodology must be locked in the plan
before Phase 143 (re-tagger) completes, so Phase 143 knows exactly what data to produce for 144

---

### Pitfall 4: Measuring only tags removed, not good tags killed (false negatives)

**What goes wrong:**
If Phase 144 reports "X% of clearance/sacrifice tags removed" as the success metric, the gate
tuning looks successful even if it killed a comparable number of real tactics. The known risk
(design note "Known risk to measure, not assume away"): two moves both winning — a fork AND a
simpler capture — produce `p(best) - p(second) ≈ 0` because both moves have similar win
probability. The gate drops the fork tag as "not forced" even though the fork is a real and
instructive tactic. With a margin of 0.35 and a 1M-node budget, this failure mode is
non-trivial at the corpus scale.

**Why it happens:**
Tag-removal rate is easy to compute; false-negative rate requires knowing the ground truth,
which is unavailable at scale. The fixture harness cannot catch this because the fixtures have
no non-forced tail — the same reason the original bug went undetected until real-game
observation.

**How to avoid:**
The Phase 144 validation report must include per-motif: (a) tags removed, (b) a hand-checked
sample of ~30 removed tags, and (c) a per-motif estimate of "looks like a real tactic but
dropped". The 30-sample check is the design note's explicit floor — do not reduce it.
Additionally, spot-check positions where `p(best) - p(second)` is between 0.20 and 0.40 (the
gray zone): these are candidates where the gate is making a real call and may be wrong in
either direction. If the hand-check shows a consistent pattern of killing real tactics in a
specific motif (e.g., fork), adjust the per-motif margin rather than one global threshold.

**Warning signs:**
A high removal rate (>50%) on motifs known to fire on genuinely forcing lines (fork, skewer,
pin) is a red flag for false negatives. Removal rates for motifs that fire deep (clearance at
depth 8+) should be high; removal rates for shallow motifs (pin, fork at depth 1-2) should be
low. If they are not ordered this way, the gate is misfiring.

**Phase to address:** Phase 143 (re-tagger must output per-position margin data);
Phase 144 (validation must include the false-negative sample, not just aggregate removal stats)

---

### Pitfall 5: Mate-score saturation in the win-prob margin calculation

**What goes wrong:**
`eval_cp_to_expected_score` for a mate position returns 1.0 (documented in eval_utils.py:
"Mate handling (D-02, Pitfall 1) — mate scores are NOT routed through the sigmoid").
If the best move is mate-in-3 and the second-best is mate-in-9, both return 1.0 from the
winning side's perspective. The gate computes `p(best) - p(second) = 1.0 - 1.0 = 0.0 < 0.35`
and marks the position as NOT forced — incorrectly suppressing a valid (and likely very
instructive) mating tactic.

Symmetric problem: if best move is mate-in-1 and second-best is a normal +500cp win, the gate
computes `1.0 - sigmoid(500) ≈ 1.0 - 0.84 = 0.16 < 0.35` — also fails the gate. But a
mate-in-1 is the most forcing move possible.

**Why it happens:**
The gate is designed for the centipawn regime where the sigmoid is the right discriminator.
lichess-puzzler handles the edge case explicitly: "A move also passes if there is no legal
second move, it's a clean mate-in-1, or it's the unique tablebase-winning move." The design
note mentions mate-in-1 in passing but does not specify how to handle best=mate-in-N vs
second=mate-in-M or best=mate vs second=large positive.

**How to avoid:**
In Phase 143, implement the following hierarchy before the sigmoid margin check:
1. If `best_mate` is not None (any forced mate) and `second_mate` is None (no mate for second):
   forced (gate passes — one move gives mate, the other does not).
2. If both `best_mate` and `second_mate` are not None:
   compare mate distances; if `abs(best_mate) < abs(second_mate)` then forced (shorter mate
   wins); if equal distances, not forced.
3. Fall through to sigmoid margin for the cp-vs-cp case.

Add a unit test covering each branch: (mate vs cp), (short mate vs long mate), (equal mates),
(cp vs cp below threshold), (cp vs cp above threshold).

**Warning signs:**
Mating combinations disappearing from the tactic UI after the gate is applied. If the
"mate" motif family has a very high gate-removal rate in Phase 144, the mate handling is wrong.
Specifically: any mate-in-1 position being suppressed is a definitive failure signal.

**Phase to address:** Phase 143 (re-tagger implementation — must include the mate hierarchy);
Phase 144 (validate against a synthetic corpus position with mate-in-N vs cp)

---

### Pitfall 6: JSONB columns leaking into stats queries via ORM SELECT *

**What goes wrong:**
`allowed_pv_lines` and `missed_pv_lines` store arrays of per-ply JSON objects (up to 12 nodes,
5 fields each). A single row's JSONB can be a few hundred bytes; across a corpus of 100k flaws,
a query that selects `*` from `game_flaws` pulls substantial TOAST I/O. Postgres automatically
TOASTs JSONB values over ~2 KB out-of-line, which means any code that accidentally expands `*`
triggers real TOAST block fetches. The risk is the existing stats queries (`/api/library/
mistake-stats`, flaw-comparison endpoint, benchmark flaw-delta computation) — these all touch
`game_flaws` and care only about `ply`, `severity`, `tag`, `tactic_motif`, not the PV blobs.

**Why it happens:**
SQLAlchemy 2.x `select(GameFlaw)` selects all mapped columns including future ones. When the
migration adds `allowed_pv_lines` and `missed_pv_lines` to the ORM model, every existing query
that uses `select(GameFlaw)` starts fetching them without any code change.

**How to avoid:**
In Phase 141, after writing the migration and adding the columns to the ORM model, grep all
existing `game_flaws` queries for `select(GameFlaw)` (model-level selection) and convert them
to explicit column projections: `select(GameFlaw.ply, GameFlaw.severity, ...)`. The PV columns
should only be selected in the re-tagger and any future PV display path. Document this
constraint in a comment on the model columns: "# Not selected by stats queries — add explicitly
only for PV access."

**Warning signs:**
A slow-down in the flaw-comparison or mistake-stats endpoints after the Phase 141 migration
without any other change. `EXPLAIN (ANALYZE, BUFFERS)` showing unexpected "Heap Fetches" or
TOAST block reads on game_flaws scans.

**Phase to address:** Phase 141 (migration + model) — audit all existing query sites before
committing the migration

---

### Pitfall 7: Defender-vs-solver node confusion in the re-tagger

**What goes wrong:**
The gate applies uniqueness only at SOLVER nodes (the attacking/tactic-delivering side).
At DEFENDER nodes, any move is valid — the engine's single best reply is played and the line
continues. If the re-tagger applies `p(best) - p(second) > 0.35` at every ply (including
defender plies), it will kill valid tactics where the defender has two reasonable responses
(both of which lead to the same tactic firing one ply later). This is a different failure mode
from the false-negative problem: it kills correct tags even at shallow depth where the tactic
is clear.

The design note is explicit: "At defender nodes there is no uniqueness check." The existing
`tactic_detector.py` uses `pov` to track whose turn it is. The re-tagger must correctly read
this turn structure from the stored PV, where ply parity (relative to the flaw ply) determines
solver vs. defender.

**Why it happens:**
The PV in `allowed_pv_lines` / `missed_pv_lines` is indexed from the flaw ply. Whether ply 0
in the blob is a solver or defender move depends on the flaw orientation (`allowed` vs
`missed`) and `user_color`. Getting this wrong by one ply means the gate fires on every
defender node and suppresses most deep tactics.

**How to avoid:**
In Phase 143, write a unit test that constructs a position where the defender has two plausible
responses (e.g., a pin where the defender can block with either of two pieces) but the attacker
has one forced winning continuation regardless. Verify the gate passes. The ply-to-pov mapping
must be extracted from the existing `tactic_detector.py` `pov` logic and reused, not
reimplemented.

**Warning signs:**
Overall tag survival rate far lower than expected — especially motifs that require defender
responses (back-rank mate, discovered attack). A pov-parity off-by-one produces approximately
a 50% reduction in all surviving tags across motifs uniformly.

**Phase to address:** Phase 143 (re-tagger implementation) — verify with unit tests covering
both allowed-flaw and missed-flaw orientations for both user colors

---

### Pitfall 8: Backfill not idempotent; lichess-eval gate policy left ambiguous

**What goes wrong:**
Two sub-pitfalls:

(a) **Idempotency failure.** If the MultiPV backfill crashes mid-run and is restarted, it may
re-evaluate already-filled positions (wasting engine time) or produce inconsistent JSONB values
from a second engine pass. The common trap: using `INSERT ... ON CONFLICT DO NOTHING` silently
skips incomplete rows if the PK exists but the JSONB columns were only partially written before
the crash.

(b) **Lichess-eval gate.** The existing eval pipeline gates all Stockfish re-evaluation on
`lichess_evals_at IS NULL` — positions whose evals came from lichess are left alone. The
MultiPV pass needs to evaluate flaw positions with Stockfish to get second-best data (lichess
provides only best-move eval). If the backfill reflexively adds `WHERE lichess_evals_at IS NULL`
to the MultiPV pass, users whose games were analyzed by lichess get NULL JSONB blobs and the
gate never fires for them — silently leaving all their noisy tags intact.

**Why it happens:**
The lichess-eval gate is deeply ingrained in the eval pipeline (EVALFIX-01..05, Phase 117.1).
Developers following that pattern reflexively add `WHERE lichess_evals_at IS NULL` to any new
Stockfish pass, even when the new pass has different semantics (second-best is needed
regardless of eval source).

**How to avoid:**
(a) Write the backfill as `UPDATE game_flaws SET allowed_pv_lines = :blob, missed_pv_lines = :blob
WHERE (user_id, game_id, ply) = (:uid, :gid, :ply) AND allowed_pv_lines IS NULL`. The
`IS NULL` guard makes it idempotent: a restart skips already-filled rows.

(b) Explicitly document in the Phase 145 plan: the MultiPV pass runs on ALL flaw positions
(NOT gated on `lichess_evals_at`), because it captures second-best data that lichess never
provided. The stored `eval_cp` in the JSONB best field may differ from the lichess-sourced
`eval_cp` on the row — this is acceptable and must be called out in a code comment.

**Warning signs:**
The backfill script reports 0 rows updated on a second run but the JSONB columns are only
partially populated (some rows NULL). The `allowed_pv_lines` column is NULL for all users
whose games have `lichess_evals_at NOT NULL` after the backfill completes.

**Phase to address:** Phase 145 (backfill script and rollout)

---

### Pitfall 9: AGPL boundary slip — copying lichess-puzzler source patterns

**What goes wrong:**
The forcing-line gate closely mirrors lichess-puzzler's `is_valid_attack` logic from
`generator/generator.py`. The temptation is to copy function structure, variable names, or
the exact conditional tree verbatim, which constitutes derivative work of AGPL-3.0 source.
The prior cook.py alignment (Phases 124/125) established the correct boundary: heuristics,
constants, and function names are facts/ideas (not copyrightable) and can be referenced in
prose. Code structure and implementation must be original.

**Why it happens:**
The reference clone at `/home/aimfeld/Projects/Python/lichess-puzzler` is explicitly used as
reference. In the flow of implementation, copying a conditional into Python and "planning to
paraphrase it later" is the classic slip. The MultiPV gate adds new surface area beyond the
prior cook.py alignment work.

**How to avoid:**
Never open `generator/generator.py` or `tagger/cook.py` while writing the re-tagger. Implement
the gate from the design note description alone — which already translates all heuristics into
our units. After implementation, confirm no function body in tactic_detector.py or the
re-tagger could only have been derived from the reference clone source (not from the design
note prose). The Phase 143 code review must include an explicit AGPL scan.

**Warning signs:**
Any variable named `is_valid_attack`, `cook_advantage`, or other verbatim lichess-puzzler
internal names appearing in committed source (these names in comments and design notes are
fine; in code they signal copy-paste risk). Function bodies that match the reference clone
line-for-line.

**Phase to address:** Phase 143 (re-tagger implementation and code review)

---

### Pitfall 10: python-chess MultiPV API returns a list, not a scalar InfoDict

**What goes wrong:**
The existing `_analyse_with_pv` method calls `protocol.analyse(board, limit)` and treats the
return as a single `chess.engine.InfoDict`. With `multipv=2`, python-chess's `analyse()` call
returns `list[InfoDict]` where index 0 is the best-move line and index 1 is the second-best.
If Phase 142 adds `{"MultiPV": 2}` to the options or passes it as a search parameter but still
treats the return as a scalar, it silently takes the second-best eval as the best, or crashes
with `AttributeError: 'list' object has no attribute 'get'` on the first real call.

**Why it happens:**
The chess.engine API difference between `multipv=1` (scalar InfoDict) and `multipv>1` (list)
is not obvious from the function signature. All existing callers pass scalar results to
`_score_to_cp_mate(info)` which calls `info.get("score")` — this will fail or mis-read if
`info` is a list.

**How to avoid:**
In Phase 142, add a new `_analyse_multipv` method alongside the existing `_analyse_with_pv`.
This method must handle the list return: `infos = await protocol.analyse(board, limit,
multipv=2)` returns `list[InfoDict]`. Extract `infos[0]` for best-move data and `infos[1]`
for second-best. Guard for the case where only one legal move exists (`len(infos) == 1`):
treat as forced (no second best). Add a unit test that mocks `protocol.analyse` returning a
two-element list and verifies correct extraction of best vs second.

**Warning signs:**
`AttributeError: 'list' object has no attribute 'get'` in the engine pool on the first
MultiPV call. Or, more insidiously: tactic tags consistently suppressed across all motifs
(if best/second evals are transposed, the margin is near zero for all positions).

**Phase to address:** Phase 142 (engine.py MultiPV method implementation)

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Inline JSONB on game_flaws (not sidecar table) | No JOIN for re-tagger | If stats queries select `*` on game_flaws, TOAST I/O becomes a bottleneck at >200k flaws | Acceptable IF Pitfall 6 prevention (explicit column projection) is applied in Phase 141 |
| Reuse 1M-node budget for MultiPV pass without measuring margin distribution | No timeout change | Ordering may be noisy at the threshold; false-negative rate inflated | Never — Phase 142 must include the margin histogram check before budget is finalized |
| Single global 0.35 margin for all motifs | Simple implementation | Pin/fork at depth 1 and clearance at depth 8 have different noise profiles | Acceptable for v1.30; flag as a follow-on tuning seed if Phase 144 shows per-motif FN divergence |
| Backfill during prod hours without throttle | No deploy window needed | MultiPV backfill competes with import-era eval drain for pool workers | Only if the backfill leaves at least 2 pool slots free for live traffic (checked via pool-size arithmetic) |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| python-chess MultiPV analyse() | Passing result to `_score_to_cp_mate(info)` as a scalar | `infos = await protocol.analyse(..., multipv=2)` returns `list[InfoDict]`; check `len(infos)` before indexing |
| chess.engine.Limit with MultiPV | Assuming `Limit(nodes=1_000_000)` gives equal quality to single-PV at same budget | MultiPV=2 at 1M nodes gives roughly single-PV quality at ~500k nodes per line; measure margin stability before finalizing |
| Remote workers + MultiPV pass | Creating a parallel submission pathway outside the existing lease/submit contract | Extend the existing lease payload to include the `multipv=2` flag and expected return schema; do not add a separate endpoint |
| game_flaws ORM model | SQLAlchemy `select(GameFlaw)` auto-includes all mapped columns after migration | Use explicit column selects in all stats queries; JSONB columns selected only by PV-specific callers |
| Already-winning reject (>300 cp) | Re-computing the reject threshold using the MultiPV best-eval from the new engine pass | Use the stored `eval_cp` at the flaw ply from the existing eval pipeline (already materialized); do not mix eval sources in the gate |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| JSONB blobs selected in flaw-comparison / mistake-stats queries | Slow endpoints after Phase 141 migration with no other change | Explicit column projection in all stats queries (Pitfall 6) | Noticeable at >50k game_flaws rows per user; measurable at corpus scale |
| Backfill using a second independent EnginePool | Backend RSS spikes toward 4g during Phase 145 | Reuse the module-level pool; calculate RSS before any pool-size change | Any time two pools overlap with combined size > 8 workers |
| MultiPV eval on all game_positions ply by ply | Phase 142 scope creep inflating the eval drain runtime | MultiPV pass is only for FLAW POSITIONS (game_flaws rows), not all game_positions; the flaw set is typically <5% of all positions | Immediately at corpus scale — all-ply drain is already several seconds per game |
| Node budget increase without timeout increase | Timeout-triggered (None, None) returns on slow/busy machine; gate silently skips positions with NULL second-best | If budget > 1M, scale `_NODES_TIMEOUT_S` proportionally; document the ratio | On prod where machine load varies |

## "Looks Done But Isn't" Checklist

- [ ] **MultiPV ordering reliability:** the margin histogram is plotted and confirms most positions are far from the 0.35 threshold before finalizing the node budget — not just "the pass runs without error"
- [ ] **Mate-score special case:** unit tests cover (mate vs cp), (short mate vs long mate), (equal-length mates), (mate-in-1) — the gate must not suppress a mate-in-1
- [ ] **Solver-vs-defender parity:** the re-tagger applies the gate only at solver nodes; a unit test with a defender-branching position confirms the gate passes
- [ ] **False negatives measured:** Phase 144 report includes a per-motif "good tags killed" estimate from a 30-sample hand-check, not just total removed count
- [ ] **A/B isolation verified:** old-logic replay reads stored `eval_cp` from dev's DB and does NOT call the engine; confirmed by checking that re-running Phase 144 with a mocked engine produces identical old-logic results
- [ ] **python-chess list API:** the new MultiPV method is tested against a mock that returns `[InfoDict, InfoDict]`; the `len(infos) == 1` (only-move) path is tested separately
- [ ] **Stats query column audit:** `grep -rn "select(GameFlaw)" app/` shows zero hits in stats paths after Phase 141 (all converted to explicit column projection)
- [ ] **Backfill idempotency:** running the Phase 145 backfill script twice produces zero rows updated on the second run and identical JSONB content
- [ ] **Lichess-eval policy explicit:** the Phase 145 plan documents that lichess-eval positions ARE included in the MultiPV pass (second-best from Stockfish is new data not from lichess)
- [ ] **AGPL scan complete:** no variable or function body in the committed re-tagger matches the reference clone's `is_valid_attack` or `generator.py` structure; reviewer confirms independently

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Wrong node budget and noisy ordering producing bad corpus tags | MEDIUM | Re-run MultiPV backfill at corrected budget (idempotency means clean update); re-tag with stored blobs — no engine re-pass |
| RSS regression / OOM-kill during backfill | LOW | Stop backfill, reduce pool size or throttle concurrency, restart; partial progress preserved by idempotency guard |
| A/B methodology flaw discovered post-Phase-144 | LOW | Re-run Phase 144 with correct same-stored-eval methodology; stored MultiPV blobs are already in dev's DB |
| False negative issue found post-rollout | HIGH | Re-tune margin per-motif, re-run offline re-tagger against stored blobs, ship updated tags via another backfill; no schema change, no engine re-pass |
| Mate-score gate bug suppressing mating combinations post-rollout | MEDIUM | Fix re-tagger logic, re-run offline re-tagger against stored blobs, redeploy updated tags |
| JSONB leaking into stats queries | LOW | Add explicit column projection to offending queries; no migration needed |
| AGPL slip in re-tagger | HIGH | Rewrite the gate implementation from the design note prose alone; legal review if the code was public-facing |
| Defender-node parity bug suppressing real tags | MEDIUM | Fix pov-mapping in re-tagger, re-run against stored blobs — no engine re-pass |
| Backfill non-idempotent and partial state in prod | LOW | NULL out partially-filled rows via migration, restart backfill; the `IS NULL` guard then re-processes only incomplete rows |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| MultiPV ordering unreliable at 1M nodes | Phase 142 | Margin histogram on 200+ flaw positions; budget locked before merge |
| RSS regression from second pool or increased budget | Phase 142 + Phase 145 | `docker stats` during Phase 145 backfill dry-run on dev; backend stays <3.5 GB |
| A/B conflating gate effect with eval drift | Phase 144 (plan) + Phase 143 (re-tagger output format) | Old-logic replay does not call engine; verified by mocking evaluate_nodes in test |
| False negatives unmeasured | Phase 143 + Phase 144 | Phase 144 report includes per-motif hand-check table with good-tags-killed count |
| Mate-score saturation at the gate | Phase 143 | Unit tests covering all 4 mate/cp combinations; no mate-in-1 suppressed in corpus spot-check |
| JSONB in stats queries | Phase 141 | `grep -rn "select(GameFlaw)"` returns zero hits in stats paths after migration |
| Defender-vs-solver parity | Phase 143 | Unit test with defender-branching position passing the gate |
| Backfill not idempotent / lichess-eval gate | Phase 145 | Second backfill run updates 0 rows; NULL check for lichess-eval users passes |
| AGPL boundary slip | Phase 143 (implementation + code review) | No reference clone file open during implementation; reviewer confirms no structural match |
| python-chess MultiPV list API | Phase 142 | Unit test with mocked 2-element list return; `len==1` guard tested separately |

## Sources

- `app/services/engine.py` — QUEUE-07 accounting comment (6-worker RSS measured 1,586 MB; 4g container headroom ~0.76 GB including FastAPI); `_HASH_MB = 32`, `_NODES_BUDGET = 1_000_000`, `_NODES_TIMEOUT_S = 5.0`
- `app/services/eval_utils.py` — mate handling note (sigmoid saturates at mate; mate-score special case needed); `LICHESS_K = 0.00368208`
- `.planning/notes/tactic-forcing-line-gate.md` — design note; "Known risk to measure" and "Open knobs" sections; solver-only gate description; storage schema rationale
- `.planning/PROJECT.md` — v1.30 milestone context; OOM history references (v1.18 Phase 90, v1.26 Phase 116 QUEUE-07); cook.py alignment (Phases 124/125)
- `CLAUDE.md` — prod config (4g container, pool=6, ~368 MB/worker), AGPL norms ("Copy no source"), Critical Constraints
- Project memory files: `project_eval_nondeterminism`, `project_prod_oom_cause_and_stockfish_capacity`, `project_game_flaws_both_players_scope`, `project_eval_completion_columns`, `project_tactic_detector_flaw_move_context`

---
*Pitfalls research for: MultiPV=2 + JSONB + forcing-line tactic gate (v1.30 FlawChess)*
*Researched: 2026-06-29*
