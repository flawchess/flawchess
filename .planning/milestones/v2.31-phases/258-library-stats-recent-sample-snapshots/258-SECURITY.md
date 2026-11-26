---
phase: "258"
slug: "library-stats-recent-sample-snapshots"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-21"
---

# Phase 258 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

The register was authored at plan time (all five plans carry a `<threat_model>` block). This audit
verified each mitigation at ASVS level 1 (grep depth) against the implementation; it did not scan
for new threats. All five SUMMARY files report "Threat Flags: None".

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| client -> GET /api/library/flaw-comparison, /facepalm-comparison, /tactic-comparison | Authenticated (`current_active_user`), existing validated filters, no new query parameter | The user's own game and flaw aggregates |
| dev clock header -> `dev_now_utc` | `X-Dev-Clock-Offset-Minutes` shifts "now" only when `ENVIRONMENT == "development"` | A time offset |
| window ids -> bound `int[]` parameter | Ids come from this request's own window statement, never from the request | Game ids of the authenticated user |
| API payload -> Stats tab | Renders the user's own windowed counts; no new request | Counts and dates |
| Sidebar filter store -> Stats tab copy | The quiet message reads filter state to pick a qualifier; it never writes | Local UI state |
| UI -> Umami | No new event; new testids are static strings | None |
| operator script -> prod database | Read-only transactions over the prod tunnel, orchestrator only | Timings and plans |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-258-01 | Information disclosure | `fetch_recent_window_rows`, `_analyzed_game_ids_subquery(game_ids=)` | high | mitigate | `Game.user_id == user_id` in the window predicates (`app/repositories/library_repository.py:2150`) on top of the user-scoped filtered base; the restricted subquery keeps `Game.user_id == user_id` (`:1925`); `tests/services/test_library_window.py::test_two_user_isolation` | closed |
| T-258-02 | Denial of service | Window statement on every Stats load | medium | mitigate | `Game.played_at >= window_start` bound (`:2160`), `rn <= cap` with `RECENT_GAMES_PER_TC_CAP` (`:2187`); prod timing gate passed (UAT test 4, D-18) | closed |
| T-258-03 | Tampering | SQL composition of the window | low | mitigate | SQLAlchemy expressions and bound parameters only; the single `text()` in the file is the constant `SET LOCAL jit = off` (`:1688`) | closed |
| T-258-04 | Spoofing | Forged dev-clock header in production | low | accept | `dev_now_utc` returns real UTC unless `ENVIRONMENT == "development"` (`app/core/dev_clock.py:68`) | closed |
| T-258-05 | Information disclosure | Windowed facepalm and tactic fetches | high | mitigate | Both read the user-scoped `_fetch_recent_window`; `GameFlaw.user_id == user_id` kept on the inner scans; `test_facepalm_two_user_isolation` and `test_tactic_comparison_service.py::test_two_user_isolation` run on the windowed services | closed |
| T-258-06 | Denial of service | JIT compile on the window statement in the facepalm transaction | medium | mitigate | `disable_jit_for_transaction` awaited before the window statement (`app/services/library_service.py:2121`); prod EXPLAIN in plan 04 showed no need on the flaw and tactic paths | closed |
| T-258-07 | Information disclosure | Quiet-state message, caption, popover basis | low | accept | Copy shows only the user's own counts from the existing authenticated payload | closed |
| T-258-08 | Tampering | Analytics targets derived from testids | low | mitigate | `flaw-stats-no-recent` (`LibraryStatsSections.tsx:275`) and `flaw-trend-caption` (`FlawTrendChart.tsx:175`) are static literals on non-interactive elements, not InfoPopover testIds | closed |
| T-258-09 | Information disclosure | Prod timings and plans printed by the timing script | medium | mitigate | Script and outputs live under gitignored `temp/library-258/` (`.gitignore:5`, nothing under `temp/` is tracked); read-only transactions | closed |
| T-258-10 | Denial of service | Measurement load on prod | low | mitigate | One connection, foreground run by the orchestrator (258-04 SUMMARY) | closed |
| T-258-11 | Tampering | Gate auto-fixes changing behaviour | low | accept | Deterministic formatters; full suite runs after them in the same gate | closed |
| T-258-12 | Tampering | `flaw-stats-no-recent` message (shared filter store) | low | mitigate | Two plain `<p>` elements, no button; the component test asserts zero buttons inside the message (`LibraryStatsSections.test.tsx:700`) | closed |
| T-258-13 | Information disclosure | Quiet message qualifier | low | accept | States only that a non-default filter is active, from local filter state; no new request or event | closed |
| T-258-SC | Tampering | npm/pip installs | low | accept | No dependency or lockfile change on the phase branch versus `main` | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-258-01 | T-258-04 | The dev clock is fail-closed outside development, and the window only reads the user's own games | Plan 258-01 (plan-time disposition) | 2026-11-21 |
| AR-258-02 | T-258-07 | Only the user's own counts are shown; nothing new leaves the browser | Plan 258-03 (plan-time disposition) | 2026-11-21 |
| AR-258-03 | T-258-11 | Formatters are deterministic and the full suite runs after them | Plan 258-04 (plan-time disposition) | 2026-11-21 |
| AR-258-04 | T-258-13 | The qualifier reveals only local filter state to the user who set it | Plan 258-05 (plan-time disposition) | 2026-11-21 |
| AR-258-05 | T-258-SC | No package installed or updated in this phase | Plans 258-01 to 258-05 (plan-time disposition) | 2026-11-21 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-21 | 14 | 14 | 0 | /gsd-secure-phase orchestrator (ASVS L1, grep depth) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-21
