---
phase: "229"
slug: "umami-identify-feature-events"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-03"
---

# Phase 229 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (+ @testing-library/react, jsdom per file) |
| **Config file** | `frontend/vite.config.ts` (test block, `setupFiles: ['src/vitest.setup.ts']`) |
| **Quick run command** | `cd frontend && npx vitest run src/lib/__tests__/analytics.test.ts` |
| **Full suite command** | `cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip` |
| **Estimated runtime** | ~120 seconds (full), ~5 seconds (quick) |

---

## Sampling Rate

- **After every task commit:** the touched component's test file plus `analytics.test.ts`
- **After every plan wave:** `cd frontend && npm test -- --run && npm run build`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

Filled by the planner from `229-RESEARCH.md` § Validation Architecture (Decision → Test Map).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 229-01-01 | 01 | 1 | D-08/D-09/D-10/D-11/D-16 | T-229-01, T-229-02 | impersonation tokens never identify; malformed or non-numeric sub yields no id; string-form identify, deduped, retried when the tracker was absent | unit + build | `cd frontend && npx vitest run src/lib/__tests__/analytics.test.ts` then `cd frontend && npm run build` | ✅ extended | ✅ green |
| 229-01-02 | 01 | 1 | D-07 | T-229-03 | logout hard navigation pinned (test fails if removed) | unit | `cd frontend && npx vitest run src/hooks/__tests__/useAuth.test.tsx src/components/train/__tests__/SignupAskActions.test.tsx` | ✅ created | ✅ green |
| 229-01-03 | 01 | 1 | D-17/D-18, Privacy | T-229-05, T-229-06 | Privacy claim replaced; Umami pinned 3.4.0; deletion SQL with shared-session pre-check | grep + build | grep chain in 229-01 Task 3 verify, then `cd frontend && npm run build` | n/a | ✅ green |
| 229-02-01 | 02 | 2 | D-01/D-04/D-05/D-13/D-14/D-15 | T-229-07, T-229-08, T-229-10 | enumerated registry; popover targets id-free; excluded routes send nothing | unit + lint/build | `cd frontend && npx vitest run src/lib/__tests__/analytics.test.ts src/hooks/__tests__/useTrackedOpen.test.tsx` then `cd frontend && npm run lint && npm run build` | ✅ created | ✅ green |
| 229-02-02 | 02 | 2 | D-13 | T-229-09 | 7 popover shells fire once per mount | unit + build | `cd frontend && npx vitest run src/components/popovers/__tests__/AchievableScorePopover.test.tsx src/components/charts/__tests__/PercentileChip.test.tsx src/components/bots/__tests__/PersonaEloDisclosurePopover.test.tsx src/hooks/__tests__/useTrackedOpen.test.tsx` | ✅ extended | ✅ green |
| 229-03-01 | 03 | 3 | D-03/D-13 | T-229-12 | panel-open on open only, never on mount/close | unit + build | `cd frontend && npx vitest run src/components/layout/__tests__/panelOpenTracking.test.tsx` then `cd frontend && npm run build` | ✅ created | ✅ green |
| 229-03-02 | 03 | 3 | D-12/D-14 | T-229-11 | More-drawer nav never names admin/activity | unit + lint/build | `cd frontend && npx vitest run src/App.test.tsx src/components/settings/__tests__/SettingsDialogButton.test.tsx src/components/settings/__tests__/SettingsSheetButton.test.tsx` | ✅ extended | ✅ green |
| 229-04-01 | 04 | 3 | D-03/D-12 | T-229-13 | filter changes typed; render and re-tap silent | unit + lint/build | `cd frontend && npx vitest run src/components/filters/__tests__/FilterPanel.tracking.test.tsx` | ✅ created | ✅ green |
| 229-04-02 | 04 | 3 | D-03/D-12 | T-229-15 | sliders track on commit only | unit + build | `cd frontend && npx vitest run src/components/filters/__tests__/FlawFilterControl.test.tsx` | ✅ extended | ✅ green |
| 229-04-03 | 04 | 3 | D-04/D-12 | T-229-14 | bookmark id never in payload | unit + lint/build | `cd frontend && npx vitest run src/components/position-bookmarks/__tests__/PositionBookmarkCard.tracking.test.tsx` | ✅ created | ✅ green |
| 229-05-01 | 05 | 3 | D-02/D-12 | T-229-17 | tab-switch on user change only; ELO/temperature commit-only, enumerated | unit + lint/build | `cd frontend && npx vitest run src/components/analysis/__tests__/AnalysisTabs.tracking.test.tsx src/components/analysis/__tests__/EloSelector.test.tsx src/components/analysis/__tests__/TemperatureSelector.test.tsx src/pages/__tests__/Analysis.test.tsx` | ✅ created | ✅ green |
| 229-05-02 | 05 | 3 | D-06/D-12 | T-229-16 | flip tracked, move stepping silent; no pasted text sent | unit + build | `cd frontend && npx vitest run src/components/board/__tests__/BoardControls.test.tsx` (+ 6 regression suites in the task) | ✅ extended | ✅ green |
| 229-06-01 | 06 | 3 | D-12 | T-229-18 | accordion/legend tracking without combo keys | unit + build | `cd frontend && npx vitest run src/components/charts/__tests__/EndgameTypeBreakdownSection.test.tsx src/components/charts/__tests__/EndgameEloTimelineSection.test.tsx` | ✅ extended | ✅ green |
| 229-06-02 | 06 | 3 | D-04/D-12 | T-229-18 | game id never in payload | unit + lint/build | `cd frontend && npx vitest run src/components/results/__tests__/LibraryGameCard.test.tsx` | ✅ extended | ✅ green |
| 229-07-01 | 07 | 3 | D-12 | T-229-19, T-229-20 | Train actions tracked; DB-known retry/dismiss left out | unit + build | `cd frontend && npx vitest run src/components/train/__tests__/TrainReveal.test.tsx` (+ 3 regression suites) | ✅ extended | ✅ green |
| 229-07-02 | 07 | 3 | D-03/D-12 | T-229-19 | setup choices tracked on change only; no persona ids | unit + lint/build | `cd frontend && npx vitest run src/components/bots/__tests__/PlayStyleControl.test.tsx` (+ 4 regression suites) | ✅ extended | ✅ green |
| 229-08-01 | 08 | 4 | D-12 | T-229-21 | bot in-game actions tracked; DB-known outcomes silent | unit | `cd frontend && npx vitest run src/components/bots/__tests__/GameResultDialog.test.tsx src/components/bots/__tests__/ResumeGate.test.tsx` | ✅ extended | ✅ green |
| 229-08-02 | 08 | 4 | D-15/D-17, locked docs | T-229-23 | CLAUDE.md rule, CHANGELOG, note pointer | grep | grep chain in 229-08 Task 2 verify | n/a | ✅ green |
| 229-08-03 | 08 | 4 | D-05, phase gate | T-229-22 | full pre-merge gate incl. knip; existing events intact | full suite | `cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip` + backend gate | n/a | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

New test files are created inside the task that first needs them (each task writes its tests alongside the code, tdd="true"), so no separate Wave 0 plan exists:

- [x] `frontend/src/hooks/__tests__/useTrackedOpen.test.tsx` — `useTrackedOpen` / `useTrackedPopoverOpen` + InfoPopover integration (D-13), Plan 02 Task 1
- [x] `frontend/src/components/layout/__tests__/panelOpenTracking.test.tsx` — SidebarLayout + MobileFilterDrawer `panel-open` (D-13), Plan 03 Task 1
- [x] `frontend/src/components/filters/__tests__/FilterPanel.tracking.test.tsx` — D-03, Plan 04 Task 1
- [x] `frontend/src/components/position-bookmarks/__tests__/PositionBookmarkCard.tracking.test.tsx` — D-04, Plan 04 Task 3
- [x] `frontend/src/components/analysis/__tests__/AnalysisTabs.tracking.test.tsx` — D-02 + ELO/temperature commit, Plan 05 Task 1
- [x] `frontend/src/hooks/__tests__/useAuth.test.tsx` — logout hard navigation (D-07), Plan 01 Task 2

---

## Final Gate Record (plan 229-08, 2026-10-03)

| Step | Result |
|------|--------|
| `ruff format app/ tests/ scripts/ analysis/`, `ruff check . --fix` | clean, no files modified |
| `ty check app/ tests/ scripts/` and `analysis/` | all checks passed |
| `check_function_size.py app/ --fail-over-depth 4` | OK, 1077 functions, no breaches |
| `pytest -n auto -x -q` | 4985 passed, 19 skipped |
| `npm run lint` / `npm run build` | clean |
| `npm test -- --run` | 293 files, 4780 tests passed |
| `npm run knip` | exit 0 (only a pre-existing `.css` configuration hint), every registry export consumed |
| D-05 emitter check | all 11 legacy events still emitted; none of their 8 emitter files differ from `main` |
| Payload hygiene | 86 `trackFeature` call sites; the only template literal is `EloSelector` `${snapToLadder(...)}` (a `MAIA_ELO_LADDER` rung, typed `${number}`) |

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| First `/api/send` pageview of a load carries `id` | D-09/D-16 | Needs the real tracker script in a browser | Dev build with tracker enabled, devtools network tab, reload a protected route, inspect the first pageview payload |
| `session.distinct_id` populated after ship | Phase goal | Prod Umami DB, post-deploy | Orchestrator runs the 5 SQL queries in `229-RESEARCH.md` via `flawchess-umami-db` MCP |
| Umami 3.4.0 actually running after deploy | D-17 | Prod infra | Read-only `ssh flawchess "cd /opt/flawchess && docker compose images umami"` shows 3.4.0; the served `script.js` gains the `distinct-id` marker once Cloudflare's 1-day cache expires |
| Inventory events + guest identify + impersonation skip on a dev build | D-11/D-12/D-13/D-16 | Needs a real browser across auth transitions and all pages | Claude runs it via claude-in-chrome with a console recorder replacing `window.umami` (Plan 08 Task 3 human-check, legs 1-4) |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 120s (full frontend suite ~30s locally)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** automated gate green 2026-10-03 (plan 229-08). Manual-Only rows resolved 2026-10-03: browser UAT legs 1-4 passed before the squash-merge, post-deploy checks passed after the release (229-UAT.md tests 6-8; Umami migrations 25/26 applied, 3 of 3 post-ship sessions identified, first-pageview gap 0).

---

## Browser UAT script (run by the orchestrator via claude-in-chrome, dev build, before the squash-merge)

Start the stack (`bin/run_local.sh`), open `http://localhost:5173`, and in the page console replace `window.umami` with a recorder: `track` pushes `[name, data]` onto `window.__ev`, `identify` pushes its arguments onto `window.__id` (the dev tracker never sends because of `data-domains`).

1. **Guest identify.** Logged-out Home, click "Use as guest": `window.__id` gains one entry `[<guest users.id as digit string>, {account: 'guest'}]`.
2. **Inventory walk.** Walk every row of the "Feature-event inventory (D-15)" table in `229-02-PLAN.md` at desktop width and again at 375px. Each interaction adds exactly the listed event with `page` and `target` (and `value` where listed). Page loads, panel closes, move stepping, fast-forward and eval-chart clicks add nothing; a slider drag adds its single event only on thumb release. No payload contains a FEN, SAN move, username, opening name, game or bookmark id. Plan 229-08 additions to walk: bot Resume, confirmed Discard (first Discard click and Cancel add nothing), Rematch, New opponent, Analyze this game, draw Decline (Accept adds nothing), Return to live position.
3. **Impersonation.** Log in as the dev superuser, impersonate another user from `/admin`, reload with the recorder re-installed: `window.__id` stays empty and nothing fires on `/admin`.
4. **Logout.** Click Logout: the page fully reloads (the recorder object is gone afterwards).

Log any mismatch per inventory row with the observed payload (dev ids only, T-229-22).

## Post-deploy verification (after the owner's release via `bin/deploy.sh`, read-only)

- (a) `ssh flawchess "cd /opt/flawchess && docker compose images umami"` shows tag 3.4.0.
- (b) On https://flawchess.com logged in, with claude-in-chrome reading network requests, the first `/api/send` pageview payload of a fresh load carries `id` (RESEARCH A1, boot identify before the first pageview).
- (c) The orchestrator runs the five queries in `229-RESEARCH.md` "Post-ship verification SQL" through the `flawchess-umami-db` MCP with `ship_ts` = release time (website `0ca19960-2398-4caf-b321-8039708fa7ef`), pulls admin `users.id`s from `flawchess-prod-db` to exclude them (D-10), and joins in Python (separate databases).
- Expected: identified sessions above 0 (baseline 0 of 1,941), first-pageview-gap count near 0, feature events present with page/target/value props.

## Validation Audit 2026-10-03
| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

All 19 task rows already green with automated commands; the four Manual-Only rows are closed by 229-UAT.md (8/8 pass).
