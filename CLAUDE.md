# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

FlawChess — a free, open-source chess analysis platform at flawchess.com. Tagline: "Engines are flawless, humans play FlawChess."

Users import their games from chess.com and/or lichess and analyze win/draw/loss (WDL) rates by board position using Zobrist hashes. This solves inconsistent opening categorization on existing platforms — instead of named openings, FlawChess matches positions exactly.

### Key Features

- **Interactive move explorer** — navigate positions on a chessboard and see WDL rates for each candidate move, scout opponents, detect weaknesses
- **Opening comparison and tracking** — bookmark openings, compare performance, track win rate over time with filters
- **System opening filter** — filter by user's pieces only to analyze system openings (e.g. the London) across all opponent variations
- **Endgame analytics** — WDL rates by endgame type, material conversion/recovery stats, performance gauges, rolling-window timelines
- **Cross-platform analysis** — combine chess.com and lichess games, powerful filters (color, time control, recency)

### User Flow

1. Sign up (free, no credit card)
2. Import games from chess.com and/or lichess (background async import)
3. Explore openings on the interactive board with WDL statistics
4. Analyze endgame performance by type with conversion/recovery metrics
5. Optionally scout opponents or bookmark positions

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

# Deploy via GitHub Actions (preferred — runs tests first)
bin/deploy.sh

# Deploy via SSH (direct — skips CI tests)
ssh flawchess "cd /opt/flawchess && git pull origin main && docker compose up -d --build"

# Restart backend only
ssh flawchess "cd /opt/flawchess && docker compose restart backend"

# Full restart (data persists in named volumes)
ssh flawchess "cd /opt/flawchess && docker compose down && docker compose up -d"
```

- Domain: flawchess.com (Caddy handles auto-TLS)
- Stack: PostgreSQL 18 + FastAPI/Uvicorn + Caddy 2.11.2
- Hetzner Cloud, 4 vCPUs, 7.6 GB RAM + 2 GB swap (`/swapfile`), 75 GB NVMe (upgraded 2026-04-01, disk unchanged — can downgrade)
- Swap added 2026-03-22 after PostgreSQL was OOM-killed during a large game import. Import batch size was also reduced from 50 to 10 games (see `_BATCH_SIZE` in `import_service.py`).
- Hetzner Cloud Firewall configured with inbound TCP 22/80/443 + ICMP from any
- Alembic migrations run automatically on backend container startup via `deploy/entrypoint.sh`
- `.env` on server at `/opt/flawchess/.env` — never commit production secrets

## Version Control

- **`main`** is the production branch. Pushes to main do NOT auto-deploy — deployment is manual via `workflow_dispatch` in GitHub Actions or SSH.
- Always create a pull request before merging a feature or phase branch into main. Squash and merge the pull request into main only when approved or requested by the user.
- When working on the main branch (e.g. with /gsd:quick), don't commit the changes unless the user explicitly asks for it. When working on a feature branch, you can commit as often as you like.
- **v2 development** will use a long-lived `v2` branch. v1.x work continues on `main` via feature branches.

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

## Coding Guidelines

- **No magic numbers** — extract thresholds, limits, and configuration values into named constants. Example: `const MIN_GAMES_FOR_COLOR = 10` not a bare `10` in a conditional.
- **Theme constants in theme.ts** — all theme-relevant color constants (WDL colors, gauge zone colors, glass overlays, opacity factors) must be defined in `frontend/src/lib/theme.ts` and imported from there. Never hard-code color values that have semantic meaning (win/loss/draw, danger/warning/success, muted states) directly in components.
- **Type safety** — leverage TypeScript's type system and Python type hints fully. Avoid `any`, prefer explicit types for function signatures, props, and return values. Use discriminated unions over loose string types. On the backend, use Pydantic models for validation and typed dataclasses/TypedDicts where appropriate. Never use bare `str` for fields with a fixed set of values — use `Literal["a", "b", "c"]` in Pydantic schemas, function signatures, and return types. This applies to both schemas and service/repository function parameters.
- **ty compliance** — all backend code must pass `uv run ty check app/ tests/` with zero errors. ty runs in CI between ruff and pytest and blocks the build. When writing new code:
  - Add explicit return type annotations on all functions.
  - Use `Sequence[str]` (not `list[str]`) for function parameters that accept `list[Literal[...]]` values — list is invariant, Sequence is covariant.
  - Use Pydantic models at system boundaries (external API input/output) and TypedDicts for internal structured data (filter params, accumulators). See `app/schemas/normalization.py` and `app/services/stats_service.py` for examples.
  - Use `# ty: ignore[rule-name]` (not `# type: ignore`) to suppress errors that can't be fixed (e.g., SQLAlchemy forward refs, FastAPI-Users generics). Always include the rule name and a brief reason.
- **Comment bug fixes** — when fixing a bug, add a comment at the fix site explaining what broke and why. Future readers shouldn't have to dig through git history to understand why non-obvious code exists.
- **Always check mobile variants** — when modifying a component that has separate desktop and mobile sections (e.g. Openings page sidebar vs mobile layout), apply the change to both. Search for duplicated markup before considering a change complete.

## Error Handling & Sentry

Sentry is initialized in both backend (`app/main.py`) and frontend (`frontend/src/instrument.ts`). These rules ensure errors are captured consistently.

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

## Critical Constraints

- Always use `httpx.AsyncClient` for external HTTP calls — `requests` blocks the event loop
- lichess `since`/`until` parameters use millisecond timestamps, not seconds
- Only import `Standard` variant games — filter out Chess960, crazyhouse, etc.
- Time control bucketing: <180s = bullet, <600s = blitz, <=1800s = rapid, else classical (based on estimated game duration)
- PGN parsing: wrap per-game in try/except, handle `UnicodeDecodeError`, loop `read_game()` until `None` for multi-game strings
- Use `board.board_fen()` (piece placement only) not `board.fen()` (includes castling/en passant) when comparing positions
- chess.com requires `User-Agent` header; fetch archives sequentially with 100-300ms delays
- API responses never expose internal hashes — return FEN for display

## User Interface

- The UI must be mobile friendly. Use responsive design patterns (Tailwind breakpoints, flexible layouts) so all pages and components work well on small screens.

## Browser Automation Rules

These rules ensure the UI remains compatible with the Claude Chrome extension and other automated testing tools.

### Required on All New Frontend Code

1. **`data-testid` on every interactive element** — buttons, links, inputs, select triggers, toggle items, and collapsible triggers. Use kebab-case, component-prefixed format: `data-testid="btn-import"`, `data-testid="nav-bookmarks"`, `data-testid="filter-time-control-bullet"`.

2. **Semantic HTML** — use `<button>` for clickable non-link elements, `<a>` for navigation, `<nav>` for navigation regions, `<main>` for page content, `<form>` for data entry. Never use `<div onClick>` or `<span onClick>`.

3. **ARIA labels on icon-only buttons** — any button without visible text must have `aria-label`. Example: `<Button aria-label="Flip board" data-testid="board-btn-flip">`.

4. **Major layout containers** — page containers, section headings, and modal dialogs must have `data-testid`. Example: `data-testid="dashboard-page"`, `data-testid="import-modal"`.

5. **Chess board** — the board container must have `data-testid="chessboard"` and the `id="chessboard"` option set (generates stable square IDs like `chessboard-square-e4`). Board moves must support both drag-drop and click-to-click (two clicks: source then target).

### Naming Convention
- `btn-{action}` — standalone action buttons
- `nav-{page}` — navigation links
- `filter-{name}` — filter controls
- `board-btn-{action}` — board control buttons
- `{component}-{element}-{id?}` — dynamic elements (e.g., `bookmark-card-3`)
- `square-{coord}` — chess squares (e.g., `square-e4`)
