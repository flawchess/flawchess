---
id: SEED-164
status: promoted (→ Phase 220, 2026-09-09)
planted: 2026-09-09
updated: 2026-09-09 (promoted to Phase 220; two-source confirmation added to hardening; screen/confirm thresholds now derived from a measured noise floor in expected-score units, histogram-vs-control acceptance)
planted_during: ad-hoc investigation of game 2356581 (spurious blunders at ply 5/6), branch study/tilt
trigger_when: next maintenance window; MUST land before the next flaw-based benchmark refresh or any data story that uses opening flaw rates
scope: one repair phase (audit table + resumable screen/confirm/propagate/re-derive scripts + metrics report), one hardening plan (two-source confirmation replacing first-write-wins, submit path writes the cache so remote-worker lanes incl. the benchmark DB get opening dedup, provenance, backfill SQL, nightly cross-check), one open sample-screen question for the legacy cohort beyond ply 20
---

# SEED-164: `opening_position_eval` is poisoned with legacy wrong-position evals

## Symptom

Game 2356581 (bot game, 1.d4 d5 2.Nc3 Bf5 3.Bf4 e6 4.e3) shows two blunders at ply 5
(e6, `is_lucky`) and ply 6 (e3, `is_miss` + `is_squandered`). Browser Stockfish says e6 is
the best move and e3 is top-2. `game_positions.eval_cp` runs 9, **305**, 12 across plies
4/5/6. The +305 is a transplant from the opening dedup cache: the
`opening_position_eval` row for the position after 3...e6 holds `eval_cp = 305` while its
own cached PV is a quiet London line. A fresh run of the project engine on that position
returns +9 with best move e2e3.

The visible signature everywhere: evals bouncing `~0 -> +300 -> ~0` (or the mirror)
inside the first 20 plies, classified as a "lucky" blunder immediately followed by a
"squandered"/"miss" blunder.

## Diagnosis (established 2026-09-09 against prod)

1. **The cache is first-write-wins on eval_cp.** `_upsert_opening_cache`
   (`app/services/eval_drain.py`) only self-heals `pv` (`ON CONFLICT DO UPDATE SET pv`
   when the existing pv is NULL). A wrong `eval_cp` never corrects, and every later engine
   game reaching the position takes it as a dedup transplant (`_fetch_dedup_evals` /
   `_resolve_full_eval` in `app/services/eval_apply.py`, ply <= `DEDUP_MAX_PLY` = 20).
2. **The bad values predate the cache.** The cache shipped 2026-06-17 (c086d7984). The
   earliest carriers of every poisoned value examined are games with ids ~469k-620k
   whose `full_evals_completed_at` is 2026-06-14 to 06-16, i.e. the first days of the
   full-game drain (Phase 116/117, around the SEED-044 post-move convention fix
   d7bf552c3). Game 622723 already has 305 at ply 5 on 06-16 with no cache involved.
3. **The one-time backfill enshrined them.** `OPENING_CACHE_BACKFILL_SQL`
   (`eval_drain.py`, also archived `scripts/archive/backfill_opening_eval_cache.py`) is
   `SELECT DISTINCT ON (nxt.full_hash) ... ` with **no ORDER BY**, so the donor per
   position is arbitrary. For all 9 popular poisoned positions checked, clean donors
   existed at backfill time (10-43 each) and the poisoned early game won anyway.
4. **They are evals of the wrong position, not shallow evals.** Stockfish at depth 1-6 and
   at 1/10/100/1000 nodes gives -16..+17 for the 3...e6 position, never anything near
   +305; same for the other three positions tested. The values cluster at a piece
   (285, 295, 297, 300, 302, 305, 313, 349), which is what a hash-to-eval misalignment
   by one or two plies around a capture produces. The exact June/July mechanism is not
   pinned down and does not need to be: it is no longer active (see 5).
5. **The current write path is clean.** 18 of 18 cache rows first written after
   2026-08-20 agree with a fresh 1M-node engine run within 40cp. Nothing needs pausing.
6. **The suspect window extends past the backfill.** Among the 85 lichess-flagged bad
   rows (below), 11 have their earliest engine carrier after 2026-06-18, the latest on
   2026-07-26 (e.g. Accelerated Dragon `e4 c5 Nf3 g6 d4 cxd4 Nxd4 Bg7 Bc4`, cache 252 vs
   lichess median 0, carried by 37 games, first seen 2026-07-04). Either those donors were
   deleted / were lichess games that pre-Phase-174 could seed the cache, or the
   lease-submit path was still misaligning in July (see memory
   `atomic-eval-submit-incremental-lease`). Consequence: **no date cut identifies the
   bad rows**, and there are no provenance columns. Every row has to be screened.
7. **Only the server pool writes the cache.** `_upsert_opening_cache` is invoked solely
   from `_full_drain_tick` (`eval_drain.py` ~1119 via `eval_apply.py`
   `update_opening_cache=True`). Remote-worker submits never insert rows; they only
   consume the dedup fill. This is a gap in its own right, not just a diagnosis fact:
   remote workers carry ~85% of full-eval throughput (memory `worker-fleet-topology`),
   so most fresh opening evals never reach the cache, and a lane evaluated entirely by
   remote workers (the benchmark DB) gets no dedup at all. Its cache is empty after
   ~91k engine games, which is why the benchmark DB is clean but also why every one of
   those games paid full price for its opening plies. Consequences: the poisoned donors
   were server-pool writes (or the backfill); a confirmation scheme that counts only
   tick-path writes as sources would starve; and **the phase must make the submit path
   write the cache** (hardening item 4) so the benchmark lane, and prod's remote-heavy
   periods, benefit from opening dedup.

## Blast radius (lower bound; the total is unknowable without screening)

| Measure | Value |
|---|---|
| Cache rows | 2,567,473 (1,642,720 without pv; 150,837 with a one-move pv) |
| Cache rows with `abs(eval_cp) >= 150` | 704,308 (most are real early blunders, NOT a usable filter) |
| Cache rows checkable against >=3 independent lichess-evaluated games (ply 1-12) | 25,444 |
| ...of which off by >150cp vs the lichess median | 87 (0.34%); 45 in the 240-360cp band |
| Engine games carrying those 85 values (excl. 2 magnitude<150) | 4,361 |
| Games carrying the single 3...e6 value | 226 of 305 games with that position |
| Distinct opening hashes present in pre-2026-06-18 engine games (the backfill's donor pool) | 943,168 |
| Fully evaluated games in that legacy cohort | 95,428 of 633,180 |

Extrapolating 0.34% to the whole cache gives roughly 8-9k poisoned rows, but the rate is
higher for popular positions (9 of the 20 most shared big-eval positions at ply <= 8),
so the game count is what matters and it will be in the tens of thousands of flaw rows.

Independent references that prove poisoning (reuse in the plan's verification):

```sql
-- lichess cross-check: cache vs median of lichess-analysed games (never touch the cache)
WITH l AS (
  SELECT gp.full_hash,
         percentile_cont(0.5) WITHIN GROUP (ORDER BY prev.eval_cp) AS med, count(*) AS n
  FROM games g
  JOIN game_positions gp   ON gp.game_id = g.id AND gp.ply BETWEEN 1 AND 12
  JOIN game_positions prev ON prev.game_id = g.id AND prev.ply = gp.ply - 1
  WHERE g.lichess_evals_at IS NOT NULL AND prev.eval_cp IS NOT NULL AND prev.eval_mate IS NULL
  GROUP BY gp.full_hash HAVING count(*) >= 3)
SELECT count(*) AS n_checked,
       count(*) FILTER (WHERE abs(o.eval_cp - l.med) > 150) AS n_bad
FROM l JOIN opening_position_eval o ON o.full_hash = l.full_hash
WHERE o.eval_mate IS NULL;
-- 2026-09-09 baseline: 25,444 / 87. Target after repair: 0 (allow a handful of
-- genuine depth disagreements in trap lines, e.g. the Qf3xa8 rook grab at +300 vs +500).
```

The 150cp cut above is a **sizing and verification** statistic, not the detector (the
repair screens every cache row against a fresh engine eval, see step 2). To answer
"what about poison below 150cp", the same query as a histogram, with the spread of
lichess's own evals per position (IQR across the >=3 lichess games) as the noise control
(prod, 2026-09-09):

| abs(delta) band | cache vs lichess median | lichess-internal IQR (control) |
|---|---|---|
| < 25 | 21,987 | 24,000 |
| 25-50 | 3,064 | 1,132 |
| 50-75 | 203 | 183 |
| 75-100 | 52 | 66 |
| 100-150 | 49 | 37 |
| 150-250 | 50 | 20 |
| 250-400 | 35 | 6 |
| > 400 | 4 | 0 |

Reading: the 25-50 excess is the systematic offset between our 1M-node Stockfish and
lichess cloud evals (a 25cp screen cut would flag ~12% of the cache for nothing). Between
50 and 100cp the cache matches the control, so this check sees no hidden sub-100
population; the excess sits at piece magnitude, consistent with misalignment around a
capture. Caveat: these are popular ply-1-12 positions, mostly quiet mainlines. Sharp
lines with pawn grabs, where a one-ply misalignment yields ~100cp, are underrepresented,
so the repair must not rely on a hand-picked cp threshold (see "Thresholds" below).

```sql
-- histogram + control (report verification block, before and after)
WITH l AS (
  SELECT gp.full_hash,
         percentile_cont(0.5) WITHIN GROUP (ORDER BY prev.eval_cp) AS med,
         percentile_cont(0.75) WITHIN GROUP (ORDER BY prev.eval_cp)
           - percentile_cont(0.25) WITHIN GROUP (ORDER BY prev.eval_cp) AS iqr
  FROM games g
  JOIN game_positions gp   ON gp.game_id = g.id AND gp.ply BETWEEN 1 AND 12
  JOIN game_positions prev ON prev.game_id = g.id AND prev.ply = gp.ply - 1
  WHERE g.lichess_evals_at IS NOT NULL AND prev.eval_cp IS NOT NULL AND prev.eval_mate IS NULL
  GROUP BY gp.full_hash HAVING count(*) >= 3),
d AS (SELECT abs(o.eval_cp - l.med) AS delta, l.iqr
      FROM l JOIN opening_position_eval o ON o.full_hash = l.full_hash WHERE o.eval_mate IS NULL),
h AS (SELECT width_bucket(delta, ARRAY[25,50,75,100,150,250,400]) AS b, count(*) AS n_cache FROM d GROUP BY 1),
c AS (SELECT width_bucket(iqr,   ARRAY[25,50,75,100,150,250,400]) AS b, count(*) AS n_ctrl  FROM d GROUP BY 1)
SELECT coalesce(h.b, c.b) AS bucket, n_cache, n_ctrl FROM h FULL JOIN c ON c.b = h.b ORDER BY 1;
```

Conventions the scripts must respect (see `_post_move_eval` in `eval_apply.py` and
memory `atomic-eval-submit-incremental-lease`):

- `game_positions` row P stores the eval of the position AFTER move P, i.e. the eval of
  the position whose `full_hash` sits on row P+1. The cache is keyed by the position's
  own hash. So **cache[hash(row P+1)] == game_positions[row P].eval_cp** for a
  transplant, and `best_move`/`pv` on row P+1 are FROM that position.
- The cache stores only `full_hash`; there is no FEN. A board can only be rebuilt by
  replaying a carrier game's moves (`game_positions.move_san` ordered by ply, honouring
  `games.initial_fen` for pasted games). Use `app/services/zobrist.py: compute_hashes`
  to assert the replayed hash equals the cache key before evaluating; mismatch = skip
  and mark `hash_mismatch` (never write an eval for a board we could not verify).
- Lichess-eval games (`lichess_evals_at IS NOT NULL`) never read the cache today, but 2
  of the 226 carriers of the 305 value are lichess games, so the propagation must be
  keyed by hash + exact old value, not by game type.

## Repair design

Everything below is **resumable by construction**: all state lives in DB tables keyed
by `full_hash` or `(game_id, ply)`, every step is a status transition, commits happen
every N rows, and re-running any step after a kill picks up where the status column
says. No in-memory-only progress, no "done" files. `--db {dev,benchmark,prod}` is
required (pattern: `scripts/resweep_holed_games.py`, `db_url_for_target`). Every step
has `--dry-run` and `--limit`. Engine work uses the project `EnginePool`
(`STOCKFISH_POOL_SIZE`) so it can run from the local 4-worker box against prod through
`bin/prod_db_tunnel.sh`; only hashes and evals cross the wire.

### Thresholds (measured, in expected-score units; decision 2026-09-09)

A hand-picked 100cp cut is wrong twice over: 100cp at +600 changes nothing while 100cp
at 0 is a mistake (severity boundaries near equality under the Lichess sigmoid:
~54cp inaccuracy, ~110cp mistake, ~168cp blunder, from `INACCURACY_DROP` 0.05 /
`MISTAKE_DROP` 0.10 / `BLUNDER_DROP` 0.15 in `flaws_service.py`), and a cache error of
55-100cp can still manufacture a spurious inaccuracy pair. So:

- **Units**: every delta in the audit table is `abs(expected_score(new) -
  expected_score(old))` via `eval_cp_to_expected_score` /
  `eval_mate_to_expected_score` (`app/services/eval_utils.py`); keep `delta_cp` as a
  display column only. Mate vs non-mate disagreement is always a flag.
- **Noise floor is measured, not assumed** (a `calibrate` subcommand, run once before
  `screen`, result stored in `opening_cache_repair_progress`): take ~500 cache rows
  written after 2026-08-20 (known clean, diagnosis point 5), rebuild + hash-assert the
  board, run both the depth-15 `evaluate` and the 1M-node `evaluate_nodes_with_pv`,
  and record p99 of the expected-score delta for each budget against the stored value.
  `screen_floor` = p99(depth-15 vs stored); `confirm_floor` = p99(1M vs stored).
  Expect roughly 50cp-equivalent near equality; refuse to run `screen` with an
  unset floor.
- **Screen** flags when the expected-score delta exceeds `screen_floor` (screening is
  cheap either way; only the confirm stage scales with the flag count, and ~1% flagged
  is ~26k 1M-node evals, about a day on the 4-worker box).
- **Confirm overwrites whenever the 1M-node value differs from the stored one by more
  than `confirm_floor`**. The fresh value is at least as good by construction (same
  budget as the drain, hash-asserted board), so there is no reason to keep an old
  value that merely fell under an arbitrary cut. Propagate stays cheap (old-value
  predicate); rederive is a diff, so games whose classification does not change cost
  one classify call and no writes.
- **Acceptance is the residual distribution, not a count at one cut**: after repair the
  cache-delta histogram above must match the lichess-internal control in every band
  above the noise floor. That is the check that also covers positions below any single
  threshold, and it needs no threshold to state.

### Tables (Alembic migration, kept after the repair as the audit trail)

`opening_cache_audit` (one row per cache row):

| column | notes |
|---|---|
| full_hash BIGINT PK | FK-free; the cache row may be deleted later |
| status TEXT CHECK | `pending` → `screened_clean` / `flagged` → `confirmed_bad` / `confirmed_clean` / `orphan` / `hash_mismatch` → `repaired` |
| old_cp, old_mate, old_best_move, old_pv | snapshot of the cache row at seeding time |
| sample_game_id, sample_ply | carrier used to rebuild the board |
| screen_cp, screen_mate, screened_at | depth-15 result |
| full_cp, full_mate, full_best_move, full_pv, confirmed_at | 1M-node result |
| delta_score REAL, delta_cp SMALLINT | expected-score difference (the decision column) and its cp-equivalent for display; mate mapped through the existing sigmoid helpers |
| engine_version TEXT | from `uci` `id name` |
| repaired_at | set by the propagate step |

`opening_cache_repair_rows` (one row per rewritten `game_positions` row):
`game_id, ply, full_hash, old_cp, old_mate, new_cp, new_mate, best_move_replaced BOOL,
repaired_at`, PK `(game_id, ply)`.

`opening_cache_repair_games` (one row per affected game):
`game_id PK, user_id, status (pending|reclassified|failed), rows_repaired,
flaws_before_inacc/mist/blund, flaws_after_inacc/mist/blund, flaws_removed,
flaws_added, drill_items_pruned, herrings_touched, white_acpl_before/after,
black_acpl_before/after, reclassified_at, error TEXT`.

`opening_cache_repair_progress` (single row): `last_game_id_walked` for step 2,
`screen_floor`, `confirm_floor`, `calibration_n`, `calibrated_at` from the calibrate
step, plus `stage_started_at/finished_at` per stage for the report's timing.

### Step 1: seed (`scripts/opening_cache_repair.py seed`)

`INSERT INTO opening_cache_audit (full_hash, status, old_*) SELECT ... FROM
opening_position_eval ON CONFLICT (full_hash) DO NOTHING`. One statement, idempotent.
Rows inserted into the cache after seeding are clean by (5) and are ignored.

### Step 1b: calibrate (`... calibrate`)

Measures `screen_floor` / `confirm_floor` as described under "Thresholds" and writes
them to `opening_cache_repair_progress`. Idempotent (re-running overwrites with a fresh
sample); `--n` defaults to 500. `screen` refuses to run until this has finished.

### Step 2: screen (`... screen`)

Walk engine games by `id` ascending from `last_game_id_walked`, batches of ~200 games,
replay the first `min(DEDUP_MAX_PLY + 1, ply_count)` plies, and for each position whose
audit row is `pending`: assert the hash, run the depth-15 `evaluate` (~0.09s), write
`screen_*`, set `screened_clean` when the expected-score delta is within `screen_floor`
and mate/non-mate agree, else `flagged`. Advance `last_game_id_walked` per batch in the same transaction as the
rows. Re-walking a game after a kill is harmless because rows are status-gated.
When the walk finishes, any row still `pending` has no carrier: mark `orphan` and
delete it from the cache (a future game will re-evaluate it once; cheap).
Budget: 2.57M x 0.09s ~ 65 CPU-hours; ~16h on the 4-worker box.

Why depth-15 for the screen and not the 1M-node call: 10x cheaper, and with the flag
cut at the measured depth-15 noise floor nothing that could move a flaw boundary
survives the screen unflagged. Step 3 exists to turn the screen's false positives
back into clean rows.

### Step 3: confirm (`... confirm`)

For `flagged` rows: rebuild the board from the recorded sample, run
`evaluate_nodes_with_pv` (the same call the drain uses), write `full_*`. Expected-score
delta beyond `confirm_floor` (or mate/non-mate disagreement) → `confirmed_bad` and
overwrite the cache row (`eval_cp, eval_mate, best_move, pv`); else `confirmed_clean`
(screen noise, cache untouched). Both branches are a status
transition per row, so a kill mid-batch loses at most the uncommitted batch.

### Step 4: propagate (`... propagate`)

For each `confirmed_bad` hash not yet `repaired`:

```sql
UPDATE game_positions p
SET eval_cp = :new_cp, eval_mate = :new_mate
FROM game_positions n
WHERE n.full_hash = :hash AND n.ply BETWEEN 1 AND 20        -- ix_gp_full_hash_opening
  AND p.game_id = n.game_id AND p.user_id = n.user_id AND p.ply = n.ply - 1
  AND p.eval_cp IS NOT DISTINCT FROM :old_cp AND p.eval_mate IS NOT DISTINCT FROM :old_mate
RETURNING p.game_id, p.ply, ...
```

The `old value` predicate is what makes this safe: rows that carry a different value
were evaluated independently (pre-cache engine games, lichess games, resweeps) and are
left alone. On row `n` replace `best_move`/`pv` only when they equal the old cached
`best_move`/`pv` (i.e. they were transplanted too). Insert one
`opening_cache_repair_rows` row per RETURNING row and upsert the game into
`opening_cache_repair_games (status='pending')`. Set `repaired_at` on the audit row in
the same transaction. Resumable: re-running finds no rows matching the old value.

### Step 5: re-derive per game (`... rederive`)

For each `opening_cache_repair_games` row with `status='pending'`, in one transaction:

1. Snapshot `flaws_before_*` from `game_flaws` for the game (by severity) and the four
   accuracy/ACPL columns.
2. Re-run flaw classification through the SAME path the drain uses:
   `flaws_service.classify_game_flaws` + `flaw_record_to_row` and the 4-way diff/upsert in
   `_classify_and_fill_oracle` (`eval_apply.py`; it is a diff, not delete-then-insert,
   see memory). Extend `scripts/backfill_flaws.py` with `--from-repair-table` rather than
   writing a second classifier call site (D-10 single-writer rule in its docstring).
3. Recompute oracle counts + accuracy/ACPL. Extract the block at
   `eval_apply.py` ~1335-1375 into a shared `refresh_game_oracle_counts(session, game,
   positions)` so the drain and the script cannot drift (the archived
   `backfill_accuracy_acpl.py` did this separately; do not resurrect it).
4. A repaired ply can become a NEW flaw that has no `allowed_pv_lines`/`missed_pv_lines`
   yet. Count these as `flaws_added` and re-arm the game for the existing PV/blob
   lottery (clear `blobs_completed_at`; confirm with `_missing_flaw_pv_targets` semantics
   during planning, do not invent a new PV writer).
5. Prune `drill_items` whose `(user_id, game_id, ply)` no longer has a `game_flaws` row
   (the drill join already filters them, but they hold streak state that would resurrect
   if the flaw ever reappeared). Count as `drill_items_pruned`. Keep `drill_solves`
   (history).
6. `herring_pool` rows at repaired `(game_id, ply)`: the herring is defined by the
   position's eval being fine; a repaired eval can flip that either way. Planning must
   read the writer in `app/repositories/train_repository.py` and decide delete-vs-keep;
   count as `herrings_touched` either way.
7. Gem/great badges need nothing: `best_move_tier_sql` / `classify_best_move` compute
   the tier at read time from `game_positions` evals + `game_best_moves`, so they
   self-heal with step 4.
8. Write `flaws_after_*`, `flaws_removed = sum(before) - sum(after) + flaws_added`,
   `status='reclassified'`. On exception: `status='failed'`, `error`, Sentry capture,
   continue (never leave a game half-written: the transaction covers 1-8).

### Step 6: report (`... report`, read-only, run any time)

Prints and writes `reports/opening-cache-repair/opening-cache-repair-YYYY-MM-DD.md`:

- Cache: rows seeded / screened_clean / flagged / confirmed_bad / confirmed_clean /
  orphan / hash_mismatch / repaired; delta histogram (old vs new) for confirmed_bad;
  top-30 confirmed_bad positions by carrier count with the SAN line.
- Positions: `game_positions` rows rewritten; how many also had best_move/pv replaced;
  by ply.
- Games: affected games, by platform and by user (top 20 users, plus the count of
  users with >= 1 affected game); per-game rows repaired distribution.
- Flaws: before/after totals by severity; **spurious flaws removed**; flaws added;
  games whose blunder count changed; drill items pruned; herrings touched; accuracy
  and ACPL mean shift for affected games.
- Verification block: the lichess cross-check query above re-run (n_checked / n_bad),
  the delta histogram with the lichess-internal control (must match in every band above
  the noise floor after repair; this is the primary acceptance signal), the measured
  `screen_floor` / `confirm_floor`, the opening bounce rate (`|eval_P - eval_{P-1}| >= 200 AND |eval_{P+1} - eval_{P-1}|
  <= 60`, plies 2-19) before/after, and the status of game 2356581 plies 5/6 and the 9
  named hashes (must read `confirmed_bad` → `repaired`).
  Bounce-rate noise floor from the cache-free benchmark DB (engine games, 1-in-8
  sample, 198k rows, 2026-09-09): 0.618% any bounce, 0.235% in the 250-360cp band.
  Prod engine games on the same definition (1-in-16 sample): legacy pre-cutoff 0.798% /
  0.298%, mid 0.625% / 0.243%, recent 0.844% / 0.271%. The poison is ~0.1-0.2pp on top
  of a ~0.6% legitimate blunder-then-miss rate, so the bounce rate is a coarse sanity
  check only; the audit table counts and the lichess cross-check are the real
  verification.
- Timing per stage from `opening_cache_repair_progress`.

Run order: seed → calibrate → screen → confirm → propagate → rederive → report. Each step is
independently re-runnable and refuses to run out of order (checks the previous stage's
`finished_at`). Expect a couple of days wall clock for screen; the rest is hours.

### Operational

- Run from the local 4-worker box against prod via the tunnel (memory
  `remote-workers-cover-pool`: prod CPU starvation during a heavy pass is acceptable,
  but here the engine work does not even touch prod CPU). `STOCKFISH_POOL_SIZE=4`.
- No `asyncio.gather` on one session; one session per worker coroutine, batches of 500
  rows per commit.
- Do NOT truncate the cache. It would not repair a single game (games need the diff
  to be found), it costs opening-ply engine work on every new import until popular
  positions refill, and there is no provenance to truncate selectively. Screening the
  2.57M unique positions is also the minimal set: repairing from the game side would be
  95k legacy games x ~20 plies.
- **Benchmark DB is NOT affected** (verified 2026-09-09, correcting an earlier draft of
  this seed that called it "a clone with the same poison"). It is an independent import
  with its own engine evals, its `opening_position_eval` table is empty, and the
  discovery position has 693 carriers there with median eval 0 and zero rows at 305.
  Reason: only the server full-drain tick writes the cache (`_full_drain_tick` passes
  `update_opening_cache=True` with `_upsert_opening_cache`); the remote-worker
  lease/submit path (`routers/eval_remote.py`) only READS it for the dedup fill, and the
  benchmark lane is evaluated through remote workers. So benchmarks and stories need no
  re-clone or re-run because of this seed. The benchmark DB is also useless as a
  per-game reference for prod: 7 of 1,500 sampled legacy prod lichess games exist
  there, 1 of them engine-evaluated. Its empty cache is the symptom of hardening
  item 4; after that fix the benchmark lane gains opening dedup for the first time.
- Changelog: user-facing bullet (early users, game ids < ~620k, will see opening flaw
  counts drop slightly and a few gems/greats appear or vanish).
- Dev DB: run the same pipeline against dev first (`--db dev`) for the smoke test; the
  dev cache is small. Never gate on `bin/reset_db.sh` (memory `no-dev-db-reset-in-plans`).

## Hardening (separate plan, can ship before the repair)

1. **Provenance on the cache**: `written_at`, `engine_version`, `node_budget`, `source`
   (`tick` / `backfill` / `repair`). Without these, this audit is unrepeatable and the next
   Stockfish bump silently mixes engines in a first-write-wins table.
2. **`OPENING_CACHE_BACKFILL_SQL`**: delete it (the backfill is archived) or give it a
   deterministic `ORDER BY nxt.full_hash, g.full_evals_completed_at DESC, cur.pv IS NULL`
   so the newest pv-bearing donor wins. Tests reference it as the "gate"; keep the gate
   predicate, fix the ordering. Under item 3 any backfilled row is a candidate, never
   confirmed.
3. **Two-source confirmation (replaces first-write-wins; the main measure).** Decision
   2026-09-09 after weighing keep-vs-drop: the cache saves roughly 20-25% of per-game
   engine cost (about 12.7M opening-ply evals over 633k games collapse onto 2.57M
   distinct positions, so ~4 in 5 opening evals are hits) and lets weak remote workers
   skip the opening. Dropping it would push that cost onto a fleet whose backfill
   lotteries already never finish. The risk is asymmetric: one bad write on a popular
   position taints hundreds of games forever, and a canary only catches it late. So keep
   the cache but stop trusting a single write:
   - Schema: add `confirmed BOOL NOT NULL DEFAULT false`, `n_sources SMALLINT`,
     `engine_version TEXT`, `written_at`, `confirmed_at` (folds item 1 in).
   - Write path (`_upsert_opening_cache`): no row → insert as **candidate**
     (`confirmed=false`, `n_sources=1`). Candidate exists and the new engine result
     agrees within 50cp (mate/non-mate must match) → promote (`confirmed=true`,
     `n_sources=2`, keep the pv-bearing/longer pv). Candidate exists and disagrees →
     replace the candidate with the new value, bump a `disagreements` counter,
     `sentry_sdk.capture_message` with `set_context(hash, both values)` so a recurring
     misalignment is visible within a day instead of a quarter. Confirmed rows are never
     overwritten by the tick path (only by the repair script or a future re-audit).
   - Read path (`_fetch_dedup_evals` in `eval_apply.py` and
     `_fetch_cached_opening_hashes` in `routers/eval_remote.py`): transplant and
     lease-omit **only `confirmed` rows**. A candidate position is evaluated again by
     the next game that reaches it; that second evaluation is what promotes it.
   - **The submit path must be a source too**: see hardening item 4, which is a
     prerequisite for this item to promote anything in remote-heavy lanes.
   - Cost: one extra eval per distinct position ever cached, ~2.6M against the ~10M
     saved, so about three quarters of the benefit survives. A misaligned hash-to-eval
     pair would have to repeat identically to poison anything.
   - Interplay with the repair: rows that come out of the repair as `screened_clean`,
     `confirmed_clean` or `repaired` had their board hash-asserted and were evaluated
     twice (old value + screen, or screen + full), so the migration marks them
     `confirmed=true, n_sources=2`. Rows never screened (inserted after the audit seed)
     start as candidates. Nothing in the repair depends on this item, and this item
     can ship first; if it ships first, the repair's confirm step must set `confirmed`
     itself.
   - Engine version is recorded, not enforced. Demoting 2.57M rows on a Stockfish bump
     would double opening cost for months; evals are already non-reproducible across
     machines at sub-percentile magnitude (note in `engine.py`). Keep a documented
     `--demote-engine-version <v>` path in the repair script for a bump that changes the
     eval scale (new NNUE net), and decide per bump.
   - Optional canary (1 in N confirmed hits re-evaluated, N ~ 500) only if trivial to
     add on top; it is no longer the safety mechanism.
4. **Submit path writes the cache (bug fix, required).** `_upsert_opening_cache` is
   called only from `_full_drain_tick`; the remote-worker submit in
   `routers/eval_remote.py` (`_apply_*_submit` paths that merge worker results into
   `engine_result_map`) never inserts opening-region rows. Fix: after a submit is
   accepted and applied, run the same cache write (candidate/promote logic from item 3,
   or the plain upsert if item 3 ships later) over the submitted opening-region targets,
   restricted to `ply <= DEDUP_MAX_PLY`, non-terminal, non-null evals, exactly as the
   tick path filters. One shared function, two call sites; do not duplicate the
   dedup-by-hash collapse. Trusted-operator gating stays as it is in that router: only
   submissions the server already accepts as evals count, so this adds no new trust
   surface. The cache-aware lease (`_fetch_cached_opening_hashes`) already omits cached
   positions, so once rows exist the benchmark lane's workers stop re-grinding openings
   with no further change. Acceptance: on the benchmark DB, `opening_position_eval`
   grows as the lane progresses (it is 0 rows today after ~91k engine games), and a
   leased game whose opening positions are cached carries fewer engine targets than an
   uncached one. Test with the existing submit-endpoint fixtures in
   `tests/test_eval_worker_endpoints.py`: a submit for a game with opening plies leaves
   rows in the cache; a second game reaching the same positions gets them omitted from
   its lease.
5. **Nightly integrity check**: add the lichess cross-check query and the opening bounce
   rate to the `db-report` skill's sanity section with a threshold (n_bad > 5 flags).
6. **Legacy cohort beyond ply 20 (open question)**: the misalignment was not
   cache-specific, only amplified by it. The 95k games fully evaluated before
   2026-06-18 may carry the same wrong-position evals at plies > 20 where nothing
   transplants them but the flaws are equally spurious (e.g. game 480700 ply 13 shows
   366 between 218 and 305 with a pv that does not match its best_move). Sample-screen
   200 of those games at depth 15 across all plies; if the disagreement rate at
   ply > 20 is above the fresh-game noise floor, add a `--legacy-cohort` mode to the
   screen that walks whole games instead of the cache. Decide from the sample, not
   from this seed. (The benchmark DB cannot answer this by diffing: cross-DB game
   overlap is ~0.5%.)

## Acceptance check: the game this was discovered in

The problem was discovered in **game_id = 2356581 (prod, user 28), plies 5 and 6**. It
is the canonical before/after fixture; the report step and the phase verification must
both assert it explicitly.

Before (2026-09-09):

| ply | move | `game_positions.eval_cp` | `game_flaws` row |
|---|---|---|---|
| 4 | Bf4 | 9 | none |
| 5 | e6 | **305** (transplant from cache hash `-3185735734450884963`) | severity 2, `is_lucky` |
| 6 | e3 | 12 | severity 2, `is_miss`, `is_squandered` |
| 21 | O-O | 395 (real) | severity 2 (real, must survive) |

After the repair, expected:

- `opening_position_eval` row `-3185735734450884963` reads ~+9 (engine 2026-09-09: 9,
  best move e2e3) and its audit row is `repaired`.
- `game_positions` ply 5 of game 2356581 reads ~+9; plies 4 and 6 unchanged.
- `game_flaws` rows at plies 5 and 6 are gone; the ply-21 blunder remains.
- `games.white_blunders` for 2356581 goes 1 → 0 and `black_blunders` 2 → 1;
  `white_accuracy`/`white_acpl` improve accordingly.
- The same holds for the other 225 engine games carrying 305 at that position (count
  them before and after with the query below), and for the 9 named hashes in the
  diagnosis (`3250950765068847520`, `-1357424544074167494`, `3912952322572315143`,
  `-4495720059219567338`, `-3692655065124884866`, `6991966663941067682`,
  `-4230257548248121256`, `-7106566961782875842`, `-3185735734450884963`).

```sql
-- carriers of the poisoned value at the discovery position (226 before, 0 after)
SELECT count(*) FROM game_positions gp
JOIN game_positions prev ON prev.game_id = gp.game_id AND prev.ply = gp.ply - 1
WHERE gp.full_hash = -3185735734450884963 AND prev.eval_cp = 305;

-- the discovery game itself
SELECT ply, severity, is_lucky, is_miss, is_squandered
FROM game_flaws WHERE game_id = 2356581 ORDER BY ply;   -- expect only ply 21
```

## Explicitly not in this seed

- Changing flaw thresholds, the post-move storage convention, or `DEDUP_MAX_PLY`.
- Re-evaluating lichess-analysed games (their evals are lichess's and never took
  transplants except the 2 carriers handled by step 4's value predicate).
- Rebuilding `herring_pool` or drill scheduling beyond pruning orphans.
- Any frontend change.
- Pinning down the exact June/July misalignment mechanism; only worth doing if the
  legacy-cohort sample (hardening item 6) shows it also hit plies > 20 at scale.
