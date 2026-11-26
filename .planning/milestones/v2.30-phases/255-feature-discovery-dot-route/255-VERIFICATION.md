---
phase: 255-feature-discovery-dot-route
verified: 2026-11-15T23:30:00Z
status: passed
score: 47/47 must-haves verified
covered_files:
  - ".planning/phases/255-feature-discovery-dot-route/255-01-PLAN.md"
  - ".planning/phases/255-feature-discovery-dot-route/255-01-SUMMARY.md"
  - ".planning/phases/255-feature-discovery-dot-route/255-02-PLAN.md"
  - ".planning/phases/255-feature-discovery-dot-route/255-02-SUMMARY.md"
  - ".planning/phases/255-feature-discovery-dot-route/255-03-PLAN.md"
  - ".planning/phases/255-feature-discovery-dot-route/255-03-SUMMARY.md"
  - ".planning/phases/255-feature-discovery-dot-route/255-04-PLAN.md"
  - ".planning/phases/255-feature-discovery-dot-route/255-04-SUMMARY.md"
  - ".planning/phases/255-feature-discovery-dot-route/255-05-PLAN.md"
  - ".planning/phases/255-feature-discovery-dot-route/255-05-SUMMARY.md"
  - ".planning/phases/255-feature-discovery-dot-route/255-06-PLAN.md"
  - ".planning/phases/255-feature-discovery-dot-route/255-06-SUMMARY.md"
  - ".planning/phases/255-feature-discovery-dot-route/255-07-PLAN.md"
  - ".planning/phases/255-feature-discovery-dot-route/255-07-SUMMARY.md"
  - "CHANGELOG.md"
  - "alembic/versions/20261115_180000_c3f8e2a6d255_phase_255_feature_route_seed.py"
  - "app/repositories/feature_route_repository.py"
  - "app/repositories/game_repository.py"
  - "app/routers/users.py"
  - "app/schemas/feature_route.py"
  - "app/schemas/users.py"
  - "app/services/feature_route_service.py"
  - "frontend/src/App.tsx"
  - "frontend/src/components/feature-route/FeatureRouteRecorder.tsx"
  - "frontend/src/components/feature-route/RouteDot.tsx"
  - "frontend/src/components/openings/stats/OpeningColorSwitch.tsx"
  - "frontend/src/components/train/TrainStartScreen.tsx"
  - "frontend/src/components/train/TrainSubnav.tsx"
  - "frontend/src/hooks/useFeatureRoute.ts"
  - "frontend/src/hooks/useRecordFeatureRoute.ts"
  - "frontend/src/lib/featureRoute.ts"
  - "frontend/src/lib/retiredLocalStorage.ts"
  - "frontend/src/lib/theme.ts"
  - "frontend/src/pages/Openings.tsx"
  - "frontend/src/pages/Train.tsx"
  - "frontend/src/pages/library/LibraryPage.tsx"
  - "frontend/src/pages/openings/OpeningsDesktopSidebar.tsx"
  - "frontend/src/pages/openings/OpeningsMobileBoardPanel.tsx"
  - "frontend/src/pages/openings/useSidebarState.ts"
  - "frontend/src/types/users.ts"
covered_digest: "v4:sha256:cbece07cfbae5a35206e2e504092b299a4f2284a16dc178b37c74b68dd01206d"
behavior_unverified: 0
overrides_applied: 0
---

# Phase 255: Feature Discovery Dot Route Verification Report

**Phase Goal:** One coherent strategy for the red pulsating dot: an ordered route of features, the dot in exactly one place at a time, one arbiter replacing the nav dots, the Openings sidebar hint chain and the re-minted Train flag; the same mechanism onboards new users and announces a new feature to returning ones.
**Verified:** 2026-11-15
**Status:** passed
**Re-verification:** No, initial verification (judged against the code after review fixes WR-01..WR-04 and the merge of main).

## Goal Achievement

The coverage set is the CONTEXT decisions D-01..D-23 (the phase has no REQUIREMENTS.md IDs). Verification was done against the current code, not the SUMMARY claims.

### Observable Truths (by decision)

| #   | Decision | Status | Evidence |
| --- | -------- | ------ | -------- |
| 1 | D-01 dot only | VERIFIED | The only affordance is `RouteDot`; no What's New or New pill code was added (grep of the diff, route walk step 7). |
| 2 | D-02 one dot at a time | VERIFIED | `resolveRouteDot` (`frontend/src/lib/featureRoute.ts`) returns one placement from the first unresolved step. Header, bottom bar and drawer all read `useRouteDotPlacement` through `useNavIndicators` (`App.tsx` 184-205). Pinned by `featureRoute.test.ts` and `App.test.tsx` (header and drawer dot ids equal single-element lists). Walk: never more than one route dot. |
| 3 | D-03 two places per step | VERIFIED | `placeStep`: `nav:` slot outside the section, `subtab:` or `control:` slot inside. Sites exist: LibraryPage (import and stats tabs, desktop and mobile), Openings (stats tab, played-as, filters), Train (Today tab, start button). Walk at 1280 and 390 px. |
| 4 | D-04 server-side completion | VERIFIED | `users.prompt_state.feature_route`, written only by guarded UPDATEs in `app/repositories/feature_route_repository.py`, served as `profile.feature_route`. `useUserFlag.ts` is deleted and no non-test file reads it. `removeRetiredDotKeys()` sweeps old keys from ProtectedLayout (`App.tsx` 705). |
| 5 | D-05 / D-08 only important features | VERIFIED | `FEATURE_ROUTE` holds exactly nine entries; none targets Library Flaws, Endgames Games or Analysis. |
| 6 | D-06 route order | VERIFIED | Backend `FeatureRouteStepId` Literal and frontend `FEATURE_ROUTE` hold import, train, bots, openings, openings-played-as, openings-filters, openings-stats, endgames, library-stats; pinned by `test_step_ids_are_pinned_in_d06_order` and the vitest twin. |
| 7 | D-07 sidebar chain folded in, bookmarks dot removed | VERIFIED | `showBookmarksHint`, `showPlayedAsHint`, `showFiltersHint` and the two hint keys are gone from non-test code; `useSidebarState.ts` holds no localStorage state. Played-as and filters are route steps with `recordPlayedAs` and `recordFilters` wired to the control handlers (`Openings.tsx` 88-94, 160, 272, 370, 608, 724, 767). |
| 8 | D-09 blunder-check not a step; adding a step is small | VERIFIED | Registry has no blunder-check entry. A new step is one `FEATURE_ROUTE` entry plus one Literal member (comments and list tests on both sides). |
| 9 | D-10 3-day auto-skip | VERIFIED | `FEATURE_ROUTE_SKIP_ACTIVE_DAYS = 3` on both sides. Client `isCandidateExpired` (`activeDays - since_days >= 3`) and server `_SKIP_SQL` guard (`active_days >= since_days + 3`). `test_skip_timeline_applies_exactly_at_since_days_plus_three` passes. |
| 10 | D-11 active days from user_activity, no write per display | VERIFIED | `feature_route_service._count_active_days` uses `feedback_ask_repository.count_active_days_before` + 1 (same count as `profile.active_days`). Writes are one `current` stamp per transition and one done or skip per step. `test_profile_feature_route_is_empty_and_reads_never_write` and `test_current_repost_keeps_since_days_and_reads_never_write` pass. |
| 11 | D-12 new step enters in order | VERIFIED | `findCandidate` returns the first unresolved step; a new registry entry is reached only after earlier steps are resolved. Unit test with a reordered route. |
| 12 | D-13 completion rules | VERIFIED | `completion: 'visit'` steps are recorded by `planDoneWrites` from `visitMatch`; `used` steps by control handlers (played-as, filters, train). |
| 13 | D-14 Import done on visit | VERIFIED | `import` entry: `visitMatch` on `/library/import`, `requiresGames: false`. Recorder test and walk step 2. |
| 14 | D-15 every completion recorded, even without the dot | VERIFIED | `planDoneWrites` records any available visit step whether or not it is the candidate; control handlers post `done` unconditionally. Server stores `with_dot` as whether the step was current. Mutation check: removing the recorder cooldown made tests (h) and (l) fail, so the retry and loop guards (WR-01, WR-03) have teeth. |
| 15 | D-16 / D-22 existing users start complete, as an explicit ID set | VERIFIED | Migration `c3f8e2a6d255` seeds the nine IDs as `done` per existing row with no `current` key and a hard-coded ID list; the four migration tests pass (seed, idempotent, downgrade removes only the route key, a row created later is empty). Single alembic head `c3f8e2a6d255`. Dev DB: 20 of 20 users carry nine steps. |
| 16 | D-17 Train badge replaces the Train dot | VERIFIED | `NavIndicator` and the drawer row skip the route dot on Train when `trainBadgeLabel != null`; other items still show the dot. Covered in `App.test.tsx`; walk saw badge plus Bots dot together. |
| 17 | D-18 Library import dot is step 0 | VERIFIED | `import` is the first registry entry, stored server-side; the old library flag logic is gone. |
| 18 | D-19 guests the same | VERIFIED | No guest guard in the repository; `test_guest_route_is_stored_and_survives_email_promotion` and `test_guest_stamps_current_and_skips` pass; walks used guests. |
| 19 | D-20 sticky subnav out of scope | VERIFIED | Dots sit on the existing non-sticky tab bars; no sticky subnav code. |
| 20 | D-21 Train used on Start/Resume | VERIFIED | `Train.tsx` `handleEnterLoop` posts `{action: 'done', step: 'train'}` before `loop.enterLoop()`; the registry entry has `completion: 'used'`, no `visitMatch`, `requiresGames: false`. Dot on nav, on the Today tab trigger and inside the start button. Walk step 3. |
| 21 | D-23 locked steps pause the route | VERIFIED | `findCandidate` returns null when the first unresolved step is locked and never looks past it; `planClockWrites` therefore stamps and skips nothing while locked (clock paused). `delete_all_games_for_user` calls `clear_current` (`game_repository.py` 322), so a current stamp does not survive a return to zero games; three server tests cover it. Walk: zero dots during the 350 s import at 1280 px and during the 84 s import at 390 px, dot on Openings within 1 s of unlock. |

Plan-level must_have truths (47 across plans 01 to 07) all map onto the rows above plus the guard-level items below, each checked in code:

- Plan 01: nested steps merge keeps earlier steps and `feedback_v1`; repeated done is a 200 no-op that keeps the first record; corrupt state gives `feature_route: null` with one Sentry capture and no 500; impersonation never writes. Tests pass (`test_second_step_keeps_first_and_repeat_is_noop`, `test_done_keeps_feedback_state`, `test_corrupt_stored_state_fails_closed`, `test_impersonated_session_never_writes`).
- Plan 02: `FeatureRouteRecorder` mounted in ProtectedLayout; null state posts nothing; impersonation never writes (recorder tests).
- Plan 03: drawer dot with the `-drawer` suffix and the retired-key sweep (storage errors swallowed) pinned by `App.test.tsx` and `retiredLocalStorage.test.ts`.
- Plan 04: skip window, `since_days` stability, 422 on unknown step or action or extra key, auth required, duplicate-post idempotence.
- Plan 05: subtab and control dots, "any click on the mobile Stats colour switch" via `onAnyClick`, red route dot wins over the brown filters-modified dot (`Openings.tsx` 521).
- Plan 06: Train dot on the Today tab, start button, and Today-tab dot independent of the badge.
- Plan 07: single alembic head, CHANGELOG bullets, gate (recorded green on the merged tree), route walk.

**Score:** 47/47 must-haves verified; 0 present-but-behavior-unverified.

### Review-fix state (post-plan changes)

The recorder uses a 10 s resend cooldown (`ROUTE_WRITE_RESEND_COOLDOWN_MS`) rather than the stamp-signature reset described in 255-04-SUMMARY.md, and `useRecordFeatureRoute` repeats a profile refetch that a route write cancelled. These satisfy the same must_haves (no write loop, retry of a failed write, no stale profile). I replaced the cooldown line with a no-op and re-ran the recorder tests: tests (h) and (l) failed, then I restored the file with `git checkout`.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Backend route endpoint, clock, D-23 stamp removal, seed migration | `uv run pytest tests/test_feature_route.py tests/test_migration_255_feature_route_seed.py` | 27 passed | PASS |
| Arbiter, recorder, nav surfaces, retired keys, Train, Openings, Library | `npx vitest run` over featureRoute, feature-route, App, retiredLocalStorage, Train.subnav, Openings.render, library | 9 files, 249 tests passed | PASS |
| Single migration head | `uv run alembic heads` | `c3f8e2a6d255 (head)` | PASS |
| Full pre-merge gate on the merged tree | recorded by the orchestrator (not re-run) | ruff, ty x2, depth gate, pytest 6634 passed, frontend lint, build, vitest 6453 passed, knip clean | PASS (reported) |

### Anti-Patterns Found

None blocking. No TBD, FIXME or XXX markers introduced. Open review items IN-01..IN-05 are info level (see below).

### Residual Items (non-blocking, not human gates)

1. Step 8 of the route walk (an existing pre-migration account shows no dot) was not seen in a browser. Evidence in its place: the seed migration tests, 20 of 20 dev users holding all nine steps, the arbiter unit test "a fully resolved route has no dot", and a browser-observed all-done guest with no dot at both widths. The goal-relevant behavior is determined entirely by that data plus the arbiter, so I do not consider a human gate necessary. An owner glance when convenient is cheap.
2. The hop onto the mobile Openings Stats tab at 390 px was not seen in a browser; it was seen at 1280 px, and `Openings.render.test.tsx` asserts `openings-stats-notification-dot-mobile` inside `tab-stats-mobile`.
3. The walk predates WR-01..WR-04. Those fixes touch only the recorder retry and refetch behavior, which recorder tests (h) to (m) exercise (mutation-checked above). No repeat walk required.
4. Open review infos IN-01 (stale `current` after its step resolves, never rendered), IN-02, IN-03 (dead `_CorruptRouteStateError`), IN-04 (stale comments referencing `useUserFlag.ts` in `botGameSnapshot.ts` and `sounds.ts`) and IN-05 are cosmetic or harmless.
5. Edge worth knowing, not a gap: a lock that spans several active days without deleting games (for example a long re-import on an account that already holds games) keeps the old stamp, so the step could expire right after unlock. Assumption A-7 in plan 04 covers the delete-all-games case, which is the realistic path to a lock.

### Gaps Summary

No gaps. Every decision D-01..D-23 is accounted for in the codebase, the tests that guard them pass and have teeth, and the recorded browser walk covers the user-visible route at both widths including D-23.

---

_Verified: 2026-11-15_
_Verifier: Claude (gsd-verifier)_
