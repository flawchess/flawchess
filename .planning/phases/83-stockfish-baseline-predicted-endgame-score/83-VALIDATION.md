---
phase: 83
slug: stockfish-baseline-predicted-endgame-score
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-11
---

# Phase 83 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (backend), vitest (frontend) |
| **Config file** | `pyproject.toml` (backend), `frontend/vitest.config.ts` (frontend) |
| **Quick run command** | `uv run pytest tests/services/test_eval_utils.py tests/services/test_endgame_service.py -x` |
| **Full suite command** | `uv run pytest && cd frontend && npm test -- --run` |
| **Estimated runtime** | ~120 seconds (full); ~10 seconds (quick) |

---

## Sampling Rate

- **After every task commit:** Run scoped `pytest` for the file touched (or the matching frontend test)
- **After every plan wave:** Run `uv run pytest` for backend waves; `npm test -- --run` for frontend wave
- **Before `/gsd-verify-work`:** Full suite must be green + `uv run ty check app/ tests/` zero errors + `npm run lint` clean
- **Max feedback latency:** 30 seconds for scoped tests; 120 seconds for full

---

## Per-Task Verification Map

> Filled by planner during plan generation; one row per task with `<automated>` block.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 83-01-* | 01-eval-utils | 1 | D-02, D-03 | — | N/A (pure functions) | unit | `uv run pytest tests/services/test_eval_utils.py` | ❌ W0 | ⬜ pending |
| 83-02-* | 02-backend-plumbing | 2 | D-04, D-05, D-06, D-07, D-21 | — | NULL eval filter applied | integration | `uv run pytest tests/services/test_endgame_service.py -k expected_score` | ❌ W0 | ⬜ pending |
| 83-03-* | 03-ui-restructure | 3 | D-08..D-13 | — | N/A | RTL component | `cd frontend && npx vitest run src/components/charts/EndgameStartVsEndSection.test.tsx` | ✅ | ⬜ pending |
| 83-04-* | 04-benchmark-calibration | 4 | D-14, D-15, D-16 | — | N/A | drift + unit | `uv run python scripts/gen_endgame_zones_ts.py && git diff --exit-code frontend/src/generated/endgameZones.ts` | ✅ | ⬜ pending |
| 83-05-* | 05-llm-prompt | 5 | D-17, D-18, D-19, D-20 | — | N/A | unit | `uv run pytest tests/services/test_insights_service.py -k endgame_start_vs_end` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/services/test_eval_utils.py` — created in Plan 1 (target file does not yet exist)
- [ ] Plan 2 extends existing `tests/services/test_endgame_service.py` with `entry_expected_score`-scoped cases — no new file, but new test functions count as Wave 0 stubs for D-04..D-07
- [ ] No framework install needed (pytest + vitest already configured)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 2×2 grid renders correctly on mobile (390px) with eval/WDL on top and score-axis bullets on bottom | D-12 | Responsive collapse order is layout-only; jsdom doesn't render breakpoints | Open dev server, narrow viewport to 390px, navigate to Endgames → verify "Where you start" tile shows entry-eval → achievable-score top-to-bottom, "What you do with it" shows WDL → endgame-score top-to-bottom |
| "Achievable score" popover wording reads correctly and avoids the word "underperformance" | D-10 | Wording polish is UX judgement | Hover/tap info-icon on the new bullet, read paragraph aloud, verify "2300+", "Lichess winning-chances sigmoid", "Compare against your achieved Endgame score" all present; "underperformance" absent |
| LLM narration for the new finding sounds correct on a real user's data (achievable=0.58 vs achieved=0.47 scenario) | D-18 | Prompt quality requires reading live output | After Plan 5 deploys, generate insights for a representative user; verify narration leads with the gap and uses entry_eval_pawns as the explanatory unit; verify "underperformance" is absent |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (tests/services/test_eval_utils.py)
- [ ] No watch-mode flags (all commands use `--run` / `-x`)
- [ ] Feedback latency < 30s for scoped tests
- [ ] `nyquist_compliant: true` set in frontmatter once planner fills task IDs

**Approval:** pending
