---
phase: "239"
slug: "library-stats-you-vs-opponents"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-13"
---

# Phase 239 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| client → /api/library/{flaw-comparison, tactic-comparison, flaw-stats} | Authenticated user requests their own per-TC aggregates | the user's own game aggregates (low sensitivity) |
| localStorage → TC selection store | Stored TC key read back on mount | enumerated TC literal |
| frontend → Umami analytics | option-change / panel-open / popover-open events | enumerated targets and TC literals only |
| scripts / smoke / UAT → benchmark and dev DBs | Local operator reads | benchmark aggregates, dev data |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-239-01 | Tampering | chapter5.py SQL string assembly | medium | mitigate | Interpolates only closed in-code sets; `--db` is an argparse choice; `tests/scripts/test_chapter5_sql.py` pins the predicates | closed |
| T-239-02 | Denial of Service | benchmark DB container | low | mitigate | One foreground run; `SET TRANSACTION READ ONLY` (`scripts/benchmarks/chapter5.py:927`) | closed |
| T-239-03 | Information disclosure | per-TC flaw payloads (IDOR) | high | mitigate | `user_id=user.id` from `current_active_user` (`app/routers/library.py` flaw-comparison, flaw-stats); `tests/services/test_flaw_comparison.py::test_two_user_isolation` | closed |
| T-239-04 | Tampering | filter query params | low | mitigate | FastAPI Query typing + 422 date guard unchanged; no TC param; filters only via `apply_game_filters` | closed |
| T-239-05 | Denial of Service | below-gate TCs compute bullets | low | accept | See accepted risks | closed |
| T-239-06 | Tampering | tcSelectionStore storage read | low | mitigate | Validated against `TIME_CONTROL_ORDER` and the offered list; try/catch on read and write (`frontend/src/hooks/tcSelectionStore.ts:91,119`); tested | closed |
| T-239-07 | Information disclosure | popover-open analytics targets | low | mitigate | testIds built from metric keys + TC segment only | closed |
| T-239-08 | Information disclosure | per-TC tactic payload (IDOR) | high | mitigate | `user_id=user.id` from `current_active_user` (`app/routers/library.py` tactic-comparison); subqueries scoped by `Game.user_id` / `GameFlaw.user_id`; `tests/services/test_tactic_comparison_service.py::test_two_user_isolation` | closed |
| T-239-09 | Tampering | tactic_families query param | low | mitigate | Unknown keys expand to no motif ints (existing test kept) | closed |
| T-239-10 | Information disclosure | library-stats-tc option-change event | low | mitigate | Typed `TimeControlBucket` (`frontend/src/lib/analytics.ts:490`); click handler only | closed |
| T-239-11 | Tampering | rendering server values (Flaw Stats) | low | accept | See accepted risks | closed |
| T-239-12 | Tampering | dev DB during the D-12 check | medium | mitigate | SELECT-only inside `BEGIN READ ONLY` (239-06 SUMMARY); reset_db never run | closed |
| T-239-13 | Tampering | benchmark DB during the run | low | mitigate | chapter5 CLI READ ONLY transaction; one run at a time | closed |
| T-239-14 | Tampering | registry values | low | mitigate | Values traced to `## Accepted` in 239-ZONE-PROPOSAL.md; literal-pinned registry tests | closed |
| T-239-15 | Information disclosure | Elo anchor lookup | medium | mitigate | Not applicable: no Elo keying was implemented (owner decision) | closed |
| T-239-16 | Information disclosure | tactic-advanced event and tactic popover testIds | low | mitigate | Registered literal `tactic-advanced` (`frontend/src/lib/analytics.ts:379`); testIds from family keys + TC only | closed |
| T-239-17 | Tampering | dev DB during smoke and UAT | medium | mitigate | Smoke runs `SET TRANSACTION READ ONLY` and calls read-only services; UAT only navigated and reset filters | closed |
| T-239-18 | Tampering | rendering server values (vs-opponents) | low | accept | See accepted risks | closed |
| T-239-SC | Tampering | npm/pip/cargo installs | low | accept | See accepted risks | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-239-01 | T-239-05 | Below-gate TCs compute bullets in the same single per-game scan; cost bounded by the user's own analyzed games, no extra query per TC | plan 239-02 threat model | 2026-10-12 |
| AR-239-02 | T-239-11, T-239-18 | React escapes all text; no `dangerouslySetInnerHTML` in `components/library/stats/`; values are numbers and enumerated keys | plans 239-05 / 239-10 threat models | 2026-10-12 |
| AR-239-03 | T-239-SC | No package installs in any phase 239 plan | all plan threat models | 2026-10-12 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-13 | 19 | 19 | 0 | secure-phase (orchestrator, L1 grep; register authored at plan time, auditor skipped per ASVS 1 short-circuit) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-13
