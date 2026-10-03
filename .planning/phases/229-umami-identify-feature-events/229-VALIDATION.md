---
phase: "229"
slug: "umami-identify-feature-events"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| 229-01-01 | 01 | 1 | D-08/D-09/D-10/D-11/D-16 | T-229-01, T-229-02 | impersonation tokens never identify; malformed or non-numeric sub yields no id; string-form identify, deduped, retried when the tracker was absent | unit + build | `cd frontend && npx vitest run src/lib/__tests__/analytics.test.ts` then `cd frontend && npm run build` | ✅ extend | ⬜ pending |
| 229-01-02 | 01 | 1 | D-07 | T-229-03 | logout hard navigation pinned (test fails if removed) | unit | `cd frontend && npx vitest run src/hooks/__tests__/useAuth.test.tsx src/components/train/__tests__/SignupAskActions.test.tsx` | ❌ W0 (new useAuth.test.tsx) | ⬜ pending |
| 229-01-03 | 01 | 1 | D-17/D-18, Privacy | T-229-05, T-229-06 | Privacy claim replaced; Umami pinned 3.4.0; deletion SQL with shared-session pre-check | grep + build | grep chain in 229-01 Task 3 verify, then `cd frontend && npm run build` | n/a | ⬜ pending |
| 229-02-01 | 02 | 2 | D-01/D-04/D-05/D-13/D-14/D-15 | T-229-07, T-229-08, T-229-10 | enumerated registry; popover targets id-free; excluded routes send nothing | unit + lint/build | `cd frontend && npx vitest run src/lib/__tests__/analytics.test.ts src/hooks/__tests__/useTrackedOpen.test.tsx` then `cd frontend && npm run lint && npm run build` | ❌ W0 (new useTrackedOpen.test.tsx) | ⬜ pending |
| 229-02-02 | 02 | 2 | D-13 | T-229-09 | 7 popover shells fire once per mount | unit + build | `cd frontend && npx vitest run src/components/popovers/__tests__/AchievableScorePopover.test.tsx src/components/charts/__tests__/PercentileChip.test.tsx src/components/bots/__tests__/PersonaEloDisclosurePopover.test.tsx src/hooks/__tests__/useTrackedOpen.test.tsx` | ✅ extend | ⬜ pending |
| 229-03-01 | 03 | 3 | D-03/D-13 | T-229-12 | panel-open on open only, never on mount/close | unit + build | `cd frontend && npx vitest run src/components/layout/__tests__/panelOpenTracking.test.tsx` then `cd frontend && npm run build` | ❌ W0 (new panelOpenTracking.test.tsx) | ⬜ pending |
| 229-03-02 | 03 | 3 | D-12/D-14 | T-229-11 | More-drawer nav never names admin/activity | unit + lint/build | `cd frontend && npx vitest run src/App.test.tsx src/components/settings/__tests__/SettingsDialogButton.test.tsx src/components/settings/__tests__/SettingsSheetButton.test.tsx` | ✅ extend | ⬜ pending |
| 229-04-01 | 04 | 3 | D-03/D-12 | T-229-13 | filter changes typed; render and re-tap silent | unit + lint/build | `cd frontend && npx vitest run src/components/filters/__tests__/FilterPanel.tracking.test.tsx` | ❌ W0 (new FilterPanel.tracking.test.tsx) | ⬜ pending |
| 229-04-02 | 04 | 3 | D-03/D-12 | T-229-15 | sliders track on commit only | unit + build | `cd frontend && npx vitest run src/components/filters/__tests__/FlawFilterControl.test.tsx` | ✅ extend | ⬜ pending |
| 229-04-03 | 04 | 3 | D-04/D-12 | T-229-14 | bookmark id never in payload | unit + lint/build | `cd frontend && npx vitest run src/components/position-bookmarks/__tests__/PositionBookmarkCard.tracking.test.tsx` | ❌ W0 (new) | ⬜ pending |
| 229-05-01 | 05 | 3 | D-02/D-12 | T-229-17 | tab-switch on user change only; ELO/temperature commit-only, enumerated | unit + lint/build | `cd frontend && npx vitest run src/components/analysis/__tests__/AnalysisTabs.tracking.test.tsx src/components/analysis/__tests__/EloSelector.test.tsx src/components/analysis/__tests__/TemperatureSelector.test.tsx src/pages/__tests__/Analysis.test.tsx` | ❌ W0 (new AnalysisTabs.tracking.test.tsx) | ⬜ pending |
| 229-05-02 | 05 | 3 | D-06/D-12 | T-229-16 | flip tracked, move stepping silent; no pasted text sent | unit + build | `cd frontend && npx vitest run src/components/board/__tests__/BoardControls.test.tsx` (+ 6 regression suites in the task) | ✅ extend | ⬜ pending |
| 229-06-01 | 06 | 3 | D-12 | T-229-18 | accordion/legend tracking without combo keys | unit + build | `cd frontend && npx vitest run src/components/charts/__tests__/EndgameTypeBreakdownSection.test.tsx src/components/charts/__tests__/EndgameEloTimelineSection.test.tsx` | ✅ extend | ⬜ pending |
| 229-06-02 | 06 | 3 | D-04/D-12 | T-229-18 | game id never in payload | unit + lint/build | `cd frontend && npx vitest run src/components/results/__tests__/LibraryGameCard.test.tsx` | ✅ extend | ⬜ pending |
| 229-07-01 | 07 | 3 | D-12 | T-229-19, T-229-20 | Train actions tracked; DB-known retry/dismiss left out | unit + build | `cd frontend && npx vitest run src/components/train/__tests__/TrainReveal.test.tsx` (+ 3 regression suites) | ✅ extend | ⬜ pending |
| 229-07-02 | 07 | 3 | D-03/D-12 | T-229-19 | setup choices tracked on change only; no persona ids | unit + lint/build | `cd frontend && npx vitest run src/components/bots/__tests__/PlayStyleControl.test.tsx` (+ 4 regression suites) | ✅ extend | ⬜ pending |
| 229-08-01 | 08 | 4 | D-12 | T-229-21 | bot in-game actions tracked; DB-known outcomes silent | unit | `cd frontend && npx vitest run src/components/bots/__tests__/GameResultDialog.test.tsx src/components/bots/__tests__/ResumeGate.test.tsx` | ✅ extend | ⬜ pending |
| 229-08-02 | 08 | 4 | D-15/D-17, locked docs | T-229-23 | CLAUDE.md rule, CHANGELOG, note pointer | grep | grep chain in 229-08 Task 2 verify | n/a | ⬜ pending |
| 229-08-03 | 08 | 4 | D-05, phase gate | T-229-22 | full pre-merge gate incl. knip; existing events intact | full suite | `cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip` + backend gate | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

New test files are created inside the task that first needs them (each task writes its tests alongside the code, tdd="true"), so no separate Wave 0 plan exists:

- [ ] `frontend/src/hooks/__tests__/useTrackedOpen.test.tsx` — `useTrackedOpen` / `useTrackedPopoverOpen` + InfoPopover integration (D-13), Plan 02 Task 1
- [ ] `frontend/src/components/layout/__tests__/panelOpenTracking.test.tsx` — SidebarLayout + MobileFilterDrawer `panel-open` (D-13), Plan 03 Task 1
- [ ] `frontend/src/components/filters/__tests__/FilterPanel.tracking.test.tsx` — D-03, Plan 04 Task 1
- [ ] `frontend/src/components/position-bookmarks/__tests__/PositionBookmarkCard.tracking.test.tsx` — D-04, Plan 04 Task 3
- [ ] `frontend/src/components/analysis/__tests__/AnalysisTabs.tracking.test.tsx` — D-02 + ELO/temperature commit, Plan 05 Task 1
- [ ] `frontend/src/hooks/__tests__/useAuth.test.tsx` — logout hard navigation (D-07), Plan 01 Task 2

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| First `/api/send` pageview of a load carries `id` | D-09/D-16 | Needs the real tracker script in a browser | Dev build with tracker enabled, devtools network tab, reload a protected route, inspect the first pageview payload |
| `session.distinct_id` populated after ship | Phase goal | Prod Umami DB, post-deploy | Orchestrator runs the 5 SQL queries in `229-RESEARCH.md` via `flawchess-umami-db` MCP |
| Umami 3.4.0 actually running after deploy | D-17 | Prod infra | Read-only `ssh flawchess "cd /opt/flawchess && docker compose images umami"` shows 3.4.0; the served `script.js` gains the `distinct-id` marker once Cloudflare's 1-day cache expires |
| Inventory events + guest identify + impersonation skip on a dev build | D-11/D-12/D-13/D-16 | Needs a real browser across auth transitions and all pages | Claude runs it via claude-in-chrome with a console recorder replacing `window.umami` (Plan 08 Task 3 human-check, legs 1-4) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
