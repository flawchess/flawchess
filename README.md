<p align="center">
  <img src="frontend/public/icons/logo-128.png" alt="FlawChess logo" width="128" />
</p>

<h1 align="center">FlawChess</h1>

<p align="center">
  <em>Engines are flawless, humans play FlawChess</em>
</p>

<p align="center">
  Live at <a href="https://flawchess.com"><strong>flawchess.com</strong></a>
</p>

<p align="center">
  <a href="https://github.com/flawchess/flawchess/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/flawchess/flawchess/actions/workflows/ci.yml/badge.svg" /></a>
  <a href="https://github.com/flawchess/flawchess/actions/workflows/github-code-scanning/codeql"><img alt="CodeQL" src="https://github.com/flawchess/flawchess/actions/workflows/github-code-scanning/codeql/badge.svg" /></a>
  <a href="https://docs.renovatebot.com"><img alt="Renovate" src="https://img.shields.io/badge/renovate-enabled-brightgreen?logo=renovatebot" /></a>
  <img alt="License" src="https://img.shields.io/badge/license-MIT-blue" />
  <img alt="Python" src="https://img.shields.io/badge/python-3.13-blue" />
  <img alt="React" src="https://img.shields.io/badge/react-19-blue" />
  <img alt="FastAPI" src="https://img.shields.io/badge/fastapi-0.115-green" />
  <img alt="PostgreSQL" src="https://img.shields.io/badge/postgresql-18-blue" />
</p>

## What is FlawChess?

A free, open-source chess analysis platform. Import games from chess.com and lichess to find leaks in your openings, endgames, and time management, with AI-narrated insights that explain what your stats mean. Position matching uses Zobrist hashes (not opening names), so analysis stays consistent across platforms.

![Opening Explorer](frontend/public/screenshots/opening-explorer.png)

## Features

- **Endgame analytics** — WDL by endgame type (rook, minor piece, pawn, queen, mixed), conversion rates when up material and recovery rates when down, Endgame ELO timeline per platform/time control, and LLM-narrated personalized feedback explaining what your stats mean.
- **Opening explorer & insights** — step through any position and see your WDL per candidate move; an automatic 16-half-move scan surfaces opening strengths and weaknesses with deep-links into the explorer; works for scouting opponents too.
- **Time management stats** — clock advantage/deficit at endgame entry, performance under matching time pressure vs opponents, flag rates per time control.
- **Opening comparison & tracking** — bookmark openings and compare WDL trends over time, filter by time control to see what works where.
- **System opening filter** — filter by your pieces only to analyze system openings like the London across all opponent variations.
- **Cross-platform import** — combine chess.com and lichess games, filter by color, time control, opponent type, and recency.
- **Mobile-friendly PWA** — installable on Android and iOS, optimized for touch.
- **Open source** — self-hostable, MIT licensed.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, Python 3.13, SQLAlchemy 2.x, Alembic |
| Frontend | React 19, TypeScript, Vite 5, Tailwind CSS |
| Database | PostgreSQL 18 |
| Chess | python-chess (Zobrist hashing), chess.js, react-chessboard |
| Auth | FastAPI-Users (JWT + Google OAuth) |
| Monitoring | Sentry |
| Hosting | Docker Compose, Caddy (auto-TLS), Hetzner Cloud CPX42 (8 vCPU, 16 GB RAM, 160 GB NVMe) |

## Getting Started

### Prerequisites

- Python 3.13 + [uv](https://docs.astral.sh/uv/)
- Node.js 20+
- Docker

### Setup

```bash
git clone https://github.com/flawchess/flawchess.git
cd flawchess
cp .env.example .env  # Edit with your settings
bin/run_local.sh
```

The script starts PostgreSQL (Docker), installs dependencies, runs migrations, seeds the openings reference table, installs the pinned Stockfish binary (via `bin/install_stockfish.sh` — same release and SHA-256 as the prod Docker image), and launches both backend and frontend. The API is at `http://localhost:8000` (docs at `/docs`), frontend at `http://localhost:5173`.

> **Note:** Google OAuth and Sentry are optional — the app works with email/password auth and without error monitoring. Leave those `.env` values empty to skip them.

> **Stockfish:** `bin/install_stockfish.sh` installs the pinned `sf_18` binary for your platform (Linux x86_64, macOS Apple Silicon, or macOS Intel) to `~/.local/stockfish/sf`, SHA-256 verified. The backend auto-discovers it (no `STOCKFISH_PATH` needed in dev); set `STOCKFISH_PATH` only to point at a binary in a non-standard location. Other platforms: install Stockfish manually and set `STOCKFISH_PATH`.

### Running Tests

```bash
uv run pytest          # Run all tests (serial)
uv run pytest -x       # Stop on first failure
uv run pytest -n auto  # Run in parallel across all CPU cores (much faster locally)
```

Each test run, and each `pytest-xdist` worker under `-n auto`, gets its own database cloned from a migrated template, so parallel and concurrent runs are fully isolated. `-n auto` is roughly 2x faster than serial on a multi-core machine. The template auto-refreshes whenever you add a migration, so there is no manual rebuild step. CI runs the suite serially for deterministic, bisectable logs; `-n auto` is a local convenience.

### Test Coverage

Backend uses `pytest-cov` (already in dev dependencies):

```bash
uv run pytest --cov=app --cov-report=term-missing   # Terminal report with missing lines
uv run pytest --cov=app --cov-report=html           # HTML report at htmlcov/index.html
```

Frontend uses Vitest's coverage (v8 provider):

```bash
cd frontend
npx vitest run --coverage                           # Terminal + HTML at coverage/index.html
```

### Linting & Type Checking

```bash
uv run ruff check .           # Backend lint
uv run ruff format .          # Backend format
uv run ty check app/ tests/   # Backend type check (zero errors required)
cd frontend && npm run lint   # Frontend lint
```

The CI pipeline runs these in order: ruff (lint) → [ty](https://github.com/astral-sh/ty) (type check) → pytest (tests). All three must pass.

## Remote eval worker

`scripts/remote_eval_worker.py` adds off-box CPU to the Stockfish eval pipeline. Run it on any trusted machine to drain the same tier-3 eval queue as the production server: lease a game over HTTPS, evaluate its positions locally with Stockfish, batch-submit the results unchanged (the server owns the storage convention).

### Prerequisites

- Stockfish installed locally (`bin/install_stockfish.sh`).
- Server and worker share an `EVAL_OPERATOR_TOKEN` in their `.env`. Endpoints fail closed: unset token → 403, wrong token → 401. Optionally set `EXPECTED_SF_VERSION` on the server to reject mismatched engine builds. Use `--token` to override the worker's `.env` value for a one-off run.

The worker is a standalone HTTP client plus a local Stockfish driver: it talks to the server over HTTPS and never opens a database connection, so **no Docker is required** to run it. A repo checkout with `uv sync` (the worker imports `app.*`) plus a Stockfish binary is all you need.

### Running on Windows

The worker runs natively on Windows — the only Linux-specific code path (`SCHED_IDLE` scheduling) is guarded and skipped on non-Linux hosts. Two setup steps differ from Linux/macOS:

1. **Stockfish binary.** `bin/install_stockfish.sh` is a bash script that fetches the Linux build, so it won't run on Windows. Download the Windows Stockfish release manually (match the version the server pins via `EXPECTED_SF_VERSION`, or submits are rejected by the D-5 version gate) and point the worker at it with `STOCKFISH_PATH` in `.env`:

   ```
   STOCKFISH_PATH=C:\path\to\stockfish.exe
   ```

   The engine resolver checks `STOCKFISH_PATH` first, then falls back to `stockfish` on `PATH`.
2. **`.env`.** Only `EVAL_OPERATOR_TOKEN` is required (every other setting has a default, and the worker needs no database). Pass `--token` instead if you'd rather not write a `.env`.

Then run the same commands as below via `uv run python scripts/remote_eval_worker.py …`.

### Start

With the token in `.env` and `--base-url` defaulting to production, the worker needs no flags:

```bash
# Connectivity smoke test — lease + evaluate, never submit:
uv run python scripts/remote_eval_worker.py --dry-run --once

# Process one game, then exit:
uv run python scripts/remote_eval_worker.py --once

# Continuous drain (default — 4 parallel Stockfish processes):
uv run python scripts/remote_eval_worker.py

# 8 engine processes, pointed at a staging server:
uv run python scripts/remote_eval_worker.py --workers 8 --base-url http://localhost:8000
```

Flags: `--base-url` (default `https://flawchess.com`), `--token` (override `.env`), `--workers N` (default 4, ≈ core count), `--idle-sleep SECONDS` (empty-queue poll delay, default 5), `--dry-run` (never submit), `--once` (one cycle then exit).

### Stop

It's a foreground process — press `Ctrl-C`. The worker shuts the engine pool down cleanly on interrupt. For an unattended long-running drain, wrap it yourself (`tmux`/`screen`, `nohup … &`, or a systemd unit); there is no built-in daemon mode. The continuous loop is resilient: a transient network error, a 5xx, or a bad position is logged to Sentry, then the worker backs off `--idle-sleep` and retries rather than dying.

### Monitoring throughput

The worker logs each cycle with a UTC timestamp (`Leased game_id=… (N positions)` → `Submitted game_id=…`), so per-game timing is visible in stdout. For aggregate throughput across *all* drain sources (the server pool plus any workers), query the server: every completed game is stamped with `full_evals_completed_at`, so `count(*)` over that column in a time window gives games/minute directly.

## Backups & Recovery

The production VM is backed up by Hetzner's **automatic daily whole-server backup** feature with a 7-day rolling retention. Snapshots are managed by Hetzner and stored off the VM — a full disk loss can be recovered from the previous day's snapshot via the Hetzner Cloud Console.

- **Frequency:** daily, managed by Hetzner
- **Retention:** 7 days (rolling)
- **Scope:** full server image (PostgreSQL data volume included)
- **RPO:** up to 24 hours
- **PITR:** not enabled (point-in-time recovery would require WAL archiving in addition to the daily snapshot)

For deeper data-corruption scenarios that slip past 7 days (e.g. a silent bug that corrupts rows across weeks), a logical `pg_dump` retained separately would be a useful second layer but is not currently configured.

## Changelog & Releases

Release notes are published per milestone on the [GitHub Releases](https://github.com/flawchess/flawchess/releases) page. The full history across all milestones lives in [CHANGELOG.md](CHANGELOG.md), which follows a [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) -inspired format.

## Contributing

Contributions are welcome. Please open an issue to discuss a feature or bug before submitting a pull request — this keeps effort aligned and avoids duplicate work.

Code style:
- Python: [Ruff](https://docs.astral.sh/ruff/) for linting and formatting, [ty](https://github.com/astral-sh/ty) for static type checking — `uv run ty check app/ tests/` must pass with zero errors
- TypeScript: ESLint (`npm run lint` in the `frontend/` directory)

## License

MIT — see [LICENSE](LICENSE).

## Links

- Live app: https://flawchess.com
- Contact: support@flawchess.com
