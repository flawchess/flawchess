---
phase: "234"
slug: "milestone-feedback-ask"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-06"
---

# Phase 234 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| client -> POST /api/users/me/feedback-ask | untrusted action body; identity from the JWT | `{action}` enum |
| client -> GET/PUT /api/users/me/profile | profile reports ask state; impersonation tokens cross here | `active_days`, `feedback_ask.active` |
| API -> users.prompt_state | JSONB written only by guarded single-statement UPDATEs | ask state (status, round, dates) |
| client -> POST /api/feedback | untrusted `source` next to the existing free text | free text (user content), `source` enum |
| API -> Sentry | feedback signal carries `feedback_source` tag; ask service captures corrupt state | user id in context, enum tag |
| browser -> Umami | two click events leave the app | enumerated action targets only |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-234-01 | Tampering / Elevation | feedback_ask_action, apply_view/snooze/done | high | mitigate | `WHERE id = :uid` from `current_active_user` only (app/repositories/feedback_ask_repository.py:65,88,102; app/routers/users.py) | closed |
| T-234-02 | Tampering | FeedbackAskActionRequest | medium | mitigate | `FeedbackAskAction = Literal[...]`, `extra="forbid"` (app/schemas/feedback_ask.py:28,55) | closed |
| T-234-03 | Repudiation | impersonated admin answering the ask | medium | mitigate | `if user.is_guest or impersonated: return _INACTIVE` before any write (app/services/feedback_ask_service.py:117,169); impersonation no-write test | closed |
| T-234-04 | Tampering (integrity) | concurrent tabs | medium | mitigate | one guarded `UPDATE ... RETURNING` per transition (repository :75,93,105); `test_feedback_ask_concurrent_same_day_views_count_once` | closed |
| T-234-05 | Tampering (integrity) | users.prompt_state shape | medium | mitigate | NOT NULL `'{}'` default (app/models/user.py:122), CAST-typed binds, `FeedbackAskState(extra="forbid")`, Sentry capture + fail closed (feedback_ask_service.py:75-78) | closed |
| T-234-06 | Tampering / Repudiation | forged `source=milestone_ask` | low | accept | see Accepted Risks | closed |
| T-234-07 | Tampering | dev clock header in production | low | mitigate | header honoured only when `ENVIRONMENT == "development"` (app/core/dev_clock.py:24) | closed |
| T-234-08 | DoS | POST /me/feedback-ask flooding | low | accept | see Accepted Risks | closed |
| T-234-09 | Information disclosure | Sentry events from the ask service | low | mitigate | constant messages; user id via `set_context("feedback_ask", ...)` (feedback_ask_service.py:77) | closed |
| T-234-10 | Information disclosure | Umami click events | low | mitigate | enumerated `feedback-ask-sure` / `feedback-ask-later` targets only (frontend/src/lib/analytics.ts:401-402); kebab-case test | closed |
| T-234-11 | Repudiation / Spoofing | ask UI under impersonation | low | mitigate | UI renders only from server `feedback_ask.active` (forced false under impersonation); action route no-ops server-side | closed |
| T-234-12 | Tampering | client-chosen `source` | low | accept | see Accepted Risks | closed |
| T-234-13 | Spoofing / Elevation | Train landing and Bots roster ask branches | low | mitigate | both read `feedbackAskDays(profile)` (frontend/src/lib/feedbackAsk.ts:21), no client-side eligibility | closed |
| T-234-14 | Information disclosure | Hilda's copy | low | accept | see Accepted Risks | closed |
| T-234-15 | Tampering / Information disclosure | `FeedbackCreate.source`, Sentry `feedback_source` tag | low | mitigate | `FeedbackSource = Literal[...]` (app/schemas/feedback.py:16,30) + `ck_feedback_source` (app/models/feedback.py:15, migration f4b9d2c7e815); tag value is one of two literals (app/services/feedback_service.py:70) | closed |
| T-234-SC | Tampering | npm/pip/cargo installs | low | accept | see Accepted Risks | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-234-01 | T-234-06, T-234-12 | A user can only label their own feedback; Literal + DB CHECK bound the value; existing 5/hour/user rate limit applies. Worst case skews a funnel count. | plan-time (234-02/03 PLAN) | 2026-10-05 |
| AR-234-02 | T-234-08 | One indexed single-row UPDATE per call, no-op after the first view of the day; same exposure as the existing first-touch route. | plan-time (234-01 PLAN) | 2026-10-05 |
| AR-234-03 | T-234-14 | Shows the signed-in user's own active-day count to that user only. | plan-time (234-04 PLAN) | 2026-10-05 |
| AR-234-04 | T-234-SC | No packages installed by any plan in this phase. | plan-time (234-RESEARCH) | 2026-10-05 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-06 | 16 | 16 | 0 | execute-phase orchestrator (ASVS L1 grep verification) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-06
