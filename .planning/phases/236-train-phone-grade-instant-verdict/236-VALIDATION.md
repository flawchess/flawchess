---
phase: "236"
slug: "train-phone-grade-instant-verdict"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-08"
---

# Phase 236 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (+ pytest-xdist locally), Vitest |
| **Config file** | `pyproject.toml`, `tests/conftest.py`; `frontend/vite.config.ts` test block |
| **Quick run command** | `uv run pytest tests/schemas/test_train_phone_grade_schema.py tests/services/test_train_pool.py -x` ; `cd frontend && npx vitest run src/lib/__tests__/trainRecheck.test.ts` |
| **Full suite command** | `uv run pytest -n auto -x` and `cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip` |
| **Estimated runtime** | ~300 seconds (full); ~30 seconds (targeted) |

---

## Sampling Rate

- **After every task commit:** Run the targeted test file(s) for that task (backend single files serially; frontend single test files)
- **After every plan wave:** Run `uv run pytest -n auto -x` + `cd frontend && npm run build && npm test -- --run`
- **Before `/gsd-verify-work`:** Full pre-merge gate (CLAUDE.md) green, plus one serial `uv run pytest -x` run of the train test files
- **Max feedback latency:** 60 seconds (targeted)

---

## Per-Task Verification Map

Filled by the planner per task (2026-10-08):

| Task | Plan | Wave | Decisions | Test Type | Automated Command | File Exists | Status |
|------|------|------|-----------|-----------|-------------------|-------------|--------|
| 236-01-T1 | 01 | 1 | D-01, D-02, D-07, D-13 | integration + migration | `uv run pytest tests/routers/test_train.py -x -k "phone_grade"` (+ alembic at-head / round-trip on d3a7f1c9e246) | ✅ file / ❌ tests | ⬜ pending |
| 236-01-T2 | 01 | 1 | D-01, D-12, D-13 | unit + integration | `uv run pytest tests/schemas/test_train_phone_grade_schema.py -x` ; `uv run pytest tests/routers/test_train.py -x -k "phone_grade or review"` | ❌ W0 (schema file) | ⬜ pending |
| 236-02-T1 | 02 | 1 | D-01, D-13 | unit + component | `cd frontend && npx vitest run src/lib/__tests__/trainPhoneGrade.test.ts src/components/train/__tests__/TrainSolveScreen.test.tsx` | ❌ W0 (lib test) | ⬜ pending |
| 236-02-T2 | 02 | 1 | D-04, D-05, D-06, D-11, D-13 | unit + component | `cd frontend && npx vitest run src/hooks/__tests__/useTrainGradingEngine.test.ts src/lib/__tests__/trainRecheck.test.ts src/lib/__tests__/trainPhoneGrade.test.ts src/components/train/__tests__/TrainSolveScreen.test.tsx` | ✅ extend | ⬜ pending |
| 236-03-T1 | 03 | 2 | D-03, D-08 | integration | `uv run pytest tests/routers/test_train.py -x -k "pre_attempt or vetted_move_material"` ; `uv run pytest tests/repositories/test_train_repository.py -x -k "answer_key"` | ✅ extend | ⬜ pending |
| 236-03-T2 | 03 | 2 | D-08 parity, D-10 | unit + integration | `uv run pytest tests/repositories/test_train_repository.py -x -k "graded_parity or resolve_grade"` ; three-file `-n auto` suite | ❌ W0 (parity test) | ⬜ pending |
| 236-04-T1 | 04 | 2 | D-12, D-14 (Pitfall 1 serialization) | unit | `cd frontend && npx vitest run src/hooks/__tests__/useTrainGradingEngine.test.ts` | ✅ extend | ⬜ pending |
| 236-04-T2 | 04 | 2 | D-14 hook API (onKeyLine) | unit | `cd frontend && npx vitest run src/hooks/__tests__/useTrainGradingEngine.test.ts` | ✅ extend | ⬜ pending |
| 236-05-T1 | 05 | 3 | D-09, D-10, D-11, D-12, D-16 | unit + component | `cd frontend && npx vitest run src/lib/__tests__/trainPhoneGrade.test.ts src/components/train/__tests__/TrainSolveScreen.test.tsx` | ✅ extend (HeldPositionWorker W0 fixture) | ⬜ pending |
| 236-05-T2 | 05 | 3 | D-12, D-15, Pitfall 1 (end to end), Pitfall 4 | unit + component | `cd frontend && npx vitest run src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts src/components/train/__tests__/TrainSolveScreen.test.tsx` | ✅ extend | ⬜ pending |
| 236-06-T1 | 06 | 4 | D-14, D-15 | component | `cd frontend && npx vitest run src/components/train/__tests__/TrainReveal.test.tsx src/components/train/__tests__/TrainSolveScreen.test.tsx` | ✅ extend | ⬜ pending |
| 236-06-T2 | 06 | 4 | D-09, D-16, Pitfall 2 | unit + component | `cd frontend && npx vitest run src/components/train/__tests__/trainBubbleState.test.ts src/components/train/__tests__/TrainSolveScreen.test.tsx src/components/train/__tests__/TrainReveal.test.tsx` | ✅ extend | ⬜ pending |
| 236-06-T3 | 06 | 4 | phase gate | full suite | CLAUDE.md pre-merge gate + serial train backend run | ✅ | ⬜ pending |

Mutation proofs are named per task in the plans (D-08 parity: 236-03-T2 a/b; Pitfall 1 serialization: 236-04-T1 (hook level) and 236-05-T2 a (component level); stale-puzzle guard: 236-05-T2 b/c; reveal fallbacks: 236-06-T2 a-c).

Decision-to-test map from RESEARCH.md:

| Decision | Behavior | Test Type | Automated Command | File Exists | Status |
|----------|----------|-----------|-------------------|-------------|--------|
| D-01 | `PhoneGrade` parses; malformed dropped to None on solve and review bodies | unit | `uv run pytest tests/schemas/test_train_phone_grade_schema.py -x` | ❌ W0 | ⬜ pending |
| D-01 | Column SQL NULL when absent, dict when present | integration | `uv run pytest tests/routers/test_train.py -k phone_grade -x` | ✅ file / ❌ tests | ⬜ pending |
| D-02 | Phone tier stored verbatim; `move_quality` stays effective tier | integration | same | ❌ | ⬜ pending |
| D-03/D-08 | `server_graded_moves` per source, illegal entries dropped | unit + integration | `uv run pytest tests/services/test_train_pool.py -k server_graded -x` | ✅ extend | ⬜ pending |
| D-08 parity | Composition list == solve-time `graded_moves` (fresh + resumed) | integration | `uv run pytest tests/repositories/test_train_repository.py -k graded_parity -x` | ❌ W0 | ⬜ pending |
| D-10 | Path 1 overrides payload tier; path 3 keeps it | unit | `uv run pytest tests/repositories/test_train_repository.py -k resolve_grade -x` | ✅ extend | ⬜ pending |
| D-12 | Review writes column write-once, not into telemetry | integration | `uv run pytest tests/routers/test_train.py -k review -x` | ✅ extend | ⬜ pending |
| D-13 | Resubmit keeps first `phone_grade` | integration | `uv run pytest tests/routers/test_train.py -k phone_grade -x` | ❌ | ⬜ pending |
| D-04/05/06 | Phone reading builder per path | unit | `cd frontend && npx vitest run src/hooks/__tests__/useTrainGradingEngine.test.ts` | ✅ extend | ⬜ pending |
| D-11 | `shouldRecheck` false for any server-graded move | unit | `cd frontend && npx vitest run src/lib/__tests__/trainRecheck.test.ts` | ✅ extend | ⬜ pending |
| D-09/14/15/16 | Instant path POSTs before engine finishes; loading then fill; error leaves no record | component | `cd frontend && npx vitest run src/components/train/__tests__/TrainSolveScreen.test.tsx src/components/train/__tests__/TrainReveal.test.tsx` | ✅ extend | ⬜ pending |
| D-12 client | Late record in Next/pagehide flush, reset on puzzle change | unit | `cd frontend && npx vitest run src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts` | ✅ extend | ⬜ pending |
| Pitfall 1 | Game-move search waits for in-flight played search | unit | useTrainGradingEngine tests | ❌ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/schemas/test_train_phone_grade_schema.py` — D-01 (mirror `test_train_recheck_schema.py`)
- [ ] D-08 composition/solve parity test in `tests/repositories/test_train_repository.py`
- [ ] Frontend fixtures: `TrainPuzzle` builder with `server_graded_moves`; FakeWorker variant that withholds `bestmove` until released

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Instant verdict timing + Your-move card fill | D-09/D-14 | Real timing needs a browser | Desktop Chrome UAT: play a server-graded non-key move, verdict appears in ~RTT, Your-move card fills ~1.5 s later |
| Eval-bar contention on phones | Pitfall 1 / A1 | No phone hardware in CI | Report-only; inspect `phone_grade` depths in prod after release |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] Mutation check: D-08 parity test and Pitfall 1 serialization test fail when their fix is reverted
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
