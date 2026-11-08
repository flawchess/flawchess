---
phase: "246"
slug: "train-subnav-split"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-06"
---

# Phase 246 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest with pytest-xdist (backend); Vitest with Testing Library (frontend) |
| **Config file** | `pyproject.toml`, `frontend/vite.config.ts` test block |
| **Quick run command** | `uv run pytest tests/routers/test_train.py -k archive -x` and `npm --prefix frontend test -- --run src/pages/__tests__/Train.subnav.test.tsx` |
| **Full suite command** | Pre-merge gate in `CLAUDE.md` |
| **Estimated runtime** | ~60 seconds for the quick commands; not measured for the full gate |

---

## Sampling Rate

- **After every task commit:** Run the quick command for the touched area
- **After every plan wave:** Run `uv run pytest tests/routers/test_train.py tests/repositories/test_train_repository.py tests/routers/test_train_leaderboard.py -x` and `( cd frontend && npm test -- --run && npm run build && npm run knip )`
- **Before `/gsd-verify-work`:** Full pre-merge gate must be green
- **Max feedback latency:** 60 seconds for the quick commands

---

## Per-Task Verification Map

Task IDs are `{plan}-T{task}`, assigned by the planner; each row's command is in that task's `<verify>` block. Coverage is drawn from `246-RESEARCH.md` § Validation Architecture.

| Decision | Behavior | Test Type | Automated Command | File Exists | Task ID | Status |
|----------|----------|-----------|-------------------|-------------|---------|--------|
| D-01 | `parseTrainRoute` covers all paths, trailing slash, unknown → null | unit | `npm --prefix frontend test -- --run src/lib/__tests__/trainRoute.test.ts` | ❌ W0 | 246-02-T1, 246-05-T2 | ⬜ pending |
| D-01 | `/train/foo` redirects to `/train` | component | `npm --prefix frontend test -- --run src/pages/__tests__/Train.subnav.test.tsx` | ❌ W0 | 246-02-T1 | ⬜ pending |
| D-02 | Schedule controls render with no toggle click; Next session line stays | component | `npm --prefix frontend test -- --run src/components/train/__tests__/TrainScheduleSettings.test.tsx` | ✅ update | 246-03-T3 | ⬜ pending |
| D-03 | Leaderboard tab renders the card; absent from Today | component | `npm --prefix frontend test -- --run src/pages/__tests__/Train.subnav.test.tsx` | ❌ W0 | 246-02-T1, 246-08-T2 | ⬜ pending |
| D-04 | Toggle, URL page, 20 per page, Back restores page | component | `npm --prefix frontend test -- --run src/components/train/__tests__/TrainArchiveTab.test.tsx` | ❌ W0 | 246-05-T2 | ⬜ pending |
| D-05 / D-08 | No arrows; no move, motif or severity in DOM or response keys | component + router | `npm --prefix frontend test -- --run src/components/train/__tests__/TrainPuzzleCard.test.tsx`; `uv run pytest tests/routers/test_train.py -k archive` | ❌ W0 | 246-04-T1, 246-04-T2, 246-01-T1 | ⬜ pending |
| D-05 | Analyze href uses `ply - 1`; solve screen unchanged | unit | `npm --prefix frontend test -- --run src/lib/analysisUrl.test.ts src/components/train/__tests__/TrainSolveScreen.test.tsx` | ✅ extend | 246-04-T1, 246-04-T2 | ⬜ pending |
| D-06 | Deep link to Leaderboard or Archive: 0 POSTs, no Worker constructed | component | `npm --prefix frontend test -- --run src/pages/__tests__/Train.subnav.test.tsx` | ❌ W0 | 246-02-T1, 246-05-T1 | ⬜ pending |
| D-06 | Today → tab → Today: exactly 1 POST and 1 Worker | component | same | ❌ W0 | 246-02-T1 | ⬜ pending |
| D-06 | Cached reveal: no `train-tabs` on first paint, before the session resolves | component | same | ❌ W0 | 246-02-T2 | ⬜ pending |
| D-06 | `resolveTrainImmersive` truth table | unit | `npm --prefix frontend test -- --run src/hooks/__tests__/useTrainLoop.test.ts` | ❌ W0 | 246-02-T2 | ⬜ pending |
| D-06 | Medal host: absent mid-session, present on Leaderboard deep link, no reopen on switch | component | `npm --prefix frontend test -- --run src/pages/__tests__/Train.subnav.test.tsx` | ❌ W0 | 246-08-T2 | ⬜ pending |
| D-06 | Back out of loop: solve screen gone, 0 POST on the destination tab, 1 POST on return | component | same | ❌ W0 | 246-02-T2, 246-05-T1 | ⬜ pending |
| D-06 | Hidden landing: no feedback-ask view and no streak snapshot write until Today is visible; the schedule card keeps its DOM node across the flip | component | `npm --prefix frontend test -- --run src/pages/__tests__/Train.subnav.test.tsx src/components/train/__tests__/TrainStartScreen.test.tsx` | ❌ W0 | 246-08-T1 | ⬜ pending |
| D-16 | Tab switch during Tank's landing intro keeps the same copy; Back out of the solve screen's stepper stamps nothing and the next Start replays it | component | `npm --prefix frontend test -- --run src/pages/__tests__/Train.subnav.test.tsx` | ❌ W0 | 246-08-T1 | ⬜ pending |
| D-07 / D-13 | Sort newest first, stable tiebreak, filler and herring solves ignored | integration | `uv run pytest tests/repositories/test_train_repository.py -k archive` | ❌ add | 246-01-T2 | ⬜ pending |
| D-14 | Item with no `game_flaws` row listed; `total` equals progress count | integration | same | ❌ add | 246-01-T2 | ⬜ pending |
| D-07 | Corrupt PGN keeps the row with `fen` null | integration | same | ❌ add | 246-01-T2 | ⬜ pending |
| Security | Other user's items absent; bad `list` is 422; offset and limit bounds are 422; 401 without token | router | `uv run pytest tests/routers/test_train.py -k archive` | ❌ add | 246-01-T2 | ⬜ pending |
| D-09 | Per-list empty copy and Today link; error branch does not show empty copy | component | `npm --prefix frontend test -- --run src/components/train/__tests__/TrainArchiveTab.test.tsx` | ❌ W0 | 246-05-T2 | ⬜ pending |
| D-10 / D-11 | Rank text; fallback when `viewer` null; no fallback while pending | component | `npm --prefix frontend test -- --run src/components/train/__tests__/TrainStreakCard.test.tsx` | ✅ extend | 246-03-T1 | ⬜ pending |
| D-11 | Hidden and guest viewers carry a numeric Points rank | router | `uv run pytest tests/routers/test_train_leaderboard.py -k "hidden or guest"` | ✅ extend | 246-01-T2 | ⬜ pending |
| D-12 | Points line on completed only; `TrainStatsCard` gone | component | `npm --prefix frontend test -- --run src/components/train/__tests__/TrainStartScreen.test.tsx` | ✅ update | 246-03-T2 | ⬜ pending |
| D-15 / D-16 | Tabs present in intro, no-games and empty states; `train-page` class identical on every tab | component | `npm --prefix frontend test -- --run src/pages/__tests__/Train.subnav.test.tsx` | ❌ W0 | 246-02-T1, 246-02-T2, 246-05-T1 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

Prove the invariants by reverting them (project rule): the latch, `ply - 1`, the `isToday` gate on loop screens, and the first-paint clause must each fail a test when reverted.

---

## Wave 0 Requirements

- [ ] `frontend/src/lib/__tests__/trainRoute.test.ts`
- [ ] `frontend/src/hooks/__tests__/useTrainLoop.test.ts`
- [ ] `frontend/src/pages/__tests__/Train.subnav.test.tsx` (fake Worker and `trainApi` mock from `Train.solveLoop.test.tsx`; import in `beforeAll`)
- [ ] `frontend/src/components/train/__tests__/TrainArchiveTab.test.tsx`
- [ ] `frontend/src/components/train/__tests__/TrainPuzzleCard.test.tsx`
- [ ] Archive cases in `tests/routers/test_train.py` and `tests/repositories/test_train_repository.py`

---

## Manual-Only Verifications

All three are run in a real browser by the orchestrator session inline, not by a gsd-executor and not handed to the owner: 246-06-T2, with evidence in `temp/246-uat/results.md`. The evidence gate in that task's `<verify>` needs exactly one line with values for every step, so a step that was not measured or that also carries a `FAIL` line fails it. It also checks step 4's `url_ply` against `card_ply`. 246-07-T1 runs the same check on 246-06's committed SUMMARY, plus the `API` and `CLEANUP` lines, and stops if they are missing. Only an `OWNER OVERRIDE` line, written after the owner's own message, can stand in for the step lines, and it never waives `CLEANUP`.

| Behavior | Decision | Why Manual | Test Instructions |
|----------|----------|------------|-------------------|
| Tabs do not change size or position when switching | D-15 | Needs real layout, including scrollbar effects | At desktop width, switch all three tabs and compare the tab bar's position (246-06-T2 step 2) |
| Card layout on phone and desktop | D-05 | Needs real rendering | Check one column at 375px and two on desktop (246-06-T2 step 3) |
| Analyze lands on the card's board; Back restores list and page | D-04, D-05 | Needs real navigation and scroll restoration | Open Archive page 2, click Analyze, compare the board, press Back (246-06-T2 steps 4 and 5) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
