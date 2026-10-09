---
phase: 230-weekly-train-leaderboards
source: 230-REVIEW.md
recorded: 2026-10-04
counts: { critical: 0, warning: 3, info: 2, total: 5 }
---

# Phase 230: Code review disposition

One row per finding in `230-REVIEW.md`. Triaged by the owner on 2026-10-04.

| ID | Severity | Location | Summary | Disposition | Note |
|----|----------|----------|---------|-------------|------|
| WR-01 | warning | app/repositories/train_leaderboard_repository.py:52-59 (source: app/repositories/train_repository.py record_solve) | Off-key moves keep the client-asserted `move_quality`, so a direct API caller can bank up to 2 of 3 points per puzzle on both public boards | accepted-risk | Owner 2026-10-04: accept for the leaderboards; recorded in SEED-185 as a blocker the medals phase must close (verify or clamp off-key tiers server-side) |
| WR-02 | warning | frontend/src/hooks/useUserProfile.ts:35-38 (app/routers/users.py:148) | Privacy toggle writes the PUT response (impersonation=None) into the profile cache, dropping the admin impersonation pill | wont-fix | Owner 2026-10-04: not selected for fixing (admin-only, cosmetic) |
| WR-03 | warning | frontend/src/components/train/TrainLeaderboardCard.tsx:218-245 | Countdown can hit 0 up to ~1 s before the deadline; the one-shot rollover guard then never retries, leaving last week's board on "ending now" | fixed | 3c27c91f2: seconds_remaining rounded up server-side; bounded rollover retry (2 s, max 3); two new card tests fail without the fix |
| IN-01 | info | app/services/train_leaderboard.py:136,247,300 | `viewer_visibility` parameter shadows the module function of the same name | fixed | 3c27c91f2: function renamed to resolve_viewer_visibility |
| IN-02 | info | frontend/src/components/train/TrainLeaderboardCard.tsx:88-94 | "Hidden from others" / "(tentative)" sit inside the truncating name span, so narrow screens cut the cue | fixed | 3c27c91f2: only the name truncates; cues wrap below it. Re-checked at 375 px in the browser: "(tentative)" fully visible on a second line, no overflow |
