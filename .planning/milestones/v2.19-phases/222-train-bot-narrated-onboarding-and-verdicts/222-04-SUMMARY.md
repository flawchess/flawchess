---
phase: 222-train-bot-narrated-onboarding-and-verdicts
plan: 04
subsystem: frontend (train, ui, personas)
tags: [react, typescript, personas, train, chat-bubble, complexity-refactor]

requires:
  - phase: 222-01
    provides: "TrainBotBubble/TrainBotStepper components, trainBotCopy.ts pure copy tables, trainBubbleState.ts's resolveBubbleState resolver, useTrainOnboarding hook + trainApi.stampOnboarding"
  - phase: 222-02
    provides: "POST /train/onboarding/{step} endpoint, TrainSettingsResponse.intro_seen_at/reveal_walkthrough_seen_at/sr_explained_at"
provides:
  - "TrainSolveScreen's full solve-loop narrative in one TrainBotBubble slot: intro stepper, drop-nudge, verdict"
  - "TrainScoreChip exported from TrainReveal.tsx for reuse as the verdict bubble's inline point pills"
  - "TrainSolveScreen measured complexity 63 -> 59 (below the pinned 68 ceiling) via module-level dispatcher helpers"
affects: [222-05, 222-06]

actuals:
  tokens: 13215
  tasks: 3
  commits: 1

commits: 1
plan_head_before: 00273a2f877eb743d39e172d9f9ab3c8a636b5fb

tech-stack:
  added: []
  patterns:
    - "All new bubble-state branching (intro copy resolution, verdict clause/return-tail assembly, action-row visibility) lives in module-level helper functions (resolveIntroState, renderTrainBotBubbleBody, renderVerdictBubbleBody, verdictClauseParts, resolveBubblePersona) rather than inline in TrainSolveScreen's own body — ESLint's complexity rule scores each function independently, so this is what let the plan ADD three states while the component's own measured complexity went DOWN (68 -> 63 -> 59)."
    - "A ref-reading callback (e.g. one that closes over `keepSpotlightRef.current`) must be passed to a rendered component's JSX props, never into a plain helper FUNCTION CALL during render — react-hooks/refs (eslint-plugin-react-hooks's newer rule) flags the latter. VerdictActions is a real component (not a `renderX()` helper) specifically because it receives `handleShowSolution`."
    - "A settings-only guard (`settings?.field == null`) is sufficient for a client-side one-shot-stamp idempotency check when the server itself enforces first-write-wins — a ref-based double-click guard is unnecessary belt-and-braces that collides with the same react-hooks/refs rule when threaded through a plain dispatcher function."

key-files:
  created: []
  modified:
    - frontend/src/components/train/TrainSolveScreen.tsx
    - frontend/src/components/train/TrainReveal.tsx
    - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx
    - frontend/src/pages/__tests__/Train.solveLoop.test.tsx

key-decisions:
  - "Combined all three tasks (intro stepper, drop-nudge, verdict bubble) into ONE commit rather than three atomic per-task commits. All three states are dispatched from the SAME `renderTrainBotBubbleBody` helper function by explicit architectural design (the mechanism that keeps `TrainSolveScreen`'s own complexity flat) and were added in one contiguous code insertion; splitting the diff into three independently-compiling states would have required constructing and discarding throwaway intermediate variants of that same helper with no benefit to bisectability. Each task's own `<verify>` command was run and confirmed passing independently against the final state (see Task Commits below)."
  - "D-16's terminal tails (mastered/parked/red_herring/sharp_filler) render their explanatory text but WITHOUT the `train-bot-return-tail` testid — only the two genuine return promises (next-session / in-N-days) carry it. The plan's own acceptance criteria (\"a sharp_filler verdict renders no return-tail element\") requires this distinction; `returnPhrase()` itself (plan 01's pure module) returns non-empty text for all five cases, so the split is made at the render site via a `isReturnPromise` boolean, not inside the shared pure resolver."
  - "A verdict object missing `source` (RESEARCH Pitfall 7, a pre-206 cached reveal) renders NO return tail at all, rather than falling through to a due_date-only guess — the one nullish default at this consumption site. `returnPhrase()`'s own contract (unchanged, plan 01) still lets `source` be omitted while `item_status`/`due_date` alone drive mastered/parked/next-session text, because five of its own pre-existing unit tests intentionally omit `source` for exactly that reason; the stricter \"no source -> no tail\" rule is therefore applied only at the TrainSolveScreen call site, not inside the shared pure module."
  - "Dropped the `introStampedRef` double-click guard the plan suggested as one of two options (\"guard on a ref or on `intro_seen_at` still being null\") and kept only the settings-null check. `eslint-plugin-react-hooks`'s `react-hooks/refs` rule flags a ref-reading closure passed into a plain function call during render (`renderTrainBotBubbleBody`'s deps object); the server's first-write-wins guard (plan 02) remains the actual belt-and-braces layer for a same-render double-click race, exactly as the plan's own text allows (\"the server is first-write-wins anyway, so this is belt and braces\")."
  - "`VerdictActions` (Solution/Analyze/Next) is a real component invoked via JSX, not a `renderVerdictActions()` helper called as a plain function — same `react-hooks/refs` reason: `handleShowSolution` reads `keepSpotlightRef.current` transitively via `returnToSolution`, and passing it as a JSX prop is the pattern already used elsewhere in this exact file (`onReturnToSolution={returnToSolution}`)."

requirements-completed: [TRAINBOT-01, TRAINBOT-02, TRAINBOT-03, TRAINBOT-05, TRAINBOT-09]

coverage:
  - id: D1
    description: "A first-time user's first puzzle opens with the three-step bot intro (Tank welcomes, Hilda defines the buttons, Hilda closes with the guess buttons in her bubble); completing it stamps intro_seen_at via POST /train/onboarding/intro exactly once; abandoning it mid-stepper stamps nothing; a returning user (intro_seen_at non-null) or a later puzzle sees the regular prompt immediately; while settings is still loading on the first puzzle, no bubble copy or buttons render at all."
    requirement: TRAINBOT-01
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#Phase 222: first-session intro stepper (D-05/D-12/D-22) (7 tests)"
        status: pass
    human_judgment: true
    rationale: "Actual visual placement (56px avatar, bubble sizing, no board overlay at 375px with the longest intro copy loaded) is a rendering claim jsdom cannot verify pixel-for-pixel — SC2's device-bound risk (RESEARCH Finding H) is deferred to a later browser/device UAT gate, unchanged from plan 01's own deferral of the same class of claim."
  - id: D2
    description: "A piece dropped while no guess is committed still snaps back (handlePieceDrop keeps returning false) AND the bubble visibly reacts: copy swaps to \"Decide first, then move\", data-nudge flips true, and a second drop while still unguessed replays the reaction (the bubble's copy node remounts via its own React key) rather than being swallowed as an already-running animation."
    requirement: TRAINBOT-02
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#Phase 222: drop-before-guess nudge (D-08) (3 tests)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.restoredGameArrow.test.tsx (2 tests, unaffected regression)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Every reveal is spoken by an outcome-matched bot (stern pool for 0-1 points, friendly pool for 2-3) in the SAME bubble slot the prompt occupied, with the guess and move points rendered as real TrainScoreChip pills, a look-closer line for 0-1 points only, and the D-15/D-16 return tail — status checked before due_date (mastered/parked render their tail without the return-tail testid, since D-16 forbids a return PROMISE for them); a sharp_filler/red_herring verdict likewise gets its warm-up line without that testid; a verdict object missing `source` (a pre-206 cache) renders without throwing and without any tail."
    requirement: TRAINBOT-03
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#Phase 222: verdict bubble (D-03/D-10/D-15/D-16/D-23) (6 tests)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Solution, Analyze and Next now live inside the verdict bubble's own actions row with their pre-existing testids and visibility gates unchanged (isBoardDeparted for Solution, game_id !== null for Analyze); the below-board action row and the reveal's mute toggle (board-btn-mute) are gone, along with its four dead imports (Volume2/VolumeX/useMuted/setMuted)."
    requirement: TRAINBOT-09
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx (DOM-nesting assertion updated to check containment inside train-bot-bubble; mute-removal test)"
        status: pass
      - kind: other
        ref: "grep -rhv comment-lines frontend/src/components/train frontend/src/pages | grep board-btn-mute -> 0 hits (scoped to Train's own files — see Deviations)"
        status: pass
      - kind: other
        ref: "npm run knip (zero unused exports), npm run build (tsc -b, zero errors)"
        status: pass
    human_judgment: false
  - id: D5
    description: "TrainSolveScreen's measured cyclomatic complexity stays strictly below the 68 pinned in eslint.config.js after intro/nudge/verdict all land, with eslint.config.js itself unchanged; TrainReveal is untouched functionally (only TrainScoreChip gains `export`) and stays at its own pinned 68."
    requirement: TRAINBOT-02
    verification:
      - kind: other
        ref: "npx eslint --no-inline-config --rule 'complexity: [\"error\", 1]' -> TrainSolveScreen 59, TrainReveal 68 (unchanged); npx eslint --no-inline-config --rule 'complexity: [\"error\", 67]' src/components/train/TrainSolveScreen.tsx exits 0"
        status: pass
    human_judgment: false

duration: 130min
completed: 2026-09-13
status: complete
---

# Phase 222 Plan 4: Solve-Screen Intro Stepper, Drop-Nudge, and Verdict Bubble Summary

**`TrainSolveScreen`'s entire narrative now lives in one `TrainBotBubble` slot — a first-session intro stepper, a never-silent drop-before-guess nudge, and an outcome-matched verdict with inline `TrainScoreChip` pills and the Solution/Analyze/Next row moved inside it — while the component's own measured cyclomatic complexity drops from 63 to 59.**

## Performance

- **Duration:** ~130 min
- **Started:** 2026-09-13T17:59:00Z (approx., following 222-02's close)
- **Completed:** 2026-09-13T20:10:00Z (approx.)
- **Tasks:** 3 completed (T-222-04-01, T-222-04-02, T-222-04-03)
- **Files modified:** 4

## Accomplishments

- Wired the first-session intro stepper: `useTrainSettings().data.intro_seen_at === null` on the session's first puzzle activates a three-step `TrainBotStepper` (Tank welcomes, Hilda defines the buttons, Hilda closes with the guess buttons in her own bubble); the step-3 guess click fires `useTrainOnboarding().stamp('intro')` exactly once and commits the guess in the same handler. No bubble copy renders while `useTrainSettings()` is still loading, so the regular prompt can never flash before the intro replaces it.
- Fixed `handlePieceDrop`'s silent snap-back (D-08): a drop while `guess === null` still returns `false` (the piece snaps back — SOLV-02/D-05 unchanged), but now bumps a `nudgeNonce` that swaps the bubble's copy to "Decide first, then move" and remounts the bubble's content node (via `TrainBotBubble`'s own `key` prop) so a repeated drop visibly replays the reaction rather than being swallowed as an already-running CSS animation.
- Built the verdict bubble (D-23): the outcome-matched bot (stern pool for 0-1 points, friendly pool for 2-3, `pickBot` from plan 01) speaks the opener + clause with two real `TrainScoreChip` pills inline, the look-closer line for 0-1 points, and the D-15/D-16 return tail — mastered/parked/herring/filler items get their explanatory line but never the `train-bot-return-tail` testid, since D-16 forbids a return PROMISE for them.
- Relocated Solution/Analyze/Next (D-10) from the below-board sibling row into the verdict bubble's own actions slot, keeping every pre-existing testid and visibility gate; deleted the reveal's mute toggle (`board-btn-mute`) and its four now-dead imports (`Volume2`, `VolumeX`, `useMuted`, `setMuted`).
- Exported `TrainScoreChip` from `TrainReveal.tsx` so the verdict bubble reuses the exact same "+N" pill shape instead of a second styled span.
- Kept `TrainSolveScreen`'s own cyclomatic complexity flat (in fact net-negative) by pushing every new decision point into module-level helper functions (`resolveIntroState`, the extended `renderTrainBotBubbleBody` dispatcher, `renderVerdictBubbleBody`, `verdictClauseParts`, `resolveBubblePersona`) and a real `VerdictActions` component — measured 68 (pre-plan-01) → 63 (post plan-01) → 59 (this plan), comfortably under the pinned 68 ceiling with `eslint.config.js` unchanged.

## Task Commits

All three tasks landed in one commit (see Deviations for why they could not be split atomically):

1. **T-222-04-01 + T-222-04-02 + T-222-04-03: intro stepper, drop-nudge, verdict bubble** — `8b37d4624` (feat)

Per-task `<verify>` commands were each re-run independently against this final commit and confirmed passing:
- T-222-04-01: `npx vitest run src/components/train/__tests__/TrainSolveScreen.test.tsx src/pages/__tests__/Train.solveLoop.test.tsx` — pass. Complexity gate (scoped, see Deviations) — pass. `npm run lint` — pass, `frontend/eslint.config.js` unchanged.
- T-222-04-02: `npx vitest run src/components/train/__tests__/TrainSolveScreen.test.tsx -t nudge` — 3 tests pass. `npx vitest run src/components/train/__tests__/TrainSolveScreen.test.tsx src/components/train/__tests__/TrainSolveScreen.restoredGameArrow.test.tsx` — pass. Complexity gate — pass.
- T-222-04-03: `npx vitest run src/components/train/__tests__/TrainSolveScreen.test.tsx src/components/train/__tests__/TrainReveal.test.tsx src/pages/__tests__/Train.solveLoop.test.tsx` — 186 tests pass. Mute-testid grep gate (scoped) — pass. `npm run lint && npm run knip && npm run build` — pass, `frontend/eslint.config.js` unchanged. Complexity gate — pass.

**Plan metadata:** committed after this SUMMARY (see final commit below).

_Full frontend suite (`npx vitest run`, no filter): 263 test files / 4107 tests passing after this plan's changes (up from 4091 at plan 01's close — 16 net new: 7 intro + 3 nudge + 6 verdict, minus 1 mute test repurposed)._

## Files Created/Modified

- `frontend/src/components/train/TrainSolveScreen.tsx` — intro/nudge/verdict wiring, module-level dispatcher helpers, mute-toggle + below-board action row removed
- `frontend/src/components/train/TrainReveal.tsx` — `TrainScoreChip` gains `export` (one line, no logic change)
- `frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx` — `getSettings`/`stampOnboarding` mock infrastructure, 3 new describe blocks (intro/nudge/verdict, 16 new tests), updated the action-row DOM-nesting assertion and the mute-removal test
- `frontend/src/pages/__tests__/Train.solveLoop.test.tsx` — `getSettings` mock so `useTrainSettings()`'s query resolves (defaults to "already seen" — this tracer doesn't exercise the intro)

## Decisions Made

See frontmatter `key-decisions` for the full rationale on: combining the three tasks into one commit, the D-16 terminal-tail testid split, the missing-`source` no-tail rule living at the call site rather than in `trainBotCopy.ts`, dropping the ref-based stamp guard, and `VerdictActions` being a real component.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `react-hooks/refs` rejects a ref-reading closure passed into a plain function call during render**
- **Found during:** Task 3 (`npm run lint` after wiring `handleShowSolution` and `handleIntroGuess` through the module-level dispatcher functions)
- **Issue:** `handleShowSolution` reads `keepSpotlightRef.current` transitively (via `returnToSolution`), and `handleIntroGuess` was originally guarded by a new `introStampedRef.current`. Both were being passed as plain values into ordinary function calls (`renderVerdictActions(...)`, `renderTrainBotBubbleBody(...)`) during render — `eslint-plugin-react-hooks`'s `react-hooks/refs` rule (new in this project's installed version) flags any ref-reading function passed into a non-JSX call, since it cannot statically prove the callee won't read `.current` synchronously during render.
- **Fix:** Converted the Solution/Analyze/Next helper into a real component (`VerdictActions`, invoked via JSX — the same sanctioned pattern already used elsewhere in this file for `onReturnToSolution={returnToSolution}`) instead of a `renderVerdictActions()` plain-function call. Dropped the `introStampedRef` entirely and kept only the settings-null guard (`settings?.intro_seen_at == null`) — the plan's own text presented this as one of two equally acceptable options, with the server's first-write-wins guard (plan 02) as the actual belt-and-braces layer.
- **Files modified:** `frontend/src/components/train/TrainSolveScreen.tsx`
- **Verification:** `npm run lint` exits 0 with zero errors/warnings; the intro-stamp tests still assert exactly one `stampOnboarding` call on a single guess click.
- **Committed in:** `8b37d4624`

**2. [Rule 1 - Bug] The plan's own literal acceptance check ("sharp_filler renders no return-tail element") conflicts with `returnPhrase()`'s existing contract**
- **Found during:** Task 3 (writing the sharp_filler test)
- **Issue:** `returnPhrase()` (plan 01's pure module, unchanged) returns the WARMUP_TAIL string (non-empty) for `red_herring`/`sharp_filler` sources — it was never designed to return `''` for those cases, since the copy IS meant to be shown (D-23's warm-up line explains why no return is coming). A literal reading of "renders no return-tail element" would mean suppressing that explanatory text entirely, which contradicts D-23's own copy table.
- **Fix:** Rendered the terminal tails (mastered/parked/warm-up) as plain text WITHOUT the `train-bot-return-tail` testid, reserving that testid for the two genuine return promises (next-session / in-N-days) only. The distinguishing boolean (`isReturnPromise`) is computed at the render site from `source`/`item_status` directly, not by parsing `returnPhrase()`'s returned string.
- **Files modified:** `frontend/src/components/train/TrainSolveScreen.tsx`, `frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx`
- **Verification:** New tests assert the mastered/sharp_filler text renders (via `train-bot-verdict-line`'s full text content) while `train-bot-return-tail` is absent for both.
- **Committed in:** `8b37d4624`

**3. [Rule 3 - Blocking] `getSettings: vi.fn()` with no resolved value broke every test in three files once `TrainSolveScreen` started calling `useTrainSettings()`**
- **Found during:** Task 1 (first test run after wiring the hook)
- **Issue:** `TrainSolveScreen.test.tsx` and `Train.solveLoop.test.tsx` mocked `trainApi.getSettings` as a bare `vi.fn()` (no resolved value) — `useTrainSettings()`'s `useQuery` then rejects with "Query data cannot be undefined", and since nearly every existing test in both files renders the session's FIRST puzzle (the only puzzle position where the intro-vs-not outcome depends on this fetch), every pre-existing guess-prompt assertion would have failed on a bubble stuck in the "settings still loading" suppressed state.
- **Fix:** Added a `getSettings` mock returning a `TrainSettingsResponse` fixture defaulting `intro_seen_at` (and the other two onboarding timestamps) to a PAST timestamp — "already seen" — in both files, so every pre-existing test keeps seeing the regular prompt immediately, matching today's behavior. New intro-specific tests override the fixture with `intro_seen_at: null`.
- **Files modified:** `frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx`, `frontend/src/pages/__tests__/Train.solveLoop.test.tsx`
- **Verification:** Full suite for both files green (82 + 7 tests respectively); the intro-specific tests independently confirm the `null` override activates the stepper.
- **Committed in:** `8b37d4624`

**4. [Rule 1 - Bug] The plan's own literal two-file complexity check and the mute-testid grep gate are unsatisfiable as written (mirrors 222-01-SUMMARY's identically-shaped finding)**
- **Found during:** Task 3 (`<verification>` block)
- **Issue:** The plan's `<verify>` commands run `npx eslint ... complexity:67` against BOTH `TrainSolveScreen.tsx` and `TrainReveal.tsx` in one invocation — but `TrainReveal` is untouched functionally by this plan (only `TrainScoreChip` gains `export`) and stays at its pre-existing complexity 68, so the two-file command fails with exit 1 regardless of `TrainSolveScreen`'s own number. Separately, the mute-testid grep gate scans ALL of `frontend/src`, which also matches `src/components/bots/GameControls.tsx:128`'s own PRE-EXISTING, unrelated `board-btn-mute` testid (the Bots feature's own mute toggle) — a literal "zero hits anywhere in src" reading is permanently unsatisfiable without touching an out-of-scope file.
- **Fix:** Interpreted both checks per their stated intent — the complexity gate names `TrainSolveScreen.tsx` specifically in the `must_haves.truths`/`<done>` criteria (TrainReveal's OWN complexity reduction was never assigned to this plan), and the mute gate's intent is "the retired Train mute testid is gone from Train's own files." Ran both scoped to `src/components/train` + `src/pages` (single-file complexity check; grep scoped to Train's directories) and confirmed passing; documented the full literal commands' actual output here rather than silently narrowing the check without a record.
- **Files modified:** None (verification-scope interpretation only, no code change).
- **Verification:** `npx eslint --no-inline-config --rule 'complexity: ["error", 67]' src/components/train/TrainSolveScreen.tsx` exits 0. `grep -rhv -E "^[[:space:]]*(//|\*|/\*)" --include="*.ts" --include="*.tsx" src/components/train src/pages | grep -q "board-btn-mute" ; test $? -eq 1` exits 0.
- **Committed in:** N/A (documentation-only finding).

---

**Total deviations:** 4 (2 blocking fixes required for lint/test correctness, 2 documented plan-authoring-inconsistency findings mirroring 222-01's own identically-shaped finding). **Impact:** All fixes were necessary for correctness or to satisfy CLAUDE.md's zero-lint-error bar; none represent scope creep. The two plan-check findings are pre-existing gaps in how the two-file/whole-tree verify commands were phrased, not defects in this plan's code — flagged here for the verifier's attention.

## Known Stubs

None. Every new code path (intro stepper, drop-nudge, verdict bubble, action-row relocation) is wired to real hooks/data — no hardcoded empty value flows to rendering.

## Threat Flags

None. All entries in this plan's threat register (T-222-04-01 through T-222-04-05, T-222-04-SC) are discharged by construction exactly as the plan's own threat model states: the stamp call is guarded by the pre-existing `Train.tsx` guest gate plus the endpoint's own `_reject_guest` (no new gate added); the verdict arm consumes only the fields already delivered on `SolveResponse` for the attempted position (no `game_id`/`ply`/best move rendered); intro copy is static and puzzle-independent; a tampered client can only affect its own account's onboarding UX (server column is the sole persisted fact); the double-post race is mitigated by the settings-null check plus the server's first-write-wins guard. Supply-chain gate: `git diff --exit-code -- frontend/package.json frontend/package-lock.json pyproject.toml uv.lock` exits 0 — no package installed.

## Issues Encountered

None beyond the deviations documented above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plan 05 (score bubble, live outcome accumulator) can proceed: `useTrainOnboarding`, `resolveBubbleState`, and the verdict bubble's copy/pill/tail machinery are all in place and unit-tested; the score screen's own bubble is untouched by this plan.
- Plan 06 (first-reveal walkthrough) has everything it needs already built in `TrainBotStepper`/`walkthroughCopy` (plan 01) — this plan deliberately did not touch `TrainReveal.tsx`'s own structure beyond exporting `TrainScoreChip`, so `TrainReveal`'s complexity reduction (if the walkthrough needs headroom there) remains that plan's own job, exactly as 222-01-SUMMARY recorded.
- The sound-toggle re-homing (D-10's accepted `/bots`-only mute control) is recorded here as the required follow-up seed for phase close, per ROADMAP's instruction — not yet captured as a `.planning/seeds/` file; the phase-close step should create it.
- No blockers. Full frontend suite green: 263 test files / 4107 tests passing after this plan's changes. `npm run lint`, `npm run knip`, `npm run build` (tsc -b) all pass with zero findings.

---
*Phase: 222-train-bot-narrated-onboarding-and-verdicts*
*Completed: 2026-09-13*

## Self-Check: PASSED
