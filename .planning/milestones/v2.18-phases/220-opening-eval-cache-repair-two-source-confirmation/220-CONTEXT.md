# Phase 220: Opening Eval Cache Repair & Two-Source Confirmation - Context

**Gathered:** 2026-09-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Repair the poisoned `opening_position_eval` dedup cache (2.57M rows, first-write-wins,
poisoned by the 2026-06-17 `DISTINCT ON` backfill and the first days of the full-game
drain) and every `game_positions` / `game_flaws` row it tainted, then stop a single engine
write from ever poisoning it again. Deliverables are fixed by ROADMAP.md (CACHEFIX-01..12):
(a) a resumable, DB-state-driven repair pipeline `seed -> calibrate -> screen -> confirm ->
propagate -> rederive -> report` with audit tables that stay as the trail, run against dev
then prod from the local 4-worker box through the tunnel; (b) two-source confirmation plus
provenance columns replacing first-write-wins; (c) the remote-worker submit path writing the
cache through the same shared function as the tick; (d) an integrity check; (e) a recorded
decision on the pre-2026-06-18 legacy cohort beyond ply 20.

The seed (`.planning/seeds/SEED-164-opening-eval-cache-poisoned-legacy-evals.md`) and the
Phase 220 ROADMAP section already lock the table shapes, stage semantics, threshold method
(expected-score units, measured floors), the old-value propagate predicate, the rederive
path (drain's own classifier + shared oracle-count refresh), the report contents and the
prod acceptance assertions. This CONTEXT.md only records what those left open.

Out of scope (ROADMAP): flaw thresholds, the post-move storage convention, `DEDUP_MAX_PLY`,
re-evaluating lichess-analysed games, rebuilding `herring_pool` or drill scheduling beyond
pruning orphans, any frontend change, pinning down the June/July misalignment mechanism,
any benchmark DB re-clone or benchmark/story re-run.

</domain>

<decisions>
## Implementation Decisions

The user delegated all four open areas ("I'll let you decide"). Decisions below are
Claude's, with the reasoning that downstream agents should preserve. Where a decision
refines a CACHEFIX requirement's wording, it says so explicitly.

### Ship order and the dedup-off window
- **D-01:** **Repair first, two-source hardening second.** Release 1 = audit-table
  migration (CACHEFIX-01) + `scripts/opening_cache_repair.py` (CACHEFIX-02..07) +
  CACHEFIX-12 as a plain upsert through the existing `_upsert_opening_cache` (one shared
  function, two call sites) + the `OPENING_CACHE_BACKFILL_SQL` fix. Then the prod repair
  runs as the operator stage. Release 2 = CACHEFIX-08 (provenance columns, candidate ->
  promote write path, confirmed-only read paths) whose migration marks rows by audit
  status exactly as CACHEFIX-08 already states. — **Reversibility:** costly — flipping the
  order later means either accepting a multi-day prod window with opening dedup at ~0 (all
  2.57M legacy rows become candidates the moment CACHEFIX-08's read paths ship) or marking
  unscreened legacy rows `confirmed=true`, which makes the column lie.
  - Why: the write path is clean (18/18 rows after 2026-08-20 agree with a fresh 1M-node
    run, seed diagnosis 5), so there is no bleeding to stop first. Shipping hardening
    first would either switch opening dedup off on prod for the ~3-day repair (every
    opening ply re-evaluated, ~20-25% more engine cost on a fleet whose backfill lotteries
    never finish) or force `confirmed=true` on rows known to be 0.34%+ poisoned. Repair
    first keeps `confirmed` honest: it means "two hash-asserted evaluations agree".
  - Consequence: the repair script does NOT need to know about `confirmed`/`n_sources`;
    the CACHEFIX-08 migration derives them from `opening_cache_audit.status`
    (`screened_clean` / `confirmed_clean` / `repaired` -> `confirmed=true, n_sources=2`;
    everything else, including rows inserted after the seed, -> candidate). A future
    re-audit after hardening must set the columns itself; note that in the script's
    docstring, do not build it now.
  - CACHEFIX-12 ships in release 1 because it is a bug fix independent of the
    confirmation scheme and is the throughput win for the benchmark lane. Under
    first-write-wins its rows are the same worker results already landing in
    `game_positions`; rows inserted after `seed` are ignored by the repair (clean by
    diagnosis 5).
- **D-02:** Screen/confirm do not set any provenance column progressively (no such
  columns exist in release 1). Nothing in the repair depends on hardening.

### Prod run choreography
- **D-03:** **Nothing is paused.** The server full-drain tick, the remote workers and the
  PV/blob lotteries keep running through every stage. Justification per stage: seed /
  calibrate / screen only read the cache and write audit rows; confirm overwrites cache
  rows that the tick never overwrites (`ON CONFLICT` first-write-wins in release 1);
  propagate rewrites `game_positions` rows of long-completed carrier games that the drain
  is not holding; rederive is the only stage that touches rows a concurrent lane may also
  touch (`game_flaws` blob writes from the tier-4 lottery).
- **D-04:** **Rederive concurrency invariant (must be in the plan and tested):** rederive
  takes `SELECT ... FROM games WHERE id = :id FOR UPDATE` at the start of its per-game
  transaction, and a concurrent blob/PV submit for a flaw row that rederive removed must
  not resurrect that flaw (the submit's write must be a no-op for a missing `game_flaws`
  row, never an insert). The drain/submit paths currently take no game-row lock
  (verified 2026-09-09: no `with_for_update`/`FOR UPDATE` in `eval_apply.py`,
  `eval_drain.py`, `routers/eval_remote.py`), so the planner must read the blob-submit
  write path and either add the same single-row lock there or prove the no-resurrect
  property from its upsert shape. Test: rederive removes a flaw, then a blob submit for
  that ply lands, and `game_flaws` stays empty at that ply. Pausing the lotteries via the
  existing env gates is the fallback only if the lock cannot be added safely; record
  which was chosen.
- **D-05:** **Stage gating stays strict** as CACHEFIX-02 states (each stage refuses to run
  before the previous stage's `finished_at`). No pipelining of confirm behind a
  still-walking screen: the wall-clock saving is at most a day, and strict gating is what
  makes "re-run after a kill" and the per-stage timing in the report trivially correct.
  The screen walks engine games by `id` ascending (cursor = `last_game_id_walked`), not
  popular-first, for the same reason.
- **D-06:** **Hash-mismatch handling in screen:** when the replayed board's
  `compute_hashes` full hash does not equal the cache key for the first carrier found,
  try up to `MAX_CARRIERS_PER_HASH = 3` distinct carrier games (named constant) before
  marking `hash_mismatch`. A pasted game with an odd `initial_fen` must not by itself
  condemn a popular position. `hash_mismatch` rows are never evaluated and are left in
  the cache untouched (reported; a future re-audit decides).
- **D-07:** **CACHEFIX-10 legacy sample runs after `report`, as its own subcommand
  (`legacy-sample`)**, gated on `calibrate` having finished (it uses `screen_floor`).
  Design: 200 games fully evaluated before 2026-06-18 across ALL plies at depth 15,
  plus a like-for-like control of 50 games fully evaluated after 2026-08-20 on the same
  walk. Per-row disagreement = expected-score delta beyond `screen_floor` or mate/non-mate
  mismatch. Decision rule, written down in the summary whichever way it goes: build and
  run `screen --legacy-cohort` (walk whole games, plies > 20) only if the legacy
  disagreement rate at ply > 20 exceeds twice the control rate AND the absolute excess is
  at least 1 percentage point; otherwise record the numbers and build nothing.
  — **Reversibility:** reversible — the sample is ~25 minutes of engine time and can be
  re-run with a different rule. Runs after the main pipeline so a yes/no that may build
  nothing never delays the repair.

### Herrings and drills at repaired plies
- **D-08:** **`herring_pool` rows at repaired `(game_id, ply)` are KEPT, never deleted or
  regenerated.** Verified 2026-09-09: a pool row is self-sufficient — it stores its own
  `fen`, `arriving_move_uci`, `mover_color` and a five-entry MultiPV-5 `ladder` from its
  own Stockfish search (`app/models/herring_pool.py`, Phase 192 D-03/D-16). The
  `game_positions` eval is only a generation-time prefilter in
  `scripts/gen_red_herring_pool.py` (`abs(eval_cp) <= HERRING_PREFILTER_ABS_CP`), so a
  repaired eval cannot make a stored ladder wrong. `herrings_touched` is a report counter
  only: the number of pool rows whose `(game_id, ply)` appears in
  `opening_cache_repair_rows`. Also note the ~91% cross-user serving (memory
  `herring-pool-cross-user-ownership`): deleting rows would remove puzzles from strangers'
  Train sessions for no correctness gain.
- **D-09:** `drill_items` whose `(user_id, game_id, ply)` no longer has a `game_flaws`
  row are pruned (as the seed says); `drill_solves` are kept (history,
  `herring_pool_id`/game links are `SET NULL`-tolerant already). No `drill_items` are
  created for flaws ADDED by the repair; the normal drill top-up picks them up. No change
  to drill scheduling or streak state beyond the prune.

### Integrity check and the two-source agree tolerance
- **D-10:** **No in-app nightly tick.** CACHEFIX-09 is implemented as written: the lichess
  cross-check query and the opening bounce rate join the `db-report` skill's Sanity Checks
  section (`.claude/skills/db-report/SKILL.md` §3), with `n_bad > 5` flagged in the
  report. The ROADMAP goal's word "nightly" is superseded: there is no cron in this repo
  (in-process periodic asyncio tasks are the only pattern, `app/main.py`), the cross-check
  joins `game_positions` twice over every lichess-analysed game and is not something to
  run on prod every night, and after CACHEFIX-08 the real-time detector is the
  disagreement counter + Sentry (D-12), not a batch query. The `db-report` sanity section
  additionally reports `count(*) FILTER (WHERE disagreements >= 1)` on the cache once the
  column exists.
- **D-11:** **Two-source agreement is measured in expected-score units, not 50cp.**
  CACHEFIX-08's "within 50cp" is refined to: promote when
  `abs(expected_score(new) - expected_score(old)) <= OPENING_CACHE_AGREE_MAX_SCORE_DELTA`
  and mate/non-mate match (via `eval_cp_to_expected_score` /
  `eval_mate_to_expected_score` in `app/services/eval_utils.py`). The constant is a named
  module constant in `eval_drain.py` (the app must not depend on a
  `opening_cache_repair_progress` row existing at runtime: benchmark DB, dev, tests), set
  from the prod `calibrate` result: the measured `confirm_floor` (p99 of the 1M-node
  delta against a known-clean stored value), rounded up, with a docstring citing the
  calibration date and value. Because hardening ships after the repair (D-01) the
  number exists when the constant is written. Reason: a fixed cp cut is wrong twice over
  (100cp at +600 is nothing, 55cp at 0 is an inaccuracy boundary), exactly the argument
  the seed makes for the repair thresholds; the tolerance must be the same noise model.
- **D-12:** **Disagreement reporting is throttled per row, not per event.** A candidate
  that disagrees is replaced and `disagreements` is incremented (as CACHEFIX-08 says), but
  `sentry_sdk.capture_message` fires only when `disagreements` reaches 2 on the same row
  (a third evaluation also failed to agree with the value that replaced the first). With a
  p99 floor roughly 1% of honest second sources look like disagreements, which over 2.6M
  positions would be ~26k Sentry events for nothing; two consecutive misses on one
  position is the misalignment signature. The message string is fixed (grouping), hash
  and all values go in `set_context`, `set_tag("source", "opening-cache")`.
- **D-13:** **Self-promotion is impossible by construction.** The cache gains
  `source_game_id BIGINT NULL` (no FK, so the cache row survives game deletion). A result
  whose `game_id` equals the candidate's `source_game_id` neither promotes nor counts as a
  disagreement (a resubmitted or re-drained game is the same source). Two different games
  reaching the same position inside one tick or one submit batch are two genuine sources.
  Column set for CACHEFIX-08 is therefore: `confirmed`, `n_sources`, `disagreements`,
  `engine_version`, `written_at`, `confirmed_at`, `source_game_id`.
  — **Reversibility:** one-way — a migration on a 2.57M-row table that both read paths
  and both write paths key on; dropping `source_game_id` later would reopen the
  same-source self-promotion hole.

### Claude's Discretion
- Everything the seed and ROADMAP already lock is not re-decided here; where this file
  and the seed differ, this file wins (D-07 rule, D-10 no tick, D-11 units, D-12
  throttle, D-13 column). Anything else (batch sizes within the 500-row convention,
  subcommand flag names, report table layout, test fixture shapes) is the planner's.
- The optional 1-in-N canary from the seed is NOT built unless it is a trivial add-on;
  D-12 is the safety signal.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase spec (locked)
- `.planning/seeds/SEED-164-opening-eval-cache-poisoned-legacy-evals.md` — the full
  diagnosis, blast-radius numbers, histogram + lichess-internal control, bounce-rate noise
  floors, table shapes, stage semantics, reference SQL, the 9 named hashes and the game
  2356581 before/after fixture. Read end to end.
- `.planning/ROADMAP.md` §"Phase 220" — CACHEFIX-01..12, success criteria, out-of-scope,
  cross-cutting constraints (4-worker box via tunnel, one session per coroutine, never
  write an eval for an unasserted hash).

### Conventions the scripts must respect
- `.planning/notes/eval-completion-columns.md` — which columns mean "analyzed by us"
  (`full_evals_completed_at` + `lichess_evals_at IS NULL`), used to define the engine-game
  walk and the calibration sample.
- Memory `atomic-eval-submit-incremental-lease` (in `MEMORY.md`) — post-move shift (row P
  stores the eval of the position on row P+1), `_classify_and_fill_oracle` is a 4-way
  diff/upsert not delete-then-insert, dedup transplants must carry `pv`.
- `CLAUDE.md` §"Database design rules" — column types (SMALLINT + CHECK for status),
  FK/ondelete policy, no native ENUM; §"Critical Constraints" — no `asyncio.gather` on one
  session.
- `docs/dev-tooling.md` — script inventory and the `db_url_for_target` / `--db` pattern.

### Code the phase extends (read, do not re-derive)
- `app/services/eval_drain.py` — `_upsert_opening_cache` (~line 437, first-write-wins +
  pv self-heal), `OPENING_CACHE_BACKFILL_SQL`, `_full_drain_tick`, `_DEDUP_MAX_PLY`.
- `app/services/eval_apply.py` — `_fetch_dedup_evals` / `_resolve_full_eval`,
  `_classify_and_fill_oracle` (~992), the oracle-count / accuracy block (~1335-1375) to
  extract as `refresh_game_oracle_counts`, `apply_full_eval` (`update_opening_cache`,
  ~2775-2931), `_missing_flaw_pv_targets`.
- `app/routers/eval_remote.py` — `_fetch_cached_opening_hashes` (~211, lease omit),
  `_apply_atomic_submit` (~1167; the comment at ~1369 "update_opening_cache stays False
  here (Pitfall 4 / D-05)" is the exact site CACHEFIX-12 reverses; keep the trusted-
  operator gating), `_apply_flaw_blob_submit` (~951, the concurrent writer in D-04).
- `app/services/eval_utils.py` — `eval_cp_to_expected_score` (~65),
  `eval_mate_to_expected_score` (~90).
- `app/services/zobrist.py` — `compute_hashes` (~119), the hash assertion.
- `app/services/engine.py` — `evaluate` (depth-15 screen), `evaluate_nodes_with_pv`
  (the drain's 1M-node call), `EnginePool`, `STOCKFISH_POOL_SIZE`.
- `app/services/flaws_service.py` — `classify_game_flaws`, `INACCURACY_DROP` /
  `MISTAKE_DROP` / `BLUNDER_DROP`.
- `scripts/backfill_flaws.py` — gains `--from-repair-table` (single-writer rule in its
  docstring); `scripts/resweep_holed_games.py` — the `--db {dev,benchmark,prod}` /
  `db_url_for_target` / `--dry-run` / `--limit` script shape to copy.
- `scripts/gen_red_herring_pool.py` + `app/models/herring_pool.py` — why herrings are
  kept (D-08).
- `app/models/opening_position_eval.py`, `app/models/drill_item.py`,
  `app/models/drill_solve.py` — schemas touched by CACHEFIX-08 and the rederive prune.
- `.claude/skills/db-report/SKILL.md` §3 "Sanity Checks" — where CACHEFIX-09 lands.
- `tests/test_eval_worker_endpoints.py` — submit-endpoint fixtures for CACHEFIX-12.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `EnginePool` + `evaluate` / `evaluate_nodes_with_pv` (`app/services/engine.py`): the
  screen and confirm stages use them unchanged; `STOCKFISH_POOL_SIZE=4` on the local box.
- `compute_hashes` (`app/services/zobrist.py`) for the mandatory hash assertion before any
  write; `eval_cp_to_expected_score` / `eval_mate_to_expected_score` for every delta.
- `scripts/resweep_holed_games.py` and `scripts/backfill_flaws.py`: the `--db` target
  pattern, batch/commit loop shape and Sentry capture convention for long-running scripts.
- `run_periodic_guest_cleanup` / `run_periodic_train_reminders` (`app/main.py`
  `create_task` pattern) exist but are deliberately NOT used (D-10).
- `db-report` skill sanity section already has the shape for an "expected vs actual with
  threshold" check.

### Established Patterns
- Post-move storage: `game_positions` row P holds the eval of the position on row P+1;
  the cache is keyed by the position's own hash. Every propagate/screen query must join
  `prev.ply = gp.ply - 1`.
- `_classify_and_fill_oracle` is a diff/upsert; the drain is the single classifier
  writer (D-10 in `backfill_flaws.py`'s docstring) — the script must call through it.
- `IS NOT DISTINCT FROM` old-value predicate is the only thing that separates transplanted
  rows from independently evaluated ones (no provenance today).
- Scripts run against prod through `bin/prod_db_tunnel.sh`; only hashes and evals cross
  the wire.
- No game-row locking exists in the drain/submit write paths (D-04 makes rederive add one).

### Integration Points
- `eval_drain.py::_upsert_opening_cache` becomes the shared write function with two call
  sites (`_full_drain_tick`, `_apply_atomic_submit`) in release 1, and gains the
  candidate/promote logic in release 2.
- `eval_apply.py::_fetch_dedup_evals` and `eval_remote.py::_fetch_cached_opening_hashes`
  gain the `confirmed` filter in release 2.
- New Alembic migrations: release 1 (four audit/repair tables), release 2 (cache
  provenance columns + status-derived marking).
- `reports/opening-cache-repair/` (new directory) for the report stage output;
  `CHANGELOG.md [Unreleased]` user-facing bullet with release 1 (the repair) and a
  second bullet with release 2 if user-visible (it is not; a `chore` line suffices).

</code_context>

<specifics>
## Specific Ideas

- Acceptance fixture is game 2356581 (prod, user 28) plies 5/6 and cache row
  `-3185735734450884963` (~+9, best move e2e3), plus the 9 named hashes in the seed; the
  report and the phase verification assert them explicitly (CACHEFIX-11).
- Primary acceptance signal is the residual delta histogram matching the lichess-internal
  IQR control in every band above the noise floor (baseline 50 vs 20 at 150-250cp, 35 vs
  6 at 250-400cp), not a count at one cut; the bounce rate is a coarse sanity check only.
- Dev smoke must include a real SIGTERM mid-batch on every stage and a second invocation
  that resumes without duplicating or skipping rows (success criterion 1).

</specifics>

<deferred>
## Deferred Ideas

- Optional 1-in-N confirmed-hit canary (seed hardening item 3): not built unless trivial;
  revisit if D-12's disagreement signal proves too quiet.
- Multi-thread Stockfish build for the pool (noted in Phase 219 D-09): unrelated, stays a
  seed.
- A post-hardening re-audit mode that sets `confirmed`/`n_sources` from the script itself
  (needed only if the cache is ever re-screened after release 2): documented in the script
  docstring, not built.

### Reviewed Todos (not folded)
- "Bitboard storage for partial-position queries" — storage design idea, unrelated to the
  cache repair.
- "WR-01 pt-33 Tailwind axis label" — frontend, out of scope (no frontend change).
- "172 deferred review findings" — keyword noise (status/pending/source).
- "variation-tree nested button" — frontend, keyword noise.

</deferred>

---

*Phase: 220-opening-eval-cache-repair-two-source-confirmation*
*Context gathered: 2026-09-09*
