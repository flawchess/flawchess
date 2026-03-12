# Roadmap: Chessalytics

## Overview
- Total phases: 4
- Total requirements: 21
- Granularity: Coarse

---

## Phase 1: Data Foundation

**Goal:** Establish the database schema and position-hashing module that every subsequent phase depends on — getting this wrong would require rewriting the data layer.

**Requirements:**
- INFRA-01: Database schema supports efficient position-based queries using indexed Zobrist hash columns
- INFRA-03: Duplicate games are prevented via unique constraint on (platform, platform_game_id)
- IMP-05: All available game metadata is stored (PGN, time control, rated flag, result, opponent, color, platform URL, timestamps)
- IMP-06: Position hashes (white, black, full Zobrist) are precomputed and stored for every half-move at import time

**Plans:** 2/2 plans complete

Plans:
- [ ] 01-01-PLAN.md — Project scaffold, SQLAlchemy models, and Alembic migration
- [ ] 01-02-PLAN.md — Zobrist hash computation module (TDD)

**Success Criteria:**
1. A developer can run migrations and observe `games`, `game_positions`, and related tables with the correct columns and indexes in the DB.
2. Given a PGN string, the position hash module returns three integer hashes per half-move, and unit tests confirm identical board states produce identical hashes.
3. Inserting the same game twice leaves exactly one row (duplicate constraint enforced at the DB level).

**Dependencies:** None

---

## Phase 2: Import Pipeline

**Goal:** Let a user fetch their full game history from chess.com and lichess in the background, with incremental re-sync and visible progress.

**Requirements:**
- IMP-01: User can import games from chess.com by entering their username
- IMP-02: User can import games from lichess by entering their username
- IMP-03: User can re-sync to fetch only new games since last import (incremental)
- IMP-04: User sees import progress and status while games are being fetched
- INFRA-02: Game import runs as a background task (does not block the API server)

**Plans:** 4/4 plans complete

Plans:
- [x] 02-01-PLAN.md — ImportJob model, schemas, normalization utilities, and game repository
- [x] 02-02-PLAN.md — chess.com and lichess API clients
- [ ] 02-03-PLAN.md — Import service orchestrator and API router

**Success Criteria:**
1. A user submits a chess.com or lichess username and immediately receives a job ID; the import runs in the background and completes without blocking other requests.
2. Polling the import status endpoint shows live progress (games fetched so far) and a terminal state (completed or failed with an error message).
3. Running re-sync after new games have been played fetches only the new games; total game count increases by the exact number of new games, with no duplicates.
4. Submitting an invalid username returns a clear error message without crashing the import pipeline.

**Dependencies:** Phase 1

---

## Phase 3: Analysis API

**Goal:** Define and implement the full backend analysis contract so that any client (including the not-yet-built frontend) can query win/draw/loss rates and matching game lists by position, side, and filters.

**Requirements:**
- ANL-02: User can filter position matches by white pieces only, black pieces only, or both sides
- ANL-03: User sees win/draw/loss counts and percentages for all matching games
- FLT-01: User can filter analysis results by time control (bullet, blitz, rapid, classical)
- FLT-02: User can filter analysis results by rated vs casual games
- FLT-03: User can filter analysis results by game recency (week, month, 3 months, 6 months, 1 year, all time)
- FLT-04: User can filter analysis results by color played (white or black)
- RES-01: User sees a list of matching games showing opponent name, result, date, and time control
- RES-02: Each matching game has a clickable link to the game on chess.com or lichess
- RES-03: User always sees the total games denominator ("X of Y games matched")

**Plans:** 2/2 plans complete

Plans:
- [ ] 03-01-PLAN.md — Schemas, repository, service, and router for analysis endpoint
- [ ] 03-02-PLAN.md — Repository and service test suite

**Success Criteria:**
1. Posting a target position hash to the analysis endpoint with `match_side=white` returns only games where the user's white pieces matched, with correct W/D/L counts.
2. Applying time control, rated, recency, and color filters in combination changes the match count predictably — verifiable against the raw game records in the DB.
3. Every result record includes opponent name, result, date, time control, and a working external URL to the game.
4. The response always includes both the match count and the total eligible game count, even when zero games match.

**Dependencies:** Phase 1, Phase 2

---

## Phase 4: Frontend and Auth

**Goal:** Deliver a complete, multi-user web application where each user can log in, import their games, specify a position on an interactive board, apply filters, and read their personal win rates.

**Requirements:**
- ANL-01: User can specify a target position by playing moves on an interactive chess board
- AUTH-01: User can create an account and log in
- AUTH-02: Each user's games and analyses are isolated (row-level data scoping)

**Plans:** 3 plans (2/3 complete)

Plans:
- [x] 04-01-PLAN.md — Backend auth: User model, FastAPI-Users, auth routes, CORS, replace user_id=1, tests
- [x] 04-02-PLAN.md — Frontend scaffold: Vite + React + shadcn/ui, auth pages, Zobrist JS port
- [ ] 04-03-PLAN.md — Dashboard UI: chess board, filters, W/D/L results, import modal

**Success Criteria:**
1. A new user can register, log in, enter a chess.com or lichess username, and see their import progress — all from the browser with no manual API calls.
2. A user can play moves on the interactive board, select a side filter, and submit the position; the page displays W/D/L percentages and a scrollable list of matching games with external links.
3. Two different users' game data and analysis results are fully isolated — user A cannot see or query user B's games.
4. All filter controls (time control, rated, recency, color) are visible simultaneously and update results without a page reload.

**Dependencies:** Phase 1, Phase 2, Phase 3

---

## Requirement Coverage

All 21 v1 requirements are mapped:
- Phase 1: 4 requirements (INFRA-01, INFRA-03, IMP-05, IMP-06)
- Phase 2: 5 requirements (IMP-01, IMP-02, IMP-03, IMP-04, INFRA-02)
- Phase 3: 9 requirements (ANL-02, ANL-03, FLT-01, FLT-02, FLT-03, FLT-04, RES-01, RES-02, RES-03)
- Phase 4: 3 requirements (ANL-01, AUTH-01, AUTH-02)

---
*Created: 2026-03-11*
