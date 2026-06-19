---
id: SEED-053
status: dormant
planted: 2026-06-17
planted_during: v1.28 Tactic Tagging
trigger_when: when the full-eval drain throughput becomes a bottleneck again (a large re-drain, a new big-import wave, or a backlog the pool can't clear fast enough), OR when the eval-reuse `DISTINCT ON (full_hash)` query reappears as a top server-time consumer in a db-report
scope: medium
---

# SEED-053: Opening-eval dedup cache table (`opening_position_eval`)

## Why This Matters

The full-eval drain's dedup lookup (`_fetch_dedup_evals`, `app/services/eval_drain.py:270`)
is the **single largest consumer of total DB server time** in prod. From the
2026-06-17 db-report (stats window since 2026-06-15 reset):

- `DISTINCT ON (full_hash) … eval_cp, eval_mate, best_move` — **8.4 s avg, 10,655 calls,
  89M ms total (~24.7 h cumulative)**. Dominates total server time.

It's called **once per game** during the drain to recover a position's own eval/best_move
from an existing engine eval at the same `full_hash` (cross-user dedup, D-116-02), so it
can skip a Stockfish run. The dedup itself is correct and valuable — but the *lookup* is
pathologically expensive, and it's plausibly the drain's per-game serial bottleneck.

## Root Cause (measured)

The cost is **low-ply fan-out** under **post-move storage**, not a missing index. A
position's eval lives in the *predecessor* row (the move that reached it), so the lookup
is a self-join: index `ix_gp_full_hash_opening` finds the hash, then joins back one ply to
read `eval_cp`. Common opening positions share one `full_hash` across nearly all games:

| ply | distinct hashes | dup factor (rows / hash) |
|---|---|---|
| 0 | 46 | **13,534×** |
| 2 | 522 | 1,191× |
| 4 | 9,133 | 68× |
| 6 | 42,634 | 14.5× |
| 13+ | 335k–522k | 1.2–1.8× (≈unique) |

Every game has the ply-0 starting position → every lookup self-joins ~622k candidate
rows just to keep one. Dedup value is concentrated at ply 0–6 and near-zero past ply ~13.

## EXPLAIN evidence (prod, real 21-hash batch incl. ply-0)

| Approach | Exec time | Buffers touched |
|---|---|---|
| Current `DISTINCT ON` self-join | **16.4 s** | 6.5M |
| `LATERAL … LIMIT 1` rewrite (no new table) | **7.8 s** | 4.2M |
| **Cache table (projected)** | **~1–5 ms** | 21 PK probes on an ~80MB resident table |

**The cheap query rewrite only buys 2× and is still ~8 s** — a structural ceiling: under
post-move storage the eval is on a *different* row than the hash match, so no covering
index can ever serve the lookup. A position-keyed cache sidesteps the join entirely.

## Proposed Design

A denormalized, position-keyed cache:

```sql
CREATE TABLE opening_position_eval (
  full_hash  BIGINT   PRIMARY KEY,
  eval_cp    SMALLINT,
  eval_mate  SMALLINT,
  best_move  VARCHAR(5)
);
```

- **Size:** ~1.06M rows (prod's distinct opening hashes that have an our-engine eval),
  ~80MB with the PK index — smaller than `shared_buffers` (2GB), so it stays fully
  resident and never touches the 10GB `game_positions` table or fights the drain for
  buffers. (Prod ply≤20: 12.9M rows → 4.68M distinct hashes → 1.06M cacheable.)
- **No invalidation / FK / cascade.** The cached value is *position-intrinsic and
  immutable* (the eval of a position doesn't depend on which game reached it). A dangling
  entry after a game/user deletion is still a correct eval. This is the headache that
  usually kills cache tables and it simply doesn't apply here.
- **Read path:** replace the `_fetch_dedup_evals` self-join with
  `SELECT full_hash, eval_cp, eval_mate, best_move FROM opening_position_eval
  WHERE full_hash = ANY(:hashes)`. **Pure drop-in** — keep every existing read-side guard
  unchanged (`t.ply <= DEDUP_MAX_PLY`, `not in flaw_adjacent_plies`, `not is_terminal`).
- **Write path:** the drain already writes `eval_cp/eval_mate/best_move`; add an
  `INSERT … ON CONFLICT (full_hash) DO NOTHING` for `ply ≤ DEDUP_MAX_PLY` engine evals
  (first eval per hash wins; DO NOTHING avoids overwrite churn — eval is non-deterministic
  so re-writing buys nothing).
- **Backfill:** one-time migration `INSERT … SELECT DISTINCT ON (full_hash) …` from the
  current self-join over our-engine games (~1.06M rows, a few minutes, run once).

## Decisions already settled in discussion (2026-06-17)

- **Seed from PROD only, NOT the benchmark DB.** Benchmark has 5.3× more opening-eval
  coverage (5.64M vs 1.06M distinct hashes) and is tempting, but it's the *wrong currency*:
  (1) benchmark `game_positions` has **no `best_move` and no `pv` columns**, so it can't
  let the drain skip the Stockfish pass (that pass produces eval+best_move+pv together —
  eval-only cache entries save zero engine work); (2) benchmark opening evals are
  **lichess %eval**, but the dedup deliberately gates on `has_engine_full_evals`
  (`full_evals_completed_at IS NOT NULL AND lichess_evals_at IS NULL`, D-117-07) to
  transplant only our 1M-node Stockfish evals. Seeding lichess evals would create a
  two-tier-provenance cache that undermines flaw-threshold/explorer consistency.
- **No flaw filtering at population time.** "Flaw" is a property of a move-in-a-game, not
  a position; the same opening hash is a blunder in one game and the top move in another.
  Caching its eval/best_move is correct for every game. The pv concern is entirely
  read-side (see [[SEED-056-opening-flaw-pv-gap-engine-games]]) and pre-exists this work.

## When to Surface

This is **transient drain-window cost** — once the backlog is caught up, lookup volume
drops to incremental per-import levels. Build it when (a) drain throughput is a current
priority (big re-drain / import wave), or (b) the `DISTINCT ON` query is back at the top
of a db-report's total-time leaderboard. Re-check the db-report *after the current drain
finishes* (pg_stat_statements was reset 2026-06-17): if it falls off the leaderboard
under normal user traffic, this stays dormant.

## Scope Estimate

**Medium.** Migration (table + one-time backfill) + write-path upsert + read-path swap +
tests. No invalidation logic. The risk surface is small because it's a drop-in for an
existing, well-guarded lookup. The backfill is a one-time ~minutes-long INSERT.

## Breadcrumbs

- `app/services/eval_drain.py:270` — `_fetch_dedup_evals` (the self-join to replace).
- `app/services/eval_drain.py:1640-1665` — dedup partition + engine-target selection
  (read-side guards to preserve verbatim).
- `app/models/game_position.py` — `DEDUP_MAX_PLY` (=20), `ix_gp_full_hash_opening`
  partial index, post-move storage convention notes.
- `app/models/game.py:223` — `has_engine_full_evals` hybrid (the provenance gate).
- `reports/db-stats/db-report-prod-2026-06-17.md` §2 — the original measurement.
- [[SEED-056-opening-flaw-pv-gap-engine-games]] — read-side pv gap, surfaces together.
- [[SEED-043-lichess-best-move-pv-backfill]] — related provenance/coverage decision.

## Notes

Diagnosed live in prod 2026-06-17 while reviewing the db-report. EXPLAIN ANALYZE numbers
and sizing taken against prod during the active 4-worker import + tier-3 drain (so the
8.4s avg is partly inflated by the 70.95% cache-hit ratio of that window — another reason
to re-measure post-drain before committing). The LATERAL rewrite was tested and rejected
as insufficient (2× only).
