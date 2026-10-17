# Phase 240: Train First-Session Onboarding Load - Research

**Researched:** 2026-10-15
**Domain:** Train onboarding UX (React copy/state machine) + one Alembic column swap + a session-composition reorder (FastAPI/SQLAlchemy)
**Confidence:** HIGH (every claim below is from code read this session; no external libraries involved)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Intro (puzzle 1, before the first move)
- **D-01:** Intro = 2 bubbles: the welcome (`INTRO_WELCOME_COPY`, all 4 audience variants **kept
  verbatim**), then the existing closing prompt ("Decide first, then play. Your turn. {promptCopy}")
  carrying the guess buttons. `INTRO_QUESTION`, `INTRO_VOCABULARY`, `INTRO_PRACTICE` and
  `INTRO_WARMUP_COPY` retire from the intro. `introStepCount` no longer varies with warm-up (2 always);
  `IntroStep` narrows accordingly.
- **D-02:** The warm-up notice is **dropped without relocation**. In a warm-up session every puzzle is a
  filler or herring, so the puzzle-1 verdict tail already says "That one was a warm-up, so it won't
  come back…" (`WARMUP_TAIL_COPY`, audience-aware), and the warm-up score bubble repeats it
  (`WARMUP_SCORE_CLAUSE`). No new warm-up copy.

#### Vocabulary lesson (puzzle 1 reveal)
- **D-03:** The vocabulary lives in **tour part 1's result bubble** (the Hilda stepper overlay, shown on
  every device), NOT in the verdict text. On phones the verdict is a one-line strip and the full
  feedback only opens on a tap, so verdict text would be missed. Verdict copy (`verdictCopy`,
  `verdictStripLine`) stays unchanged.
- **D-04:** The result bubble explains what the call meant **for this position, per answer type**: a
  "only one" variant (sharp) and a "several" variant (soft SR item or herring). The several variant is
  needed because part 1 can land on a herring or soft puzzle (own-games first session with no sharp
  puzzle, or an abandoner whose first reveal comes in a later session, see D-13).
- **D-05:** The scoring explanation ("a point for the right call and up to two for the move") is
  **dropped** from the tour: the strip and verdict already show `[+1]`/`[+2]`. Tour part 1 stays at 2
  steps: result + vocabulary, then Next.

#### Reveal tour split
- **D-06:** Three parts (as in the seed): **P1** = result/vocabulary + Next; **P2** = chips + stepping
  through lines; **P3** = sidelines/rewind, "understand, don't memorize", Analyze. Chips stay visible but
  unexplained on P1 (no variant reveal screen). Every step stays within `STEPPER_COPY_MAX_CHARS` (145),
  shortened not concatenated. Merged-chip and per-device copy variants from Phase 237 carry over.
- **D-07:** **Trigger = the next reveal after the previous part was completed**, account-scoped, at most
  one part per reveal. It is not tied to puzzle 2/3 of session 1: someone who quits after P1 gets P2 on
  their first reveal next session.
- **D-08:** A part counts as complete when the user leaves its last step (same as today's walkthrough).
  A part left halfway replays on the next reveal.

#### Stamp storage
- **D-09:** **Stage counter**: one `SmallInteger` column on `train_settings` (e.g. `reveal_tour_stage`,
  0-3, `CHECK` 0..3, default 0). It only moves forward and is idempotent on replay: advance to N only
  from N-1, the same first-write-wins spirit as `stamp_onboarding_step`'s guarded `IS NULL` UPDATE.
  — **Reversibility:** one-way — needs an Alembic migration plus a column drop (D-10); undoing restores data only from the counter.
- **D-10:** **Retire `reveal_walkthrough_seen_at`**: the migration backfills `reveal_tour_stage = 3`
  wherever it is non-null, then drops the column. Remove it from `TrainSettingsRow`,
  `TrainSettingsResponse`, `_ONBOARDING_COLUMNS`, `OnboardingStep`, and the frontend types/hooks.
  — **Reversibility:** one-way — dropped column; the completion timestamp is lost (owner accepted).
- **D-11:** **Hard cut, no compat shim.** A stale PWA tab that POSTs `/train/onboarding/reveal_walkthrough`
  gets a 422 and may replay the old tour until it reloads. Accepted given the traffic.
- **D-12:** Users who are mid-onboarding at deploy (intro seen, old tour not finished) start the new
  split tour from part 1. Intro gating (`intro_seen_at`) is unchanged.

#### First-session composition (backend)
- **D-13:** The reorder applies to the **first-ever session only**: the user has no earlier
  `drill_sessions` row of any status. A recomposed untouched/resized first session
  (`_discard_if_untouched_and_resized`) still counts as first-ever; the researcher verifies the
  discarded row is gone before the check runs. The reorder runs **after** the D-09 seeded shuffle in
  `_assemble_session_items` and stays deterministic. Later sessions keep the plain shuffle, so the only
  herring leak is "slot 0 of session 1 is never a herring".
- **D-14:** "Sharp" for slot 0 = **answer-key type `sharp`**, the same classification the verdict uses
  (`answer_key_for` / `classify_puzzle_type` on the live blob for SR items; sharp fillers are always
  sharp). Not a source proxy, since SR items can be soft. Answer keys are attached after materialize
  today (`_attach_answer_keys`), so composition may need the type earlier; the researcher checks the
  cost and picks the seam. If no sharp puzzle exists (own-games session), keep the random order.
- **D-15:** Puzzle 2 or 3 (index 1-2) of the first-ever session holds **any "several" puzzle** (herring or
  soft SR item, the first one in shuffled order). If none is there already, swap it in (seeded
  choice between index 1 and 2). If none exists, leave the order alone. Default sessions are 6
  puzzles with 1 herring (`HERRING_SHARE` 0.25); warm-up sessions have no soft puzzles.

#### Score screen
- **D-16:** The practice rationale is **shortened and merged into line 1** (after the session opener)
  of the score bubble. The bubble stays at 2 lines; UAT confirms the score stays above the fold at
  375x667 (the Phase 222 round 6 regression). Draft direction: "Practice teaches you when to calculate
  and when a quick good move is enough." (final copy at Claude's discretion).
- **D-17:** The rationale shows on the **first completed session** (`isFirstCompletedSession`, which
  can be session 2 for an abandoner), in all three `scoreBubbleCopy` branches: regular, perfect
  ("Nothing got away today"), and warm-up.
- **D-18 (added by owner in discuss):** **Remove the returning-counts sentence from the score screen for
  every session** (`returningCountsSentence`: "2 come back next session, 1 in 3 days." / "Nothing else
  is coming back yet."). It is clutter. The per-puzzle verdict return tails (`returnPhrase`, e.g. "Let's
  see if you remember this in 3 days") **stay**; they are where spaced-repetition timing is shown.
  Clean up whatever `ScoreBubbleInput` fields only that sentence used (`outcomes`, `session_date`,
  `expires_on` if nothing else reads them).

#### Copy sheet
- **D-19:** The copy sheet in `<specifics>` below is the **owner-reviewed starting draft** for every
  step and conditional variant. Planner and executor implement it verbatim. Small wording fixes found
  at UAT are fine, but every bubble stays within 145 chars and no step is added. This includes the
  warm-up shortening on the first completed session (line 1 drops "nothing to bring back yet").

#### Tour spotlight styling
- **D-20:** The element a tour step explains gets a **more salient highlight**: the flaw-fixed card's
  border (`FLAW_FIXED_GLOW` in `frontend/src/components/train/TrainFlawFixedBanner.tsx`:
  `rgba(205,127,50,0.85)`, the homepage "brand glow". The owner calls it gold; it is the bronze brand
  color, so reuse that exact value) plus a **pulsating glow** of the same color. This replaces today's
  scattered `ring-2 ring-brand-brown` spotlights (`TrainReveal.tsx` verdict/tree/lines,
  `TrainSolveScreen.tsx` board, the action bar) with **one shared class/constant** used by every tour
  target. It applies to all three tour parts.
  - Pulse = a new `@keyframes` in `frontend/src/index.css` animating the `box-shadow` glow (alpha/blur),
    looping while the step is active, next to the existing `arrow-pulse` / `row-highlight-pulse`.
  - `prefers-reduced-motion`: static glow, no pulse.
  - The highlight must not shift layout (border width compensated, or `outline`/`box-shadow` only) and
    must not be clipped by `overflow` parents (the board row, the fixed phone action bar).
  - Phase 237 UAT left the chips row un-ringed because the active chip's own ring already marked it.
    With the new glow the **chips row container does get the highlight** (salience is the goal, and
    the glow reads differently from a chip's selection ring). Recheck at UAT that the two don't clash.

### Claude's Discretion
- Copy beyond D-19's sheet (none expected). Whether the P1 bubble refers to the user's own guess: no,
  per the sheet.
- Onboarding endpoint shape for the stage advance (e.g. `POST /train/onboarding/reveal_tour` with the
  target stage, or step literals mapping to stages), keeping the fixed-dict / no-`getattr` rule from
  T-222-02-03.
- How the reveal decides which part to show (from `reveal_tour_stage` in the settings query).
- Phase 233 D-13 telemetry: keep `review_walkthrough: true` on any reveal where a tour part ran.

### Copy sheet (D-19, verbatim from CONTEXT `<specifics>`)

"Unchanged" = today's string in `frontend/src/lib/trainBotCopy.ts`. `{back}`/`{forward}`/`{rewind}` are
`TOUR_ICON_TOKEN`s rendered as icons. Char counts measured with tokens as text (all ≤ 145).

**Intro (puzzle 1, before the first move): 2 steps**

- **I-1 Welcome** (unchanged, `INTRO_WELCOME_COPY` per audience):
  - has_games: "Welcome to FlawChess Train! You will improve by solving puzzles created from your own games."
  - has_games_guest: "Welcome to FlawChess Train! Sign up free and you will improve by solving puzzles created from your own mistakes."
  - no_games: "Welcome to FlawChess Train! Import your games and you will improve by solving puzzles created from your own mistakes."
  - no_games_guest: "Welcome to FlawChess Train! Import your games and sign up, and you will improve by solving puzzles created from your own mistakes."
- **I-2 Closing prompt + guess buttons** (unchanged): "Decide first, then play. Your turn. You play {white|black}. Is there only one good move, or several?"
- Retired: `INTRO_QUESTION`, `INTRO_VOCABULARY`, `INTRO_PRACTICE`, `INTRO_WARMUP_COPY`.

**Warm-up verdict tail** (unchanged, carries the warm-up notice per D-02): "That one was a warm-up, so it
won't come back." + has_games "Your own positions will." / has_games_guest "Sign up free and your own
positions will." / no_games "Import your games and your own positions will." / no_games_guest "Import
your games, then sign up, and your own positions will."

**Tour part 1 (first reveal): 2 steps**

- **P1-1 Result + vocabulary** (new, spotlight `verdict`), by device × answer type (sharp = key type
  `sharp`; several = `soft` or `herring`):
  - phone + sharp (124): "This strip is your result. Here only one move was good, every other move was a mistake. Tap the strip for the full feedback."
  - phone + several (117): "This strip is your result. Here several moves were fine, so any good move works. Tap the strip for the full feedback."
  - desktop + sharp (102): "Your result is in the highlighted bubble. Here only one move was good, every other move was a mistake."
  - desktop + several (95): "Your result is in the highlighted bubble. Here several moves were fine, so any good move works."
- **P1-2 Next** (new, spotlight `bar`): "Next takes you to the next puzzle."

**Tour part 2 (next reveal after part 1): 2 steps**

- **P2-1 Chips** (unchanged, spotlight `chips`): "The Move, Best, and Game chips are the lines, one per
  move. Tap one to focus it on the board." + only when shown: ' "Move = Best" means you found the best
  move.' / ' "Move = Game" means you played the game move.' (max 139)
- **P2-2 Stepping** (unchanged, spotlight `tree`):
  - phone (90): "Step through the focused line with {back} {forward} in the bar, or tap a move in the list."
  - desktop (116): "Step through the focused line with {back} {forward} under the board, the arrow keys, or a tap on a move in the list."

**Tour part 3 (next reveal after part 2): 3 steps**

- **P3-1 Sidelines** (unchanged, spotlight `board`):
  - phone (124): "Move a piece to try your own idea: it branches off as a sideline. {rewind} in the bar takes you back to the puzzle position."
  - desktop (121): "Move a piece to try your own idea: it branches off as a sideline. {rewind} or Home takes you back to the puzzle position."
- **P3-2 Understand** (unchanged, spotlight `lines`, 127): "Understanding why a move works or fails by analyzing the lines is what makes the pattern stick. Don't just memorize the answer."
- **P3-3 Analyze** (changed: the Next sentence moved to P1-2; spotlight `bar`):
  - analyzeOpens = game (102): "The Analyze button opens the whole game one move before the mistake, so you can see how you got there."
  - analyzeOpens = position (61): "The Analyze button opens this position on the analysis board."

**Score screen** (`scoreBubbleCopy`). `{rationale}` = "Practice teaches you when to calculate and when a
quick good move is enough." (76), first completed session only (D-17). The returning-counts sentence is
gone from every branch (D-18).

| Branch | Line 1 | Line 2 |
|---|---|---|
| Regular, first completed | `{opener} {rationale}` | "Reminders build the habit that makes Train work." + `{reminder ask}` |
| Regular, later | `{opener} See you tomorrow.` | none |
| Perfect, first completed | "Nothing got away today." + `{rationale}` | "Reminders build the habit that makes Train work." + `{reminder ask}` |
| Perfect, later | "Nothing got away today." | `{reminder ask}`; if reminders already on: "Remember to analyze why the moves work or fail, not just memorize the best move." |
| Warm-up, first completed | `{opener} {rationale} Those were warm-ups. {warm-up clause}` (shortened, ~180 max) | guest: `GUEST_SIGNUP_ASK_SCORE`; has_games: `WARMUP_REMINDER_ASK_COPY`; no_games: none |
| Warm-up, later | `{opener} Those were warm-ups, nothing to bring back yet. {warm-up clause}` (unchanged) | same as above |

- `{opener}` (unchanged): green "Strong session." / yellow "Solid session, with a few that got away." /
  red "Tough session. That is exactly what Train is for." / no band "Session done."
- `{reminder ask}` (unchanged `REMINDER_ASK_COPY`): remind_me "Turn on Remind me and let the next session
  find you." / scan_qr "Train works best on your phone: scan the code below to install FlawChess there
  and turn on reminders." / none "Yours are already on, so the next session will find you."
- `{warm-up clause}` (unchanged `WARMUP_SCORE_CLAUSE`): has_games "Once your games are analyzed, your own
  mistakes take over." / has_games_guest "Guest games are not analyzed automatically, so your own
  mistakes are not here yet." / no_games "Import your games and your own mistakes take over." /
  no_games_guest "Import your games, then sign up, and your own mistakes take over."

**Measurement** (from CONTEXT): re-run the SEED-200 clean-cohort funnel (split guest-origin vs registered)
before and after. "Never finished the tour" becomes `reveal_tour_stage < 3` (or `= 0` for "never finished
part 1"). Commit a "before" snapshot during the phase; the "after" read is a post-deploy follow-up,
not a phase gate.

### Deferred Ideas (OUT OF SCOPE)
None. The one addition raised in discuss (removing the score-screen returning counts) was folded in as
D-18.

Reviewed Todos (not folded): `172-deferred-review-findings.md`,
`2026-03-11-bitboard-storage-for-partial-position-queries.md`, `2026-08-29-variation-tree-nested-button.md`,
`2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label.md` — unrelated to Train onboarding.
</user_constraints>

<phase_requirements>
## Phase Requirements

The coverage contract is the D-XX decisions in 240-CONTEXT.md (no REQ-IDs were registered).

| ID | Description | Research Support |
|----|-------------|------------------|
| D-01 | Intro = 2 steps (welcome + closing guess prompt) | `introSteps`/`introStepCount`/`introCopy`/`IntroStep` at `trainBotCopy.ts:282-409`; consumers `TrainSolveScreen.tsx:400-417,557-571,594-609,654,1705-1712`, `trainBubbleState.ts:26,34,56`. See Pattern 4. |
| D-02 | Warm-up notice dropped from intro, no relocation | `INTRO_WARMUP_COPY` `trainBotCopy.ts:341-354` deleted; `WARMUP_TAIL_COPY` (`:533-541`) + `WARMUP_SCORE_CLAUSE` (`:763-770`) untouched. `isWarmup` param drops out of `introSteps`/`introStepCount`/`introCopy` and `resolveBubblePersona`. |
| D-03/D-04/D-05 | P1-1 result bubble teaches vocabulary per device × answer type; no scoring line | `SolveResponse.puzzle_type` (`types/train.ts:286`) is the answer-type source on the reveal. Pattern 2 (tour model). |
| D-06/D-07/D-08 | Three parts, next reveal after previous part completed, complete on leaving last step | `useTrainWalkthrough.ts` rewrite (Pattern 3: part latched per reveal). |
| D-09/D-10/D-11/D-12 | `reveal_tour_stage` SmallInteger 0..3, backfill 3, drop old column, hard cut | Model `train_settings.py:141-149`; migration pattern `phase_193` CHECK; endpoint `routers/train.py:554-591`; repo `train_repository.py:679-721`. Pattern 1 + Runtime State Inventory + consumer table. |
| D-13/D-14/D-15 | First-ever session: sharp to slot 0, a "several" puzzle into index 1-2 | `_assemble_session_items` `train_repository.py:1993-2121`, shuffle at `:2104`, discard-delete at `:1572`, `answer_key_for` `train_pool.py:363-392`. Pattern 5. |
| D-16/D-17/D-18 | Rationale merged into score line 1 (first completed session, all 3 branches); returning counts removed | `scoreBubbleCopy` `trainBotCopy.ts:866-953`; `TrainScoreScreen.tsx:222-254` latch + stamp gate (**gap found**, see Pitfall 1). |
| D-19 | Copy sheet verbatim, ≤145 per bubble | Char counts re-measured this session (all ≤ 139). Budget enforced by vitest only (`trainBotCopy.test.ts:291-300,755-763`). |
| D-20 | One shared pulsing bronze spotlight class, reduced-motion static, no layout shift/clipping, chips row highlighted | Ring sites inventoried below (TrainVerdictStrip `:63,:152`, TrainReveal `:420-428`, TrainSolveScreen `:1886`, action bar has none today). Pattern 6. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **No magic numbers**: stage bounds, part count, first-session "several" slot indices go into named constants (`REVEAL_TOUR_STAGE_COUNT`-style). [VERIFIED: CLAUDE.md]
- **Literal types, never bare `str`** for fixed sets: step names, answer kinds, tour step ids. `Sequence[...]` for list-of-Literal params. [VERIFIED: CLAUDE.md]
- **ty must pass** (`uv run ty check app/ tests/ scripts/`), explicit return types; `# ty: ignore[rule]` only where unfixable. [VERIFIED: CLAUDE.md]
- **Nesting depth ≤ 4** gated by `scripts/check_function_size.py app/ --fail-over-depth 4` (backend) and eslint `max-depth` (frontend). The reorder helper must stay shallow (guard clauses). [VERIFIED: CLAUDE.md]
- **DB rules**: no native ENUM; low-volume bounded integer = `SmallInteger` + range `CHECK` (exactly the `shield_level`/`reminder_hour` precedent in `train_settings.py:52-58`). [VERIFIED: CLAUDE.md, app/models/train_settings.py:52-58]
- **Routers thin, no SQL in services/routers**; repository owns the UPDATE. [VERIFIED: CLAUDE.md]
- **Sentry**: `capture_exception` in non-trivial except blocks in routers/services; never variables in messages (the onboarding router already follows this at `routers/train.py:581-588`). [VERIFIED: CLAUDE.md, app/routers/train.py:581-588]
- **Never `asyncio.gather` on one AsyncSession**; time from `dev_now_utc` (`NowUtc`) dependency. [VERIFIED: CLAUDE.md]
- **Frontend**: theme colors in `lib/theme.ts` (the bronze glow value has semantic meaning, so it belongs there or in an `index.css` CSS variable, not inline in components); `data-testid` on interactive elements; min font `text-sm`; `noUncheckedIndexedAccess`; knip must stay clean (delete dead exports like `ScoreBubbleOutcome`, `WALKTHROUGH_STEP_COUNT` when retired); `npm run build` (tsc) before integrating shared-type changes. [VERIFIED: frontend/CLAUDE.md]
- **Umami**: new user-facing feature ships with its `trackFeature` event, BUT "skip what the database already says" — tour progress is now a DB column (`reveal_tour_stage`), so no event is needed. No existing Umami event is tied to the intro/tour (grep of `lib/analytics.ts` and the tour components found none), so nothing must be renamed. [VERIFIED: frontend/CLAUDE.md; grep of frontend/src/lib/analytics.ts]
- **Changelog**: user-facing bullet under `## [Unreleased]` (`CHANGELOG.md:9`) when the phase merges. [VERIFIED: CHANGELOG.md:9]
- **Pre-merge gate** (full list in CLAUDE.md) before squash-merge; **never run `bin/reset_db.sh`**; plans must not gate on a DB reset (memory: work against existing dev DB). `scripts/reset_train_state.py` is the sanctioned per-account reset for UAT and must be updated (it writes `reveal_walkthrough_seen_at=None`, line 210). [VERIFIED: CLAUDE.md; scripts/reset_train_state.py:200-212]
- **Communication**: em-dashes sparingly in UI copy (the copy sheet already complies; the walkthrough test asserts "no copy has an em-dash", `trainBotCopy.test.ts:744`). [VERIFIED: frontend/src/lib/__tests__/trainBotCopy.test.ts:744]

## Summary

This phase is almost entirely a rewrite of one pure copy module (`frontend/src/lib/trainBotCopy.ts`), one hook (`useTrainWalkthrough.ts`), and their call sites, plus two small backend changes: a `train_settings` column swap (timestamp → stage counter) and a deterministic post-shuffle reorder for the first-ever session. No new libraries. Every integration point was located with file:line evidence.

Three findings change the plan beyond what CONTEXT anticipated. (1) **The `sr_explained` stamp gate breaks D-17**: today the score screen stamps `sr_explained` only when the regular-with-misses branch renders (`TrainScoreScreen.tsx:248`, `showsFullExplanation = firstExplanation && !isWarmup && missedCount > 0`). If the rationale now also renders in the warm-up and perfect branches without widening that gate, a zero-game guest (every session is a warm-up) would see the "first session" rationale on every session forever. The gate must become "stamp whenever the first-completed variant rendered, in any branch". (2) **A stage stamp landing mid-reveal can chain two tour parts on one reveal** (the stamp's `onSuccess` rewrites the settings cache, which drives the hook), so the part must be latched once per reveal at verdict time (D-07 "at most one part per reveal"). (3) **The phone action bar lives in a different React tree** (`App.tsx` `MobileBottomBar` via the `mobileBoardControls` store), so spotlighting it for P1-2/P3-3 needs a new payload field; it is not ringed at all today (removed in Phase 237 UAT because the ring "was clipped by the fixed mobile bottom bar", `TrainRevealActionBar.tsx:103-105`).

The backend reorder is cheap: `_assemble_session_items` already knows each puzzle's `source`; herrings are always type `herring`, sharp fillers always `sharp` (`answer_key_for`, `train_pool.py:386-389`), and only SR items need one extra query for `GameFlaw.missed_pv_lines` (≤ 6 rows, first-ever session only). The first-ever check must run after `_resolve_existing_session`, which is where an untouched/resized first session is deleted with an immediate `DELETE` statement on the same transaction (`train_repository.py:1572`), so a subsequent `EXISTS` sees it gone.

**Primary recommendation:** Keep the existing `POST /train/onboarding/{step}` shape and extend its `Literal` with `reveal_tour_1|2|3` mapped through a fixed dict to a guarded `UPDATE ... SET reveal_tour_stage = N WHERE reveal_tour_stage = N-1`; model the tour as three parts of named step ids in `trainBotCopy.ts`; latch the part per reveal in the hook; widen the `sr_explained` stamp gate to every first-completed branch.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Intro step list / copy (D-01, D-02) | Browser (pure module `trainBotCopy.ts`) | — | All copy is client-side by design (Phase 222 D-06). |
| Tour part selection + step state (D-06..D-08) | Browser (`useTrainWalkthrough`) | API (stage read via `GET /train/settings`) | Server owns the durable stage; client owns per-reveal step index and the latch. |
| Tour progress persistence (D-09, D-10) | API + Database | — | Server-owned watermark, response-only, never in `TrainSettingsUpdate` (Phase 222 D-12 rule). |
| Answer type for P1-1 copy (D-04) | API (already on `SolveResponse.puzzle_type`) | Browser (reads it) | Same classification the verdict's `correct_guess` uses; client never re-derives. |
| First-session order (D-13..D-15) | API / Repository (`train_repository.py`) | Database (`drill_solves.position`) | Order is frozen into `drill_solves.position` at materialize time; must be decided before insert. |
| Score bubble copy (D-16..D-18) | Browser (`scoreBubbleCopy`) | API (`sr_explained_at` watermark) | Copy client-side; "first completed" = `sr_explained_at IS NULL` latch. |
| Spotlight styling (D-20) | Browser (CSS keyframes + one shared class) | — | Pure presentation. |
| Funnel measurement | Database (prod, read-only) | — | Orchestrator/human runs SQL over the prod tunnel (subagents lack project MCP). |

## Standard Stack

No new dependencies. Everything uses what is installed.

### Core (existing, versions from CLAUDE.md)
| Library | Purpose in this phase |
|---------|----------------------|
| SQLAlchemy 2.x async + Alembic | Column swap migration, guarded UPDATE, one composition query |
| FastAPI + Pydantic v2 | `Literal` path param validation on `/train/onboarding/{step}` |
| React 19 + TanStack Query | Hook state, `setQueryData` on the shared `['train','settings']` cache |
| Tailwind + `index.css` keyframes | Spotlight class + pulse animation |
| Vitest / pytest | Tests (see Validation Architecture) |

**Installation:** none.

## Package Legitimacy Audit

Not applicable: this phase installs no external packages (npm, PyPI or otherwise). **Packages removed due to [SLOP] verdict:** none. **Packages flagged [SUS]:** none.

## Architecture Patterns

### System Architecture Diagram

```
                      ┌────────────────────── Browser ───────────────────────┐
 Start (POST /train/sessions)                                                 │
        │                                                                     │
        ▼                                                                     │
 compose_and_materialize_session ──► _resolve_existing_session                │
   (train_repository.py:2419)          ├─ open + untouched + resized ─► DELETE row (:1572)
                                       ├─ open ─► resume (order frozen)       │
                                       └─ completed in window ─► resume       │
        │ (none to resume)                                                     │
        ▼                                                                     │
 first_ever? = NOT EXISTS drill_sessions WHERE user_id  (NEW)                 │
        ▼                                                                     │
 _assemble_session_items: select → reconstruct → filler backfill → D-09 shuffle (:2104)
        │                                         │                           │
        │                       first_ever ──► types (herring/sharp/SR blob) ─► reorder:
        │                                         sharp→slot0, several→idx1|2 (NEW, seeded)
        ▼                                                                     │
 _materialize_session_rows (positions frozen) ─► _attach_answer_keys ─► TrainSessionResponse
                                                                              │
 Puzzle 1: intro (2 steps) when intro_seen_at null ──guess──► POST /train/onboarding/intro
        ▼                                                                     │
 Solve ─► SolveResponse{puzzle_type, ...} ─► reveal                           │
        ▼                                                                     │
 useTrainWalkthrough: latch part = settings.reveal_tour_stage (if < 3) at first verdict
        ├─ part 0: [result(sharp|several × phone|desktop), next]
        ├─ part 1: [chips, stepping]
        └─ part 2: [sidelines, understand, analyze]
        │ bar Next consumes steps; leave from last step ─► POST /train/onboarding/reveal_tour_{part+1}
        ▼                                                                     │
 Server: UPDATE train_settings SET reveal_tour_stage=N WHERE stage=N-1 ─► settings response ─► setQueryData
        ▼                                                                     │
 Session end ─► TrainScoreScreen: latch first = (sr_explained_at null) ─► scoreBubbleCopy
                    └─ first-completed variant rendered (any branch) ─► POST /train/onboarding/sr_explained
                      └──────────────────────────────────────────────────────┘
```

### Component Responsibilities (file:line inventory)

**Intro machinery** (all `frontend/src/lib/trainBotCopy.ts`, read this session):
| Symbol | Lines | Current value / role |
|---|---|---|
| `IntroStep` | 282 | `export type IntroStep = 0 \| 1 \| 2 \| 3 \| 4 \| 5;` [VERIFIED: trainBotCopy.ts:282] → becomes `0 \| 1` |
| `INTRO_WELCOME_COPY` | 296-309 | kept verbatim (D-01) |
| `INTRO_QUESTION` / `INTRO_VOCABULARY` / `INTRO_PRACTICE` | 310-327 | delete |
| `INTRO_WARMUP_COPY` | 341-354 | delete (D-02) |
| `introSteps(sideToMove, isWarmup, audience)` | 367-385 | becomes `[welcome, closing]`, drop `isWarmup` param |
| `introStepCount(isWarmup, audience)` | 389-391 | returns 2; drop `isWarmup` |
| `introCopy(step, sideToMove, isWarmup, audience)` | 399-409 | drop `isWarmup` |
| `promptCopy` | 206-208 | `` `You play ${sideToMove}. Is there only one good move, or several?` `` [VERIFIED: trainBotCopy.ts:207] unchanged |
| `HILDA_ID` docstring | 36-40 | stale ("steps 2-3") — refresh comment |

Intro consumers: `TrainSolveScreen.tsx` `resolveIntroState` (400-417), `BubbleBodyDeps.isWarmup` (488-489), `renderTrainBotBubbleBody` intro branch (557-571), `resolveBubblePersona` (594-609, takes `isWarmup`), `useState<IntroStep>(0)` (654), `handleIntroNext` (1710-1712), `bubblePersona` call (1797-1804); `trainBubbleState.ts:26,34,56` (`IntroStep` type in the union). [VERIFIED: read this session]

**Reveal tour machinery:**
| Symbol | Location | Value / role |
|---|---|---|
| `WalkthroughStep`, `WALKTHROUGH_STEP_COUNT` | `trainBotCopy.ts:605-606` | `export type WalkthroughStep = 0 \| 1 \| 2 \| 3 \| 4 \| 5;` / `export const WALKTHROUGH_STEP_COUNT = 6;` [VERIFIED] |
| `WalkthroughTarget` | `trainBotCopy.ts:616` | `export type WalkthroughTarget = 'verdict' \| 'chips' \| 'tree' \| 'board' \| 'lines' \| 'bar';` [VERIFIED] (keep) |
| `WalkthroughContext` | `trainBotCopy.ts:632-636` | `{ analyzeOpens: 'game' \| 'position'; mergedChip: 'best' \| 'game' \| null; isDesktop: boolean }` [VERIFIED] → add answer kind |
| `TOUR_ICON_TOKEN` | `trainBotCopy.ts:642-646` | `{ rewind: '{rewind}', back: '{back}', forward: '{forward}' }` [VERIFIED] (keep) |
| step strings | `trainBotCopy.ts:648-669, 717-724` | `WALKTHROUGH_RESULT_*` replaced by P1-1 variants; `walkthroughActionsCopy` loses the Next sentence; `WALKTHROUGH_NEXT_PART` becomes P1-2 |
| `walkthroughCopy(step, ctx)` | `trainBotCopy.ts:681-708` | replace with part/step-id resolver |
| `useTrainWalkthrough` | `hooks/useTrainWalkthrough.ts` (whole file) | `resolveWalkthroughStep` gates on `settings.reveal_walkthrough_seen_at !== null` (line 107); `useState<WalkthroughStep>(0)` (140); `isLastStep = activeStep === WALKTHROUGH_STEP_COUNT - 1` (148); `leave()` → `stamp('reveal_walkthrough')` (196-199) [VERIFIED: grep -n this session] |
| overlay | `components/train/TrainTourOverlay.tsx` | Hilda avatar + bordered bubble (`TRAIN_BUBBLE_BORDER`), `TourStepCount` "n / m" (line 62), `data-testid="train-tour-overlay"` (107), reopen badge `btn-train-tour-reopen` |
| tour mount | `TrainSolveScreen.tsx:997-1038` | builds `TrainTourOverlay` with `stepCount={WALKTHROUGH_STEP_COUNT}`; telemetry `markWalkthroughActive()` (1035-1038) |
| Next routing | `TrainSolveScreen.tsx:1759-1772` | `walkthrough.consumeNext()` then `flushReviewOnNext()`, `walkthrough.leave()`; Analyze also calls `leave()` |
| Hilda exclusion | `TrainSolveScreen.tsx:1690-1692` | `const tourMaybePending = settings?.reveal_walkthrough_seen_at == null;` → `stage < 3` |
| Landing reminder gate | `TrainStartScreen.tsx:251` | `const onboardingDone = settings?.reveal_walkthrough_seen_at != null;` → stage-based |

**Stamp end-to-end (`reveal_walkthrough_seen_at`):**
| Layer | Location | Note |
|---|---|---|
| Migration (origin) | `alembic/versions/20260913_144712_7d6bb75aae54_phase_222_train_onboarding_seen.py:35-38` | added nullable `DateTime(timezone=True)` |
| Alembic head | `778c806092fb` | [VERIFIED: `uv run alembic heads` output "778c806092fb (head)"] new migration's `down_revision` |
| Model | `app/models/train_settings.py:144-146` | column; table CHECKs at 49-59 |
| Repo row | `app/repositories/train_repository.py:180` (`TrainSettingsRow`), 319 (`get_settings`), 367/388 (`get_or_create_settings`), 519/530/546 (`upsert_settings` RETURNING), 681 (`_ONBOARDING_COLUMNS`), 850 (`get_progress` row rebuild) | 7 sites |
| Schema | `app/schemas/train.py:723` `OnboardingStep = Literal["intro", "reveal_walkthrough", "sr_explained"]` [VERIFIED]; `:762` response field | |
| Router | `app/routers/train.py:486` (`_settings_response`), `:554-591` endpoint | |
| Script | `scripts/reset_train_state.py:28,210` | resets to None for UAT |
| FE type | `frontend/src/types/train.ts:379` | |
| FE hook | `useTrainOnboarding.ts:25` `export type OnboardingStep = 'intro' \| 'reveal_walkthrough' \| 'sr_explained';` [VERIFIED]; `api/client.ts:347-348` | |
| FE consumers | `useTrainWalkthrough.ts:107,198`, `TrainSolveScreen.tsx:1690`, `TrainStartScreen.tsx:251` | |
| Backend tests | `tests/routers/test_train.py:2662-2972` (onboarding + settings), `tests/repositories/test_train_repository.py:3923-4012`, `tests/scripts/test_reset_train_state.py:50,79` | |
| FE tests/fixtures | `TrainSolveScreen.test.tsx:259,3395,3773,4025,4292-4294,4426`, `TrainStartScreen.test.tsx:82,89,215,532,546`, `TrainScoreScreen.test.tsx:104`, `TrainReminderButton.test.tsx:117`, `Train.solveLoop.test.tsx:149` | fixture field rename |
| Analytics/admin/SQL | none in `app/`, `scripts/`, `frontend/src/pages/activity` | only the SEED-200 funnel SQL in the seed file [VERIFIED: repo-wide grep, excluding `.planning/milestones`] |

Guest handling: guests are real `users` rows with their own `train_settings` row (`test_guest_onboarding_stamp_200`, `tests/routers/test_train.py:2866`); promotion is an in-place `UPDATE users` (Phase 224 note in `trainBotCopy.ts:776-780`), so the stage carries over with no extra work. [VERIFIED: read this session]

**Verdict + score screen:**
- Verdict surface: `TrainReveal.tsx:376-390` picks `TrainVerdictCard` (desktop) or `TrainVerdictStrip` (phone); both take `ring={tourRingVerdict}` (`:305`). `verdict.puzzle_type` is on `SolveResponse` (`types/train.ts:286`: `puzzle_type: 'sharp' | 'soft' | 'herring';`). [VERIFIED]
- Score screen: `TrainScoreScreen.tsx` latch (222-229), `scoreBubbleCopy` call (230-243), stamp gate (248-254), props `sessionDate`/`expiresOn` (132-139) fed by `pages/Train.tsx:260-261`. `scoreBubbleCopy` + `returningCountsSentence` + `ScoreBubbleInput` at `trainBotCopy.ts:814-953`. [VERIFIED]

**Composition:** see Pattern 5.

### Recommended file touch list
```
app/models/train_settings.py          # drop reveal_walkthrough_seen_at, add reveal_tour_stage + CHECK
app/services/train_scheduler.py       # (or a train onboarding constants spot) REVEAL_TOUR_STAGE_MAX = 3, like SHIELD_CAP
alembic/versions/2026xxxx_..._phase_240_reveal_tour_stage.py
app/schemas/train.py                  # OnboardingStep literal + response field
app/repositories/train_repository.py  # row dataclass, 7 sites, advance helper, first-session reorder
app/routers/train.py                  # _settings_response + endpoint dispatch
scripts/reset_train_state.py          # reset stage to 0
frontend/src/lib/trainBotCopy.ts      # intro, tour parts, score bubble
frontend/src/hooks/useTrainWalkthrough.ts, useTrainOnboarding.ts
frontend/src/types/train.ts, api/client.ts (docstring)
frontend/src/components/train/{TrainSolveScreen,TrainReveal,TrainVerdictStrip,TrainMoveTreeList,
  TrainRevealActionBar,TrainScoreScreen,TrainStartScreen,trainBubbleState}.tsx/.ts
frontend/src/lib/mobileBoardControls.ts, App.tsx    # bar spotlight flag through the payload
frontend/src/index.css, frontend/src/lib/theme.ts   # keyframes + glow color
CHANGELOG.md
```

### Pattern 1: Stage advance through the existing onboarding endpoint (Claude's discretion, recommended)

**What:** Extend the path `Literal` with three step names that map, through a fixed dict, to a target stage. Same endpoint, same response, same client `stamp(step)` hook, no request body. Keeps T-222-02-03 (fixed dict, no `getattr`, no SQL interpolation).

**Why not `/{stage}` int path or a body:** a body breaks the "no body schema at all" contract of this endpoint (`routers/train.py:570-572`); an int `Literal` path param relies on Pydantic's lax string-to-int coercion for literals, which I did not verify. String literals need no coercion. [ASSUMED: Pydantic Literal[int] path coercion behavior not checked]

```python
# app/schemas/train.py  (names are a proposal, not existing values)
OnboardingStep = Literal["intro", "sr_explained", "reveal_tour_1", "reveal_tour_2", "reveal_tour_3"]
RevealTourStep = Literal["reveal_tour_1", "reveal_tour_2", "reveal_tour_3"]

# app/repositories/train_repository.py
_ONBOARDING_COLUMNS: dict[TimestampOnboardingStep, Any] = {   # "intro", "sr_explained" only
    "intro": TrainSettings.intro_seen_at,
    "sr_explained": TrainSettings.sr_explained_at,
}
_REVEAL_TOUR_TARGET_STAGE: dict[RevealTourStep, int] = {
    "reveal_tour_1": 1, "reveal_tour_2": 2, "reveal_tour_3": 3,
}

async def advance_reveal_tour_stage(
    session: AsyncSession, *, user_id: int, step: RevealTourStep
) -> TrainSettingsRow:
    """D-09: forward-only, idempotent. Advance to N only from N-1 (a replay or an
    out-of-order POST matches zero rows), mirroring stamp_onboarding_step's guarded UPDATE."""
    await get_or_create_settings(session, user_id=user_id)
    target = _REVEAL_TOUR_TARGET_STAGE[step]
    await session.execute(
        update(TrainSettings)
        .where(TrainSettings.user_id == user_id, TrainSettings.reveal_tour_stage == target - 1)
        .values(reveal_tour_stage=target)
    )
    refreshed = await get_settings(session, user_id=user_id)
    assert refreshed is not None
    return refreshed
```
Router: one guard-clause dispatch (`if step in _REVEAL_TOUR_STEPS: ... else: stamp_onboarding_step(...)`), inside the existing try/except + Sentry block. `ty` narrowing on `step in dict` may need a `cast`/`TypeGuard`; a small `is_reveal_tour_step(step) -> TypeGuard[RevealTourStep]` helper is the clean option. [ASSUMED: ty narrowing behavior on Literal membership not tested]

`now_utc` stays a parameter of the endpoint (still needed for the timestamp steps).

### Pattern 2: Tour as parts of named step ids (replaces `WalkthroughStep` 0..5)

```typescript
// frontend/src/lib/trainBotCopy.ts  (proposal)
export type TourStepId = 'result' | 'next' | 'chips' | 'stepping' | 'sidelines' | 'understand' | 'analyze';
export type TourPart = 0 | 1 | 2;
/** Mirrors the server's REVEAL_TOUR_STAGE max: stage 3 = tour done. */
export const TOUR_PART_COUNT = 3;
const TOUR_PARTS: Record<TourPart, readonly TourStepId[]> = {
  0: ['result', 'next'],
  1: ['chips', 'stepping'],
  2: ['sidelines', 'understand', 'analyze'],
};
export interface WalkthroughContext {
  analyzeOpens: 'game' | 'position';
  mergedChip: 'best' | 'game' | null;
  isDesktop: boolean;
  /** D-04: 'sharp' for SolveResponse.puzzle_type === 'sharp', else 'several' (soft or herring). */
  answerKind: 'sharp' | 'several';
}
export function tourPartSteps(part: TourPart): readonly TourStepId[] { return TOUR_PARTS[part]; }
export function tourStepCopy(step: TourStepId, ctx: WalkthroughContext): WalkthroughStepCopy { /* switch */ }
```
Spotlight targets per step: result→`verdict`, next→`bar`, chips→`chips`, stepping→`tree`, sidelines→`board`, understand→`lines`, analyze→`bar` (from the copy sheet). The `TourStepCount` then shows "n / partLength" (1/2, 1/2, 1/3). The budget test iterates every step id × context combination (now 4 boolean-ish axes: device, mergedChip, analyzeOpens, answerKind).

### Pattern 3: Hook latches the part once per reveal

**Problem:** `leave()` stamps and then `handleNext()` moves on; the stamp's `onSuccess` `setQueryData`s settings (`useTrainOnboarding.ts:30-35`). If a reveal is still mounted when the new stage lands (slow network then a fast next verdict, or the Analyze round trip restoring the same reveal), a hook that derives the part live from `settings.reveal_tour_stage` would jump to the next part mid-reveal, breaking D-07 "at most one part per reveal".

**Fix:** latch `part` when the verdict first lands for this puzzle (settings loaded, stage < 3), clear it in `reset()` (already called on every puzzle transition, `TrainSolveScreen.tsx:1127-1128`). Derive `activeStep` from the latched part and the per-reveal step index. A stale latch can only replay a part (the server no-ops the duplicate advance), never skip one.

```typescript
const [latchedPart, setLatchedPart] = useState<TourPart | null>(null);
useEffect(() => {
  if (latchedPart !== null || settings === undefined || !hasVerdict) return;
  const stage = settings.reveal_tour_stage;
  if (stage >= TOUR_PART_COUNT) return;
  setLatchedPart(stage as TourPart);
}, [latchedPart, settings, hasVerdict]);
// leave(): if on the part's last step → stamp(`reveal_tour_${latchedPart + 1}`)
```
Note: an effect-driven latch costs one render; to avoid a flash of "no tour" on the first verdict render, compute `part = latchedPart ?? liveStageIfEligible` for the render and latch in the effect (same render result either way). `OnboardingStep` on the client must mirror the server literal exactly; a template-literal type for the stamp (`` `reveal_tour_${1 | 2 | 3}` ``) keeps it typed.

Telemetry (Claude's discretion): keep `markWalkthroughActive()` firing whenever `activeStep !== null` (unchanged code at `TrainSolveScreen.tsx:1035-1038`), so `review_walkthrough: true` is reported on any reveal where a part ran.

### Pattern 4: Intro shrink

`introSteps(sideToMove, audience)` returns exactly `[welcome, closing]`; `IntroStep = 0 | 1`; `introStepCount(audience)` (or a constant `INTRO_STEP_COUNT = 2`, since the count never varies). Remove `isWarmup` from `BubbleBodyDeps`, `introCopy`, `resolveBubblePersona`, `handleIntroNext` (`isWarmup` stays in `TrainSolveScreen` for the reveal's `returnPhrase`). `introCopy`'s "index past the end resolves to the closing step" fallback (`trainBotCopy.ts:399-409`) stays, it protects a stale state value. Update `trainBubbleState.test.ts:76,93,107,121` (`introStep: 2` is no longer a valid `IntroStep`; vitest will not catch this, only `npm run build`).

### Pattern 5: First-ever session reorder (D-13..D-15)

**First-ever check placement:** in `compose_and_materialize_session`, after `_resolve_existing_session` returns `None` (`train_repository.py:2522-2526`) and before `_assemble_session_items` (`:2528`). `_discard_if_untouched_and_resized` runs `await session.execute(delete(DrillSession).where(DrillSession.id == drill_session.id))` (`:1572`), an immediate SQL DELETE on the same transaction, so an `EXISTS` issued afterwards no longer sees the discarded first session. [VERIFIED: train_repository.py:1568-1573, 1939-1944] `expire_stale_sessions` only changes status, so an expired (never played) first session still counts as a prior session (consistent with D-13 "any status"). Existing idiom for the check: `select(select(DrillItem.user_id).where(DrillItem.user_id == user_id).exists())` (`train_repository.py:618`). `drill_sessions` has no plain `user_id` index (only the partial unique `uq_drill_sessions_user_open`, `drill_session.py:55-60`), but the table is one row per user-day and other queries already filter it by `user_id` (`:760`, `:928`), so no index is needed. [VERIFIED: app/models/drill_session.py:44-60]

**Type classification seam (D-14):** compute types after the shuffle, only when `first_ever`, with the same function the verdict uses:
- `DrillSource.RED_HERRING` → `"herring"`; `DrillSource.SHARP_FILLER` → `"sharp"` (`answer_key_for`, `train_pool.py:386-389`: `return PuzzleAnswerKey(_herring_key(ladder), "herring", None)` / `return PuzzleAnswerKey(_non_empty_str(filler_solution_uci), "sharp", None)`). [VERIFIED]
- SR item → `classify_puzzle_type(missed_pv_lines, mover_color_for_ply(ply))` (`train_pool.py:390`), so one query for the SR keys' blobs. `GameFlaw.missed_pv_lines` is `deferred=True` (`app/models/game_flaw.py:121`), but selecting the column explicitly loads it. Cost: ≤ `n` rows by PK-ish key, only on a user's first composition ever. Calling `answer_key_for(..., best_move=None, ladder=None, filler_solution_uci=None).puzzle_type` reuses the single derivation verbatim (type does not depend on the key move). [VERIFIED: train_pool.py:363-392]

**Pure reorder helper** (unit-testable without a DB, depth ≤ 3):
```python
# Names are proposals. Constants avoid magic numbers.
_FIRST_SESSION_SEVERAL_SLOTS: tuple[int, ...] = (1, 2)  # D-15: puzzle 2 or 3
_SEVERAL_TYPES: frozenset[TrainPuzzleType] = frozenset({"soft", "herring"})

def _first_session_order(
    puzzles: Sequence[_ReconstructedPuzzle],
    types: Sequence[TrainPuzzleType],
    rng: random.Random,
) -> list[_ReconstructedPuzzle]:
    """D-13..D-15: sharp to slot 0, then a several puzzle into index 1 or 2.
    Runs AFTER the D-09 shuffle on the first-ever session only. Stable when no
    sharp (or no several) puzzle exists."""
    order = list(range(len(puzzles)))
    sharp = next((i for i in order if types[i] == "sharp"), None)
    if sharp is not None:
        order.insert(0, order.pop(order.index(sharp)))
    slots = [s for s in _FIRST_SESSION_SEVERAL_SLOTS if s < len(order)]
    if not slots or any(types[order[s]] in _SEVERAL_TYPES for s in slots):
        return [puzzles[i] for i in order]
    several = next((p for p, i in enumerate(order) if p > 0 and types[i] in _SEVERAL_TYPES), None)
    if several is None:
        return [puzzles[i] for i in order]
    target = rng.choice(slots)
    order[target], order[several] = order[several], order[target]
    return [puzzles[i] for i in order]
```
Determinism: seed the helper's rng from the same inputs as D-09 with a distinct suffix, e.g. `random.Random(f"{user_id}:{today.isoformat()}:first-session")`, so recomposition is reproducible. Move-vs-swap for slot 0: "move" (pop/insert) preserves the relative shuffled order of the rest; either satisfies D-13. `is_warmup`/`surviving_sr_keys` are unaffected (set-valued). Edge: `puzzles_per_session` can be 1 (`ck_train_settings_puzzles` 1..50), so `slots` must be clamped to the list length (done above).

**Where the type helper and reorder run:** inside `_assemble_session_items` right after line 2104 (the shuffle), gated by a new `first_ever: bool` argument, or as a separate stage between `_assemble_session_items` and `_materialize_session_rows` that returns a `replace(items, reconstructed=...)`. The second keeps `_assemble_session_items` free of an extra I/O step; either is fine for function size.

### Pattern 6: One shared pulsing spotlight (D-20)

Current spotlight sites [VERIFIED: read this session]:
| Target | Site | Today |
|---|---|---|
| verdict (phone strip) | `TrainVerdictStrip.tsx:63` | `ring && 'ring-2 ring-brand-brown'` |
| verdict (desktop card) | `TrainVerdictStrip.tsx:152` (`TrainVerdictCard`) | same |
| tree / lines | `TrainReveal.tsx:418-428` wrapper `data-testid="train-tree-tour-ring"` | `'rounded-md ring-2 ring-brand-brown'` |
| chips | `TrainReveal.tsx:408-416` `<div data-tour-target="chips">` | none (D-20: add) |
| board | `TrainSolveScreen.tsx:1881-1887` (`boardRef` row) | `ring-2 ring-brand-brown ring-offset-4 ring-offset-background` |
| bar (sm+, in flow) | `TrainSolveScreen.tsx:1959-1972` `<TrainRevealActionBar framed .../>` | none |
| bar (phone, fixed) | `App.tsx:478-503` `renderBoardControlsBar` → `TrainRevealActionBar`, inside `MOBILE_BOTTOM_BAR_CLASSES` = `'fixed bottom-0 inset-x-0 flex sm:hidden z-40 bg-background border-t border-border pb-safe'` (`App.tsx:466-467`) | none; payload type `lib/mobileBoardControls.ts` |
| dead prop | `TrainMoveTreeList.tsx:106` `ring` prop | never passed (only `TrainReveal` verdict props pass `ring=`); delete |

Glow value today: `FLAW_FIXED_GLOW = 'border border-[rgba(205,127,50,0.85)] shadow-[0_0_24px_rgba(205,127,50,0.35)]'` (`TrainFlawFixedBanner.tsx:29-30`). [VERIFIED]

Recommended shape: one class in `index.css` driven by a CSS variable for the color, applied through one exported constant (e.g. `TOUR_SPOTLIGHT_CLASS`), so every target uses `cn(..., isTarget && TOUR_SPOTLIGHT_CLASS)`:
```css
/* index.css, next to arrow-pulse / row-highlight-pulse */
.train-tour-spotlight {
  /* 2px ring + halo, both box-shadow: no layout shift (border width untouched) */
  box-shadow: 0 0 0 2px var(--tour-glow), 0 0 24px var(--tour-glow-halo);
  animation: train-tour-spotlight-pulse 1.6s ease-in-out infinite;
}
@keyframes train-tour-spotlight-pulse {
  0%, 100% { box-shadow: 0 0 0 2px var(--tour-glow), 0 0 12px var(--tour-glow-halo); }
  50%      { box-shadow: 0 0 0 2px var(--tour-glow), 0 0 28px var(--tour-glow-strong); }
}
@media (prefers-reduced-motion: reduce) {
  .train-tour-spotlight { animation: none; }
}
```
The color values (`rgba(205,127,50,0.85)` / `0.35`) belong in `lib/theme.ts` per frontend CLAUDE.md, or as `@theme`/`:root` CSS variables in `index.css` if the class consumes them; pick one source and reference it from both. Note the existing `index.css` precedent: components omit animation classes under reduced motion AND a `@media (prefers-reduced-motion: reduce)` block is the second line of defense (`index.css:529-535`). [VERIFIED: index.css:395-405, 529-535]

**Box-shadow vs Tailwind ring:** Tailwind `ring-*` is also a box-shadow; combining both on one element overwrites. The verdict strip/card's own `border-2` + `TRAIN_BUBBLE_BORDER` stays; the spotlight only adds box-shadow, so no layout shift.

**Phone bar:** add an optional `spotlight?: boolean` (name is a proposal) to `MobileBoardControls`, include it in the `useMemo` payload and deps (`TrainSolveScreen.tsx:1462-1493`), and pass `className={cn('flex-1', boardControls.spotlight && TOUR_SPOTLIGHT_CLASS)}` in `App.tsx`. An outward halo on a fixed bottom bar is partly off-screen at the bottom; if UAT finds it unreadable, use an inset variant (`inset 0 0 0 2px ...`) for the phone host only. The bar has `px-2 py-2` padding and no `overflow-hidden`, so a 2px outer ring on the inner `TrainRevealActionBar` should not clip; why Phase 237 saw clipping is unrecorded beyond the comment, so treat it as a UAT check. [VERIFIED: App.tsx:466-467,549-553; TrainRevealActionBar.tsx:100-107]

**Board overlay clipping:** `ChessBoard.tsx:547` sets `overflow: 'hidden'` on the board's own inner square; the spotlight goes on the outer `boardRef` row (as the ring does today), which is outside that clip. [VERIFIED: components/board/ChessBoard.tsx:547]

### Anti-Patterns to Avoid
- **Deriving the tour part live from settings** (mid-reveal part chaining, see Pattern 3).
- **Reordering after materialize** (positions are already inserted into `drill_solves`; reordering there means rewriting `position` on a unique-constrained table). Decide order before `_materialize_session_rows`.
- **Classifying SR "sharp" by source** (D-14 explicitly forbids; SR items are often soft, the default test blob `_MISSED_PV_LINES` is soft).
- **Concatenating old bubbles to make new ones** (D-06/D-19; budget 145).
- **Leaving `ScoreBubbleOutcome` / `WALKTHROUGH_STEP_COUNT` / `INTRO_*` exported after their last use** (knip fails CI).
- **Putting `data-umami-event` or a `trackFeature` on tour progress** (DB-known, see constraints).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Puzzle answer type at composition | A second sharp/soft rule | `answer_key_for(...).puzzle_type` (`train_pool.py:363-392`) | D-14 requires the verdict's exact classification; one derivation already shared by compose + solve |
| First-write-wins / forward-only stamp | Read-modify-write in Python | Guarded `UPDATE ... WHERE stage = N-1` | Atomic under concurrent POSTs, same as `stamp_onboarding_step` (`:714-718`) |
| Deterministic randomness | `Math.random`/`random.random()` | `random.Random(seed_str)` like D-09 (`:2104`) | Recomposition reproducibility |
| Icons in tour copy | New glyph strings | `TOUR_ICON_TOKEN` + `TourCopy` (`TrainTourOverlay.tsx`) | Phase 237 UAT fixed glyph drift this way |
| Phone scroll to target | New scroll code | existing `computeTourScrollDelta`/`animateScrollTop` in the hook | Already tuned (`WALKTHROUGH_SCROLL_DURATION_MS = 700`) |
| Migration backfill test | Ad-hoc SQL checks | `tests/test_migration_186_user_import_settings.py` pattern (downgrade → seed → upgrade → assert) | Established harness against the per-run DB |

## Runtime State Inventory

This phase retires a column (a data migration), so runtime state was checked:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Prod/dev `train_settings.reveal_walkthrough_seen_at` (non-null for every user who finished the 6-step tour) | **Data migration**: `UPDATE train_settings SET reveal_tour_stage = 3 WHERE reveal_walkthrough_seen_at IS NOT NULL` before the drop (D-10). The "before" funnel snapshot must be taken **before deploy**, since the column disappears. |
| Live service config | None. No Umami event or dashboard references the tour (grep `lib/analytics.ts`); no admin page reads the column (`frontend/src/pages/activity`, `app/services/activity_queries.py` grep clean). | None |
| OS-registered state | None (no cron/systemd job reads onboarding columns; reminder job reads `reminder_*` only). | None |
| Secrets/env vars | None. | None |
| Build artifacts / client caches | Installed PWA bundles and open tabs running the old JS: they read `reveal_walkthrough_seen_at` (now absent, `undefined`) and POST `reveal_walkthrough` (now 422). `trainRevealCache` (sessionStorage) holds verdict/bot/review state only, no tour state. | None by design (D-11 hard cut). Note: an old bundle sees `undefined != null` as false in `TrainStartScreen` and `undefined !== null` true in the old hook, i.e. an old tab replays the old tour and gets 422s until reload; accepted. |

## Common Pitfalls

### Pitfall 1: `sr_explained` stamp gate repeats the rationale forever for warm-up users
**What goes wrong:** `TrainScoreScreen.tsx:248` stamps only when `firstExplanation && !isWarmup && missedCount > 0`. D-17 puts the rationale in the warm-up and perfect branches too. Without widening, a zero-game guest (all sessions warm-up) or a user with consecutive perfect sessions keeps `sr_explained_at` null and sees the "first session" rationale every session.
**How to avoid:** stamp whenever the first-completed variant actually rendered: `showsFirstSessionCopy = firstExplanation` (bubble copy non-null). Consequence: a user whose first completed session is a warm-up never sees the regular "Reminders build the habit..." line later (warm-up line 2 already asks for reminders via `WARMUP_REMINDER_ASK_COPY`, and guests get the sign-up ask). Flagged in Open Questions for owner confirmation.
**Warning signs:** `TrainScoreScreen.test.tsx:485` ("a warm-up session ... stamps nothing") and `:499` (nothing-missed) currently assert no stamp; they must flip.

### Pitfall 2: Tour part chaining on one reveal
See Pattern 3. **Test:** render a reveal with stage 0, finish part 1 except the last Next, then `setQueryData` stage 1 mid-reveal; the overlay must stay on part 1.

### Pitfall 3: Hidden ordering assumptions in backend tests
**What goes wrong:** many repository/router tests compose a first session for a fresh user; the real committed `SHARP_SET` (`app/data/sharp_filler_puzzles.csv`, loaded at import in `app/services/sharp_filler.py`) fills shortfalls, so slot 0 will now often be a sharp filler where a test may expect an SR item at `puzzles[0]` / position 0. 13 `puzzles[0]`-style index sites exist across `tests/routers/test_train.py`, `tests/repositories/test_train_repository.py`, `tests/test_guest_auth.py`, `tests/test_imports_router.py`. [VERIFIED: grep count this session]
**How to avoid:** run the full backend suite right after the reorder lands; fix tests by selecting by source/identity instead of index, never by special-casing production code.

### Pitfall 4: Herring leak into later sessions
**How to avoid:** gate strictly on `first_ever`; test with a spy/monkeypatch on the reorder helper asserting it is not called when any prior `drill_sessions` row exists (any status, including `expired`), plus a pure-helper unit table. Prove the gate by reverting it and watching the test fail (project memory: mutation-test gap closures).

### Pitfall 5: First-ever check before the discard
**What goes wrong:** checking `EXISTS` before `_resolve_existing_session` would see the untouched/resized first session and skip the reorder for its recomposition. **How to avoid:** check after `resolved is None` (Pattern 5). Test: compose first session at n=6, change `puzzles_per_session`, compose again → still reordered.

### Pitfall 6: Warm-up first-session score line 1 is longer than CONTEXT estimated
CONTEXT says "~180 max". Measured this session: max line 1 = **230 chars** (red opener "Tough session. That is exactly what Train is for." + rationale + "Those were warm-ups." + the has_games_guest clause), vs 180 for today's warm-up line. Score bubble lines are not under `STEPPER_COPY_MAX_CHARS`, but D-16's 375x667 fold check must use this worst case (red band, guest with games, warm-up, first completed). [VERIFIED: python length computation over the copy-sheet strings]

### Pitfall 7: Type-level breakage invisible to vitest
`IntroStep` narrowing breaks `trainBubbleState.test.ts` literals (`introStep: 2`) and any `as IntroStep` casts; `TrainSettingsResponse` field swap breaks 5 fixture files. `npm test` passes regardless (esbuild strips types); only `npm run build` catches it (project memory). Include `npm run build` in each frontend task's verify step.

### Pitfall 8: Spotlight tests assert class names
`TrainSolveScreen.test.tsx:4043-4119` assert `className` contains/omits `'ring-2'` (strip, card, tree wrapper, board row, chips, action bar). These become assertions on the shared spotlight class; the "never rings the chips row" (`:4079`) and "nothing on the bar step" (`:4089-4119`) expectations invert under D-20.

### Pitfall 9: Old copy strings asserted in tests
`'Tap it'` (`TrainSolveScreen.test.tsx:4053,4074,4210`) changes to "Tap the strip"; `walkthroughCopy(5, ...)` expectations (`trainBotCopy.test.ts:736-741`) change because P3-3 drops the Next sentence; `introStepCount(...)).toBe(5/6)` (`trainBotCopy.test.ts:274,360-361`); returning-counts tests (`trainBotCopy.test.ts:784-983`, `TrainScoreScreen.test.tsx:534` "comes back" counts) are deleted or rewritten.

## Code Examples

### Migration (column swap with backfill)
```python
# Source pattern: alembic/versions/20260728_055940_f2624e60292e_phase_193_session_tick_shield.py:46-52
# (hard-coded CHECK literal in the migration; the model derives the bound from a constant).
# Column/constraint names below are proposals.
def upgrade() -> None:
    op.add_column(
        "train_settings",
        sa.Column("reveal_tour_stage", sa.SmallInteger(), server_default="0", nullable=False),
    )
    op.create_check_constraint(
        "ck_train_settings_reveal_tour_stage", "train_settings", "reveal_tour_stage BETWEEN 0 AND 3"
    )
    op.execute(
        "UPDATE train_settings SET reveal_tour_stage = 3 WHERE reveal_walkthrough_seen_at IS NOT NULL"
    )
    op.drop_column("train_settings", "reveal_walkthrough_seen_at")


def downgrade() -> None:
    # One-way in data terms (D-10): the original completion instant is gone.
    op.add_column(
        "train_settings",
        sa.Column("reveal_walkthrough_seen_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("UPDATE train_settings SET reveal_walkthrough_seen_at = now() WHERE reveal_tour_stage = 3")
    op.drop_constraint("ck_train_settings_reveal_tour_stage", "train_settings", type_="check")
    op.drop_column("train_settings", "reveal_tour_stage")
```
`down_revision = "778c806092fb"` (current head). Model: `reveal_tour_stage: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")` plus a `CheckConstraint(f"reveal_tour_stage BETWEEN 0 AND {REVEAL_TOUR_STAGE_MAX}", name=...)` in `__table_args__`, mirroring `shield_level` (`train_settings.py:52-54,85`). `get_or_create_settings` must set `reveal_tour_stage=0` in both the insert values and the returned row (`:338-390`). `TrainSettingsUpdate` must NOT gain the field (add a smuggle test like `test_put_settings_cannot_smuggle_onboarding_seen_timestamp`, `tests/routers/test_train.py:2977`).

### Composition hook-in
```python
# app/repositories/train_repository.py, compose_and_materialize_session (after :2526)
first_ever = not (
    await session.execute(
        select(select(DrillSession.id).where(DrillSession.user_id == user_id).exists())
    )
).scalar_one()
items = await _assemble_session_items(session, user_id=user_id, today=today, n=n)
if first_ever and items.reconstructed:
    types = await _composition_puzzle_types(session, user_id=user_id, puzzles=items.reconstructed)
    rng = random.Random(f"{user_id}:{today.isoformat()}:first-session")
    items = replace(items, reconstructed=_first_session_order(items.reconstructed, types, rng))
```
`_AssembledSessionItems` is a frozen dataclass (`:1972-1990`), so `dataclasses.replace` works (already imported for `_attach_answer_keys`, `:2406`).

### Score bubble (D-16..D-18) shape
```typescript
// ScoreBubbleInput loses outcomes/session_date/expires_on (only returningCountsSentence read them,
// verified: trainBotCopy.ts:866-889 is their only reader). TrainScoreScreen drops the sessionDate/
// expiresOn props; Train.tsx:260-261 stops passing them (nextSessionDate stays).
const PRACTICE_RATIONALE = 'Practice teaches you when to calculate and when a quick good move is enough.';
// first completed:  regular  -> [`${opener} ${PRACTICE_RATIONALE}`, `${HABIT} ${ask}`]
//                   perfect  -> [`Nothing got away today. ${PRACTICE_RATIONALE}`, `${HABIT} ${ask}`]
//                   warm-up  -> [`${opener} ${PRACTICE_RATIONALE} Those were warm-ups. ${clause}`, line2?]
// later:            regular  -> [`${opener} See you tomorrow.`]
//                   perfect  -> ['Nothing got away today.', ask-or-understanding-tip]
//                   warm-up  -> unchanged
```
`missedCount` still needs `solvedOutcomes` (`TrainScoreScreen.tsx:206-210`), so the `solvedOutcomes` prop stays.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 5-6 intro steps (Phase 222 split for phone height) | 2 steps, act within 1-2 taps | this phase | `IntroStep`/count/tests change |
| One 6-step tour on the first reveal, one timestamp | 3 parts over consecutive reveals, stage counter 0-3 | this phase | column swap, hook latch |
| Plain D-09 shuffle for every session | First-ever session: sharp slot 0 + several in slot 1-2 | this phase | only session 1 deviates |
| `ring-2 ring-brand-brown` spotlights | one pulsing bronze glow class | this phase | test class assertions change |

**Deprecated/outdated after this phase:** `reveal_walkthrough_seen_at`, `OnboardingStep` member `reveal_walkthrough`, `WALKTHROUGH_STEP_COUNT`, `WalkthroughStep` 0..5, `walkthroughCopy`, `returningCountsSentence`, `ScoreBubbleOutcome`, `INTRO_QUESTION/VOCABULARY/PRACTICE/WARMUP_COPY`, `TrainMoveTreeList.ring`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Pydantic `Literal[int]` path params may not coerce `"1"` → `1`; string step literals avoid the question | Pattern 1 | Low: recommendation already sidesteps it |
| A2 | `ty` may not narrow a `Literal` union via `step in dict`; a `TypeGuard` helper or `cast` may be needed | Pattern 1 | Low: compile-time only, fix during execution |
| A3 | Widening the `sr_explained` stamp to every first-completed branch is acceptable (owner has not explicitly confirmed losing the later "Reminders build the habit" line for warm-up starters) | Pitfall 1 | Medium: wrong choice either repeats the rationale forever or drops one habit line; confirm at plan review or UAT |
| A4 | Landing reminder ask (`TrainStartScreen.tsx:251`) should wait for the full tour (`stage >= 3`) to keep "onboarding is over" semantics | Open Q2 | Low: a one-line gate either way |
| A5 | Proposed names (`reveal_tour_stage` per CONTEXT, `ck_train_settings_reveal_tour_stage`, `reveal_tour_1..3`, `TourStepId`, `TOUR_SPOTLIGHT_CLASS`, `spotlight` payload field) | Patterns/Code | None: naming is discretionary |
| A6 | Phone fixed-bar outer glow is readable; fallback to inset glow if not | Pattern 6 | Low: UAT decides |

## Open Questions

1. **`sr_explained` stamp scope (Pitfall 1).** What we know: D-17 requires the rationale in all three first-completed branches; today's gate stamps in one. Recommendation: stamp whenever the first-completed variant rendered (any branch). Needs owner nod (A3).
2. **Landing reminder-ask gate** (`TrainStartScreen.tsx:251`). Options: `stage >= 3` (whole tour done, today's semantics) or `stage >= 1`. Recommendation: `>= TOUR_PART_COUNT` (`3`).
3. **Hilda exclusion as host** (`TrainSolveScreen.tsx:1690`): today Hilda is excluded while the tour is pending. With the split tour that is `stage < 3`, which can span several sessions for abandoners. Recommendation: keep `stage < 3` (she narrates any part on any reveal).
4. **Prod "before" funnel snapshot.** Requires the prod DB tunnel (`bin/prod_db_tunnel.sh`) and the `flawchess-prod-db` MCP, which executor subagents cannot call (project memory). Recommendation: a plan task executed by the orchestrator (or `checkpoint:human-action`), committing the result table under the phase dir (e.g. `240-FUNNEL-BEFORE.md`) before the migration ships. The SEED-200 SQL runs unchanged pre-deploy. Adapted post-deploy select:
   ```sql
   -- replace t.reveal_walkthrough_seen_at with t.reveal_tour_stage in CTE j, then:
   count(*) filter (where reveal_tour_stage = 0) as tour_part1_unfinished,
   count(*) filter (where reveal_tour_stage < 3) as tour_unfinished
   ```
5. **"n / m" counter in the overlay** per part (1/2) vs global (1/7). Recommendation: per part, since parts are separate experiences across reveals.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node / npm | frontend build/tests | ✓ | v24.19.0 / 11.17.0 | — |
| uv (Python) | backend tests, alembic | ✓ | 0.10.9 | — |
| Dev PostgreSQL (Docker) | pytest, alembic | ✓ | container `flawchess-dev-db-1` running | — |
| Prod DB tunnel + MCP | "before" funnel snapshot | orchestrator-only | — | human runs SQL and pastes result |
| Browser (Chrome extension) | mobile/desktop UAT at 390x844, 375x667, desktop | per project memory: orchestrator runs browser UAT itself | — | — |

Baselines run this session: `npx vitest run src/lib/__tests__/trainBotCopy.test.ts` → 106 passed (1.4 s); `uv run pytest tests/routers/test_train.py -k onboarding -q` → 8 passed (7.3 s).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (async, per-session cloned PostgreSQL DB, template auto-refreshes on Alembic head change) + Vitest (jsdom) |
| Config file | `pyproject.toml` / `tests/conftest.py`; `frontend/vite.config.ts` test block + `src/vitest.setup.ts` |
| Quick run (backend) | `uv run pytest tests/routers/test_train.py -k "onboarding or settings" -x` |
| Quick run (frontend) | `cd frontend && npx vitest run src/lib/__tests__/trainBotCopy.test.ts` |
| Full suite | `uv run pytest -n auto -x` and `cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| D-01 | intro is exactly [welcome, closing], count 2 for every audience and warm-up flag | unit | `npx vitest run src/lib/__tests__/trainBotCopy.test.ts -t intro` | ✅ (rewrite `:242-364`) |
| D-01 | puzzle 1 shows welcome → Next → closing with guess buttons; stamps `intro` once on guess | component | `npx vitest run src/components/train/__tests__/TrainSolveScreen.test.tsx -t "intro stepper"` | ✅ (rewrite `:3534-3672`) |
| D-02 | no warm-up step in intro; warm-up verdict tail unchanged | unit + component | same files; `returnPhrase` tests `trainBotCopy.test.ts:485-670` stay green | ✅ |
| D-03/D-04 | P1-1 copy per device × answer kind; `herring` and `soft` both map to several | unit + component | `-t "tour"` in both files (new cases using `verdict.puzzle_type`) | ❌ Wave 0 new cases |
| D-05 | no tour step mentions points | unit | budget/content test iterating all step ids | ❌ new |
| D-06 | parts = [result,next] / [chips,stepping] / [sidelines,understand,analyze]; every step ≤145 across all contexts; no em-dash | unit | `npx vitest run src/lib/__tests__/trainBotCopy.test.ts -t tour` | ✅ rewrite `:672-763` |
| D-07 | stage 1 shows part 2 on next reveal; at most one part per reveal even if stage changes mid-reveal | component | `TrainSolveScreen.test.tsx -t "tour"` (latch case) | ❌ new |
| D-08 | leaving last step stamps `reveal_tour_{n}` once; unmount/abandon mid-part stamps nothing | component | same | ✅ adapt `:4121-4147` |
| D-09 | advance N only from N-1; replay and out-of-order are no-ops; CHECK rejects 4 | router + repo | `uv run pytest tests/routers/test_train.py -k onboarding -x`; `tests/repositories/test_train_repository.py -k "onboarding or reveal_tour"` | ✅ adapt `:2883-2972`, `:3923-4012` |
| D-10 | migration backfills 3 where old column non-null, 0 otherwise; column gone; downgrade restores column | migration | `uv run pytest tests/test_migration_240_reveal_tour_stage.py -x` | ❌ Wave 0 (pattern `test_migration_186_user_import_settings.py`) |
| D-10 | PUT cannot smuggle `reveal_tour_stage`; GET exposes it, not the old field | router | `uv run pytest tests/routers/test_train.py -k "smuggle or exposes" -x` | ✅ adapt `:2960-2990` |
| D-11 | `POST /train/onboarding/reveal_walkthrough` → 422 | router | `-k unknown_step` style case | ✅ extend `:2883` |
| D-12 | `intro_seen_at` gating unchanged | router/component | existing intro tests | ✅ |
| D-13 | first-ever session reordered; recomposed resized first session still reordered; second session (any prior status incl. expired) not reordered | repo | `uv run pytest tests/repositories/test_train_repository.py -k first_session -x` | ❌ new |
| D-14 | slot 0 is type sharp (filler or sharp-blob SR); own-games session without sharp keeps shuffle order | unit (pure helper) + repo | `-k first_session` | ❌ new (use `_SHARP_KEYED_PV_LINES`/`_SOFT_KEYED_PV_LINES`, `test_train_repository.py:5341,5346`) |
| D-15 | a several puzzle sits at index 1 or 2 when one exists; deterministic for (user, day); n=1/2 safe | unit | `-k first_session` | ❌ new |
| D-16/D-17 | rationale in line 1 of all three first-completed branches; bubble stays 2 lines max | unit | `trainBotCopy.test.ts -t scoreBubbleCopy` | ✅ rewrite `:765-1060` |
| D-17 | `sr_explained` stamped once in warm-up/perfect/regular first-completed renders | component | `TrainScoreScreen.test.tsx -t "score bubble"` | ✅ flip `:485,:499` |
| D-18 | no "come back" / "Nothing else is coming back" in any branch; verdict return tails unchanged | unit | `trainBotCopy.test.ts` | ✅ |
| D-19 | exact copy strings | unit | string equality cases per variant | ❌ new |
| D-20 | each tour target carries the shared spotlight class; chips row highlighted; reduced-motion class/media rule present | component | `TrainSolveScreen.test.tsx -t "ring follows"` rewrite | ✅ rewrite `:4043-4119` |
| D-16/D-20 | score above fold at 375x667 (worst case 230-char line 1), glow not clipped, overlay reads as Hilda, mobile+desktop | manual UAT (browser) | — | manual-only: layout/visual |

### Sampling Rate
- **Per task commit:** the quick command for the touched area plus `npm run build` for any frontend type change.
- **Per wave merge:** `uv run pytest -n auto -x` (backend waves) / full frontend chain.
- **Phase gate:** full pre-merge gate from CLAUDE.md green, including `scripts/check_function_size.py app/ --fail-over-depth 4` and `npm run knip`.

### Wave 0 Gaps
- [ ] `tests/test_migration_240_reveal_tour_stage.py` (`BASE_REVISION = "778c806092fb"`: downgrade to it, seed one row with and one without `reveal_walkthrough_seen_at`, upgrade, assert stages 3/0 and column absent; use a fresh user-id range per that file's convention).
- [ ] First-session reorder tests in `tests/repositories/test_train_repository.py` (pure helper table + integration with sharp/soft blob fixtures + "not first-ever" spy).
- [ ] Tour latch test in `TrainSolveScreen.test.tsx`.
- No framework install needed.

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (unchanged; `current_active_user`) | FastAPI-Users |
| V3 Session Management | no | — |
| V4 Access Control | yes | user id only from `current_active_user.id`, never path/body (existing pattern, `routers/train.py:574-576`) |
| V5 Input Validation | yes | `Literal` path param, 422 before handler; DB `CHECK reveal_tour_stage BETWEEN 0 AND 3` |
| V6 Cryptography | no | — |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Mass assignment of server-owned stage via `PUT /train/settings` | Tampering | Field absent from `TrainSettingsUpdate`; smuggle test |
| SQL/column injection via step name | Tampering | fixed dict lookup, no `getattr`, no interpolation (T-222-02-03) |
| Client skipping/rewinding its own tour | Tampering (self only) | Forward-only guarded UPDATE; harmless to others |
| Herring position inference from fixed layout | Information disclosure (game integrity) | Reorder limited to first-ever session; slot 0 never-herring is the accepted leak (D-13) |

## Sources

### Primary (HIGH confidence, read this session)
- `.planning/phases/240-.../240-CONTEXT.md`, `240-DISCUSSION-LOG.md`, `.planning/seeds/SEED-200-...md`, `.planning/STATE.md`
- `frontend/src/lib/trainBotCopy.ts` (full), `hooks/useTrainWalkthrough.ts`, `hooks/useTrainOnboarding.ts`, `components/train/TrainBotStepper.tsx`, `TrainTourOverlay.tsx`, `TrainScoreScreen.tsx`, `TrainRevealActionBar.tsx`, `TrainSolveScreen.tsx` (380-660, 960-1050, 1680-1910), `TrainReveal.tsx` (295-438), `TrainVerdictStrip.tsx`, `TrainMoveTreeList.tsx`, `TrainStartScreen.tsx` (225-300), `trainBubbleState.ts`, `types/train.ts`, `lib/mobileBoardControls.ts`, `App.tsx` (462-560), `index.css` (292-540), `TrainFlawFixedBanner.tsx`
- `app/models/train_settings.py`, `app/models/drill_session.py`, `app/repositories/train_repository.py` (140-560, 660-860, 1520-2560, 2741-2800), `app/services/train_pool.py` (105-424, 1327-1345), `app/services/sharp_filler.py`, `app/routers/train.py` (455-591), `app/schemas/train.py` (715-775), Phase 222 and Phase 193 migrations, `scripts/reset_train_state.py`
- Test files: `TrainSolveScreen.test.tsx`, `trainBotCopy.test.ts`, `TrainScoreScreen.test.tsx`, `tests/routers/test_train.py`, `tests/repositories/test_train_repository.py`, `tests/test_migration_186_user_import_settings.py`

### Secondary / Tertiary
- None. No web or library documentation was needed; no external package is involved.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH, no new dependencies.
- Architecture: HIGH, every seam located in code with line numbers; discretionary shapes (endpoint naming, tour model) are recommendations.
- Pitfalls: HIGH for 1-3, 5, 7-9 (read in code); MEDIUM for the phone-bar glow readability (UAT).

**Research date:** 2026-10-15
**Valid until:** until the next change to `trainBotCopy.ts`, `useTrainWalkthrough.ts` or `train_repository.py` composition (fast-moving files; re-grep line numbers before executing).
