---
phase: 230-weekly-train-leaderboards
verified: 2026-10-04T05:20:00Z
status: passed
score: 15/15 must-haves verified
covered_files:
  - ".planning/phases/230-weekly-train-leaderboards/230-01-PLAN.md"
  - ".planning/phases/230-weekly-train-leaderboards/230-01-SUMMARY.md"
  - ".planning/phases/230-weekly-train-leaderboards/230-02-PLAN.md"
  - ".planning/phases/230-weekly-train-leaderboards/230-02-SUMMARY.md"
  - ".planning/phases/230-weekly-train-leaderboards/230-03-PLAN.md"
  - ".planning/phases/230-weekly-train-leaderboards/230-03-SUMMARY.md"
  - ".planning/phases/230-weekly-train-leaderboards/230-04-PLAN.md"
  - ".planning/phases/230-weekly-train-leaderboards/230-04-SUMMARY.md"
  - ".planning/phases/230-weekly-train-leaderboards/230-05-PLAN.md"
  - ".planning/phases/230-weekly-train-leaderboards/230-05-SUMMARY.md"
  - "alembic/versions/20261003_120000_c4e7a91d2b58_users_leaderboard_hidden.py"
  - "app/models/drill_solve.py"
  - "app/models/user.py"
  - "app/repositories/train_leaderboard_repository.py"
  - "app/routers/train.py"
  - "app/routers/users.py"
  - "app/schemas/train.py"
  - "app/schemas/users.py"
  - "app/services/train_leaderboard.py"
  - "app/services/train_score.py"
  - "frontend/src/App.test.tsx"
  - "frontend/src/api/client.ts"
  - "frontend/src/components/settings/LeaderboardPrivacyCard.tsx"
  - "frontend/src/components/settings/SettingsPanel.tsx"
  - "frontend/src/components/settings/__tests__/LeaderboardPrivacyCard.test.tsx"
  - "frontend/src/components/settings/__tests__/SettingsDialogButton.test.tsx"
  - "frontend/src/components/settings/__tests__/SettingsPanel.test.tsx"
  - "frontend/src/components/settings/__tests__/SettingsSheetButton.test.tsx"
  - "frontend/src/components/train/SignupAskActions.tsx"
  - "frontend/src/components/train/TrainDevClock.tsx"
  - "frontend/src/components/train/TrainLeaderboardCard.tsx"
  - "frontend/src/components/train/TrainScoreRankLines.tsx"
  - "frontend/src/components/train/TrainScoreScreen.tsx"
  - "frontend/src/components/train/TrainStartScreen.tsx"
  - "frontend/src/components/train/__tests__/TrainLeaderboardCard.test.tsx"
  - "frontend/src/components/train/__tests__/TrainScoreRankLines.test.tsx"
  - "frontend/src/components/train/__tests__/TrainScoreScreen.test.tsx"
  - "frontend/src/components/train/__tests__/TrainStartScreen.test.tsx"
  - "frontend/src/hooks/useTrainLeaderboard.ts"
  - "frontend/src/hooks/useUserProfile.ts"
  - "frontend/src/lib/__tests__/analytics.test.ts"
  - "frontend/src/lib/__tests__/trainLeaderboard.test.ts"
  - "frontend/src/lib/analytics.ts"
  - "frontend/src/lib/trainLeaderboard.ts"
  - "frontend/src/lib/trainScore.ts"
  - "frontend/src/pages/Privacy.tsx"
  - "frontend/src/pages/Train.tsx"
  - "frontend/src/pages/__tests__/Bots.test.tsx"
  - "frontend/src/pages/__tests__/Train.solveLoop.test.tsx"
  - "frontend/src/types/train.ts"
  - "frontend/src/types/users.ts"
  - "tests/repositories/test_train_leaderboard_repository.py"
  - "tests/routers/test_train_leaderboard.py"
  - "tests/services/test_train_leaderboard.py"
  - "tests/services/test_train_score_parity.py"
  - "tests/test_users_router.py"
covered_digest: "v2:sha256:8c7c82cdfe18aeb61659c85e61c29b9904bc4ccfd0bad943bcae47ca631abe64"
behavior_unverified: 0
overrides_applied: 0
human_verification: []
---

# Phase 230: Weekly Train Leaderboards Verification Report

**Phase Goal:** Two weekly leaderboards on Train (Points and an average-session-score "Accuracy" board), visible from the first session, top 5 plus the viewer's row with neighbours, server-side scoring pinned to the frontend by a parity test, one ISO UTC week keyed on `drill_solves.solved_at`, opt-out, guest/hidden private rows, score-screen rank lines.
**Verified:** 2026-10-04
**Status:** passed (owner triaged the review warnings on 2026-10-04; see Owner Triage)
**Re-verification:** No, initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | One tabbed "This week" card (Points / Accuracy), countdown in header, remembered tab, "Accuracy" helper, never "skill" (D-07, D-09, D-10) | VERIFIED | `TrainLeaderboardCard.tsx` (ToggleGroup, `readLeaderboardTab`/`writeLeaderboardTab` with try/catch, `ACCURACY_HELPER_COPY`); tests for tab restore, unknown value fallback, no "skill" pass |
| 2 | Card placed after `TrainStreakCard`, before `TrainStatsCard`, in in-progress, default and exhausted landing branches (D-08) | VERIFIED | `TrainStartScreen.tsx` diff: three `<TrainLeaderboardCard isGuest={isGuest} />` insertions, order checked; `TrainStartScreen.test.tsx` passes |
| 3 | Visible from the first session: empty-board copy, "Solve a puzzle to enter", guests see board plus ghost row, score screen gives rank after first session | VERIFIED | `EMPTY_WEEK_COPY`, `ENTER_BOARD_HINT_COPY`, `viewerHint`; `rankLineCopy` "#N this week" path; browser UAT legs 3, 4, 6 |
| 4 | Server-side scoring `correct_guess::int + move_quality` (max 3), pinned to `trainScore.ts` by a parity test (D-01) | VERIFIED | `app/services/train_score.py`, SQL CASE built from `MOVE_TIER_POINTS`/`MOVE_QUALITY_TIER` in the repository; `test_train_score_parity.py` regex-extracts `GUESS_POINTS`, `MOVE_TIER_POINTS`, `TRAIN_POINTS_PER_PUZZLE` from the .ts (6 tests pass); real-row scoring test pins 9 points / 6 puzzles |
| 5 | Points counts every solve; Accuracy and its qualifier exclude `SHARP_FILLER`; only `solved_at` rows count (D-01) | VERIFIED | `_NON_FILLER` filter on nf columns, range predicate excludes NULL `solved_at`; repository tests `test_filler_solves_count_on_points_but_not_in_non_filler_totals`, `test_unsolved_rows_are_not_counted` pass |
| 6 | One ISO UTC week keyed on `solved_at`, half-open, deadline split by solve timestamp, time from `dev_now_utc` only (D-02) | VERIFIED | `week_window`, `fetch_week_aggregates` predicate `>= week_start, < week_end`; no `session_date` or `datetime.now` in the two modules (grep); `test_window_is_half_open_on_solved_at`, `test_deadline_splits_one_session_across_two_weeks` pass; countdown from server `seconds_remaining` (see WR-03 for the rollover edge) |
| 7 | Qualifier: tentative until 20 non-filler puzzles, ranked and marked; zero non-filler = no Accuracy entry, specific not-on-board copy (D-03, D-19) | VERIFIED | `ACCURACY_QUALIFY_MIN_PUZZLES = 20`, `_entry_for` returns None for no non-filler, `puzzlesToQualifyCopy`, `ACCURACY_NOT_ENTERED_COPY`; service and card tests pass |
| 8 | Competition ranks (1,1,1,4), ties ordered by puzzles desc; top 5 + viewer with 2 above and 2 below with gap marker; Points "N points to pass <name>" (D-04) | VERIFIED | `_competition_ranks`, `_order_key`, `_slice_indices`, `_pass_target`; rank, slice and pass-target tests (including slice gap cases) pass |
| 9 | Identity: lichess, else chess.com, else "Anonymous"; no verification code (D-05, D-15) | VERIFIED | `display_name`; no blocklist/OAuth code added; `test_display_name_precedence_and_blank_handling` passes; card test renders server-sent "Anonymous" |
| 10 | Opt-out: server-persisted `users.leaderboard_hidden`; Privacy card in settings overlay outside Reset, hidden for guests; hidden user absent from others' boards and ranks, own private "Hidden from others" row (D-06, D-13, D-16) | VERIFIED | Migration `c4e7a91d2b58` (single alembic head), model, `UserProfileUpdate`/`Response`, `LeaderboardPrivacyCard` after Reset button and outside `isAtDefaults`; `test_users_router.py` round-trip (default false, true persists, omitted/null unchanged, non-bool 422); `test_profile_opt_out_hides_user_from_other_viewers`, `test_hidden_viewer_sees_private_row`; UAT leg 5 |
| 11 | Guests never appear to others; guest sees ghost row "You (guest)" with neighbours plus "Sign up to claim your spot" and `SignupAskActions` (D-14) | VERIFIED | Visibility filtering before ranking in `build_board`; `test_guest_viewer_sees_ghost_row`, `test_guest_never_appears_on_or_shifts_a_registered_viewers_board`; `LeaderboardGuestCta` with `source="train-leaderboard"`; UAT leg 6 |
| 12 | Score screen: compact rank line per board under "Points: x/y"; rank with vs without this session (IDOR-safe); "(up N)" only on improvement, never "(down N)"; guest "You'd be #N"; first-of-week "#N this week" (D-11, D-12, D-17, D-18) | VERIFIED | `fetch_session_contribution` scoped to `DrillSolve.user_id == user_id`; `_rank_without` against the same visible others; `rankLineCopy` (`before > rank` only); `TrainScoreRankLines` wired in `TrainScoreScreen`, `sessionId` passed from `Train.tsx`; `test_foreign_session_id_ignored`, `test_rank_without_session_follows_the_viewer_across_two_sessions`, session_id 422 validation, rank-line tests pass; UAT legs 3, 6 |
| 13 | Privacy page carries the leaderboard line; "Last updated" bumped | VERIFIED | `Privacy.tsx` diff; UAT leg 7 |
| 14 | Wire contract: no user id/email in any row; `SolveResponse` unchanged; no medal logic or snapshot table | VERIFIED | `test_response_key_set_has_no_user_ids` and `test_solve_response_key_set_is_exactly_the_wire_contract` (tests/routers/test_train.py, 81 pass); only "medals" hit in app/ is a docstring noting `week_window` is reusable |
| 15 | Umami `tab-switch` for hand switches only; toggle sends no event; CHANGELOG bullet present | VERIFIED | `trackFeature('tab-switch', ...)` guarded against `''` and same-tab; analytics registry extended; CHANGELOG `[Unreleased]` line 14 |

**Score:** 15/15 truths verified (0 present-but-behavior-unverified). Behavior-dependent truths (D-12 session delta, hidden/guest rank exclusion, deadline split, once-per-week rollover) each have a passing behavioral test; the one gap in that area is the early-fire edge in WR-03, not covered by a test.

### Decision-ID Accounting (REQUIREMENTS.md does not exist)

PLAN frontmatter `requirements:` cite D-01..D-19; each is a locked decision in 230-CONTEXT.md.

| D-ID | Cited by | Honored |
|------|----------|---------|
| D-01 | 01, 02 | Yes (truths 4, 5) |
| D-02 | 01, 02, 03 | Yes (truth 6; WR-03 caveat on rollover edge) |
| D-03 | 01, 03 | Yes (truth 7) |
| D-04 | 01, 03 | Yes (truth 8) |
| D-05 | 01 | Yes (truth 9) |
| D-06 | 01, 02, 04 | Yes (truths 10, 11, 14) |
| D-07 | 03 | Yes (truth 1) |
| D-08 | 03 | Yes (truth 2) |
| D-09 | 03 | Yes (truth 1) |
| D-10 | 03 | Yes (truth 1) |
| D-11 | 05 | Yes (truth 12) |
| D-12 | 02, 05 | Yes (truth 12) |
| D-13 | 01, 02, 03, 04 | Yes (truth 10) |
| D-14 | 01, 02, 03 | Yes (truth 11) |
| D-15 | 01, 03 | Yes (truth 9) |
| D-16 | 01, 04 | Yes (truth 10) |
| D-17 | 05 | Yes (truth 12) |
| D-18 | 02, 05 | Yes (truth 12) |
| D-19 | 01, 03, 05 | Yes (truth 7, 12) |

All 19 IDs are cited by at least one plan and none is orphaned. No ROADMAP-registered requirement IDs exist ("Requirements: TBD").

### Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `alembic/versions/..._c4e7a91d2b58_users_leaderboard_hidden.py` | VERIFIED | column + partial index, downgrade symmetrical, `alembic heads` = single head `c4e7a91d2b58` |
| `app/services/train_score.py` | VERIFIED | constants + parity test |
| `app/repositories/train_leaderboard_repository.py` | VERIFIED | one GROUP BY aggregate + caller-scoped contribution; sequential awaits |
| `app/services/train_leaderboard.py` | VERIFIED | pure ranking/slicing/visibility, wired from router |
| `app/routers/train.py` GET `/train/leaderboard` | VERIFIED | `Query(ge=1, le=2**31-1)`, `NowUtc` dependency, Sentry capture on exception |
| `TrainLeaderboardCard.tsx`, `trainLeaderboard.ts`, `useTrainLeaderboard.ts` | VERIFIED | wired into `TrainStartScreen`; query key invalidated by dev clock, rollover and opt-out |
| `TrainScoreRankLines.tsx` | VERIFIED | wired into `TrainScoreScreen`, session id from `Train.tsx` |
| `LeaderboardPrivacyCard.tsx`, `useSetLeaderboardHidden` | VERIFIED | wired into `SettingsPanel`; see WR-02 |

### Key Link Verification

| From | To | Status |
|------|----|--------|
| router -> `get_weekly_leaderboard(... session_id=session_id)` | service | WIRED |
| service -> `fetch_week_aggregates` then `fetch_session_contribution` (sequential) | repository | WIRED |
| repository points CASE -> `MOVE_TIER_POINTS` | `train_score.py` | WIRED |
| parity test -> `frontend/src/lib/trainScore.ts` | regex extraction | WIRED |
| `TrainStartScreen` -> `TrainLeaderboardCard` (3 branches) | card | WIRED |
| `Train.tsx` -> `TrainScoreScreen sessionId` -> `TrainScoreRankLines` -> `useTrainLeaderboard({sessionId})` -> `GET ?session_id=` | score screen | WIRED |
| `SettingsPanel` -> `LeaderboardPrivacyCard` -> `PUT /users/me/profile` -> `update_profile` (None-filter keeps `False`) | profile | WIRED |

### Data-Flow Trace (Level 4)

Board rows originate from the real `drill_solves` GROUP BY (no static fallback); rank lines come from the server response; privacy switch reads `useUserProfile().data.leaderboard_hidden` populated from the DB column. FLOWING.

### Behavioral Spot-Checks and Test Runs (executed by verifier)

| Check | Command | Result |
|-------|---------|--------|
| Backend phase tests | `uv run pytest tests/routers/test_train_leaderboard.py tests/services/test_train_leaderboard.py tests/repositories/test_train_leaderboard_repository.py tests/services/test_train_score_parity.py tests/test_users_router.py -n auto` | 107 passed |
| Existing train router suite (SolveResponse key-set pin) | `uv run pytest tests/routers/test_train.py -n auto` | 81 passed |
| Lint / types | `uv run ruff check app tests`, `uv run ty check app/` | clean |
| Alembic heads | `uv run alembic heads` | single head `c4e7a91d2b58` |
| Frontend types | `npx tsc -b` | exit 0 |
| Frontend phase tests | vitest on leaderboard lib, card, rank lines, score screen, start screen, settings, analytics, solveLoop | 11 files, 271 passed |

Full-suite numbers in 230-05-SUMMARY (5071 backend, 4892 frontend) were not re-run; the targeted subsets above reproduce green.

### Probe Execution

SKIPPED (no probes declared by any plan).

### Requirements Coverage

No REQUIREMENTS.md. Locked decisions D-01..D-19 accounted for above; 19/19 satisfied.

### Anti-Patterns Found

No TBD/FIXME/XXX/TODO/HACK markers in files changed by the phase (grep). No stubs, no hardcoded empty rendering paths. Function-size/nesting gate reported clean in plan 05 and ruff/ty are clean here.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/src/hooks/useUserProfile.ts` | 35-38 | Overwrites cached profile with PUT response whose `impersonation` is hard-coded null (`app/routers/users.py:148`) | Warning (WR-02, confirmed) | Admin loses impersonation pill after toggling Hide while impersonating |
| `frontend/src/components/train/TrainLeaderboardCard.tsx` | 218-245 | One-shot `rolledOverWeekEnd` guard plus truncating server/client `seconds_remaining` | Warning (WR-03, confirmed by reading code) | If the refetch lands before the true deadline, last week's board stays on "ending now" until remount/refocus. Narrow window |
| `app/repositories/train_leaderboard_repository.py` | 52-59 (source `train_repository.py` ~2963-2977) | Public rankings sum a client-asserted `move_quality` for off-key moves | Warning (WR-01, confirmed against `record_solve`) | A direct API caller can bank up to 2 of 3 points per puzzle; undecided in CONTEXT |
| `app/services/train_leaderboard.py` | 136, 247, 300 | Parameter `viewer_visibility` shadows same-named function | Info (IN-01) | Latent trap only |
| `TrainLeaderboardCard.tsx` | 88-94 | "Hidden from others" / "(tentative)" inside the truncating name span | Info (IN-02) | Cue cut off at narrow widths; also seen in UAT leg 2 |

### Human Verification Required

#### 1. Owner triage of open review warnings

**Test:** Review WR-01, WR-02, WR-03 (and optionally IN-01, IN-02) in `230-REVIEW.md` / `230-REVIEW-DISPOSITION.md` and set a disposition for each.
**Expected:** WR-01: record as an accepted risk in 230-CONTEXT.md/SEED-185 or schedule a server-side clamp of off-key tiers. WR-02 and WR-03: fix now (both are one-file frontend changes with the fix sketched in the review) or defer knowingly.
**Why human:** WR-01 is a design/security call that no locked decision covers (D-05 accepts impersonation only). WR-02/WR-03 are real but outside the phase goal's contract, so they do not fail a truth; they need an owner disposition rather than a verifier verdict.

Browser UAT legs 1-7 were completed by the orchestrator (230-05-SUMMARY "Browser UAT") and are accepted as completed human-check evidence; they are not re-listed.

### Gaps Summary

No goal-blocking gaps. Every roadmap contract item and every locked decision D-01..D-19 is implemented, wired and covered by passing behavioral tests; the migration chain is a single head; no medal/snapshot scope creep; `SolveResponse` untouched. The phase is marked `human_needed` only because three code-review warnings remain `open` in the disposition file and WR-01 in particular is an unrecorded owner risk decision. If the owner accepts all three (or fixes them), the phase can move to `passed` without a re-plan.

---

_Verified: 2026-10-04_
_Verifier: Claude (gsd-verifier)_

## Owner Triage (2026-10-04, orchestrator)

The single human item (disposition of the open review warnings) is resolved; see `230-REVIEW-DISPOSITION.md`.

- **WR-01:** accepted risk for the leaderboards. Recorded in SEED-185 as a blocker the medals phase must close (server-side verification or clamp of off-key tiers) before any medal is awarded.
- **WR-02:** won't fix (owner did not select it; admin-only, cosmetic).
- **WR-03:** fixed in 3c27c91f2. `seconds_remaining` is rounded up server-side, and the card retries the rollover refetch every 2 s (max 3) while the response still carries the old `week_end`. Two new card tests fail with the old component and pass with the fix; a backend test pins the round-up.
- **IN-01 / IN-02:** fixed in 3c27c91f2. IN-02 was re-checked in the browser at 375 px: "(tentative)" now wraps fully visible below the name, with no overflow.

Post-fix gates: ruff, ty, function-size check, the leaderboard backend suites (76 passed), frontend lint, build (tsc -b), knip and all train component tests (501 passed) are green.
