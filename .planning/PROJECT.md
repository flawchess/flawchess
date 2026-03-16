# Chessalytics

## What This Is

A multi-user chess analysis platform that lets players import their games from chess.com and lichess, then analyze win/draw/loss rates for specific board positions. It solves the problem of inconsistent opening categorization on existing platforms — instead of relying on opening names, users define positions visually and filter by actual piece placement.

## Core Value

Users can determine their success rate for any opening position they specify, filtering by their own pieces only, regardless of how platforms categorize the opening.

## Current Milestone: v1.1 Opening Explorer & UI Restructuring

**Goal:** Add an interactive move explorer (inspired by openingtree.com) showing next moves with W/D/L stats for every position, and restructure the UI with a dedicated Import page and merged Openings tab with sub-tabs.

**Target features:**
- Move explorer: next moves with W/D/L stats per move, click-to-navigate
- Store move SAN in game_positions for performant lookups
- Dedicated Import page (replaces modal)
- Merged Openings tab with Move Explorer / Games / Statistics sub-tabs
- Shared filter sidebar across all sub-tabs

## Requirements

### Validated

<!-- Shipped in v1.0 and confirmed working -->

- ✓ Import games from chess.com and lichess via API by username — v1.0
- ✓ On-demand re-sync to fetch latest games — v1.0
- ✓ Store all available game metadata for future analyses — v1.0
- ✓ Interactive chess board to specify search positions by playing moves — v1.0
- ✓ Filter analysis by white/black/both position matching — v1.0
- ✓ Filter by time control, rated/casual, recency, color, opponent type — v1.0
- ✓ Display win/draw/loss rates for matching games — v1.0
- ✓ Display matching games as cards with metadata and platform links — v1.0
- ✓ Multi-user support with data isolation — v1.0
- ✓ Position bookmarks with auto-suggestions, mini boards, drag-reorder — v1.0
- ✓ Rating history and global stats pages — v1.0

### Active

<!-- v1.1 scope — building toward these -->

- [ ] Move explorer showing next moves with W/D/L stats per move
- [ ] Store move SAN in game_positions with index for performant lookups
- [ ] Dedicated Import page replacing import modal
- [ ] Merged Openings tab with Move Explorer / Games / Statistics sub-tabs
- [ ] Shared filter sidebar across Openings sub-tabs

### Out of Scope

- Manual PGN file upload — API import only
- In-app game viewer — link to chess.com/lichess instead
- Mobile app — web-first
- Human-like engine analysis — future: engine evaluation filtered by human move plausibility at target Elo (see Maia Chess approach)

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
| FastAPI for backend | User expertise, async support, modern Python | Settled |
| API-only import (no PGN upload) | Simpler v1, covers primary use case | Settled |
| Interactive board over FEN input | Better UX for target users | Settled |
| uv for package management | Fast, modern Python tooling | Settled |
| React 19 + TypeScript + Vite 5 | react-chessboard 5.x requires React 19; TanStack Query supports it | Settled |
| PostgreSQL (no SQLite) | Multi-user concurrent writes, BIGINT index performance, asyncpg | Settled |

| DB wipe for v1.1 | No migration needed — reimport after schema change | Settled |

---
*Last updated: 2026-03-16 after milestone v1.1 start*
