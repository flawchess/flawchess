---
phase: "242"
slug: "openings-stats-insights-rework"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-17"
---

# Phase 242 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Browser → `/stats`, `/insights/openings`, `/openings/*` | Authenticated API calls for the user's own repertoire, findings and time series | User-scoped game aggregates; `user_id` only from `current_active_user` |
| `X-Dev-Now` header → `dev_now_utc` | Dev clock override shifting the current-repertoire cutoff | Timestamp; honoured only when `ENVIRONMENT == "development"` |
| Frontend → Umami | Analytics events for colour switch, popovers, panel opens | Registered literal targets and indices only, never SAN/FEN/opening names |
| Frontend → localStorage | One-time sweep of retired bookmark chart toggle keys | Fixed key prefix only |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-242-01 | Information disclosure | `query_nth_recent_played_at`, bookmark full-hash load | medium | mitigate | `Game.user_id == user_id` + `apply_game_filters` in `stats_repository.query_nth_recent_played_at`; bookmarks via `get_bookmarks(session, user_id)` | closed |
| T-242-02 | Tampering | dev clock shifting the cutoff | low | mitigate | `NowUtc = Depends(dev_now_utc)` in `app/routers/stats.py`; header gated on `ENVIRONMENT == "development"` in `app/core/dev_clock.py` | closed |
| T-242-03 | Denial of service | most-played pipeline + second fetch | medium | mitigate | second fetch only when `cutoff is not None and _needs_recent_fallback(...)` (`stats_service.py:648`); eval batch only on survivors | closed |
| T-242-04 | Repudiation/Info | Sentry capture for non-replayable bookmark | low | mitigate | `sentry_sdk.set_context("bookmark", {...})` then `capture_exception` (`stats_service.py:442`) | closed |
| T-242-05 | Information disclosure | insights cutoff + findings queries | medium | mitigate | `OpeningInsightsRequest` `ConfigDict(extra="forbid")`; `resolve_current_cutoffs` user-scoped | closed |
| T-242-06 | Denial of service | insights eval enrichment | medium | mitigate | `FINDINGS_CARD_CAP = 5`; enrichment on card findings only (`opening_insights_service.py`) | closed |
| T-242-07 | Tampering | dev clock header (insights) | low | mitigate | `NowUtc = Depends(dev_now_utc)` in `app/routers/insights.py` | closed |
| T-242-08 | Information disclosure | `query_time_series` for arbitrary hash | medium | mitigate | `GamePosition.user_id == user_id` in `openings_repository.query_time_series` | closed |
| T-242-09 | Tampering | dev clock header (openings) | low | mitigate | `NowUtc = Depends(dev_now_utc)` in `app/routers/openings.py` | closed |
| T-242-10 | Denial of service | extra cutoff queries per time-series request | low | accept | see Accepted Risks | closed |
| T-242-11 | Information disclosure | Umami eval popover target | low | mitigate | fixed literal `eval-bullet-popover-trigger` in `PositionResultsPanel.tsx` | closed |
| T-242-12 | Tampering | rendering of API numbers | low | accept | see Accepted Risks | closed |
| T-242-13 | Information disclosure | Umami option-change payload | low | mitigate | `{ target: 'opening-stats-color'; value: 'white' \| 'black' }` in `analytics.ts` | closed |
| T-242-14 | Tampering | localStorage sweep | low | mitigate | fixed `RETIRED_BOOKMARK_CHART_KEY_PREFIX`; storage access in `try/catch` (`retiredLocalStorage.ts`) | closed |
| T-242-15 | Tampering (XSS) | bookmark labels in table rows | low | mitigate | React text nodes; no `dangerouslySetInnerHTML` under openings/charts components | closed |
| T-242-16 | Information disclosure | Umami popover targets (table) | low | mitigate | `${testId}-score-info` / `-eval-info` with index-based testIds (`RepertoireTable.tsx`) | closed |
| T-242-17 | Information disclosure | Umami targets for findings | low | mitigate | registered literals `opening-findings-unclear`, `opening-insights-more` (`OpeningFindings.tsx`) | closed |
| T-242-18 | Tampering (open redirect) | legacy `/insights` redirect | low | mitigate | `<Navigate to="/openings/stats" replace />` fixed internal path (`Openings.tsx`) | closed |
| T-242-19 | Information disclosure | lazy row series request | low | mitigate | backend user scoping (T-242-08) | closed |
| T-242-20 | Elevation of privilege | Remove bookmark from expanded row | low | mitigate | `get_bookmark` filters `PositionBookmark.user_id == user_id` | closed |
| T-242-21 | Denial of service | many expanded rows fetching series | low | accept | see Accepted Risks | closed |
| T-242-SC | Tampering | npm/pip/cargo installs | high | accept | no package installs in any plan | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-242-01 | T-242-10 | At most two indexed cutoff queries (~3 ms each on the heaviest dev user) per time-series request | plan 242-03 | 2026-10-17 |
| AR-242-02 | T-242-12 | API numbers render through auto-escaped React text nodes | plan 242-04 | 2026-10-17 |
| AR-242-03 | T-242-21 | Row series fire only on user expansion, one per row, cached by TanStack Query | plan 242-09 | 2026-10-17 |
| AR-242-04 | T-242-SC | No package installs in this phase; nothing to verify | plans 242-01..09 | 2026-10-17 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-17 | 22 | 22 | 0 | secure-phase (L1 grep verification, execute-phase verify:post) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-17
