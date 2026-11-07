---
phase: 246-train-subnav-split
reviewed: 2026-11-07T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - frontend/src/components/train/TrainArchiveTab.tsx
  - frontend/src/components/train/TrainStreakCard.tsx
  - frontend/src/components/train/__tests__/TrainArchiveTab.test.tsx
  - frontend/src/components/train/__tests__/TrainStreakCard.test.tsx
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: issues_found
---

# Phase 246: Code Review Report

**Reviewed:** 2026-11-07
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

This is an incremental review of commit 7f5db60cc (owner UAT changes to the Archive toggle and streak card), diffed against df68c8b9f. It covers four files: `TrainArchiveTab.tsx`, `TrainStreakCard.tsx` and their two test files.

The change does five things:
- The per-item `InfoPopover` wrappers in the Archive toggle are replaced by a single explainer sentence under the group.
- The `ToggleGroupItem`s are now direct children of the group, as the shadcn `first:`/`last:` selectors in `components/ui/toggle-group.tsx` require.
- The empty-state subtitles are dropped.
- The "See this week's leaderboard" fallback link is removed from the rank line.
- The tests are rewritten to match.

I traced everything that depended on what was removed:
- A repo-wide grep finds no remaining reference to `train-mastered-info`, `train-parked-info`, `MASTERED_EXPLAINER`, `PARKED_EXPLAINER`, the old empty-state subtitles or the "See this week's leaderboard" copy in `frontend/src`, `tests` or `docs`. Only planning artifacts mention them.
- `popoverTargetFromTestId` derives its targets from the `testId`, so no analytics registry entry is orphaned.
- `'train-rank-line'` in `NAV_SOURCES` is still used by the remaining link.
- The new tests do assert the new behaviour. The direct-child test checks `parentElement`, the explainer tests check the exact text per list and after a toggle click, and the no-rank and error tests wait for the pending placeholder to leave before asserting the link is absent.

I found no correctness crash or security defect. There are two new warnings: the new Parked sentence is factually wrong for part of the population, and the rank-line placeholder causes a layout shift in the common no-rank case, contrary to its own comment. There is one new info item.

The carried findings come from the full 37-file review of 2026-11-06 and keep their original IDs, titles and text, except where noted:
- **WR-01, WR-02, IN-01, IN-02:** carried. I re-checked each against the current code and all are still accurate. The line numbers are unchanged (the files they point at were not touched by this pass).
- **IN-03 (wrapped `ToggleGroupItem`s):** left out. It is resolved: `TrainArchiveTab.tsx:73-85,117-118` shows the items are now direct children of the group, and a test pins this (`TrainArchiveTab.test.tsx`, "keeps both items as direct children of the group").

## Warnings

### WR-01: Archive query has no supporting index on `drill_solves`; the flagged "no migration" assumption was never verified

**File:** `app/repositories/train_repository.py:614-636` (the `last_solve` subquery in `_archive_page_stmt`)
**Disposition:** deferred by owner, do not fix. Prod measured 19,493 rows and 3.6 ms, under the 300k/50 ms migration rule; see 246-REVIEW-DISPOSITION.md.
**Issue:** `CONTEXT.md` ("Findings to resolve in planning") required running `EXPLAIN` on the sort query and flagging a migration if it is a sequential scan. `246-01-SUMMARY.md:144` records that no EXPLAIN was run. Dev has only 135 `drill_solves` rows, so nothing was learned.

The query filters `drill_solves` by `user_id`, `source` and `solved_at IS NOT NULL`, then groups by `(game_id, ply)`. The model's only secondary index is the partial `ix_drill_solves_solved_at` on `solved_at`, and the primary key is `(session_id, position)`. Neither supports a `user_id` lookup. Every Archive page request, and every page turn, therefore scans the whole global `drill_solves` table (all users), not just the caller's rows. The table gains one row per puzzle per session per user, so the cost grows with the whole user base, and the `OFFSET` makes it identical for page 1 and page N. The comment "Deliberately ONE grouped scan" acknowledges the missing index but treats it as a given.

**Fix:** Before this ships, run `EXPLAIN (ANALYZE, BUFFERS)` against a prod-sized copy or the benchmark DB. If it is a Seq Scan on `drill_solves`, add a migration with a partial index that matches the predicate:
```python
Index(
    "ix_drill_solves_user_sr_game_ply",
    "user_id", "game_id", "ply",
    postgresql_where=text("source = 0 AND solved_at IS NOT NULL"),
)
```
Whichever way it goes, record the plan in the phase artifacts so the open item is closed.

### WR-02: No test pins the upper boundary of the archive `offset` bound

**File:** `tests/routers/test_train.py:4515-4533` vs `app/routers/train.py:81`
**Issue:** `test_archive_rejects_bad_params` covers the 422 side (`offset=2147483648`, `limit=0/51`, `list=active`). Nothing asserts the accepting side of the same bound: that `offset=2147483647` (`_ARCHIVE_OFFSET_MAX`) returns 200 with an empty `items` list and the true `total`. The frontend depends on exactly that: `ARCHIVE_PAGE_MAX = 1_000_000` is sized so `(page-1)*20` stays under the bound, and an over-range page is then redirected to the last page based on `items=[]` with `total>0`. If the bound or the SQL regressed (for example an asyncpg overflow at a large offset), it would surface as a Sentry 500 instead of the redirect.

**Fix:** Add a 200-case with a large valid offset, for example `?list=mastered&offset=19999980` (the largest offset the UI can send) and `?offset=2147483647`, asserting `items == []` and `total` equals the seeded count.

### WR-03: The new Parked sentence misstates the park rule for puzzles that were ever solved

**File:** `frontend/src/components/train/TrainArchiveTab.tsx:28-35` (copy at line 34)
**Issue:** `ARCHIVE_EXPLAINER.parked` reads "Missed 3 or more times and set aside." The comment above it claims "3 or more" covers both park doors. It does not. `app/services/train_scheduler.py:351-352` has two doors:
- Door A: `not state.ever_correct and new_fail_count >= PARK_FAIL_THRESHOLD` (3).
- Door B: `new_fail_count >= LEECH_FAIL_THRESHOLD` (4), regardless of `ever_correct`.

A puzzle the player has solved at least once and then missed 3 times is not parked. It stays active until the 4th miss. The sentence is true as "a parked puzzle was missed at least 3 times", but a reader takes it as the rule: "3 misses means parked". That reading is wrong for part of the population, and the comment asserts a correctness the copy does not have. The previous text ("Missed 4 times in total, or 3 times without ever solving it") was accurate. The owner chose the shorter wording in UAT. This is still a user-facing inaccuracy, and it can contradict what a player sees on Today.

**Fix:** Keep the brevity but state the rule truthfully, for example `'Missed too often to keep practising, so set aside.'`, or `'Missed 4 times, or 3 times without ever solving it.'`. If "3 or more" is deliberately kept, fix the comment so it no longer claims to cover both doors.

### WR-04: Rank-line row is reserved while loading and then removed when there is no rank, so the card jumps

**File:** `frontend/src/components/train/TrainStreakCard.tsx:72-83` (comment at 75, `return null` at 83)
**Issue:** While `isPending`, `TrainRankLine` renders a `&nbsp;` span so "nothing shifts when the rank arrives". With no rank (or on error) it now returns `null`, which removes that row and its `gap-1.5` from the flex column, so everything below it moves up by one line plus the gap.
- The viewer is `null` whenever they have no Points entry this week (`app/services/train_leaderboard.py:535-557`, `viewer_index is None`). That covers a new user, and anyone who has not solved a puzzle since the week rolled over. It is not an edge case.
- The card grid uses `items-center`, so the flame column re-centres as well.
- The comment is only true for viewers who have a rank.
- The tests assert that the placeholder is present and then gone, so they pin the shift instead of catching it.

**Fix:** Either reserve the row permanently (render the `&nbsp;` span instead of `null` when `rank === null`, with a cheap `min-h` so it does not read as a gap), or accept the shift and correct the comment and the "reserves the row" test name. Reserving the space is the cheaper fix. Update the two "renders no line" tests to assert that no `train-rank-line` link exists rather than that the placeholder is gone.

## Info

### IN-01: Formatting glitch in `TrainPuzzleCard`

**File:** `frontend/src/components/train/TrainPuzzleCard.tsx:93`
**Issue:** `lastMove={uciToSquares(item.last_move_uci) ?? undefined}          />` has the closing `/>` on the same line after a run of spaces. It is valid but looks like a bad merge. The project has no Prettier, so nothing normalizes it.
**Fix:** Put `/>` on its own line.

### IN-02: Stale docstring and a stray double blank line in `TrainStartScreen`

**File:** `frontend/src/components/train/TrainStartScreen.tsx:2-4, 113-114`
**Issue:** The header still says `Train.tsx` "fetches session status automatically on mount". That is now `useTrainLoop` on the first Today visit. There is also a double blank line before `type LandingState`.
**Fix:** Update the docstring to name `useTrainLoop` and remove the extra blank line.

### IN-04: The Archive explainer sentence is not tied to the toggle for assistive tech

**File:** `frontend/src/components/train/TrainArchiveTab.tsx:107-122`
**Issue:** The popovers carried their own `aria-label`s. The replacement `<p data-testid="train-archive-explainer">` is a plain sibling of the group with no association. A screen-reader user focusing the toggle gets "Archive list" and "Mastered 12" but not the definition.
**Fix:** Give the paragraph an `id` and add `aria-describedby` to the `ToggleGroup`, for example `id="train-archive-explainer-text"`. A `useId()` is not needed because there is one instance per page.

---

_Reviewed: 2026-11-07_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
