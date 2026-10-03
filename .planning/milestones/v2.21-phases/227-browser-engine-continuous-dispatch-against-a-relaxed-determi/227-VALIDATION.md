---
phase: "227"
slug: "browser-engine-continuous-dispatch-against-a-relaxed-determi"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-02"
---

# Phase 227 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `227-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (frontend), pytest (verdict twin), Node `*.check.mjs` scripts (harness) |
| **Config file** | `frontend/vite.config.ts` test block; `pyproject.toml` |
| **Quick run command** | `cd frontend && npx vitest run src/lib/engine/__tests__/mctsSearch.continuous.test.ts src/lib/engine/__tests__/mctsSearch.test.ts` |
| **Full suite command** | `( cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip ) && uv run pytest tests/scripts/test_engine_dispatch_227_verdict.py` |
| **Estimated runtime** | ~30 seconds (quick); several minutes (full) |

---

## Sampling Rate

- **After every task commit:** Run the quick command (continuous test file + `mctsSearch.test.ts`)
- **After every plan wave:** Run the full suite command plus the harness check scripts
- **Before `/gsd-verify-work`:** Full CLAUDE.md pre-merge gate must be green
- **Max feedback latency:** 30 seconds (quick)

---

## Per-Task Verification Map

Filled in by the planner/executor per task. Decision-level map from research:

| Decision | Behavior | Test Type | Automated Command | File Exists | Status |
|----------|----------|-----------|-------------------|-------------|--------|
| D-11 | c=1 continuous ≡ round (snapshots + result, jittered fixtures) | unit | `npx vitest run src/lib/engine/__tests__/mctsSearch.continuous.test.ts -t "c=1"` | ❌ W0 | ⬜ pending |
| D-11 | round mode unchanged when `dispatchMode` omitted vs `'round'` | unit | existing `mctsSearch.test.ts`, `mctsSearch.roundFill.test.ts` + one equality test | ✅ / ❌ W0 | ⬜ pending |
| D-09 / L-2 | result settling after abort is not applied | unit | `-t "after abort"` | ❌ W0 | ⬜ pending |
| D-09 | early stop aborts inner signal; stale result not applied | unit | `-t "early stop"` | ❌ W0 | ⬜ pending |
| D-10 | `nodesEvaluated ≤ maxNodes`; `inFlight == 0` at exhaustion | unit | `-t "budget"` | ❌ W0 | ⬜ pending |
| D-08 | no leaf dispatched twice while pending; arrival-order apply | unit | `-t "arrival order"` | ❌ W0 | ⬜ pending |
| D-08 | per-fill block scoping keeps c in flight on a peaked policy | unit | `-t "fill"` | ❌ W0 | ⬜ pending |
| Y-9 | exactly one dispatch until the root is applied | unit | `-t "root guard"` | ❌ W0 | ⬜ pending |
| Y-8 | rejection propagates, siblings aborted, no unhandled rejection | unit | `-t "rejection"` | ❌ W0 | ⬜ pending |
| X-8 | settlement with no waiter still wakes the loop | unit | `-t "wakeup"` | ❌ W0 | ⬜ pending |
| Pitfall 7 | outer-signal listener removed after search | unit | `-t "listener"` | ❌ W0 | ⬜ pending |
| D-19 | equal-priority app SF grades served FIFO | unit | `npx vitest run src/lib/engine/__tests__/workerPool.test.ts -t "FIFO"` | ❌ W0 | ⬜ pending |
| Pitfall 2 | Node pool abort stops engine, no stale result | check script | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/stockfish-pool.check.mjs` | ✅ extend | ⬜ pending |
| D-18 | harness Maia in worker_threads; event loop not blocked during FIFO bursts | check script | new/extended Maia check script | ❌ W0 | ⬜ pending |
| D-14 | harness dispatch mode matches app flag; round bit-identity PASS | check script | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-determinism.check.mjs` | ✅ extend | ⬜ pending |
| Tooling tripwire | round-mode MQ under new harness == 226 `a21s` TSVs | orchestrator run + diff | MQ `--dispatch-mode round --repeats 1` + diff script | ❌ W0 | ⬜ pending |
| D-01/D-03/D-17/D-15 | verdict arithmetic, frozen constants, invalid states | pytest | `uv run pytest tests/scripts/test_engine_dispatch_227_verdict.py` | ❌ W0 | ⬜ pending |
| D-06 | dev WebGPU tool absent from prod bundle | build + grep | `npm run build && ! grep -r "<marker>" dist/` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Mutation checks (required):** for each guard (apply-after-abort, early-stop, per-fill block clearing, D-10 budget guard, listener removal, harness abort, FIFO tie-break), revert it and confirm the named test fails. Record in the SUMMARY.

---

## Wave 0 Requirements

- [ ] `frontend/src/lib/engine/__tests__/mctsSearch.continuous.test.ts`
- [ ] `scripts/engine_dispatch_227_verdict.py` + `tests/scripts/test_engine_dispatch_227_verdict.py`
- [ ] Harness: Node pool abort, Maia worker_threads, `--dispatch-mode` switches, MQ `--repeats`, interleave driver + machine-speed probe
- [ ] Round-mode MQ diff tripwire against 226 `a21s` TSVs

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| WebGPU Maia latency and bot-move wall, round vs continuous | D-06 / D-07 | Needs a machine with a WebGPU adapter (hardware leg; this Linux Chrome has none) | Owner opens the dev-only tool on localhost (secure, cross-origin-isolated) and pastes the report |
| Ship / hold decision | D-04 / D-00 | Owner decides from the mechanical verdict | Read the verdict report; record the decision |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
