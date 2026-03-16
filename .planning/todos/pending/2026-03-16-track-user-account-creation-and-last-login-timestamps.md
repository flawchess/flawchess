---
created: 2026-03-16T18:04:25.423Z
title: Track user account creation and last login timestamps
area: auth
files: []
---

## Problem

Currently the user model does not track when accounts are created or when users last logged in. This metadata is useful for analytics, admin dashboards, and understanding user engagement. Without `created_at` and `last_login` timestamps, there's no way to know user signup dates or activity recency.

## Solution

- Add a `created_at` column (datetime, non-nullable, default=now) to the users table
- Add a `last_login` column (datetime, nullable) to the users table
- Update the login flow to set `last_login` on each successful authentication
- Create an Alembic migration for the schema change
- Check if FastAPI-Users already provides hooks for these fields or if custom logic is needed
