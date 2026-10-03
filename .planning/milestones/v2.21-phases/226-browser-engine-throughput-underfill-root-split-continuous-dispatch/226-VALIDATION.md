---
phase: "226"
slug: "browser-engine-throughput-underfill-root-split-continuous-dispatch"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-09-28"
---

# Phase 226 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest ^5 (frontend engine), Node `--self-test` / `*.check.mjs` harness checks, pytest (verdict and calibration twins) |
| **Config file** | `frontend/vite.config.ts` test block (project-wide timeouts, never per-file); `pyproject.toml` pytest config |
| **Quick run command** | `cd frontend && npx vitest run src/lib/engine/__tests__/mctsSearch.test.ts src/lib/engine/__tests__/mctsSearch.roundFill.test.ts src/lib/engine/__tests__/rootSplit.test.ts` plus the touched tool's `--self-test` or `uv run pytest tests/scripts/test_engine_throughput_226_*.py -x` |
| **Full suite command** | CLAUDE.md pre-merge gate (ruff format/check, ty x2, function-size gate, `uv run pytest -n auto -x`, `cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip`) |
| **Estimated runtime** | ~226 seconds for quick commands; measurement plans (07, 12, 14) run hours to days by design and are orchestrator-inline |

---

## Sampling Rate

- **After every task commit:** the task's own `<automated>` command(s) (unit tests, `--self-test`, one-position smokes)
- **After every plan wave:** `cd frontend && npm test -- --run && npm run lint && npm run build`; `uv run pytest tests/scripts -x`
- **Before `/gsd-verify-work`:** full pre-merge gate green (Plan 226-14 Task 3) and `engine_throughput_226_verdict.py gates` exits 0
- **Max feedback latency:** 226 seconds for code tasks; measurement checkpoints report through their resume signals

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 226-01-01 | 01 | 1 | D-03 | T-226-02 | Warm grading pools receive zero Clear Hash; adjudication stays cleared | real-engine check | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/stockfish-pool.check.mjs` and `... calibration-determinism.check.mjs --no-clear-hash --games 1` | ❌ W0 (created in task) | ⬜ pending |
| 226-01-02 | 01 | 1 | D-18, D-19, D-08 | T-226-01 | Harness forwards gradeRoot; split dormant (exit 3) before A21S | real-engine check | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/stockfish-pool.check.mjs --root-split` (expects 3) | ❌ W0 | ⬜ pending |
| 226-02-01 | 02 | 1 | D-13 | — | N/A | self-test + smoke | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-search-trace.mjs --self-test` | ❌ W0 | ⬜ pending |
| 226-02-02 | 02 | 1 | D-14 | T-226-03, T-226-04 | Fixture rule committed before generation; integrity enforced | self-test + smoke | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/build-move-quality-fixture.mjs --self-test` | ❌ W0 | ⬜ pending |
| 226-02-03 | 02 | 1 | D-17 | — | N/A | smoke | `profile_search.mjs 8 4 4 0 <json>` prints the D17 line | ✅ (script exists) | ⬜ pending |
| 226-03-01 | 03 | 1 | D-09, D-10 | T-226-05 | Thresholds derived from the null, not chosen | unit | `uv run pytest tests/scripts/test_engine_throughput_226_calibration.py -x` | ❌ W0 | ⬜ pending |
| 226-03-02 | 03 | 1 | D-10, D-11 | T-226-06 | Void comparison escalates, never silent no-refit | unit + mutation | same pytest file | ❌ W0 | ⬜ pending |
| 226-03-03 | 03 | 1 | D-09..D-17, D-19 | T-226-05 | Protocol committed before any step-0 data | doc check | grep of step0-protocol.md + no data dir | ❌ W0 | ⬜ pending |
| 226-04-01 | 04 | 2 | D-04, D-18 | T-226-07 | pool_size recorded; split dormant | self-test + smoke | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-grading-depth-ab.mjs --self-test` | ❌ W0 (self-test new) | ⬜ pending |
| 226-04-02 | 04 | 2 | D-04, D-14 | T-226-08 | root_split_calls column present | self-test | `... engine-dispatch-stop-rule.mjs --self-test && ... engine-move-quality.mjs --self-test` | ✅ | ⬜ pending |
| 226-05-01 | 05 | 2 | D-10, D-16 | T-226-09, T-226-10 | Unset constants exit 2; mislabeled arm data exit 1 | unit | `uv run pytest tests/scripts/test_engine_throughput_226_verdict.py -x` | ❌ W0 | ⬜ pending |
| 226-05-02 | 05 | 2 | D-11, D-12, D-15, D-16 | T-226-09 | Item rules and refit decision as pre-registered | unit + mutation | same pytest file | ❌ W0 | ⬜ pending |
| 226-05-03 | 05 | 2 | D-14, D-16, D-17 | T-226-09 | Design inputs by formula only | unit | same pytest file | ❌ W0 | ⬜ pending |
| 226-06-01 | 06 | 3 | D-16 | T-226-11 | Real root candidates | self-test + smoke | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-root-split-content.mjs --self-test` | ❌ W0 | ⬜ pending |
| 226-06-02 | 06 | 3 | D-16, D-18 | T-226-12 | Pool source proves a split happened | smoke | warm prototype smoke; pool smoke exits 3 pre-A21S | ❌ W0 | ⬜ pending |
| 226-07-01..03 | 07 | 4 | D-03, D-04, D-09, D-10, D-13, D-14, D-16, D-17, D-19 | T-226-13..15 | Idle-box gate, copy-back before worktree removal | measurement (orchestrator) | `build-move-quality-fixture.mjs --check`, git ls-files step0 check, `engine_throughput_226_verdict.py design-inputs` exit 0 | — | ⬜ pending |
| 226-08-01..03 | 08 | 5 | D-01..D-20 (contract) | T-226-16, T-226-17 | Constants pinned to committed design inputs | doc + unit | grep checks; `uv run pytest tests/scripts/test_engine_throughput_226_verdict.py -x` | — | ⬜ pending |
| 226-09-01 | 09 | 6 | D-12, D-13 | T-226-18, T-226-19 | Allowed-file diff only; restart loop terminates | unit + mutation + trace smoke | `cd frontend && npx vitest run src/lib/engine/__tests__/mctsSearch.roundFill.test.ts src/lib/engine/__tests__/mctsSearch.test.ts` | ❌ (cherry-picked from d428a0194) | ⬜ pending |
| 226-09-02 | 09 | 6 | D-12 | T-226-18 | Guard mutation-proven | unit + mutation | same + `npm run build && npm run lint` | ❌ (cherry-picked from 4a13b2f3a/27beff12f) | ⬜ pending |
| 226-10-01 | 10 | 7 | D-18, D-08 | T-226-21 | Providers without gradeRoot byte-identical | unit + real-engine | `... stockfish-pool.check.mjs --root-split` exits 0; depth-ab smoke splits | ❌ W0 (rootSplit.test.ts) | ⬜ pending |
| 226-10-02 | 10 | 7 | D-18 | T-226-20 | Merge never fabricates a grade | unit + mutation | `cd frontend && npx vitest run src/lib/engine/__tests__/rootSplit.test.ts src/lib/engine/__tests__/mctsSearch.test.ts -t "gradeRoot|partitionCandidates|mergeShardGrades|ENGINE-07"` | ❌ W0 | ⬜ pending |
| 226-11-01 | 11 | 8 | D-18, L-3, L-4 | T-226-23 | One success-only merged cache write | unit (MockWorker E2E) | `cd frontend && npx vitest run src/lib/engine/__tests__/workerPool.test.ts` | ✅ file, ❌ new block | ⬜ pending |
| 226-11-02 | 11 | 8 | D-08, D-18, L-2 | T-226-22, T-226-24 | Any failed shard resolves empty; siblings stopped; no listener leak | unit + mutation | `... workerPool.test.ts -t "root split"` + full frontend gate | ❌ W0 | ⬜ pending |
| 226-11-03 | 11 | 8 | D-17 | — | N/A | unit (conditional) | treeCommon/mctsSearch tests when CANDIDATE_CAP_ARM_ACTIVE | ✅ | ⬜ pending |
| 226-12-01..03 | 12 | 9 | D-03, D-04, D-08..D-16 | T-226-25..28 | Lock before data; arms verified; unsplit A21S rejected | measurement (orchestrator) | `engine_throughput_226_verdict.py reruns` + `gates` exit 0 | — | ⬜ pending |
| 226-13-01..03 | 13 | 10 | D-01, D-02, D-05..D-07, D-09..D-11, D-15, D-16, D-18 | T-226-29, T-226-30 | Ship exactly what the verdict passes | CLI + unit + build | `gates` exit 0; `cd frontend && npx vitest run src/lib/engine && npm run build` | — | ⬜ pending |
| 226-14-01..03 | 14 | 11 | D-04, D-11, D-20 | T-226-31..33 | Refit iff verdict says refit; no generated drift | orchestrator + full gate | regen drift check; full pre-merge gate | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Created inside the plans that need them (no separate Wave 0 plan; each is written test-first in its own task):

- [ ] `scripts/lib/stockfish-pool.check.mjs` (Plan 01)
- [ ] `--no-clear-hash` arm in `scripts/lib/calibration-determinism.check.mjs` (Plan 01)
- [ ] `scripts/engine-search-trace.mjs --self-test`, `scripts/build-move-quality-fixture.mjs --self-test` (Plan 02)
- [ ] `tests/scripts/test_engine_throughput_226_calibration.py` (Plan 03)
- [ ] `scripts/engine-grading-depth-ab.mjs --self-test` and `--pool-size` cases in the stop-rule and move-quality self-tests (Plan 04)
- [ ] `tests/scripts/test_engine_throughput_226_verdict.py` (Plan 05)
- [ ] `scripts/engine-root-split-content.mjs --self-test` (Plan 06)
- [ ] `frontend/src/lib/engine/__tests__/rootSplit.test.ts` and the gradeRoot routing block in `mctsSearch.test.ts` (Plan 10)
- [ ] "root split" describe block in `workerPool.test.ts` (Plan 11)

No framework install needed; vitest, Node and pytest are already present.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real-phone bot game latency on a 2-worker pool | D-04 (report-only) | Needs the owner's phone; the Node pool-of-2 run is the gating measurement | Open the dev build on the phone, play a bot game, note move latency; record in 226-UAT.md (never blocks) |
| Dev-build smoke of analysis search and a bot game | D-18 (app pool path) | The app WorkerPool is only unit-tested (MockWorker); a real-worker smoke catches integration regressions | Automated by the orchestrator in the browser (Plan 14 Task 2); result in 226-UAT.md |
| Lock decision before gate data | D-10 | A pre-registration one-way door needs an explicit human choice | Plan 12 Task 1 checkpoint:decision |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 226s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** {pending / approved YYYY-MM-DD}
