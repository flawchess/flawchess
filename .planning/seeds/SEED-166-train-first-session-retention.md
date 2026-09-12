---
id: SEED-166
status: planted
planted: 2026-09-12
planted_during: /gsd-explore "Train retention" (prod funnel cut + research pass)
trigger_when: next Train window; both fixes share one metric pair and should ship together so the second one has a population to act on
scope: one phase — (A) first-ever-puzzle premise explanation inline at the guess step, (B) first-completed-session close that explains spaced repetition and frames the reminder as being for the user; plus two funnel metrics recorded before/after
---

# SEED-166: Train loses 57% of first-timers before their first move, and half of the rest after one session

## Symptom

5–7 completed Train sessions per day, almost all from the same ~5 users. Personalized
training is the only feature built to bring the same person back on a schedule, and it
isn't doing that.

## Prod funnel (2026-09-12, `drill_sessions` / `drill_solves` / `train_settings`)

Every user who ever opened a Train session, bucketed by completed sessions:

| Completed | Users | Reminder on | Pressed "Remind me" | First session: solved 0 puzzles |
|---:|---:|---:|---:|---:|
| 0 | **70** | 2 | – | **52** |
| 1 | 27 | 2 | 0 | 4 |
| 2–4 | 18 | 1 | 1 | 12 |
| 5+ | 8 | 2 | (incl. above) | – |

Of 123 openers: 57% never finished a session, 22% finished exactly one, 21% came back.
Five users hold 126 of 220 completed sessions.

Facts that shaped the diagnosis:

- **52 of the 70 never-finishers left the first puzzle without playing a move**
  (`solved_at IS NULL` on every row of their first session). 14 quit after 1–2 puzzles,
  4 after 3+. The leak is at the first screen, not mid-session.
- **Warm-up is not the cause.** Only 5 of the 70 (and 4 of the 27 one-timers) got a
  warm-up first session; the typical bouncer had real own-blunder puzzles waiting.
- **One-timers did fine**: solved ~5 of ~7, 61% guesses right, 64% moves right, missed
  2.7 puzzles on average (only 3 of 27 missed nothing). So there is always something
  concrete to promise at the end ("these 3 come back").
- **The reminder ask is not being declined at the permission prompt; it isn't pressed.**
  `reminder_intent_at` is null for all 27 one-timers. 7 of 123 openers ever enabled it.
- 25 of 27 one-timers are on the untouched `weekday_mask = 127` (daily) default.
  Decision: **daily stays**; it is the right SR cadence and the leak is elsewhere.

## Diagnosis

Two separate leaks, different populations, different fixes, one root: the product never
states its premise.

**Leak 1 (first puzzle, ~42% of first-timers).** The first thing a new user sees is a
locked board and *"Before you move with white, decide: [One critical move] [Several fine
moves]"*. Nothing says why. The guess step is the actual skill Train exists to build:
in a real game nobody tells you a tactic is on the board, and deciding whether this is
a moment that demands precision or a normal position where several moves are fine is the
decision you face every move. Ordinary puzzle sites skip that decision by construction.
A newcomer who has only seen ordinary puzzles reads the two buttons as an unexplained
quiz and leaves.

Compounding it, and probably the dominant mechanism for the 52: **the locked board
gives no feedback.** Pieces are draggable before the guess, and `handlePieceDrop`
returns `false` silently while `guess === null`
(`frontend/src/components/train/TrainSolveScreen.tsx:535`), so a dragged piece snaps
back with no explanation. On a phone the board fills the viewport and the prompt plus
the two buttons sit below it in small text. The natural first action on a chessboard
is to move a piece; here that action fails silently, and the instruction that would
have explained it is the thing the user skipped.

**Leak 2 (after one completed session, ~half of finishers).** The score screen says
"Session complete" plus stats and a "Remind me" button. It closes a loop instead of
opening one. Nothing tells the user that the positions they missed will come back, when,
or why repeating *their own* blunders at growing intervals is worth more than a fresh
puzzle rush. The reminder is therefore an unmotivated ask for commitment before any value
has been felt. The next-session cue that does exist lives on the landing page, which only
a returning user sees.

Onboarding *before* the session (a spaced-repetition explainer up front) would touch
neither leak: leak 1 is at the puzzle, leak 2 is at the close.

## Research (admitted claims only, with sources)

- Anki labels every answer button with the interval that answer produces ("Each answer
  button shows the next time a card will be reviewed"), so the SR payoff is visible from
  the first card. https://docs.ankiweb.net/studying.html
- Duolingo moved signup behind the first lesson (+20% DAU) and tuned reminder cadence to
  23.5h: commitment asks belong after the first value moment.
  https://review.firstround.com/the-tenets-of-a-b-testing-from-duolingos-master-growth-hacker/
- Lichess Storm has no tutorial; its one non-obvious mechanic is explained inline at the
  moment it applies ("Skip this move to preserve your combo! Only works once per race").
  https://raw.githubusercontent.com/lichess-org/lila/master/translation/source/storm.xml

Unresolved (do not cite as fact): Chessable surfacing next-due in-product (interval list
is primary, display claim unsourced); "ask for push at session 4–6" opt-in figures (all
trace to a dead vendor post); any day-1→day-2 return benchmark.

## Scope

**A. First-ever puzzle: explain the premise, inline, once.** Before the first guess is
committed, state in a few lines: this is a real position from a real game (yours, once
enough are analyzed); unlike a puzzle, nobody has told you whether a tactic exists;
decide first, then play. Define the two buttons: *one critical move* = a single move
matters and everything else loses something; *several fine moves* = a normal position,
several moves are fine, just play sensibly. Say that the guess is the point, not a
formality. Storm-style: at the buttons, not a pre-session page. Shown once per user
(server-side flag, not device-local).

The locked board must react to a move attempt. Options, in order of preference: on a
drop while `guess === null`, pull the guess prompt into view and make it impossible to
miss (overlay on the board, or shake/pulse the two buttons and scroll them into view);
or put the guess prompt *on* the board from the start (an overlay the user dismisses by
choosing) so the first tap is the guess and there is no silent failure to have. Either
way, no drag may ever snap back with nothing said. Decide in the UI phase; the mobile
viewport (board fills the screen, prompt below the fold) is the layout to design for.

**B. First completed session: explain spaced repetition and the reminder's purpose.**
On the score screen of the first completed session (and lighter on later ones): the N
positions you missed come back, and when (Anki-style "returns in 3 days", from the
actual SR schedule); the ones you got are parked until later; why repeating your own
blunders at growing intervals beats one-off puzzles; and that "Remind me" exists so
this works for you, not for us. The reminder ask comes *after* that explanation, in
the same view.

**C. Metrics, recorded before and after** (SQL in this seed's history, or add to
`db-report`):
- First-session 0-solve rate: users whose first session has no `solved_at` / users who
  ever opened a session. Baseline **52/123 = 42%**.
- Second-session return: users with ≥2 completed / users with ≥1 completed. Baseline
  **26/53 = 49%**.

## Out of scope

- Changing the daily default cadence (decided: keep).
- Push channel changes (email, etc.). The button isn't pressed; the channel isn't the
  problem yet.
- A pre-session spaced-repetition onboarding page.
