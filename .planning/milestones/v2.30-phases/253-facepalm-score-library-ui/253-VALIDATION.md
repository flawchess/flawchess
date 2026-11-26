---
phase: "253"
slug: "facepalm-score-library-ui"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
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

Task IDs follow `{phase}-{plan}-T{n}`; rows are keyed on the CONTEXT.md decision they prove.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 253-01-T1 | 01 | 1 | D-04, D-14, D-17 | T-253-02 | Narrowed range returns only the user's in-range scored blunder | integration (HTTP to DB tracer): High range on GET /library/flaws returns only (game1, ply 2); every row carries `facepalm_score` or null | `uv run pytest tests/test_library_router.py -n auto -q -k facepalm` | ✅ (created in 253-01-T1) | ✅ green |
| 253-01-T2 | 01 | 1 | D-06 | T-253-02 | Games EXISTS stays user-scoped (ValueError without user_id) | unit (SQL compile): `apply_game_filters` with only facepalm params emits the EXISTS; 0/100 and None/None emit none | `uv run pytest tests/test_query_utils.py -n auto -q -k facepalm` | ✅ (created in 253-01-T2) | ✅ green |
| 253-01-T2 | 01 | 1 | D-06, D-05 | T-253-02 | Opponent-only scored game never matches | integration (HTTP to DB): High returns game1 only, Low game2 only, game3 (opponent-only) never | `uv run pytest tests/test_library_router.py -n auto -q -k "facepalm and games"` | ✅ (created in 253-01-T2) | ✅ green |
| 253-01-T3 | 01 | 1 | D-04 | — | N/A | unit (SQL compile): full range (None/None, 0/100, 0/None, None/100) adds no clause; narrowed adds the `facepalm_score` predicate; asyncpg binds `::FLOAT`, no floor | `uv run pytest tests/test_library_repository.py -n auto -q -k facepalm` | ✅ (created in 253-01-T3) | ✅ green |
| 253-01-T3 | 01 | 1 | D-04, D-10, D-11 | — | N/A | integration (`query_flaws`): 0.27 and 0.2999 → Low; 0.30, 0.699 and a seeded 0.70 (stored float4 0.6999999881, floors to 69) → Mid; 0.7001 and 1.0 → High; NULL blunder and mistake excluded; mistake-only + High → 0 rows; floor invariant on every returned row | `uv run pytest tests/repositories/test_library_repository.py -n auto -q -k facepalm` | ✅ (created in 253-01-T3) | ✅ green |
| 253-01-T3 | 01 | 1 | D-06, D-05 | T-253-02 | A scored opponent-ply flaw never matches | integration (`query_filtered_games`): same-row AND with a tag; unscored-only game excluded | `uv run pytest tests/test_library_repository.py -n auto -q -k "facepalm and games"` | ✅ (created in 253-01-T3) | ✅ green |
| 253-01-T3 | 01 | 1 | Router | T-253-01 | Out-of-range params (101, -1) rejected with 422 on both endpoints | API | `uv run pytest tests/test_library_router.py -n auto -q -k facepalm` | ✅ (created in 253-01-T3) | ✅ green |
| 253-02-T1, T3 | 02 | 1 | D-09, D-10 | — | N/A | unit: presets, `displayUpper`, query params ({} at default; Low → max 29; Mid → 30/69; High → 70/100; 40/40 → 40/44), summary (All, 0-29%, 30-69%, 70-100%) | `cd frontend && npx vitest run src/lib/__tests__/facepalm.test.ts` | ✅ (created in 253-02-T1) | ✅ green |
| 253-02-T1, T3 | 02 | 1 | D-08, D-11, D-12, D-13, D-19 | T-253-05 | Umami sends preset or `custom`, never bounds | component: High click emits 70/100; four presets; summary style; hint "Mistakes are excluded" only when narrowed; D-19 copy; position after severity and before Best Moves / Tactic Depth; severity toggles untouched; Umami `facepalm` | `cd frontend && npx vitest run src/components/filters/__tests__/FlawFilterControl.test.tsx` | ✅ extend | ✅ green |
| 253-02-T1 | 02 | 1 | D-04 (dot) | — | N/A | unit: defaults 0/100; `isFlawFilterNonDefault` true only when narrowed, false for partial mocks | `cd frontend && npx vitest run src/hooks/__tests__/useFlawFilterStore.test.ts` | ✅ extend | ✅ green |
| 253-02-T1, T2 | 02 | 1 | D-04, D-06 | — | N/A | hook + client: params sent only when narrowed, part of the query key, forwarded by `getGames` / `getFlaws` | `cd frontend && npx vitest run src/hooks/__tests__/useLibraryGames.test.tsx src/api/__tests__/client.test.ts` | ✅ extend | ✅ green |
| 253-03-T1 | 03 | 2 | D-14, D-17 | T-253-08 | Score rendered as a floored, clamped number | component (tracer): FlawCard with `facepalm_score` 0.946 shows `Blunder`, palm icon, `94%`; click opens `Facepalm 94%` + D-18 copy; null score shows no percent | `cd frontend && npx vitest run src/components/library/__tests__/FlawCard.test.tsx src/lib/__tests__/facepalm.test.ts` | ✅ extend | ✅ green |
| 253-03-T2 | 03 | 2 | D-16, D-18 | T-253-07 | Umami target is the id-free `facepalm-badge` | component: opens on mouse hover (100 ms), click and keyboard focus; keyboard re-focus opens it after an earlier click or drag-off plus blur; touch enter/leave ignored; a tap leaves it open; Escape and tab-away close; open tracked once | `cd frontend && npx vitest run src/components/library/__tests__/FacepalmBadgePopover.test.tsx` | ✅ (created in 253-03-T2) | ✅ green |
| 253-03-T2 | 03 | 2 | D-15, D-17 | — | N/A | component: unscored blunder, mistake, inaccuracy and count badges unchanged; scored badge keeps severity colors, testid and ring | `cd frontend && npx vitest run src/components/library/__tests__/SeverityBadge.test.tsx` | ✅ extend | ✅ green |
| 253-02-T3, 253-03-T3 | 02, 03 | 1, 2 | D-03, D-07 | — | N/A | grep: no banned odds/peer-share wording and no note that values may change in the new copy | `! grep -rniE "avoidable\|chance you\|provisional" frontend/src/components/filters frontend/src/components/library frontend/src/lib/facepalm.ts` | — | ✅ green |
| 253-03-T3 | 03 | 2 | all | — | N/A | full pre-merge gate (CLAUDE.md) | see 253-03-PLAN.md Task 3 | — | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `frontend/src/lib/__tests__/facepalm.test.ts` — new file, D-09/D-10 pure logic (253-02-T1)
- [x] `tests/test_library_router.py` `_seed_flaw_committed` — `facepalm_score` kwarg, plus the `facepalm_test_state` fixture (253-01-T1)
- [x] `tests/test_library_repository.py` `_seed_game_flaw` — `facepalm_score` and `is_reversed` kwargs (253-01-T3)
- [x] `tests/repositories/test_library_repository.py` seed helpers — `facepalm_score` kwarg (253-01-T3)
- [x] `frontend/src/components/library/__tests__/FlawCard.test.tsx` `makeFlaw` — `facepalm_score: null` default (253-03-T1)
- [x] `frontend/src/components/library/__tests__/FacepalmBadgePopover.test.tsx` — new file (253-03-T2)
- FlawsTab test fixtures: no change needed; FlawCard treats a missing `facepalm_score` as unscored (`!= null` check)

No framework install needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Mutation proof of the Games-tab gate (253-01-T2, recorded in its SUMMARY) | D-06 | A revert-and-rerun, not a standing test | Remove `facepalm_active` from the `apply_game_filters` EXISTS condition, run the facepalm-only Games-tab test, confirm it fails, restore |
| Touch behaviour of the badge popover on a real phone | D-16 | jsdom only simulates pointer types | On a phone, tap a scored Blunder badge: the popover opens once and stays open; tap outside closes it |
| Panel layout and badge look | D-13, D-14, D-15 | Visual | Library → Flaws tab: filter sits under Blunders/Mistakes, above Best Moves; the badge reads `Blunder <palm> N%` in blunder colors |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 90s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-11-14 (all 16 map rows green on the merged phase branch)

## Validation Audit 2026-11-14

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
