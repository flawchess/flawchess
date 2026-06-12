---
name: db-report
description: Generate a database storage and performance report for FlawChess. Use this skill when the user asks about database size, storage usage, table sizes, index sizes, game counts, position counts, slow queries, query performance, cache hit ratio, sequential scans, index usage, dead tuples, data integrity / sanity checks (e.g. do the games blunder/mistake count columns match game_flaws), or wants a DB health/status overview. Trigger on phrases like "db report", "database report", "how big is the database", "storage usage", "index sizes", "table sizes", "slow queries", "query performance", "db performance", "db health", "data integrity", "sanity check", or any question about DB metrics. Supports both production and local dev databases. Writes a timestamped markdown report to reports/db-stats/db-report-{env}-YYYY-MM-DD.md.
---

# DB Report

Generate a database storage and performance report by querying the FlawChess PostgreSQL database.

## Target selection

- If the user says "local", "dev", or "local db" → use the **local** connection
- If the user says "prod", "production", or "server" → use the **production** connection
- If ambiguous → ask which environment they mean

## Connections

Use the PostgreSQL MCP servers for direct database queries (no SSH or psql needed):

- **Local dev**: `mcp__flawchess-db__query` — requires dev DB running: `docker compose -f docker-compose.dev.yml -p flawchess-dev up -d`
- **Production**: `mcp__flawchess-prod-db__query` — requires SSH tunnel: `bin/prod_db_tunnel.sh`

Both accept a single `sql` parameter. Run one SQL statement per call (no semicolon-separated multi-statements).

## Report scope

The report has four sections (Users, Storage, Performance, Sanity Checks). By default, run **all** sections and write the output to `reports/db-stats/db-report-{env}-YYYY-MM-DD.md` (UTC date, where `{env}` is `prod` or `local`). If the user only asks for storage/sizes, run Section 1 only. If the user only asks for performance/slow queries, run Section 2 only. If the user only asks for data integrity / sanity checks, run Section 3 only. When running a subset, append to today's report rather than overwriting prior sections.

When writing the report, always include at the top:
- Target DB (prod/local) and snapshot timestamp (ISO UTC)
- Which sections were run

---

## Section 0: Users Overview

Run all three queries in parallel (separate MCP tool calls in a single message) since they are independent.

### Query 0a — User summary
```sql
SELECT count(*) AS total_users, count(*) FILTER (WHERE NOT is_guest) AS registered_users, count(*) FILTER (WHERE is_guest) AS guest_users FROM users
```

### Query 0b — 10 most recent users with game and position counts

PII (email, chess.com username, lichess username) is intentionally excluded — boolean flags below preserve the signal (does the user have a linked platform account?) without leaking identifiers into the report file.

```sql
SELECT u.id, (u.chess_com_username IS NOT NULL) AS has_chess_com, (u.lichess_username IS NOT NULL) AS has_lichess, u.is_guest, u.created_at, u.last_login, COALESCE(g.game_count, 0) AS games, COALESCE(gp.position_count, 0) AS positions FROM users u LEFT JOIN (SELECT user_id, count(*) AS game_count FROM games GROUP BY user_id) g ON g.user_id = u.id LEFT JOIN (SELECT user_id, count(*) AS position_count FROM game_positions GROUP BY user_id) gp ON gp.user_id = u.id ORDER BY u.created_at DESC LIMIT 10
```

### Query 0c — Platform breakdown across all users
```sql
SELECT platform, count(DISTINCT user_id) AS users, count(*) AS games FROM games GROUP BY platform ORDER BY games DESC
```

### Users output format

Present results as:

1. **User summary** — single-row table: total users, registered users, guest users
2. **10 most recent users** — table with columns: user id, has_chess_com, has_lichess, guest?, registered, last login, games, positions. Format dates as YYYY-MM-DD. Do NOT include email, chess.com username, or lichess username — these are PII and must not appear in the report file. The boolean flags are sufficient to spot signups that never linked a platform account or never imported games.
3. **Platform breakdown** — table: platform, users, games

End with a brief note on user activity (e.g., how many recent signups have actually imported games, guest vs registered ratio).

---

## Section 1: Storage Report

Run all queries in parallel (separate MCP tool calls in a single message) since they are independent.

### Query 1a — Database size
```sql
SELECT pg_size_pretty(pg_database_size('flawchess')) AS db_size
```

### Query 1b — Game count
```sql
SELECT count(*) AS total_games FROM games
```

### Query 1c — Position count
```sql
SELECT count(*) AS total_positions FROM game_positions
```

### Query 2 — Per-table sizes
```sql
SELECT relname AS table, pg_size_pretty(pg_total_relation_size(c.oid) - pg_relation_size(c.oid)) AS index_size, pg_size_pretty(pg_relation_size(c.oid)) AS table_size, pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relkind = 'r' ORDER BY pg_total_relation_size(c.oid) DESC;
```

### Query 3 — Per-index sizes
```sql
SELECT i.relname AS index_name, t.relname AS table_name, pg_size_pretty(pg_relation_size(i.oid)) AS index_size FROM pg_class i JOIN pg_index ix ON ix.indexrelid = i.oid JOIN pg_class t ON t.oid = ix.indrelid JOIN pg_namespace n ON n.oid = t.relnamespace WHERE n.nspname = 'public' ORDER BY pg_relation_size(i.oid) DESC;
```

### Storage output format

Present results as three markdown tables:

1. **Overview** — database size, total games, total positions, and average positions per game
2. **Per-table breakdown** — table name, data size, index size, total size (sorted by total descending)
3. **Per-index breakdown** — index name, table, size (sorted by size descending)

End with a brief summary highlighting notable findings (e.g., index-to-data ratio, largest consumers).

---

## Section 2: Performance Analysis

Run all five queries in parallel (separate MCP tool calls in a single message) since they are independent.

### Query 4 — Top 20 queries by average execution time (requires pg_stat_statements)
```sql
SELECT round(mean_exec_time::numeric, 2) AS avg_ms, round(max_exec_time::numeric, 2) AS max_ms, calls, round(total_exec_time::numeric, 0) AS total_ms, rows, left(query, 300) AS query FROM pg_stat_statements WHERE dbid = (SELECT oid FROM pg_database WHERE datname = 'flawchess') ORDER BY mean_exec_time DESC LIMIT 20;
```

### Query 5 — Top 20 queries by total execution time
```sql
SELECT round(total_exec_time::numeric, 0) AS total_ms, calls, round(mean_exec_time::numeric, 2) AS avg_ms, rows, left(query, 300) AS query FROM pg_stat_statements WHERE dbid = (SELECT oid FROM pg_database WHERE datname = 'flawchess') ORDER BY total_exec_time DESC LIMIT 20;
```

### Query 6 — Table scan statistics (seq scans vs index scans, dead tuples, autovacuum)
```sql
SELECT schemaname, relname, seq_scan, seq_tup_read, idx_scan, idx_tup_fetch, n_live_tup, n_dead_tup, last_autovacuum, last_autoanalyze FROM pg_stat_user_tables ORDER BY seq_tup_read DESC;
```

### Query 7 — Index usage statistics
```sql
SELECT relname, indexrelname, idx_scan, idx_tup_read, idx_tup_fetch FROM pg_stat_user_indexes ORDER BY idx_scan DESC;
```

### Query 8 — Buffer cache hit ratio
```sql
SELECT round(100.0 * blks_hit / nullif(blks_hit + blks_read, 0), 2) AS cache_hit_pct FROM pg_stat_database WHERE datname = 'flawchess';
```

If Query 4 or 5 fails because `pg_stat_statements` is not installed, note this in the output and skip those queries. The remaining queries (6-8) use built-in pg_stat views and will always work.

### Performance output format

Present results as:

1. **Buffer cache hit ratio** — single value with assessment (>99% = excellent, 95-99% = good, <95% = investigate)
2. **Slowest queries by avg time** — markdown table: avg_ms, max_ms, calls, total_ms, truncated query. Focus on the top 5-10 that actually matter (skip queries under 10ms avg unless they have very high call counts).
3. **Highest total time queries** — markdown table: total_ms, calls, avg_ms, truncated query. Highlight queries that dominate server time (high total_ms) even if per-call time is low — these are optimization targets.
4. **Sequential scan analysis** — markdown table: table, seq_scans, idx_scans, verdict. Flag tables with high seq_scan counts relative to idx_scan — but note that tiny tables (under ~100 rows) legitimately use seq scans because PostgreSQL's optimizer correctly determines they're faster than index lookups.
5. **Index usage** — identify unused indexes (0 scans) and note whether they can be dropped. Indexes required for FK integrity, PKs, or OAuth/auth flows should be marked "keep" even if unused. Only recommend dropping indexes that are both large and genuinely unused.
6. **Dead tuples / autovacuum** — flag tables with dead tuple ratios above 20% or where autovacuum hasn't run recently.

### EXPLAIN ANALYZE for slow queries

If any query from Query 4/5 averages over 500ms, run `EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)` on a representative version of that query to check the actual execution plan. The pg_stat_statements averages may be skewed by historical runs before index changes — EXPLAIN ANALYZE shows current reality. Note: you'll need to substitute realistic parameter values (e.g., `user_id = 1`).

### Performance recommendations

End with actionable recommendations, categorized as:
- **No action needed** — things that look fine, with brief explanation why
- **Monitor** — things to watch but not urgent (e.g., "reset stats and re-check in a week")
- **Recommended** — changes that would improve performance
- **Consider** — optional optimizations with trade-offs noted

If pg_stat_statements has never been reset (check `stats_reset` from `pg_stat_database`), mention that cumulative stats may not reflect current performance and offer to reset them.

---

## Section 3: Sanity Checks

Data-integrity checks. Run both unless the user asks for one.

- **Check A — Flaw counts: `games` oracle columns vs `game_flaws`.** Are the per-color move-quality count columns on `games` (`white/black_mistakes`, `white/black_blunders`) consistent with the derived `game_flaws` table?
- **Check B — Eval coverage vs oracle-column presence.** Are there games with ≥90% per-ply eval coverage (`game_positions`) whose `games` oracle columns are NULL? This guards the **Flaws Timeline** feature, which reads the precomputed `games` oracle columns directly (`fetch_flaw_trend_rows`, no `game_positions` join) and gates on "oracle present". A game that is "analyzed" by eval coverage but has NULL oracle columns is silently dropped from the Timeline.

---

### Check A — Flaw counts: `games` oracle columns vs `game_flaws`

#### Background (read before interpreting results)

- `games.{white,black}_{mistakes,blunders}` come **directly from the lichess analysis API** and are per-color counts for the whole game. They are **NULL for chess.com** (chess.com supplies game-level *accuracy*, not M/B counts) and NULL for lichess games lichess never analyzed.
- `game_flaws` is an **independently derived** materialization (one row per mistake/blunder, both players, severity 1=mistake / 2=blunder), classified from move evals using lila-mirrored ES thresholds (see `app/services/flaws_service.py`). It is only populated for **lichess games that lichess analyzed**; chess.com games have **zero** `game_flaws` rows even though their evals are completed.
- Because the two are independent classifiers (lichess win% vs our Option-B ES thresholds), small per-game disagreement is **expected, not a bug** — aggregate totals should agree within ~1%. The mate-ladder path is known to drift (see `MATE_LADDER_*` in `flaws_service.py`).

Two things we want to know:
1. **Do the counts match?** For lichess games with counts present, does `white_mistakes + black_mistakes` equal the `game_flaws` mistake count (severity 1), and likewise for blunders (severity 2)?
2. **Are the count columns NULL when they should have a value?** I.e. a lichess game that has `game_flaws` rows (so it *was* analyzed) but whose count columns are all NULL — that is a genuine data gap.

Both checks are **scoped to `platform = 'lichess'`**. chess.com is excluded by design (NULL counts + no flaw rows is the correct state there).

### Query 9 — Flaw count integrity summary
```sql
WITH gf AS (
  SELECT game_id,
         count(*) FILTER (WHERE severity = 1) AS gf_mistakes,
         count(*) FILTER (WHERE severity = 2) AS gf_blunders
  FROM game_flaws GROUP BY game_id
)
SELECT
  count(*) FILTER (WHERE gf.game_id IS NOT NULL) AS lichess_games_with_flaws,
  count(*) FILTER (WHERE gf.game_id IS NOT NULL
                     AND g.white_mistakes IS NULL AND g.black_mistakes IS NULL
                     AND g.white_blunders IS NULL AND g.black_blunders IS NULL) AS flaws_but_all_counts_null,
  count(*) FILTER (WHERE (g.white_mistakes IS NOT NULL OR g.white_blunders IS NOT NULL)
                     AND coalesce(g.white_mistakes,0)+coalesce(g.black_mistakes,0) = coalesce(gf.gf_mistakes,0)
                     AND coalesce(g.white_blunders,0)+coalesce(g.black_blunders,0) = coalesce(gf.gf_blunders,0)) AS exact_match,
  count(*) FILTER (WHERE (g.white_mistakes IS NOT NULL OR g.white_blunders IS NOT NULL)
                     AND coalesce(g.white_mistakes,0)+coalesce(g.black_mistakes,0) <> coalesce(gf.gf_mistakes,0)) AS mistake_mismatch,
  count(*) FILTER (WHERE (g.white_mistakes IS NOT NULL OR g.white_blunders IS NOT NULL)
                     AND coalesce(g.white_blunders,0)+coalesce(g.black_blunders,0) <> coalesce(gf.gf_blunders,0)) AS blunder_mismatch
FROM games g
LEFT JOIN gf ON gf.game_id = g.id
WHERE g.platform = 'lichess';
```

### Query 10 — Mismatch direction & aggregate totals (diagnostic; run only if Query 9 shows mismatches)
```sql
WITH gf AS (
  SELECT game_id,
         count(*) FILTER (WHERE severity = 1) AS gf_mistakes,
         count(*) FILTER (WHERE severity = 2) AS gf_blunders
  FROM game_flaws GROUP BY game_id
)
SELECT
  count(*) FILTER (WHERE coalesce(g.white_mistakes,0)+coalesce(g.black_mistakes,0) > coalesce(gf.gf_mistakes,0)) AS mistakes_gf_under,
  count(*) FILTER (WHERE coalesce(g.white_mistakes,0)+coalesce(g.black_mistakes,0) < coalesce(gf.gf_mistakes,0)) AS mistakes_gf_over,
  count(*) FILTER (WHERE coalesce(g.white_blunders,0)+coalesce(g.black_blunders,0) > coalesce(gf.gf_blunders,0)) AS blunders_gf_under,
  count(*) FILTER (WHERE coalesce(g.white_blunders,0)+coalesce(g.black_blunders,0) < coalesce(gf.gf_blunders,0)) AS blunders_gf_over,
  sum(coalesce(g.white_mistakes,0)+coalesce(g.black_mistakes,0)) AS total_lichess_mistakes,
  sum(coalesce(gf.gf_mistakes,0)) AS total_gf_mistakes,
  sum(coalesce(g.white_blunders,0)+coalesce(g.black_blunders,0)) AS total_lichess_blunders,
  sum(coalesce(gf.gf_blunders,0)) AS total_gf_blunders
FROM games g
LEFT JOIN gf ON gf.game_id = g.id
WHERE g.platform = 'lichess'
  AND (g.white_mistakes IS NOT NULL OR g.white_blunders IS NOT NULL);
```

#### Check A output format

1. **NULL-count gap** — report `flaws_but_all_counts_null`. This is the headline integrity number: it **should be 0**. Any non-zero value means lichess games have derived flaws but the source count columns were never populated — a real bug to investigate.
2. **Count match rate** — `exact_match / lichess_games_with_flaws` as a percentage, plus the raw `mistake_mismatch` / `blunder_mismatch` counts. A match rate above ~97% is healthy given the two classifiers are independent.
3. **Mismatch diagnosis** (only if mismatches exist) — from Query 10, report whether `game_flaws` over- or under-counts relative to lichess, and the aggregate totals (these should agree within ~1%). Frame per-game drift as expected classifier disagreement unless the **aggregate** totals diverge by more than a few percent or the NULL-count gap is non-zero.

Verdict line (Check A): **PASS** if `flaws_but_all_counts_null = 0` and aggregate totals agree within ~1%; **INVESTIGATE** otherwise.

> Reference (prod snapshot 2026-06-12): `flaws_but_all_counts_null = 0`, match rate 98.4% (38,355 / 38,964), aggregate totals within ~1% (mistakes 112,838 vs 111,939; blunders 177,472 vs 177,206). Verdict: PASS.

---

### Check B — Eval coverage vs oracle-column presence (Flaws Timeline gate)

#### Background (read before interpreting results)

- The **Flaws Timeline** chart (`fetch_flaw_trend_rows` → `_compute_flaw_trend`) is built **only** from the precomputed `games` oracle columns (`white/black_blunders/mistakes/inaccuracies`, picked by `user_color`) plus `ply_count`/`played_at`. It does **not** join `game_positions`. Its "analyzed" gate is **oracle-present** (the user's-color `*_blunders IS NOT NULL`).
- A different, older notion of "analyzed" is **eval coverage**: ≥`EVAL_COVERAGE_MIN` (0.90, `flaws_service.py`) of a game's plies carry an `eval_cp`/`eval_mate` in `game_positions`. The two can diverge because they come from different sources: oracle columns are **lichess judgment annotations** (lichess-only); per-ply evals are **lichess %eval OR Stockfish backfill**.
- **Gotcha:** `games.evals_completed_at` being non-NULL does **not** imply ≥90% full-ply coverage — it tracks **endgame-span entry-ply** evaluation only. chess.com games typically have sparse evals (entry plies) and so usually do **not** clear the 0.90 gate; the ≥90%-coverage set is effectively the fully-analyzed lichess games, which already have oracle columns. So this check is expected to find **few or zero** rows. Any chess.com games appearing in `ge90_but_oracle_null` would be the interesting case — fully eval-covered yet invisible to the Timeline.

This check answers: **are there games with ≥90% eval coverage whose oracle columns are NULL** (i.e. analyzed-by-coverage but dropped from the Timeline)?

#### Query 11 — Eval-coverage ≥90% vs oracle-null, by platform
> Heavier query: aggregates all of `game_positions` (tens of millions of rows). Expect a few seconds. Run it last.
```sql
WITH cov AS (
  SELECT game_id, user_id,
         sum(CASE WHEN eval_cp IS NOT NULL OR eval_mate IS NOT NULL THEN 1 ELSE 0 END)::float
           / count(*) AS coverage
  FROM game_positions
  GROUP BY game_id, user_id
)
SELECT
  g.platform,
  count(*) AS games_ge90_coverage,
  count(*) FILTER (
    WHERE (g.user_color = 'white'
             AND (g.white_blunders IS NULL OR g.white_mistakes IS NULL OR g.white_inaccuracies IS NULL))
       OR (g.user_color = 'black'
             AND (g.black_blunders IS NULL OR g.black_mistakes IS NULL OR g.black_inaccuracies IS NULL))
  ) AS ge90_but_oracle_null,
  count(*) FILTER (
    WHERE (g.user_color = 'white' AND g.white_blunders IS NOT NULL)
       OR (g.user_color = 'black' AND g.black_blunders IS NOT NULL)
  ) AS ge90_oracle_present
FROM cov
JOIN games g ON g.id = cov.game_id AND g.user_id = cov.user_id
WHERE cov.coverage >= 0.90
GROUP BY g.platform
ORDER BY games_ge90_coverage DESC;
```

#### Check B output format

Report `ge90_but_oracle_null` per platform (the headline number for this check), alongside `games_ge90_coverage`.

- **0 rows / `ge90_but_oracle_null = 0`** — PASS. The Timeline's oracle-present gate loses no eval-covered games.
- **Non-zero, lichess only** — usually benign edge cases (lichess game with %eval present but judgment annotations missing). Note the count; investigate only if large.
- **Non-zero on chess.com** — INVESTIGATE. It means full-game Stockfish coverage landed (chess.com games clearing 0.90) while oracle columns stayed NULL, so those games are analyzed yet silently excluded from the Flaws Timeline. This is the signal to revisit the Timeline's gate (or to backfill chess.com oracle columns).

Verdict line (Check B): **PASS** if `ge90_but_oracle_null = 0` (or only a small lichess remainder); **INVESTIGATE** if chess.com appears or the lichess count is material.

---

## Report file layout

Write to `reports/db-stats/db-report-{env}-YYYY-MM-DD.md` using today's UTC date, where `{env}` is `prod` or `local`. Separate files per environment so a local snapshot never clobbers a prod snapshot taken the same day. Layout:

```markdown
# FlawChess DB Report — <DATE>

- **DB**: prod / local
- **Snapshot taken**: <ISO UTC timestamp>
- **Sections run**: users / storage / performance / sanity

## 0. Users Overview
...

## 1. Storage Report
...

## 2. Performance Analysis
...

## 3. Sanity Checks
...

## Summary
<brief top-line findings: DB size, largest tables, cache hit ratio, notable slow queries, anything that warrants action>
```

The `Summary` section at the bottom is the main deliverable — a short paragraph or bulleted list of the top findings and any recommended actions. Don't just restate the tables; call out what's surprising or actionable.

After writing the file, output a one-line summary in chat with the absolute path to the report (e.g. `Wrote reports/db-stats/db-report-prod-2026-04-16.md`) so the user knows where to find it.

## Re-running & append mode

If `reports/db-stats/db-report-{env}-YYYY-MM-DD.md` already exists for today, check which sections are present. If the user asked for a subset (e.g. "just rerun section 2" or "refresh the perf numbers"), replace only that section — do not clobber the others. Always preserve the header and rebuild the bottom Summary from whichever sections are present in the file.

If the user explicitly asks for a fresh snapshot, overwrite the file. Never mutate older-dated reports.
