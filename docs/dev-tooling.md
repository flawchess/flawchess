# Dev Tooling Reference

Scripts, database access, and the dev clock. The root `CLAUDE.md` keeps only the guardrails; details live here.

## Scripts

`bin/` holds shell helpers, `scripts/` holds Python maintenance/backfill/benchmark tools. Most are self-describing — read the docstring or run with `--help`. The ones with non-obvious behavior:

- **`bin/deploy.sh`** — the only sanctioned deploy path (CI → `production`). Never deploy by direct SSH.
- **`bin/reset_db.sh`** — destroys and recreates the dev DB. **DO NOT RUN WITHOUT EXPLICIT PERMISSION FROM THE USER.**
- **`bin/prod_db_tunnel.sh`** — SSH tunnel forwarding prod PostgreSQL to `localhost:15432` (needed for the prod-db MCP and `--db prod` scripts). Stop with `bin/prod_db_tunnel.sh stop`.
- **`bin/benchmark_db.sh`** — lifecycle (`start`/`stop`/`reset`) for the benchmark Postgres on port 5433.
- **`bin/install_pre_push_hook.sh`** — optional one-time hook running `ruff format --check`, `ruff check`, and `ty check` on push (pytest excluded for speed). Bypass with `git push --no-verify`.
- **`bin/check_cloudflare_ips.sh`**: diffs the inline CIDR range list between the `# BEGIN cloudflare-ranges` / `# END cloudflare-ranges` markers in `deploy/Caddyfile` against the live [cloudflare.com/ips-v4](https://www.cloudflare.com/ips-v4) and [ips-v6](https://www.cloudflare.com/ips-v6) endpoints. Run with `bash bin/check_cloudflare_ips.sh` (optional first argument overrides the Caddyfile path). Exits 0 when the ranges match, non-zero and names the differing CIDRs on drift, and non-zero if either fetch fails or the markers are missing. Deliberately not wired into CI (D-11) since a network call to cloudflare.com on every run is not worth it for a list that changes on the order of months.
- **`scripts/gen_*.py`** (e.g. `gen_endgame_zones_ts.py`, `gen_flaw_thresholds_ts.py`) — regenerate committed `frontend/src/generated/*` files from Python sources. CI fails on drift, so re-run after editing the source registry.
- **`scripts/backfill_*.py`** — most take `--db dev|benchmark|prod` and `--user-id`; `--db prod` requires `prod_db_tunnel.sh`.
- **`scripts/reset_train_state.py`** — wipes one user's Train/drill state (items, sessions, solves, streak snapshot) so a schedule test starts clean. Refuses `--db prod`. Pairs with the dev clock below.
- **`scripts/check_function_size.py`** — AST nesting-depth gate (depth <= 4, `app/` only, CI + pre-merge gate). No ruff stable rule covers nesting depth; ruff's preview-only `PLR1702` was rejected because `--preview` expands the effective rule set from ~5 rules to 914 (214-RESEARCH.md). `uv run python scripts/check_function_size.py app/ --fail-over-depth 4`; `--json` also reports raw/logic LOC per function for human review — LOC is not gated (quick 260926-evd, D-03).
- **Ruff rule set** — explicit pin `E4`/`E7`/`E9`/`F` plus `TID251`/`B`/`ASYNC`/`DTZ` (see the `pyproject.toml` comment above `select` for why the set is pinned). `B`/`ASYNC`/`DTZ` target `app/` (bugbear also stays on for `tests/`); `scripts/`, `analysis/` and `alembic/` are scoped out of all three. Banned APIs (`TID251`): `requests`, `berserk`. Pre-existing findings are baselined in `[tool.ruff.lint.per-file-ignores]` under a dated comment; an entry is deleted once its file is fixed, never added for new code.
- **Cognitive complexity, report-only on both stacks** — `uv run complexipy app/ --max-complexity-allowed 15 --failed --sort desc` (backend) and `npm run lint:cognitive` (frontend, `sonarjs/cognitive-complexity` at 15, its own config `frontend/eslint.config.sonarjs.mjs`); neither runs in CI.
- **Frontend complexity gate** — eslint `max-depth` (4) at `error` in `frontend/eslint.config.js`'s `**/*.{ts,tsx}` block is the only hard complexity rule, gated by `npm run lint`. Scoped to TypeScript only because `eslint .` also walks the vendored engine bundles under `frontend/public/` (Stockfish/Maia/ONNX runtime). One test file (`src/lib/__tests__/reminderSlotState.test.ts`) is baselined at 10; a new breach elsewhere is fixed, not baselined.

## Database access (MCP)

Three PostgreSQL MCP servers are configured for direct queries, all exposed as query-only tools (`mcp__flawchess-*-db__query`):

- **`flawchess-db`** — local dev database (Docker on `localhost:5432`). Requires the dev DB running: `docker compose -f docker-compose.dev.yml -p flawchess-dev up -d`. Uses the app user (read-write at SQL level, but the wrapper is query-only).
- **`flawchess-prod-db`** — production database via a dedicated read-only role. Requires the SSH tunnel: `bin/prod_db_tunnel.sh`.
- **`flawchess-benchmark-db`** — benchmark database (Docker on `localhost:5433`). Requires `bin/benchmark_db.sh start`. Read-only role; password is local-only, not committed.

## Dev clock (testing Train's schedule without waiting days)

Train's behavior is calendar-shaped (weekday mask, session expiry, due-date ladder, Mon-start streak weeks). `app/core/dev_clock.py` provides a `dev_now_utc` FastAPI dependency that shifts "now" by the `X-Dev-Clock-Offset-Minutes` request header, **honored only when `ENVIRONMENT == "development"`** (inert in every other environment).

The Train page renders a time-travel strip in dev builds (`frontend/src/components/train/TrainDevClock.tsx`, gated on `import.meta.env.DEV`) that persists the offset in localStorage; `frontend/src/api/client.ts`'s request interceptor attaches the header.

Rows written while shifted keep the shifted dates, so after travelling forward run `scripts/reset_train_state.py --user-id N` for a clean slate. **Any new time-dependent endpoint should take `now_utc` from this dependency** rather than calling `datetime.now()` inline.
