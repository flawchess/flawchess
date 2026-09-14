# Phase 222: Train Bot-Narrated Onboarding & Verdicts (SEED-166) - Context

**Gathered:** 2026-09-13
**Status:** Ready for planning

<domain>
## Phase Boundary

The Bots personas become the permanent voice of Train, delivered through one reusable
avatar + speech-bubble "chat row" component (sketch 003 winner A, sketch 004 Synthesis):

1. **Guess bubble** on every puzzle: a bot row under the board carries the guess
   question and the two decision buttons inside the bubble. First session only: a
   three-step intro stepper (Tank welcomes, Hilda defines the buttons, Hilda closes and
   the buttons appear). A piece dropped before the guess nudges the bubble and swaps its
   copy; no drop ever snaps back silently. The board is never covered.
2. **Verdict bubble** on every reveal: an outcome-matched bot (stern for 0–1 points,
   friendly for 2–3) speaks one verdict with the guess and move point pills inline and
   ends with when the position returns (from `SolveResponse.due_date`); herring, filler,
   mastered and parked items get no-return variants. Analyze / Next / Solution move
   inside the bubble; the reveal's sound toggle is retired (follow-up seed). First
   session only: a three-step Hilda walkthrough of the solution screen, each step
   spotlighting its element.
3. **Score bubble**: replaces the "Session complete" heading, states what returns and
   when (counts grouped by date), explains spaced repetition and the reminder's purpose,
   and only then the existing Remind me / Done row. Full explanation on the first
   completed session, one line afterwards.
4. **Server-side seen state** (three timestamps on `train_settings`, stamped by a
   dedicated endpoint when a stepper is completed), never device-local.
5. **Funnel metrics** on the superuser activity dashboard (`/activity`, Train sessions
   section): first-session 0-solve rate (baseline 42%) and second-session return
   (baseline 49%), cohorted by first-session date within the selected window.

Out of scope (ROADMAP): renaming the feature, bot images on the Train landing page,
harsh verdict copy, mapping bots to puzzle type, changing the daily reminder default,
push-channel changes, a pre-session SR onboarding page, the settings page that re-homes
the sound toggle.

</domain>

<decisions>
## Implementation Decisions

### Bot casting
- **D-01:** A `temperament: 'stern' | 'friendly' | 'smart'` field is added to `Persona`
  and set on all 24 registry entries (`frontend/src/lib/personas/personaRegistry.ts`).
  The Train sets are derived from it (no separate id lists). Draft mapping below in
  `<specifics>` for the user to review before planning; the executor uses whatever the
  reviewed table says. — **Reversibility:** costly — the field is typed into the
  exhaustive `Record<PersonaId, Persona>`; removing it touches all 24 entries and every
  Train cast site.
- **D-02:** The regular-session guess bubble is hosted by a **random smart bot per
  puzzle**, `Math.random`, not seeded and not persisted. A page reload may pick another
  bot; that is accepted (reloads are rare on the solve screen).
- **D-03:** The verdict bot is picked with `Math.random` per reveal from the stern set
  (0–1 points) or the friendly set (2–3 points). Points = `scorePuzzle(correct_guess,
  move_quality)` from `frontend/src/lib/trainScore.ts`. A restored reveal may show a
  different bot than the live one did; accepted.
- **D-04:** The score-screen bubble is spoken by a **random smart bot** regardless of the
  rating band.
- **D-05:** Teaching is always **Hilda** (`wall-1800`, temperament smart): intro steps 2
  and 3, and the first-reveal walkthrough. **Tank** (`grinder-1600`, stern) speaks intro
  step 1 only. The random smart host still asks the question on every later puzzle; on
  the very first puzzle the buttons appear in Hilda's step-3 bubble.
- **D-06:** Copy is authored **per outcome bucket with variants, never per bot**
  (ROADMAP SC7). Bot identity carries the face and name only.

### Bubble states (solve screen)
- **D-07:** One chat-row slot under the board persists through the whole puzzle: guess
  prompt with buttons → after the guess the SAME host bubble swaps copy to the move
  prompt ("Now play a move for white.") → while grading "Checking your move…" with the
  spinner → the outcome bot's verdict row replaces it when the reveal opens. No layout
  jump, no vanishing bot.
- **D-08:** A piece dropped while `guess === null` keeps the board locked, pulses /
  nudges the bubble into view and swaps its copy to the "Decide first, then move" line
  (sketch 003 drop state). `handlePieceDrop` must never return `false` silently.
- **D-09:** The guess vocabulary changes: the question is "Is there only one good move,
  or several?" and the buttons read **"Only one"** / **"Several"**. `GUESS_LABELS` in
  `frontend/src/lib/trainGuessLabels.ts` is the single source; the reveal's guess card
  header gets its own longer form ("Your call: only one good move" / "Your call: several
  good moves") because "Guess: Only one" is unreadable out of context. This resolves the
  375px two-line wrap from sketch 003 without stacking. `guessFeedbackProse` sentences
  stay as they are (locked wording).
- **D-10:** Action buttons (Analyze, Next, Solution once the board leaves the reveal
  position) move INSIDE the verdict bubble on their own row; the below-board
  Solution/Analyze/Next row in `TrainSolveScreen` is removed. The mobile bottom bar is
  unaffected (it only takes over during free-play exploration). The reveal's mute
  toggle is dropped; record its re-homing as a follow-up seed.

### Seen state (server-side)
- **D-11:** Three nullable `DateTime(timezone=True)` columns on `train_settings`:
  `intro_seen_at`, `reveal_walkthrough_seen_at`, `sr_explained_at`. Not one stage enum
  (the steps are not strictly ordered), not a boolean. — **Reversibility:** one-way —
  Alembic migration on a user-owned table; the columns become part of the
  `TrainSettingsResponse` contract.
- **D-12:** Stamped by the **client on stepper completion** through a dedicated endpoint
  (shape for the planner, e.g. `POST /train/onboarding/{step}` with a `Literal` step).
  Only a completed explanation counts: an abandoned stepper replays next time. NEVER via
  `PUT /train/settings` (full-replace body; the update schema must not carry these
  fields). The three timestamps are exposed read-only on `TrainSettingsResponse` so the
  client can branch without a second fetch.
- **D-13:** **No backfill.** The migration leaves all three NULL for every existing row;
  regulars, one-timers and never-finishers all see each stepper once. The first
  completed session's full SR explanation likewise shows once to everyone.
- **D-14:** Guests never reach any of this (every `/train/*` endpoint 403s guests), so no
  device-local fallback exists or is needed.

### Return dates and score data
- **D-15:** Return phrasing uses **server dates only**: `due_date <= session.expires_on`
  → "in the next session"; otherwise "in N days" with `N = due_date - session_date`.
  No client clock or timezone math anywhere. Failed items are "next session" by
  construction (`next_scheduled_day(today, weekday_mask)`).
- **D-16:** Never-returning items get **distinct lines**: `item_status == 'mastered'`
  (three spaced correct solves), `item_status == 'parked'` (leech shelf), and
  `source in ('red_herring', 'sharp_filler')` (warm-up). The verdict never promises a
  return for any of these. The score bubble counts mastered separately.
- **D-17:** `SolvedResult` (`app/schemas/train.py`, served in
  `TrainSessionResponse.solved_results`) is **extended with `source`, `item_status`,
  `due_date`**, the exact values `SolveResponse` already returned for the same
  positions (no new answer-key exposure; entries still carry no game_id/ply/best move).
  The score screen derives everything from this array, so it survives a reload and the
  phone handoff. — **Reversibility:** reversible — additive optional fields on an
  existing response.
- **D-18:** The score bubble lists returns as **counts grouped by when** ("Three come
  back next session, one in 4 days."), never per-position identifiers.

### Funnel metrics
- **D-19:** New card in the Train sessions section of the activity dashboard
  (`app/services/activity_queries.py` + `frontend/src/pages/activity/render.js` +
  `ActivityPage.tsx`): cohort = users whose FIRST drill session started inside the
  selected window; show first-session 0-solve share and second-session return share,
  each with numerator/denominator, plus an all-time line for the baselines (52/123 =
  42%, 26/53 = 49%). Moving the window before/after the release is the comparison.
  Definitions are the seed's: 0-solve = first session has no `solved_at`; return =
  users with ≥2 completed sessions / users with ≥1 completed.
- **D-20:** No Umami events for any of this: the DB knows every fact (frontend
  CLAUDE.md rule).

### Copy (starting points, tone locked)
- **D-21:** All copy below is **approved as a starting point**: the messages,
  structure and tone are locked; the planner/executor may tighten wording within the
  rules. Rules: encouraging voice, never a comment on the user, always forward-looking,
  no em-dashes, Tank may call it a boot camp, nothing harsh. Three messages must
  survive any edit: (a) these are not ordinary puzzles, they come from your own
  mistakes and teach when to spend time vs. play a good-enough move quickly; (b) the
  goal is understanding patterns with the analysis tools, not memorizing positions;
  (c) reminders build the habit that makes Train work.
- **D-22:** Group 1, guess bubble:
  - Intro 1 (Tank): "Welcome to FlawChess Train, my chess boot camp. These are not
    ordinary puzzles. Every position comes from a real game, and once enough of yours
    are analyzed, from your own mistakes. Nobody tells you whether a tactic is on the
    board. That is the point." [Next]
  - Intro 2 (Hilda): "In a game, every move starts with one question: is there only one
    good move here, or several? **Only one** means a single move works and everything
    else loses something. Take your time. **Several** means a normal position: pick a
    sensible move and keep going." [Next]
  - Intro 3 (Hilda): "That is the skill Train builds: knowing when to slow down and
    calculate, and when a good enough move played quickly is right. Decide first, then
    play. Your turn. You play white: is there only one good move, or several?"
    [Only one] [Several]
  - Regular prompt (random smart host): "You play white. Is there only one good move,
    or several?" [Only one] [Several]
  - Drop before guess (bubble pulses): "Decide first, then move. Only one good move
    here, or several?"
  - After guess: "Now play a move for white." Grading: "Checking your move…"
  - Reveal guess card header: "Your call: only one good move" / "Your call: several
    good moves". ("white" is always the puzzle's `side_to_move`.)
- **D-23:** Group 2, verdict bubble = opener (2 variants per points bucket) + clauses
  with inline pills + look-closer line (0–1 points only) + return tail:
  - 0 pts: "Not this time." / "Not quite." → "Wrong call [+0], wrong move [+0]."
  - 1 pt: "Close." / "Halfway there." → "Right call [+1], wrong move [+0]." or "Wrong
    call [+0], decent move [+1]."
  - 2 pts: "Nice." / "Solid." → "Right call [+1], decent move [+1]." or "Wrong call
    [+0], but the right move [+2]."
  - 3 pts: "Good job!" / "Clean." → "Right call [+1], right move [+2]."
  - Look-closer (0–1 pts): "Step through the best line and your own move to see why."
  - Tails: next session "We'll try this one again in the next session." / later "Let's
    see if you remember this in N days." / mastered "Three in a row. You have this one
    down, it won't come back." / parked "This one keeps slipping, so it is parked for
    now. On to positions that stick." / warm-up "That one was a warm-up, so it won't
    come back. Your own positions will."
- **D-24:** Group 3, first-reveal walkthrough (Hilda, Next / Next / Got it, each step
  spotlights its target: verdict bubble, line cards, action row):
  1. "This is your feedback. One point for the call, up to two for the move, and when
     this position comes back."
  2. "The cards are the lines: your move, the best move, and what was played in the
     game. Tap one to see it on the board and step through it. Understanding why a move
     fails is what makes the pattern stick."
  3. "Analyze opens the whole game one move before the mistake. Next takes you to the
     next puzzle."
- **D-25:** Group 4, score bubble (random smart bot; counts are live):
  - First completed session: "Session done. Three positions got away from you. They
    come back at growing gaps until you get them cold. The goal is not to memorize
    them: use the lines and the analysis board to understand the pattern, and the next
    position that looks like it will feel familiar. Three come back next session, one
    in 4 days. Train works when it is a habit, so turn on Remind me and let the next
    session find you."
  - Later sessions: "Three come back next session, one in 4 days. See you tomorrow."
    ("tomorrow" or the weekday name, from `expires_on`.)
  - Nothing missed: "Nothing got away today. All six come back later, at longer gaps."
  - Warm-up session (`is_warmup`, no SR items): "Those were warm-ups, nothing to bring
    back yet. Once your games are analyzed, your own mistakes take over. Turn on
    Remind me so the habit is there when they arrive."

### Claude's Discretion
- Chat-row visuals within the sketch: 56px avatar with the name under it, left-tail
  bubble, desktop layout of the row, pulse animation for the nudge, spotlight styling
  for the walkthrough (reuse the reveal's existing spotlight ring look).
- Exact endpoint path/verb for stamping the seen timestamps, and the `Literal` step
  names.
- Whether the smart host on the first puzzle is Hilda by construction (simplest: the
  first-session stepper renders Hilda's row and the buttons live in her last bubble).
- Test strategy for the random casts (inject the picker or stub `Math.random`).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Problem, evidence, delivery vehicle
- `.planning/seeds/SEED-166-train-first-session-retention.md` — prod funnel numbers,
  diagnosis of the two leaks, bot roles and tone rules, scope A/B/C, planning notes
  (`due_date` is None for herrings/filler; no seen flag exists; avatar art per persona).
- `.planning/ROADMAP.md` §"Phase 222" — goal, success criteria 1–7, out-of-scope list,
  cross-cutting constraints (no board overlay; complexity gate 15 for new code; the
  bubble is a new shared component, not more branches in `TrainSolveScreen` /
  `TrainReveal`).

### Design (winners; prose in them is placeholder, superseded by D-21..D-25)
- `.planning/sketches/003-train-bot-guess-bubble/README.md` and `index.html` — chat row
  under the board, buttons inside the bubble, first-session 3-bubble stepper, drop
  state, after-guess state.
- `.planning/sketches/004-train-bot-verdict-and-score/README.md` and `index.html` —
  verdict row directly under the board with inline pills and the action row inside the
  bubble; Hilda walkthrough steps with spotlight targets; score bubble replacing the
  heading.
- `.planning/sketches/MANIFEST.md` §003/§004 — the recorded winner rationale.

### Metrics surface
- `docs/activity-dashboard.md` — layout of the superuser activity dashboard, the
  React/imperative seam (`render.js` addresses DOM ids), read-only engine, and the
  mobile layout harness `npm run check:activity-layout` that must stay green.

### Frontend rules
- `frontend/CLAUDE.md` — testids on every interactive element, `text-sm` floor, Button
  variants (`default` primary, `brand-outline` secondary), no Umami for DB-known facts.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/lib/personas/personaRegistry.ts` (`PERSONA_REGISTRY`, `Persona`,
  `personaForId`) and `personaAvatars.ts` (`resolveAvatarSrc`, `placeholderAvatarFor`):
  all 24 personas have curated 128px WebP art, so every persona is castable.
- `frontend/src/components/bots/PersonaCard.tsx`, `ClockDisplay.tsx`,
  `PersonaDetailSurface.tsx`: existing avatar render sites to mirror for the chat row's
  image + fallback.
- `frontend/src/lib/trainGuessLabels.ts`: `Guess`, `GUESS_LABELS`, `guessFeedbackProse`
  (locked sentences).
- `frontend/src/lib/trainScore.ts`: `scorePuzzle`, `GUESS_POINTS`, `MOVE_TIER_POINTS`,
  `TRAIN_POINTS_PER_PUZZLE`; `TrainReveal.tsx`'s `TrainScoreChip` is the existing
  `+N` pill (reuse for the inline pills).
- `TrainReveal.tsx` spotlight mechanism (`SpotlightEntry`, `ring-2 ring-brand-brown`)
  for the walkthrough's element highlighting.
- `TrainLineStepper.tsx`: an existing stepper shape for prev/next controls.
- `app/schemas/train.py`: `SolveResponse` (`due_date`, `source`, `item_status`),
  `SolvedResult`, `TrainSessionResponse` (`session_date`, `expires_on`, `is_warmup`),
  `TrainSettingsResponse` / `TrainSettingsUpdate` (separate schemas so a PUT can never
  smuggle server-owned fields; keep that split for the new timestamps).
- `app/services/activity_queries.py` (`fetch_train`, `fetch_solves`) and
  `frontend/src/pages/activity/render.js` (`renderTrainCard`) for the funnel card.

### Established Patterns
- Guess buttons and prompts live in `TrainSolveScreen.tsx` ~L1132-1165; the
  Solution/Analyze/Next row ~L1042-1095 (with the mute toggle); `handlePieceDrop`
  ~L541 returns `false` while `guess === null` (the silent snap-back to fix).
- `TrainScoreScreen.tsx` gets `score` + `nextSessionDate` (= `expires_on`) from
  `pages/Train.tsx`; `useTrainSession.ts` seeds the score from `solved_results`, so the
  extended `SolvedResult` flows through the same hook.
- `train_settings` columns use `DateTime(timezone=True)` nullable instants for
  client-stamped moments (`reminder_intent_at` precedent) and are applied at the app
  layer in `train_repository.get_or_create_settings`.
- Router convention: `APIRouter(prefix="/train")`, relative paths; `_reject_guest`
  guards every endpoint.
- Time-dependent endpoints take `now_utc` from `dev_now_utc` (`app/core/dev_clock.py`).
- Both `TrainSolveScreen.tsx` (1222 lines) and `TrainReveal.tsx` (1365 lines) are
  already large: the chat row, steppers and copy tables are NEW modules
  (`components/train/TrainBotBubble.tsx`-style + a `trainBotCopy.ts`), not added
  branches. Complexity gate 15 applies to new code.

### Integration Points
- Solve screen slot under the board (replaces the prompt/buttons block and the action
  row); reveal top (verdict row above every card); score screen top (replaces the
  heading); `TrainSettingsResponse` + new stamping endpoint; Alembic migration for the
  three columns; activity dashboard Train section (query + payload TypedDict +
  `types/activity.ts` mirror + render card + layout harness fixture).

</code_context>

<specifics>
## Specific Ideas

### Draft temperament mapping (D-01) — REVIEW BEFORE PLANNING
Drawn from each persona's bio. Seed anchors kept except Hilda and Rocco, which move to
`smart` because Hilda is the fixed teacher and smart bots host the guess bubble.

| Temperament | Personas |
|---|---|
| stern (8) | Talon the Falcon (attacker-1200), Fury the Wolverine (attacker-1400), Butch the Ram (attacker-1600), Diesel the Bull (attacker-1800), Cackle the Hyena (trickster-1800), Nell the Penguin (grinder-1400), Tank the Ox (grinder-1600), Gus the Gorilla (grinder-1800) |
| smart (7) | Vix the Fox (trickster-1200), Riko the Raccoon (trickster-1400), Sly the Coyote (trickster-1600), Dig the Mole (grinder-1000), Otto the Otter (grinder-1200), Rocco the Armadillo (wall-1600), Hilda the Hippo (wall-1800) |
| friendly (9) | Ziggy the Wasp (attacker-800), Duke the Terrier (attacker-1000), Miko the Magpie (trickster-800), Slinky the Ferret (trickster-1000), Pip the Ant (grinder-800), Sheldon the Snail (wall-800), Spike the Hedgehog (wall-1000), Shelly the Turtle (wall-1200), Bruno the Badger (wall-1400) |

### Other specifics
- Anki-style framing: the return date is the last thing the verdict says.
- Stern face, encouraging voice: a stern bot on 0–1 points still looks forward.
- Sketch 004's "parked until due again" line for correctly solved items is wrong
  terminology; correct items are `active` with a later `due_date`, "parked" is the
  leech shelf (D-16).

</specifics>

<deferred>
## Deferred Ideas

- **Sound toggle re-homing**: the reveal's mute toggle is retired in this phase; a
  settings page that re-homes it is a follow-up seed (ROADMAP asks for the seed to be
  recorded at phase close).
- **Bot face in the points pop over the board** (seed nice-to-have): not in scope
  unless trivially free inside the new component.
- **Bot images on the Train landing page**: revisit after the metrics have a
  post-change reading (seed).

### Reviewed Todos (not folded)
- WR-01 `pt-33` Tailwind class on the Score Y-axis label — a chart bug in a different
  surface, not Train.
- 172 deferred review findings, bitboard storage for partial-position queries,
  variation-tree nested button — keyword matches only, unrelated to this phase.

</deferred>

---

*Phase: 222-train-bot-narrated-onboarding-and-verdicts*
*Context gathered: 2026-09-13*
