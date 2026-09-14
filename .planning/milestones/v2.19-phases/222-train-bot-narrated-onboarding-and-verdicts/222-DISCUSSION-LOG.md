# Phase 222: Train Bot-Narrated Onboarding & Verdicts - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-13
**Phase:** 222-train-bot-narrated-onboarding-and-verdicts
**Areas discussed:** Bot casting & bubble states, Seen flag & existing users, Return dates & score data, Final copy

---

## Bot casting & bubble states

| Option | Description | Selected |
|--------|-------------|----------|
| Hilda always | One stable host for the guess question | |
| Random friendly bot per puzzle | Random host, unseeded | ✓ (as random SMART bot, see below) |
| Random friendly bot per session | Stable per session, needs persistence | |

**User's choice:** Random per puzzle; no seeding/persistence, a reload picking another bot is fine.

| Option | Description | Selected |
|--------|-------------|----------|
| Deterministic hash of session_id + position | Stable across reload/device | |
| Math.random per reveal | Simplest | ✓ |
| Cycle through the set | Predictable rotation | |

| Option | Description | Selected |
|--------|-------------|----------|
| Two explicit PersonaId lists | Curation local to Train | |
| Temperament field on Persona | Field on all 24 registry entries | ✓ (stern / friendly / smart) |

**Notes:** User added a third value, `smart`.

| Option | Description | Selected |
|--------|-------------|----------|
| Same host bubble, copy swaps | One slot through guess → move → grading | ✓ |
| Bubble disappears after the guess | Today's prompt lines return | |

| Option | Description | Selected |
|--------|-------------|----------|
| Smart = explainers | Smart bots do the teaching | |
| Smart bots host the guess bubble | Random smart host asks every puzzle | ✓ |
| Label only | Reserved for later | |

| Option | Description | Selected |
|--------|-------------|----------|
| Claude drafts the 24-row mapping, user reviews in CONTEXT.md | | ✓ |
| Only the seed's ten get a label | | |
| User gives the list now | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Random smart bot on the score screen | | ✓ |
| Band-matched stern/friendly | | |
| Always Tank | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Stack the two guess buttons full-width below sm | | |
| Shorten the labels | | |
| You decide | | |

**User's choice (Other):** Rephrase the question to "Is there only one or several good moves?" with buttons "Only one" / "Several".

| Option | Description | Selected |
|--------|-------------|----------|
| The puzzle's smart host narrates the teaching steps | | |
| A fixed smart bot (Hilda) for all teaching | | ✓ |
| Tank does all three intro steps | | |

---

## Seen flag & existing users

| Option | Description | Selected |
|--------|-------------|----------|
| Three timestamps on train_settings | intro_seen_at, reveal_walkthrough_seen_at, sr_explained_at | ✓ |
| One onboarding_stage column | Ordered enum | |
| One boolean | First session done | |

| Option | Description | Selected |
|--------|-------------|----------|
| Client stamps on dismiss via a dedicated endpoint | Only a completed stepper counts | ✓ |
| Server stamps on the triggering event | | |
| Client stamps on first display | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Everyone sees them once, no backfill | | ✓ |
| Backfill users with ≥1 completed session | | |
| Backfill everyone with any session | | |

| Option | Description | Selected |
|--------|-------------|----------|
| db-report skill section | | |
| Standalone script | | |
| SQL block in the seed | | |

**User's choice (Other):** The activity dashboard has a Train sessions section; add the funnel metrics there.

| Option | Description | Selected |
|--------|-------------|----------|
| Cohort by first-session date in the selected window, all-time baseline line | | ✓ |
| All-time only, two tiles | | |
| Weekly cohort chart | | |

---

## Return dates & score data

| Option | Description | Selected |
|--------|-------------|----------|
| Server dates only (due_date <= expires_on → next session; else N = due_date − session_date) | | ✓ |
| Client local today | | |
| Always "in N days" | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Distinct lines: mastered / parked / herring-filler | | ✓ |
| One shared no-return line | | |
| You decide | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Extend SolvedResult with source, item_status, due_date | | ✓ |
| Client accumulates SolveResponses | | |
| New session summary endpoint | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Counts grouped by when | | ✓ |
| Per-position list with move and date | | |
| Counts later / list on the first session | | |

---

## Final copy

Round 1: Claude drafted four groups from the sketch placeholders. Group 3 (reveal
walkthrough) approved as a starting point; groups 1, 2, 4 sent back with pointers:
open with "Welcome to FlawChess Train, my chess boot camp.", stress that these are not
ordinary puzzles (own mistakes; when to spend time vs. play a good-enough move
quickly), the goal is understanding patterns via the analysis tools rather than
memorizing, and reminders establish the training habit.

Round 2: revised groups 1, 2 and 4 approved as starting points (structure and
messages locked, wording may be tightened).

---

## Claude's Discretion

Chat-row visuals within the sketch, endpoint shape for stamping, whether the first
puzzle's host is Hilda by construction, test strategy for random casts.

## Deferred Ideas

Sound toggle re-homing seed; bot face in the points pop; bot images on the Train
landing page.
