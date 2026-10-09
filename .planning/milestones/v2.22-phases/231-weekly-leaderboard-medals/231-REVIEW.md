---
phase: 231-weekly-leaderboard-medals
reviewed: 2026-10-04T00:00:00Z
depth: standard
files_reviewed: 48
files_reviewed_list:
  - CHANGELOG.md
  - alembic/env.py
  - alembic/versions/20261004_120000_e3a8c5f17b20_train_weekly_standings.py
  - app/models/train_weekly_standing.py
  - app/repositories/train_medals_repository.py
  - app/routers/train.py
  - app/schemas/train.py
  - app/services/train_leaderboard.py
  - app/services/train_medals.py
  - docs/production-runbook.md
  - frontend/src/api/client.ts
  - frontend/src/components/admin/LeaderboardMedalsDemo.tsx
  - frontend/src/components/settings/LeaderboardPrivacyCard.tsx
  - frontend/src/components/train/TrainLeaderboardCard.tsx
  - frontend/src/components/train/TrainStartScreen.tsx
  - frontend/src/components/train/medals/LastWeekPodium.tsx
  - frontend/src/components/train/medals/MedalClaimDialog.tsx
  - frontend/src/components/train/medals/MedalIcon.tsx
  - frontend/src/components/train/medals/MedalTally.tsx
  - frontend/src/components/train/medals/TrainMedalDialogHost.tsx
  - frontend/src/hooks/useTrainMedals.ts
  - frontend/src/index.css
  - frontend/src/lib/leaderboardMedalsDemoData.ts
  - frontend/src/lib/theme.ts
  - frontend/src/lib/trainMedals.ts
  - frontend/src/pages/Admin.tsx
  - frontend/src/pages/Privacy.tsx
  - frontend/src/types/train.ts
  - tests/repositories/test_train_medals_finalization.py
  - tests/repositories/test_train_medals_repository.py
  - tests/routers/test_train_leaderboard.py
  - tests/routers/test_train_medals.py
  - tests/scripts/test_opening_cache_repair.py
  - tests/services/test_train_leaderboard.py
  - tests/services/test_train_medals.py
  - frontend/src/components/admin/__tests__/LeaderboardMedalsDemo.test.tsx
  - frontend/src/components/settings/__tests__/LeaderboardPrivacyCard.test.tsx
  - frontend/src/components/train/__tests__/TrainLeaderboardCard.test.tsx
  - frontend/src/components/train/__tests__/TrainScoreRankLines.test.tsx
  - frontend/src/components/train/__tests__/TrainStartScreen.test.tsx
  - frontend/src/components/train/medals/__tests__/LastWeekPodium.test.tsx
  - frontend/src/components/train/medals/__tests__/MedalClaimDialog.test.tsx
  - frontend/src/components/train/medals/__tests__/MedalTally.test.tsx
  - frontend/src/components/train/medals/__tests__/TrainMedalDialogHost.test.tsx
  - frontend/src/lib/__tests__/trainLeaderboard.test.ts
  - frontend/src/lib/__tests__/trainMedals.test.ts
  - frontend/src/pages/__tests__/Train.solveLoop.test.tsx
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 231: Code Review Report

**Reviewed:** 2026-10-04
**Depth:** standard
**Files Reviewed:** 48
**Status:** issues_found

## Summary

I reviewed the backend and frontend changes of the weekly leaderboard medals phase, with the focus areas from the request. I found no blocker.

Verified as sound:
- **Finalization concurrency.** `claim_week` inserts the marker `ON CONFLICT DO NOTHING RETURNING`. A concurrent finalizer blocks on the primary key until the first transaction commits, then gets no row and skips the week. If the first transaction aborts, the blocked insert takes over. Weeks are processed in ascending order, so there is no lock-order inversion. The standings insert is also `ON CONFLICT DO NOTHING` on the unique constraint.
- **Router transaction path.** `_finalize_medal_weeks` commits on success. On failure it rolls back and calls `capture_exception`, and the board is still served. The router copies `user.id`, `is_guest` and `leaderboard_hidden` before the finalizer, so the rollback's `expire_all` cannot cause a lazy load.
- **Claim IDOR.** `mark_celebrated` matches on the caller's `user_id` plus the posted `(week_start, board)` pairs, with `celebrated_at IS NULL` for idempotency. Neither GET nor POST takes a user parameter. The body is capped at `MEDAL_CLAIM_MAX_ITEMS`, which equals the unclaimed-read limit, so a dialog's POST is always valid.
- **Migration.** The FK is `ON DELETE SET NULL` on `user_id` and `ON DELETE CASCADE` on the marker. The CHECK constraints are present. The `BEFORE UPDATE OF user_id ... WHEN (OLD.user_id IS NOT NULL AND NEW.user_id IS NULL)` trigger fires on the FK action, and a test deletes a real user and asserts the stored name. Downgrade drops the trigger, function, index and tables in the right order. The down-revision is the single current head.
- **Privacy.** Hidden users, guests and tentative Accuracy users get no snapshot row (`is_public` filter plus `rank is not None`). Podium names are masked at read time ("Anonymous" for hidden-now users except the viewer, "Deleted user" for NULL `user_id`). No id reaches the wire. The tally query is scoped to ids already visible on the board.
- **Frontend double-fire.** The `settledRef` guard keeps Claim and dismiss to one callback per open cycle. `unlockAudio` is called inside the tap. The host's `isFetchedAfterMount` guard rules out a stale cache showing already-claimed medals. The impersonation and guest guards are in place.
- **Tooling.** The targeted backend tests pass (128 passed). ruff, ty, the depth gate, complexipy, knip and eslint are clean for the touched areas.

## Warnings

### WR-01: Claim dialog flashes "You won 0 medals!" and an empty list while fading out

**File:** `frontend/src/hooks/useTrainMedals.ts:40-48`, `frontend/src/components/train/medals/TrainMedalDialogHost.tsx:46-49`
**Issue:** `finish()` sets `closed` and calls `claim.mutate(keys)`. On success, `useClaimMedals.onSuccess` removes the claimed keys from the cached unclaimed list. The host derives `medals` from that cache, so `medals` becomes `[]` and the dialog re-renders with the title `medalDialogTitle(0)` ("You won 0 medals!") and an empty list. Radix Presence keeps the content mounted for the exit animation (`duration-100` in `ui/dialog.tsx`). If the POST resolves inside that window, the user sees a visible text and layout glitch as the dialog closes. On a fast connection (or a local one) the POST is likely to finish within 100 ms. The medals shown while closing should be frozen, not live.
**Fix:** Snapshot the shown medals when the dialog opens or settles, and render from the snapshot while closing:
```tsx
const [shown, setShown] = useState<readonly UnclaimedMedal[]>([]);
useEffect(() => {
  if (open) setShown(medals);
}, [open, medals]);
// pass `medals={open ? medals : shown}` to MedalClaimDialog
```
Alternatively, skip the `setQueryData` pruning in `onSuccess` and rely on the per-mount `closed` flag plus `refetchOnMount: 'always'`.

### WR-02: Eligibility is evaluated at the time of the first request after the deadline, not at the deadline

**File:** `app/services/train_medals.py:75-101`, `app/repositories/train_leaderboard_repository.py:63-103`
**Issue:** Lazy finalization reads `users.leaderboard_hidden` live inside `fetch_week_aggregates` when the first request arrives after Sunday 24:00 UTC plus grace. With low Train traffic that can be hours later (for example the Monday morning European visit). A user who toggles "Hide me from leaderboards" between the deadline and that first request is excluded, and every user below them moves up a rank, so who wins a permanent medal depends on request timing. The reverse also holds: a user hidden at the deadline who un-hides before finalization gets a medal. The seed and D-01 say "opted-out at finalization time", but the intent is plainly the public board as it stood at the deadline, and the lazy gap is unbounded. The medals are permanent and not reproducible after the fact (D-01 notes this is "costly" to reverse).
**Fix:** The cheap options are to accept and document it, or to narrow the gap. Document the behaviour in the privacy copy and the runbook ("opt-outs take effect for a week's medals until the first visit after the deadline"). To narrow the gap, add a lightweight scheduled call (for example the existing cron or health tick) to `finalize_due_weeks`, which is idempotent, so the first visit is no longer the trigger.

## Info

### IN-01: A stray tap on the overlay silently consumes the celebration

**File:** `frontend/src/components/train/medals/TrainMedalDialogHost.tsx:46-49`
**Issue:** The dialog opens on its own after the landing's fetch resolves, and any outside click or Escape counts as a dismiss, which POSTs the claim (D-13, locked). A user tapping a landing button at the moment the dialog appears hits the overlay and loses the celebration with no sound or confetti, and the medal never reappears. The behaviour is locked, so I am noting it only.
**Fix:** If it proves to be a problem in UAT, ignore pointer-down-outside for the first few hundred milliseconds after open, or make outside click a no-op and keep only the explicit close button and Escape as dismiss.

### IN-02: Unrelated test change inside the phase diff

**File:** `tests/scripts/test_opening_cache_repair.py:3230-3290`
**Issue:** Two tests in `TestLegacySample` gain `_ensure_user` calls to fix an order-dependent FK failure. The fix is correct but outside the phase 231 scope (the project rules say to flag unplanned changes rather than fold them in).
**Fix:** Keep it, but note it in the phase summary or move it to its own `fix(tests)` commit so the phase diff stays reviewable.

### IN-03: Snapshot columns lack basic value CHECK constraints

**File:** `alembic/versions/20261004_120000_e3a8c5f17b20_train_weekly_standings.py:50-56`
**Issue:** `final_rank`, `value` and `puzzles` are plain `INTEGER NOT NULL`. `medal` has a CHECK but nothing ties it to the data (for example `medal IS NULL OR value > 0`, or `final_rank >= 1`). The service enforces these rules and the table is written only by one code path, so this is robustness only. A bad manual repair row could produce a zero-value medal that `final_rank <= 3`-style reads would show.
**Fix:** Optionally add `CHECK (final_rank >= 1 AND value >= 0 AND puzzles >= 0)` and `CHECK (medal IS NULL OR value > 0)` in the migration and the model.

---

_Reviewed: 2026-10-04_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
