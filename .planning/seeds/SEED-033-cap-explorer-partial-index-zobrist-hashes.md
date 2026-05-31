---
id: SEED-033
status: dormant
planted: 2026-05-31
planted_during: /gsd-explore session on Zobrist hash storage/index cost
trigger_when: next backend DB storage/performance maintenance phase, OR when game_positions index footprint becomes a prod concern (the 3 hash indexes total ~4.8 GB)
scope: phase (single, backend + small frontend cap)
---

# SEED-033: Cap move explorer at ply 28 + partial-index the Zobrist hashes

> **One-line:** The three Zobrist-hash indexes on `game_positions` are ~4.8 GB and only matter for opening-depth positions. Hard-cap the move explorer at ply 28 and rebuild the hash indexes as partial (`WHERE ply <= 28`) to reclaim ~3 GB with zero data loss and no table rewrite.

## Why This Matters

`game_positions` carries three Zobrist hashes per row (`full_hash`, `white_hash`, `black_hash`) and three indexes built on them:

| Index | Size |
|---|---|
| `ix_gp_user_full_hash_move_san` | 2,210 MB |
| `ix_gp_user_white_hash` | 1,303 MB |
| `ix_gp_user_black_hash` | 1,294 MB |
| **Total** | **~4.8 GB** |

These hashes are only ever queried for **opening-phase position matching** (explorer, opening insights, bookmarks, system-opening filter). Past the opening, positions diverge and the hashes are dead weight in the index. Capping the indexed range to opening depth reclaims most of that footprint.

## The Decision (settled during exploration)

### 1. Cut on **ply**, NOT `phase`

The original idea was `NULL the hashes WHERE phase != 0`. **Rejected — empirically unsafe.**

`phase` uses Lichess Divider semantics (material/structure-based, monotonic), not depth. Openings that simplify early (Berlin endgame, Exchange Slav/QGD, French Exchange queen trades) get stamped `phase=1`/`phase=2` while still being heavily-played opening theory. Measured on dev DB:

- Within ply ≤ 24 (our `openings` book p99), **15.3% of positions are `phase != 0`** (690k middlegame rows + 446 endgame rows).
- Under `WHERE phase != 0 → wipe`, those get destroyed → e.g. a user with 50 Berlin games would show **0** games through the Berlin tabiya, silently undercounting WDL on a core feature.

So the cutoff must be **ply-based** (aligned with what the explorer queries), not phase-based.

### 2. Boundary = **ply 28**

Theory depth, from FlawChess's own `openings` table (`ply_count`):

| Metric | Ply |
|---|---|
| Median | 9 |
| p90 | 16 |
| p95 | 19 |
| p99 | 24 |
| Max | 36 |

External corroboration: ECO's named-position ceiling is **28 plies**; only elite forcing lines (Najdorf Poisoned Pawn, Botvinnik Semi-Slav, Marshall) run deeper, and those live at ply 40-80 so no practical cutoff catches them.

- **ply ≤ 16** under-captures — drops the entire p90→p99 tail (10% of the book).
- **ply ≤ 24** captures p99 of our book (32.4% of all position rows).
- **ply ≤ 28** captures the full ECO ceiling + headroom (37.4% of rows). Chosen: removes any "did we clip theory?" doubt for ~5pp more index rows than 24.

### 3. **Hard-cap the move explorer at ply 28** (the enabling move)

Today the explorer can go arbitrarily deep, and bookmarks can be set at any reached position — so an unbounded `full_hash.in_(hashes)` lookup *could* hit a position only present past the cap (late transposition), which would change query semantics under a partial index.

Capping the explorer at ply 28 **dissolves that risk entirely**: if the explorer can't reach past the cap, no query ever looks up a hash past it, so the partial-index boundary and the explorer cap become the same number and the win is unconditional across all three hashes. In practice the user almost never goes above ply 16, so the cap is invisible. (Dev DB: 35 bookmarks, **max depth 6 plies**, zero past 24.)

### 4. **Keep the columns — do NOT NULL them**

Index-only win is fully reversible, needs no `VACUUM FULL`/`pg_repack`, and doesn't foreclose a future middlegame-position feature. NULLing the columns would only reclaim heap (~24 B × ~63% of rows), marginal next to the ~3 GB index win and not worth the irreversibility.

## Implementation Sketch

- **Shared constant** `MAX_EXPLORER_PLY = 28` as the single source of truth, used by *both* the explorer cap and the index `WHERE` predicate. They MUST stay equal — if the cap ever exceeds the index boundary, queries past the boundary silently miss the index. (Constant lives backend-side; frontend explorer cap reads/mirrors it.)
- **Frontend:** hard-cap the move explorer at `MAX_EXPLORER_PLY` plies (indirectly caps bookmark creation depth).
- **Alembic migration:** rebuild the three hash indexes as partial `WHERE ply <= 28`:
  - `ix_gp_user_full_hash_move_san` (user_id, full_hash, move_san)
  - `ix_gp_user_white_hash` (user_id, white_hash)
  - `ix_gp_user_black_hash` (user_id, black_hash)
  - Use `CREATE INDEX CONCURRENTLY` then drop old — the 14M-row table (prod larger) can't take an `ACCESS EXCLUSIVE` lock during business hours. Note: `CONCURRENTLY` cannot run inside Alembic's default transaction; mark the migration non-transactional / use raw connection.
- **Query predicates:** each hash query in `app/repositories/stats_repository.py`, `app/services/openings_service.py`, and `app/repositories/position_bookmark_repository.py` must add `AND ply <= 28` so the planner picks the partial index. (`opening_insights` scan is already bounded by `ix_gp_user_game_ply WHERE ply BETWEEN 0 AND 17`.)
- **Pre-migration prod check:** confirm no bookmarks past the cap before shipping (dev has none; verify prod via tunnel). If any exist, decide: leave their occurrences uncounted (degraded) or grandfather.

## Estimated Win

- Index footprint: ~4.8 GB → ~1.8 GB (**~3 GB reclaimed**) at ply ≤ 28.
- No heap rewrite, no data loss, reversible (drop partial indexes, recreate full ones to roll back).

## Secondary Lever (out of scope for first cut)

Stop *computing/storing* hashes past the cap at import time (make the hash columns nullable, populate only ≤ cap). Shrinks heap on all future imports for free, but is more invasive (relaxes `NOT NULL`, touches the import path + reclassify/reimport scripts). Defer unless heap size becomes a separate concern.

## Open / To Confirm at Plan Time

- Final cap value: 28 (recommended) vs 24 (cheaper by ~5pp of rows). Plan should re-confirm against the latest `openings.ply_count` max.
- Whether `white_hash`/`black_hash` (system-opening "my pieces only" filter) want a *deeper* boundary than `full_hash` — resolved to "no" given the unified explorer cap, but re-verify the system-filter UX doesn't surface positions past the cap independently of the explorer.
