---
phase: "235"
slug: "train-grading-server-answer-key"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-07"
---

# Phase 235 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (+ pytest-asyncio, xdist) backend; vitest (jsdom) frontend |
| **Config file** | `pyproject.toml` / `tests/conftest.py`; `frontend/vite.config.ts` test block |
| **Quick run command** | `uv run pytest tests/services/test_train_pool.py tests/schemas/ -x` ; `cd frontend && npx vitest run src/lib src/hooks/__tests__/useTrainGradingEngine.test.ts` |
| **Full suite command** | `uv run pytest -n auto -x` and `cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip` |
| **Estimated runtime** | ~240 seconds (full); ~30 seconds (quick) |

---

## Sampling Rate

- **After every task commit:** the touched file's test module (serial, single file)
- **After every plan wave:** `uv run pytest tests/routers/test_train.py tests/repositories/test_train_repository.py tests/services/test_train_pool.py tests/schemas -n auto` + `cd frontend && npm test -- --run`
- **Before `/gsd-verify-work`:** full pre-merge gate (CLAUDE.md) must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

Task IDs are filled by the planner; the decision-level map below is the contract.

| Decision | Behavior | Test Type | Test File (new = Wave 0) | Assertion | Status |
|----------|----------|-----------|--------------------------|-----------|--------|
| D-05/D-06 | `answer_key_for` per source | unit | `tests/services/test_train_pool.py` | SR key = best_move, type from blob, runner_up only when sharp; herring key = ladder[0].move_uci; filler key = solution_uci, type sharp; illegal key -> None | ⬜ pending |
| D-05 | wire key set | router | `tests/routers/test_train.py::test_pre_attempt_payload_shape` (update) | pre-attempt puzzle keys = old six + new key/type fields | ⬜ pending |
| D-05 | resume path carries keys (herring ladder deferred column) | repo | `tests/repositories/test_train_repository.py` | resumed puzzle key equals pool ladder[0] / best_move / solution | ⬜ pending |
| D-07 | no best_move -> null key | repo/router | same | SR with no `game_positions` row -> key None, type still computed | ⬜ pending |
| D-02 | sharp `su` graded server-side | repo | `tests/repositories/test_train_repository.py` | client "good" on `su` -> recorded per blob `b`/`s`; `vetted_moves == []` | ⬜ pending |
| D-14 | confirmed disagreement accepted | unit + router | pure `_resolve_grade` tests; router test | sharp + off-key + off-su + good + confirmed -> `correct_guess` True for BOTH guesses | ⬜ pending |
| D-14 | sanity checks reject | unit | same | soft/herring, played == key, played == su, tier != good, outcome resolved -> normal `correct_guess` | ⬜ pending |
| D-17/D-18 | column write | router | `tests/routers/test_train.py` | no recheck -> SQL NULL; resolved + confirmed stored; resubmit keeps first | ⬜ pending |
| D-18 | schema drop-invalid | schema | `tests/schemas/test_train_recheck_schema.py` (W0) | extra key / bad outcome / ES out of range / NaN -> None, solve still 200 | ⬜ pending |
| Stale bundle | old SolveRequest body | router | `tests/routers/test_train.py` | body without recheck -> 200, grading unchanged | ⬜ pending |
| D-01/D-08 | anchor = after-key search; played == key no search | hook | `frontend/src/hooks/__tests__/useTrainGradingEngine.test.ts` | mount posts after-key FEN; gradeMove(key) sends no second `go`; off-key compares after-key vs after-played ES | ⬜ pending |
| D-07 | null key -> root search | hook | same | `startGrading(FEN, null)` posts root FEN | ⬜ pending |
| D-09 | clamp to key line; game-move == key shortcut | hook | same | played line eval capped at key line; game move == key resolves without search | ⬜ pending |
| D-10 | re-check trigger | unit | `frontend/src/lib/__tests__/trainRecheck.test.ts` (W0) | true only for sharp + key + off-key + off-su + good | ⬜ pending |
| D-11/D-13/D-16 | re-check search + outcomes | hook | `useTrainGradingEngine.test.ts` | two 3000ms searches with re-check node cap; confirmed -> unclamped; resolved -> slow tier; re-check timeout constant | ⬜ pending |
| D-12 | wait copy | component | `TrainSolveScreen.test.tsx` / `trainBubbleState.test.ts` | re-check in flight shows re-check copy, not `GRADING_COPY` | ⬜ pending |
| D-15 | prose | unit | `TrainReveal.test.tsx` `describe('guessFeedbackProse')` | disagreement -> exact new line for both guesses; six existing strings unchanged | ⬜ pending |
| D-09 | arrow names key | component | `TrainReveal.test.tsx` / `trainArrows.test.ts` | best arrow/box UCI = key when phone search prefers another move | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

Mutation discipline: for D-14 sanity checks and the omit-when-absent write, prove each test by reverting the check and watching it fail.

---

## Wave 0 Requirements

- [ ] `tests/schemas/test_train_recheck_schema.py` — D-18 validation
- [ ] `frontend/src/lib/__tests__/trainRecheck.test.ts` — D-10 trigger

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| User-28 repro depth/ES at 1.5s and 3s budgets | D-10/D-11 | Real SF18 WASM timing, device-dependent | `node temp/phase235/probe_budget.mjs` or `frontend/scripts/measure-train-movetime.mjs --fens=...` |
| Reveal on a real Train session shows key arrow and coherent copy | D-09/D-15 | End-to-end UX | Browser UAT on the dev build (memory: run UAT yourself) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
