# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

FlawChess — a free, open-source chess analysis platform at flawchess.com. Tagline: "Engines are flawless, humans play FlawChess."

Users import their games from chess.com and/or lichess and analyze win/draw/loss (WDL) rates by board position using Zobrist hashes. This solves inconsistent opening categorization on existing platforms — instead of named openings, FlawChess matches positions exactly.

### Key Features

- **Interactive move explorer** — navigate positions on a chessboard and see WDL rates for each candidate move, based on the user's own game history
- **Opponent scouting** — explore an opponent's opening weaknesses before a match
- **Weakness detection** — find positions where the user's win rate drops off
- **Powerful filters** — filter analysis by color (white/black), time control (bullet/blitz/rapid/classical), and recency
- **System opening analysis** — analyze named opening systems (e.g. the London) across all games
- **Cross-platform analysis** — combine chess.com and lichess games into a single unified dataset

### User Flow

1. Sign up (free, no credit card)
2. Import games from chess.com and/or lichess (background async import)
3. Explore openings on the interactive board with WDL statistics
4. Optionally scout opponents or bookmark positions

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
uv run alembic upgrade head     # Run migrations
uv run alembic revision --autogenerate -m "description"  # Create migration

# Frontend
npm install                     # Install dependencies
npm run dev                     # Dev server
npm run build                   # Production build
npm run lint                    # Lint

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
- Hetzner Cloud, 2 vCPUs, 3.7 GB RAM + 2 GB swap (`/swapfile`), 75 GB NVMe
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
- **Type safety** — leverage TypeScript's type system and Python type hints fully. Avoid `any`, prefer explicit types for function signatures, props, and return values. Use discriminated unions over loose string types. On the backend, use Pydantic models for validation and typed dataclasses/TypedDicts where appropriate.
- **Comment bug fixes** — when fixing a bug, add a comment at the fix site explaining what broke and why. Future readers shouldn't have to dig through git history to understand why non-obvious code exists.
- **Always check mobile variants** — when modifying a component that has separate desktop and mobile sections (e.g. Openings page sidebar vs mobile layout), apply the change to both. Search for duplicated markup before considering a change complete.

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
