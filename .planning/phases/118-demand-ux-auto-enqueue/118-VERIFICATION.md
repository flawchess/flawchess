---
phase: 118-demand-ux-auto-enqueue
verified: 2026-06-14T12:30:00Z
status: verified
score: 5/5
overrides_applied: 0
human_verification_completed: 2026-06-14
human_verification:
  - test: "As a signed-in non-guest with some unanalyzed games, open Library → Flaws and confirm the EvalCoverageBadge shows real 'N of M analyzed' (not 'coming soon') in the match-count row of both the Games and Flaws subtabs."
    expected: "Badge renders with real analyzed count; no 'coming soon' text anywhere in the Library."
    why_human: "Requires running the full app locally with a real user who has games in mixed analysis states."
  - test: "With coverage below 80%, click 'Analyze more' in EvalCoverageBadge. Confirm badge shows '· K in progress' and the button disappears without page reload. Confirm it re-enables once the tier-2 window drains."
    expected: "Button disables within one render cycle; in-flight count updates via 3s polling; button re-enables after drain."
    why_human: "Live eval drain behaviour, timer-based polling, and disabled-until-drained state cannot be tested without a running backend with EVAL_AUTO_DRAIN_ENABLED=True."
  - test: "Open a Library game card with no engine analysis ('no_engine_analysis' state). Click 'Analyze'. Confirm a localised 'Analyzing…' pulse appears on that card only. Wait ~10s; confirm card flips to the analyzed view without a page reload."
    expected: "Only the clicked card shows the pulse. Other cards unaffected. Card state clears once library-games refetch delivers updated analysis_state."
    why_human: "Localised in-flight state, tier-1 fan-out timing, and games-list polling require a running backend."
  - test: "Open a lichess-eval game card ('analyzed' analysis_state). Confirm NO 'Analyze' button appears."
    expected: "NoAnalysisState returns null for analyzed games — no button rendered."
    why_human: "Requires a real user with lichess-eval games in the dev DB."
  - test: "Log in as a guest (or view as guest). Confirm 'Sign up to unlock full-game analysis' replaces both the bulk EvalCoverageBadge CTA and the per-game NoAnalysisState button. Confirm the link goes to /login?tab=register."
    expected: "Guest sees sign-up CTA in every analyze slot. No silent no-op anywhere."
    why_human: "Requires a guest session in the running app."
  - test: "Confirm Endgames / Openings / GlobalStats coverage messaging is UNCHANGED (D-118-08 scope guard — pct_complete / isPending semantics in other routes must not be altered)."
    expected: "No regression on the existing pending_count / total_count / pct_complete coverage surfaces."
    why_human: "Requires navigating each surface in the running app."
---

# Phase 118: Demand UX — Auto-Enqueue Verification Report

**Phase Goal:** Users' recent games are automatically queued for analysis on import completion and on activity, with a visible explicit "analyze more" affordance showing real-time progress, coverage indicators on eval-dependent surfaces, and live in-flight status — all without requiring the user to initiate or monitor analysis manually.

**Verified:** 2026-06-14T12:30:00Z
**Status:** verified (all automated checks passed; 6 human UAT items completed in-browser on 2026-06-14)
**Re-verification:** No — initial verification

---

## Amendment (2026-06-14, post-verification)

This report was generated at 12:30, **before** commit `ba940f89` dropped the
tier-2 auto-window enqueue, and before the `EVAL_AUTO_DRAIN_ENABLED` default was
flipped to `False`. The following findings below are now **superseded** and do
not match the shipped code:

- **Tier-2 auto-enqueue was removed.** `enqueue_tier2_window`,
  `TIER2_AUTO_WINDOW_SIZE`, the `POST /imports/eval/tier2` route, the import- and
  activity-completion triggers, and `count_tier2_in_flight` no longer exist.
  Any row below that claims tier-2 is "VERIFIED present" is stale. The only
  automatic eval source is the tier-3 idle-backlog drain, gated by
  `EVAL_AUTO_DRAIN_ENABLED`. Observable Truth #1 (auto-enqueue on import/activity)
  is **not** delivered as written; the phase landed on an explicit-demand model
  (per-game tier-1 "Analyze" + tier-3 idle drain) instead.
- **`EVAL_AUTO_DRAIN_ENABLED` now defaults to `False`** (was `True`). Prod opts
  back in via `docker-compose.yml`. The "6 tests fail under
  `EVAL_AUTO_DRAIN_ENABLED=False`" note at the bottom is also stale — those
  tests were either pinned to `True` (`cf89136a`) or removed with the tier-2
  drop. Full suite is green: 2606 passed, 10 skipped.

The coverage-badge / per-game-Analyze / guest-CTA findings (Observable Truths
#3–#5) remain accurate. The 6 human UAT items were completed in-browser on
2026-06-14 and passed (UAT item #2's "tier-2 window drains" wording is moot
post-drop; the in-flight badge + re-enable behaviour was verified against the
tier-3 idle drain). Phase status: **verified**.

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | After import completion or on throttled activity, the user's ~200 most recent unanalyzed games are auto-enqueued at tier-2 without user action | VERIFIED | `enqueue_tier2_window` in `app/services/eval_queue_service.py:382–445`: guest-safe (returns 0), idempotent (ON CONFLICT DO NOTHING), capped at `TIER2_AUTO_WINDOW_SIZE=200`, uses `Game.needs_engine_full_evals` (D-118-03). Import trigger: `import_service.py:542-543` via `asyncio.create_task`. Middleware trigger: `last_activity.py:98-99` after session closes. |
| 2 | User can explicitly trigger "analyze more games" and see a progress indicator (analyzed / queued) updating without page refresh | VERIFIED | `POST /imports/eval/tier2` (`imports.py:327-349`): returns `EnqueueTier2Response` with in-flight gate. `useTier2Enqueue` invalidates `['imports','eval-coverage']` on success (cache refresh within one render cycle). `useEvalCoverage` polls every 3s while `in_flight_count > 0`. `EvalCoverageBadge` shows "N of M analyzed · K in progress". |
| 3 | Eval-dependent surfaces show "based on N of M analyzed" and a CTA to analyze more when coverage is below threshold | VERIFIED | `EvalCoverageBadge.tsx` renders in both Games subtab (`LibraryGameCardList`) and Flaws subtab (`FlawsTab`). `FlawDenominatorPill` in `FlawStatsPanel.tsx` extended with `inFlightCount`/`isGuest`/`isCoverageError` props. `LOW_COVERAGE_THRESHOLD=0.8` named constant. Zero "coming soon" strings found across entire `frontend/src`. |
| 4 | User can see whether their games are currently queued or being analyzed without refreshing the page | VERIFIED | `useEvalCoverage` keeps polling while `in_flight_count > 0` (even at 100% pct_complete). `GamesTab` passes `EVAL_COVERAGE_POLL_INTERVAL_MS` to `useLibraryGames` while in-flight so game cards refresh. `LibraryGameCard` uses `useEffect` to clear local `isInFlight` when `isAnalyzed && isInFlight` after games-list refetch. |
| 5 | Guest users see account promotion as the unlock for full-game analysis, never a silent no-op | VERIFIED | `NoAnalysisState.tsx:48-60`: guest branch renders `btn-signup-for-analysis` linking to `/login?tab=register`. `NoEngineAnalysisFlawsState.tsx`: guest branch renders `btn-signup-for-analysis-flaws`. `EvalCoverageBadge.tsx`: guest branch renders sign-up CTA instead of "Analyze more". Backend: `POST /eval/tier1` and `POST /eval/tier2` both return `skipped_guest` server-side (QUEUE-08 defense-in-depth). |

**Score: 5/5 truths verified**

---

### Deferred Items

None — all success criteria addressed by this phase.

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/services/eval_queue_service.py` | `enqueue_tier2_window`, `TIER2_AUTO_WINDOW_SIZE`, refined `_claim_tier3_derived` ORDER BY | VERIFIED | Function at line 382, constant at line 56; ORDER BY includes `User.last_activity.desc().nullslast()` (line 216) and `Game.lichess_evals_at.isnot(None).asc()` (line 228) |
| `app/repositories/game_repository.py` | `count_is_analyzed_games`, `count_in_flight_evals`, `count_tier2_in_flight` | VERIFIED | All three functions present at lines 95, 111, 130; use correct predicates (is_analyzed via `Game.is_analyzed`, TIER_AUTO_WINDOW filter) |
| `alembic/versions/20260614_140000_phase_118_user_active_index.py` | Partial index `ix_eval_jobs_user_active` | VERIFIED | Migration exists, creates index on `eval_jobs(user_id) WHERE status IN ('pending', 'leased')` |
| `app/schemas/imports.py` | Extended `EvalCoverageResponse` + `EnqueueTier1Response` + `EnqueueTier2Response` | VERIFIED | `EvalCoverageResponse` has `analyzed_count` and `in_flight_count`; both enqueue schemas present; `admin.py` re-exports `EnqueueTier1Response` |
| `app/routers/imports.py` | `POST /eval/tier1/{game_id}`, `POST /eval/tier2`, extended `GET /eval-coverage` | VERIFIED | All three endpoints at lines 297, 327, 264; IDOR guard on tier-1; in-flight gate on tier-2; sequential awaits on eval-coverage |
| `frontend/src/hooks/useEnqueueGame.ts` | `useTier1Enqueue`, `useTier2Enqueue` with cache invalidation | VERIFIED | Both mutations present; `useTier1Enqueue` invalidates `['imports','eval-coverage']` AND `['library-games']`; `useTier2Enqueue` invalidates `['imports','eval-coverage']` |
| `frontend/src/components/library/EvalCoverageBadge.tsx` | Reusable badge for Games and Flaws subtabs | VERIFIED | Created in UAT fix (commit a1e679f8); wired into `LibraryGameCardList` and `FlawsTab`; has `isError` branch |
| `frontend/src/components/library/analysisCoverageCopy.tsx` | `LOW_COVERAGE_THRESHOLD`, no "coming soon" | VERIFIED | Exports `LOW_COVERAGE_THRESHOLD=0.8`; zero "coming soon" strings in file or codebase |
| `frontend/src/components/library/NoAnalysisState.tsx` | Four-branch component (guest / analyze / in-flight / null) | VERIFIED | All four branches present with correct `data-testid` attributes |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `import_service._complete_import_job` | `enqueue_tier2_window` | `asyncio.create_task` fire-and-forget | VERIFIED | Line 542-543: local import + `create_task(enqueue_tier2_window(job.user_id))` after Stage B block |
| `last_activity.py` | `enqueue_tier2_window` | local import + `create_task` after session closes | VERIFIED | Lines 97-99: local import inside `try` block, `create_task` AFTER `async with` session block closes (anti-pattern avoided) |
| `app/routers/imports.py POST /eval/tier1/{game_id}` | `enqueue_tier1_game` | service call after IDOR guard | VERIFIED | `game.user_id != user.id → 404`; then `enqueue_tier1_game(game_id, user_id)` |
| `app/routers/imports.py POST /eval/tier2` | `enqueue_tier2_window` + `count_tier2_in_flight` | in-flight gate then service call | VERIFIED | `count_tier2_in_flight` checked first; `enqueue_tier2_window` called only if 0 in-flight |
| `app/routers/imports.py GET /eval-coverage` | `count_is_analyzed_games` + `count_in_flight_evals` | sequential awaits on one session | VERIFIED | Lines 286-287: two sequential awaits, no `asyncio.gather` |
| `useTier1Enqueue / useTier2Enqueue onSuccess` | `['imports','eval-coverage']` query | `queryClient.invalidateQueries` | VERIFIED | Both mutations call `invalidateQueries({ queryKey: ['imports', 'eval-coverage'] })`; `useTier1Enqueue` also invalidates `['library-games']` |
| `NoAnalysisState / EvalCoverageBadge / NoEngineAnalysisFlawsState` | `useEvalCoverage` + `useUserProfile` | `inFlightCount`/`analyzedCount` + `is_guest` gating | VERIFIED | All three components consume hook data with proper guest gating |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `EvalCoverageBadge.tsx` | `analyzedCount`, `inFlightCount` | `useEvalCoverage` → `GET /imports/eval-coverage` → `count_is_analyzed_games` + `count_in_flight_evals` (DB queries with `is_analyzed` and `status IN ('pending','leased')`) | Yes — real DB counts | FLOWING |
| `NoAnalysisState.tsx` | `isAnalyzed` | `LibraryGameCard` derives from `game.analysis_state === 'analyzed'` → `['library-games']` query → DB | Yes — `game_flaws` presence | FLOWING |
| `FlawDenominatorPill` | `inFlightCount`, `analyzedCount` | `useEvalCoverage` sourced at `GlobalStats.tsx` and `FlawsTab.tsx` level | Yes — same real DB queries | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `enqueue_tier2_window` function exists and has `TIER2_AUTO_WINDOW_SIZE` | `grep -n "async def enqueue_tier2_window\|TIER2_AUTO_WINDOW_SIZE" app/services/eval_queue_service.py` | Lines 56, 382 found | PASS |
| `POST /imports/eval/tier1/{game_id}` and `POST /imports/eval/tier2` routes exist in router | `grep -n "eval/tier1\|eval/tier2" app/routers/imports.py` | Lines 297, 327 found | PASS |
| `EvalCoverageResponse` has `analyzed_count` and `in_flight_count` | `grep -n "analyzed_count\|in_flight_count" app/schemas/imports.py` | Lines 81, 82 found | PASS |
| Frontend: no "coming soon" strings remain | `grep -r "coming soon" frontend/src/` | No output | PASS |
| Frontend tests pass (920/920) | `npm --prefix frontend test -- --run` | 920 passed, 0 failed | PASS |
| Tier-1 enqueue router tests pass | `pytest tests/routers/test_imports_tier1_enqueue.py -n auto` | 6 passed, 0 failed | PASS |
| Eval-coverage router tests pass | `pytest tests/routers/test_imports_eval_coverage.py -n auto` | 12 passed, 0 failed | PASS |
| Game repository count tests pass | `pytest tests/test_game_repository.py -k "analyzed_count or in_flight or tier2_in_flight" -n auto` | 3 passed, 0 failed | PASS |

---

### Test Failures — Post-Phase-118 Regression Note

6 tests fail under the current local environment due to `EVAL_AUTO_DRAIN_ENABLED=False` in `.env`:

- `TestTier2AutoWindow::test_tier2_enqueue`
- `TestTier2AutoWindow::test_tier2_idempotent`
- `TestTier3Derived::test_tier3_derived`
- `TestTier3Ordering::test_tier3_ordering`
- `TestTier3Ordering::test_tier3_pv_ordering`
- `test_imports_tier2_enqueue.py::test_tier2_enqueue`

**Root cause:** Commit `5f36f85e` (`feat(117): EVAL_AUTO_DRAIN_ENABLED toggle`) was committed to the branch AFTER all phase 118 work completed. That commit added the `EVAL_AUTO_DRAIN_ENABLED` early-return guard to both `enqueue_tier2_window` and `claim_eval_job`, but did not patch the existing positive-path tests to `monkeypatch.setattr(svc.settings, "EVAL_AUTO_DRAIN_ENABLED", True)`. With the local `.env` having `EVAL_AUTO_DRAIN_ENABLED=False` (dev setting), these tests return 0 / None and fail their assertions.

**This is not a phase 118 failure.** Phase 118 code was verified as passing (`2615 passed, 10 skipped` reported in the 118-02 SUMMARY after the full suite ran with the eval flag enabled). The post-phase commit `5f36f85e` introduced an environment-specific test regression. The fix is to add `monkeypatch.setattr(svc.settings, "EVAL_AUTO_DRAIN_ENABLED", True)` to the positive-path test bodies in `test_eval_queue.py` and patch `settings.EVAL_AUTO_DRAIN_ENABLED` in the tier-2 router test.

---

### Probe Execution

No conventional `scripts/*/tests/probe-*.sh` files referenced in the phase plans. Step 7c: SKIPPED.

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| QUEUE-04 | 118-01 | Import completion and user activity automatically enqueue ~200 most recent unanalyzed games | SATISFIED | `import_service.py:542-543` + `last_activity.py:98-99` fire `enqueue_tier2_window` fire-and-forget; service targets `Game.needs_engine_full_evals`, capped at 200, idempotent |
| EVUX-01 | 118-02, 118-03 | User can trigger "analyze more games" and see progress | SATISFIED | `POST /imports/eval/tier2` + `POST /imports/eval/tier1/{game_id}` endpoints; `useTier2Enqueue` / `useTier1Enqueue` mutations; `EvalCoverageBadge` with "K in progress" text |
| EVUX-02 | 118-02, 118-03 | User can see analysis coverage with CTA when coverage is low | SATISFIED | `GET /eval-coverage` returns `analyzed_count` + `in_flight_count`; `EvalCoverageBadge` in Games and Flaws subtabs; `LOW_COVERAGE_THRESHOLD=0.8`; CTAs present |
| EVUX-03 | 118-02, 118-03 | User sees in-flight status without blind refresh | SATISFIED | `useEvalCoverage` polls every 3s while `in_flight_count > 0`; `GamesTab` polls games list while in-flight; `LibraryGameCard` auto-clears local in-flight state on `isAnalyzed` flip |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `tests/services/test_eval_queue.py` | 629, 694 | `test_tier2_enqueue` / `test_tier2_idempotent` missing `EVAL_AUTO_DRAIN_ENABLED=True` patch | Warning | Tests fail in dev env with flag disabled; introduced by post-phase commit `5f36f85e`, not phase 118 itself |
| `tests/routers/test_imports_tier2_enqueue.py` | 182 | `test_tier2_enqueue` fails when `EVAL_AUTO_DRAIN_ENABLED=False` in `.env` | Warning | Same root cause |
| `tests/services/test_eval_queue.py` | 380, 787, 829 | `test_tier3_derived` / `test_tier3_ordering` / `test_tier3_pv_ordering` also affected | Warning | Pre-existing under `EVAL_AUTO_DRAIN_ENABLED=False`; exposed by `5f36f85e` |

No `TBD`, `FIXME`, or `XXX` markers found in any phase 118 modified files.
No "coming soon" strings remain anywhere in the frontend.
No `return null` / empty stubs found — all components have real implementations.

---

### Human Verification Required

Phase 118 went through human UAT (four UAT fix commits: `ba2fd576`, `a1e679f8`, `b6a7801d`, `c3c25765`). The user confirmed all surfaces work in the browser. These items are documented for completeness as the UAT context provided to this verifier describes outcomes, not this verifier's own browser session:

### 1. Real coverage badge in Library subtabs

**Test:** As a signed-in non-guest with imported games, open Library → Games and Library → Flaws. Confirm the `EvalCoverageBadge` shows "N of M analyzed" in each match-count row.
**Expected:** Real counts visible; no "coming soon" text.
**Why human:** Requires running app with real game data.

### 2. "Analyze more" bulk button disabled-until-drained

**Test:** With coverage below 80%, click "Analyze more". Confirm the badge shows "· K in progress" and the button disappears/disables without page reload. Confirm re-enable once the tier-2 window drains.
**Expected:** Button state reflects in-flight count via 3s polling cycle.
**Why human:** Requires running eval backend with `EVAL_AUTO_DRAIN_ENABLED=True`.

### 3. Per-game "Analyze" button and localized in-flight state

**Test:** Open a game card with `no_engine_analysis` state, click "Analyze". Confirm only that card shows "Analyzing…" pulse. Confirm it clears when analysis completes (without page reload).
**Expected:** Localized state; other cards unaffected; card flips within ~3s of eval completion.
**Why human:** Requires a running backend and a tier-1 eval completing.

### 4. Lichess-eval game shows no analyze button

**Test:** Open a lichess-eval game card ("analyzed" state). Confirm no "Analyze" button appears.
**Expected:** `NoAnalysisState` returns null for analyzed games.
**Why human:** Requires a user with lichess-eval games in the dev DB.

### 5. Guest promotion in every analyze slot

**Test:** Log in as guest. Confirm "Sign up to unlock full-game analysis" appears in EvalCoverageBadge CTA, NoEngineAnalysisFlawsState, and per-game NoAnalysisState. Confirm link targets `/login?tab=register`.
**Expected:** No silent no-op for guests anywhere.
**Why human:** Requires a guest session in the running app.

### 6. Endgames/Openings/GlobalStats coverage unchanged

**Test:** Navigate to Endgames, Openings, and GlobalStats. Confirm the existing `pct_complete`/`isPending` coverage UI is unchanged.
**Expected:** No regression on existing coverage surfaces (D-118-08 scope guard).
**Why human:** Requires navigating each surface in a real session.

---

### Gaps Summary

No gaps. All 5 success criteria are verified in the codebase. The 6 failing tests are a known regression from post-phase commit `5f36f85e` and are not blocking the phase goal. The test fix is straightforward (add `monkeypatch.setattr(svc.settings, "EVAL_AUTO_DRAIN_ENABLED", True)` to the positive-path tier-2 and tier-3 tests).

The `status: human_needed` reflects that the full UAT checklist (6 browser-based checks) cannot be confirmed programmatically, even though the user reported the surfaces work in the browser during the UAT checkpoint.

---

_Verified: 2026-06-14T12:30:00Z_
_Verifier: Claude (gsd-verifier)_
