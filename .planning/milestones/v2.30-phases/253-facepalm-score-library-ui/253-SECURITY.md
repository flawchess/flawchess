---
phase: "253"
slug: "facepalm-score-library-ui"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-14"
---

# Phase 253 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| browser to API | two new integer query params on authenticated list endpoints | untrusted `min_facepalm_pct` / `max_facepalm_pct` |
| API to DB | the params become bound thresholds in the shared flaw predicate | float thresholds |
| API to browser | `facepalm_score` rendered on the flaw card | the user's own 0..1 score |
| browser to Umami | filter-change and popover-open events | preset key, id-free target |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-253-01 | Tampering | `min_facepalm_pct` / `max_facepalm_pct` | low | mitigate | typed `int` with `Query(ge=FACEPALM_PCT_MIN, le=FACEPALM_PCT_MAX)` on both endpoints (`app/routers/library.py:77-86,339-348`); values reach SQL only as SQLAlchemy comparisons with bound floats (`app/repositories/library_repository.py:347-351`); 422 tests in `tests/test_library_router.py` | closed |
| T-253-02 | Information disclosure | `_facepalm_clause` in `build_flaw_filter_clauses` | medium | mitigate | the clause is appended inside `build_flaw_filter_clauses` (`library_repository.py:736`), whose two callers scope by `GameFlaw.user_id == user_id` and `player_only_gate` (`:818-819`, `:1215-1219`); `apply_game_filters` raises without a user_id (`app/repositories/query_utils.py:414-418`); opponent-ply exclusion tested on both endpoints. Residual: no test seeds another user's scored flaw (review IN-05, open, info) | closed |
| T-253-03 | Information disclosure | `FlawListItem.facepalm_score` | low | mitigate | read from rows already owner-scoped by `query_flaws` (`library_repository.py:1070`, `app/schemas/library.py:241`) | closed |
| T-253-04 | Denial of service | unindexed REAL comparison on `game_flaws` | low | accept | see Accepted Risks | closed |
| T-253-05 | Information disclosure | `FacepalmFilter` Umami events | low | mitigate | `FilterChangeProps` admits only `FacepalmPreset \| 'custom'` (`frontend/src/lib/analytics.ts:485`); handlers send `derivePreset(...) ?? 'custom'` (`frontend/src/components/filters/FacepalmFilter.tsx:66,78`); tracking tests in `FlawFilterControl.test.tsx` | closed |
| T-253-06 | Tampering | crafted params from a modified client | low | accept | see Accepted Risks | closed |
| T-253-07 | Information disclosure | `FacepalmBadgePopover` Umami tracking | low | mitigate | testid `facepalm-badge-{gameId}-{ply}` (`frontend/src/components/library/FacepalmChip.tsx:23`, moved out of SeverityBadge by the UAT redesign) normalized to `facepalm-badge` by `useTrackedPopoverOpen`; tracking test asserts the id-free target | closed |
| T-253-08 | Tampering | rendering `facepalm_score` | low | mitigate | `toFacepalmPct` floors and clamps to 0..100 (`frontend/src/lib/facepalm.ts:141-144`); rendered as React text, no `dangerouslySetInnerHTML` in the new components | closed |
| T-253-09 | Information disclosure | `FlawMarker.facepalm_score` (UAT redesign, D-22) | low | accept | see Accepted Risks. The marker is null unless the live severity is blunder (`app/services/library_service.py`, `_build_eval_series`) | closed |
| T-253-SC | Tampering | npm/pip/cargo installs | low | accept | see Accepted Risks | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-253-01 | T-253-04 | residual filter on rows already narrowed by user_id and the game join; same cost class as the tactic depth filter, no new index | plan 253-01 threat model | 2026-11-14 |
| AR-253-02 | T-253-06 | the server rejects anything outside 0..100 with 422; an inverted range only returns the user's own empty result | plan 253-02 threat model | 2026-11-14 |
| AR-253-04 | T-253-09 | `GET /library/games/{game_id}` is deliberately not owner-scoped, so a logged-in non-owner who opens the game sees the owner's facepalm scores on its blunder markers. Consistent with what that endpoint already exposes (evals, flaws, tactics of the game) | owner | 2026-11-14 |
| AR-253-03 | T-253-SC | no package manifest or lockfile changed in the phase diff | plans 253-01..03 threat models | 2026-11-14 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-14 | 9 | 9 | 0 | orchestrator (secure-phase, ASVS L1 grep-depth) |
| 2026-11-14 | 10 | 10 | 0 | orchestrator (after the UAT redesign: T-253-09 added and accepted by the owner, T-253-07 location updated) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-14
