---
phase: 246-train-subnav-split
fixed_at: 2026-11-07T00:00:00Z
review_path: /home/aimfeld/Projects/Games/flawchess/.planning/phases/246-train-subnav-split/246-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 2
skipped: 2
status: partial
---

# Phase 246: Code Review Fix Report

**Fixed at:** 2026-11-07
**Source review:** .planning/phases/246-train-subnav-split/246-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4
- Fixed: 2
- Skipped: 2

Edits and commits were made directly on `gsd/phase-246-train-subnav-split` in the main checkout (no temporary worktree), as instructed by the orchestrator. Verification ran in the main checkout, so the numbers are reproducible from the tree.

## Fixed Issues

### WR-02: No test pins the upper boundary of the archive `offset` bound

**Files modified:** `tests/routers/test_train.py`
**Commit:** 3979cc8a9
**Applied fix:** Added `test_archive_accepts_large_offset_with_empty_items`, parametrized over `?list=mastered&offset=19999980` and `?offset=2147483647`. It seeds one mastered puzzle with the existing `_seed_archive_puzzle` helper, asserts 200 with `items == []` and `total == 1`, and cleans up the session and game in a `finally` block like the neighbouring tests.

Verification:
- `uv run pytest tests/routers/test_train.py -k archive`: 12 passed (2 new).
- Bite check: temporarily set `_ARCHIVE_OFFSET_MAX` to 1000 in `app/routers/train.py`; both new cases failed (`assert 422 == 200`). Restored with `git checkout -- app/routers/train.py`; `_ARCHIVE_OFFSET_MAX` is back at `2**31 - 1` and the tree was clean afterwards.
- `uv run ruff format --check`, `uv run ruff check`, `uv run ty check` on the test file: all clean.

### WR-04: Rank-line row is reserved while loading and then removed when there is no rank, so the card jumps

**Files modified:** `frontend/src/components/train/TrainStreakCard.tsx`
**Commit:** 1d7047a11
**Applied fix:** Reviewer's second option only. The comment at the `isPending` branch now says the row is reserved so nothing shifts when a rank arrives, that the reservation only holds for viewers who have a rank, and that with no rank (or on error) the row collapses once the query resolves, which is intended.

Behaviour is unchanged. No permanent blank row was added. The choice (collapse for no-rank viewers) is being raised with the owner. No test was renamed: none claims the row is reserved unconditionally (the "reserves the row ... while the leaderboard is pending" test is scoped to the pending state and stays accurate), and assertions were left alone.

Verification:
- `cd frontend && npm test -- --run src/components/train/__tests__/TrainStreakCard.test.tsx`: 34 passed.
- `npx eslint src/components/train/TrainStreakCard.tsx`: no output (clean).

## Skipped Issues

### WR-01: Archive query has no supporting index on `drill_solves`

**File:** `app/repositories/train_repository.py:614-636`
**Reason:** deferred by owner, see 246-REVIEW-DISPOSITION.md
**Original issue:** The grouped scan over `drill_solves` has no `user_id` index; no EXPLAIN was recorded.

### WR-03: The new Parked sentence misstates the park rule for puzzles that were ever solved

**File:** `frontend/src/components/train/TrainArchiveTab.tsx:28-35`
**Reason:** copy decision raised with owner
**Original issue:** "Missed 3 or more times and set aside." is wrong for puzzles solved at least once, which are parked only at the 4th miss.

---

_Fixed: 2026-11-07_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
