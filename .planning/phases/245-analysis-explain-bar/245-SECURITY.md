---
phase: "245"
slug: "analysis-explain-bar"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-05"
---

# Phase 245 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| API -> browser | `GET /library/flaws/{game_id}/{ply}/tactic-lines` returns PV SAN strings; `flaw_markers` carry `move_san`; both are rendered and replayed client-side | public chess move notation (non-sensitive) |
| browser -> API | D-11 landing prefetch fires on every eligible mistake/blunder landing | game id + ply (non-sensitive) |
| browser -> Umami | Explain / Got it click events via `trackFeature` | enumerated literals only (`explain-open`, `explain-close`) |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-245-01 | Denial of service | Graft of API-supplied PV SANs | low | mitigate | `usableExplainLines` (`frontend/src/lib/explainBar.ts:49-50`) refuses empty PVs, length-1 allowed lines and ply-0 missed lines; existing `insertPvLine` try/catch stops at a malformed SAN | closed |
| T-245-02 | Information disclosure | `trackFeature` payloads | low | mitigate | Only `{ target: 'explain-open' \| 'explain-close' }` sent from click handlers (`frontend/src/hooks/analysis/useExplainBar.ts:105,119`); no SAN/ply/FEN/game id | closed |
| T-245-03 | Tampering (script injection) | `move_san` headline in `ExplainBar` | low | mitigate | Rendered as React text children; no `dangerouslySetInnerHTML`/`innerHTML` in `frontend/src/components/analysis/ExplainBar.tsx` | closed |
| T-245-04 | Denial of service | Landing prefetch volume | low | mitigate | Prefetch enabled only for eligible M/B plies (`useExplainBar.ts:83`); TanStack dedupe + `LIBRARY_STALE_TIME_MS` cache; 404s no longer retry | closed |
| T-245-05 | Repudiation (monitoring noise) | Sentry capture of 404s | low | mitigate | `useTacticLines` maps axios 404 to `null` inside `queryFn` (`frontend/src/hooks/useLibrary.ts:319`); 500s still error (tested in `useLibrary.test.ts`) | closed |
| T-245-06 | Information disclosure | tactic-lines endpoint not owner-scoped | low | accept | Existing, intentional (`app/routers/library.py`); phase adds no endpoint or parameter | closed |
| T-245-07 | Spoofing (misleading UI) | Tactic overlay on non-motif lines | low | mitigate | `focusedLineHasMotif` gate in `frontend/src/hooks/analysis/useAnalysisBoardArrows.ts:335,378` (fed by `lineHasVisibleMotif`) renders a plain arrow, no countdown/tint | closed |
| T-245-SC | Tampering | npm/pip/cargo installs | low | accept | No packages installed in this phase | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-245-01 | T-245-06 | tactic-lines is intentionally not owner-scoped (shared analysis data, pre-existing design); this phase reads only data the page already shows | plan-time threat model (245-02-PLAN.md) | 2026-11-05 |
| AR-245-02 | T-245-SC | No package installs in this phase | plan-time threat model (245-01/02-PLAN.md) | 2026-11-05 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-05 | 8 | 8 | 0 | secure-phase orchestrator (L1 grep, auditor skipped per short-circuit rule) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-05
