---
created: 2026-03-11T14:19:24.354Z
title: Add users table and authentication
area: database
files:
  - app/models.py
  - app/routers/imports.py
---

## Problem

The `games` table references a `user_id` column, but there is no `users` table or authentication system. Currently, games imported from chess.com and lichess have no proper user identity linking them. When a user imports games from both platforms, they should be associated with the same user account.

Multi-user support requires:
- A `users` table to store user accounts
- Registration and login flows
- FastAPI-Users integration (already specified in CLAUDE.md tech stack)
- Linking games from both chess.com and lichess to a single authenticated user

## Solution

- Add a GSD phase for user management and authentication
- Use FastAPI-Users (already in CLAUDE.md) for registration, login, JWT tokens
- Create `users` table with Alembic migration
- Wire existing `user_id` foreign keys to the new `users` table
- Consider OAuth integration with chess.com/lichess for streamlined onboarding
