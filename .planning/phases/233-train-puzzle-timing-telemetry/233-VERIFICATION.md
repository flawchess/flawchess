---
phase: 233-train-puzzle-timing-telemetry
verified: 2026-10-05T19:00:00Z
status: passed
score: 18/18 must-haves verified (2 by owner override)
covered_files:
  - ".planning/phases/233-train-puzzle-timing-telemetry/233-01-PLAN.md"
  - ".planning/phases/233-train-puzzle-timing-telemetry/233-01-SUMMARY.md"
  - ".planning/phases/233-train-puzzle-timing-telemetry/233-02-PLAN.md"
  - ".planning/phases/233-train-puzzle-timing-telemetry/233-02-SUMMARY.md"
  - ".planning/phases/233-train-puzzle-timing-telemetry/233-03-PLAN.md"
  - ".planning/phases/233-train-puzzle-timing-telemetry/233-03-SUMMARY.md"
  - ".planning/phases/233-train-puzzle-timing-telemetry/233-04-PLAN.md"
  - ".planning/phases/233-train-puzzle-timing-telemetry/233-04-SUMMARY.md"
  - ".planning/phases/233-train-puzzle-timing-telemetry/233-05-PLAN.md"
  - ".planning/phases/233-train-puzzle-timing-telemetry/233-05-SUMMARY.md"
  - "CHANGELOG.md"
  - "alembic/versions/20261005_120000_a7c3e9d41f02_drill_solves_telemetry.py"
  - "app/models/drill_solve.py"
  - "app/repositories/train_repository.py"
  - "app/routers/train.py"
  - "app/schemas/train.py"
  - "frontend/src/api/__tests__/client.test.ts"
  - "frontend/src/api/client.ts"
  - "frontend/src/components/train/TrainLineStepper.tsx"
  - "frontend/src/components/train/TrainReveal.tsx"
  - "frontend/src/components/train/TrainSolveScreen.tsx"
  - "frontend/src/components/train/__tests__/TrainLineStepper.test.tsx"
  - "frontend/src/components/train/__tests__/TrainReveal.test.tsx"
  - "frontend/src/components/train/__tests__/TrainSolveScreen.restoredGameArrow.test.tsx"
  - "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx"
  - "frontend/src/hooks/__tests__/useTrainFreePlay.test.ts"
  - "frontend/src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts"
  - "frontend/src/hooks/useInstallPrompt.ts"
  - "frontend/src/hooks/useTrainFreePlay.ts"
  - "frontend/src/hooks/useTrainPuzzleTelemetry.ts"
  - "frontend/src/lib/__tests__/deviceClass.test.ts"
  - "frontend/src/lib/__tests__/trainRevealCache.test.ts"
  - "frontend/src/lib/__tests__/visibleStopwatch.test.ts"
  - "frontend/src/lib/deviceClass.ts"
  - "frontend/src/lib/trainRevealCache.ts"
  - "frontend/src/lib/trainTelemetry.ts"
  - "frontend/src/lib/visibleStopwatch.ts"
  - "frontend/src/pages/Privacy.tsx"
  - "frontend/src/pages/__tests__/Privacy.test.tsx"
  - "frontend/src/pages/__tests__/Train.solveLoop.test.tsx"
  - "frontend/src/types/train.ts"
  - "tests/routers/test_train.py"
  - "tests/schemas/test_train_telemetry_parity.py"
  - "tests/schemas/test_train_telemetry_schema.py"
covered_digest: "v3:sha256:1b65f9aeb4f6366cbbb26e9580a0a2040240e9dd00a7c2e0e7c66f61fa946c08"
behavior_unverified: 2
overrides_applied: 2
overrides:
  - must_have: "C7: a real browser unload / tab background / nav-away / Analyze exit lands exit='pagehide', and return + Next overwrites with exit='next' (D-03, D-06, D-07)"
    reason: "Owner accepted the recorded orchestrator evidence in 233-UAT.md test 1 (result: pass). Local Chrome drove the dev build at commits 54bf184a0/c741b6334; drill_solves rows for sessions 231/232 showed exit=pagehide on nav-away, Analyze, tab switch and tab close, and exit=next with larger review_ms and review_hidden_ms 12015 after return + Next, including the last-puzzle Next. The verifier did not observe this at runtime."
    accepted_by: "Adrian Imfeld (owner, via chat 'mark as passed')"
    accepted_at: "2026-10-05T19:21:13Z"
  - must_have: "C8: desktop 800 ms hover-hold counts a card and a real phone tap counts at once (D-11)"
    reason: "Owner override. Desktop leg passed in 233-UAT.md test 2 (2 s hover counted, measured 233 ms hover did not; review_cards_opened 1). The phone-tap leg was not run on a real device (deferred); it is covered by unit tests in useTrainPuzzleTelemetry.test.ts."
    accepted_by: "Adrian Imfeld (owner, via chat 'mark as passed')"
    accepted_at: "2026-10-05T19:21:13Z"
override_note: "Owner marked the phase passed on 2026-10-05T19:21:13Z after the orchestrator browser UAT; C8 phone-tap leg deferred (needs a real phone)."
behavior_unverified_items:
  - truth: "A real browser unload / tab background / in-app nav-away / Analyze-then-close lands a keepalive flush with exit='pagehide' in drill_solves.telemetry, and a return plus Next overwrites it with exit='next' (D-03, D-06, D-07)"
    test: "On a dev build: open a Train reveal and close the tab; repeat for switch-tab-and-return, nav-link away, and Analyze-then-close. Inspect drill_solves.telemetry via flawchess-db after each. Then return to a reveal that was hidden and press Next."
    expected: "Each non-Next exit leaves review_* keys with exit='pagehide'; a return plus Next overwrites to exit='next' with larger cumulative totals; no 401 and no duplicate-row corruption."
    why_human: "jsdom cannot unload or background a page. Unit tests prove fetch is called with keepalive + Bearer and that the guards dedupe, not that the browser delivers the request on unload."
  - truth: "Desktop 800 ms hover-hold counts a card as opened and a real phone tap counts at once (D-11)"
    test: "On a desktop dev build hover a solution card for under and over 800 ms, and on a real phone tap a card; inspect review_cards_opened in drill_solves.telemetry after Next."
    expected: "A fly-over under 800 ms does not count; a hold of 800 ms or more counts; a phone tap counts immediately; review_cards_total equals the cards shown."
    why_human: "jsdom has no real pointer dwell or touch. The threshold constant and counting rule are unit-tested, the in-browser feel is not."
human_verification:
  - test: "C7: real-browser exit flushes (see behavior_unverified_items[0])"
    expected: "exit='pagehide' lands for close-tab, switch-tab, nav-away and Analyze-then-close; return plus Next lands exit='next'"
    why_human: "jsdom cannot unload or background a page"
  - test: "C8: 800 ms desktop hover feel and real phone tap (see behavior_unverified_items[1])"
    expected: "Fly-overs under 800 ms are ignored, holds and phone taps count"
    why_human: "jsdom has no real pointer dwell or touch"
---

# Phase 233: Train Per-Puzzle Timing & Engagement Telemetry Verification Report

**Phase Goal:** Record HOW each Train puzzle was solved, not just whether: client-measured think time, review time and a reveal-engagement summary, stored on the solve row (one nullable `drill_solves.telemetry` JSONB, merged never overwritten, SQL NULL when absent) so they join to the outcome and to the next attempt at the same SR item. Grading untouched. Go-forward only, no backfill.
**Verified:** 2026-10-05
**Status:** passed (owner override, see frontmatter)
**Re-verification:** No, initial verification

All automated evidence supports the goal. Two truths are present and wired but depend on real-browser behavior jsdom cannot exercise (C7 unload flushes, C8 hover/touch feel); they route to human verification and do not count toward the score. No blocker was found. The two code-review warnings are real but do not defeat a locked must-have (details below).

## Goal Achievement

### Observable Truths

Contract: ROADMAP Phase 233 goal plus locked decisions D-01..D-14 (REQUIREMENTS.md does not exist; ROADMAP says "Requirements: TBD"). The roadmap's `navigator.sendBeacon` is superseded by CONTEXT D-06 (keepalive fetch); judged against D-06.

| #  | Truth | Status | Evidence |
| -- | ----- | ------ | -------- |
| 1  | D-01 storage: one nullable `drill_solves.telemetry` JSONB, Alembic migration, single head, no backfill | VERIFIED | `alembic/versions/20261005_120000_a7c3e9d41f02_drill_solves_telemetry.py` adds `JSONB(none_as_null=True)` nullable, no default, no backfill statement. `uv run alembic heads` = `a7c3e9d41f02 (head)`, current = head. Model column at `app/models/drill_solve.py:196`. |
| 2  | D-01 merge never overwrite; SQL NULL when absent | VERIFIED | `_merged_telemetry` = `coalesce(telemetry,'{}') \|\| patch` (`train_repository.py:2871`); `record_solve` adds the column to the claim UPDATE only when a patch exists (`:3056`); both routers use `model_dump(exclude_none=True)`. Real-DB tests pass: `test_telemetry_solve_without_telemetry_stays_sql_null` (asserts `telemetry IS NULL` and `jsonb_typeof`), `test_review_flush_merges_into_solved_row`, `..._last_write_wins_per_key`, `..._on_row_solved_without_telemetry_creates_object`. |
| 3  | D-01 boundary validation: `extra="forbid"`, typed/capped fields, `v` | VERIFIED | `SolveTelemetry` / `ReviewTelemetry` in `app/schemas/train.py` (closed keys, `Literal`, strict bool/int, clamp-not-reject caps, `v: Literal[1]`). `tests/schemas/test_train_telemetry_schema.py` and `test_review_flush_rejects_bad_body` pass. |
| 4  | D-02 think time `guess_ms`/`move_ms` measured client-side, sent on the solve POST, optional so a stale bundle still solves | VERIFIED | `useTrainPuzzleTelemetry` frozen snapshot wired at `TrainSolveScreen.tsx` (`markGuess`/`markMove`, `telemetry: puzzleTelemetry.solveTelemetry()` in the solve body). `SolveRequest.telemetry` optional with wrap validator dropping invalid telemetry (`test_telemetry_invalid_telemetry_still_solves`). Screen test asserts the real POST body carries the keys; retry resends the identical object. |
| 5  | D-03 review route: `POST /train/sessions/{id}/solves/{position}/review`, owner-scoped, solved rows only, accepted after session completed/expired, 404 otherwise | VERIFIED | `record_puzzle_review` (`app/routers/train.py:195`) + `merge_solve_telemetry` single UPDATE filtering `user_id` (from `current_active_user`), `solved_at IS NOT NULL`, no session-status check; `Path` bounds. Tests: `_rejects_other_users_row`, `_rejects_unsolved_row`, `_accepts_completed_and_expired_session`, `_path_bounds`, `_unknown_position` all pass (53 telemetry/review backend tests green when I ran them). |
| 6  | D-03 client flush wiring: Next flush once per puzzle, plus every non-Next exit (hidden, pagehide, unmount) through one funnel; no per-click events | VERIFIED (wiring) | `flushReviewOnNext` called first in `handleNextFromReveal`; `flushReviewNonNext` fed by `visibilitychange`, `window` `pagehide`, and aliveRef-guarded unmount microtask. Hook tests (9 `exit:` cases incl. StrictMode, Next-then-unmount no-op, hidden-then-pagehide dedupe) pass. Real delivery on unload: see truth 15. |
| 7  | D-04 visible-only time, `hidden` stored separately, durations capped ~30 min | VERIFIED | `visibleStopwatch.ts` pure accumulator; `think_hidden_ms` / `review_hidden_ms` keys; `TELEMETRY_DURATION_CAP_MS = 1800000` mirrored and CI-locked by `test_train_telemetry_parity.py`; stopwatch and hook tests pass. Note: D-04's single `hidden_ms` was deliberately split into two keys so the per-key merge cannot collide (documented in the schema docstring and 233-01 SUMMARY); an owner-visible refinement, not a gap. |
| 8  | D-05 grading untouched: telemetry never an input to `move_quality`, `correct_guess`, scoring, SR ladder, leaderboard | VERIFIED | `grep telemetry app/` shows reads only in the model, schema, the two merge writers and the router pass-through; nothing in `app/services/`, scoring or leaderboard code. `frontend/src/lib/trainScore.ts` and all `app/services/` untouched by the phase diff. `test_telemetry_does_not_change_grading` passes (identical response and SR ladder with/without telemetry). |
| 9  | D-06 transport: no `sendBeacon`; keepalive fetch with Bearer header for the unload flush; Next uses normal `apiClient` | VERIFIED | `postReviewKeepalive` in `frontend/src/api/client.ts` (`fetch(..., {keepalive: true, headers: {Authorization}})`, same-origin relative URL, bypasses 401 interceptor, captures 5xx only). `grep sendBeacon frontend/src` (non-test) = no hits. `client.test.ts#postReviewKeepalive` passes. |
| 10 | D-07 `exit` set on every flush; no extra shown ping | VERIFIED | `exit: Literal["next","pagehide"]` is required in `ReviewTelemetry`; `buildReviewTelemetry` always sets it; no third write per puzzle. Semantics documented: `pagehide` = left the reveal without pressing Next. |
| 11 | D-08 leaderboard toggle already tracked; no impression event added | VERIFIED | `TrainLeaderboardCard.tsx:392` `trackFeature('tab-switch', {target: LEADERBOARD_TAB_TARGET[next]})`; the file and `analytics.ts` have an empty diff over the phase; `TrainLeaderboardCard.test.tsx` passes (I ran it). |
| 12 | D-09 device class: `client: "mobile" \| "desktop"` Literal inside telemetry, reusing the project's UA definition; one Privacy line | VERIFIED (with WR-01 caveat) | `lib/deviceClass.ts` extracted from `useInstallPrompt` (kept verbatim per D-09's "reuse an existing signal"); `Privacy.tsx` item added; `Privacy.test.tsx` passes. Caveat: modern iPadOS sends a Macintosh UA, so iPads are labelled `desktop` (WR-01). |
| 13 | D-10 no `train-review` Umami mirror | VERIFIED | `analytics.ts` unchanged; no `train-review` string. |
| 14 | D-11..D-14 engagement counters: closed 7-key set (`review_cards_opened`, `review_cards_total`, `review_line_steps`, `review_explored`, `review_explore_moves`, `review_analyze_opened`, `review_walkthrough`), distinct-card counting, 800 ms hover rule (logic), mobile tap / departed-board click count at once, walkthrough sticky flag, capped | VERIFIED (logic) | `TrainLineStepper.onUserStep` (goTo only), `useTrainFreePlay.onUserMove`, `TrainReveal` `onCardEngage`/`onCardsTotalChange`, hook hover timer with `REVIEW_CARD_HOVER_MIN_MS = 800` and hidden-page cancellation. Test "closed set: a flush body has exactly the 11 D-14 keys" and the `cards:` / `counters:` hook tests pass. TrainReveal hook-order refactor covered by an explicit render test. No flip or Solution-return counter exists. Real hover/touch feel: see truth 16. |
| 15 | Discretion items: one review timer across the Analyze round-trip (reveal cache), resumed flag, StrictMode safety | VERIFIED | `trainRevealCache.reviewTelemetry` + update-only mirror; `analyze:` hook tests and `TrainSolveScreen` "Analyze saves the review snapshot" test pass (116 tests across TrainSolveScreen, Train.solveLoop, restoredGameArrow green). |
| 16 | Go-forward only, no backfill | VERIFIED | Migration has no data step; composition inserts never set the column; no backfill script in the diff. |
| 17 | [PRESENT_BEHAVIOR_UNVERIFIED] A real browser unload/background/nav-away/Analyze-close delivers the flush (C7) | PRESENT_BEHAVIOR_UNVERIFIED | Transport and listeners are present and wired, with unit evidence; browser delivery is not exercised. See Human Verification. |
| 18 | [PRESENT_BEHAVIOR_UNVERIFIED] Desktop 800 ms hover feel and real phone tap (C8) | PRESENT_BEHAVIOR_UNVERIFIED | Rule and constant are unit-tested; real pointer/touch feel is not. See Human Verification. |

**Score:** 16/18 truths verified (rows 1-16); 2 present and wired but behavior-unverified (rows 17-18, C7/C8). No FAILED truth.

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `alembic/versions/..._a7c3e9d41f02_drill_solves_telemetry.py` | nullable JSONB column | VERIFIED | Single head, nullable, no default |
| `app/models/drill_solve.py` | `telemetry` mapped column | VERIFIED | `JSONB(none_as_null=True)`, default None |
| `app/schemas/train.py` | `SolveTelemetry`, `ReviewTelemetry`, caps | VERIFIED | Substantive, wired in `SolveRequest` and the route |
| `app/repositories/train_repository.py` | merge helper, `record_solve` param, `merge_solve_telemetry` | VERIFIED | Substantive, called from router |
| `app/routers/train.py` | review route | VERIFIED | Wired, auth + Sentry shape |
| `frontend/src/hooks/useTrainPuzzleTelemetry.ts` | think/review timers, counters, flush funnel | VERIFIED | Used by `TrainSolveScreen` |
| `frontend/src/lib/{visibleStopwatch,trainTelemetry,deviceClass,trainRevealCache}.ts` | builders, constants, device class, cache mirror | VERIFIED | All imported and used |
| `frontend/src/api/client.ts` | `recordReview`, `postReviewKeepalive` | VERIFIED | Both called from the hook |
| `frontend/src/pages/Privacy.tsx` | disclosure line | VERIFIED | Rendered-page test passes |
| `CHANGELOG.md` | `[Unreleased]` bullet | VERIFIED | Present under Changed |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `TrainSolveScreen` | solve POST | `telemetry: puzzleTelemetry.solveTelemetry()` | WIRED | Frozen snapshot, retry-safe |
| `handleNextFromReveal` | `recordReview` | `flushReviewOnNext()` before `handleNext()` | WIRED | Called first (ordering matters, tested) |
| `visibilitychange` / `pagehide` / unmount | `postReviewKeepalive` | `flushReviewNonNext` | WIRED | Single call site in hook |
| `TrainReveal` card handlers | hook counters | `onCardEngage`, `onCardsTotalChange`, `onLineUserStep` | WIRED | Props passed from `TrainSolveScreen` |
| `useTrainFreePlay` | hook counters | `onUserMove: puzzleTelemetry.onExploreMove` | WIRED | |
| Analyze click | reveal cache | `snapshotReviewForAnalyze()` into `saveTrainRevealCache` | WIRED | |
| Review route | `drill_solves.telemetry` | `merge_solve_telemetry` single UPDATE | WIRED | Real-DB tests |
| TS caps | Python caps | `test_train_telemetry_parity.py` regex lock | WIRED | Mutation-proven per 233-02 SUMMARY |

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Real Data | Status |
| -------- | ---- | ------ | --------- | ------ |
| solve POST telemetry | `guess_ms`, `move_ms`, `think_hidden_ms`, `client`, `resumed` | stopwatch + Date.now + UA | Yes | FLOWING |
| review flush | `review_*` | stopwatch + countersRef fed by real UI callbacks | Yes | FLOWING |
| `drill_solves.telemetry` | JSONB | merge UPDATE | Yes (asserted via SQL in tests) | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Backend telemetry/review/parity/schema tests | `uv run pytest tests/routers/test_train.py tests/schemas/test_train_telemetry_parity.py tests/schemas/test_train_telemetry_schema.py -k "telemetry or review_flush or parity"` | 53 passed | PASS |
| Frontend telemetry units, client, Privacy, leaderboard, reveal, stepper, free-play | `npx vitest run` over 8 targets (72 files) | 1345 passed | PASS |
| TrainSolveScreen, Train.solveLoop, restoredGameArrow | `npx vitest run` over 3 files | 116 passed | PASS |
| Lint/type | `ruff check app tests`, `ty check app/ tests/` | clean | PASS |
| Alembic head | `uv run alembic heads` / `current` | `a7c3e9d41f02 (head)` | PASS |
| Full pre-merge gate | not re-run (plan 05 reports green: pytest 5197, vitest 5146, lint/build/knip clean) | n/a | taken from SUMMARY, spot-checked above |

### Probe Execution

Step 7c: SKIPPED (no probe scripts declared by this phase).

### Requirements Coverage

No REQUIREMENTS.md IDs. Locked decisions D-01..D-14, all accounted for:

| Decision | Status | Evidence |
| -------- | ------ | -------- |
| D-01 | SATISFIED | truths 1-3 |
| D-02 | SATISFIED | truth 4 |
| D-03 | SATISFIED (delivery on real unload needs human, truth 17) | truths 5, 6 |
| D-04 | SATISFIED (hidden key split into two, documented) | truth 7 |
| D-05 | SATISFIED | truth 8 |
| D-06 | SATISFIED | truth 9 |
| D-07 | SATISFIED | truth 10 |
| D-08 | SATISFIED | truth 11 |
| D-09 | SATISFIED (iPad caveat WR-01) | truth 12 |
| D-10 | SATISFIED | truth 13 |
| D-11 | SATISFIED in logic (feel needs human, truth 18) | truth 14 |
| D-12, D-13, D-14 | SATISFIED | truth 14 |

No orphaned requirements.

### Anti-Patterns Found

TBD/FIXME/XXX scan across the 34 changed code files: none. No stubs, no static-return data sources. The code-review items are treated below.

### Code Review Findings vs Must-Haves

Disposition file records all six as `open` (untriaged).

| Finding | Defeats a must-have? | Assessment |
| ------- | -------------------- | ---------- |
| WR-01 iPadOS classified `desktop` | No (WARNING) | D-09 explicitly says to reuse the existing UA definition, which is what shipped, so the locked decision is met. But the `client` data is irreversibly mislabelled for modern iPads from day one, and the Privacy copy says "phone or computer". Recommend the owner either apply the `Macintosh` + `maxTouchPoints > 1` check for telemetry only, or accept and document it, before deploy (data cannot be regenerated). |
| WR-02 Next flush is plain XHR, guard set before response, not retried | No (WARNING) | D-06 says "Next can use the normal `apiClient` call" and CONTEXT locks the client-side "flushed" guard, so this is the specified design. The residual risk is a lost Next flush (tab closed just after Next, transient failure) leaving `exit='pagehide'`, which skews the D-07 "puzzle N+1 was shown" derivation for that row. Cheap fix: send Next through `postReviewKeepalive` too, or set the guard in `onSuccess`. Owner call. |
| IN-01 `Literal[1]` not parity-tested against the constant | No | Add a one-line test before any schema-version bump. |
| IN-02 Dropped solve telemetry is unobservable | No | D-02 mandates the silent drop; a breadcrumb would help detect frontend/backend drift. |
| IN-03 `_merged_telemetry` trusts callers to exclude None | No | Both callers use `exclude_none=True` today (verified); harden the helper. |
| IN-04 First-puzzle `guess_ms` includes the intro stepper | No | Bounded to one row per user; note the exclusion rule in the SEED-190 analysis. |

### Human Verification Required

#### 1. Real-browser exit flushes (C7)

**Test:** On a dev build, open a Train reveal and (a) close the tab, (b) switch tabs and return, (c) click a nav link away, (d) leave via Analyze and close without returning. Inspect `drill_solves.telemetry` (flawchess-db MCP) after each. Then hide a reveal, return, and press Next.
**Expected:** Each non-Next exit leaves `review_*` keys with `exit='pagehide'`; return plus Next overwrites with `exit='next'` and larger cumulative totals; no 401s.
**Why human:** jsdom cannot unload or background a page; unit tests prove `fetch` is invoked with `keepalive` and the Bearer header, not that the browser delivers it during unload.

#### 2. Hover/tap feel (C8)

**Test:** Desktop dev build: hover a solution card for under and over 800 ms. Real phone: tap a card. Press Next and inspect `review_cards_opened` / `review_cards_total`.
**Expected:** Fly-overs under 800 ms are not counted, holds of 800 ms or more are, a phone tap counts immediately, total equals the cards shown.
**Why human:** jsdom has no real pointer dwell or touch.

### Gaps Summary

No gaps and no blockers. Every locked decision D-01..D-14 is implemented and backed by passing tests (backend tests run against the real dev DB, including SQL `IS NULL` and merge semantics). Status is `human_needed` solely because C7 and C8 need a real browser, and because the two review warnings (WR-01, WR-02) are open owner decisions that affect irreversible data quality; neither contradicts a locked must-have.

---

_Verified: 2026-10-05_
_Verifier: Claude (gsd-verifier)_

## Post-verification updates (2026-10-05, orchestrator)

- **WR-01 fixed** (54bf184a0): `telemetryClient()` also treats a Macintosh UA with >= 2 touch points (iPadOS) as `mobile`; `isMobileUserAgent()` and the install prompt are unchanged (D-06). New deviceClass tests; reverting the fix fails the iPadOS test.
- **WR-02 fixed** (c741b6334): the Next review flush now uses `postReviewKeepalive` like every other exit; `trainApi.recordReview` removed. Reverting the call fails 28 hook/screen tests. Frontend lint, build and full suite (5147) green.
- **Browser UAT** (233-UAT.md): C7 passed on every leg (nav-away, Analyze, tab switch, return + Next, last-puzzle Next, tab close), C8 desktop hover leg passed. Only the C8 phone-tap leg remains (needs a real phone).
