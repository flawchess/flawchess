-- Creates the benchmark database on first container init
-- Phase 69 INFRA-01: isolated benchmark instance for v1.12 population baselines
CREATE DATABASE flawchess_benchmark;

-- App user matching .env defaults (used by Alembic migrations and ingestion scripts)
CREATE USER flawchess_benchmark WITH PASSWORD 'flawchess_benchmark';
GRANT ALL PRIVILEGES ON DATABASE flawchess_benchmark TO flawchess_benchmark;

\c flawchess_benchmark
GRANT ALL ON SCHEMA public TO flawchess_benchmark;

-- Read-only user for the flawchess-benchmark-db MCP server (Phase 69 INFRA-03).
-- Replace <PASSWORD> with: openssl rand -hex 16
-- Do NOT commit the real password — keep <PASSWORD> as the placeholder in git.
-- Mirrors the prod RO-user pattern documented in CLAUDE.md §Database Access.
CREATE USER flawchess_benchmark_ro WITH PASSWORD '<PASSWORD>';
GRANT CONNECT ON DATABASE flawchess_benchmark TO flawchess_benchmark_ro;
GRANT USAGE ON SCHEMA public TO flawchess_benchmark_ro;
-- Default privileges must be scoped to flawchess_benchmark, since Alembic creates
-- tables as that role. Without FOR ROLE, the grant only applies to tables created
-- by the current session role (postgres) and new app-created tables get no SELECT.
ALTER DEFAULT PRIVILEGES FOR ROLE flawchess_benchmark IN SCHEMA public GRANT SELECT ON TABLES TO flawchess_benchmark_ro;
ALTER DEFAULT PRIVILEGES FOR ROLE flawchess_benchmark IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO flawchess_benchmark_ro;
-- No-op on first init (Alembic hasn't run yet); kept for clarity / defense-in-depth
-- if future bootstrap steps create tables before Alembic.
GRANT SELECT ON ALL TABLES IN SCHEMA public TO flawchess_benchmark_ro;
