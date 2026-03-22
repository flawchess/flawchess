<p align="center">
  <img src="frontend/public/icons/logo-128.png" alt="FlawChess logo" width="128" />
</p>

<h1 align="center">FlawChess</h1>

<p align="center">
  <em>Engines are flawless, humans play FlawChess</em>
</p>

<p align="center">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-blue" />
  <img alt="Python" src="https://img.shields.io/badge/python-3.13-blue" />
  <img alt="React" src="https://img.shields.io/badge/react-19-blue" />
  <img alt="FastAPI" src="https://img.shields.io/badge/fastapi-0.115-green" />
  <img alt="PostgreSQL" src="https://img.shields.io/badge/postgresql-16-blue" />
</p>

## What is FlawChess?

FlawChess is a chess opening analysis platform that matches positions by Zobrist hash — not by opening name. Import your games from chess.com and lichess, then analyze win/draw/loss rates for any exact board position you specify. Stop guessing which "Sicilian line" lost you points; find out which specific positions you actually struggle with.

## Features

- **Find weaknesses in your openings** — analyze W/D/L rates for any board position across all your games
- **Scout your opponents** — load an opponent's username and study their opening tendencies
- **Interactive move explorer** — play moves on the board to navigate positions; see next-move frequency and W/D/L stats per move
- **Cross-platform analysis** — import from chess.com and lichess in one place, analyze combined results
- **Powerful filters** — filter by time control, rating, color, opponent type, platform, recency, and more
- **Mobile-friendly PWA** — installable on Android and iOS, optimized for touch
- **Open source** — self-hostable, MIT licensed

## Screenshots

Screenshots coming soon — visit [flawchess.com](https://flawchess.com) to see the live app.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, Python 3.13, SQLAlchemy 2.x, Alembic |
| Frontend | React 19, TypeScript, Vite 5, Tailwind CSS |
| Database | PostgreSQL 16 |
| Chess | python-chess (Zobrist hashing), chess.js, react-chessboard |
| Auth | FastAPI-Users (JWT + Google OAuth) |
| Monitoring | Sentry |
| Hosting | Docker Compose, Caddy (auto-TLS), Hetzner VPS |

## Local Development

### Prerequisites

- Python 3.13
- Node.js 20+
- Docker

### Setup

```bash
# Clone
git clone https://github.com/flawchess/flawchess.git
cd flawchess

# Start PostgreSQL
docker compose -f docker-compose.dev.yml -p flawchess-dev up -d

# Backend
cp .env.example .env  # Edit with your settings
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`. The frontend dev server runs at `http://localhost:5173`.

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

## Architecture: Zobrist Hash Position Matching

The core idea: positions are matched via precomputed 64-bit Zobrist hashes rather than FEN string comparison or opening name. Three hashes are computed at import time for every half-move:

- **white_hash** — white pieces only (enables "my pieces only" queries)
- **black_hash** — black pieces only
- **full_hash** — complete board position

All hashes are stored in the `game_positions` table, turning position queries into fast indexed integer lookups. This solves the inconsistent opening categorization problem — two games in the same position are guaranteed to match, regardless of how the platform labels the opening.

## Contributing

Contributions are welcome. Open an issue to discuss a feature or bug before submitting a PR.

## License

MIT — see [LICENSE](LICENSE).

## Links

- Live app: https://flawchess.com
- Contact: support@flawchess.com
