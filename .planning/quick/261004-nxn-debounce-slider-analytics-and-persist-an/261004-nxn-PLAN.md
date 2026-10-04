---
phase: quick-261004-nxn
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/lib/analytics.ts
  - frontend/src/hooks/useDebouncedTrackFeature.ts
  - frontend/src/hooks/__tests__/useDebouncedTrackFeature.test.ts
  - frontend/src/components/analysis/TemperatureSelector.tsx
  - frontend/src/components/analysis/EloSelector.tsx
  - frontend/src/components/filters/TacticDepthFilter.tsx
  - frontend/src/components/filters/OpponentStrengthFilter.tsx
  - frontend/src/components/analysis/__tests__/AnalysisTabs.tracking.test.tsx
  - frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx
  - frontend/CLAUDE.md
  - frontend/src/lib/engineSettings.ts
  - frontend/src/lib/__tests__/engineSettings.test.ts
  - frontend/src/pages/Analysis.tsx
  - frontend/src/pages/__tests__/Analysis.test.tsx
  - CHANGELOG.md
autonomous: true
requirements: [QUICK-261004-nxn]

estimate:
  tokens: 90000
  raw_tokens: 90000
  tasks: 2
  confidence: low

must_haves:
  truths:
    - "A burst of slider commits (held arrow key, repeated PageUp/PageDown) on the Play style, ELO, Tactic Depth or Opponent Strength slider sends exactly one Umami event, carrying the final value, SLIDER_TRACK_DEBOUNCE_MS (1000 ms) after the last commit; a single pointer drag still sends exactly one event."
    - "Two slider adjustments separated by more than SLIDER_TRACK_DEBOUNCE_MS send one event each."
    - "Unmounting a slider with a pending event sends it immediately, attributed to the page where the slider was moved (and subject to that page's D-14 exclusion), not to the page navigated to."
    - "The engine-driving path is never delayed: every onValueChange still calls the component's onChange synchronously."
    - "The Stockfish, Maia and FlawChess switches on the analysis board keep their on/off state across visits (flat localStorage keys, so guests persist too); first-time and tampered values default to ON."
    - "Restoring the switches from storage sends no toggle event; each switch click still sends exactly one toggle event."
    - "A persisted-off engine can never leave the analysis board stuck behind the non-dismissible engine-ready gate."
    - "If localStorage writes throw, the switches still work for the rest of the session."
  artifacts:
    - path: frontend/src/hooks/useDebouncedTrackFeature.ts
      provides: "SLIDER_TRACK_DEBOUNCE_MS and useDebouncedTrackFeature: trailing-debounced trackFeature with flush on unmount and commit-time pathname capture"
    - path: frontend/src/lib/analytics.ts
      provides: "trackFeature optional pathname argument (defaults to window.location.pathname)"
    - path: frontend/src/lib/engineSettings.ts
      provides: "ENGINE_TOGGLE_STORAGE_KEYS, useEngineToggles, setEngineToggle with a session fallback when storage writes fail"
    - path: frontend/src/pages/Analysis.tsx
      provides: "Engine switches read from useEngineToggles; gate initializer requires all three engines on"
  key_links:
    - from: "frontend/src/components/analysis/TemperatureSelector.tsx (and EloSelector, TacticDepthFilter, OpponentStrengthFilter) onValueCommit"
      to: "frontend/src/hooks/useDebouncedTrackFeature.ts"
      via: "the commit handler calls the debounced scheduler instead of trackFeature"
      pattern: "useDebouncedTrackFeature"
    - from: "frontend/src/hooks/useDebouncedTrackFeature.ts flush"
      to: "frontend/src/lib/analytics.ts trackFeature"
      via: "trackFeature(name, props, capturedPathname)"
      pattern: "trackFeature\\("
    - from: "frontend/src/pages/Analysis.tsx handleStockfishToggle / handleMaiaToggle / handleFlawChessToggle"
      to: "frontend/src/lib/engineSettings.ts setEngineToggle"
      via: "handlers persist, then track; useEngineToggles feeds engineEnabled / maiaEnabled / flawChessEnabled"
      pattern: "setEngineToggle\\("
    - from: "frontend/src/pages/Analysis.tsx engineGateOpen lazy initializer"
      to: "frontend/src/lib/engineSettings.ts useEngineToggles"
      via: "useEngineToggles() is called above the gate useState so the initializer can read all three switches"
      pattern: "engineGateRequired\\(\\) &&"
---

<objective>
Two Umami-noise and UX fixes from the 2026-10-04 analytics investigation.

1. Slider analytics debounce. Radix Slider fires onValueCommit on every keyboard step as well as on
   pointer-up. The Play style (temperature) slider has step 0.01 over [-1, 1], so a held arrow key
   sent 60+ "temperature lower" events at 50-150 ms intervals in one prod session. A shared
   trailing-debounce hook makes one adjustment burst send exactly one event with the final value.
   Applies to all four Slider-based trackFeature sites found by grep (onValueCommit plus
   trackFeature): TemperatureSelector, EloSelector, TacticDepthFilter, OpponentStrengthFilter.
   PresetRangeFilter only passes onValueCommit through and stays unchanged.

2. Persist the analysis-board engine switches. engineEnabled (Stockfish), maiaEnabled and
   flawChessEnabled are useState(true) in Analysis.tsx and reset to ON on every mount, so users
   switch engines off again on every visit. They move into the existing engineSettings store
   (localStorage plus useSyncExternalStore, the same seam as fcLines/fcArrows/sfLines/sfArrows).
   Defaults stay ON. Tracking stays in the three handlers only.

Decisions taken here (Claude's discretion, record them in the SUMMARY):
- The switches are NOT added to the Settings panel UI and NOT reset by "Reset all settings"
  (resetAllSettings): they are not panel settings, and a reset that silently re-enables heavy
  engines would surprise users. Persistence only.
- The engine-ready gate now opens at mount only when the cache is cold AND all three engines are
  on. Reason: the gate is non-dismissible and only closes once every required asset has
  downloaded, but an asset only downloads when an engine that uses it is on. A user whose seen
  flags were never written (an `unsupported` device, where the gate is suppressed and the probe
  never runs while engines are off, or a future new asset id) would otherwise be locked out by a
  persisted-off engine. The all-on default, the cold-start state the gate was built for, keeps
  today's behavior exactly.
- Debounce is trailing, per component instance, 1000 ms. An event still pending when the tab is
  closed is lost (no pagehide flush): acceptable for analytics, note it in the SUMMARY.

Out of scope (do NOT implement, list in the SUMMARY only): the focused slider thumb swallowing
ArrowLeft/ArrowRight board navigation; once-per-session dedupe of the engine-gate-shown and
pwa-install-offer-shown events.

Structure note: tracer-first is not applied, matching recent quick plans. Both changes are local
edits to proven surfaces (the analytics registry and the engineSettings store) with no
architectural uncertainty, and the two tasks are independent of each other.

Purpose: clean Umami option-change counts, and engine switches that respect the user's choice.
Output: one shared hook, four rewired slider handlers, a persisted engine-switch store wired into
Analysis.tsx, tests for both, a frontend/CLAUDE.md rule update and a CHANGELOG bullet.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@frontend/CLAUDE.md

<interfaces>
From frontend/src/lib/analytics.ts (current):
- `export function trackFeature<E extends FeatureEventName>(name: E, props: FeatureEventMap[E]): void`
  It returns early when `isTrackingExcludedPath(window.location.pathname)` (D-14) and otherwise calls
  `trackEvent(name, { page: currentPage(), ...props })`. `currentPage(pathname)` already accepts a
  pathname argument.
- `FeatureEventName`, `FeatureEventMap` are exported. 'option-change' props are `OptionChangeProps`
  (target 'elo' | 'temperature' | ...), 'filter-change' props are `FilterChangeProps`.

From frontend/src/lib/engineSettings.ts (current, the pattern to extend):
- Module-level `listeners` Set, `subscribe`, `notify`; one flat localStorage key per setting
  (`flawchess_settings_*`), one primitive per useSyncExternalStore call, every read validated and
  wrapped in try/catch falling back to the default.
- `useEngineDisplaySettings()`, `setCountSetting(id, value)`, `resetAllSettings()` (counts plus sound).
- `SETTINGS_STORAGE_KEYS` is cleared in Analysis.test.tsx's top-level beforeEach (line ~416).

From frontend/src/pages/Analysis.tsx (current, lines ~418-440):
- `const [engineGateOpen, setEngineGateOpen] = useState(() => engineGateRequired());` (line 418)
- `const [engineEnabled, setEngineEnabled] = useState(true);` plus maiaEnabled / flawChessEnabled
- `handleStockfishToggle`, `handleMaiaToggle`, `handleFlawChessToggle` (useCallback, []) each set the
  state then `trackFeature('toggle', { target: 'engine-stockfish' | 'engine-maia' | 'engine-flawchess', value: onOff(on) })`.
- The raw setters are used nowhere else; `setFlawChessEnabled: handleFlawChessToggle` and
  `setEngineEnabled: handleStockfishToggle` further down are prop keys, not the state setters.

Toggle testids: `btn-analysis-engine-toggle` (Stockfish, AnalysisDesktopCards.tsx),
`btn-analysis-maia-toggle` (MaiaHumanPanel.tsx), `btn-analysis-flawchess-toggle` (AnalysisTabs.tsx).
Analysis.test.tsx captures hook options in `maiaCalls`, `flawChessCalls`, `gradingCalls` (each entry
has `enabled`).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Debounced slider tracking hook, wired into all four slider commit handlers</name>
  <files>frontend/src/lib/analytics.ts, frontend/src/hooks/useDebouncedTrackFeature.ts, frontend/src/hooks/__tests__/useDebouncedTrackFeature.test.ts, frontend/src/components/analysis/TemperatureSelector.tsx, frontend/src/components/analysis/EloSelector.tsx, frontend/src/components/filters/TacticDepthFilter.tsx, frontend/src/components/filters/OpponentStrengthFilter.tsx, frontend/src/components/analysis/__tests__/AnalysisTabs.tracking.test.tsx, frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx, frontend/CLAUDE.md</files>
  <read_first>frontend/src/lib/analytics.ts (trackFeature, lines ~405-420), frontend/src/hooks/useTrackedOpen.ts (house style for tracking hooks), frontend/src/components/analysis/TemperatureSelector.tsx, frontend/src/components/analysis/EloSelector.tsx, frontend/src/components/filters/TacticDepthFilter.tsx (lines 40-60), frontend/src/components/filters/OpponentStrengthFilter.tsx (lines 35-55), frontend/src/components/analysis/__tests__/AnalysisTabs.tracking.test.tsx (lines 1-100 and the EloSelector / TemperatureSelector tracking describes), frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx (lines 435-460 and 555-600)</read_first>
  <behavior>
    - Hook: three scheduler calls 100 ms apart with different props send nothing until SLIDER_TRACK_DEBOUNCE_MS after the last call, then exactly one event with the LAST props.
    - Hook: call, advance past the window, call, advance past the window: two events.
    - Hook: call, then unmount before the window: exactly one event sent at unmount; advancing timers afterwards sends nothing more.
    - Hook: scheduled on /analysis, history moved to /library, then unmount: the flushed event has page 'analysis'.
    - Hook: scheduled while on /admin: nothing is ever sent (D-14 still enforced at the captured path).
    - Hook: unmount with nothing pending sends nothing.
    - TemperatureSelector: five ArrowLeft presses on the focused thumb of the stateful wrapper send nothing immediately and exactly one option-change temperature 'lower' after the window.
    - EloSelector: three ArrowRight presses on the stateful wrapper starting at 1500 call onChange synchronously three times (before any timer advance) and send exactly one option-change elo '1800' after the window.
    - EloSelector: two single steps separated by more than the window send two events; one step then unmount sends one event at unmount.
    - Existing pointer-drag and single-keystroke slider tests (both slider files) assert nothing is tracked right after the commit and exactly one event after advancing SLIDER_TRACK_DEBOUNCE_MS.
  </behavior>
  <action>
1. analytics.ts: give trackFeature an optional third parameter `pathname: string` defaulting to `window.location.pathname`, used for BOTH the isTrackingExcludedPath check and `currentPage(pathname)`. Update its doc comment: deferred senders pass the pathname captured when the user acted, so a send that happens after navigation is attributed to the right page and still honors D-14. Existing two-argument callers are unchanged.

2. New frontend/src/hooks/useDebouncedTrackFeature.ts:
   - `export const SLIDER_TRACK_DEBOUNCE_MS = 1000;` with a doc comment citing why (Radix commits on every keyboard step; 0.01-step temperature slider; prod session with 60+ events from one held key).
   - `export function useDebouncedTrackFeature<E extends FeatureEventName>(name: E, delayMs: number = SLIDER_TRACK_DEBOUNCE_MS): (props: FeatureEventMap[E]) => void`.
   - State in refs only (no React state, no re-render): a pending record holding the props plus `window.location.pathname` captured at call time, and the timer handle (`ReturnType<typeof setTimeout> | null`).
   - A stable `flush` (useCallback on [name]): clears the timer; if a record is pending, nulls it and calls `trackFeature(name, record.props, record.pathname)`.
   - The returned scheduler (useCallback on [flush, delayMs]): replaces the pending record, clears any running timer, starts a new setTimeout(flush, delayMs). Trailing only, no leading send.
   - A useEffect whose cleanup calls `flush()` so an unmount sends the last value instead of dropping it. Call the function rather than reading `.current` directly in the cleanup, so react-hooks/exhaustive-deps does not warn. StrictMode's simulated unmount at mount is a no-op because nothing is pending yet.
   - Module doc comment: use this for slider onValueCommit tracking only; never debounce onValueChange (it drives the engines).

3. Rewire the four commit handlers to call the scheduler instead of trackFeature, keeping each payload exactly as today:
   - TemperatureSelector: `const trackCommit = useDebouncedTrackFeature('option-change');` and handleValueCommit sends `{ target: 'temperature', value: temperatureBucket(...) }` through it. Rewrite the "Once per drag (commit), not per tick." comment: one event per adjustment burst, because Radix commits on every keyboard step. handleValueChange and onChange are untouched.
   - EloSelector: same pattern for `{ target: 'elo', value: ... }`; update the Pitfall 2 comment the same way. handleReset keeps its immediate `board-tool` elo-reset trackFeature call (a click, not a slider).
   - TacticDepthFilter and OpponentStrengthFilter: `useDebouncedTrackFeature('filter-change')`; handleSliderCommit calls the scheduler and its useCallback deps become [the scheduler]. Preset clicks (handlePreset) keep their immediate trackFeature calls. Update the "Tracked on drag END only" comments to mention the debounce.
   - Do not touch PresetRangeFilter.tsx (pass-through only).

4. Tests:
   - New frontend/src/hooks/__tests__/useDebouncedTrackFeature.test.ts (jsdom pragma like the sibling tests, renderHook from @testing-library/react, `vi.useFakeTimers()` in beforeEach and `vi.useRealTimers()` in afterEach, window.umami track spy, history.pushState for paths, delete window.umami in afterEach) covering the six hook behaviors above. Import SLIDER_TRACK_DEBOUNCE_MS rather than repeating 1000.
   - AnalysisTabs.tracking.test.tsx: enable fake timers ONLY inside the "EloSelector tracking (Pitfall 2)" and "TemperatureSelector tracking" describes (beforeEach/afterEach there), so the tab and popover tests elsewhere in the file keep real timers. In every existing slider-commit test, assert `track` was not called right after the commit, then `vi.advanceTimersByTime(SLIDER_TRACK_DEBOUNCE_MS)` and keep the existing one-call assertions. The elo-reset test needs no advance (immediate). Add the burst, separated-steps, synchronous-onChange and unmount-flush tests from the behavior list (use the existing StatefulElo / StatefulTemperature wrappers and the render result's unmount).
   - FlawFilterControl.test.tsx: in the describe holding "fires nothing per drag step and exactly one event on drag end" and "reports a tactic-depth slider commit as a preset or custom", use fake timers the same way; assert nothing is tracked right after pointerUp, then exactly one event after advancing. Preset-click tests stay synchronous and unchanged.
   - Mutation check before committing: temporarily make one handler call trackFeature directly again (or stash the TemperatureSelector edit), confirm the new "not called right after commit" assertion fails, then restore.

5. frontend/CLAUDE.md, Umami "Feature events" list: change the Sliders bullet to say sliders track in onValueCommit through `useDebouncedTrackFeature` (Radix commits on every keyboard step, so direct tracking sends one event per arrow press), never on every change.

Commit as e.g. `fix(analytics): debounce slider commit tracking to one event per adjustment`.
  </action>
  <verify>
    <automated>npm --prefix frontend test -- src/hooks/__tests__/useDebouncedTrackFeature.test.ts src/components/analysis/__tests__/AnalysisTabs.tracking.test.tsx src/components/filters/__tests__/FlawFilterControl.test.tsx src/components/analysis/__tests__/TemperatureSelector.test.tsx src/components/analysis/__tests__/EloSelector.test.tsx src/lib/__tests__/analytics.test.ts && npm --prefix frontend run lint && test "$(grep -l "useDebouncedTrackFeature" frontend/src/components/analysis/TemperatureSelector.tsx frontend/src/components/analysis/EloSelector.tsx frontend/src/components/filters/TacticDepthFilter.tsx frontend/src/components/filters/OpponentStrengthFilter.tsx | wc -l)" -eq 4</automated>
  </verify>
  <done>All four slider commit handlers route through useDebouncedTrackFeature; a held key or a drag yields exactly one event with the final value after 1000 ms; unmount flushes with the commit-time page; onChange is still synchronous; the six targeted test files pass and lint is clean; frontend/CLAUDE.md documents the hook.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Persist the Stockfish / Maia / FlawChess switches in the engineSettings store</name>
  <files>frontend/src/lib/engineSettings.ts, frontend/src/lib/__tests__/engineSettings.test.ts, frontend/src/pages/Analysis.tsx, frontend/src/pages/__tests__/Analysis.test.tsx, CHANGELOG.md</files>
  <read_first>frontend/src/lib/engineSettings.ts (whole file), frontend/src/lib/sounds.ts (lines 75-200, the '1'/'0' mute key format), frontend/src/lib/__tests__/engineSettings.test.ts (lines 1-60), frontend/src/pages/Analysis.tsx (lines 405-445 only; the file is 2,800 lines, do not read it whole), frontend/src/pages/__tests__/Analysis.test.tsx (lines 395-460, 536-640, 880-910), CHANGELOG.md (lines 1-30)</read_first>
  <behavior>
    - Store: with empty storage useEngineToggles() returns { stockfish: true, maia: true, flawChess: true }.
    - Store: setEngineToggle('maia', false) writes '0' under ENGINE_TOGGLE_STORAGE_KEYS.maia and re-renders a mounted subscriber to false; setEngineToggle('maia', true) writes '1'.
    - Store: stored values 'false', '', 'off', '2' and '1' all read as true; only exactly '0' reads as false.
    - Store: with Storage.prototype.setItem throwing, setEngineToggle('flawChess', false) still flips the subscriber to false for the session; after restoring setItem, setEngineToggle('flawChess', true) writes '1' and reads true (the session override is cleared by a successful write).
    - Store: resetAllSettings() leaves a stored engine toggle '0' untouched.
    - Page: with ENGINE_TOGGLE_STORAGE_KEYS.flawChess = '0' before render, the FlawChess switch renders off, the latest flawChessCalls entry has enabled false, and no Umami event fires on render.
    - Page: clicking btn-analysis-maia-toggle stores '0' for maia; after unmount and a fresh render the latest maiaCalls entry has enabled false.
    - Page: cold cache (localStorage cleared, resetEngineAssetsForTests) plus a persisted-off Stockfish switch renders no engine-ready-gate; the existing cold-cache test (all defaults) still renders it.
  </behavior>
  <action>
1. engineSettings.ts (extend the existing store, same listeners/subscribe/notify, no new mechanism):
   - Types and constants: `export type EngineToggleId = 'stockfish' | 'maia' | 'flawChess';`, `export interface EngineToggles { stockfish: boolean; maia: boolean; flawChess: boolean }`, `export const ENGINE_TOGGLE_STORAGE_KEYS: Readonly<Record<EngineToggleId, string>>` mapping to 'flawchess_settings_engine_stockfish', 'flawchess_settings_engine_maia', 'flawchess_settings_engine_flawchess' (flat, not email-scoped, so guests persist). Named value constants for '1' (on) and '0' (off), mirroring the sounds.ts mute format.
   - Read: a stored value of exactly the off constant is false; anything else (absent, '1', tampered) is true. try/catch falls back as described next, never throws.
   - Session fallback (storage-write failure must not make an engine switch inert, unlike setCountSetting which may simply not apply): a module-level `Partial<Record<EngineToggleId, boolean>>` of session overrides. setEngineToggle(id, on) tries localStorage.setItem; on success it deletes that id's override, on failure it records the override; then notify(). The reader returns the override when one exists, else the storage read (a storage read that throws yields the default true). Because successful writes never populate the override, tests that clear localStorage cannot leak state through it.
   - `export function useEngineToggles(): EngineToggles` with three useSyncExternalStore calls (stable boolean primitives, server snapshot returns true), and `export function setEngineToggle(id: EngineToggleId, on: boolean): void`.
   - resetAllSettings stays as is (switches are not panel settings, see the objective). Update the module doc comment: the store now also persists the three analysis-board engine switches, still the single account-sync seam, and reset deliberately leaves the switches alone.

2. Analysis.tsx, minimal edit (accepted complexity residual, no refactor):
   - Import useEngineToggles and setEngineToggle from '@/lib/engineSettings' (the module is already imported for useEngineDisplaySettings).
   - Call `useEngineToggles()` ABOVE the engineGateOpen useState and destructure it to the existing names (`stockfish: engineEnabled`, `maia: maiaEnabled`, `flawChess: flawChessEnabled`) so every downstream reference stays untouched. Delete the three useState(true) declarations.
   - Gate initializer becomes `engineGateRequired() && engineEnabled && maiaEnabled && flawChessEnabled`. Add a bug-fix comment at the site: the gate is non-dismissible and only closes once every required asset is done, an asset only downloads while an engine that uses it is on, so with a persisted-off engine and missing seen flags (an unsupported device whose probe never runs, or a newly added asset id) the gate would never close; the all-on default keeps the original cold-start behavior. Keep the existing G-213-34 comment about the lazy initializer being evaluated once at mount.
   - Handlers: replace each raw setter call with `setEngineToggle('stockfish' | 'maia' | 'flawChess', on)`; keep the trackFeature calls and empty deps. Tracking stays ONLY in these handlers; hydration from storage emits nothing.
   - Replace the "D-06: engine on by default" / "Phase 155 D-02/D-03 ... all three engine cards default ON" comments with one comment: all three default ON and persist across visits via the engineSettings store (quick 261004-nxn).

3. Audit (read, then record each finding in the SUMMARY; change code only if a real defect is found). Mid-session off states were already reachable before this task, so only "off at mount" is new:
   - useStockfishEngine, useMaiaEngine, useFlawChessEngine, useStockfishGradingEngine: grep their effects for `enabled` and confirm none spawns or warms a worker when enabled is false on the very first render.
   - useFastForward reads no engine state (per the Analysis.tsx comment); the mobile tab default is 'moves' (AnalysisTabs.tsx defaultValue) and engine-independent; the grading run is gated on maiaEnabled or flawChessEnabled; the Phase 196 root-injection effect handles a disabled side; the eval-bar fallbacks handle off states.
   - Bots (useBotGame) and Train free play (useTrainFreePlay) run their own engines and do not read these switches; confirm with grep and leave them untouched.

4. Tests:
   - engineSettings.test.ts: add a useEngineToggles / setEngineToggle describe covering the five store behaviors above (spy on Storage.prototype.setItem for the failure case; the file's afterEach already restores mocks and clears storage).
   - Analysis.test.tsx: in the top-level beforeEach next to the SETTINGS_STORAGE_KEYS loop (line ~416), also remove every ENGINE_TOGGLE_STORAGE_KEYS value. This is required: many existing tests click a switch off and expect the next test to start with all engines on, which now persists through storage. Then add a describe "Analysis page: persisted engine switches (quick 261004-nxn)" covering the three page behaviors above. For the switch state, assert whatever the Switch renders (aria-checked or data-state; check the component). For the gate case follow the existing gate describe's setup (localStorage.clear() plus resetEngineAssetsForTests()) and set the Stockfish key to '0' afterwards. Install a window.umami track spy for the no-event-on-render assertion and delete it in afterEach.
   - Mutation check before committing: temporarily restore `useState(true)` for flawChessEnabled, confirm the persisted-off page test fails, then restore.

5. CHANGELOG.md: one bullet under "## [Unreleased]" then "### Changed", plain prose without em-dashes, e.g. "Analysis board: the Stockfish, Maia and FlawChess engine switches now remember your choice, so an engine you switch off stays off on your next visit." The slider debounce is analytics-internal and gets no bullet.

6. Run the full frontend gate (see verification) and fix anything it reports. Commit as e.g. `feat(analysis): remember engine on/off switches across visits`.
  </action>
  <verify>
    <automated>npm --prefix frontend test -- src/lib/__tests__/engineSettings.test.ts src/pages/__tests__/Analysis.test.tsx && npm --prefix frontend run build && test "$(grep -c "setEngineToggle(" frontend/src/pages/Analysis.tsx)" -ge 3</automated>
  </verify>
  <done>The three switches read from and write to the engineSettings store, default ON, survive a remount, emit no event on hydration and one per click; a persisted-off engine never shows the engine-ready gate; storage-write failure keeps the switch working for the session; the audit findings are written down; CHANGELOG has the bullet; targeted tests and tsc build pass.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| localStorage -> analysis page | User- or extension-writable engine switch values now decide whether engines run at mount. |
| browser -> Umami (deferred send) | Slider events are now sent up to 1 s after the user acted, possibly after navigation. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-261004-nxn-01 | Tampering | engineSettings engine switch read | low | mitigate | Only the exact off constant disables an engine; every other stored value reads as the default ON and the read never throws. The value is a boolean that only feeds the hooks' `enabled` flag, never search parameters. Covered by the tamper test in engineSettings.test.ts. |
| T-261004-nxn-02 | Information disclosure | useDebouncedTrackFeature deferred send | low | mitigate | The payload is still built from the typed registry (enumerated literals only, D-04). The captured pathname is used only to derive the coarse page id and the D-14 exclusion and is never sent; an /admin capture sends nothing (hook test). |
| T-261004-nxn-03 | Denial of service | Analysis.tsx engine-ready gate with a persisted-off engine | medium | mitigate | The gate opens at mount only when the cache is cold AND all three engines are on, so a switch that keeps an asset from downloading can never pin the non-dismissible gate open. Covered by the cold-cache page test. |
| T-261004-nxn-04 | Repudiation | analytics completeness | low | accept | An event still pending when the tab closes is lost (no pagehide flush). Analytics only; the burst-collapse benefit outweighs a lost tail event. |
| T-261004-nxn-SC | Tampering | npm installs | low | accept | No package installs in this plan, so the package-legitimacy gate has nothing to check. |
</threat_model>

<verification>
Full frontend gate, run once after Task 2 from the repo root (all must exit 0; frontend has no Prettier, never run it):
- npm --prefix frontend run lint
- npm --prefix frontend run build
- npm --prefix frontend test
- npm --prefix frontend run knip

Optional manual spot check (not gating): on the dev build, switch Maia off on /analysis, reload, and confirm it is still off and no gate appears; hold ArrowLeft on the Play style slider with the Umami tracker stubbed in DevTools and confirm one option-change call about a second after release.

No backend files change, so the backend part of the CLAUDE.md pre-merge gate is not needed for this quick task.
</verification>

<success_criteria>
- One adjustment burst on any of the four sliders produces exactly one Umami event with the final value; drags still produce one; unmount flushes with the commit-time page.
- Slider onChange (engine path) is never debounced.
- Engine switches persist across visits, default ON, hydrate silently, keep tracking only in the click handlers, and cannot strand the page behind the engine-ready gate.
- frontend/CLAUDE.md documents useDebouncedTrackFeature; CHANGELOG.md has the user-facing bullet.
- SUMMARY lists the Claude's-discretion decisions, the audit findings and the two out-of-scope follow-ups.
</success_criteria>

<output>
Create `.planning/quick/261004-nxn-debounce-slider-analytics-and-persist-an/261004-nxn-SUMMARY.md` when done.
</output>
