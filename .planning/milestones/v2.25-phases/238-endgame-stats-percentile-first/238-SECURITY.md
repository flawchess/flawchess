---
phase: "238"
slug: "endgame-stats-percentile-first"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-11"
---

# Phase 238 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| client → `GET /api/endgames/ranked-stats` | Authenticated, filter-free ranked payload | user_id from auth only; per-user game aggregates |
| client → `GET /api/endgames/stats` | Authenticated, filtered per-category stats for the Games tab | typed filter query params → bound SQL expressions |
| client → `POST /api/insights/endgame`, `GET /api/insights/endgame/cached` | Filter-free LLM report and its per-user cache | user_id from auth only; cached report text |
| repository → PostgreSQL | Ranked-sample SQL with interpolated TC literal and bound params | user_id, game id arrays |
| browser `localStorage` | Remembered Stats TC choice (`endgame_stats_tc`) | user-writable enum value |
| browser → Umami | Feature events for the TC switch and peer rows | enumerated literals only |
| dev browser session (UAT) | UAT against the local dev stack and dev DB | dev data reads, one insights generate |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-238-01 | Tampering | ranked_games_sql / fetch_ranked_games | high | mitigate | `ranked_games_sql(tc: TimeControlBucket)` interpolates only the 4-value Literal; user_id via `CAST(:user_id AS int)` bindparam (app/services/canonical_slice_sql.py:323, :40) | closed |
| T-238-02 | Information disclosure | GET /ranked-stats, repository queries | high | mitigate | user_id from `current_active_user`; `test_ranked_stats_two_user_isolation` (tests/services/test_endgame_ranked_parity.py:571) green in 238-09 | closed |
| T-238-03 | Denial of service | on-read computation for heavy accounts | medium | mitigate | `RECENT_GAMES_PER_TC_CAP = 3000` (canonical_slice_sql.py:126); measured medians 441 ms / 1049 ms (users 7 / 14) | closed |
| T-238-04 | Tampering | apply_game_filters game_ids | medium | mitigate | `game_ids_any_predicate`: one bound `ARRAY(Integer)` param with `= ANY`, keyword-only, default None (app/repositories/query_utils.py:153-203) | closed |
| T-238-05 | Tampering | GET /endgames/stats query params | medium | mitigate | Typed FastAPI Query params into `apply_game_filters`; `from_date > to_date` → 422; user from `current_active_user` (app/routers/endgames.py) | closed |
| T-238-06 | Denial of service | per-TC timeline/clock aggregation | medium | mitigate | Same 3000-per-TC cap and inner id push; latency recorded in 238-02 and 238-09, below the 2 s flag | closed |
| T-238-07 | Tampering | useEndgameStatsTc localStorage read | low | mitigate | `isTimeControlBucket` guard, read/write in try/catch, fallback to the D-12 default (frontend/src/hooks/useEndgameStatsTc.ts) | closed |
| T-238-08 | Information disclosure | analytics events | low | mitigate | Typed registry: `endgame-stats-tc` (value: TimeControlBucket) and `endgame-peer-row` only (frontend/src/lib/analytics.ts) | closed |
| T-238-09 | Tampering | rendering payload text | low | accept | React escapes text; no `dangerouslySetInnerHTML` in the endgame or insights components | closed |
| T-238-10 | Information disclosure | cached report lookup | high | mitigate | `LlmLog.user_id == user_id` first key (app/repositories/llm_log_repository.py:202); `test_other_users_log_not_returned` green, mutation-checked in 238-04 | closed |
| T-238-11 | Elevation of privilege | removed filter gate | low | accept | No filter params accepted; extra params ignored and produce the same report | closed |
| T-238-12 | Denial of service / cost | repeated Generate clicks | medium | mitigate | Per-user structural cache is checked before any LLM call (`generate_insights`, app/services/insights_llm.py), so repeat clicks are cache hits. Note: the plan's "existing insights rate limiter" does not exist (none before or after this phase); the cache is the actual bound | closed |
| T-238-13 | Tampering | prompt content | low | accept | Prompt holds numbers, enumerated ids and server-built labels only | closed |
| T-238-14 | Tampering | rendering numeric payload in charts/tables | low | accept | React/Recharts text nodes; authenticated, user-scoped numeric values | closed |
| T-238-15 | Repudiation / analytics integrity | removed accordion events | low | accept | Old PANEL_TARGETS entries kept registered (no rename) | closed |
| T-238-16 | Information disclosure | removed GET /endgames/overview | low | mitigate | Route deleted; `test_overview_returns_404` (tests/test_endgames_router.py:175) green | closed |
| T-238-17 | Tampering | hidden filter UI | low | mitigate | Hiding never commits drafts or calls the applied-filter setter; `Endgames.filterVisibility.test.tsx` green; browser UAT confirmed the applied filter survives a Stats round trip | closed |
| T-238-18 | Denial of service / cost | Generate button without filter reset | low | accept | Per-user structural cache unchanged (see T-238-12) | closed |
| T-238-19 | Tampering | dev database during UAT | medium | mitigate | No reset or destructive script run; UAT read data and generated one report | closed |
| T-238-20 | Denial of service (availability) | retirement sweep deletions | low | mitigate | Importer grep before `git rm`; knip, lint, build and full tests green after (238-06) | closed |
| T-238-21 | Information disclosure | deleted chip-decoupling V4 scoping test | medium | mitigate | Deletion gated on `test_ranked_stats_two_user_isolation` passing; still green in 238-09 | closed |
| T-238-SC | Tampering | npm/pip/cargo installs | low | accept | No new packages; executors ran `npm ci` / `uv sync` from the existing lockfiles only | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-238-01 | T-238-09 | React escapes all rendered text; no raw HTML path added | plan-time threat model (238-03) | 2026-10-11 |
| AR-238-02 | T-238-11 | Nothing to bypass once filters are not accepted | plan-time threat model (238-04) | 2026-10-11 |
| AR-238-03 | T-238-13 | No user free text reaches the prompt | plan-time threat model (238-04) | 2026-10-11 |
| AR-238-04 | T-238-14 | Numeric, user-scoped values rendered as text | plan-time threat model (238-05) | 2026-10-11 |
| AR-238-05 | T-238-15 | Analytics history preserved by keeping old targets registered | plan-time threat model (238-05) | 2026-10-11 |
| AR-238-06 | T-238-18 | Cost bounded by the per-user cache | plan-time threat model (238-07) | 2026-10-11 |
| AR-238-07 | T-238-SC | No dependency changes in this phase | plan-time threat model (all plans) | 2026-10-11 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-11 | 22 | 22 | 0 | execute-phase orchestrator (L1 grep-depth; auditor skipped per short-circuit rule) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-11
