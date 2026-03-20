# Phase 12: Backend Next-Moves Endpoint - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning

<domain>
## Phase Boundary

A single POST endpoint that aggregates next moves for any position hash with correct W/D/L counts per move, respecting all existing filters and handling transpositions without double-counting. Frontend display (Phase 13) and UI restructuring (Phase 14) are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Response contract
- Dedicated `NextMovesRequest` schema (not extending AnalysisRequest) — same filter fields but no pagination (offset/limit)
- Each move entry includes: `move_san`, `game_count`, `wins`, `draws`, `losses`, `win_pct`, `draw_pct`, `loss_pct`, `result_hash` (resulting position's full_hash as string), `result_fen` (resulting board FEN), `transposition_count`
- Response includes top-level `position_stats` (total games, W/D/L for the queried position) alongside the moves list — avoids a separate /analysis/positions call

### Match side behavior
- Next-moves endpoint uses `full_hash` only — no `match_side` parameter
- Both move aggregation and position_stats use full_hash exclusively
- White/black hash matching doesn't apply to move exploration (it's about exact positions)

### Transposition handling
- `game_count` per move: `COUNT(DISTINCT game_id)` grouped by `move_san` — a game reaching the same position multiple times and playing the same move counts once for that move
- `transposition_count` per move: total distinct games where the resulting position's full_hash appears (via any move order), using the same active filters
- Computed eagerly for all moves in a single batch query (one extra DB round-trip, not lazy on hover)
- Frontend derives "reached via other moves" as `transposition_count - game_count`
- Transposition count respects active filters (consistent with move aggregation)

### Sort and limits
- Default sort: by `game_count` descending (most-played moves first)
- Support `sort_by: 'frequency' | 'win_rate'` parameter, default `frequency`
- No limit on moves returned — return all distinct moves found (positions rarely have >30 legal moves)

### Claude's Discretion
- Exact SQL query structure and optimization approach
- Whether to use CTE, subquery, or separate queries for transposition counts
- Error handling for invalid hash values
- Test structure and fixture design

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Backend patterns
- `app/repositories/analysis_repository.py` — `_build_base_query` filter pattern, DISTINCT dedup approach, HASH_COLUMN_MAP
- `app/services/analysis_service.py` — Service orchestration pattern, `derive_user_result`, `recency_cutoff` helper
- `app/schemas/analysis.py` — Existing schema patterns, BigInt string coercion validator, WDLStats model
- `app/routers/analysis.py` — Router pattern, dependency injection for session + user

### Data model
- `app/models/game_position.py` — GamePosition model with `move_san` column, covering index `ix_gp_user_full_hash_move_san`
- `app/models/game.py` — Game model with all filterable fields

### Requirements
- `.planning/REQUIREMENTS.md` — MEXP-04 (next-moves endpoint), MEXP-05 (transposition handling), MEXP-10 (transposition count)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_build_base_query`: Handles all filter combinations + DISTINCT dedup — can be adapted or extended for next-moves aggregation
- `HASH_COLUMN_MAP`: Maps match_side to hash column — not needed here (full_hash only) but pattern is useful reference
- `WDLStats` schema: Reusable for position_stats in the response
- `derive_user_result`: Converts PGN result + user_color to win/draw/loss — needed for W/D/L computation
- `recency_cutoff` helper: Converts recency string to datetime cutoff — reuse directly
- BigInt string coercion `field_validator`: Copy pattern for `target_hash` in NextMovesRequest

### Established Patterns
- Repository → Service → Router layering (no SQL in services, no business logic in routers)
- All filter parameters passed explicitly (no kwargs/dict spreading)
- DISTINCT by game_id to prevent transposition double-counting
- POST for query endpoints (body carries filter payload)

### Integration Points
- New endpoint registers on the existing `analysis` router at `POST /analysis/next-moves`
- Uses same `get_async_session` and `current_active_user` dependencies
- Covering index `ix_gp_user_full_hash_move_san` already exists for the primary aggregation query

</code_context>

<specifics>
## Specific Ideas

- Inspired by openingtree.com and lichess explorer — frequency-first move ordering is the standard
- Support both frequency and win_rate sorting now (not waiting for MEXP-08) since it's trivial at the SQL level
- Include result_hash and result_fen per move so the frontend can navigate without recomputing hashes

</specifics>

<deferred>
## Deferred Ideas

- Alphabetical sort option — excluded from sort_by for now, add if needed later
- MEXP-09: Show resulting position FEN/thumbnail on move hover — Phase 13 frontend concern (result_fen is already in the response)

</deferred>

---

*Phase: 12-backend-next-moves-endpoint*
*Context gathered: 2026-03-16*
