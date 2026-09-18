---
phase: "224"
slug: "guest-activation-welcome-removal-and-guest-train"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-09-17"
---

# Phase 224 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-xdist (backend, PostgreSQL template clone per session) · vitest (frontend) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`, `tests/conftest.py`) · `frontend/vite.config.ts` test block + `frontend/src/vitest.setup.ts` |
| **Quick run command** | `uv run pytest tests/<changed file>` · `( cd frontend && npx vitest run <changed test files> )` |
| **Full suite command** | `uv run pytest -n auto -x` · `( cd frontend && npm run lint && npm run build && npm run knip && npm test -- --run )` |
| **Estimated runtime** | backend ~3 min with `-n auto`; frontend vitest ~90 s, full frontend gate ~4 min |

---

## Sampling Rate

- **After every task commit:** Run the changed test files (`uv run pytest <file>` / `npx vitest run <files>`); `uv run ty check app/ tests/ scripts/` after any backend edit
- **After every plan wave:** Run the full suite for the stack(s) the wave touched; `npm run build` is the ONLY frontend type check (esbuild strips types in lint/test) and `npm run knip` must run because this phase deletes files (`welcomeDismissal.ts`, `TrainGuestGate.tsx`)
- **Before `/gsd-verify-work`:** Both full suites green plus the pre-merge gate from CLAUDE.md (ruff format/check, ty, `scripts/check_function_size.py`, pytest `-n auto -x`, frontend lint + test)
- **Max feedback latency:** ~4 min (full frontend gate)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-T1 (tracer) | 224-01 | 1 | GUESTACT-02, GUESTACT-03, GUESTACT-14 | T-224-01, T-224-02, T-224-03, T-224-05 | Removing the account-type gate does not widen per-user scoping; the D-09 backstop is recorded in code | integration + unit | `uv run pytest tests/routers/test_train.py -k guest -x` · `( cd frontend && npx vitest run src/App.test.tsx )` | ✅ both exist | ⬜ pending |
| 01-T2 | 224-01 | 1 | GUESTACT-04 | T-224-02 | A zero-game guest's session is scoped to its own user id end to end | integration | `uv run pytest tests/routers/test_train.py -k guest_zero_game -x -q` | ❌ new test (authored by this task) | ⬜ pending |
| 02-T1 | 224-02 | 1 | GUESTACT-01 | T-224-06 | A client-controlled localStorage flag leaves the routing decision path | unit | `( cd frontend && npx vitest run src/pages/__tests__/Home.redirect.test.tsx )` | ❌ new test file | ⬜ pending |
| 02-T2 | 224-02 | 1 | GUESTACT-08 | T-224-07, T-224-08 | The promotion handoff is reused verbatim, never re-authored | unit | `( cd frontend && npx vitest run src/pages/__tests__/Welcome.test.tsx )` | ✅ exists (rewritten) | ⬜ pending |
| 03-T1 | 224-03 | 1 | GUESTACT-13 | T-224-09, T-224-10 | Named-parameter binding, aggregate-only output on a read-only connection | integration | `uv run pytest tests/test_admin_activity_stats.py -x -q` | ✅ exists (extended) | ⬜ pending |
| 03-T2 | 224-03 | 1 | GUESTACT-13 | T-224-09 | No new chart geometry surface | harness + build | `( cd frontend && npm run check:activity-layout )` | ✅ exists | ⬜ pending |
| 03-T3 | 224-03 | 1 | GUESTACT-12 | T-224-11, T-224-12 | Provenance committed next to every number; no secret is read | doc gate | `test -f reports/growth/guest-activation-baseline-2026-09-17.md && [ "$(grep -n '```sql' reports/growth/guest-activation-baseline-2026-09-17.md \| wc -l)" -ge 4 ]` | ❌ new file | ⬜ pending |
| 03-T4 (checkpoint:human-action) | 224-03 | 1 | GUESTACT-12 | T-224-11 | Umami credentials stay with the operator | manual | human checkpoint, then `grep -c 'PENDING OPERATOR READING' reports/growth/guest-activation-baseline-2026-09-17.md` returns 0 | n/a | ⬜ pending |
| 04-T1 | 224-04 | 2 | GUESTACT-09 | T-224-14 | No zero-game string promises an analysis that is not running | unit | `( cd frontend && npx vitest run src/lib/__tests__/trainBotCopy.test.ts )` | ✅ exists (extended) | ⬜ pending |
| 04-T2 | 224-04 | 2 | GUESTACT-09 | T-224-15 | `is_guest` originates from `useUserProfile()` and travels as a prop | unit | `( cd frontend && npx vitest run src/components/train/__tests__/TrainStartScreen.test.tsx src/components/train/__tests__/TrainSolveScreen.test.tsx src/components/train/__tests__/TrainSolveScreen.restoredGameArrow.test.tsx src/components/train/__tests__/TrainScoreScreen.test.tsx src/pages/__tests__/Train.solveLoop.test.tsx )` | ✅ all exist | ⬜ pending |
| 04-T3 | 224-04 | 2 | GUESTACT-15 | T-224-13, T-224-16 | A guest cannot reach `reminder_enabled=true` or a push subscription from the UI | unit | `( cd frontend && npx vitest run src/components/train/__tests__/TrainScheduleSettings.test.tsx )` | ✅ exists (extended) | ⬜ pending |
| 05-T1 | 224-05 | 2 | GUESTACT-10 | T-224-17, T-224-18, T-224-19 | Deletes sit inside the WR-01 eligibility re-check transaction | integration | `uv run pytest tests/test_guest_cleanup_service.py -x -q` | ✅ exists | ⬜ pending |
| 05-T2 | 224-05 | 2 | GUESTACT-10 | T-224-17, T-224-19 | The filler solve with `game_id IS NULL` is provably reached | integration | `uv run pytest tests/test_guest_cleanup_service.py -k drill -x -q` | ✅ exists (rewritten) | ⬜ pending |
| 05-T3 | 224-05 | 2 | GUESTACT-06, GUESTACT-16 | T-224-20, T-224-21 | In-place promotion preserves FK'd children; the fan-out guest filter stays | integration | `uv run pytest tests/test_guest_auth.py -x -q` | ✅ exists (extended) | ⬜ pending |
| 06-T1 | 224-06 | 3 | GUESTACT-11 | T-224-22, T-224-23 | `logoutForPromotion()` ordering preserved; no umami attribute on an internal route control | unit | `( cd frontend && npx vitest run src/components/train/__tests__/SignupAskActions.test.tsx )` | ❌ new test file | ⬜ pending |
| 06-T2 | 224-06 | 3 | GUESTACT-05 | T-224-24, T-224-25, T-224-26 | Guest branch is additive and guarded; the registered render is unchanged | unit | `( cd frontend && npx vitest run src/components/train/__tests__/TrainScoreScreen.test.tsx )` | ✅ exists (extended) | ⬜ pending |
| 06-T3 | 224-06 | 3 | GUESTACT-07, GUESTACT-11 | T-224-24, T-224-25 | Per-surface umami source; no Train pitch and no third button | unit | `( cd frontend && npx vitest run src/components/import/__tests__/ImportGuestPromoBubble.test.tsx )` | ❌ new test file | ⬜ pending |
| 06-T4 | 224-06 | 3 | — | — | No internal identifier leaks into user-facing release notes | doc gate | `[ "$(grep -c '^## \[Unreleased\]' CHANGELOG.md)" -eq 1 ] && ! grep -nE 'GUESTACT-\|\.tsx\|\.py' CHANGELOG.md` | ✅ exists | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Resolved at planning time — the module is `tests/routers/test_train.py` (not `tests/test_train_router.py`), and every gap below is owned by a named task rather than a separate Wave 0 plan, because the phase's tests all live beside existing suites:

- [ ] `tests/routers/test_train.py` — four guest 403 tests inverted to 200 and renamed (plan 224-01 task 1)
- [ ] `tests/routers/test_train.py::test_guest_zero_game_warmup_end_to_end` — NEW (plan 224-01 task 2)
- [ ] `frontend/src/App.test.tsx` — the two Train-locked assertions inverted, in the same commit as the `IMPORT_EXEMPT_ROUTES` edit (plan 224-01 task 1)
- [ ] `frontend/src/pages/__tests__/Train.guestGate.test.tsx` — DELETED, closing the Phase 215 deferred contamination flake (plan 224-01 task 1)
- [ ] `frontend/src/pages/__tests__/Home.redirect.test.tsx` — NEW, no `HomePage` coverage exists today (plan 224-02 task 1)
- [ ] `frontend/src/pages/__tests__/Welcome.test.tsx` — rewritten; its dismissal-helper describe block goes with the deleted module (plan 224-02 task 2)
- [ ] `tests/test_guest_cleanup_service.py::test_purge_guest_cascades_drill_rows` — rewritten for D-08 (explicit `DrillSession` + `TrainSettings` delete, `game_id IS NULL` filler solve reaches 0) (plan 224-05 task 2)
- [ ] `tests/test_guest_auth.py::test_train_state_preserved_after_promotion` — NEW (plan 224-05 task 3)
- [ ] `frontend/src/components/train/__tests__/SignupAskActions.test.tsx` — NEW (plan 224-06 task 1)
- [ ] `frontend/src/components/import/__tests__/ImportGuestPromoBubble.test.tsx` — NEW; no test covers the `import-guest-promo-*` testids today (plan 224-06 task 3)

Existing infrastructure (pytest template DB, vitest setup) covers all phase requirements; no framework install needed.

---

## Manual-Only Verifications

- Baseline numbers for lever A (`/welcome` landings, Umami) are read from the Umami UI or via `ssh flawchess` and recorded in the baseline note before merge (operator checkpoint, plan 224-03 task 4, RESEARCH.md Open Question 3)
- Registered-user score screen byte-identity is asserted by structural prop assertions in `TrainScoreScreen.test.tsx` (plan 224-06 task 2); a visual pass on dev is the human backstop
- `workflow.human_verify_mode` is `end-of-phase` (absent from `.planning/config.json`, so the default applies), so no plan emits a `checkpoint:human-verify`; the one blocking checkpoint in this phase is the `checkpoint:human-action` in plan 224-03, which cannot be automated because the Umami credentials live in `.env` and are hook-denied
