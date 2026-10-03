---
phase: "230"
slug: "weekly-train-leaderboards"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-03"
---

# Phase 230 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (backend); vitest + Testing Library (frontend) |
| **Config file** | `pyproject.toml` / `tests/conftest.py`; `frontend/vite.config.ts` test block |
| **Quick run command** | `uv run pytest tests/services/test_train_leaderboard.py tests/services/test_train_score_parity.py -x` (backend) / `cd frontend && npx vitest run <touched test file>` (frontend) |
| **Full suite command** | `uv run pytest -n auto -x` and `( cd frontend && npm test -- --run )` |
| **Estimated runtime** | ~5 seconds quick, ~300 seconds full |

---

## Sampling Rate

- **After every task commit:** Run the quick command for the touched layer
- **After every plan wave:** Run `uv run pytest tests/services tests/repositories/test_train_leaderboard_repository.py tests/routers/test_train_leaderboard.py -x` + `cd frontend && npm test -- --run src/components/train src/components/settings src/lib`
- **Before `/gsd-verify-work`:** Full CLAUDE.md pre-merge gate must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

Filled in by the planner/executor against the final task IDs. Decision → check mapping (from RESEARCH.md § Validation Architecture):

Task IDs are `230-<plan>-T<task>` (e.g. `230-01-T2` = Plan 01, Task 2). The test file for every ❌ W0 row is created by the task that lists it, before or with the code it covers (TDD tasks write the failing test first).

| Task ID | Decision | Behavior | Test Type | Automated Command | File Exists | Status |
|---------|----------|----------|-----------|-------------------|-------------|--------|
| 230-01-T2 | D-01 | Backend constants equal `trainScore.ts` | unit (regex parity) | `uv run pytest tests/services/test_train_score_parity.py -x` | ❌ W0 (created in 230-01-T2) | ⬜ pending |
| 230-02-T3 | D-01 | Points = guess + tier (legacy NULL tier = 0); accuracy excludes SHARP_FILLER; unsolved rows ignored | repo integration (unique ISO week) | `uv run pytest tests/repositories/test_train_leaderboard_repository.py -k "points or filler or unsolved" -x` | ❌ W0 (created in 230-02-T2) | ⬜ pending |
| 230-01-T1 | D-02 | Week bounds, seconds_remaining, out-of-week solves ignored via pinned `dev_now_utc` | router | `uv run pytest tests/routers/test_train_leaderboard.py -k "week or tracer or boards" -x` | ❌ W0 (created in 230-01-T1) | ⬜ pending |
| 230-01-T2 | D-02 | Monday 00:00 UTC boundary, Sunday 23:59:59.999999, non-UTC input | unit | `uv run pytest tests/services/test_train_leaderboard.py -k window -x` | ❌ W0 (created in 230-01-T2) | ⬜ pending |
| 230-02-T3 | D-02 | Deadline-spanning session splits; half-open window on real rows | repo integration | `uv run pytest tests/repositories/test_train_leaderboard_repository.py -k "window or deadline" -x` | ❌ W0 (created in 230-02-T2) | ⬜ pending |
| 230-01-T2 | D-03/D-19 | <20 non-filler = tentative + puzzles_to_qualify, still ranked; zero non-filler → no accuracy entry | unit | `uv run pytest tests/services/test_train_leaderboard.py -k qualify -x` | ❌ W0 | ⬜ pending |
| 230-01-T2 | D-04 | 1,1,1,4 ranks; puzzles-desc tie order; top 5 + ±2 slicing; pass target nearest strictly better | unit | `uv run pytest tests/services/test_train_leaderboard.py -k "rank or slice or pass_target" -x` | ❌ W0 | ⬜ pending |
| 230-01-T2 | D-05/D-15 | Name precedence; blank → "Anonymous" | unit | `uv run pytest tests/services/test_train_leaderboard.py -k display_name -x` | ❌ W0 | ⬜ pending |
| 230-01-T2, 230-02-T3 | D-06/D-13 | Hidden user absent from others' rows/ranks; hidden viewer gets private would-be row | unit + router | `uv run pytest tests/services/test_train_leaderboard.py tests/routers/test_train_leaderboard.py -k hidden -x` | ❌ W0 | ⬜ pending |
| 230-01-T2, 230-02-T3 | D-14 | Guest never on others' boards; guest ghost row | unit + router | `uv run pytest tests/services/test_train_leaderboard.py tests/routers/test_train_leaderboard.py -k guest -x` | ❌ W0 | ⬜ pending |
| 230-02-T1, 230-02-T2 | D-12/D-18 | rank without session; foreign session id no effect; bad session_id → 422; first session → null; Accuracy may be worse (returned as computed) | unit + repo + router | `uv run pytest tests/services/test_train_leaderboard.py tests/repositories/test_train_leaderboard_repository.py tests/routers/test_train_leaderboard.py -k "without_session or session or contribution" -x` | ❌ W0 | ⬜ pending |
| 230-01-T1 | D-16 | Migration c4e7a91d2b58 up/down clean on the dev DB | migration | `uv run alembic upgrade head && uv run alembic current` | ❌ W0 (created in 230-01-T1) | ⬜ pending |
| 230-04-T1 | D-16 | `PUT /users/me/profile {leaderboard_hidden}` round-trip; omitted leaves unchanged; GET exposes it; non-bool 422 | router | `uv run pytest tests/test_users_router.py -k leaderboard -x` | ✅ extend | ⬜ pending |
| 230-04-T2 | D-06/D-13/D-16 | Opt-out via the API hides the user from other viewers, keeps their private row | router (end to end) | `uv run pytest tests/routers/test_train_leaderboard.py -k opt_out -x` | ✅ extend | ⬜ pending |
| 230-01-T1, 230-01-T2 | Security | No `user_id`/email in any row; key set pinned on a seeded week (k=4), incl. the pass target | router key-set test | `uv run pytest tests/routers/test_train_leaderboard.py -k key_set -x` | ❌ W0 | ⬜ pending |
| 230-03-T1 | D-07/D-08 | Card order on start screen (completed, fresh, exhausted) | component | `cd frontend && npx vitest run src/components/train/__tests__/TrainStartScreen.test.tsx` | ✅ extend | ⬜ pending |
| 230-03-T1 | D-04/D-14/D-15 | Rows, shared ranks, viewer highlight, gap marker, guest nudge | component | `cd frontend && npx vitest run src/components/train/__tests__/TrainLeaderboardCard.test.tsx` | ❌ W0 (created in 230-03-T1) | ⬜ pending |
| 230-03-T2 | D-09 | Tab persisted; throwing localStorage → Points | unit | `cd frontend && npx vitest run src/lib/__tests__/trainLeaderboard.test.ts` | ❌ W0 (created in 230-03-T1) | ⬜ pending |
| 230-03-T2 | D-03/D-10/D-19 | "Accuracy" label + helper; qualifier and not-entered hints; no ability framing | component | `cd frontend && npx vitest run src/components/train/__tests__/TrainLeaderboardCard.test.tsx` | ❌ W0 | ⬜ pending |
| 230-03-T3 | D-02/D-13/D-14 | Countdown format and rollover invalidation; hidden / guest row labels | unit + component | `cd frontend && npx vitest run src/lib/__tests__/trainLeaderboard.test.ts src/components/train/__tests__/TrainLeaderboardCard.test.tsx` | ❌ W0 | ⬜ pending |
| 230-03-T2 | Umami | `tab-switch` on user tab change only | unit + component | `cd frontend && npx vitest run src/lib/__tests__/analytics.test.ts src/components/train/__tests__/TrainLeaderboardCard.test.tsx` | ✅ extend | ⬜ pending |
| 230-04-T1, 230-04-T2 | D-16 | Privacy card guest-hidden, excluded from Reset, error/pending states | component | `cd frontend && npx vitest run src/components/settings/__tests__/` | ✅ extend + ❌ new | ⬜ pending |
| 230-05-T1, 230-05-T2 | D-11/D-12/D-17/D-18/D-19 | Rank-line copy variants and fetch with session_id | unit + component | `cd frontend && npx vitest run src/components/train/__tests__/TrainScoreRankLines.test.tsx src/lib/__tests__/trainLeaderboard.test.ts` | ❌ W0 (created in 230-05-T1) | ⬜ pending |
| 230-05-T1 | D-11 | Rank lines sit right under "Points: x/y" | component | `cd frontend && npx vitest run src/components/train/__tests__/TrainScoreScreen.test.tsx` | ✅ extend | ⬜ pending |
| 230-05-T3 | Gate | Full root CLAUDE.md pre-merge gate + serial leaderboard run | gate | `uv run pytest -n auto -x` and `( cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip )` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/services/test_train_leaderboard.py` — pure window/rank/slice/name/qualifier/without-session tests
- [ ] `tests/services/test_train_score_parity.py` — regex parity with `frontend/src/lib/trainScore.ts`
- [ ] `tests/repositories/test_train_leaderboard_repository.py` — unique-ISO-week fixtures, filler exclusion, guest/hidden flags, caller-scoped contribution (created in 230-02-T2)
- [ ] `tests/routers/test_train_leaderboard.py` — auth, guest, `dev_now_utc` override, key-set, foreign `session_id`; every test pins its own declared week from the module k table (k 0-9 Plan 01, 10-29 Plan 02, 30-39 Plan 04)
- [ ] Frontend: `trainLeaderboard.test.ts`, `TrainLeaderboardCard.test.tsx`, `TrainScoreRankLines.test.tsx`, privacy card test
- [ ] Mocks for the new hook/components in `TrainStartScreen.test.tsx`, `TrainScoreScreen.test.tsx`, `SettingsPanel.test.tsx`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Mobile layout of the tabbed card at `max-w-2xl`, plus the multi-account opt-out and guest flows | D-07 / D-13 / D-14 / discretion | Visual fit, two browser profiles | Browser UAT on the dev build at phone width, scripted in 230-05-T3's human-check (Claude runs it with claude-in-chrome per project memory); mismatches go to 230-UAT.md with screenshots under temp/230-uat/ |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
