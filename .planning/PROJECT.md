# Chessalytics

## What This Is

A multi-user chess analysis platform that lets players import their games from chess.com and lichess, then analyze win/draw/loss rates for specific board positions. It solves the problem of inconsistent opening categorization on existing platforms — instead of relying on opening names, users define positions visually and filter by actual piece placement.

## Core Value

Users can determine their success rate for any opening position they specify, filtering by their own pieces only, regardless of how platforms categorize the opening.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Import games from chess.com and lichess via API by username
- [ ] On-demand re-sync to fetch latest games
- [ ] Store all available game metadata for future analyses
- [ ] Interactive chess board to specify search positions by playing moves
- [ ] Filter analysis by white position only, black position only, or both
- [ ] Strict move order matching or any-order position matching
- [ ] Filter by time control (bullet, blitz, rapid, classical)
- [ ] Filter by rated vs casual games
- [ ] Filter by game recency (week, month, 3 months, 6 months, 1 year, all time)
- [ ] Display win/draw/loss rates for matching games
- [ ] Display matching games with ending position, opponent names, and links to source platform
- [ ] Multi-user support (users import and analyze their own games)

### Out of Scope

- Manual PGN file upload — API import only for v1
- In-app game viewer — link to chess.com/lichess instead
- Advanced stats (opponent rating, performance over time) — v2
- Mobile app — web-first

## Context

- The problem: lichess categorizes the same moves as different openings (e.g., Pirc Defense vs Czech Defense) even when the user plays identical moves. Existing tools don't let you group games by your own piece positions while ignoring opponent moves.
- Chess.com and lichess both have public APIs for fetching games by username.
- python-chess is the established library for chess logic in Python.
- Data volume: thousands of games per user, needs efficient querying.

## Constraints

- **Tech stack**: Python backend (FastAPI), uv for package management
- **Database**: Must support efficient position-based queries across thousands of games
- **Deployment**: Must work locally and be deployable to a server
- **Libraries**: Use established open-source libraries (python-chess, etc.) rather than reinventing

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| FastAPI for backend | User expertise, async support, modern Python | — Pending |
| API-only import (no PGN upload) | Simpler v1, covers primary use case | — Pending |
| Interactive board over FEN input | Better UX for target users | — Pending |
| uv for package management | Fast, modern Python tooling | — Pending |
| Frontend framework | TBD — need to decide React vs simpler approach | — Pending |
| Database choice | TBD — SQLite vs Postgres, needs position query efficiency | — Pending |

---
*Last updated: 2026-03-11 after initialization*
