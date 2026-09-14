# Phase 222: Train Bot-Narrated Onboarding & Verdicts - Research

**Researched:** 2026-09-13
**Domain:** React 19 component extraction on two already-baselined large components + FastAPI/Alembic nullable-timestamp columns + a read-only analytics SQL card
**Confidence:** HIGH (every structural claim below was read out of the working tree this session; the two SQL drafts were executed against the dev database)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

*(Copied verbatim from `.planning/phases/222-.../222-CONTEXT.md` `<decisions>`.)*

#### Bot casting
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

#### Bubble states (solve screen)
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

#### Seen state (server-side)
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

#### Return dates and score data
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

#### Funnel metrics
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

#### Copy (starting points, tone locked)
- **D-21..D-25:** see `222-CONTEXT.md` `<decisions>` — the four copy groups (guess
  bubble, verdict bubble, first-reveal walkthrough, score bubble) are approved as
  starting points; messages, structure and tone are locked, wording may be tightened
  within the rules (encouraging voice, never a comment on the user, always
  forward-looking, no em-dashes, nothing harsh). The three messages that must survive
  any edit are in D-21.

### Claude's Discretion
- Chat-row visuals within the sketch: 56px avatar with the name under it, left-tail
  bubble, desktop layout of the row, pulse animation for the nudge, spotlight styling
  for the walkthrough (reuse the reveal's existing spotlight ring look).
- Exact endpoint path/verb for stamping the seen timestamps, and the `Literal` step
  names.
- Whether the smart host on the first puzzle is Hilda by construction (simplest: the
  first-session stepper renders Hilda's row and the buttons live in her last bubble).
- Test strategy for the random casts (inject the picker or stub `Math.random`).

### Deferred Ideas (OUT OF SCOPE)
- **Sound toggle re-homing**: the reveal's mute toggle is retired in this phase; a
  settings page that re-homes it is a follow-up seed (ROADMAP asks for the seed to be
  recorded at phase close).
- **Bot face in the points pop over the board**: not in scope unless trivially free
  inside the new component.
- **Bot images on the Train landing page**: revisit after the metrics have a
  post-change reading.
- Reviewed todos not folded: WR-01 `pt-33` Score Y-axis label; 172 deferred review
  findings; bitboard storage; variation-tree nested button.

**Out of scope (ROADMAP):** renaming the feature, bot images on the Train landing page,
harsh verdict copy, mapping bots to puzzle type, changing the daily reminder default,
push-channel changes, a pre-session SR onboarding page, the settings page that re-homes
the sound toggle.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

No active `REQUIREMENTS.md` exists for this milestone; the planner mints `TRAINBOT-NN`
IDs (same pattern as Phases 204–221). Suggested minting, derived from ROADMAP §Phase 222
success criteria 1–7 and the locked decisions, with the research that enables each:

| Suggested ID | Description (from SC / D) | Research Support |
|----|-------------|------------------|
| TRAINBOT-01 | A first-time user cannot reach a silent failure: first puzzle opens with the bot intro stepper; guess buttons sit inside the last bubble; a drop before the guess nudges the bubble and changes its copy (SC1, D-08, D-22) | §Pattern 2 (chat-row slot state machine), §Pitfall 2 (`handlePieceDrop` must return `true`-with-no-move is illegal — see the correct shape), §Code Example 1 |
| TRAINBOT-02 | Every puzzle in every session shows the guess prompt inside a bot bubble; the board is fully visible above it at 375px with the longest first-session copy (SC2, D-02, D-07) | §Finding H (`useFitBoardToViewport` auto-shrinks the board; floor 240px is the risk), §Pitfall 6 |
| TRAINBOT-03 | Every reveal shows an outcome-matched bot line with inline point pills ending in the return date for SR items, and a no-return variant for herring/filler/mastered/parked (SC3, D-03, D-15, D-16, D-23) | §Finding E (`due_date`/`expires_on` semantics verified), §Finding A (where the verdict row must live), §Code Example 3 |
| TRAINBOT-04 | The score screen states what returns and when before the reminder ask; first completed session gets the full SR explanation, later ones a single line (SC4, D-04, D-18, D-25) | §Finding C (a live accumulator is required — D-17 alone is insufficient) |
| TRAINBOT-05 | Explanation-seen state is stored server-side and survives a device switch (SC5, D-11, D-12, D-13, D-14) | §Backend seam (migration template, `get_or_create_settings`, `TrainSettingsResponse`), §Finding D (settings are already cached app-wide) |
| TRAINBOT-06 | Both funnel metrics have a recorded baseline and a repeatable query, so the post-change reading is one run (SC6, D-19, D-20) | §Finding J (both queries drafted and executed against the dev DB) |
| TRAINBOT-07 | Bot copy is authored per outcome bucket with a few variants, never per persona; the stern/friendly/smart sets come from a `temperament` field (SC7, D-01, D-06) | §Persona registry seam (all 24 have curated art; no generator/test blocks a new field) |
| TRAINBOT-08 | The guess vocabulary changes to "Only one" / "Several" everywhere it is surfaced (D-09) | §Pitfall 8 (three call sites + two test assertions + one marketing line) |
| TRAINBOT-09 | Analyze / Next / Solution move inside the verdict bubble; the reveal's mute toggle is retired (D-10) | §Finding F (keep the testids), §Pitfall 9 (`/bots` becomes the only mute control) |
</phase_requirements>

---

## Project Constraints (from CLAUDE.md)

Directives the planner must not contradict. All confirmed present in
`./CLAUDE.md` and `./frontend/CLAUDE.md` this session.

| Constraint | Source | Consequence for this phase |
|---|---|---|
| `uv run ty check app/ tests/ scripts/` must be zero errors; explicit return types on all functions | CLAUDE.md §Coding Guidelines | New router handler, repo function, and schema need annotations |
| Never bare `str` for a fixed value set — `Literal[...]` in schemas, signatures, return types | CLAUDE.md §Coding Guidelines | The onboarding step name is `Literal["intro", "reveal_walkthrough", "sr_explained"]` (names are Claude's discretion) |
| Avoid native PG `ENUM`; low-volume domain columns use TEXT + CHECK | CLAUDE.md §Database design rules | N/A here — D-11 locks three nullable timestamps, no new categorical column |
| FK constraints mandatory with explicit `ondelete` | CLAUDE.md §Database design rules | N/A — columns land on the existing `train_settings` (PK = `user_id`, already `ondelete="CASCADE"`) |
| Router convention: `APIRouter(prefix=...)` + relative decorator paths | CLAUDE.md §Architecture | The stamp endpoint decorator must be relative, e.g. `@router.post("/onboarding/{step}")` under the existing `prefix="/train"` |
| Routers hold no business logic; services hold logic; repositories hold all SQL | CLAUDE.md §Architecture | The stamp UPDATE belongs in `app/repositories/train_repository.py`, not the router |
| Time-dependent endpoints take `now_utc` from `dev_now_utc` | CLAUDE.md §Scripts & tooling | The stamp endpoint must take `NowUtc`, never `datetime.now()` |
| `sentry_sdk.capture_exception()` in non-trivial `except` in services/routers; no variables in error message strings | CLAUDE.md §Error Handling | Mirror the existing `/train/*` handlers' try/rollback/`set_context`/`capture` shape |
| Never `asyncio.gather` on the same `AsyncSession` | CLAUDE.md §Critical Constraints | Execute new queries sequentially |
| Nesting depth soft 3 / hard 4; logic LOC soft 100 / hard 200; cognitive ≤15 | CLAUDE.md §Coding Guidelines | New modules only — see §Finding B |
| Frontend: `data-testid` on every interactive element, kebab-case, component-prefixed | frontend/CLAUDE.md §Browser Automation | Every new button/stepper control needs one; naming `btn-{action}` |
| Frontend: `text-sm` is the floor, never `text-xs` | frontend/CLAUDE.md §Code Style | Bot name under the avatar, point pills, bubble copy all at `text-sm` minimum |
| Frontend: primary = `variant="default"`, secondary = `variant="brand-outline"`; never hand-rolled button colors | frontend/CLAUDE.md §UI | Guess buttons stay `brand-outline` (they are a pair, neither is the CTA); Next stays `default` |
| Frontend: theme colors live in `lib/theme.ts` | frontend/CLAUDE.md §Code Style | A bubble border/pulse color must be a `theme.ts` constant, not an inline hex |
| Frontend: `noUncheckedIndexedAccess` is on | frontend/CLAUDE.md §Code Style | `COPY_VARIANTS[bucket][idx]` needs narrowing or `!` |
| Frontend: knip runs in CI (dead exports fail the build) | frontend/CLAUDE.md §Code Style | Every new export must be imported somewhere |
| Frontend: `complexity` 15 / `max-depth` 4 / `max-statements` 100 at **error**; the override region is a Phase 215 snapshot, **not** an escape hatch for new code | frontend/CLAUDE.md §Code Style | See §Finding B — the Train baseline is pinned at exactly 68 |
| No Umami for facts the DB already knows | frontend/CLAUDE.md §Outbound link tracking | D-20 — no events at all for this phase |
| Pre-merge gate is mandatory before the squash-merge to `main` | CLAUDE.md §Version Control | Full command list reproduced in §Validation Architecture |
| `bin/reset_db.sh` requires explicit user permission | CLAUDE.md §Scripts & tooling | Use `scripts/reset_train_state.py --user-id N` for UAT replay — see §Finding I |
| Changelog is not optional | CLAUDE.md §Version Control | `## [Unreleased]` bullet at merge |

---

## Summary

This phase is almost entirely **extraction and relocation**, not new machinery. Every
piece of data it needs already crosses the wire: `SolveResponse` already carries
`source`, `item_status` and `due_date`; `TrainSessionResponse` already carries
`session_date`, `expires_on` and `is_warmup`; all 24 personas already have curated 128px
WebP art with a resolver; `scorePuzzle` already produces the 0–3 bucket the verdict copy
keys on; the reveal already owns a spotlight ring look. The only genuinely new server
surface is three nullable timestamps plus one stamping endpoint, and one read-only SQL
card on the superuser dashboard.

Four findings change how the phase should be planned, and three of them are not visible
from the CONTEXT document. **(A)** the verdict chat row must live in `TrainSolveScreen`'s
**board column**, not at the top of `TrainReveal`, or D-07's "no layout jump" breaks on
desktop where the reveal is a separate column. **(B)** `TrainSolveScreen` and
`TrainReveal` are baselined in `eslint.config.js` at complexity **exactly 68** — their
current measured value — so a single new `&&` or ternary in either function body fails
`npm run lint`; the ROADMAP's "new modules, not more branches" constraint is
mechanically enforced, not advisory. **(C)** D-17 alone cannot feed the score bubble: the
session response's `solved_results` is fetched once at compose/resume and is **empty**
for a session played start-to-finish in one sitting, so `useTrainSession` needs a live
per-solve accumulator seeded from `solved_results`. **(D)** `useTrainSettings` is already
mounted app-wide in `App.tsx` for every non-guest, so the solve screen can read the three
new flags off the shared TanStack cache with zero extra network cost — D-12's
"without a second fetch" claim holds.

The riskiest single success criterion is SC2 (board fully visible at 375px with the
longest first-session copy). `useFitBoardToViewport` already shrinks the board
automatically as the column's non-board height grows, but it floors at 240px, and
Intro 2 is the longest copy in the phase. That is a real UAT gate, not a code review item.

**Primary recommendation:** Build three new modules — `TrainBotBubble.tsx` (avatar +
bubble + optional button row, pure presentational), `trainBotCopy.ts` (all copy tables,
the outcome-bucket resolver, the return-phrase resolver, and an injectable `rng` picker,
all pure), and `TrainBotStepper` state inside `TrainSolveScreen` — then **move** the
existing guess block and the existing Solution/Analyze/Next row into the bubble
**keeping every `data-testid` unchanged**, which keeps roughly 140 existing test
assertions green.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Bot casting (which persona speaks) | Browser / Client | — | Pure presentation over a client-side registry (`personaRegistry.ts`); the server has no persona concept for Train |
| Copy tables and outcome-bucket resolution | Browser / Client | — | D-06/D-21: copy is per outcome bucket, derived from values already on `SolveResponse`; no server round trip |
| Return-date phrasing ("next session" / "in N days") | Browser / Client | API (supplies the dates) | D-15: the server owns both dates (`due_date`, `expires_on`, `session_date`); the client only compares and subtracts them — no clock, no timezone |
| Explanation-seen state | API / Backend | Database | D-12/D-14: must survive the phone handoff; guests never reach it; the client only reads and stamps |
| Per-puzzle SR outcome (`source`/`item_status`/`due_date`) | API / Backend | Database | Already server-computed in `record_solve`; D-17 re-serves it on the resume path |
| Score-screen session recap | Browser / Client | API (seed on resume) | Live accumulation in `useTrainSession`, seeded from the server's `solved_results` so a reload/handoff recovers it |
| Funnel metrics | Database | API (read-only engine) | D-19/D-20: the DB knows every fact; the dashboard's read-only engine already exists |
| Board rendering / drop validation | Browser / Client | — | Unchanged — `handlePieceDrop` stays where it is |

---

## Standard Stack

**This phase adds no new package to either ecosystem.** Every library it needs is
already a direct dependency, verified in the working tree this session.

### Core (existing, no version change)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `date-fns` | `^4.4.0` `[VERIFIED: frontend/package.json:31]` | `parseISO` + `differenceInCalendarDays` for the D-15 "in N days" arithmetic | Already the project's date library; `TrainScoreScreen.tsx:33` already does `format(parseISO(nextSessionDate), 'MMM d, yyyy')` |
| `lucide-react` | existing | Stepper chevrons / Search icon on Analyze | Already imported by `TrainSolveScreen.tsx:38` and `TrainLineStepper.tsx:35` |
| `@tanstack/react-query` | existing | The shared `['train','settings']` cache the seen-flags ride on | Already app-wide (`App.tsx:627,630`) |
| Tailwind CSS | existing | Bubble/tail/nudge styling | Sketch 003's bubble is pure CSS (border + two `::before`/`::after` triangles) |
| SQLAlchemy 2.x async + Alembic | existing | Three `DateTime(timezone=True)` columns | Precedent migration is 39 lines end to end |
| Pydantic v2 | existing | `Literal` step name, extended `SolvedResult` | Existing schema conventions |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `differenceInCalendarDays(parseISO(a), parseISO(b))` | the module-private `parseDate` in `frontend/src/lib/utils.ts:10-17` + manual `Math.round(ms/86400000)` | The utils helper is not exported and the manual form is the DST-fragile idiom date-fns exists to replace. `differenceInCalendarDays` is DST-exact by construction — verified below. Use date-fns. |
| `vi.spyOn(Math, 'random')` in component tests | an injected `rng: () => number` parameter on the picker | Both have precedent (`SetupScreen.test.tsx:138`, `chessClock.ts:233`). Recommendation: **do both** — the pure picker in `trainBotCopy.ts` takes `rng = Math.random` so its unit tests are deterministic with no global patching; component tests use `vi.spyOn` for the rendered cast. |
| A new "onboarding stepper" built on `TrainLineStepper` | a plain `step` index in the bubble | `TrainLineStepper` is a **chess move** stepper (replays SAN from a FEN, reports board positions) — not reusable. See §Pitfall 4. |

**Installation:** none.

**Version verification:**
```bash
# Ran this session:
node -e "require('date-fns/package.json').version"   # -> 4.4.0
```

## Package Legitimacy Audit

**Not applicable — this phase installs no external package.** No `npm install`, no
`uv add`. Every import in the plan resolves to a module already in `package.json` /
`pyproject.toml` or to a file inside the repository.

- Packages removed due to `[SLOP]` verdict: none.
- Packages flagged `[SUS]`: none.

---

## Architecture Patterns

### System Architecture Diagram

```
                             ┌─────────────────────────────────────────┐
   App.tsx (every protected  │  GET /train/settings                    │
   route, non-guest)   ──────►  TrainSettingsResponse                  │
   useReminderResurface /    │  + intro_seen_at                        │
   useDevicePushResync       │  + reveal_walkthrough_seen_at   (NEW)   │
        │                    │  + sr_explained_at                      │
        │  populates         └─────────────────────────────────────────┘
        ▼
  TanStack cache ['train','settings']      ◄──── setQueryData on stamp success
        │                                              ▲
        │ read (cache hit, no extra fetch)              │
        ▼                                              │
 ┌───────────────────────────────────────┐   POST /train/onboarding/{step}
 │ Train.tsx                             │──────────────┘  (NEW, _reject_guest,
 │  ├─ TrainStartScreen                  │                  dev_now_utc, returns
 │  ├─ TrainSolveScreen  ◄── the phase   │                  TrainSettingsResponse)
 │  └─ TrainScoreScreen      lives here  │
 └───────────────────────────────────────┘
                │
   ┌────────────┴──────────────────────────────────────────────┐
   │ TrainSolveScreen — BOARD COLUMN (columnRef, measured)      │
   │   progress bar                                            │
   │   ChessBoard  ◄── handlePieceDrop (drop-before-guess       │
   │   eval bar         now nudges instead of silently          │
   │                    returning false)                        │
   │   ┌─────────────────────────────────────────────┐         │
   │   │ TrainBotBubble  (NEW — the one chat slot)   │  D-07   │
   │   │  avatar+name │ bubble                        │         │
   │   │   state: intro-1|intro-2|intro-3|prompt|     │         │
   │   │          drop-nudge|move|grading|verdict     │         │
   │   │   buttons inside: [Only one][Several]        │         │
   │   │              or  [Solution][Analyze][Next]   │  D-10   │
   │   └─────────────────────────────────────────────┘         │
   └───────────────────────────────────────────────────────────┘
                │ walkthroughStep prop (NEW) ─────────────┐
                ▼                                          ▼
   ┌──────────────────────────────────────────┐   ring-2 ring-brand-brown
   │ TrainReveal — line cards, guess card,    │   on the line-card group
   │ game footer.  NO verdict row, NO action  │   for walkthrough step 2
   │ row (both move to the bubble above).     │
   └──────────────────────────────────────────┘

   trainBotCopy.ts (NEW, pure, no React)
     ├─ TEMPERAMENT sets derived from PERSONA_REGISTRY (D-01)
     ├─ pickHost(rng) / pickVerdictBot(points, rng)          (D-02/D-03/D-04)
     ├─ verdictCopy(points, correct_guess, move_quality)      (D-23)
     ├─ returnPhrase(due_date, expires_on, session_date,
     │               source, item_status)                     (D-15/D-16)
     └─ scoreBubbleCopy(outcomes[], is_warmup, firstSession)  (D-18/D-25)

   /activity (superuser) ── GET /api/admin/activity/stats
     activity_queries.fetch_train_funnel(conn, window_start)  (NEW)
     → Payload["train_funnel"] → render.js renderTrainFunnelCard()
```

### Recommended Project Structure

```
frontend/src/
├── components/train/
│   ├── TrainBotBubble.tsx        # NEW — avatar + bubble + optional button row.
│   │                             #   Pure presentational, no data fetching,
│   │                             #   no Train domain logic. Complexity target <= 8.
│   ├── TrainBotStepper.tsx       # NEW (optional split) — forward-only step index
│   │                             #   + Next/Got it. Owns NO copy; renders children.
│   ├── TrainSolveScreen.tsx      # MODIFIED — guess block + action row MOVE into
│   │                             #   the bubble slot. Net branch count must not rise.
│   ├── TrainReveal.tsx           # MODIFIED — verdict row + action row REMOVED;
│   │                             #   one new optional `walkthroughStep` prop.
│   └── TrainScoreScreen.tsx      # MODIFIED — bubble replaces the h1.
├── lib/
│   ├── trainBotCopy.ts           # NEW — all copy tables + pure resolvers + rng picker.
│   ├── trainGuessLabels.ts       # MODIFIED — D-09 GUESS_LABELS + a new call-form map.
│   └── personas/personaRegistry.ts  # MODIFIED — `temperament` on Persona + 24 entries.
└── hooks/useTrainSession.ts      # MODIFIED — live per-solve outcome accumulator.

app/
├── models/train_settings.py      # MODIFIED — 3 nullable DateTime(timezone=True).
├── schemas/train.py              # MODIFIED — SolvedResult +3 fields;
│                                 #   TrainSettingsResponse +3 (Update untouched).
├── routers/train.py              # MODIFIED — one new POST handler.
├── repositories/train_repository.py  # MODIFIED — stamp fn + solved_results join.
└── services/activity_queries.py  # MODIFIED — fetch_train_funnel + Payload key.

alembic/versions/<new>_phase_222_train_onboarding_seen.py   # NEW
```

### Pattern 1: The single chat-row slot lives in the board column

**What:** One `TrainBotBubble` mount point inside `TrainSolveScreen`'s measured board
column (`columnRef`), rendered for every puzzle state including the verdict.

**When to use:** Always. This is the load-bearing structural decision of the phase.

**Why (FINDING A):** `TrainSolveScreen` is a two-column flex. The board column is
`className="flex w-full flex-col items-center gap-4 max-lg:sticky max-lg:top-0 …"`
`[VERIFIED: frontend/src/components/train/TrainSolveScreen.tsx:963]`, and `TrainReveal`
is a **sibling** rendered after it `[VERIFIED: TrainSolveScreen.tsx:1188-1189]` inside a
container that is `lg:flex-row`
`[VERIFIED: TrainSolveScreen.tsx:943 — "…lg:mx-0 lg:max-w-none lg:flex-row lg:items-start lg:justify-center lg:gap-8"]`.
On desktop `TrainReveal` is therefore the **right column**
(`className="flex w-full flex-col gap-4 lg:mt-[46px] lg:max-w-sm"`
`[VERIFIED: TrainReveal.tsx:1147]`).

If the verdict bubble were mounted at the top of `TrainReveal`, then on desktop the bot
would vanish from under the board (left column) and reappear in the right column the
moment the reveal opens — precisely the "layout jump / vanishing bot" D-07 forbids. On
mobile the two are vertically adjacent so the swap reads correctly, which is why the
sketch (a phone mock) does not expose the problem.

Keeping the row in the board column also makes D-10 a pure in-place change: the
Solution/Analyze/Next row is **already** in the board column
`[VERIFIED: TrainSolveScreen.tsx:1048-1105]`, so "move the actions inside the bubble"
means wrapping an existing sibling, not relocating it across components.

**Consequence for the walkthrough (D-24):** step 1 spotlights an element in the board
column, step 2 the line cards (inside `TrainReveal`), step 3 the action row (back in the
board column). The step index must therefore be owned by `TrainSolveScreen` (the common
parent) and passed to `TrainReveal` as one new optional prop.

### Pattern 2: The bubble state is derived, never a second state machine

`TrainSolveScreen` already holds every input the bubble needs. Derive, do not add state:

| Bubble state | Existing predicate | Source |
|---|---|---|
| intro step 1–3 | `settings.intro_seen_at === null && guess === null && !moveApplied` + local `introStep` | NEW local `introStep` only |
| guess prompt | `guess === null && !moveApplied` | `[VERIFIED: TrainSolveScreen.tsx:1128 — "{guess === null && !moveApplied && ("]` |
| drop nudge | NEW `nudgeNonce` bumped by `handlePieceDrop` | `[VERIFIED: TrainSolveScreen.tsx:543]` |
| move prompt | `guess !== null && !moveApplied` | `[VERIFIED: TrainSolveScreen.tsx:1159 — "{guess !== null && !moveApplied && ("]` |
| grading | `moveApplied && isGrading` | `[VERIFIED: TrainSolveScreen.tsx:1166]` |
| verdict | `verdict !== null` | `[VERIFIED: TrainSolveScreen.tsx:289 — "const verdict = liveVerdict ?? restoredSolve?.verdict ?? null;"]` |

Because these predicates already exist as JSX guards, replacing the five sibling blocks
with **one** `<TrainBotBubble state={…} />` whose `state` comes from a single extracted
helper function actually **lowers** `TrainSolveScreen`'s cyclomatic complexity. That is
the only way to satisfy §Finding B while adding the nudge and intro states.

### Pattern 3: Pure copy module with an injectable rng

`trainBotCopy.ts` contains no React import (mirrors `lib/trainScore.ts`'s stated
convention `[VERIFIED: frontend/src/lib/trainScore.ts:1-6]`). Every resolver is a pure
function of values that already exist on `SolveResponse` / `TrainSessionResponse`.
The random picker takes `rng: () => number = Math.random` so unit tests are
deterministic without patching globals.

### Pattern 4: Additive server fields, separate write schema

`TrainSettingsResponse` and `TrainSettingsUpdate` are already deliberately separate
schemas so a PUT can never smuggle a server-owned field
`[VERIFIED: app/schemas/train.py:295-300]`. The three new timestamps go on the **Response
only**. This is safe on the client because `useTrainSettings`'s `mutationFn` builds a
`TrainSettingsUpdate` object literal field-by-field
`[VERIFIED: frontend/src/hooks/useTrainSettings.ts:67-74]` — it does not spread the
response.

### Anti-Patterns to Avoid

- **Mounting the verdict bubble in `TrainReveal`.** Breaks D-07 on desktop (Pattern 1).
- **Reusing `spotlightKey` / `onSpotlightChange` for the walkthrough.** Those props drive
  `applyTrainSpotlight` over the **board overlay** (filters which arrows are drawn)
  `[VERIFIED: TrainSolveScreen.tsx:733-736]`. Reuse the *visual* only:
  `'ring-2 ring-brand-brown'` `[VERIFIED: TrainReveal.tsx:1035, 1203]`. A separate
  `walkthroughStep` prop, never the spotlight channel.
- **Adding a branch to `TrainSolveScreen` / `TrainReveal`.** See §Finding B.
- **Renaming existing testids while moving elements.** See §Finding F.
- **Computing "N days" from `new Date()` or `Date.now()`.** D-15 forbids it and the
  server already supplies all three dates.
- **A second `GET /train/settings` fetch on the solve screen.** The cache is already
  warm (§Finding D) — call `useTrainSettings()` and let TanStack dedupe.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Calendar-day difference between two ISO dates | `Math.round((new Date(a) - new Date(b)) / 86400000)` | `differenceInCalendarDays(parseISO(a), parseISO(b))` | `new Date('2026-09-13')` parses as **UTC midnight**; `parseISO` parses date-only as **local** midnight. Mixing them silently shifts by a day in any non-UTC zone. Verified below. |
| Avatar image with emoji fallback | A new `<img>` + try/catch | `resolveAvatarSrc(persona)` / `placeholderAvatarFor(persona)` `[VERIFIED: frontend/src/lib/personas/personaAvatars.ts:59-61, 102-104]` | Handles the Vite `import.meta.glob` URL map and the per-style tint; the exact two-line render idiom is at `ClockDisplay.tsx:52-58` and `PersonaCard.tsx:138-144` |
| "Which persona is this id" | `PERSONA_REGISTRY[id]` inline | `personaForId(id)` `[VERIFIED: personaRegistry.ts:500-503]` | Guarded lookup, never throws on an unknown id |
| The `+N` point pill | A new styled span | `TrainScoreChip` `[VERIFIED: TrainReveal.tsx:319-333]` | It is already the shared pill shape with the green/red rule; the phase must **export** it from `TrainReveal.tsx` or move it to its own module (knip will not flag it, it will be imported) |
| Per-puzzle score | Re-deriving points from `correct_guess`/`move_quality` | `scorePuzzle(correctGuess, moveTier)` `[VERIFIED: frontend/src/lib/trainScore.ts:64-66]` | `trainScore.ts` is the declared single source of truth (Option B, LOCKED) |
| Board sizing around a taller bubble | A new reserved-height constant | `useFitBoardToViewport` — already wired | It measures `column.offsetHeight - board.offsetHeight` with a `ResizeObserver` on the column `[VERIFIED: frontend/src/hooks/useFitBoardToViewport.ts:72,82-84]`, so a taller bubble shrinks the board automatically |
| Reduced-motion detection | A fresh `matchMedia` call | `prefersReducedMotion()` `[VERIFIED: frontend/src/lib/confetti.ts:78]` | Already the project helper; `TrainScoreScreen.tsx:116,126` is the "omit the animation class" precedent |
| The onboarding step UI | Extending `TrainLineStepper` | A plain `useState<number>` + Next/Got it buttons | `TrainLineStepper` replays SAN moves from a FEN onto the shared board `[VERIFIED: TrainLineStepper.tsx:17-24]`. Entirely different job. |
| A big-number stat card on /activity | A new chart primitive | The `#conv-big` / `#conv-exp` text pattern `[VERIFIED: frontend/src/pages/activity/render.js:242-258]` | Keeps `npm run check:activity-layout` untouched — the harness only exercises chart primitives with synthetic fixtures `[VERIFIED: frontend/scripts/check-activity-layout.mjs:187-386]` |
| A cohort-flag subquery per metric | Two separate SQL round trips | One CTE with `count(*) FILTER (WHERE …)` | Drafted and executed below; one statement, four numbers |

**Key insight:** every "new" capability in this phase already has a working
implementation twenty lines away. The phase's real work is *deletion and relocation*
under a complexity ceiling that is already at its cap.

---

## Key Findings (with evidence)

### FINDING A — The verdict row must live in the board column
See §Pattern 1. Evidence: `TrainSolveScreen.tsx:943` (`lg:flex-row` container),
`:963` (board column), `:1048-1105` (existing action row, already in that column),
`:1188-1189` (`TrainReveal` mounted as a sibling), `TrainReveal.tsx:1147`
(`lg:max-w-sm` right column). **This contradicts the naive reading of sketch 004's
"bot row directly under the board (above every card)" as "top of `TrainReveal`".**

### FINDING B — The complexity baseline is pinned at exactly the current value
`frontend/eslint.config.js:216-222`:
```js
  {
    files: [
      'src/components/train/TrainReveal.tsx',
      'src/components/train/TrainSolveScreen.tsx',
    ],
    rules: { complexity: ['error', 68] },
  },
```
`[VERIFIED: frontend/eslint.config.js:216-222]`

Measured this session:
```
$ npx eslint --no-inline-config --rule 'complexity: ["error", 60]' \
    src/components/train/TrainSolveScreen.tsx src/components/train/TrainReveal.tsx
  TrainReveal.tsx      696:8  Function 'TrainReveal' has a complexity of 68.
  TrainSolveScreen.tsx 202:8  Function 'TrainSolveScreen' has a complexity of 68.
```
Both are at the ceiling with **zero headroom**. Any added `&&`, `?:`, `||`, `if`, or
optional-chain in either top-level function body fails `npm run lint`. `frontend/CLAUDE.md`
explicitly forbids re-baselining ("the override region is a historical snapshot from
Phase 215, not an escape hatch for new code"). Net-negative branch count is the target:
removing the guess block (2 branches), the move prompt (1), the grading block (1), the
action row (4: `verdict !== null`, `isBoardDeparted`, `game_id !== null`, `muted ? :`)
and replacing them with one `<TrainBotBubble>` gives ample room.

### FINDING C — D-17 alone cannot feed the score bubble
`useTrainSession` seeds `sessionScore` from `data.solved_results` in the session
mutation's `onSuccess` `[VERIFIED: frontend/src/hooks/useTrainSession.ts:172-176]`, and
thereafter accumulates only a **number** and a `Set<number>` of positions
`[VERIFIED: useTrainSession.ts:190-196]`. There is no list of per-solve outcomes and the
session is **never refetched** — `showScoreScreen` is local view state flipped in
`handleNext` when `lastSolveResponse.session_complete` is true
`[VERIFIED: frontend/src/pages/Train.tsx:65, 116-120]`.

Consequence: for a session composed and completed in one sitting, `session.solved_results`
is `[]` (the composer returns an empty list for a fresh session
`[VERIFIED: app/repositories/train_repository.py:2062 — "solved_results=[],"]`), so a
score bubble reading only `solved_results` would say "nothing comes back" for every
first-time user — the exact population this phase exists to serve.

**Required:** add `solvedOutcomes: SolvedResult[]` to `useTrainSession`, seeded from
`data.solved_results` in the session mutation's `onSuccess` and appended in the solve
mutation's `onSuccess` from the live `SolveResponse` (which already carries `source`,
`item_status`, `due_date` `[VERIFIED: app/schemas/train.py:219-222]`). D-17's schema
extension then covers only the resume/reload/handoff path — which is exactly what it is
for. Both halves are needed.

### FINDING D — The settings cache is already warm on every protected route
`App.tsx:627` calls `useReminderResurfaceRedirect({ enabled: profile != null && !profile.is_guest })`
and `:630` calls `useDevicePushResync({ enabled: … })`; both funnel into
`useTrainSettings({ enabled })` `[VERIFIED: frontend/src/hooks/useReminderResurface.ts:84,
frontend/src/hooks/useDevicePushResync.ts:59]`, which is a `useQuery` on
`TRAIN_SETTINGS_QUERY_KEY = ['train','settings']`
`[VERIFIED: frontend/src/hooks/useTrainSettings.ts:23,53-57]`.

So calling `useTrainSettings()` inside `TrainSolveScreen` costs **no extra request** for
a logged-in non-guest arriving at /train. D-12's "branch without a second fetch" is
sound. Caveat: on the very first render `data` is `undefined`. **Rule:** render no bubble
copy until `data !== undefined` (a fixed-height empty bubble, or nothing), otherwise a
first-timer sees the regular prompt flash before the intro replaces it.

The stamp endpoint should **return `TrainSettingsResponse`** so its `onSuccess` can do
`queryClient.setQueryData(TRAIN_SETTINGS_QUERY_KEY, data)` — the exact idiom the PUT
already uses `[VERIFIED: useTrainSettings.ts:78]`.

### FINDING E — D-15's `due_date <= expires_on` comparison is sound; both are `date`
`SolveResponse.due_date: date | None` `[VERIFIED: app/schemas/train.py:222]`;
`TrainSessionResponse.session_date: date` and `expires_on: date`
`[VERIFIED: app/schemas/train.py:112-113]`. Pydantic serializes `date` as `YYYY-MM-DD`,
so the client receives three date-only strings — lexicographic `<=` on those strings is
equivalent to date comparison, and `differenceInCalendarDays` gives an exact N.

The semantics behind the rule, verified in the scheduler:
- `expires_on = session_window(session_date, mask) = next_scheduled_day(session_date + 1 day, mask)`
  — "the first scheduled day strictly after `session_date`"
  `[VERIFIED: app/services/train_scheduler.py:373-392]`.
- A **failed** item: `due_date = next_scheduled_day(today, weekday_mask)`
  `[VERIFIED: app/services/train_scheduler.py:366]`, i.e. today itself on a scheduled
  day → `due_date <= expires_on` always holds → "next session". CONTEXT's claim is
  correct.
- A **correct** solve: `ideal_due = today + LADDER_DAYS[new_streak]` then snapped
  `[VERIFIED: train_scheduler.py:334-337]`, with
  `LADDER_DAYS: dict[int, int] = {0: 0, 1: 3, 2: 10}`
  `[VERIFIED: app/services/train_scheduler.py:57]`. With the default daily mask
  (`DEFAULT_WEEKDAY_MASK` = 127, `server_default="127"`
  `[VERIFIED: app/models/train_settings.py:70]`), `expires_on = today + 1`, so a streak-1
  item lands at `today + 3` → "in 3 days". With a sparse mask the snap can put a
  streak-1 item exactly on `expires_on` → "next session", which is accurate.
- **Mastered**: `due_date` is left UNTOUCHED at the previous value and the item is never
  rescheduled `[VERIFIED: train_scheduler.py:322-332]`. **Parked**: same — `due_date`
  untouched `[VERIFIED: train_scheduler.py:350-362]`. So for both, `due_date` is a
  **stale** value that must never be phrased as a return date — D-16's distinct lines are
  not cosmetic, they are correctness. `item_status` must be checked **before**
  `due_date`.
- `MASTERY_STREAK_THRESHOLD: int = 3` `[VERIFIED: train_scheduler.py:60]` — D-23's
  "Three in a row" copy is accurate.

Verified date-fns behaviour (run this session in `frontend/`):
```
parseISO date-only -> Sun Sep 13 2026 00:00:00 GMT+0200 (CEST)   # local, not UTC
differenceInCalendarDays(parseISO('2026-09-17'), parseISO('2026-09-13')) = 4
differenceInCalendarDays across a US DST boundary (10-30 -> 11-05) = 6   # exact
date-fns version: 4.4.0
```

### FINDING F — Keep the testids and ~140 assertions stay green
Occurrence counts in the frontend test suite (measured this session):

| testid | TrainSolveScreen.test | TrainReveal.test | Train.solveLoop.test |
|---|---:|---:|---:|
| `btn-train-guess-critical` | 51 | – | 2 |
| `train-verdict-guess` | 40 | 32 | 5 |
| `btn-train-solution` | 20 | – | – |
| `btn-train-analyze` | 12 | – | – |
| `btn-train-next` | 5 | – | 3 |
| `btn-train-guess-several` | 5 | – | – |
| `train-move-prompt` | 4 | – | – |
| `board-btn-mute` | 3 | – | – |
| `train-guess-prompt` | – | – | 2 |

Moving an element into the bubble while keeping its `data-testid` is a no-op for every
one of these. Only `board-btn-mute` (3 assertions) is genuinely deleted. Keep
`train-guess-prompt` and `train-move-prompt` on the bubble's copy node.

### FINDING G — The test suite's `matchMedia` stub defaults to `matches: true`
`frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx:58` declares
`let matchMediaMatches = true;` and `:62` returns it for **every** query. So inside that
file, `prefersReducedMotion()` (which reads
`window.matchMedia('(prefers-reduced-motion: reduce)').matches`
`[VERIFIED: frontend/src/lib/confetti.ts:78]`) returns **true**. If the drop-nudge pulse
is gated on `!prefersReducedMotion()`, it will never render in that file's tests. Either
make the stub query-aware, or assert the nudge through a non-animated signal (the copy
swap + a `data-nudge` attribute), which is the more robust choice anyway.

### FINDING H — SC2 is mechanically assisted but not guaranteed
`useFitBoardToViewport` computes
`nonBoardHeight = column.offsetHeight - board.offsetHeight` and observes the column with
a `ResizeObserver` `[VERIFIED: frontend/src/hooks/useFitBoardToViewport.ts:72, 82-84]`,
so a taller bubble inside the column shrinks the board automatically. But it floors at
`TRAIN_BOARD_MIN_WIDTH_PX = 240` `[VERIFIED: TrainSolveScreen.tsx:136]` and returns
early while scrolled (`if (window.scrollY > 0) return;`
`[VERIFIED: useFitBoardToViewport.ts:67]`).

Intro 2 (D-22) is ~63 words. At `text-sm` / 1.45 line-height in a ~330px-wide bubble
that is roughly 9–11 lines (~200–230px) plus the avatar column and the Next button. On a
375×667 device with browser chrome (~557px usable), the budget is
`557 − progress(46) − bubble(~270) − gutter(40) ≈ 200` → below the 240px floor → the page
scrolls. **This is the phase's highest-risk criterion and it is a device UAT gate, not a
unit test.** Levers available without breaking D-21: split Intro 2 into two shorter
steps, tighten the wording (explicitly permitted by D-21), or let the bubble body scroll
internally on the intro steps only. Note that steps 1–2 do not require the board to be
studied — only step 3 does, and step 3's copy is short.

### FINDING I — `scripts/reset_train_state.py` must clear the three new columns
`_reset` currently resets only the tick snapshot:
```python
            .values(
                streak_count=0,
                shield_level=0,
                streak_settled_through=None,
                pool_eligible_since=None,
            )
```
`[VERIFIED: scripts/reset_train_state.py:191-198]`

Without adding `intro_seen_at=None, reveal_walkthrough_seen_at=None, sr_explained_at=None`
there, a dev account can see each stepper **exactly once, ever** — making iterative UAT
of the three onboarding flows impossible without `bin/reset_db.sh`, which CLAUDE.md
forbids without explicit permission. Add the three to the UPDATE and extend
`tests/scripts/test_reset_train_state.py` (which already asserts the cleared snapshot at
`:68-71`).

### FINDING J — Both funnel queries drafted and executed against the dev DB
`drill_sessions.status` is TEXT with
`CHECK (status = ANY (ARRAY['open'::text, 'completed'::text, 'expired'::text]))`
`[VERIFIED: live `\d drill_sessions` on flawchess-dev-db-1]`, so "completed" is
`status = 'completed'` — the same definition `fetch_train` already uses
`[VERIFIED: app/services/activity_queries.py:289]`.

One statement produces all four numbers (executed successfully this session; returned
`openers=9 zero_solve_users=2 finishers=5 returners=3` on the dev database):

```sql
WITH first_session AS (
    SELECT DISTINCT ON (user_id) user_id, id AS session_id, session_date
    FROM drill_sessions
    ORDER BY user_id, session_date, id
),
cohort AS (
    SELECT user_id, session_id FROM first_session
    WHERE session_date >= CAST(:cutoff AS date)
),
flags AS (
    SELECT c.user_id,
           NOT EXISTS (
               SELECT 1 FROM drill_solves s
               WHERE s.session_id = c.session_id AND s.solved_at IS NOT NULL
           ) AS no_solve,
           (SELECT count(*) FROM drill_sessions d
             WHERE d.user_id = c.user_id AND d.status = 'completed') AS completed_count
    FROM cohort c
)
SELECT count(*)                                    AS openers,
       count(*) FILTER (WHERE no_solve)            AS zero_solve_users,
       count(*) FILTER (WHERE completed_count >= 1) AS finishers,
       count(*) FILTER (WHERE completed_count >= 2) AS returners
FROM flags;
```

The all-time baseline line is the identical query with `:cutoff` = the dataset start
(`'1970-01-01'` works, or reuse `window.data_start`). Two `_rows` calls, or one query
with two `FILTER` sets — either is cheap. `build_payload` already runs ~16 sequential
queries under a 300s cache `[VERIFIED: docs/activity-dashboard.md §Query cost]`, so one
or two more is within budget; note the doc's own warning that these have not been timed
against production.

**Interpretation caveat to put on the card:** the return metric is right-censored — a
user whose first session lands on the last day of the window has had no opportunity to
return. This belongs in the card's `<p className="note">`, consistent with the
dashboard's existing "the current day is always partial" caveats.

### FINDING K — D-09 vocabulary change has a fourth, off-Train call site
`GUESS_LABELS` is read at `TrainSolveScreen.tsx:1146,1154` (buttons) and
`TrainReveal.tsx:1216` (`Guess: {GUESS_LABELS[guess]}`). Two test assertions pin the
literal strings: `TrainReveal.test.tsx:273` (`expect(text).toContain('One critical move')`)
and `:281` (`'Several fine moves'`). The module docstring at
`TrainSolveScreen.tsx:6-7` also quotes them.

**Plus one outside Train:** `frontend/src/pages/Home.tsx:68` carries the marketing line
`'One critical move, or several fine moves? Commit before you play. …'`. After D-09 the
homepage describes a vocabulary the product no longer uses. Flagging as an Open Question
— it is a one-line copy edit, but it is outside the phase's stated scope.

### FINDING L — Retiring the mute toggle leaves `/bots` as the app's only mute control
`setMuted` has exactly two call sites: `Bots.tsx:373` and
`TrainSolveScreen.tsx:1098` `[VERIFIED: grep across frontend/src]`. The shared preference
is persisted, so a user who mutes on Train and then only uses Train can never unmute.
D-10 accepts this and the ROADMAP requires recording the re-homing seed at phase close;
the plan should carry that seed-recording as an explicit task, not an assumption.

Removal also strands four imports in `TrainSolveScreen.tsx`: `Volume2`, `VolumeX`
(line 38), and `useMuted`/`setMuted` (line 60), plus the `const muted = useMuted();`
local at line 223 — `muted` has no other use in the file (lines 987/1127/1168 are
`bg-muted` / `text-muted-foreground` Tailwind classes, not the variable). ESLint
`no-unused-vars` will fail the build if they are left behind.

---

## Backend Seam Detail

### `train_settings` migration
Template to copy verbatim in shape:
`alembic/versions/20260802_174733_6e7e50844af5_phase_203_reminder_intent.py` — 39 lines,
one `op.add_column("train_settings", sa.Column("reminder_intent_at", sa.DateTime(timezone=True), nullable=True))`
and its `drop_column` `[VERIFIED: that file:30-39]`. Current head is `b7d4f5a60002`
(`alembic/versions/20260912_120000_b7d4f5a60002_phase_220_cache_provenance.py`) — the new
revision's `down_revision` `[VERIFIED: `uv run alembic heads` this session]`.

The model precedent for the column type and its no-backfill rationale is
`reminder_intent_at` at `app/models/train_settings.py:114-126`:
```python
    reminder_intent_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
```

Test-DB handling is automatic: the pytest template auto-refreshes when the live Alembic
head differs from the template's stored `alembic_version`, so no manual rebuild step
`[VERIFIED: tests/conftest.py:55-56, 67-68]`.

### `get_or_create_settings` / `TrainSettingsRow`
Three call-graph touch points, all mechanical:
- `TrainSettingsRow` dataclass fields `[VERIFIED: app/repositories/train_repository.py:154-164]`
- `get_settings`'s row→dataclass mapping `[VERIFIED: train_repository.py:258-270]`
- `get_or_create_settings`'s `pg_insert(...).values(...)` **and** the returned
  `TrainSettingsRow(...)` for the just-inserted case — both must carry the three `None`s
  `[VERIFIED: train_repository.py:287-330]`
- `upsert_settings` must **not** gain them (D-12).

### The stamp endpoint
Shape (path/verb/step names are Claude's discretion per CONTEXT):
```python
OnboardingStep = Literal["intro", "reveal_walkthrough", "sr_explained"]

@router.post("/onboarding/{step}", response_model=TrainSettingsResponse)
async def stamp_onboarding_step(
    step: OnboardingStep,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    now_utc: NowUtc,
) -> TrainSettingsResponse:
    _reject_guest(user)
    ...
```
`_reject_guest` is the first statement in every `/train/*` handler by explicit convention
`[VERIFIED: app/routers/train.py:48-55, and every handler at :69, :130, :181, :222, :252, :299]`.
`NowUtc = Annotated[datetime.datetime, Depends(dev_now_utc)]`
`[VERIFIED: app/routers/train.py:45]`.

**Recommend first-write-wins** (`COALESCE(intro_seen_at, :now)` or a
`WHERE intro_seen_at IS NULL` guard) so a replayed POST does not move the timestamp —
this matters if the timestamps are ever used analytically. Returning
`TrainSettingsResponse` lets the client `setQueryData` the shared cache (§Finding D).

Returning a `Literal` path parameter: FastAPI validates it and 422s an unknown step —
no hand-rolled validation needed, and it satisfies CLAUDE.md's "never bare `str`".

### `SolvedResult` extension (D-17)
`SolveResponse` already returns all three fields per solve
`[VERIFIED: app/schemas/train.py:219-222]`:
```python
    source: Literal["sr_item", "red_herring", "sharp_filler"]
    item_status: Literal["active", "mastered", "parked"] | None
    streak: int | None
    due_date: date | None
```
The resume path currently selects only three columns
`[VERIFIED: app/repositories/train_repository.py:1315-1320]`:
```python
    solved_rows_stmt = (
        select(DrillSolve.correct_guess, DrillSolve.move_quality, DrillSolve.correct_move)
        .where(DrillSolve.session_id == drill_session.id, DrillSolve.solved_at.isnot(None))
        .order_by(DrillSolve.position)
    )
```
`drill_solves` carries `source` (SMALLINT, `DrillSource`) plus `game_id`/`ply`
`[VERIFIED: app/models/drill_solve.py:143,146,160]`, and `drill_items` is keyed
`(user_id, game_id, ply)` with `status` + `due_date`
`[VERIFIED: app/models/drill_item.py:75,81,84,86,88]`. So one LEFT JOIN supplies the rest.
Executed successfully against the dev DB this session:

```sql
SELECT s.position, s.source, s.correct_guess, s.move_quality, s.correct_move,
       i.status AS item_status, i.due_date
FROM drill_solves s
LEFT JOIN drill_items i
  ON i.user_id = s.user_id AND i.game_id = s.game_id AND i.ply = s.ply
WHERE s.solved_at IS NOT NULL
ORDER BY s.session_id DESC, s.position;
-- non-sr_item rows (source 1/2) return NULL item_status + NULL due_date, as required.
```

Map through the existing helpers, do not re-derive:
`_wire_source(...)` `[VERIFIED: train_repository.py:2222-2228]`,
`_STATUS_LITERAL` `[VERIFIED: train_repository.py:85-88]`,
`_resolve_move_quality_tier(...)` `[VERIFIED: train_repository.py:103-121]`.
An existing helper `_read_drill_item_state` already returns exactly
`(item_status, streak, due_date)` `[VERIFIED: train_repository.py:2467-2483]` — useful as
the single-row reference for the semantics, though the resume path wants the set-based
join, not N queries.

**Caveat:** the joined `due_date` is the item's *current* value, not a frozen
at-solve-time snapshot. Within one session that is identical (each position is solved
once, and `record_solve` writes the item before the resume read). Across a re-composed
session the item may have advanced further — acceptable, and arguably more truthful for a
"when does it come back" statement. Document it in the schema docstring.

**Security re-check (the schema docstring's own standard):** `SolvedResult`'s docstring
argues it is not an answer-key leak because every field "was already returned by
`SolveResponse` for each of these same positions"
`[VERIFIED: app/schemas/train.py:65-73]`. `source`, `item_status` and `due_date` all meet
that bar exactly. Entries still carry no `position`, `game_id`, `ply` or best move, so
nothing about an **unattempted** puzzle is revealed. The `PuzzleRevealResponse` 409 gate
is untouched.

### Activity dashboard wiring
Four files, in order:
1. `app/services/activity_queries.py` — new `async def fetch_train_funnel(conn, window_start) -> list[list[Any]]`
   using `_table(await _rows(conn, "...", cutoff=window_start))`
   `[VERIFIED: activity_queries.py:94-114 for the helpers; :282-299 for `fetch_train`'s exact shape]`,
   plus a new key on the `Payload` TypedDict `[VERIFIED: activity_queries.py:62-85]`.
2. `app/services/activity_stats.py` — one line inside `build_payload`'s single
   `async with` block, alongside `train=await queries.fetch_train(conn, window.window_start)`
   `[VERIFIED: app/services/activity_stats.py:79]`.
3. `frontend/src/types/activity.ts` — mirror the new `Payload` key
   `[VERIFIED: frontend/src/types/activity.ts:18-39]`.
4. `frontend/src/pages/activity/render.js` — a `renderTrainFunnelCard()` called from the
   render list (`renderTrainCard()` is invoked at `:368`), plus the new DOM ids in
   `ActivityPage.tsx`'s Train section `[VERIFIED: ActivityPage.tsx:462-479]`.
   **The `render.js` ↔ JSX seam addresses the DOM by id — renaming an id in the JSX
   silently drops the card** `[CITED: docs/activity-dashboard.md §The React / imperative seam]`.
   Destructure the payload row into a module-level const next to
   `SIGNUPS=payload.signups; BOT=payload.bot; TRAIN=payload.train; …`
   `[VERIFIED: render.js:38]`.

`npm run check:activity-layout` needs **no** change if the card uses the text/big-number
pattern: the harness loads `charts.js` into a `node:vm` sandbox and invokes the chart
primitives directly with synthetic fixtures `[VERIFIED: check-activity-layout.mjs:20-24,
158, 187-386]` — it never reads the real payload or `render.js`. Only a **new chart
primitive** would require a fixture case. It still must be run as part of the gate.

---

## Common Pitfalls

### Pitfall 1: Mounting the verdict bubble inside `TrainReveal`
**What goes wrong:** on desktop the bot vanishes from the left column and reappears in
the right one when the reveal opens — D-07's explicit prohibition.
**Why it happens:** sketch 004 is a phone mock; on a phone the two columns are stacked so
the bug is invisible.
**How to avoid:** Pattern 1 — the chat row is a board-column citizen for all states.
**Warning sign:** a `<TrainBotBubble>` inside `TrainReveal.tsx`'s return.

### Pitfall 2: `handlePieceDrop` returning `true` for a rejected drop
**What goes wrong:** `react-chessboard` interprets `true` as "the move was accepted" and
leaves the piece on the target square. D-08 wants the piece to snap back **and** the
bubble to react — those are two different things.
**How to avoid:** keep `return false` (the board must reject the move) and add a side
effect *before* it. Current code `[VERIFIED: TrainSolveScreen.tsx:541-543]`:
```ts
  function handlePieceDrop(source: string, target: string): boolean {
    // D-05: board locked until the binary guess is committed.
    if (guess === null) return false;
```
becomes:
```ts
    if (guess === null) {
      setNudgeNonce((n) => n + 1);   // bubble swaps copy + replays the pulse
      return false;                  // the piece still snaps back — this is correct
    }
```
D-08's "never return `false` **silently**" means "never without feedback", not "never
return false".
**Warning sign:** a test asserting the piece stayed on the target square.

### Pitfall 3: Replaying a CSS animation on an unchanged class
**What goes wrong:** repeated drops before the guess set the same class, and the browser
does not restart an already-running animation, so the second nudge is invisible.
**How to avoid:** the sketch's own trick — force a reflow — or, more idiomatically for
React, `key={nudgeNonce}` on the bubble element so it remounts. Sketch 003's raw-DOM
version is `bubble.classList.remove('attn'); void bubble.offsetWidth; … add('attn')`
`[VERIFIED: .planning/sketches/003-train-bot-guess-bubble/index.html:279]`.
Also gate on `prefersReducedMotion()` — and see Pitfall 5.

### Pitfall 4: Reaching for `TrainLineStepper` for the onboarding steppers
**What goes wrong:** it is a chess-move stepper — it replays SAN from `startFen` with
chess.js and reports derived FENs to the shared board
`[VERIFIED: TrainLineStepper.tsx:17-24]`. Wiring it to onboarding copy means fighting its
entire contract. CONTEXT lists it under "Reusable Assets" as "an existing stepper shape
for prev/next controls", which is misleading.
**How to avoid:** a forward-only `useState<number>` plus Next / Got it buttons, in a tiny
new component. Its `btn-train-step-prev` / `btn-train-step-next` testids
`[VERIFIED: TrainLineStepper.tsx:256,304]` must not be reused — the new controls need
their own.

### Pitfall 5: `prefersReducedMotion()` is `true` in the existing test file
See §Finding G. `TrainSolveScreen.test.tsx:58` sets `matchMediaMatches = true` for every
query. Prefer asserting the nudge via the copy swap plus a `data-` attribute rather than
the animation class.

### Pitfall 6: A tall bubble starving the board on a 375px viewport
See §Finding H. The `ResizeObserver` handles it down to the 240px floor, and the
measurement is **skipped while scrolled** (`if (window.scrollY > 0) return;`
`[VERIFIED: useFitBoardToViewport.ts:67]`) — so a bubble that grows after the user has
scrolled will not re-fit. Verify on a real 375px viewport with Intro 2 loaded.

### Pitfall 7: `SolveResponse` optional-field degradation applies to the verdict bot too
`vetted_moves`, `graded_es_before`, `graded_es_after` are OPTIONAL on the TS type
specifically because `trainRevealCache` entries written by an older bundle restore a
`verdict` object without those keys at runtime `[VERIFIED: frontend/src/types/train.ts:120-132]`.
`source`, `item_status` and `due_date` are **required** on the TS type
`[VERIFIED: frontend/src/types/train.ts:115-118]` but a cached reveal written before
Phase 206 would still lack `source` at runtime. The verdict copy resolver must tolerate
`undefined` for all three (one nullish default, at the consumption site — the
project's stated one-default-per-seam rule, `[VERIFIED: TrainSolveScreen.tsx:283-286]`).

### Pitfall 8: The D-09 vocabulary change is a four-site edit plus two test strings
See §Finding K. `GUESS_LABELS` (2 sites), `TrainReveal.tsx:1216`, the
`TrainSolveScreen.tsx:6-7` docstring, `TrainReveal.test.tsx:273/281`, and
`Home.tsx:68` (out of scope, flagged). D-09 requires a **second** map for the reveal's
longer "Your call: …" form — do not overload `GUESS_LABELS` with both.

### Pitfall 9: Dead imports after the mute-toggle removal
See §Finding L — `Volume2`, `VolumeX`, `useMuted`, `setMuted`, and the `muted` local all
become unused and will fail lint.

### Pitfall 10: Exact-dict assertions on the settings response
Adding three fields to `TrainSettingsResponse` breaks exactly two backend assertions:
`tests/routers/test_train.py:2307` and `:2358`, both of the form
`assert resp.json() == { … }` with the full six-key dict
`[VERIFIED: tests/routers/test_train.py:2307-2315]`. Update both; no other test does
exact-dict equality on that response.

### Pitfall 11: `SolvedResult` fixtures in the frontend tests
Five construction sites: the two `makeSolvedResult` factories
(`useTrainSession.test.ts:56`, `TrainSolveScreen.test.tsx:323`) and three inline literal
arrays (`Train.solveLoop.test.tsx:433`, `:481`, `:570`). Small, but a required-field
extension will fail `tsc -b` at all five.

### Pitfall 12: `tsc -b` is not run by `npm run lint` or `npm test`
Project memory and CLAUDE.md: esbuild strips types, so neither lint nor vitest
type-checks. This phase changes shared types (`Persona`, `SolvedResult`,
`TrainSettingsResponse`, `TrainRevealProps`) — `npm run build` must be run.

### Pitfall 13: asyncpg JSONB `None` vs SQL NULL
Not applicable to this phase (no JSONB column is written), but worth stating explicitly
since project memory flags it: the three new columns are `DateTime(timezone=True)`, so a
Python `None` writes a genuine SQL NULL and `IS NULL` predicates work as expected.

### Pitfall 14: `render.js` id drift
Renaming a DOM id in `ActivityPage.tsx` without updating `render.js` silently drops the
card with no error `[CITED: docs/activity-dashboard.md §The React / imperative seam]`.

---

## Code Examples

### Example 1: The bubble state resolver (keeps `TrainSolveScreen`'s complexity flat)

```ts
// frontend/src/components/train/trainBubbleState.ts  (or inside trainBotCopy.ts)
// Pure. Extracted OUT of the component so TrainSolveScreen's own cyclomatic
// complexity does not rise — see RESEARCH §Finding B (baseline pinned at 68).

export type TrainBubbleState =
  | { kind: 'intro'; step: 0 | 1 | 2 }
  | { kind: 'prompt' }
  | { kind: 'drop-nudge' }
  | { kind: 'move' }
  | { kind: 'grading' }
  | { kind: 'verdict' };

export function resolveBubbleState(input: {
  introPending: boolean;   // settings loaded AND intro_seen_at === null
  introStep: 0 | 1 | 2;
  nudged: boolean;
  guess: Guess | null;
  moveApplied: boolean;
  isGrading: boolean;
  hasVerdict: boolean;
}): TrainBubbleState {
  if (input.hasVerdict) return { kind: 'verdict' };
  if (input.moveApplied && input.isGrading) return { kind: 'grading' };
  if (input.guess !== null) return { kind: 'move' };
  if (input.introPending) return { kind: 'intro', step: input.introStep };
  if (input.nudged) return { kind: 'drop-nudge' };
  return { kind: 'prompt' };
}
```

### Example 2: The return-phrase resolver (D-15 + D-16), status before date

```ts
// frontend/src/lib/trainBotCopy.ts
import { differenceInCalendarDays, parseISO } from 'date-fns';

/** D-16 ordering is load-bearing: `due_date` is a STALE value for mastered and
 * parked items (train_scheduler.apply_result leaves it UNTOUCHED on both
 * branches), so status must be checked before any date comparison. */
export function returnPhrase(v: {
  source?: SolveResponse['source'];
  item_status?: SolveResponse['item_status'];
  due_date?: string | null;
  sessionDate: string;   // TrainSessionResponse.session_date, "YYYY-MM-DD"
  expiresOn: string;     // TrainSessionResponse.expires_on,   "YYYY-MM-DD"
}): string {
  if (v.source === 'red_herring' || v.source === 'sharp_filler') return WARMUP_TAIL;
  if (v.item_status === 'mastered') return MASTERED_TAIL;
  if (v.item_status === 'parked') return PARKED_TAIL;
  if (v.due_date == null) return '';                  // defensive: pre-206 cached verdict
  if (v.due_date <= v.expiresOn) return NEXT_SESSION_TAIL;   // ISO dates: string <= is date <=
  const days = differenceInCalendarDays(parseISO(v.due_date), parseISO(v.sessionDate));
  return laterTail(days);
}
```

### Example 3: The injectable random picker (D-02/D-03/D-04)

```ts
// frontend/src/lib/trainBotCopy.ts
import { PERSONA_REGISTRY, type Persona } from '@/lib/personas/personaRegistry';

// D-01: derived from the temperament field, never a hand-maintained id list.
const BY_TEMPERAMENT = Object.values(PERSONA_REGISTRY).reduce<Record<Temperament, Persona[]>>(
  (acc, p) => { acc[p.temperament].push(p); return acc; },
  { stern: [], friendly: [], smart: [] },
);

/** `rng` is injected so unit tests are deterministic without patching globals
 * (the chessClock.ts / selectBookMove precedent); component tests still use
 * `vi.spyOn(Math, 'random')` (SetupScreen.test.tsx:138). */
export function pickBot(temperament: Temperament, rng: () => number = Math.random): Persona {
  const pool = BY_TEMPERAMENT[temperament];
  // noUncheckedIndexedAccess: the pools are non-empty by construction (the
  // registry test asserts 24 entries), but narrow rather than assert.
  return pool[Math.floor(rng() * pool.length)] ?? pool[0]!;
}
```

### Example 4: The live outcome accumulator (§Finding C)

```ts
// frontend/src/hooks/useTrainSession.ts
const [solvedOutcomes, setSolvedOutcomes] = useState<SolvedResult[]>([]);

// in sessionMutation.onSuccess — seed from the server (resume / reload / handoff):
setSolvedOutcomes(data.solved_results);

// in solveMutation.onSuccess — append the live verdict (which already carries
// source / item_status / due_date):
setSolvedOutcomes((prev) => [
  ...prev,
  {
    correct_guess: data.correct_guess,
    move_quality: data.move_quality,
    source: data.source,
    item_status: data.item_status,
    due_date: data.due_date,
  },
]);
```

### Example 5: The avatar render idiom (copy verbatim)

```tsx
// From ClockDisplay.tsx:45-58 / PersonaCard.tsx:108-144 — do not re-derive.
const avatar = placeholderAvatarFor(persona);
const avatarSrc = resolveAvatarSrc(persona);
// ...
<span
  className="…rounded-full overflow-hidden…"
  style={{ backgroundColor: avatar.tint, width: AVATAR_SIZE_PX, height: AVATAR_SIZE_PX }}
>
  {avatarSrc !== undefined ? (
    <img src={avatarSrc} alt="" loading="lazy" className="h-full w-full object-cover" />
  ) : (
    avatar.emoji
  )}
</span>
```
All 24 WebPs are present in `frontend/src/assets/personas/`
`[VERIFIED: `ls` returned exactly 24 files, one per persona id]`, so the emoji branch is
currently unreachable — but keep it, per the module's documented contract.

---

## Runtime State Inventory

*(Not a rename/refactor/migration phase in the string-replacement sense, but it does add
persisted state and change a user-facing vocabulary. Answering the five categories
explicitly.)*

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `train_settings` gains three nullable timestamps (D-13: **no backfill**, every existing row lands on NULL by design). `drill_solves`/`drill_items` unchanged — D-17 reads them via a new JOIN, writes nothing. | Alembic migration only; no data migration |
| Live service config | None — verified: no n8n workflow, Datadog tag, Tailscale ACL or Cloudflare config references Train onboarding state | None |
| OS-registered state | None — verified: the Train reminder job (`app/services/train_reminder_service.py`) reads `reminder_enabled`/`reminder_hour`/`reminder_last_sent_on`, none of which this phase touches; no scheduler task references the new columns | None |
| Secrets / env vars | None — no new secret, no new env var | None |
| Build artifacts / generated files | `frontend/src/generated/personaCalibration.ts` is regenerated by `scripts/gen_persona_calibration.py`, which writes **only** `{ botElo, label }` per id `[VERIFIED: scripts/gen_persona_calibration.py:240]`. The new `temperament` field is hand-authored in `personaRegistry.ts` and is **not** generator-owned — no drift risk, no CI regeneration needed. | None |
| **Dev-account onboarding replay** | `scripts/reset_train_state.py` does not clear the three new columns — see §Finding I | Add them to `_reset`'s `.values(...)` and extend its test |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL 18 (dev, Docker) | backend tests, migration, SQL drafting | ✓ | container `flawchess-dev-db-1` on `:5432` | — |
| `uv` / Python 3.14 | backend suite, alembic, ty | ✓ | project standard | — |
| Node / npm (frontend) | vitest, eslint, tsc, knip, layout harness | ✓ | `date-fns@4.4.0` confirmed | — |
| Alembic head `b7d4f5a60002` | new revision's `down_revision` | ✓ | `uv run alembic heads` | — |
| Benchmark DB (`:5433`) | not needed | ✓ (running) | — | — |
| Real 375px device or browser device-mode | SC2 verification | manual | — | none — this is the UAT gate, not automatable |
| Production DB tunnel (`bin/prod_db_tunnel.sh`) | reading the real post-release funnel numbers | not needed during the phase | — | the /activity card itself is the reading surface |

**Missing dependencies with no fallback:** none blocking implementation. The 375px
device check is a human-action checkpoint (project memory: run these yourself, don't
defer).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Backend framework | pytest 9.x + pytest-asyncio, per-session cloned PostgreSQL from an auto-refreshing migrated template `[VERIFIED: tests/conftest.py:50-68]` |
| Backend config | `pyproject.toml` (addopts) + `tests/conftest.py` |
| Frontend framework | Vitest + @testing-library/react, jsdom per-file via `// @vitest-environment jsdom` |
| Frontend config | `frontend/vite.config.ts` `test:` block — `testTimeout`/`hookTimeout`/`setupFiles: ['src/vitest.setup.ts']` `[VERIFIED: frontend/vite.config.ts:90-94]` |
| Backend quick run | `uv run pytest tests/routers/test_train.py -x` |
| Backend full suite | `uv run pytest -n auto -x` |
| Frontend quick run | `cd frontend && npm test -- --run src/components/train` |
| Frontend full suite | `cd frontend && npm run lint && npm test -- --run && npm run build` |

**Timeout rule (project memory, non-negotiable):** never add a per-file/per-test timeout.
The project-wide values live in `vite.config.ts` + `src/vitest.setup.ts`. If a new heavy
test is slow, hoist any `await import` out of the test body into `beforeAll`.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TRAINBOT-01 | Intro stepper renders for `intro_seen_at === null`; step 3 carries the guess buttons | unit (component) | `npm test -- --run src/components/train/__tests__/TrainSolveScreen.test.tsx` | ✅ extend |
| TRAINBOT-01 | Drop before guess: board rejects the move AND the bubble copy swaps to the nudge line | unit (component) | same file — drive `onPieceDrop` directly via the mocked ChessBoard | ✅ extend |
| TRAINBOT-01 | `resolveBubbleState` covers all six states, precedence order | unit (pure) | `npm test -- --run src/components/train/__tests__/trainBubbleState.test.ts` | ❌ Wave 0 |
| TRAINBOT-02 | Bubble renders the prompt for every non-first session | unit (component) | TrainSolveScreen.test.tsx | ✅ extend |
| TRAINBOT-02 | Board fully visible at 375px with Intro 2 loaded | **manual UAT** | device / browser device-mode at 375×667 | n/a — §Finding H |
| TRAINBOT-03 | `returnPhrase` — the full D-15/D-16 truth table (next-session, N-days, mastered, parked, herring, filler, null due_date) | unit (pure) | `npm test -- --run src/lib/__tests__/trainBotCopy.test.ts` | ❌ Wave 0 |
| TRAINBOT-03 | Verdict bubble shows the outcome-matched bot + both point pills + the tail | unit (component) | TrainSolveScreen.test.tsx (the bubble lives there per §Finding A) | ✅ extend |
| TRAINBOT-03 | `pickBot` is deterministic under an injected rng and draws only from its temperament set | unit (pure) | trainBotCopy.test.ts | ❌ Wave 0 |
| TRAINBOT-04 | Score bubble counts group correctly across a live session (accumulator) and a resumed one (`solved_results`) | unit (hook) | `npm test -- --run src/hooks/__tests__/useTrainSession.test.ts` | ✅ extend |
| TRAINBOT-04 | First-completed-session copy vs later-session copy vs warm-up copy | unit (component) | `npm test -- --run src/components/train/__tests__/TrainScoreScreen.test.tsx` | ✅ extend |
| TRAINBOT-05 | `POST /train/onboarding/{step}` stamps the right column; 403 for a guest; 422 for an unknown step; idempotent replay does not move the timestamp | integration (router) | `uv run pytest tests/routers/test_train.py -k onboarding` | ✅ extend |
| TRAINBOT-05 | The three timestamps appear on `GET /train/settings` and are NOT accepted by `PUT /train/settings` | integration (router) | `uv run pytest tests/routers/test_train.py -k settings` | ✅ extend (fix the two exact-dict asserts, Pitfall 10) |
| TRAINBOT-05 | Migration upgrade/downgrade round-trip; all existing rows land NULL | integration | `uv run pytest tests/repositories/test_train_repository.py` + the template auto-refresh | ✅ extend |
| TRAINBOT-05 | State survives a device switch | **manual UAT** | phone handoff: complete the intro on desktop, open /train on the phone, intro must not replay | n/a |
| TRAINBOT-06 | Funnel SQL: a seeded cohort yields the expected four numbers; cohort respects the window; non-first sessions excluded | integration (query) | `uv run pytest tests/test_admin_activity_stats.py -k funnel` | ✅ extend (no per-query test exists today — this is genuinely new coverage) |
| TRAINBOT-06 | Layout harness stays green with the new card | integration | `cd frontend && npm run check:activity-layout` | ✅ exists |
| TRAINBOT-07 | All 24 personas carry a valid `temperament`; the three sets are non-empty; Hilda is smart and Tank is stern | unit (pure) | `npm test -- --run src/lib/personas/__tests__/personaRegistry.test.ts` | ✅ extend |
| TRAINBOT-08 | New guess labels render on the buttons and the reveal's call form | unit (component) | TrainSolveScreen.test.tsx + TrainReveal.test.tsx | ✅ extend (Pitfall 8 — two literal assertions to update) |
| TRAINBOT-09 | Analyze / Next / Solution render inside the bubble with unchanged testids and unchanged behaviour | unit (component) | TrainSolveScreen.test.tsx (32 existing assertions already cover the behaviour) | ✅ exists |
| TRAINBOT-09 | Mute toggle is gone; no dead imports | lint | `cd frontend && npm run lint && npm run knip` | ✅ exists |

### Sampling Rate

- **Per task commit:** the narrowest relevant file —
  `uv run pytest tests/routers/test_train.py -x` or
  `cd frontend && npm test -- --run src/components/train`.
- **Per wave merge:** `uv run pytest -n auto -x` + `cd frontend && npm run lint && npm test -- --run`.
- **Phase gate (the CLAUDE.md pre-merge gate, in full, before the squash-merge):**
  ```bash
  uv run ruff format app/ tests/ scripts/ analysis/
  uv run ruff check . --fix
  uv run ty check app/ tests/ scripts/
  uv run --project analysis --with ty ty check analysis/
  uv run python scripts/check_function_size.py app/ --fail-over-depth 4 --fail-over-loc 200
  uv run pytest -n auto -x
  ( cd frontend && npm run lint && npm test -- --run )
  ```
  **Plus, mandatory for this phase specifically:**
  ```bash
  cd frontend && npm run build                  # tsc -b — shared types change (Pitfall 12)
  cd frontend && npm run knip                   # new exports must be imported
  cd frontend && npm run check:activity-layout  # the new dashboard card
  ```

### Wave 0 Gaps

- [ ] `frontend/src/lib/__tests__/trainBotCopy.test.ts` — covers TRAINBOT-03, TRAINBOT-07
      (return-phrase truth table, verdict bucket resolution, injected-rng picker)
- [ ] `frontend/src/components/train/__tests__/trainBubbleState.test.ts` — covers
      TRAINBOT-01 (state precedence)
- [ ] `frontend/src/components/train/__tests__/TrainBotBubble.test.tsx` — covers the
      presentational contract (avatar fallback, button slot, testids)
- [ ] A seeded-cohort fixture for the funnel query in `tests/test_admin_activity_stats.py`
      — that file currently has **no** per-query test (`grep "def test"` shows only
      endpoint-auth, cache and `resolve_window` tests), so TRAINBOT-06 needs a new
      fixture pattern; `tests/routers/test_train.py`'s session-seeding helpers are the
      model to borrow from
- [ ] No framework install needed

### Manual UAT checklist (device-bound legs only; run them yourself)

1. **375×667, longest copy** — first-ever session, intro step 2 loaded: board fully
   visible, both Next and the eventual guess buttons on screen without scrolling (SC2).
2. **Phone handoff** — complete the intro on desktop, open /train on a phone with the
   same account: the intro does not replay (SC5).
3. **Drop before the guess** — drag a piece: it snaps back, the bubble visibly reacts and
   its copy changes (SC1).
4. **Reveal walkthrough** — three steps, each spotlighting the right element, on both
   viewports (desktop is the one that can break — the three targets span two columns).
5. **Score screen** — first completed session shows the full SR explanation; a second
   session shows the one-liner; a warm-up session shows the warm-up variant (SC4).
6. Replay steps 1–5 after `uv run python scripts/reset_train_state.py --db dev --user-id <N>`
   to confirm §Finding I's fix works.

---

## Security Domain

`security_enforcement` is not set in `.planning/config.json` → treated as enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (unchanged) | FastAPI-Users `current_active_user`, already applied |
| V3 Session Management | no (unchanged) | Bearer JWT, unchanged |
| V4 Access Control | **yes** | The stamp endpoint must take the user id from `current_active_user.id` only, **never** from body or path — the documented V4/IDOR guard on every existing `/train/*` handler `[VERIFIED: app/routers/train.py:66-68, 126-129]`. Plus `_reject_guest` as the first statement. |
| V5 Input Validation | **yes** | The step name is a `Literal[...]` path parameter → FastAPI validates and 422s anything else. No free-form string reaches the repository. No new body schema is needed at all. |
| V6 Cryptography | no | Nothing cryptographic |
| V7 Error Handling / Logging | **yes** | Mirror the existing rollback + `sentry_sdk.set_context("train", {...})` + `capture_exception()` shape; never interpolate `user_id`/`step` into an exception message (CLAUDE.md grouping rule) |
| V8 Data Protection | **yes (re-check)** | D-17 widens `SolvedResult`. Verified non-leaking: all three fields were already returned by `SolveResponse` for the same positions, and entries still carry no `position`/`game_id`/`ply`/best move — see §Backend Seam Detail. The `PuzzleRevealResponse` 409 gate is untouched. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| IDOR on the stamp endpoint (stamping another user's flags) | Elevation of Privilege | User id from the auth dependency only; the `train_settings` PK is `user_id` so the UPDATE is inherently scoped |
| Guest reaching a registered-only surface | Elevation of Privilege | `_reject_guest` first statement (D-14) |
| Answer-key disclosure through the widened `SolvedResult` | Information Disclosure | Field-by-field re-check above; keep the schema docstring's argument current |
| SQL injection in the new activity query | Tampering | `_rows(conn, sql, **params)` uses SQLAlchemy `text()` bound parameters `[VERIFIED: app/services/activity_queries.py:94-96]`; the read-only engine sets `default_transaction_read_only` so even a successful injection cannot write `[CITED: docs/activity-dashboard.md §Safety]` |
| Dashboard exposure to non-superusers | Information Disclosure | `current_superuser` on `GET /api/admin/activity/stats`, which also 403s impersonation tokens `[CITED: docs/activity-dashboard.md §Safety]` — unchanged by this phase |
| Timestamp replay moving an analytics watermark | Tampering (minor) | First-write-wins on the stamp (`WHERE <col> IS NULL` / `COALESCE`) |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Train prompt = a bare `<p>` + two buttons under the board | Bot avatar + speech bubble carrying prompt and buttons | this phase | The delivery vehicle; SEED-166's diagnosis is that a plain prompt under a board is skippable |
| Reveal action row below the board with a mute toggle | Actions inside the verdict bubble; mute retired | this phase | §Finding L |
| "One critical move" / "Several fine moves" | "Only one" / "Several" | this phase (D-09) | §Finding K — four call sites |
| Score tallied in localStorage | Score seeded from server `solved_results` | quick 260728-tgc | The pattern this phase extends for the outcome list (§Finding C) |
| `puzzle_type !== 'herring'` as the "your game" proxy | `verdict.source === 'sr_item'` | Phase 206 D-19 | Use `source`, never `puzzle_type`, for D-16's warm-up branch — a sharp filler has `puzzle_type: 'sharp'` `[VERIFIED: TrainReveal.tsx:1310-1319 comment]` |
| `flame_state` TEXT enum on `train_settings` | `shield_level` SMALLINT + CHECK | Phase 193 | Confirms the "no native enum, no TEXT state column" convention the new columns follow by being plain timestamps |

**Deprecated / outdated in context:**
- SEED-166's line-number reference `TrainSolveScreen.tsx:535` for the silent snap-back
  has drifted — the guard is now at `:543` inside a function starting at `:541`.
- CONTEXT's "`TrainLineStepper.tsx`: an existing stepper shape for prev/next controls"
  is misleading (§Pitfall 4).
- The brief's SQL table names `train_sessions` / `train_session_items` do not exist; the
  real tables are `drill_sessions` / `drill_solves` (the seed uses the correct names).

---

## Contradictions and drift found against CONTEXT / the brief

Flagged rather than silently worked around, per the research brief.

1. **`TrainSolveScreen.tsx` line numbers have drifted.** CONTEXT: "guess buttons and
   prompts ~L1132-1165; the Solution/Analyze/Next row ~L1042-1095; `handlePieceDrop`
   ~L541". Actual: guess block `L1128-1156` (prompt `:1136`, buttons `:1139-1155`), move
   prompt `L1159-1164`, grading `L1166-1171`; action row `L1048-1105` (mute `:1093-1104`);
   `handlePieceDrop` at `:541` with the guard at `:543`. Directionally correct, but the
   plan should cite the verified anchors.
2. **SEED-166 cites `TrainSolveScreen.tsx:535`** for the `guess === null` return — now
   `:543`.
3. **`TrainLineStepper` is not a reusable onboarding stepper** (§Pitfall 4). CONTEXT
   lists it under "Reusable Assets"; it is a chess-move stepper.
4. **D-17 is necessary but not sufficient for the score bubble** (§Finding C). CONTEXT
   says "The score screen derives everything from this array, so it survives a reload and
   the phone handoff" — true for the reload/handoff path, but the array is empty for a
   session played straight through, which is the majority case. The plan needs the live
   accumulator too.
5. **Sketch 004's "bot row directly under the board (above every card)" cannot mean "top
   of `TrainReveal`" on desktop** (§Finding A). The sketch is a phone mock.
6. **The research brief names `train_sessions` / `train_session_items`.** Those tables do
   not exist; the schema is `drill_sessions` / `drill_solves` / `drill_items`.
7. **D-19's "all-time line for the baselines (52/123 = 42%, 26/53 = 49%)".** Those are
   2026-09-12 production readings. Recommend computing the all-time line **live** from
   the same query with a `1970-01-01` cutoff rather than hardcoding, so the card cannot
   drift from reality; the seed keeps the frozen baseline for the record.
8. **The D-01 draft temperament table is internally consistent and maps to real ids** —
   verified all 24 persona names against `personaRegistry.ts` (8 stern + 7 smart +
   9 friendly = 24; Hilda = `wall-1800`, Tank = `grinder-1600`, Rocco = `wall-1600`, all
   correct). No correction needed; it is ready for the user's review.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Intro 2's rendered bubble height at 375px is ~200–270px | §Finding H, Pitfall 6 | Estimated from word count and line-height, not measured in a browser. If taller, SC2 fails harder; if shorter, the risk is overstated. **Must be measured during UAT** — it does not change the plan's shape either way. |
| A2 | Removing the guess block, move prompt, grading block and action row nets enough complexity headroom for the bubble slot | §Finding B | If the net is still ≥ 68, the plan needs a further extraction (e.g. lifting the free-play wiring into a hook). Verifiable in one `npx eslint --rule 'complexity:["error",1]'` run mid-implementation — make it a per-task check. |
| A3 | `render.js`'s big-number/text card pattern is sufficient for the two funnel ratios (no chart primitive) | §Backend Seam Detail | If the planner wants a time series instead, `check:activity-layout` needs a new fixture case. The ratios are point-in-time by D-19's definition, so a chart would be misleading anyway. |
| A4 | First-write-wins is preferable to last-write-wins for the seen timestamps | §Backend Seam Detail | Only matters if the timestamps are ever read analytically; either is functionally correct for the gating behaviour. Not a locked decision — the planner may pick. |
| A5 | No consumer outside the files surveyed reads `Persona`'s field set exhaustively | §Runtime State Inventory | Checked `PERSONA_REGISTRY` importers (`useBotGame.ts`, `Bots.tsx`, `botPersonaSetupSettings.ts`, three `__tests__` files) and the generator; none enumerate fields. A missed `Object.keys(persona)` assertion would surface immediately as a red test. |
| A6 | `drill_items` rows survive for the lifetime of a completed session, so D-17's LEFT JOIN resolves for every sr_item solve | §Backend Seam Detail | If an item is deleted (game deletion path) the join yields NULL and the entry falls into the "no return promised" branch — a graceful degradation, not a crash. Worth one repository test. |

---

## Open Questions (RESOLVED)

1. **Does the homepage copy change with D-09?**
   - RESOLVED: yes — `Home.tsx` updated to the `GUESS_LABELS` vocabulary in 222-01-PLAN.md (§Planning notes).
   - What we know: `frontend/src/pages/Home.tsx:68` reads "One critical move, or several
     fine moves? Commit before you play." — the exact vocabulary D-09 replaces.
   - What's unclear: whether the user wants marketing copy touched in this phase.
   - Recommendation: include it as a one-line task, flagged for the user to drop if
     out of scope. Leaving it creates a documented inconsistency between the landing page
     and the product.

2. **Should the three seen-flags also ride on `TrainSessionResponse`?**
   - RESOLVED: no — D-12 kept as written; 222-01/02/04 read the flags from `TrainSettingsResponse` only and gate the bubble on `data !== undefined`.
   - What we know: D-12 locks them onto `TrainSettingsResponse`; §Finding D shows that is
     already free of extra cost because `useTrainSettings` is mounted app-wide.
   - What's unclear: the sub-frame `data === undefined` window on a cold cache (a hard
     reload directly onto `/train`).
   - Recommendation: **keep D-12 as written** and gate the bubble on `data !== undefined`.
     Only if UAT shows a visible flash should adding them to `TrainSessionResponse` be
     reconsidered — and that would be an additive, reversible change.

3. **Does the first puzzle's smart host need to be Hilda by construction?**
   - RESOLVED: yes — Hilda hosts the first puzzle by construction (222-01-PLAN.md §Planning notes).
   - CONTEXT leaves this to discretion. Recommendation: **yes** — the intro stepper
     renders Hilda's row for all three steps and the buttons live in her step-3 bubble
     (D-05's own "simplest" reading). It removes a whole state (a random host that must
     be suppressed on the first puzzle) and one branch from the complexity budget.

4. **Score bubble on the restored-reveal path.**
   - RESOLVED: 222-05-PLAN.md carries both halves of Finding C (live `solvedOutcomes` accumulator + D-17 seed) and an explicit restored-reveal test.
   - What we know: `Train.tsx:132` reads `restoredReveal?.verdict.session_complete === true`
     to route a restored reveal to the score screen.
   - What's unclear: a user who leaves via Analyze on the final puzzle and comes back has
     `solvedOutcomes` reseeded from a **fresh session POST** (which, for a completed
     session, does return populated `solved_results` via `_resume_session`
     `[VERIFIED: train_repository.py:1315-1337]`) — so it should work, but it is the one
     path where the two halves of §Finding C interact.
   - Recommendation: one explicit test for it.

5. **Interpretation caveat wording for the right-censored return metric.**
   - RESOLVED: implemented as the right-censoring note on the funnel card in 222-03-PLAN.md task 2.
   - Recommendation: a `<p className="note">` on the card stating that a user whose first
     session falls near the window's end has had no chance to return, so the return share
     is a floor for recent windows. Matches the dashboard's existing caveat style.

---

## Sources

### Primary (HIGH confidence) — files read in the working tree this session
- `frontend/src/components/train/TrainSolveScreen.tsx` (1222 lines, read in full)
- `frontend/src/components/train/TrainReveal.tsx` (targeted: props, TrainScoreChip, spotlight, guess card, render tail)
- `frontend/src/components/train/TrainScoreScreen.tsx`, `TrainLineStepper.tsx`, `buttonStyles.ts`
- `frontend/src/pages/Train.tsx`, `frontend/src/hooks/useTrainSession.ts`, `useTrainSettings.ts`, `useFitBoardToViewport.ts`, `useIsDesktop.ts`
- `frontend/src/lib/trainScore.ts`, `trainGuessLabels.ts`, `utils.ts`, `confetti.ts`, `personas/personaRegistry.ts`, `personas/personaAvatars.ts`
- `frontend/src/types/train.ts`, `frontend/src/types/activity.ts`
- `frontend/src/components/bots/PersonaCard.tsx`, `ClockDisplay.tsx`, `frontend/src/components/ui/card.tsx`
- `frontend/src/pages/activity/render.js`, `ActivityPage.tsx`, `frontend/scripts/check-activity-layout.mjs`, `frontend/src/index.css`
- `frontend/eslint.config.js`, `frontend/vite.config.ts`, `frontend/package.json`
- `app/schemas/train.py`, `app/routers/train.py`, `app/routers/admin_activity.py`
- `app/repositories/train_repository.py` (targeted), `app/services/train_scheduler.py`, `app/services/activity_queries.py`, `app/services/activity_stats.py`
- `app/models/train_settings.py`, `drill_solve.py`, `drill_item.py`, `drill_session.py`
- `alembic/versions/20260802_174733_6e7e50844af5_phase_203_reminder_intent.py`
- `scripts/reset_train_state.py`, `scripts/gen_persona_calibration.py`
- `tests/conftest.py`, `tests/routers/test_train.py`, `tests/test_admin_activity_stats.py`, `tests/scripts/test_reset_train_state.py`
- `frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx`, `TrainReveal.test.tsx`, `frontend/src/pages/__tests__/Train.solveLoop.test.tsx`, `frontend/src/hooks/__tests__/useTrainSession.test.ts`, `frontend/src/lib/personas/__tests__/personaRegistry.test.ts`

### Primary (HIGH confidence) — commands executed this session
- `uv run alembic heads` → `b7d4f5a60002 (head)`
- `npx eslint --no-inline-config --rule 'complexity: ["error", 60]' <two Train components>` → both 68
- `docker exec flawchess-dev-db-1 psql … "\d drill_sessions"` → status CHECK values
- `docker exec flawchess-dev-db-1 psql …` the funnel CTE → `9 / 2 / 5 / 3`
- `docker exec flawchess-dev-db-1 psql …` the `drill_solves` ⟕ `drill_items` join → NULLs for non-sr_item
- `node -e` date-fns `parseISO` / `differenceInCalendarDays` probe → local-midnight, DST-exact, v4.4.0
- `ls frontend/src/assets/personas/` → 24 WebPs

### Secondary (MEDIUM confidence) — project documentation
- `CLAUDE.md`, `frontend/CLAUDE.md` — constraints table above
- `docs/activity-dashboard.md` — the React/imperative seam, safety model, query cost
- `.planning/ROADMAP.md` §Phase 222, `.planning/seeds/SEED-166-*.md`,
  `.planning/sketches/003/README.md`, `004/README.md`, `MANIFEST.md` §003/§004,
  `.planning/sketches/003-train-bot-guess-bubble/index.html` (bubble/nudge CSS)

### Tertiary (LOW confidence)
- None. No external/web source was needed: the phase adds no dependency and introduces
  no pattern that is not already present in the repository.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new package; every version read from the lockfile/manifest
- Architecture (Findings A–L): HIGH — each anchored to a file:line read this session;
  the two SQL drafts and the date-fns behaviour were executed, not assumed
- Pitfalls: HIGH for 1,2,4,5,7,8,9,10,11,12,14 (all file-anchored); MEDIUM for 3
  (animation replay is a known browser behaviour, the React remount fix is standard but
  the specific interaction with `tw-animate-css` was not exercised); MEDIUM for 6
  (the mechanism is verified, the specific 375px outcome is A1)
- Validation architecture: HIGH — frameworks, configs and existing test files all read;
  the one genuinely new coverage area (a per-query activity test) is called out
- Security: HIGH — the V4/V5 controls are the file-verified existing conventions; the V8
  re-check reuses the schema's own stated standard

**Research date:** 2026-09-13
**Valid until:** 2026-10-13 (30 days — no external dependency to go stale; the only decay
risk is further line drift in `TrainSolveScreen.tsx` / `TrainReveal.tsx` if another phase
touches them first)
