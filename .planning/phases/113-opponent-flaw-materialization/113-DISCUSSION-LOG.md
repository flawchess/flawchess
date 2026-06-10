# Phase 113: Opponent-Flaw Materialization - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-10
**Phase:** 113-opponent-flaw-materialization
**Areas discussed:** is_opponent representation (+ index), backfill strategy & scope
**Areas locked to recommended default (not contested):** opponent tag fidelity, classify-kernel shape

---

## Pre-discussion: roadmap format fix

The v1.25 milestone roadmap was created in a bullets-only format missing the per-phase
`#### Phase N:` detail sections that GSD tooling parses, so `roadmap.get-phase` / `init.phase-op`
reported phases 113–115 as missing (blocking discuss + plan). Restored the standard
active-milestone format (matching v1.24), content-preserving, committed separately before the
discussion.

---

## Gray areas presented (multiSelect)

User selected **is_opponent index design** and **Backfill recompute & scope**, and via free-text
raised a challenge: *"do we need the is_opponent column, or can we join it from games? If we
benefit from is_opponent via indexing, materialize it."* The two unselected areas (opponent tag
fidelity, classify-kernel shape) were locked to their recommended defaults.

## is_opponent representation

| Option | Description | Selected |
|--------|-------------|----------|
| Materialize, no index | Store NOT NULL bool computed in kernel; no dedicated index; amend FLAWX-03 | |
| Derive via repo helper | No column; single `is_opponent_expr(ply, user_color)` SQL helper; amends FLAWX-01/03 | ✓ |
| Materialize + composite index | Store column AND add a speculative composite index | |

**User's choice:** Derive via repo helper.
**Notes:** Analysis showed the indexing benefit is nil — `is_opponent` is ~50% selective (no
useful standalone index), it is a `GROUP BY` dimension not a selective filter in phase 115, and
the phase-115 query always joins `games` (so `user_color` is free) with `ply` already in the PK.
A Postgres generated column is impossible (cross-table dependency on `games.user_color`). The
only argument for materializing was maintainability (fragile ply→color parity), which a single
tested helper satisfies without denormalizing. User's stated decision rule ("materialize only if
indexing benefits") therefore pointed to derive.

**Consequences captured in CONTEXT.md:** no Alembic migration at all this phase (D-02); no new
index (D-03); and the hidden-scope item — every existing `game_flaws` reader must be retrofitted
with a player-only gate (D-04), since the table stops being player-only-by-construction.

## Backfill strategy & scope

| Option | Description | Selected |
|--------|-------------|----------|
| Wipe+recompute, dev+benchmark in 113 | Full per-game wipe+recompute for dev 28/44 AND benchmark cohort, in this phase | ✓ |
| Dev now, benchmark in 114 | Dev backfill in 113; defer benchmark to start of 114 | |
| Additive opponent-only insert | Only insert missing opponent rows; skip existing | |

**User's choice:** Wipe+recompute, dev+benchmark in 113.
**Notes:** Uses the existing idempotent `delete_flaws_for_game` + `bulk_insert_game_flaws`
(batched at 100). Benchmark must be populated before phase 114 consumes it. Benchmark run flagged
as a longer HUMAN-UAT step. Prod stays empty.

---

## Claude's Discretion

- Exact form/location of `is_opponent_expr` (SQLAlchemy hybrid expression vs `query_utils` helper),
  provided it is the single source of the parity convention and is unit-tested against both
  white-user and black-user games.
- Whether to wrap the expr in `player_only()` / `opponent_only()` convenience helpers for D-04.

## Deferred Ideas

None — discussion stayed within phase scope.
