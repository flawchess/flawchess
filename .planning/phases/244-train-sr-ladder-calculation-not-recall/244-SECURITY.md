---
phase: "244"
slug: "train-sr-ladder-calculation-not-recall"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-02"
---

# Phase 244 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| client -> POST /api/train/sessions/{id}/solve | solve outcome drives the SR ladder for the caller's own items | authenticated user's drill outcome (low sensitivity) |
| migration -> prod drill_items | one-off UPDATE rewrites due dates of in-flight prod items at deploy | per-user drill scheduling dates (low sensitivity) |
| static copy -> React render | fixed string literals rendered as text in Train UI and Home | none (compile-time literals) |
| phase branch -> main | pre-merge gate is the only safety net before squash-merge | source code |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-244-01 | Tampering | migration e2a7c4f9b244 PUSH_DUE_DATES_SQL | medium | mitigate | UPDATE guarded by `di.status = ACTIVE`, `source = SR`, `solved_at IS NOT NULL`, `floor_date > UTC today`, `due_date < floor_date`; SET writes only `due_date` (migration lines 81–112); `test_push_due_dates_per_case` cases A–K + rerun no-op test; mutation checks in 244-01-SUMMARY | closed |
| T-244-02 | Denial of service | migration on deploy | low | mitigate | UTC-only date conversion (`AT TIME ZONE 'UTC'`), never the stored IANA zone; single set-based statement | closed |
| T-244-03 | Repudiation / Integrity | irreversible due-date push (no-op downgrade) | low | accept | Owner accepted in 244-CONTEXT D-05; upgrade logs pushed rowcount | closed |
| T-244-04 | Elevation of privilege | apply_result inputs on the solve path | low | accept | Input removed, none added; `_advance_drill_item` (`app/repositories/train_repository.py:3092`) still filters `DrillItem.user_id == user_id` | closed |
| T-244-05 | Tampering (XSS) | Home.tsx, trainBotCopy.ts, TrainStatsCard.tsx copy | low | accept | Changed copy is string literals in `FEATURES`/explainers rendered as React text; the only `dangerouslySetInnerHTML` in Home.tsx is the pre-existing FAQ JSON-LD, untouched by this phase | closed |
| T-244-06 | Tampering | integration of plans 244-01/02 into main | medium | mitigate | Full CLAUDE.md pre-merge gate green (244-02-SUMMARY), independently re-run by orchestrator 2026-11-02: backend 5668 passed, frontend build + 5706 tests passed | closed |
| T-244-SC | Tampering | npm/pip/cargo installs | high | accept | No package installs in either plan; `uv.lock` / `package-lock.json` unchanged | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-244-01 | T-244-03 | One-way data change only delays resurfacing of items; rowcount logged at deploy | owner (244-CONTEXT D-05) | 2026-11-02 |
| AR-244-02 | T-244-04 | Change narrows inputs; ownership filter unchanged | plan-time register | 2026-11-02 |
| AR-244-03 | T-244-05 | Compile-time literals, no user data rendered | plan-time register | 2026-11-02 |
| AR-244-04 | T-244-SC | No dependency changes | plan-time register | 2026-11-02 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-02 | 7 | 7 | 0 | secure-phase orchestrator (ASVS L1 short-circuit, register authored at plan time) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-02
