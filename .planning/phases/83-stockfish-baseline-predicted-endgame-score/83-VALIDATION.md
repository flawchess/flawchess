---
phase: 83
slug: stockfish-baseline-predicted-endgame-score
status: ready
nyquist_compliant: true
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
| **Quick run command** | `uv run pytest tests/services/test_eval_utils.py tests/services/test_endgame_service.py tests/services/test_score_confidence.py tests/services/test_insights_service.py -x` |
| **Full suite command** | `uv run pytest && cd frontend && npm test -- --run` |
| **Estimated runtime** | ~120 seconds (full); ~10 seconds (quick) |

---

## Sampling Rate

- **After every task commit:** Run scoped `pytest` for the file touched (or the matching frontend test)
- **After every plan wave:** Run `uv run pytest` for backend waves; `npm test -- --run` for frontend wave
- **Before `/gsd-verify-work`:** Full suite green + `uv run ty check app/ tests/` zero errors + `npm run lint` clean + `cd frontend && npx tsc --noEmit` zero errors
- **Max feedback latency:** 30 seconds for scoped tests; 120 seconds for full

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 83-01-01 | 01-eval-utils | 1 | D-03 | — | N/A (pure functions) | unit (RED) | `uv run pytest tests/services/test_eval_utils.py` | ❌ W0 | ⬜ pending |
| 83-01-02 | 01-eval-utils | 1 | D-02 | — | N/A | unit (GREEN) | `uv run pytest tests/services/test_eval_utils.py -x && uv run ty check app/services/eval_utils.py tests/services/test_eval_utils.py` | ❌ W0 | ⬜ pending |
| 83-02-01 | 02-backend-plumbing | 2 | D-04, D-05, D-22 | — | N/A | unit + regression | `uv run pytest tests/services/test_score_confidence.py -x && uv run ty check app/services/score_confidence.py tests/services/test_score_confidence.py` | ✅ | ⬜ pending |
| 83-02-02 | 02-backend-plumbing | 2 | D-21 | — | N/A | smoke + ty | `uv run python -c "from app.schemas.endgames import EndgamePerformanceResponse; r = EndgamePerformanceResponse(); assert r.entry_expected_score == 0.0" && uv run ty check app/schemas/endgames.py` | ✅ | ⬜ pending |
| 83-02-03 | 02-backend-plumbing | 2 | D-04, D-05, D-06, D-07 | — | NULL eval filter; mate INCLUDED inversion | integration | `uv run pytest tests/services/test_endgame_service.py -k 'expected_score or entry_eval' -x && uv run ty check app/services/endgame_service.py` | ✅ | ⬜ pending |
| 83-03-01 | 03-ui-restructure | 4 | D-21 (mirror) | — | N/A | TS check | `cd frontend && npx tsc --noEmit; cd ..` | ✅ | ⬜ pending |
| 83-03-02 | 03-ui-restructure | 4 | D-10 | — | Forbidden-word grep (`underperformance`) | TS + grep | `cd frontend && npx tsc --noEmit; cd .. && (grep -ci 'underperformance' frontend/src/components/popovers/AchievableScorePopover.tsx; test $? -ne 0)` | ❌ W0 | ⬜ pending |
| 83-03-03 | 03-ui-restructure | 4 | D-08..D-13 | — | N/A | RTL component | `cd frontend && npx vitest run src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx --reporter=verbose && npx tsc --noEmit && npm run lint; cd ..` | ✅ | ⬜ pending |
| 83-04-01 | 04-benchmark-calibration | 3 | D-14, D-15 | — | bic.status='completed' AND sparse-cell excluded | drift + existence | `test -f reports/benchmarks-2026-05-11.md && grep -c 'bic.status' .claude/skills/benchmarks/SKILL.md && grep -c '2400.*classical\|sparse' .claude/skills/benchmarks/SKILL.md` | ❌ W0 | ⬜ pending |
| 83-04-02 | 04-benchmark-calibration | 3 | D-15 | — | N/A | checkpoint | Human approval of `(typical_lower, typical_upper)` pair | n/a | ⬜ pending |
| 83-04-03 | 04-benchmark-calibration | 3 | D-14, D-16 | — | CI drift gate | drift + ty | `uv run python scripts/gen_endgame_zones_ts.py && git diff --exit-code frontend/src/generated/endgameZones.ts && uv run ty check app/services/endgame_zones.py && grep -c 'entry_expected_score' app/services/endgame_zones.py` | ✅ | ⬜ pending |
| 83-05-01 | 05-llm-prompt | 4 | D-17, D-19 | — | No `verdict` field regression | unit | `uv run pytest tests/services/test_insights_service.py -k 'endgame_start_vs_end or third_finding' -x && uv run ty check app/services/insights_service.py tests/services/test_insights_service.py` | ✅ | ⬜ pending |
| 83-05-02 | 05-llm-prompt | 4 | D-18, D-20 | — | Forbidden-word grep + version bump | grep + ty | `grep -c '"endgame_v25"' app/services/insights_llm.py && grep -c 'endgame_v24' app/services/insights_llm.py && grep -c 'entry_expected_score' app/prompts/endgame_insights.md` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/services/test_eval_utils.py` — created in Plan 1 Task 1 (RED phase; the module under test does not yet exist, expected to fail with `ModuleNotFoundError`)
- [ ] `frontend/src/components/popovers/AchievableScorePopover.tsx` — created in Plan 3 Task 2 (the directory does not yet exist)
- [ ] `reports/benchmarks-2026-05-11.md` — created in Plan 4 Task 1
- [ ] New tests in `tests/services/test_endgame_service.py`, `tests/services/test_score_confidence.py`, `tests/services/test_insights_service.py` count as Wave 0 stubs for their respective requirements (no new file, new test functions)
- [ ] No framework install needed (pytest + vitest already configured)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 2x2 grid renders correctly on mobile (390px) with eval/WDL on top and score-axis bullets on bottom | D-12 | Responsive collapse order is layout-only; jsdom does not render breakpoints | Open dev server, narrow viewport to 390px, navigate to Endgames; verify "Where you start" tile shows entry-eval then achievable-score top-to-bottom; verify "What you do with it" shows WDL then endgame-score top-to-bottom |
| "Achievable score" popover wording reads correctly and avoids the word "underperformance" | D-10 | Wording polish is UX judgement | Hover/tap info-icon on the new bullet, read paragraph aloud, verify "2300+", "Lichess winning-chances sigmoid", "Compare against your achieved Endgame score" all present; "underperformance" absent |
| Recommended cohort band is sensible given the benchmark report | D-14, D-15 | Editorial-judgement tightening is a human call (memory feedback_zone_band_judgement.md) | Read reports/benchmarks-2026-05-11.md "Recommendations" and "Collapse verdict" sections; verify pooled p50 is reasonable under equal-footing filter; approve typical_lower/typical_upper pair |
| LLM narration for the new finding sounds correct on a real user's data (achievable=0.58 vs achieved=0.47 scenario) | D-18 | Prompt quality requires reading live output | After Plan 5 deploys, generate insights for a representative user; verify narration leads with the gap and uses entry_eval_pawns as the explanatory unit; verify "underperformance" is absent |
| Visual juxtaposition: achievable-vs-achieved gap is directly readable across the bottom row of the 2x2 | D-22 | Visual UX assessment | Open the Endgames page on a user with a known gap; verify both bullets share the W+0.5D axis; verify the visual offset between them communicates the gap without prose |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (or a manual-only row above with explicit rationale)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (tests/services/test_eval_utils.py, frontend/src/components/popovers/AchievableScorePopover.tsx, reports/benchmarks-2026-05-11.md)
- [x] No watch-mode flags (all commands use `--run` / `-x`)
- [x] Feedback latency < 30s for scoped tests
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** ready
