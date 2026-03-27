---
name: db-report
description: Generate a database storage report for FlawChess. Use this skill when the user asks about database size, storage usage, table sizes, index sizes, game counts, position counts, or wants a DB health/status overview. Trigger on phrases like "db report", "database report", "how big is the database", "storage usage", "index sizes", "table sizes", or any question about DB metrics. Supports both production and local dev databases.
---

# DB Report

Generate a database storage report by querying the FlawChess PostgreSQL database.

## Target selection

- If the user says "local", "dev", or "local db" → use the **local** connection
- If the user says "prod", "production", or "server" → use the **production** connection
- If ambiguous → ask which environment they mean

## Connections

### Local dev database
```
docker compose -f docker-compose.dev.yml -p flawchess-dev exec -T db psql -U flawchess -d flawchess -c "<SQL>"
```

### Production database
```
ssh flawchess "cd /opt/flawchess && docker compose exec -T db psql -U flawchess -d flawchess -c \"<SQL>\""
```

## Queries

Run all three queries in parallel (separate Bash tool calls in a single message) since they are independent.

### Query 1 — Overview
```sql
SELECT pg_size_pretty(pg_database_size('flawchess')) AS db_size;
SELECT count(*) AS total_games FROM games;
SELECT count(*) AS total_positions FROM game_positions;
```

### Query 2 — Per-table sizes
```sql
SELECT relname AS table, pg_size_pretty(pg_total_relation_size(c.oid) - pg_relation_size(c.oid)) AS index_size, pg_size_pretty(pg_relation_size(c.oid)) AS table_size, pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relkind = 'r' ORDER BY pg_total_relation_size(c.oid) DESC;
```

### Query 3 — Per-index sizes
```sql
SELECT i.relname AS index_name, t.relname AS table_name, pg_size_pretty(pg_relation_size(i.oid)) AS index_size FROM pg_class i JOIN pg_index ix ON ix.indexrelid = i.oid JOIN pg_class t ON t.oid = ix.indrelid JOIN pg_namespace n ON n.oid = t.relnamespace WHERE n.nspname = 'public' ORDER BY pg_relation_size(i.oid) DESC;
```

## Output format

Present results as three markdown tables:

1. **Overview** — database size, total games, total positions, and average positions per game
2. **Per-table breakdown** — table name, data size, index size, total size (sorted by total descending)
3. **Per-index breakdown** — index name, table, size (sorted by size descending)

End with a brief summary highlighting notable findings (e.g., index-to-data ratio, largest consumers).
