---
name: db-report
description: Generate a database storage and performance report for FlawChess. Use this skill when the user asks about database size, storage usage, table sizes, index sizes, game counts, position counts, slow queries, query performance, cache hit ratio, sequential scans, index usage, dead tuples, or wants a DB health/status overview. Trigger on phrases like "db report", "database report", "how big is the database", "storage usage", "index sizes", "table sizes", "slow queries", "query performance", "db performance", "db health", or any question about DB metrics. Supports both production and local dev databases.
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

The report has three sections. By default, run **all** sections. If the user only asks for storage/sizes, run Section 1 only. If the user only asks for performance/slow queries, run Section 2 only.

---

## Section 0: Users Overview

Run all three queries in parallel (separate MCP tool calls in a single message) since they are independent.

### Query 0a — User summary
```sql
SELECT count(*) AS total_users, count(*) FILTER (WHERE NOT is_guest) AS registered_users, count(*) FILTER (WHERE is_guest) AS guest_users FROM users
```

### Query 0b — 10 most recent users with game and position counts
```sql
SELECT u.id, u.email, u.chess_com_username, u.lichess_username, u.is_guest, u.created_at, u.last_login, COALESCE(g.game_count, 0) AS games, COALESCE(gp.position_count, 0) AS positions FROM users u LEFT JOIN (SELECT user_id, count(*) AS game_count FROM games GROUP BY user_id) g ON g.user_id = u.id LEFT JOIN (SELECT user_id, count(*) AS position_count FROM game_positions GROUP BY user_id) gp ON gp.user_id = u.id ORDER BY u.created_at DESC LIMIT 10
```

### Query 0c — Platform breakdown across all users
```sql
SELECT platform, count(DISTINCT user_id) AS users, count(*) AS games FROM games GROUP BY platform ORDER BY games DESC
```

### Users output format

Present results as:

1. **User summary** — single-row table: total users, registered users, guest users
2. **10 most recent users** — table with columns: email (truncated/masked if needed), chess.com username, lichess username, guest?, registered, last login, games, positions. Format dates as YYYY-MM-DD. For users with 0 games, this highlights signups that never imported.
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
