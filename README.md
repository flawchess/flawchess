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
  <img alt="License" src="https://img.shields.io/badge/license-MIT-blue" />
  <img alt="Python" src="https://img.shields.io/badge/python-3.13-blue" />
  <img alt="React" src="https://img.shields.io/badge/react-19-blue" />
  <img alt="FastAPI" src="https://img.shields.io/badge/fastapi-0.115-green" />
  <img alt="PostgreSQL" src="https://img.shields.io/badge/postgresql-18-blue" />
</p>

## What is FlawChess?

A free, open-source chess analysis platform. Import games from chess.com and lichess to analyze your openings by position (not just name), track endgame performance by category, and find exactly where you win and lose. FlawChess matches positions via Zobrist hashes for precise, cross-platform analysis.

![Opening Explorer](frontend/public/screenshots/opening-explorer.png)

## Features

- **Interactive opening explorer** — step through any opening and see your win/draw/loss rate for every move, scout opponents before a match, discover which moves you struggle against
- **Opening comparison and tracking** — bookmark openings and compare their performance, track how your opening study impacts your win rate over time, filter by time control
- **System opening filter** — filter by your pieces only to analyze system openings like the London across all opponent variations
- **Endgame analytics** — win/draw/loss rates by endgame type (rook, minor piece, pawn, queen, mixed), material conversion and recovery statistics, performance gauges and timelines
- **Cross-platform import** — import from chess.com and lichess, sync new games, scout opponents by importing their games
- **Mobile-friendly PWA** — installable on Android and iOS, optimized for touch
- **Open source** — self-hostable, MIT licensed

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, Python 3.13, SQLAlchemy 2.x, Alembic |
| Frontend | React 19, TypeScript, Vite 5, Tailwind CSS |
| Database | PostgreSQL 18 |
| Chess | python-chess (Zobrist hashing), chess.js, react-chessboard |
| Auth | FastAPI-Users (JWT + Google OAuth) |
| Monitoring | Sentry |
| Hosting | Docker Compose, Caddy (auto-TLS), Hetzner VPS |

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

The script starts PostgreSQL (Docker), installs dependencies, runs migrations, and launches both backend and frontend. The API is at `http://localhost:8000` (docs at `/docs`), frontend at `http://localhost:5173`.

> **Note:** Google OAuth and Sentry are optional — the app works with email/password auth and without error monitoring. Leave those `.env` values empty to skip them.

### Running Tests

```bash
uv run pytest        # Run all tests
uv run pytest -x     # Stop on first failure
```

### Linting

```bash
uv run ruff check .  # Backend lint
uv run ruff format . # Backend format
cd frontend && npm run lint  # Frontend lint
```

## Contributing

Contributions are welcome. Please open an issue to discuss a feature or bug before submitting a pull request — this keeps effort aligned and avoids duplicate work.

Code style:
- Python: [Ruff](https://docs.astral.sh/ruff/) for linting and formatting (`uv run ruff check .` / `uv run ruff format .`)
- TypeScript: ESLint (`npm run lint` in the `frontend/` directory)

## License

MIT — see [LICENSE](LICENSE).

## Links

- Live app: https://flawchess.com
- Contact: support@flawchess.com
