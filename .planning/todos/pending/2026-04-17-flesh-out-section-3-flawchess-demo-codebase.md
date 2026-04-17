---
created: 2026-04-17T10:10:20.889Z
title: Flesh out Section 3 FlawChess demo codebase
area: docs
files:
  - docs/agentic-engineering-flawchess.md:148-150
---

## Problem

Section 3 (FlawChess: the demo codebase) has 8 minutes budgeted but only ~20 words of content: "What it is, tech stack, scale (LOC, tables, tests). Why it's a good demo: real domain, real constraints, real bugs." This is the codebase the whole demo rides on — if the audience does not buy that FlawChess is a real production codebase, Sections 4 and 5 lose credibility.

## Solution

- Fill in concrete numbers: backend LOC, frontend LOC, table count, test count, commit count, deployment history.
- Add a UI screenshot (endgame performance page or openings explorer).
- One-sentence "why it's a real codebase not a toy": prod users, real import pipeline hitting two external APIs, real PostgreSQL at scale, real Sentry issues, real CI.
- Call out the constraints the agent has to respect (async SQLAlchemy, Zobrist hashing, FK discipline) that make it a realistic test of agentic engineering.
- Numbers can be pulled from `reports/flawchess_quality_assessment.md` and `gsd-stats`.
