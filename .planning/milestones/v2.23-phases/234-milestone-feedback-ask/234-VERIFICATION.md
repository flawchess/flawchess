---
phase: 234-milestone-feedback-ask
verified: 2026-10-06T06:00:00Z
status: passed
score: 10/10 must-haves verified
covered_files:
  - ".planning/phases/234-milestone-feedback-ask/234-01-PLAN.md"
  - ".planning/phases/234-milestone-feedback-ask/234-01-SUMMARY.md"
  - ".planning/phases/234-milestone-feedback-ask/234-02-PLAN.md"
  - ".planning/phases/234-milestone-feedback-ask/234-02-SUMMARY.md"
  - ".planning/phases/234-milestone-feedback-ask/234-03-PLAN.md"
  - ".planning/phases/234-milestone-feedback-ask/234-03-SUMMARY.md"
  - ".planning/phases/234-milestone-feedback-ask/234-04-PLAN.md"
  - ".planning/phases/234-milestone-feedback-ask/234-04-SUMMARY.md"
  - "CHANGELOG.md"
  - "alembic/versions/20261005_140000_f4b9d2c7e815_users_prompt_state_feedback_source.py"
  - "app/models/feedback.py"
  - "app/models/user.py"
  - "app/models/user_activity.py"
  - "app/repositories/feedback_ask_repository.py"
  - "app/repositories/feedback_repository.py"
  - "app/routers/users.py"
  - "app/schemas/feedback.py"
  - "app/schemas/feedback_ask.py"
  - "app/services/feedback_ask_service.py"
  - "app/services/feedback_service.py"
  - "frontend/src/App.tsx"
  - "frontend/src/components/bots/PersonaGrid.tsx"
  - "frontend/src/components/feedback/FeedbackAskBubble.tsx"
  - "frontend/src/components/feedback/FeedbackAskModalHost.tsx"
  - "frontend/src/components/feedback/FeedbackModal.tsx"
  - "frontend/src/components/train/TrainStartScreen.tsx"
  - "frontend/src/hooks/useFeedback.ts"
  - "frontend/src/hooks/useFeedbackAsk.ts"
  - "frontend/src/lib/analytics.ts"
  - "frontend/src/lib/feedbackAsk.ts"
  - "frontend/src/pages/Bots.tsx"
  - "frontend/src/pages/Import.tsx"
  - "frontend/src/pages/Train.tsx"
  - "frontend/src/types/feedback.ts"
  - "frontend/src/types/users.ts"
covered_digest: "v3:sha256:27537491ead72b18fa0743a63a9c5dc3c5c1005ab1019c6b2bd63d9c80b8adbd"
behavior_unverified: 0
overrides_applied: 1
overrides:
  - must_have: "ui.safety-gate wave-post gate (234-UI-SPEC.md must exist for a frontend phase)"
    reason: "Project uses no UI-SPECs; CONTEXT D-05 and PATTERNS pin the bubble design (reuse of TrainBotBubble / SignupAskActions shape). Gate blocked every wave only because no 234-UI-SPEC.md exists."
    accepted_by: "owner (recorded by orchestrator: 'Override, continue')"
    accepted_at: "2026-10-06T00:00:00Z"
human_verification:
  - test: "Cross-page one-view-per-day walk. Seed a registered dev user (no feedback rows, Train intro completed) with 4 prior user_activity days and prompt_state '{}'. Visit Import, then Train, then Bots on the same day."
    expected: "Hilda with 'for 5 days now' on all three surfaces; prompt_state->'feedback_v1'->>'views' is 1 afterwards."
    why_human: "Cross-surface, cross-route behavior in a real browser; component tests mock each surface in isolation."
  - test: "Phone width (375px) on the Train landing with the ask active."
    expected: "Hilda's bubble is visible above the streak card (no max-sm:hidden); streak card and Start button pushed down but reachable."
    why_human: "Visual/layout judgment; jsdom does not evaluate Tailwind breakpoints (tests assert class absence only)."
  - test: "Start an import so the 3s profile poll runs, click 'Sure!', type a draft, wait several poll ticks, then submit."
    expected: "Hilda disappears; the modal and typed draft persist; submit stores feedback.source = 'milestone_ask' and toasts."
    why_human: "Real Radix dialog + live polling + real network; the unit test only simulates the done-response cache patch."
  - test: "'Maybe later' on a fresh state."
    expected: "Hilda vanishes at once on the current page and stays gone on the other two surfaces; prompt_state snoozed_by = 'click'."
    why_human: "Cross-page browser walk (234-04 UAT leg 4); not run during execution."
---

# Phase 234: Milestone Feedback Ask Verification Report

**Phase Goal:** Turn invested users into feedback senders with a timed, character-voiced ask instead of the generic desktop-only floating button. Hilda the Hippo asks once a user reaches 5 active days, on whichever surface they hit first.
**Verified:** 2026-10-06
**Status:** passed (was human_needed; all four human items passed in 234-UAT.md on 2026-10-06)
**Re-verification:** Digest refresh only. After this report, the WR-01/WR-02 fix commits (d4357b380, cb8cb200e) changed `app/services/feedback_ask_service.py` and `tests/test_feedback_ask.py`. Owner chose a targeted re-check over a full verifier re-run: `tests/test_feedback_ask.py`, `test_feedback_repository.py` and `test_feedback_router.py` pass (81 passed), the browser UAT exercised the gated snooze path, and `covered_digest` was recomputed via `verification.fingerprint`.

All automated evidence supports goal achievement. The status is `human_needed` solely because the manual-only browser checks (VALIDATION.md and 234-04's UAT legs) were never run. There are no gaps. Two open code-review warnings (WR-01, WR-02) are non-blocking robustness items.

## Goal Achievement

### Observable Truths (roadmap contract = SEED-191 locked decisions; plan must-haves merged)

| #  | Truth | Status | Evidence |
| -- | ----- | ------ | -------- |
| 1  | Eligibility is server-decided: non-guest, non-impersonated, `active_days >= 5` (today-inclusive), no feedback row from any source, stored state permits | VERIFIED | `resolve_feedback_ask` and `build_feedback_ask_snapshot` in `app/services/feedback_ask_service.py`. `has_feedback` is an EXISTS probe on `feedback.user_id`. Guest/impersonation/<5 days short-circuit before the EXISTS. Truth-table and integration tests pass (75 backend tests re-run by me: all green). |
| 2  | Three surfaces share one state, whichever is hit first: Import replaces the explore AND welcome bubbles (D-03) | VERIFIED | `Import.tsx:457-460` renders `FeedbackAskBubble surface="import"` whenever `feedbackAskDays(profile) !== null`, else `ImportBotBubble`. `Import.feedbackAsk.test.tsx` covers explore, welcome, inactive, and missing-field cases. |
| 3  | Train landing: Hilda replaces the rotating host and outranks the reminder/import asks, only after the intro is done (D-04), visible on phones | VERIFIED | `TrainStartScreen.tsx:260-272`: `askDays = introDone ? feedbackAskDays : null`; whole host bubble swapped; `max-sm:hidden` only applied when `!isIntroHost && askDays == null`. Wired from `Train.tsx:227`. Five new tests pass. Both `TrainHeader` call sites (completed and fresh states) pass the prop. The empty state mounts no TrainHeader, as designed. |
| 4  | Bots roster: Hilda replaces the welcome greeting; info popover hidden; PersonaGrid stays query-free | VERIFIED | `PersonaGrid.tsx:88-98` early-returns `FeedbackAskBubble surface="bots"`. `Bots.tsx:794` prop-drills `feedbackAskDays(profile)`. PersonaGrid has no query hook (the hook lives only in the bubble). Test at `PersonaGrid.test.tsx:172`. |
| 5  | Session score screen is NOT a surface | VERIFIED | No `FeedbackAsk` reference in the score-screen files. The grep of `FeedbackAsk` across the frontend finds only Import, Train, Bots, PersonaGrid, TrainStartScreen, App, lib, hooks and types. |
| 6  | A view is at most one per UTC day across all surfaces, counted only when the bubble renders; 3rd view auto-snoozes with a same-day grace; re-ask once after +10 active days; never after round 2 | VERIFIED | Single guarded UPDATE in `feedback_ask_repository.py` (`_VIEW_SQL`). The view is posted from the mount effect in `FeedbackAskBubble.tsx`, never on profile fetch. **Mutation proofs run by me:** dropping the `last_view_date <> today` guard turned `test_same_day_view_is_noop` and `test_feedback_ask_concurrent_same_day_views_count_once` red. Dropping the `round < max_rounds` guard turned both `test_exhausted_round_two_is_never_viewed_again[click|views]` red. Both reverted (`git status` clean). |
| 7  | State is server-side in one generic JSONB `users.prompt_state` (NOT NULL DEFAULT '{}'), atomic UPDATE, never Python read-modify-write; other keys preserved | VERIFIED | Migration `f4b9d2c7e815` (single head per the review); model `user.py:122`; all three transitions are single `UPDATE ... RETURNING` with CAST-typed binds and `||` (not `jsonb_set`); concurrency test passes; unrelated-key preservation covered by the repository test matrix. |
| 8  | 'Maybe later' hides immediately and snoozes; 'Sure!' opens FeedbackModal with a concrete placeholder and marks done even if closed unsubmitted | VERIFIED | `useFeedbackAsk.ts` `onMutate` cancels profile queries and optimistically patches inactive; `FeedbackAskBubble.tsx` `handleSure` opens the modal first, then `mutate('done')`. `FEEDBACK_ASK_PLACEHOLDER = "What's one thing you'd change or add?"`. Bubble tests (`:166`, `:186`, `:198`, `:226`) pass. |
| 9  | The modal survives the bubble unmounting (Pitfall 1): app-level host, not behind `!playActive`, both layout branches | VERIFIED | `FeedbackAskModalHost.tsx` is mounted at `App.tsx:837` and `:863` and driven by a `useSyncExternalStore` store. Test `FeedbackAskBubble.test.tsx:239` (modal and typed draft survive the done response) passes. The real-browser variant is a human item. |
| 10 | Feedback submissions are source-tagged: `milestone_ask` vs `floating_button`; invalid values rejected; any submission ends the ask | VERIFIED | `FeedbackSource` Literal in `schemas/feedback.py`; `create_feedback` writes `source=data.source`; DB CHECK `ck_feedback_source` in the migration; `useFeedback` invalidates `USER_PROFILE_QUERY_KEY` on success; `FeedbackModal` takes `source`/`placeholder` props; Sentry gets a distinct `feedback_source` tag (`feedback_service.py:70`). The router and repository tests (TestFeedbackSource) pass. |
| 11 | GET and PUT `/users/me/profile` both emit `active_days` and `feedback_ask` (no cache clobber, Pitfall 2) | VERIFIED | Both routes use `_build_profile_response` (`users.py:80-121`); `test_feedback_ask_get_and_put_profile_agree` passes. |
| 12 | Copy interpolates the real active-day count, identical in both rounds (D-01/D-02); API exposes no round field | VERIFIED | `feedbackAskCopy(activeDays)` in `lib/feedbackAsk.ts`; `FeedbackAskView` carries only `active`. |

**Score:** 10/10 requirement IDs verified; 12/12 truths verified, 0 behavior-unverified. Every behavior-dependent truth (once-per-day, round cap, concurrency, modal survival, view-not-resurrecting-dismissal) has a passing behavioral test. The two repository-guard tests were additionally proven by mutation.

### Requirements Coverage (FBASK-01..10, defined in 234-RESEARCH.md; not in REQUIREMENTS.md)

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| FBASK-01 | 01, 03 | Migration: `prompt_state` JSONB NOT NULL '{}'; `feedback.source` + CHECK | SATISFIED | Migration file; model columns; `test_feedback_ask_new_user_prompt_state_is_empty_object`; IntegrityError test in `test_feedback_repository.py`. |
| FBASK-02 | 01 | Profile GET and PUT expose `active_days` + `feedback_ask` | SATISFIED | `_build_profile_response`; GET/PUT agreement test. |
| FBASK-03 | 01 | Eligibility (non-guest, >=5 days, no feedback, state allows) | SATISFIED | `resolve_feedback_ask` truth table and integration tests. |
| FBASK-04 | 01 | POST `/me/feedback-ask` view/snooze/done, atomic, dedupe, auto-snooze, round 2 | SATISFIED | Repository, service and router tests (51 plus); mutation proofs above. |
| FBASK-05 | 02, 03 | `FeedbackCreate.source` persisted; modal accepts placeholder and source | SATISFIED | Schema, repository, modal props; tests pass. |
| FBASK-06 | 02, 03 | Shared Hilda bubble, view on render, app-level modal host | SATISFIED | `FeedbackAskBubble`, `FeedbackAskModalHost`, `useFeedbackAsk`. |
| FBASK-07 | 02 | Import surface | SATISFIED | `Import.tsx:457`. |
| FBASK-08 | 04 | Train landing | SATISFIED | `TrainStartScreen.tsx:260-272`. |
| FBASK-09 | 04 | Bots roster | SATISFIED | `PersonaGrid.tsx:88-98`. |
| FBASK-10 | 02 | Umami `feedback-ask-sure` / `feedback-ask-later` | SATISFIED | `analytics.ts:401-402`; `trackFeature` is called only from the two click handlers, never on mount (test "tracks nothing" on mount passes); analytics kebab-case test passes. |

Orphaned requirements: none. REQUIREMENTS.md does not register these IDs (`requirements_path` null for this phase). All ten IDs are accounted for in the plans' `requirements` frontmatter (01: 01-04; 02: 05, 06, 07, 10; 03: 01, 05, 06; 04: 08, 09).

### Locked Decisions (CONTEXT D-01..D-05)

| Decision | Status | Evidence |
| -------- | ------ | -------- |
| D-01 copy inserts `active_days` | HONORED | `feedbackAskCopy`. |
| D-02 same copy in round 2 | HONORED | No round in the API or the frontend. |
| D-03 ask wins on Import (explore and welcome) | HONORED | `Import.tsx:455-461`. |
| D-04 Tank's intro wins on Train | HONORED | `introDone` gate. |
| D-05 no UI-SPEC; reuse existing bubble components | HONORED | `TrainBotBubble` and the `SignupAskActions` shape are reused. See the override. |

### Required Artifacts and Key Links

All artifacts named in the four plans exist, are substantive, and are wired (checked by reading the code and by passing tests): migration, `schemas/feedback_ask.py`, `repositories/feedback_ask_repository.py`, `services/feedback_ask_service.py`, router `_build_profile_response` and `feedback_ask_action`, `FeedbackAskBubble`, `useFeedbackAsk`, `lib/feedbackAsk.ts`, `FeedbackAskModalHost` (two mounts in `App.tsx`), the three surface wire-ups (`Import.tsx`, `Train.tsx` to `TrainStartScreen`, `Bots.tsx` to `PersonaGrid`), the CHANGELOG bullet (line 16). Key links:
- Router to service (`_build_profile_response` and `apply_feedback_ask_action`): WIRED.
- Service to repository (`apply_view/snooze/done`, `has_feedback`): WIRED.
- Bubble to endpoint (`/users/me/feedback-ask`): WIRED.
- Bubble to host (`openFeedbackAskModal` store): WIRED.
- `useFeedback` to `USER_PROFILE_QUERY_KEY`: WIRED.

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Real data? | Status |
| -------- | ---- | ------ | ---------- | ------ |
| Bubble copy `activeDays` | `profile.active_days` | `count(user_activity rows < today) + 1` (DB) | Yes | FLOWING |
| Surface switch | `profile.feedback_ask.active` | `resolve_feedback_ask` over `users.prompt_state`, `feedback` EXISTS and `user_activity` count | Yes | FLOWING |
| Ask state | `prompt_state.feedback_v1` | Guarded UPDATE ... RETURNING, validated by Pydantic | Yes | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Backend phase tests (ask, repository, service, feedback router, feedback repository) | `uv run pytest <5 files>` | 75 passed | PASS |
| Frontend phase tests (feedback components, useFeedback, Import ask, TrainStartScreen, PersonaGrid, analytics) | `npx vitest run <8 files>` | 170 passed | PASS |
| Once-per-day guard has teeth | Removed the `last_view_date` guard, ran the tests, restored | 2 tests failed | PASS |
| Round-2 cap has teeth | Removed the `round < max_rounds` guard, ran the tests, restored | 2 tests failed | PASS |

I did not re-run the full suites. I relied on the orchestrator's evidence: backend 5254 passed, frontend 5172 passed, and ruff, ty, lint, build and knip clean.

### Probe Execution

Step 7c: SKIPPED. The phase declares no probes.

### Anti-Patterns Found

None. The scan of `TBD|FIXME|XXX` over lines added by the phase in all touched source files found 0 markers. There are no stubs; every handler has real behavior.

### Code-Review Findings (234-REVIEW.md, all dispositioned `open`; 0 critical)

| ID | Severity here | Assessment |
| -- | ------------- | ---------- |
| WR-01 | WARNING (not a gap) | I confirmed it in code. `_run_transition` calls `model_validate` on the RETURNING value, and `apply_feedback_ask_action` does not catch `ValidationError` on that path. A corrupt stored state (only reachable by a manual or out-of-band write, since only the guarded SQL writes it) would 500 on a stale-tab action. The profile path fails closed correctly, so the user-facing ask never shows for such a user. The transaction rolls back, so there is no state damage. Fix: wrap `_transition` in the same `try/except ValidationError` plus `rollback`. |
| WR-02 | WARNING (not a gap) | I confirmed it in code. Only `view` is gated by `_base_eligible`; `snooze` and `done` are not. Not reachable from the UI, since the bubble renders only when `active` is true. A stale or buggy client could write ask state for an under-5-day user. Self-inflicted only, with no cross-user effect. Fix: gate `snooze` (and optionally `done`). |
| IN-01..IN-05 | INFO | IN-05 (Sure! marks done before submit) is intentional per SEED-191 #5. IN-01, IN-02, IN-03 and IN-04 are cosmetic or self-healing. |

Recommend triaging WR-01 and WR-02 (fix or `deferred`) before merge, but they do not block goal achievement.

### Overrides

- `ui.safety-gate` wave-post gate blocked on the missing `234-UI-SPEC.md`. The owner chose "Override, continue" because the project uses no UI-SPECs and CONTEXT D-05 plus PATTERNS pin the design. Recorded in the frontmatter `overrides:`; it is not a gap.

### Human Verification Required

These are the manual-only checks from VALIDATION.md and 234-04's UAT. They are classified as human items, not automated failures.

1. **Cross-page one-view-per-day walk.** Seed a dev user with 4 prior `user_activity` days and `prompt_state '{}'`, then visit Import, Train and Bots on one day. Expected: Hilda on all three ("for 5 days now") and `views = 1`. Why human: cross-route behavior in a real browser.
2. **Phone width (375px) on the Train landing.** Expected: Hilda visible above the streak card. Why human: layout judgment; jsdom cannot evaluate breakpoints.
3. **"Sure!" during an active import poll.** Expected: the modal and the draft persist after Hilda unmounts, and submit stores `source = 'milestone_ask'`. Why human: real dialog, polling and network.
4. **"Maybe later" on a fresh state.** Expected: Hilda is gone at once and stays gone on the other two surfaces. Why human: cross-page walk.

### Gaps Summary

No gaps. All ten requirement IDs and all locked decisions are implemented, wired, and behaviorally tested, and the two load-bearing state-machine guards were proven by mutation. Remaining work before declaring the phase fully done: run the four browser checks above (the project's memory says to run these yourself via the browser), and triage the WR-01 and WR-02 review warnings.

---

_Verified: 2026-10-06_
_Verifier: Claude (gsd-verifier)_
