---
phase: "233"
slug: "train-puzzle-timing-telemetry"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-05"
---

# Phase 233 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `233-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (async, per-session cloned DB) + vitest 5 / Testing Library / jsdom |
| **Config file** | `pyproject.toml`, `frontend/vite.config.ts` (`test:` block) |
| **Quick run command** | `uv run pytest tests/routers/test_train.py -k "telemetry or review" -x` / `cd frontend && npx vitest run src/lib/__tests__/visibleStopwatch.test.ts src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts` |
| **Full suite command** | CLAUDE.md pre-merge gate (`uv run pytest -n auto -x`, ruff, ty, `npm run lint && npm run build && npm test -- --run && npm run knip`) |
| **Estimated runtime** | ~30 seconds (quick), several minutes (full gate) |

---

## Sampling Rate

- **After every task commit:** quick-run command for the touched side
- **After every plan wave:** `uv run pytest tests/routers/test_train.py tests/schemas -x` and `cd frontend && npx vitest run src/components/train src/hooks src/lib`
- **Before `/gsd-verify-work`:** full pre-merge gate must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| D-01 storage/NULL | TBD | — | D-01 | — | no telemetry → SQL NULL | integration | `uv run pytest tests/routers/test_train.py -k "solve_without_telemetry_stays_sql_null or solve_with_telemetry_stores_object" -x` | ❌ W0 | ⬜ pending |
| D-01 merge | TBD | — | D-01 | — | merge never overwrites other keys | integration | `uv run pytest tests/routers/test_train.py -k "review_flush_merges or review_flush_last_write_wins" -x` | ❌ W0 | ⬜ pending |
| D-01 forbid/caps | TBD | — | D-01 | — | unknown keys rejected, values capped | unit | `uv run pytest tests/schemas/test_train_telemetry_schema.py -x` | ❌ W0 | ⬜ pending |
| D-02 optional | TBD | — | D-02 | — | invalid telemetry never costs a solve | integration | `uv run pytest tests/routers/test_train.py -k "invalid_telemetry_still_solves" -x` | ❌ W0 | ⬜ pending |
| D-02 measurement | TBD | — | D-02 | — | N/A | unit | `cd frontend && npx vitest run src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts` | ❌ W0 | ⬜ pending |
| D-03 route | TBD | — | D-03 | — | 404 foreign user / unsolved row | integration | `uv run pytest tests/routers/test_train.py -k review -x` | ❌ W0 | ⬜ pending |
| D-03 Next flush | TBD | — | D-03 | — | N/A | component | `cd frontend && npx vitest run src/components/train/__tests__/TrainSolveScreen.test.tsx -t telemetry` | ✅ file | ⬜ pending |
| D-06 pagehide | TBD | — | D-06 | — | Bearer header on keepalive fetch | unit | `cd frontend && npx vitest run src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts -t pagehide` | ❌ W0 | ⬜ pending |
| D-04 visible only | TBD | — | D-04 | — | N/A | unit | `cd frontend && npx vitest run src/lib/__tests__/visibleStopwatch.test.ts` | ❌ W0 | ⬜ pending |
| D-04 caps parity | TBD | — | D-04 | — | N/A | unit | `uv run pytest tests/schemas/test_train_telemetry_parity.py -x` | ❌ W0 | ⬜ pending |
| D-05 grading | TBD | — | D-05 | — | N/A | integration | `uv run pytest tests/routers/test_train.py -k "telemetry_does_not_change_grading" -x` | ❌ W0 | ⬜ pending |
| D-07 exit | TBD | — | D-07 | — | N/A | unit | `uv run pytest tests/schemas/test_train_telemetry_schema.py -x` | ❌ W0 | ⬜ pending |
| D-08 toggle | TBD | — | D-08 | — | N/A | component | `cd frontend && npx vitest run src/components/train/__tests__/TrainLeaderboardCard.test.tsx -t "tab-switch"` | ✅ | ⬜ pending |
| D-09 client | TBD | — | D-09 | — | N/A | unit | `cd frontend && npx vitest run src/lib/__tests__/deviceClass.test.ts` | ❌ W0 | ⬜ pending |
| D-09 privacy | TBD | — | D-09 | — | disclosure present | component | `cd frontend && npx vitest run src/pages/__tests__/Privacy.test.tsx` | ❌ W0 | ⬜ pending |
| D-11..D-14 counters | TBD | — | D-11..D-14 | — | N/A | unit/component | `cd frontend && npx vitest run src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts src/components/train/__tests__/TrainLineStepper.test.tsx` | ❌ W0 | ⬜ pending |
| Analyze round trip | TBD | — | Discretion | — | N/A | unit | `cd frontend && npx vitest run src/lib/__tests__/trainRevealCache.test.ts` | ✅ file | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/schemas/test_train_telemetry_schema.py` — D-01/D-07 model behaviour
- [ ] `tests/schemas/test_train_telemetry_parity.py` — caps parity (regex approach of `test_train_score_parity.py`)
- [ ] `tests/routers/test_train.py` — `_solve(..., telemetry=)` kwarg, `_review` and `_telemetry` helpers
- [ ] `frontend/src/lib/__tests__/visibleStopwatch.test.ts`
- [ ] `frontend/src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts`
- [ ] `frontend/src/lib/__tests__/deviceClass.test.ts`
- [ ] `recordReview` added to `trainApi` mocks in `TrainSolveScreen.test.tsx`, `TrainSolveScreen.restoredGameArrow.test.tsx`, `Train.solveLoop.test.tsx`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| pagehide keepalive flush actually lands on a real browser unload | D-03/D-06 | jsdom cannot unload a page | Dev build: solve a puzzle, close the tab on the reveal, check `drill_solves.telemetry` for `exit = "pagehide"` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
