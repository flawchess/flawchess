---
phase: "229"
slug: "umami-identify-feature-events"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-03"
---

# Phase 229 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| localStorage auth_token to analytics id | The token is user-readable and user-editable; its `sub` claim becomes an analytics label | numeric `users.id` (pseudonymous) |
| browser to analytics.flawchess.com | identify and event payloads leave the browser to the first-party Umami instance | distinct id, account tag, enumerated `page`/`target`/`value` props |
| admin browser during impersonation | An admin acts with the target's token; analytics must not attribute the admin's clicks to the target | none (identify skipped) |
| operator to prod Umami DB | The deletion runbook runs destructive SQL by hand | per-account analytics rows |

---

## Threat Register

Register authored at plan time (229-01 to 229-08 `<threat_model>` blocks). `T-229-SC` appears in every plan and is listed once.

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-229-01 | Repudiation | distinctIdFromToken / ProtectedLayout effect | high | mitigate | `analytics.ts:156` returns null on `is_impersonation`; `App.tsx:677` returns null on `profile.impersonation`; both required (`App.tsx:720`); UAT leg 3 ran the real function | closed |
| T-229-02 | Information disclosure | identifyUser payload | high | mitigate | `DISTINCT_ID_PATTERN = /^\d+$/` (`analytics.ts:127,158`); only sub + account tag sent; `?token=` scrubbing intact | closed |
| T-229-03 | Information disclosure | logout on a shared browser | medium | mitigate | `useAuth.ts:176` hard navigation, pinned by `useAuth.test.tsx`; Umami 3.4.0 running (UAT test 6) | closed |
| T-229-04 | Tampering | user-edited auth_token sub | low | accept | See Accepted Risks Log | closed |
| T-229-05 | Tampering | runbook deletion SQL | medium | mitigate | `production-runbook.md`: preview block, shared-session pre-check, `BEGIN` ... `ROLLBACK` dry run by default (stricter than planned) | closed |
| T-229-06 | Tampering | Umami container image | medium | mitigate | `docker-compose.yml:128` `ghcr.io/umami-software/umami:3.4.0` | closed |
| T-229-07 | Information disclosure | trackFeature / FeatureEventMap | high | mitigate | Literal-union registry, build gate, registry test (VALIDATION 229-02-01 green) | closed |
| T-229-08 | Information disclosure | popover-open target | high | mitigate | `popoverTargetFromTestId` drops numeric segments, rejects non `^[a-z][a-z0-9-]*$` (`analytics.ts:440`) | closed |
| T-229-09 | Denial of service | hover-driven popover opens | low | mitigate | `useTrackedPopoverOpen` once per mount (`useTrackedOpen.ts:52`), tested | closed |
| T-229-10 | Information disclosure | page label on excluded routes | low | mitigate | `EXCLUDED_PAGE_SEGMENTS` admin/activity/login/auth (`analytics.ts:235`); page is a fixed enum | closed |
| T-229-11 | Information disclosure | MobileMoreDrawer nav-click | low | mitigate | `navDestinationOf` only matches `NAV_DESTINATIONS` (`analytics.ts:317`); superuser App.test case | closed |
| T-229-12 | Tampering | MobileFilterDrawer open-transition effect | low | mitigate | Mount-value ref, mount-open drawer test (`panelOpenTracking.test.tsx`) | closed |
| T-229-13 | Information disclosure | recency custom range, opponent-strength slider | medium | mitigate | Value unions `Preset \| 'custom'` (`analytics.ts:354-365`) | closed |
| T-229-14 | Information disclosure | PositionBookmarkCard | medium | mitigate | `PositionBookmarkCard.tracking.test.tsx` asserts bookmark id absent | closed |
| T-229-15 | Denial of service | slider filters | low | mitigate | `onValueCommit` in OpponentStrength/PresetRange/TacticDepth filters, tested | closed |
| T-229-16 | Information disclosure | PasteModal, VariationTree, AnalysisTagsPanel | high | mitigate | Fixed literal targets only; UAT leg 2 saw no FEN/SAN in paste-load payload | closed |
| T-229-17 | Denial of service | ELO and temperature sliders | low | mitigate | `onValueCommit` in EloSelector/TemperatureSelector; ladder rung / 3-value bucket | closed |
| T-229-18 | Information disclosure | LibraryGameCard, FlawCard, TacticMotifGroup | high | mitigate | Literal targets; LibraryGameCard test asserts game id absent | closed |
| T-229-19 | Information disclosure | PersonaCard, Train actions | medium | mitigate | Literal targets; UAT leg 2 `persona-open` carried no id/name | closed |
| T-229-20 | Repudiation | DB-known duplication | low | mitigate | Retry/dismiss traced and left untracked (229-07 SUMMARY) | closed |
| T-229-21 | Information disclosure | bot action events | low | mitigate | Literal targets; draw accept/resign/results un-evented (GameResultDialog, ResumeGate tests) | closed |
| T-229-22 | Information disclosure | UAT evidence | low | mitigate | UAT records dev ids only; post-deploy evidence keeps aggregate counts (prod ids scrubbed from 229-UAT.md before commit, 2026-10-03) | closed |
| T-229-23 | Tampering | future features skipping the registry | medium | mitigate | `frontend/CLAUDE.md:49-57` rule + typed `trackFeature` signature | closed |
| T-229-SC | Tampering | npm/pip/cargo installs | high | mitigate | No dependency manifest or lockfile changes in the phase diff (`8c6555593..fff3d103b`) | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-229-01 | T-229-04 | Editing the stored token only relabels the editor's own analytics; the API rejects the forged token, so there is no authorization impact | plan 229-01 threat model | 2026-10-03 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-03 | 24 | 24 | 0 | orchestrator (ASVS L1 grep verification, short-circuit: register authored at plan time) |

## Security Audit 2026-10-03
| Metric | Count |
|--------|-------|
| Threats found | 24 |
| Closed | 24 |
| Open | 0 |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-03
