---
phase: "253"
slug: "facepalm-score-library-ui"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-14"
---

# Phase 253 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Source: `253-RESEARCH.md`
> § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (+ pytest-asyncio, xdist) backend; vitest + RTL + jsdom frontend |
| **Config file** | `pyproject.toml`, `tests/conftest.py` (per-worker cloned DB); `frontend/vite.config.*` |
| **Quick run command (backend)** | `uv run pytest tests/test_library_repository.py tests/repositories/test_library_repository.py tests/test_query_utils.py tests/test_library_router.py -n auto` |
| **Quick run command (frontend)** | `cd frontend && npx vitest run src/lib/__tests__/facepalm.test.ts src/components/library/__tests__/SeverityBadge.test.tsx src/components/filters/__tests__/FlawFilterControl.test.tsx src/hooks/__tests__/useFlawFilterStore.test.ts` |
| **Full suite command** | The pre-merge gate in root `CLAUDE.md` (ruff, ty, function-size gate, `uv run pytest -n auto -x`, `npm run lint && npm run build && npm test -- --run && npm run knip`) |
| **Estimated runtime** | ~60 seconds quick, several minutes full |

---

## Sampling Rate

- **After every task commit:** the quick-run command for the touched stack
- **After every plan wave:** both quick-run commands plus `cd frontend && npm run build` (the `FlawListItem` type changes)
- **Before `/gsd-verify-work`:** the full pre-merge gate must be green
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

Task IDs are assigned by the planner; rows are keyed on the CONTEXT.md decision they prove.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | D-04 | — | N/A | unit (SQL compile): full range (None/None, 0/100) adds no clause, narrowed adds the `facepalm_score` predicate | `uv run pytest tests/test_library_repository.py -k facepalm` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-04, D-10 | — | N/A | integration (`query_flaws`): 0.27 → Low, 0.699 → Mid, 0.70 and 1.0 → High, NULL and a mistake excluded | `uv run pytest tests/repositories/test_library_repository.py -k facepalm` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-06 | — | N/A | integration (`query_filtered_games`): a facepalm-only range narrows games; with tags it needs the same flaw row | `uv run pytest tests/test_library_repository.py -k "facepalm and games"` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-05 | — | A scored opponent-ply flaw never matches | integration | `uv run pytest tests/test_library_repository.py -k facepalm` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-06 | — | N/A | unit (SQL compile): `apply_game_filters` with only facepalm params emits the EXISTS | `uv run pytest tests/test_query_utils.py -k facepalm` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | Router | — | Out-of-range params (101, -1) rejected with 422 | API | `uv run pytest tests/test_library_router.py -k facepalm` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | Schema | — | N/A | integration: `FlawListItem.facepalm_score` from the row, None when NULL | `uv run pytest tests/repositories/test_library_repository.py -k facepalm` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-09, D-10 | — | N/A | unit: presets, summary, query params ({} at default; Low → max 29; Mid → 30/69; High → 70/100), `0.697 → 69` | `cd frontend && npx vitest run src/lib/__tests__/facepalm.test.ts` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-08, D-12, D-13, D-19 | — | N/A | component: four presets, active summary, hint "Mistakes are excluded" only when narrowed, position after severity and before Best Moves, Umami `facepalm` with preset or `custom` | `cd frontend && npx vitest run src/components/filters/__tests__/FlawFilterControl.test.tsx` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | Store | — | N/A | unit: defaults 0/100; `isFlawFilterNonDefault` true only when narrowed | `cd frontend && npx vitest run src/hooks/__tests__/useFlawFilterStore.test.ts` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | Query wiring | — | N/A | hook: params sent only when narrowed and part of the query key | `cd frontend && npx vitest run src/hooks/__tests__/useLibraryGames.test.tsx` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-14, D-17 | — | N/A | component: scored blunder badge shows `Blunder`, icon, `94%`; unscored blunder, mistake, inaccuracy and the Train call site unchanged | `cd frontend && npx vitest run src/components/library/__tests__/SeverityBadge.test.tsx` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-16, D-18 | — | N/A | component: popover opens on click, mouse hover and keyboard focus; a touch tap leaves it open (no double toggle); heading `Facepalm 94%` plus the D-18 copy; open tracked once | `cd frontend && npx vitest run src/components/library/__tests__/SeverityBadge.test.tsx` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-14 | — | N/A | component: `FlawCard` passes `facepalm_score` through | `cd frontend && npx vitest run src/components/library/__tests__/FlawCard.test.tsx` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-03 | — | N/A | grep: no "avoidable" / "chance you" in the new copy | `grep -rniE "avoidable\|chance you" frontend/src/components/filters frontend/src/components/library frontend/src/lib/facepalm.ts` | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/src/lib/__tests__/facepalm.test.ts` — new file, D-09/D-10 pure logic
- [ ] `tests/test_library_repository.py` `_seed_game_flaw` — add a `facepalm_score: float | None = None` kwarg
- [ ] `tests/repositories/test_library_repository.py` seed helpers — same kwarg
- [ ] `frontend/src/components/library/__tests__/FlawCard.test.tsx` `makeFlaw` — `facepalm_score: null` default
- [ ] FlawsTab test fixtures — add the `facepalm_score` field

No framework install needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Mutation proof of the Games-tab gate | D-06 | A revert-and-rerun, not a standing test | Remove `facepalm_active` from the `apply_game_filters` EXISTS condition, run the facepalm-only Games-tab test, confirm it fails, restore |
| Touch behaviour of the badge popover on a real phone | D-16 | jsdom only simulates pointer types | On a phone, tap a scored Blunder badge: the popover opens once and stays open; tap outside closes it |
| Panel layout and badge look | D-13, D-14, D-15 | Visual | Library → Flaws tab: filter sits under Blunders/Mistakes, above Best Moves; the badge reads `Blunder <palm> N%` in blunder colors |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
