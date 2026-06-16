---
phase: 119-eval-drain-coverage-bounded-retry-hole-filling-recency-weigh
fixed_at: 2026-06-14T15:41:12Z
review_path: .planning/phases/119-eval-drain-coverage-bounded-retry-hole-filling-recency-weigh/119-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 119: Code Review Fix Report

**Fixed at:** 2026-06-14T15:41:12Z
**Source review:** .planning/phases/119-eval-drain-coverage-bounded-retry-hole-filling-recency-weigh/119-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (all Warning — 0 Critical)
- Fixed: 4
- Skipped: 0
- Info findings (IN-01..IN-04): out of `critical_warning` scope, not attempted.

## Fixed Issues

### WR-01: GlobalStats badge error state derives from a different query than its displayed numbers

**Files modified:** `frontend/src/pages/GlobalStats.tsx`
**Commit:** 03cb93e5
**Applied fix:** The `EvalCoverageBadge` on the Stats tab now takes `isCoverageError={flawStatsError}` (the `useLibraryFlawStats` query that also supplies `analyzed_n`/`total_n`) instead of the unrelated `useEvalCoverage()` error. Since `isError` was the only consumer of `useEvalCoverage()` on this page, the hook call and its import were removed entirely (confirmed clean by `knip`). The badge's error signal now matches the data source actually rendered.

### WR-02: Refresh effect fires a spurious invalidation on initial page load

**Files modified:** `frontend/src/pages/library/GamesTab.tsx`, `frontend/src/pages/library/FlawsTab.tsx`
**Commit:** 6886505c
**Applied fix:** Changed `prevAnalyzedRef` from `useRef(analyzedCount)` (the hook default `0` on first render) to `useRef<number | null>(null)`, and guarded the effect with `if (prev !== null && analyzedCount > prev)`. The first observed `analyzedCount` is now treated as the baseline, so the `library-*` invalidation no longer fires on initial load for returning users with existing analysis. The intended "card flips from Analyzing… to analyzed without reload" behavior (a genuine increase after mount) is preserved. No frontend test asserted the suppressed initial-load transition, so no test updates were required; the full suite (924 tests) still passes.

### WR-03: `resweep_holed_games` exception handler relies on `dir()` for scope inspection

**Files modified:** `app/services/eval_drain.py`
**Commit:** 74c56731
**Applied fix:** Initialized `game_ids: list[int] = []` before the `try`, so the except handler is now `sentry_sdk.set_context("resweep", {"game_count": len(game_ids)})` with no `"game_ids" in dir()` probe. If `session.execute` raises before the assignment, `game_count` is correctly `0`.

### WR-04: `resweep_holed_games` clears markers in one unbounded UPDATE without batching

**Files modified:** `app/services/eval_drain.py`
**Commit:** 74c56731
**Applied fix:** Added `_RESWEEP_UPDATE_CHUNK_SIZE = 1000` and chunked the re-arm UPDATE with `for chunk_start in range(0, count, _RESWEEP_UPDATE_CHUNK_SIZE)`, committing each chunk independently. The documented unbounded "sweep all" prod path can no longer re-arm the entire ~558k holed backlog in one `IN (...)` statement/transaction (avoids bind-param blowup and a simultaneous tier-3 re-queue). The small-N path (`count <= 1000`) remains a single statement + single commit, behaviorally identical to the pre-batching code. The 3 existing resweep tests still pass.

---

_Fixed: 2026-06-14T15:41:12Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
