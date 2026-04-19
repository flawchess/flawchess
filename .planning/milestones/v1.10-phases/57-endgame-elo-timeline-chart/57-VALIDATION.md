---
phase: 57
slug: endgame-elo-timeline-chart
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-18
---

# Phase 57 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (backend) + vitest (frontend) |
| **Config file** | pyproject.toml (pytest) / vitest.config.ts |
| **Quick run command** | `uv run pytest tests/test_endgame_service.py -x` |
| **Full suite command** | `uv run pytest && cd frontend && npm test && npm run lint && cd .. && uv run ruff check . && uv run ty check app/ tests/` |
| **Estimated runtime** | ~90 seconds |

---

## Sampling Rate

- **After every task commit:** Run `{quick run command}` scoped to the module touched (pytest path filter or `npm test -- path/to/file`)
- **After every plan wave:** Run the full suite command
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

Each task in 57-01 and 57-02 bundles its own automated verification (TDD: tests co-delivered with code). No Wave 0 test scaffolding phase is needed because every task's `<verify><automated>` block runs real tests against real code produced by the same task.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|--------|
| 57-01-T1 | 01 | 1 | ELO-05 | T-57-04 | No PII leak: aggregate-only response shape | ty + ruff | `uv run ty check app/schemas/endgames.py` | ⬜ pending |
| 57-01-T2 | 01 | 1 | ELO-05 | T-57-01, T-57-02 | User scoping: `Game.user_id == user_id` top-level; apply_game_filters used | ty + ruff | `uv run ty check app/repositories/endgame_repository.py && uv run ruff check app/repositories/endgame_repository.py` | ⬜ pending |
| 57-01-T3 | 01 | 1 | ELO-05 | T-57-01, T-57-05 | Formula clamp safe; window pre-fills; all queries scoped | unit | `uv run pytest tests/test_endgame_service.py::TestEndgameElo tests/test_endgame_service.py::TestEndgameSkillFromBucketRows tests/test_endgame_service.py::TestEndgameEloTimeline -x` | ⬜ pending |
| 57-01-T4 | 01 | 1 | ELO-05 (SC-2, SC-3) | T-57-01 | End-to-end HTTP route scoping via seeded_user fixture | integration | `uv run pytest tests/test_integration_routers.py -k endgame_overview_elo_timeline -x` | ⬜ pending |
| 57-02-T1 | 02 | 2 | ELO-05 | — | No hex/oklch literals in chart component; theme-centralized | unit | `cd frontend && npm test -- --run src/lib/utils.test.ts` | ⬜ pending |
| 57-02-T2 | 02 | 2 | ELO-05 | T-57-07, T-57-08, T-57-09 | Locked info-popover copy (no dangerouslySetInnerHTML, no API interpolation); `noUncheckedIndexedAccess` satisfied via FALLBACK_COMBO_COLOR | lint + build | `cd frontend && npm run lint && npx tsc --noEmit && npm run knip && npm run build` | ⬜ pending |
| 57-02-T3 | 02 | 2 | ELO-05 (SC-1) | — | Visual/functional check on live stack | manual | Manual smoke per how-to-verify block | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Nyquist sampling continuity:** No 3 consecutive tasks lack an automated `<verify>`. Every `auto` task has one; the single manual checkpoint (57-02-T3) sits after two verified auto-tasks in plan 02 and after plan 01's four verified tasks.

---

## Wave 0 Requirements

**Satisfied inline via TDD within each task — no separate Wave 0 phase needed.**

- ✅ `tests/test_endgame_service.py` — `TestEndgameElo` + `TestEndgameSkillFromBucketRows` + `TestEndgameEloTimeline` are authored inside 57-01 Task 3 (same commit as the service code they test).
- ✅ `tests/test_integration_routers.py` — `test_endgame_overview_elo_timeline_respects_filters` + `test_endgame_overview_elo_timeline_cold_start_returns_empty_combos` are authored inside 57-01 Task 4 (same commit as the service+overview wiring they exercise).
- ✅ `frontend/src/lib/utils.test.ts` — `describe('niceEloAxis', ...)` is authored inside 57-02 Task 1 (same commit as the `niceEloAxis` helper it tests).
- Existing pytest + vitest infra already installed — no framework install needed.

**No dedicated Wave 0 test scaffolding step:** tasks are TDD-marked (`tdd="true"` with `<behavior>` blocks), so tests precede implementation inside each task. This is the "tests bundled with implementation" pattern — acceptable under Nyquist sampling continuity because the `<verify><automated>` gate on each task proves the test file exists and runs green before the task is considered done.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual hue/contrast of paired bright/dark lines | ELO-05 SC-1 | Color perception / accessibility is subjective; theme-level concern | Load /endgames on real account, toggle combos in legend, verify bright/dark distinction is visible |
| Mobile legend wrap / collapse behavior | ELO-05 SC-1 | Responsive layout visual check | Open /endgames on iPhone viewport (Chrome devtools), confirm legend does not overflow and chart remains readable |
| Cold-start empty state copy readability | ELO-05 SC-3 | Prose/UX review (functional check is covered by the integration test; this is the copy-is-readable check) | Create test account with 0 games, navigate to Endgames tab, verify empty-state message appears instead of chart |
| Component-level error state renders locked copy | CLAUDE.md `isError` rule | Requires simulating API failure in the browser | Stop uvicorn, reload /endgames, confirm `endgame-elo-timeline-error` container renders with "Failed to load Endgame ELO timeline" / "Something went wrong. Please try again in a moment." |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (satisfied via TDD-bundled tests per task)
- [x] No watch-mode flags
- [x] Feedback latency < 120s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
