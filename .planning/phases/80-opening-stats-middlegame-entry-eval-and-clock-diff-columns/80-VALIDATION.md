---
phase: 80
slug: opening-stats-middlegame-entry-eval-and-clock-diff-columns
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-03
---

# Phase 80 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (backend) + vitest (frontend) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`), `frontend/vitest.config.ts` |
| **Quick run command** | `uv run pytest tests/test_eval_confidence.py tests/repositories/test_openings_repository.py -x -q` |
| **Full suite command** | `uv run pytest && cd frontend && npm test` |
| **Estimated runtime** | ~30 seconds quick, ~3 minutes full |

---

## Sampling Rate

- **After every task commit:** Run quick command (relevant module tests).
- **After every plan wave:** Run full suite (`uv run pytest`).
- **Before `/gsd-verify-work`:** Full suite green AND `uv run ty check app/ tests/` zero errors AND `cd frontend && npm run build && npm run lint && npm run knip` all pass.
- **Max feedback latency:** 60 seconds for unit tests.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 80-01-01 | 01 | 1 | D-04 | — | one-sample t-test confidence helper produces low/medium/high per N+p thresholds | unit | `uv run pytest tests/test_eval_confidence.py -x` | ❌ W0 | ⬜ pending |
| 80-01-02 | 01 | 1 | D-04 | — | helper handles N<10, zero variance, single sample edge cases without exception | unit | `uv run pytest tests/test_eval_confidence.py::test_edge_cases -x` | ❌ W0 | ⬜ pending |
| 80-02-01 | 02 | 1 | D-01..D-05 | — | `OpeningWDL` schema has new optional fields; older clients still parse | unit | `uv run pytest tests/test_stats_schemas.py -x` | ❌ W0 | ⬜ pending |
| 80-03-01 | 03 | 2 | D-01,D-04 | — | repo aggregation returns avg eval (signed user-perspective), CI bounds, eval_n, p-value, confidence | integration | `uv run pytest tests/repositories/test_openings_repository.py::test_mg_entry_eval_aggregation -x` | ❌ W0 | ⬜ pending |
| 80-03-02 | 03 | 2 | D-05 | — | repo returns avg clock diff at MG entry (pct + seconds, signed) | integration | `uv run pytest tests/repositories/test_openings_repository.py::test_mg_entry_clock_diff -x` | ❌ W0 | ⬜ pending |
| 80-03-03 | 03 | 2 | D-01..D-05 | — | mate-at-MG-entry rows excluded from eval mean, included in WDL total | integration | `uv run pytest tests/repositories/test_openings_repository.py::test_mate_excluded_from_eval -x` | ❌ W0 | ⬜ pending |
| 80-03-04 | 03 | 2 | D-01..D-05 | — | EXPLAIN ANALYZE on `/openings/stats` does not regress > 25% on representative user | manual | `pytest tests/perf/test_openings_stats_explain.py::test_no_regression -x` | ❌ W0 | ⬜ pending |
| 80-04-01 | 04 | 2 | D-01..D-05 | — | service wires new fields into response payload | unit | `uv run pytest tests/services/test_stats_service.py -x` | ❌ W0 | ⬜ pending |
| 80-05-01 | 05 | 3 | D-02 | — | `MiniBulletChart` renders CI whisker when `ciLow`/`ciHigh` provided; no whisker when omitted | unit | `cd frontend && npm test -- MiniBulletChart` | ❌ W0 | ⬜ pending |
| 80-05-02 | 05 | 3 | D-02 | — | open-ended whisker (no cap) when CI extends past chart domain | unit | `cd frontend && npm test -- MiniBulletChart.openEnded` | ❌ W0 | ⬜ pending |
| 80-06-01 | 06 | 3 | D-01..D-06 | — | `MostPlayedOpeningsTable` renders new columns desktop + mobile second line | unit | `cd frontend && npm test -- MostPlayedOpeningsTable` | ❌ W0 | ⬜ pending |
| 80-07-01 | 07 | 3 | D-03 | — | board hidden on Stats subtab desktop, mobile unchanged | unit | `cd frontend && npm test -- Openings.statsBoard` | ❌ W0 | ⬜ pending |
| 80-08-01 | 08 | 4 | D-01..D-06 | — | `npm run build`, `npm run lint`, `npm run knip` all green; `ty check` zero errors | smoke | `cd frontend && npm run build && npm run lint && npm run knip` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_eval_confidence.py` — stubs for new one-sample-t-test helper (covers D-04)
- [ ] `tests/test_stats_schemas.py` — stubs for extended `OpeningWDL` (covers D-01..D-05)
- [ ] `tests/repositories/test_openings_repository.py` — stubs for MG-entry eval + clock-diff aggregation (covers D-01, D-04, D-05; mate exclusion)
- [ ] `tests/services/test_stats_service.py` — service wiring stub (existing file extended)
- [ ] `tests/perf/test_openings_stats_explain.py` — EXPLAIN ANALYZE perf guard (new file; non-blocking, manual review)
- [ ] `frontend/src/components/charts/__tests__/MiniBulletChart.test.tsx` — CI whisker stubs (existing file extended)
- [ ] `frontend/src/components/stats/__tests__/MostPlayedOpeningsTable.test.tsx` — new column stubs
- [ ] `frontend/src/pages/__tests__/Openings.test.tsx` — Stats-subtab board hide stub

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Bullet chart CI whisker visual quality at extreme domain edges | D-02 | Visual rendering, no straightforward unit assertion for end-cap geometry | Run `npm run dev`, navigate to Openings → Stats, inspect a bookmarked opening with eval near +1.0 or -1.0 (domain edge); verify whisker either clips correctly or renders open-ended without overlapping the bar |
| Mobile second-line layout at narrow viewport (320px) | D-06 | Responsive layout, automated viewport testing not configured | Open Chrome DevTools, set viewport to 320px wide, verify the bullet chart + confidence pill + clock diff stack without horizontal overflow |
| Confidence pill colors match opening-insights cards | D-04 | Visual cross-reference; theme constant correctness already covered by build, but visual parity isn't | Compare a Phase 80 row's confidence pill side-by-side with an `OpeningFindingCard` (Phase 75/76) at equal confidence levels |
| EXPLAIN ANALYZE comparison pre/post on representative user | (perf) | Requires running both old and new code paths against the same DB snapshot | Capture `EXPLAIN ANALYZE` for `/openings/stats` on a typical user with ~500 games before merging schema changes; capture again after; compare total ms — flag regression >25% |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
