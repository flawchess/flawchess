---
created: 2026-03-24T17:36:08.056Z
title: Optimize game_positions column types for storage efficiency
area: database
files:
  - app/models/game_position.py:25
  - app/models/game_position.py:36
  - app/models/base.py:9-11
---

## Problem

The `type_annotation_map` in `Base` maps all `Mapped[int]` to `BIGINT` (8 bytes). This was set for Zobrist hashes (which need 64-bit), but it forces every integer column — including `ply`, `user_id`, `material_imbalance` — to use `BIGINT` unnecessarily.

Similarly, `clock_seconds` uses `Float` (no precision), which maps to `DOUBLE PRECISION` (8 bytes) on PostgreSQL. Clock values are at most ~10,000 seconds with 1 decimal place — `REAL` (4 bytes) is sufficient.

On a table with millions of rows (every half-move of every game), saving ~10 bytes per row adds up significantly.

**Columns to downsize:**
- `ply`: `BIGINT` (8B) → `SmallInteger` (2B) — max value ~300
- `clock_seconds`: `DOUBLE PRECISION` (8B) → `REAL` (4B) — ~7 digits precision is plenty
- `material_imbalance`: `BIGINT` (8B) → `SmallInteger` (2B) — centipawn range ±~3900

## Solution

1. Remove `int: BIGINT` from `type_annotation_map` in `Base` — let SQLAlchemy default to `INTEGER` (4B) for all `Mapped[int]` columns
2. Add explicit `BigInteger` on the three Zobrist hash columns (`full_hash`, `white_hash`, `black_hash`) which genuinely need 64-bit
3. Add explicit `SmallInteger` overrides on `ply` and `material_imbalance`
4. Change `clock_seconds` to `Float(24)` (`REAL`, 4B) instead of default `DOUBLE PRECISION`
5. Create an Alembic migration to `ALTER COLUMN ... TYPE` across all affected tables (touches PKs and FKs, so not trivial)
