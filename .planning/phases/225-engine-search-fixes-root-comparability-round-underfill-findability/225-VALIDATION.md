---
phase: "225"
slug: "engine-search-fixes-root-comparability-round-underfill-findability"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-09-27"
---

# Phase 225 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `225-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (frontend); Node `--self-test` harness checks; Python stdlib self-test |
| **Config file** | `frontend/vite.config.ts` `test` block (project-wide timeouts; never per-file) |
| **Quick run command** | `cd frontend && npx vitest run src/lib/engine/__tests__/mctsSearch.test.ts src/lib/engine/__tests__/findability.test.ts src/lib/engine/__tests__/fallbackExpectimax.test.ts src/lib/engine/__tests__/selectBotMove.test.ts` |
| **Full suite command** | `cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip` (+ CLAUDE.md pre-merge gate before squash-merge) |
| **Estimated runtime** | quick ~5 s; full frontend ~2-3 min |

---

## Sampling Rate

- **After every task commit:** Run the quick run command
- **After every plan wave:** Run `cd frontend && npm test -- --run && npm run lint && npm run build`
- **Before `/gsd-verify-work`:** Full pre-merge gate green and accept-rule verdicts rendered
- **Max feedback latency:** 5 seconds (quick run)

---

## Per-Task Verification Map

Task IDs are filled by the planner; rows map decisions to their automated checks.

| Decision | Plan/Task | Behavior | Test Type | Automated Command | File Exists | Status |
|----------|-----------|----------|-----------|-------------------|-------------|--------|
| D-06/D-08 | 225-04 T1 | Every non-tail round dispatches `c` expansions under one- and two-candidate peaked policies (50 nodes, c=4) | unit | `cd frontend && npx vitest run src/lib/engine/__tests__/mctsSearch.roundFill.test.ts` | ❌ W0 | ⬜ pending |
| D-06 mutation | 225-04 T2 | Reverting the restart makes D-08 fail | mutation | same command with the fix reverted | — | ⬜ pending |
| D-06 determinism | 225-04 T2 | Peaked fixture bit-identical under jitter; ENGINE-07 tests unchanged | unit | `cd frontend && npx vitest run src/lib/engine/__tests__/mctsSearch.test.ts -t "ENGINE-07"` | ✅ | ⬜ pending |
| D-01 | 225-05 T1/T2 | Unsettled in-window child blocks clear-winner stop; out-of-window does not; closed top child counts as settled | unit + mutation | `cd frontend && npx vitest run src/lib/engine/__tests__/mctsSearch.test.ts -t "stop rule"` | ✅ rewrite + ❌ W0 additions | ⬜ pending |
| D-03 | 225-05 T2 | Flatness branch unchanged | unit | same | ✅ | ⬜ pending |
| D-02 | 225-05 T2 | Allowance constant present on bot stop rule, >= 0 | unit | `cd frontend && npx vitest run src/hooks/useFlawChessEngine.test.tsx` | ✅ extend | ⬜ pending |
| D-02 measurement | 225-01 T1, 225-03 T1 | Root-trace deltas to pooled-p90 allowance (fallback 0.10) | unit + orchestrator run | `uv run pytest tests/scripts/test_engine_search_fixes_allowance.py -x` | ❌ W0 | ⬜ pending |
| D-10a/b/c/e | 225-06 T1/T2 | rankScore bounds, normalized Vfb, zero-prior guard, clamp case, rewritten D-03 + "demotes" tests | unit | `cd frontend && npx vitest run src/lib/engine/__tests__/findability.test.ts src/lib/engine/__tests__/fallbackExpectimax.test.ts src/lib/engine/__tests__/mctsSearch.test.ts` | ✅ rewrite | ⬜ pending |
| D-10d | 225-06 T2 | `selectBotMove` identical pick under any `rankedLines` permutation | unit | `cd frontend && npx vitest run src/lib/engine/__tests__/selectBotMove.test.ts` | ❌ W0 | ⬜ pending |
| tooling | 225-01 T1 | Stop-rule harness new flags parse | self-test | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-dispatch-stop-rule.mjs --self-test` | ✅ extend | ⬜ pending |
| tooling | 225-01 T2 | Move-quality runner parseArgs + fixture integrity | self-test | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-move-quality.mjs --self-test` | ❌ W0 | ⬜ pending |
| D-11/D-13/D-14 verdict | 225-02 T1/T2 | Gate criteria, calibration branch table, item decisions, cells-to-json | unit | `uv run pytest tests/scripts/test_engine_search_fixes_verdict.py -x` | ❌ W0 | ⬜ pending |
| verdict | 225-02 T2 | Parity arithmetic | self-test | `uv run python scripts/calibration_parity_verdict.py --self-test` | ✅ | ⬜ pending |
| gates | 225-07 T2/T3, 225-08 T1 | Throughput / stop-rule / move-quality / calibration per accept rule | measurement (orchestrator-inline) | per `reports/engine-search-fixes-225/accept-rule.md`; `uv run python scripts/engine_search_fixes_verdict.py gates` | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/src/lib/engine/__tests__/mctsSearch.roundFill.test.ts` — D-08, written RED against current code first
- [ ] Guard tests (out-of-window, closed-top) in `mctsSearch.test.ts`
- [ ] D-10d permutation test in `selectBotMove.test.ts`
- [ ] `scripts/engine-move-quality.mjs` + `--self-test`
- [ ] Stop-rule harness flags (no-stop-rule, root trace, guard window) + self-test cases
- [ ] `tests/scripts/test_engine_search_fixes_allowance.py` — D-02 allowance calculator (225-01)
- [ ] `tests/scripts/test_engine_search_fixes_verdict.py` — gate verdict, calibration branch table, cells-to-json (225-02)

---

## Manual-Only Verifications

| Behavior | Decision | Why Manual | Test Instructions |
|----------|----------|------------|-------------------|
| Gate arm runs (throughput ~80 min, calibration ~4.5 h) | D-11..D-14 | Multi-hour, must run from the orchestrator (setsid nohup + Monitor), not an executor | Follow the accept rule and runbook; record verdicts in the phase report |
| Item 3 qualitative ordering check | D-13 | Judgement on a handful of winning positions | Compare `rankedLines[0]` before/after on hard-to-find winning positions (move-quality runner `analysis_move` column) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
