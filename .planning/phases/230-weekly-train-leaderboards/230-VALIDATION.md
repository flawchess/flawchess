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

| Decision | Behavior | Test Type | Automated Command | File Exists | Status |
|----------|----------|-----------|-------------------|-------------|--------|
| D-01 | Backend constants equal `trainScore.ts` | unit (regex parity) | `uv run pytest tests/services/test_train_score_parity.py -x` | ❌ W0 | ⬜ pending |
| D-01 | Points = guess + tier; accuracy excludes SHARP_FILLER; unsolved rows ignored | repo integration (unique ISO week) | `uv run pytest tests/repositories/test_train_leaderboard_repository.py -x` | ❌ W0 | ⬜ pending |
| D-02 | Monday 00:00 UTC boundary, Sunday 23:59:59.999999, deadline-spanning session splits; `dev_now_utc` | unit + router | `uv run pytest tests/services/test_train_leaderboard.py -k window -x` | ❌ W0 | ⬜ pending |
| D-03/D-19 | <20 non-filler = tentative + puzzles_to_qualify, still ranked; zero non-filler → no accuracy entry | unit | `uv run pytest tests/services/test_train_leaderboard.py -k qualify -x` | ❌ W0 | ⬜ pending |
| D-04 | 1,1,1,4 ranks; puzzles-desc tie order; top 5 + ±2 slicing; pass target nearest strictly better | unit | `uv run pytest tests/services/test_train_leaderboard.py -k "rank or slice or pass_target" -x` | ❌ W0 | ⬜ pending |
| D-05/D-15 | Name precedence; blank → "Anonymous" | unit | `uv run pytest tests/services/test_train_leaderboard.py -k display_name -x` | ❌ W0 | ⬜ pending |
| D-06/D-13 | Hidden user absent from others' rows/ranks; hidden viewer gets private would-be row | unit + router | `uv run pytest tests/routers/test_train_leaderboard.py -k hidden -x` | ❌ W0 | ⬜ pending |
| D-14 | Guest never on others' boards; guest ghost row | unit + router | `uv run pytest tests/routers/test_train_leaderboard.py -k guest -x` | ❌ W0 | ⬜ pending |
| D-12/D-18 | rank without session; foreign session id no effect; first session → null; Accuracy worse → no delta | unit + router + component | `uv run pytest tests/services/test_train_leaderboard.py -k without_session -x` | ❌ W0 | ⬜ pending |
| D-16 | `PUT /users/me/profile {leaderboard_hidden}` round-trip; omitted leaves unchanged; GET exposes it; migration up/down | router | `uv run pytest tests/test_users_router.py -k leaderboard -x` | ✅ extend | ⬜ pending |
| Security | No `user_id`/email in any row | router key-set test | `uv run pytest tests/routers/test_train_leaderboard.py -k key_set -x` | ❌ W0 | ⬜ pending |
| D-07/D-08 | Card order on start screen (both branches) | component | `cd frontend && npx vitest run src/components/train/__tests__/TrainStartScreen.test.tsx` | ✅ extend | ⬜ pending |
| D-09 | Tab persisted; throwing localStorage → Points | unit | `cd frontend && npx vitest run src/lib/__tests__/trainLeaderboard.test.ts` | ❌ W0 | ⬜ pending |
| D-10 | "Accuracy" label + helper; no "skill" | component | `cd frontend && npx vitest run src/components/train/__tests__/TrainLeaderboardCard.test.tsx` | ❌ W0 | ⬜ pending |
| D-11/D-12/D-17/D-18 | Rank-line copy variants | unit + component | `cd frontend && npx vitest run src/components/train/__tests__/TrainScoreRankLines.test.tsx` | ❌ W0 | ⬜ pending |
| D-16 | Privacy card guest-hidden, excluded from Reset | component | `cd frontend && npx vitest run src/components/settings/__tests__/` | ✅ extend + ❌ new | ⬜ pending |
| Umami | `tab-switch` on user tab change only | unit | `cd frontend && npx vitest run src/lib/__tests__/analytics.test.ts` | ✅ extend | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/services/test_train_leaderboard.py` — pure window/rank/slice/name/qualifier/without-session tests
- [ ] `tests/services/test_train_score_parity.py` — regex parity with `frontend/src/lib/trainScore.ts`
- [ ] `tests/repositories/test_train_leaderboard_repository.py` — unique-ISO-week fixtures, filler exclusion, guest/hidden flags
- [ ] `tests/routers/test_train_leaderboard.py` — auth, guest, `dev_now_utc` override, key-set, foreign `session_id`
- [ ] Frontend: `trainLeaderboard.test.ts`, `TrainLeaderboardCard.test.tsx`, `TrainScoreRankLines.test.tsx`, privacy card test
- [ ] Mocks for the new hook/components in `TrainStartScreen.test.tsx`, `TrainScoreScreen.test.tsx`, `SettingsPanel.test.tsx`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Mobile layout of the tabbed card at `max-w-2xl` | D-07 / discretion | Visual fit | Browser UAT on the dev build at phone width (run it yourself per project memory) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
