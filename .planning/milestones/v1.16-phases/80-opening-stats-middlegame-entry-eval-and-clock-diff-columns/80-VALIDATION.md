---
phase: 80
slug: opening-stats-middlegame-entry-eval-and-clock-diff-columns
status: approved
nyquist_compliant: true
wave_0_complete: true
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
| **Quick run command** | `uv run pytest tests/services/test_eval_confidence.py tests/test_stats_schemas.py tests/test_stats_repository.py tests/services/test_stats_service.py -x -q` |
| **Full suite command** | `uv run pytest && (cd frontend && npm test --run)` |
| **Estimated runtime** | ~30 seconds quick, ~3 minutes full |

---

## Sampling Rate

- **After every task commit:** Run quick command (relevant module tests).
- **After every plan wave:** Run full suite (`uv run pytest`).
- **Before `/gsd-verify-work`:** Full suite green AND `uv run ty check app/ tests/` zero errors AND `(cd frontend && npm run build && npm run lint && npm run knip)` all pass.
- **Max feedback latency:** 60 seconds for unit tests.

---

## Per-Task Verification Map

Task IDs follow the convention `80-{plan}-{task}` and map 1:1 onto the actual `<task>` blocks inside each PLAN.md. Plans 01..06 are the only plans in Phase 80.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 80-01-01 | 01 | 1 | D-04 | — | one-sample t-test confidence helper produces low/medium/high per N+p thresholds; handles n=0, n=1, zero-variance edges without exception | unit | `uv run pytest tests/services/test_eval_confidence.py -x` | ✅ | ⬜ pending |
| 80-01-02 | 01 | 1 | D-01, D-04, D-05 | — | `OpeningWDL` schema gains 9 optional fields additively; older clients still parse | unit | `uv run pytest tests/test_stats_schemas.py -x` | ✅ | ⬜ pending |
| 80-02-01 | 02 | 2 | D-01, D-04, D-05 | T-80-03, T-80-04, T-80-05, T-80-06 | repo aggregation returns signed avg eval at MG entry, mate excluded from mean, partition `eval_n + mate_n + null_eval_n == wdl.total`, color-flip symmetry, clock-diff with two-LEFT-JOIN shape | integration | `uv run pytest tests/test_stats_repository.py -x` | ✅ | ⬜ pending |
| 80-02-02 | 02 | 2 | D-01, D-04, D-05 | T-80-05 | service wires new fields into `/api/stats/most-played-openings` payload via sequential awaits (no `asyncio.gather`); CI bounds + p-value + confidence bucket finalised end-to-end | integration | `uv run pytest tests/services/test_stats_service.py -x` | ✅ | ⬜ pending |
| 80-03-01 | 03 | 1 | D-02 | — | `MiniBulletChart` renders CI whisker when `ciLow`/`ciHigh` provided; backward-compatible when omitted; open-ended caps suppressed when CI extends past `domain` | unit | `(cd frontend && npm test -- MiniBulletChart --run)` | ✅ | ⬜ pending |
| 80-04-01 | 04 | 1 | D-07 | — | `EVAL_BULLET_DOMAIN_PAWNS`, `EVAL_NEUTRAL_MIN_PAWNS`, `EVAL_NEUTRAL_MAX_PAWNS` exported from `frontend/src/lib/openingStatsZones.ts` with calibrated values | unit | `(cd frontend && npm test -- openingStatsZones --run)` | ✅ | ⬜ pending |
| 80-04-02 | 04 | 1 | D-03 | — | board container hidden on Stats subtab desktop (`activeTab === 'stats'`); board JSX stays mounted (chess.js state preserved per Pitfall 7); mobile layout unchanged | unit | `(cd frontend && npm test -- Openings.statsBoard --run)` | ✅ | ⬜ pending |
| 80-05-01 | 05 | 3 | D-04, D-05 | — | shared `<ConfidencePill>` component renders level + tooltip; `formatSignedSeconds` / `formatSignedPct1` extracted to `frontend/src/lib/clockFormat.ts`; `OpeningFindingCard` + `EndgameClockPressureSection` refactored to consume shared helpers | unit | `(cd frontend && npm test -- ConfidencePill clockFormat OpeningFindingCard --run)` | ✅ | ⬜ pending |
| 80-05-02 | 05 | 3 | D-01, D-02, D-04, D-05, D-06 | T-80-10, T-80-11, T-80-12 | `MostPlayedOpeningsTable` renders three new columns desktop + mobile second-line stack; em-dash fallback for missing data; dimming for unreliable rows; column-header InfoPopovers; bookmarked + most-played reuse both updated | unit | `(cd frontend && npm test -- MostPlayedOpeningsTable --run)` | ✅ | ⬜ pending |
| 80-06-01 | 06 | 4 | D-01..D-07 | T-80-13 | full regression matrix green (ruff, ruff-format, ty, pytest, vitest, lint, knip, build); EXPLAIN ANALYZE within 1.5x baseline (or deferred to manual checkpoint) | smoke | `uv run ruff check . && uv run ruff format --check . && uv run ty check app/ tests/ && uv run pytest -x -q && (cd frontend && npm test --run && npm run lint && npm run knip && npm run build)` | ✅ | ⬜ pending |
| 80-06-02 | 06 | 4 | D-01..D-07 | — | CHANGELOG `[Unreleased]` carries a Phase 80 entry under `### Added` with concrete user-facing language | smoke | `grep -c "Phase 80" CHANGELOG.md` | ✅ | ⬜ pending |
| 80-06-03 | 06 | 4 | D-01..D-06 | T-80-13 | human-verify: board hide on Stats subtab, all three columns render, bookmarked + most-played parity, mobile second-line at 320px viewport, confidence pill colors match `OpeningFindingCard`, InfoPopovers render, no console errors | manual | `human-verify` (checkpoint:human-verify per `80-06-PLAN.md` Task 3) | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

All test files referenced in the verification map already exist or will be created by Wave 0 stub tasks within their owning plans. No separate Wave 0 plan is required for Phase 80 — each plan's Task 1 is TDD-shaped (`tdd="true"`) and creates its own RED test scaffold before GREEN implementation.

- [x] `tests/services/test_eval_confidence.py` — Plan 01 Task 1 (RED scaffold for one-sample t-test helper, covers D-04)
- [x] `tests/test_stats_schemas.py` — Plan 01 Task 2 (RED scaffold for extended `OpeningWDL`, covers D-01..D-05)
- [x] `tests/test_stats_repository.py` — Plan 02 Task 1 (RED scaffold for MG-entry aggregation; mate exclusion, partition invariant `eval_n + mate_n + null_eval_n == total`, clock diff)
- [x] `tests/services/test_stats_service.py` — Plan 02 Task 2 (extended; service wiring + `asyncio.gather` regression guard via `inspect.getsource` + word-boundary regex)
- [x] `frontend/src/components/charts/__tests__/MiniBulletChart.test.tsx` — Plan 03 (extended; CI whisker stubs)
- [x] `frontend/src/lib/__tests__/openingStatsZones.test.ts` — Plan 04 Task 1 (constants module test)
- [x] `frontend/src/pages/__tests__/Openings.statsBoard.test.tsx` — Plan 04 Task 2 (board hide on Stats subtab)
- [x] `frontend/src/components/insights/__tests__/ConfidencePill.test.tsx` — Plan 05 Task 1 (new shared component)
- [x] `frontend/src/lib/__tests__/clockFormat.test.ts` — Plan 05 Task 1 (new shared formatters)
- [x] `frontend/src/components/stats/__tests__/MostPlayedOpeningsTable.test.tsx` — Plan 05 Task 2 (new column tests)

Perf check (`tests/perf/test_openings_stats_explain.py`) was originally listed as a Wave 0 file. It is intentionally **not gated** — RESEARCH §Performance Concern lines 467-471 designate the EXPLAIN ANALYZE comparison as a one-shot manual review documented in `80-02-SUMMARY.md`, not an automated CI gate. Plan 06 Task 1 reads the SUMMARY to confirm or flag for the human checkpoint.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Bullet chart CI whisker visual quality at extreme domain edges | D-02 | Visual rendering, no straightforward unit assertion for end-cap geometry | Run `npm run dev`, navigate to Openings → Stats, inspect a bookmarked opening with eval near +1.0 or -1.0 (domain edge); verify whisker either clips correctly or renders open-ended without overlapping the bar |
| Mobile second-line layout at narrow viewport (320px) | D-06 | Responsive layout, automated viewport testing not configured | Open Chrome DevTools, set viewport to 320px wide, verify the bullet chart + confidence pill + clock diff stack without horizontal overflow |
| Confidence pill colors match opening-insights cards | D-04 | Visual cross-reference; theme constant correctness already covered by build, but visual parity isn't | Compare a Phase 80 row's confidence pill side-by-side with an `OpeningFindingCard` (Phase 75/76) at equal confidence levels |
| EXPLAIN ANALYZE comparison pre/post on representative user | (perf) | Requires running both old and new code paths against the same DB snapshot | Capture `EXPLAIN ANALYZE` for `/api/stats/most-played-openings` on Adrian's user (~30k games) before merging schema changes; capture again after; compare total ms — flag regression >50% (1.5x threshold) per RESEARCH lines 467-471 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or are explicit `manual` / `checkpoint:human-verify` tasks (Task 80-06-03 only)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all referenced test files (each plan's TDD task creates its own RED scaffold)
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter
- [x] `wave_0_complete: true` set in frontmatter

**Approval:** approved 2026-05-03
</content>
</invoke>