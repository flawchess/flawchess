---
phase: "260"
slug: "facepalm-first-class-move-quality"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-11-22"
---

# Phase 260 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `260-RESEARCH.md` §Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (+ pytest-xdist, per-worker cloned Postgres DB) backend; vitest + Testing Library frontend |
| **Config file** | `pyproject.toml`, `tests/conftest.py`; `frontend/vite.config.*` |
| **Quick run command** | `uv run pytest tests/test_flaw_predicate.py tests/repositories/test_library_repository.py -x` and `cd frontend && npx vitest run src/lib/__tests__/moveStatsCounts.test.ts src/components/library/__tests__/MoveStats.test.tsx` |
| **Full suite command** | `uv run pytest -n auto -x` and `( cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip )` |
| **Estimated runtime** | quick ~30 seconds, full ~6 minutes |

---

## Sampling Rate

- **After every task commit:** Run the quick command for the files touched (one backend test file or one vitest file group)
- **After every plan wave:** Run `uv run pytest -n auto -x` plus `( cd frontend && npm run build && npm test -- --run && npm run knip )`
- **Before `/gsd-verify-work`:** The full pre-merge gate from `CLAUDE.md` must be green, plus one serial `uv run pytest -x`
- **Max feedback latency:** 60 seconds for the quick command

---

## Per-Task Verification Map

Task IDs filled in by the planner (2026-11-22). Task ID = `{plan}-T{n}`. Deviation from the research map: the Games-EXISTS
truth table lives in `tests/repositories/test_library_repository.py` (via `query_filtered_games`), not in
`tests/test_library_repository.py`, because plan 259-09 edits that file.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 260-01-T1 | 01 | 1 | D-12 (router, end to end) | T-260-01 | `severity=inaccuracy` and unknown values return 422; `facepalm` accepted | integration (HTTP) | `uv run pytest tests/test_library_router.py -k "FlawSeverityFacepalm or invalid_severity" -x` | ✅ extend | ✅ green |
| 260-01-T2 | 01 | 1 | D-08 / D-12 (compile) | T-260-02 | No KeyError for any subset of filter values | unit (SQL compile) | `uv run pytest tests/test_flaw_predicate.py -x` | ✅ extend | ✅ green |
| 260-01-T2 | 01 | 1 | D-08 / D-09 (Flaws list and Games EXISTS) | T-260-04 | Opponent above-cut blunder never matches | integration (DB) | `uv run pytest tests/repositories/test_library_repository.py -k severity_tags -x` | ❌ W0 (new tests) | ✅ green |
| 260-01-T2 | 01 | 1 | D-12 (default) | — | N/A | integration | `uv run pytest tests/services/test_library_service.py -k default_severity -x` | ❌ W0 (new test) | ✅ green |
| 260-01-T3 | 01 | 1 | D-24 | T-260-03 | Rows stay scoped by `GameFlaw.user_id` | integration (DB) | `uv run pytest -n auto tests/test_library_repository.py tests/services/test_maia_flaw_scoring.py tests/services/test_library_service.py -x` | ✅ update + ❌ new | ✅ green |
| 260-02-T1 | 02 | 1 | D-01 to D-04, D-07 | — | N/A | unit + component | `cd frontend && npx vitest run src/lib/__tests__/moveStatsCounts.test.ts src/components/library/__tests__/MoveStats.test.tsx src/components/results/__tests__/LibraryGameCard.test.tsx` | ✅ extend | ✅ green |
| 260-02-T2 | 02 | 1 | D-01, D-04, D-05, D-06 | — | N/A | component | `cd frontend && npx vitest run src/components/library/__tests__/MoveStats.test.tsx src/components/analysis/__tests__/AnalysisTagsPanel.test.tsx` | ✅ update | ✅ green |
| 260-02-T3 | 02 | 1 | D-15 / D-16 / D-25 | — | N/A | unit + human-check | `cd frontend && npx vitest run src/lib/__tests__/gameCardGeometry.test.ts` | ❌ W0 (new) | ✅ green |
| 260-03-T1 | 03 | 2 | D-10, D-14 (UI) | — | N/A | component | `cd frontend && npx vitest run src/components/filters/__tests__/FlawFilterControl.test.tsx` | ✅ update | ✅ green |
| 260-03-T2 | 03 | 2 | D-14 (state, requests) | T-260-08 | Stale objects with range fields load as the default filter | unit | `cd frontend && npx vitest run src/hooks/__tests__/useLibraryGames.test.tsx src/api/__tests__/client.test.ts src/hooks/__tests__/useFlawFilterStore.test.ts` | ✅ update | ✅ green |
| 260-03-T3 | 03 | 2 | D-14, D-21 | T-260-09 | N/A | unit + gate | `cd frontend && npx vitest run src/lib/__tests__/facepalm.test.ts && npm run knip` | ✅ update | ✅ green |
| 260-04-T1 | 04 | 3 | D-17 | — | N/A | unit | `cd frontend && npx vitest run src/lib/__tests__/flawDotColor.test.ts` | ❌ W0 (new) | ✅ green |
| 260-04-T2 | 04 | 3 | D-18 / D-26 | — | N/A | component + human-check | `cd frontend && npx vitest run src/components/library/__tests__/EvalChart.test.tsx` | ✅ extend | ✅ green |
| 260-05-T1 | 05 | 4 | D-08, D-09 (UI, request) | T-260-12 | Analytics value is an enumerated literal | component + unit | `cd frontend && npx vitest run src/components/filters/__tests__/FlawFilterControl.test.tsx src/hooks/__tests__/useLibraryGames.test.tsx` | ✅ update | ✅ green |
| 260-05-T2 | 05 | 4 | D-08 (store, URL) | T-260-11 | Unknown URL severity values dropped | unit + component | `cd frontend && npx vitest run src/hooks/__tests__/useFlawFilterStore.test.ts src/pages/library/__tests__/FlawsTab.test.tsx` | ✅ extend | ✅ green |
| 260-06-T1 | 06 | 5 | D-20, D-28 | T-260-16 | Ring user side only | component | `cd frontend && npx vitest run src/components/results/__tests__/LibraryGameCard.test.tsx src/components/results/__tests__/LibraryGameCardPastedBadge.test.tsx src/components/library/__tests__/MoveStats.test.tsx` | ✅ extend | ✅ green |
| 260-06-T2 | 06 | 5 | D-27 | — | N/A | component | `cd frontend && npx vitest run src/components/library/__tests__/SeverityBadge.test.tsx src/components/library/__tests__/FlawCard.test.tsx src/components/train/__tests__/TrainPuzzleCard.test.tsx` | ✅ extend | ✅ green |
| 260-07-T1 | 07 | 6 | D-13 | T-260-13 | Removed range parameters are ignored, not an error path | integration (HTTP) | `uv run pytest tests/test_library_router.py -k "facepalm or severity" -x` | ✅ rewrite | ✅ green |
| 260-07-T2 | 07 | 6 | D-13, D-21 | T-260-14 | Player gate tests stay in the suite | full suite | `uv run pytest -n auto -x` | ✅ rewrite | ✅ green |
| 260-07-T3 | 07 | 6 | D-22, D-15 / D-16 / D-25 (layout re-measure) | T-260-15 | N/A | pre-merge gate + human-check | full CLAUDE.md pre-merge gate; orchestrator bounding-rect measurement | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/repositories/test_library_repository.py` — D-08 truth-table tests on `query_flaws` and on the Games EXISTS via `query_filtered_games` (260-01-T2; reuse `_seed_non_tactic_flaw(facepalm_target=...)`)
- [x] `tests/services/test_library_service.py` — default severity lists facepalms (260-01-T2), opponent marker carries its score (260-01-T3)
- [x] `frontend/src/lib/__tests__/flawDotColor.test.ts` — the new pure colour function (260-04-T1)
- [x] `frontend/src/lib/__tests__/gameCardGeometry.test.ts` — the desktop board / chart derivation (260-02-T3)
- [x] No framework install needed

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Desktop miniboard and move quality card end level with 8 rows, chart taller, tags card height kept | D-15 / D-16 / D-25 | Pixel geometry depends on rendered font and Tailwind classes | Orchestrator browser automation at `lg` (>= 1280px): `getBoundingClientRect()` of the miniboard, `move-stats-table-card-{id}`, `eval-chart-{id}` and the left-lane tags card (260-02-T3, repeated in 260-07-T3) |
| Facepalm dot, tooltip and filter pill colours read correctly | D-08 / D-17 / D-18 | Visual judgement of the dark red tone | After Phase 259's switch release (D-22), open a game with a facepalm blunder and check the chart dot, tooltip and the Flaws filter pill |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-11-22 (automated map green; manual-only items await owner UAT)

## Validation Audit 2026-11-22

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
