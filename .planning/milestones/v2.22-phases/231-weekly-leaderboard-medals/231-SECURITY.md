---
phase: "231"
slug: "weekly-leaderboard-medals"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-04"
---

# Phase 231 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| client -> GET /api/train/leaderboard | Authenticated (JWT); viewer id only from current_active_user. The request also triggers a global write (lazy finalization). | Board rows, podium names, medal counts (no ids) |
| client -> GET /api/train/medals/unclaimed | Authenticated; caller id only from current_active_user | Caller's own unclaimed medals |
| client -> POST /api/train/medals/claim | Untrusted body (list of week/board keys); server scopes it to the caller | Writes celebrated_at |
| snapshot -> live board tally | Counts keyed by user id computed server-side, attached to already-visible rows | Medal counts |
| stored usernames -> other users' clients | Self-typed platform usernames frozen into display_name, shown on the podium | Usernames (React text only) |
| users table -> train_weekly_standings | Account deletion must erase personal data held in a second table | display_name (GDPR) |
| admin impersonation session -> user's celebration state | An impersonating admin acts with the user's identity | Claim state |
| superuser -> /admin demo | SuperuserRoute + page guard; demo is client-only fixtures | None (static fixtures) |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-231-01 | Information disclosure | build_last_week podium names | high | mitigate | Read-time "Anonymous" mask for hidden-now non-viewers (`ANONYMOUS_DISPLAY_NAME`, `app/services/train_leaderboard.py:64`); `test_podium_masks_hidden_now_and_deleted_users` (`tests/routers/test_train_medals.py:344`) | closed |
| T-231-02 | Information disclosure | display_name after account deletion (GDPR) | high | mitigate | FK `ondelete='SET NULL'` + `trg_train_weekly_standings_erase_name` (migration e3a8c5f17b20:13-60); `test_deleted_user_row_has_its_display_name_erased`, `test_erase_name_trigger_exists` (`tests/repositories/test_train_medals_finalization.py:253,278`) | closed |
| T-231-03 | Tampering | concurrent finalizers | medium | mitigate | Marker insert `on_conflict_do_nothing(...).returning(...)` as the lock, unique standings constraint (`app/repositories/train_medals_repository.py:97-126`); `test_concurrent_finalizers_write_one_marker_and_no_duplicates` (:305) | closed |
| T-231-04 | Denial of service | finalization failure on the board request | medium | mitigate | Router rollback + `sentry_sdk.capture_exception()` and still serves (`app/routers/train.py:88-90,160-162`); `test_finalization_failure_still_serves_the_board` (`tests/routers/test_train_medals.py:468`) | closed |
| T-231-05 | Information disclosure | user ids via podium or tally | medium | mitigate | Id-free schemas; `test_response_key_set_has_no_user_ids` (`tests/routers/test_train_leaderboard.py:246`) | closed |
| T-231-06 | Tampering | client-asserted move_quality inflating scores (WR-01) | low | accept | See Accepted Risks Log AR-231-01 | closed |
| T-231-07 | Repudiation | solve just after the deadline missing from the snapshot | low | mitigate | `MEDALS_FINALIZE_GRACE` 5 min (`app/services/train_medals.py:61`) with grace-boundary `due_weeks` tests | closed |
| T-231-08 | Tampering | stored XSS through display_name | medium | transfer | Frontend renders names as React text only (T-231-14) | closed |
| T-231-09 | Elevation of privilege | POST /medals/claim IDOR | high | mitigate | UPDATE scoped by `TrainWeeklyStanding.user_id == user_id` (`train_medals_repository.py:197,237`); `test_claim_is_scoped_to_the_caller_and_idempotent` (router :642), `test_mark_celebrated_is_scoped_to_the_caller_and_idempotent` (repository :184) | closed |
| T-231-10 | Information disclosure | GET /medals/unclaimed | medium | mitigate | No user parameter, WHERE user_id = caller; `test_fetch_unclaimed_skips_celebrated_non_medal_and_foreign_rows` (repository :139) | closed |
| T-231-11 | Denial of service / Tampering | claim body size and content | medium | mitigate | `Field(min_length=1, max_length=MEDAL_CLAIM_MAX_ITEMS)` (`app/schemas/train.py:586`); `test_claim_validation_rejects_bad_bodies` (router :705) | closed |
| T-231-12 | Information disclosure | tally user enumeration | medium | mitigate | Counts only for visible keys; `test_visible_keys_*` (`tests/services/test_train_leaderboard.py:1023-1048`) | closed |
| T-231-13 | Tampering | replayed claims | low | mitigate | `celebrated_at.is_(None)` guard (`train_medals_repository.py:199,239`); idempotency tests above | closed |
| T-231-14 | Tampering (stored XSS) | podium / row names | medium | mitigate | React text children only; `renders a name containing markup as literal text (T-231-14)` (`TrainLeaderboardCard.test.tsx:602`) | closed |
| T-231-15 | Information disclosure | podium / tally rendering | low | transfer | Server-side masking, erasure and id-free payloads (T-231-01/02/05/12) | closed |
| T-231-16 | Repudiation / Tampering | admin impersonation consuming a celebration | medium | mitigate | Host disabled while `profile.impersonation` is set; `an impersonating admin triggers no GET and shows nothing (T-231-16)` (`TrainMedalDialogHost.test.tsx:189`) | closed |
| T-231-17 | Tampering | duplicate claim POSTs | low | mitigate | `settledRef` guard (`MedalClaimDialog.tsx:62-68`), per-mount closed state, server idempotency (T-231-13) | closed |
| T-231-18 | Information disclosure | analytics leakage of claims | low | mitigate | No `trackFeature`/`trackEvent` in medals impl (grep: only test mocks asserting no calls) | closed |
| T-231-19 | Information disclosure | LeaderboardMedalsDemo | low | mitigate | No apiClient/trainApi/useQuery in demo or fixtures (grep empty); zero-call spy test | closed |
| T-231-20 | Elevation of privilege | demo section outside the DEV gate | low | accept | See Accepted Risks Log AR-231-02 | closed |
| T-231-21 | Repudiation | privacy disclosure of stored standings | low | mitigate | `frontend/src/pages/Privacy.tsx` states stored standings and "Deleted user" erasure | closed |
| T-231-22 | Elevation of privilege | client claim keys reaching another user's rows | high | transfer | Enforced server-side by T-231-09 | closed |
| T-231-23 | Tampering | concurrency-test rows leaking into other tests | low | mitigate | Own 2034 weeks, ids 93710-93711, cleanup before seeding and in `finally` (`test_train_medals_finalization.py:67-68,370`) | closed |
| T-231-SC | Tampering | npm/pip/cargo installs | high | accept | See Accepted Risks Log AR-231-03 | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-231-01 | T-231-06 | Client-asserted move_quality (Phase 230 review WR-01): no prizes, small user base, clamping would lower honest scores; do not fix | Owner | 2026-10-04 |
| AR-231-02 | T-231-20 | Demo lives on /admin, which keeps SuperuserRoute and the page-level is_superuser guard; it exposes only static fixtures and production components | Owner (plan 231-05) | 2026-10-04 |
| AR-231-03 | T-231-SC | No packages installed in any plan of this phase (RESEARCH Package Legitimacy Audit lists none); reserved row per phase convention | Owner (plans 231-01..06) | 2026-10-04 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-04 | 24 | 24 | 0 | secure-phase orchestrator (ASVS L1 grep-depth short-circuit; register authored at plan time; phase test files green: 141 backend, 143 frontend) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-04
