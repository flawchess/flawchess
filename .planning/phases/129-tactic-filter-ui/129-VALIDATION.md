---
phase: 129
slug: tactic-filter-ui
status: approved
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-20
---

# Phase 129 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Content transcribed from RESEARCH.md `## Validation Architecture` and the plans'
> `<verify>` blocks; signed off during the 2026-06-20 revision.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Backend framework** | pytest + per-run Postgres DB (`flawchess_test_<pid>` / `_gw*`), cloned from a migrated template |
| **Frontend framework** | Vitest (`vitest run`) + `tsc -b` type gate + ESLint/knip |
| **Config file** | `pyproject.toml` (`[tool.pytest]`, `addopts = --ignore=tests/scripts/benchmarks --ignore=tests/scripts/tagger`); `frontend/vitest` via `package.json` |
| **Backend quick run** | `uv run pytest tests/test_query_utils.py tests/test_library_repository.py tests/test_library_router.py -x` |
| **Frontend quick run** | `cd frontend && npm test -- --run <changed __tests__/ file>` then `npx tsc -b` |
| **Backend full suite** | `uv run pytest -n auto` |
| **Frontend full suite** | `cd frontend && npm run lint && npm test -- --run && npx tsc -b` |
| **Type gate (FE)** | `cd frontend && npx tsc -b` — NOT covered by lint/test (esbuild strips types); mandatory at the shared-type boundary |
| **Estimated runtime** | backend quick subset ~30-60s; backend full `-n auto` ~3-5 min; frontend quick file <10s; frontend full lint+vitest+tsc ~60-120s |

**Note:** all frontend test files live in `__tests__/` subdirectories, NOT co-located with source (revision correction). New FE tests go in `src/lib/__tests__/` and `src/hooks/__tests__/`.

---

## Sampling Rate

- **After every task commit:** Run the relevant quick-run subset (the touched backend test file(s) or the touched `__tests__/` vitest file + `tsc -b` for any type-touching task).
- **After every plan wave:** Backend wave → `uv run pytest -n auto` + `uv run ty check app/ tests/` + ruff. Frontend wave → `npm run lint && npm test -- --run && npx tsc -b`.
- **Before `/gsd-verify-work`:** Full backend suite green + full frontend gate green + `tsc -b` clean.
- **Max feedback latency:** < 120 seconds (quick subset is well under 60s; the per-wave gate is the upper bound).

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 129-01-01 | 01 | 1 | TACUI-04 | T-129-01 / T-129-02 / T-129-04 | Closed-enum orientation + bound int + mate exemption resolved only via `_tactic_orientation_pairs` (no SQL interpolation); new clauses sit INSIDE the existing `user_id`/`player_only_gate` ownership predicate | unit (repo + query_utils) | `uv run pytest tests/test_query_utils.py tests/test_library_repository.py -x -q` | ✅ (extend) | ⬜ pending |
| 129-01-02 | 01 | 1 | TACUI-05 | T-129-03 | Dual-orientation comparison derives from the same player-scoped GameFlaw rows; no new data class, no orientation query param (D-09); post-gate only | integration (router) + unit (service) | `uv run pytest tests/test_library_router.py -k tactic_comparison -x -q && uv run pytest -k compute_tactic_bullets -x -q` | ✅ (extend) | ⬜ pending |
| 129-01-03 | 01 | 1 | TACUI-04, TACUI-05 | — | N/A (full-suite regression gate) | gate | `uv run ruff format app/ tests/ && uv run ruff check app/ tests/ --fix && uv run ty check app/ tests/ && uv run pytest -n auto -x` | ✅ | ⬜ pending |
| 129-02-01 | 02 | 2 | TACUI-06 | T-129-06 | Frontend sends well-formed `max_tactic_depth` (half-ply) / `tactic_orientation` via `depthToQueryParam` (omits when null); no trust beyond what plan 01 re-validates server-side | unit (vitest) + type gate | `cd frontend && npm test -- --run src/lib/__tests__/tacticDepth.test.ts src/hooks/__tests__/useFlawFilterStore.test.ts && npx tsc -b` | ❌ W0 (tacticDepth.test.ts + useFlawFilterStore.test.ts NEW) | ⬜ pending |
| 129-02-02 | 02 | 2 | TACUI-06 | T-129-05 | New controls beta-gated via `useUserProfile().data.beta_enabled` (not always-null `useAuth().user`); semantic HTML + ARIA + data-testid | lint + type gate (visual = UAT) | `cd frontend && npm run lint && npx tsc -b` | n/a (component, no new unit test — covered by FlawFilterControl.test.tsx + UAT) | ⬜ pending |
| 129-02-03 | 02 | 2 | TACUI-07 | T-129-07 | Flaws list is player-only; card renders only the user's own motifs already returned by the API; no re-added per-chip popover | component (vitest) + type gate | `cd frontend && npm test -- --run src/components/library/__tests__/TacticMotifChip.test.tsx src/components/library/__tests__/FlawCard.test.tsx && npx tsc -b` | ✅ (extend, in __tests__/) | ⬜ pending |
| 129-02-04 | 02 | 2 | TACUI-06, TACUI-07 | — | N/A (frontend wave gate; knip = no dead tacticDepth exports) | gate | `cd frontend && npm run lint && npm test -- --run && npx tsc -b` | ✅ | ⬜ pending |
| 129-03-01 | 03 | 3 | TACUI-08 | T-129-08 / T-129-09 | Aggregate dual-orientation bullets are post-gate + beta-gated client-side; no per-game/cross-user detail; no orientation toggle on the grid (D-09) | component (vitest) + type gate | `cd frontend && npm test -- --run src/components/library/__tests__/TacticComparisonGrid.test.tsx && npx tsc -b` | ✅ (extend, in __tests__/) | ⬜ pending |
| 129-03-02 | 03 | 3 | TACUI-08 | — | N/A (phase-final frontend gate) | gate | `cd frontend && npm run lint && npm test -- --run && npx tsc -b` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Two NEW frontend test files must be created before/at the start of their respective tasks (both in `__tests__/` subdirs):

- [ ] `frontend/src/lib/__tests__/tacticDepth.test.ts` — full-move-slider ↔ half-ply-API conversion (`sliderToMax`/`maxToSlider` round-trips), `derivePreset` (2/6/null exact + custom), `depthToQueryParam` omit-when-null + half-ply passthrough, full-move summary strings (TACUI-06, D-03).
- [ ] `frontend/src/hooks/__tests__/useFlawFilterStore.test.ts` — `isFlawFilterNonDefault` treats `tacticOrientation='either'` + `tacticDepthPreset='intermediate'` as default (D-02); each off-default value flips it true.

All other targets EXTEND existing files (backend: `tests/test_query_utils.py`, `tests/test_library_repository.py`, `tests/test_library_router.py`; frontend: `src/components/library/__tests__/{TacticMotifChip,FlawCard,TacticComparisonGrid}.test.tsx`). No framework install needed — pytest + vitest already configured.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Filter controls + two-bullet cards render correctly at 375px mobile width (parity) | TACUI-06, TACUI-08 / SC#4 | Visual layout/parity not unit-testable; mobile drawer renders the same `FlawFilterControl` | At 375px viewport: open the Flaws-tab mobile filter drawer; confirm Orientation toggle + Tactic Difficulty slider render above Tactic Motif at `min-h-11`/`h-11`; confirm comparison-grid cards stack two bullets vertically and the "More Tactics" accordion matches the Endgame Statistics Concepts visual. |
| Beta-gated visibility end-to-end | TACUI-06/07/08 / 126 D-01 | Component tests mock `useUserProfile`; the real beta toggle is an account-level flag | With a beta-enabled account confirm all new tactic UI is visible; with a non-beta account confirm it is hidden (no controls/chips/grid). |
| Filter dot does NOT light at the Either + Intermediate default | TACUI-06 / D-02 | Visual indicator behavior on the live filter chrome | On first load of the Flaws tab, confirm the filter-active dot reads as default (not "narrowing") at Either + Intermediate, and lights once orientation≠Either or preset≠Intermediate. |

All other phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (the two NEW frontend tests are the only Wave 0 items)
- [x] Sampling continuity: no 3 consecutive implementation tasks without automated verify (every impl task has a quick-run command; each wave ends in a full gate)
- [x] Wave 0 covers all MISSING references (the two NEW `__tests__/` files; all other targets exist and are extended)
- [x] No watch-mode flags (`npm test -- --run` / `vitest run`, never `test:watch`)
- [x] Feedback latency < 120s
- [x] `nyquist_compliant: true` set in frontmatter

**Note on `wave_0_complete`:** left `false` — the two NEW frontend test files are not yet created; the executor sets it true once `tacticDepth.test.ts` and `useFlawFilterStore.test.ts` exist (early in 129-02 task 1).

**Approval:** approved 2026-06-20
