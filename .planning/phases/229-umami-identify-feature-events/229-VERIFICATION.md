---
phase: 229-umami-identify-feature-events
verified: 2026-10-03T21:40:00Z
status: human_needed
score: 5/5 roadmap truths and 18/18 CONTEXT decisions verified
covered_files:
  - .planning/phases/229-umami-identify-feature-events/229-01-PLAN.md
  - .planning/phases/229-umami-identify-feature-events/229-01-SUMMARY.md
  - .planning/phases/229-umami-identify-feature-events/229-02-PLAN.md
  - .planning/phases/229-umami-identify-feature-events/229-02-SUMMARY.md
  - .planning/phases/229-umami-identify-feature-events/229-03-PLAN.md
  - .planning/phases/229-umami-identify-feature-events/229-03-SUMMARY.md
  - .planning/phases/229-umami-identify-feature-events/229-04-PLAN.md
  - .planning/phases/229-umami-identify-feature-events/229-04-SUMMARY.md
  - .planning/phases/229-umami-identify-feature-events/229-05-PLAN.md
  - .planning/phases/229-umami-identify-feature-events/229-05-SUMMARY.md
  - .planning/phases/229-umami-identify-feature-events/229-06-PLAN.md
  - .planning/phases/229-umami-identify-feature-events/229-06-SUMMARY.md
  - .planning/phases/229-umami-identify-feature-events/229-07-PLAN.md
  - .planning/phases/229-umami-identify-feature-events/229-07-SUMMARY.md
  - .planning/phases/229-umami-identify-feature-events/229-08-PLAN.md
  - .planning/phases/229-umami-identify-feature-events/229-08-SUMMARY.md
  - CHANGELOG.md
  - docker-compose.yml
  - docs/production-runbook.md
  - frontend/CLAUDE.md
  - frontend/src/App.tsx
  - frontend/src/components/analysis/AnalysisTabs.tsx
  - frontend/src/components/analysis/AnalysisTagsPanel.tsx
  - frontend/src/components/analysis/EloSelector.tsx
  - frontend/src/components/analysis/EngineLines.tsx
  - frontend/src/components/analysis/FlawChessEngineLines.tsx
  - frontend/src/components/analysis/PasteModal.tsx
  - frontend/src/components/analysis/TemperatureSelector.tsx
  - frontend/src/components/analysis/VariationTree.tsx
  - frontend/src/components/board/BoardControls.tsx
  - frontend/src/components/bots/BotDrawOfferActions.tsx
  - frontend/src/components/bots/BotGameMobileBar.tsx
  - frontend/src/components/bots/GameResultDialog.tsx
  - frontend/src/components/bots/MoveListPanel.tsx
  - frontend/src/components/bots/PersonaCard.tsx
  - frontend/src/components/bots/PersonaDetailSurface.tsx
  - frontend/src/components/bots/PersonaEloDisclosurePopover.tsx
  - frontend/src/components/bots/PersonaGrid.tsx
  - frontend/src/components/bots/PlayStyleControl.tsx
  - frontend/src/components/bots/ResumeGate.tsx
  - frontend/src/components/bots/SetupScreen.tsx
  - frontend/src/components/charts/EndgameEloTimelineSection.tsx
  - frontend/src/components/charts/EndgameMetricsByTcSection.tsx
  - frontend/src/components/charts/EndgameTimePressureSection.tsx
  - frontend/src/components/charts/EndgameTypeBreakdownSection.tsx
  - frontend/src/components/charts/PercentileChip.tsx
  - frontend/src/components/filters/FilterActions.tsx
  - frontend/src/components/filters/FilterPanel.tsx
  - frontend/src/components/filters/FlawFilterControl.tsx
  - frontend/src/components/filters/MobileFilterDrawer.tsx
  - frontend/src/components/filters/OpponentStrengthFilter.tsx
  - frontend/src/components/filters/PresetRangeFilter.tsx
  - frontend/src/components/filters/TacticDepthFilter.tsx
  - frontend/src/components/insights/BulletConfidencePopover.tsx
  - frontend/src/components/insights/OpeningInsightsBlock.tsx
  - frontend/src/components/insights/ScoreConfidencePopover.tsx
  - frontend/src/components/layout/SidebarLayout.tsx
  - frontend/src/components/library/FlawCard.tsx
  - frontend/src/components/library/FlawTrendChart.tsx
  - frontend/src/components/library/MoveStats.tsx
  - frontend/src/components/library/TacticComparisonGrid.tsx
  - frontend/src/components/library/TacticMotifGroup.tsx
  - frontend/src/components/popovers/AchievableScorePopover.tsx
  - frontend/src/components/popovers/FlawBulletPopover.tsx
  - frontend/src/components/popovers/MetricStatPopover.tsx
  - frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx
  - frontend/src/components/results/LibraryGameCard.tsx
  - frontend/src/components/settings/SettingsDialogButton.tsx
  - frontend/src/components/settings/SettingsSheetButton.tsx
  - frontend/src/components/stats/OpeningStatsSection.tsx
  - frontend/src/components/train/TrainReminderResurfaceBanner.tsx
  - frontend/src/components/train/TrainReveal.tsx
  - frontend/src/components/train/TrainScheduleSettings.tsx
  - frontend/src/components/train/TrainSolveScreen.tsx
  - frontend/src/components/ui/info-popover.tsx
  - frontend/src/hooks/useAuth.ts
  - frontend/src/hooks/useTrackedOpen.ts
  - frontend/src/lib/analytics.ts
  - frontend/src/lib/botTimeControlPresets.ts
  - frontend/src/main.tsx
  - frontend/src/pages/Analysis.tsx
  - frontend/src/pages/Endgames.tsx
  - frontend/src/pages/GlobalStats.tsx
  - frontend/src/pages/Openings.tsx
  - frontend/src/pages/Privacy.tsx
  - frontend/src/pages/library/FlawsTab.tsx
  - frontend/src/pages/library/GamesTab.tsx
  - frontend/src/pages/openings/OpeningsFilterFields.tsx
  - frontend/src/pages/openings/OpeningsMobileDrawers.tsx
covered_digest: "v2:sha256:e0f85e3aa4b442977368eb2885b0a268fce0d53e0c7293f9143985a68bc02d53"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "First /api/send pageview of a fresh load on flawchess.com carries the id (D-09/D-16, RESEARCH A1; UAT test 7)"
    expected: "After release, logged in, reload a protected route with network requests visible: the first pageview payload contains `id` equal to users.id"
    why_human: "Needs the real deployed tracker script; the dev tracker is gated off by data-domains. Code ordering (defer tracker script before the module main.tsx, identifyFromStoredToken before the first pageview) is verified, the runtime ordering is not."
  - test: "Umami 3.4.0 actually running after deploy (D-17; UAT test 6)"
    expected: "`ssh flawchess \"cd /opt/flawchess && docker compose images umami\"` shows 3.4.0; migrations 25/26 applied without crash loop"
    why_human: "Prod infra, after the owner's release via bin/deploy.sh"
  - test: "session.distinct_id populated in prod Umami (phase goal, SEED-183 baseline 0 of 1,941; UAT test 8)"
    expected: "Identified sessions > 0 for sessions after ship_ts, first-pageview-gap count near 0, feature events present with page/target/value props (queries in 229-RESEARCH.md, joined to users in Python, admin ids excluded per D-10)"
    why_human: "Prod data, only exists after release"
---

# Phase 229: Umami User Identification & Feature Events Verification Report

**Phase Goal:** Make UI behavior joinable to accounts so we can see which features go unused and whether touching a feature predicts retention. Every authenticated session (guests included) calls `umami.identify(String(users.id))`, so guest -> registered -> retention stitches into one `distinct_id`; a per-page inventory of UI-only interactions ships as a small set of prop-carrying events; the Privacy page stops claiming no personal data is collected. Frontend-only.
**Verified:** 2026-10-03T21:40:00Z
**Status:** human_needed
**Re-verification:** Yes, after owner naming decisions (2c437a7f3); prior verdict human_needed 5/5, covered source changed
**Branch:** gsd/phase-229-umami-identify-feature-events (diff base 8c6555593; delta re-verified: 2c437a7f3)

No code gaps found. Everything that can be verified before a release holds in the code; the remaining items need the deployed tracker / prod Umami, or are owner naming decisions.

## Goal Achievement

### Observable Truths (ROADMAP contract)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Every authenticated session, guests included, identifies with `String(users.id)` as `distinct_id` | VERIFIED | `analytics.ts` `distinctIdFromToken` (JWT `sub`, digits only) + `identifyUser(id, account)` -> `window.umami.identify(id, {account})`. Called from `main.tsx:33` (`identifyFromStoredToken`, boot) and `App.tsx:727-731` (`ProtectedLayout` effect, covers guest and registered). Guest and registered tokens both come from FastAPI-Users `write_token` (`app/services/guest_service.py:52,65,131,214`, `app/routers/auth.py:297`), so `sub = str(user.id)`; backend untouched by the phase. UAT leg 1 observed `__id = [["108", {account:"guest"}]]` on a fresh guest start. Unit tests: `analytics.test.ts` (distinctIdFromToken, identifyUser, identifyFromStoredToken: 156 tests in 5 targeted suites re-run by me, all green). |
| 2 | Guest -> registered -> retention stitches into one distinct_id (same users row) | VERIFIED | Promotion keeps the `users` row (`guest_service.py`, per CONTEXT canonical ref); the id is the JWT `sub`, so it is identical across promotion. `logoutForPromotion` callers hard-navigate (documented in `useAuth.ts`), `ProtectedLayout` re-identifies from the new token. The actual `session.distinct_id` stitching in prod is a post-deploy item (human item 3). |
| 3 | Per-page inventory of UI-only interactions ships as a small set of prop-carrying events | VERIFIED | `analytics.ts` typed registry: 9 verbs (`tab-switch`, `toggle`, `filter-change`, `option-change`, `board-tool`, `popover-open`, `panel-open`, `action`, `nav-click`), `FeatureEventMap` + exhaustive `FEATURE_EVENT_NAME_SET`, props `page`/`target`/`value` from literal unions only. 86 `trackFeature(` call sites across 60+ files covering all four D-12 groups (grep reviewed; every row of the 229-02 inventory table has a call site, popover hook adopted in InfoPopover + 7 shells, `SidebarLayout`/`MobileFilterDrawer` panel-open, nav-click in `MobileMoreDrawer`). Registry-level and per-surface `*.tracking.test.tsx` suites exist (AnalysisTabs, FilterPanel, PositionBookmarkCard, panelOpenTracking, etc.); I re-ran `AnalysisTabs.tracking` green. UAT leg 2 walked the desktop-reachable rows: each fired exactly once with page + enumerated target/value, no FEN/SAN/name/id in payloads. |
| 4 | The Privacy page stops claiming no personal data is collected | VERIFIED | `Privacy.tsx:58` now reads "...For logged-in and guest accounts this usage data is linked to your account ID, stays on our own servers, and is never shared with third parties." The old "No personal data is collected or shared" sentence is gone (grep over `frontend/src`, README: no other occurrence; remaining "privacy-friendly" strings are `stories/` HTML comments, out of scope). |
| 5 | Frontend-only | VERIFIED | `git diff 8c6555593 HEAD` outside `.planning`: only `frontend/**`, `docker-compose.yml` (D-17 pin), `docs/production-runbook.md` (D-18), `CHANGELOG.md`. No `app/`, `tests/`, `alembic/` changes. |

**Score:** 5/5 roadmap truths, 18/18 CONTEXT decisions, all locked items verified; 0 behavior-unverified.

### CONTEXT Decision Coverage (D-01..D-18)

| Decision | Status | Evidence |
|----------|--------|----------|
| D-01 verb-level events with props, one registry | VERIFIED | 9 verbs, `FeatureEventMap`; costly-reversibility naming decisions still open (human item 4) |
| D-02 no events for URL-routed tab switches | VERIFIED | `tab-switch` typed `AnalysisTabId` only, fired only in `AnalysisTabs.tsx:805`; no Openings/Endgames/Library sub-tab tracking; UAT: URL-routed tab switches silent |
| D-03 user-initiated change only | VERIFIED | Handlers, not effects. One documented exception, `MobileFilterDrawer.tsx:77` (open-transition effect, WR-06), written into `frontend/CLAUDE.md`; UAT confirmed mount/restore/active re-click silent |
| D-04 enumerated prop values, typed wrapper | VERIFIED | `trackFeature<E>` typed by `FeatureEventMap`; only template literal is the Maia ladder rung `${number}`; `popoverTargetFromTestId` strips numeric segments and rejects non-kebab slugs |
| D-05 existing events untouched | VERIFIED | VALIDATION: all 11 legacy events still emitted, none of the 8 emitter files differ from main; legacy kept on `trackEvent` |
| D-06 skip high-frequency interactions | VERIFIED | No tracking on move stepping/drag/eval scrubbing (UAT: back/forward/start/end, eval-chart hover silent); sliders track in `onValueCommit` (WR-03 accepted: keyboard stepping fires per step) |
| D-07 logout is a clean break | VERIFIED | `useAuth.ts` `logout` hard-navigates (`window.location.href = '/'`), commented as load-bearing; 401 interceptor (`api/client.ts:104-108`) also hard-redirects; `logoutForPromotion` callers hard-navigate. `useAuth.test.tsx` asserts the hard navigation; UAT leg 4 observed the page marker and recorder gone after logout. Impersonate/login paths replace the token in place, but the id is re-identified (dedupe key includes id) or skipped (impersonation) |
| D-08 no browser storage, id in memory, re-identify per load | VERIFIED | `identifyUser` string form, in-memory `lastIdentifyKey` per page load; `main.tsx` + `ProtectedLayout` re-identify each load; token read via `localStorage` is the existing app auth token, not a new store |
| D-09 first pageview coverage | VERIFIED in code / post-deploy for runtime | Tracker `defer` script (index.html:41) precedes `type=module` main.tsx (index.html:53); `identifyFromStoredToken` runs at boot, bails without recording the dedupe key if the tracker is absent (late-load safe). Runtime proof on 3.4.0 is human item 1 |
| D-10 admins identified normally | VERIFIED | No admin special-case in `identifyUser`/`ProtectedLayout`; no `account: admin` tag; analysis-time exclusion in VALIDATION post-ship plan |
| D-11 impersonation never identifies | VERIFIED | Two guards: `distinctIdFromToken` returns null for `is_impersonation` claim (real claim, `app/users.py:241`, sub = target id) and `umamiAccountTypeOf` returns null for `profile.impersonation`; effect requires both non-null. Unit-tested `distinctIdFromToken`; UAT leg 3 verified the real function via Vite import (impersonation JWT -> null). No end-to-end impersonation run (kept the owner's admin session intact); the effect wiring itself has no component-level test, only code reading |
| D-12 inventory covers four surface groups | VERIFIED | Analysis board, Openings/Endgames/Library filters/toggles/flaw card, Train + Bots, popovers + More drawer all have call sites (see truth 3); two surfaces from UAT findings resolved by owner decision 2026-10-03: `tactic-grid-more` added (2c437a7f3), endgame score-timeline legend is static labels with no click handler, nothing to track |
| D-13 open events for explanation popovers and filter panels | VERIFIED | `useTrackedPopoverOpen` (once per mounted instance) in InfoPopover + 7 shells; `panel-open` for filters/tags/bookmarks via `SidebarLayout`/`MobileFilterDrawer`; UAT: sidebar open fires, close silent |
| D-14 exclude /admin, /activity, auth | VERIFIED | `isTrackingExcludedPath` gate inside `trackFeature` (admin, activity, login, auth); `navDestinationOf` can never name admin/activity; unit-tested; UAT confirmed `/admin` and `/activity` excluded |
| D-15 inventory written down, no review gate | VERIFIED | Registry const arrays plus the inventory table in `229-02-PLAN.md`; `frontend/CLAUDE.md` references the registry |
| D-16 identity from JWT sub, boot + ProtectedLayout, impersonation skip, no profile `id` field | VERIFIED | As above; no change to `UserProfileResponse`/backend |
| D-17 Umami image pinned to 3.4.0 | VERIFIED in repo | `docker-compose.yml`: `ghcr.io/umami-software/umami:3.4.0`, `pull_policy: missing`, comment explains the upgrade mechanism; CHANGELOG operator bullet; runbook post-deploy checks. Deployed state is human item 2 |
| D-18 account-deletion runbook step | VERIFIED | `docs/production-runbook.md` "Umami analytics" section: deletion SQL with placeholder id, separate preview and delete blocks, delete ends in `ROLLBACK` (review WR-01 fixed in fcadc13a2), shared-session handling |

Locked items from ROADMAP not covered by a numbered decision:

| Item | Status | Evidence |
|------|--------|----------|
| `frontend/CLAUDE.md` rule that new features ship with events; DB-known wording touched up | VERIFIED | "Umami analytics" section: "Feature events", "Identity" subsections; DB-known bullet reworded to note identify makes it joinable |
| Supersession pointer in `.planning/notes/active-engagement-time-tracking.md` | VERIFIED | Line 64: "Superseded for usage analytics by SEED-183 / Phase 229 (2026-10-03)" (also corrects the persistence claim) |
| Keep `account: guest\|registered` tag, retype `window.umami.identify` to `(distinctId, data)` | VERIFIED | `analytics.ts` Window typing `identify: (distinctId: string, data?: Record<string,string>)`; `identifyUser` passes `{account}` |
| Internal links use `trackEvent`/`trackFeature` in onClick, never `data-umami-event` on a Link | VERIFIED | `MobileMoreDrawer` nav links use `onClick` -> `trackMoreDrawerNav`; Library/FlawCard analyze links use onClick |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/lib/analytics.ts` | identity helpers + typed registry | VERIFIED | Substantive (350 added lines), imported by 60+ components, tests in `analytics.test.ts` |
| `frontend/src/hooks/useTrackedOpen.ts` | open-transition tracking hook | VERIFIED | Fires in setter, outside updaters (StrictMode safe), used by 11 files; `useTrackedOpen.test.tsx` |
| `frontend/src/main.tsx` | boot identify | VERIFIED | `identifyFromStoredToken()` after `installUmamiBeforeSend()` |
| `frontend/src/App.tsx` | ProtectedLayout identify, More drawer events | VERIFIED | Lines 676-731, 549-600 |
| `frontend/src/hooks/useAuth.ts` | logout reset documented and kept | VERIFIED | Hard navigation intact |
| `frontend/src/pages/Privacy.tsx` | updated disclosure | VERIFIED | Line 58 |
| `docker-compose.yml`, `docs/production-runbook.md`, `CHANGELOG.md`, `frontend/CLAUDE.md` | D-17/D-18/docs | VERIFIED | Read diffs above |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `main.tsx` | `window.umami.identify` | `identifyFromStoredToken` -> `distinctIdFromToken` -> `identifyUser` | WIRED | Tracker script ordered before module script |
| `ProtectedLayout` | `window.umami.identify` | `useEffect([umamiDistinctId, umamiAccountType])` | WIRED | Impersonation double guard |
| Components | `window.umami.track` | `trackFeature` -> `trackEvent` | WIRED | 86 call sites; excluded-route gate in wrapper |
| `scrubUmamiPayload` | identify/track payloads | `data-before-send` | WIRED | Unchanged hook still covers every outgoing payload |
| `logout` / 401 handler | identity reset | hard navigation | WIRED | Browser UAT leg 4 |

### Data-Flow Trace (Level 4)

| Artifact | Data variable | Source | Real data | Status |
|----------|---------------|--------|-----------|--------|
| `identifyUser` id | `umamiDistinctId` | `localStorage auth_token` JWT `sub` set by backend `write_token` | Yes (guest id `108` observed) | FLOWING |
| Event props | `value`/`target` | literal unions from user handlers, not state restore | Yes (UAT payloads) | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Identity, registry, hook, logout, More-drawer, tracking suites | `npx vitest run src/lib/__tests__/analytics.test.ts src/hooks/__tests__/useTrackedOpen.test.tsx src/hooks/__tests__/useAuth.test.tsx src/App.test.tsx src/components/analysis/__tests__/AnalysisTabs.tracking.test.tsx` | 5 files, 156 tests passed | PASS |
| Full gate (lint, tsc build, vitest 293 files/4783 tests, knip, backend gate) | Run by the orchestrator after final merge, not re-run by me (full suite not repeated, per verification constraints) | Reported green | NOT RE-RUN |
| Debt markers in modified files | grep `TBD\|FIXME\|XXX` over non-test files in the diff | none | PASS |

### Probe Execution

SKIPPED: no probes declared by the phase plans.

### Requirements Coverage

No requirement IDs registered in REQUIREMENTS.md for this phase; coverage accounted per CONTEXT decisions D-01..D-18 above (all VERIFIED, with D-09 runtime and D-17 deployed-state items routed to post-deploy human verification).

### Anti-Patterns Found

None blocking. Notes:

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/src/components/filters/MobileFilterDrawer.tsx` | 77 | tracking in an open-transition effect | Info | Documented exception (WR-06); safe while every parent opens the drawer from a tap |
| `frontend/src/App.tsx` | 727 | `ProtectedLayout` identify effect has no component-level test | Info | Pieces unit-tested; wiring covered by code reading and UAT leg 1; impersonation not run end to end |

### Human Verification Required

1. **First pageview carries id on deployed tracker.** Test: after release, logged in on flawchess.com, reload a protected route and inspect the first `/api/send` payload. Expected: `id` present. Why human: needs the real tracker (D-09/D-16, RESEARCH A1).
2. **Umami 3.4.0 running.** Test: `docker compose images umami` on the server and check the logs for migrations 25/26. Expected: tag 3.4.0, no crash loop. Why human: prod infra after release (D-17).
3. **`session.distinct_id` populated.** Test: run the five post-ship SQL queries in `229-RESEARCH.md` via `flawchess-umami-db`, exclude admin ids from `flawchess-prod-db`. Expected: identified sessions > 0 (baseline 0 of 1,941), first-pageview gap near 0, feature events with props. Why human: prod data after release.


Also not walkable in the browser (covered by unit tests, noted in 229-UAT.md): mobile More drawer and `nav-click` (< 736 px viewport), Stockfish engine toggle, Train solve loop events, bot result dialog actions and confirmed discard, `line-delete` and analysis tags-panel chip-cycle (acceptance grep only). I confirmed call sites for these by grep (`App.tsx:554,576,595`, `Analysis.tsx:431`, `TrainSolveScreen.tsx:527,1509`, `GameResultDialog.tsx:173-208`, `ResumeGate.tsx:117,123`, `VariationTree.tsx:691,1033`, `AnalysisTagsPanel.tsx:224`).

## Delta Verification (2c437a7f3, owner naming decisions 2026-10-03)

Read the full diff and checked each change against the registry, call sites, tests and D-xx decisions.

| Change | Verdict | Evidence |
|--------|---------|----------|
| `popoverTargetFromTestId` drops a TC word only when the raw previous segment is `tc` or `card` | VERIFIED | `analytics.ts:418-450`: the check runs on `raw` before numeric filtering, so `opening-finding-card-3-bullet-popover` keeps `bullet` (prev raw segment `3`), `score-bullet-popover-trigger` keeps it (prev `score`). Real call sites match: `metrics-tc-${tc}-${bucket}-title-info`, `time-pressure-card-${tc}-*-info`, `type-card-${tc}-${class}-*`; I found no other `card-<tc>` / `tc-<tc>` popover ids in non-test source. Test table in `analytics.test.ts` covers metrics-tc, type-card, time-pressure-card, score-bullet and finding-card-3-bullet cases. Output is still validated by `POPOVER_TARGET_PATTERN`; no free value can reach the target. |
| Openings color toggle sends `filter-change played-as`; `color` target and `Color` import removed | VERIFIED | Both call sites (`Openings.tsx:661`, `:817`) updated; `grep "target: 'color'"` over `frontend/src` is empty; `'color'` gone from `FILTER_TARGETS` and `FilterChangeProps`. Value `Color` (white\|black) is assignable to `FilterState['playedAs']` (either\|white\|black); `npx tsc -b` exits 0, and since the union member is removed, any stale `color` caller would fail tsc. |
| `TacticComparisonGrid` accordion fires `panel-open tactic-grid-more` on expand only | VERIFIED | `onValueChange` fires only when Radix reports a non-empty value; `tactic-grid-more` added to `PANEL_TARGETS` (the exhaustive `FeatureEventMap`/const-array test passes). New test: render silent, expand fires once with `{page:'library', target:'tactic-grid-more'}`, collapse silent. |
| chip-cycle stays one target | VERIFIED | Unchanged; owner decision recorded as IN-02 accepted. |

D-01 naming stability: the renames (`color` to `played-as`, per-TC popover targets collapsing) change event names only before any release (the tracker events were never shipped), so no Umami history splits; acceptable. D-04 no ids: still holds, the delta adds no new free-valued prop and `tactic-grid-more` is a registry literal. D-03/D-13: the new accordion handler is a user handler, expand only (D-13 discovery, not use), not an effect. D-02/D-05/D-06 unaffected. frontend/CLAUDE.md popover rule updated to describe the per-TC segment stripping.

Minor, non-blocking: the Openings `played-as` swap has no dedicated component test (the Library/Endgames `played-as` path is tested in `FilterPanel.tracking.test.tsx`); the typed registry makes a regression a compile error, and UAT test 5 recorded it as applied. The old stale 21:20 digest is replaced: fresh `covered_digest` computed via `verification.fingerprint` after adding `TacticComparisonGrid.tsx` to the covered set (`Openings.tsx` and `analytics.ts` were already covered).

Re-run for this delta: `npx vitest run src/lib/__tests__/analytics.test.ts src/components/library/__tests__/TacticComparisonGrid.test.tsx src/pages` (20 files, 335 tests passed), `npx tsc -b` (clean), `npx eslint` on the three changed source files (clean). The orchestrator reported the full frontend gate green after the delta (lint, build, 293 files / 4788 tests, knip); I did not repeat the full suite.

### Gaps Summary

No gaps. Phase goal is achieved in the codebase; status is `human_needed` solely because the join-ability outcome (prod `session.distinct_id`, Umami 3.4.0 in prod, first-pageview stitching) can only be observed after the owner's release, and the three UAT post-deploy checks (tests 6-8) cannot run before the owner's release. The four owner naming decisions are closed (see Delta Verification).

---

_Verified: 2026-10-03_
_Verifier: Claude (gsd-verifier)_
