---
phase: "231"
slug: "weekly-leaderboard-medals"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-04"
---

# Phase 231 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (backend, per-run cloned DB from a migrated template); vitest + Testing Library (frontend) |
| **Config file** | `pyproject.toml`, `tests/conftest.py`; `frontend/vite.config.ts` (test block), `frontend/src/vitest.setup.ts` |
| **Quick run command** | `uv run pytest tests/services/test_train_leaderboard.py tests/services/test_train_medals.py -x` |
| **Full suite command** | `uv run pytest -n auto -x` and `( cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip )` |
| **Estimated runtime** | ~30 seconds targeted; full gate several minutes |

---

## Sampling Rate

- **After every task commit:** Run the targeted command(s) for the touched area (see map below)
- **After every plan wave:** `uv run pytest tests/services tests/repositories tests/routers -n auto -k "leaderboard or medal"` and `cd frontend && npm test -- --run src/components/train src/components/admin src/lib`
- **Before `/gsd-verify-work`:** Full pre-merge gate from CLAUDE.md green, plus one full **serial** backend run (serial CI hides isolation bugs)
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

Derived requirements (no REQ-IDs mapped; keyed by CONTEXT decisions). Plan-Task ids filled in at planning (231-NN-PLAN.md, task N).

| Req (derived) | Plan-Task | Behavior | Test Type | Automated Command | File Exists | Status |
|---------------|-----------|----------|-----------|-------------------|-------------|--------|
| SNAP / D-01 | 01-T1, 01-T2 | public-only rows; Accuracy qualified-only; hidden/guest/tentative excluded | unit | `uv run pytest tests/services/test_train_leaderboard.py -k final_standings -x` | ✅ file, ❌ tests | ⬜ pending |
| D-02 / D-06 | 01-T2 | ranks equal live-board ranks; Olympic 1,1,3 / 1,2,2 / 1,1,1 | unit | `uv run pytest tests/services/test_train_leaderboard.py -k "final_standings or medal_for" -x` | ❌ | ⬜ pending |
| D-05 | 01-T2 | 0 pts / 0% gets a row + rank, `medal` None | unit | `uv run pytest tests/services/test_train_leaderboard.py -k medal_for -x` | ❌ | ⬜ pending |
| FINAL due weeks | 01-T2 | start week, grace boundary, skips finalized, ascending | unit | `uv run pytest tests/services/test_train_medals.py -k due_weeks -x` | ❌ W0 | ⬜ pending |
| FINAL idempotent | 01-T1, 06-T2 | second call inserts nothing; empty week gets a marker | repository | `uv run pytest tests/repositories/test_train_medals_finalization.py -k finalize -x` | ❌ W0 | ⬜ pending |
| FINAL concurrency | 06-T1 | two sessions finalize concurrently → one marker, no duplicate rows | repository | `uv run pytest tests/repositories/test_train_medals_finalization.py -k concurrent -x` | ❌ | ⬜ pending |
| FINAL failure isolation | 01-T2 | finalizer raises → board still 200, Sentry captured once, no marker | router | `uv run pytest tests/routers/test_train_medals.py -k failure -x` | ❌ | ⬜ pending |
| DEL | 01-T2, 06-T2 | delete user → `user_id` NULL, `display_name` "Deleted user"; trigger in `pg_trigger` | repository | `uv run pytest tests/repositories/test_train_medals_finalization.py -k "deleted or trigger" -x` | ❌ | ⬜ pending |
| TALLY | 02-T3 | grouped counts per board for visible keys only; no ids in payload | unit + router | `uv run pytest tests/services/test_train_leaderboard.py -k "tally or visible_keys" -x`; `uv run pytest tests/routers/test_train_medals.py tests/repositories/test_train_medals_repository.py -k tally -x` | ❌ | ⬜ pending |
| PODIUM / D-07..D-09 | 01-T1, 01-T2 | prev week only; Anonymous if hidden now (not for self); Deleted user; ties | unit + router | `uv run pytest tests/routers/test_train_medals.py -k "last_week or podium" -x` | ❌ | ⬜ pending |
| FINISH / D-03 / D-04 | 01-T1, 01-T2 | line only for own non-medal row; hidden-now viewer still sees own line | unit + router | `uv run pytest tests/services/test_train_leaderboard.py -k viewer_final_rank -x`; `uv run pytest tests/routers/test_train_medals.py -k podium -x` | ❌ | ⬜ pending |
| CLAIM | 02-T1, 02-T2 | unclaimed ordering, `shared`; claim scoped to caller (IDOR), idempotent | router | `uv run pytest tests/routers/test_train_medals.py -k "unclaimed or claim" -x` | ❌ W0 | ⬜ pending |
| Key-set (no ids) | 01-T1, 02-T3 | response keys include `medals`/`last_week`, never `user_id`/`id`/`email` | router | `uv run pytest tests/routers/test_train_leaderboard.py -x` | ✅ (update) | ⬜ pending |
| TALLY UI | 03-T2 | non-zero types only, gold/silver/bronze order, aria-label, in name block | component | `cd frontend && npx vitest run src/components/train/medals` | ❌ | ⬜ pending |
| PODIUM / FINISH UI | 03-T1, 03-T2 | podium above helper; hidden when empty; second hint line | component | `cd frontend && npx vitest run src/components/train/__tests__/TrainLeaderboardCard.test.tsx` | ✅ (extend) | ⬜ pending |
| DIALOG D-10..D-13 | 04-T1, 04-T2 | title count, entries newest first; Claim → unlock + sound once + confetti unless muted/reduced; dismiss → POST only | component | `cd frontend && npx vitest run src/components/train/medals` | ❌ | ⬜ pending |
| Landing mount | 04-T1 | host on empty/completed/default branches | component | `cd frontend && npx vitest run src/components/train/__tests__/TrainStartScreen.test.tsx` | ✅ (extend) | ⬜ pending |
| DEMO | 05-T1, 05-T2 | renders real components; scenario buttons; no API calls | component | `cd frontend && npx vitest run src/components/admin` | ❌ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/services/test_train_medals.py` — `due_weeks` pure tests
- [ ] `tests/repositories/test_train_medals_finalization.py` (Plan 06) — base Monday 2034-01-02, k 0-19, ids 93700-93719; rollback-scoped `db_session` except the concurrency test, which cleans its weeks' markers + users before seeding and in finally
- [ ] `tests/repositories/test_train_medals_repository.py` (Plan 02) — same base Monday, k 20-39, ids 93720-93739, rollback-scoped `db_session`
- [ ] `tests/routers/test_train_medals.py` — end-to-end via pinned clock + `monkeypatch MEDALS_START_WEEK`
- [ ] Update `tests/routers/test_train_leaderboard.py` key-set test
- [ ] Frontend fixture updates: `TrainLeaderboardCard.test.tsx`, `Train.solveLoop.test.tsx` (trainApi mock), `TrainStartScreen.test.tsx`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| First-tap win sound on iOS | D-12 / D-13 | Real-device audio unlock cannot be automated | Open admin "Leaderboard medals demo" on an iPhone, run a celebrate scenario, tap Claim, confirm sound + confetti |
| Medal colors readable on dark card; 375 px wrap | Tally / podium | Visual judgement | Admin demo in dev, desktop + 375 px viewport |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
