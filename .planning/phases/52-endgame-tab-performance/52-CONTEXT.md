# Phase 52: Endgame Tab Performance - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning
**Source:** In-session diagnosis following user-testing incident 2026-04-10

<domain>
## Phase Boundary

Make the Endgames tab load fast under concurrent production load, WITHOUT changing the endgame analytics algorithms or schema. Three tactical fixes:

1. **Backend — collapse timeline fan-out.** `query_endgame_timeline_rows` currently runs 8 sequential queries against `game_positions` (1 overall endgame + 1 non-endgame + 6 per-class). Replace with 2 queries total.
2. **Backend — consolidate endgame endpoints.** `/api/endgames/stats`, `/performance`, `/timeline`, `/conv-recov-timeline` are 4 separate endpoints that the frontend fires in parallel on every filter change, each on its own DB session. Consolidate into one overview endpoint that runs all internal queries sequentially on a single session. `/games` remains separate.
3. **Frontend — defer desktop filter apply.** Desktop Endgames tab fires queries on every filter keystroke. Mobile already defers apply until the filter sidebar closes. Replicate the mobile pattern on desktop so changes to pending filter state do not trigger backend queries until the user explicitly applies.

Out of scope: materialized `endgame_spans` table, any schema changes, any changes to endgame classification/persistence logic, any changes to other tabs.

</domain>

<decisions>
## Implementation Decisions

### Backend — Query Consolidation (LOCKED)
- `query_endgame_timeline_rows` must run ≤2 queries against `game_positions`: one grouped by `endgame_class` returning per-class rows in a single pass, and one for non-endgame rows. The current 8-query sequential loop (`app/repositories/endgame_repository.py:512-522`) must be removed.
- Per-class result rows must include the `endgame_class` column so the service can bucket them into the dict shape `per_type_rows` that the current interface returns.
- A single new overview endpoint (working name `/api/endgames/overview`) returns the combined payload for stats, performance, timeline, and conv-recov-timeline. Keep all four response models; just serve them together.
- The new endpoint runs its internal queries sequentially on one `AsyncSession`. Never `asyncio.gather` on the same session. Follow the existing pattern comments in `endgame_repository.py:423-428`.
- `/api/endgames/games` remains an independent endpoint — it changes when the user picks a different endgame class, which is orthogonal to the overview filters.
- The legacy endpoints (`/stats`, `/performance`, `/timeline`, `/conv-recov-timeline`) should be removed once the overview endpoint is in place. No frontend code should still call them after this phase. Backward compatibility is not required — there are no external API consumers.

### Frontend — Deferred Filter Apply (LOCKED)
- Desktop Endgames tab must NOT fire backend queries on filter state changes. Queries only fire when the filter sidebar is closed/applied.
- Reuse the existing mobile deferred-apply pattern — do not invent a new mechanism. Search for the existing "pending filter" / "applied filter" state split used by the mobile Openings drawer (see v1.6 accomplishment: "Mobile drawer sidebars for filters and bookmarks with deferred filter apply on close") and apply the same pattern to the desktop Endgames filter sidebar.
- The `gamesData` (endgame class selector) should remain immediate — it's not a sidebar filter.
- Mobile Endgames tab continues to use its existing deferred behavior unchanged.

### What is NOT changing (LOCKED)
- No new tables, no new columns, no new indexes, no migrations.
- No changes to `query_endgame_entry_rows`, `query_endgame_performance_rows`, or `query_conv_recov_timeline_rows` internals — their `GROUP BY + array_agg` aggregations stay as-is. Only `query_endgame_timeline_rows` gets rewritten.
- No changes to any endgame classification logic, persistence filter, or material imbalance thresholds.
- No changes to chess.com / lichess import pipeline.
- No changes to React Query stale time / caching config.

### Claude's Discretion
- Exact name of the consolidated endpoint (`/overview`, `/bundle`, `/all` — planner picks).
- Whether to combine the per-class and non-endgame timeline queries into a single SQL statement via UNION ALL, or keep them as two separate queries on the same session (both satisfy criterion 1).
- Exact shape of the desktop pending-filter state (reuse whatever helper the mobile drawer uses).
- Whether loading state is a single spinner or per-chart placeholders during the consolidated fetch.
- Whether to remove or deprecate the legacy individual endpoints (removal preferred per Decisions above).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Backend — Endgame query layer
- `app/repositories/endgame_repository.py` — contains `query_endgame_timeline_rows` (the 8-query offender), `query_endgame_entry_rows`, `query_endgame_performance_rows`, `query_conv_recov_timeline_rows`. Note the comments at lines 423-428 and 512-522 explaining why `asyncio.gather` is forbidden.
- `app/routers/endgames.py` — the 5 endpoints that currently fan out. `/stats`, `/performance`, `/timeline`, `/conv-recov-timeline` are the consolidation targets; `/games` stays separate.
- `app/services/endgame_service.py` — service layer between routers and repository; shapes response models from the raw rows.
- `app/schemas/endgames.py` — response model definitions (`EndgameStatsResponse`, `EndgamePerformanceResponse`, `EndgameTimelineResponse`, `ConvRecovTimelineResponse`). The consolidated endpoint reuses these as fields of a wrapper model.
- `app/repositories/query_utils.py` — `apply_game_filters()`, the single source of truth for time control / platform / rated / opponent type / recency / opponent strength filter SQL. Do not duplicate.

### Frontend — Endgame tab and filter state
- `frontend/src/pages/Endgames.tsx` — hosts the 5 useQuery hooks at lines 69-73 and the filter state. This is where deferred apply needs to land on desktop.
- `frontend/src/hooks/useEndgame*.ts` (or equivalent — planner should locate them from `useEndgameStats`, `useEndgamePerformance`, `useEndgameTimeline`, `useEndgameConvRecovTimeline`, `useEndgameGames` imports). The hooks need to switch from per-endpoint to one overview hook.
- `frontend/src/api/client.ts` — API client functions for the endgame endpoints. Add new overview function, remove legacy ones.
- Reference pattern: existing mobile deferred-filter-apply implementation from v1.6 (mobile drawer sidebars). Planner must find the exact file and replicate on desktop.

### Roadmap entry
- `.planning/ROADMAP.md` Phase 52 section — canonical goal and 9 success criteria.

### CLAUDE.md constraints
- `/home/aimfeld/Projects/Python/flawchess/CLAUDE.md` — router convention (prefix-based), shared query filters rule, forbidden `asyncio.gather` on `AsyncSession`, ty type-check must pass, knip must pass, mobile parity rule ("Always apply changes to mobile too").

### Production diagnostic data (2026-04-11)
The 2026-04-11 user-testing incident root cause analysis (in session) found:
- `pg_stat_statements` on prod shows endgame queries averaging 150–478 seconds per call under concurrent load.
- EXPLAIN ANALYZE on the biggest user (user 13, 20,933 games, 781,282 endgame positions) runs the same query in 443 ms with optimal `Index Only Scan` + `GroupAggregate`. The index `ix_gp_user_endgame_game` with `INCLUDE(material_imbalance)` is already optimal.
- The 1000× gap is explained by concurrent fan-out (5 parallel HTTP requests × ~15 heavy GROUP BYs) on a 4 vCPU / 7.6 GB RAM Hetzner VPS, causing work_mem and buffer contention (swap was added after an earlier OOM — see STATE.md blockers).
- Cache hit ratio is 99.86% under normal load; no index rework needed.
- Sentry FLAWCHESS-24 (AxiosError Network Error on `/login` userProfile) is a downstream symptom, not a separate bug.

</canonical_refs>

<specifics>
## Specific Ideas

- Timeline consolidation via `GROUP BY game_id, endgame_class` at the outer level, then letting the service split rows by `endgame_class` value — cleaner than `UNION ALL` of 6 class-specific queries.
- The consolidated endpoint's Pydantic response model can simply compose existing models, e.g. `class EndgameOverviewResponse(BaseModel): stats: EndgameStatsResponse; performance: EndgamePerformanceResponse; timeline: EndgameTimelineResponse; conv_recov_timeline: ConvRecovTimelineResponse`. No new field shapes.
- Desktop deferred-filter pattern might live in `useDeferredFilters` or similar — or might be inline in the mobile drawer component. Planner must locate and not duplicate.
- Verification step should re-query `pg_stat_statements` from the production DB via MCP after deploy to confirm the old query patterns drop out of the top offenders list, using the biggest user (user 13) as the benchmark.

</specifics>

<deferred>
## Deferred Ideas

- **Materialized `endgame_spans` table** — the "biggest win" fix from the diagnosis. Explicitly deferred by the user on 2026-04-11 because "the algorithms for endgame analysis will likely change soon anyway". Do not implement in this phase. May become a future phase once endgame algorithms stabilize.
- **Server RAM upgrade (7.6 GB → 16 GB)** — also flagged in the diagnosis as a stopgap. Not part of this phase; infra decision, not code.
- **FastAPI-Users `FOR KEY SHARE` seq scans** — 52M calls on the users table surfaced during the DB report. Unrelated to endgame performance; flagged for a later phase.

</deferred>

---

*Phase: 52-endgame-tab-performance*
*Context gathered: 2026-04-11 from in-session diagnosis (no discuss-phase run)*
