---
phase: 112
slug: flaws-subtab-card-rework
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-09
---

# Phase 112 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (backend) + vitest (frontend) |
| **Config file** | `pyproject.toml` (pytest) / `frontend/vitest.config.ts` |
| **Quick run command** | `uv run pytest -n auto tests/test_library*.py` / `cd frontend && npm test -- --run src/components/library src/pages/library` |
| **Full suite command** | `uv run pytest -n auto -x` + `( cd frontend && npm run lint && npm test -- --run )` |
| **Estimated runtime** | ~90 seconds (backend parallel) + ~30 seconds (frontend) |

---

## Sampling Rate

- **After every task commit:** Run the quick run command for the affected stack
- **After every plan wave:** Run the full suite command
- **Before `/gsd-verify-work`:** Full suite must be green (backend + frontend)
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 112-01-* | 01 | 1 | SC-2/SC-4 (eval-join, ratings, schema slim) | — | Eval join reproduces es_before/es_after on dev rows | unit | `uv run pytest -n auto tests/test_library_repository.py tests/test_flaws_service.py` | ❌ W0 | ⬜ pending |
| 112-02-* | 02 | 2 | SC-7 (single-game endpoint) | T-112-01 (IDOR scoping) | `GET /library/games/{id}` only returns games owned by the authed user (404 on cross-user id) | unit | `uv run pytest -n auto tests/test_library.py` | ❌ W0 | ⬜ pending |
| 112-03-* | 03 | 3 | SC-1/SC-3/SC-4/SC-5/SC-6/SC-8 (FlawCard + grid) | — | data-testid/ARIA present on card + view-game button | unit | `cd frontend && npm test -- --run src/components/library` | ❌ W0 | ⬜ pending |
| 112-04-* | 04 | 3 | SC-7/SC-8 (modal + hook) | — | modal renders LibraryGameCard, isError branch present | unit | `cd frontend && npm test -- --run src/pages/library` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

> **Note:** The plans are TDD-structured — the test files below are **created by the plan tasks during execution** (tests-first within each task), not pre-execution Wave-0 stubs. Every task already carries an `<automated>` verify command, so no separate Wave-0 scaffolding pass is required. The items below are the authoritative test-file targets the executor must produce.

- [x] `tests/test_library.py` — add cases for new `GET /library/games/{game_id}` endpoint (success, cross-user 404, eval/ratings present)
- [x] `tests/test_library_repository.py` — ES-reproduction assertion for the `game_positions` eval join (Pitfall 1 regression guard)
- [x] `tests/test_flaws_service.py` — assert classifier no longer persists `es_before`/`es_after`/`move_san`
- [x] `frontend/src/components/library/FlawCard.test.tsx` — new component test
- [x] No framework install needed — pytest + vitest already configured

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual parity of FlawCard with Games card (header band, 132px board, chip colors) | SC-2/SC-3/SC-5/SC-6 | Pixel/visual judgment not automatable | Open Library → Flaws tab in dev; compare a flaw card against a Games card side by side |
| Modal eval-chart tooltip not clipped inside scrollable Dialog (Pitfall 2) | SC-7 | Tooltip portal/overflow interaction needs live render | Open "View game" modal, hover the eval chart, confirm tooltip escapes the card border and is not clipped |
| 2-up grid → 1-up collapse at the `lg` breakpoint | SC-1/SC-8 | Responsive layout visual check | Resize browser below/above 1024px; confirm column count |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none — TDD tasks create their own test files)
- [x] No watch-mode flags
- [x] Feedback latency < 120s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-09
