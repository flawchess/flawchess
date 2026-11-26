---
phase: "251"
slug: "blunder-check-schedule-streak-and-leaderboards-seed-261108-d"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-19"
---

# Phase 251 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Register assembled from the `<threat_model>` blocks of plans 01-13 (authored at plan time); mitigations verified at grep depth (ASVS L1) by gsd-security-auditor against diff base `c56374ff6`.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| client -> /blunder-check/* | Beta gate removed (D-18): every authenticated user, guests included, reaches the drill routes | session / window ids (user-scoped on every query) |
| client -> PUT /train/settings | Per-mode sizes and level become user-editable at any time | bounded ints, `BlunderCheckLevel` literal |
| client -> /train/leaderboard, /train/medals/* | Four weekly boards incl. blunder-check Points and Score % | public display names and scores only; guests and hidden users never on others' boards |
| client -> POST /train/blunder-check-notice/dismiss | New caller-scoped write | none (no body) |
| foreign games -> guest drills | Other users' games served as blunder-check windows | game id, time control, date, rating only |
| phase branch -> main -> production | Single all-users launch (D-18), no beta soak | release integrity |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-251-01 | Tampering | apply_day_completion streak/freeze writes | medium | mitigate | `streak_credited_on` idempotence guard (train_repository.py ~4133-4169); test_double_credit_raise_bc_after_puzzles_done | closed |
| T-251-02 | Elevation of privilege | get_session_date / completed_session_in_window / expire_stale_sessions | high | mitigate | lookups scoped by session id AND user_id (blunder_check_repository.py); test_bc_get_session_date_scoped_to_user | closed |
| T-251-03 | Denial of service | migration backfill | low | mitigate | constant-default ADD COLUMN, single-statement backfills, unknown TZ -> UTC, data-aware downgrade (migration ccc5e4f91f6d) | closed |
| T-251-04 | Tampering | train_settings sizes (DB) | medium | mitigate | CHECKs bc 0..30, some_mode_on, puzzles 0..50 (migration + models/train_settings.py) | closed |
| T-251-05 | Information disclosure | BC boards (guests, hidden users) | high | mitigate | shared `_entry_for`/`_rank_board` public filter (train_leaderboard.py); service + router tests | closed |
| T-251-06 | Tampering | POST /train/medals/claim with BC keys | medium | mitigate | widened `LeaderboardBoardKind` Literal (422 on unknown); claim WHERE user_id = caller; test_claim_bc_medal | closed |
| T-251-07 | Information disclosure | fetch_week_bc_aggregates | medium | mitigate | column-only select; response schemas carry no ids/emails | closed |
| T-251-08 | Tampering | Score % ranking (abandoned windows) | low | accept | see Accepted Risks Log | closed |
| T-251-09 | Elevation of privilege | BC drill routes after gate removal | high | mitigate | `current_active_user` + user-scoped repository lookups on all routes; IDOR tests incl. test_non_beta_user_cannot_touch_another_users_session | closed |
| T-251-10 | Denial of service | guest churn composing foreign sessions | medium | mitigate | one-open-session partial unique index; done-in-window guard; size cap 30 (schema + DB); compose probe 0.3-0.5 s | closed |
| T-251-11 | Information disclosure | foreign windows served to guests | low | mitigate | foreign pick returns Game.id only, excludes guest owners; GameInfo carries TC/date/rating only | closed |
| T-251-12 | Tampering | TrainSettingsUpdate | medium | mitigate | schema bounds, `BlunderCheckLevel` Literal, both-off validator + service resolved check (422), DB CHECK backstop; router tests | closed |
| T-251-13 | Tampering | streak via repeated size toggles | medium | mitigate | idempotent credit; resize matches only status='open' (never reopens) | closed |
| T-251-14 | Denial of service | repeated BC extension via PUTs | low | mitigate | extension = new_size - window_count, size <= 30, one open session | closed |
| T-251-15 | Elevation of privilege | resize_open_session | high | mitigate | no session-id parameter; locks and writes WHERE user_id = caller FOR UPDATE | closed |
| T-251-16 | Tampering | readLeaderboardMode (localStorage) | low | mitigate | parse against the two-literal union with try/catch fallback; unit tests | closed |
| T-251-17 | Information disclosure | BC boards in the card | low | mitigate | renders server rows only; visibility enforced server-side (T-251-05) | closed |
| T-251-18 | Tampering | notice dismiss endpoint | low | mitigate | no body, caller-scoped idempotent UPDATE; test_notice_dismiss_is_scoped_to_caller | closed |
| T-251-19 | Information disclosure | progress modes payload | low | mitigate | caller's own counts/flags only, no ids | closed |
| T-251-20 | Repudiation / annoyance | reminder job | low | mitigate | settle -> day_complete_on -> claim_reminder_day; reminder service tests | closed |
| T-251-21 | Tampering | restored BC solution cache | low | mitigate | session-id match check, RESET + onExit on mismatch; BlunderCheckTab test | closed |
| T-251-22 | Denial of service | double-tap Start composing twice | low | mitigate | synchronous startInFlight ref guard + server one-open-session index; StrictMode test | closed |
| T-251-23 | Information disclosure | analytics events | low | mitigate | enumerated literal tuples only; no ids, FENs or names | closed |
| T-251-24 | Tampering | level value in PUT | low | mitigate | server Literal (422 on unknown), client three-literal union | closed |
| T-251-25 | Denial of service | repeated dismiss taps | low | accept | see Accepted Risks Log | closed |
| T-251-26 | Tampering | lost/conflicting settings edits | medium | mitigate | single shared draft with one debounced PUT carrying all fields; TrainModeSettings tests | closed |
| T-251-27 | Tampering | both sizes at 0 | low | mitigate | UI draft drops the patch; server 422; DB CHECK some_mode_on | closed |
| T-251-28 | Tampering | feature-route step ID | low | mitigate | `FeatureRouteStepId` Literal with `blunder-check` appended; extra="forbid"; pinned-order test | closed |
| T-251-29 | Repudiation | route step completion | low | accept | see Accepted Risks Log | closed |
| T-251-30 | Tampering | release integrity | medium | mitigate | full pre-merge gate green (251-VALIDATION.md Gate Results); serial suite run by the orchestrator before release | closed |
| T-251-31 | Denial of service | launch-day guest compose load | low | accept | see Accepted Risks Log | closed |
| T-251-32 | Elevation of privilege | finish_session -> apply_day_completion | high | mitigate | user-scoped windows_for_session (404 before any credit); get_session_date(user_id, session_id) | closed |
| T-251-33 | Tampering | settings hook optional fields | low | mitigate | keys sent only when defined; typed; server validation + DB CHECKs | closed |
| T-251-SC | Tampering | dependency installs | low | accept | see Accepted Risks Log | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-251-01 | T-251-08 | Started-but-unended windows are excluded from Score %; little to gain and the server owns all grading (A5) | plan 251-02 threat model | 2026-11-19 |
| AR-251-02 | T-251-25 | Repeated dismiss taps are an idempotent, caller-scoped single-row UPDATE; optimistic UI prevents repeats | plan 251-08 threat model | 2026-11-19 |
| AR-251-03 | T-251-29 | Route-step completion is a UX hint, not a security fact; server-guarded UPDATEs prevent early skips | plan 251-10 threat model | 2026-11-19 |
| AR-251-04 | T-251-31 | Launch-day guest load is bounded (30 cap, one open session, ~0.3-0.5 s per 18-window compose); watch Sentry and latency after deploy | plan 251-11 threat model | 2026-11-19 |
| AR-251-05 | T-251-SC | No packages installed in any phase-251 plan (dependency manifests and lockfiles unchanged vs c56374ff6) | plans 01-13 threat models | 2026-11-19 |

*Accepted risks do not resurface in future audit runs.*

**Informational (not threats):** `blunder_check_repository.complete_session` filters by session id and `status='open'` but not `user_id`; both callers pass an id already resolved through a user-scoped lookup, so it is not exploitable. Adding a `user_id` parameter would be cheap defense in depth.

**Process items (not counted in threats_open):** serial `uv run pytest` before release (T-251-30); Sentry and latency watch after deploy (T-251-10, T-251-31).

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-19 | 34 | 34 | 0 | gsd-security-auditor (ASVS L1, block_on high) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-19
