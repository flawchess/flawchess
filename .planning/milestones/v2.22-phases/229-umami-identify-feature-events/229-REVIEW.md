---
phase: 229-umami-identify-feature-events
reviewed: 2026-10-03T00:00:00Z
depth: standard
files_reviewed: 95
files_reviewed_list:
  - docker-compose.yml
  - docs/production-runbook.md
  - frontend/CLAUDE.md
  - frontend/src/App.test.tsx
  - frontend/src/App.tsx
  - frontend/src/components/analysis/AnalysisTabs.tsx
  - frontend/src/components/analysis/AnalysisTagsPanel.tsx
  - frontend/src/components/analysis/EloSelector.tsx
  - frontend/src/components/analysis/EngineLines.tsx
  - frontend/src/components/analysis/FlawChessEngineLines.tsx
  - frontend/src/components/analysis/PasteModal.tsx
  - frontend/src/components/analysis/TemperatureSelector.tsx
  - frontend/src/components/analysis/__tests__/AnalysisTabs.tracking.test.tsx
  - frontend/src/components/analysis/VariationTree.tsx
  - frontend/src/components/board/BoardControls.tsx
  - frontend/src/components/board/__tests__/BoardControls.test.tsx
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
  - frontend/src/components/bots/__tests__/GameResultDialog.test.tsx
  - frontend/src/components/bots/__tests__/PersonaCard.test.tsx
  - frontend/src/components/bots/__tests__/PersonaEloDisclosurePopover.test.tsx
  - frontend/src/components/bots/__tests__/PlayStyleControl.test.tsx
  - frontend/src/components/bots/__tests__/ResumeGate.test.tsx
  - frontend/src/components/bots/__tests__/SetupScreen.test.tsx
  - frontend/src/components/charts/EndgameEloTimelineSection.tsx
  - frontend/src/components/charts/EndgameMetricsByTcSection.tsx
  - frontend/src/components/charts/EndgameTimePressureSection.tsx
  - frontend/src/components/charts/EndgameTypeBreakdownSection.tsx
  - frontend/src/components/charts/PercentileChip.tsx
  - frontend/src/components/charts/__tests__/EndgameEloTimelineSection.test.tsx
  - frontend/src/components/charts/__tests__/EndgameTypeBreakdownSection.test.tsx
  - frontend/src/components/charts/__tests__/PercentileChip.test.tsx
  - frontend/src/components/filters/FilterActions.tsx
  - frontend/src/components/filters/FilterPanel.tsx
  - frontend/src/components/filters/FlawFilterControl.tsx
  - frontend/src/components/filters/MobileFilterDrawer.tsx
  - frontend/src/components/filters/OpponentStrengthFilter.tsx
  - frontend/src/components/filters/PresetRangeFilter.tsx
  - frontend/src/components/filters/TacticDepthFilter.tsx
  - frontend/src/components/filters/__tests__/FilterPanel.tracking.test.tsx
  - frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx
  - frontend/src/components/insights/BulletConfidencePopover.tsx
  - frontend/src/components/insights/OpeningInsightsBlock.tsx
  - frontend/src/components/insights/ScoreConfidencePopover.tsx
  - frontend/src/components/layout/SidebarLayout.tsx
  - frontend/src/components/layout/__tests__/panelOpenTracking.test.tsx
  - frontend/src/components/library/FlawCard.tsx
  - frontend/src/components/library/FlawTrendChart.tsx
  - frontend/src/components/library/MoveStats.tsx
  - frontend/src/components/library/TacticMotifGroup.tsx
  - frontend/src/components/popovers/AchievableScorePopover.tsx
  - frontend/src/components/popovers/FlawBulletPopover.tsx
  - frontend/src/components/popovers/MetricStatPopover.tsx
  - frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx
  - frontend/src/components/position-bookmarks/__tests__/PositionBookmarkCard.tracking.test.tsx
  - frontend/src/components/results/LibraryGameCard.tsx
  - frontend/src/components/results/__tests__/LibraryGameCard.test.tsx
  - frontend/src/components/settings/SettingsDialogButton.tsx
  - frontend/src/components/settings/SettingsSheetButton.tsx
  - frontend/src/components/settings/__tests__/SettingsDialogButton.test.tsx
  - frontend/src/components/settings/__tests__/SettingsSheetButton.test.tsx
  - frontend/src/components/stats/OpeningStatsSection.tsx
  - frontend/src/components/train/__tests__/TrainReveal.test.tsx
  - frontend/src/components/train/TrainReminderResurfaceBanner.tsx
  - frontend/src/components/train/TrainReveal.tsx
  - frontend/src/components/train/TrainScheduleSettings.tsx
  - frontend/src/components/train/TrainSolveScreen.tsx
  - frontend/src/components/ui/info-popover.tsx
  - frontend/src/hooks/__tests__/useAuth.test.tsx
  - frontend/src/hooks/__tests__/useTrackedOpen.test.tsx
  - frontend/src/hooks/useAuth.ts
  - frontend/src/hooks/useTrackedOpen.ts
  - frontend/src/lib/analytics.ts
  - frontend/src/lib/botTimeControlPresets.ts
  - frontend/src/lib/__tests__/analytics.test.ts
  - frontend/src/main.tsx
  - frontend/src/pages/Analysis.tsx
  - frontend/src/pages/Endgames.tsx
  - frontend/src/pages/GlobalStats.tsx
  - frontend/src/pages/library/FlawsTab.tsx
  - frontend/src/pages/library/GamesTab.tsx
  - frontend/src/pages/openings/OpeningsFilterFields.tsx
  - frontend/src/pages/openings/OpeningsMobileDrawers.tsx
  - frontend/src/pages/Openings.tsx
  - frontend/src/pages/Privacy.tsx
  - frontend/src/pages/__tests__/Analysis.test.tsx
findings:
  critical: 0
  warning: 6
  info: 5
  total: 11
status: issues_found
---

# Phase 229: Code Review Report

**Reviewed:** 2026-10-03
**Depth:** standard
**Files Reviewed:** 95
**Status:** issues_found

## Summary

Reviewed the Umami identify path, the typed `trackFeature` registry and all ~86 call sites against the CONTEXT decisions (D-01..D-18). Also ran `npm run knip` and `npx tsc -b` in `frontend/`: both clean.

The identify path holds up. Boot identify and `ProtectedLayout` identify dedupe correctly (the bail-before-record in `identifyUser` is right), impersonation tokens are skipped by two independent guards, logout and `logoutForPromotion` all hard-navigate (verified all three promotion callers: `Welcome.tsx`, `SignupAskActions.tsx`, `EvalCoverageBadge.tsx`; the 401 interceptor in `api/client.ts` also hard-navigates), and the guest-token path is never read. No payload leaks an id, FEN, name or free text: I audited every `testId` that reaches `popoverTargetFromTestId` through the tracked popover components (the SAN-bearing `maia-prose-move-*` / `flawchess-verdict-move-*` ids go through `ProseSpan`, which does not use `useTrackedPopoverOpen`). The Umami 3.4.0 ghcr tag exists, and the runbook table/column names match the v3.4.0 `prisma/schema.prisma` (I fetched it and compared). The runbook deletion is scoped by `website_id` on every statement and handles shared sessions correctly.

No BLOCKERs. The remaining defects are events firing on non-changes or with the wrong `page`, one destructive-SQL ergonomics hazard in the runbook, and a doc/rule contradiction. Behavioral refactors (`Analysis.tsx` handler swaps, `EloSelector.snapToLadder`, `useTrackedOpen` in the settings buttons, `MobileFilterDrawer` `panel` prop) are behavior-preserving: snapping is a no-op because Radix already steps from `min` by the ladder step, and every `MobileFilterDrawer` caller is a user-initiated open.

## Warnings

### WR-01: Runbook deletion block is paste-executable with a real-looking placeholder id

**File:** `docs/production-runbook.md:76`
**Issue:** The destructive block starts with `\set did '123'`. Numeric ids are exactly what `distinct_id` holds, so pasting the block "as is" (the doc says "Then run, replacing the id") deletes every Umami row for the real user whose `users.id` is 123, and the preview counts (steps 1 and 2) run straight into the `BEGIN; ... COMMIT;` with no pause. The `ROLLBACK` dry run is only mentioned in prose above the block. A wrong id silently deletes the wrong person's analytics (irreversible, no backup of the Umami tables is referenced).
**Fix:** Use a placeholder that matches nothing and add a guard so an unedited paste is a no-op, and make the commit explicit:
```sql
\set did 'REPLACE_WITH_USERS_ID'
\set site '0ca19960-2398-4caf-b321-8039708fa7ef'
-- ...steps 1 and 2 (read only)...
-- STOP: check the counts above, then run the block below separately.
BEGIN;
-- ...deletes...
-- Review row counts, then:  COMMIT;   (or ROLLBACK;)
```
Split the preview and the destructive transaction into two separate code fences, and end the transaction block with `ROLLBACK;` by default so the operator has to change it to `COMMIT;` deliberately.

### WR-02: Bots "Analyze" can be recorded with `page: analysis` instead of `page: bots`

**File:** `frontend/src/components/bots/GameResultDialog.tsx:170-172`
**Issue:** The handler calls `onAnalyze()` first and tracks afterwards. `Bots.tsx` `handleAnalyze` takes a synchronous `navigate(buildAnalysisLineUrl(...))` branch when `storedGameId === null` (store retries exhausted, `Bots.tsx:360-366`). The app uses `BrowserRouter`, whose `navigate` calls `history.pushState` synchronously, so `window.location.pathname` is already `/analysis` when `trackFeature` derives `page`. The event is then attributed to the Analysis page, exactly the failure mode the author guarded against in `Openings.tsx` (`handleAnalyzePosition` tracks before navigating, with a comment) and `TrainSolveScreen.handleAnalyzeClick`. The normal branch (`enqueueTier1.mutate(..., onSettled: navigate)`) is async and fine, so the bug only shows in the fallback path, which is the one that signals degraded storage.
**Fix:** Track before invoking the callback, consistent with the other two Analyze sites:
```tsx
onClick={() => {
  trackFeature('action', { target: 'analyze' });
  onAnalyze();
}}
```
The same ordering rule should be applied wherever a handler both navigates synchronously and tracks (grep for `trackFeature` immediately after a callback that can call `navigate`).

### WR-03: Slider tracking fires once per arrow-key press, contradicting "once per drag"

**File:** `frontend/src/components/analysis/EloSelector.tsx:138`, `frontend/src/components/analysis/TemperatureSelector.tsx:121`, `frontend/src/components/filters/OpponentStrengthFilter.tsx:105`, `frontend/src/components/filters/TacticDepthFilter.tsx:99`
**Issue:** Radix Slider calls `onValueCommit` for every keyboard step (`onStepKeyDown` commits with `{ commit: true }`), not only at pointer release. A keyboard user stepping the ELO slider 10 rungs sends 10 `option-change` events; the code comments ("once per drag", "never per slider tick") and the frontend CLAUDE.md rule ("Sliders track in `onValueCommit`, not on every change") are only true for pointer input. This is the high-frequency interaction D-06 says to skip, and it also inflates the dashboard for assistive-tech users. Pointer path is fine.
**Fix:** Debounce the commit tracker per slider instance (for example a trailing 500 ms timer in a ref that sends only the last committed value), or track on `onPointerUp`/`onBlur` of the slider root. Update the CLAUDE.md sentence if keyboard steps are intentionally counted.

### WR-04: Preset chips report a "change" when the active preset is re-clicked

**File:** `frontend/src/components/filters/OpponentStrengthFilter.tsx:55-61`, `frontend/src/components/filters/TacticDepthFilter.tsx:61-67` (call site: `PresetRangeFilter.tsx:~100`, `onClick={() => onPreset(preset.key)}`)
**Issue:** `PresetRangeFilter` renders plain `<button>` chips (no Radix single-select that swallows a re-tap) and calls `onPreset` unconditionally. `handlePreset` then tracks every click, including on the already-active preset, so a re-click sends `filter-change` for a non-change. D-03 requires user-initiated change only, and the sibling bot chips (`SetupScreen`, `PersonaDetailSurface`, `PlayStyleControl`) already guard with `if (!isActive)` and the filter `ToggleGroup`s are tested for silent re-tap. These two are the inconsistent ones.
**Fix:** Pass the guard where the active state is known, for example in `PresetRangeFilter`:
```tsx
onClick={() => { if (!isActive) onPreset(preset.key); }}
```
or compare `preset === activePreset` inside each `handlePreset` before tracking.

### WR-05: Time-control chip reports a change when the click is a no-op

**File:** `frontend/src/components/filters/FilterPanel.tsx:334-343`
**Issue:** `toggleTimeControl` clamps the "turn off the last remaining time control" case to `[tc]` (`next.length === 0 ? [tc] : next`), i.e. the filter state does not change, but `trackFeature('filter-change', { target: 'time-control', value: tc })` still runs unconditionally. The event also carries no on/off, so on/off toggling of the same chip is indistinguishable (same for `platform`, `severity`, `flaw-tag`, `tactic-family`, which are all multi-select chips reported as `value: <item>` only), which makes "which time controls do people filter to" unanswerable from the stream.
**Fix:** Skip the event when the resulting state equals the current one, and consider reporting the new state for multi-select chips (`filter-change` with a `${tc}:on|off`-style enumerated value, or reuse the `OnOff` union as `has-gem` does).

### WR-06: Effect-based drawer tracking contradicts the documented "never from a useEffect" rule

**File:** `frontend/src/components/filters/MobileFilterDrawer.tsx:70-79`, `frontend/CLAUDE.md` ("Register first" bullet)
**Issue:** CLAUDE.md states trackFeature is "Never from a `useEffect` on a value", yet `MobileFilterDrawer` tracks from exactly such an effect and the comment calls it "the one allowed effect-style tracking site". Today all callers (`Openings`, `Endgames`, `GlobalStats`, `GamesTab`, `FlawsTab`) open the drawer from a user tap, so it is currently correct, but any future programmatic open (deep link, auto-open on a hint, restored state) would fire `panel-open` without a user action and nobody will connect it to this rule. The rule is also undocumented for contributors reading only CLAUDE.md.
**Fix:** Either track in the parent open handlers (`openFilterSidebar`, `handleMobileFiltersOpenChange(true)`) like `SidebarLayout.handleStripClick` and `Openings.openSuggestions` do, or document the exception explicitly in `frontend/CLAUDE.md` (name the component and the "parent must only open on user tap" invariant) so the rule and the code agree.

## Info

### IN-01: Events fire even when the wrapped callback is absent

**File:** `frontend/src/components/analysis/VariationTree.tsx:690,1032`, `frontend/src/components/library/MoveStats.tsx:344`, `frontend/src/components/train/TrainReveal.tsx:459`
**Issue:** `onDeleteLine?.(...)`, `onToggleCollapse?.()` and `onExit?.()` are optional, but `trackFeature` runs regardless, so a render without the callback records a `line-delete` / `move-stats-expand` / `train-explore-exit` that did nothing.
**Fix:** Guard on the callback (`if (!onDeleteLine) return;`) or fire inside the optional-call branch.

### IN-02: `chip-cycle` conflates tag chips with Move Stats cell clicks

**File:** `frontend/src/components/analysis/AnalysisTagsPanel.tsx:212-224`, `frontend/src/components/results/LibraryGameCard.tsx:600-604`
**Issue:** `handleActivate` is shared by flaw tag chips, motif chips and Move Stats category cells (the comment at `AnalysisTagsPanel.tsx:218` says Move Stats cells "navigate only"), and all send `action / chip-cycle`. The dashboard row therefore cannot separate "tag chip use" from "move stats use".
**Fix:** If that distinction matters, branch on `ref.kind` and add a registered `move-stats-cell` target; otherwise note the conflation in `ACTION_TARGETS`.

### IN-03: Impersonation leaves the admin's id in tracker memory

**File:** `frontend/src/App.tsx:726-731`, `frontend/src/hooks/useAuth.ts:99-115`
**Issue:** `impersonate()` swaps the token without a reload. `ProtectedLayout`'s effect computes `umamiDistinctId === null` and does nothing, which satisfies D-11 (no identify as the target), but the tracker keeps the admin's previous in-memory id, so pageviews and feature events during the impersonation are attributed to the admin's `distinct_id`, with the admin's `account` tag. D-10 excludes admin ids at analysis time so the data is filtered out, but only if the analyst remembers; the cleaner alternative is to hard-navigate on impersonate (as logout does).
**Fix:** Either document this in `frontend/CLAUDE.md` Identity ("impersonation events carry the admin id") or reload after `impersonate()` so the tracker starts anonymous. Not a blocker.

### IN-04: `lib/analytics.ts` imports component and lib types, inverting the layering

**File:** `frontend/src/lib/analytics.ts:16-32`
**Issue:** The registry imports `FilterState` from `components/filters/FilterPanel`, which itself imports `trackFeature` from this module. The `import type` is erased so there is no runtime cycle, but the dependency direction (lib -> component) is the wrong way round and will break if the import is ever made a value import. `FilterChangeProps['played-as']` is the only use.
**Fix:** Move `PlayedAs` (the `FilterState['playedAs']` union) to `@/types/api` and import it from there.

### IN-05: Time-control and platform filter events carry no on/off, and `color` vs `played-as` taxonomy is split

**File:** `frontend/src/lib/analytics.ts:352-369`, `frontend/src/pages/Openings.tsx:656-660,816`
**Issue:** The Openings board color toggle reports `filter-change target=color` while the Library/Endgames "Played as" control reports `target=played-as` for the same underlying `filters.color`/`playedAs` concept, so one user intent lands in two dashboard rows depending on the page. Since D-01 says renaming later splits history, this is cheap to unify now and expensive later.
**Fix:** Pick one target for the "which side am I analyzing" control (`played-as` is the user-visible label) and map the Openings toggle to it before the first release.

---

_Reviewed: 2026-10-03_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
