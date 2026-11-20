---
phase: "257"
slug: "facepalm-rate-library-stats"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-20"
---

# Phase 257 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `257-RESEARCH.md` §"Validation Architecture".

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (+ pytest-asyncio, xdist); vitest 5.1.0 + Testing Library |
| **Config file** | `pyproject.toml [tool.pytest.ini_options]`; `frontend/vite*.config` |
| **Quick run command** | `uv run pytest tests/services/test_facepalm_score.py tests/services/test_flaw_comparison.py -x` and `cd frontend && npx vitest run src/components/library` |
| **Full suite command** | `uv run pytest -n auto -x` and `cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip` |
| **Estimated runtime** | quick ~60 seconds, full ~10 minutes |

---

## Sampling Rate

- **After every task commit:** Run the quick command of the touched area
- **After every plan wave:** Run `uv run pytest -n auto -x` plus `cd frontend && npm test -- --run`
- **Before `/gsd-verify-work`:** The full pre-merge gate from CLAUDE.md must be green (ruff, ty x2,
  function-size, pytest, frontend lint/build/test/knip)
- **Max feedback latency:** 120 seconds for the quick commands

---

## Per-Task Verification Map

Task IDs are filled in by the planner; the rows below are the decision-to-test contract they must cover.

| Decision | Behavior | Test Type | Automated Command | File Exists | Status |
|----------|----------|-----------|-------------------|-------------|--------|
| D-01 | `FACEPALM_STATS_MIN == 0.7`, separate from `FACEPALM_SCORE_MIN` | unit | `uv run pytest tests/services/test_facepalm_score.py -k stats_min` | ❌ W0 | ⬜ pending |
| D-02 | Type twin parity (grid, aggregate grid, extreme rows, stored facts); tie → allowed loss; no material → missed win; unknown loss → None; lambda-free | unit + DB | `uv run pytest tests/services/test_facepalm_score.py -k type` | ❌ W0 | ⬜ pending |
| D-08 | `query_flaws` returns the type; type None when score None | repo | `uv run pytest tests/test_library_repository.py -k facepalm` | extend | ⬜ pending |
| D-08 | `fetch_page_facepalm_scores` returns (score, type), owner side only | repo | `uv run pytest tests/test_library_repository.py -k FetchPageFacepalm` | extend | ⬜ pending |
| D-08 | `_build_eval_series` sets the type only on blunders | unit | `uv run pytest tests/services/test_eval_chart_service.py -k facepalm` | extend | ⬜ pending |
| D-03 | Share pooled over the window; same dates as the trend; null below the floor; unscored excluded; user side only | unit + DB | `uv run pytest tests/services/test_library_service.py -k facepalm_share` | ❌ W0 | ⬜ pending |
| D-12 | Rows paired per 100 user moves; `player_rate - opp_rate == delta`; total = missed + allowed; same anchor game set as `fetch_flaw_comparison` | DB | `uv run pytest tests/services/test_flaw_comparison.py -k facepalm` | ❌ W0 | ⬜ pending |
| D-13 | `has_zone False`; significance computed but drives no colour | unit | `uv run pytest tests/services/test_flaw_comparison.py -k facepalm` and `cd frontend && npx vitest run src/lib/__tests__/gapBar.test.ts` | ❌ W0 / extend | ⬜ pending |
| D-06 | Drill and filter readers unchanged | regression | `uv run pytest tests/repositories/test_blunder_check_repository.py tests/test_query_utils.py` | ✅ | ⬜ pending |
| D-08/D-09 | Chip, mini-chip and tooltip line take the type colours; no `FACEPALM_CHIP*` left | component | `cd frontend && npx vitest run src/components/library/__tests__/FlawCard.test.tsx src/components/analysis/__tests__/VariationTree.test.tsx` | extend | ⬜ pending |
| D-10 | Explanation names the type (both variants) | component | `cd frontend && npx vitest run src/components/library/__tests__/FacepalmExplanation.test.tsx` | extend | ⬜ pending |
| D-14..D-16 | Labels, hints with 70%, intro, popover "no typical range", no "Fewer is better." | component | `cd frontend && npx vitest run src/components/library/stats/__tests__/GapPopover.test.tsx` | extend; FacepalmCard test ❌ W0 | ⬜ pending |
| D-03 | Share chart renders; text fallback below 2 non-null points; tooltip counts | component | `cd frontend && npx vitest run src/components/library/__tests__/FacepalmShareChart.test.tsx` | ❌ W0 | ⬜ pending |
| D-11 | Card behind the gate, follows the TC switch | component | `cd frontend && npx vitest run src/components/library/stats/__tests__/LibraryStatsSections.test.tsx` | extend | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/facepalm_seed.py` — a `facepalm_type=` option on `facepalm_fact_columns` (missed-win seeds at
  >= 0.7), plus `tests/services/test_facepalm_seed.py` coverage
- [ ] Type-twin parity tests in `tests/services/test_facepalm_score.py`
- [ ] Facepalm comparison and share tests in `tests/services/test_flaw_comparison.py` and
  `tests/services/test_library_service.py`
- [ ] `FacepalmShareChart.test.tsx`, `FacepalmCard.test.tsx`; update `stats/__tests__/flawStatsFixtures.ts`

---

## Manual-Only Verifications

| Behavior | Decision | Why Manual | Test Instructions |
|----------|----------|------------|-------------------|
| Share line is not jumpy on real accounts at the chosen floor | D-03 | Needs prod data (dev has one scored user) | Run `temp/facepalm-257/prod_share_probe.sql` read-only on prod; keep the floor if `max_step_below50` is routinely above ~0.08 while `max_step_at_or_above50` stays under ~0.06 |
| Comparison query latency on the largest account | D-11 | Needs prod data volume | `EXPLAIN (ANALYZE, BUFFERS)` on `temp/facepalm-257/prod_comparison_probe.sql` for the largest account; above ~1 s, split the rows into their own endpoint |
| Opponent side of the card shows real values | D-12 | Dev has only 144 of 5,624 opponent blunders scored for user 28 | Check on prod after deploy (or after an opponent backfill on dev) |
| Tint and copy read correctly on the three chip surfaces | D-08..D-10 | Visual | Browser UAT: flaws card, analysis move list, eval chart tooltip, both types |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
