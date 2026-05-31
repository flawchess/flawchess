-- Creates the dev database on first container init.
--
-- The test suite no longer uses a static `flawchess_test` database: each pytest
-- run (and each pytest-xdist worker) clones its own throwaway
-- `flawchess_test_<pid>` / `flawchess_test_gw*` database from a migrated
-- `flawchess_test_template`, all created at runtime by tests/conftest.py against
-- the `postgres` maintenance DB using the `postgres` superuser (see
-- TEST_DATABASE_URL). Nothing here needs to create or grant on it.
CREATE DATABASE flawchess;

-- Create app user matching .env defaults
CREATE USER flawchess WITH PASSWORD 'flawchess';
GRANT ALL PRIVILEGES ON DATABASE flawchess TO flawchess;

-- Allow flawchess user to create objects in public schema
\c flawchess
GRANT ALL ON SCHEMA public TO flawchess;
