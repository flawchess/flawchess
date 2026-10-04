---
phase: 231-weekly-leaderboard-medals
fixed_at: 2026-10-04T00:00:00Z
review_path: .planning/phases/231-weekly-leaderboard-medals/231-REVIEW.md
iteration: 1
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
---

# Phase 231: Code Review Fix Report

**Fixed at:** 2026-10-04
**Source review:** .planning/phases/231-weekly-leaderboard-medals/231-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 2
- Fixed: 2
- Skipped: 0

Verification ran in the main checkout (no isolated worktree), on branch `gsd/phase-231-weekly-leaderboard-medals`, because the orchestrator directed work on the current branch and the frontend gates need the main checkout's `node_modules`.

## Fixed Issues

### WR-01: Claim dialog flashes "You won 0 medals!" and an empty list while fading out

**Files modified:** `frontend/src/components/train/medals/TrainMedalDialogHost.tsx`, `frontend/src/components/train/medals/__tests__/TrainMedalDialogHost.test.tsx`
**Commit:** b7100b45b
**Applied fix:** The host keeps a `shown` snapshot of the medals, updated during render while the dialog is open (React's adjust-state-during-render pattern, so no extra effect and no stale frame). `MedalClaimDialog` gets `open ? medals : shown`, so the post-claim cache prune cannot empty the content during the Radix exit animation. A comment at the fix site explains what broke and why. New regression test fakes an exit animation (stubbed `getComputedStyle`) so Radix Presence keeps the content mounted, then asserts the title still reads "You won 2 medals!" and both entries remain after the cache is pruned. Proven by reverting the host change: the test failed with "You won 0 medals!", and passed again once restored. `npm run lint`, `npm test -- --run src/components/train/medals` (32 passed) and `npm run build` are clean. Status note: this is a rendering/state fix, not a logic-condition change; the visual fade-out itself is not covered by jsdom beyond the faked animation.

### WR-02: Eligibility is evaluated at the time of the first request after the deadline, not at the deadline

**Files modified:** `app/services/train_medals.py`, `docs/production-runbook.md`
**Commit:** 6e8995b16
**Applied fix:** Per orchestrator direction, accepted and documented rather than adding a scheduler. Module docstring in `train_medals.py` now states that `leaderboard_hidden` is read live at finalization (first request after deadline plus grace) and that this was accepted. `docs/production-runbook.md` gets a short "Weekly leaderboard medals" section covering the same behavior, that `finalize_due_weeks` is idempotent (the `train_weekly_finalizations` marker is the lock) and can be triggered by loading either endpoint, and a dev-only cleanup note warning against deleting finalizations in prod. No code behavior and no user-facing copy changed. `ruff check`, `ruff format --check` and `ty check app/ tests/ scripts/` pass.

---

_Fixed: 2026-10-04_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
