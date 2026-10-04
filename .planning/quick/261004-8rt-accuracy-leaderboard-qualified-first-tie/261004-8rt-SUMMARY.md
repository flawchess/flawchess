---
phase: quick-261004-8rt
plan: 01
subsystem: train-leaderboard
tags: [leaderboard, accuracy, ranking, frontend, backend]
status: complete
commits: 3
plan_head_before: 89e392a67278d9c650910443d4da22e7ef8be21a
plan_head_after: eb3c0f530
requirements: [QUICK-261004-8rt]
key-files:
  modified:
    - app/services/train_leaderboard.py
    - app/schemas/train.py
    - tests/services/test_train_leaderboard.py
    - tests/routers/test_train_leaderboard.py
    - frontend/src/types/train.ts
    - frontend/src/lib/trainLeaderboard.ts
    - frontend/src/components/train/TrainLeaderboardCard.tsx
    - frontend/src/lib/__tests__/trainLeaderboard.test.ts
    - frontend/src/components/train/__tests__/TrainLeaderboardCard.test.tsx
    - frontend/src/components/train/__tests__/TrainScoreRankLines.test.tsx
    - CHANGELOG.md
decisions:
  - "Accuracy board is tiered: qualified (20+ non-filler puzzles) ranked first; tentative listed below with rank null, ordered puzzles desc, value desc, name, key (supersedes Phase 230 D-03)."
  - "rank_without_session is None when the viewer is tentative with or without the session; counted against qualified visible others only."
  - "Per-row '(tentative)' cue removed; the 'Not yet qualified' divider carries that meaning."
actuals:
  tasks: 3
  commits: 3
---

# Quick 261004-8rt: Accuracy leaderboard qualified-first tiering Summary

Weekly Accuracy board now ranks qualified users (20+ non-filler puzzles) above every tentative user; tentative users are listed unranked under a "Not yet qualified" divider, and a tentative viewer's score-screen line reads "Accuracy: N more to qualify".

## What changed

- **Backend** (`c0499df76`): `_tiered_order` sorts qualified entries with the existing `_order_key` and competition ranks, then appends tentative entries by `_tentative_order_key` with rank `None`. `BoardRow.rank`, `ViewerStanding.rank` and the Pydantic mirrors are `int | None`. `_rank_without` counts only public, qualified, non-viewer others and returns `None` when the viewer is tentative without the session; `build_board` also skips it when the viewer is tentative with the session. Filtering for hidden/guest users still happens before tiering. Points board untouched. Added 10 `tier` tests; repaired the 4 service and 3 router tests the new contract legitimately changes.
- **Frontend** (`173435102`): `rank: number | null` on the wire types; `firstUnrankedRowIndex` and `NOT_YET_QUALIFIED_DIVIDER_COPY`; `rankLineCopy` returns "Accuracy: N more to qualify" for a null rank and no longer adds any "(tentative)" suffix; the card renders rank-less rows plus one `train-leaderboard-qualify-divider` li (after the gap marker, before the first unranked row, not aria-hidden).
- **CHANGELOG** (`eb3c0f530`): one bullet under `[Unreleased]` / `### Changed`.

`ACCURACY_QUALIFY_MIN_PUZZLES` stays 20.

## Verification

- `uv run pytest -n auto` on the 4 leaderboard modules plus `tests/test_users_router.py`: 118 passed; `-k tier`: 10 passed.
- `ruff format`/`ruff check`, `ty check app/ tests/ scripts/`, `check_function_size.py --fail-over-depth 4`: clean.
- Frontend: `npm run lint`, `npm run build` (tsc -b), full `npm test -- --run`, `npm run knip`: all exit 0 (knip prints one pre-existing `.css` configuration hint).
- No `scripts/gen_*.py` references the leaderboard schema; nothing to regenerate.
- The full backend suite (pre-merge gate) was not run; per the plan it runs before squash-merge at the orchestrator's call.

## Deviations from Plan

None - plan executed as written. The mutation check (revert the fix, confirm tests fail) was not performed.

## Known Stubs

None.

## Threat Flags

None. Tiering runs on the already-filtered combined list, so hidden users and guests cannot reach either tier of another viewer's board (asserted by `test_tier_guest_and_hidden_viewers_sit_in_the_tentative_section`).

## Notes

- A nested-looking `vitest` full run exceeded the tool's 120 s foreground limit and was auto-backgrounded by the harness; it completed with exit 0.
- Two unrelated `docs(231)` commits from another agent landed on `main` between my commits (shared checkout); my 3 commits are the ones listed above.

## Self-Check: PASSED

Commits `c0499df76`, `173435102`, `eb3c0f530` exist on `main`; all modified files present.
