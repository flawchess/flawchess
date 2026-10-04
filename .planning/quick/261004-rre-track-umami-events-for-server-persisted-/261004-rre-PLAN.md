---
phase: quick-261004-rre
plan: 01
quick_id: 261004-rre
mode: quick
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/lib/analytics.ts
  - frontend/src/lib/__tests__/analytics.test.ts
  - frontend/src/components/train/TrainReminderResurfaceBanner.tsx
  - frontend/src/components/train/__tests__/TrainReminderResurfaceBanner.test.tsx
  - frontend/src/components/train/TrainReminderButton.tsx
  - frontend/src/components/train/__tests__/TrainReminderButton.test.tsx
  - frontend/src/components/train/TrainScheduleSettings.tsx
  - frontend/src/components/train/__tests__/TrainScheduleSettings.test.tsx
  - frontend/src/components/filters/ImportFilterCard.tsx
  - frontend/src/components/filters/__tests__/ImportFilterCard.test.tsx
  - frontend/src/components/settings/LeaderboardPrivacyCard.tsx
  - frontend/src/components/settings/__tests__/LeaderboardPrivacyCard.test.tsx
  - frontend/CLAUDE.md
autonomous: true
requirements: ["QUICK-261004-rre"]

estimate:
  tokens: 150000
  raw_tokens: 150000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "Pressing 'Remind me' on the score screen, 'Get reminders' on the iOS score screen, 'Turn on reminders' on the resurface banner, or switching on the Train-settings reminder switch sends exactly one `action` event with target `reminder-enable`, an enumerated `source` (score-screen | resurface-banner | train-settings) and an enumerated `outcome` (subscribed | dismissed | denied | unsupported | error | install-instructions)"
    - "Clicking an import time-control button sends `toggle` with target `import-tc-{bullet|blitz|rapid|classical}` and the new on/off state; the last-active-TC no-op click sends nothing"
    - "Picking a backlog cap sends `option-change` with target `import-cap` and value '1000' | '3000' | '5000'; re-tapping the active cap sends nothing"
    - "Train schedule: a weekday chip sends `toggle` target `train-day-{mon..sun}` on/off; a puzzles-per-session slider burst sends exactly one debounced `option-change` target `train-puzzles-per-session` with a value on the 3..30 step-3 grid; the reminder switch sends `toggle` target `train-reminder` on/off; the hour picker sends `option-change` target `train-reminder-hour` with '0'..'23'"
    - "Flipping 'Hide me from leaderboards' sends the legacy `settings-change` event with setting `leaderboard-hidden` and value on/off, exactly like SettingsPanel's sound switch"
    - "No new event fires on mount, on settings load, or on draft seeding (D-03); every new prop value is an enumerated string-literal union (D-04), and a number off its enumerated grid sends nothing"
    - "frontend/CLAUDE.md's 'Skip what the URL or database already says' bullet states that row-creating handlers stay un-evented while settings rows overwritten in place get an event"
  artifacts:
    - path: "frontend/src/lib/analytics.ts"
      provides: "Registry entries: reminder-enable action + source/outcome unions, import-tc/train-day/train-reminder toggle targets, import-cap/train-puzzles-per-session/train-reminder-hour option targets + value arrays, enumeratedValue narrowing helper"
      contains: "'reminder-enable'"
    - path: "frontend/src/components/train/TrainScheduleSettings.tsx"
      provides: "Weekday, slider (debounced commit), reminder switch and hour tracking"
      contains: "useDebouncedTrackFeature('option-change')"
    - path: "frontend/src/components/filters/ImportFilterCard.tsx"
      provides: "TC toggle and backlog cap tracking"
      contains: "trackFeature('option-change'"
    - path: "frontend/src/components/settings/LeaderboardPrivacyCard.tsx"
      provides: "Legacy settings-change event for leaderboard-hidden"
      contains: "trackEvent('settings-change'"
    - path: "frontend/CLAUDE.md"
      provides: "Amended Umami skip rule"
      contains: "overwritten in place"
  key_links:
    - from: "frontend/src/components/train/TrainReminderButton.tsx"
      to: "frontend/src/lib/analytics.ts"
      via: "trackFeature('action', { target: 'reminder-enable', source, outcome }) after ensureDeviceSubscribed resolves and on the iOS tap"
      pattern: "target: 'reminder-enable'"
    - from: "frontend/src/components/train/TrainScheduleSettings.tsx"
      to: "frontend/src/hooks/useDebouncedTrackFeature.ts"
      via: "Slider onValueCommit -> debounced option-change"
      pattern: "onValueCommit"
    - from: "frontend/src/components/train/TrainScheduleSettings.tsx"
      to: "frontend/src/lib/analytics.ts"
      via: "WEEKDAY_CHIPS[].toggleTarget typed as TrainDayToggleTarget"
      pattern: "toggleTarget"
---

<objective>
Close the Umami tracking gaps on settings controls whose state is persisted server-side by overwriting a row in place (import settings, train schedule, reminder opt-in, leaderboard privacy). The table only holds the latest value, so change history, switch-offs and the reminder permission funnel are otherwise invisible.

Purpose: owner-approved analytics coverage (frontend only), all through the typed registry in frontend/src/lib/analytics.ts, so a wrong target or value stays a build error.
Output: registry entries, five instrumented components, tests that go red if any new call is removed, and an amended frontend/CLAUDE.md rule.

Ground rules for every task (from frontend/CLAUDE.md Umami section): register first, then call; reuse the 9 existing verbs (no new event names, FEATURE_EVENT_NAMES stays at 9); never rename existing events or targets (reminder-banner-dismiss stays untouched); fire only from user-initiated handlers or their async continuations, never from a useEffect, on mount, or on draft seeding; values are enumerated string-literal unions only.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@frontend/CLAUDE.md
@frontend/src/lib/analytics.ts
@frontend/src/hooks/useDebouncedTrackFeature.ts

Facts verified at planning time (HEAD 2e752f228, analytics.ts already includes quick 261004-rmc's umamiBeforeSend changes; plan against that):
- `FeatureEventMap.action` is currently `{ target: ActionTarget }` with no `value`; `trackFeature` spreads all props into the Umami payload as strings after `page`, so extra keys (`source`, `outcome`) reach Umami without changing trackFeature.
- `DeviceSubscribeResult['status']` in frontend/src/lib/push.ts is `'subscribed' | 'dismissed' | 'denied' | 'unsupported' | 'error'`. push.ts does not import analytics.ts.
- `GameCap` (frontend/src/hooks/useImportSettings.ts) is `1000 | 3000 | 5000`; useImportSettings does not import analytics.ts.
- `REMINDER_HOUR_OPTIONS` (push.ts) is `readonly number[]` covering 0..23. `PUZZLES_PER_SESSION_MIN/MAX/STEP` (TrainScheduleSettings.tsx) are 3/30/3.
- Analytics test pattern: real analytics module + `window.umami = { track, identify: vi.fn() }` stub in beforeEach, `delete window.umami` in afterEach, `window.history.pushState({}, '', '/train')` to fix `page` (see frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx around L438). SettingsPanel tests assert `trackEvent('settings-change', { setting, value })`.
- frontend/src/components/settings/__tests__/LeaderboardPrivacyCard.test.tsx currently has a test asserting NO event on flip (around L163); it must be inverted, not deleted.
- TrainScheduleSettings tests use REAL timers. The debounced slider hook flushes a pending event immediately on unmount, and collapsing the card (`btn-train-schedule-toggle`) unmounts the controls, so a collapse click (or RTL `cleanup()`) flushes deterministically without waiting SLIDER_TRACK_DEBOUNCE_MS.
- Page attribution: TrainScheduleSettings, the score screen and the banner render on /train (page `train`); ImportFilterCard renders on /library/import (page `library`, acceptable per owner).
</context>

<tasks>

<task type="tracer">
  <name>Task 1: Register every new target/value and wire the reminder-enable funnel end-to-end through the resurface banner</name>
  <files>frontend/src/lib/analytics.ts, frontend/src/lib/__tests__/analytics.test.ts, frontend/src/components/train/TrainReminderResurfaceBanner.tsx, frontend/src/components/train/__tests__/TrainReminderResurfaceBanner.test.tsx</files>
  <read_first>frontend/src/lib/analytics.ts (feature-event registry section), frontend/src/lib/push.ts (DeviceSubscribeResult), frontend/src/hooks/useImportSettings.ts (GameCap), frontend/src/components/train/TrainReminderResurfaceBanner.tsx, frontend/src/components/train/__tests__/TrainReminderResurfaceBanner.test.tsx, frontend/src/lib/__tests__/analytics.test.ts (L241-L400)</read_first>
  <behavior>
    - analytics.test: the kebab-case slug test also covers every new const array; FEATURE_EVENT_NAMES still has exactly 9 entries.
    - analytics.test: `enumeratedValue(TRAIN_PUZZLES_PER_SESSION_VALUES, 18)` returns '18'; `enumeratedValue(TRAIN_PUZZLES_PER_SESSION_VALUES, 4)` returns null; `enumeratedValue(REMINDER_HOUR_VALUES, 0)` returns '0' and 23 returns '23'.
    - analytics.test: `trackFeature('action', { target: 'reminder-enable', source: 'resurface-banner', outcome: 'denied' })` on /train calls window.umami.track with ('action', { page: 'train', target: 'reminder-enable', source: 'resurface-banner', outcome: 'denied' }).
    - Banner test: 'Turn on reminders' with ensureDeviceSubscribed resolving subscribed sends exactly one ('action', { page: 'train', target: 'reminder-enable', source: 'resurface-banner', outcome: 'subscribed' }).
    - Banner test: the denied mock sends outcome 'denied'; a rejected ensureDeviceSubscribed sends outcome 'error'; dismissed sends 'dismissed'.
    - Banner test: rendering alone sends nothing; 'Not now' still sends only the unchanged reminder-banner-dismiss event.
  </behavior>
  <action>
    Registry (frontend/src/lib/analytics.ts), all additions in this one task so later tasks only consume them:
    (a) Add type-only imports: `DeviceSubscribeResult` from '@/lib/push' and `GameCap` from '@/hooks/useImportSettings'.
    (b) New exported const arrays, each placed next to the registry list it feeds, with a one-line doc comment:
      IMPORT_TC_TOGGLE_TARGETS = 'import-tc-bullet', 'import-tc-blitz', 'import-tc-rapid', 'import-tc-classical' (as const, with a `satisfies` check against the template-literal type built from TimeControl so a new TC cannot silently drift);
      TRAIN_DAY_TOGGLE_TARGETS = 'train-day-mon' through 'train-day-sun' in Monday-first order (as const), plus exported type TrainDayToggleTarget;
      REMINDER_ENABLE_SOURCES = 'score-screen', 'resurface-banner', 'train-settings';
      REMINDER_ENABLE_OUTCOMES = 'subscribed', 'dismissed', 'denied', 'unsupported', 'error', 'install-instructions', typed by `satisfies` against ReminderEnableOutcome = DeviceSubscribeResult['status'] | 'install-instructions' (the outcome union derives from the source type per the registry convention; 'install-instructions' is the iOS tap, which never prompts);
      TRAIN_PUZZLES_PER_SESSION_VALUES = '3','6','9','12','15','18','21','24','27','30' (the slider grid as strings; comment that a test in TrainScheduleSettings.test.tsx pins it to PUZZLES_PER_SESSION_MIN/MAX/STEP);
      REMINDER_HOUR_VALUES = '0' through '23' (exact hour kept rather than coarse buckets: 24 bounded literals carry no PII, and the exact hour is the useful signal for reminder scheduling; comment that a test pins it to REMINDER_HOUR_OPTIONS).
    (c) TOGGLE_TARGETS: append the spread of IMPORT_TC_TOGGLE_TARGETS, the spread of TRAIN_DAY_TOGGLE_TARGETS, and 'train-reminder' (keep it `as const`; existing entries untouched and in place).
    (d) ACTION_TARGETS: append 'reminder-enable'. Replace `action: { target: ActionTarget }` in FeatureEventMap with a new ActionProps discriminated union: every other action target keeps the bare `{ target }` shape (via Exclude), and 'reminder-enable' requires `source: ReminderEnableSource` and `outcome: ReminderEnableOutcome`. Existing `trackFeature('action', { target: ... })` call sites must keep compiling unchanged.
    (e) OPTION_TARGETS: append 'import-cap', 'train-puzzles-per-session', 'train-reminder-hour'. Extend OptionChangeProps with: import-cap whose value is the template-literal string form of GameCap; train-puzzles-per-session whose value is the TRAIN_PUZZLES_PER_SESSION_VALUES element type; train-reminder-hour whose value is the REMINDER_HOUR_VALUES element type.
    (f) Export a small generic helper `enumeratedValue(values, n)`: given a readonly array of string literals and a number, return the literal equal to String(n), or null when the number is not in the list (callers send nothing on null). Explicit return type, no `any`.
    Do not add a new event name, do not rename anything, and do not touch the quick 261004-rmc beforeSend code.

    Banner (frontend/src/components/train/TrainReminderResurfaceBanner.tsx): in handleTurnOn, immediately after the awaited `ensureDeviceSubscribed(...).catch(...)` result is available and before the status branches, send one `action` event with target 'reminder-enable', source 'resurface-banner', outcome = the result's status. One line, no new branch. Leave handleDismiss and its reminder-banner-dismiss event exactly as they are.

    Tests: extend analytics.test.ts per the behavior list (add the six new arrays to the slug test's list; add an enumeratedValue test; add the reminder-enable trackFeature payload test inside the existing 'feature-event registry' describe, whose beforeEach already imports the module, never an `await import` inside a test body). In TrainReminderResurfaceBanner.test.tsx add a tracking describe with a window.umami stub and pushState('/train') in beforeEach, `delete window.umami` and pushState('/') in afterEach, reusing the file's existing mockResurface/mockPushCapability helpers and the existing ensureDeviceSubscribed mock. No per-file or per-test timeouts.

    Mutation proof (owner rule: each event needs a test that fails if the call is removed): temporarily delete the banner's new trackFeature line, run the banner test file, confirm the new tracking tests fail, restore the line.

    Commit: check `git branch --show-current` prints `main`, then commit with `feat(analytics): register settings tracking targets and track reminder opt-in on the resurface banner`.
  </action>
  <verify>
    <automated>npm --prefix frontend test -- --run src/lib/__tests__/analytics.test.ts src/components/train/__tests__/TrainReminderResurfaceBanner.test.tsx && npm --prefix frontend run build</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "'reminder-enable'" frontend/src/lib/analytics.ts` is at least 2 (ACTION_TARGETS entry + ActionProps member).
    - `grep -c "target: 'reminder-enable'" frontend/src/components/train/TrainReminderResurfaceBanner.tsx` equals 1.
    - `grep -c "reminder-banner-dismiss" frontend/src/components/train/TrainReminderResurfaceBanner.tsx` is unchanged from HEAD (still 1).
    - `grep -c "export function enumeratedValue" frontend/src/lib/analytics.ts` equals 1.
    - Build passes (tsc proves every existing trackFeature('action', ...) call site still type-checks against ActionProps).
  </acceptance_criteria>
  <done>The registry carries every new target/value union, the banner sends one reminder-enable event per Turn-on press with source and outcome, analytics and banner tests pass, the mutation check went red then green, and the commit is on main.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Track the score-screen reminder opt-in and every Train schedule control</name>
  <files>frontend/src/components/train/TrainReminderButton.tsx, frontend/src/components/train/__tests__/TrainReminderButton.test.tsx, frontend/src/components/train/TrainScheduleSettings.tsx, frontend/src/components/train/__tests__/TrainScheduleSettings.test.tsx</files>
  <read_first>frontend/src/components/train/TrainReminderButton.tsx (handleIosTap ~L185, handleClick ~L271), frontend/src/components/train/TrainScheduleSettings.tsx (WEEKDAY_CHIPS ~L123, ReminderControls ~L335, PuzzlesPerSessionControl ~L406, handlers ~L587-L626, chip onClick ~L682), frontend/src/components/analysis/EloSelector.tsx (L99-L114, the debounced onValueCommit precedent), the existing harness/helpers at the top of both test files (renderWithClient, stubBrowserGlobals, mockVapidConfigured, expandSchedule, advanceDebounce)</read_first>
  <behavior>
    - TrainReminderButton: 'Remind me' with a granted prompt and resolving subscribe sends ('action', { page: 'train', target: 'reminder-enable', source: 'score-screen', outcome: 'subscribed' }) exactly once; a denied prompt sends outcome 'denied'.
    - TrainReminderButton: the iOS-tabbed 'Get reminders' tap sends source 'score-screen', outcome 'install-instructions' (also when settings have not loaded yet).
    - TrainScheduleSettings: after settings load and the card is expanded, no event other than the expand's existing panel-open has fired (mount/seed sends nothing).
    - Clicking the Fr chip when Friday is off sends ('toggle', { page: 'train', target: 'train-day-fri', value: 'on' }); clicking the Mo chip when Monday is on sends value 'off'.
    - Two ArrowRight presses on the puzzles slider from 12 send exactly ONE ('option-change', { page: 'train', target: 'train-puzzles-per-session', value: '18' }) once the pending event is flushed (collapse the card or cleanup), and none before the flush.
    - Reminder switch ON with a granted prompt sends ('toggle', { ..., target: 'train-reminder', value: 'on' }) and ('action', { ..., target: 'reminder-enable', source: 'train-settings', outcome: 'subscribed' }); with a denied prompt the action outcome is 'denied'; switching OFF from reminder_enabled true sends toggle value 'off' and no reminder-enable action.
    - Picking hour 9 sends ('option-change', { ..., target: 'train-reminder-hour', value: '9' }).
    - Drift guard: TRAIN_PUZZLES_PER_SESSION_VALUES equals the grid generated from PUZZLES_PER_SESSION_MIN..MAX by STEP (as strings), and REMINDER_HOUR_VALUES equals REMINDER_HOUR_OPTIONS mapped to strings.
  </behavior>
  <action>
    TrainReminderButton (frontend/src/components/train/TrainReminderButton.tsx), uses the Task 1 registry:
    - handleIosTap: as its FIRST statement (before the `data === undefined` early return, so both paths count) send `action` target 'reminder-enable', source 'score-screen', outcome 'install-instructions'. The iOS tap never prompts; the instructions reveal unconditionally, so that is the outcome.
    - handleClick: immediately after the awaited ensureDeviceSubscribed result, before the status branches, send `action` target 'reminder-enable', source 'score-screen', outcome = result status. The later save() success/failure is not part of the outcome (save errors already reach Sentry through the global MutationCache handler).

    TrainScheduleSettings (frontend/src/components/train/TrainScheduleSettings.tsx), all from user handlers, never from the seed effect or the debounced-save effect:
    - WEEKDAY_CHIPS: add a `toggleTarget: TrainDayToggleTarget` field to the WeekdayChip interface and set it explicitly per chip (bit 0 'train-day-mon' through bit 6 'train-day-sun'), keeping the Monday=0 bit convention comment intact.
    - Extract the inline chip onClick into a named handler (e.g. handleWeekdayToggle(chip)) in the component body: read the chip's current state from the render's draft (draft non-null and bit set), keep the existing hasEditedRef + functional setDraft XOR update, and send `toggle` with chip.toggleTarget and onOff of the NEW state (the negation of the current one).
    - PuzzlesPerSessionControl: call useDebouncedTrackFeature('option-change') inside this component (EloSelector precedent) and pass an onValueCommit handler to the Slider that narrows the committed value with enumeratedValue(TRAIN_PUZZLES_PER_SESSION_VALUES, n) and schedules target 'train-puzzles-per-session' only when the result is non-null. onValueChange stays untouched and undebounced (frontend/CLAUDE.md slider rule). Update its docstring: tracking happens on commit, debounced per burst.
    - handleReminderToggle: as its first statement send `toggle` target 'train-reminder' with onOff(checked), the user's requested state (pairs with switch-offs, which are otherwise lost). In the ensureDeviceSubscribed `.then` continuation, right after setSubscribing(false), send `action` target 'reminder-enable', source 'train-settings', outcome = result status. Rationale to put in a short comment: desktop has no score-screen 'Remind me' button, so the settings switch is the only desktop opt-in path and the funnel would be blind to desktop without it. Do not move or alter the D-09 toggle-ON exception logic.
    - handleReminderHourChange: narrow the hour with enumeratedValue(REMINDER_HOUR_VALUES, hour) and send `option-change` target 'train-reminder-hour' when non-null, alongside the existing draft update. ReminderControls stays presentational.
    - Keep every function at nesting depth 4 or less (eslint max-depth gate); the component body must not gain nested conditionals (complexity is report-only but already near 15, so prefer the extracted handler shapes above).

    Tests: add a tracking describe to each test file (window.umami stub + pushState('/train') in beforeEach, `delete window.umami` + pushState('/') in afterEach), reusing the existing helpers and browser-global stubs for each scenario in the behavior list. For the slider, keep the file's REAL timers: after the keyDowns assert nothing was tracked yet, then click btn-train-schedule-toggle to collapse (unmounts the slider and flushes the debounced event) and assert exactly one option-change. Put the drift-guard test in TrainScheduleSettings.test.tsx (it already imports the component module's constants; import REMINDER_HOUR_OPTIONS from '@/lib/push'). No `await import` inside test bodies, no per-file or per-test timeouts.

    Mutation proof: temporarily delete (one at a time) the handleClick reminder-enable call in TrainReminderButton and the weekday toggle call in TrainScheduleSettings, run the matching test file, confirm the new tests fail, restore.

    Commit: check `git branch --show-current` prints `main`, then commit with `feat(analytics): track score-screen reminder opt-in and train schedule settings`.
  </action>
  <verify>
    <automated>npm --prefix frontend test -- --run src/components/train/__tests__/TrainReminderButton.test.tsx src/components/train/__tests__/TrainScheduleSettings.test.tsx src/components/train/__tests__/TrainStartScreen.test.tsx && npm --prefix frontend run lint && npm --prefix frontend run build</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "target: 'reminder-enable'" frontend/src/components/train/TrainReminderButton.tsx` equals 2.
    - `grep -c "target: 'reminder-enable'" frontend/src/components/train/TrainScheduleSettings.tsx` equals 1.
    - `grep -c "useDebouncedTrackFeature('option-change')" frontend/src/components/train/TrainScheduleSettings.tsx` equals 1 and `grep -c "onValueCommit" frontend/src/components/train/TrainScheduleSettings.tsx` is at least 1.
    - `grep -c "toggleTarget: 'train-day-" frontend/src/components/train/TrainScheduleSettings.tsx` equals 7.
    - `grep -c "trackFeature" frontend/src/components/train/TrainScheduleSettings.tsx` is at least 5 (existing panel-open + weekday + switch toggle + funnel + hour).
    - lint (max-depth) and build pass.
  </acceptance_criteria>
  <done>Score-screen and settings opt-ins report source and outcome, every schedule control sends its typed event from user handlers only, the slider sends one event per burst, the drift guard pins both value arrays to their sources, mutation checks went red then green, and the commit is on main.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Track import filters and leaderboard privacy, amend the Umami rule, run the full frontend gate</name>
  <files>frontend/src/components/filters/ImportFilterCard.tsx, frontend/src/components/filters/__tests__/ImportFilterCard.test.tsx, frontend/src/components/settings/LeaderboardPrivacyCard.tsx, frontend/src/components/settings/__tests__/LeaderboardPrivacyCard.test.tsx, frontend/CLAUDE.md</files>
  <read_first>frontend/src/components/filters/ImportFilterCard.tsx (handleToggleTc ~L80, handleCapChange ~L89), frontend/src/components/filters/__tests__/ImportFilterCard.test.tsx (mockSettings/mockUpdateMutation helpers, BASE_SETTINGS), frontend/src/components/settings/LeaderboardPrivacyCard.tsx, frontend/src/components/settings/__tests__/LeaderboardPrivacyCard.test.tsx (L163 no-event test), frontend/src/components/settings/SettingsPanel.tsx (L130-L133 handleSoundChange), frontend/CLAUDE.md (Feature events, 'Skip what the URL or database already says' bullet)</read_first>
  <behavior>
    - ImportFilterCard on /library/import: clicking the inactive Bullet button sends ('toggle', { page: 'library', target: 'import-tc-bullet', value: 'on' }); clicking an active TC (with another TC still active) sends value 'off'.
    - Clicking the only remaining active TC (guard no-op) sends nothing and calls no mutate.
    - Clicking cap 3000 when 1000 is stored sends ('option-change', { page: 'library', target: 'import-cap', value: '3000' }); re-tapping the active cap (Radix emits '') sends nothing.
    - Rendering the card sends nothing.
    - LeaderboardPrivacyCard: flipping the switch on sends exactly one ('settings-change', { setting: 'leaderboard-hidden', value: 'on' }) via window.umami.track (the old no-event test is inverted); flipping off from a hidden profile sends value 'off'.
  </behavior>
  <action>
    ImportFilterCard (frontend/src/components/filters/ImportFilterCard.tsx):
    - handleToggleTc: after the last-one-standing guard and alongside the mutate call, send `toggle` with target built as the template literal 'import-tc-' + tc (contextually typed against IMPORT_TC_TOGGLE_TARGETS; if tsc does not narrow the template literal, add a typed Record from TimeControl to the import-tc target instead of casting) and onOff of the NEW state (not currentlyActive).
    - handleCapChange: after the empty-value guard and the mutate call, send `option-change` target 'import-cap' with the cap as its template-literal string form (typed by Task 1's GameCap-derived union, no cast to string).

    LeaderboardPrivacyCard (frontend/src/components/settings/LeaderboardPrivacyCard.tsx):
    - Extract the Switch's onCheckedChange into a named handler that calls mutation.mutate(next) and then trackEvent('settings-change', { setting: LEADERBOARD_HIDDEN_SETTING_ID, value: next ? 'on' : 'off' }), matching SettingsPanel's handleSoundChange exactly (legacy event, legacy trackEvent, D-05). LEADERBOARD_HIDDEN_SETTING_ID is a module constant 'leaderboard-hidden' (do not add it to engineSettings' SettingId, which is the localStorage settings registry). Import trackEvent from '@/lib/analytics'.
    - Rewrite the component docstring sentence that says the switch sends no Umami event: it now sends the legacy settings-change event because the profile row is overwritten in place and switch-offs would otherwise be lost (quick 261004-rre).

    Tests: ImportFilterCard.test.tsx gets a tracking describe (window.umami stub, pushState('/library/import') in beforeEach; `delete window.umami` and pushState('/') in afterEach) using the existing mockSettings/mockUpdateMutation helpers for each behavior case. In LeaderboardPrivacyCard.test.tsx invert the existing no-event test into the 'on' assertion (rename it so the title describes the event) and add the 'off' case; keep its existing umami stub/unstub pattern.

    Docs (frontend/CLAUDE.md, Feature events section, the 'Skip what the URL or database already says' bullet): replace its last sentence so it says a handler whose whole effect creates a row (train retry, bookmark save) stays un-evented because the row is DB-known, while settings rows overwritten in place (import settings, train schedule, reminder and privacy toggles) do get an event, since the table keeps only the latest value and change history and switch-offs would otherwise be lost. One or two sentences, include the literal phrase 'overwritten in place', at most one em-dash, no other edits to the file.

    Mutation proof: temporarily delete the handleCapChange trackFeature call and the LeaderboardPrivacyCard trackEvent call (one at a time), run the matching test file, confirm failure, restore.

    Full frontend gate (owner's verification set, from frontend/): lint, build, the whole test suite, knip. Never run prettier (frontend has none). Fix any failure, including knip flagging an unused new export (export only what another module or a test imports; arrays used in-file to derive types are already covered by ignoreExportsUsedInFile).

    Commits: check `git branch --show-current` prints `main` before each. Code + tests: `feat(analytics): track import filter and leaderboard privacy settings`. Docs: `docs(frontend): event in-place settings rows, keep row-creating writes un-evented`.
  </action>
  <verify>
    <automated>npm --prefix frontend run lint && npm --prefix frontend run build && npm --prefix frontend test -- --run && npm --prefix frontend run knip</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "trackFeature('toggle'" frontend/src/components/filters/ImportFilterCard.tsx` equals 1 and `grep -c "trackFeature('option-change'" frontend/src/components/filters/ImportFilterCard.tsx` equals 1.
    - `grep -c "trackEvent('settings-change'" frontend/src/components/settings/LeaderboardPrivacyCard.tsx` equals 1.
    - `grep -c "overwritten in place" frontend/CLAUDE.md` equals 1.
    - Full lint + build + test suite + knip pass with zero failures.
    - `git log --oneline -4` shows the task commits on main and `git status --porcelain` is empty.
  </acceptance_criteria>
  <done>Import TC/cap and leaderboard privacy changes send their typed events, the rule in frontend/CLAUDE.md distinguishes row-creating writes from in-place settings, the full frontend gate is green, and all commits are on main.</done>
</task>

</tasks>

<threat_model>
ASVS level 1, block on high (workflow.security_asvs_level=1, security_block_on=high).

## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| browser -> Umami collector | Client-built event payloads leave the app; anything put in props is stored in Umami event data and joined to users.id (Phase 229 identity) |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-rre-01 | Information disclosure | New trackFeature props (source, outcome, import-tc/train-day/train-reminder toggles, import-cap, train-puzzles-per-session, train-reminder-hour) | medium | mitigate | Every value is a string-literal union in FeatureEventMap (D-04); numbers pass through enumeratedValue and send nothing when off-grid, so no free text, id, FEN or username can be expressed and tsc fails the build on anything else |
| T-rre-02 | Information disclosure | settings-change leaderboard-hidden event (legacy trackEvent, untyped Record) | low | mitigate | Call site sends only the constant setting id and an 'on'/'off' ternary; test asserts the exact payload. The flag already lives in the users table, and Umami is first-party analytics joined by the same users.id, so no new party learns it |
| T-rre-03 | Information disclosure | Events on excluded routes (/admin, /activity, auth) | low | mitigate | All new feature events go through trackFeature, whose D-14 isTrackingExcludedPath gate is unchanged; none of the instrumented components render on excluded routes |
| T-rre-04 | Tampering | Client-side event forgery | low | accept | Analytics events are client-controlled by nature and drive no server behavior or authorization |
| T-rre-SC | Tampering | npm/pip/cargo installs | high | accept | Not applicable: this plan installs no packages; any install would require the package-legitimacy gate |
</threat_model>

<verification>
- `npm --prefix frontend run lint && npm --prefix frontend run build && npm --prefix frontend test -- --run && npm --prefix frontend run knip` passes.
- Each new call site was proven load-bearing by a remove-and-rerun mutation check (red, then restored green).
- `git branch --show-current` is `main` and the working tree is clean.
</verification>

<success_criteria>
- reminder-enable funnel covers score screen (incl. iOS tap), resurface banner and the settings switch, each with enumerated source and outcome.
- Import TC toggles, backlog cap, weekday chips, puzzles slider (debounced commit), reminder switch, reminder hour and leaderboard privacy each send exactly one typed event per user change and nothing on mount.
- No new event name, no renamed event or target, FEATURE_EVENT_NAMES still 9.
- frontend/CLAUDE.md skip rule amended.
</success_criteria>

<output>
Create `.planning/quick/261004-rre-track-umami-events-for-server-persisted-/261004-rre-SUMMARY.md` when done
</output>
