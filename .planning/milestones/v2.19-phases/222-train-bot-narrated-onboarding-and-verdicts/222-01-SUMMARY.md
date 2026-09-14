---
phase: 222-train-bot-narrated-onboarding-and-verdicts
plan: 01
subsystem: frontend (train, ui, personas)
tags: [react, typescript, personas, train, chat-bubble, tdd]

requires: []
provides:
  - "temperament casting axis on all 24 bot personas (stern/friendly/smart)"
  - "pure trainBotCopy.ts copy tables + resolvers (prompt/move/grading/intro/drop-nudge/verdict/return-phrase/walkthrough/score-bubble)"
  - "trainBubbleState.ts's six-state precedence resolver, extracted so the state machine never adds a branch to TrainSolveScreen"
  - "TrainBotBubble.tsx presentational chat-row component"
  - "TrainBotStepper.tsx controlled forward-only stepper (not a TrainLineStepper wrapper)"
  - "D-09 guess vocabulary ('Only one'/'Several' + reveal call-form) across every surfaced call site"
  - "one live bot chat-row bubble replacing 5 sibling JSX guard blocks in TrainSolveScreen, net complexity 68 -> 63"
  - "useTrainOnboarding hook + trainApi.stampOnboarding client call for POST /train/onboarding/{step} (plan 02 implements the server side)"
  - "SolvedResult TS type extended with source/item_status/due_date (D-17)"
affects: [222-02, 222-04, 222-05, 222-06]

actuals:
  tokens: 23667
  tasks: 3
  commits: 3

# Measured (#3968) — git rev-list --count against the pre-plan ledger base.
commits: 3
plan_head_before: e6c0af67e580acbc46320feadaff78e831b00c3f

tech-stack:
  added: []
  patterns:
    - "Extract bubble-state resolution to a pure module-level function so growing a component's state machine never raises its own ESLint-measured cyclomatic complexity (trainBubbleState.ts, mirrors resolveTrainEvalBarReading's existing convention in TrainSolveScreen.tsx)"
    - "Pure copy modules with an injectable rng defaulting to Math.random (pickBot, verdictCopy) for deterministic unit tests without patching globals"
    - "Casting pools derived from a registry field via Object.values().reduce(), never a hand-maintained id list (BY_TEMPERAMENT)"

key-files:
  created:
    - frontend/src/lib/trainBotCopy.ts
    - frontend/src/components/train/trainBubbleState.ts
    - frontend/src/components/train/TrainBotBubble.tsx
    - frontend/src/components/train/TrainBotStepper.tsx
    - frontend/src/hooks/useTrainOnboarding.ts
    - frontend/src/lib/__tests__/trainBotCopy.test.ts
    - frontend/src/components/train/__tests__/trainBubbleState.test.ts
    - frontend/src/components/train/__tests__/TrainBotBubble.test.tsx
  modified:
    - frontend/src/lib/personas/personaRegistry.ts
    - frontend/src/lib/personas/__tests__/personaRegistry.test.ts
    - frontend/src/lib/trainGuessLabels.ts
    - frontend/src/lib/theme.ts
    - frontend/src/index.css
    - frontend/src/pages/Home.tsx
    - frontend/src/components/train/TrainSolveScreen.tsx
    - frontend/src/components/train/TrainReveal.tsx
    - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx
    - frontend/src/components/train/__tests__/TrainReveal.test.tsx
    - frontend/src/types/train.ts
    - frontend/src/api/client.ts
    - frontend/src/hooks/__tests__/useTrainSession.test.ts
    - frontend/src/pages/__tests__/Train.solveLoop.test.tsx

key-decisions:
  - "Temperament mapping applied exactly per the reviewed 222-CONTEXT.md table: 8 stern / 7 smart / 9 friendly, verified by an exhaustive test (assumption_delta_decision invariant style, matching the pre-existing personaRegistry.test.ts conventions)."
  - "verdictCopy's clause text keeps D-23's literal '[+N]' bracket notation as plain text rather than wiring live TrainScoreChip components — the actual pill-embedded verdict bubble UI is plan 04's job; this plan only builds the pure, testable copy resolver."
  - "dropNudgeCopy and introCopy's step-2 line reuse promptCopy internally (D-08/D-22 'Decide first, then move' + 'Your turn' both end in the same guess question) rather than duplicating the sentence, so the two can never drift apart."
  - "scoreBubbleCopy's D-21 must-survive messages are reproduced as three separate string constants injected into the first-completed-session variant verbatim, rather than trusting D-25's own sample text (which does not literally contain message (a) about blunders/mistakes) — this satisfies the task's explicit instruction that all three survive."

requirements-completed: [TRAINBOT-01, TRAINBOT-02, TRAINBOT-03, TRAINBOT-04, TRAINBOT-07, TRAINBOT-08]

coverage:
  - id: D1
    description: "All 24 personas carry a temperament field derived from the reviewed CONTEXT table; the three Train casting pools (BY_TEMPERAMENT) are derived from that field, never a hand-maintained id list."
    requirement: TRAINBOT-07
    verification:
      - kind: unit
        ref: "frontend/src/lib/personas/__tests__/personaRegistry.test.ts#temperament (Phase 222 D-01)"
        status: pass
    human_judgment: false
  - id: D2
    description: "One bot chat-row bubble (guess prompt -> move prompt -> grading) renders inside TrainSolveScreen's measured board column, replacing the five sibling JSX guard blocks, with every pre-existing testid intact and no board overlay."
    requirement: TRAINBOT-02
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx (200 tests, incl. the guess/move/grading-indicator assertions)"
        status: pass
      - kind: unit
        ref: "frontend/src/pages/__tests__/Train.solveLoop.test.tsx"
        status: pass
    human_judgment: true
    rationale: "Actual visual placement (no board overlay, no layout jump, avatar/bubble styling under the board on a real viewport) is a rendering claim that jsdom-based component tests cannot verify pixel-for-pixel; a browser/device check is deferred to a later plan's UAT gate (SC2's 375px risk applies once the intro stepper's longer copy lands in plan 04)."
  - id: D3
    description: "TrainSolveScreen's measured cyclomatic complexity is strictly lower after the bubble lands than the 68 pinned in eslint.config.js, with eslint.config.js itself unchanged."
    requirement: TRAINBOT-02
    verification:
      - kind: other
        ref: "npx eslint --no-inline-config --rule 'complexity: [\"error\", 67]' src/components/train/TrainSolveScreen.tsx (exit 0; measured 68 -> 63 via the complexity:1 sweep)"
        status: pass
    human_judgment: false
  - id: D4
    description: "The guess vocabulary is 'Only one'/'Several' at every surfaced call site (guess buttons, reveal's longer call-form header, Home.tsx marketing line, TrainSolveScreen docstring), with the pre-existing guessFeedbackProse sentences untouched."
    requirement: TRAINBOT-08
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainReveal.test.tsx"
        status: pass
      - kind: other
        ref: "grep -rv comment-lines frontend/src | grep -c 'critical move' -> 0"
        status: pass
    human_judgment: false
  - id: D5
    description: "The full D-22..D-25 copy set (prompt/move/grading/intro/drop-nudge/verdict/return-phrase/walkthrough/score-bubble) exists as tested pure functions, including the D-15/D-16 return-phrase truth table (status checked before any date comparison, both stale-due_date traps for mastered/parked)."
    requirement: TRAINBOT-03
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/trainBotCopy.test.ts (38 tests)"
        status: pass
    human_judgment: false
  - id: D6
    description: "The stamp hook, API call, TrainBotStepper component, and extended TS types (TrainSettingsResponse seen-timestamps, SolvedResult source/item_status/due_date) compile against the contract plan 02 implements; TrainSettingsUpdate is unchanged."
    requirement: TRAINBOT-04
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainBotBubble.test.tsx#TrainBotStepper"
        status: pass
      - kind: other
        ref: "npm run build (tsc -b via vite build) — zero error TS lines"
        status: pass
    human_judgment: false

duration: 105min
completed: 2026-09-13
status: complete
---

# Phase 222 Plan 1: Bot Chat-Row Tracer, Temperament Casting, Full Copy Tables Summary

**A single `<TrainBotBubble>` chat row replaces five sibling guess/move/grading JSX blocks inside TrainSolveScreen's board column — net-negative branch count drops its cyclomatic complexity 68 to 63 — hosted by a random smart-temperament bot per puzzle, backed by 24 newly-cast personas and a full D-22..D-25 pure copy-table module with 38 passing unit tests.**

## Performance

- **Duration:** 105 min
- **Started:** 2026-09-13T16:14:00Z (approx.)
- **Completed:** 2026-09-13T17:59:00Z (approx.)
- **Tasks:** 3 completed
- **Files modified:** 22 (8 created, 14 modified)

## Accomplishments

- Added a `Temperament` field (`'stern' | 'friendly' | 'smart'`) to `Persona`, set on all 24 registry entries per the reviewed CONTEXT table (8 stern / 7 smart / 9 friendly) — enforced exhaustive by `Record<PersonaId, Persona>`.
- Built `trainBotCopy.ts`, a pure (no React import) module carrying every D-22..D-25 copy table and resolver: `pickBot` (injectable rng), `promptCopy`/`movePromptCopy`/`GRADING_COPY`, `introCopy`, `dropNudgeCopy`, `verdictCopy`/`lookCloserCopy`, `returnPhrase` (the full D-15/D-16 status-before-date truth table), `walkthroughCopy`, `scoreBubbleCopy` (D-18/D-25, counts grouped by when).
- Built `trainBubbleState.ts`'s `resolveBubbleState` — the six-state precedence chain (verdict > grading > move > intro > drop-nudge > prompt), extracted so future states never add a branch to `TrainSolveScreen` itself.
- Built the presentational `TrainBotBubble.tsx` (avatar + speech bubble + optional actions row) and the controlled `TrainBotStepper.tsx` (forward-only step index, explicitly not a `TrainLineStepper` wrapper).
- Wired the tracer end-to-end: `TrainSolveScreen`'s guess prompt, move prompt, and grading indicator are now one `<TrainBotBubble>` mount inside the measured board column, hosted by `pickBot('smart')`, with every pre-existing testid unchanged.
- Landed D-09's vocabulary change (`GUESS_LABELS` -> "Only one"/"Several", new `GUESS_CALL_LABELS` for the reveal's longer form) across all four call sites plus the Home.tsx marketing line.
- Added the seen-state client plumbing: `useTrainOnboarding` hook, `trainApi.stampOnboarding`, and the `TrainSettingsResponse`/`SolvedResult` TS type extensions, fixing all five `SolvedResult` fixture construction sites.

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end bot chat-row tracer** — `118f12dd3` (feat)
2. **Task 2: Full copy tables + pure resolvers with unit tests** — `c4d0bc531` (test)
3. **Task 3: Onboarding stepper, stamp-hook plumbing, SolvedResult extension** — `201b599cc` (feat)

**Plan metadata:** committed after this SUMMARY (see final commit below).

## Files Created/Modified

- `frontend/src/lib/trainBotCopy.ts` - pure copy tables + resolvers (D-22..D-25)
- `frontend/src/components/train/trainBubbleState.ts` - the six-state bubble precedence resolver
- `frontend/src/components/train/TrainBotBubble.tsx` - presentational chat-row component
- `frontend/src/components/train/TrainBotStepper.tsx` - controlled forward-only stepper
- `frontend/src/hooks/useTrainOnboarding.ts` - POST /train/onboarding/{step} mutation hook
- `frontend/src/lib/personas/personaRegistry.ts` - `Temperament` field on all 24 personas
- `frontend/src/lib/trainGuessLabels.ts` - D-09 vocabulary + new `GUESS_CALL_LABELS`
- `frontend/src/lib/theme.ts` - `TRAIN_BUBBLE_BORDER`/`TRAIN_BUBBLE_NUDGE_BORDER`
- `frontend/src/index.css` - `animate-train-bubble-nudge` keyframes
- `frontend/src/pages/Home.tsx` - D-09 marketing line
- `frontend/src/components/train/TrainSolveScreen.tsx` - single `<TrainBotBubble>` mount replacing 3 JSX blocks
- `frontend/src/components/train/TrainReveal.tsx` - D-09 "Your call:" header
- `frontend/src/types/train.ts` - `TrainSettingsResponse`/`SolvedResult` extensions
- `frontend/src/api/client.ts` - `trainApi.stampOnboarding`
- Plus 8 test files (3 new, 5 extended) — see frontmatter `key-files`.

## Decisions Made

- Complexity before/after (per acceptance criteria, measured via `npx eslint --no-inline-config --rule 'complexity: ["error", 1]'`): **TrainSolveScreen 68 -> 63** (net -5, below the pinned 68 ceiling). **TrainReveal remained at 68 unchanged** — task 1's only TrainReveal edit was the one-line D-09 header swap (`GUESS_LABELS` -> `GUESS_CALL_LABELS`, same ternary shape, no branch removed); TrainReveal's own complexity reduction is explicitly plan 04's job (it removes the verdict/action rows from TrainReveal, per RESEARCH's project structure table).
- Temperament mapping applied verbatim from the reviewed CONTEXT.md table (8 stern / 7 smart / 9 friendly), confirmed by an exhaustive count assertion in `personaRegistry.test.ts`.
- `verdictCopy`'s clause strings keep D-23's literal `[+N]` bracket notation as plain text; wiring actual `TrainScoreChip` pill components into the rendered verdict bubble is plan 04's UI work, not this plan's pure-copy-module scope.
- Otherwise followed the plan exactly.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Task 1's own `<verify>` combined-file complexity check cannot pass as literally written**
- **Found during:** Task 1 (tracer verification)
- **Issue:** The plan's task-1 `<verify>` block runs `npx eslint --no-inline-config --rule 'complexity: ["error", 67]'` against **both** `TrainSolveScreen.tsx` and `TrainReveal.tsx` in one invocation, requiring BOTH functions to measure below 68. But the plan's own action steps (and the `must_haves.truths`/`<done>` criteria, which explicitly name only `TrainSolveScreen`) never ask task 1 to touch `TrainReveal.tsx` structurally — RESEARCH's own project-structure table assigns TrainReveal's verdict/action-row removal (its complexity-lowering edit) to plan 04. Since `TrainReveal` genuinely starts and ends task 1 at exactly complexity 68 (unchanged), the literal two-file command fails with exit 1 regardless of what task 1 does to `TrainSolveScreen`.
- **Fix:** Interpreted the check per its stated intent (`must_haves.truths` item 5 and the `<done>` criterion both name TrainSolveScreen specifically) and ran the same rule scoped to `TrainSolveScreen.tsx` alone, which passes (exit 0, complexity 63). Documented the full two-file command's actual output (one error naming `TrainReveal.tsx` at complexity 68) here rather than silently narrowing the check without a record.
- **Files modified:** None (verification-scope interpretation only, no code change).
- **Verification:** `npx eslint --no-inline-config --rule 'complexity: ["error", 67]' src/components/train/TrainSolveScreen.tsx` exits 0.
- **Committed in:** N/A (documentation-only finding, recorded here for the verifier).

**2. [Rule 1 - Bug] A third TrainReveal.test.tsx assertion pinned the retired "Guess:" header text**
- **Found during:** Task 1 (D-09 vocabulary call sites)
- **Issue:** The plan named exactly two TrainReveal.test.tsx assertions to update (`:273`, `:281`), but a third (`:1501`, `expect(card.textContent).toContain('Guess:')`) also pinned the retired header prefix and was not listed.
- **Fix:** Updated the assertion to `'Your call:'`, matching the new header text.
- **Files modified:** `frontend/src/components/train/__tests__/TrainReveal.test.tsx`
- **Verification:** Full `TrainReveal.test.tsx` suite passes (95/95).
- **Committed in:** `118f12dd3` (Task 1 commit)

**3. [Rule 1 - Bug] The new D-22 move-prompt copy ends in a period, breaking two exact-string test assertions**
- **Found during:** Task 1 (integration)
- **Issue:** D-22's own quoted copy is `"Now play a move for white."` (with a trailing period), but the two pre-existing `TrainSolveScreen.test.tsx` assertions the plan named for update (`:1418-1433`) expected the old no-period wording. Updating the copy without updating the assertions' expected string broke both tests.
- **Fix:** Updated both `.toBe(...)` assertions to include the trailing period, matching D-22's copy verbatim.
- **Files modified:** `frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx`
- **Verification:** Both named tests pass; full file suite green (200/200 across the four task-1 verify files).
- **Committed in:** `118f12dd3` (Task 1 commit)

**4. [Rule 3 - Blocking] `useMemo`'s intentionally-unreferenced `puzzle.position` dependency triggered a new lint warning**
- **Found during:** Task 1 (integration)
- **Issue:** `const bot = useMemo(() => pickBot('smart'), [puzzle.position])` intentionally re-runs the random draw per puzzle even though the callback never reads `puzzle.position` — `react-hooks/exhaustive-deps` flagged it as an "unnecessary dependency" warning, which would have been new lint noise attributable to this change.
- **Fix:** Added a `// eslint-disable-next-line react-hooks/exhaustive-deps` comment explaining the intentional cache-busting dependency (a documented, pre-existing idiom in this same file for a similar case).
- **Files modified:** `frontend/src/components/train/TrainSolveScreen.tsx`
- **Verification:** `npm run lint` (which respects inline disables, unlike the `--no-inline-config` verify command) exits 0 with zero warnings.
- **Committed in:** `118f12dd3` (Task 1 commit)

**5. [Rule 1 - Bug] `TrainBotStepper.tsx`'s own doc comment quoted the forbidden testid strings**
- **Found during:** Task 3 (acceptance-criteria check)
- **Issue:** The doc comment explaining why `TrainLineStepper` is not reused literally spelled out `btn-train-step-prev`/`btn-train-step-next` for clarity — which is exactly the substring the acceptance criterion's grep check forbids anywhere in the file (comments included).
- **Fix:** Reworded the comment to describe the testids without spelling them out literally.
- **Files modified:** `frontend/src/components/train/TrainBotStepper.tsx`
- **Verification:** `grep -c "btn-train-step-prev\|btn-train-step-next" TrainBotStepper.tsx` returns 0.
- **Committed in:** `201b599cc` (Task 3 commit)

---

**Total deviations:** 5 (2 documentation/verification-scope findings, 3 auto-fixed bugs/blockers). **Impact:** All fixes were necessary for test-suite correctness or acceptance-criteria compliance; none represent scope creep. The task-1 combined-complexity-check finding is a plan-authoring inconsistency (not a code defect) and is flagged here for the verifier's attention — `TrainReveal`'s own complexity reduction remains explicitly assigned to plan 04.

## Known Stubs

None. `useTrainOnboarding.ts` is exported but genuinely unused until plan 04 imports it (per the plan's own explicit instruction: "if knip fails at the end of THIS plan, note it in the SUMMARY rather than deleting the export") — this is intentional forward-compat plumbing, not a stub. `npm run knip` confirms exactly one such flagged export (`useTrainOnboarding`) and nothing else.

## Threat Flags

None. All four threat-register entries assigned to this plan (T-222-01-01..04) are discharged by construction per the plan's own threat model: the copy resolvers consume only fields already delivered on `SolveResponse`, the `SolvedResult` extension mirrors the server schema verbatim, `pickBot`'s cast is cosmetic only, and the stamp hook sends no user identifier. The T-222-01-SC supply-chain gate passed: `git diff --exit-code -- frontend/package.json frontend/package-lock.json pyproject.toml uv.lock frontend/eslint.config.js` exits 0.

## Issues Encountered

None beyond the deviations documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 02 (server-side seen state + `POST /train/onboarding/{step}`) can proceed immediately: the client already calls `trainApi.stampOnboarding('intro' | 'reveal_walkthrough' | 'sr_explained')` and expects a `TrainSettingsResponse` back with the three new nullable fields — plan 02 need only match that exact contract.
- Plan 04 (solve-screen intro stepper + drop-nudge + verdict bubble) has everything it needs already built: `resolveBubbleState`'s `intro`/`drop-nudge` arms, `TrainBotStepper`, `introCopy`/`dropNudgeCopy`/`verdictCopy`/`returnPhrase`, and `useTrainOnboarding` are all in place and unit-tested — plan 04 is pure wiring, plus TrainReveal's own complexity reduction (verdict/action-row removal) that this plan deliberately deferred.
- Plan 05/06 (score bubble, first-reveal walkthrough) can consume `scoreBubbleCopy`/`walkthroughCopy` directly; plan 05 additionally needs the live `solvedOutcomes` accumulator in `useTrainSession` (RESEARCH Finding C), not yet built (not this plan's scope).
- No blockers. Full frontend suite green: 263 test files / 4091 tests passing after this plan's changes.

---
*Phase: 222-train-bot-narrated-onboarding-and-verdicts*
*Completed: 2026-09-13*

## Self-Check: PASSED

All 8 created files verified present on disk; all 3 task commits (`118f12dd3`, `c4d0bc531`, `201b599cc`) verified present in git history.
