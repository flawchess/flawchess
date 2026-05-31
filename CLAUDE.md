# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

FlawChess — a free, open-source chess analysis platform at flawchess.com. Tagline: "Engines are flawless, humans play FlawChess."

Users import their games from chess.com and/or lichess and analyze win/draw/loss (WDL) rates by board position using Zobrist hashes. This solves inconsistent opening categorization on existing platforms — instead of named openings, FlawChess matches positions exactly. The product covers openings, endgames, and time management.

### Key Features

- **Endgame Analytics** — WDL by endgame type (rook, minor piece, pawn, queen, mixed), conversion rates when up material, recovery rates when down, Endgame ELO timeline per (platform, time control), and LLM-narrated personalized feedback (`POST /api/insights/endgame`).
- **Opening Explorer & Insights** — interactive move explorer with WDL per candidate move; automatic 16-half-move scan (`POST /api/insights/openings`) surfaces opening strengths/weaknesses with deep-links into the explorer; usable for scouting opponents.
- **Time Management Stats** — average clock advantage/deficit at endgame entry, performance under matching time-pressure levels vs opponents, flag rates per time control.
- **Opening Comparison & Tracking** — bookmark positions, compare WDL trends over time, filter by time control.
- **System Opening Filter** — filter by user's pieces only (white_hash / black_hash) to analyze system openings (e.g. the London) across all opponent variations.
- **Cross-platform import** — combine chess.com and lichess games, filter by color, time control, opponent type, recency.
- **Mobile-first PWA** — installable on iOS/Android, drawer-based filter and bookmark sidebars, click-to-move on touch.

### User Flow

1. Sign up (free, no credit card), or use as guest
2. Import games from chess.com and/or lichess (background async import)
3. Explore openings on the interactive board with WDL statistics and AI-narrated insights
4. Analyze endgame performance by type with conversion/recovery metrics and AI-narrated feedback
5. Inspect time management stats: clock advantage at endgame entry, performance under time pressure, flag rates per time control
6. Optionally bookmark openings to track them over time, or scout an opponent's repertoire before a match

## Tech Stack

- **Backend**: FastAPI 0.115.x, Python 3.13, uv, Uvicorn
- **Frontend**: React 19 + TypeScript + Vite 5, react-chessboard 5.x, chess.js, TanStack Query, Tailwind CSS
- **Database**: PostgreSQL (asyncpg). No SQLite.
- **ORM**: SQLAlchemy 2.x async (`select()` API, not legacy 1.x) + Alembic + asyncpg
- **Auth**: FastAPI-Users
- **HTTP client**: httpx async only — never use `requests` or `berserk`
- **Chess logic**: python-chess 1.10.x
- **Validation**: Pydantic v2 throughout

## Commands

```bash
# Dev database (PostgreSQL 18 in Docker — required before running backend or tests)
docker compose -f docker-compose.dev.yml -p flawchess-dev up -d

# Backend
uv sync                          # Install dependencies from lockfile
uv run uvicorn app.main:app --reload  # Run dev server
uv run pytest                    # Run all tests
uv run pytest tests/test_foo.py::test_bar  # Run single test
uv run pytest -x               # Stop on first failure
uv run ruff check .             # Lint
uv run ruff format .            # Format
uv run ty check app/ tests/     # Type check (must pass with zero errors)
uv run alembic upgrade head     # Run migrations
uv run alembic revision --autogenerate -m "description"  # Create migration

# Frontend
npm install                     # Install dependencies
npm run dev                     # Dev server
npm run build                   # Production build
npm run lint                    # Lint
npm test                        # Run frontend tests
npm run test:watch              # Run tests in watch mode

# CI/CD (GitHub Actions)
gh run list                     # List recent workflow runs
gh run view <run-id> --log-failed  # View failed job logs
gh run watch <run-id>           # Watch a run in progress
gh pr checks <pr-number>        # Check PR status
```

### Pre-PR checklist (MANDATORY before `git push` / `gh pr create`)

Run these locally and resolve all output **before** pushing a branch that will become a PR. CI runs the same gates and will fail the build if any of them are dirty; catching them locally avoids a "fix CI" round-trip commit.

```bash
uv run ruff format app/ tests/         # apply formatting (not just --check)
uv run ruff check app/ tests/ --fix    # apply autofixable lint
uv run ty check app/ tests/            # type check, zero errors required
uv run pytest -x                       # backend tests, stop on first failure
( cd frontend && npm run lint && npm test -- --run )  # frontend lint + tests
```

If any step modifies files, commit the result with a `style(...)` or `chore(...)` prefix before pushing. Never push expecting CI to surface a formatter diff — the formatter is deterministic, so a CI "would reformat" failure is always avoidable locally. This is the single most common preventable CI failure on this project; treat the checklist as part of `git push`, not optional.

**Enforcement via git hook (recommended one-time setup):**

```bash
bin/install_pre_push_hook.sh    # installs .git/hooks/pre-push
```

The hook runs `ruff format --check`, `ruff check`, and `ty check` on every `git push`, blocking the push if any gate fails. Pytest is intentionally excluded from the hook to keep pushes fast — run it manually before opening a PR. Bypass for WIP pushes with `git push --no-verify`.

## Scripts

### `bin/`
- **`deploy.sh`** — Triggers GitHub Actions CI/deploy workflow for main and monitors progress
- **`run_local.sh`** — Starts local dev environment with backend and frontend servers
- **`reset_db.sh`** — Tears down and recreates the dev database from scratch, then runs migrations. DO NOT RUN WITHOUT EXPLICIT PERMISSION FROM THE USER.
- **`prod_db_tunnel.sh`** — Opens/closes SSH tunnel forwarding production PostgreSQL to localhost:15432
- **`benchmark_db.sh`** — Lifecycle for the isolated benchmark Postgres on port 5433 (`start` / `stop` / `reset`); runs Alembic migrations and re-grants read-only privileges on start
- **`download_1password.sh`** / **`upload_1password.sh`** — Sync `.env` and `.prod.env` to/from the FlawChess 1Password vault
- **`env_vars.sh`** — Shared variables sourced by the 1Password scripts (vault name, env file paths)

### `scripts/`
- **`seed_openings.py`** — Populates openings table from `app/data/openings.tsv` with precomputed Zobrist hashes
- **`reimport_games.py`** — Deletes and re-imports all games for a user or all users to backfill new data fields
- **`reclassify_positions.py`** — Reclassifies existing game positions with updated metadata by replaying stored PGNs
- **`select_benchmark_users.py`** — Streams a Lichess monthly PGN dump (`.pgn.zst`) and populates `benchmark_selected_users` with per-(rating bucket, TC bucket) username pools
- **`import_benchmark_users.py`** — Orchestrates Lichess game import for the selected benchmark users, checkpointing per (user, TC) into `benchmark_ingest_checkpoints`
- **`backfill_eval.py`** — Backfills Stockfish `eval_cp` / `eval_mate` into endgame span-entry rows; supports `--db dev|benchmark|prod` (prod requires `prod_db_tunnel.sh`)
- **`gen_endgame_zones_ts.py`** — Regenerates `frontend/src/generated/endgameZones.ts` from `app/services/endgame_zones.py`. CI fails on drift, so re-run after editing the Python registry

## Database Access (MCP)

Three PostgreSQL MCP servers are configured for direct database queries:

- **`flawchess-db`** — local dev database (Docker on `localhost:5432`). Requires dev DB running: `docker compose -f docker-compose.dev.yml -p flawchess-dev up -d`
- **`flawchess-prod-db`** — production database via read-only user. Requires SSH tunnel: `bin/prod_db_tunnel.sh` (forwards `localhost:15432` → prod DB on port 5432). Stop with `bin/prod_db_tunnel.sh stop`.
- **`flawchess-benchmark-db`** — benchmark database (Docker on `localhost:5433`). Requires benchmark DB running: `bin/benchmark_db.sh start` (or `docker compose -f docker-compose.benchmark.yml -p flawchess-benchmark up -d`). Read-only role `flawchess_benchmark_ro`; password is set locally and is not committed to git (the same `<PASSWORD>` placeholder pattern as the prod read-only user). Stop with `bin/benchmark_db.sh stop`.

All three are read-only query tools (`mcp__flawchess-db__query`, `mcp__flawchess-prod-db__query`, `mcp__flawchess-benchmark-db__query`). The first is read-write at the SQL level (it uses the app user) but the MCP wrapper is query-only by design; the latter two use dedicated read-only DB roles.

## Architecture

### Core Concept: Zobrist Hash Position Matching

The central architectural decision. Positions are matched via precomputed 64-bit integer Zobrist hashes, not FEN string comparison:
- `white_hash` — hash of white pieces only (enables "my pieces only" queries)
- `black_hash` — hash of black pieces only
- `full_hash` — hash of complete position

All three are computed at import time for every half-move and stored in `game_positions`. Position queries become indexed integer equality lookups.

### Backend Layout

```
routers/          # HTTP layer only — no business logic
services/         # Business logic (import, analysis)
repositories/     # DB access (no SQL in services)
```

### Router Convention

All routers use `APIRouter(prefix="/resource", tags=["resource"])` with relative paths in decorators. Never embed the resource prefix in individual route paths:
```python
# CORRECT
router = APIRouter(prefix="/openings", tags=["openings"])
@router.post("/positions", ...)

# WRONG — duplicates prefix in every route
router = APIRouter(tags=["openings"])
@router.post("/openings/positions", ...)
```

### Shared Query Filters

`app/repositories/query_utils.py` contains `apply_game_filters()` — the single implementation for time control, platform, rated, opponent type, recency, and color filtering. All repositories import from here. Never duplicate filter logic in individual repositories.

### Database Design Rules

- **Foreign key constraints are mandatory.** Every column referencing another table's primary key must use `ForeignKey()` with an explicit `ondelete` policy (typically `CASCADE` for user-owned data). Never use bare integer columns as implicit references — PostgreSQL must enforce referential integrity.
- **Unique constraints for natural keys.** Add `UniqueConstraint` for any business-level uniqueness (e.g., one import job per user+platform combo, one game per user+platform+platform_game_id).
- **Use appropriate column types.** E.g. don't use BIGINT where SmallInteger suffices. 

### Import Pipeline

Background async tasks (not blocking the API). chess.com fetches monthly archives sequentially with rate-limit delays. lichess streams NDJSON line-by-line. Both normalize to a unified schema before storage.

## Production Server

The production server is accessible via `ssh flawchess` (configured in user's SSH config). The deploy user is `deploy`, app lives at `/opt/flawchess`.

```bash
# SSH into server
ssh flawchess

# Check services
ssh flawchess "cd /opt/flawchess && docker compose ps"

# View backend logs
ssh flawchess "cd /opt/flawchess && docker compose logs --tail=50 backend"

# Deploy (always use this — runs CI tests, then deploys the `production` branch)
# Promote a release first: PR main → production, then:
bin/deploy.sh

# Restart backend only
ssh flawchess "cd /opt/flawchess && docker compose restart backend"

# Full restart (data persists in named volumes)
ssh flawchess "cd /opt/flawchess && docker compose down && docker compose up -d"
```

- Domain: flawchess.com (Caddy handles auto-TLS)
- Stack: PostgreSQL 18 + FastAPI/Uvicorn + Caddy 2.11.2
- Hetzner Cloud CPX42, 8 vCPUs, 16 GB RAM + 4 GB swap (`/swapfile`), 160 GB NVMe (upgraded from CPX32 on 2026-05-22 after the FLAWCHESS-3Q recurrence; previous box was 4 vCPU / 7.6 GB / 75 GB).
- Swap added 2026-03-22 after PostgreSQL was OOM-killed during a large game import. Import batch size was also reduced from 50 to 10 games (see `_BATCH_SIZE` in `import_service.py`).
- **OOM recurrence 2026-05-16 (FLAWCHESS-56 / FLAWCHESS-3Q)**: Phase 41.1 had raised `_BATCH_SIZE` back to 28 and added a per-batch Stockfish eval pass; with prod `STOCKFISH_POOL_SIZE=4` this re-triggered a Postgres OOM-kill during a (concurrent, duplicate) import for user 94. Hotfix: `_BATCH_SIZE` → 12, `_HASH_MB` → 32, prod swap raised above 2 GB, `STOCKFISH_POOL_SIZE` lowered. Deferred to a GSD phase: resilient failure-state recording (retry on DB-recovery), scheduled orphan-job reaper (current `cleanup_orphaned_jobs()` only runs at backend startup, so a Postgres-only restart leaves jobs stuck `in_progress`), and an atomic duplicate-import guard.
- **OOM recurrence 2026-05-21 13:42 UTC (FLAWCHESS-3Q, hotfix PR #139)**: a single chess.com import for user 101 (`delusional_sacrificer`, job `72a4ca0d`) ran fetch at ~20 g/s — roughly 2× the 11 g/s the Phase 91 dual-platform stress test measured against, because no lichess fetch was contending for CPU. One uvicorn process fanned out to 13 active Postgres backends (SQLAlchemy `pool_size=20, max_overflow=30` = 50 ceiling) and exhausted host RAM + 4 GB swap; Postgres auto-recovered in ~3 s. Hotfix: SQLAlchemy pool → 10 + 10 = 20, Postgres `max_connections` → 30, backend/db container `mem_limit` + `memswap_limit` set (no swap → contained OOM-restart), Hetzner upgrade CPX32 → CPX42. Postgres memory settings retuned for 16 GB host: `shared_buffers=4GB`, `effective_cache_size=12GB`, `work_mem=16MB`, `maintenance_work_mem=512MB`.
- Hetzner Cloud Firewall configured with inbound TCP 22/80/443 + ICMP from any
- Alembic migrations run automatically on backend container startup via `deploy/entrypoint.sh`
- `.env` on server at `/opt/flawchess/.env` — never commit production secrets
- Docker BuildKit cache is capped at 3 GB by a daily cron job at `/etc/cron.d/docker-builder-prune` (3am UTC, logs to `/var/log/docker-builder-prune.log`). Daily (not weekly) because each `bin/deploy.sh` run rebuilds images on the server, and a few deploys per day grow the cache past 6 GB between weekly runs. Without it the cache grows tens of GB over a few weeks of deploys and fills the disk. Note: with Docker's containerd image store, BuildKit cache lives in `/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs`, not `/var/lib/docker/buildkit` — use `docker system df` to inspect, not `du`.

## Version Control

This project uses **GitLab Flow** (adopted 2026-05-16): `main` is the integration trunk, a long-lived `production` branch is exactly what is deployed.

- **`main`** — integration trunk. Feature/phase work branches off `main` and merges back via **local squash-merge** (`git checkout main && git merge --squash <branch> && git commit && git push`, then delete the merged branch: `git branch -D <branch>` plus `git push origin --delete <branch>` if it was pushed), not a GitHub PR — the PR round-trip is too slow and only gets slower as the suite grows. `main` may contain unreleased, unshipped milestone work. Pushing to `main` never deploys. **The full-suite gate runs once, right before the squash-merge that integrates a unit of work into `main`** — the *complete* Pre-PR checklist below (backend `ruff`/`ty`/`pytest` **and** frontend `npm run lint && npm test`). That run is the safety net replacing pre-merge CI, so at that integration point a subset run (e.g. one test file) is not acceptable. It is NOT a per-commit tax: incremental commits on a feature branch, and small direct commits to `main`, run only the tests you judge relevant (or none for trivial no-logic changes — docs, comments, a constant, CHANGELOG line). Use judgment on what's "small"; when a commit *is* the integration of real work, run the full gate. This relies on `main` having branch protection with `enforce_admins: false` (admins bypass the required `test` check); if that ever flips to `true`, revert to the PR route. CodeQL still runs post-merge on the push to `main`.
- **`production`** — tracks the exact commit running in prod, and is the real gate: every release goes `main → production` via PR, and `bin/deploy.sh` re-runs the full CI matrix before anything ships, so a broken `main` commit can never reach users. Never commit directly to it; it only ever receives merges from `main` (releases) or from `hotfix/*` branches (urgent prod fixes). `bin/deploy.sh` deploys the `production` branch, not `main`. Always use a PR for `production`.
- **Release promotion**: at a milestone boundary (or any approved release point), open a PR `main → production`, then run `bin/deploy.sh`.
- **Hotfix flow** (urgent prod fix without shipping unreleased `main`):
  1. `git checkout -b hotfix/<slug> production`
  2. Apply the minimal fix, PR into `production`, merge when approved.
  3. `bin/deploy.sh` (deploys `production`).
  4. Forward-port: merge `production` back into `main` (or cherry-pick the fix) so the fix isn't lost at the next release. Expect conflicts when `main` has diverged — resolve in favour of the prod-safe value.
- **First deploy after adopting GitLab Flow**: the server checkout was on `main`. The deploy workflow now does `git checkout production` + `git reset --hard origin/production`, so the switch is automatic on the next `bin/deploy.sh`. No manual server step needed unless the server working tree is dirty (the deploy aborts on a dirty tree by design).
- **`main`**: local squash-merge after the full local gate passes (see the `main` bullet above). No GitHub PR required. **`production`**: always via PR `main → production`, then `bin/deploy.sh`.

## Changelog & Releases

Releases are cut at the **milestone** boundary (not per phase). Changes accumulate in `CHANGELOG.md` under `## [Unreleased]` as phases merge, then get promoted to a versioned section when the milestone ships.

### Per-phase (when a phase merges to `main`)

Append one or more bullets under `## [Unreleased]` in `CHANGELOG.md`, grouped into `### Added` / `### Changed` / `### Fixed` / `### Removed` / `### Security` / `### Tests` subsections. Reference the phase number. Keep the tone terse and user-facing (what changed, not how). Skip this for `/gsd-quick` / `/gsd-fast` tasks that don't meaningfully change behavior (pure refactors, tooling tweaks, internal cleanup).

### Per-milestone (at milestone close)

When a milestone ships (e.g. via `/gsd-complete-milestone`):

1. In `CHANGELOG.md`, rename `## [Unreleased]` → `## [vX.Y] Milestone Title — YYYY-MM-DD` and reset `[Unreleased]` to empty.
2. Add the compare link at the bottom: `[vX.Y]: https://github.com/flawchess/flawchess/compare/vX.Y-1...vX.Y` and update the `[Unreleased]` link to `compare/vX.Y...HEAD`.
3. Create the git tag (`git tag vX.Y && git push origin vX.Y`).
4. Create the GitHub release, using the `CHANGELOG.md` section as the body:
   ```bash
   gh release create vX.Y --title "vX.Y Milestone Title" --notes-file <(sed -n '/^## \[vX.Y\]/,/^## /p' CHANGELOG.md | sed '$d')
   ```
   Or craft the notes inline with `--notes "$(cat <<'EOF' ... EOF)"` when you want a richer release page (stats, PR list) than the CHANGELOG entry.

Never cut a release without a matching `CHANGELOG.md` entry. Never edit a released section retroactively — corrections go in a new `[Unreleased]` bullet.

## Project Management

This project is managed with [GET SHIT DONE (GSD)](https://github.com/gsd-build/get-shit-done). All features and work are planned through GSD phases and roadmap. Do not add unplanned features, refactors, or improvements outside the current GSD phase scope. If something seems needed but isn't in the plan, flag it rather than implementing it.

### GSD Context Management

- **Discuss → Plan: keep context.** The planner benefits from having the raw discussion available for resolving ambiguities not fully captured in artifacts.
- **Plan → Execute: `/clear` before execution.** The executor reads `PLAN.md` and `RESEARCH.md` from `.planning/` — everything important is already distilled there. Clearing frees context for file reads, test output, and error traces, and improves signal-to-noise ratio.
- **Small tasks (`/gsd:quick`, `/gsd:fast`): don't bother clearing** — the overhead isn't worth it for inline tasks.

## User Context

- Data scientist, 15 years web dev, Python expert, proficient with FastAPI
- Not a frontend specialist but comfortable with React
- Wants to approve tech decisions before they're locked in

## Communication Style

- **No sycophancy** — never open with hollow praise ("Great question!", "That's a great idea!"). Get straight to substance.
- **Challenge ideas constructively** — if an instruction or approach has flaws, trade-offs, or better alternatives, say so directly with reasoning. Don't just agree and execute.
- **Flag over-engineering and scope creep** — push back when a request adds unnecessary complexity or drifts from the goal.
- **Be honest about uncertainty** — say "I'm not sure" or "this might not work because…" rather than presenting guesses as facts.
- **Disagree and commit** — after raising concerns, respect the user's final call and execute fully.
- **Use em-dashes sparingly** — they've become a tell for AI-generated text. Prefer commas, periods, parentheses, or colons in prose, chat replies, commit messages, PR descriptions, and user-facing UI copy (tooltips, info popovers, empty states). A single em-dash per paragraph is plenty; two in one sentence is too many. This is a style preference for human-readable text, not a hard rule for code comments or existing files.

## Coding Guidelines

These apply to both backend and frontend code. For frontend-only rules, see the [Frontend](#frontend) section below.

- **No magic numbers** — extract thresholds, limits, and configuration values into named constants. Example: `const MIN_GAMES_FOR_COLOR = 10` not a bare `10` in a conditional.
- **Type safety** — leverage TypeScript's type system and Python type hints fully. Avoid `any`, prefer explicit types for function signatures, props, and return values. Use discriminated unions over loose string types. On the backend, use Pydantic models for validation and typed dataclasses/TypedDicts where appropriate. Never use bare `str` for fields with a fixed set of values — use `Literal["a", "b", "c"]` in Pydantic schemas, function signatures, and return types. This applies to both schemas and service/repository function parameters.
- **ty compliance** — all backend code must pass `uv run ty check app/ tests/` with zero errors. ty runs in CI between ruff and pytest and blocks the build. When writing new code:
  - Add explicit return type annotations on all functions.
  - Use `Sequence[str]` (not `list[str]`) for function parameters that accept `list[Literal[...]]` values — list is invariant, Sequence is covariant.
  - Use Pydantic models at system boundaries (external API input/output) and TypedDicts for internal structured data (filter params, accumulators). See `app/schemas/normalization.py` and `app/services/stats_service.py` for examples.
  - Use `# ty: ignore[rule-name]` (not `# type: ignore`) to suppress errors that can't be fixed (e.g., SQLAlchemy forward refs, FastAPI-Users generics). Always include the rule name and a brief reason.
- **Comment bug fixes** — when fixing a bug, add a comment at the fix site explaining what broke and why. Future readers shouldn't have to dig through git history to understand why non-obvious code exists.
- **Keep functions small and shallow** — the strongest signals are nesting depth and branching density; raw LOC is a cheap proxy. Limits:
  - **Nesting depth**: soft 3, hard 4 inside any function body. This is the firm rule (Linus' "if you need more than 3 levels of indentation, you're screwed" applies in both stacks).
  - **Logic LOC**: soft 100, hard 200. Measure *logic* lines — exclude the returned JSX tree, large literal config objects (Recharts axis/gradient configs, lookup tables), docstrings, and blank lines. A component with a 30-line hook body and a 200-line declarative JSX return is fine; the same component with 200 lines of `if/else` data shaping before the return is not.
  - **Cognitive complexity**: aim for ≤15 per function (SonarQube default). If a function has many branches but each branch is one line, it can still be too complex even at low LOC.
  Past these limits, split before continuing. Common splits:
  - **Pipeline orchestrators** (insights, import, normalization): one function per stage (`_fetch`, `_classify`, `_attribute`, `_dedupe`, `_rank`), with the top-level function reading as a list of stage calls.
  - **React components mixing data + JSX**: extract data shaping into a `useXyzData` hook; split desktop and mobile renderers into sibling components when both branches exceed ~40 LOC of *logic* (not JSX); pull large Recharts subtrees (gradients, custom tooltips, axis configs) into named sub-components only when they have real reuse value or hide complexity — don't fragment a cohesive declarative tree just to hit a line count.
  - **Routers doing more than HTTP**: keep routers thin — validation, service call, response shaping. Push branching/caching/aggregation into the service layer.
  - **Deeply nested loops**: invert with early `continue`/`return`, extract the inner body into a helper that takes the loop variable, or replace manual bucketing with a dict/`Counter` accumulator.
  - **Don't invent context dataclasses to make signatures fit.** If a dataclass has fewer than 3 fields, one writer, and one reader, pass a tuple or the args directly. Context types earn their keep when they're threaded through 3+ stages or carry ≥4 fields with their own invariants. A bag-of-state created so a helper signature looks tidy is over-engineering.
  - **Group callbacks by domain, not by shared dependencies.** A "handlers" hook that bundles unrelated callbacks because they all need the same context (`navigate`, `setFilters`, etc.) just moves complexity into the type signature. If two callbacks don't share *purpose*, leave them in the parent or co-locate them with the feature they belong to.
- **Refactor bloated code on sight** — when editing a file, if you encounter a function that already breaches the limits above (deep nesting, high logic LOC, mixes 3+ concerns), refactor it as part of the task rather than adding to it. Exceptions: do not refactor outside the scope of a GSD phase plan without flagging it; for `/gsd-quick`/`/gsd-fast` work, prefer a follow-up note over an unscoped refactor. When in doubt, surface the bloat and ask before expanding scope. Note: splitting a function usually grows total LOC in the file by 20–50% (named helpers, signatures, dataclasses). That cost is only worth paying when each piece is independently readable. If your split requires a context object to thread state between helpers that always run together, the original function was probably cohesive — leave it alone or split along a different seam.

## Error Handling & Sentry

Sentry is initialized in both backend (`app/main.py`) and frontend (`frontend/src/instrument.ts`). These rules ensure errors are captured consistently.

### Sentry Dashboard

- **URL**: https://flawchess.sentry.io
- **Organization**: flawchess
- **Project**: flawchess (ID: 4511084868272208)
- **Region**: de.sentry.io

### Backend Rules

- **Always call `sentry_sdk.capture_exception()`** in every non-trivial `except` block in `app/services/` and `app/routers/`. Do not rely on logging alone — errors logged to DB or console do NOT reach Sentry unless explicitly captured.
- **Skip trivial/expected exceptions** — `ValueError` from parsing user input (e.g. time control strings), `UserAlreadyExists` from FastAPI-Users, and similar expected conditions are not bugs and should not be reported.
- **Retry loops: capture on last attempt only** — for retry patterns (chess.com/lichess API retries), do NOT call `capture_exception` on each transient failure. Let the final exception propagate to the top-level handler which captures it once.
- **Never embed variables in error messages** — this fragments Sentry grouping. Pass variable data via `sentry_sdk.set_context()` or `sentry_sdk.set_tag()`:
  ```python
  # WRONG — fragments grouping (each job_id creates a separate Sentry issue)
  raise RuntimeError(f"Import failed for job {job_id}")

  # RIGHT — preserves grouping, variables as context
  sentry_sdk.set_context("import", {"job_id": job_id, "user_id": user_id})
  sentry_sdk.capture_exception(exc)
  ```
- **Use tags for filterable dimensions** — `source` (import/api/auth), `platform` (chess.com/lichess). Use `set_context` for structured data (job_id, game_id, user_id).

### Frontend Rules

- **Global TanStack Query errors** are already captured in `frontend/src/lib/queryClient.ts` via `QueryCache.onError` and `MutationCache.onError`. Do NOT add duplicate `Sentry.captureException()` in components that use `useQuery`/`useMutation` — the global handler covers them.
- **Manual fetch/axios calls in catch blocks** (auth forms, direct API calls outside TanStack Query) MUST call `Sentry.captureException(error, { tags: { source: '...' } })`.
- **Skip expected failures** — e.g. checking if Google OAuth is available (`.catch(() => setGoogleAvailable(false))`) is expected to fail in dev environments.
- **Always handle `isError` in data-loading ternary chains** — every `useQuery` result rendered with a loading/data/empty chain must include an `isError` branch showing "Failed to load [X]. Something went wrong. Please try again in a moment." Never let errors fall through to empty-state messages like "No games imported yet" — this misleads users into thinking they have no data when the API simply failed.

## Critical Constraints

- **Never use `asyncio.gather` on the same `AsyncSession`** — SQLAlchemy's `AsyncSession` is not safe for concurrent use from multiple coroutines. A single session uses one DB connection, so gather provides no concurrency benefit anyway. Execute queries sequentially within the same session.
- Always use `httpx.AsyncClient` for external HTTP calls — `requests` blocks the event loop
- lichess `since`/`until` parameters use millisecond timestamps, not seconds
- Only import `Standard` variant games — filter out Chess960, crazyhouse, etc.
- Time control bucketing: <180s = bullet, <600s = blitz, <=1800s = rapid, else classical (based on estimated game duration)
- PGN parsing: wrap per-game in try/except, handle `UnicodeDecodeError`, loop `read_game()` until `None` for multi-game strings
- Use `board.board_fen()` (piece placement only) not `board.fen()` (includes castling/en passant) when comparing positions
- chess.com requires `User-Agent` header; fetch archives sequentially with 100-300ms delays
- API responses never expose internal hashes — return FEN for display

## Frontend

Rules specific to `frontend/` (React + TypeScript + Vite). Shared cross-stack rules live in [Coding Guidelines](#coding-guidelines).

### Code Style & Safety

- **Theme constants in theme.ts** — all theme-relevant color constants (WDL colors, gauge zone colors, glass overlays, opacity factors) must be defined in `frontend/src/lib/theme.ts` and imported from there. Never hard-code color values that have semantic meaning (win/loss/draw, danger/warning/success, muted states) directly in components.
- **`noUncheckedIndexedAccess` is enabled** — every array/Record index access in TypeScript returns `T | undefined`. You must narrow before use: assign to a local variable and check (`const val = arr[i]; if (val) { ... }`), use `!` non-null assertion when the index is provably in bounds, or use `?? fallback` for Records. Never use `// @ts-ignore` to suppress these errors.
- **Knip runs in CI** — `npm run knip` in the frontend detects dead exports and unused dependencies. CI fails if knip finds issues. When removing a feature, also remove its exports. When adding exports, ensure they're actually imported somewhere.
- **Minimum font size is `text-sm`** — never use `text-xs` (or smaller) in new code. Even for badges, captions, metadata, footnotes, and "supporting" labels — `text-sm` is the floor. Sub-`text-sm` becomes unreadable on real devices and at high DPI. If a row feels too dense at `text-sm`, fix the layout (more whitespace, fewer columns, shorter labels), don't shrink the type. Applies to all Tailwind utilities (`text-xs`, raw `font-size` < 14px, `[font-size:0.75rem]`, etc.) and to UI copy on both desktop and mobile. **Exception: hover/tap-activated info tooltips** (Radix popover bodies with the HelpCircle trigger pattern — `MetricStatPopover`, `WdlConfidenceTooltip`, `EvalConfidenceTooltip`, `AchievableScorePopover`, etc.) may use `text-xs`; these are short, transient, opt-in surfaces where the denser text reads as a visual aside rather than primary content.

### UI & Components

- **Mobile friendly UI** — use responsive design patterns (Tailwind breakpoints, flexible layouts) so all pages and components work well on small screens.
- **Always apply changes to mobile too** — when modifying a component that has separate desktop and mobile sections (e.g. Openings page sidebar vs mobile drawer layout), apply the same change to both unless the change is desktop-specific by nature (e.g. a desktop-only layout restructuring). Search for duplicated markup before considering a change complete. This includes styling changes (button variants, colors), adding/removing UI elements (info popovers, icons), and behavioral changes.
- **Primary vs secondary buttons** — "primary" buttons use `variant="default"` (solid filled, high emphasis) for the main call-to-action on a screen/panel. "Secondary" buttons use `variant="brand-outline"` (outlined, lower emphasis) for supporting actions like Save/Suggest in the Bookmarks panel or Reset Filters in the FilterPanel. Do NOT use `variant="secondary"` for secondary actions — that variant is reserved for neutral gray chips/toggles. When a user asks for a "secondary button", they mean `brand-outline`.

### Browser Automation Rules

These rules ensure the UI remains compatible with the Claude Chrome extension and other automated testing tools.

**Required on All New Frontend Code:**

1. **`data-testid` on every interactive element** — buttons, links, inputs, select triggers, toggle items, and collapsible triggers. Use kebab-case, component-prefixed format: `data-testid="btn-import"`, `data-testid="nav-bookmarks"`, `data-testid="filter-time-control-bullet"`.

2. **Semantic HTML** — use `<button>` for clickable non-link elements, `<a>` for navigation, `<nav>` for navigation regions, `<main>` for page content, `<form>` for data entry. Never use `<div onClick>` or `<span onClick>`.

3. **ARIA labels on icon-only buttons** — any button without visible text must have `aria-label`. Example: `<Button aria-label="Flip board" data-testid="board-btn-flip">`.

4. **Major layout containers** — page containers, section headings, and modal dialogs must have `data-testid`. Example: `data-testid="dashboard-page"`, `data-testid="import-modal"`.

5. **Chess board** — the board container must have `data-testid="chessboard"` and the `id="chessboard"` option set (generates stable square IDs like `chessboard-square-e4`). Board moves must support both drag-drop and click-to-click (two clicks: source then target).

**Naming Convention:**
- `btn-{action}` — standalone action buttons
- `nav-{page}` — navigation links
- `filter-{name}` — filter controls
- `board-btn-{action}` — board control buttons
- `{component}-{element}-{id?}` — dynamic elements (e.g., `bookmark-card-3`)
- `square-{coord}` — chess squares (e.g., `square-e4`)
